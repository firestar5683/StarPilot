import math
import time

from openpilot.starpilot.parked_evidence import RESUME_SKEW_NS

GPS_TTL_NS = 2_500_000_000
GPS_SOURCES = {"gpsLocationExternal": "ublox", "gpsLocation": "qcomdiag"}


def boot_time_ns():
  return time.clock_gettime_ns(getattr(time, "CLOCK_BOOTTIME", time.CLOCK_MONOTONIC))


class NavigationStatusSource:
  def __init__(self, *, mono_clock=time.monotonic_ns, boot_clock=boot_time_ns):
    from openpilot.cereal import messaging
    self.sm = messaging.SubMaster(['starpilotNavigation', *GPS_SOURCES])
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
    state = self.sm['starpilotNavigation']
    return {'revision': state.revision, 'status': state.status,
                'instruction': state.instruction.to_dict() if state.status in ('guiding', 'arrived') else None,
                'route': [row.to_dict() for row in state.route]}

  def search_position(self) -> tuple[float, float] | None:
    position = self.map_position()
    return (position['longitude'], position['latitude']) if position is not None else None

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
    for service, producer in GPS_SOURCES.items():
      try:
        gps = self.sm[service]
        stamp = int(self.sm.logMonoTime[service])
        receipt = int(self.sm.recv_time[service] * 1e9)
        # Both current GPS producers call Python new_message (MONOTONIC).
        # BOOTTIME pairing above detects suspend; it is not the envelope clock.
        if (self.sm.seen[service] and self.sm.alive[service] and self.sm.valid[service] and gps.hasFix and
            str(gps.source) == producer and self.gps_after_mono_ns < stamp <= after <= stamp + GPS_TTL_NS and
            0 <= after - receipt <= GPS_TTL_NS and
            all(math.isfinite(v) for v in (gps.longitude, gps.latitude, gps.horizontalAccuracy)) and
            -180 <= gps.longitude <= 180 and -90 <= gps.latitude <= 90 and
            0 < gps.horizontalAccuracy <= 25):
          candidates.append((stamp, {'longitude': float(gps.longitude), 'latitude': float(gps.latitude),
                                    **({'bearing': float(gps.bearingDeg)} if math.isfinite(getattr(gps, 'bearingDeg', float('nan'))) else {}),
                                    'validForMs': min(stamp + GPS_TTL_NS - after, receipt + GPS_TTL_NS - after) / 1e6}))
      except (AttributeError, KeyError, TypeError, ValueError, OverflowError, RuntimeError):
        continue
    return max(candidates, default=(0, None), key=lambda row: row[0])[1]

  def close(self):
    for socket in getattr(self.sm, 'sock', {}).values():
      close = getattr(socket, 'close', None)
      if close is not None:
        close()
    self.sm = None
