import math
import numpy as np
from opendbc.can import CANPacker
from opendbc.car import ACCELERATION_DUE_TO_GRAVITY, Bus, DT_CTRL, structs
from opendbc.car.lateral import ISO_LATERAL_ACCEL, apply_std_steer_angle_limits
from opendbc.car.ford import fordcan
from opendbc.car.ford.values import CarControllerParams, FordFlags
from opendbc.car.interfaces import CarControllerBase, V_CRUISE_MAX
# This Ford extension boundary substantially adapts BluePilot bp-7.0 work. See the root CREDITS.md
# (including Alan Polk's d0aac605f and db2bdff05) and THIRD_PARTY_NOTICES.md.
from openpilot.starpilot.car.ford import fordcan as starpilot_fordcan
from openpilot.starpilot.car.ford.lateral import FordLateralController, FordLateralResult

LongCtrlState = structs.CarControl.Actuators.LongControlState
VisualAlert = structs.CarControl.HUDControl.VisualAlert

# CAN FD limits:
# Limit to average banked road since safety doesn't have the roll
AVERAGE_ROAD_ROLL = 0.06  # ~3.4 degrees, 6% superelevation. higher actual roll raises lateral acceleration
MAX_LATERAL_ACCEL = ISO_LATERAL_ACCEL - (ACCELERATION_DUE_TO_GRAVITY * AVERAGE_ROAD_ROLL)  # ~2.4 m/s^2


class FordStockCruiseButton:
  """Resolve Ford's context-sensitive cancel/resume switch for stock ACC."""

  def __init__(self):
    self.pressed = False
    self.cancel = False
    self.resume = False

  def update(self, pressed: bool, cruise_available: bool, cruise_enabled: bool) -> tuple[bool, bool]:
    if pressed and not self.pressed:
      self.cancel = cruise_available and cruise_enabled
      self.resume = cruise_available and not cruise_enabled
    elif not pressed:
      self.cancel = False
      self.resume = False

    self.pressed = pressed
    return self.cancel, self.resume


def apply_ford_angle(desired_angle_deg: float, current_angle_deg: float) -> float:
  relative_angle = desired_angle_deg - current_angle_deg
  return float(np.clip(relative_angle, -5.8, 5.8))


def apply_ford_curvature_limits(apply_curvature, apply_curvature_last, current_curvature, v_ego_raw, steering_angle, lat_active, CP):
  # No blending at low speed due to lack of torque wind-up and inaccurate current curvature
  if v_ego_raw > 9:
    apply_curvature = np.clip(apply_curvature, current_curvature - CarControllerParams.CURVATURE_ERROR,
                              current_curvature + CarControllerParams.CURVATURE_ERROR)

  # Curvature rate limit after driver torque limit
  apply_curvature = apply_std_steer_angle_limits(apply_curvature, apply_curvature_last, v_ego_raw, steering_angle, lat_active, CarControllerParams.ANGLE_LIMITS)

  # Ford Q4/CAN FD has more torque available compared to Q3/CAN so we limit it based on lateral acceleration.
  # Safety is not aware of the road roll so we subtract a conservative amount at all times
  if CP.flags & FordFlags.CANFD:
    # Limit curvature to conservative max lateral acceleration
    curvature_accel_limit = MAX_LATERAL_ACCEL / (max(v_ego_raw, 1) ** 2)
    apply_curvature = float(np.clip(apply_curvature, -curvature_accel_limit, curvature_accel_limit))

  return apply_curvature


def apply_creep_compensation(accel: float, v_ego: float) -> float:
  creep_accel = np.interp(v_ego, [1., 3.], [0.6, 0.])
  creep_accel = np.interp(accel, [0., 0.2], [creep_accel, 0.])
  accel -= creep_accel
  return float(accel)


class CarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.packer = CANPacker(dbc_names[Bus.pt])
    self.CAN = fordcan.CanBus(CP)

    self.apply_curvature_last = 0
    self.apply_angle_last = 0
    self.accel = 0.0
    self.gas = 0.0
    self.brake_request = False
    self.main_on_last = False
    self.lkas_enabled_last = False
    self.steer_alert_last = False
    self.lead_distance_bars_last = None
    self.distance_bar_frame = 0
    self.ford_lateral = None if CP.flags & FordFlags.LKA_STEERING else FordLateralController(CP)
    self.ford_extended_lateral_announced = False
    self.stock_cruise_button = FordStockCruiseButton()

  def update(self, CC, CS, now_nanos, starpilot_toggles):
    can_sends = []

    actuators = CC.actuators
    hud_control = CC.hudControl

    main_on = CS.out.cruiseState.available
    steer_alert = hud_control.visualAlert in (VisualAlert.steerRequired, VisualAlert.ldw)
    fcw_alert = hud_control.visualAlert == VisualAlert.fcw

    if self.ford_lateral is not None:
      self.ford_lateral.update_inputs()

    ### acc buttons ###
    stock_cancel = False
    stock_resume = False
    if not self.CP.openpilotLongitudinalControl:
      stock_cancel, stock_resume = self.stock_cruise_button.update(
        bool(CS.buttons_stock_values["CcAslButtnCnclResPress"]),
        CS.out.cruiseState.available,
        CS.out.cruiseState.enabled,
      )

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
    if self.CP.flags & FordFlags.LKA_STEERING:
      lka_active = CC.latActive and CS.lkas_available
      if lka_active:
        self.apply_angle_last = apply_ford_angle(actuators.steeringAngleDeg, CS.out.steeringAngleDeg)
        current_curvature = -CS.out.yawRate / max(CS.out.vEgoRaw, 0.1)
        self.apply_curvature_last = apply_ford_curvature_limits(actuators.curvature, self.apply_curvature_last, current_curvature,
                                                                CS.out.vEgoRaw, 0., True, self.CP)
      else:
        self.apply_angle_last = 0.
        self.apply_curvature_last = 0.

      # Keep the stock LMC heartbeat present while steering through Lane_Assist_Data1.
      if (self.frame % CarControllerParams.STEER_STEP) == 0:
        can_sends.append(fordcan.create_lat_ctl_msg(self.packer, self.CAN, False, 0., 0., 0., 0.,
                                                   stock_lmc=CS.lateral_motion_control))

      if (self.frame % CarControllerParams.LKA_STEP) == 0:
        direction = 0
        if lka_active:
          direction = 2 if CS.out.steeringAngleDeg > 0 else 4
        ramp_type = 1 if abs(self.apply_angle_last) >= 5 else 0
        can_sends.append(fordcan.create_lka_msg(self.packer, self.CAN, active=lka_active, apply_angle=self.apply_angle_last,
                                               direction=direction, ramp_type=ramp_type, curvature=-self.apply_curvature_last))
    else:
      if (self.frame % CarControllerParams.STEER_STEP) == 0:
        lateral = self.ford_lateral.update(CC, CS, actuators) \
          if self.ford_extended_lateral_announced else FordLateralResult()

        self.apply_curvature_last = lateral.curvature
        if self.CP.flags & FordFlags.CANFD:
          counter = (self.frame // CarControllerParams.STEER_STEP) % 0x10
          can_sends.append(starpilot_fordcan.create_lat_ctl2_msg(
            self.packer, self.CAN, 1 if lateral.active else 0,
            lateral.ramp_type, lateral.precision_type,
            -lateral.curvature, -lateral.curvature_rate, counter))
        else:
          can_sends.append(starpilot_fordcan.create_lat_ctl_msg(
            self.packer, self.CAN, lateral.active,
            lateral.ramp_type, lateral.precision_type,
            -lateral.curvature, -lateral.curvature_rate))

      if (self.frame % CarControllerParams.LKA_STEP) == 0:
        can_sends.append(starpilot_fordcan.create_lka_msg(self.packer, self.CAN))
        self.ford_extended_lateral_announced = True

    ### longitudinal control ###
    # send acc msg at 50Hz
    if self.CP.openpilotLongitudinalControl and (self.frame % CarControllerParams.ACC_CONTROL_STEP) == 0:
      accel = actuators.accel
      gas = accel

      if CC.longActive:
        # Compensate for engine creep at low speed.
        # Either the ABS does not account for engine creep, or the correction is very slow
        # TODO: verify this applies to EV/hybrid
        accel = apply_creep_compensation(accel, CS.out.vEgo)

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

      stopping = CC.actuators.longControlState == LongCtrlState.stopping
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
      hands_free_cluster = bool(
        self.ford_lateral is not None
        and self.ford_extended_lateral_announced
        and self.ford_lateral.hands_free_cluster_enabled)
      can_sends.append(fordcan.create_acc_ui_msg(self.packer, self.CAN, self.CP, main_on, CC.latActive,
                                                 fcw_alert, CS.out.cruiseState.standstill, show_distance_bars,
                                                 hud_control, CS.acc_tja_status_stock_values,
                                                 hands_free_cluster))

    self.main_on_last = main_on
    self.lkas_enabled_last = CC.latActive
    self.steer_alert_last = steer_alert
    self.lead_distance_bars_last = hud_control.leadDistanceBars

    new_actuators = actuators.as_builder()
    if self.CP.flags & FordFlags.LKA_STEERING:
      new_actuators.steeringAngleDeg = self.apply_angle_last + CS.out.steeringAngleDeg
    new_actuators.curvature = self.apply_curvature_last
    new_actuators.accel = self.accel
    new_actuators.gas = self.gas

    self.frame += 1
    return new_actuators, can_sends
