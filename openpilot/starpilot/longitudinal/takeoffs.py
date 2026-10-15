"""Optional launch-state admission; vehicle owners retain stop and output limits."""
import math
from numbers import Real

from openpilot.starpilot.longitudinal.ioniq6_start import StartEvidence


def eligible(cp):
  return bool(getattr(cp, 'openpilotLongitudinalControl', False) and
              not any(getattr(cp, key, True) for key in ('passive', 'dashcamOnly', 'notCar')))


class TakeoffStart:
  def __init__(self):
    self.last_ns = 0
    self.drive_id = 0

  def select(self, *, active, CS, target, should_stop, limits, evidence, stock_hold_allowed=False):
    if not isinstance(evidence, StartEvidence):
      return False
    stamp, drive = evidence.observed_ns, evidence.drive_id
    if (type(stamp) is not int or type(drive) is not int or not 0 < drive < stamp or
        stamp <= self.last_ns):
      return False
    changed = self.drive_id not in (0, drive)
    self.last_ns, self.drive_id = stamp, drive
    try:
      lower, upper = limits
      physical = all(isinstance(v, Real) and not isinstance(v, bool) and math.isfinite(v) for v in (CS.vEgo, target, lower, upper))
      return bool(not changed and active and not should_stop and not CS.brakePressed and not CS.gasPressed and
        CS.canValid and not CS.canTimeout and evidence.car_fresh and evidence.plan_fresh and
        type(evidence.lead_clear) is bool and physical and 0 <= CS.vEgo <= 0.1 and
        lower <= 0 <= upper and min(target, upper) >= 0.75 and
        (stock_hold_allowed or not CS.cruiseState.standstill))
    except (TypeError, ValueError, OverflowError):
      return False
