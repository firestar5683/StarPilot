from collections import deque

import numpy as np

from opendbc.can.packer import CANPacker
from opendbc.car import Bus
from opendbc.car.interfaces import CarControllerBase
from opendbc.car.lateral import apply_std_steer_angle_limits
from opendbc.car.volvo.helpers import LCA3CounterSync
from opendbc.car.volvo.volvocan import (create_c1_cancel, create_c1_pscm_message, create_c1_steering_control, create_lca_message,
                                        create_pscm_message, create_lca_3_message, create_lca_2_message, create_lca_4_message, create_lca_5_message,
                                        create_lca_6_message, create_lca_7_message, create_pscm_related_message)
from opendbc.car.volvo.values import CAR, CarControllerParams, VolvoC1PlatformConfig


class CarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.is_c1 = isinstance(CAR(CP.carFingerprint).config, VolvoC1PlatformConfig)
    self.packer = CANPacker(dbc_names[Bus.pt] if self.is_c1 else dbc_names[Bus.party])
    self.apply_angle_last = 0.0  # Track last applied steering angle
    self.c1_torque_samples = deque(maxlen=CarControllerParams.C1_N_ZERO_TORQUE)
    self.c1_recovery_until = -1

    self.gear_acc = 60
    self.lca_4_acc = 0  # Bresenham accumulator for 29 Hz

    # Counter management for LCA_2
    self.lca_2_counter_1 = None  # Will grab initial value from CarState
    self.lca_2_counter_2 = None

    # Counter management for PSCM_RELATED
    self.pscm_related_counter = None  # Will grab initial value from CarState

    # Counter management for LCA_3 (pattern-based)
    self.lca_3_counter_sync = LCA3CounterSync()

    # Counter management for LCA_5 (formerly SPEED_1)
    self.lca_5_counter = None  # Will grab initial value from CarState

    self.last_lat_active = False  # Track state

    self.lca_7_acc = 0  # Bresenham accumulator for 29 Hz
    self.lca_7_last_steer = 0 # used to calculate change in steer from last update

    # LCA torque-authority envelope state. Both arms are persistent across frames.
    # See CarControllerParams.LCA_AUTH_* and route_analysis/lca_override_mechanism.md.
    # When lat_active goes True they ramp up from 0 to ±MAX at REBUILD_RATE; on
    # driver override they collapse at COLLAPSE_RATE (symmetric until SPLIT, then
    # asymmetric: yielding arm → 0, counter arm holds at ±PLATEAU).
    self.lca_auth_pos = 0.0
    self.lca_auth_neg = 0.0
    # "Light contact" rising-edge detector for haptic-ack on resting hands.
    # Per-frame |drv| derivative; LIGHT_HOLD_FRAMES counter ticks down while
    # the brief-yield window is active and does not re-arm during that window.
    self.lca_auth_drv_prev = 0.0
    self.lca_auth_light_frames = 0
    # Frames since real_override was last active — used to gate light_collapse
    # re-arming during active co-steering (must be > LIGHT_COOLDOWN_FRAMES).
    self.lca_auth_real_off_frames = 1000  # large initial → light can fire immediately
    # Override-mode latch with hysteresis (enter at ENTER, exit at EXIT).
    # Prevents threshold flapping when driver torque hovers near the boundary,
    # which caused ~10 Hz EPS-torque ripple felt during lane-change overrides.
    self.lca_auth_override_active = False
    # LP-filtered |drv| for yield-arm magnitude calculation. Suppresses 1-2
    # unit driver-torque jitter that would otherwise propagate (~10x amplified
    # via YIELD_SLOPE) into envelope ripple felt at the wheel.
    self.lca_auth_drv_mag_filt = 0.0

  def update(self, CC, CS, now_nanos, starpilot_toggles):
    if self.is_c1:
      return self._update_c1(CC, CS)

    can_sends = []
    actuators = CC.actuators

    # Detect disengagement
    if not CC.latActive and self.last_lat_active:
      #self.lca_commands.reset()  # Clear state ← IMPORTANT!
      pass

    lat_active = CC.latActive

    # lateral control - angle-based steering
    # NOTE: LCA message is sent every frame (even when inactive) to replace stock LCA
    # Stock LCA is permanently blocked by panda safety, so we must always send
    if self.frame % CarControllerParams.STEER_STEP == 0:  # 100 Hz
      # Get desired steering angle from controlsd (LatControlAngle)
      apply_angle = actuators.steeringAngleDeg  # degrees

      # Clamp commanded angle to actual ± ANGLE_ERROR. Without this, a driver override
      # lets the model's plan drift far from the wheel's actual position; on release,
      # the EPS slams back toward that stale command and overshoots. Stock Volvo Pilot
      # Assist keeps this gap inside ~2° even under sustained override.
      apply_angle = float(np.clip(
        apply_angle,
        CS.out.steeringAngleDeg - CarControllerParams.ANGLE_ERROR,
        CS.out.steeringAngleDeg + CarControllerParams.ANGLE_ERROR,
      ))

      # Rate limit + inactive passthrough (apply_angle = steering angle when not lat_active)
      apply_angle = apply_std_steer_angle_limits(apply_angle, self.apply_angle_last, CS.out.vEgoRaw,
                                                 CS.out.steeringAngleDeg, lat_active, CarControllerParams.ANGLE_LIMITS)

      # Update LCA torque-authority envelope (replicates stock Pilot Assist's
      # easy-override and bounce-free release). Stock holds both arms at ±614
      # in steady state; on override the arms collapse to a shifted plateau
      # (counter arm deeper than yielding arm); rebuilds at +230 c/s.
      P = CarControllerParams
      DT = 0.01  # 100 Hz
      # Override trigger uses an explicit |steeringTorque| threshold rather than
      # CS.steeringPressed, which is a very-sensitive DM-fallback floor (raw>2)
      # — fires from resting hands alone and is not an override-intent signal.
      drv_mag = abs(CS.out.steeringTorque)
      drv_rate = drv_mag - self.lca_auth_drv_prev
      self.lca_auth_drv_prev = drv_mag
      # LP filter on |drv| used for yield-arm magnitude — absorbs 1-2 unit
      # driver-torque jitter that would otherwise propagate into ~10 unit
      # envelope ripple via the YIELD_SLOPE multiplier.
      self.lca_auth_drv_mag_filt = ((1.0 - P.LCA_AUTH_YIELD_LP_ALPHA) * self.lca_auth_drv_mag_filt
                                    + P.LCA_AUTH_YIELD_LP_ALPHA * drv_mag)
      # Hysteretic override latch — enter at ENTER, hold until drv drops below
      # EXIT. Eliminates ~10 Hz envelope flapping when |drv| hovers near a
      # single threshold during sustained co-steering.
      if not self.lca_auth_override_active and drv_mag > P.LCA_AUTH_OVERRIDE_ENTER:
        self.lca_auth_override_active = True
      elif self.lca_auth_override_active and drv_mag < P.LCA_AUTH_OVERRIDE_EXIT:
        self.lca_auth_override_active = False
      real_override = self.lca_auth_override_active
      # Track frames since real_override was last active. Used to gate light
      # contact re-firing — light_collapse must NOT trigger while the driver
      # is actively co-steering (real_override repeatedly entering/exiting).
      if real_override:
        self.lca_auth_real_off_frames = 0
      else:
        self.lca_auth_real_off_frames += 1
      # Per-frame rising edge into the "light contact" zone arms a brief-yield
      # window for haptic acknowledgment of hand-on-wheel. Suppressed while
      # the window is already active OR real_override has been off less than
      # LIGHT_COOLDOWN_FRAMES (i.e., user is actively co-steering).
      if (drv_mag > P.LCA_AUTH_LIGHT_THRESH and
          drv_rate > P.LCA_AUTH_LIGHT_RISE_DELTA and
          self.lca_auth_light_frames == 0 and
          self.lca_auth_real_off_frames > P.LCA_AUTH_LIGHT_COOLDOWN_FRAMES):
        self.lca_auth_light_frames = P.LCA_AUTH_LIGHT_HOLD_FRAMES
      else:
        self.lca_auth_light_frames = max(0, self.lca_auth_light_frames - 1)
      light_collapse = self.lca_auth_light_frames > 0
      overriding = real_override or light_collapse
      # Collapse rate scales with driver torque so a sharp pothole jolt drops the
      # envelope faster than a soft sustained press. Floor at base rate so light
      # contact still produces a perceptible (but small) dip.
      collapse_rate = P.LCA_AUTH_COLLAPSE_RATE * max(1.0, drv_mag / float(P.LCA_AUTH_OVERRIDE_ENTER))
      step = collapse_rate * DT
      if not lat_active:
        self.lca_auth_pos = 0.0
        self.lca_auth_neg = 0.0
        self.lca_auth_drv_prev = 0.0
        self.lca_auth_light_frames = 0
        self.lca_auth_override_active = False
        self.lca_auth_drv_mag_filt = 0.0
        self.lca_auth_real_off_frames = 1000
      elif overriding:
        if self.lca_auth_pos > P.LCA_AUTH_SPLIT or -self.lca_auth_neg > P.LCA_AUTH_SPLIT:
          # Symmetric collapse phase: both arms shrink toward ±SPLIT
          self.lca_auth_pos = max(float(P.LCA_AUTH_SPLIT), self.lca_auth_pos - step)
          self.lca_auth_neg = min(-float(P.LCA_AUTH_SPLIT), self.lca_auth_neg + step)
        else:
          # Asymmetric plateau phase. CS.out.steeringTorque > 0 in openpilot
          # convention = driver pushing right → yields right authority
          # (LOOSELY/+ arm), retains left (INV/- arm).
          # Yield arm scales with |drv| above OVERRIDE_THRESH — strong presses
          # (potholes, hard corrections) cross past zero so EPS hands the wheel
          # to the driver in their direction.
          excess = max(0.0, self.lca_auth_drv_mag_filt - float(P.LCA_AUTH_OVERRIDE_ENTER))
          yield_signed = float(P.LCA_AUTH_YIELD_BASE) - P.LCA_AUTH_YIELD_SLOPE * excess
          yield_signed = max(float(P.LCA_AUTH_YIELD_MIN), min(yield_signed, float(P.LCA_AUTH_YIELD_BASE)))
          if CS.out.steeringTorque > 0:  # driver pushing right
            target_pos = yield_signed                              # yield arm (+ side)
            target_neg = -float(P.LCA_AUTH_PLATEAU_COUNTER)        # counter arm
          else:  # driver pushing left (or zero — default to symmetric collapse direction)
            target_pos = float(P.LCA_AUTH_PLATEAU_COUNTER)         # counter arm
            target_neg = -yield_signed                             # yield arm (− side)
          # Drive each arm toward its plateau target at COLLAPSE_RATE
          self.lca_auth_pos = max(target_pos, self.lca_auth_pos - step) \
                              if self.lca_auth_pos > target_pos \
                              else min(target_pos, self.lca_auth_pos + step)
          self.lca_auth_neg = min(target_neg, self.lca_auth_neg + step) \
                              if self.lca_auth_neg < target_neg \
                              else max(target_neg, self.lca_auth_neg - step)
      else:
        # No override → rebuild both arms toward saturation
        rebuild_step = P.LCA_AUTH_REBUILD_RATE * DT
        self.lca_auth_pos = min(float(P.LCA_AUTH_MAX), self.lca_auth_pos + rebuild_step)
        self.lca_auth_neg = max(-float(P.LCA_AUTH_MAX), self.lca_auth_neg - rebuild_step)

      # LCA - 0x58 - 100 Hz (angle-based)
      can_sends.append(create_lca_message(self.packer, lat_active, apply_angle, CS.msg_lca,
                                          authority_pos=int(round(self.lca_auth_pos)),
                                          authority_neg=int(round(self.lca_auth_neg))))
      self.apply_angle_last = apply_angle

      # PSCM (bus 2 -> 0) - 0x16 - 100 Hz
      can_sends.append(create_pscm_message(self.packer, lat_active, CS.msg_pscm, self.frame))
      # EGSM - 0x45 - 100 Hz
      #can_sends.append(create_egsm_message(self.packer, CS.msg_egsm))

      # PSCM_RELATED (bus 2 -> 0) - 0x17 - 100 Hz
      # Initialize counter from CarState on first run
      if self.pscm_related_counter is None:
        self.pscm_related_counter = CS.msg_pscm_related['SIG1_BYTE_1_HI_NIBBLE']

      # Increment counter by +1, wrap from 14 → 0 (modulo 15)
      self.pscm_related_counter = (self.pscm_related_counter + 1) % 15

      can_sends.append(create_pscm_related_message(self.packer, lat_active, CS.pilot_assist_engaged,
                                                     CS.msg_pscm_related, self.pscm_related_counter))

    # LCA_3 - 0x57 - avg 66.66 Hz
    #if (self.frame * 67) % 100 < 67: # if (self.frame % 3) < 2:
    # 0x57 at ~66.67 Hz: send on 2 out of every 3 frames
    # Pattern: send on frame % 3 == 0 or 2, skip when frame % 3 == 1
    if self.frame % 3 != 1:  # → 2/3 * 100 Hz = 66.67 Hz
      # Update counter with observed value, get counter to send
      counter, is_synced = self.lca_3_counter_sync.update(CS.msg_lca_3['COUNTER_1'])
      can_sends.append(create_lca_3_message(self.packer, lat_active, apply_angle, CS.msg_lca_3, counter))
      #can_sends.append(create_0x1a_message(self.packer, CS.msg_0x1a))

    # SPEED messages - 0x60, 0x68 - 50 Hz
    if self.frame % 2 == 0: # 50 Hz
      #can_sends.append(create_speed_message(self.packer, CS.msg_speed))
      #can_sends.append(create_speed_2_message(self.packer, CS.msg_speed_2))
      pass

    # LCA_2 - 0x69 - 50 Hz
    # Spoof PILOT_ASSIST_ENGAGED to keep PSCM accepting LCA commands
    if self.frame % 2 == 0: # 50 Hz
      # Initialize counters from CarState on first run
      if self.lca_2_counter_1 is None:
        self.lca_2_counter_1 = CS.msg_lca_2['COUNTER_1']
        self.lca_2_counter_2 = CS.msg_lca_2['COUNTER_2']

      # Increment counters (COUNTER_1 by +2, COUNTER_2 by +4, both modulo 16)
      self.lca_2_counter_1 = (self.lca_2_counter_1 + 2) % 16
      self.lca_2_counter_2 = (self.lca_2_counter_2 + 4) % 16

      can_sends.append(create_lca_2_message(self.packer, lat_active, CS.msg_lca_2,
                                            self.lca_2_counter_1, self.lca_2_counter_2))

    # LCA_5 (formerly SPEED_1) - 0x67 - 50 Hz
    # Contains wheel speeds + LCA signals (LCA_TURN_BITS, LCA_5_STEER)
    if self.frame % 2 == 0: # 50 Hz
      # Initialize counter from CarState on first run
      if self.lca_5_counter is None:
        self.lca_5_counter = CS.msg_lca_5['COUNTER']

      # Increment counter by +4, wrap at 15 (0xF never used)
      self.lca_5_counter = (self.lca_5_counter + 4) % 15

      can_sends.append(create_lca_5_message(self.packer, lat_active, apply_angle,
                                            CS.msg_lca_5, self.lca_5_counter))

    # LCA_4 - 0x90 - 29 Hz
    # Spoof LCA_ENABLE bits to maintain PA ON state when openpilot is active
    # Using Bresenham-style accumulator for precise 29 Hz
    self.lca_4_acc += 29
    if self.lca_4_acc >= 100:
      self.lca_4_acc -= 100
      can_sends.append(create_lca_4_message(self.packer, lat_active, CS.msg_lca_4, apply_angle))

    # LCA_6 - 0X97 - 25 Hz
    if self.frame % 4 == 0: # 25 Hz
        can_sends.append(create_lca_6_message(self.packer, lat_active, CS.msg_lca_6, apply_angle))

    # LCA_7 - 0x92 - 29 Hz
    # Using Bresenham-style accumulator for precise 29 Hz
    self.lca_7_acc += 29
    if self.lca_7_acc >= 100:
      self.lca_7_acc -= 100
      delta_steer = apply_angle - self.lca_7_last_steer
      can_sends.append(create_lca_7_message(self.packer, lat_active, CS.msg_lca_7, apply_angle, delta_steer))
      self.lca_7_last_steer = apply_angle

    # GEAR_POSITION - 0x80 - 40 Hz
    #self.gear_acc += 40 # Bresenham-style approach
    #if self.gear_acc >= 100:
    #    self.gear_acc -= 100
    if self.frame % 5 == 0 or self.frame % 5 == 2:  # 2/5 * 100 Hz = 40 Hz # openpilot forward delay causes DTC in EGSM, but fixes DTC in PSCM
      #can_sends.append(create_gear_position_message(self.packer, CS.msg_gear_position))
      pass

    new_actuators = actuators.as_builder()
    new_actuators.steeringAngleDeg = self.apply_angle_last
    self.frame += 1
    self.last_lat_active = CC.latActive
    return new_actuators, can_sends

  def _update_c1(self, CC, CS):
    can_sends = []
    actuators = CC.actuators

    if self.frame % 2 == 0:  # stock FSM1 and PSCM1 messages are 50 Hz
      requested_active = CC.latActive and CS.out.vEgo > self.CP.minSteerSpeed
      recovering = requested_active and self.frame < self.c1_recovery_until

      if not requested_active:
        self.c1_torque_samples.clear()
        self.c1_recovery_until = -1
      elif recovering:
        self.c1_torque_samples.clear()
      else:
        if self.c1_recovery_until >= 0:
          self.c1_recovery_until = -1
          self.c1_torque_samples.clear()
        self.c1_torque_samples.append(CS.c1_lka_torque)
        if (len(self.c1_torque_samples) == CarControllerParams.C1_N_ZERO_TORQUE and
            all(torque == 0 for torque in self.c1_torque_samples)):
          self.c1_recovery_until = self.frame + 100
          self.c1_torque_samples.clear()
          recovering = True

      lat_active = requested_active and not recovering
      desired_angle = float(np.clip(
        actuators.steeringAngleDeg,
        CS.out.steeringAngleDeg - CarControllerParams.C1_ANGLE_ERROR,
        CS.out.steeringAngleDeg + CarControllerParams.C1_ANGLE_ERROR,
      ))
      apply_angle = apply_std_steer_angle_limits(
        desired_angle, self.apply_angle_last, CS.out.vEgoRaw,
        CS.out.steeringAngleDeg, lat_active, CarControllerParams.C1_ANGLE_LIMITS,
      )

      can_sends.append(create_c1_pscm_message(self.packer, CS.c1_msg_pscm))
      can_sends.append(create_c1_steering_control(self.packer, apply_angle, lat_active))
      self.apply_angle_last = apply_angle

    if CC.cruiseControl.cancel and self.frame % 10 == 0:
      can_sends.append(create_c1_cancel(self.packer))

    new_actuators = actuators.as_builder()
    new_actuators.steeringAngleDeg = self.apply_angle_last
    self.frame += 1
    return new_actuators, can_sends
