"""Displayed Max Set and posted-limit values for the Big UI speed card."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UnifiedSpeedPresentation:
  mode: str
  max_speed_text: str
  posted_speed_text: str
  effective_speed_text: str
  offset_text: str | None
  unit_text: str
  source: str
  confirmation_pending: bool
  active_side: str


def resolve_unified_speed(show_max: bool, cruise_set: bool, max_speed: float,
                          slc_state: dict | None, slc_enabled: bool, is_metric: bool) -> UnifiedSpeedPresentation:
  """Compare the rounded values the driver sees; ignore override speed for layout."""
  unit = "km/h" if is_metric else "mph"
  max_text = str(round(max_speed)) if cruise_set else "–"
  posted_text = effective_text = "–"
  offset_text = None
  source = "None"
  pending = has_limit = slc_is_limiting = False
  if slc_state is not None:
    conversion = slc_state['speed_conversion']
    accepted = slc_state['accepted_speed_limit_ms']
    pending = bool(slc_state['speed_limit_changed'] and slc_state['unconfirmed_valid'])
    source = slc_state['presented_source']
    has_limit = (source not in ("", "None") and accepted > 1) or pending
    if has_limit:
      posted_text = str(round(slc_state['unconfirmed_speed_limit'])) if pending else str(round(accepted * conversion))
      effective = slc_state['effective_target_ms']
      slc_is_limiting = slc_state['slc_is_limiting_max_set']
      if slc_is_limiting is None:
        slc_is_limiting = cruise_set and accepted > 1 and 0 < effective * conversion < max_speed
      effective_text = str(round(effective * conversion)) if effective > 0 else "–"
      offset_display = round(slc_state['offset_ms'] * conversion)
      offset_text = f"{offset_display:+d}" if offset_display else None
    else:
      source = "None"

  # Max-only is valid only when SLC is disabled.
  if pending:
    mode = "split"
  elif slc_enabled:
    mode = "merged" if show_max and cruise_set and has_limit and max_text == effective_text else "split" if show_max else "limit_only"
  elif has_limit:
    mode = "split" if show_max else "limit_only"
  else:
    mode = "max_only"

  active_side = "none" if slc_state is not None and slc_state['slc_overridden_speed'] else "shared" if mode == "merged" else (
    "slc" if slc_enabled and cruise_set and slc_is_limiting else
    "max" if (show_max or pending) and cruise_set else "none"
  )
  return UnifiedSpeedPresentation(mode, max_text, posted_text, effective_text, offset_text, unit, source, pending, active_side)
