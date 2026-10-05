"""First-generation Electrified GV70 torque shaping."""

import math
from collections import deque

import numpy as np

from openpilot.cereal import log
from opendbc.car import structs
from opendbc.car.lateral import get_friction
from opendbc.car.hyundai.values import CAR
from openpilot.common.constants import ACCELERATION_DUE_TO_GRAVITY
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
)


from openpilot.starpilot.lateral.gv70_shaping import (
  get_genesis_gv70_friction_threshold,
  get_genesis_gv70_friction_jerk_deadzone,
  get_genesis_gv70_center_output_scale,
  get_genesis_gv70_unwind_ff_scale,
  get_genesis_gv70_high_speed_error_scale,
  get_genesis_gv70_reversal_output_scale,
  get_genesis_gv70_low_speed_center_overshoot_scale,
  get_genesis_gv70_stabilized_output,
  GENESIS_GV70_MEASUREMENT_DAMPING_SPEED_BP, GENESIS_GV70_MEASUREMENT_DAMPING_V,
)

def supported_cp(CP):
  return (
    CP.brand == "hyundai"
    and CP.carFingerprint == CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN
    and CP.steerControlType == structs.CarParams.SteerControlType.torque
    and CP.lateralTuning.which() == "torque"
    and not CP.dashcamOnly
    and not CP.passive
    and not CP.notCar
  )



class GenesisGV70TorquePolicy:
  def __init__(self, parent, CP):
    if not supported_cp(CP):
      raise ValueError("Electrified GV70 policy does not match CarParams")
    self.parent = parent
    self.dt = parent.dt
    parent.pid = PIDController([INTERP_SPEEDS, KP_INTERP], KI,
                               [GENESIS_GV70_MEASUREMENT_DAMPING_SPEED_BP, GENESIS_GV70_MEASUREMENT_DAMPING_V],
                               rate=1 / self.dt)
    parent.update_limits()
    self.request_buffer_len = int(LAT_ACCEL_REQUEST_BUFFER_SECONDS / self.dt)
    self.curvature_request_buffer = deque([0.0] * self.request_buffer_len, maxlen=self.request_buffer_len)
    self.jerk_filter = FirstOrderFilter(0.0, 1 / (2 * np.pi * LP_FILTER_CUTOFF_HZ), self.dt)
    self.measurement_rate_filter = FirstOrderFilter(0.0, 1 / (2 * np.pi * (MAX_LAT_JERK_UP - 0.5)), self.dt)
    self.previous_measurement = 0.0
    self.prev_desired_lateral_accel = 0.0
    self.prev_steering_pressed = False
    self.prev_output_torque = 0.0
    self.previous_feedforward = None
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
      self.previous_feedforward = None
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
    ff *= get_genesis_gv70_unwind_ff_scale(setpoint, measurement, desired_lateral_jerk, CS.vEgo)
    friction_threshold = get_genesis_gv70_friction_threshold(CS.vEgo, setpoint, desired_lateral_jerk)
    vehicle_deadzone = get_genesis_gv70_friction_jerk_deadzone(CS.vEgo, setpoint)
    friction_jerk_deadzone = center_chatter_friction_jerk_deadzone(CS.vEgo, setpoint, vehicle_deadzone)
    friction_jerk = math.copysign(max(abs(desired_lateral_jerk) - friction_jerk_deadzone, 0.0), desired_lateral_jerk)
    ff += get_friction(error_with_lsf + JERK_GAIN * friction_jerk, lateral_accel_deadzone, friction_threshold, parent.torque_params)
    if CS.vEgo < self.low_speed_reset_threshold:
      parent.pid.reset()
    # Filter feedforward before PID so feedback remains immediate.
    ff *= get_genesis_gv70_center_output_scale(setpoint, CS.vEgo)
    ff *= get_genesis_gv70_low_speed_center_overshoot_scale(setpoint, measurement, CS.vEgo)
    ff *= get_genesis_gv70_high_speed_error_scale(setpoint, measurement, desired_lateral_jerk, CS.vEgo)
    ff *= get_genesis_gv70_reversal_output_scale(setpoint, measurement, desired_lateral_jerk, CS.vEgo)
    if not CS.steeringPressed and not self.prev_steering_pressed and self.previous_feedforward is not None:
      ff = get_genesis_gv70_stabilized_output(ff, self.previous_feedforward, setpoint,
                                            desired_lateral_jerk, CS.vEgo, self.dt)
    self.previous_feedforward = ff
    error_rate = 0.0 if CS.steeringPressed else -measurement_rate
    freeze_integrator = steer_limited_by_safety or CS.steeringPressed or CS.vEgo < self.low_speed_reset_threshold or unwind_detected
    output_lataccel = parent.pid.update(pid_log.error, error_rate=error_rate, speed=CS.vEgo, feedforward=ff, freeze_integrator=freeze_integrator)
    output_torque = parent.torque_from_lateral_accel(output_lataccel, parent.torque_params)
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
