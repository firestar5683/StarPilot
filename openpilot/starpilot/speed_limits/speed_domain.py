"""Pure offset selection and qualified raw/cluster coordinate conversion for SLC."""

import math
from dataclasses import dataclass
from enum import Enum

from openpilot.starpilot.speed_limits import acceptance as acc


class DomainStatus(Enum):
  VALID = "valid"
  ABSENT = "absent"
  UNKNOWN = "unknown"
  STALE = "stale"
  UNAVAILABLE = "unavailable"
  INVALID = "invalid"


@dataclass(frozen=True)
class SpeedPair:
  status: DomainStatus
  raw_mps: float | None = None
  cluster_mps: float | None = None
  session_id: str | None = None
  timestamp_ns: int | None = None


@dataclass(frozen=True)
class OffsetBand:
  lower_mps: float
  upper_mps: float | None
  offset_mps: float


@dataclass(frozen=True)
class OffsetSchedule:
  bands: tuple[OffsetBand, ...]


@dataclass(frozen=True)
class DomainContext:
  session_id: str
  timestamp_ns: int
  accepted_raw_mps: float
  offset_mps: float
  effective_cluster_mps: float
  selected_raw_mps: float
  selected_delta_mps: float
  ego_raw_mps: float
  ego_delta_mps: float


@dataclass(frozen=True)
class DomainResolution:
  status: DomainStatus
  context: DomainContext | None = None
  reason: str = ""


@dataclass(frozen=True)
class PlannerCoordinate:
  cap_mps: float | None
  basis: str
  cluster_target_mps: float | None = None
  ego_delta_mps: float | None = None


def _number(value: object, *, positive: bool = False) -> bool:
  if type(value) not in (int, float):
    return False
  assert isinstance(value, (int, float))
  try:
    return math.isfinite(value) and (value > 0 if positive else value >= 0)
  except OverflowError:
    return False


def _signed_number(value: object) -> bool:
  if type(value) not in (int, float):
    return False
  assert isinstance(value, (int, float))
  try:
    return math.isfinite(value)
  except OverflowError:
    return False


def _pair_valid(pair: object, *, positive_raw: bool) -> bool:
  if not isinstance(pair, SpeedPair) or not isinstance(pair.status, DomainStatus):
    return False
  if pair.status is not DomainStatus.VALID:
    return pair.raw_mps is None and pair.cluster_mps is None
  return (_number(pair.raw_mps, positive=positive_raw) and _number(pair.cluster_mps) and
          pair.cluster_mps is not None and pair.raw_mps is not None and
          type(pair.session_id) is str and bool(pair.session_id) and
          type(pair.timestamp_ns) is int and pair.timestamp_ns >= 0)


def selected_pair_from_kph(raw_mps: float, cluster_kph: float, *, session_id: str, timestamp_ns: int) -> SpeedPair:
  """Convert a qualified dashboard-selected cluster value from km/h to m/s."""
  if not _number(raw_mps, positive=True) or not _number(cluster_kph):
    return SpeedPair(DomainStatus.INVALID)
  return SpeedPair(DomainStatus.VALID, raw_mps, cluster_kph / 3.6, session_id, timestamp_ns)


def context_is_valid(context: object) -> bool:
  if not isinstance(context, DomainContext):
    return False
  return (type(context.session_id) is str and bool(context.session_id) and type(context.timestamp_ns) is int and
          context.timestamp_ns >= 0 and _number(context.accepted_raw_mps, positive=True) and
          _signed_number(context.offset_mps) and _number(context.effective_cluster_mps, positive=True) and
          context.effective_cluster_mps == context.accepted_raw_mps + context.offset_mps and
          _number(context.selected_raw_mps, positive=True) and _number(context.selected_delta_mps) and
          _number(context.ego_raw_mps) and _number(context.ego_delta_mps))


def _schedule_valid(schedule: object) -> bool:
  if not isinstance(schedule, OffsetSchedule) or not isinstance(schedule.bands, tuple) or not schedule.bands:
    return False
  previous_upper = None
  for i, band in enumerate(schedule.bands):
    if not isinstance(band, OffsetBand) or not _number(band.lower_mps) or not _signed_number(band.offset_mps):
      return False
    if band.upper_mps is not None and (not _number(band.upper_mps, positive=True) or band.upper_mps <= band.lower_mps):
      return False
    if i and (previous_upper is None or band.lower_mps < previous_upper):
      return False
    previous_upper = band.upper_mps
  return True


def offset_for_limit(speed_mps: float, schedule: OffsetSchedule) -> float | None:
  if not _number(speed_mps, positive=True) or not _schedule_valid(schedule):
    return None
  for band in schedule.bands:
    if band.lower_mps <= speed_mps and (band.upper_mps is None or speed_mps < band.upper_mps):
      return band.offset_mps
  return None


def adjusted_limit(speed_mps: float, schedule: OffsetSchedule) -> float | None:
  """Informational cluster limit using the same validated bands as control."""
  offset = offset_for_limit(speed_mps, schedule)
  if offset is None:
    return None
  value = speed_mps + offset
  return value if _number(value, positive=True) else None


def resolve(decision: acc.Decision, schedule: OffsetSchedule, selected: SpeedPair, ego: SpeedPair) -> DomainResolution:
  """Bind an explicit offset and contemporaneous speed pairs to an acceptance output."""
  if (not isinstance(decision, acc.Decision) or not isinstance(decision.state, acc.State) or decision.errors or
      not _schedule_valid(schedule) or not _pair_valid(selected, positive_raw=True) or
      not _pair_valid(ego, positive_raw=False) or
      type(decision.state.session_id) is not str or not decision.state.session_id or
      type(decision.state.last_timestamp_ns) is not int or decision.state.last_timestamp_ns < 0 or
      not isinstance(decision.authority, acc.Authority) or
      not acc.authority_is_valid(decision.authority) or not isinstance(decision.policy, acc.Policy) or
      any(type(value) is not bool for value in (decision.policy.confirm_lower, decision.policy.confirm_higher,
                                                decision.policy.fallback_previous, decision.policy.display_only)) or
      not acc.observation_is_valid(decision.state.observation, session_id=decision.state.session_id)):
    return DomainResolution(DomainStatus.INVALID, reason="invalid acceptance, schedule or speed pair")
  accepted = decision.state.accepted
  if accepted is not None and (not isinstance(accepted, acc.AcceptedLimit) or
                               type(accepted.session_id) is not str or not accepted.session_id or
                               type(accepted.accepted_at_ns) is not int or accepted.accepted_at_ns < 0 or
                               not acc.observation_is_valid(acc.Observation(acc.ObservationKind.VALID, accepted.candidate),
                                                            session_id=decision.state.session_id)):
    return DomainResolution(DomainStatus.INVALID, reason="invalid accepted limit")
  if selected.status is DomainStatus.INVALID or ego.status is DomainStatus.INVALID:
    return DomainResolution(DomainStatus.INVALID, reason="invalid speed coordinate")
  if ((selected.status is DomainStatus.VALID and (selected.session_id != decision.state.session_id or
                                                 selected.timestamp_ns != decision.state.last_timestamp_ns)) or
      (ego.status is DomainStatus.VALID and (ego.session_id != decision.state.session_id or
                                           ego.timestamp_ns != decision.state.last_timestamp_ns))):
    return DomainResolution(DomainStatus.INVALID, reason="speed pair session or timestamp mismatch")
  if decision.control_target_mps is None or selected.status is not DomainStatus.VALID or ego.status is not DomainStatus.VALID:
    return DomainResolution(DomainStatus.UNAVAILABLE, reason="target or coordinate evidence unavailable")
  target = decision.control_target_mps
  if (not _number(target, positive=True) or accepted is None or
      accepted.candidate.speed_mps != target or not decision.authority.can_control or
      decision.policy.display_only or
      decision.state.observation.kind in (acc.ObservationKind.UNKNOWN, acc.ObservationKind.STALE) or
      (decision.state.observation.kind is acc.ObservationKind.ABSENT and
       (not decision.policy.fallback_previous or decision.basis != "previous_accepted"))):
    return DomainResolution(DomainStatus.INVALID, reason="accepted target mismatch")
  assert selected.raw_mps is not None and selected.cluster_mps is not None
  assert ego.raw_mps is not None and ego.cluster_mps is not None
  offset = offset_for_limit(target, schedule)
  if offset is None:
    return DomainResolution(DomainStatus.UNAVAILABLE, reason="no configured offset band")
  effective = target + offset
  if not _number(effective, positive=True):
    return DomainResolution(DomainStatus.INVALID, reason="nonpositive effective target")
  return DomainResolution(DomainStatus.VALID, DomainContext(
    decision.state.session_id, decision.state.last_timestamp_ns, target, offset, effective,
    selected.raw_mps, max(0.0, selected.cluster_mps - selected.raw_mps),
    ego.raw_mps, max(0.0, ego.cluster_mps - ego.raw_mps)))


def to_planner_coordinate(context: DomainContext, contribution_raw_mps: float | None, basis: str) -> PlannerCoordinate:
  """Apply a raw override in cluster space, then remove the ego delta exactly once."""
  if (not context_is_valid(context) or basis not in ("none", "adoption_clear", "pedal", "persistent") or
      (basis in ("none", "adoption_clear")) != (contribution_raw_mps is None)):
    return PlannerCoordinate(None, "invalid")
  if contribution_raw_mps is not None and not _number(contribution_raw_mps, positive=True):
    return PlannerCoordinate(None, "invalid")
  cluster_target = context.effective_cluster_mps
  if basis == "pedal":
    if contribution_raw_mps != context.ego_raw_mps:
      return PlannerCoordinate(None, "invalid")
    cluster_target = max(cluster_target, context.ego_raw_mps + context.ego_delta_mps)
  elif basis == "persistent":
    assert contribution_raw_mps is not None
    cluster_target = max(cluster_target, contribution_raw_mps + context.selected_delta_mps)
  cap = cluster_target - context.ego_delta_mps
  if not _number(cap, positive=True):
    return PlannerCoordinate(None, "nonpositive", cluster_target, context.ego_delta_mps)
  return PlannerCoordinate(cap, basis, cluster_target, context.ego_delta_mps)
