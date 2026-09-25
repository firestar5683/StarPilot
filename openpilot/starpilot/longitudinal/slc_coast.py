"""Frozen named-profile SLC coast preference for the cruise candidate only."""

import math

from openpilot.starpilot.longitudinal.accel_profile import akima_interp

_WINDOW_BP = (0.0, 10.0, 20.0, 35.0)
_WINDOW = (0.20, 0.40, 0.65, 1.10)
_EXCESS = (0.8, 1.8, 3.5, 5.5)
_STYLE = {
  'eco': (1.20, -0.02),
  'standard': (1.00, -0.03),
  'sport': (0.75, -0.04),
}


def braking_lead_relevant(lead: object, v_ego: float) -> bool:
  if not getattr(lead, 'present', False):
    return False
  try:
    lead_speed = float(lead.vLead)
    lead_accel = float(lead.aLeadK)
    distance = float(lead.dRel)
  except (AttributeError, TypeError, ValueError, OverflowError):
    return True
  if not all(math.isfinite(value) for value in (v_ego, lead_speed, lead_accel, distance)):
    return True
  return v_ego - lead_speed > 0.5 or lead_accel < -0.4 or distance < max(18.0, 2.0 * v_ego)


def slc_coast_floor(*, v_ego: float, slc_target: float | None, driver_cruise: float,
                    full_brake_floor: float, relevant_lead: bool, stop_context: bool,
                    braking_style: str = 'standard') -> float | None:
  """Return a cruise-only brake floor; None preserves the ordinary planner."""
  if (slc_target is None or type(braking_style) is not str or braking_style not in _STYLE or
      any(type(flag) is not bool for flag in (relevant_lead, stop_context)) or
      not all(type(value) in (int, float) and math.isfinite(value)
              for value in (v_ego, slc_target, driver_cruise, full_brake_floor)) or
      slc_target <= 0.0 or v_ego <= 4.0 or v_ego <= slc_target + 0.05 or
      slc_target >= driver_cruise - 0.15 or relevant_lead or stop_context or
      not -3.5 <= full_brake_floor < 0.0):
    return None

  window_multiplier, coast_floor = _STYLE[braking_style]
  coast_window = akima_interp(v_ego, _WINDOW_BP, _WINDOW) * window_multiplier
  excess_scale = max(akima_interp(v_ego, _WINDOW_BP, _EXCESS), coast_window + 0.1)
  excess = max(0.0, v_ego - slc_target)
  if excess <= coast_window:
    return max(full_brake_floor, coast_floor)
  t = min(max((excess - coast_window) / (excess_scale - coast_window), 0.0), 1.0) ** 2
  return max(full_brake_floor, coast_floor + t * (full_brake_floor - coast_floor))
