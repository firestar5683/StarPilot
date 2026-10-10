"""Reason-qualified intent retention; this module never grants an axis."""
from openpilot.cereal import log
from openpilot.starpilot.aol.runtime import AXIS_MAX_AGE_NS, SAFETY_MAX_AGE_NS, current_native, native_inventory_matches_cp
from openpilot.starpilot.aol.wire import SafetyState, decode_intent


def cp_identity(cp):
  return (str(cp.brand), str(cp.carFingerprint), int(cp.flags), int(cp.alternativeExperience),
          bool(cp.passive), bool(cp.dashcamOnly), bool(cp.notCar),
          bool(cp.openpilotLongitudinalControl), bool(cp.pcmCruise),
          tuple((int(c.safetyModel.raw), int(c.safetyParam)) for c in cp.safetyConfigs))


def _healthy_transport_native(sm, cp, cs, session, now_ns, native=None):
  """Require the live, exact native configuration, including every Panda."""
  try:
    native = native or current_native(sm, cp, now_ns=now_ns, axis_session_id=session)
    if (not session or native is None or str(native.axisSessionId) != session or
        not cs.canValid or cs.canTimeout or cs.steerFaultTemporary or cs.steerFaultPermanent or
        native.requestedLateral and not native.lateralAllowed or
        native.requestedLongitudinal and not native.longitudinalAllowed):
      return None
    coherent = bool(native.pandaInventory)
    if coherent and (int(sm.logMonoTime['aolSafetyWire']) != native.observedMonoTime or
                     not 0 < native.observedMonoTime <= now_ns <= native.validUntilMonoTime or
                     now_ns - native.observedMonoTime > SAFETY_MAX_AGE_NS or
                     native.validUntilMonoTime - native.observedMonoTime > SAFETY_MAX_AGE_NS):
      return None
    if coherent and (not native_inventory_matches_cp(native, cp) or
                     any(p.safetyRxChecksInvalid or p.heartbeatLost or p.faults or
                         (native.requestedLongitudinal and str(config.safetyModel) not in ('silent', 'noOutput') and
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
               (not native.requestedLongitudinal or str(c.safetyModel) in ('silent', 'noOutput') or p.controlsAllowed)
               for p, c in zip(pandas, cp.safetyConfigs, strict=True)) else None
  except (AttributeError, KeyError, IndexError, TypeError, ValueError):
    return None


def healthy_transport(sm, cp, cs, session, now_ns, native=None):
  """Require the live, exact native configuration, including every Panda."""
  return _healthy_transport_native(sm, cp, cs, session, now_ns, native) is not None


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
    eligible = bool(cp_identity(cp) == self.cp and session == self.session and not hard_fault and model_ready and
                    healthy_transport(sm, cp, cs, session, now_ns, native) and companion is not None)
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
    self.lateral_inventory = None
    self.lateral_native_ns = 0
    self.longitudinal_cancel_ns = 0
    self.last_cancel_source_ns = 0

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

  def observe(self, sm, cp, cs, now_ns, *, latched=True, cancel_source_ns=0):
    self.qualified = False
    self.awaiting = False
    try:
      axis = sm['aolAxisState']
      stamp = int(sm.logMonoTime['aolAxisState'])
      reason = str(axis.faultReason)
      signature = (str(axis.sessionId), int(axis.sequence), stamp, int(axis.observedMonoTime),
                   int(axis.validUntilMonoTime), reason, int(axis.faultEventMonoTime), str(axis.faultSessionId),
                   int(axis.sourceCarStateMonoTime), bool(axis.lateralActive), bool(axis.longitudinalActive),
                   bool(axis.desiredLateral), bool(axis.desiredLongitudinal), bool(axis.nativeAcknowledged))
      current = bool(sm.seen['aolAxisState'] and sm.valid['aolAxisState'] and sm.alive['aolAxisState'] and
                     axis.qualified and axis.sessionId and axis.sequence > 0 and stamp == axis.observedMonoTime and
                     0 < stamp <= now_ns <= axis.validUntilMonoTime and now_ns - stamp <= AXIS_MAX_AGE_NS and
                     axis.validUntilMonoTime - stamp <= AXIS_MAX_AGE_NS and axis.faultSessionId == axis.sessionId and
                     cp_identity(cp) == self.cp)
      continuity = bool(not self.session or axis.sessionId == self.session and
                        (axis.sequence > self.sequence or axis.sequence == self.sequence and signature == self.signature))
      baseline = bool(reason == 'none' and axis.nativeAcknowledged and
                      0 < axis.sourceCarStateMonoTime <= stamp and
                      stamp - axis.sourceCarStateMonoTime <= AXIS_MAX_AGE_NS)
      native = _healthy_transport_native(sm, cp, cs, str(axis.sessionId), now_ns)
      transport_healthy = native is not None
      cancel_native = (self._longitudinal_cancel_current(sm, cp, cs, axis, now_ns, latched=latched,
                                                        cancel_source_ns=cancel_source_ns)
                       if current and continuity and baseline and not transport_healthy else None)
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
        self.lateral_native_ns = int(cancel_native.observedMonoTime)
        self.sequence = int(axis.sequence)
        self.signature = signature
        return False
      if transport_healthy:
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
        self.session = str(axis.sessionId)
        lateral_baseline = bool(axis.desiredLateral and axis.lateralActive and native is not None and
                                native.pandaInventory and native.requestedLateral and native.lateralAllowed)
        self.lateral_baseline_ns = now_ns if lateral_baseline else 0
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
