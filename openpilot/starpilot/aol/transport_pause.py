"""Reason-qualified intent retention; this module never grants an axis."""
from openpilot.cereal import log
from openpilot.starpilot.aol.runtime import AXIS_MAX_AGE_NS, SAFETY_MAX_AGE_NS, current_native, native_inventory_matches_cp
from openpilot.starpilot.aol.wire import SafetyState, decode_intent


def cp_identity(cp):
  return (str(cp.brand), str(cp.carFingerprint), int(cp.flags), int(cp.alternativeExperience),
          bool(cp.passive), bool(cp.dashcamOnly), bool(cp.notCar),
          bool(cp.openpilotLongitudinalControl), bool(cp.pcmCruise),
          tuple((int(c.safetyModel.raw), int(c.safetyParam)) for c in cp.safetyConfigs))


def _healthy_transport_native(sm, cp, cs, session, now_ns, native=None, *, require_longitudinal=True):
  """Require the live, exact native configuration, including every Panda."""
  try:
    native = native or current_native(sm, cp, now_ns=now_ns, axis_session_id=session)
    if (not session or native is None or str(native.axisSessionId) != session or
        not cs.canValid or cs.canTimeout or cs.steerFaultTemporary or cs.steerFaultPermanent or
        native.requestedLateral and not native.lateralAllowed or
        require_longitudinal and native.requestedLongitudinal and not native.longitudinalAllowed):
      return None
    coherent = bool(native.pandaInventory)
    if coherent and (int(sm.logMonoTime['aolSafetyWire']) != native.observedMonoTime or
                     not 0 < native.observedMonoTime <= now_ns <= native.validUntilMonoTime or
                     now_ns - native.observedMonoTime > SAFETY_MAX_AGE_NS or
                     native.validUntilMonoTime - native.observedMonoTime > SAFETY_MAX_AGE_NS):
      return None
    if coherent and (not native_inventory_matches_cp(native, cp) or
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
    issue = live_event and availability_only(events)
    if reason not in ('none', 'availabilityPause') or faults and not issue:
      return False
    typed = bool(reason == 'availabilityPause' and not axis.lateralActive and not axis.longitudinalActive and
                 0 < axis.faultEventMonoTime <= stamp)
    source_expired = bool(typed and axis.sourceCarStateMonoTime == 0)
    if source_expired and not 0 < self.lateral_source_ns <= now_ns <= self.lateral_source_ns + SAFETY_MAX_AGE_NS:
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

  def _source_availability_retention(self, sm, cp, cs, axis, stamp, now_ns, *, latched, continuity, producer, signature):
    # Output freshness withdraws commands, not previously accepted driver intent.
    # Missing/expired full-LONG output can retain only the exact held identity;
    # the existing lateral-only source-retention path keeps its original guards.
    held = bool(signature == self.signature and not self.retention_started_ns)
    output_missing = not (sm.seen['aolAxisState'] and sm.valid['aolAxisState'] and sm.alive['aolAxisState'])
    if (not latched or self.failed or self.paused or self.pending_event or not self.session or
        cp_identity(cp) != self.cp or not continuity or
        str(axis.sessionId) != self.session or str(axis.faultSessionId) != self.session or
        str(axis.faultReason) != 'none' or not axis.qualified or not axis.nativeAcknowledged or
        not axis.desiredLateral or not axis.lateralActive or
        (axis.desiredLongitudinal or axis.longitudinalActive) and not held or
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

  def observe(self, sm, cp, cs, now_ns, *, latched=True, cancel_source_ns=0, brake_source_ns=0, intent_producer_session=''):
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
      brake_native = (self._honda_brake_lateral_current(sm, cp, cs, axis, now_ns,
        latched=latched, brake_source_ns=brake_source_ns) if current and continuity else None)
      if brake_native is not None:
        # Keep only existing intent. The original native lease and source stamps
        # remain unchanged; decide_axes/native TX independently withdraw LONG.
        self.healthy_feedback_ns = stamp
        self.healthy_native_ns = int(brake_native.observedMonoTime)
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
      if self.retention_started_ns:
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
