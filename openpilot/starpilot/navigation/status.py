import time

from openpilot.starpilot.parked_evidence import RESUME_SKEW_NS

from openpilot.starpilot.navigation.wire import navigation_state

from openpilot.starpilot.gps.source import GPS_MAX_AGE_NS as GPS_TTL_NS, GPS_SOURCES, bearing, observation


def boot_time_ns():
  return time.clock_gettime_ns(getattr(time, "CLOCK_BOOTTIME", time.CLOCK_MONOTONIC))


class NavigationStatusSource:
  def __init__(self, *, mono_clock=time.monotonic_ns, boot_clock=boot_time_ns):
    from openpilot.cereal import messaging
    self.sm = messaging.SubMaster(['starpilotNavigation', *GPS_SOURCES, 'deviceState'])
    self.mono_clock, self.boot_clock = mono_clock, boot_clock
    self.gps_after_mono_ns = mono_clock()
    self.gps_offset_ns = None

  def snapshot(self) -> dict | None:
    if self.sm is None:
      return None
    self.sm.update(0)
    stamp = self.sm.logMonoTime['starpilotNavigation']
    if not self.sm.valid['starpilotNavigation'] or not 0 < stamp <= time.monotonic_ns() <= stamp + 3_000_000_000:
      return None
    state = navigation_state(self.sm['starpilotNavigation'])
    if state is None:
      return None
    return {'revision': state.revision, 'status': state.status,
                'instruction': state.instruction.to_dict() if state.status in ('guiding', 'arrived') else None,
                'route': [row.to_dict() for row in state.route]}

  def search_position(self) -> tuple[float, float] | None:
    position = self.map_position()
    return (position['longitude'], position['latitude']) if position is not None else None

  def network_status(self) -> str:
    """The comma's connection, independent of the browser's network or downloaded maps."""
    if self.sm is None:
      return 'unknown'
    self.sm.update(0)
    try:
      stamp, now = self.sm.logMonoTime['deviceState'], self.mono_clock()
      if not self.sm.valid['deviceState'] or not 0 < stamp <= now <= stamp + 5_000_000_000:
        return 'unknown'
      kind = str(self.sm['deviceState'].networkType)
      return 'offline' if kind == 'none' else 'unknown'
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
      return 'unknown'

  def map_position(self) -> dict | None:
    """Optional search bias; no last-known or route/control authority."""
    if self.sm is None:
      return None
    before, boot, after = self.mono_clock(), self.boot_clock(), self.mono_clock()
    offset = boot - (before + after) // 2
    if (after < before or after - before > RESUME_SKEW_NS or
        (self.gps_offset_ns is not None and abs(offset - self.gps_offset_ns) > RESUME_SKEW_NS)):
      self.gps_after_mono_ns = max(self.gps_after_mono_ns, after)
      self.gps_offset_ns = offset
      return None
    self.gps_offset_ns = offset
    self.sm.update(0)
    before, boot, after = self.mono_clock(), self.boot_clock(), self.mono_clock()
    offset = boot - (before + after) // 2
    if (after < before or after - before > RESUME_SKEW_NS or
        abs(offset - self.gps_offset_ns) > RESUME_SKEW_NS):
      self.gps_after_mono_ns = max(self.gps_after_mono_ns, after)
      self.gps_offset_ns = offset
      return None
    candidates = []
    for service in GPS_SOURCES:
      try:
        fix = observation(self.sm, service, after)
        if fix is None:
          continue
        stamp, gps = fix
        receipt = int(self.sm.recv_time[service] * 1e9)
        if (self.sm.seen[service] and self.sm.alive[service] and self.gps_after_mono_ns < stamp and
            0 <= after - receipt <= GPS_TTL_NS):
          direction = bearing(gps)
          candidates.append((service != "starpilotCarState", stamp,
                             {'longitude': float(gps.longitude), 'latitude': float(gps.latitude),
                              **({'bearing': direction} if direction is not None else {}),
                              'validForMs': min(stamp + GPS_TTL_NS - after, receipt + GPS_TTL_NS - after) / 1e6}))
      except (AttributeError, KeyError, TypeError, ValueError, OverflowError, RuntimeError):
        continue
    return max(candidates, default=(False, 0, None), key=lambda row: row[:2])[2]

  def close(self):
    for socket in getattr(self.sm, 'sock', {}).values():
      close = getattr(socket, 'close', None)
      if close is not None:
        close()
    self.sm = None
