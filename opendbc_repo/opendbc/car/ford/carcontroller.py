import math
import numpy as np
from opendbc.can import CANPacker
from opendbc.car import ACCELERATION_DUE_TO_GRAVITY, Bus, DT_CTRL, apply_hysteresis, structs
from opendbc.car.ford import fordcan
from opendbc.car.ford.manual_turn import ManualTurnLatch
from opendbc.car.ford.stock_cruise import FordStockCruiseButton, qualified as stock_switch_qualified
from opendbc.car.ford.curvature_preview import blend_curvature
from opendbc.car.ford import mache_can
from opendbc.car.ford.extended_classic_can import create_extended_classic_lat_ctl_msg
from opendbc.car.ford.classic_lateral import create_controller as create_classic_controller, bounded_command as classic_bounded_command
from opendbc.car.ford.generic_canfd_can import create_extended_canfd_msg
from opendbc.car.ford.generic_canfd_lateral import GenericCanfdLateralController, qualified as generic_canfd_qualified, bounded_command as generic_canfd_bounded_command
from opendbc.car.ford.mache_lateral import MachELateralController, FordLateralResult, bounded_command, qualified as mache_qualified
from opendbc.car.ford.values import CarControllerParams, FordFlags, FordSafetyFlags, CAR
from opendbc.car.interfaces import CarControllerBase, V_CRUISE_MAX

LongCtrlState = structs.CarControl.Actuators.LongControlState
VisualAlert = structs.CarControl.HUDControl.VisualAlert

def anti_overshoot(apply_curvature, apply_curvature_last, v_ego):
  diff = 0.1
  tau = 5  # 5s smooths over the overshoot
  dt = DT_CTRL * CarControllerParams.STEER_STEP
  alpha = 1 - np.exp(-dt / tau)

  lataccel = apply_curvature * (v_ego ** 2)
  last_lataccel = apply_curvature_last * (v_ego ** 2)
  last_lataccel = apply_hysteresis(lataccel, last_lataccel, diff)
  last_lataccel = alpha * lataccel + (1 - alpha) * last_lataccel

  output_curvature = last_lataccel / (max(v_ego, 1) ** 2)

  return float(np.interp(v_ego, [5, 10], [apply_curvature, output_curvature]))


def apply_creep_compensation(accel: float, v_ego: float, car_fingerprint: str, *, standstill: bool, stopping: bool) -> float:
  if car_fingerprint == CAR.FORD_MUSTANG_MACH_E_MK1 and not (standstill and stopping):
    return accel
  creep_accel = np.interp(v_ego, [1., 3.], [0.6, 0.])
  creep_accel = np.interp(accel, [0., 0.2], [creep_accel, 0.])
  accel -= creep_accel
  return float(accel)


class CarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.packer = CANPacker(dbc_names[Bus.pt])
    self.CAN = fordcan.CanBus(CP)

    self.manual_turn = ManualTurnLatch() if CP.carFingerprint == CAR.FORD_MUSTANG_MACH_E_MK1 and not CP.flags & FordFlags.LKA_STEERING else None
    self.stock_cruise_button = FordStockCruiseButton()
    self.manual_turn_inputs = None
    self.mache_lateral = MachELateralController(CP) if mache_qualified(CP) else None
    self.mache_extended_announced = False
    self.generic_canfd = generic_canfd_qualified(CP)
    self.classic_lateral = GenericCanfdLateralController(CP) if self.generic_canfd else create_classic_controller(CP)
    self.classic_extended_announced = False
    self.classic_profile = any(s.safetyModel == structs.CarParams.SafetyModel.ford and
                                s.safetyParam & (FordSafetyFlags.CLASSIC_EXTENDED | FordSafetyFlags.GENERIC_CANFD_EXTENDED) for s in CP.safetyConfigs)
    self.mache_profile = any(s.safetyModel == structs.CarParams.SafetyModel.ford and
                             s.safetyParam & FordSafetyFlags.MACH_E_EXTENDED for s in CP.safetyConfigs)
    self.apply_curvature_last = 0
    self.anti_overshoot_curvature_last = 0
    self.accel = 0.0
    self.gas = 0.0
    self.brake_request = False
    self.main_on_last = False
    self.lkas_enabled_last = False
    self.steer_alert_last = False
    self.lead_distance_bars_last = None
    self.distance_bar_frame = 0
    self.apply_lka_angle_last = 0.
    self.apply_lka_curvature_last = 0.

  def update(self, CC, CS, now_nanos):
    can_sends = []
    if (self.mache_lateral is not None or self.classic_lateral is not None) and self.manual_turn_inputs is not None:
      self.manual_turn_inputs.update()
      self.manual_turn_inputs.apply_blend_settings(self)

    actuators = CC.actuators
    hud_control = CC.hudControl

    main_on = CS.out.cruiseState.available
    steer_alert = hud_control.visualAlert in (VisualAlert.steerRequired, VisualAlert.ldw)
    fcw_alert = hud_control.visualAlert == VisualAlert.fcw

    ### acc buttons ###
    stock_cancel = False
    stock_resume = False
    if stock_switch_qualified(self.CP):
      stock_cancel, stock_resume = self.stock_cruise_button.update(
        bool(CS.buttons_stock_values["CcAslButtnCnclResPress"]),
        CS.out.cruiseState.available, CS.out.cruiseState.enabled)

    if CC.cruiseControl.cancel:
      can_sends.append(fordcan.create_button_msg(self.packer, self.CAN.camera, CS.buttons_stock_values, cancel=True))
      can_sends.append(fordcan.create_button_msg(self.packer, self.CAN.main, CS.buttons_stock_values, cancel=True))
    elif (stock_cancel or stock_resume) and (self.frame % CarControllerParams.BUTTONS_STEP) == 0:
      can_sends.append(fordcan.create_button_msg(
        self.packer, self.CAN.camera, CS.buttons_stock_values, cancel=stock_cancel, resume=stock_resume))
      can_sends.append(fordcan.create_button_msg(
        self.packer, self.CAN.main, CS.buttons_stock_values, cancel=stock_cancel, resume=stock_resume))
    elif CC.cruiseControl.resume and (self.frame % CarControllerParams.BUTTONS_STEP) == 0:
      can_sends.append(fordcan.create_button_msg(self.packer, self.CAN.camera, CS.buttons_stock_values, resume=True))
      can_sends.append(fordcan.create_button_msg(self.packer, self.CAN.main, CS.buttons_stock_values, resume=True))
    # if stock lane centering isn't off, send a button press to toggle it off
    # the stock system checks for steering pressed, and eventually disengages cruise control
    elif CS.acc_tja_status_stock_values["Tja_D_Stat"] != 0 and (self.frame % CarControllerParams.ACC_UI_STEP) == 0:
      can_sends.append(fordcan.create_button_msg(self.packer, self.CAN.camera, CS.buttons_stock_values, tja_toggle=True))

    ### lateral control ###
    # send steer msg at 20Hz
    if (self.frame % CarControllerParams.STEER_STEP) == 0 and self.CP.flags & FordFlags.LKA_STEERING:
      # Preserve the stock LMC heartbeat without requesting lateral action.
      can_sends.append(fordcan.create_lat_ctl_msg(self.packer, self.CAN, False, 0., 0., 0., 0.,
                                                  stock_lmc=CS.lateral_motion_control))
    elif (self.frame % CarControllerParams.STEER_STEP) == 0 and self.mache_lateral is not None:
      inputs = self.manual_turn_inputs.lateral_snapshot(CS.out.vEgoRaw) if self.manual_turn_inputs is not None else None
      if inputs is not None:
        self.mache_lateral.set_inputs(*inputs)
      else:
        # Withdraw stale preview while retaining current actuator/manual-turn control.
        self.mache_lateral.set_inputs(None, (), 0.2, self.manual_turn_inputs.enabled if self.manual_turn_inputs is not None else True)
      previous = self.mache_lateral.curvature_last
      previous_path_angle = self.mache_lateral.path_angle_last
      demanded = self.mache_lateral.update(CC, CS, actuators) if self.mache_extended_announced else FordLateralResult()
      lateral = bounded_command(self.mache_lateral, demanded, previous, CS.out.vEgoRaw, previous_path_angle)
      self.mache_lateral_demand = demanded
      self.apply_curvature_last = lateral.curvature
      counter = (self.frame // CarControllerParams.STEER_STEP) % 0x10
      can_sends.append(mache_can.create_lat_ctl2_msg(
        self.packer, self.CAN, int(lateral.active), lateral.ramp_type, lateral.precision_type,
        -lateral.curvature, -lateral.curvature_rate, counter, -lateral.path_angle))
    elif (self.frame % CarControllerParams.STEER_STEP) == 0 and self.classic_lateral is not None:
      inputs = self.manual_turn_inputs.lateral_snapshot(CS.out.vEgoRaw) if self.manual_turn_inputs is not None else None
      if inputs is not None:
        self.classic_lateral.set_inputs(*inputs)
      else:
        self.classic_lateral.set_inputs(None, (), 0.2, self.manual_turn_inputs.enabled if self.manual_turn_inputs is not None else True)
      previous = self.classic_lateral.curvature_last
      demanded = self.classic_lateral.update(CC, CS, actuators) if self.classic_extended_announced else FordLateralResult()
      bound = generic_canfd_bounded_command if self.generic_canfd else classic_bounded_command
      lateral = bound(self.classic_lateral, demanded, previous, CS.out.vEgoRaw,
                                         -CS.out.yawRate / max(CS.out.vEgoRaw, 0.1))
      self.classic_lateral_demand = demanded
      self.apply_curvature_last = lateral.curvature
      if self.generic_canfd:
        counter = (self.frame // CarControllerParams.STEER_STEP) % 0x10
        can_sends.append(create_extended_canfd_msg(
          self.packer, self.CAN, lateral.active, lateral.ramp_type, lateral.precision_type,
          -lateral.curvature, -lateral.curvature_rate, counter))
      else:
        can_sends.append(create_extended_classic_lat_ctl_msg(
          self.packer, self.CAN, lateral.active, lateral.ramp_type, lateral.precision_type,
          -lateral.curvature, -lateral.curvature_rate))
    elif (self.frame % CarControllerParams.STEER_STEP) == 0:
      lateral_active = CC.latActive and not self.mache_profile and not self.classic_profile
      manual_turn = False
      if self.manual_turn is not None and self.manual_turn_inputs is not None:
        detection_enabled, lane_change, model_ready = self.manual_turn_inputs.update()
        manual_turn = self.manual_turn.update(CC, CS, float(actuators.curvature), detection_enabled, lane_change, model_ready)
        if manual_turn:
          lateral_active = False
          self.apply_curvature_last = 0.
      # Bronco and some other cars consistently overshoot curv requests
      # Apply some deadzone + smoothing convergence to avoid oscillations
      if self.CP.carFingerprint in (CAR.FORD_BRONCO_SPORT_MK1, CAR.FORD_F_150_MK14):
        self.anti_overshoot_curvature_last = anti_overshoot(actuators.curvature, self.anti_overshoot_curvature_last, CS.out.vEgoRaw)
        apply_curvature = self.anti_overshoot_curvature_last
      else:
        apply_curvature = actuators.curvature

      # apply rate limits, curvature error limit, and clip to signal range
      current_curvature = -CS.out.yawRate / max(CS.out.vEgoRaw, 0.1)
      if self.manual_turn is not None and self.manual_turn_inputs is not None and lateral_active:
        prediction = getattr(self.manual_turn_inputs, "preview_curvature", None)
        preview = prediction(CS.out.vEgoRaw) if prediction is not None else None
        if preview is not None:
          apply_curvature = blend_curvature(apply_curvature, preview, current_curvature)
      # No blending at low speed due to lack of torque wind-up and inaccurate current curvature
      if CS.out.vEgoRaw > 9:
        apply_curvature = float(np.clip(apply_curvature, current_curvature - CarControllerParams.CURVATURE_ERROR,
                                        current_curvature + CarControllerParams.CURVATURE_ERROR))
      apply_curvature = CarControllerParams.CURVATURE_LIMITS.apply_limits(apply_curvature, self.apply_curvature_last, CS.out.vEgoRaw,
                                                                          0., lateral_active, CarControllerParams.STEER_STEP)
      self.apply_curvature_last = 0. if manual_turn else apply_curvature

      if self.CP.flags & FordFlags.CANFD:
        # TODO: extended mode
        # Ford uses four individual signals to dictate how to drive to the car. Curvature alone (limited to 0.02 m^-1)
        # can actuate the steering for a large portion of any lateral movements. However, in order to get further control on
        # steer actuation, the other three signals are necessary. Ford controls vehicles differently than most other makes.
        # A detailed explanation on ford control can be found here:
        # https://www.f150gen14.com/forum/threads/introducing-bluepilot-a-ford-specific-fork-for-comma3x-openpilot.24241/#post-457706
        mode = 1 if lateral_active else 0
        counter = (self.frame // CarControllerParams.STEER_STEP) % 0x10
        can_sends.append(fordcan.create_lat_ctl2_msg(self.packer, self.CAN, mode, 0., 0., -self.apply_curvature_last, 0., counter))
      else:
        can_sends.append(fordcan.create_lat_ctl_msg(self.packer, self.CAN, lateral_active, 0., 0., -self.apply_curvature_last, 0.))

    # send lka msg at 33Hz
    if (self.frame % CarControllerParams.LKA_STEP) == 0:
      if self.CP.flags & FordFlags.LKA_STEERING:
        source_age_ns = now_nanos - CS.lkas_available_ts_nanos
        lka_active = (CC.latActive and CS.lkas_available and 0 <= source_age_ns <= 100_000_000 and
                      CS.out.cruiseState.enabled and
                      not CS.out.steerFaultTemporary and
                      not CS.out.vehicleSensorsInvalid)
        if lka_active:
          desired_angle = float(np.clip(actuators.steeringAngleDeg - CS.out.steeringAngleDeg, -5.8, 5.8))
          self.apply_lka_angle_last = float(np.clip(desired_angle, self.apply_lka_angle_last - 1.,
                                                    self.apply_lka_angle_last + 1.))
          desired_curvature = -actuators.curvature
          current_curvature = CS.out.yawRate / max(CS.out.vEgoRaw, 0.1)
          if CS.out.vEgoRaw > 9.:
            desired_curvature = float(np.clip(desired_curvature, current_curvature - CarControllerParams.CURVATURE_ERROR,
                                              current_curvature + CarControllerParams.CURVATURE_ERROR))
          self.apply_lka_curvature_last = CarControllerParams.LKA_CURVATURE_LIMITS.apply_limits(
            desired_curvature, self.apply_lka_curvature_last, CS.out.vEgoRaw, 0., True, CarControllerParams.LKA_STEP)
        else:
          self.apply_lka_angle_last = 0.
          self.apply_lka_curvature_last = 0.
        self.apply_curvature_last = -self.apply_lka_curvature_last
        direction = 2 if self.apply_lka_angle_last >= 0. else 4
        can_sends.append(fordcan.create_lka_msg(self.packer, self.CAN, lka_active, self.apply_lka_angle_last,
                                                direction, self.apply_lka_curvature_last, transit=True))
      elif self.mache_lateral is not None:
        can_sends.append(mache_can.create_lka_msg(self.packer, self.CAN))
        self.mache_extended_announced = True
      elif self.classic_lateral is not None:
        can_sends.append(mache_can.create_lka_msg(self.packer, self.CAN))
        self.classic_extended_announced = True
      else:
        can_sends.append(fordcan.create_lka_msg(self.packer, self.CAN))

    ### longitudinal control ###
    # send acc msg at 50Hz
    if self.CP.openpilotLongitudinalControl and (self.frame % CarControllerParams.ACC_CONTROL_STEP) == 0:
      accel = actuators.accel
      gas = accel
      stopping = actuators.longControlState == LongCtrlState.stopping

      if CC.longActive:
        accel = apply_creep_compensation(accel, CS.out.vEgo, self.CP.carFingerprint,
                                         standstill=CS.out.standstill, stopping=stopping)

        # The stock system has been seen rate limiting the brake accel to 5 m/s^3,
        # however even 3.5 m/s^3 causes some overshoot with a step response.
        accel = max(accel, self.accel - (3.5 * CarControllerParams.ACC_CONTROL_STEP * DT_CTRL))

      accel = float(np.clip(accel, CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX))
      gas = float(np.clip(gas, CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX))

      # Both gas and accel are in m/s^2, accel is used solely for braking
      if not CC.longActive or gas < CarControllerParams.MIN_GAS:
        gas = CarControllerParams.INACTIVE_GAS

      # PCM applies pitch compensation to gas/accel, but we need to compensate for the brake/pre-charge bits
      accel_due_to_pitch = 0.0
      if len(CC.orientationNED) == 3:
        accel_due_to_pitch = math.sin(CC.orientationNED[1]) * ACCELERATION_DUE_TO_GRAVITY

      accel_pitch_compensated = accel + accel_due_to_pitch
      if accel_pitch_compensated > 0.3 or not CC.longActive:
        self.brake_request = False
      elif accel_pitch_compensated < 0.0:
        self.brake_request = True

      # TODO: look into using the actuators packet to send the desired speed
      can_sends.append(fordcan.create_acc_msg(self.packer, self.CAN, CC.longActive, gas, accel, stopping, self.brake_request, v_ego_kph=V_CRUISE_MAX))

      self.accel = accel
      self.gas = gas

    ### ui ###
    send_ui = (self.main_on_last != main_on) or (self.lkas_enabled_last != CC.latActive) or (self.steer_alert_last != steer_alert)
    # send lkas ui msg at 1Hz or if ui state changes
    if (self.frame % CarControllerParams.LKAS_UI_STEP) == 0 or send_ui:
      can_sends.append(fordcan.create_lkas_ui_msg(self.packer, self.CAN, main_on, CC.latActive, steer_alert, hud_control, CS.lkas_status_stock_values))

    # send acc ui msg at 5Hz or if ui state changes
    if hud_control.leadDistanceBars != self.lead_distance_bars_last:
      send_ui = True
      self.distance_bar_frame = self.frame

    if (self.frame % CarControllerParams.ACC_UI_STEP) == 0 or send_ui:
      show_distance_bars = self.frame - self.distance_bar_frame < 400
      can_sends.append(fordcan.create_acc_ui_msg(self.packer, self.CAN, self.CP, main_on, CC.latActive,
                                                 fcw_alert, CS.out.cruiseState.standstill, show_distance_bars,
                                                 hud_control, CS.acc_tja_status_stock_values))

    self.main_on_last = main_on
    self.lkas_enabled_last = CC.latActive
    self.steer_alert_last = steer_alert
    self.lead_distance_bars_last = hud_control.leadDistanceBars

    new_actuators = actuators.as_builder()
    new_actuators.curvature = self.apply_curvature_last
    if self.CP.flags & FordFlags.LKA_STEERING:
      new_actuators.steeringAngleDeg = CS.out.steeringAngleDeg + self.apply_lka_angle_last
    new_actuators.accel = self.accel
    new_actuators.gas = self.gas

    self.frame += 1
    return new_actuators, can_sends
