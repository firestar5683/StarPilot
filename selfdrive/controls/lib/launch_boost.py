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
