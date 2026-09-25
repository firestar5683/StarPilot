"""Pure composition of source, acceptance, offset, override and lead SLC decisions."""

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace

from openpilot.starpilot.longitudinal.cruise_ceiling import CruiseCeiling
from openpilot.starpilot.speed_limits import acceptance as acc
from openpilot.starpilot.speed_limits import action_arbitration as arb
from openpilot.starpilot.speed_limits import lead_relaxation as lr
from openpilot.starpilot.speed_limits import overrides as ov
from openpilot.starpilot.speed_limits import selection as sel
from openpilot.starpilot.speed_limits import speed_domain as sd


@dataclass(frozen=True)
class HostState:
  system_long_available: bool
  long_control_active: bool
  selfdrive_enabled: bool
  force_decel: bool
  force_stop_active: bool
  driver_v_cruise_kph: float
  selected_cluster_kph: float | None


@dataclass(frozen=True)
class Frame:
  now_ns: int
  observations: Mapping[sel.Source, acc.Observation]
  selection_policy: sel.SelectionPolicy
  authority: acc.Authority
  acceptance_policy: acc.Policy
  offset_schedule: sd.OffsetSchedule
  selected_kind: sd.DomainStatus
  ego_pair: sd.SpeedPair
  pedal_pressed: bool | None
  lead: lr.LeadEvidence
  lead_policy: lr.Policy
  host: HostState
  action: acc.DriverAction | None = None
  adopt: acc.AdoptRequest | None = None
  classified_cruise: arb.Result | None = None


@dataclass(frozen=True)
class State:
  session_id: str
  acceptance: acc.State
  override: ov.State
  lead_prior: lr.PriorApplied | None = None
  control_generation: int = 0
  last_now_ns: int | None = None
  previous_mode: acc.Mode | None = None
  previous_owner: acc.LongitudinalOwner | None = None
  was_active_path: bool = False
  reset_required: bool = False


@dataclass(frozen=True)
class Result:
  state: State
  selection: sel.Selection | None = None
  acceptance: acc.Decision | None = None
  domain: sd.DomainResolution | None = None
  override: ov.Decision | None = None
  coordinate: sd.PlannerCoordinate | None = None
  relaxation: lr.Result | None = None
  ceiling: CruiseCeiling | None = None
  status: str = "none"
  errors: tuple[str, ...] = ()


def _integer(value: object) -> bool:
  return type(value) is int and value >= 0


def _number(value: object, *, positive: bool = False) -> bool:
  if type(value) not in (int, float):
    return False
  assert isinstance(value, (int, float))
  try:
    return math.isfinite(value) and (value > 0 if positive else value >= 0)
  except OverflowError:
    return False


def _state_valid(state: object) -> bool:
  if not isinstance(state, State) or not isinstance(state.acceptance, acc.State) or not isinstance(state.override, ov.State):
    return False
  if (type(state.session_id) is not str or not state.session_id or state.acceptance.session_id != state.session_id or
      state.override.session_id != state.session_id or not _integer(state.control_generation) or
      (state.last_now_ns is not None and not _integer(state.last_now_ns)) or
      type(state.was_active_path) is not bool or type(state.reset_required) is not bool):
    return False
  if ((state.previous_mode is None) != (state.previous_owner is None) or
      (state.previous_mode is not None and not isinstance(state.previous_mode, acc.Mode)) or
      (state.previous_owner is not None and not isinstance(state.previous_owner, acc.LongitudinalOwner))):
    return False
  return state.lead_prior is None or (isinstance(state.lead_prior, lr.PriorApplied) and
                                      state.lead_prior.session_id == state.session_id and
                                      state.lead_prior.continuity_id == f"control:{state.control_generation}" and
                                      _number(state.lead_prior.cap_mps, positive=True))


def _host_valid(host: object) -> bool:
  return (isinstance(host, HostState) and
          all(type(value) is bool for value in (host.system_long_available, host.long_control_active,
                                                host.selfdrive_enabled, host.force_decel, host.force_stop_active)) and
          _number(host.driver_v_cruise_kph) and
          (host.selected_cluster_kph is None or _number(host.selected_cluster_kph)))


def _override_evidence(kind: sd.DomainStatus) -> ov.EvidenceKind:
  return {sd.DomainStatus.VALID: ov.EvidenceKind.VALID,
          sd.DomainStatus.ABSENT: ov.EvidenceKind.ABSENT,
          sd.DomainStatus.STALE: ov.EvidenceKind.STALE}.get(kind, ov.EvidenceKind.UNKNOWN)


def new_session(session_id: str, qualified_history: acc.AcceptedLimit | None = None) -> State:
  return State(session_id, acc.new_session(session_id, qualified_history), ov.new_session(session_id))


def step(state: State, frame: Frame) -> Result:
  if not _state_valid(state):
    return Result(state, status="invalid_state", errors=("invalid composition state",))
  if state.reset_required:
    return Result(state, status="session_reset_required", errors=("new session required",))
  if (not isinstance(frame, Frame) or not _integer(frame.now_ns) or
      (state.last_now_ns is not None and frame.now_ns < state.last_now_ns) or
      not _host_valid(frame.host) or not acc.authority_is_valid(frame.authority) or
      not isinstance(frame.acceptance_policy, acc.Policy) or
      any(type(value) is not bool for value in (frame.acceptance_policy.confirm_lower,
                                                frame.acceptance_policy.confirm_higher,
                                                frame.acceptance_policy.fallback_previous,
                                                frame.acceptance_policy.display_only,
                                                frame.acceptance_policy.vision_driver_confirm)) or
      not isinstance(frame.selected_kind, sd.DomainStatus) or not isinstance(frame.ego_pair, sd.SpeedPair) or
      not isinstance(frame.lead, lr.LeadEvidence)):
    return Result(replace(state, lead_prior=None, reset_required=True), status="invalid_frame", errors=("invalid frame or clock",))
  host = frame.host
  selected_initialized = host.driver_v_cruise_kph > 0 and host.driver_v_cruise_kph != 255.0
  host_long = host.system_long_available and host.long_control_active and host.selfdrive_enabled
  system_mode = frame.authority.mode in (acc.Mode.LONGITUDINAL_ONLY, acc.Mode.COMBINED) and frame.authority.owner is acc.LongitudinalOwner.SYSTEM
  if system_mode and frame.authority.longitudinal_active != host_long:
    return Result(replace(state, lead_prior=None, last_now_ns=frame.now_ns, reset_required=True),
                  status="host_authority_disagreement", errors=("host and system-long authority disagree",))
  active_path = (frame.authority.can_control and host_long and selected_initialized and
                 not host.force_decel and not host.force_stop_active and not frame.acceptance_policy.display_only)
  mode_changed = state.previous_mode is not None and (state.previous_mode != frame.authority.mode or
                                                       state.previous_owner != frame.authority.owner)
  generation = state.control_generation + int(active_path and (not state.was_active_path or mode_changed))
  prior = state.lead_prior if active_path and state.was_active_path and not mode_changed else None
  elapsed_s = 0.0 if state.last_now_ns is None else (frame.now_ns - state.last_now_ns) / 1e9
  base = replace(state, control_generation=generation, lead_prior=prior, last_now_ns=frame.now_ns,
                 previous_mode=frame.authority.mode, previous_owner=frame.authority.owner, was_active_path=active_path)

  if frame.classified_cruise is not None:
    classified = frame.classified_cruise
    if (not isinstance(classified, arb.Result) or classified.errors or not isinstance(classified.state, arb.Ledger) or
        not isinstance(classified.change, arb.ClassifiedChange) or classified.state.session_id != state.session_id or
        classified.change.session_id != state.session_id or classified.state.reset_required or
        classified.state.last_timestamp_ns != frame.now_ns or
        classified.state.last_effect_id != classified.change.effect_id or
        not isinstance(classified.change.disposition, arb.Disposition) or
        classified.status != classified.change.disposition.value or frame.action is not None or frame.adopt is not None):
      return Result(replace(base, lead_prior=None, reset_required=True), status="invalid_ledger_result",
                    errors=("invalid, stale or ambiguous causal ledger result",))
  selected = sel.select_limit(frame.observations, frame.selection_policy)
  if selected.errors:
    return Result(replace(base, lead_prior=None, reset_required=True), selection=selected, status="invalid_selection", errors=selected.errors)
  acceptance = acc.step(base.acceptance, selected.observation, frame.authority, frame.acceptance_policy,
                        now_ns=frame.now_ns, action=frame.action, adopt=frame.adopt)
  base = replace(base, acceptance=acceptance.state)
  if acceptance.errors:
    return Result(replace(base, lead_prior=None, reset_required=True), selected, acceptance,
                  status="invalid_acceptance", errors=acceptance.errors)

  # The raw selected set speed is derived solely from the actual driver vCruise kph.
  if frame.selected_kind is sd.DomainStatus.VALID and selected_initialized and host.selected_cluster_kph is not None:
    pair = sd.selected_pair_from_kph(host.driver_v_cruise_kph / 3.6, host.selected_cluster_kph,
                                     session_id=state.session_id, timestamp_ns=frame.now_ns)
  elif selected_initialized:
    pair = sd.SpeedPair(frame.selected_kind)
  else:
    pair = sd.SpeedPair(sd.DomainStatus.ABSENT)
  domain = sd.resolve(acceptance, frame.offset_schedule, pair, frame.ego_pair)
  selected_evidence = ov.SelectedEvidence(_override_evidence(pair.status), pair.raw_mps if pair.status is sd.DomainStatus.VALID else None)
  pedal_evidence = ov.PedalEvidence(_override_evidence(frame.ego_pair.status),
                                    frame.pedal_pressed if frame.ego_pair.status is sd.DomainStatus.VALID else None,
                                    frame.ego_pair.raw_mps if frame.ego_pair.status is sd.DomainStatus.VALID else None)
  change = frame.classified_cruise.change if frame.classified_cruise is not None else None
  override = ov.step(base.override, acceptance, frame.authority, frame.acceptance_policy,
                     selected_evidence, pedal_evidence, now_ns=frame.now_ns, change=change, domain=domain)
  base = replace(base, override=override.state)
  if override.errors or domain.status is sd.DomainStatus.INVALID:
    return Result(replace(base, lead_prior=None, reset_required=True), selected, acceptance, domain, override,
                  status="invalid_domain_or_override", errors=override.errors or (domain.reason,))
  if not active_path or domain.status is not sd.DomainStatus.VALID:
    return Result(replace(base, lead_prior=None), selected, acceptance, domain, override, status="inactive_or_unavailable")
  context = domain.context
  if (not isinstance(context, sd.DomainContext) or override.state.session_id != state.session_id or
      override.state.last_timestamp_ns != frame.now_ns or override.state.accepted_mps != context.accepted_raw_mps or
      override.state.effective_target_mps != context.effective_cluster_mps):
    return Result(replace(base, lead_prior=None, reset_required=True), selected, acceptance, domain, override,
                  status="invalid_join", errors=("override and speed domain mismatch",))
  coordinate = sd.to_planner_coordinate(context, override.contribution_mps, override.basis)
  if coordinate.cap_mps is None:
    return Result(replace(base, lead_prior=None, reset_required=True), selected, acceptance, domain, override, coordinate,
                  status="invalid_coordinate", errors=("planner coordinate unavailable",))
  source = lr.SourceEvidence(acceptance.state.observation.kind, True)
  relaxation = lr.step(coordinate.cap_mps, source=source, lead=frame.lead, prior=prior,
                       session_id=state.session_id, continuity_id=f"control:{generation}", ego_mps=context.ego_raw_mps,
                       override_active=override.contribution_mps is not None, active_path=True,
                       elapsed_s=elapsed_s, policy=frame.lead_policy)
  base = replace(base, lead_prior=relaxation.next_prior)
  if relaxation.errors or relaxation.cap_mps is None:
    return Result(base, selected, acceptance, domain, override, coordinate, relaxation,
                  status="invalid_relaxation" if relaxation.errors else "no_cap", errors=relaxation.errors)
  return Result(base, selected, acceptance, domain, override, coordinate, relaxation,
                CruiseCeiling(relaxation.cap_mps, frame.authority), "ceiling")
