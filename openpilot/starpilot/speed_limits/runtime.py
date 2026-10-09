"""One plannerd-owned SLC lifecycle over real, typed replayable observations."""

import math
import uuid
from dataclasses import dataclass, replace

import openpilot.cereal.messaging as messaging
from openpilot.cereal.services import SERVICE_LIST
from openpilot.starpilot.speed_limits import acceptance as acc
from openpilot.starpilot.speed_limits import action_arbitration as arb
from openpilot.starpilot.speed_limits import composition as comp
from openpilot.starpilot.speed_limits import lead_relaxation as lr
from openpilot.starpilot.speed_limits import selection as sel
from openpilot.starpilot.speed_limits import speed_domain as sd
from openpilot.starpilot.speed_limits.runtime_settings import Settings
from openpilot.starpilot.speed_limits.vision.observation import clock_pair_ns, vision_observation


def _number(value, *, positive=False) -> bool:
  return type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else value >= 0)


def _fresh(sm, service: str, now_ns: int) -> bool:
  timestamp = sm.logMonoTime.get(service, 0)
  frequency = SERVICE_LIST[service].frequency
  # SubMaster uses ten expected periods for its alive check. Apply the same
  # transport window to replay timestamps, which may be held across frames.
  max_age_ns = int(10e9 / frequency) if frequency > 0 else 0
  return (bool(sm.valid.get(service, False)) and bool(sm.alive.get(service, False)) and
          0 < timestamp <= now_ns and now_ns - timestamp <= max_age_ns)


def _paired_card_frame(sm, source_log_ns: int, now_ns: int, *, max_skew_service: str) -> bool:
  """Accept a card event preceding the latest CarState by at most two producer ticks."""
  car_log_ns = int(sm.logMonoTime.get('carState', 0))
  max_skew_ns = int(2e9 / SERVICE_LIST[max_skew_service].frequency)
  return (_fresh(sm, 'carState', now_ns) and 0 < source_log_ns <= car_log_ns <= now_ns and
          car_log_ns - source_log_ns <= max_skew_ns)


def dashboard_observation(evidence, *, car_fingerprint: str, session_id: str, now_ns: int) -> acc.Observation:
  """Project an OEM TSR observation; schema default zero is never absence."""
  status = str(evidence.status)
  timestamp, expiry = int(evidence.observedMonoTime), int(evidence.validUntilMonoTime)
  if status == "unknown" or timestamp <= 0:
    return acc.Observation(acc.ObservationKind.UNKNOWN)
  if timestamp > now_ns or expiry <= timestamp or now_ns > expiry:
    return acc.Observation(acc.ObservationKind.STALE)
  if status == "stale":
    return acc.Observation(acc.ObservationKind.STALE)
  if status == "absent":
    return acc.Observation(acc.ObservationKind.ABSENT)
  if status != "valid" or not _number(evidence.speedMps, positive=True) or int(evidence.episode) <= 0:
    return acc.Observation(acc.ObservationKind.UNKNOWN)
  producer_session = str(evidence.producerSessionId)
  if not producer_session:
    return acc.Observation(acc.ObservationKind.UNKNOWN)
  identity = acc.ObservationIdentity(acc.IdentityKind.PRODUCER_EPISODE,
                                     value=f"{session_id}:{producer_session}:{car_fingerprint}:{int(evidence.episode)}")
  return acc.Observation(acc.ObservationKind.VALID,
                         acc.Candidate(sel.Source.DASHBOARD.value, identity, float(evidence.speedMps)))


def _lead(sm, now_ns: int) -> lr.LeadEvidence:
  if not _fresh(sm, "radarState", now_ns):
    return lr.LeadEvidence(lr.LeadKind.STALE if sm.logMonoTime.get("radarState", 0) else lr.LeadKind.UNKNOWN)
  lead = sm["radarState"].leadOne
  if not lead.present:
    return lr.LeadEvidence(lr.LeadKind.VALID, False, False, 0.0, 0.0, 0.0)
  if not all(_number(value, positive=(name == "distance")) for name, value in
             (("distance", lead.dRel), ("speed", lead.vLeadK))):
    return lr.LeadEvidence(lr.LeadKind.UNKNOWN)
  if type(lead.aLeadK) not in (int, float) or not math.isfinite(lead.aLeadK):
    return lr.LeadEvidence(lr.LeadKind.UNKNOWN)
  return lr.LeadEvidence(lr.LeadKind.VALID, True, True, float(lead.dRel), float(lead.vLeadK), float(lead.aLeadK))


def _authority(CP, sm, host_long: bool, lateral: bool) -> acc.Authority:
  car_state = sm["carState"]
  stock = not bool(CP.openpilotLongitudinalControl) and bool(car_state.cruiseState.enabled)
  if bool(CP.openpilotLongitudinalControl) and host_long:
    return acc.Authority(acc.Mode.COMBINED if lateral else acc.Mode.LONGITUDINAL_ONLY,
                         acc.LongitudinalOwner.SYSTEM, lateral, True, False, False)
  if stock:
    return acc.Authority(acc.Mode.LATERAL_ONLY if lateral else acc.Mode.OFF,
                         acc.LongitudinalOwner.STOCK, lateral, False, True, False)
  return acc.Authority(acc.Mode.LATERAL_ONLY if lateral else acc.Mode.OFF,
                       acc.LongitudinalOwner.NONE, lateral, False, False, not lateral)


@dataclass(frozen=True)
class Action:
  session_id: str
  sequence_id: int
  decision_id: int
  presentation_id: int
  kind: str


@dataclass(frozen=True)
class CruiseEvent:
  event_id: int
  observed_ns: int
  previous_mps: float
  selected_mps: float
  button: str
  producer_session: str = 'replay-card'
  car_state_log_ns: int = 0
  kind: str = 'driverChange'
  session_id: str = ''
  decision_id: int = 0
  presentation_id: int = 0
  command_id: int = 0


@dataclass(frozen=True)
class Output:
  result: comp.Result
  message: object
  action_result: arb.Result | None = None
  command: object | None = None
  settings: Settings | None = None


class Runtime:
  """Own a unique drive session, action ledger and current-frame UI receipt."""

  def __init__(self, settings: Settings, *, session_id: str | None = None, vision_enabled: bool = False,
               vision_control_qualified: bool = False, vision_display_qualified: bool = False):
    self.settings = settings
    self.vision_enabled = vision_enabled
    # Exact saved Vision opt-in may grant control; source identity and current
    # driver confirmation remain independent requirements for each episode.
    self.vision_control_qualified = vision_enabled and vision_control_qualified
    self.vision_display_qualified = bool(vision_enabled and vision_display_qualified and settings.display and not settings.enabled)
    self.vision_diagnostic = acc.Observation(acc.ObservationKind.UNKNOWN)
    self._last_vision_producer = ''
    self._last_vision_frame = 0
    self._last_vision_eof_boot = 0
    self._last_vision_episode = 0
    self.session_id = session_id or uuid.uuid4().hex
    self.state = comp.new_session(self.session_id)
    self.ledger = arb.new_ledger(self.session_id)
    self.last_action_result: arb.Result | None = None
    self.last_ui_sequence = -1
    self.last_cruise_event = -1
    self.last_cruise_producer: str | None = None
    self.last_command_id = 0
    self.command_status = ''
    self._command_ui_sequence = 0
    self._ui_receipt = None
    self.command_issued_ns = 0
    self.command_expiry_ns = 0
    self.command_expected_mps = 0.0
    self.command_target_mps = 0.0
    self.command_card_producer = ''

  def reset(self) -> None:
    self.vision_diagnostic = acc.Observation(acc.ObservationKind.UNKNOWN)
    self._last_vision_producer = ''
    self._last_vision_frame = 0
    self._last_vision_eof_boot = 0
    self._last_vision_episode = 0
    self.session_id = uuid.uuid4().hex
    self.state = comp.new_session(self.session_id)
    self.ledger = arb.new_ledger(self.session_id)
    self.last_action_result = None
    self.last_ui_sequence = -1
    self.last_cruise_event = -1
    self.last_cruise_producer = None
    self.last_command_id = 0
    self.command_status = ''
    self._command_ui_sequence = 0
    self._ui_receipt = None
    self.command_issued_ns = 0
    self.command_expiry_ns = 0
    self.command_expected_mps = 0.0
    self.command_target_mps = 0.0
    self.command_card_producer = ''

  def _event_current(self, event: CruiseEvent, sm, now_ns: int) -> bool:
    return (bool(event.producer_session) and 0 < event.observed_ns <= now_ns and
            now_ns - event.observed_ns <= int(2e9 / SERVICE_LIST['modelV2'].frequency) and
            _paired_card_frame(sm, event.car_state_log_ns, now_ns, max_skew_service='modelV2') and
            (event.producer_session != self.last_cruise_producer or event.event_id > self.last_cruise_event))

  def _mark_event(self, event: CruiseEvent) -> None:
    if event.producer_session != self.last_cruise_producer:
      self.last_cruise_producer = event.producer_session
      self.last_cruise_event = -1
    self.last_cruise_event = event.event_id

  def _cruise(self, event: CruiseEvent | None, sm, now_ns: int) -> arb.Result | None:
    if (event is None or event.kind != 'driverChange' or not self._event_current(event, sm, now_ns) or
        event.button not in ('accel', 'decel') or not _number(event.previous_mps, positive=True) or
        not _number(event.selected_mps, positive=True) or event.previous_mps == event.selected_mps or
        abs(float(sm['carState'].vCruise) / 3.6 - event.selected_mps) > 0.1):
      return None
    self._mark_event(event)
    action_id = self.ledger.last_action_id + 1
    context = self.state.override.context
    if context is not None and context.issued_at_ns > event.observed_ns:
      return None
    context_id = context.context_id if context is not None else 'no-slc-context'
    begun = arb.step(self.ledger, arb.BeginAction(self.session_id, action_id, arb.Origin.DRIVER_CRUISE, context_id), now_ns=now_ns)
    self.ledger = begun.state
    if begun.errors or begun.status != 'begun':
      return None
    resolved = arb.step(self.ledger, arb.ResolveAction(self.session_id, action_id, arb.Disposition.DRIVER_INTENT), now_ns=now_ns)
    self.ledger = resolved.state
    if resolved.errors:
      return None
    classified = arb.step(self.ledger, arb.CruiseChange(self.session_id, self.ledger.last_effect_id + 1, action_id,
                                                         event.previous_mps, event.selected_mps), now_ns=now_ns)
    self.ledger = classified.state
    completed = arb.step(self.ledger, arb.CompleteAction(self.session_id, action_id), now_ns=now_ns)
    self.ledger = completed.state
    return classified if not classified.errors and classified.change is not None else None

  def _physical_action(self, event: CruiseEvent, sm, now_ns: int) -> tuple[acc.DriverAction | None, int | None]:
    if (event.kind not in ('confirmationAccept', 'confirmationReject') or
        not self._event_current(event, sm, now_ns)):
      return None, None
    self._mark_event(event)
    pending = self.state.acceptance.pending
    shown = self.state.acceptance.presentation
    if (event.session_id != self.session_id or pending is None or shown is None or
        event.producer_session != str(sm['slcDashboardObservation'].producerSessionId) or
        event.decision_id != pending.decision_id or event.presentation_id != shown.presentation_id or
        pending.candidate != shown.candidate or
        event.button != ('accel' if event.kind == 'confirmationAccept' else 'decel')):
      return None, None
    action_id = self.ledger.last_action_id + 1
    begun = arb.step(self.ledger, arb.BeginAction(self.session_id, action_id, arb.Origin.DRIVER_CRUISE,
                                                  f'pending:{pending.decision_id}'), now_ns=now_ns)
    self.ledger = begun.state
    if begun.errors or begun.status != 'begun':
      return None, None
    kind = acc.ActionKind.ACCEPT if event.kind == 'confirmationAccept' else acc.ActionKind.REJECT
    return acc.DriverAction(self.session_id, action_id, pending.decision_id, kind), action_id

  def _command_receipt(self, event: CruiseEvent, sm, now_ns: int) -> None:
    if (event.kind not in ('commandApplied', 'commandRejected') or
        not self._event_current(event, sm, now_ns)):
      return
    self._mark_event(event)
    if (event.session_id == self.session_id and event.command_id == self.last_command_id and
        event.producer_session == self.command_card_producer and self.command_status in ('issued', 'expired') and
        self.command_issued_ns <= event.observed_ns <= self.command_expiry_ns):
      if event.kind == 'commandApplied':
        if (not _number(event.previous_mps, positive=True) or
            abs(event.previous_mps - self.command_expected_mps) > 0.1 or
            not _number(event.selected_mps, positive=True) or
            abs(event.selected_mps - self.command_target_mps) > 0.5):
          return
        self.command_status = 'applied'
      else:
        self.command_status = 'rejected'

  def _observations(self, sm, CP, now_ns: int, now_boot_ns: int | None = None) -> dict[sel.Source, acc.Observation]:
    unknown = acc.Observation(acc.ObservationKind.UNKNOWN)
    values = dict.fromkeys(sel.Source, unknown)
    if (_fresh(sm, "carState", now_ns) and not sm["carState"].canTimeout and
        _fresh(sm, 'slcDashboardObservation', now_ns)):
      evidence = sm['slcDashboardObservation']
      source_log_ns = int(evidence.carStateLogMonoTime)
      if (int(sm.logMonoTime['slcDashboardObservation']) == source_log_ns and
          _paired_card_frame(sm, source_log_ns, now_ns, max_skew_service='carState')):
        values[sel.Source.DASHBOARD] = dashboard_observation(
          evidence, car_fingerprint=str(CP.carFingerprint), session_id=self.session_id, now_ns=now_ns)
    elif sm.logMonoTime.get("carState", 0) or sm.logMonoTime.get('slcDashboardObservation', 0):
      values[sel.Source.DASHBOARD] = acc.Observation(acc.ObservationKind.STALE)
    if self.vision_enabled and _fresh(sm, 'slcVisionObservation', now_ns):
      pair = clock_pair_ns() if now_boot_ns is None else (now_ns, now_boot_ns)
      if pair is not None:
        evidence = sm['slcVisionObservation'].vision
        self.vision_diagnostic = vision_observation(
          evidence, receipt_mono_ns=int(sm.logMonoTime['slcVisionObservation']),
          now_mono_ns=pair[0], now_boot_ns=pair[1], car_fingerprint=str(CP.carFingerprint),
          drive_session=self.session_id)
        if self.vision_diagnostic.kind is acc.ObservationKind.VALID:
          producer = str(evidence.producerSessionId)
          frame_id, eof_boot, episode = int(evidence.frameId), int(evidence.cameraFrameEofBootTime), int(evidence.episode)
          if (producer == self._last_vision_producer and
              (frame_id < self._last_vision_frame or eof_boot < self._last_vision_eof_boot or
               episode < self._last_vision_episode)):
            self.vision_diagnostic = acc.Observation(acc.ObservationKind.STALE)
          else:
            self._last_vision_producer = producer
            self._last_vision_frame = frame_id
            self._last_vision_eof_boot = eof_boot
            self._last_vision_episode = episode
        if self.vision_control_qualified or self.vision_display_qualified:
          values[sel.Source.VISION] = self.vision_diagnostic
      else:
        self.vision_diagnostic = acc.Observation(acc.ObservationKind.STALE)
    elif self.vision_enabled and sm.logMonoTime.get('slcVisionObservation', 0):
      self.vision_diagnostic = acc.Observation(acc.ObservationKind.STALE)
    else:
      self.vision_diagnostic = acc.Observation(acc.ObservationKind.UNKNOWN)
    # An unqualified producer stays diagnostic even with a valid observation.
    return values

  def _frame(self, sm, CP, now_ns: int, now_boot_ns: int | None, action: acc.DriverAction | None, adopt: acc.AdoptRequest | None,
             classified: arb.Result | None) -> comp.Frame:
    car_fresh = _fresh(sm, "carState", now_ns) and not sm["carState"].canTimeout
    controls_fresh = _fresh(sm, "controlsState", now_ns)
    selfdrive_fresh = _fresh(sm, "selfdriveState", now_ns)
    car_control_fresh = _fresh(sm, 'carControl', now_ns)
    car_state, controls, selfdrive = sm["carState"], sm["controlsState"], sm["selfdriveState"]
    long_active = str(controls.longControlState) != "off" if controls_fresh else False
    host_long = bool(CP.openpilotLongitudinalControl and long_active and car_control_fresh and sm['carControl'].longActive and
                     selfdrive.enabled and car_fresh and selfdrive_fresh)
    lateral = bool(car_control_fresh and sm['carControl'].latActive and selfdrive_fresh)
    authority = _authority(CP, sm, host_long, lateral)
    selected = float(car_state.vCruise) if car_fresh and _number(car_state.vCruise) else 0.0
    selected_cluster = float(car_state.vCruiseCluster) if car_fresh and _number(car_state.vCruiseCluster) else None
    ego_valid = car_fresh and _number(car_state.vEgo) and _number(car_state.vEgoCluster)
    ego = (sd.SpeedPair(sd.DomainStatus.VALID, float(car_state.vEgo), float(car_state.vEgoCluster), self.session_id, now_ns)
           if ego_valid else sd.SpeedPair(sd.DomainStatus.STALE if sm.logMonoTime.get("carState", 0) else sd.DomainStatus.UNKNOWN))
    host = comp.HostState(bool(CP.openpilotLongitudinalControl), host_long, bool(selfdrive.enabled and selfdrive_fresh),
                          bool(controls.forceDecel) if controls_fresh else True, False, selected, selected_cluster)
    acceptance_policy = (replace(self.settings.acceptance, vision_driver_confirm=True)
                         if self.vision_control_qualified else self.settings.acceptance)
    return comp.Frame(now_ns, self._observations(sm, CP, now_ns, now_boot_ns), self.settings.selection, authority,
                      acceptance_policy, self.settings.offsets,
                      sd.DomainStatus.VALID if car_fresh and selected_cluster is not None else sd.DomainStatus.STALE,
                      ego, bool(car_state.gasPressed) if car_fresh and self.settings.manual_override else False,
                      _lead(sm, now_ns), self.settings.lead_policy, host, action=action, adopt=adopt,
                      classified_cruise=classified)

  def _action(self, request: Action | None, now_ns: int) -> tuple[acc.DriverAction | None, acc.AdoptRequest | None, int | None]:
    if request is None or request.session_id != self.session_id or request.kind not in ("accept", "reject", "adopt"):
      return None, None, None
    if request.sequence_id <= self.last_ui_sequence:
      return None, None, None
    self.last_ui_sequence = request.sequence_id
    shown = self.state.acceptance.presentation
    if request.kind == 'adopt' and (shown is None or shown.presentation_id != request.presentation_id):
      return None, None, None
    action_id = self.ledger.last_action_id + 1
    context = self.state.override.context
    context_id = context.context_id if context is not None else "slc-presentation"
    begun = arb.step(self.ledger, arb.BeginAction(self.session_id, action_id, arb.Origin.DRIVER_OTHER, context_id),
                     now_ns=now_ns)
    self.ledger = begun.state
    if begun.errors:
      return None, None, None
    if request.kind == "adopt":
      assert shown is not None
      return None, acc.AdoptRequest(self.session_id, action_id, request.presentation_id, shown.candidate), action_id
    kind = acc.ActionKind.ACCEPT if request.kind == "accept" else acc.ActionKind.REJECT
    return acc.DriverAction(self.session_id, action_id, request.decision_id, kind), None, action_id

  def step(self, sm, CP, *, now_ns: int, now_boot_ns: int | None = None, request: Action | None = None,
           cruise_event: CruiseEvent | None = None) -> Output:
    old_accepted = self.state.acceptance.accepted
    old_pending = self.state.acceptance.pending
    if self.command_status == 'issued' and now_ns > self.command_expiry_ns:
      self.command_status = 'expired'
    classified = self._cruise(cruise_event, sm, now_ns) if request is None else None
    if cruise_event is not None and request is None:
      self._command_receipt(cruise_event, sm, now_ns)
    action, adopt, action_id = self._action(request, now_ns)
    if cruise_event is not None and request is None:
      action, action_id = self._physical_action(cruise_event, sm, now_ns)
    frame = self._frame(sm, CP, now_ns, now_boot_ns, action, adopt, classified)
    result = comp.step(self.state, frame)
    self.state = result.state
    action_result = None
    if action_id is not None:
      if result.acceptance is not None:
        action_result = arb.resolve_acceptance(self.ledger, action_id, result.acceptance, now_ns=now_ns)
        self.ledger = action_result.state
        self.last_action_result = action_result
      completed = arb.step(self.ledger, arb.CompleteAction(self.session_id, action_id), now_ns=now_ns)
      self.ledger = completed.state
    command = self._command(result, sm, CP, now_ns, old_accepted, old_pending, action, adopt)
    message = self._message(now_ns, result, sm, frame.observations)
    if command is not None:
      self._command_ui_sequence = request.sequence_id if request is not None else 0
    message.slcState.commandActionSequenceId = getattr(self, '_command_ui_sequence', 0)
    if action_result is not None and action_result.status == 'resolved' and request is not None:
      self._ui_receipt = (request.sequence_id, str(message.slcState.actionStatus))
    receipt = getattr(self, '_ui_receipt', None)
    if receipt is not None:
      message.slcState.actionSequenceId, message.slcState.actionStatus = receipt
    return Output(result, message, action_result, command, self.settings)

  def _command(self, result: comp.Result, sm, CP, now_ns: int, old_accepted, old_pending,
               action: acc.DriverAction | None, adopt: acc.AdoptRequest | None):
    decision = result.acceptance
    if (decision is None or (decision.history_write is None and decision.adoption is None) or result.domain is None or
        result.domain.context is None or result.selection is None or
        result.selection.selected_source is not sel.Source.DASHBOARD or
        (action is None and adopt is None) or
        (action is not None and (old_pending is None or action.kind is not acc.ActionKind.ACCEPT))):
      return None
    target = result.domain.context.effective_cluster_mps
    selected_kph = float(sm['carState'].vCruise)
    previous_limit = old_accepted.candidate.speed_mps if old_accepted is not None else 0.0
    if (not _number(target, positive=True) or not _number(selected_kph, positive=True) or
        selected_kph >= 255 or target <= selected_kph / 3.6 + 0.1 or
        (action is not None and decision.history_write.candidate.speed_mps <= previous_limit)):
      return None
    evidence = sm['slcDashboardObservation']
    if dashboard_observation(evidence, car_fingerprint=str(CP.carFingerprint),
                             session_id=self.session_id, now_ns=now_ns).kind is not acc.ObservationKind.VALID:
      return None
    expiry = min(int(evidence.validUntilMonoTime), now_ns + int(2e9 / SERVICE_LIST['slcState'].frequency))
    if expiry <= now_ns:
      return None
    self.last_command_id += 1
    self.command_status = 'issued'
    self.command_issued_ns = now_ns
    self.command_expiry_ns = expiry
    self.command_expected_mps = selected_kph / 3.6
    self.command_target_mps = target
    self.command_card_producer = str(evidence.producerSessionId)
    command = messaging.new_message('slcCruiseCommand')
    command.valid = True
    command.logMonoTime = now_ns
    record = command.slcCruiseCommand
    record.kind = 'adoptAcceptedHigherLimit'
    record.sessionId = self.session_id
    record.commandId = self.last_command_id
    record.actionId = action.sequence_id if action is not None else adopt.sequence_id
    record.decisionId = old_pending.decision_id if old_pending is not None else 0
    record.presentationId = self.state.acceptance.presentation.presentation_id if self.state.acceptance.presentation is not None else 0
    record.sourceProducerSessionId = str(evidence.producerSessionId)
    record.sourceEpisode = int(evidence.episode)
    record.sourceObservedMonoTime = int(evidence.observedMonoTime)
    record.sourceValidUntilMonoTime = int(evidence.validUntilMonoTime)
    record.issuedMonoTime = now_ns
    record.expiresMonoTime = expiry
    record.expectedSelectedMps = selected_kph / 3.6
    record.targetMps = target
    return command

  def _message(self, now_ns: int, result: comp.Result, sm, observations=None):
    message = messaging.new_message("slcState")
    message.logMonoTime = now_ns
    message.valid = not result.errors
    state = message.slcState
    state.sessionId = self.session_id
    # Display metadata is copied from the same qualified inputs used by selection.
    enabled_sources = (set(self.settings.selection.slots) if self.settings.selection.mode == sel.SelectionMode.ORDERED
                       else set(sel.PRIMARY_ORDER if sel.Source.VISION in self.settings.selection.slots else sel.PRIMARY_ORDER[:2]))
    if self.settings.selection.online_fallback:
      enabled_sources.add(sel.Source.ONLINE)
    rows = state.init('sourceReadings', len(sel.Source))
    for row, source in zip(rows, sel.Source, strict=True):
      observation = (observations or {}).get(source)
      row.source = source.value
      row.enabled = bool(self.settings.display and source in enabled_sources)
      row.observationKind = observation.kind.value if observation is not None else 'unknown'
      if observation is not None and observation.kind == acc.ObservationKind.VALID and observation.candidate is not None:
        row.speedLimit = observation.candidate.speed_mps
    state.frameMonoTime = now_ns
    state.enabled = self.settings.enabled
    state.displayOnly = self.settings.display and not self.settings.enabled
    state.observationKind = result.selection.observation.kind.value if result.selection is not None else "unknown"
    state.source = result.selection.selected_source.value if result.selection is not None and result.selection.selected_source is not None else "none"
    if result.selection is not None and result.selection.observation.candidate is not None:
      state.speedLimit = result.selection.observation.candidate.speed_mps
    accepted = result.state.acceptance.accepted
    if accepted is not None:
      state.hasAccepted = True
      state.acceptedSpeedLimit = accepted.candidate.speed_mps
      state.acceptedSource = accepted.candidate.source
    if result.domain is not None and result.domain.context is not None:
      state.offset = result.domain.context.offset_mps
    if result.ceiling is not None and self.settings.enabled:
      state.hasCeiling = True
      state.effectiveCap = result.ceiling.speed_mps
    # Publish the qualified domain coordinate; a raw cap is not a cluster value.
    context = result.domain.context if result.domain is not None else None
    if context is not None:
      state.hasEffectiveClusterTarget = True
      state.effectiveClusterTarget = context.effective_cluster_mps
      state.isLimitingMaxSet = bool(state.hasCeiling and result.ceiling.speed_mps < context.selected_raw_mps)
    # Override state.active means the override context is eligible, even with no
    # driver override. Only pedal/persistent contributions actually replace the cap.
    state.driverOverrideActive = bool(result.override is not None and result.override.contribution_mps is not None)
    pending = result.state.acceptance.pending
    if pending is not None:
      state.hasPending = True
      state.pendingSpeedLimit = pending.candidate.speed_mps
      state.pendingSource = pending.candidate.source
      state.decisionId = pending.decision_id
    state.overrideBasis = (result.override.basis if state.driverOverrideActive else 'none')
    state.retainedOverride = bool(result.state.override.persistent_selected_mps is not None)
    shown = result.state.acceptance.presentation
    if state.observationKind == 'valid':
      for candidate, value_field, flag_field in (
        (accepted.candidate if accepted is not None else None, 'acceptedAdjustedLimit', 'hasAcceptedAdjustedLimit'),
        (pending.candidate if pending is not None else None, 'pendingAdjustedLimit', 'hasPendingAdjustedLimit'),
        (shown.candidate if shown is not None else None, 'presentationAdjustedLimit', 'hasPresentationAdjustedLimit'),
      ):
        value = sd.adjusted_limit(candidate.speed_mps, self.settings.offsets) if candidate is not None else None
        if value is not None:
          setattr(state, value_field, value)
          setattr(state, flag_field, True)
    if shown is not None:
      state.presentationId = shown.presentation_id
    state.status = result.status
    if state.source == 'dashboard' and state.observationKind == 'valid':
      evidence = sm['slcDashboardObservation']
      state.sourceProducerSessionId = str(evidence.producerSessionId)
      state.sourceEpisode = int(evidence.episode)
      state.sourceObservedMonoTime = int(evidence.observedMonoTime)
      state.sourceValidUntilMonoTime = int(evidence.validUntilMonoTime)
    elif state.source == 'vision' and state.observationKind == 'valid' and (self.vision_control_qualified or self.vision_display_qualified):
      evidence = sm['slcVisionObservation'].vision
      state.sourceProducerSessionId = str(evidence.producerSessionId)
      state.sourceEpisode = int(evidence.episode)
      state.sourceObservedMonoTime = int(evidence.observedMonoTime)
      state.sourceValidUntilMonoTime = int(evidence.validUntilMonoTime)
    state.commandId = self.last_command_id
    state.commandStatus = self.command_status
    receipt = result.acceptance.action_receipt or result.acceptance.adoption_receipt if result.acceptance else None
    if receipt is not None:
      state.actionSequenceId = receipt.sequence_id
      state.actionStatus = receipt.status
    return message
