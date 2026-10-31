"""Card-side qualification for SLC buttons and selected-speed commands."""

import math

from openpilot.cereal.services import SERVICE_LIST
from openpilot.selfdrive.car.cruise import SlcPendingConfirmation, V_CRUISE_MIN, V_CRUISE_MAX
from openpilot.starpilot.speed_limits.acceptance import CONFIRMATION_NS
from openpilot.starpilot.speed_limits.selection import Source


STATE_MAX_AGE_NS = int(2e9 / SERVICE_LIST['slcState'].frequency)
COMMAND_MAX_AGE_NS = int(2e9 / SERVICE_LIST['slcState'].frequency)


def finite_speed(value: object) -> bool:
  if type(value) not in (int, float):
    return False
  assert isinstance(value, (int, float))
  return math.isfinite(value) and value > 0


def adoption_speed(state):
  boundary = str(getattr(state, 'upcomingBoundaryId', ''))
  if not boundary:
    return float(state.speedLimit) if finite_speed(state.speedLimit) else None
  if len(boundary) != 64 or any(c not in '0123456789abcdef' for c in boundary):
    return None
  speed = getattr(state, 'upcomingSpeedLimit', 0.0)
  return float(speed) if finite_speed(speed) else None


def source_matches(state, observation, producer_session: str, now_ns: int) -> bool:
  return (str(state.source) == 'dashboard' and str(state.observationKind) == 'valid' and
          str(state.sourceProducerSessionId) == producer_session and producer_session != '' and
          getattr(observation.status, 'value', observation.status) == 'valid' and int(state.sourceEpisode) > 0 and
          int(state.sourceEpisode) == int(observation.episode) and
          int(state.sourceObservedMonoTime) == int(observation.observed_ns) and
          int(state.sourceValidUntilMonoTime) == int(observation.valid_until_ns) and
          0 < int(observation.observed_ns) <= now_ns <= int(observation.valid_until_ns) and
          finite_speed(state.speedLimit) and finite_speed(observation.speed_mps) and
          abs(float(state.speedLimit) - float(observation.speed_mps)) <= 0.02)


def _state(sm, now_ns: int):
  if not (sm.valid['slcState'] and sm.alive['slcState'] and
          0 < int(sm.logMonoTime['slcState']) <= now_ns and
          now_ns - int(sm.logMonoTime['slcState']) <= STATE_MAX_AGE_NS):
    return None
  state = sm['slcState']
  if not (state.enabled and not state.displayOnly and str(state.sessionId) and
          0 < int(state.frameMonoTime) <= int(sm.logMonoTime['slcState']) and
          now_ns - int(state.frameMonoTime) <= STATE_MAX_AGE_NS):
    return None
  return state


def _current_state(sm, now_ns: int):
  state = _state(sm, now_ns)
  return state if (state is not None and str(state.observationKind) == 'valid' and
                   str(state.source) in tuple(Source) and finite_speed(state.speedLimit) and adoption_speed(state) is not None) else None


def state_current(sm, observation, producer_session: str, now_ns: int):
  state = _current_state(sm, now_ns)
  if state is None:
    return None
  if (not getattr(state, 'upcomingBoundaryId', '') and str(state.source) == 'dashboard' and
      (observation is None or not source_matches(state, observation, producer_session, now_ns))):
    return None
  return state


def engagement_state(sm, observation, producer_session: str, now_ns: int, *, after_ns: int = 0):
  state = _current_state(sm, now_ns)
  if (state is None or int(state.frameMonoTime) <= after_ns or int(state.presentationId) <= 0 or
      str(state.source) == 'online' or not state.hasPresentationAdjustedLimit):
    return None
  if str(state.source) == 'dashboard' and (
      observation is None or observation.observed_ns <= after_ns or not source_matches(state, observation, producer_session, now_ns)):
    return None
  if str(state.source) == 'vision' and not (
      state.sourceProducerSessionId and state.sourceEpisode > 0 and
      0 < state.sourceObservedMonoTime <= now_ns <= state.sourceValidUntilMonoTime):
    return None
  target = float(state.presentationAdjustedLimit)
  return state if finite_speed(target) and V_CRUISE_MIN / 3.6 - 1e-5 <= target <= V_CRUISE_MAX / 3.6 + 1e-5 else None


def pending_confirmation(sm, now_ns: int, *, long_active: bool,
                         after_ns: int = 0) -> SlcPendingConfirmation | None:
  if not long_active:
    return None
  # The planner owns pending choices for every source; Dashboard commands also bind local OEM evidence.
  state = _state(sm, now_ns)
  if (state is None or int(state.frameMonoTime) <= after_ns or not state.hasPending or state.automaticAdoptionPending or
      int(state.decisionId) <= 0 or int(state.presentationId) < 0):
    return None
  if not finite_speed(state.pendingSpeedLimit):
    return None
  if int(state.presentationId) == 0:
    started = int(state.pendingSinceMonoTime)
    # Consume the displayed choice even if its deadline passes in transit.
    if str(state.pendingSource) not in tuple(Source) or not 0 < started <= int(state.frameMonoTime) <= started + CONFIRMATION_NS:
      return None
  elif (_current_state(sm, now_ns) is None or
        abs(float(state.pendingSpeedLimit) - adoption_speed(state)) > 0.02):
    return None
  return SlcPendingConfirmation(str(state.sessionId), int(state.decisionId), int(state.presentationId))


def command_applicable(command, state, observation, producer_session: str, now_ns: int,
                       selected_mps: float, *, long_active: bool, button_event: bool) -> bool:
  if state is None or button_event or not long_active or not state.hasAccepted:
    return False
  boundary = str(getattr(state, 'upcomingBoundaryId', ''))
  speed = adoption_speed(state)
  if speed is None or str(getattr(command, 'upcomingBoundaryId', '')) != boundary:
    return False
  source = 'map' if boundary else str(state.source)
  producer, episode, observed, valid_until = ('', 0, 0, 0) if boundary else (
    str(state.sourceProducerSessionId), int(state.sourceEpisode), int(state.sourceObservedMonoTime), int(state.sourceValidUntilMonoTime))
  if (str(command.kind) != 'adoptAcceptedLimit' or not str(command.sessionId) or
      str(command.sessionId) != str(state.sessionId) or int(command.commandId) <= 0 or
      int(command.actionId) < 0 or int(command.presentationId) <= 0 or
      int(command.commandId) != int(state.commandId) or
      int(command.presentationId) != int(state.presentationId) or
      int(command.sourceEpisode) != episode or
      str(command.source) != source or
      str(command.sourceProducerSessionId) != producer or
      int(command.sourceObservedMonoTime) != observed or
      int(command.sourceValidUntilMonoTime) != valid_until or
      (source == 'dashboard' and (observation is None or not source_matches(state, observation, producer_session, now_ns)))):
    return False
  issued, expires = int(command.issuedMonoTime), int(command.expiresMonoTime)
  if not (0 < issued <= now_ns <= expires and expires - issued <= COMMAND_MAX_AGE_NS):
    return False
  expected, target = float(command.expectedSelectedMps), float(command.targetMps)
  # Float32 transport can round a legal boundary just outside its double-precision value.
  return (finite_speed(expected) and finite_speed(target) and finite_speed(selected_mps) and
          abs(expected - selected_mps) <= 0.1 and
          abs(float(state.acceptedSpeedLimit) - speed) <= 0.02 and
          abs(target - (float(state.acceptedSpeedLimit) + float(state.offset))) <= 0.1 and
          V_CRUISE_MIN / 3.6 - 1e-5 <= target <= V_CRUISE_MAX / 3.6 + 1e-5)
