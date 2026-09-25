"""Physical Traffic Mode intent; planner is the sole live owner."""

from dataclasses import dataclass
from opendbc.car.gm.profiles import profiles_supported as gm_profiles_supported
import math
import re
import secrets

from openpilot.cereal import messaging
from openpilot.starpilot.conditional_mode.manual import Button, ButtonMap, Gesture, Press, TRAFFIC_MODE_ACTION, ioniq6_media_eligible, read_button_map
from openpilot.starpilot.conditional_mode.status import settings_fingerprint


SOURCE_MAX_AGE_NS = 300_000_000
EVENT_MAX_AGE_NS = 100_000_000
_SESSION = re.compile(r'[0-9a-f]{32}\Z')


@dataclass(frozen=True)
class TrafficVerdict:
  requested: bool
  effective: bool | None
  reason: str
  source_epoch: int
  source_boot_ns: int
  source_mono_ns: int
  settings_fingerprint: str
  map_fingerprint: str
  # Physical status may be unknown while an unused optional button must leave
  # the unrelated ordinary profile alone. None revokes a previously accepted
  # Traffic target on the first loss frame.
  profile_mode: bool | None = None
  controller_source: bool = False


class TrafficOwner:
  def __init__(self):
    self.status_session = secrets.token_hex(16)
    self.status_sequence = 0
    self.card_session: str | None = None
    self.retired: tuple[str, ...] = ()
    self.card_sequence = 0
    self.drive_id = 0
    self.source_epoch = -1
    self.source_boot_ns = 0
    self.source_mono_ns = 0
    self.settings_fingerprint = ''
    self.map_fingerprint = ''
    self.requested = False
    self.controller_source = False
    self.map_checked_ns = 0
    self.cached_buttons: ButtonMap | None = None

  def reset(self, *, retire: bool = False, preserve_map: bool = False) -> None:
    buttons, map_fingerprint, checked_ns = self.cached_buttons, self.map_fingerprint, self.map_checked_ns
    if retire and self.card_session is not None:
      self.retired = (*self.retired[-7:], self.card_session)
    self.card_session = None
    self.card_sequence = 0
    self.drive_id = 0
    self.source_epoch = -1
    self.source_boot_ns = 0
    self.source_mono_ns = 0
    self.settings_fingerprint = ''
    self.map_fingerprint = ''
    self.requested = False
    self.controller_source = False
    self.map_checked_ns = 0
    self.cached_buttons = None
    if preserve_map:
      self.cached_buttons = buttons
      self.map_fingerprint = map_fingerprint
      self.map_checked_ns = checked_ns

  @staticmethod
  def _fresh(sm, name: str, drive_id: int, now_ns: int, limit_ns: int = 250_000_000) -> bool:
    try:
      stamp = sm.logMonoTime[name]
      receipt = sm.recv_time[name]
      if type(stamp) is not int or type(receipt) not in (int, float) or not math.isfinite(receipt):
        return False
      receipt_ns = int(receipt * 1e9)
      return bool(sm.seen[name] and sm.alive[name] and sm.valid[name] and
                  drive_id < stamp <= now_ns and drive_id < receipt_ns <= now_ns and
                  now_ns - stamp <= limit_ns and now_ns - receipt_ns <= limit_ns)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      return False

  def sample(self, event, *, params, settings, sm, cp, drive_id: int,
             now_mono_ns: int, now_boot_ns: int, controller_toggle: bool = False) -> TrafficVerdict:
    if type(drive_id) is not int or drive_id <= 0:
      prior = self.requested
      self.reset()
      return TrafficVerdict(False, None, 'drive_unavailable', -1, 0, 0, '', '', None if prior else False)
    if self.drive_id and drive_id != self.drive_id:
      self.reset()
    gm_distance = gm_profiles_supported(cp)
    if not (ioniq6_media_eligible(cp) or gm_distance) or not cp.openpilotLongitudinalControl or cp.passive or cp.dashcamOnly or cp.notCar:
      self.reset()
      return TrafficVerdict(False, None, 'unsupported_car', -1, 0, 0, '', '', False)
    if (not self._fresh(sm, 'deviceState', drive_id, now_mono_ns, 1_000_000_000) or
        not sm['deviceState'].started or
        not self._fresh(sm, 'carState', drive_id, now_mono_ns) or
        not self._fresh(sm, 'modelV2', drive_id, now_mono_ns) or
        not sm['carState'].canValid or sm['carState'].canTimeout):
      prior = self.requested
      self.reset()
      return TrafficVerdict(False, None, 'can_unavailable', -1, 0, 0, '', '', None if prior else False)
    snapshot = settings.refresh(now_mono_ns)
    setting = settings.verdict(snapshot, now_mono_ns=now_mono_ns, drive_id=drive_id)
    fingerprint = settings_fingerprint(snapshot) if setting.status == 'ready' and setting.safe_mode is False else None
    if fingerprint is None:
      prior = self.requested
      self.reset()
      return TrafficVerdict(False, None, 'settings_unavailable', -1, 0, 0, '', '', None if prior else False)
    if self.settings_fingerprint and self.settings_fingerprint != fingerprint:
      self.reset()
    if controller_toggle:
      self.requested = not self.requested
      self.controller_source = True
    if self.controller_source:
      self.drive_id = drive_id
      self.settings_fingerprint = fingerprint
      authority = (self._fresh(sm, 'carControl', drive_id, now_mono_ns) and
                   self._fresh(sm, 'selfdriveState', drive_id, now_mono_ns) and
                   sm['carControl'].enabled and sm['carControl'].longActive and sm['selfdriveState'].enabled)
      return TrafficVerdict(self.requested, self.requested if authority else None,
                            'active' if authority and self.requested else 'off' if authority else 'authority_unavailable',
                            0, now_boot_ns, int(sm.logMonoTime['modelV2']), fingerprint, '',
                            self.requested if authority else None if self.requested else False, True)
    # Saved map changes revoke intent even without a new physical event. The
    # bounded poll also catches edits while the media source is silent.
    try:
      incoming_map = str(event.slcCruiseEvent.trafficMode.buttonMapFingerprint) if event is not None else ''
      incoming_toggle = bool(event.slcCruiseEvent.trafficMode.toggle) if event is not None else False
    except (AttributeError, TypeError, ValueError):
      incoming_map, incoming_toggle = '', False
    if (self.cached_buttons is None or incoming_toggle or
        (incoming_map and incoming_map != self.map_fingerprint) or
        now_mono_ns - self.map_checked_ns >= 1_000_000_000):
      buttons = read_button_map(params, include_ioniq_media=not gm_distance)
      self.map_checked_ns = now_mono_ns
      if buttons is None:
        prior = self.requested
        self.reset()
        return TrafficVerdict(False, None, 'map_unavailable', -1, 0, 0, fingerprint, '', None if prior else False)
      actual_map = buttons.fingerprint()
      if self.map_fingerprint and self.map_fingerprint != actual_map:
        self.reset()
      self.map_fingerprint = actual_map
      self.cached_buttons = buttons
    else:
      buttons = self.cached_buttons
      actual_map = self.map_fingerprint
    self.settings_fingerprint = fingerprint
    assignments = ((buttons.distance, buttons.distance_long, buttons.distance_very_long) if gm_distance else
                   (buttons.mode, buttons.mode_long, buttons.mode_very_long,
                    buttons.custom, buttons.custom_long, buttons.custom_very_long))
    if TRAFFIC_MODE_ACTION not in assignments:
      self.card_session = None
      self.card_sequence = 0
      self.drive_id = drive_id
      self.source_epoch = -1
      self.source_boot_ns = 0
      self.source_mono_ns = 0
      self.requested = False
      self.controller_source = False
      return TrafficVerdict(False, False, 'unassigned', -1, 0,
                            int(sm.logMonoTime['modelV2']), fingerprint, actual_map, False)
    if event is not None:
      try:
        record = event.slcCruiseEvent
        wire = record.trafficMode
        session = str(wire.sessionId)
        sequence = int(wire.sequence)
        observed = int(wire.observedMonoTime)
        car_stamp = int(wire.sourceCarStateMonoTime)
        expiry = int(wire.validUntilMonoTime)
        source_boot = int(wire.sourceBootTime)
        epoch = int(wire.sourceEpoch)
        valid = (event.valid and str(record.kind) == 'trafficMode' and wire.version == 1 and
                 _SESSION.fullmatch(session) is not None and session not in self.retired and sequence > 0 and
                 str(record.producerSessionId) == session and int(record.observedMonoTime) == observed and
                 int(record.eventId) > 0 and int(wire.driveStartMonoTime) == drive_id and
                 str(wire.settingsFingerprint) == fingerprint and
                 str(wire.buttonMapFingerprint) == self.map_fingerprint and
                 drive_id < observed <= car_stamp <= int(event.logMonoTime) <= now_mono_ns and
                 car_stamp - observed <= EVENT_MAX_AGE_NS and
                 car_stamp < expiry <= car_stamp + EVENT_MAX_AGE_NS and now_mono_ns <= expiry and
                 car_stamp <= sm.logMonoTime['carState'] and
                 0 < source_boot <= now_boot_ns and now_boot_ns - source_boot <= SOURCE_MAX_AGE_NS and
                 (self.card_session != session or sequence > self.card_sequence) and
                 (self.card_session != session or source_boot > self.source_boot_ns))
        if valid:
          if self.card_session is not None and self.card_session != session:
            self.reset(retire=True)
          if self.source_epoch >= 0 and self.source_epoch != epoch:
            self.requested = False
            self.controller_source = False
          self.card_session = session
          self.card_sequence = sequence
          self.drive_id = drive_id
          self.source_epoch = epoch
          self.source_boot_ns = source_boot
          self.source_mono_ns = observed
          self.settings_fingerprint = fingerprint
          self.map_fingerprint = actual_map
          if wire.toggle:
            gesture = Gesture(Button(str(wire.button)), Press(str(wire.press)))
            if (buttons is not None and gesture.button in ((Button.DISTANCE,) if gm_distance else (Button.MODE, Button.CUSTOM)) and
                buttons.action(gesture) == TRAFFIC_MODE_ACTION and self._fresh(sm, 'carControl', drive_id, now_mono_ns) and
                self._fresh(sm, 'selfdriveState', drive_id, now_mono_ns) and
                sm['carControl'].enabled and sm['carControl'].longActive and sm['selfdriveState'].enabled):
              self.requested = not self.requested
        # Invalid/reordered packets never refresh the source clock or toggle.
      except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
        pass
    if self.source_boot_ns <= 0 or now_boot_ns < self.source_boot_ns or now_boot_ns - self.source_boot_ns > SOURCE_MAX_AGE_NS:
      prior = self.requested
      self.reset(preserve_map=True)
      return TrafficVerdict(False, None, 'media_unavailable', -1, 0, 0, fingerprint, '', None if prior else False)
    authority = (self._fresh(sm, 'carControl', drive_id, now_mono_ns) and
                 self._fresh(sm, 'selfdriveState', drive_id, now_mono_ns) and
                 sm['carControl'].enabled and sm['carControl'].longActive and sm['selfdriveState'].enabled)
    return TrafficVerdict(self.requested, self.requested if authority else None,
                          'active' if authority and self.requested else 'off' if authority else 'authority_unavailable',
                          self.source_epoch, self.source_boot_ns, self.source_mono_ns,
                          fingerprint, self.map_fingerprint,
                          self.requested if authority else None if self.requested else False)

  def attach(self, event, verdict: TrafficVerdict, *, now_ns: int, drive_id: int,
             profile_target_ready: bool = False, profile_reason: str = ''):
    if event is None:
      event = messaging.new_message('slcState', valid=True)
      event.logMonoTime = now_ns
    self.status_sequence += 1
    event.slcState.trafficMode = {
      'version': 1, 'sessionId': self.status_session, 'sequence': self.status_sequence,
      'observedMonoTime': now_ns, 'validUntilMonoTime': now_ns + EVENT_MAX_AGE_NS,
      'driveStartMonoTime': drive_id, 'sourceEpoch': max(0, verdict.source_epoch),
      'sourceBootTime': verdict.source_boot_ns, 'accepted': verdict.requested,
      'effective': verdict.effective is True, 'reason': verdict.reason,
      'settingsFingerprint': verdict.settings_fingerprint,
      'buttonMapFingerprint': verdict.map_fingerprint,
      'profileTargetReady': profile_target_ready,
      'profileReason': profile_reason,
      'controllerSource': verdict.controller_source,
    }
    return event
