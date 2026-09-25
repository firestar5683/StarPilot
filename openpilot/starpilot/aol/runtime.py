"""Bounded AOL axis requests and native acknowledgment checks.

The requester and the actuator are deliberately separate: a native permission
cannot be required before the host sends its first desired-axis request.
"""

from __future__ import annotations

from dataclasses import dataclass

from opendbc.car.structs import car
from openpilot.starpilot.aol.vehicle import native_matches_cp, native_profile_supported
from openpilot.starpilot.aol.wire import INTENT_SERVICE, SAFETY_SERVICE, IntentState, decode_intent, decode_safety

INTENT_MAX_AGE_NS = 30_000_000
SAFETY_MAX_AGE_NS = 200_000_000
AXIS_MAX_AGE_NS = 30_000_000


@dataclass(frozen=True)
class AxisDecision:
  desired_lateral: bool = False
  desired_longitudinal: bool = False
  lateral_active: bool = False
  longitudinal_active: bool = False
  native_acknowledged: bool = False

  @property
  def mode(self) -> str:
    if self.lateral_active and self.longitudinal_active:
      return 'combined'
    if self.lateral_active:
      return 'lateralOnly'
    if self.longitudinal_active:
      return 'longitudinalOnly'
    return 'off'


def current_intent(sm, *, car_state_ns: int, now_ns: int, previous: IntentState | None = None):
  if not (sm.valid[INTENT_SERVICE] and sm.alive[INTENT_SERVICE] and sm.seen[INTENT_SERVICE]):
    return None
  intent = decode_intent(sm[INTENT_SERVICE])
  if intent is None:
    return None
  # Intent is published before its carState wakeup. If the carState socket
  # times out exactly between those sends, only the already accepted companion
  # for that *same retained carState* may bridge the publication boundary.
  # Revalidate its original lease; never accept a newer intent for older CAN.
  if (intent.carStateLogMonoTime > car_state_ns and previous is not None and
      previous.carStateLogMonoTime == car_state_ns and intent.settingsQualified and
      intent.producerSessionId == previous.producerSessionId and
      int(sm.logMonoTime[INTENT_SERVICE]) == intent.carStateLogMonoTime and
      intent.observedMonoTime <= now_ns <= intent.validUntilMonoTime and
      now_ns - intent.observedMonoTime <= INTENT_MAX_AGE_NS):
    intent = previous
    message_ns = int(previous.carStateLogMonoTime)
  else:
    message_ns = int(sm.logMonoTime[INTENT_SERVICE])
  observed = int(intent.observedMonoTime)
  produced_for = int(intent.carStateLogMonoTime)
  if (not intent.settingsQualified or not intent.producerSessionId or produced_for <= 0 or
      message_ns != produced_for or
      produced_for > car_state_ns or car_state_ns - produced_for > INTENT_MAX_AGE_NS or
      observed > now_ns or now_ns > int(intent.validUntilMonoTime) or
      now_ns - observed > INTENT_MAX_AGE_NS):
    return None
  return intent


def current_native(sm, CP, *, now_ns: int, axis_session_id: str | None = None):
  if not (sm.valid[SAFETY_SERVICE] and sm.alive[SAFETY_SERVICE] and sm.seen[SAFETY_SERVICE]):
    return None
  state = decode_safety(sm[SAFETY_SERVICE])
  if state is None:
    return None
  if (not native_matches_cp(CP, int(state.safetyModel), int(state.safetyParam)) or
      not state.compatible or int(state.protocolVersion) != 1 or not state.pandaSerial or not state.axisSessionId or
      (axis_session_id is not None and str(state.axisSessionId) != axis_session_id) or
      int(sm.logMonoTime[SAFETY_SERVICE]) > now_ns or
      now_ns - int(sm.logMonoTime[SAFETY_SERVICE]) > SAFETY_MAX_AGE_NS or
      int(state.observedMonoTime) > now_ns or now_ns > int(state.validUntilMonoTime)):
    return None
  return state


def decide_axes(*, standard_lateral: bool, standard_longitudinal: bool, intent,
                native, car_state, initialized: bool, model_ready: bool,
                no_entry: bool, immediate_disable: bool, dm_lockout: bool,
                pause_brake_mps: float, lateral_inhibit: bool = False) -> AxisDecision:
  if intent is None or not initialized or not car_state.canValid or immediate_disable or no_entry or dm_lockout:
    return AxisDecision()
  gear = car_state.gearShifter
  driving = gear not in (car.CarState.GearShifter.neutral, car.CarState.GearShifter.park,
                         car.CarState.GearShifter.reverse, car.CarState.GearShifter.unknown)
  lateral_safe = (driving and model_ready and not lateral_inhibit and not car_state.steerFaultPermanent and
                  not car_state.steerFaultTemporary and
                  (not car_state.brakePressed or car_state.vEgo >= pause_brake_mps or car_state.standstill))
  desired_lateral = bool(lateral_safe and not intent.pauseLateral and (standard_lateral or intent.allowedLatch))
  desired_longitudinal = bool(driving and standard_longitudinal and not intent.pauseLongitudinal)
  lateral_ack = native is not None and bool(native.requestedLateral) == desired_lateral
  longitudinal_ack = native is not None and bool(native.requestedLongitudinal) == desired_longitudinal
  return AxisDecision(
    desired_lateral=desired_lateral, desired_longitudinal=desired_longitudinal,
    lateral_active=bool(desired_lateral and lateral_ack and native.lateralAllowed),
    longitudinal_active=bool(desired_longitudinal and longitudinal_ack and native.longitudinalAllowed),
    native_acknowledged=bool(native is not None),
  )


def current_axis(sm, *, now_ns: int):
  if not (sm.valid['aolAxisState'] and sm.alive['aolAxisState'] and sm.seen['aolAxisState']):
    return None
  state = sm['aolAxisState']
  if (not state.qualified or not state.sessionId or
      int(sm.logMonoTime['aolAxisState']) > now_ns or
      now_ns - int(sm.logMonoTime['aolAxisState']) > AXIS_MAX_AGE_NS or
      int(state.observedMonoTime) > now_ns or now_ns > int(state.validUntilMonoTime)):
    return None
  return state


def monitoring_lateral_engaged(sm, *, now_ns: int) -> bool:
  axis = current_axis(sm, now_ns=now_ns)
  if axis is None or not axis.lateralActive or not axis.nativeAcknowledged:
    return False
  if not (sm.valid[SAFETY_SERVICE] and sm.seen[SAFETY_SERVICE] and sm.alive[SAFETY_SERVICE]):
    return False
  native = decode_safety(sm[SAFETY_SERVICE])
  if native is None:
    return False
  return bool(native.compatible and int(native.protocolVersion) == 1 and
              native.axisSessionId == axis.sessionId and
              native_profile_supported(int(native.safetyModel), int(native.safetyParam)) and
              int(sm.logMonoTime[SAFETY_SERVICE]) <= now_ns and
              now_ns - int(sm.logMonoTime[SAFETY_SERVICE]) <= SAFETY_MAX_AGE_NS and
              int(native.observedMonoTime) <= now_ns <= int(native.validUntilMonoTime) and
              native.requestedLateral and native.lateralAllowed)


def ordinary_lateral_requested(active: bool, CS, CP) -> bool:
  """The standard lateral output gate, shared by request and actuation owners."""
  standstill = abs(CS.vEgo) <= max(CP.minSteerSpeed, 0.3) or CS.standstill
  return bool(active and not CS.steerFaultTemporary and not CS.steerFaultPermanent and
              (not standstill or CP.steerAtStandstill))


def decide_ordinary_axis(*, requested: bool, native) -> AxisDecision:
  """Acknowledgment cannot create driver intent or an independent axis."""
  acknowledged = bool(native is not None and native.requestedLateral == requested and
                      not native.requestedLongitudinal)
  return AxisDecision(desired_lateral=bool(requested),
                      lateral_active=bool(requested and acknowledged and native.lateralAllowed),
                      native_acknowledged=acknowledged)


def ordinary_axis_acknowledged(sm, CP, *, now_ns: int) -> bool:
  axis = current_axis(sm, now_ns=now_ns)
  native = current_native(sm, CP, now_ns=now_ns,
                          axis_session_id=str(axis.sessionId) if axis is not None else None)
  return bool(axis is not None and native is not None and axis.nativeAcknowledged and
              axis.desiredLateral and axis.lateralActive and not axis.desiredLongitudinal and
              native.requestedLateral and not native.requestedLongitudinal and native.lateralAllowed)
