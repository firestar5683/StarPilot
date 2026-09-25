"""Pure large-card presentation over qualified modern SLC observations.

The accepted/pending number owns its source. A selected source may belong to a
new decision and must never relabel the still-accepted sign. UI equality is only
for merging displayed numerals; control activity comes from publisher evidence.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class UnifiedSpeedPresentation:
  mode: str
  max_text: str
  posted_text: str
  offset_text: str | None
  unit: str
  source: str
  pending: bool
  active_side: str


def displayed_limit_mps(observation):
  """The sign and pulse share one qualified, positive candidate selection."""
  if str(observation.kind) != "valid":
    return None
  for value in (observation.pending_speed_limit_mps, observation.accepted_speed_limit_mps,
                observation.speed_limit_mps):
    if value is not None and math.isfinite(value) and value > 0:
      return value
  return None


def resolve_unified_speed(state) -> UnifiedSpeedPresentation:
  observation = state.speed_limit
  factor = 3.6 if state.metric else 2.2369362921
  def positive(value):
    return value is not None and math.isfinite(value) and value > 0
  def speed(value):
    return str(round(value * factor)) if positive(value) else "–"
  show_max = not state.appearance.hide_max_speed
  max_text = (str(round(state.cruise_kph if state.metric else state.cruise_kph * 0.621371))
              if positive(state.cruise_kph) else "–")
  # A stale/missing publisher cannot keep an accepted sign or a pending prompt.
  valid = str(observation.kind) == "valid"
  pending = valid and positive(observation.pending_speed_limit_mps)
  accepted = valid and positive(observation.accepted_speed_limit_mps)
  posted = displayed_limit_mps(observation)
  source = observation.pending_source if pending else observation.accepted_source if accepted else observation.source
  if source in ("", "none") and positive(posted):
    source = "unknown"
  has_limit = positive(posted)
  effective = observation.effective_cluster_target_mps
  effective_text = speed(effective)
  mode = "split" if show_max and has_limit else "limit_only" if has_limit else "max_only" if show_max else "hidden"
  if (mode == "split" and not pending and observation.action_enabled and
      positive(effective) and positive(state.cruise_kph) and max_text == effective_text):
    mode = "merged"
  active = "none"
  if state.cruise_active and not observation.driver_override_active and not state.longitudinal_overridden:
    if observation.action_enabled and observation.limiting_max_set and has_limit:
      active = "shared" if mode == "merged" else "slc"
    elif show_max:
      active = "shared" if mode == "merged" else "max"
  adjustment = observation.offset_mps
  offset = None
  if state.show_slc_offset and not pending and has_limit and adjustment is not None and math.isfinite(adjustment):
    rounded = round(adjustment * factor)
    if rounded:
      offset = f"{rounded:+d}"
  return UnifiedSpeedPresentation(mode, max_text, speed(posted), offset,
                                  "km/h" if state.metric else "mph", source if has_limit else "none", pending, active)


def large_limit_bounds(state) -> tuple[int, int, int, int]:
  """Logical sign hit bounds; customization offsets are applied by the caller."""
  mode = resolve_unified_speed(state).mode
  top = 75 if mode == "limit_only" else 271
  return (88, top, 264, top + 215)
