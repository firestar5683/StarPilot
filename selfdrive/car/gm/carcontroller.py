from typing import Tuple
import time
from cereal import car
from openpilot.common.conversions import Conversions as CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.numpy_fast import interp, clip
from openpilot.common.realtime import DT_CTRL
from openpilot.common.params_pyx import Params
from opendbc.can.packer import CANPacker
from openpilot.selfdrive.car import apply_driver_steer_torque_limits, create_gas_interceptor_command
from openpilot.selfdrive.car.gm import gmcan
from openpilot.selfdrive.car.gm.values import DBC, AccState, CanBus, CarControllerParams, CruiseButtons, GMFlags, CC_ONLY_CAR, SDGM_CAR, EV_CAR, CC_REGEN_PADDLE_CAR
from openpilot.selfdrive.car.interfaces import CarControllerBase
from openpilot.selfdrive.controls.lib.drive_helpers import apply_deadzone
from openpilot.selfdrive.controls.lib.vehicle_model import ACCELERATION_DUE_TO_GRAVITY
from openpilot.common.swaglog import cloudlog

VisualAlert = car.CarControl.HUDControl.VisualAlert
NetworkLocation = car.CarParams.NetworkLocation
LongCtrlState = car.CarControl.Actuators.LongControlState
GearShifter = car.CarState.GearShifter
TransmissionType = car.CarParams.TransmissionType

# Camera cancels up to 0.1s after brake is pressed, ECM allows 0.5s
CAMERA_CANCEL_DELAY_FRAMES = 10
# Enforce a minimum interval between steering messages to avoid a fault
MIN_STEER_MSG_INTERVAL_MS = 15
# Two‑sided spacing tuned for ~33 Hz steer; target a 10 ms wide window per interval
# Paddle spoofing and scheduling constants
PADDLE_STEER_GAP_MIN_NS = 5_000_000   # ≥5 ms each side (EPS guard)
PADDLE_STEER_GAP_MAX_NS = 12_000_000  # cap for long intervals
PADDLE_GAP_TARGET_NS    = 5_000_000   # aim per‑side gap even if interval//2 − early is larger
PADDLE_NONBLOCK_GAP_NS  = 1_000_000   # ≥1 ms since last paddle send
PADDLE_SLOT_EARLY_NS    = 1_000_000   # allow firing up to 1 ms before slot
OVERFLOW_THRESH         = 1.00        # fire one extra slot whenever credits ≥ 1.0
PADDLE_TARGET_HZ        = 42.0        # desired paddle rate (Hz) when regen active; steer is ~33 Hz
# Constants for pitch compensation
BRAKE_PITCH_FACTOR_BP = [5., 10.]  # [m/s] smoothly revert to planned accel at low speeds
BRAKE_PITCH_FACTOR_V = [0., 1.]  # [unitless in [0,1]]; don't touch
PITCH_DEADZONE = 0.01  # [radians] 0.01 ≈ 1% grade

class CarController(CarControllerBase):
  def __init__(self, dbc_name, CP, VM):
    self.CP = CP
    self.start_time = 0.
    self.apply_steer_last = 0
    self.apply_gas = 0
    self.apply_brake = 0
    self.apply_speed = 0
    self.frame = 0
    self.last_steer_frame = 0
    self.last_steer_ts_ns = 0
    self.last_regen_active = False
    self.prev_steer_ts_ns = 0
    self.last_spoof_ts_ns = 0
    self.last_paddle_ts_ns = 0
    self.last_button_frame = 0
    self.cancel_counter = 0
    self.pedal_steady = 0.

    self.lka_steering_cmd_counter = 0
    self.lka_icon_status_last = (False, False)

    self.params = CarControllerParams(self.CP)
    self.params_ = Params()

    self.packer_pt = CANPacker(DBC[self.CP.carFingerprint]['pt'])
    self.packer_obj = CANPacker(DBC[self.CP.carFingerprint]['radar'])
    self.packer_ch = CANPacker(DBC[self.CP.carFingerprint]['chassis'])

    # FrogPilot variables
    self.accel_g = 0.0

    self.pitch = FirstOrderFilter(0., 0.09 * 4, DT_CTRL * 4)  # runs at 25 Hz
    self.accel_g = 0.0
    self.regen_paddle_pressed = False
    self.aego = 0.0
    self.regen_paddle_timer = 0



    # Midpoint + overflow spoof accumulator and flags
    self.spoof_accum = 0.0
    self.spoof_mid_sent = False
    self.spoof_over_sent = False
    self.last_interval_ns = 0

  def calc_pedal_command(self, accel: float, long_active: bool, car_velocity) -> Tuple[float, bool]:
    if not long_active:
      return 0., False

    # Regen paddle hysteresis (frame-based): hold 10 frames, with decrement dead-zone
    if not hasattr(self, 'regen_paddle_timer'):
      self.regen_paddle_timer = 0  # frames

    # Regen paddle hysteresis (frame‑based): count frames when decelerating hard, decrement only when truly released
    if self.aego < -0.7:
      self.regen_paddle_timer += 1
    elif self.aego > -0.3:
      self.regen_paddle_timer = max(self.regen_paddle_timer - 1, 0)
    # else: hold timer between -0.7 and -0.3

    # Base paddle press hysteresis
    self.regen_paddle_pressed = self.regen_paddle_timer >= 10  # 10 frames
    press_regen_paddle = self.regen_paddle_pressed


    # Regen gain ratios from bin-averaged 60–0 deceleration sweep; Calculates stronger decel from paddle
    speed_mps = [0.559, 1.678, 2.797, 3.916, 5.035, 6.154, 7.273, 8.392, 9.511, 10.63,
                 11.749, 12.868, 13.987, 15.106, 16.225, 17.344, 18.463, 19.582, 20.701, 21.820,
                 22.939, 24.058, 25.177, 26.296]
    regen_gain_ratio = [
      1.000000, 1.057308, 1.131123, 1.220611, 1.270247, 1.300253, 1.339543, 1.361002,
      1.388410, 1.403253, 1.414721, 1.430949, 1.420289, 1.436787, 1.434116, 1.436805,
      1.417508, 1.402213, 1.395360, 1.360921, 1.342030, 1.292219, 1.270048, 1.239172
    ]

    gain = interp(car_velocity, speed_mps, regen_gain_ratio)
    pedaloffset = interp(car_velocity, [0., 3, 6, 30], [0.10, 0.175, 0.240, 0.240])

    # Compute raw pedal gas
    raw_pedal_gas = clip((pedaloffset + (accel / gain) * 0.6), 0.0, 1.0) if press_regen_paddle else clip((pedaloffset + accel * 0.6), 0.0, 1.0)

    # --- Immediate application of raw pedal gas, no blending ---
    pedal_gas = raw_pedal_gas
    # Safety cap: ramp from 22% at 0 m/s to 37.25% at 10 mph (4.47 m/s), then allow full throttle
    pedal_gas_max = interp(car_velocity, [0.0, 4.47, 4.48], [0.22, 0.3725, 1.0])
    pedal_gas = clip(pedal_gas, 0.0, pedal_gas_max)
    return pedal_gas, press_regen_paddle


  def update(self, CC, CS, now_nanos, frogpilot_toggles):
    self.CS = CS
    self.aego = CS.out.aEgo
    actuators = CC.actuators
    accel = brake_accel = actuators.accel
    press_regen_paddle = False
    hud_control = CC.hudControl
    hud_alert = hud_control.visualAlert
    hud_v_cruise = hud_control.setSpeed
    if hud_v_cruise > 70:
      hud_v_cruise = 0

    # Send CAN commands.
    can_sends = []
    paddle_sends = []

    raw_regen_active = (
      self.CP.carFingerprint in CC_REGEN_PADDLE_CAR and
      self.CP.openpilotLongitudinalControl and
      CC.longActive and
      self.CP.enableGasInterceptor and
      self.regen_paddle_timer >= 10  # raw hysteresis-only (10 frames)
    )
    regen_active = raw_regen_active

    # === Spoof scheduling: midpoint + overflow (~target Hz) ===
    # Rising-edge reset on regen start
    if raw_regen_active and not self.last_regen_active:
      self.prev_steer_ts_ns = self.last_steer_ts_ns
      self.last_spoof_ts_ns = 0
      self.spoof_accum = 0.0
      self.spoof_mid_sent = False
      self.spoof_over_sent = False

    if raw_regen_active:
      # Interval between last two bus-0 steer sends
      interval_ns = self.last_steer_ts_ns - self.prev_steer_ts_ns

      # Adaptive two‑sided gap sized to the current steer interval, but capped to a target so the window stays wide enough
      gap_ns = (PADDLE_STEER_GAP_MIN_NS if interval_ns <= 0 else
                max(PADDLE_STEER_GAP_MIN_NS,
                    min(PADDLE_STEER_GAP_MAX_NS,
                        min((interval_ns // 2) - PADDLE_SLOT_EARLY_NS, PADDLE_GAP_TARGET_NS))))

      # New steer interval? clear per-interval flags and add credits to reach target Hz
      if interval_ns != self.last_interval_ns:
        self.spoof_mid_sent = False
        self.spoof_over_sent = False
        self.last_interval_ns = interval_ns
        # Add credits once per new steer interval to reach the desired paddle rate
        if interval_ns > 0:
          steer_hz = 1e9 / float(interval_ns)
          extra_needed = max(0.0, (PADDLE_TARGET_HZ / steer_hz) - 1.0)  # e.g., 42/33 − 1 ≈ 0.2727
          self.spoof_accum += extra_needed

      # Midpoint spoof: one per interval
      if not self.spoof_mid_sent and interval_ns > 0:
        midpoint_ns = self.prev_steer_ts_ns + interval_ns // 2
        cloudlog.error("PADDLE MID: Δafter=%.1fms Δbefore=%.1fms credits=%.3f timer=%d",
                       (now_nanos - self.last_steer_ts_ns) * 1e-6,
                       (now_nanos - self.prev_steer_ts_ns) * 1e-6,
                       self.spoof_accum,
                       self.regen_paddle_timer)
        # Compute spacing to last and next steer (two-sided guard)
        next_steer_ts_ns = self.last_steer_ts_ns + interval_ns if interval_ns > 0 else 0
        delta_after_ns = now_nanos - self.last_steer_ts_ns
        delta_before_ns = (next_steer_ts_ns - now_nanos) if interval_ns > 0 else 1_000_000_000
        if (CS.out.vEgo > 2.68
            and now_nanos >= (midpoint_ns - PADDLE_SLOT_EARLY_NS)
            and delta_after_ns >= gap_ns
            and delta_before_ns >= gap_ns):
          # Non-blocking 1 ms spacing for paddle frames
          if now_nanos - self.last_paddle_ts_ns >= PADDLE_NONBLOCK_GAP_NS:
            paddle_sends.append(gmcan.create_prndl2_command(self.packer_pt, CanBus.POWERTRAIN, True))
            paddle_sends.append(gmcan.create_regen_paddle_command(self.packer_pt, CanBus.POWERTRAIN, True))
            self.last_paddle_ts_ns = now_nanos
          self.last_spoof_ts_ns = now_nanos
          self.spoof_mid_sent = True

      # Overflow spoof: insert extra when accumulator allows
      if self.spoof_accum >= OVERFLOW_THRESH and not self.spoof_over_sent and interval_ns > 0:
        slot2_ns = self.prev_steer_ts_ns + (interval_ns * 2) // 3
        cloudlog.error("PADDLE OFL: Δafter=%.1fms Δbefore=%.1fms credits=%.3f thresh=%.1f timer=%d",
                       (now_nanos - self.last_steer_ts_ns) * 1e-6,
                       (now_nanos - self.prev_steer_ts_ns) * 1e-6,
                       self.spoof_accum,
                       OVERFLOW_THRESH,
                       self.regen_paddle_timer)
        # Two-sided spacing relative to steer
        next_steer_ts_ns = self.last_steer_ts_ns + interval_ns if interval_ns > 0 else 0
        delta_after_ns = now_nanos - self.last_steer_ts_ns
        delta_before_ns = (next_steer_ts_ns - now_nanos) if interval_ns > 0 else 1_000_000_000
        if (CS.out.vEgo > 2.68
            and now_nanos >= (slot2_ns - PADDLE_SLOT_EARLY_NS)
            and delta_after_ns >= gap_ns
            and delta_before_ns >= gap_ns):
          # Non-blocking 1 ms spacing for paddle frames
          if now_nanos - self.last_paddle_ts_ns >= PADDLE_NONBLOCK_GAP_NS:
            paddle_sends.append(gmcan.create_prndl2_command(self.packer_pt, CanBus.POWERTRAIN, True))
            paddle_sends.append(gmcan.create_regen_paddle_command(self.packer_pt, CanBus.POWERTRAIN, True))
            self.last_paddle_ts_ns = now_nanos
          self.last_spoof_ts_ns = now_nanos
          self.spoof_over_sent = True
          self.spoof_accum -= OVERFLOW_THRESH
    # === End Spoof scheduling ===

    # === Off-pulse scheduling on regen release ===
    if not raw_regen_active and self.last_regen_active:
      # schedule two off-slots at 1/3 and 2/3 of the last steer interval
      if self.prev_steer_ts_ns and self.last_steer_ts_ns:
        intv = self.last_steer_ts_ns - self.prev_steer_ts_ns
        self.off_schedule_ns = [
          self.prev_steer_ts_ns + intv // 3,
          self.prev_steer_ts_ns + (2 * intv) // 3
        ]
        self.off_sent = [False, False]

    if hasattr(self, "off_schedule_ns"):
      for i, t_ns in enumerate(self.off_schedule_ns):
        if not self.off_sent[i] and now_nanos >= (t_ns - PADDLE_SLOT_EARLY_NS):
          cloudlog.error("PADDLE OFF %d: Δafter=%.1fms Δto_slot=%.1fms timer=%d",
                         i,
                         (now_nanos - self.last_steer_ts_ns) * 1e-6,
                         (now_nanos - t_ns) * 1e-6,
                         self.regen_paddle_timer)
          # Two-sided spacing to steer before sending
          interval_ns = self.last_steer_ts_ns - self.prev_steer_ts_ns
          gap_ns = (PADDLE_STEER_GAP_MIN_NS if interval_ns <= 0 else
                    max(PADDLE_STEER_GAP_MIN_NS,
                        min(PADDLE_STEER_GAP_MAX_NS,
                            min((interval_ns // 2) - PADDLE_SLOT_EARLY_NS, PADDLE_GAP_TARGET_NS))))
          next_steer_ts_ns = self.last_steer_ts_ns + interval_ns if interval_ns > 0 else 0
          delta_after_ns = now_nanos - self.last_steer_ts_ns
          delta_before_ns = (next_steer_ts_ns - now_nanos) if interval_ns > 0 else 1_000_000_000
          if (delta_after_ns >= gap_ns and delta_before_ns >= gap_ns):
            # Non-blocking 1 ms spacing for paddle frames
            if now_nanos - self.last_paddle_ts_ns >= PADDLE_NONBLOCK_GAP_NS:
              paddle_sends.append(gmcan.create_prndl2_command(self.packer_pt, CanBus.POWERTRAIN, False))
              paddle_sends.append(gmcan.create_regen_paddle_command(self.packer_pt, CanBus.POWERTRAIN, False))
              self.last_paddle_ts_ns = now_nanos
            self.off_sent[i] = True
      # clean up once both off pulses are sent
      if hasattr(self, "off_sent") and all(self.off_sent):
        del self.off_schedule_ns
        del self.off_sent
    # === End off-pulse scheduling ===

    # Steering (Active: 50Hz, inactive: 10Hz)
    steer_step = self.params.STEER_STEP if CC.latActive else self.params.INACTIVE_STEER_STEP

    if self.CP.networkLocation == NetworkLocation.fwdCamera:
      # Also send at 50Hz:
      # - on startup, first few msgs are blocked
      # - until we're in sync with camera so counters align when relay closes, preventing a fault.
      #   openpilot can subtly drift, so this is activated throughout a drive to stay synced
      out_of_sync = self.lka_steering_cmd_counter % 4 != (CS.cam_lka_steering_cmd_counter + 1) % 4
      if CS.loopback_lka_steering_cmd_ts_nanos == 0 or out_of_sync:
        steer_step = self.params.STEER_STEP

    self.lka_steering_cmd_counter += 1 if CS.loopback_lka_steering_cmd_updated else 0

    # Avoid GM EPS faults when transmitting messages too close together: skip this transmit if we
    # received the ASCMLKASteeringCmd loopback confirmation too recently
    last_lka_steer_msg_ms = (now_nanos - CS.loopback_lka_steering_cmd_ts_nanos) * 1e-6
    if (self.frame - self.last_steer_frame) >= steer_step and last_lka_steer_msg_ms > MIN_STEER_MSG_INTERVAL_MS:
      # Initialize ASCMLKASteeringCmd counter using the camera until we get a msg on the bus
      if CS.loopback_lka_steering_cmd_ts_nanos == 0:
        self.lka_steering_cmd_counter = CS.pt_lka_steering_cmd_counter + 1

      if CC.latActive:
        new_steer = int(round(actuators.steer * self.params.STEER_MAX))
        apply_steer = apply_driver_steer_torque_limits(new_steer, self.apply_steer_last, CS.out.steeringTorque, self.params)
      else:
        apply_steer = 0

      # shift previous steer timestamp
      self.prev_steer_ts_ns = self.last_steer_ts_ns
      self.last_steer_ts_ns = now_nanos
      self.last_steer_frame = self.frame
      self.apply_steer_last = apply_steer
      idx = self.lka_steering_cmd_counter % 4
      can_sends.append(gmcan.create_steering_control(self.packer_pt, CanBus.POWERTRAIN, apply_steer, idx, CC.latActive))

    # Update regen_active state and last_regen_paddle_pressed for next loop
    self.last_regen_active = regen_active
    self.last_regen_paddle_pressed = self.regen_paddle_pressed

    if paddle_sends:
      interval_ns = self.last_steer_ts_ns - self.prev_steer_ts_ns
      flush_gap_ns = (PADDLE_STEER_GAP_MIN_NS if interval_ns <= 0 else
                      max(PADDLE_STEER_GAP_MIN_NS,
                          min(PADDLE_STEER_GAP_MAX_NS,
                              min((interval_ns // 2) - PADDLE_SLOT_EARLY_NS, PADDLE_GAP_TARGET_NS))))
      if now_nanos - self.last_steer_ts_ns >= flush_gap_ns:
        can_sends.extend(paddle_sends)

    if self.CP.openpilotLongitudinalControl:
      # Gas/regen, brakes, and UI commands - all at 25Hz
      if self.frame % 4 == 0:
        stopping = actuators.longControlState == LongCtrlState.stopping

        # Pitch compensated acceleration;
        # TODO: include future pitch (sm['modelDataV2'].orientation.y) to account for long actuator delay
        if frogpilot_toggles.long_pitch and len(CC.orientationNED) > 1:
          self.pitch.update(CC.orientationNED[1])
          self.accel_g = ACCELERATION_DUE_TO_GRAVITY * apply_deadzone(self.pitch.x, PITCH_DEADZONE) # driving uphill is positive pitch
          accel += self.accel_g
          brake_accel = actuators.accel + self.accel_g * interp(CS.out.vEgo, BRAKE_PITCH_FACTOR_BP, BRAKE_PITCH_FACTOR_V)

        at_full_stop = CC.longActive and CS.out.standstill
        near_stop = CC.longActive and (CS.out.vEgo < self.params.NEAR_STOP_BRAKE_PHASE)
        interceptor_gas_cmd = 0
        if not CC.longActive:
          # ASCM sends max regen when not enabled
          self.apply_gas = self.params.INACTIVE_REGEN
          self.apply_brake = 0
        elif near_stop and stopping and not CC.cruiseControl.resume:
          self.apply_gas = self.params.INACTIVE_REGEN
          self.apply_brake = int(min(-100 * frogpilot_toggles.stopAccel, self.params.MAX_BRAKE))
        else:
          # Normal operation
          self.apply_gas = int(round(interp(accel, self.params.GAS_LOOKUP_BP, self.params.GAS_LOOKUP_V)))
          self.apply_brake = int(round(interp(brake_accel, self.params.BRAKE_LOOKUP_BP, self.params.BRAKE_LOOKUP_V)))
          # Don't allow any gas above inactive regen while stopping
          # FIXME: brakes aren't applied immediately when enabling at a stop
          if stopping:
            self.apply_gas = self.params.INACTIVE_REGEN
          if self.CP.carFingerprint in CC_ONLY_CAR:
            # gas interceptor only used for full long control on cars without ACC
            interceptor_gas_cmd, press_regen_paddle = self.calc_pedal_command(actuators.accel, CC.longActive, CS.out.vEgo)

        if self.CP.enableGasInterceptor and self.apply_gas > self.params.INACTIVE_REGEN and CS.out.cruiseState.standstill:
          # "Tap" the accelerator pedal to re-engage ACC
          interceptor_gas_cmd = self.params.SNG_INTERCEPTOR_GAS
          self.apply_brake = 0
          self.apply_gas = self.params.INACTIVE_REGEN

        idx = (self.frame // 4) % 4

        if self.CP.flags & GMFlags.CC_LONG.value:
          if CC.longActive and CS.out.vEgo > self.CP.minEnableSpeed:
            # Using extend instead of append since the message is only sent intermittently
            can_sends.extend(gmcan.create_gm_cc_spam_command(self.packer_pt, self, CS, actuators))
        if self.CP.enableGasInterceptor:
          can_sends.append(create_gas_interceptor_command(self.packer_pt, interceptor_gas_cmd, idx))
        if self.CP.carFingerprint not in CC_ONLY_CAR:
          friction_brake_bus = CanBus.CHASSIS
          # GM Camera exceptions
          # TODO: can we always check the longControlState?
          if self.CP.networkLocation == NetworkLocation.fwdCamera and self.CP.carFingerprint not in CC_ONLY_CAR:
            at_full_stop = at_full_stop and stopping
            friction_brake_bus = CanBus.POWERTRAIN

          if self.CP.autoResumeSng:
            resume = actuators.longControlState != LongCtrlState.starting or CC.cruiseControl.resume
            at_full_stop = at_full_stop and not resume

          if CC.cruiseControl.resume and CS.pcm_acc_status == AccState.STANDSTILL and frogpilot_toggles.volt_sng:
            acc_engaged = False
          else:
            acc_engaged = CC.enabled

          # GasRegenCmdActive needs to be 1 to avoid cruise faults. It describes the ACC state, not actuation
          can_sends.append(gmcan.create_gas_regen_command(self.packer_pt, CanBus.POWERTRAIN, self.apply_gas, idx, acc_engaged, at_full_stop))
          can_sends.append(gmcan.create_friction_brake_command(self.packer_ch, friction_brake_bus, self.apply_brake,
                                                               idx, CC.enabled, near_stop, at_full_stop, self.CP))

          # Send dashboard UI commands (ACC status)
          send_fcw = hud_alert == VisualAlert.fcw
          can_sends.append(gmcan.create_acc_dashboard_command(self.packer_pt, CanBus.POWERTRAIN, CC.enabled,
                                                              hud_v_cruise * CV.MS_TO_KPH, hud_control, send_fcw))
      else:
        # to keep accel steady for logs when not sending gas
        accel += self.accel_g

      # Radar needs to know current speed and yaw rate (50hz),
      # and that ADAS is alive (5hz, previously 10hz)
      if not self.CP.radarUnavailable:
        tt = self.frame * DT_CTRL
        time_and_headlights_step = 20
        if self.frame % time_and_headlights_step == 0:
          idx = (self.frame // time_and_headlights_step) % 4
          can_sends.append(gmcan.create_adas_time_status(CanBus.OBSTACLE, int((tt - self.start_time) * 60), idx))
          can_sends.append(gmcan.create_adas_headlights_status(self.packer_obj, CanBus.OBSTACLE))
          can_sends.append(gmcan.create_adas_steering_status(CanBus.OBSTACLE, idx))
          can_sends.append(gmcan.create_adas_accelerometer_speed_status(CanBus.OBSTACLE, CS.out.vEgo, idx))

      if self.CP.networkLocation == NetworkLocation.gateway and self.frame % (self.params.ADAS_KEEPALIVE_STEP * 2) == 0:
        can_sends += gmcan.create_adas_keepalive(CanBus.POWERTRAIN)

      # TODO: integrate this with the code block below?
      if (
          (self.CP.flags & GMFlags.PEDAL_LONG.value)  # Always cancel stock CC when using pedal interceptor
          or (self.CP.flags & GMFlags.CC_LONG.value and not CC.enabled)  # Cancel stock CC if OP is not active
      ) and CS.out.cruiseState.enabled:
        if (self.frame - self.last_button_frame) * DT_CTRL > 0.04:
          self.last_button_frame = self.frame
          can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.POWERTRAIN, (CS.buttons_counter + 1) % 4, CruiseButtons.CANCEL))

    else:
      # While car is braking, cancel button causes ECM to enter a soft disable state with a fault status.
      # A delayed cancellation allows camera to cancel and avoids a fault when user depresses brake quickly
      self.cancel_counter = self.cancel_counter + 1 if CC.cruiseControl.cancel else 0

      # Stock longitudinal, integrated at camera
      if (self.frame - self.last_button_frame) * DT_CTRL > 0.04:
        if self.cancel_counter > CAMERA_CANCEL_DELAY_FRAMES:
          self.last_button_frame = self.frame
          if self.CP.carFingerprint in SDGM_CAR:
            can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.POWERTRAIN, CS.buttons_counter, CruiseButtons.CANCEL))
          else:
            can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.CAMERA, CS.buttons_counter, CruiseButtons.CANCEL))

    if self.CP.networkLocation == NetworkLocation.fwdCamera:
      # Silence "Take Steering" alert sent by camera, forward PSCMStatus with HandsOffSWlDetectionStatus=1
      if self.frame % 20 == 0:
        can_sends.append(gmcan.create_pscm_status(self.packer_pt, CanBus.CAMERA, CS.pscm_status))

    new_actuators = actuators.as_builder()
    new_actuators.accel = accel
    new_actuators.steer = self.apply_steer_last / self.params.STEER_MAX
    new_actuators.steerOutputCan = self.apply_steer_last
    new_actuators.gas = self.apply_gas
    new_actuators.brake = self.apply_brake
    new_actuators.speed = self.apply_speed

    self.frame += 1
    return new_actuators, can_sends
