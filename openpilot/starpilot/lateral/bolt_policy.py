"""Vehicle-owned default torque controller for the five manual Bolt identities."""

from collections import deque
import math

import numpy as np

from opendbc.car import structs
from opendbc.car.gm.values import CAR
from opendbc.car.lateral import get_friction
from openpilot.starpilot.flm import live as flm
from openpilot.starpilot.lateral.torque_extension import apply_turn_assist
from openpilot.cereal import log
from openpilot.common.constants import ACCELERATION_DUE_TO_GRAVITY
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.pid import PIDController
from openpilot.starpilot.lateral import bolt_shaping as shaping
from openpilot.starpilot.lateral.torque_shaping import (
  FF_ROLL_OFFSET_FADE_BP,
  FF_ROLL_OFFSET_FADE_V,
  JERK_GAIN,
  KI,
  LAT_ACCEL_REQUEST_BUFFER_SECONDS,
  LOW_SPEED_X,
  LOW_SPEED_Y,
  LP_FILTER_CUTOFF_HZ,
  MAX_LAT_JERK_UP,
  MIN_SPEED,
  UNWIND_D_DES_THRESHOLD,
  UNWIND_LAT_ACCEL_NEAR_ZERO,
  center_chatter_friction_jerk_deadzone,
)

BOLT_GENERATIONS = {
  CAR.CHEVROLET_BOLT_CC_2017: 2017,
  CAR.CHEVROLET_BOLT_CC_2018_2021: 2018,
  CAR.CHEVROLET_BOLT_CC_2022_2023: 2022,
  CAR.CHEVROLET_BOLT_ACC_2022_2023: 2022,
  CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL: 2022,
}


def supported_cp(cp):
  return (
    cp.brand == 'gm'
    and cp.carFingerprint in BOLT_GENERATIONS
    and not cp.notCar
    and not cp.passive
    and not cp.dashcamOnly
    and cp.steerControlType == structs.CarParams.SteerControlType.torque
    and cp.lateralTuning.which() == 'torque'
    and math.isfinite(cp.lateralTuning.torque.latAccelFactor)
    and cp.lateralTuning.torque.latAccelFactor > 0
    and math.isfinite(cp.lateralTuning.torque.latAccelOffset)
    and math.isfinite(cp.lateralTuning.torque.friction)
    and cp.lateralTuning.torque.friction >= 0
  )


class BoltTorquePolicy:
  def __init__(self, parent, cp):
    self.parent = parent
    if not supported_cp(cp):
      raise ValueError('Unsupported Bolt torque profile')
    self.generation = BOLT_GENERATIONS[cp.carFingerprint]
    self.dt = parent.dt
    # Preserve the source calibration's Float32 parameter representation.
    self.ff_positive = float(np.float32(1.03))
    self.ff_negative = float(np.float32(float(np.float32(1.07)) * (0.9 if self.generation == 2017 else 1.07)))
    self.ki_multiplier = float(np.float32(float(np.float32(0.93)) * (0.9 if self.generation == 2017 else 0.93)))
    self.center_boost = float(np.float32(0.026)) if self.generation == 2017 else float(np.float32(float(np.float32(0.02)) * 0.75))
    coefficients = {
      2017: ((2.15, 1.0, 0.129, 0.0), (2.15, 1.0, 0.145, 0.0)),
      2018: ((1.8, 1.1, 0.27, 0.0), (2.0, 1.0, 0.205, 0.0)),
      2022: ((2.6531724862969748, 1.1, 0.1919764879840985, 0.0), (2.7031724862969748, 1.0, 0.1469764879840985, 0.0)),
    }[self.generation]
    lateral_values = np.arange(-5.0, 5.0, 0.01)
    torque_values = []
    for value in lateral_values:
      a, b, c, d = coefficients[0 if value >= 0 else 1]
      sig_input = a * value
      sigmoid = np.sign(sig_input) * (1 / (1 + math.exp(-abs(sig_input))) - 0.5)
      torque_values.append(float(sigmoid * b + value * c + d))
    parent.torque_from_lateral_accel = lambda value, tune: np.interp(value, lateral_values, torque_values)
    parent.lateral_accel_from_torque = lambda value, tune: np.interp(value, torque_values, lateral_values)
    parent.pid = PIDController(0.6, KI * self.ki_multiplier, rate=1 / self.dt)
    parent.update_limits()
    self.buffer_len = int(LAT_ACCEL_REQUEST_BUFFER_SECONDS / self.dt)
    self.curvature_buffer = deque([0.0] * self.buffer_len, maxlen=self.buffer_len)
    self.jerk_filter = FirstOrderFilter(0.0, 1 / (2 * np.pi * LP_FILTER_CUTOFF_HZ), self.dt)
    self.measurement_filter = FirstOrderFilter(0.0, 1 / (2 * np.pi * (MAX_LAT_JERK_UP - 0.5)), self.dt)
    self.low_speed_reset_threshold = max(cp.minSteerSpeed, 0.3)
    self.previous_measurement = 0.0
    self.previous_setpoint = 0.0
    self.previous_output = 0.0
    self.previous_pressed = False

  def steer_ratio_scale(self, speed):
    if self.generation == 2017:
      return 1.0 + (1.045 - 1.0) * shaping._bolt_2017_high_speed_factor(speed)
    return 1.01 if self.generation == 2018 else 1.0

  def update(self, active, cs, vm, params, safety_limited, curvature, curvature_limited, delay):
    parent = self.parent
    pid_log = log.ControlsState.LateralTorqueState.new_message()
    pid_log.version = 2
    measurement = -vm.calc_curvature(math.radians(cs.steeringAngleDeg - params.angleOffsetDeg), cs.vEgo, params.roll) * cs.vEgo**2
    future = curvature * cs.vEgo**2
    if not active:
      parent.pid.reset()
      self.previous_output = 0.0
      self.curvature_buffer.append(curvature)
      self.previous_measurement = measurement
      self.measurement_filter.x = self.jerk_filter.x = 0.0
      self.previous_setpoint = future
      self.previous_pressed = cs.steeringPressed
      pid_log.active = False
      return 0.0, 0.0, pid_log
    if self.previous_pressed and not cs.steeringPressed:
      parent.pid.i *= 0.8
    fade = np.interp(cs.vEgo, FF_ROLL_OFFSET_FADE_BP, FF_ROLL_OFFSET_FADE_V)
    roll = params.roll * ACCELERATION_DUE_TO_GRAVITY * fade
    deadzone = abs(vm.calc_curvature(math.radians(parent.steering_angle_deadzone_deg + flm.deadband(parent.flm_surface, cs.vEgo)), cs.vEgo, 0.0)) * cs.vEgo**2
    delay_frames = int(np.clip(delay / self.dt, 1, self.buffer_len))
    expected = self.curvature_buffer[-delay_frames] * cs.vEgo**2
    self.curvature_buffer.append(curvature)
    raw_jerk = np.clip((future - expected) / max(delay, self.dt), -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP)
    jerk = np.clip(self.jerk_filter.update(raw_jerk), -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP)
    setpoint = expected + jerk * delay
    unwind = (setpoint - self.previous_setpoint) / self.dt < UNWIND_D_DES_THRESHOLD and abs(setpoint) < UNWIND_LAT_ACCEL_NEAR_ZERO
    self.previous_setpoint = setpoint
    rate = np.clip(self.measurement_filter.update((measurement - self.previous_measurement) / self.dt), -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP)
    self.previous_measurement = measurement
    lsf = (np.interp(cs.vEgo, LOW_SPEED_X, LOW_SPEED_Y) / max(cs.vEgo, MIN_SPEED)) ** 2
    kp = np.interp(cs.vEgo, parent.pid._k_p[0], parent.pid._k_p[1])
    error = (setpoint - measurement) * (1 + lsf / max(kp, 1e-3))
    gravity_adjusted = future - roll
    ff = gravity_adjusted - parent.torque_params.latAccelOffset * fade
    ff *= np.interp(ff, [-0.05, 0.0, 0.05], [self.ff_negative, 1.0, self.ff_positive])
    original_base_threshold = shaping.get_gm_base_friction_threshold(cs.vEgo)
    threshold = flm.base_threshold(parent.flm_surface, cs.vEgo, original_base_threshold)
    friction_scale = 1.0
    if self.generation == 2022:
      rich_input = ff
      ff *= shaping.get_bolt_2022_2023_ff_scale(setpoint, jerk, cs.vEgo)
      threshold = shaping.get_bolt_2022_2023_friction_threshold(cs.vEgo, setpoint, jerk)
      friction_scale = shaping.get_bolt_2022_2023_friction_scale(cs.vEgo, setpoint, jerk)
      ff, threshold = flm.stages(parent.flm_surface, cs, setpoint, jerk, ff, threshold, rich=True, rich_input=rich_input)
    elif self.generation == 2018:
      threshold = shaping.get_bolt_2018_2021_friction_threshold(cs.vEgo, setpoint, jerk)
      friction_scale = shaping.get_bolt_2018_2021_friction_scale(cs.vEgo, setpoint, jerk)
      threshold = flm.scaled_threshold(parent.flm_surface, cs.vEgo, threshold, original_base_threshold)
    if self.generation != 2022:
      ff, threshold = flm.stages(parent.flm_surface, cs, setpoint, jerk, ff, threshold)
    jerk_deadzone = center_chatter_friction_jerk_deadzone(cs.vEgo, setpoint, 0.0)
    friction_jerk = math.copysign(max(abs(jerk) - jerk_deadzone, 0.0), jerk)
    ff += friction_scale * get_friction(error + JERK_GAIN * friction_jerk, deadzone, threshold, parent.torque_params)
    if abs(gravity_adjusted) < 0.15:
      ff += np.sign(gravity_adjusted) * self.center_boost * np.interp(abs(gravity_adjusted), [0.0, 0.15], [1.0, 0.0])
    if cs.vEgo < self.low_speed_reset_threshold:
      parent.pid.reset()
    freeze = safety_limited or cs.steeringPressed or cs.vEgo < self.low_speed_reset_threshold or unwind
    pid_log.error = float(error)
    output = parent.torque_from_lateral_accel(
      parent.pid.update(pid_log.error, error_rate=-rate, speed=cs.vEgo, feedforward=ff, freeze_integrator=freeze), parent.torque_params
    )
    output = apply_turn_assist(parent, cs, vm, params, curvature, output)
    if self.generation == 2022:
      output *= shaping.get_bolt_2022_2023_center_output_scale(setpoint, cs.vEgo)
      limit = shaping.get_bolt_2022_2023_low_speed_center_output_limit(setpoint, cs.vEgo)
      output = float(np.clip(output, -limit, limit))
      output = shaping.get_bolt_2022_2023_low_speed_center_output(output, self.previous_output, setpoint, cs.vEgo)
    elif self.generation == 2017:
      output *= shaping.get_bolt_2017_torque_scale(setpoint, jerk, cs.vEgo)
    else:
      output *= shaping.get_bolt_2018_2021_dynamic_torque_scale(setpoint, jerk, cs.vEgo)
    self.previous_output = float(output)
    self.previous_pressed = cs.steeringPressed
    pid_log.active = True
    pid_log.p, pid_log.i, pid_log.d, pid_log.f = map(float, (parent.pid.p, parent.pid.i, parent.pid.d, parent.pid.f))
    pid_log.output = float(-output)
    pid_log.actualLateralAccel, pid_log.desiredLateralAccel, pid_log.desiredLateralJerk = map(float, (measurement, setpoint, jerk))
    pid_log.saturated = bool(parent._check_saturation(parent.steer_max - abs(output) < 1e-3, cs, safety_limited, curvature_limited))
    return -float(output), 0.0, pid_log
