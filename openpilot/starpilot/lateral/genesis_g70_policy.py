"""Default Genesis G70 2020 torque shaping from StarPilot ba901b5f (no FLM overrides)."""

import math
from collections import deque

import numpy as np

from openpilot.starpilot.lateral.torque_extension import apply_turn_assist
from openpilot.cereal import log
from opendbc.car import structs
from opendbc.car.lateral import get_friction
from opendbc.car.hyundai.values import CAR
from openpilot.common.constants import ACCELERATION_DUE_TO_GRAVITY, CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.pid import PIDController
from openpilot.starpilot.lateral.torque_shaping import (
  INTERP_SPEEDS,
  KP_INTERP,
  KI,
  LAT_ACCEL_REQUEST_BUFFER_SECONDS,
  LP_FILTER_CUTOFF_HZ,
  MAX_LAT_JERK_UP,
  LOW_SPEED_X,
  LOW_SPEED_Y,
  MIN_SPEED,
  JERK_GAIN,
  FF_ROLL_OFFSET_FADE_BP,
  FF_ROLL_OFFSET_FADE_V,
  UNWIND_D_DES_THRESHOLD,
  UNWIND_LAT_ACCEL_NEAR_ZERO,
  center_chatter_friction_jerk_deadzone,
  sigmoid as _sigmoid,
  get_standard_friction_threshold,
)


def supported_cp(CP):
  return (
    CP.brand == "hyundai"
    and CP.carFingerprint == CAR.GENESIS_G70_2020
    and CP.steerControlType == structs.CarParams.SteerControlType.torque
    and CP.lateralTuning.which() == "torque"
    and not CP.dashcamOnly
    and not CP.passive
  )

GENESIS_G70_FRICTION_THRESHOLD_GAIN = 0.10
GENESIS_G70_CURVE_TURN_IN_JERK_REDUCTION = 0.50
GENESIS_G70_CURVE_TURN_IN_SPEED_BP = [20.0, 25.0]
GENESIS_G70_CURVE_TURN_IN_LAT_BP = [0.35, 0.70]
GENESIS_G70_FRICTION_THRESHOLD_SPEED_BP = [10.0, 20.0]
GENESIS_G70_FRICTION_THRESHOLD_SPEED_V = [1.0, 2.0]
GENESIS_G70_FRICTION_SPEED_ONSET = 10.0
GENESIS_G70_FRICTION_SPEED_ONSET_WIDTH = 3.0
GENESIS_G70_FRICTION_SPEED_CUTOFF = 35.0
GENESIS_G70_FRICTION_SPEED_CUTOFF_WIDTH = 6.0
GENESIS_G70_FRICTION_CENTER_LAT = 0.28
GENESIS_G70_FRICTION_CENTER_LAT_WIDTH = 0.10
GENESIS_G70_FRICTION_CALM_JERK = 0.35
GENESIS_G70_FRICTION_CALM_JERK_WIDTH = 0.10
GENESIS_G70_FRICTION_JERK_DEADZONE_MAX = 0.39
GENESIS_G70_FRICTION_JERK_DEADZONE_LAT = 0.30
GENESIS_G70_FRICTION_JERK_DEADZONE_LAT_WIDTH = 0.08
GENESIS_G70_FRICTION_JERK_DEADZONE_SPEED = 12.0
GENESIS_G70_FRICTION_JERK_DEADZONE_SPEED_WIDTH = 3.5
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_MAX = 0.26
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_SPEED = 35.0 * CV.MPH_TO_MS
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_SPEED_WIDTH = 8.0 * CV.MPH_TO_MS
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT = 0.35
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT_WIDTH = 0.15
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT_CUTOFF = 1.75
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT_CUTOFF_WIDTH = 0.30
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_JERK = 0.20
GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_JERK_WIDTH = 0.12
GENESIS_G70_CENTER_OUTPUT_TAPER_MAX = 0.30
GENESIS_G70_CENTER_OUTPUT_TAPER_LAT = 0.30
GENESIS_G70_CENTER_OUTPUT_TAPER_LAT_WIDTH = 0.10
GENESIS_G70_CENTER_OUTPUT_TAPER_SPEED = 18.0
GENESIS_G70_CENTER_OUTPUT_TAPER_SPEED_WIDTH = 3.0
GENESIS_G70_LOW_SPEED_CENTER_TAPER_MAX = 0.06
GENESIS_G70_LOW_SPEED_CENTER_TAPER_LAT = 0.14
GENESIS_G70_LOW_SPEED_CENTER_TAPER_LAT_WIDTH = 0.05
GENESIS_G70_LOW_SPEED_CENTER_TAPER_SPEED_MAX = 7.5
GENESIS_G70_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH = 1.2
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_MAX = 0.24
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_SPEED = 6.0
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_SPEED_WIDTH = 1.5
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ERROR = 7.0
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ERROR_WIDTH = 3.0
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ACTUAL = 8.0
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ACTUAL_WIDTH = 4.0
GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_BLEND = 0.50
GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_REDUCTION = 0.85
GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_LAT = 0.14
GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_LAT_WIDTH = 0.05
GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_SPEED = 6.0
GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_SPEED_WIDTH = 1.5
GENESIS_G70_UNWIND_FF_REDUCTION_MAX = 0.34
GENESIS_G70_UNWIND_FF_OVERSHOOT = 0.13
GENESIS_G70_UNWIND_FF_OVERSHOOT_WIDTH = 0.17
GENESIS_G70_UNWIND_FF_JERK = 0.08
GENESIS_G70_UNWIND_FF_JERK_WIDTH = 0.11
GENESIS_G70_UNWIND_FF_SPEED = 18.0
GENESIS_G70_UNWIND_FF_SPEED_WIDTH = 3.0
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_MAX = 0.22
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_SPEED = 50.0 * CV.MPH_TO_MS
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_SPEED_WIDTH = 8.0 * CV.MPH_TO_MS
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_ERROR = 0.18
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_ERROR_WIDTH = 0.15
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_JERK = 0.15
GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_JERK_WIDTH = 0.10
GENESIS_G70_OUTPUT_SMOOTHING_SPEED = 40.0 * CV.MPH_TO_MS
GENESIS_G70_OUTPUT_SMOOTHING_SPEED_WIDTH = 6.0 * CV.MPH_TO_MS
GENESIS_G70_OUTPUT_SMOOTHING_CENTER_LAT = 0.42
GENESIS_G70_OUTPUT_SMOOTHING_CENTER_LAT_WIDTH = 0.14
GENESIS_G70_OUTPUT_SMOOTHING_CENTER_RC = 0.18
GENESIS_G70_OUTPUT_SMOOTHING_CURVE_RC = 0.10
GENESIS_G70_OUTPUT_SMOOTHING_RELEASE_RC = 0.03
GENESIS_G70_OUTPUT_SMOOTHING_OVERSHOOT = 0.08
GENESIS_G70_ANGLE_OUTPUT_TAPER_MIN = 0.45
GENESIS_G70_ANGLE_OUTPUT_TAPER_START = 70.0
GENESIS_G70_ANGLE_OUTPUT_TAPER_WIDTH = 6.0

def get_genesis_g70_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0,
                                       desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_standard_friction_threshold(v_ego)
  base_threshold *= np.interp(v_ego, GENESIS_G70_FRICTION_THRESHOLD_SPEED_BP, GENESIS_G70_FRICTION_THRESHOLD_SPEED_V)
  speed_onset = _sigmoid((v_ego - GENESIS_G70_FRICTION_SPEED_ONSET) / GENESIS_G70_FRICTION_SPEED_ONSET_WIDTH)
  speed_cutoff = _sigmoid((GENESIS_G70_FRICTION_SPEED_CUTOFF - v_ego) / GENESIS_G70_FRICTION_SPEED_CUTOFF_WIDTH)
  center_weight = _sigmoid((GENESIS_G70_FRICTION_CENTER_LAT - abs(desired_lateral_accel)) /
                           GENESIS_G70_FRICTION_CENTER_LAT_WIDTH)
  calm_jerk_weight = _sigmoid((GENESIS_G70_FRICTION_CALM_JERK - abs(desired_lateral_jerk)) /
                              GENESIS_G70_FRICTION_CALM_JERK_WIDTH)
  gain = (GENESIS_G70_FRICTION_THRESHOLD_GAIN * speed_onset * speed_cutoff *
          center_weight * calm_jerk_weight)
  return base_threshold * (1.0 + gain)

def get_genesis_g70_friction_jerk_deadzone(v_ego: float, desired_lateral_accel: float,
                                           desired_lateral_jerk: float = 0.0,
                                           measured_lateral_accel: float = 0.0) -> float:
  speed_weight = _sigmoid((v_ego - GENESIS_G70_FRICTION_JERK_DEADZONE_SPEED) /
                          GENESIS_G70_FRICTION_JERK_DEADZONE_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_G70_FRICTION_JERK_DEADZONE_LAT - abs(desired_lateral_accel)) /
                           GENESIS_G70_FRICTION_JERK_DEADZONE_LAT_WIDTH)
  deadzone = GENESIS_G70_FRICTION_JERK_DEADZONE_MAX * speed_weight * center_weight

  if desired_lateral_accel * desired_lateral_jerk > 0.0:
    turn_in_weight = (np.interp(v_ego, GENESIS_G70_CURVE_TURN_IN_SPEED_BP, [0.0, 1.0]) *
                      np.interp(abs(desired_lateral_accel), GENESIS_G70_CURVE_TURN_IN_LAT_BP, [0.0, 1.0]))
    deadzone += (GENESIS_G70_CURVE_TURN_IN_JERK_REDUCTION * turn_in_weight *
                 max(abs(desired_lateral_jerk) - deadzone, 0.0))

  overshoot = max(abs(measured_lateral_accel) - abs(desired_lateral_accel), 0.0)
  if (desired_lateral_accel * desired_lateral_jerk < 0.0 and
      desired_lateral_accel * measured_lateral_accel > 0.0 and overshoot > 0.0):
    curve_speed_weight = _sigmoid(
      (max(v_ego, 0.0) - GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_SPEED) /
      GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_SPEED_WIDTH
    )
    curve_onset_weight = _sigmoid(
      (abs(desired_lateral_accel) - GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT) /
      GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT_WIDTH
    )
    curve_cutoff_weight = _sigmoid(
      (GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT_CUTOFF - abs(desired_lateral_accel)) /
      GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_LAT_CUTOFF_WIDTH
    )
    jerk_weight = _sigmoid(
      (abs(desired_lateral_jerk) - GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_JERK) /
      GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_JERK_WIDTH
    )
    overshoot_weight = _sigmoid((overshoot - 0.08) / 0.10)
    boundary_weight = get_genesis_g70_overshoot_blend(desired_lateral_accel, measured_lateral_accel)
    boundary_weight *= min(abs(desired_lateral_jerk) / 0.15, 1.0)
    deadzone += (GENESIS_G70_CURVE_UNWIND_FRICTION_JERK_DEADZONE_MAX * curve_speed_weight *
                 curve_onset_weight * curve_cutoff_weight * jerk_weight * overshoot_weight * boundary_weight)
  return deadzone

def get_genesis_g70_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sigmoid((v_ego - GENESIS_G70_CENTER_OUTPUT_TAPER_SPEED) /
                          GENESIS_G70_CENTER_OUTPUT_TAPER_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_G70_CENTER_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                           GENESIS_G70_CENTER_OUTPUT_TAPER_LAT_WIDTH)
  reduction = GENESIS_G70_CENTER_OUTPUT_TAPER_MAX * speed_weight * center_weight
  low_speed_weight = _sigmoid((GENESIS_G70_LOW_SPEED_CENTER_TAPER_SPEED_MAX - v_ego) /
                               GENESIS_G70_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH)
  low_speed_center_weight = _sigmoid((GENESIS_G70_LOW_SPEED_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                                     GENESIS_G70_LOW_SPEED_CENTER_TAPER_LAT_WIDTH)
  reduction += GENESIS_G70_LOW_SPEED_CENTER_TAPER_MAX * low_speed_weight * low_speed_center_weight
  return 1.0 - reduction

def get_genesis_g70_low_speed_angle_damping(desired_angle_deg: float, actual_angle_deg: float,
                                             current_output_torque: float, v_ego: float) -> float:
  angle_error = desired_angle_deg - actual_angle_deg
  speed_weight = _sigmoid((GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_SPEED - max(v_ego, 0.0)) /
                          GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_SPEED_WIDTH)
  error_weight = _sigmoid((abs(angle_error) - GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ERROR) /
                          GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ERROR_WIDTH)
  actual_angle_weight = _sigmoid((abs(actual_angle_deg) - GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ACTUAL) /
                                 GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_ACTUAL_WIDTH)
  damping_torque = math.copysign(
    GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_MAX * speed_weight * error_weight * actual_angle_weight,
    -angle_error,
  )
  if abs(damping_torque) < 1e-4:
    return current_output_torque
  if current_output_torque * damping_torque >= 0.0:
    damping_torque *= GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_BLEND
  return float(np.clip(current_output_torque + damping_torque, -1.0, 1.0))

def get_genesis_g70_low_speed_output_limit(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sigmoid((GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_SPEED - max(v_ego, 0.0)) /
                          GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_LAT - abs(desired_lateral_accel)) /
                           GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_LAT_WIDTH)
  return max(0.05, 1.0 - GENESIS_G70_LOW_SPEED_OUTPUT_LIMIT_REDUCTION * speed_weight * center_weight)

def get_genesis_g70_angle_output_scale(steering_angle_deg: float, output_torque: float) -> float:
  """Ease G70 torque as it approaches the EPS high-angle protection threshold."""
  if steering_angle_deg == 0.0 or output_torque * steering_angle_deg <= 0.0:
    return 1.0

  angle_weight = _sigmoid((abs(steering_angle_deg) - GENESIS_G70_ANGLE_OUTPUT_TAPER_START) /
                          GENESIS_G70_ANGLE_OUTPUT_TAPER_WIDTH)
  return 1.0 - ((1.0 - GENESIS_G70_ANGLE_OUTPUT_TAPER_MIN) * angle_weight)

def get_genesis_g70_overshoot_blend(setpoint: float, measured_lateral_accel: float) -> float:
  if setpoint * measured_lateral_accel <= 0.0:
    return 0.0
  overshoot = max(abs(measured_lateral_accel) - abs(setpoint), 0.0)
  return float(np.interp(abs(setpoint), [0.10, 0.35], [0.0, 1.0]) * min(overshoot / 0.15, 1.0))

def get_genesis_g70_unwind_ff_scale(setpoint: float, measured_lateral_accel: float,
                                    desired_lateral_jerk: float, v_ego: float) -> float:
  if setpoint * desired_lateral_jerk >= 0.0 or setpoint * measured_lateral_accel <= 0.0:
    return 1.0

  overshoot = max(abs(measured_lateral_accel) - abs(setpoint), 0.0)
  if overshoot <= 0.0:
    return 1.0
  overshoot_weight = _sigmoid((overshoot - GENESIS_G70_UNWIND_FF_OVERSHOOT) /
                              GENESIS_G70_UNWIND_FF_OVERSHOOT_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - GENESIS_G70_UNWIND_FF_JERK) /
                         GENESIS_G70_UNWIND_FF_JERK_WIDTH)
  speed_weight = _sigmoid((v_ego - GENESIS_G70_UNWIND_FF_SPEED) /
                          GENESIS_G70_UNWIND_FF_SPEED_WIDTH)
  boundary_weight = get_genesis_g70_overshoot_blend(setpoint, measured_lateral_accel)
  boundary_weight *= min(abs(desired_lateral_jerk) / 0.15, 1.0)
  return 1.0 - GENESIS_G70_UNWIND_FF_REDUCTION_MAX * overshoot_weight * jerk_weight * speed_weight * boundary_weight

def get_genesis_g70_high_speed_error_scale(setpoint: float, measured_lateral_accel: float,
                                            desired_lateral_jerk: float, v_ego: float) -> float:
  if (setpoint == 0.0 or setpoint * measured_lateral_accel <= 0.0 or
      abs(measured_lateral_accel) <= abs(setpoint)):
    return 1.0
  tracking_error = abs(measured_lateral_accel - setpoint)
  speed_weight = _sigmoid((v_ego - GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_SPEED) /
                          GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_SPEED_WIDTH)
  error_weight = _sigmoid((tracking_error - GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_ERROR) /
                          GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_ERROR_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_JERK) /
                         GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_JERK_WIDTH)
  unwind_jerk = -math.copysign(1.0, setpoint) * desired_lateral_jerk
  phase_weight = float(np.interp(unwind_jerk, [0.0, 0.15], [0.45, 1.0]))
  reduction = (GENESIS_G70_HIGH_SPEED_ERROR_DAMPING_MAX * speed_weight * error_weight *
               (0.35 + (0.65 * jerk_weight)) * phase_weight *
               get_genesis_g70_overshoot_blend(setpoint, measured_lateral_accel))
  return 1.0 - reduction

def get_genesis_g70_stabilized_output(output_torque: float, prev_output_torque: float,
                                      desired_lateral_accel: float, measured_lateral_accel: float,
                                      desired_lateral_jerk: float, v_ego: float, dt: float) -> float:
  speed_weight = _sigmoid((max(v_ego, 0.0) - GENESIS_G70_OUTPUT_SMOOTHING_SPEED) /
                          GENESIS_G70_OUTPUT_SMOOTHING_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_G70_OUTPUT_SMOOTHING_CENTER_LAT - abs(desired_lateral_accel)) /
                           GENESIS_G70_OUTPUT_SMOOTHING_CENTER_LAT_WIDTH)
  response_time = (GENESIS_G70_OUTPUT_SMOOTHING_CURVE_RC * (1.0 - center_weight) +
                   GENESIS_G70_OUTPUT_SMOOTHING_CENTER_RC * center_weight)

  measured_overshoot = (desired_lateral_accel * measured_lateral_accel > 0.0 and
                        abs(measured_lateral_accel) > abs(desired_lateral_accel) + GENESIS_G70_OUTPUT_SMOOTHING_OVERSHOOT)
  reducing_output = (prev_output_torque * output_torque <= 0.0 or
                     abs(output_torque) < abs(prev_output_torque))
  if reducing_output or (desired_lateral_accel * desired_lateral_jerk < 0.0 and measured_overshoot):
    response_time = GENESIS_G70_OUTPUT_SMOOTHING_RELEASE_RC

  output_alpha = dt / (response_time + dt)
  smoothed_output = prev_output_torque + output_alpha * (output_torque - prev_output_torque)
  return float(output_torque + speed_weight * (smoothed_output - output_torque))


GENESIS_G70_CENTER_MEASUREMENT_DAMPING_MAX = 0.09
GENESIS_G70_CENTER_MEASUREMENT_DAMPING_SPEED_BP = [50.0 * CV.MPH_TO_MS, 60.0 * CV.MPH_TO_MS]
GENESIS_G70_CENTER_MEASUREMENT_DAMPING_LAT_BP = [0.15, 0.35]
GENESIS_G70_CENTER_MEASUREMENT_DAMPING_JERK_BP = [0.20, 0.50]


def get_genesis_g70_center_measurement_damping_gain(v_ego: float, desired_lateral_accel: float,
                                                  measured_lateral_accel: float, desired_lateral_jerk: float) -> float:
  speed_weight = np.interp(v_ego, GENESIS_G70_CENTER_MEASUREMENT_DAMPING_SPEED_BP, [0.0, 1.0])
  center_weight = np.interp(max(abs(desired_lateral_accel), abs(measured_lateral_accel)),
                           GENESIS_G70_CENTER_MEASUREMENT_DAMPING_LAT_BP, [1.0, 0.0])
  jerk_weight = np.interp(abs(desired_lateral_jerk), GENESIS_G70_CENTER_MEASUREMENT_DAMPING_JERK_BP, [1.0, 0.0])
  return float(GENESIS_G70_CENTER_MEASUREMENT_DAMPING_MAX * speed_weight * center_weight * jerk_weight)


class GenesisG70TorquePolicy:
  def __init__(self, parent, CP):
    if not supported_cp(CP):
      raise ValueError("Genesis G70 2020 policy does not match CarParams")
    self.parent = parent
    self.dt = parent.dt
    parent.pid = PIDController([INTERP_SPEEDS, KP_INTERP], KI, rate=1 / self.dt)
    parent.update_limits()
    self.request_buffer_len = int(LAT_ACCEL_REQUEST_BUFFER_SECONDS / self.dt)
    self.curvature_request_buffer = deque([0.0] * self.request_buffer_len, maxlen=self.request_buffer_len)
    self.jerk_filter = FirstOrderFilter(0.0, 1 / (2 * np.pi * LP_FILTER_CUTOFF_HZ), self.dt)
    self.measurement_rate_filter = FirstOrderFilter(0.0, 1 / (2 * np.pi * (MAX_LAT_JERK_UP - 0.5)), self.dt)
    self.previous_measurement = 0.0
    self.prev_desired_lateral_accel = 0.0
    self.prev_steering_pressed = False
    self.prev_output_torque = 0.0
    self.low_speed_reset_threshold = max(CP.minSteerSpeed, 0.3)

  def update(self, active, CS, VM, params, steer_limited_by_safety, desired_curvature, curvature_limited, lat_delay):
    parent = self.parent
    pid_log = log.ControlsState.LateralTorqueState.new_message()
    pid_log.version = 2
    measured_curvature = -VM.calc_curvature(math.radians(CS.steeringAngleDeg - params.angleOffsetDeg), CS.vEgo, params.roll)
    measurement = measured_curvature * CS.vEgo**2
    future_desired_lateral_accel = desired_curvature * CS.vEgo**2
    if not active:
      parent.pid.reset()
      self.prev_output_torque = 0.0
      self.curvature_request_buffer.append(desired_curvature)
      self.previous_measurement = measurement
      self.measurement_rate_filter.x = 0.0
      self.jerk_filter.x = 0.0
      self.prev_desired_lateral_accel = future_desired_lateral_accel
      self.prev_steering_pressed = CS.steeringPressed
      pid_log.active = False
      return 0.0, 0.0, pid_log

    if self.prev_steering_pressed and not CS.steeringPressed:
      parent.pid.i *= 0.8
    roll_offset_fade = float(np.interp(CS.vEgo, FF_ROLL_OFFSET_FADE_BP, FF_ROLL_OFFSET_FADE_V))
    roll_compensation = params.roll * ACCELERATION_DUE_TO_GRAVITY * roll_offset_fade
    curvature_deadzone = abs(VM.calc_curvature(math.radians(parent.steering_angle_deadzone_deg), CS.vEgo, 0.0))
    lateral_accel_deadzone = curvature_deadzone * CS.vEgo**2
    delay_frames = int(np.clip(lat_delay / self.dt, 1, self.request_buffer_len))
    expected_lateral_accel = self.curvature_request_buffer[-delay_frames] * CS.vEgo**2
    self.curvature_request_buffer.append(desired_curvature)
    raw_lateral_jerk = (future_desired_lateral_accel - expected_lateral_accel) / max(lat_delay, self.dt)
    raw_lateral_jerk = float(np.clip(raw_lateral_jerk, -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP))
    desired_lateral_jerk = float(np.clip(self.jerk_filter.update(raw_lateral_jerk), -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP))
    gravity_adjusted_future_lateral_accel = future_desired_lateral_accel - roll_compensation
    setpoint = expected_lateral_accel + desired_lateral_jerk * lat_delay
    desired_lateral_accel_magnitude_rate = (abs(setpoint) - abs(self.prev_desired_lateral_accel)) / self.dt
    unwind_detected = desired_lateral_accel_magnitude_rate < UNWIND_D_DES_THRESHOLD and abs(setpoint) < UNWIND_LAT_ACCEL_NEAR_ZERO
    self.prev_desired_lateral_accel = setpoint
    measurement_rate = self.measurement_rate_filter.update((measurement - self.previous_measurement) / self.dt)
    measurement_rate = float(np.clip(measurement_rate, -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP))
    self.previous_measurement = measurement
    low_speed_factor = (np.interp(CS.vEgo, LOW_SPEED_X, LOW_SPEED_Y) / max(CS.vEgo, MIN_SPEED)) ** 2
    current_kp = np.interp(CS.vEgo, parent.pid._k_p[0], parent.pid._k_p[1])
    error = setpoint - measurement
    error_with_lsf = error * (1 + low_speed_factor / max(current_kp, 1e-3))
    pid_log.error = float(error_with_lsf)
    ff = gravity_adjusted_future_lateral_accel - parent.torque_params.latAccelOffset * roll_offset_fade
    ff *= get_genesis_g70_unwind_ff_scale(setpoint, measurement, desired_lateral_jerk, CS.vEgo)
    friction_threshold = get_genesis_g70_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
    vehicle_deadzone = get_genesis_g70_friction_jerk_deadzone(CS.vEgo, setpoint, desired_lateral_jerk, measurement)
    friction_jerk_deadzone = center_chatter_friction_jerk_deadzone(CS.vEgo, setpoint, vehicle_deadzone)
    friction_jerk = math.copysign(max(abs(desired_lateral_jerk) - friction_jerk_deadzone, 0.0), desired_lateral_jerk)
    ff += get_friction(error_with_lsf + JERK_GAIN * friction_jerk, lateral_accel_deadzone, friction_threshold, parent.torque_params)
    if CS.vEgo < self.low_speed_reset_threshold:
      parent.pid.reset()
    damping_gain = 0.0 if CS.steeringPressed else get_genesis_g70_center_measurement_damping_gain(
      CS.vEgo, setpoint, measurement, desired_lateral_jerk,
    )
    parent.pid._k_d = [[0.0], [damping_gain]]
    freeze_integrator = steer_limited_by_safety or CS.steeringPressed or CS.vEgo < self.low_speed_reset_threshold or unwind_detected
    output_lataccel = parent.pid.update(pid_log.error, error_rate=-measurement_rate, speed=CS.vEgo, feedforward=ff, freeze_integrator=freeze_integrator)
    output_torque = parent.torque_from_lateral_accel(output_lataccel, parent.torque_params)
    output_torque = apply_turn_assist(parent, CS, VM, params, desired_curvature, output_torque)
    if not CS.steeringPressed and CS.vEgo < GENESIS_G70_LOW_SPEED_ANGLE_DAMPING_SPEED + 2.0:
      desired_angle = math.degrees(VM.get_steer_from_curvature(-desired_curvature, CS.vEgo, params.roll))
      actual_angle = CS.steeringAngleDeg - params.angleOffsetDeg
      output_torque = get_genesis_g70_low_speed_angle_damping(desired_angle, actual_angle, output_torque, CS.vEgo)
    output_torque *= get_genesis_g70_center_output_scale(setpoint, CS.vEgo)
    output_torque *= get_genesis_g70_high_speed_error_scale(setpoint, measurement, desired_lateral_jerk, CS.vEgo)
    output_torque *= get_genesis_g70_angle_output_scale(CS.steeringAngleDeg, -output_torque)
    output_limit = get_genesis_g70_low_speed_output_limit(setpoint, CS.vEgo)
    output_torque = float(np.clip(output_torque, -output_limit, output_limit))
    if not CS.steeringPressed:
      output_torque = get_genesis_g70_stabilized_output(output_torque, self.prev_output_torque, setpoint, measurement,
                                                      desired_lateral_jerk, CS.vEgo, self.dt)
    pid_log.active = True
    pid_log.p = float(parent.pid.p)
    pid_log.i = float(parent.pid.i)
    pid_log.d = float(parent.pid.d)
    pid_log.f = float(parent.pid.f)
    pid_log.output = float(-output_torque)
    pid_log.actualLateralAccel = float(measurement)
    pid_log.desiredLateralAccel = float(setpoint)
    pid_log.desiredLateralJerk = float(desired_lateral_jerk)
    pid_log.saturated = bool(parent._check_saturation(parent.steer_max - abs(output_torque) < 1e-3, CS, steer_limited_by_safety, curvature_limited))
    self.prev_steering_pressed = CS.steeringPressed
    self.prev_output_torque = float(output_torque)
    return -output_torque, 0.0, pid_log
