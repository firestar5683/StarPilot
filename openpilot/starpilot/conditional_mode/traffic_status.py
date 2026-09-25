"""Read-only, source-bound Traffic Mode status for the onroad display."""

from dataclasses import dataclass
import re


_SESSION = re.compile(r'[0-9a-f]{32}\Z')
_FINGERPRINT = re.compile(r'[0-9a-f]{64}\Z')
_SOURCE_UNAVAILABLE = frozenset(('media_unavailable', 'settings_unavailable', 'map_unavailable',
                                  'can_unavailable', 'clock_unavailable'))


@dataclass(frozen=True)
class TrafficDisplay:
  state: str  # active, paused, off, unavailable_profile, unavailable_source
  label: str


class TrafficDisplayProjector:
  """Never turn a saved button assignment or an old planner frame into status."""

  def __init__(self):
    self.drive_id = 0
    self.session: str | None = None
    self.sequence = 0
    self.observed_ns = 0
    self.last: tuple | None = None
    self.retired: tuple[str, ...] = ()

  def reset(self) -> None:
    self.drive_id = 0
    self.session = None
    self.sequence = 0
    self.observed_ns = 0
    self.last = None
    self.retired = ()

  def project(self, state, *, now_mono_ns: int, now_boot_ns: int, drive_id: int,
              settings_fingerprint: str | None, map_fingerprint: str | None,
              map_assigned: bool, profile_valid: bool, long_active: bool, selfdrive_enabled: bool,
              car_valid: bool, system_long: bool) -> TrafficDisplay | None:
    if type(drive_id) is not int or drive_id <= 0:
      self.reset()
      return None
    if self.drive_id != drive_id:
      self.reset()
      self.drive_id = drive_id
    if state is None:
      return None
    try:
      wire = state.trafficMode
      session, sequence = str(wire.sessionId), int(wire.sequence)
      observed, expiry = int(wire.observedMonoTime), int(wire.validUntilMonoTime)
      source_boot, source_epoch = int(wire.sourceBootTime), int(wire.sourceEpoch)
      source_settings, source_map = str(wire.settingsFingerprint), str(wire.buttonMapFingerprint)
      controller_source = bool(getattr(wire, "controllerSource", False))
      accepted, effective, ready = bool(wire.accepted), bool(wire.effective), bool(wire.profileTargetReady)
      reason, profile_reason = str(wire.reason), str(wire.profileReason)
      identity = (session, sequence, observed, expiry, source_boot, source_epoch, source_settings,
                  source_map, accepted, effective, ready, reason, profile_reason, controller_source)
      if (wire.version != 1 or _SESSION.fullmatch(session) is None or session in self.retired or sequence <= 0 or
          type(now_mono_ns) is not int or type(now_boot_ns) is not int or now_boot_ns <= 0 or
          not drive_id < observed <= now_mono_ns <= expiry <= observed + 100_000_000 or
          int(wire.driveStartMonoTime) != drive_id or source_epoch < 0 or
          (source_boot > 0 and not source_boot <= now_boot_ns <= source_boot + 300_000_000) or
          source_settings and _FINGERPRINT.fullmatch(source_settings) is None or
          source_map and _FINGERPRINT.fullmatch(source_map) is None):
        return None
      if source_settings and source_settings != settings_fingerprint:
        return None
      if source_map and source_map != map_fingerprint:
        return None
      if self.session is not None and session != self.session:
        self.retired = (*self.retired[-7:], self.session)
        self.session, self.sequence, self.observed_ns, self.last = session, sequence, observed, identity
        return None  # One fresh-frame barrier after a planner restart.
      if session == self.session:
        if (sequence < self.sequence or sequence == self.sequence and identity != self.last or
            sequence > self.sequence and observed <= self.observed_ns):
          return None
      self.session, self.sequence, self.observed_ns, self.last = session, sequence, observed, identity
      if reason in _SOURCE_UNAVAILABLE:
        return TrafficDisplay('unavailable_source', 'TRAFFIC UNAVAILABLE')
      if controller_source:
        map_assigned = True
      if settings_fingerprint is None or (not controller_source and map_fingerprint is None):
        return None
      if not accepted and not effective and reason == 'off' and map_assigned:
        return TrafficDisplay('off', 'TRAFFIC OFF')
      if accepted and not effective and reason == 'authority_unavailable' and map_assigned:
        return TrafficDisplay('paused', 'TRAFFIC PAUSED')
      if (accepted and effective and reason == 'active' and map_assigned and long_active and selfdrive_enabled and
          car_valid and system_long):
        if not ready or not profile_valid or profile_reason != 'qualified':
          return TrafficDisplay('unavailable_profile', 'TRAFFIC PROFILE UNAVAILABLE')
        return TrafficDisplay('active', 'TRAFFIC')
    except (AttributeError, TypeError, ValueError, OverflowError):
      return None
    return None
