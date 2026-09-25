"""Reached Silverado interceptor law and final caller overrides."""

import math
import numpy as np
from opendbc.car import ACCELERATION_DUE_TO_GRAVITY

def pedal_fraction(accel: float, speed: float) -> float:
  """Original Silverado generic pedal fraction; no regen paddle owner."""
  accel_gain = np.interp(speed, [0.0, 3.0, 8.0, 20.0], [0.47, 0.52, 0.57, 0.61])
  offset = np.interp(speed, [0.0, 1.0, 3.0, 6.0, 15.0, 30.0], [0.085, 0.11, 0.17, 0.23, 0.235, 0.23])
  accel = 0.0 if abs(accel) < 0.04 else accel
  scale = np.interp(abs(accel), [0.0, 0.35, 0.8, 1.5, 2.5],
                    [0.58, 0.68, 0.82, 0.93, 1.0] if accel >= 0 else [0.44, 0.54, 0.70, 0.89, 1.0])
  command_accel = accel * scale
  if accel < -2.0:
    command_accel *= np.interp(abs(accel), [2., 2.5, 3.], [1., 1.03, 1.06])
  command = float(np.clip(offset + command_accel * accel_gain, 0., 1.))
  ceiling = np.interp(speed, [0.0, 1.0, 2.5, 4.5, 6.0, 8.0, 12.0], [0.20, 0.235, 0.29, 0.365, 0.52, 0.78, 1.0])
  return float(min(command, ceiling))

def pedal_slew(target: float, steady: float, accel: float, speed: float) -> float:
  urgency = float(np.clip(abs(accel) / 2.0, 0.0, 1.0))
  rise = np.interp(speed, [0.0, 3.0, 8.0, 20.0], [0.007, 0.012, 0.022, 0.036]) + 0.011 * urgency
  if accel > 0.0 and speed > 6.0:
    rise *= np.interp(abs(accel), [0.0, 0.12, 0.25, 0.45, 0.8], [0.55, 0.58, 0.68, 0.82, 1.0])
  if accel > 1.2:
    rise += np.interp(speed, [0.0, 4.0, 12.0, 25.0], [0.006, 0.005, 0.003, 0.002])
  fall = np.interp(speed, [0.0, 3.0, 8.0, 20.0], [0.008, 0.014, 0.026, 0.045]) + 0.015 * urgency
  return float(np.clip(target, steady - fall, steady + rise))

class SilveradoPedalCommand:
  def __init__(self, cp):
    self.mass = cp.mass
    self.wheelbase = cp.wheelbase
    self.stop_accel = cp.stopAccel
    self.reset()

  def reset(self):
    self.steady = 0.
    self.active_last = False
    self.recovering = False
    self.recovery_emitted = 0.

  def prime_recovery(self):
    # Invalid input revokes actuation. Recovery resumes through the original slew from zero.
    self.steady = 0.
    self.active_last = True
    self.recovering = True
    self.recovery_emitted = 0.

  def pause_recovery(self):
    if self.recovering:
      self.recovery_emitted = 0.

  def update(self, accel, long_active, cs, *, stopping, resume, orientation=None):
    # The original outer caller bypasses calc on these branches and retains its memory.
    if not long_active:
      self.pause_recovery()
      return 0., -650., 0
    if cs.vEgo < .25 and stopping and not resume:
      self.pause_recovery()
      return 0., -650., int(min(-100 * self.stop_accel, 400))
    target = pedal_fraction(accel, cs.vEgo)
    self.steady = pedal_slew(target, self.steady, accel, cs.vEgo) if self.active_last else target
    self.active_last = True
    command = self.steady

    pitch = 0.
    if orientation is not None and len(orientation) == 3 and cs.vEgo > .5 and math.isfinite(orientation[1]):
      pitch = math.sin(orientation[1]) * ACCELERATION_DUE_TO_GRAVITY
      pitch = 0. if pitch > 0. and accel > 0. else min(pitch, .20)
    radius = .075 * self.wheelbase + .1453
    drag = .5 * .30 * (1.05 * self.wheelbase + .0679) * 1.225 * cs.vEgo ** 2
    scaled = radius * (self.mass * float(np.clip(accel + pitch, -4., 2.)) + drag) + 6150
    gas = int(round(np.clip(scaled, 5500, 7168)))
    brake = int(round(np.interp(min((scaled - 6150) / (radius * self.mass), 0.), [-4., 0.], [400., 0.])))
    if brake > 0 or stopping:
      gas = 5500
    if gas > 5500 and cs.cruiseState.standstill and (cs.standstill or cs.vEgo < .5):
      command = 18. / 255.
      gas, brake = 5500, 0
    if self.recovering:
      desired = command
      # Bound the final command, including SNG, after invalid input. Zero and decreases are immediate.
      command = min(desired, pedal_slew(desired, self.recovery_emitted, accel, cs.vEgo)) if desired > .001 else 0.
      self.recovery_emitted = command
      if command == desired:
        self.recovering = False
    return command, gas - 6150, brake
