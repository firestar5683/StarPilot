"""GM-owned AOL capabilities; exact CP admission lives with the vehicle."""

import math

from opendbc.car.structs import CarParams
from opendbc.car.gm.values import CAR, control_flags, camera_acc_pedal_profile, is_volt_ascm_longitudinal
from opendbc.car.gm.aol import GM_AOL_ALTERNATIVE_EXPERIENCE, GM_AOL_WORDS, qualified_gm
from openpilot.starpilot.aol.policy import AolVehiclePolicy
from openpilot.starpilot.aol.intent import AOL_TOGGLE, AolCardIntent


def policy_for(cp) -> AolVehiclePolicy:
  qualified = qualified_gm(cp)
  return AolVehiclePolicy(intent_supported=qualified, settings_supported=qualified,
                         runtime_supported=qualified, normal_runtime_supported=qualified,
                         lkas_button_supported=False,
                         full_axis_runtime_required=qualified and int(cp.alternativeExperience) == GM_AOL_ALTERNATIVE_EXPERIENCE,
                         alternative_experience_addition=GM_AOL_ALTERNATIVE_EXPERIENCE if qualified else 0)


def native_profile_supported(model: int, param: int) -> bool:
  return model == int(CarParams.SafetyModel.gm) and param in GM_AOL_WORDS


def native_accepts_cp(cp, model: int, param: int) -> bool:
  return (qualified_gm(cp) and int(cp.alternativeExperience) == GM_AOL_ALTERNATIVE_EXPERIENCE and
          native_profile_supported(model, param))


class GmAolCardIntent(AolCardIntent):
  """Main-following intent with explicit main-cycle recovery after fatal faults."""

  def __init__(self, settings, cp=None):
    super().__init__(settings, lkas_button_supported=False)
    self.cp = cp
    self.requires_fault_observation = True
    self._main_cycle_required = False
    self._main_available = False
    self._main_arm_ns = 0
    self.startup_calibration_pending = True
    self._startup_incomplete = False

  def update(self, CS, *, consumed_buttons=frozenset(), fault_active=None,
             now_ns=0, native_rejection_ns=0, standard_enabled=False):
    main_rise = False
    if CS.canValid and not CS.canTimeout:
      main_rise = bool(CS.cruiseState.available and not self._main_available)
      self._main_available = bool(CS.cruiseState.available)
    fault = bool(fault_active or CS.steerFaultPermanent)
    if fault:
      self._main_cycle_required = True
    elif CS.canValid and not CS.canTimeout and not CS.cruiseState.available:
      self._main_cycle_required = False
    super().update(CS, consumed_buttons=consumed_buttons, fault_active=fault_active,
                   now_ns=now_ns, native_rejection_ns=native_rejection_ns,
                   standard_enabled=standard_enabled)
    if self._main_cycle_required:
      self.allowed_latch = False
      self.startup_calibration_pending = False
    if not self.allowed_latch:
      self._main_arm_ns = 0
    elif main_rise:
      self._main_arm_ns = now_ns

  @property
  def main_arm_ns(self):
    return (self._main_arm_ns if self.settings.enabled and self.settings.main_action != AOL_TOGGLE and
            not self.pause_lateral and not self.pause_longitudinal else 0)

  def _arm_from_full_engagement(self, CS, *, source_ns):
    if not self._main_cycle_required:
      super()._arm_from_full_engagement(CS, source_ns=source_ns)

  def observe_calibration(self, CS, *, events=None, standard_enabled=False):
    from openpilot.cereal import log
    # Cold calibration readiness is not a previously revoked driver gesture.
    # The original calibration inhibit still withdraws all optional output.
    prior_incomplete = self._startup_incomplete
    cold_safe = True
    if events is not None:
      from openpilot.starpilot.aol.intent import disarming_fault
      remaining = [event for event in _intent_fault_events(self.cp, events) if
        event.name != log.OnroadEvent.EventName.calibrationIncomplete or event.immediateDisable]
      cold_safe = not disarming_fault(remaining, CS,
        temporary_selfdrive_lagging=qualified_gm(self.cp))
      self._startup_incomplete = bool(cold_safe and
        any(event.name == log.OnroadEvent.EventName.calibrationIncomplete for event in events))
    cold_readiness = bool(self.startup_calibration_pending and cold_safe and
      (prior_incomplete or self._startup_incomplete) and
      self.settings.enabled and self.settings.main_action != AOL_TOGGLE and
      not CS.steerFaultPermanent and not self._main_cycle_required)
    if cold_readiness:
      self._calibration_rearm_required = False
    super().observe_calibration(CS, events=events, standard_enabled=standard_enabled)
    if cold_readiness:
      self._calibration_rearm_required = False
    if (events is not None and CS.canValid and not CS.canTimeout and not self._startup_incomplete and
        not any(event.name == log.OnroadEvent.EventName.selfdriveInitializing for event in events)):
      self.startup_calibration_pending = False

  def output(self, CS):
    allowed, pause_lateral, pause_longitudinal = super().output(CS)
    return (bool(allowed and not CS.canTimeout and CS.cruiseState.available),
            pause_lateral, pause_longitudinal)


def create_intent(cp, settings):
  return GmAolCardIntent(settings, cp) if qualified_gm(cp) else None


def prior_main_off_intent_current(feedback, sm, cp, cs, axis, now_ns, *, latched, main_arm_ns, producer):
  """An older idle response cannot reject a newly armed cruise MAIN request."""
  from opendbc.car.structs import car
  from openpilot.cereal import log
  from openpilot.starpilot.aol.runtime import AXIS_MAX_AGE_NS
  from openpilot.starpilot.aol.transport_pause import _healthy_transport_native

  if (not qualified_gm(cp) or not latched or not 0 < main_arm_ns <= now_ns or
      now_ns - main_arm_ns > AXIS_MAX_AGE_NS or
      feedback.failed or feedback.paused or feedback.pending_event or
      feedback.retention_started_ns or feedback.source_retention_started_ns or
      feedback.longitudinal_cancel_ns or feedback.honda_brake_ns or feedback.gm_withdrawal_ns or
      not feedback.signature or not producer or
      (str(axis.intentProducerSessionId), int(axis.intentIntegrityEpoch)) != feedback.signature[14:16] or
      str(axis.intentProducerSessionId) != producer or
      not cs.canValid or cs.canTimeout or not cs.cruiseState.available or cs.accFaulted or cs.doorOpen or
      cs.steerFaultTemporary or cs.steerFaultPermanent or
      cs.gearShifter not in (car.CarState.GearShifter.drive, car.CarState.GearShifter.low,
                            car.CarState.GearShifter.sport, car.CarState.GearShifter.brake) or
      any(event.type == car.CarState.ButtonEvent.Type.cancel for event in cs.buttonEvents) or
      str(axis.faultReason) != 'none' or axis.nativeAcknowledged or
      axis.desiredLateral or axis.desiredLongitudinal or axis.lateralActive or axis.longitudinalActive or
      not 0 < axis.sourceCarStateMonoTime <= axis.observedMonoTime or axis.sourceCarStateMonoTime >= main_arm_ns or
      now_ns - axis.sourceCarStateMonoTime > AXIS_MAX_AGE_NS or
      not sm.seen['onroadEvents'] or not sm.valid['onroadEvents'] or not sm.alive['onroadEvents'] or
      not 0 < sm.logMonoTime['onroadEvents'] <= now_ns or
      now_ns - sm.logMonoTime['onroadEvents'] > 1_500_000_000):
    return False
  for event in sm['onroadEvents']:
    if event.immediateDisable or event.softDisable:
      return False
    if event.userDisable and not (
        event.name == log.OnroadEvent.EventName.pedalPressed and (cs.brakePressed or cs.regenBraking) or
        event.name == log.OnroadEvent.EventName.pcmDisable and not cs.cruiseState.enabled or
        event.name == log.OnroadEvent.EventName.wrongCarMode and sm.logMonoTime['onroadEvents'] < main_arm_ns):
      return False
  native = _healthy_transport_native(sm, cp, cs, str(axis.sessionId), now_ns)
  return bool(native is not None and native.pandaInventory and
              not native.requestedLateral and not native.requestedLongitudinal and
              not native.lateralAllowed and not native.longitudinalAllowed)


def configuration_settings_policy(cp):
  """Saving stock Silverado lateral intent does not establish its physical source graph."""
  try:
    if (cp.brand == 'gm' and cp.carFingerprint == CAR.CHEVROLET_MALIBU_HYBRID_CC and
        not cp.notCar and not cp.passive and cp.lateralTuning.which() == 'torque' and
        cp.steerControlType == CarParams.SteerControlType.torque and
        int(cp.alternativeExperience) in (0, GM_AOL_ALTERNATIVE_EXPERIENCE)):
      return AolVehiclePolicy(settings_supported=True, lkas_button_supported=False)
    if (cp.brand != 'gm' or cp.carFingerprint != CAR.CHEVROLET_SILVERADO_CC or
        cp.notCar or cp.passive or cp.networkLocation != CarParams.NetworkLocation.gateway or
        cp.transmissionType != CarParams.TransmissionType.automatic or not cp.radarUnavailable or
        not cp.pcmCruise or cp.openpilotLongitudinalControl or cp.alphaLongitudinalAvailable or
        control_flags(cp) != 0 or int(cp.alternativeExperience) not in (0, GM_AOL_ALTERNATIVE_EXPERIENCE) or
        len(cp.safetyConfigs) != 1 or cp.safetyConfigs[0].safetyModel != CarParams.SafetyModel.gm or
        int(cp.safetyConfigs[0].safetyParam) != 16 or cp.steerControlType != CarParams.SteerControlType.torque or
        cp.lateralTuning.which() != 'torque'):
      return None
    tune = cp.lateralTuning.torque
    if (not all(math.isfinite(value) for value in (tune.latAccelFactor, tune.latAccelOffset, tune.friction)) or
        tune.latAccelFactor <= 0 or tune.friction < 0):
      return None
    return AolVehiclePolicy(settings_supported=True, lkas_button_supported=False)
  except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
    return None


def _intent_fault_events(cp, events):
  from openpilot.cereal import log
  if qualified_gm(cp):
    availability = (log.OnroadEvent.EventName.commIssue, log.OnroadEvent.EventName.commIssueAvgFreq)
    events = [event for event in events if not
              (event.name in availability and event.softDisable and not event.immediateDisable)]
  if qualified_gm(cp) and camera_acc_pedal_profile(cp) is None and is_volt_ascm_longitudinal(cp):
    events = [event for event in events if event.name != log.OnroadEvent.EventName.accFaulted]
  return events


def intent_disarming_fault(cp, events, state, **context):
  """An ASCM Volt ACC fault withdraws axes without erasing main-armed intent."""
  from openpilot.cereal import log
  from openpilot.starpilot.aol.intent import disarming_fault
  cold_calibration = context.pop('startup_calibration_pending', False)
  if qualified_gm(cp) and cold_calibration and not state.steerFaultPermanent:
    events = [event for event in events if not (
      event.name == log.OnroadEvent.EventName.calibrationIncomplete and not event.immediateDisable)]
  return disarming_fault(_intent_fault_events(cp, events), state, **context)


def physical_longitudinal_withdrawal_source(cp, cs, parser, observation, now_ns) -> int:
  """Bind a Bolt pedal-owner withdrawal to its parsed CAN and local receipt."""
  from opendbc.car.gm.values import CruiseButtons, is_bolt_present_no_acc_pedal_profile
  from opendbc.car.structs import car
  try:
    if (not qualified_gm(cp) or not is_bolt_present_no_acc_pedal_profile(cp) or
        int(cp.alternativeExperience) != GM_AOL_ALTERNATIVE_EXPERIENCE or
        observation is None or observation[0] is not cs or not cs.canValid or cs.canTimeout):
      return 0
    fields = []
    if cs.brakePressed and parser.vl['ECMEngineStatus']['BrakePressed']:
      fields.append(('ECMEngineStatus', 'BrakePressed'))
    if cs.regenBraking and parser.vl['EBCMRegenPaddle']['RegenPaddle']:
      fields.append(('EBCMRegenPaddle', 'RegenPaddle'))
    if (parser.vl['ASCMSteeringButton']['ACCButtons'] == CruiseButtons.CANCEL and
        any(e.type == car.CarState.ButtonEvent.Type.cancel and e.pressed for e in cs.buttonEvents)):
      fields.append(('ASCMSteeringButton', 'ACCButtons'))
    _, received_ns, can_source_ns, boot_ns = observation
    if not fields or not 0 < received_ns <= now_ns or now_ns - received_ns > 30_000_000:
      return 0
    # Parser/CAN batch use BOOTTIME. The fixed deadline uses the original
    # local MONOTONIC receipt; neither clock is converted or restamped.
    stamps = [int(parser.ts_nanos[message][signal]) for message, signal in fields]
    if not all(0 < stamp <= can_source_ns <= boot_ns and boot_ns - stamp <= 30_000_000 and
               can_source_ns - stamp <= 30_000_000 for stamp in stamps):
      return 0
    return received_ns
  except (AttributeError, KeyError, IndexError, TypeError, ValueError):
    return 0


def retained_physical_longitudinal_intent(feedback, sm, cp, cs, axis, now_ns, *, latched, source_ns, producer):
  """Retain accepted LAT intent through a bounded physical LONG withdrawal."""
  from opendbc.car.gm.values import is_bolt_present_no_acc_pedal_profile
  from opendbc.car.structs import car
  from openpilot.cereal import log
  from openpilot.starpilot.aol.runtime import AXIS_MAX_AGE_NS, SAFETY_MAX_AGE_NS
  from openpilot.starpilot.aol.transport_pause import independent_lateral_health
  occurrence = feedback.gm_withdrawal_ns or source_ns
  if (not qualified_gm(cp) or not is_bolt_present_no_acc_pedal_profile(cp) or
      int(cp.alternativeExperience) != GM_AOL_ALTERNATIVE_EXPERIENCE or
      not latched or feedback.failed or feedback.paused or feedback.pending_event or
      feedback.retention_started_ns or not feedback.session or str(axis.sessionId) != feedback.session or
      not feedback.healthy_feedback_ns or not 0 <= now_ns - feedback.healthy_feedback_ns <= AXIS_MAX_AGE_NS or
      not 0 < occurrence <= now_ns or now_ns - occurrence > SAFETY_MAX_AGE_NS or
      not feedback.gm_withdrawal_ns and now_ns - occurrence > AXIS_MAX_AGE_NS or
      not producer or producer != feedback.availability_producer or
      str(axis.intentProducerSessionId) != producer or int(axis.intentIntegrityEpoch) != feedback.availability_epoch or
      cs.accFaulted or cs.doorOpen or not cs.cruiseState.available or
      cs.gearShifter not in (car.CarState.GearShifter.drive, car.CarState.GearShifter.low,
                            car.CarState.GearShifter.sport, car.CarState.GearShifter.brake) or
      str(axis.faultReason) != 'none' or not axis.desiredLateral or not axis.lateralActive or
      not axis.nativeAcknowledged or
      not 0 < axis.sourceCarStateMonoTime <= axis.observedMonoTime <= now_ns or
      now_ns - axis.sourceCarStateMonoTime > AXIS_MAX_AGE_NS):
    return None
  # The saved LAT contract treats a parsed unlatched belt as a LONG lock.
  # After rebuckling, accept only a prior producer's matching belt event and
  # LAT-only proof within the already established physical occurrence. Events
  # publish sparsely, so their stamp binds to faultEventMonoTime, not the newer
  # car-state source. The original axis/native leases remain unchanged.
  event_ns = int(sm.logMonoTime['onroadEvents'])
  prior_belt_proof = bool(feedback.gm_withdrawal_ns and
    feedback.gm_withdrawal_ns <= event_ns <= axis.observedMonoTime < now_ns and
    event_ns == axis.faultEventMonoTime and str(axis.faultSessionId) == feedback.session and
    int(sm.logMonoTime['aolAxisState']) == axis.observedMonoTime and
    now_ns <= axis.validUntilMonoTime <= axis.observedMonoTime + AXIS_MAX_AGE_NS and
    not axis.desiredLongitudinal and not axis.longitudinalActive)
  if (not sm.seen['onroadEvents'] or not sm.valid['onroadEvents'] or not sm.alive['onroadEvents'] or
      not 0 < event_ns <= now_ns or now_ns - event_ns > 1_500_000_000 or
      any(e.immediateDisable or e.softDisable and not
          ((cs.seatbeltUnlatched or prior_belt_proof) and e.name == log.OnroadEvent.EventName.seatbeltNotLatched and
           e.noEntry and not e.userDisable) for e in sm['onroadEvents'])):
    return None
  native = independent_lateral_health(sm, cp, cs, feedback.session, now_ns)
  if (native is None or not native.pandaInventory or not native.requestedLongitudinal or
      not any(not p.controlsAllowed for p in sm['pandaStates']) or
      native.observedMonoTime < feedback.healthy_native_ns or
      (native.pandaSerial, tuple(p.hardwareSerial for p in native.pandaInventory)) != feedback.healthy_inventory):
    return None
  # One occurrence spans the held native request. Held/released samples and
  # duplicate Card calls cannot renew it; output/native leases remain original.
  feedback.gm_withdrawal_ns = occurrence
  return native


def physical_cancel_lateral_allowed(cp, cs, intent, native, *, source_ns, now_ns) -> bool:
  """Exact armed Bolt Cancel removes only the lateral NO_ENTRY restriction."""
  from opendbc.car.gm.values import is_bolt_present_no_acc_pedal_profile
  from opendbc.car.structs import car
  from openpilot.starpilot.aol.runtime import AXIS_MAX_AGE_NS, SAFETY_MAX_AGE_NS, native_inventory_matches_cp
  try:
    return bool(qualified_gm(cp) and is_bolt_present_no_acc_pedal_profile(cp) and
      int(cp.alternativeExperience) == GM_AOL_ALTERNATIVE_EXPERIENCE and
      intent is not None and intent.settingsQualified and intent.allowedLatch and intent.lateralArmed and
      intent.producerSessionId and intent.carStateLogMonoTime == source_ns and
      0 < source_ns <= intent.observedMonoTime <= now_ns <= intent.validUntilMonoTime and
      now_ns - source_ns <= AXIS_MAX_AGE_NS and
      # Card declares a 200ms wire lease; admission and this source remain 30ms fresh.
      intent.validUntilMonoTime - intent.observedMonoTime <= SAFETY_MAX_AGE_NS and
      cs.canValid and not cs.canTimeout and not cs.steerFaultTemporary and not cs.steerFaultPermanent and
      any(e.type == car.CarState.ButtonEvent.Type.cancel for e in cs.buttonEvents) and
      native is not None and native.requestedLateral and native.lateralAllowed and
      native.pandaInventory and native_inventory_matches_cp(native, cp) and
      0 < native.observedMonoTime <= now_ns <= native.validUntilMonoTime)
  except (AttributeError, KeyError, IndexError, TypeError, ValueError):
    return False


def seatbelt_lateral_soft_event_allowed(cp, cs, intent, native, event, *, source_ns, now_ns, axis_session_id) -> bool:
  """The qualified saved LAT owner treats only its ordinary belt event as a LONG lock."""
  if not qualified_gm(cp):
    return False
  from opendbc.car.gm.values import is_bolt_present_no_acc_pedal_profile
  from opendbc.car.structs import car
  from openpilot.cereal import log
  from openpilot.starpilot.aol.runtime import AXIS_MAX_AGE_NS, SAFETY_MAX_AGE_NS, native_inventory_matches_cp
  try:
    return bool(is_bolt_present_no_acc_pedal_profile(cp) and
      int(cp.alternativeExperience) == GM_AOL_ALTERNATIVE_EXPERIENCE and
      event.name == log.OnroadEvent.EventName.seatbeltNotLatched and event.softDisable and
      event.noEntry and not event.immediateDisable and not event.userDisable and
      cs.seatbeltUnlatched and cs.canValid and not cs.canTimeout and not cs.accFaulted and not cs.doorOpen and
      not cs.steerFaultTemporary and not cs.steerFaultPermanent and cs.cruiseState.available and
      cs.gearShifter in (car.CarState.GearShifter.drive, car.CarState.GearShifter.low,
                        car.CarState.GearShifter.sport, car.CarState.GearShifter.brake) and
      intent is not None and intent.settingsQualified and intent.allowedLatch and intent.lateralArmed and
      intent.producerSessionId and intent.carStateLogMonoTime == source_ns and
      0 < source_ns <= intent.observedMonoTime <= now_ns <= intent.validUntilMonoTime and
      now_ns - source_ns <= AXIS_MAX_AGE_NS and
      intent.validUntilMonoTime - intent.observedMonoTime <= SAFETY_MAX_AGE_NS and
      native is not None and native.compatible and int(native.protocolVersion) == 1 and
      axis_session_id and native.axisSessionId == axis_session_id and
      native.requestedLateral and native.lateralAllowed and native.pandaInventory and
      native_inventory_matches_cp(native, cp) and
      0 < native.observedMonoTime <= now_ns <= native.validUntilMonoTime and
      native.validUntilMonoTime - native.observedMonoTime <= SAFETY_MAX_AGE_NS)
  except (AttributeError, KeyError, IndexError, TypeError, ValueError):
    return False
