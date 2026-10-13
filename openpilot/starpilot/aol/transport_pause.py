"""Reason-qualified intent retention; this module never grants an axis."""
from openpilot.cereal import log
from openpilot.starpilot.aol.runtime import AXIS_MAX_AGE_NS, SAFETY_MAX_AGE_NS, current_native, native_inventory_matches_cp
from openpilot.starpilot.aol.wire import SafetyState, decode_intent


def cp_identity(cp):
  return (str(cp.brand), str(cp.carFingerprint), int(cp.flags), int(cp.alternativeExperience),
          bool(cp.passive), bool(cp.dashcamOnly), bool(cp.notCar),
          bool(cp.openpilotLongitudinalControl), bool(cp.pcmCruise),
          tuple((int(c.safetyModel.raw), int(c.safetyParam)) for c in cp.safetyConfigs))


def _configured_transport_native(sm, cp, session, now_ns, native=None, *, require_longitudinal=True):
  """Validate the exact live native configuration and every Panda."""
  try:
    validated_here = native is None
    native = native or current_native(sm, cp, now_ns=now_ns, axis_session_id=session)
    if (not session or native is None or str(native.axisSessionId) != session or
        native.requestedLateral and not native.lateralAllowed or
        require_longitudinal and native.requestedLongitudinal and not native.longitudinalAllowed):
      return None
    coherent = bool(native.pandaInventory)
    if coherent and (int(sm.logMonoTime['aolSafetyWire']) != native.observedMonoTime or
                     not 0 < native.observedMonoTime <= now_ns <= native.validUntilMonoTime or
                     now_ns - native.observedMonoTime > SAFETY_MAX_AGE_NS or
                     native.validUntilMonoTime - native.observedMonoTime > SAFETY_MAX_AGE_NS):
      return None
    # current_native already checked this exact inventory in this call.
    # Supplied native values still need structural validation here.
    if coherent and (not validated_here and not native_inventory_matches_cp(native, cp) or
                     any(p.safetyRxChecksInvalid or p.heartbeatLost or p.faults or
                         (require_longitudinal and native.requestedLongitudinal and str(config.safetyModel) not in ('silent', 'noOutput') and
                          not p.controlsAllowed)
                         for p, config in zip(native.pandaInventory, cp.safetyConfigs, strict=True))):
      return None
    # v2 carries exact producer-read health under its monotonic 200ms lease.
    # The independently conflated BOOTTIME PandaStates is a latest veto only.
    stamp = int(sm.logMonoTime['pandaStates'])
    if not (sm.seen['pandaStates'] and sm.valid['pandaStates'] and sm.alive['pandaStates'] and
            stamp > 0 and (coherent or stamp <= now_ns and now_ns - stamp <= SAFETY_MAX_AGE_NS)):
      return None
    pandas = sm['pandaStates']
    if not cp.safetyConfigs or len(pandas) != len(cp.safetyConfigs):
      return None
    return native if all(int(p.safetyModel.raw) == int(c.safetyModel.raw) and p.safetyParam == c.safetyParam and
               p.alternativeExperience == cp.alternativeExperience and not p.safetyRxChecksInvalid and
               not p.heartbeatLost and not p.faults and
               (not require_longitudinal or not native.requestedLongitudinal or str(c.safetyModel) in ('silent', 'noOutput') or p.controlsAllowed)
               for p, c in zip(pandas, cp.safetyConfigs, strict=True)) else None
  except (AttributeError, KeyError, IndexError, TypeError, ValueError):
    return None


def _healthy_transport_native(sm, cp, cs, session, now_ns, native=None, *, require_longitudinal=True):
  """Require both current vehicle health and the exact live native configuration."""
  try:
    if not cs.canValid or cs.canTimeout or cs.steerFaultTemporary or cs.steerFaultPermanent:
      return None
    return _configured_transport_native(sm, cp, session, now_ns, native,
                                        require_longitudinal=require_longitudinal)
  except (AttributeError, KeyError, IndexError, TypeError, ValueError):
    return None


def independent_lateral_health(sm, cp, cs, session, now_ns):
  """Structural health for retaining LAT intent; never grant either output axis."""
  native = _healthy_transport_native(sm, cp, cs, session, now_ns, require_longitudinal=False)
  return native if native is not None and native.requestedLateral and native.lateralAllowed else None


def healthy_transport(sm, cp, cs, session, now_ns, native=None):
  """Require the live, exact native configuration, including every Panda."""
  return _healthy_transport_native(sm, cp, cs, session, now_ns, native) is not None


AVAILABILITY_EVENTS = (log.OnroadEvent.EventName.commIssue, log.OnroadEvent.EventName.commIssueAvgFreq)


def availability_only(events):
  faults = [event for event in events if event.immediateDisable or event.softDisable]
  return bool(faults and all(event.name in AVAILABILITY_EVENTS and event.softDisable and
                            not event.immediateDisable for event in faults))


HOST_SOURCE_AVAILABILITY_EVENTS = (*AVAILABILITY_EVENTS, log.OnroadEvent.EventName.selfdrivedLagging)


def host_source_availability_only(events):
  """Closed host SOFT set for qualified inactive source-zero intent only."""
  faults = [event for event in events if event.immediateDisable or event.softDisable]
  return bool(faults and not any(event.userDisable for event in events) and
              all(event.name in HOST_SOURCE_AVAILABILITY_EVENTS and event.softDisable and
                  not event.immediateDisable for event in faults))


class AvailabilityPause:
  """Retain an accepted armed producer; this proof never enables output."""
  def __init__(self, cp, session):
    self.cp, self.session = cp_identity(cp), session
    self.producer = ''
    self.epoch = None
    self.inventory = None
    self.native_ns = 0
    self.baseline_ns = 0
    self.active = False

  def observe(self, *, cp, session, sm, cs, native, now_ns, companion, intent,
              events, model_ready, source_current, prior_lateral_active, hard_fault, healthy_native, source_expired=False):
    try:
      healthy = healthy_native
      eligible = bool(cp_identity(cp) == self.cp and
        session == self.session and not hard_fault and model_ready and (source_current or source_expired) and companion is not None and
        companion.last_drain_ok and intent is not None and intent.allowedLatch and intent.lateralArmed and
        healthy is not None and healthy.requestedLateral and healthy.lateralAllowed and healthy.pandaInventory)
      if not eligible:
        self.active = False
        self.baseline_ns = 0
        return False
      if source_expired:
        latest = companion.latest
        raw = latest[2] if latest is not None and latest[1] else None
        verified = companion.verified_sm_projection
        sm_intent = decode_intent(sm['aolIntentWire'])
        projection = bool(verified is not None and int(sm.logMonoTime['aolIntentWire']) == verified[0] and
          verified[2] == companion.integrity_epoch and verified[3] == companion.session and
          sm_intent == verified[1] and 0 < verified[0] <= now_ns <= verified[0] + SAFETY_MAX_AGE_NS and
          sm_intent.settingsQualified and sm_intent.allowedLatch and sm_intent.lateralArmed and
          sm_intent.producerSessionId == intent.producerSessionId)
        if (raw is None or not raw.settingsQualified or not raw.allowedLatch or not raw.lateralArmed or
            raw.producerSessionId != intent.producerSessionId or
            not 0 < intent.carStateLogMonoTime <= now_ns or
            now_ns - intent.carStateLogMonoTime > SAFETY_MAX_AGE_NS or
            not 0 < raw.carStateLogMonoTime <= now_ns or raw.observedMonoTime > now_ns or
            now_ns - raw.carStateLogMonoTime > SAFETY_MAX_AGE_NS or
            (int(sm.logMonoTime['aolIntentWire']) != raw.carStateLogMonoTime and not projection) or
            not sm.seen['aolIntentWire'] or not sm.valid['aolIntentWire'] or not sm.alive['aolIntentWire']):
          self.active = False
          return False
      inventory = (healthy.pandaSerial, tuple(p.hardwareSerial for p in healthy.pandaInventory))
      faults = [event for event in events if event.immediateDisable or event.softDisable]
      if not faults:
        recovery_handoff = bool(self.active and source_current and not source_expired and self.baseline_ns > 0 and
          self.producer == intent.producerSessionId and self.epoch == companion.integrity_epoch and
          self.inventory == inventory and healthy.observedMonoTime >= self.native_ns)
        self.active = False
        if prior_lateral_active or recovery_handoff:
          self.producer, self.epoch = intent.producerSessionId, companion.integrity_epoch
          self.inventory, self.native_ns, self.baseline_ns = inventory, healthy.observedMonoTime, now_ns
        return False
      matched = bool(availability_only(events) and self.producer == intent.producerSessionId and
        self.epoch == companion.integrity_epoch and self.inventory == inventory and
        healthy.observedMonoTime >= self.native_ns and self.baseline_ns > 0 and
        (self.active or 0 <= now_ns - self.baseline_ns <=
         (SAFETY_MAX_AGE_NS if source_expired else AXIS_MAX_AGE_NS)))
      self.active = matched
      if matched:
        self.native_ns = healthy.observedMonoTime
      else:
        self.baseline_ns = 0
      return matched
    except (AttributeError, KeyError, IndexError, TypeError, ValueError):
      self.active = False
      self.baseline_ns = 0
      return False


class TransportPause:
  def __init__(self, cp, session):
    self.cp = cp_identity(cp)
    self.session = session
    self.active = False
    self.producer = ''
    self.epoch = None

  def observe(self, *, cp, session, sm, cs, native, now_ns, companion, previous_intent,
              intent, expired_healthy_source, previously_active, hard_fault, model_ready, user_disable):
    """Return (temporary inhibit, hard upgrade); require a prior accepted pair."""
    # Overwritten on every observation; consumed only by the adjacent producer.
    self.observed_native = None
    context_current = bool(cp_identity(cp) == self.cp and session == self.session and model_ready and companion is not None)
    if context_current:
      self.observed_native = _healthy_transport_native(sm, cp, cs, session, now_ns, native)
    eligible = bool(context_current and not hard_fault and self.observed_native is not None)
    latest = companion.latest if companion is not None else None
    raw = decode_intent(sm['aolIntentWire']) if sm.seen.get('aolIntentWire', False) else None
    previous = previous_intent
    producer = self.producer if self.active else str(previous.producerSessionId) if previous is not None else ''
    eligible = bool(eligible and latest is not None and latest[1] and raw is not None and
                    sm.valid['aolIntentWire'] and sm.alive['aolIntentWire'] and
                    raw.settingsQualified and raw.producerSessionId == producer and
                    latest[2].producerSessionId == producer and
                    int(sm.logMonoTime['aolIntentWire']) == raw.carStateLogMonoTime and
                    0 < raw.carStateLogMonoTime <= now_ns and raw.observedMonoTime <= now_ns and
                    (self.epoch is None or self.epoch == companion.integrity_epoch))
    if self.active:
      if not eligible:
        self.active = False
        return False, True
      if user_disable or intent is not None and not intent.allowedLatch:
        self.active = False
        self.epoch = companion.integrity_epoch
        return False, False
      return True, False
    if (eligible and expired_healthy_source and previously_active and previous is not None and
        previous.allowedLatch and previous.lateralArmed and raw.allowedLatch and raw.lateralArmed and
        not user_disable):
      self.active = True
      self.producer = producer
      self.epoch = companion.integrity_epoch
      return True, False
    if intent is not None and companion is not None:
      self.epoch = companion.integrity_epoch
    return False, False


class TransportPauseFeedback:
  """Card accepts pause provenance only after a healthy same-session baseline."""
  def __init__(self, cp):
    self.cp = cp_identity(cp)
    self.session = ''
    self.sequence = 0
    self.signature = None
    self.paused = False
    self.qualified = False
    self.pending_event = 0
    self.awaiting = False
    self.failed = False
    self.lateral_baseline_ns = 0
    self.lateral_source_ns = 0
    self.lateral_inventory = None
    self.lateral_native_ns = 0
    self.longitudinal_cancel_ns = 0
    self.last_cancel_source_ns = 0
    self.honda_brake_ns = 0
    self.gm_withdrawal_ns = 0
    self.retention_qualified = False
    self.retention_pending = False
    self.retention_event_ns = 0
    self.retention_started_ns = 0
    self.retention_verified = False
    self.availability_producer = ''
    self.availability_epoch = None
    self.source_retention_started_ns = 0
    self.healthy_feedback_ns = 0
    self.healthy_native_ns = 0
    self.healthy_inventory = None

  def _temporary_lag_intent_current(self, sm, cp, cs, axis, stamp, now_ns, *, latched, producer, signature):
    """Retain intent only through isolated lag or its bounded critical/event join."""
    reason = str(axis.faultReason)
    events = sm['onroadEvents']
    faults = [event for event in events if event.immediateDisable or event.softDisable]
    isolated = bool(len(faults) == 1 and faults[0].name == log.OnroadEvent.EventName.selfdrivedLagging and
                    faults[0].softDisable and not faults[0].immediateDisable)
    # Healthy cycles never reach policy/native/provenance work. A critical
    # proof can precede its event, but cannot yet establish a lag exemption.
    if not isolated and (reason != 'critical' or faults):
      return False
    previous = self.signature
    joining = bool(self.pending_event and previous is not None and previous[5] == 'critical' and
                   previous[6] == self.pending_event)
    if (not latched or self.failed or self.paused or self.pending_event and not joining or self.retention_started_ns or
        not self.session or str(axis.sessionId) != self.session or reason not in ('none', 'critical') or
        not producer or producer != self.availability_producer or
        str(getattr(axis, 'intentProducerSessionId', '')) != producer or
        int(getattr(axis, 'intentIntegrityEpoch', 0)) != self.availability_epoch or
        not self.lateral_baseline_ns or not self.lateral_inventory or
        not cs.canValid or cs.canTimeout or cs.steerFaultTemporary or cs.steerFaultPermanent or cs.accFaulted or
        not 0 < axis.sourceCarStateMonoTime <= stamp <= now_ns or
        now_ns - axis.sourceCarStateMonoTime > AXIS_MAX_AGE_NS):
      return False
    event_ns = int(sm.logMonoTime['onroadEvents'])
    if (not sm.seen['onroadEvents'] or not sm.valid['onroadEvents'] or not sm.alive['onroadEvents'] or
        not 0 < event_ns <= now_ns or now_ns - event_ns > 1_500_000_000 or
        any(event.userDisable for event in events) or joining and
          (axis.faultEventMonoTime != self.pending_event or now_ns - self.pending_event > AXIS_MAX_AGE_NS)):
      return False
    withdrawn = bool(reason == 'critical' and not axis.desiredLateral and not axis.desiredLongitudinal and
                     not axis.lateralActive and not axis.longitudinalActive)
    matched = bool(withdrawn and isolated and axis.faultEventMonoTime == event_ns <= stamp)
    held_original = bool(reason == 'none' and isolated and signature == previous and
      axis.desiredLateral and axis.lateralActive and axis.nativeAcknowledged and
      0 < axis.faultEventMonoTime < event_ns and now_ns - event_ns <= AXIS_MAX_AGE_NS)
    known_lag = bool(isolated and previous is not None and previous[5] == 'critical' and previous[6] == event_ns)
    pending = bool(withdrawn and event_ns < axis.faultEventMonoTime <= stamp and
      now_ns - axis.faultEventMonoTime <= AXIS_MAX_AGE_NS and
      (joining or known_lag or not faults and previous is not None and previous[5] == 'none' and
       0 <= now_ns - self.lateral_baseline_ns <= AXIS_MAX_AGE_NS))
    if not (matched or held_original or pending):
      return False
    from openpilot.starpilot.aol.vehicle import policy_for
    if not policy_for(cp).intent_supported:
      return False
    native = _healthy_transport_native(sm, cp, cs, self.session, now_ns)
    if (native is None or not native.pandaInventory or
        held_original and not (native.requestedLateral and native.lateralAllowed) or
        native.observedMonoTime < self.lateral_native_ns or
        (native.pandaSerial, tuple(p.hardwareSerial for p in native.pandaInventory)) != self.lateral_inventory):
      return False
    if pending:
      if not self.pending_event:
        self.pending_event = int(axis.faultEventMonoTime)
      self.awaiting = True
    elif joining:
      self.pending_event = 0
    return True

  def _temporary_steering_intent_current(self, sm, cp, cs, axis, stamp, now_ns, *, latched, producer, signature):
    """Keep an existing armed intent during isolated temporary EPS withdrawal."""
    if (not latched or self.failed or self.paused or self.pending_event or self.retention_started_ns or
        not self.session or str(axis.sessionId) != self.session or not cs.steerFaultTemporary or
        cs.steerFaultPermanent or not cs.canValid or cs.canTimeout or
        str(axis.faultReason) != 'none' or
        not producer or producer != self.availability_producer or
        str(getattr(axis, 'intentProducerSessionId', '')) != producer or
        int(getattr(axis, 'intentIntegrityEpoch', 0)) != self.availability_epoch or
        not self.lateral_baseline_ns or not self.lateral_inventory or
        not 0 < axis.sourceCarStateMonoTime <= stamp <= now_ns or
        now_ns - axis.sourceCarStateMonoTime > AXIS_MAX_AGE_NS):
      return False
    withdrawn = not axis.desiredLateral and not axis.lateralActive
    # Card can parse the first temporary EPS sample before SD publishes its
    # withdrawal. Retain only the already accepted original proof, still inside
    # its original source/output lease; never synthesize a new output grant.
    held_original = bool(axis.desiredLateral and axis.lateralActive and axis.nativeAcknowledged and
                         signature == self.signature)
    if not withdrawn and not held_original:
      return False
    event_ns = int(sm.logMonoTime['onroadEvents'])
    events = sm['onroadEvents']
    temporary_names = (log.OnroadEvent.EventName.steerTempUnavailable,
                       log.OnroadEvent.EventName.steerTempUnavailableSilent)
    if (not sm.seen['onroadEvents'] or not sm.valid['onroadEvents'] or not sm.alive['onroadEvents'] or
        not 0 < event_ns <= now_ns or now_ns - event_ns > 1_500_000_000 or
        any(event.immediateDisable or event.softDisable and event.name != temporary_names[0] for event in events)):
      return False
    temporary_event = any(event.name in temporary_names for event in events)
    if withdrawn and not (temporary_event and axis.faultEventMonoTime == event_ns <= stamp):
      return False
    if held_original and not (
        axis.faultEventMonoTime == event_ns <= stamp and not any(event.softDisable for event in events) or
        temporary_event and 0 < axis.faultEventMonoTime < event_ns and now_ns - event_ns <= AXIS_MAX_AGE_NS):
      return False
    # This exception validates intent only. The normal vehicle-health helper
    # continues to reject temporary EPS for transport and availability proofs.
    native = _configured_transport_native(sm, cp, self.session, now_ns)
    if (native is None or not native.pandaInventory or
        held_original and not (native.requestedLateral and native.lateralAllowed) or
        axis.longitudinalActive and not native.longitudinalAllowed or
        native.observedMonoTime < self.lateral_native_ns or
        (native.pandaSerial, tuple(p.hardwareSerial for p in native.pandaInventory)) != self.lateral_inventory):
      return False
    return True

  def _honda_brake_lateral_current(self, sm, cp, cs, axis, now_ns, *, latched, brake_source_ns):
    """Preserve existing LAT intent through brake's LONG withdrawal, never output."""
    from opendbc.car.honda.stock_aol import qualified
    from opendbc.car.structs import car

    source_ns = self.honda_brake_ns or (brake_source_ns if cs.brakePressed else 0)
    if (not qualified(cp, marked_only=True) or not latched or self.failed or self.paused or self.pending_event or
        not self.session or str(axis.sessionId) != self.session or
        not self.healthy_feedback_ns or not 0 <= now_ns - self.healthy_feedback_ns <= AXIS_MAX_AGE_NS or
        not 0 < source_ns <= now_ns or now_ns - source_ns > SAFETY_MAX_AGE_NS or
        (not self.honda_brake_ns and now_ns - source_ns > AXIS_MAX_AGE_NS) or
        cs.accFaulted or cs.seatbeltUnlatched or
        cs.gearShifter not in (car.CarState.GearShifter.drive, car.CarState.GearShifter.sport,
                              car.CarState.GearShifter.low, car.CarState.GearShifter.brake) or
        str(axis.faultReason) != 'none' or not axis.desiredLateral or not axis.lateralActive or
        (not axis.nativeAcknowledged and (axis.desiredLongitudinal or axis.longitudinalActive)) or
        not 0 < axis.sourceCarStateMonoTime <= axis.observedMonoTime or
        axis.observedMonoTime - axis.sourceCarStateMonoTime > AXIS_MAX_AGE_NS):
      return None
    event_ns = int(sm.logMonoTime['onroadEvents'])
    if (not sm.seen['onroadEvents'] or not sm.valid['onroadEvents'] or not sm.alive['onroadEvents'] or
        not 0 < event_ns <= now_ns or now_ns - event_ns > 1_500_000_000 or
        any(e.immediateDisable or e.softDisable for e in sm['onroadEvents'])):
      return None
    native = independent_lateral_health(sm, cp, cs, self.session, now_ns)
    if (native is None or not native.requestedLateral or not native.lateralAllowed or
        not native.requestedLongitudinal or native.observedMonoTime < self.healthy_native_ns or
        (native.pandaSerial, tuple(p.hardwareSerial for p in native.pandaInventory)) != self.healthy_inventory):
      return None
    self.honda_brake_ns = source_ns
    return native

  def _longitudinal_cancel_current(self, sm, cp, cs, axis, now_ns, *, latched, cancel_source_ns, withdrawal_required=True) -> SafetyState | None:
    """Retain existing intent during Cancel's bounded LONG withdrawal handshake."""
    from opendbc.car.hyundai.ev6_aol import qualified
    from opendbc.car.structs import car

    if (not latched or self.failed or self.paused or self.pending_event or
        not self.session or str(axis.sessionId) != self.session or not qualified(cp, marked_only=True) or
        not self.lateral_baseline_ns or not 0 <= now_ns - self.lateral_baseline_ns <= AXIS_MAX_AGE_NS or
        str(axis.faultReason) != 'none' or not axis.nativeAcknowledged or
        not axis.desiredLateral or not axis.lateralActive or cs.accFaulted or
        not cs.canValid or cs.canTimeout or cs.steerFaultTemporary or cs.steerFaultPermanent):
      return None
    cancel = any(e.type == car.CarState.ButtonEvent.Type.cancel and e.pressed for e in cs.buttonEvents)
    fresh_cancel = bool(cancel and self.last_cancel_source_ns < cancel_source_ns <= now_ns and
                        now_ns - cancel_source_ns <= AXIS_MAX_AGE_NS)
    if not self.longitudinal_cancel_ns and not fresh_cancel:
      return None
    if not withdrawal_required and (self.longitudinal_cancel_ns or not fresh_cancel):
      return None
    if self.longitudinal_cancel_ns and not 0 <= now_ns - self.longitudinal_cancel_ns <= SAFETY_MAX_AGE_NS:
      return None
    event_ns = int(sm.logMonoTime['onroadEvents'])
    if (not sm.seen['onroadEvents'] or not sm.valid['onroadEvents'] or not sm.alive['onroadEvents'] or
        not 0 < event_ns <= now_ns or now_ns - event_ns > 1_500_000_000 or
        any(e.immediateDisable or e.softDisable for e in sm['onroadEvents'])):
      return None
    native = current_native(sm, cp, now_ns=now_ns, axis_session_id=self.session)
    if (native is None or not native.pandaInventory or not native.requestedLateral or not native.lateralAllowed or
        not native.requestedLongitudinal or withdrawal_required and native.longitudinalAllowed or
        native.observedMonoTime < self.lateral_native_ns or
        not native_inventory_matches_cp(native, cp) or
        (native.pandaSerial, tuple(p.hardwareSerial for p in native.pandaInventory)) != self.lateral_inventory):
      return None
    stamp = int(sm.logMonoTime['pandaStates'])
    pandas = sm['pandaStates']
    if (not sm.seen['pandaStates'] or not sm.valid['pandaStates'] or not sm.alive['pandaStates'] or stamp <= 0 or
        len(pandas) != len(cp.safetyConfigs)):
      return None
    # controlsAllowed represents the withdrawn normal/LONG axis here. Preserve
    # every latest raw configuration/fault veto and exact producer-read inventory.
    current_pandas = all(int(p.safetyModel.raw) == int(c.safetyModel.raw) and p.safetyParam == c.safetyParam and
                         p.alternativeExperience == cp.alternativeExperience and not p.safetyRxChecksInvalid and
                         not p.heartbeatLost and not p.faults and
                         (str(c.safetyModel) not in ('silent', 'noOutput') or not p.controlsAllowed)
                         for p, c in zip(pandas, cp.safetyConfigs, strict=True))
    return native if current_pandas else None


  def _availability_retention(self, sm, cp, cs, axis, stamp, now_ns, *, latched, current, continuity, intent_producer_session):
    reason = str(axis.faultReason)
    events = sm['onroadEvents']
    if reason not in ('none', 'availabilityPause') or reason == 'none' and not availability_only(events):
      return False
    if not (latched and current and continuity and not self.paused and not self.pending_event and
            cp_identity(cp) == self.cp and intent_producer_session and
            getattr(axis, 'intentProducerSessionId', '') == intent_producer_session == self.availability_producer and
            int(getattr(axis, 'intentIntegrityEpoch', 0)) == self.availability_epoch and
            self.session and
            self.lateral_inventory and axis.desiredLateral and
            (str(axis.faultReason) == 'none' or not axis.desiredLongitudinal) and
            axis.nativeAcknowledged and (
              0 < axis.sourceCarStateMonoTime <= stamp and stamp - axis.sourceCarStateMonoTime <= AXIS_MAX_AGE_NS or
              reason == 'availabilityPause' and axis.sourceCarStateMonoTime == 0 and
              not axis.lateralActive and not axis.longitudinalActive)):
      return False
    native = _healthy_transport_native(sm, cp, cs, str(axis.sessionId), now_ns)
    if (native is None or not native.requestedLateral or not native.lateralAllowed or
        native.observedMonoTime < self.lateral_native_ns or
        (native.pandaSerial, tuple(p.hardwareSerial for p in native.pandaInventory)) != self.lateral_inventory):
      return False
    event_ns = int(sm.logMonoTime['onroadEvents'])
    faults = [event for event in events if event.immediateDisable or event.softDisable]
    live_event = bool(sm.valid['onroadEvents'] and sm.alive['onroadEvents'] and
                      0 < event_ns <= now_ns and now_ns - event_ns <= 1_500_000_000)
    host_source_off = bool(reason == 'availabilityPause' and axis.sourceCarStateMonoTime == 0 and
                           not axis.lateralActive and not axis.longitudinalActive)
    issue = live_event and (availability_only(events) or host_source_off and host_source_availability_only(events))
    if reason not in ('none', 'availabilityPause') or faults and not issue:
      return False
    typed = bool(reason == 'availabilityPause' and not axis.lateralActive and not axis.longitudinalActive and
                 0 < axis.faultEventMonoTime <= stamp)
    source_expired = bool(typed and axis.sourceCarStateMonoTime == 0)
    # The 200ms original source bound admits an initial episode, never an
    # active command. Once its exact event/proof pair was verified, continuing
    # fresh OFF source-zero proofs may retain driver intent with a CURRENT real
    # native LAT grant and the same producer/epoch/configuration/inventory.
    # Missing/mismatched events still use the unchanged fixed 30ms join below;
    # every other output/source/native deadline and branch remains unchanged.
    continuing_intent = bool(source_expired and self.retention_verified and issue)
    if source_expired and not (0 < self.lateral_source_ns <= now_ns and
        (now_ns <= self.lateral_source_ns + SAFETY_MAX_AGE_NS or continuing_intent)):
      return False
    baseline_age_limit = SAFETY_MAX_AGE_NS if source_expired else AXIS_MAX_AGE_NS
    matched = typed and issue and axis.faultEventMonoTime == event_ns
    occurrence = max(int(axis.faultEventMonoTime) if typed else 0, event_ns if issue else 0)
    if not occurrence or occurrence < self.retention_event_ns:
      return False
    if matched:
      if not self.retention_verified and not 0 <= now_ns - self.lateral_baseline_ns <= baseline_age_limit:
        return False
      if self.retention_started_ns and now_ns - self.retention_started_ns > AXIS_MAX_AGE_NS:
        return False
      self.retention_verified = True
      self.retention_started_ns = 0
      self.retention_event_ns = occurrence
    else:
      if not self.retention_started_ns:
        if not self.retention_verified and not 0 <= now_ns - self.lateral_baseline_ns <= baseline_age_limit:
          return False
        self.retention_started_ns = now_ns
        self.retention_event_ns = occurrence
      if occurrence != self.retention_event_ns or now_ns - self.retention_started_ns > AXIS_MAX_AGE_NS:
        return False
    self.retention_qualified, self.retention_pending = matched, not matched
    self.lateral_native_ns = native.observedMonoTime
    return True

  def _availability_recovery_current(self, sm, cp, cs, axis, stamp, now_ns, *, latched, current, continuity, producer):
    """Join a verified pause's healthy recovery pair; this never grants output."""
    event_ns = int(sm.logMonoTime['onroadEvents'])
    if (not latched or self.failed or self.paused or self.pending_event or not self.retention_verified or
        not self.retention_started_ns or not 0 <= now_ns - self.retention_started_ns <= AXIS_MAX_AGE_NS or
        not current or not continuity or str(axis.sessionId) != self.session or
        not producer or producer != self.availability_producer or
        str(getattr(axis, 'intentProducerSessionId', '')) != producer or
        int(getattr(axis, 'intentIntegrityEpoch', 0)) != self.availability_epoch or
        str(axis.faultReason) != 'none' or not axis.nativeAcknowledged or
        not axis.desiredLateral or not axis.lateralActive or
        not 0 < axis.sourceCarStateMonoTime <= stamp <= now_ns or
        now_ns - axis.sourceCarStateMonoTime > AXIS_MAX_AGE_NS or
        not sm.seen['onroadEvents'] or not sm.valid['onroadEvents'] or not sm.alive['onroadEvents'] or
        not 0 < event_ns == axis.faultEventMonoTime <= stamp):
      return False
    events = sm['onroadEvents']
    faults = [event for event in events if event.userDisable or event.softDisable or event.immediateDisable]
    combined = bool(axis.desiredLongitudinal and axis.longitudinalActive)
    if combined:
      # An event-first receiver has already recorded this NEW occurrence while
      # holding the verified inactive source-zero pause. Close that exact join;
      # neither the pending deadline nor any old command lease is renewed.
      previous = self.signature
      if (previous is None or previous[0] != self.session or previous[5] != 'availabilityPause' or
          previous[7] != self.session or previous[8] != 0 or previous[9] or previous[10] or
          not previous[11] or previous[12] or not previous[13] or
          previous[14] != producer or previous[15] != self.availability_epoch or
          not 0 < previous[6] < event_ns or self.retention_event_ns != event_ns or
          len(faults) != 1 or faults[0].name != log.OnroadEvent.EventName.selfdrivedLagging or
          not faults[0].softDisable or faults[0].userDisable or faults[0].immediateDisable or
          any(event.noEntry and event.name != log.OnroadEvent.EventName.selfdrivedLagging for event in events)):
        return False
    elif (axis.desiredLongitudinal or axis.longitudinalActive or
          not self.retention_event_ns < event_ns or faults):
      return False
    native = _healthy_transport_native(sm, cp, cs, self.session, now_ns)
    return bool(native is not None and native.requestedLateral and native.lateralAllowed and
      (not combined or native.requestedLongitudinal and native.longitudinalAllowed) and
      native.observedMonoTime >= self.lateral_native_ns and
      (native.pandaSerial, tuple(p.hardwareSerial for p in native.pandaInventory)) == self.lateral_inventory)

  def _new_expired_combined_source(self, sm, cp, axis, stamp, now_ns, signature):
    """An established combined producer advanced while Card missed its output lease."""
    previous = self.signature
    if (now_ns <= signature[4] or previous is None or self.retention_started_ns or
        not (sm.seen['aolAxisState'] and sm.valid['aolAxisState'] and sm.alive['aolAxisState']) or
        not axis.desiredLongitudinal or not axis.longitudinalActive or
        not all(previous[index] for index in (9, 10, 11, 12, 13)) or previous[5] != 'none' or
        signature[1] <= self.sequence or stamp <= previous[2] or
        not 0 < self.lateral_source_ns <= previous[8] < signature[8] <= stamp or
        stamp - signature[8] > AXIS_MAX_AGE_NS or
        signature[4] != stamp + AXIS_MAX_AGE_NS):
      return False
    # Only this missed, already-expired Ioniq6 combined proof needs the extra
    # path. Its original source/native retention clocks are checked below and
    # never advanced; this function supplies no current output or LONG enable.
    from openpilot.starpilot.car.hyundai.aol import qualified_ioniq6
    return qualified_ioniq6(cp)

  def _source_availability_retention(self, sm, cp, cs, axis, stamp, now_ns, *, latched, continuity, producer, signature):
    # Output freshness withdraws commands, not previously accepted driver intent.
    # Held output or a strictly forward, initially fresh combined proof may
    # retain only an already established intent under its original bounds.
    held = bool(signature == self.signature and not self.retention_started_ns)
    output_missing = not (sm.seen['aolAxisState'] and sm.valid['aolAxisState'] and sm.alive['aolAxisState'])
    if (not latched or self.failed or self.paused or self.pending_event or not self.session or
        cp_identity(cp) != self.cp or not continuity or
        str(axis.sessionId) != self.session or str(axis.faultSessionId) != self.session or
        str(axis.faultReason) != 'none' or not axis.qualified or not axis.nativeAcknowledged or
        not axis.desiredLateral or not axis.lateralActive or
        (axis.desiredLongitudinal or axis.longitudinalActive) and not held and
          not self._new_expired_combined_source(sm, cp, axis, stamp, now_ns, signature) or
        (not sm.seen['aolAxisState'] or not sm.valid['aolAxisState']) and not held or
        int(axis.observedMonoTime) != stamp or not 0 < axis.sourceCarStateMonoTime <= stamp <= now_ns or
        not 0 <= axis.validUntilMonoTime - stamp <= AXIS_MAX_AGE_NS or
        now_ns - axis.sourceCarStateMonoTime > SAFETY_MAX_AGE_NS or
        not (stamp - axis.sourceCarStateMonoTime > AXIS_MAX_AGE_NS or now_ns > axis.validUntilMonoTime or
             held and output_missing) or
        not producer or getattr(axis, 'intentProducerSessionId', '') != producer or
        producer != self.availability_producer or
        int(getattr(axis, 'intentIntegrityEpoch', 0)) != self.availability_epoch):
      return False
    if not 0 < self.lateral_source_ns <= now_ns <= self.lateral_source_ns + SAFETY_MAX_AGE_NS:
      return False
    if not self.source_retention_started_ns:
      if not self.lateral_baseline_ns or not 0 <= now_ns - self.lateral_baseline_ns <= SAFETY_MAX_AGE_NS:
        return False
      self.source_retention_started_ns = now_ns
    if not 0 <= now_ns - self.source_retention_started_ns <= SAFETY_MAX_AGE_NS:
      return False
    event_ns = int(sm.logMonoTime['onroadEvents'])
    faults = [e for e in sm['onroadEvents'] if e.immediateDisable or e.softDisable]
    if (not sm.seen['onroadEvents'] or not sm.valid['onroadEvents'] or not sm.alive['onroadEvents'] or
        not 0 < event_ns <= now_ns or now_ns - event_ns > 1_500_000_000 or
        bool(faults)):
      return False
    native = _healthy_transport_native(sm, cp, cs, self.session, now_ns)
    if (native is None or not native.pandaInventory or not native.requestedLateral or not native.lateralAllowed or
        (axis.desiredLongitudinal or axis.longitudinalActive) and not held and
          not (native.requestedLongitudinal and native.longitudinalAllowed) or
        native.observedMonoTime < self.lateral_native_ns or
        (native.pandaSerial, tuple(p.hardwareSerial for p in native.pandaInventory)) != self.lateral_inventory):
      return False
    return True

  def _event_first_retention(self, sm, cp, axis, stamp, now_ns, *, latched, signature, native):
    # A held source-capped proof may expire before the matching typed pause arrives.
    # Reuse only its previously accepted identity for intent; its output lease stays expired.
    if now_ns <= axis.validUntilMonoTime or signature != self.signature:
      return False
    if (not latched or self.failed or self.paused or not self.session or native is None or
        cp_identity(cp) != self.cp or
        str(axis.sessionId) != self.session or
        str(axis.faultSessionId) != self.session or str(axis.faultReason) != 'none' or
        not axis.qualified or not axis.nativeAcknowledged or not axis.desiredLateral or not axis.lateralActive or
        not sm.seen['aolAxisState'] or not sm.valid['aolAxisState'] or not sm.alive['aolAxisState'] or
        not 0 < axis.sourceCarStateMonoTime <= stamp <= now_ns or
        not self.pending_event and now_ns - stamp > AXIS_MAX_AGE_NS or
        stamp - axis.sourceCarStateMonoTime > AXIS_MAX_AGE_NS or
        axis.validUntilMonoTime != axis.sourceCarStateMonoTime + AXIS_MAX_AGE_NS or
        not stamp <= axis.validUntilMonoTime < stamp + AXIS_MAX_AGE_NS or
        native.observedMonoTime < self.healthy_native_ns or
        (native.pandaSerial, tuple(p.hardwareSerial for p in native.pandaInventory)) != self.healthy_inventory):
      return False
    event_ns = int(sm.logMonoTime['onroadEvents'])
    faults = [event for event in sm['onroadEvents'] if event.immediateDisable or event.softDisable]
    isolated = bool(len(faults) == 1 and faults[0].name == log.OnroadEvent.EventName.controlsMismatch and
                    faults[0].immediateDisable)
    if (not isolated or not sm.seen['onroadEvents'] or not sm.valid['onroadEvents'] or not sm.alive['onroadEvents'] or
        not 0 < axis.faultEventMonoTime < event_ns <= now_ns or now_ns - event_ns > AXIS_MAX_AGE_NS):
      return False
    if not self.pending_event:
      if not self.healthy_feedback_ns or not 0 <= now_ns - self.healthy_feedback_ns <= AXIS_MAX_AGE_NS:
        return False
      self.pending_event = event_ns
    if event_ns != self.pending_event or now_ns - self.pending_event > AXIS_MAX_AGE_NS:
      return False
    self.awaiting = True
    return True

  def observe(self, sm, cp, cs, now_ns, *, latched=True, cancel_source_ns=0, brake_source_ns=0, gm_withdrawal_source_ns=0, intent_producer_session=''):
    self.qualified = False
    self.awaiting = False
    self.retention_qualified = False
    self.retention_pending = False
    try:
      axis = sm['aolAxisState']
      stamp = int(sm.logMonoTime['aolAxisState'])
      reason = str(axis.faultReason)
      signature = (str(axis.sessionId), int(axis.sequence), stamp, int(axis.observedMonoTime),
                   int(axis.validUntilMonoTime), reason, int(axis.faultEventMonoTime), str(axis.faultSessionId),
                   int(axis.sourceCarStateMonoTime), bool(axis.lateralActive), bool(axis.longitudinalActive),
                   bool(axis.desiredLateral), bool(axis.desiredLongitudinal), bool(axis.nativeAcknowledged),
                   str(getattr(axis, 'intentProducerSessionId', '')), int(getattr(axis, 'intentIntegrityEpoch', 0)))
      current = bool(sm.seen['aolAxisState'] and sm.valid['aolAxisState'] and sm.alive['aolAxisState'] and
                     axis.qualified and axis.sessionId and axis.sequence > 0 and stamp == axis.observedMonoTime and
                     0 < stamp <= now_ns <= axis.validUntilMonoTime and now_ns - stamp <= AXIS_MAX_AGE_NS and
                     axis.validUntilMonoTime - stamp <= AXIS_MAX_AGE_NS and axis.faultSessionId == axis.sessionId and
                     cp_identity(cp) == self.cp)
      continuity = bool(not self.session or axis.sessionId == self.session and
                        (axis.sequence > self.sequence or axis.sequence == self.sequence and signature == self.signature))
      if current and continuity and (reason == 'critical' or
          getattr(sm, 'updated', {}).get('onroadEvents', False)) and self._temporary_lag_intent_current(sm, cp, cs, axis, stamp, now_ns,
          latched=latched, producer=intent_producer_session, signature=signature):
        # Received identity only; every original permission/output deadline and
        # healthy baseline timestamp remains unchanged.
        self.sequence, self.signature = int(axis.sequence), signature
        return False
      if current and continuity and self._temporary_steering_intent_current(sm, cp, cs, axis, stamp, now_ns,
          latched=latched, producer=intent_producer_session, signature=signature):
        # Advance only received sequence identity; do not renew the prior output,
        # native, source, or healthy lateral baseline leases.
        self.sequence, self.signature = int(axis.sequence), signature
        return False
      brake_native = (self._honda_brake_lateral_current(sm, cp, cs, axis, now_ns,
        latched=latched, brake_source_ns=brake_source_ns) if current and continuity else None)
      if brake_native is not None:
        # Keep only existing intent. The original native lease and source stamps
        # remain unchanged; decide_axes/native TX independently withdraw LONG.
        self.healthy_feedback_ns = stamp
        self.healthy_native_ns = int(brake_native.observedMonoTime)
        self.sequence, self.signature = int(axis.sequence), signature
        return False
      if current and continuity and (gm_withdrawal_source_ns or self.gm_withdrawal_ns):
        from openpilot.starpilot.car.gm.aol import retained_physical_longitudinal_intent
        gm_native = retained_physical_longitudinal_intent(self, sm, cp, cs, axis, now_ns,
          latched=latched, source_ns=gm_withdrawal_source_ns, producer=intent_producer_session)
        if gm_native is not None:
          # Existing GM intent only; independent runtime/native TX still owns
          # both axes and every original source/native/output deadline.
          self.healthy_feedback_ns = stamp
          self.healthy_native_ns = int(gm_native.observedMonoTime)
          self.sequence, self.signature = int(axis.sequence), signature
          return False
      if self._source_availability_retention(sm, cp, cs, axis, stamp, now_ns,
          latched=latched, continuity=continuity, producer=intent_producer_session, signature=signature):
        self.sequence, self.signature = int(axis.sequence), signature
        return False
      if not self.failed and self._availability_retention(sm, cp, cs, axis, stamp, now_ns,
          latched=latched, current=current, continuity=continuity, intent_producer_session=intent_producer_session):
        self.sequence, self.signature = int(axis.sequence), signature
        return False
      if self._availability_recovery_current(sm, cp, cs, axis, stamp, now_ns,
          latched=latched, current=current, continuity=continuity, producer=intent_producer_session):
        # Separate sockets may deliver either half first. A matched healthy
        # recovery resolves that pending join before ordinary baseline handling.
        self.retention_started_ns = self.retention_event_ns = 0
        self.retention_verified = False
      if self.retention_started_ns:
        # This unmatched episode terminates fail closed. Leave failure set;
        # only the existing healthy, unlatched baseline may clear it later.
        self.retention_started_ns = self.retention_event_ns = 0
        self.retention_verified = False
        self.failed = True
        return True
      if reason != 'availabilityPause' and not availability_only(sm['onroadEvents']):
        self.retention_started_ns = self.retention_event_ns = 0
        self.retention_verified = False
      baseline = bool(reason == 'none' and axis.nativeAcknowledged and
                      0 < axis.sourceCarStateMonoTime <= stamp and
                      stamp - axis.sourceCarStateMonoTime <= AXIS_MAX_AGE_NS)
      native = _healthy_transport_native(sm, cp, cs, str(axis.sessionId), now_ns)
      transport_healthy = native is not None
      cancel_native = (self._longitudinal_cancel_current(sm, cp, cs, axis, now_ns, latched=latched,
                                                        cancel_source_ns=cancel_source_ns)
                       if current and continuity and baseline and not transport_healthy else None)
      if self._event_first_retention(sm, cp, axis, stamp, now_ns, latched=latched,
          signature=signature, native=native):
        return False
      current = bool(current and (transport_healthy or cancel_native is not None))
      if current and baseline and not latched:
        self.session = ''
        self.pending_event = 0
        self.failed = False
        self.longitudinal_cancel_ns = 0
        continuity = True
      if self.failed:
        self.longitudinal_cancel_ns = 0
        return True
      if cancel_native is not None:
        # This is neither transport-pause provenance nor an event exemption.
        # Runtime still requires an exact independent native ACK for each axis.
        if not self.longitudinal_cancel_ns:
          self.longitudinal_cancel_ns = int(cancel_source_ns)
          self.last_cancel_source_ns = int(cancel_source_ns)
        self.lateral_baseline_ns = now_ns
        self.lateral_source_ns = int(axis.sourceCarStateMonoTime)
        self.lateral_native_ns = int(cancel_native.observedMonoTime)
        self.sequence = int(axis.sequence)
        self.signature = signature
        return False
      if transport_healthy:
        if not latched or native is not None and not native.requestedLongitudinal:
          self.gm_withdrawal_ns = 0
        if native is not None and not native.requestedLongitudinal:
          self.honda_brake_ns = 0
        if (not latched or native is not None and not native.requestedLongitudinal or
            self.longitudinal_cancel_ns and now_ns - self.longitudinal_cancel_ns > SAFETY_MAX_AGE_NS):
          self.longitudinal_cancel_ns = 0
      if not current or not continuity or reason not in ('none', 'transportPause'):
        self.longitudinal_cancel_ns = 0
        hard = (self.paused or bool(self.pending_event) or reason == 'critical' or
                bool(self.session and (latched or not continuity)))
        self.paused = False
        self.pending_event = 0
        self.failed = hard
        return hard
      known = bool(self.session)
      if reason == 'none':
        if not baseline:
          hard = self.paused or bool(self.pending_event) or bool(self.session and latched)
          self.paused = False
          self.pending_event = 0
          self.failed = hard
          return hard
        event_ns = int(sm.logMonoTime['onroadEvents'])
        faults = [e for e in sm['onroadEvents'] if e.immediateDisable or e.softDisable]
        isolated = bool(len(faults) == 1 and faults[0].name == log.OnroadEvent.EventName.controlsMismatch and
                        faults[0].immediateDisable)
        if known and isolated and sm.valid['onroadEvents'] and 0 < axis.faultEventMonoTime < event_ns <= now_ns:
          # Separate sockets can deliver the immediate event before its typed
          # proof. Defer only the persistent-intent decision against this
          # previously healthy baseline; no permission or axis is granted.
          if not self.pending_event:
            self.pending_event = event_ns
          if event_ns != self.pending_event or now_ns - self.pending_event > AXIS_MAX_AGE_NS:
            self.pending_event = 0
            self.paused = False
            self.failed = True
            return True
          self.awaiting = True
          return False
        if self.pending_event:
          self.pending_event = 0
          self.paused = False
          self.failed = True
          return True
        # Remember a real physical occurrence before its native wire arrives.
        # Duplicate Card observations and held/released samples cannot renew it.
        cancel_pending = self._longitudinal_cancel_current(sm, cp, cs, axis, now_ns, latched=latched,
          cancel_source_ns=cancel_source_ns, withdrawal_required=False)
        if cancel_pending is not None:
          self.longitudinal_cancel_ns = int(cancel_source_ns)
          self.last_cancel_source_ns = int(cancel_source_ns)
        self.source_retention_started_ns = 0
        self.healthy_feedback_ns = now_ns
        self.healthy_native_ns = int(native.observedMonoTime) if native is not None else 0
        self.healthy_inventory = ((native.pandaSerial, tuple(p.hardwareSerial for p in native.pandaInventory))
                                  if native is not None else None)
        self.session = str(axis.sessionId)
        lateral_baseline = bool(axis.desiredLateral and axis.lateralActive and native is not None and
                                native.pandaInventory and native.requestedLateral and native.lateralAllowed)
        self.lateral_baseline_ns = now_ns if lateral_baseline else 0
        self.lateral_source_ns = int(axis.sourceCarStateMonoTime) if lateral_baseline else 0
        self.availability_producer = (str(getattr(axis, 'intentProducerSessionId', '')) if lateral_baseline and
          intent_producer_session and getattr(axis, 'intentProducerSessionId', '') == intent_producer_session else '')
        self.availability_epoch = int(getattr(axis, 'intentIntegrityEpoch', 0)) if self.availability_producer else None
        if lateral_baseline and native is not None:
          self.lateral_native_ns = int(native.observedMonoTime)
          self.lateral_inventory = (native.pandaSerial, tuple(p.hardwareSerial for p in native.pandaInventory))
        else:
          self.lateral_native_ns = 0
          self.lateral_inventory = None
        self.paused = False
      else:
        provenance = bool(known and not axis.lateralActive and not axis.longitudinalActive and
                          not axis.desiredLongitudinal and 0 < axis.faultEventMonoTime <= stamp)
        pending = bool(provenance and axis.faultEventMonoTime > sm.logMonoTime['onroadEvents'])
        if pending and not self.pending_event:
          self.pending_event = int(axis.faultEventMonoTime)
        self.qualified = bool(provenance and
                              axis.faultEventMonoTime == sm.logMonoTime['onroadEvents'] and
                              sm.valid['onroadEvents'] and axis.faultEventMonoTime <= now_ns)
        if self.pending_event and (axis.faultEventMonoTime != self.pending_event or
                                   now_ns - self.pending_event > AXIS_MAX_AGE_NS):
          self.pending_event = 0
          self.paused = False
          self.failed = True
          return True
        # The producer sends the typed envelope before its event occurrence.
        # Remember that fresh provenance, but exempt no event until the exact
        # occurrence arrives. Missing/old senders cannot establish this pair.
        if not self.qualified and not pending:
          self.failed = True
          return True
        if self.qualified:
          self.pending_event = 0
        self.paused = True
      self.sequence = int(axis.sequence)
      self.signature = signature
      return False
    except (AttributeError, KeyError, IndexError, TypeError, ValueError):
      self.longitudinal_cancel_ns = 0
      hard = self.paused or bool(self.pending_event) or bool(self.session and latched)
      self.paused = False
      self.pending_event = 0
      self.failed = hard
      return hard
