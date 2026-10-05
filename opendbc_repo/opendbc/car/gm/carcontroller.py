from opendbc.car.gm.longitudinal import volt_sng_release
from opendbc.car.gm.auto_hold import AutoHold
from opendbc.car.gm.values import is_volt_auto_hold
from opendbc.car.gm.ordinary import demands as ascm_demands
import math
import numpy as np
from opendbc.can import CANPacker
from opendbc.car import ACCELERATION_DUE_TO_GRAVITY, Bus, DT_CTRL, structs
from opendbc.car.lateral import apply_driver_steer_torque_limits
from opendbc.car.gm import gmcan
from opendbc.car.gm.startup_preferences import gateway_sources_current
from opendbc.car.gm.silverado_cc import SilveradoPedalCommand
from opendbc.car.gm.conventional_pedal_command import ConventionalPedalCommand
from opendbc.car.gm.aol import lateral_request as aol_lateral_request
from opendbc.car.gm.conventional_pedal import (sources_current as conventional_pedal_sources_current,
                                               cancel_sources_current as conventional_pedal_cancel_sources_current)
from opendbc.car.gm.ordinary_cc import PhysicalObservation, ButtonCadence, button_request as ordinary_button_request
from opendbc.car.gm.cc_longitudinal import VoltCcPhysical, button_request, volt_cc_forward_gear
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gm.values import (DBC, CanBus, CarControllerParams, CruiseButtons, GMFlags, GMSafetyFlags,
                                   is_volt_gateway_alternate_brake, is_volt_gateway_longitudinal, is_volt_gateway_profile, is_volt_ascm_longitudinal,
                                   is_conventional_cc_pedal_profile, is_silverado_cc_pedal_profile, is_ordinary_ascm_profile,
                                   is_ordinary_camera_profile, is_ordinary_camera_removed,
                                   is_ordinary_sdgm_profile,
                                   is_volt_camera_longitudinal, is_volt_camera_stock, is_volt_sdgm_profile, is_volt_camera_removed,
                                   is_bolt_euv_longitudinal, is_volt_cc_longitudinal, is_volt_cc_profile, is_ordinary_cc_profile,
                                   CC_GATEWAY_STOCK_CAR, uses_camera_stock_controls, CAR, BOLT_CC_WORDS, is_bolt_cc_profile)
from opendbc.car.interfaces import CarControllerBase

from opendbc.car.gm.bolt_cc import BoltCcOwner, BoltCcProfile, auxiliary_messages

VisualAlert = structs.CarControl.HUDControl.VisualAlert
NetworkLocation = structs.CarParams.NetworkLocation
LongCtrlState = structs.CarControl.Actuators.LongControlState

# Camera cancels up to 0.1s after brake is pressed, ECM allows 0.5s
CAMERA_CANCEL_DELAY_FRAMES = 10
# Enforce a minimum interval between steering messages to avoid a fault
MIN_STEER_MSG_INTERVAL_MS = 15
PEDAL_SENSOR_TIMEOUT_NS = 100_000_000
STOCK_ACC_STATUS_TIMEOUT_NS = 300_000_000  # Three 10 Hz status periods.
CC_GATEWAY_CRUISE_TIMEOUT_NS = 300_000_000
CC_GATEWAY_BUTTON_TIMEOUT_NS = 100_000_000
CAMERA_STOCK_STATUS_TIMEOUT_NS = 300_000_000
BOLT_ACC_PEDAL_FRICTION_RELEASE_FRAMES = 5
VOLT_GRADE_CAR = {CAR.CHEVROLET_VOLT, CAR.CHEVROLET_VOLT_ASCM, CAR.CHEVROLET_VOLT_2019, CAR.CHEVROLET_VOLT_CAMERA}
VOLT_GATEWAY_GRADE_STOP_SPEED = 0.75
VOLT_CAMERA_GRADE_STOP_SPEED = 0.25
VOLT_EV_THRESHOLD_BP = [1.29, 1.52, 1.55, 1.6, 1.7, 1.8, 2.0, 2.2, 2.5, 5.52, 9.6, 20.5, 23.5, 35.0]
VOLT_EV_THRESHOLD_V = [0.0, -0.14, -0.16, -0.18, -0.215, -0.255, -0.32, -0.41,
                       -0.5, -0.72, -0.895, -1.125, -1.145, -1.16]


def bolt_euv_demands(accel: float, speed: float, orientation_ned, mass: float,
                     wheelbase: float, max_brake: int) -> tuple[int, int]:
  """Original ordinary camera Bolt torque/grade law in current DBC engineering units."""
  pitch_accel = 0.0
  if speed > 0.25 and orientation_ned is not None and len(orientation_ned) == 3:
    pitch = orientation_ned[1]
    if math.isfinite(pitch):
      pitch_accel = math.sin(pitch) * ACCELERATION_DUE_TO_GRAVITY
      if pitch_accel > 0.0 and accel > 0.0:
        pitch_accel = 0.0
      else:
        pitch_accel = min(pitch_accel, 0.20)
  tire_radius = 0.075 * wheelbase + 0.1453
  drag = 0.5 * 0.30 * (1.05 * wheelbase + 0.0679) * 1.225 * speed ** 2
  scaled_torque = tire_radius * (mass * float(np.clip(accel + pitch_accel, -4.0, 2.0)) + drag) + 6150
  gas = int(round(np.clip(scaled_torque, 5610, 8848))) - 6150
  brake_switch = int(round(np.interp(speed, [0.5, 10.0], [6150, 5610])))
  brake_accel = min((scaled_torque - brake_switch) / (tire_radius * mass), 0.0)
  brake = int(round(np.interp(brake_accel, [-4.0, 0.0], [max_brake, 0])))
  return (-500 if brake > 0 else gas), brake


def volt_demands(accel: float, speed: float, orientation_ned, stopping_speed: float,
                         mass: float, wheelbase: float, accel_min: float, accel_max: float,
                         max_brake: int, *, min_gas: int = -650, max_gas: int = 2041, inactive_gas: int = -650) -> tuple[int, int]:
  """Original Volt demand law in current normalized gas units."""
  pitch_accel = 0.0
  if speed > stopping_speed and orientation_ned is not None and len(orientation_ned) == 3:
    pitch = orientation_ned[1]
    if math.isfinite(pitch):
      pitch_accel = math.sin(pitch) * ACCELERATION_DUE_TO_GRAVITY
      if pitch_accel > 0.0 and accel > 0.0:
        pitch_accel = 0.0
      else:
        pitch_accel = min(pitch_accel, 0.20)

  aero_accel = 0.5 * 0.30 * (1.05 * wheelbase + 0.0679) * 1.225 * speed ** 2 / mass
  gas_accel = float(np.clip(accel + aero_accel + pitch_accel, accel_min, accel_max))
  brake_accel = float(np.clip(accel + aero_accel + pitch_accel * np.interp(speed, [5.0, 10.0], [0.0, 1.0]),
                              accel_min, accel_max))
  threshold = float(np.interp(speed, VOLT_EV_THRESHOLD_BP, VOLT_EV_THRESHOLD_V))
  old_raw_gas = int(round(np.interp(gas_accel, [threshold, max(0.0, threshold), accel_max], [min_gas + 6150, 6150, max_gas + 6150])))
  brake = int(round(np.interp(brake_accel, [accel_min, threshold], [max_brake, 0])))
  gas = int(np.clip(old_raw_gas, min_gas + 6150, max_gas + 6150)) - 6150
  brake = int(np.clip(brake, 0, max_brake))
  return (inactive_gas if brake > 0 else gas), brake


def volt_grade_demands(accel: float, speed: float, orientation_ned, stopping_speed: float,
                       accel_min: float, accel_max: float) -> tuple[float, float]:
  pitch_accel = 0.0
  if speed > stopping_speed and orientation_ned is not None and len(orientation_ned) == 3:
    pitch = orientation_ned[1]
    if math.isfinite(pitch):
      pitch_accel = math.sin(pitch) * ACCELERATION_DUE_TO_GRAVITY
      if pitch_accel > 0.0 and accel > 0.0:
        pitch_accel = 0.0
      else:
        pitch_accel = min(pitch_accel, 0.20)
  gas_demand = float(np.clip(accel + pitch_accel, accel_min, accel_max))
  brake_scale = float(np.interp(speed, [5.0, 10.0], [0.0, 1.0]))
  brake_demand = float(np.clip(accel + pitch_accel * brake_scale, accel_min, accel_max))
  return gas_demand, brake_demand


def fixed_stopping_brake(long_active: bool, near_stop: bool, stopping: bool, resume: bool,
                         stop_accel: float, max_brake: int) -> int | None:
  if not (long_active and near_stop and stopping and not resume):
    return None
  return int(min(-100.0 * stop_accel, max_brake))


def bolt_pedal_fraction(accel: float, speed: float, paddle_pressed: bool) -> float:
  """Frozen speed-shaped pedal calibration; physical response still needs vehicle evidence."""
  gain = np.interp(speed,
                   [0.559, 1.678, 2.797, 3.916, 5.035, 6.154, 7.273, 8.392, 9.511, 10.63,
                    11.749, 12.868, 13.987, 15.106, 16.225, 17.344, 18.463, 19.582, 20.701, 21.820,
                    22.939, 24.058, 25.177, 26.296],
                   [1.01, 1.01, 1.02, 1.05, 1.08, 1.31, 1.33, 1.34, 1.35, 1.36,
                    1.37, 1.38, 1.39, 1.39, 1.40, 1.40, 1.41, 1.42, 1.43, 1.43,
                    1.44, 1.44, 1.45, 1.45])
  gain *= np.interp(speed, [0.0, 2.0, 4.0, 5.5, 8.0, 12.0], [0.92, 0.92, 0.93, 0.94, 0.96, 1.0])
  accel_gain = np.interp(speed, [0.0, 3.0, 8.0, 20.0], [0.47, 0.52, 0.57, 0.61])
  offset = np.interp(speed, [0.0, 1.0, 3.0, 6.0, 15.0, 30.0], [0.085, 0.11, 0.17, 0.23, 0.235, 0.23])
  accel = 0.0 if abs(accel) < 0.04 else accel
  scale = np.interp(abs(accel), [0.0, 0.35, 0.8, 1.5, 2.5],
                    [0.58, 0.68, 0.82, 0.93, 1.0] if accel >= 0 else [0.44, 0.54, 0.70, 0.89, 1.0])
  command = float(np.clip(offset + accel * scale * accel_gain / max(gain, 1e-3) if paddle_pressed else
                          offset + accel * scale * accel_gain, 0.0, 1.0))
  ceiling = np.interp(speed, [0.0, 1.0, 2.5, 4.5, 6.0, 8.0, 12.0], [0.20, 0.235, 0.29, 0.365, 0.52, 0.78, 1.0])
  return float(min(command, ceiling))


def bolt_pedal_slew(target: float, steady: float, accel: float, speed: float) -> float:
  urgency = float(np.clip(abs(accel) / 2.0, 0.0, 1.0))
  rise = np.interp(speed, [0.0, 3.0, 8.0, 20.0], [0.007, 0.012, 0.022, 0.036]) + 0.011 * urgency
  if accel > 0.0 and speed > 6.0:
    rise *= np.interp(abs(accel), [0.0, 0.12, 0.25, 0.45, 0.8], [0.55, 0.58, 0.68, 0.82, 1.0])
  if accel > 1.2:
    rise += np.interp(speed, [0.0, 4.0, 12.0, 25.0], [0.006, 0.005, 0.003, 0.002])
  fall = np.interp(speed, [0.0, 3.0, 8.0, 20.0], [0.008, 0.014, 0.026, 0.045]) + 0.015 * urgency
  return float(np.clip(target, steady - fall, steady + rise))


def bolt_acc_pedal_friction_brake(accel: float, speed: float, stopping: bool, low_speed_active: bool,
                                  mass: float, wheelbase: float, max_brake: int) -> tuple[int, bool]:
  tire_radius = 0.075 * wheelbase + 0.1453
  frontal_area = 1.05 * wheelbase + 0.0679
  aero_drag_force = 0.5 * 0.30 * frontal_area * 1.225 * speed ** 2
  accel_cmd = float(np.clip(accel, -4.0, 2.0))
  scaled_torque = tire_radius * (mass * accel_cmd + aero_drag_force) + 6150
  stock_switch = int(round(np.interp(speed, [0.5, 10.0], [6150, 5500])))
  planner_limit = float(np.interp(speed, [0.0, 1.5, 4.0, 8.0, 15.0, 30.0],
                                  [-0.93, -1.28, -1.98, -2.58, -2.86, -2.95]))
  planner_switch = int(round(tire_radius * (mass * planner_limit + aero_drag_force) + 6150))
  brake_switch = max(stock_switch, planner_switch)
  brake_accel = min((scaled_torque - brake_switch) / (tire_radius * mass), 0.0)
  brake = int(round(np.interp(brake_accel, [-4.0, 0.0], [max_brake, 0.0])))
  if brake > 0:
    full_brake_accel = min(-4.0 + aero_drag_force / mass + (6150 - brake_switch) / (tire_radius * mass), -0.1)
    corrected_scale = 4.0 / max(-full_brake_accel, 0.1)
    speed_gain = float(np.interp(speed, [0.0, 8.0, 15.0, 25.0], [1.0, 1.08, 1.2, 1.35]))
    onset_gain = float(np.interp(brake, [0.0, 5.0, 20.0, 60.0, 120.0, 240.0, max_brake],
                                 [0.0, 1.8, 1.65, 1.4, 1.22, 1.08, 1.0]))
    brake = int(round(np.clip(max(brake * corrected_scale * speed_gain * onset_gain,
                                  np.interp(speed, [0.0, 6.0, 8.0, 12.0, 18.0, 25.0],
                                            [0.0, 0.0, 4.0, 10.0, 20.0, 28.0])), 0, max_brake)))

  if brake <= 0:
    return 0, False
  engage_threshold = float(np.interp(speed, [0.0, 1.5, 3.0, 5.0, 8.0], [40.0, 20.0, 12.0, 10.0, 0.0]))
  release_threshold = float(np.interp(speed, [0.0, 1.5, 3.0, 5.0, 8.0], [0.0, 8.0, 6.0, 4.0, 0.0]))
  if not low_speed_active and brake < engage_threshold:
    return 0, False
  if low_speed_active and brake < release_threshold:
    return 0, False
  if stopping:
    stop_fade = float(np.interp(speed, [0.0, 0.6, 0.9, 1.2, 1.8, 2.8], [0.0, 0.0, 0.05, 0.12, 0.32, 0.78]))
    brake = int(round(brake * stop_fade))
    if brake <= 0 or brake < release_threshold:
      return 0, False
  return brake, True


def suburban_gateway_demands(accel, speed, orientation, cp):
  """Normal Suburban gateway demand, converted to current gas units."""
  pitch = 0.0
  if orientation is not None and len(orientation) == 3 and speed > 0.5 and math.isfinite(orientation[1]):
    pitch = math.sin(orientation[1]) * ACCELERATION_DUE_TO_GRAVITY
    pitch = 0.0 if pitch > 0.0 and accel > 0.0 else min(pitch, 0.20)
  radius = 0.075 * cp.wheelbase + 0.1453
  frontal = 1.05 * cp.wheelbase + 0.0679
  demand = float(np.clip(accel + pitch, -4.0, 2.0))
  torque = radius * (cp.mass * demand + 0.5 * 0.30 * frontal * 1.225 * speed ** 2)
  gas = int(round(np.clip(torque + 6150, 5500, 7168))) - 6150
  brake = int(round(np.interp(min(torque / (radius * cp.mass), 0), [-4.0, 0.0], [400, 0])))
  return (-650 if brake > 0 else gas), brake


class CarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.long_pitch = True
    self.start_time = 0.
    self.apply_torque_last = 0
    self.apply_gas = 0
    self.apply_brake = 0
    self.last_steer_frame = 0
    self.last_button_frame = 0
    self.cancel_counter = 0
    self.pedal_steady = 0.0
    self.pedal_active_last = False
    self.volt_sng = False
    self.volt_sng_plan_input = None
    self.gm_auto_hold = False
    self.gm_auto_hold_input = None
    self.gm_auto_hold_state = AutoHold()
    self.regen_paddle_pressed = False
    self.bolt_regen_hold = False
    self.regen_press_count = 0
    self.regen_release_count = 0
    self.regen_min_on_frames = 0
    self.regen_min_off_frames = 0
    self.paddle_handoff_frames = 0
    self.bolt_acc_pedal_friction_release_frames = 0
    self.bolt_acc_pedal_friction_low_speed_active = False

    self.lka_steering_cmd_counter = 0
    self.lka_icon_status_last = (False, False)

    self.params = CarControllerParams(self.CP)
    self.volt_gateway_profile = is_volt_gateway_profile(self.CP)
    self.volt_gateway_long = is_volt_gateway_longitudinal(self.CP)
    self.volt_ascm_long = is_volt_ascm_longitudinal(self.CP)
    self.ordinary_ascm_long = is_ordinary_ascm_profile(self.CP, longitudinal=True)
    self.conventional_pedal_profile = is_conventional_cc_pedal_profile(self.CP)
    self.conventional_cancel_credit_used = 0
    self.silverado_cc_pedal_profile = is_silverado_cc_pedal_profile(self.CP)
    self.silverado_pedal_command = SilveradoPedalCommand(self.CP) if self.silverado_cc_pedal_profile else None
    self.conventional_pedal_command = (ConventionalPedalCommand(self.CP)
                                       if self.conventional_pedal_profile and not self.silverado_cc_pedal_profile else None)
    self.ordinary_camera_long = is_ordinary_camera_profile(self.CP, longitudinal=True)
    self.ordinary_camera_stock = is_ordinary_camera_profile(self.CP)
    self.ordinary_camera_removed = is_ordinary_camera_removed(self.CP)
    self.ordinary_sdgm_long = is_ordinary_sdgm_profile(self.CP, longitudinal=True)
    self.volt_sdgm_long = is_volt_sdgm_profile(self.CP, longitudinal=True)
    self.volt_camera_removed = is_volt_camera_removed(self.CP)
    self.volt_camera_removed_long = is_volt_camera_removed(self.CP, longitudinal=True)
    self.volt_removed_cancel_credit_used = 0
    self.volt_camera_long = is_volt_camera_longitudinal(self.CP) or self.volt_camera_removed_long
    self.bolt_euv_long = is_bolt_euv_longitudinal(self.CP)
    self.volt_cc_profile = is_volt_cc_profile(self.CP)
    self.ordinary_cc_profile = is_ordinary_cc_profile(self.CP)
    self.ordinary_cc_cadence = ButtonCadence(self.CP.carFingerprint == CAR.CADILLAC_XT4_CC)
    self.volt_cc_long = is_volt_cc_longitudinal(self.CP)
    self.bolt_cc_profile = is_bolt_cc_profile(self.CP)
    self.bolt_cc_owner = (BoltCcOwner(BoltCcProfile(self.CP.carFingerprint,
                          camera_removed=self.CP.safetyConfigs[0].safetyParam == BOLT_CC_WORDS[self.CP.carFingerprint][1]))
                          if self.bolt_cc_profile else None)
    self.bolt_cc_last_cruise_source = self.bolt_cc_last_button_source = 0
    self.bolt_cc_metric = False
    self.bolt_cc_last_camera_source = 0
    self.volt_cc_prev_enabled = False
    self.volt_cc_cancel_pending = False
    self.volt_cc_last_cancel_frame = 0
    self.volt_cc_metric = False
    self.volt_cc_last_button_frame = 0
    self.volt_cc_consumed_source_ns = 0

    self.packer_pt = CANPacker(DBC[self.CP.carFingerprint][Bus.pt])
    self.packer_obj = CANPacker(DBC[self.CP.carFingerprint][Bus.radar])
    self.packer_ch = CANPacker(DBC[self.CP.carFingerprint][Bus.chassis])

  def bolt_pedal_admission(self, CC, CS, now_nanos):
    age_ns = now_nanos - CS.pedal_sensor_ts_nanos
    sensor_ready = (CS.pedal_sensor_healthy and CS.pedal_sensor_ts_nanos > 0 and
                    0 <= age_ns <= PEDAL_SENSOR_TIMEOUT_NS)
    stock_acc = self.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL
    stock_age = now_nanos - CS.stock_acc_status_ts_nanos if stock_acc else 0
    owner_clear = (not stock_acc or
                   (CS.stock_acc_status_ts_nanos > 0 and 0 <= stock_age <= STOCK_ACC_STATUS_TIMEOUT_NS and
                    not CS.out.cruiseState.enabled))
    in_regen_gear = CS.out.gearShifter == structs.CarState.GearShifter.low
    active = (CC.longActive and sensor_ready and in_regen_gear and not CS.out.brakePressed and
              not CS.out.gasPressed and not CS.out.regenBraking and owner_clear and
              (not stock_acc or CS.out.cruiseState.available))
    return active, owner_clear, in_regen_gear

  def update_bolt_paddle(self, commanded_accel, measured_accel, speed, active):
    if not active:
      self.bolt_regen_hold = False
      self.regen_paddle_pressed = False
      self.regen_press_count = 0
      self.regen_release_count = 0
      self.regen_min_on_frames = 0
      self.regen_min_off_frames = 0
      return False

    speed_bp = [0., 4., 12., 25.]
    press_cmd = np.interp(speed, speed_bp, [-0.90, -0.82, -0.72, -0.65])
    release_cmd = np.interp(speed, speed_bp, [-0.10, -0.17, -0.24, -0.30])
    press_measured = np.interp(speed, speed_bp, [-0.95, -0.86, -0.76, -0.70])
    release_measured = np.interp(speed, speed_bp, [-0.16, -0.23, -0.30, -0.36])
    press_frames = int(round(np.interp(speed, speed_bp, [8., 6., 5., 4.])))
    release_frames = int(round(np.interp(speed, speed_bp, [18., 15., 12., 10.])))
    min_on = int(round(np.interp(speed, speed_bp, [34., 27., 20., 16.])))
    min_off = int(round(np.interp(speed, speed_bp, [16., 14., 12., 10.])))
    boost = int(round(np.interp(speed, [0., 6., 8., 20., 25.], [0., 0., 3., 3., 0.])))
    press_frames += boost
    release_frames += boost

    if self.bolt_regen_hold or commanded_accel <= press_cmd or measured_accel <= press_measured:
      self.regen_press_count += 1
    else:
      self.regen_press_count = max(self.regen_press_count - 1, 0)
    if not self.bolt_regen_hold and commanded_accel >= release_cmd and measured_accel >= release_measured:
      self.regen_release_count += 1
    else:
      self.regen_release_count = max(self.regen_release_count - 1, 0)
    if self.bolt_regen_hold and commanded_accel <= press_cmd - 0.30:
      self.regen_press_count = max(self.regen_press_count, press_frames)
    self.regen_min_on_frames = max(self.regen_min_on_frames - 1, 0)
    self.regen_min_off_frames = max(self.regen_min_off_frames - 1, 0)
    if self.regen_paddle_pressed:
      if self.regen_min_on_frames == 0 and self.regen_release_count >= release_frames:
        self.regen_paddle_pressed = False
        self.regen_min_off_frames = min_off
        self.regen_release_count = 0
    elif self.regen_min_off_frames == 0 and self.regen_press_count >= press_frames:
      self.regen_paddle_pressed = True
      self.regen_min_on_frames = min_on
      self.regen_press_count = 0
    return self.regen_paddle_pressed

  def update(self, CC, CS, now_nanos):
    # Sample physical hold dwell at parser/controller cadence, before current brake demands.
    hold_brake = None
    if is_volt_auto_hold(self.CP):
      hold_enabled = self.gm_auto_hold and self.gm_auto_hold_input is not None and self.gm_auto_hold_input.update(now_nanos)
      hold_brake = self.gm_auto_hold_state.update(
        CS.out, enabled=hold_enabled, sources_current=all(0 < stamp <= now_nanos and now_nanos - stamp <= limit
                                                         for stamp, limit in CS.gm_auto_hold_sources) and bool(CS.gm_auto_hold_sources) and
        not CS.gm_auto_hold_unavailable, long_active=CC.longActive, driver_brake=CS.gm_auto_hold_brake,
        controller_brake=self.apply_brake, wheel_ns=CS.gm_auto_hold_wheel_ns, now_ns=now_nanos,
        physical_forward=CS.gm_auto_hold_forward, moving=CS.gm_auto_hold_moving)
      if hold_brake is None:
        CS.gm_auto_hold_engaged = False
    actuators = CC.actuators
    hud_control = CC.hudControl
    hud_alert = hud_control.visualAlert
    hud_v_cruise = hud_control.setSpeed
    if hud_v_cruise > 70:
      hud_v_cruise = 0

    # Send CAN commands.
    can_sends = []
    cc_gateway = self.CP.carFingerprint in CC_GATEWAY_STOCK_CAR or self.volt_cc_profile
    stock_cruise_fresh = (not cc_gateway or
                          (CS.cc_gateway_cruise_ts_nanos > 0 and
                           0 <= now_nanos - CS.cc_gateway_cruise_ts_nanos <= CC_GATEWAY_CRUISE_TIMEOUT_NS))
    stock_steer_ready = (not cc_gateway or
                         (stock_cruise_fresh and CS.out.cruiseState.available and CS.out.cruiseState.enabled and
                          not CS.out.brakePressed and not CS.out.gasPressed))
    aol_lateral = aol_lateral_request(self.CP, CC)
    if self.volt_cc_profile or self.ordinary_cc_profile:
      physical = getattr(CS, 'volt_cc_physical', None)
      stock_steer_ready = (isinstance(physical, (VoltCcPhysical, PhysicalObservation)) and physical.sources_current(now_nanos) and
                           CS.out.canValid and not CS.out.canTimeout and CS.out.cruiseState.available and
                           (CS.out.cruiseState.enabled or aol_lateral) and volt_cc_forward_gear(CS.out.gearShifter))
    if self.ordinary_cc_profile:
      stock_steer_ready = (isinstance(physical, PhysicalObservation) and physical.sources_current(now_nanos) and
                          CS.out.canValid and not CS.out.canTimeout and CS.out.cruiseState.available and
                          volt_cc_forward_gear(CS.out.gearShifter))
    if self.volt_gateway_profile and not self.CP.openpilotLongitudinalControl:
      stock_steer_ready = (gateway_sources_current(getattr(CS, "volt_gateway_source_ns", ()), now_nanos) and
                          CS.out.canValid and not CS.out.canTimeout and CS.out.cruiseState.available and
                          (aol_lateral or not CS.out.brakePressed and not CS.out.regenBraking) and
                          CS.cruise_buttons != CruiseButtons.CANCEL)
    if uses_camera_stock_controls(self.CP):
      status_age = now_nanos - CS.camera_stock_status_ts_nanos
      stock_steer_ready = (CS.camera_stock_sources_valid and CS.camera_stock_status_ts_nanos > 0 and
                           0 <= status_age <= CAMERA_STOCK_STATUS_TIMEOUT_NS and
                           CS.out.cruiseState.available and (CS.out.cruiseState.enabled or aol_lateral) and
                           (aol_lateral or not CS.out.brakePressed and not CS.out.regenBraking) and
                           (aol_lateral or not CS.out.gasPressed or is_volt_camera_stock(self.CP) or is_volt_sdgm_profile(self.CP)
                               or is_ordinary_sdgm_profile(self.CP, longitudinal=False) or self.ordinary_camera_stock) and not CS.out.accFaulted)
    if self.volt_camera_long and not self.volt_camera_removed or self.volt_sdgm_long or self.ordinary_sdgm_long or self.ordinary_camera_long:
      status_age = now_nanos - CS.camera_stock_status_ts_nanos
      stock_steer_ready = (CS.camera_stock_sources_valid and CS.camera_stock_status_ts_nanos > 0 and
                           0 <= status_age <= CAMERA_STOCK_STATUS_TIMEOUT_NS and
                           CS.out.cruiseState.available)
    bolt_sources = getattr(CS, "bolt_cc_sources", ())
    bolt_sources_fresh = (len(bolt_sources) == 7 and all(stamp > 0 and 0 <= now_nanos - stamp <= 300_000_000
                                                     for stamp, raw in bolt_sources))
    if self.bolt_cc_profile:
      stock_steer_ready = (bolt_sources_fresh and CS.out.canValid and not CS.out.canTimeout and
                          CS.out.cruiseState.available and (aol_lateral or bool(bolt_sources[1][1][4] & 128)) and
                          CS.out.gearShifter in (structs.CarState.GearShifter.drive, structs.CarState.GearShifter.low) and
                          (aol_lateral or not CS.out.brakePressed and not CS.out.regenBraking))
    if self.ordinary_camera_removed:
      stock_steer_ready = (CS.out.canValid and not CS.out.canTimeout and len(CS.ordinary_removed_sources) == 6 and
                           all(stamp > 0 and 0 <= now_nanos - stamp <= 300_000_000 for stamp in CS.ordinary_removed_sources))
    if self.volt_camera_removed:
      stock_steer_ready = (CS.out.canValid and not CS.out.canTimeout and len(CS.volt_removed_sources) == 6 and
                           all(stamp > 0 and 0 <= now_nanos - stamp <= 300_000_000 for stamp in CS.volt_removed_sources))
    if self.conventional_pedal_profile:
      stock_steer_ready = conventional_pedal_sources_current(CS, now_nanos) and CS.out.cruiseState.available
    lat_active = CC.latActive and stock_steer_ready

    # Steering (Active: 50Hz, inactive: 10Hz)
    steer_step = self.params.STEER_STEP if lat_active else self.params.INACTIVE_STEER_STEP

    if (self.CP.networkLocation == NetworkLocation.fwdCamera and
        not (self.conventional_pedal_profile and not self.silverado_cc_pedal_profile and self.CP.flags & GMFlags.NO_CAMERA)):
      # Also send at 50Hz:
      # - on startup, first few msgs are blocked
      # - until we're in sync with camera so counters align when relay closes, preventing a fault.
      #   openpilot can subtly drift, so this is activated throughout a drive to stay synced
      out_of_sync = (not self.volt_camera_removed and
                     self.lka_steering_cmd_counter % 4 != (CS.cam_lka_steering_cmd_counter + 1) % 4)
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

      if lat_active and not (self.ordinary_cc_profile and CC.enabled and not CS.out.cruiseState.enabled and not aol_lateral):
        new_torque = int(round(actuators.torque * self.params.STEER_MAX))
        apply_torque = apply_driver_steer_torque_limits(new_torque, self.apply_torque_last, CS.out.steeringTorque, self.params)
      else:
        apply_torque = 0

      self.last_steer_frame = self.frame
      self.apply_torque_last = apply_torque
      idx = self.lka_steering_cmd_counter % 4
      can_sends.append(gmcan.create_steering_control(self.packer_pt, CanBus.POWERTRAIN, apply_torque, idx, lat_active))

    if self.silverado_cc_pedal_profile:
      sources_ready = conventional_pedal_sources_current(CS, now_nanos) and CS.pedal_sensor_healthy
      ready = (sources_ready and CS.out.cruiseState.available and CS.out.gearShifter in
               (structs.CarState.GearShifter.drive, structs.CarState.GearShifter.low) and
               not CS.out.brakePressed and not CS.out.gasPressed)
      if self.CP.openpilotLongitudinalControl and self.frame % 4 == 0:
        if ready:
          pedal, self.apply_gas, self.apply_brake = self.silverado_pedal_command.update(
            actuators.accel, CC.longActive, CS.out, stopping=actuators.longControlState == LongCtrlState.stopping,
            resume=CC.cruiseControl.resume, orientation=CC.orientationNED if self.long_pitch else None)
        else:
          if not sources_ready:
            self.silverado_pedal_command.prime_recovery()
          else:
            self.silverado_pedal_command.pause_recovery()
          pedal, self.apply_gas, self.apply_brake = 0., -650., 0
        self.pedal_steady = self.silverado_pedal_command.steady
        self.pedal_active_last = self.silverado_pedal_command.active_last
        can_sends.append(gmcan.create_pedal_command(self.packer_pt, pedal, (self.frame // 4) % 4))

    elif self.conventional_pedal_profile:
      sources_ready = conventional_pedal_sources_current(CS, now_nanos) and CS.pedal_sensor_healthy
      ready = (sources_ready and CS.out.cruiseState.available and CS.out.gearShifter in
               (structs.CarState.GearShifter.drive, structs.CarState.GearShifter.low) and
               not CS.out.brakePressed and not CS.out.gasPressed)
      if self.CP.openpilotLongitudinalControl and self.frame % 4 == 0:
        if ready:
          pedal, self.apply_gas, self.apply_brake = self.conventional_pedal_command.update(
            actuators.accel, CC.longActive and CC.enabled, CS.out, stopping=actuators.longControlState == LongCtrlState.stopping,
            resume=CC.cruiseControl.resume, orientation=CC.orientationNED if self.long_pitch else None)
        else:
          if not sources_ready:
            self.conventional_pedal_command.prime_recovery()
          else:
            self.conventional_pedal_command.pause_recovery()
          pedal, self.apply_gas, self.apply_brake = 0., -650., 0
        self.pedal_steady = self.conventional_pedal_command.steady
        self.pedal_active_last = self.conventional_pedal_command.active_last
        can_sends.append(gmcan.create_pedal_command(self.packer_pt, pedal, (self.frame // 4) % 4))
    elif self.CP.flags & GMFlags.PEDAL_LONG.value and self.CP.openpilotLongitudinalControl:
      active, stock_ownership_clear, in_regen_gear = self.bolt_pedal_admission(CC, CS, now_nanos)
      if not active:
        self.bolt_regen_hold = False
      else:
        press = np.interp(CS.out.vEgo, [0., 4., 12., 25.], [-0.95, -0.82, -0.70, -0.62])
        release = np.interp(CS.out.vEgo, [0., 4., 12., 25.], [-0.14, -0.22, -0.30, -0.36])
        if actuators.accel <= press:
          self.bolt_regen_hold = True
        elif actuators.accel >= release:
          self.bolt_regen_hold = False
      if self.frame % 4 == 0:
        stock_acc_variant = self.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL
        friction_variant = stock_acc_variant and bool(self.CP.flags & GMFlags.PEDAL_LONG.value)
        friction_main_on = friction_variant and CS.out.cruiseState.available and stock_ownership_clear
        if friction_variant:
          if active and friction_main_on:
            self.apply_brake, self.bolt_acc_pedal_friction_low_speed_active = bolt_acc_pedal_friction_brake(
              actuators.accel, CS.out.vEgo, actuators.longControlState == LongCtrlState.stopping,
              self.bolt_acc_pedal_friction_low_speed_active, self.CP.mass, self.CP.wheelbase, self.params.MAX_BRAKE)
          else:
            self.apply_brake = 0
            self.bolt_acc_pedal_friction_low_speed_active = False
        prior_paddle_pressed = self.regen_paddle_pressed
        paddle_pressed = self.update_bolt_paddle(actuators.accel, CS.out.aEgo, CS.out.vEgo, active)
        paddle_switched = paddle_pressed != prior_paddle_pressed
        if active:
          target = bolt_pedal_fraction(actuators.accel, CS.out.vEgo, paddle_pressed)
          if self.pedal_active_last and not (paddle_switched and CS.out.vEgo > 1.0):
            self.pedal_steady = bolt_pedal_slew(target, self.pedal_steady, actuators.accel, CS.out.vEgo)
          else:
            self.pedal_steady = target
          self.pedal_active_last = True
        else:
          self.pedal_steady = 0.0
          self.pedal_active_last = False
        can_sends.append(gmcan.create_pedal_command(self.packer_pt, self.pedal_steady, (self.frame // 4) % 16))
        if CC.enabled:
          self.paddle_handoff_frames = 2
        feed_release = bool(self.paddle_handoff_frames)
        if not CC.enabled and self.paddle_handoff_frames:
          self.paddle_handoff_frames -= 1
        if (CC.enabled or feed_release) and in_regen_gear and not CS.out.regenBraking:
          spoof_pressed = paddle_pressed and CS.out.vEgo > 2.68
          gen2 = self.CP.carFingerprint in (CAR.CHEVROLET_BOLT_CC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)
          can_sends.append(gmcan.create_bolt_regen_gear(self.packer_pt, spoof_pressed, gen2))
          can_sends.append(gmcan.create_bolt_regen_paddle(self.packer_pt, spoof_pressed))
        self.apply_gas = self.pedal_steady
        if friction_variant:
          if not stock_ownership_clear:
            self.bolt_acc_pedal_friction_release_frames = 0
          elif self.apply_brake > 0:
            self.bolt_acc_pedal_friction_release_frames = BOLT_ACC_PEDAL_FRICTION_RELEASE_FRAMES
          elif self.bolt_acc_pedal_friction_release_frames > 0:
            self.bolt_acc_pedal_friction_release_frames -= 1
          if friction_main_on or self.bolt_acc_pedal_friction_release_frames > 0:
            can_sends.append(gmcan.create_friction_brake_command(
              self.packer_ch, CanBus.POWERTRAIN, self.apply_brake, (self.frame // 4) % 4,
              active and friction_main_on, active and CS.out.vEgo < self.params.NEAR_STOP_BRAKE_PHASE,
              active and CS.out.standstill and actuators.longControlState == LongCtrlState.stopping, self.CP))
        else:
          self.apply_brake = 0
      # Stock ACC on the equipped variant is canceled while pedal control owns longitudinal.
      if (self.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL and CS.out.cruiseState.enabled and
          (self.frame - self.last_button_frame) * DT_CTRL > 0.04):
        self.last_button_frame = self.frame
        can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.CAMERA, (CS.buttons_counter + 1) % 4, CruiseButtons.CANCEL))

    elif (self.CP.openpilotLongitudinalControl and not self.volt_cc_long and not self.ordinary_cc_profile and
          not self.bolt_cc_profile and not self.silverado_cc_pedal_profile):
      # Gas/regen, brakes, and UI commands - all at 25Hz
      if self.frame % 4 == 0:
        stopping = actuators.longControlState == LongCtrlState.stopping
        near_stop = CC.longActive and abs(CS.out.vEgo) < self.params.NEAR_STOP_BRAKE_PHASE
        if not CC.longActive:
          # ASCM sends max regen when not enabled
          self.apply_gas = self.params.INACTIVE_REGEN
          self.apply_brake = 0
        else:
          stop_brake = fixed_stopping_brake(CC.longActive, near_stop, stopping, CC.cruiseControl.resume,
                                           self.CP.stopAccel, self.params.MAX_BRAKE)
          if stop_brake is not None:
            self.apply_gas = self.params.INACTIVE_REGEN
            self.apply_brake = stop_brake
          else:
            if self.CP.carFingerprint == CAR.CHEVROLET_SUBURBAN:
              self.apply_gas, self.apply_brake = suburban_gateway_demands(actuators.accel, CS.out.vEgo, CC.orientationNED if self.long_pitch else None, self.CP)
            elif self.ordinary_camera_long:
              self.apply_gas, self.apply_brake = ascm_demands(
                actuators.accel, CS.out.vEgo, CC.orientationNED if self.long_pitch else None, self.CP,
                min_gas=-540, max_gas=2698, inactive_gas=-500, brake_threshold=0.0)
            elif self.ordinary_sdgm_long:
              self.apply_gas, self.apply_brake = ascm_demands(
                actuators.accel, CS.out.vEgo, CC.orientationNED, self.CP,
                min_gas=-540, max_gas=2698, inactive_gas=-500, brake_threshold=0.0,
                stop_speed=0.35 if self.CP.carFingerprint == CAR.CHEVROLET_BLAZER else 0.25)
            elif self.ordinary_ascm_long:
              self.apply_gas, self.apply_brake = ascm_demands(
                actuators.accel, CS.out.vEgo, CC.orientationNED if self.long_pitch else None, self.CP)
            elif self.bolt_euv_long:
              self.apply_gas, self.apply_brake = bolt_euv_demands(
                actuators.accel, CS.out.vEgo, CC.orientationNED if self.long_pitch else None, self.CP.mass, self.CP.wheelbase, self.params.MAX_BRAKE)
            elif self.volt_gateway_long or self.volt_ascm_long or self.volt_camera_long or self.volt_sdgm_long:
              self.apply_gas, self.apply_brake = volt_demands(
                actuators.accel, CS.out.vEgo, CC.orientationNED if self.long_pitch else None,
                VOLT_CAMERA_GRADE_STOP_SPEED if self.volt_ascm_long or self.volt_camera_long or self.volt_sdgm_long else VOLT_GATEWAY_GRADE_STOP_SPEED,
                self.CP.mass, self.CP.wheelbase, self.params.ACCEL_MIN, self.params.ACCEL_MAX, self.params.MAX_BRAKE,
                min_gas=-540 if self.volt_camera_long or self.volt_sdgm_long else -650,
                max_gas=2698 if self.volt_camera_long or self.volt_sdgm_long else 2041,
                inactive_gas=-500 if self.volt_camera_long or self.volt_sdgm_long else -650)
            else:
              gas_demand = brake_demand = actuators.accel
              if self.CP.carFingerprint in VOLT_GRADE_CAR:
                gas_demand, brake_demand = volt_grade_demands(
                  actuators.accel, CS.out.vEgo, CC.orientationNED if self.long_pitch else None,
                  VOLT_GATEWAY_GRADE_STOP_SPEED if self.CP.networkLocation == NetworkLocation.gateway else VOLT_CAMERA_GRADE_STOP_SPEED,
                  self.params.ACCEL_MIN, self.params.ACCEL_MAX)
              self.apply_gas = float(np.interp(gas_demand, self.params.GAS_LOOKUP_BP, self.params.GAS_LOOKUP_V))
              self.apply_brake = int(round(np.interp(brake_demand, self.params.BRAKE_LOOKUP_BP, self.params.BRAKE_LOOKUP_V)))
            if stopping:
              self.apply_gas = self.params.INACTIVE_REGEN

        idx = (self.frame // 4) % 4

        at_full_stop = CC.longActive and CS.out.standstill
        friction_brake_bus = CanBus.POWERTRAIN if is_volt_gateway_alternate_brake(self.CP) else CanBus.CHASSIS
        # GM Camera exceptions
        # TODO: can we always check the longControlState?
        if self.CP.networkLocation == NetworkLocation.fwdCamera and not (self.conventional_pedal_profile and self.CP.flags & GMFlags.NO_CAMERA):
          at_full_stop = at_full_stop and stopping
          friction_brake_bus = CanBus.CAMERA if self.volt_sdgm_long or self.ordinary_sdgm_long else CanBus.POWERTRAIN

        if (self.volt_camera_long and not self.volt_camera_removed or
            self.ordinary_camera_long and not self.ordinary_camera_removed):
          can_sends.append(gmcan.create_acc_2cd_command(CanBus.POWERTRAIN, idx))

        # Resume releases only the gas/regen ACC-state bit; friction remains separately owned.
        acc_engaged = CC.enabled and not volt_sng_release(
          self.CP, self.volt_sng, CC, CS, now_nanos,
          plan_current=self.volt_sng_plan_input.update(now_nanos) if self.volt_sng and self.volt_sng_plan_input is not None else False)
        if hold_brake is None:
          can_sends.append(gmcan.create_gas_regen_command(self.packer_pt, CanBus.POWERTRAIN, self.apply_gas, idx, acc_engaged, at_full_stop))
        else:
          self.apply_brake = hold_brake
          at_full_stop = CS.out.cruiseState.standstill
          near_stop = CS.out.vEgo < self.params.NEAR_STOP_BRAKE_PHASE
        can_sends.append(gmcan.create_friction_brake_command(self.packer_ch, friction_brake_bus, self.apply_brake,
                                                             idx, CC.enabled, near_stop, at_full_stop, self.CP, auto_hold=hold_brake is not None))
        CS.gm_auto_hold_engaged = hold_brake is not None

        if self.bolt_euv_long:
          can_sends.append(gmcan.create_acc_2cd_command(CanBus.POWERTRAIN, idx))

        # Send dashboard UI commands (ACC status)
        send_fcw = hud_alert == VisualAlert.fcw
        camera_fcw = None
        if self.ordinary_ascm_long or self.ordinary_sdgm_long or self.volt_camera_long or self.volt_sdgm_long or self.ordinary_camera_long:
          camera_fcw = 3 if send_fcw else CS.stock_fcw_alert
          if camera_fcw == 0 and (CS.out.stockAeb or CS.out.stockFcw):
            camera_fcw = 3
        dashboard_state = 2 if (self.ordinary_camera_long or self.ordinary_ascm_long or self.ordinary_sdgm_long or self.volt_camera_long or
                                self.volt_sdgm_long or self.CP.carFingerprint == CAR.CHEVROLET_SUBURBAN) else None
        can_sends.append(gmcan.create_acc_dashboard_command(self.packer_pt, CanBus.POWERTRAIN, CC.enabled,
                                                           hud_v_cruise * CV.MS_TO_KPH, hud_control, send_fcw,
                                                           cruise_state=dashboard_state,
                                                           fcw_alert=camera_fcw,
                                                           acc_always_one=0 if (self.ordinary_camera_long or self.ordinary_sdgm_long
                                                               and self.CP.carFingerprint == CAR.CHEVROLET_BLAZER) else 1))

      # Radar needs to know current speed and yaw rate (50hz),
      # and that ADAS is alive (10hz)
      if (not self.CP.radarUnavailable and not self.volt_ascm_long and not self.volt_camera_long and not self.volt_sdgm_long
          and not self.ordinary_ascm_long and not self.ordinary_sdgm_long):
        tt = self.frame * DT_CTRL
        time_and_headlights_step = 10
        if self.frame % time_and_headlights_step == 0:
          idx = (self.frame // time_and_headlights_step) % 4
          can_sends.append(gmcan.create_adas_time_status(CanBus.OBSTACLE, int((tt - self.start_time) * 60), idx))
          can_sends.append(gmcan.create_adas_headlights_status(self.packer_obj, CanBus.OBSTACLE))

        speed_and_accelerometer_step = 2
        if self.frame % speed_and_accelerometer_step == 0:
          idx = (self.frame // speed_and_accelerometer_step) % 4
          can_sends.append(gmcan.create_adas_steering_status(CanBus.OBSTACLE, idx))
          can_sends.append(gmcan.create_adas_accelerometer_speed_status(CanBus.OBSTACLE, abs(CS.out.vEgo), idx))

      if (self.CP.networkLocation == NetworkLocation.gateway or self.volt_camera_removed_long or
          self.ordinary_camera_long and self.ordinary_camera_removed) and \
          self.frame % self.params.ADAS_KEEPALIVE_STEP == 0:
        can_sends += gmcan.create_adas_keepalive(CanBus.POWERTRAIN)

    elif self.volt_camera_removed:
      self.cancel_counter = self.cancel_counter + 1 if CC.cruiseControl.cancel else 0
      credit = CS.volt_removed_credit_ns
      if (self.cancel_counter > CAMERA_CANCEL_DELAY_FRAMES and (self.frame - self.last_button_frame) * DT_CTRL > 0.04 and
          stock_steer_ready and CS.out.cruiseState.available and CS.out.cruiseState.enabled and
          credit > self.volt_removed_cancel_credit_used and 0 <= now_nanos - credit <= 100_000_000):
        self.last_button_frame = self.frame
        self.volt_removed_cancel_credit_used = credit
        can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.POWERTRAIN, CS.buttons_counter, CruiseButtons.CANCEL))
    elif (not self.volt_cc_profile and not self.ordinary_cc_profile and not self.bolt_cc_profile and
          not self.volt_gateway_profile and not self.silverado_cc_pedal_profile):
      # While car is braking, cancel button causes ECM to enter a soft disable state with a fault status.
      # A delayed cancellation allows camera to cancel and avoids a fault when user depresses brake quickly
      self.cancel_counter = self.cancel_counter + 1 if CC.cruiseControl.cancel else 0

      # Stock longitudinal, integrated at camera
      if (self.frame - self.last_button_frame) * DT_CTRL > 0.04:
        button_fresh = (not cc_gateway or
                        (CS.cc_gateway_buttons_ts_nanos > 0 and
                         0 <= now_nanos - CS.cc_gateway_buttons_ts_nanos <= CC_GATEWAY_BUTTON_TIMEOUT_NS))
        if self.cancel_counter > CAMERA_CANCEL_DELAY_FRAMES and (not cc_gateway or
            (button_fresh and stock_cruise_fresh and CS.out.cruiseState.available and CS.out.cruiseState.enabled)):
          self.last_button_frame = self.frame
          cancel_bus = (CanBus.POWERTRAIN if cc_gateway or self.CP.safetyConfigs[0].safetyParam & GMSafetyFlags.SDGM_CANCEL_PT.value
                        else CanBus.CAMERA)
          can_sends.append(gmcan.create_buttons(self.packer_pt, cancel_bus, CS.buttons_counter, CruiseButtons.CANCEL))

    if self.silverado_cc_pedal_profile:
      self.cancel_counter = self.cancel_counter + 1 if CC.cruiseControl.cancel else 0
      if (not self.CP.openpilotLongitudinalControl and self.cancel_counter > CAMERA_CANCEL_DELAY_FRAMES and
          (self.frame - self.last_button_frame) * DT_CTRL > .04 and
          conventional_pedal_sources_current(CS, now_nanos) and CS.out.cruiseState.available):
        self.last_button_frame = self.frame
        can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.CAMERA, CS.buttons_counter, CruiseButtons.CANCEL))

    elif self.conventional_pedal_profile and not self.CP.openpilotLongitudinalControl:
      self.cancel_counter = self.cancel_counter + 1 if CC.cruiseControl.cancel else 0
      if (self.cancel_counter > CAMERA_CANCEL_DELAY_FRAMES and
          (self.frame - self.last_button_frame) * DT_CTRL > .04 and
          conventional_pedal_cancel_sources_current(CS, now_nanos) and
          CS.out.cruiseState.available and CS.out.cruiseState.enabled and
          CS.conventional_cancel_credit.available(now_nanos, self.conventional_cancel_credit_used)):
        self.last_button_frame = self.frame
        self.conventional_cancel_credit_used = CS.conventional_cancel_credit.credit_ns
        can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.CAMERA, CS.conventional_cancel_credit.counter, CruiseButtons.CANCEL))

    if (self.conventional_pedal_profile and self.CP.flags & GMFlags.NO_CAMERA and
        self.CP.openpilotLongitudinalControl and self.frame % 100 == 0):
      can_sends += gmcan.create_adas_keepalive(CanBus.POWERTRAIN)

    if (self.conventional_pedal_profile and self.CP.openpilotLongitudinalControl and
        conventional_pedal_sources_current(CS, now_nanos) and CS.out.cruiseState.available and
        CS.out.cruiseState.enabled and (self.frame - self.last_button_frame) * DT_CTRL > .04):
      self.last_button_frame = self.frame
      can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.POWERTRAIN,
                                           (CS.buttons_counter + 1) % 4, CruiseButtons.CANCEL))

    if self.CP.networkLocation == NetworkLocation.fwdCamera and not self.bolt_cc_profile:
      # Silence "Take Steering" alert sent by camera, forward PSCMStatus with HandsOffSWlDetectionStatus=1
      if self.frame % 10 == 0:
        can_sends.append(gmcan.create_pscm_status(self.packer_pt, CanBus.CAMERA, CS.pscm_status))

    if self.bolt_cc_profile:
      owner = self.bolt_cc_owner
      owner.frame = self.frame - 1
      if len(bolt_sources) == 7:
        cruise_stamp, cruise_raw = bolt_sources[1]
        button_stamp, button_raw = bolt_sources[2]
        if cruise_stamp > self.bolt_cc_last_cruise_source:
          owner.cruise(cruise_raw, cruise_stamp)
          self.bolt_cc_last_cruise_source = cruise_stamp
        if button_stamp > self.bolt_cc_last_button_source:
          owner.button(button_raw, button_stamp)
          self.bolt_cc_last_button_source = button_stamp
        if owner.profile.camera_required:
          camera_stamp, camera_raw = getattr(CS, "bolt_cc_camera_source", (0, b""))
          if camera_stamp > self.bolt_cc_last_camera_source:
            owner.camera(camera_raw, camera_stamp)
            self.bolt_cc_last_camera_source = camera_stamp
        if self.CP.openpilotLongitudinalControl:
          request = owner.update(now_nanos, CS.out.vEgo, CS.out.cruiseState.speed, actuators.accel,
                                 enabled=CC.enabled, long_active=CC.longActive,
                                 drive=CS.out.gearShifter in (structs.CarState.GearShifter.drive, structs.CarState.GearShifter.low),
                                 brake=CS.out.brakePressed or CS.out.regenBraking, gas=CS.out.gasPressed,
                                 sources_current=bolt_sources_fresh and CS.out.canValid and not CS.out.canTimeout,
                                 metric=self.bolt_cc_metric, hud_speed=hud_v_cruise)
          if request:
            can_sends.append(request)
        else:
          owner.frame = self.frame
        pscm_stamp, pscm_raw = bolt_sources[0]
        can_sends.extend(auxiliary_messages(owner, pscm_raw, pscm_stamp, now_nanos))

    new_actuators = actuators.as_builder()
    new_actuators.torque = self.apply_torque_last / self.params.STEER_MAX
    new_actuators.torqueOutputCan = self.apply_torque_last
    new_actuators.gas = self.apply_gas
    new_actuators.brake = self.apply_brake

    if self.volt_cc_profile or self.ordinary_cc_profile:
      physical = getattr(CS, 'volt_cc_physical', None)
      if self.volt_cc_prev_enabled and not CC.enabled and CS.out.cruiseState.enabled:
        self.volt_cc_cancel_pending = True
      if CC.enabled or not CS.out.cruiseState.enabled or not CS.out.cruiseState.available:
        self.volt_cc_cancel_pending = False
      self.volt_cc_prev_enabled = bool(CC.enabled)
      cancel_ready = (isinstance(physical, (VoltCcPhysical, PhysicalObservation)) and physical.sources_current(now_nanos) and physical.neutral_button and
                      CS.out.canValid and not CS.out.canTimeout and CS.out.cruiseState.available and CS.out.cruiseState.enabled)
      stock_cancel_requested = False
      if self.ordinary_cc_profile and not self.CP.openpilotLongitudinalControl:
        self.cancel_counter = self.cancel_counter + 1 if CC.cruiseControl.cancel else 0
        stock_cancel_requested = self.cancel_counter > CAMERA_CANCEL_DELAY_FRAMES
      cancel_sent = False
      if ((self.volt_cc_cancel_pending or stock_cancel_requested) and
          (not self.ordinary_cc_profile or self.CP.openpilotLongitudinalControl or stock_cancel_requested) and
          cancel_ready and (self.frame - self.volt_cc_last_cancel_frame) * DT_CTRL > .04 and
          physical.button_credit_ns > 0 and physical.button_credit_ns != self.volt_cc_consumed_source_ns):
        can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.POWERTRAIN, (CS.buttons_counter + 1) % 4, CruiseButtons.CANCEL))
        self.volt_cc_last_cancel_frame = self.frame
        self.volt_cc_consumed_source_ns = physical.button_credit_ns
        self.volt_cc_cancel_pending = False
        cancel_sent = True

      ready = (isinstance(physical, (VoltCcPhysical, PhysicalObservation)) and physical.current(now_nanos) and
               CS.out.canValid and not CS.out.canTimeout and CS.out.cruiseState.available and CS.out.cruiseState.enabled and
               volt_cc_forward_gear(CS.out.gearShifter) and CS.out.vEgo >= self.CP.minEnableSpeed and
               not CS.out.brakePressed and not CS.out.gasPressed and not CS.out.regenBraking)
      gas_set_ready = (self.CP.openpilotLongitudinalControl and isinstance(physical, (VoltCcPhysical, PhysicalObservation)) and physical.current(now_nanos) and
                       CS.out.canValid and not CS.out.canTimeout and CS.out.cruiseState.available and CS.out.cruiseState.enabled and
                       volt_cc_forward_gear(CS.out.gearShifter) and CS.out.vEgo >= self.CP.minEnableSpeed and
                       CC.enabled and (not CC.longActive or self.ordinary_cc_profile) and CS.out.gasPressed and
                       not CS.out.brakePressed and not CS.out.regenBraking and self.frame % 52 == 0 and
                       all(math.isfinite(value) for value in (CS.out.cruiseState.speed, CS.out.vEgo, hud_v_cruise)) and
                       CS.out.cruiseState.speed < CS.out.vEgo < hud_v_cruise and
                       physical.button_credit_ns > 0 and physical.button_credit_ns != self.volt_cc_consumed_source_ns)
      if cancel_sent:
        self.volt_cc_last_button_frame = self.frame
      elif gas_set_ready:
        can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.POWERTRAIN, (CS.buttons_counter + 1) % 4, CruiseButtons.DECEL_SET))
        self.volt_cc_consumed_source_ns = physical.button_credit_ns
        self.volt_cc_last_button_frame = self.frame
      elif not self.CP.openpilotLongitudinalControl or not ready or not CC.longActive:
        if self.ordinary_cc_profile:
          self.ordinary_cc_cadence.reset_burst()
          self.ordinary_cc_cadence.last_frame = self.frame
        self.volt_cc_last_button_frame = self.frame
        if not self.ordinary_cc_profile:
          self.volt_cc_consumed_source_ns = physical.button_credit_ns if isinstance(physical, VoltCcPhysical) else 0
      elif self.ordinary_cc_profile and (self.frame % 4 == 0 or self.CP.carFingerprint == CAR.CADILLAC_XT4_CC):
        button, rate, self.apply_speed = ordinary_button_request(
          CS.out.vEgo, CS.out.cruiseState.speed, actuators.accel, self.CP.minEnableSpeed, self.volt_cc_metric)
        source_ns = physical.button_credit_ns
        if (source_ns > 0 and source_ns != self.volt_cc_consumed_source_ns and
            self.ordinary_cc_cadence.ready(self.frame, CS.buttons_counter, button, rate)):
          self.volt_cc_consumed_source_ns = source_ns
          can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.POWERTRAIN, (CS.buttons_counter + 1) % 4, button))
      elif self.frame % 4 == 0:
        button, rate = button_request(CS.out.vEgo, CS.out.cruiseState.speed, actuators.accel, CS.out.vCruise,
                                      bool(CC.hudControl.leadVisible), self.volt_cc_metric)
        source_ns = physical.button_credit_ns
        if ((self.frame - self.volt_cc_last_button_frame) * DT_CTRL > rate and
            source_ns > 0 and source_ns != self.volt_cc_consumed_source_ns):
          self.volt_cc_last_button_frame = self.frame
          self.volt_cc_consumed_source_ns = source_ns
          can_sends.append(gmcan.create_buttons(self.packer_pt, CanBus.POWERTRAIN, (CS.buttons_counter + 1) % 4, button))

    keepalive_step = 100 if self.CP.carFingerprint == CAR.CHEVROLET_MALIBU_CC else 200
    if (self.ordinary_cc_profile and
        self.CP.openpilotLongitudinalControl and self.frame % keepalive_step == 0):
      can_sends += gmcan.create_adas_keepalive(CanBus.POWERTRAIN)
    self.frame += 1
    return new_actuators, can_sends
