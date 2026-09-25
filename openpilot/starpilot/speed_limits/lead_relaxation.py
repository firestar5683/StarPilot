"""Pure easing of a qualified SLC cruise cap after a lower accepted limit."""

import math
from dataclasses import dataclass
from enum import Enum

from openpilot.starpilot.speed_limits.acceptance import ObservationKind


class LeadKind(Enum):
  VALID = "valid"
  ABSENT = "absent"
  UNKNOWN = "unknown"
  STALE = "stale"


@dataclass(frozen=True)
class SourceEvidence:
  kind: ObservationKind
  cap_qualified: bool


@dataclass(frozen=True)
class LeadEvidence:
  kind: LeadKind
  tracking: bool | None = None
  present: bool | None = None
  distance_m: float | None = None
  speed_mps: float | None = None
  accel_mps2: float | None = None


@dataclass(frozen=True)
class Policy:
  minimum_ego_mps: float
  minimum_distance_m: float
  minimum_headway_s: float
  maximum_lead_deficit_mps: float
  maximum_lead_brake_mps2: float
  drop_guard_mps: float
  overspeed_guard_mps: float
  overspeed_breakpoints_mps: tuple[float, ...]
  deceleration_mps2: tuple[float, ...]


@dataclass(frozen=True)
class PriorApplied:
  session_id: str
  continuity_id: str
  cap_mps: float


@dataclass(frozen=True)
class Result:
  cap_mps: float | None
  next_prior: PriorApplied | None
  status: str
  errors: tuple[str, ...] = ()


def _number(value: object, *, positive: bool = False, signed: bool = False) -> bool:
  if type(value) not in (int, float):
    return False
  assert isinstance(value, (int, float))
  try:
    return math.isfinite(value) and (signed or (value > 0 if positive else value >= 0))
  except OverflowError:
    return False


def _token(value: object) -> bool:
  return type(value) is str and bool(value) and len(value) <= 256 and bool(value.strip()) and not any(ord(c) < 32 for c in value)


def _policy_valid(policy: object) -> bool:
  if not isinstance(policy, Policy):
    return False
  if any(not _number(value) for value in (
    policy.minimum_ego_mps, policy.minimum_distance_m, policy.minimum_headway_s,
    policy.maximum_lead_deficit_mps, policy.maximum_lead_brake_mps2,
    policy.drop_guard_mps, policy.overspeed_guard_mps,
  )):
    return False
  bp, decel = policy.overspeed_breakpoints_mps, policy.deceleration_mps2
  if (not isinstance(bp, tuple) or not isinstance(decel, tuple) or len(bp) < 2 or len(bp) != len(decel) or
      any(not _number(v) for v in bp) or any(not _number(v, positive=True) for v in decel)):
    return False
  return all(bp[i] > bp[i - 1] for i in range(1, len(bp)))


def _lead_valid(lead: object) -> bool:
  if not isinstance(lead, LeadEvidence) or not isinstance(lead.kind, LeadKind):
    return False
  if lead.kind is not LeadKind.VALID:
    return all(value is None for value in (lead.tracking, lead.present, lead.distance_m, lead.speed_mps, lead.accel_mps2))
  return (type(lead.tracking) is bool and type(lead.present) is bool and
          _number(lead.distance_m) and _number(lead.speed_mps) and _number(lead.accel_mps2, signed=True))


def _interpolate(value: float, xs: tuple[float, ...], ys: tuple[float, ...]) -> float:
  if value <= xs[0]:
    return ys[0]
  if value >= xs[-1]:
    return ys[-1]
  for i in range(1, len(xs)):
    if value <= xs[i]:
      ratio = (value - xs[i - 1]) / (xs[i] - xs[i - 1])
      return ys[i - 1] + ratio * (ys[i] - ys[i - 1])
  return ys[-1]


def step(raw_cap_mps: float | None, *, source: SourceEvidence, lead: LeadEvidence,
         prior: PriorApplied | None, session_id: str, continuity_id: str, ego_mps: float,
         override_active: bool, active_path: bool, elapsed_s: float, policy: Policy) -> Result:
  """Ease only a qualified cap; caller owns source, lead and control continuity."""
  if not _token(session_id) or not _token(continuity_id) or not isinstance(source, SourceEvidence) or not isinstance(source.kind, ObservationKind):
    return Result(None, None, "invalid_source", ("invalid source identity",))
  if (type(source.cap_qualified) is not bool or source.kind in (ObservationKind.UNKNOWN, ObservationKind.STALE) or
      not source.cap_qualified):
    return Result(None, None, "source_unavailable")
  if type(active_path) is not bool or not active_path or raw_cap_mps is None:
    return Result(None, None, "inactive_or_absent")
  if not _number(raw_cap_mps, positive=True):
    return Result(None, None, "invalid_cap", ("invalid raw cap",))
  assert raw_cap_mps is not None
  if (not _policy_valid(policy) or not _number(ego_mps) or type(override_active) is not bool or
      not _number(elapsed_s) or not _lead_valid(lead)):
    return Result(raw_cap_mps, None, "invalid_input", ("invalid lead, policy or elapsed time",))
  if prior is not None and (not isinstance(prior, PriorApplied) or not _token(prior.session_id) or
                            not _token(prior.continuity_id) or not _number(prior.cap_mps, positive=True) or
                            prior.session_id != session_id or prior.continuity_id != continuity_id):
    return Result(raw_cap_mps, None, "invalid_prior", ("prior control continuity mismatch",))
  if override_active:
    return Result(raw_cap_mps, None, "override")
  next_prior = PriorApplied(session_id, continuity_id, raw_cap_mps)
  if source.kind is ObservationKind.ABSENT:
    return Result(raw_cap_mps, next_prior, "fallback_source")
  if lead.kind is not LeadKind.VALID:
    return Result(raw_cap_mps, next_prior, "lead_unavailable")
  assert lead.tracking is not None and lead.present is not None
  assert lead.distance_m is not None and lead.speed_mps is not None and lead.accel_mps2 is not None
  if not lead.tracking or not lead.present:
    return Result(raw_cap_mps, next_prior, "no_tracked_lead")
  if (prior is None or raw_cap_mps >= prior.cap_mps - policy.drop_guard_mps or
      ego_mps < policy.minimum_ego_mps or raw_cap_mps >= ego_mps - policy.overspeed_guard_mps):
    return Result(raw_cap_mps, next_prior, "no_eligible_drop")
  if lead.distance_m < max(policy.minimum_distance_m, ego_mps * policy.minimum_headway_s):
    return Result(raw_cap_mps, next_prior, "close_lead")
  if lead.speed_mps < raw_cap_mps - policy.maximum_lead_deficit_mps:
    return Result(raw_cap_mps, next_prior, "slow_lead")
  if max(0.0, -lead.accel_mps2) > policy.maximum_lead_brake_mps2:
    return Result(raw_cap_mps, next_prior, "braking_lead")
  decel = _interpolate(max(0.0, ego_mps - raw_cap_mps), policy.overspeed_breakpoints_mps, policy.deceleration_mps2)
  eased = max(raw_cap_mps, prior.cap_mps - decel * elapsed_s)
  return Result(eased, PriorApplied(session_id, continuity_id, eased), "eased")
