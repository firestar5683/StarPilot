"""Conventional-cruise GM pedal command and Malibu physical limits."""

import math
import numpy as np
from opendbc.car import ACCELERATION_DUE_TO_GRAVITY
from opendbc.car.gm.values import CAR
from opendbc.car.gm.conventional_pedal import stop_start_speed
from opendbc.car.gm.silverado_cc import pedal_fraction, pedal_slew

# The no-paddle interpolation and slew are shared source arithmetic. Physical
# gas/brake limits, pitch and launch thresholds remain bound to this identity.

class ConventionalPedalCommand:
  def __init__(self, cp):
    self.mass = cp.mass
    self.wheelbase = cp.wheelbase
    self.stop_accel = cp.stopAccel
    malibu = cp.carFingerprint == CAR.CHEVROLET_MALIBU_CC
    self.stop_speed = self.start_speed = stop_start_speed(malibu)
    self.max_gas = 8191 if malibu else 7168
    self.brake_bp = [-4., -.1] if malibu else [-4., 0.]
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
    if orientation is not None and len(orientation) == 3 and cs.vEgo > self.stop_speed and math.isfinite(orientation[1]):
      pitch = math.sin(orientation[1]) * ACCELERATION_DUE_TO_GRAVITY
      pitch = 0. if pitch > 0. and accel > 0. else min(pitch, .20)
    radius = .075 * self.wheelbase + .1453
    drag = .5 * .30 * (1.05 * self.wheelbase + .0679) * 1.225 * cs.vEgo ** 2
    scaled = radius * (self.mass * float(np.clip(accel + pitch, -4., 2.)) + drag) + 6150
    gas = int(round(np.clip(scaled, 5500, self.max_gas)))
    brake = int(round(np.interp(min((scaled - 6150) / (radius * self.mass), 0.), self.brake_bp, [400., 0.])))
    if brake > 0 or stopping:
      gas = 5500
    if gas > 5500 and cs.cruiseState.standstill and (cs.standstill or cs.vEgo < max(self.start_speed, .3)):
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
