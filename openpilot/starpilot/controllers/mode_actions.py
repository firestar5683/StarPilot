"""Short-lived requests and per-drive mode intent; existing publishers carry them."""
from dataclasses import dataclass
import re
import secrets

from openpilot.cereal import messaging
from openpilot.starpilot.conditional_mode.manual import ioniq6_media_eligible
from openpilot.starpilot.conditional_mode.ui_action import current_authority, fresh_service

LIFETIME_NS = 250_000_000
KINDS = {'trafficModeToggle': 'traffic', 'switchbackModeToggle': 'switchback'}
SESSION = re.compile(r'[0-9a-f]{32}\Z')


def authority(sm, cp, now_ns: int, mode: str) -> bool:
  try:
    if mode not in ('traffic', 'switchback') or not ioniq6_media_eligible(cp):
      return False
    drive = int(sm['deviceState'].startedMonoTime)
    if mode == 'traffic':
      return current_authority(sm, cp, drive, now_ns)
    return bool(not cp.passive and not cp.dashcamOnly and not cp.notCar and
                0 < drive < now_ns and sm['deviceState'].started and
                fresh_service(sm, 'deviceState', drive, now_ns, 1_000_000_000) and
                all(fresh_service(sm, name, drive, now_ns) for name in ('carState', 'carControl')) and
                sm['carState'].canValid and not sm['carState'].canTimeout and sm['carControl'].latActive)
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return False


class ModeActionPublisher:
  def __init__(self):
    self.session = secrets.token_hex(16)
    self.sequence = 0
    self.last_ns = 0

  def dispatch(self, mode: str, sm, cp, publisher, *, now_ns: int) -> bool:
    if (now_ns - self.last_ns < 100_000_000 or not authority(sm, cp, now_ns, mode) or
        not producer_available(sm, now_ns=now_ns)):
      return False
    self.sequence += 1
    event = messaging.new_message('slcAction', valid=True)
    event.logMonoTime = now_ns
    event.slcAction.kind = next(kind for kind, value in KINDS.items() if value == mode)
    event.slcAction.controllerMode = {
      'version': 1, 'sessionId': self.session, 'sequence': self.sequence,
      'observedMonoTime': now_ns, 'validUntilMonoTime': now_ns + LIFETIME_NS,
      'driveStartMonoTime': int(sm['deviceState'].startedMonoTime),
      'carFingerprint': cp.carFingerprint, 'sourceCarControlMonoTime': int(sm.logMonoTime['carControl']),
    }
    publisher.send('slcAction', event)
    self.last_ns = now_ns
    return True


@dataclass(frozen=True)
class ModeIntent:
  drive_id: int
  requested: bool
  effective: bool


class ModeActionOwner:
  def __init__(self):
    self.drive = 0
    self.sequences = {}
    self.requested = {'traffic': False, 'switchback': False}
    self.last_apply_ns = 0

  def reset(self, drive: int = 0) -> None:
    self.drive = drive
    self.sequences.clear()
    self.requested = {'traffic': False, 'switchback': False}
    self.last_apply_ns = 0

  def update(self, event, sm, cp, *, now_ns: int) -> bool:
    try:
      drive = int(sm['deviceState'].startedMonoTime) if sm['deviceState'].started else 0
      if drive != self.drive:
        self.reset(drive)
      if event is None or not event.valid or event.which() != 'slcAction':
        return False
      mode = KINDS.get(str(event.slcAction.kind))
      if mode is None or not authority(sm, cp, now_ns, mode):
        return False
      wire = event.slcAction.controllerMode
      session, sequence = str(wire.sessionId), int(wire.sequence)
      observed, expires = int(wire.observedMonoTime), int(wire.validUntilMonoTime)
      source = int(wire.sourceCarControlMonoTime)
      if (wire.version != 1 or not SESSION.fullmatch(session) or sequence <= self.sequences.get(session, 0) or
          len(self.sequences) >= 8 and session not in self.sequences or
          int(wire.driveStartMonoTime) != drive or str(wire.carFingerprint) != cp.carFingerprint or
          not drive < observed <= now_ns <= expires or expires - observed != LIFETIME_NS or
          event.logMonoTime != observed or not drive < source <= int(sm.logMonoTime['carControl']) <= now_ns or
          now_ns - source > LIFETIME_NS or now_ns - self.last_apply_ns < 100_000_000):
        return False
      self.sequences[session] = sequence
      self.last_apply_ns = now_ns
      self.requested[mode] = not self.requested[mode]
      return True
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      return False

  def sample(self, mode: str, sm, cp, *, now_ns: int) -> ModeIntent:
    drive = int(sm['deviceState'].startedMonoTime) if sm['deviceState'].started else 0
    if drive != self.drive:
      self.reset(drive)
    requested = self.requested.get(mode, False)
    return ModeIntent(drive, requested, requested and authority(sm, cp, now_ns, mode))


class SwitchbackCooldown:
  def __init__(self):
    self.drive = 0
    self.last = {}

  def allow(self, event: str, *, active: bool, drive_id: int, now_ns: int, cooldown_ns: int) -> bool:
    if drive_id != self.drive or not active:
      self.drive = drive_id
      self.last.clear()
    if event not in ('belowSteerSpeed', 'steerSaturated') or not active or cooldown_ns <= 0:
      return True
    previous = self.last.get(event)
    if previous is not None and 0 <= now_ns - previous < cooldown_ns:
      return False
    self.last[event] = now_ns
    return True


def publish_switchback(event, intent: ModeIntent, *, session: str, sequence: int,
                       now_ns: int, source_car_control_ns: int):
  if event is None:
    event = messaging.new_message('slcState', valid=True)
    event.logMonoTime = now_ns
  observed_ns = int(event.logMonoTime)
  event.slcState.switchbackMode = {
    'version': 1, 'sessionId': session, 'sequence': sequence,
    'observedMonoTime': observed_ns, 'validUntilMonoTime': observed_ns + 100_000_000,
    'driveStartMonoTime': intent.drive_id, 'requested': intent.requested,
    'effective': intent.effective, 'sourceCarControlMonoTime': source_car_control_ns,
  }
  return event


def switchback_observation(event, *, drive_id: int, now_ns: int, event_ns: int | None = None) -> bool:
  try:
    state = getattr(event, 'slcState', event)
    wire = state.switchbackMode
    stamp = getattr(event, 'logMonoTime', event_ns)
    return bool(getattr(event, 'valid', True) and wire.version == 1 and SESSION.fullmatch(str(wire.sessionId)) and
                wire.sequence > 0 and wire.requested and wire.effective and
                wire.driveStartMonoTime == drive_id and 0 < drive_id < wire.observedMonoTime <= now_ns <=
                wire.validUntilMonoTime <= wire.observedMonoTime + 100_000_000 and
                stamp == wire.observedMonoTime and
                drive_id < wire.sourceCarControlMonoTime <= wire.observedMonoTime and
                now_ns - wire.sourceCarControlMonoTime <= LIFETIME_NS)
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return False


class SwitchbackStatusOwner:
  def __init__(self):
    self.drive = 0
    self.last = None
    self.retired = ()

  def sample(self, event, *, drive_id: int, now_ns: int, event_ns: int | None = None) -> bool:
    if drive_id != self.drive or drive_id <= 0:
      self.drive, self.last, self.retired = drive_id, None, ()
    if not switchback_observation(event, drive_id=drive_id, now_ns=now_ns, event_ns=event_ns):
      return False
    wire = getattr(event, 'slcState', event).switchbackMode
    identity = (str(wire.sessionId), int(wire.sequence), int(wire.observedMonoTime))
    if identity[0] in self.retired:
      return False
    if self.last is not None:
      if identity[0] != self.last[0]:
        self.retired = (*self.retired[-7:], self.last[0])
        self.last = identity
        return False
      if identity[1] < self.last[1] or identity[1] == self.last[1] and identity != self.last or identity[1] > self.last[1] and identity[2] <= self.last[2]:
        return False
    self.last = identity
    return True


def apply_switchback_gesture(owner, event, *, params, settings, sm, cp, now_ns: int, now_boot_ns: int, mode: str = 'switchback') -> bool:
  from openpilot.starpilot.conditional_mode.manual import Button, Gesture, Press, read_button_map
  from openpilot.starpilot.conditional_mode.status import settings_fingerprint
  try:
    drive = int(sm['deviceState'].startedMonoTime)
    if owner.drive != drive:
      owner.reset(drive)
    if mode not in ('traffic', 'switchback') or not authority(sm, cp, now_ns, mode) or not event.valid or str(event.slcCruiseEvent.kind) != mode + 'Mode':
      return False
    record = event.slcCruiseEvent
    wire = record.trafficMode
    if not wire.toggle:
      return False
    snapshot = settings.refresh(now_ns)
    verdict = settings.verdict(snapshot, now_mono_ns=now_ns, drive_id=drive)
    fingerprint = settings_fingerprint(snapshot)
    buttons = read_button_map(params, include_ioniq_media=True)
    if verdict.status != 'ready' or verdict.safe_mode is not False or fingerprint is None or buttons is None:
      return False
    session, sequence = str(wire.sessionId), int(wire.sequence)
    observed, expiry = int(wire.observedMonoTime), int(wire.validUntilMonoTime)
    source = int(wire.sourceCarStateMonoTime)
    physical = int(wire.sourceBootTime)
    gesture = Gesture(Button(str(wire.button)), Press(str(wire.press)))
    key = 'physical:' + session
    if (wire.version != 1 or not SESSION.fullmatch(session) or str(record.producerSessionId) != session or
        record.eventId <= 0 or record.observedMonoTime != observed or wire.driveStartMonoTime != drive or
        sequence <= owner.sequences.get(key, 0) or len(owner.sequences) >= 8 and key not in owner.sequences or
        not drive < observed <= source <= int(sm.logMonoTime['carState']) <= now_ns <= expiry <= source + 100_000_000 or
        event.logMonoTime != source or now_ns - observed > LIFETIME_NS or
        not 0 < physical <= now_boot_ns <= physical + 300_000_000 or
        wire.settingsFingerprint != fingerprint or wire.buttonMapFingerprint != buttons.fingerprint() or
        gesture.button not in (Button.MODE, Button.CUSTOM) or buttons.action(gesture) != (7 if mode == 'switchback' else 6) or
        now_ns - owner.last_apply_ns < 100_000_000):
      return False
    owner.sequences[key] = sequence
    owner.last_apply_ns = now_ns
    owner.requested[mode] = not owner.requested[mode]
    return True
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return False


def producer_available(sm, *, now_ns: int) -> bool:
  """An existing fresh mode producer must acknowledge this drive, even while off."""
  try:
    drive = int(sm['deviceState'].startedMonoTime)
    if not fresh_service(sm, 'slcState', drive, now_ns, 100_000_000):
      return False
    wire = sm['slcState'].switchbackMode
    return bool(wire.version == 1 and SESSION.fullmatch(str(wire.sessionId)) and wire.sequence > 0 and
                wire.driveStartMonoTime == drive and
                drive < wire.observedMonoTime == int(sm.logMonoTime['slcState']) <= now_ns <=
                wire.validUntilMonoTime <= wire.observedMonoTime + 100_000_000 and
                drive < wire.sourceCarControlMonoTime <= wire.observedMonoTime and
                now_ns - wire.sourceCarControlMonoTime <= LIFETIME_NS)
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return False
