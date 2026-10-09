import time

from openpilot.cereal import messaging
from openpilot.starpilot.gps.source import GPS_MAX_AGE_NS

FIELDS = ("latitude", "longitude", "altitude", "speed", "bearingDeg", "horizontalAccuracy",
          "verticalAccuracy", "bearingAccuracyDeg", "speedAccuracy", "unixTimestampMillis", "hasFix", "vNED")


def boot_time_ns():
  return time.clock_gettime_ns(getattr(time, "CLOCK_BOOTTIME", time.CLOCK_MONOTONIC))


class CarGpsPublisher:
  def __init__(self, *, mono_clock=time.monotonic_ns, boot_clock=boot_time_ns):
    self.mono_clock, self.boot_clock = mono_clock, boot_clock
    self.last_source_ns = 0
    self.cached_gps = None

  def update(self, car_state, pm, message=None):
    getter = getattr(car_state, "get_car_gps", None)
    fix = getter() if getter is not None else None
    gps, after = None, 0
    if fix is not None:
      source_ns = int(fix["timestamp_nanos"])
      if source_ns > self.last_source_ns:
        self.last_source_ns = source_ns
        before, boot, after = self.mono_clock(), self.boot_clock(), self.mono_clock()
        # pandad timestamps received CAN in BOOTTIME; Python Events use MONOTONIC.
        age = boot - source_ns
        if 0 <= after - before <= 1_000_000 and 0 <= age <= GPS_MAX_AGE_NS:
          stamp = before - age
          if stamp > 0:
            gps = {key: fix[key] for key in FIELDS}
            gps["vNED"] = list(fix["vNED"])
            gps["sourceMonoTime"] = stamp
            self.cached_gps = gps if fix["hasFix"] else None
    if message is None:
      if gps is None:
        return
      message = messaging.new_message("starpilotCarState", valid=bool(gps["hasFix"]), logMonoTime=after)
    gps = gps if gps is not None else self.cached_gps
    if gps is not None and 0 < gps["sourceMonoTime"] <= int(message.logMonoTime) <= gps["sourceMonoTime"] + GPS_MAX_AGE_NS:
      message.starpilotCarState.gps = gps
    pm.send("starpilotCarState", message)
