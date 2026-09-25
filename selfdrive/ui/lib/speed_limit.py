from openpilot.common.constants import CV
from openpilot.starpilot.common.speed_limit import get_speed_limit_offset


def speed_limit_override_mode(plan, gas_pressed: bool) -> str:
  if getattr(plan, "slcOverriddenSpeed", 0.0) > 0.0:
    return "pedal" if gas_pressed else "manual"
  return ""


def speed_limit_confirmation_pending(plan) -> bool:
  return bool(
    getattr(plan, "speedLimitChanged", False) and
    getattr(plan, "unconfirmedSlcSpeedLimit", 0.0) > 1.0
  )


def max_matches_speed_limit(plan, max_speed_kph: float, is_metric: bool, fallback_mode: int) -> bool:
  limit_ms = max(float(getattr(plan, "slcSpeedLimit", 0.0)), 0.0)
  target_ms = limit_ms + float(getattr(plan, "slcSpeedLimitOffset", 0.0)) if limit_ms > 0.0 else 0.0
  if target_ms <= 0.0 or not 0.0 < max_speed_kph < 255.0:
    return False

  source = getattr(plan, "slcSpeedLimitSource", "None") or "None"
  if speed_limit_confirmation_pending(plan):
    return False

  overridden = getattr(plan, "slcOverriddenSpeed", 0.0) > 0.0
  if source == "None" and not overridden and fallback_mode not in (0, 2):
    return False

  conversion = CV.MS_TO_KPH if is_metric else CV.MS_TO_MPH
  max_ms = max_speed_kph * CV.KPH_TO_MS
  return round(max_ms * conversion) == round(target_ms * conversion)


def pending_speed_limit_offset(limit_ms: float, is_metric: bool, toggles) -> float:
  """Return the configured offset for a pending limit, in m/s."""
  if limit_ms <= 0:
    return 0.0

  offsets = tuple(float(toggles.get(f"speed_limit_offset{index}", 0.0)) for index in range(1, 8))
  return get_speed_limit_offset(limit_ms, is_metric, offsets)
