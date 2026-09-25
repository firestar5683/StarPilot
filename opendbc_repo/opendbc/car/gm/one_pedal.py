"""Volt moving one-pedal braking with vehicle-owned physical admission."""
import math

import numpy as np

from opendbc.car import ACCELERATION_DUE_TO_GRAVITY
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.gm.values import CAR


class _VoltPid:
  # Original openpilot/common/pid.py arithmetic, with unused derivative/override API removed.
  def __init__(self, kp, ki):
    self.kp, self.ki = kp, ki
    self.reset()

  def reset(self):
    self.i = 0.0

  def update(self, error, *, speed, feedforward):
    proportional = float(np.interp(speed, *self.kp)) * error
    integral = self.i + float(np.interp(speed, *self.ki)) * 0.04 * error
    candidate = proportional + integral + feedforward
    upper = self.i if candidate > 0.0 else 0.0
    lower = self.i if candidate < -3.5 else -3.5
    self.i = float(np.clip(integral, lower, upper))
    return float(np.clip(proportional + self.i + feedforward, -3.5, 0.0))


class VoltOnePedal:
  def __init__(self, cp, params):
    self.params = params
    self.stopping_speed = .75 if cp.carFingerprint == CAR.CHEVROLET_VOLT else .25
    self.pid = _VoltPid(((0.,), (0.,)),
                        (cp.longitudinalTuning.kiBP, cp.longitudinalTuning.kiV))
    self.decel = 0.0
    self.brake = 0
    self.lift_frames = 0
    self.gas_last = False

  def observe(self, *, eligible, gas_pressed, speed):
    # Called at controller cadence; preserve a gas-release edge until the next 25 Hz sender.
    if eligible and self.gas_last and not gas_pressed and speed < 2.0 * CV.MPH_TO_MS:
      self.lift_frames = 8
    elif gas_pressed or not eligible:
      self.lift_frames = 0
    self.gas_last = gas_pressed

  def update(self, *, eligible, speed, acceleration, steering_angle, orientation):
    # Called only at the existing gas/friction sender cadence, with qualified physical inputs.
    finite = all(math.isfinite(value) for value in (speed, acceleration, steering_angle, *orientation))
    if not eligible or not finite or speed < 0:
      self.pid.reset()
      self.decel = min(0.0, acceleration) if math.isfinite(acceleration) else 0.0
      self.brake = 0
      self.lift_frames = 0
      return 0
    pitch_accel = 0.0
    if len(orientation) == 3 and speed > self.stopping_speed:
      pitch_accel = math.sin(orientation[1]) * ACCELERATION_DUE_TO_GRAVITY
      pitch_values = [0.4, 1.0] if pitch_accel <= 0 else [0.2, 1.0]
      pitch_accel *= float(np.interp(speed, [4.0, 8.0], pitch_values))
    target = float(np.interp(speed, [0.5 * CV.MPH_TO_MS, 6.0 * CV.MPH_TO_MS], [-1.0, -1.1]))
    measured = min(0.0, acceleration + pitch_accel)
    error = (target - measured) * float(np.interp(speed, [1.5, 20.0], [0.4, 0.2]))
    raw = float(self.pid.update(error, speed=speed, feedforward=target))
    factor = min(float(np.interp(speed, [0.0, 10.0 * CV.MPH_TO_MS], [0.2, 1.0])),
                 float(np.interp(abs(steering_angle), [20.0, 120.0], [1.0, 0.2])))
    lower = min(self.decel, measured) - 0.032 * factor
    # Preserve the original asymmetric upper expression; this is not a tuning change.
    upper = max(self.decel, measured) + 0.032 + factor
    self.decel = max(float(np.clip(raw, lower, upper)), -2.1)
    self.brake = int(round(np.clip(np.interp(self.decel, [self.params.ACCEL_MIN, 0.],
                                           [self.params.MAX_BRAKE, 0.]), 0, self.params.MAX_BRAKE)))
    if self.lift_frames > 0:
      lift = 0 if speed > 2.0 * CV.MPH_TO_MS else int(round(np.interp(
        speed, [0.0, self.params.NEAR_STOP_BRAKE_PHASE, 2.0 * CV.MPH_TO_MS], [80.0, 80.0, 20.0])))
      self.brake = max(self.brake, lift)
      self.lift_frames -= 1
    return self.brake
