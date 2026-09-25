"""Card-side qualification for SLC buttons and selected-speed commands."""

import math

from openpilot.cereal.services import SERVICE_LIST
from openpilot.selfdrive.car.cruise import SlcPendingConfirmation


STATE_MAX_AGE_NS = int(2e9 / SERVICE_LIST['slcState'].frequency)
COMMAND_MAX_AGE_NS = int(2e9 / SERVICE_LIST['slcState'].frequency)


def finite_speed(value: object) -> bool:
  if type(value) not in (int, float):
    return False
  assert isinstance(value, (int, float))
  return math.isfinite(value) and value > 0


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


def state_current(sm, observation, producer_session: str, now_ns: int):
  if not (sm.valid['slcState'] and sm.alive['slcState'] and
          0 < int(sm.logMonoTime['slcState']) <= now_ns and
          now_ns - int(sm.logMonoTime['slcState']) <= STATE_MAX_AGE_NS):
    return None
  state = sm['slcState']
  if not (state.enabled and str(state.sessionId) and state.frameMonoTime <= now_ns and
          int(state.frameMonoTime) <= int(sm.logMonoTime['slcState']) and
          source_matches(state, observation, producer_session, now_ns)):
    return None
  return state


def pending_confirmation(sm, observation, producer_session: str, now_ns: int,
                         *, long_active: bool, pcm_cruise: bool) -> SlcPendingConfirmation | None:
  if not long_active or pcm_cruise:
    return None
  state = state_current(sm, observation, producer_session, now_ns)
  if state is None or not state.hasPending or int(state.decisionId) <= 0 or int(state.presentationId) <= 0:
    return None
  if not finite_speed(state.pendingSpeedLimit) or abs(float(state.pendingSpeedLimit) - float(state.speedLimit)) > 0.02:
    return None
  return SlcPendingConfirmation(str(state.sessionId), int(state.decisionId), int(state.presentationId))


def command_applicable(command, state, observation, producer_session: str, now_ns: int,
                       selected_mps: float, *, long_active: bool, pcm_cruise: bool, button_event: bool) -> bool:
  if state is None or button_event or pcm_cruise or not long_active or not state.hasAccepted:
    return False
  if (str(command.kind) != 'adoptAcceptedHigherLimit' or not str(command.sessionId) or
      str(command.sessionId) != str(state.sessionId) or int(command.commandId) <= 0 or
      int(command.actionId) < 0 or int(command.presentationId) <= 0 or
      int(command.commandId) != int(state.commandId) or
      int(command.presentationId) != int(state.presentationId) or
      int(command.sourceEpisode) != int(state.sourceEpisode) or
      str(command.sourceProducerSessionId) != producer_session or
      int(command.sourceObservedMonoTime) != int(state.sourceObservedMonoTime) or
      int(command.sourceValidUntilMonoTime) != int(state.sourceValidUntilMonoTime) or
      not source_matches(state, observation, producer_session, now_ns)):
    return False
  issued, expires = int(command.issuedMonoTime), int(command.expiresMonoTime)
  if not (0 < issued <= now_ns <= expires and expires - issued <= COMMAND_MAX_AGE_NS):
    return False
  expected, target = float(command.expectedSelectedMps), float(command.targetMps)
  return (finite_speed(expected) and finite_speed(target) and finite_speed(selected_mps) and
          abs(expected - selected_mps) <= 0.1 and target > selected_mps + 0.1 and
          abs(target - (float(state.acceptedSpeedLimit) + float(state.offset))) <= 0.1 and
          target <= 145.0 / 3.6)
