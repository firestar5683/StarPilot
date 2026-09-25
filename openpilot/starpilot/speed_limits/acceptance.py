"""Immutable acceptance decisions with explicit authority and no runtime I/O."""

import math
from dataclasses import dataclass, replace
from enum import Enum

CONFIRMATION_NS = 30_000_000_000
MAX_REJECTIONS = 256


class ObservationKind(Enum):
  VALID = "valid"
  ABSENT = "absent"
  UNKNOWN = "unknown"
  STALE = "stale"


class IdentityKind(Enum):
  GEOGRAPHIC = "geographic"
  PRODUCER_EPISODE = "producer_episode"
  SESSION_VALUE = "session_value"


@dataclass(frozen=True)
class ObservationIdentity:
  kind: IdentityKind
  value: str | None = None
  session_id: str | None = None


@dataclass(frozen=True)
class Candidate:
  source: str
  observation_identity: ObservationIdentity
  speed_mps: float


@dataclass(frozen=True)
class Observation:
  kind: ObservationKind
  candidate: Candidate | None = None


class Mode(Enum):
  OFF = "off"
  LATERAL_ONLY = "lateral_only"
  LONGITUDINAL_ONLY = "longitudinal_only"
  COMBINED = "combined"


class LongitudinalOwner(Enum):
  NONE = "none"
  SYSTEM = "system"
  STOCK = "stock"


@dataclass(frozen=True)
class Authority:
  mode: Mode
  owner: LongitudinalOwner
  lateral_active: bool
  longitudinal_active: bool
  stock_acc_active: bool
  fully_disengaged: bool

  @property
  def can_control(self) -> bool:
    return (self.mode in (Mode.LONGITUDINAL_ONLY, Mode.COMBINED) and
            self.owner is LongitudinalOwner.SYSTEM and self.longitudinal_active)


@dataclass(frozen=True)
class Policy:
  confirm_lower: bool = True
  confirm_higher: bool = True
  fallback_previous: bool = False
  display_only: bool = False
  vision_driver_confirm: bool = False


class ActionKind(Enum):
  ACCEPT = "accept"
  REJECT = "reject"


@dataclass(frozen=True)
class DriverAction:
  session_id: str
  sequence_id: int
  decision_id: int
  kind: ActionKind


@dataclass(frozen=True)
class AdoptRequest:
  session_id: str
  sequence_id: int
  presentation_id: int
  candidate: Candidate


@dataclass(frozen=True)
class ActionReceipt:
  sequence_id: int
  acknowledged: bool
  consumed: bool
  status: str


@dataclass(frozen=True)
class AcceptedLimit:
  candidate: Candidate
  session_id: str
  accepted_at_ns: int


@dataclass(frozen=True)
class PendingDecision:
  candidate: Candidate
  decision_id: int
  active_elapsed_ns: int = 0


@dataclass(frozen=True)
class Presentation:
  presentation_id: int
  candidate: Candidate


@dataclass(frozen=True)
class AdoptionProposal:
  session_id: str
  action_sequence_id: int
  presentation_id: int
  accepted: AcceptedLimit
  reconciliation_speed_mps: float
  clear_override: bool = True


@dataclass(frozen=True)
class State:
  session_id: str
  observation: Observation = Observation(ObservationKind.ABSENT)
  accepted: AcceptedLimit | None = None
  pending: PendingDecision | None = None
  rejected: frozenset[Candidate] = frozenset()
  last_timestamp_ns: int | None = None
  timer_running: bool = False
  last_action_sequence: int = -1
  next_decision_id: int = 1
  rejection_capacity_exhausted: bool = False
  presentation: Presentation | None = None
  next_presentation_id: int = 1


@dataclass(frozen=True)
class Decision:
  state: State
  display_candidate: Candidate | None = None
  control_target_mps: float | None = None
  basis: str = "none"
  history_write: AcceptedLimit | None = None
  action_receipt: ActionReceipt | None = None
  errors: tuple[str, ...] = ()
  adoption_receipt: ActionReceipt | None = None
  adoption: AdoptionProposal | None = None
  authority: Authority | None = None
  policy: Policy | None = None


def _token(value: object) -> bool:
  return type(value) is str and 0 < len(value) <= 256 and bool(value.strip()) and not any(ord(c) < 32 for c in value)


def _integer(value: object, minimum: int = 0) -> bool:
  return type(value) is int and value >= minimum


def _identity_valid(identity: object) -> bool:
  if not isinstance(identity, ObservationIdentity) or not isinstance(identity.kind, IdentityKind):
    return False
  if identity.kind is IdentityKind.SESSION_VALUE:
    return identity.value is None and _token(identity.session_id)
  return _token(identity.value) and identity.session_id is None


def _candidate_valid(candidate: object, session_id: str | None = None) -> bool:
  if not isinstance(candidate, Candidate) or not _token(candidate.source) or not _identity_valid(candidate.observation_identity):
    return False
  identity = candidate.observation_identity
  if session_id is not None and identity.kind is IdentityKind.SESSION_VALUE and identity.session_id != session_id:
    return False
  try:
    return type(candidate.speed_mps) in (int, float) and math.isfinite(candidate.speed_mps) and candidate.speed_mps > 0
  except OverflowError:
    return False


def observation_is_valid(observation: object, *, session_id: str | None = None) -> bool:
  """Check the shared candidate contract without choosing a source or freshness policy."""
  return isinstance(observation, Observation) and isinstance(observation.kind, ObservationKind) and (
    _candidate_valid(observation.candidate, session_id) if observation.kind is ObservationKind.VALID else observation.candidate is None)


def _accepted_valid(accepted: object) -> bool:
  return (isinstance(accepted, AcceptedLimit) and _candidate_valid(accepted.candidate, accepted.session_id) and
          _token(accepted.session_id) and _integer(accepted.accepted_at_ns))


def _authority_errors(authority: object) -> list[str]:
  if not isinstance(authority, Authority) or not isinstance(authority.mode, Mode) or not isinstance(authority.owner, LongitudinalOwner):
    return ["invalid authority type"]
  if any(type(v) is not bool for v in (authority.lateral_active, authority.longitudinal_active,
                                      authority.stock_acc_active, authority.fully_disengaged)):
    return ["authority flags must be booleans"]
  errors = []
  if authority.lateral_active and authority.mode not in (Mode.LATERAL_ONLY, Mode.COMBINED):
    errors.append("active lateral axis contradicts mode")
  if authority.longitudinal_active and (authority.mode not in (Mode.LONGITUDINAL_ONLY, Mode.COMBINED) or
                                        authority.owner is not LongitudinalOwner.SYSTEM):
    errors.append("active longitudinal axis contradicts mode or owner")
  if authority.stock_acc_active and authority.owner is not LongitudinalOwner.STOCK:
    errors.append("active stock ACC contradicts owner")
  if authority.fully_disengaged and (authority.lateral_active or authority.longitudinal_active or authority.stock_acc_active):
    errors.append("fully disengaged contradicts active authority")
  return errors


def authority_is_valid(authority: object) -> bool:
  """Validate the shared mode, owner and activity contract."""
  return not _authority_errors(authority)


def _state_errors(state: State) -> list[str]:
  errors = []
  if not isinstance(state, State):
    return ["invalid state type"]
  if not _token(state.session_id) or not observation_is_valid(state.observation, session_id=state.session_id):
    errors.append("invalid state identity or observation")
  if state.accepted is not None and (not _accepted_valid(state.accepted) or not _candidate_valid(state.accepted.candidate, state.session_id)):
    errors.append("invalid accepted history")
  if state.last_timestamp_ns is not None and not _integer(state.last_timestamp_ns):
    errors.append("invalid state clock")
  if not _integer(state.last_action_sequence, -1) or not _integer(state.next_decision_id, 1) or not _integer(state.next_presentation_id, 1):
    errors.append("invalid state sequence")
  if type(state.timer_running) is not bool or type(state.rejection_capacity_exhausted) is not bool:
    errors.append("invalid state flags")
  rejections_valid = (type(state.rejected) is frozenset and len(state.rejected) <= MAX_REJECTIONS and
                      all(_candidate_valid(c, state.session_id) for c in state.rejected))
  if not rejections_valid:
    errors.append("invalid rejection history")
  elif state.accepted is not None and _accepted_valid(state.accepted) and state.accepted.candidate in state.rejected:
    errors.append("accepted candidate is also rejected")
  if state.pending is not None:
    pending = state.pending
    if (not isinstance(pending, PendingDecision) or not _candidate_valid(pending.candidate) or
        not _integer(pending.decision_id, 1) or not _integer(pending.active_elapsed_ns) or
        not _integer(state.next_decision_id, 1) or pending.decision_id >= state.next_decision_id or
        state.observation != Observation(ObservationKind.VALID, pending.candidate)):
      errors.append("invalid pending decision")
    elif rejections_valid and pending.candidate in state.rejected:
      errors.append("pending candidate is already rejected")
  if state.timer_running and (state.pending is None or state.last_timestamp_ns is None):
    errors.append("timer lacks pending decision or clock")
  if state.presentation is not None:
    shown = state.presentation
    if (not isinstance(shown, Presentation) or not _integer(shown.presentation_id, 1) or
        not _integer(state.next_presentation_id, 1) or shown.presentation_id >= state.next_presentation_id or
        not _candidate_valid(shown.candidate, state.session_id) or state.last_timestamp_ns is None or
        state.observation != Observation(ObservationKind.VALID, shown.candidate)):
      errors.append("invalid presentation context")
  elif isinstance(state.observation, Observation) and state.observation.kind is ObservationKind.VALID:
    errors.append("valid observation lacks presentation context")
  return errors


def new_session(session_id: str, accepted: AcceptedLimit | None = None) -> State:
  """Explicitly reset transient state; a caller may supply independently qualified history."""
  state = State(session_id=session_id, accepted=accepted)
  errors = _state_errors(state)
  if errors:
    raise ValueError("; ".join(errors))
  return state


def _action_valid(action: object) -> bool:
  return (isinstance(action, DriverAction) and _token(action.session_id) and _integer(action.sequence_id) and
          _integer(action.decision_id, 1) and isinstance(action.kind, ActionKind))


def _adopt_valid(adopt: object) -> bool:
  return (isinstance(adopt, AdoptRequest) and _token(adopt.session_id) and _integer(adopt.sequence_id) and
          _integer(adopt.presentation_id, 1) and _candidate_valid(adopt.candidate, adopt.session_id))


def _acknowledge(state: State, action: DriverAction | AdoptRequest | None) -> tuple[State, ActionReceipt | None]:
  if action is None:
    return state, None
  if action.session_id != state.session_id:
    return state, ActionReceipt(action.sequence_id, True, False, "foreign_session")
  if action.sequence_id <= state.last_action_sequence:
    return state, ActionReceipt(action.sequence_id, True, False, "already_seen")
  return replace(state, last_action_sequence=action.sequence_id), ActionReceipt(action.sequence_id, True, False, "seen")


def _accept(state: State, candidate: Candidate, now_ns: int) -> tuple[State, AcceptedLimit | None]:
  if state.accepted is not None and state.accepted.candidate == candidate:
    return replace(state, pending=None, timer_running=False), None
  accepted = AcceptedLimit(candidate, state.session_id, now_ns)
  return replace(state, accepted=accepted, pending=None, timer_running=False), accepted


def _reject(state: State, candidate: Candidate) -> State:
  if candidate not in state.rejected and len(state.rejected) == MAX_REJECTIONS:
    return replace(state, pending=None, timer_running=False, rejection_capacity_exhausted=True)
  return replace(state, rejected=state.rejected | {candidate}, pending=None, timer_running=False)


def step(state: State, observation: Observation, authority: Authority, policy: Policy, *, now_ns: int,
         action: DriverAction | None = None, adopt: AdoptRequest | None = None) -> Decision:
  """Return a decision, never a cruise command. Invalid input produces no control target."""
  state_errors = _state_errors(state)
  if state_errors:
    return Decision(state, errors=tuple(state_errors))
  errors = _authority_errors(authority)
  if not observation_is_valid(observation, session_id=state.session_id):
    errors.append("invalid observation")
  if not isinstance(policy, Policy) or any(type(v) is not bool for v in (
      policy.confirm_lower, policy.confirm_higher, policy.fallback_previous, policy.display_only,
      policy.vision_driver_confirm)):
    errors.append("invalid policy")
  if not _integer(now_ns) or (state.last_timestamp_ns is not None and now_ns < state.last_timestamp_ns):
    errors.append("invalid or reversed monotonic clock")
  if action is not None and not _action_valid(action):
    errors.append("invalid driver action")
  if adopt is not None and not _adopt_valid(adopt):
    errors.append("invalid adopt request")
  if action is not None and adopt is not None:
    errors.append("ambiguous action and adopt request")
  if errors:
    # Do not defer a stale prompt or credit the invalid interval on recovery.
    invalid = replace(state, observation=Observation(ObservationKind.UNKNOWN), pending=None, timer_running=False, presentation=None)
    # A valid same-session event is seen even when another input makes it ineligible.
    invalid, receipt = _acknowledge(invalid, action if _action_valid(action) else None)
    invalid, adopt_receipt = _acknowledge(invalid, adopt if _adopt_valid(adopt) else None)
    if receipt is not None and receipt.status == "seen":
      receipt = replace(receipt, status="invalid_input")
    if adopt_receipt is not None and adopt_receipt.status == "seen":
      adopt_receipt = replace(adopt_receipt, status="invalid_input")
    return Decision(invalid, action_receipt=receipt, adoption_receipt=adopt_receipt, errors=tuple(errors))

  old = state
  state, receipt = _acknowledge(replace(state, observation=observation, last_timestamp_ns=now_ns), action)
  state, adopt_receipt = _acknowledge(state, adopt)
  candidate = observation.candidate
  if candidate is None:
    state = replace(state, presentation=None)
  elif old.presentation is None or old.presentation.candidate != candidate:
    state = replace(state, presentation=Presentation(state.next_presentation_id, candidate), next_presentation_id=state.next_presentation_id + 1)

  def finish(basis: str, *, target: float | None = None, history: AcceptedLimit | None = None,
             adoption: AdoptionProposal | None = None) -> Decision:
    final_receipt = replace(receipt, status=basis) if receipt is not None and receipt.status == "seen" else receipt
    final_adopt_receipt = replace(adopt_receipt, status=basis) if adopt_receipt is not None and adopt_receipt.status == "seen" else adopt_receipt
    return Decision(state, candidate, target, basis, history, final_receipt, adoption_receipt=final_adopt_receipt,
                    adoption=adoption, authority=authority, policy=policy)

  def previous_target() -> float | None:
    return state.accepted.candidate.speed_mps if state.accepted is not None and authority.can_control else None

  if state.rejection_capacity_exhausted:
    state = replace(state, pending=None, timer_running=False)
    return finish("session_reset_required")
  if policy.display_only:
    state = replace(state, pending=None, timer_running=False)
    return finish("display_only")
  if observation.kind is not ObservationKind.VALID:
    state = replace(state, pending=None, timer_running=False,
                    accepted=None if policy.vision_driver_confirm and state.accepted is not None and
                    state.accepted.candidate.source == 'vision' else state.accepted)
    target = previous_target() if observation.kind is ObservationKind.ABSENT and policy.fallback_previous else None
    return finish("previous_accepted" if target is not None else observation.kind.value, target=target)

  assert candidate is not None
  vision_confirm = policy.vision_driver_confirm and candidate.source == 'vision'
  if (policy.vision_driver_confirm and state.accepted is not None and
      state.accepted.candidate.source == 'vision' and state.accepted.candidate != candidate):
    state = replace(state, accepted=None)
  if adopt_receipt is not None and adopt_receipt.status == "seen":
    assert adopt is not None
    if (old.presentation is None or old.presentation.presentation_id != adopt.presentation_id or
        old.presentation.candidate != candidate or adopt.candidate != candidate):
      adopt_receipt = replace(adopt_receipt, status="different_presentation")
    elif not authority.can_control:
      adopt_receipt = replace(adopt_receipt, status="no_longitudinal_authority")
    else:
      state, history = _accept(replace(state, rejected=state.rejected - {candidate}), candidate, now_ns)
      assert state.accepted is not None
      adopt_receipt = replace(adopt_receipt, consumed=True, status="adopt")
      proposal = AdoptionProposal(state.session_id, adopt.sequence_id, adopt.presentation_id, state.accepted, candidate.speed_mps)
      return finish("driver_adopt", target=candidate.speed_mps, history=history, adoption=proposal)

  if candidate in state.rejected:
    state = replace(state, pending=None, timer_running=False)
    return finish("rejected", target=previous_target())

  if authority.fully_disengaged and not vision_confirm:
    state, history = _accept(state, candidate, now_ns)
    return finish("disengaged_accept", history=history)

  if vision_confirm and state.accepted is not None and state.accepted.candidate == candidate:
    return finish("driver_confirmed_vision", target=candidate.speed_mps if authority.can_control else None)

  previous_speed = state.accepted.candidate.speed_mps if state.accepted is not None else None
  confirmation = True if vision_confirm else policy.confirm_higher if previous_speed is None or candidate.speed_mps > previous_speed else (
    policy.confirm_lower if candidate.speed_mps < previous_speed else False)
  if not confirmation:
    if authority.can_control:
      state, history = _accept(state, candidate, now_ns)
      return finish("accepted", target=candidate.speed_mps, history=history)
    state = replace(state, pending=None, timer_running=False)
    return finish("no_longitudinal_authority")

  if old.pending is not None and old.pending.candidate == candidate:
    pending = old.pending
    if old.timer_running and authority.can_control:
      assert old.last_timestamp_ns is not None
      pending = replace(pending, active_elapsed_ns=pending.active_elapsed_ns + now_ns - old.last_timestamp_ns)
  else:
    pending = PendingDecision(candidate, state.next_decision_id)
    state = replace(state, next_decision_id=state.next_decision_id + 1)
  state = replace(state, pending=pending, timer_running=authority.can_control)

  if receipt is not None and receipt.status == "seen":
    assert action is not None
    if action.decision_id != pending.decision_id:
      receipt = replace(receipt, status="different_decision")
    elif old.pending is None or old.pending.decision_id != pending.decision_id:
      receipt = replace(receipt, status="not_presented")
    elif not authority.can_control:
      receipt = replace(receipt, status="no_longitudinal_authority")
    else:
      receipt = replace(receipt, consumed=True, status=action.kind.value)
      if action.kind is ActionKind.ACCEPT:
        state, history = _accept(state, candidate, now_ns)
        return finish("driver_accept", target=candidate.speed_mps, history=history)
      state = _reject(state, candidate)
      return finish("driver_reject", target=None if state.rejection_capacity_exhausted else previous_target())

  if pending.active_elapsed_ns >= CONFIRMATION_NS and authority.can_control:
    state = _reject(state, candidate)
    return finish("timeout_reject", target=None if state.rejection_capacity_exhausted else previous_target())
  return finish("pending", target=previous_target())
