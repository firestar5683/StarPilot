"""Fresh planner-owned Traffic state for the pedal launch consumer."""

from openpilot.starpilot.conditional_mode.manual import read_button_map, TRAFFIC_MODE_ACTION
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner
from openpilot.starpilot.conditional_mode.status import settings_fingerprint
from openpilot.starpilot.conditional_mode.traffic_status import TrafficDisplayProjector


class TrafficLaunchState:
  def __init__(self, params):
    self.params = params
    self.settings = ConditionalSettingsOwner(params)
    self.projector = TrafficDisplayProjector()
    self.buttons = None
    self.checked_ns = -1_000_000_000

  def sample(self, sm, *, now_ns, boot_ns, drive_id):
    if now_ns < self.checked_ns or now_ns - self.checked_ns >= 1_000_000_000:
      self.buttons = read_button_map(self.params)
      self.checked_ns = now_ns
    if self.buttons is None:
      return None
    assigned = TRAFFIC_MODE_ACTION in (self.buttons.distance, self.buttons.distance_long, self.buttons.distance_very_long)
    if not assigned:
      self.projector.reset()
      return False
    snapshot = self.settings.refresh(now_ns)
    verdict = self.settings.verdict(snapshot, now_mono_ns=now_ns, drive_id=drive_id)
    fingerprint = settings_fingerprint(snapshot) if verdict.status == 'ready' and verdict.safe_mode is False else None
    try:
      if (fingerprint is None or not sm.seen['slcState'] or not sm.valid['slcState'] or not sm.alive['slcState'] or
          not drive_id < int(sm.logMonoTime['slcState']) <= now_ns or
          not 0 <= now_ns - int(sm.recv_time['slcState'] * 1e9) <= 100_000_000):
        return None
      display = self.projector.project(sm['slcState'], now_mono_ns=now_ns, now_boot_ns=boot_ns, drive_id=drive_id,
                                       settings_fingerprint=fingerprint, map_fingerprint=self.buttons.fingerprint(),
                                       map_assigned=True, profile_valid=True, long_active=True, selfdrive_enabled=True,
                                       car_valid=True, system_long=True)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      return None
    if display is None or display.state not in ('active', 'off'):
      return None
    return display.state == 'active'
