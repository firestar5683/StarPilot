"""GM-owned AOL capabilities; exact CP admission lives with the vehicle."""

import math

from opendbc.car.structs import CarParams
from opendbc.car.gm.values import CAR, control_flags, camera_acc_pedal_profile, is_volt_ascm_longitudinal
from opendbc.car.gm.aol import GM_AOL_ALTERNATIVE_EXPERIENCE, GM_AOL_WORDS, qualified_gm
from openpilot.starpilot.aol.policy import AolVehiclePolicy
from openpilot.starpilot.aol.intent import AolCardIntent


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

  def __init__(self, settings):
    super().__init__(settings, lkas_button_supported=False)
    self.requires_fault_observation = True
    self._main_cycle_required = False

  def update(self, CS, *, consumed_buttons=frozenset(), fault_active=None,
             now_ns=0, native_rejection_ns=0, standard_enabled=False):
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


def create_intent(cp, settings):
  return GmAolCardIntent(settings) if qualified_gm(cp) else None


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


def intent_disarming_fault(cp, events, state, **context):
  """An ASCM Volt ACC fault withdraws axes without erasing main-armed intent."""
  from openpilot.cereal import log
  from openpilot.starpilot.aol.intent import disarming_fault
  if qualified_gm(cp):
    availability = (log.OnroadEvent.EventName.commIssue, log.OnroadEvent.EventName.commIssueAvgFreq)
    # Availability withdraws current axes; only critical faults erase main-following intent.
    events = [event for event in events if not
              (event.name in availability and event.softDisable and not event.immediateDisable)]
  if qualified_gm(cp) and camera_acc_pedal_profile(cp) is None and is_volt_ascm_longitudinal(cp):
    events = [event for event in events if event.name != log.OnroadEvent.EventName.accFaulted]
  return disarming_fault(events, state, **context)


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
      cs.accFaulted or cs.seatbeltUnlatched or cs.doorOpen or not cs.cruiseState.available or
      cs.gearShifter not in (car.CarState.GearShifter.drive, car.CarState.GearShifter.low,
                            car.CarState.GearShifter.sport, car.CarState.GearShifter.brake) or
      str(axis.faultReason) != 'none' or not axis.desiredLateral or not axis.lateralActive or
      not axis.nativeAcknowledged or
      not 0 < axis.sourceCarStateMonoTime <= axis.observedMonoTime <= now_ns or
      now_ns - axis.sourceCarStateMonoTime > AXIS_MAX_AGE_NS):
    return None
  event_ns = int(sm.logMonoTime['onroadEvents'])
  if (not sm.seen['onroadEvents'] or not sm.valid['onroadEvents'] or not sm.alive['onroadEvents'] or
      not 0 < event_ns <= now_ns or now_ns - event_ns > 1_500_000_000 or
      any(e.immediateDisable or e.softDisable for e in sm['onroadEvents'])):
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
