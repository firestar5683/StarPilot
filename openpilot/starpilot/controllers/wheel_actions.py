import hashlib
import re
import secrets
from dataclasses import dataclass

from opendbc.car import structs
from openpilot.starpilot.conditional_mode.manual import Button, ButtonTracker, Press, ioniq6_media_eligible
from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.conditional_mode.ui_action import fresh_service


ACTIONS = {
  "Off": 0, "Cycle personality": 1, "Force coast": 2, "Pause steering": 3, "Pause longitudinal": 4,
  "Experimental override": 5, "Traffic mode": 6, "Switchback Mode": 7, "Bookmark": 8,
  "Toggle AOL": 9, "Adopt speed limit": 10, "Quick Select 1": 11, "Quick Select 2": 12,
  "Quick Select 3": 13, "Pulse and glide": 14,
}
KEYS = ("LKASButtonControl", "MainCruiseButtonControl", "DistanceButtonControl", "LongDistanceButtonControl",
        "VeryLongDistanceButtonControl", "CancelButtonControl", "LongCancelButtonControl", "VeryLongCancelButtonControl",
        "ModeButtonControl", "LongModeButtonControl", "VeryLongModeButtonControl", "StarButtonControl",
        "LongStarButtonControl", "VeryLongStarButtonControl")
LIFETIME_NS = 250_000_000
SESSION = re.compile(r"[0-9a-f]{32}\Z")
DELIVERED_ACTIONS = frozenset((1, 2, 5, 6, 7, 8, 10, 11, 12, 13, 14))
DEFAULTS = {"DistanceButtonControl": 1, "LongDistanceButtonControl": 5, "VeryLongDistanceButtonControl": 6}
BUTTON_KEYS = {
  Button.LKAS: (KEYS[0],), Button.DISTANCE: KEYS[2:5], Button.MODE: KEYS[8:11], Button.CUSTOM: KEYS[11:14],
}


def eligible(cp):
  try:
    return bool(cp is not None and not cp.notCar and not cp.passive and not cp.dashcamOnly and cp.carFingerprint)
  except (AttributeError, TypeError, ValueError):
    return False


def cp_fingerprint(cp):
  reader = cp.as_reader() if hasattr(cp, "as_reader") else cp
  return hashlib.sha256(reader.as_builder().to_bytes()).hexdigest()


def capture(params):
  result = {}
  for key in KEYS:
    raw, readable = read_saved(params, key, 8)
    if not readable or raw is not None and raw not in tuple(str(value).encode() for value in range(15)):
      return None
    result[key] = int(raw) if raw is not None else DEFAULTS.get(key, 0)
  return result


def key_for(gesture):
  keys = BUTTON_KEYS[gesture.button]
  index = (Press.SHORT, Press.LONG, Press.VERY_LONG).index(gesture.press)
  return keys[index] if index < len(keys) else None


@dataclass(frozen=True)
class WheelCommand:
  session: str
  sequence: int
  observed_ns: int
  drive_id: int
  source_car_ns: int
  key: str
  action: int


class WheelPublisher:
  def __init__(self, params=None):
    self.session = secrets.token_hex(16)
    self.sequence = 0
    self.drive = 0
    self.tracker = ButtonTracker()
    self.cancel_tracker = ButtonTracker()
    self.main_tracker = ButtonTracker()
    self.mapping = None
    self.last_heartbeat = 0
    self.checked_ns = 0
    self.suppress_distance_release = False
    initial = capture(params) if params is not None else None
    self.axis_keys = {key for key, action in (initial or {}).items() if action in (3, 4, 9)}
    self.initial_axis_read = initial is not None

  def observe(self, params, cp, state, *, now_ns, drive_id, media=None, blocked_keys=frozenset()):
    self.suppress_distance_release = any(event.type == structs.CarState.ButtonEvent.Type.gapAdjustCruise and not event.pressed
                                         for event in state.buttonEvents)
    edge = bool(state.buttonEvents) or bool(media is not None and media.samples)
    audit = self.mapping is None or drive_id != self.drive or edge or now_ns - self.checked_ns >= 1_000_000_000
    mapping = capture(params) if audit else self.mapping
    if audit:
      self.checked_ns = now_ns
    if (not eligible(cp) or not state.canValid or state.canTimeout or type(now_ns) is not int or
        type(drive_id) is not int or not 0 < drive_id < now_ns or mapping is None):
      self.tracker = ButtonTracker()
      self.cancel_tracker = ButtonTracker()
      self.main_tracker = ButtonTracker()
      self.mapping = None
      return ()
    if not self.initial_axis_read:
      self.axis_keys = {key for key, action in mapping.items() if action in (3, 4, 9)}
      self.initial_axis_read = True
    if drive_id != self.drive or mapping != self.mapping:
      self.tracker = ButtonTracker()
      self.cancel_tracker = ButtonTracker()
      self.main_tracker = ButtonTracker()
      self.drive, self.mapping = drive_id, mapping
    gestures = [(key_for(gesture), gesture) for gesture in self.tracker.observe(
      state, media if ioniq6_media_eligible(cp) else None)]
    for tracker, source, keys in ((self.cancel_tracker, structs.CarState.ButtonEvent.Type.cancel, KEYS[5:8]),
                                   (self.main_tracker, structs.CarState.ButtonEvent.Type.mainCruise, KEYS[1:2])):
      if not any(mapping[key] in DELIVERED_ACTIONS for key in keys):
        continue
      copy = structs.CarState(canValid=state.canValid, canTimeout=state.canTimeout)
      copy.buttonEvents = [structs.CarState.ButtonEvent(type=structs.CarState.ButtonEvent.Type.gapAdjustCruise,
                                                      pressed=event.pressed)
                           for event in state.buttonEvents if event.type == source]
      for gesture in tracker.observe(copy.as_reader()):
        index = (Press.SHORT, Press.LONG, Press.VERY_LONG).index(gesture.press)
        if index < len(keys):
          gestures.append((keys[index], gesture))
    commands = [(key, mapping[key]) for key, _ in gestures if key is not None and key not in blocked_keys and
                key not in self.axis_keys and mapping[key] in DELIVERED_ACTIONS and
                (key != "MainCruiseButtonControl" or mapping[key] == 10)]
    if commands and not audit:
      current = capture(params)
      self.checked_ns = now_ns
      if current != mapping:
        self.tracker = ButtonTracker()
        self.cancel_tracker = ButtonTracker()
        self.main_tracker = ButtonTracker()
        self.mapping = current
        return ()
    if len(commands) > 1:
      return ()
    if not commands and now_ns - self.last_heartbeat >= 100_000_000:
      commands.append(("", 0))
      self.last_heartbeat = now_ns
    return tuple(commands)

  def publish(self, commands, cp, publisher, *, now_ns, drive_id, source_car_ns, source_control_ns):
    from openpilot.cereal import messaging

    for key, action in commands:
      self.sequence += 1
      event = messaging.new_message("slcCruiseEvent", valid=True, logMonoTime=now_ns)
      event.slcCruiseEvent.kind = "wheelAction"
      event.slcCruiseEvent.eventId = self.sequence
      event.slcCruiseEvent.producerSessionId = self.session
      event.slcCruiseEvent.observedMonoTime = now_ns
      event.slcCruiseEvent.wheelAction = {
        "version": 1, "sessionId": self.session, "sequence": self.sequence, "observedMonoTime": now_ns,
        "validUntilMonoTime": now_ns + LIFETIME_NS, "driveStartMonoTime": drive_id,
        "carFingerprint": cp.carFingerprint, "sourceCarControlMonoTime": source_control_ns,
        "carParamsFingerprint": cp_fingerprint(cp),
        "sourceCarStateMonoTime": source_car_ns, "buttonKey": key, "actionCode": action,
      }
      publisher.send("slcCruiseEvent", event)


class WheelConsumer:
  def __init__(self):
    self.drive = 0
    self.session = None
    self.retired = set()
    self.sequence = 0
    self.last_heartbeat = 0

  def accept(self, event, params, cp, sm, *, now_ns):
    try:
      if not event.valid or str(event.slcCruiseEvent.kind) != "wheelAction" or not eligible(cp):
        return None
      wire = event.slcCruiseEvent.wheelAction
      drive = int(sm["deviceState"].startedMonoTime)
      if drive != self.drive:
        self.__init__()
        self.drive = drive
      observed = int(wire.observedMonoTime)
      source = int(wire.sourceCarStateMonoTime)
      session = str(wire.sessionId)
      key, action = str(wire.buttonKey), int(wire.actionCode)
      if (wire.version != 1 or int(event.slcCruiseEvent.eventId) != int(wire.sequence) or
          str(event.slcCruiseEvent.producerSessionId) != session or
          int(event.slcCruiseEvent.observedMonoTime) != observed or not SESSION.fullmatch(session) or session in self.retired or
          int(wire.driveStartMonoTime) != drive or str(wire.carFingerprint) != cp.carFingerprint or
          str(wire.carParamsFingerprint) != cp_fingerprint(cp) or
          not sm["deviceState"].started or not sm["carState"].canValid or sm["carState"].canTimeout or
          not drive < source <= observed <= now_ns <= int(wire.validUntilMonoTime) or
          int(wire.validUntilMonoTime) - observed != LIFETIME_NS or int(event.logMonoTime) != observed or
          source > int(sm.logMonoTime["carState"]) or now_ns - source > LIFETIME_NS or
          not all(fresh_service(sm, name, drive, now_ns, LIFETIME_NS) for name in ("carState", "carControl")) or
          not fresh_service(sm, "deviceState", drive, now_ns, 1_000_000_000) or
          not drive < int(wire.sourceCarControlMonoTime) <= observed or
          int(wire.sourceCarControlMonoTime) > int(sm.logMonoTime["carControl"]) or
          now_ns - int(wire.sourceCarControlMonoTime) > LIFETIME_NS):
        return None
      if action == 0:
        if key:
          return None
      elif key not in KEYS or action not in DELIVERED_ACTIONS:
        return None
      else:
        mapping = capture(params)
        if mapping is None or mapping[key] != action:
          return None
      if session != self.session:
        if self.session is not None:
          if len(self.retired) >= 8:
            return None
          self.retired.add(self.session)
        self.session, self.sequence = session, 0
      if wire.sequence <= self.sequence:
        return None
      self.sequence = int(wire.sequence)
      self.last_heartbeat = observed
      return WheelCommand(session, self.sequence, observed, drive, source, key, action)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      return None
