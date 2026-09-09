"""Shape only the extra model-trajectory launch request, before safety caps."""
import math


class LaunchBoost:
  # Fraction of the difference between normal planning and the launch request.
  FRACTIONS = {"low": 1.0 / 3.0, "medium": 2.0 / 3.0}
  # Limit increases in the extra contribution, in m/s^3. Reductions are immediate
  # so smoothing never holds acceleration above a newly reduced request.
  RISE_RATES = {"low": 0.5, "medium": 1.0}

  def __init__(self):
    self.extra = 0.0

  def update(self, target, launch_accel, level, allowed, dt):
    if not allowed or launch_accel is None or level == "off":
      self.extra = 0.0
      return target
    if not math.isfinite(target) or not math.isfinite(launch_accel):
      self.extra = 0.0
      return target
    if level == "high":
      # Exact legacy behaviour, including the existing vehicle/stop gates.
      self.extra = 0.0
      return max(target, launch_accel)
    if level not in self.FRACTIONS or not math.isfinite(dt) or dt <= 0.0:
      self.extra = 0.0
      return target
    requested_extra = max(0.0, launch_accel - target) * self.FRACTIONS[level]
    self.extra = min(requested_extra, self.extra + self.RISE_RATES[level] * min(dt, 0.1))
    return target + self.extra


class LaunchLeadGate:
  """Withhold extra launch acceleration only for a nearby, slowly accelerating or braking lead.

  Hysteresis prevents repeated toggling around either boundary. No reported lead
  clears this comfort restriction; normal planner safety gates still apply.
  """
  BLOCK_DISTANCE = 12.0  # m
  RELEASE_DISTANCE = 13.0  # m
  BLOCK_ACCEL = 0.5  # m/s^2, filtered lead acceleration
  RELEASE_ACCEL = 0.6  # m/s^2

  def __init__(self):
    self.blocked = False

  def reset(self):
    self.blocked = False

  def allows(self, leads):
    present = [lead for lead in leads if bool(getattr(lead, "status", False))]
    if not present:
      self.reset()
      return True
    try:
      gaps = [float(lead.dRel) for lead in present]
      if not all(math.isfinite(gap) and gap >= 0 for gap in gaps):
        return False
      gap = min(gaps)
      # A distant lead cannot introduce this extra comfort veto.
      if gap >= self.RELEASE_DISTANCE:
        self.reset()
        return True
      accel = float(present[gaps.index(gap)].aLeadK)
      if not math.isfinite(accel):
        return False
      if self.blocked:
        if accel >= self.RELEASE_ACCEL:
          self.reset()
      elif gap < self.BLOCK_DISTANCE and accel < self.BLOCK_ACCEL:
        self.blocked = True
      return not self.blocked
    except (AttributeError, TypeError, ValueError, OverflowError):
      return False
