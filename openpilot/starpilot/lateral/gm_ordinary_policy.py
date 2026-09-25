"""Shared ordinary GM torque law, without vehicle callback selection."""

from collections import deque
import math

import numpy as np

from opendbc.car.lateral import get_friction
from openpilot.starpilot.lateral.torque_extension import apply_turn_assist
from openpilot.starpilot.flm import live as flm
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

class GMOrdinaryTorquePolicy:
  def __init__(self, parent, cp):
    self.parent = parent
    self.dt = parent.dt
    parent.pid = PIDController(0.6, KI, rate=1 / self.dt)
    parent.update_limits()
    self.buffer_len = int(LAT_ACCEL_REQUEST_BUFFER_SECONDS / self.dt)
    self.curvature_buffer = deque([0.0] * self.buffer_len, maxlen=self.buffer_len)
    self.jerk_filter = FirstOrderFilter(0.0, 1 / (2 * np.pi * LP_FILTER_CUTOFF_HZ), self.dt)
    self.measurement_filter = FirstOrderFilter(0.0, 1 / (2 * np.pi * (MAX_LAT_JERK_UP - 0.5)), self.dt)
    self.low_speed_reset_threshold = max(cp.minSteerSpeed, 0.3)
    self.previous_measurement = 0.0
    self.previous_setpoint = 0.0
    self.previous_pressed = False

  def feedforward(self, value, setpoint, jerk, speed):
    return value

  def output(self, value, setpoint, speed):
    return value

  def update(self, active, cs, vm, params, safety_limited, curvature, curvature_limited, delay):
    parent = self.parent
    pid_log = log.ControlsState.LateralTorqueState.new_message()
    pid_log.version = 2
    measurement = -vm.calc_curvature(math.radians(cs.steeringAngleDeg - params.angleOffsetDeg), cs.vEgo, params.roll) * cs.vEgo**2
    future = curvature * cs.vEgo**2
    if not active:
      parent.pid.reset()
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
    ff = self.feedforward(ff, setpoint, jerk, cs.vEgo)
    threshold = flm.base_threshold(parent.flm_surface, cs.vEgo, shaping.get_gm_base_friction_threshold(cs.vEgo))
    ff, threshold = flm.stages(parent.flm_surface, cs, setpoint, jerk, ff, threshold)
    jerk_deadzone = center_chatter_friction_jerk_deadzone(cs.vEgo, setpoint, 0.0)
    friction_jerk = math.copysign(max(abs(jerk) - jerk_deadzone, 0.0), jerk)
    ff += get_friction(error + JERK_GAIN * friction_jerk, deadzone, threshold, parent.torque_params)
    if cs.vEgo < self.low_speed_reset_threshold:
      parent.pid.reset()
    freeze = safety_limited or cs.steeringPressed or cs.vEgo < self.low_speed_reset_threshold or unwind
    pid_log.error = float(error)
    output = parent.torque_from_lateral_accel(
      parent.pid.update(pid_log.error, error_rate=-rate, speed=cs.vEgo, feedforward=ff, freeze_integrator=freeze), parent.torque_params
    )
    output = apply_turn_assist(parent, cs, vm, params, curvature, output)
    output = self.output(output, setpoint, cs.vEgo)
    output = flm.angle_assist(parent.flm_surface, cs, vm, params, curvature, setpoint, jerk, output)
    self.previous_pressed = cs.steeringPressed
    pid_log.active = True
    pid_log.p, pid_log.i, pid_log.d, pid_log.f = map(float, (parent.pid.p, parent.pid.i, parent.pid.d, parent.pid.f))
    pid_log.output = float(-output)
    pid_log.actualLateralAccel, pid_log.desiredLateralAccel, pid_log.desiredLateralJerk = map(float, (measurement, setpoint, jerk))
    pid_log.saturated = bool(parent._check_saturation(parent.steer_max - abs(output) < 1e-3, cs, safety_limited, curvature_limited))
    return -float(output), 0.0, pid_log
