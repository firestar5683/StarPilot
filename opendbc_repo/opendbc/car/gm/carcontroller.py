import math
import numpy as np
from opendbc.can import CANPacker
from opendbc.car import ACCELERATION_DUE_TO_GRAVITY, Bus, DT_CTRL, create_gas_interceptor_command, structs
from opendbc.car.lateral import apply_driver_steer_torque_limits
from opendbc.car.gm import gmcan
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gm.values import ASCM_INT, CAR, CC_ONLY_CAR, CC_REGEN_PADDLE_CAR, DBC, EV_CAR, SDGM_CAR, AccState, CanBus, CarControllerParams, CruiseButtons, GMFlags
from opendbc.car.interfaces import CarControllerBase
from openpilot.common.params import Params, UnknownKeyName
from openpilot.starpilot.common.testing_grounds import testing_ground

VisualAlert = structs.CarControl.HUDControl.VisualAlert
NetworkLocation = structs.CarParams.NetworkLocation
LongCtrlState = structs.CarControl.Actuators.LongControlState

# Camera cancels up to 0.1s after brake is pressed, ECM allows 0.5s
CAMERA_CANCEL_DELAY_FRAMES = 10
# Enforce a minimum interval between steering messages to avoid a fault
MIN_STEER_MSG_INTERVAL_MS = 15


def get_stock_cc_active_for_cancel(CP, CS):
  stock_cc_active = CS.out.cruiseState.enabled or CS.pcm_acc_status != AccState.OFF
  if CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
    return CS.out.cruiseState.enabled
  return stock_cc_active


class CarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.start_time = 0.
    self.apply_torque_last = 0
    self.apply_gas = 0
    self.apply_brake = 0
    self.last_steer_frame = 0
    self.last_button_frame = 0
    self.cancel_counter = 0

    self.lka_steering_cmd_counter = 0
    self.lka_icon_status_last = (False, False)

    self.params = CarControllerParams(self.CP)

    self.packer_pt = CANPacker(DBC[self.CP.carFingerprint][Bus.pt])
    self.packer_obj = CANPacker(DBC[self.CP.carFingerprint][Bus.radar])
    self.packer_ch = CANPacker(DBC[self.CP.carFingerprint][Bus.chassis])

    self.apply_speed = 0
    self.prev_op_enabled = False
    self.pedal_steady = 0
    self.regen_paddle_pressed = False
    self.regen_paddle_timer = 0
    self.regen_press_counter = 0
    self.regen_release_counter = 0
    self.regen_min_on_frames = 0
    self.regen_min_off_frames = 0
    self.planner_regen_hold = False
    self.paddle_handoff_frames = 0
    self.pedal_active_last = False
    self.aego = 0.0
    self.maneuver_paddle_mode = "auto"
    self.params_ = Params()

    self.is_volt = self.CP.carFingerprint in {
      CAR.CHEVROLET_VOLT,
      CAR.CHEVROLET_VOLT_2019,
      CAR.CHEVROLET_VOLT_ASCM,
      CAR.CHEVROLET_VOLT_CAMERA,
      CAR.CHEVROLET_VOLT_CC,
    }
    self.mass = CP.mass
    self.tireRadius = 0.075 * CP.wheelbase + 0.1453
    self.frontalArea = 1.05 * CP.wheelbase + 0.0679
    self.coeffDrag = 0.30
    self.airDensity = 1.225
    self.malibu_cancel_phase = 0
    self.malibu_button_phase = 0
    self.malibu_last_button_ts_nanos = 0

  def calc_pedal_command(self, accel: float, long_active: bool, v_ego: float):
    if not long_active:
      self.planner_regen_hold = False
      self.regen_paddle_pressed = False
      self.regen_paddle_timer = 0
      self.regen_press_counter = 0
      self.regen_release_counter = 0
      self.regen_min_on_frames = 0
      self.regen_min_off_frames = 0
      self.pedal_active_last = False
      self.pedal_steady = 0.0
      return 0., False

    supports_regen_paddle = self.CP.carFingerprint in CC_REGEN_PADDLE_CAR
    switched_state = False
    press_regen_paddle = False
    if supports_regen_paddle:
      press_cmd_threshold = np.interp(v_ego, [0.0, 4.0, 12.0, 25.0], [-0.90, -0.82, -0.72, -0.65])
      release_cmd_threshold = np.interp(v_ego, [0.0, 4.0, 12.0, 25.0], [-0.10, -0.17, -0.24, -0.30])
      press_aego_threshold = np.interp(v_ego, [0.0, 4.0, 12.0, 25.0], [-0.95, -0.86, -0.76, -0.70])
      release_aego_threshold = np.interp(v_ego, [0.0, 4.0, 12.0, 25.0], [-0.16, -0.23, -0.30, -0.36])

      press_confirm_frames = int(round(np.interp(v_ego, [0.0, 4.0, 12.0, 25.0], [8.0, 6.0, 5.0, 4.0])))
      release_confirm_frames = int(round(np.interp(v_ego, [0.0, 4.0, 12.0, 25.0], [18.0, 15.0, 12.0, 10.0])))
      min_on_frames = int(round(np.interp(v_ego, [0.0, 4.0, 12.0, 25.0], [34.0, 27.0, 20.0, 16.0])))
      min_off_frames = int(round(np.interp(v_ego, [0.0, 4.0, 12.0, 25.0], [16.0, 14.0, 12.0, 10.0])))
      confirm_boost = int(round(np.interp(v_ego, [0.0, 6.0, 8.0, 20.0, 25.0], [0.0, 0.0, 3.0, 3.0, 0.0])))
      press_confirm_frames += confirm_boost
      release_confirm_frames += confirm_boost

      want_press = self.planner_regen_hold or accel <= press_cmd_threshold or self.aego <= press_aego_threshold
      want_release = (not self.planner_regen_hold) and accel >= release_cmd_threshold and self.aego >= release_aego_threshold

      if want_press:
        self.regen_press_counter += 1
      else:
        self.regen_press_counter = max(self.regen_press_counter - 1, 0)

      if want_release:
        self.regen_release_counter += 1
      else:
        self.regen_release_counter = max(self.regen_release_counter - 1, 0)

      if self.planner_regen_hold and accel <= (press_cmd_threshold - 0.30):
        self.regen_press_counter = max(self.regen_press_counter, press_confirm_frames)

      if self.regen_min_on_frames > 0:
        self.regen_min_on_frames -= 1
      if self.regen_min_off_frames > 0:
        self.regen_min_off_frames -= 1

      if self.regen_paddle_pressed:
        if self.regen_min_on_frames == 0 and self.regen_release_counter >= release_confirm_frames:
          self.regen_paddle_pressed = False
          self.regen_min_off_frames = min_off_frames
          self.regen_release_counter = 0
          switched_state = True
      else:
        if self.regen_min_off_frames == 0 and self.regen_press_counter >= press_confirm_frames:
          self.regen_paddle_pressed = True
          self.regen_min_on_frames = min_on_frames
          self.regen_press_counter = 0
          switched_state = True

      self.regen_paddle_timer = self.regen_press_counter
      press_regen_paddle = self.regen_paddle_pressed

      if self.maneuver_paddle_mode == "off":
        self.regen_paddle_pressed = False
        self.regen_press_counter = 0
        self.regen_release_counter = 0
        self.regen_min_on_frames = 0
        press_regen_paddle = False
      elif self.maneuver_paddle_mode == "force":
        forced_press = accel < -0.02
        self.regen_paddle_pressed = forced_press
        press_regen_paddle = forced_press
    else:
      self.planner_regen_hold = False
      self.regen_paddle_pressed = False
      self.regen_paddle_timer = 0
      self.regen_press_counter = 0
      self.regen_release_counter = 0
      self.regen_min_on_frames = 0
      self.regen_min_off_frames = 0

    speed_mps = [0.559, 1.678, 2.797, 3.916, 5.035, 6.154, 7.273, 8.392, 9.511, 10.63,
                 11.749, 12.868, 13.987, 15.106, 16.225, 17.344, 18.463, 19.582, 20.701, 21.820,
                 22.939, 24.058, 25.177, 26.296]
    regen_gain_ratio = [1.01, 1.01, 1.02, 1.05, 1.08, 1.31, 1.33,
                        1.34, 1.35, 1.36, 1.37, 1.38, 1.39, 1.39,
                        1.40, 1.40, 1.41, 1.42, 1.43, 1.43, 1.44,
                        1.44, 1.45, 1.45]

    gain = np.interp(v_ego, speed_mps, regen_gain_ratio)
    gain *= np.interp(v_ego, [0.0, 2.0, 4.0, 5.5, 8.0, 12.0], [0.92, 0.92, 0.93, 0.94, 0.96, 1.0])
    accel_gain = np.interp(v_ego, [0.0, 3.0, 8.0, 20.0], [0.47, 0.52, 0.57, 0.61])
    pedaloffset = np.interp(v_ego, [0.0, 1.0, 3.0, 6.0, 15.0, 30.0], [0.085, 0.11, 0.17, 0.23, 0.235, 0.23])

    accel_term_scale = (1.0 / max(gain, 1e-3)) if press_regen_paddle else 1.0
    if accel >= 0.0:
      small_cmd_scale = np.interp(abs(accel), [0.0, 0.35, 0.8, 1.5, 2.5], [0.58, 0.68, 0.82, 0.93, 1.0])
    else:
      small_cmd_scale = np.interp(abs(accel), [0.0, 0.35, 0.8, 1.5, 2.5], [0.44, 0.54, 0.70, 0.89, 1.0])
    accel_cmd = accel * small_cmd_scale
    if accel < -2.0:
      accel_cmd *= np.interp(abs(accel), [2.0, 2.5, 3.0], [1.0, 1.03, 1.06])
    raw_pedal_gas = float(np.clip(pedaloffset + accel_cmd * accel_gain * accel_term_scale, 0.0, 1.0))

    pedal_gas_max = np.interp(v_ego, [0.0, 1.0, 2.5, 4.5, 6.0, 8.0, 12.0], [0.20, 0.235, 0.29, 0.365, 0.52, 0.78, 1.0])
    target_pedal_gas = float(np.clip(raw_pedal_gas, 0.0, pedal_gas_max))

    if not self.pedal_active_last or switched_state:
      pedal_gas = target_pedal_gas
      self.pedal_active_last = True
    else:
      urgency = float(np.clip(abs(accel) / 2.0, 0.0, 1.0))
      rate_up = np.interp(v_ego, [0.0, 3.0, 8.0, 20.0], [0.007, 0.012, 0.022, 0.036]) + 0.011 * urgency
      if accel > 1.2:
        rate_up += np.interp(v_ego, [0.0, 4.0, 12.0, 25.0], [0.006, 0.005, 0.003, 0.002])
      rate_down = np.interp(v_ego, [0.0, 3.0, 8.0, 20.0], [0.008, 0.014, 0.026, 0.045]) + 0.015 * urgency
      pedal_gas = float(np.clip(target_pedal_gas, self.pedal_steady - rate_down, self.pedal_steady + rate_up))

    self.pedal_steady = pedal_gas
    return pedal_gas, press_regen_paddle

  def _update_malibu_button_slot(self, cs):
    button_ts = cs.steering_button_ts_nanos
    if button_ts != 0 and button_ts != self.malibu_last_button_ts_nanos:
      self.malibu_last_button_ts_nanos = button_ts
      return True
    return False

  def _sync_malibu_phase_from_oem(self, cs):
    phase_map = gmcan.malibu_phase_map_for_acc(cs.cruise_buttons)
    if phase_map and cs.steering_button_checksum in phase_map:
      phase = phase_map[cs.steering_button_checksum]
      self.malibu_cancel_phase = phase
      self.malibu_button_phase = phase

  def update(self, CC, CS, now_nanos, starpilot_toggles):
    actuators = CC.actuators
    self.aego = CS.out.aEgo
    accel = actuators.accel
    press_regen_paddle = False

    if self.frame % 25 == 0:
      try:
        mode = self.params_.get("LongitudinalManeuverPaddleMode")
      except UnknownKeyName:
        mode = "auto"
      if isinstance(mode, bytes):
        mode = mode.decode("utf-8", errors="replace")
      mode = (mode or "auto").strip().lower()
      self.maneuver_paddle_mode = mode if mode in ("auto", "off", "force") else "auto"

    kaofui_cars = SDGM_CAR | ASCM_INT | {
      CAR.CHEVROLET_VOLT,
      CAR.CHEVROLET_VOLT_2019,
      CAR.CHEVROLET_VOLT_ASCM,
      CAR.CHEVROLET_VOLT_CAMERA,
      CAR.CHEVROLET_VOLT_CC,
      CAR.CHEVROLET_MALIBU_CC,
      CAR.CHEVROLET_MALIBU_HYBRID_CC,
    }

    if (self.CP.enableGasInterceptorDEPRECATED and self.CP.carFingerprint in CC_REGEN_PADDLE_CAR and
        self.CP.openpilotLongitudinalControl and CC.longActive):
      if self.maneuver_paddle_mode == "off":
        self.planner_regen_hold = False
      elif self.maneuver_paddle_mode == "force":
        self.planner_regen_hold = accel < -0.02
      else:
        planner_press_threshold = np.interp(CS.out.vEgo, [0.0, 4.0, 12.0, 25.0], [-0.95, -0.82, -0.70, -0.62])
        planner_release_threshold = np.interp(CS.out.vEgo, [0.0, 4.0, 12.0, 25.0], [-0.14, -0.22, -0.30, -0.36])
        if accel <= planner_press_threshold:
          self.planner_regen_hold = True
        elif accel >= planner_release_threshold:
          self.planner_regen_hold = False
    else:
      self.planner_regen_hold = False

    hud_control = CC.hudControl
    hud_alert = hud_control.visualAlert
    hud_v_cruise = hud_control.setSpeed
    if hud_v_cruise > 70:
      hud_v_cruise = 0

    # Send CAN commands.
    can_sends = []
    malibu_cancel_requested = False
    malibu_oem_button_slot = False
    if self.CP.carFingerprint == CAR.CHEVROLET_MALIBU_HYBRID_CC:
      malibu_oem_button_slot = self._update_malibu_button_slot(CS)
      if malibu_oem_button_slot:
        self._sync_malibu_phase_from_oem(CS)

    raw_regen_active = (
      self.CP.carFingerprint in CC_REGEN_PADDLE_CAR and
      self.CP.openpilotLongitudinalControl and
      CC.longActive and
      self.CP.enableGasInterceptorDEPRECATED and
      self.regen_paddle_pressed
    )
    use_panda_paddle_sched = (
      self.CP.enableGasInterceptorDEPRECATED and
      self.CP.carFingerprint in CC_REGEN_PADDLE_CAR and
      self.CP.openpilotLongitudinalControl and
      bool(self.CP.flags & GMFlags.PEDAL_LONG.value)
    )
    if use_panda_paddle_sched:
      if CC.enabled:
        self.paddle_handoff_frames = 2
      paddle_sched_feed_active = CC.enabled or (self.paddle_handoff_frames > 0)
      if not CC.enabled and self.paddle_handoff_frames > 0:
        self.paddle_handoff_frames -= 1
    else:
      self.paddle_handoff_frames = 0
      paddle_sched_feed_active = False

    paddle_spoof_pressed = raw_regen_active and (CS.out.vEgo > 2.68)

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
        new_torque = int(round(actuators.torque * self.params.STEER_MAX))
        apply_torque = apply_driver_steer_torque_limits(new_torque, self.apply_torque_last, CS.out.steeringTorque, self.params)
      else:
        apply_torque = 0

      if (self.CP.flags & GMFlags.CC_LONG.value) and CC.enabled and not CS.out.cruiseState.enabled:
        # Keep steer command neutral while stock CC is not active on CC_LONG.
        apply_torque = 0

      self.last_steer_frame = self.frame
      self.apply_torque_last = apply_torque
      idx = self.lka_steering_cmd_counter % 4
      can_sends.append(gmcan.create_steering_control(self.packer_pt, CanBus.POWERTRAIN, apply_torque, idx, CC.latActive))

    spoof_ecm_cruise_cars = {
      CAR.CHEVROLET_BOLT_CC_2017,
      CAR.CHEVROLET_BOLT_CC_2018_2021,
      CAR.CHEVROLET_BOLT_CC_2022_2023,
      CAR.CHEVROLET_MALIBU_HYBRID_CC,
    }
    non_acc_pedal_long = (
      bool(self.CP.flags & GMFlags.PEDAL_LONG.value) and
      self.CP.carFingerprint in spoof_ecm_cruise_cars and
      self.CP.enableGasInterceptorDEPRECATED
    )
    if non_acc_pedal_long and self.frame % 4 == 0:
      can_sends.append(gmcan.create_ecm_cruise_control_command(
        self.packer_pt, CanBus.POWERTRAIN, True, hud_v_cruise * CV.MS_TO_KPH))

    if self.CP.openpilotLongitudinalControl:
      # Gas/regen, brakes, and UI commands - all at 25Hz
      if self.frame % 4 == 0:
        stopping = actuators.longControlState == LongCtrlState.stopping
        interceptor_gas_cmd = 0
        at_full_stop = CC.longActive and CS.out.standstill
        near_stop = CC.longActive and (CS.out.vEgo < self.params.NEAR_STOP_BRAKE_PHASE)
        if not CC.longActive:
          # ASCM sends max regen when not enabled
          self.apply_gas = self.params.INACTIVE_REGEN
          self.apply_brake = 0
          self.planner_regen_hold = False
          self.regen_paddle_pressed = False
          self.regen_paddle_timer = 0
          self.regen_press_counter = 0
          self.regen_release_counter = 0
          self.regen_min_on_frames = 0
          self.regen_min_off_frames = 0
        elif near_stop and stopping and not CC.cruiseControl.resume:
          stop_accel = getattr(starpilot_toggles, "stopAccel", self.CP.stopAccel)
          self.apply_gas = self.params.INACTIVE_REGEN
          self.apply_brake = int(min(-100 * stop_accel, self.params.MAX_BRAKE))
        else:
          long_pitch_enabled = bool(getattr(starpilot_toggles, "long_pitch", True))
          pedal_long_path = bool(self.CP.enableGasInterceptorDEPRECATED and (self.CP.flags & GMFlags.PEDAL_LONG.value))
          long_pitch_for_powertrain = long_pitch_enabled or pedal_long_path

          if self.is_volt:
            if long_pitch_for_powertrain and len(CC.orientationNED) == 3 and CS.out.vEgo > self.CP.vEgoStopping:
              volt_pitch_accel = math.sin(CC.orientationNED[1]) * ACCELERATION_DUE_TO_GRAVITY
            else:
              volt_pitch_accel = 0.0

            aero_drag_accel = (0.5 * self.coeffDrag * self.frontalArea * self.airDensity * CS.out.vEgo ** 2) / self.mass
            accel_cmd = float(np.clip(accel + aero_drag_accel + volt_pitch_accel, self.params.ACCEL_MIN, self.params.ACCEL_MAX))
            brake_accel = float(np.clip(
              accel + aero_drag_accel + volt_pitch_accel * np.interp(CS.out.vEgo, [5.0, 10.0], [0.0, 1.0]),
              self.params.ACCEL_MIN, self.params.ACCEL_MAX))

            if self.CP.carFingerprint in EV_CAR:
              self.params.update_ev_gas_brake_threshold(CS.out.vEgo)
              self.apply_gas = int(round(np.interp(accel_cmd, self.params.EV_GAS_LOOKUP_BP, self.params.GAS_LOOKUP_V)))
              self.apply_brake = int(round(np.interp(brake_accel, self.params.EV_BRAKE_LOOKUP_BP, self.params.BRAKE_LOOKUP_V)))
            else:
              self.apply_gas = int(round(np.interp(accel_cmd, self.params.GAS_LOOKUP_BP, self.params.GAS_LOOKUP_V)))
              self.apply_brake = int(round(np.interp(brake_accel, self.params.BRAKE_LOOKUP_BP, self.params.BRAKE_LOOKUP_V)))

            self.apply_gas = int(round(np.clip(self.apply_gas, self.params.MAX_ACC_REGEN, self.params.MAX_GAS)))
            self.apply_brake = int(round(np.clip(self.apply_brake, 0, self.params.MAX_BRAKE)))
            if self.apply_brake > 0:
              self.apply_gas = self.params.INACTIVE_REGEN
          else:
            if long_pitch_for_powertrain and len(CC.orientationNED) == 3 and CS.out.vEgo > self.CP.vEgoStopping:
              accel_due_to_pitch = math.sin(CC.orientationNED[1]) * ACCELERATION_DUE_TO_GRAVITY
            else:
              accel_due_to_pitch = 0.0

            gas_max = self.params.MAX_GAS
            accel_max = self.params.ACCEL_MAX
            if testing_ground.use_1:
              accel_max = min(accel_max, np.interp(CS.out.vEgo, [0.0, 4.0, 12.0], [1.25, 1.6, self.params.ACCEL_MAX]))

            accel_cmd = float(np.clip(actuators.accel + accel_due_to_pitch, self.params.ACCEL_MIN, accel_max))
            torque = self.tireRadius * ((self.mass * accel_cmd) + (0.5 * self.coeffDrag * self.frontalArea * self.airDensity * CS.out.vEgo ** 2))
            scaled_torque = torque + self.params.ZERO_GAS
            apply_gas_torque = np.clip(scaled_torque, self.params.MAX_ACC_REGEN, gas_max)
            brake_switch = int(round(np.interp(CS.out.vEgo, self.params.BRAKE_SWITCH_LOOKUP_BP, self.params.BRAKE_SWITCH_LOOKUP_V)))
            if testing_ground.use_1:
              brake_switch_bias = int(round(np.interp(CS.out.vEgo, [0.0, 6.0, 15.0, 30.0], [60.0, 120.0, 180.0, 220.0])))
              brake_switch = min(self.params.ZERO_GAS, brake_switch + brake_switch_bias)
            brake_accel = min((scaled_torque - brake_switch) / (self.tireRadius * self.mass), 0)
            self.apply_gas = int(round(apply_gas_torque))
            self.apply_brake = int(round(np.interp(brake_accel, self.params.BRAKE_LOOKUP_BP, self.params.BRAKE_LOOKUP_V)))
            if self.apply_brake > 0:
              self.apply_gas = self.params.INACTIVE_REGEN

          if stopping:
            self.apply_gas = self.params.INACTIVE_REGEN

          if self.CP.carFingerprint in CC_ONLY_CAR:
            # gas interceptor only used for full long control on cars without ACC
            interceptor_gas_cmd, press_regen_paddle = self.calc_pedal_command(actuators.accel, CC.longActive, CS.out.vEgo)

        if self.CP.enableGasInterceptorDEPRECATED and self.apply_gas > self.params.INACTIVE_REGEN and CS.out.cruiseState.standstill:
          interceptor_gas_cmd = self.params.SNG_INTERCEPTOR_GAS
          self.apply_brake = 0
          self.apply_gas = self.params.INACTIVE_REGEN

        idx = (self.frame // 4) % 4

        self.regen_paddle_pressed = press_regen_paddle
        raw_regen_active = (
          self.CP.carFingerprint in CC_REGEN_PADDLE_CAR and
          self.CP.openpilotLongitudinalControl and
          CC.longActive and
          self.CP.enableGasInterceptorDEPRECATED and
          self.regen_paddle_pressed
        )
        paddle_spoof_pressed = raw_regen_active and (CS.out.vEgo > 2.68)
        if paddle_sched_feed_active:
          can_sends.append(gmcan.create_prndl2_command(self.packer_pt, CanBus.POWERTRAIN, paddle_spoof_pressed, self.CP))
          can_sends.append(gmcan.create_regen_paddle_command(self.packer_pt, CanBus.POWERTRAIN, paddle_spoof_pressed))

        if self.CP.flags & GMFlags.CC_LONG.value:
          if CC.longActive and CS.out.cruiseState.enabled and CS.out.vEgo > self.CP.minEnableSpeed:
            # Using extend instead of append since the message is only sent intermittently
            can_sends.extend(gmcan.create_gm_cc_spam_command(self.packer_pt, self, CS, actuators, starpilot_toggles))
          elif (CS.out.cruiseState.enabled and CC.enabled and self.frame % 52 == 0 and
                CS.cruise_buttons == CruiseButtons.UNPRESS and CS.out.gasPressed and CS.out.cruiseState.speed < CS.out.vEgo < hud_v_cruise):
            if self.CP.carFingerprint == CAR.CHEVROLET_MALIBU_HYBRID_CC:
              can_sends.append(gmcan.create_buttons_malibu(
                self.packer_pt, CanBus.POWERTRAIN, CruiseButtons.DECEL_SET,
                self.malibu_button_phase, CS.steering_button_prefix))
              self.malibu_button_phase = (self.malibu_button_phase + 1) % 4
            else:
              can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.POWERTRAIN, (CS.buttons_counter + 1) % 4, CruiseButtons.DECEL_SET))
        if self.CP.enableGasInterceptorDEPRECATED:
          can_sends.append(create_gas_interceptor_command(self.packer_pt, interceptor_gas_cmd, idx))
        if self.CP.carFingerprint not in CC_ONLY_CAR:
          friction_brake_bus = CanBus.CHASSIS
          # GM Camera exceptions
          # TODO: can we always check the longControlState?
          if self.CP.networkLocation == NetworkLocation.fwdCamera:
            at_full_stop = at_full_stop and stopping
            friction_brake_bus = CanBus.POWERTRAIN
            if self.CP.carFingerprint in SDGM_CAR:
              friction_brake_bus = CanBus.CAMERA

          if self.CP.autoResumeSng:
            resume = actuators.longControlState != LongCtrlState.starting or CC.cruiseControl.resume
            at_full_stop = at_full_stop and not resume

          if CC.cruiseControl.resume and CS.pcm_acc_status == AccState.STANDSTILL and starpilot_toggles.volt_sng:
            acc_engaged = False
          else:
            acc_engaged = CC.enabled

          # GasRegenCmdActive needs to be 1 to avoid cruise faults. It describes the ACC state, not actuation
          can_sends.append(gmcan.create_gas_regen_command(
            self.packer_pt, CanBus.POWERTRAIN, self.apply_gas, idx, acc_engaged, at_full_stop,
            include_always_one3=self.CP.carFingerprint in kaofui_cars, use_volt_layout=self.is_volt))
          can_sends.append(gmcan.create_friction_brake_command(self.packer_ch, friction_brake_bus, self.apply_brake,
                                                             idx, CC.enabled, near_stop, at_full_stop, self.CP))

        is_bolt_acc_pedal = self.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL
        if self.CP.carFingerprint not in CC_ONLY_CAR or is_bolt_acc_pedal:
          send_fcw = hud_alert == VisualAlert.fcw
          can_sends.append(gmcan.create_acc_dashboard_command(self.packer_pt, CanBus.POWERTRAIN, CC.enabled,
                                                              hud_v_cruise * CV.MS_TO_KPH, hud_control, send_fcw))

      # Radar needs to know current speed and yaw rate (50hz),
      # and that ADAS is alive (10hz)
      if not self.CP.radarUnavailable:
        send_adas = True
        if self.CP.carFingerprint in kaofui_cars:
          if self.CP.carFingerprint not in ASCM_INT:
            send_adas = (self.CP.networkLocation != NetworkLocation.fwdCamera) and (self.CP.carFingerprint not in SDGM_CAR)

        if send_adas:
          tt = self.frame * DT_CTRL
          if self.CP.carFingerprint in kaofui_cars:
            time_and_headlights_step = 10
            speed_and_accelerometer_step = 2
            if self.frame % time_and_headlights_step == 0:
              idx = (self.frame // time_and_headlights_step) % 4
              can_sends.append(gmcan.create_adas_time_status(CanBus.OBSTACLE, int((tt - self.start_time) * 60), idx))
              can_sends.append(gmcan.create_adas_headlights_status(self.packer_obj, CanBus.OBSTACLE))
            if self.frame % speed_and_accelerometer_step == 0:
              idx = (self.frame // speed_and_accelerometer_step) % 4
              can_sends.append(gmcan.create_adas_steering_status(CanBus.OBSTACLE, idx))
              can_sends.append(gmcan.create_adas_accelerometer_speed_status(CanBus.OBSTACLE, CS.out.vEgo, idx))
          else:
            time_and_headlights_step = 20
            if self.frame % time_and_headlights_step == 0:
              idx = (self.frame // time_and_headlights_step) % 4
              can_sends.append(gmcan.create_adas_time_status(CanBus.OBSTACLE, int((tt - self.start_time) * 60), idx))
              can_sends.append(gmcan.create_adas_headlights_status(self.packer_obj, CanBus.OBSTACLE))
              can_sends.append(gmcan.create_adas_steering_status(CanBus.OBSTACLE, idx))
              can_sends.append(gmcan.create_adas_accelerometer_speed_status(CanBus.OBSTACLE, CS.out.vEgo, idx))

      keepalive_step = self.params.ADAS_KEEPALIVE_STEP if self.CP.carFingerprint in kaofui_cars else self.params.ADAS_KEEPALIVE_STEP * 2
      if self.CP.networkLocation == NetworkLocation.gateway and self.frame % keepalive_step == 0:
        can_sends += gmcan.create_adas_keepalive(CanBus.POWERTRAIN)

      pedal_cancel = bool(self.CP.flags & GMFlags.PEDAL_LONG.value) and CS.out.cruiseState.enabled
      cc_long_cancel = ((self.CP.flags & GMFlags.CC_LONG.value) and
                        self.prev_op_enabled and not CC.enabled and CS.out.cruiseState.enabled)

      if self.CP.carFingerprint == CAR.CHEVROLET_MALIBU_HYBRID_CC:
        stock_cc_active = get_stock_cc_active_for_cancel(self.CP, CS)
        pedal_cancel = bool(self.CP.flags & GMFlags.PEDAL_LONG.value) and CC.longActive
        cc_long_cancel = bool(self.CP.flags & GMFlags.CC_LONG.value) and not CC.enabled

      if (pedal_cancel or cc_long_cancel) and (stock_cc_active if self.CP.carFingerprint == CAR.CHEVROLET_MALIBU_HYBRID_CC else True):
        if self.CP.carFingerprint == CAR.CHEVROLET_MALIBU_HYBRID_CC:
          malibu_cancel_requested = True
        elif (self.frame - self.last_button_frame) * DT_CTRL > 0.04:
          self.last_button_frame = self.frame
          cancel_bus = CanBus.CAMERA if self.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL else CanBus.POWERTRAIN
          can_sends.append(gmcan.create_buttons(self.packer_pt, cancel_bus, (CS.buttons_counter + 1) % 4, CruiseButtons.CANCEL))

    else:
      # While car is braking, cancel button causes ECM to enter a soft disable state with a fault status.
      # A delayed cancellation allows camera to cancel and avoids a fault when user depresses brake quickly
      self.cancel_counter = self.cancel_counter + 1 if CC.cruiseControl.cancel else 0

      # Stock longitudinal, integrated at camera
      if self.CP.carFingerprint == CAR.CHEVROLET_MALIBU_HYBRID_CC and self.cancel_counter > CAMERA_CANCEL_DELAY_FRAMES:
        malibu_cancel_requested = True
      elif (self.frame - self.last_button_frame) * DT_CTRL > 0.04:
        if self.cancel_counter > CAMERA_CANCEL_DELAY_FRAMES:
          self.last_button_frame = self.frame
          sdgm_stock_cancel_pt = (
            self.CP.carFingerprint in SDGM_CAR and
            self.CP.carFingerprint not in {
              CAR.CHEVROLET_VOLT,
              CAR.CHEVROLET_VOLT_2019,
              CAR.CHEVROLET_VOLT_ASCM,
              CAR.CHEVROLET_VOLT_CAMERA,
              CAR.CHEVROLET_VOLT_CC,
              CAR.CHEVROLET_BLAZER,
              CAR.CHEVROLET_MALIBU_SDGM,
              CAR.CHEVROLET_TRAVERSE,
            }
          )
          cancel_bus = CanBus.POWERTRAIN if sdgm_stock_cancel_pt else CanBus.CAMERA
          can_sends.append(gmcan.create_buttons(self.packer_pt, cancel_bus, CS.buttons_counter, CruiseButtons.CANCEL))

    if self.CP.carFingerprint == CAR.CHEVROLET_MALIBU_HYBRID_CC:
      if malibu_cancel_requested and malibu_oem_button_slot:
        can_sends.append(gmcan.create_buttons_malibu_cancel(
          CanBus.POWERTRAIN, (self.malibu_cancel_phase + 1) % 4, CS.steering_button_prefix))
        self.malibu_cancel_phase = (self.malibu_cancel_phase + 1) % 4

    if self.CP.networkLocation == NetworkLocation.fwdCamera:
      # Silence "Take Steering" alert sent by camera, forward PSCMStatus with HandsOffSWlDetectionStatus=1
      if self.frame % 10 == 0:
        can_sends.append(gmcan.create_pscm_status(self.packer_pt, CanBus.CAMERA, CS.pscm_status))

    new_actuators = actuators.as_builder()
    new_actuators.torque = self.apply_torque_last / self.params.STEER_MAX
    new_actuators.torqueOutputCan = self.apply_torque_last
    new_actuators.gas = self.apply_gas
    new_actuators.brake = self.apply_brake

    self.prev_op_enabled = CC.enabled
    self.frame += 1

    new_actuators.speed = self.apply_speed

    return new_actuators, can_sends
