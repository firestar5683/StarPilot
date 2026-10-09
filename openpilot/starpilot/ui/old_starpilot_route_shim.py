"""Display historical starpilotPlan messages during replay.

Event @113 is received as customReserved6 using its frozen Cap'n Proto layout.
Activity is inferred from the restored SLC setting, target and MAX; no session
or decision IDs are invented, so historical observations cannot enable actions.

Retirement: remove the marked runtime_snapshot import/call, this module, and
test_legacy_slc_is_replay_only_display_fallback in tests/test_runtime_snapshot.py.
Remove the customReserved6 replay subscription in selfdrive/ui/ui_state.py and
its cereal/services.py registration; regenerate cereal/services.h. Empty the
CustomReserved6 struct in cereal/custom.capnp, preserving its type ID and the
reserved Event @113 slot in cereal/log.capnp for wire compatibility.
"""

import math

from openpilot.starpilot.ui.onroad_state import ObservationKind, SpeedLimitObservation


def _speed(value, *, positive=False):
  try:
    value = float(value)
  except (TypeError, ValueError, OverflowError):
    return None
  return value if math.isfinite(value) and (value > 0 if positive else value >= 0) else None


def speed_limit_fallback(ui, observation, now_ns, *, cruise_kph, car, read_message):
  """Keep modern observations; adapt only fresh historical replay messages."""
  if getattr(ui, 'replay_sample', None) is None or not ui.started or observation.kind == ObservationKind.VALID:
    return observation
  legacy = read_message(ui.sm, 'customReserved6', now_ns, after_frame=ui.started_frame)
  limit = _speed(legacy.slcSpeedLimit, positive=True) if legacy is not None else None
  if limit is None:
    return observation
  offset = _speed(legacy.slcSpeedLimitOffset)
  target = _speed(limit + (offset or 0.0), positive=True)
  try:
    enabled = bool(ui.params.get_bool('SpeedLimitController'))
  except (KeyError, OSError, ValueError):
    enabled = False
  overridden = _speed(legacy.slcOverriddenSpeed, positive=True) is not None
  source = str(legacy.slcSpeedLimitSource).lower()
  return SpeedLimitObservation(
    kind=ObservationKind.VALID, speed_limit_mps=limit, offset_mps=offset,
    presentation_adjusted_limit_mps=target,
    effective_cluster_target_mps=target if enabled else None,
    action_enabled=enabled,
    limiting_max_set=bool(target is not None and cruise_kph is not None and target < cruise_kph / 3.6),
    driver_override_active=overridden,
    override_basis=('pedal' if car is not None and getattr(car, 'gasPressed', False) else 'persistent') if overridden else 'none',
    source='unknown' if source in ('', 'none') else source, status='legacy_replay',
  )
