"""Stable large speed roles over publisher-qualified SLC evidence."""

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
  limit_text: str
  status: str
  proposal_text: str

  @property
  def max_status(self) -> str:
    if self.max_text == '–':
      return 'Not set'
    return {'max': 'Using set speed', 'shared': 'Matches speed limit'}.get(self.active_side, 'Your ceiling')

  @property
  def limit_status(self) -> str:
    if self.status == 'Set-speed override':
      return 'Overridden'
    if self.mode == 'split' and self.active_side == 'max' and self.status == 'Using set speed':
      # Describe the displayed relationship without changing source selection.
      if self.max_text != '–' and self.limit_text != '–':
        if int(self.limit_text) > int(self.max_text):
          return 'Above set speed'
        if self.limit_text == self.max_text:
          return 'Matches set speed'
    return self.status


def positive(value):
  return value is not None and math.isfinite(value) and value > 0


def displayed_limit_mps(observation):
  """A proposal never replaces the accepted sign."""
  if str(observation.kind) != 'valid':
    return None
  for value in (observation.accepted_speed_limit_mps, observation.speed_limit_mps):
    if positive(value):
      return value
  return None


def resolve_unified_speed(state) -> UnifiedSpeedPresentation:
  obs = state.speed_limit
  factor = 3.6 if state.metric else 2.2369362921
  def speed(value):
    return str(round(value * factor)) if positive(value) else '–'
  valid = str(obs.kind) == 'valid'
  pending = valid and positive(obs.pending_speed_limit_mps)
  accepted = valid and positive(obs.accepted_speed_limit_mps)
  posted = displayed_limit_mps(obs)
  source = (obs.accepted_source if accepted else obs.source) if valid else 'none'
  if source in ('', 'none'):
    source = 'unknown' if positive(posted) else 'none'
  show_max = not state.appearance.hide_max_speed
  has_slc = valid or str(obs.kind) == 'stale'
  mode = 'split' if show_max and has_slc else 'limit_only' if has_slc else 'max_only' if show_max else 'hidden'
  target = None
  if valid:
    candidates = (getattr(obs, 'accepted_adjusted_limit_mps', None), obs.effective_cluster_target_mps)
    if not accepted and not pending:
      candidates += (getattr(obs, 'presentation_adjusted_limit_mps', None),)
    target = next((value for value in candidates if positive(value)), None)
  offset = None
  if state.show_slc_offset and positive(target) and positive(posted):
    adjustment = round((target - posted) * factor)
    if adjustment:
      offset = f'{adjustment:+d}'
  active = 'none'
  status = 'Unavailable'
  if valid:
    status = 'Override saved' if getattr(obs, 'retained_override', False) else 'Cruise off'
    if getattr(obs, 'status', '') == 'display_hold':
      status = 'Unavailable'
    elif not obs.action_enabled:
      status = 'Display only'
    elif state.longitudinal_overridden:
      status = 'Using accelerator'
    elif obs.driver_override_active:
      status = {'pedal': 'Using accelerator', 'persistent': 'Set-speed override'}.get(getattr(obs, 'override_basis', ''), 'Override')
      if (getattr(obs, 'override_basis', '') == 'persistent' and state.cruise_active and
          positive(state.cruise_kph) and positive(obs.effective_cluster_target_mps)):
        # A qualified set-speed override selects MAX; pedal control does not.
        active = 'max'
    elif state.cruise_active and positive(obs.effective_cluster_target_mps):
      active = 'slc' if obs.limiting_max_set else 'max'
      if positive(target) and positive(state.cruise_kph):
        max_mps = state.cruise_kph / 3.6
        # Compare cluster ceilings before display rounding. 1 mm/s allows for
        # Float32 transport noise without treating visibly rounded ties as shared.
        if math.isclose(target, max_mps, rel_tol=0, abs_tol=0.001):
          active = 'shared'
        else:
          active = 'slc' if target < max_mps else 'max'
      status = {'slc': 'Using speed limit', 'max': 'Using set speed', 'shared': 'Matches set speed'}[active]
    elif state.cruise_active:
      status = 'Unavailable'
  max_text = str(round(state.cruise_kph * (1 if state.metric else .621371))) if positive(state.cruise_kph) else '–'
  return UnifiedSpeedPresentation(mode, max_text, speed(posted), offset, 'km/h' if state.metric else 'mph',
                                  source, pending, active, speed(target), status,
                                  speed(obs.pending_speed_limit_mps) if pending else '–')
