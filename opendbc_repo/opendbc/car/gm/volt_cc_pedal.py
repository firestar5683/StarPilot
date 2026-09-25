import numpy as np

from opendbc.car.gm.silverado_cc import pedal_fraction, pedal_slew


class VoltCcPedalCommand:
  def __init__(self):
    self.steady = 0.
    self.active_last = False
    self.recovering = False
    self.recovery_emitted = 0.

  def prime_recovery(self):
    self.steady = 0.
    self.active_last = True
    self.recovering = True
    self.recovery_emitted = 0.

  def pause_recovery(self):
    if self.recovering:
      self.recovery_emitted = 0.

  def update(self, accel, long_active, cs, *, stopping, resume, gas_above_inactive, maneuver=False):
    if not long_active or cs.vEgo < .25 and stopping and not resume:
      self.pause_recovery()
      return 0.
    target = pedal_fraction(accel, cs.vEgo)
    self.steady = pedal_slew(target, self.steady, accel, cs.vEgo) if self.active_last else target
    self.active_last = True
    command = self.steady
    if gas_above_inactive and cs.cruiseState.standstill and (cs.standstill or cs.vEgo < (2. if maneuver else .75)):
      command = max(command, float(np.interp(accel, [0., 1., 2.], [18. / 255., .11, .16]))) if maneuver else 18. / 255.
    if self.recovering:
      desired = command
      command = min(desired, pedal_slew(desired, self.recovery_emitted, accel, cs.vEgo)) if desired > .001 else 0.
      self.recovery_emitted = command
      if command == desired:
        self.recovering = False
    return command
