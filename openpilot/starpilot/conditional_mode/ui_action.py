"""Explicit UI manual-cycle requests; the planner remains the intent owner."""

from dataclasses import dataclass
import hashlib
import math
import re
import secrets

from openpilot.cereal import messaging
from openpilot.starpilot.conditional_mode.effective_status import EffectiveModeAck, observation as effective_observation
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.preferences import MAX_DOCUMENT_BYTES
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner, SettingsSnapshot
from openpilot.starpilot.conditional_mode.status import CHOICES, settings_fingerprint
from openpilot.starpilot.saved_source import read_saved


LIFETIME_NS = 100_000_000
SOURCE_MAX_AGE_NS = 250_000_000
_SESSION = re.compile(r'[0-9a-f]{32}\Z')
_FINGERPRINT = re.compile(r'[0-9a-f]{64}\Z')
_CHOICES = {wire: choice for choice, wire in CHOICES.items()}


def fresh_service(sm, name: str, drive_id: int, now_ns: int, max_age_ns: int = SOURCE_MAX_AGE_NS) -> bool:
  try:
    producer, receipt = sm.logMonoTime[name], sm.recv_time[name]
    if type(producer) is not int or type(receipt) not in (int, float) or not math.isfinite(receipt):
      return False
    receipt_ns = int(receipt * 1e9)
    return bool(sm.seen[name] and sm.alive[name] and sm.valid[name] and
                drive_id < producer <= now_ns and drive_id < receipt_ns <= now_ns and
                now_ns - producer <= max_age_ns and now_ns - receipt_ns <= max_age_ns)
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return False


def current_authority(sm, cp, drive_id: int, now_ns: int) -> bool:
  try:
    return bool(type(now_ns) is int and type(drive_id) is int and 0 < drive_id < now_ns and
                cp.openpilotLongitudinalControl and not cp.passive and not cp.dashcamOnly and not cp.notCar and
                all(fresh_service(sm, name, drive_id, now_ns) for name in ('carState', 'carControl', 'selfdriveState')) and
                fresh_service(sm, 'deviceState', drive_id, now_ns, 1_000_000_000) and
                sm['deviceState'].started and sm['deviceState'].startedMonoTime == drive_id and
                sm['carState'].canValid and not sm['carState'].canTimeout and
                sm['carControl'].enabled and sm['carControl'].longActive and sm['selfdriveState'].enabled)
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return False


def exact_settings(params, snapshot: SettingsSnapshot) -> bool:
  try:
    return (read_saved(params, 'ConditionalModeConfig', MAX_DOCUMENT_BYTES) == (snapshot.document_raw, True) and
            read_saved(params, 'SafeMode', 8) == (snapshot.safe_mode_raw, True))
  except (AttributeError, OSError, TypeError, ValueError):
    return False


@dataclass(frozen=True)
class UiActionContext:
  drive_id: int
  fingerprint: str
  choice: ModeChoice
  planner_session: str
  selfdrive_session: str
  manual_code: int
  effective_experimental: bool

  @property
  def token(self) -> str:
    fields = (self.drive_id, self.fingerprint, self.choice.value, self.planner_session,
              self.selfdrive_session, self.manual_code, self.effective_experimental)
    return hashlib.sha256(repr(fields).encode()).hexdigest()


@dataclass(frozen=True)
class UiAction:
  session: str
  sequence: int
  observed_ns: int
  expires_ns: int
  drive_id: int
  fingerprint: str
  choice: ModeChoice
  planner_session: str
  car_state_ns: int
  selfdrive_state_ns: int
  manual_code: int
  effective_experimental: bool


def observation(event, now_ns: int) -> UiAction | None:
  try:
    if not event.valid or event.which() != 'slcAction' or str(event.slcAction.kind) != 'conditionalModeCycle':
      return None
    if event.slcAction.sessionId or event.slcAction.sequenceId or event.slcAction.decisionId or event.slcAction.presentationId:
      return None
    value = event.slcAction.conditionalManual
    choice = _CHOICES[str(value.choice)]
    observed, expiry, drive = value.observedMonoTime, value.validUntilMonoTime, value.driveStartMonoTime
    car_state, selfdrive_state = value.sourceCarStateMonoTime, value.sourceSelfdriveStateMonoTime
    session, planner, fingerprint = str(value.sessionId), str(value.plannerSessionId), str(value.settingsFingerprint)
    if (type(now_ns) is not int or value.version != 1 or value.sequence <= 0 or
        not _SESSION.fullmatch(session) or not _SESSION.fullmatch(planner) or not _FINGERPRINT.fullmatch(fingerprint) or
        choice not in (ModeChoice.CEM, ModeChoice.CCM) or value.expectedManualCode not in (0, 1, 2) or
        event.logMonoTime != observed or not 0 < drive < observed <= now_ns <= expiry or expiry - observed != LIFETIME_NS or
        not drive < car_state <= observed or not drive < selfdrive_state <= observed or
        observed - min(car_state, selfdrive_state) > SOURCE_MAX_AGE_NS):
      return None
    return UiAction(session, value.sequence, observed, expiry, drive, fingerprint, choice, planner,
                    car_state, selfdrive_state, value.expectedManualCode, value.expectedExperimental)
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return None


class ConditionalUiActionOwner:
  def __init__(self, params):
    self.params = params
    self.settings = ConditionalSettingsOwner(params)
    self.session = secrets.token_hex(16)
    self.sequence = 0
    self.last_token: str | None = None
    self.last_dispatch_ns = 0
    self.ack_drive = 0
    self.last_ack: EffectiveModeAck | None = None
    self.retired_ack_sessions: tuple[str, ...] = ()
    self.last_now_ns = 0

  def configured_choice(self, *, now_ns: int) -> ModeChoice | None:
    snapshot = self.settings.refresh(now_ns)
    return snapshot.preferences.mode if self.settings.affirm(snapshot, now_mono_ns=now_ns) and snapshot.preferences is not None else None

  def context(self, sm, cp, *, now_ns: int) -> UiActionContext | None:
    if type(now_ns) is not int or now_ns < self.last_now_ns:
      return None
    self.last_now_ns = now_ns
    snapshot = self.settings.refresh(now_ns)
    fingerprint = settings_fingerprint(snapshot)
    if not self.settings.affirm(snapshot, now_mono_ns=now_ns) or snapshot.preferences is None or fingerprint is None:
      return None
    try:
      drive_id = int(sm['deviceState'].startedMonoTime)
      if not current_authority(sm, cp, drive_id, now_ns) or not fresh_service(sm, 'starpilotSelfdriveState', drive_id, now_ns):
        return None
      ack = effective_observation(sm['starpilotSelfdriveState'], now_ns)
      if (ack is None or not ack.accepted or ack.drive_id != drive_id or ack.fingerprint != fingerprint or
          ack.choice is not snapshot.preferences.mode or ack.planner_session is None or
          ack.observed_ns != sm.logMonoTime['starpilotSelfdriveState'] or
          not ack.selfdrive_state_ns <= sm.logMonoTime['selfdriveState'] <= now_ns or
          ack.effective_experimental is not sm['selfdriveState'].experimentalMode):
        return None
      if drive_id != self.ack_drive:
        self.ack_drive, self.last_ack, self.retired_ack_sessions = drive_id, None, ()
      previous = self.last_ack
      if ack.session in self.retired_ack_sessions:
        return None
      if previous is not None:
        if ack.session != previous.session:
          self.retired_ack_sessions = (*self.retired_ack_sessions[-7:], previous.session)
          self.last_ack = ack
          return None
        if (ack.sequence < previous.sequence or ack.sequence == previous.sequence and ack != previous or
            ack.sequence > previous.sequence and ack.observed_ns <= previous.observed_ns):
          return None
      self.last_ack = ack
      return UiActionContext(drive_id, fingerprint, ack.choice, ack.planner_session, ack.session,
                             ack.status_code if ack.status_code in (1, 2) else 0, ack.effective_experimental)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      return None

  def dispatch(self, expected_context: UiActionContext, sm, cp, publisher, *, now_ns: int) -> bool:
    current = self.context(sm, cp, now_ns=now_ns)
    snapshot = self.settings.current
    if (current is None or current != expected_context or snapshot is None or not exact_settings(self.params, snapshot) or
        now_ns <= self.last_dispatch_ns or
        current.token == self.last_token and now_ns <= self.last_dispatch_ns + LIFETIME_NS):
      return False
    self.sequence += 1
    event = messaging.new_message('slcAction', valid=True)
    event.logMonoTime = now_ns
    event.slcAction.kind = 'conditionalModeCycle'
    event.slcAction.conditionalManual = {
      'version': 1, 'sessionId': self.session, 'sequence': self.sequence,
      'observedMonoTime': now_ns, 'validUntilMonoTime': now_ns + LIFETIME_NS,
      'driveStartMonoTime': current.drive_id, 'settingsFingerprint': current.fingerprint,
      'choice': CHOICES[current.choice], 'plannerSessionId': current.planner_session,
      'sourceCarStateMonoTime': sm.logMonoTime['carState'], 'sourceSelfdriveStateMonoTime': sm.logMonoTime['selfdriveState'],
      'expectedManualCode': current.manual_code, 'expectedExperimental': current.effective_experimental,
    }
    try:
      publisher.send('slcAction', event)
    except (OSError, RuntimeError):
      return False
    self.last_token, self.last_dispatch_ns = current.token, now_ns
    return True
