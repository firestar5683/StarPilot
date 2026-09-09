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


# Conservative eligibility for the extra boost, not ordinary stop release.
LAUNCH_LEAD_GAP_MARGIN = 0.5  # metres beyond the normal standstill gap
LAUNCH_LEAD_MIN_SPEED = 0.5  # m/s
LAUNCH_LEAD_MIN_OPENING_SPEED = 0.25  # m/s
LAUNCH_LEAD_MIN_ACCEL = 0.3  # m/s^2, filtered lead acceleration
LAUNCH_LEAD_MIN_PROB = 0.85
LAUNCH_LEAD_MAX_LATERAL = 1.75  # metres


def lead_allows_launch_boost(leads, ego_speed, stop_distance):
  """Require the nearest reported lead to be clear of the gap and pulling away.

  Unknown/malformed lead data withholds only this optional extra acceleration.
  A farther accelerating lead must not authorize boost past a nearer slow lead.
  """
  present = [lead for lead in leads if bool(getattr(lead, "status", False))]
  if not present:
    return False
  try:
    gaps = [float(lead.dRel) for lead in present]
    if not all(math.isfinite(gap) and gap > 0 for gap in gaps):
      return False
    lead = present[gaps.index(min(gaps))]
    speed, accel, lateral = float(lead.vLead), float(lead.aLeadK), float(lead.yRel)
    probability = float(getattr(lead, "modelProb", 0.0))
    ego_speed, stop_distance = float(ego_speed), float(stop_distance)
    if not all(math.isfinite(value) for value in (speed, accel, lateral, probability, ego_speed, stop_distance)):
      return False
    return bool(
      ego_speed >= 0 and stop_distance >= 0 and
      (bool(getattr(lead, "radar", False)) or probability >= LAUNCH_LEAD_MIN_PROB) and
      abs(lateral) <= LAUNCH_LEAD_MAX_LATERAL and
      min(gaps) >= stop_distance + LAUNCH_LEAD_GAP_MARGIN and
      speed >= LAUNCH_LEAD_MIN_SPEED and
      speed - ego_speed >= LAUNCH_LEAD_MIN_OPENING_SPEED and
      accel >= LAUNCH_LEAD_MIN_ACCEL
    )
  except (AttributeError, TypeError, ValueError, OverflowError):
    return False
