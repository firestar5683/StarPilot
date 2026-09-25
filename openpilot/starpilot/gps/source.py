import math

GPS_SOURCES = {"gpsLocationExternal": "ublox", "gpsLocation": "qcomdiag", "starpilotCarState": "car"}
GPS_MAX_AGE_NS = 2_500_000_000


def observation(sm, service, now_ns):
  try:
    gps = sm[service].gps if service == "starpilotCarState" else sm[service]
    envelope = int(sm.logMonoTime[service])
    stamp = int(gps.sourceMonoTime) if service == "starpilotCarState" else envelope
    if (not sm.valid[service] or not gps.hasFix or
        not 0 < stamp <= envelope <= now_ns <= stamp + GPS_MAX_AGE_NS or
        not all(math.isfinite(v) for v in (gps.latitude, gps.longitude, gps.horizontalAccuracy)) or
        not (-90 <= gps.latitude <= 90 and -180 <= gps.longitude <= 180 and 0 < gps.horizontalAccuracy <= 25)):
      return None
    if service != "starpilotCarState" and str(gps.source) != GPS_SOURCES[service]:
      return None
    return stamp, gps
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError, RuntimeError):
    return None


def select_location(sm, now_ns):
  native = [fix for service in ("gpsLocationExternal", "gpsLocation")
            if (fix := observation(sm, service, now_ns)) is not None]
  return max(native, key=lambda fix: fix[0]) if native else observation(sm, "starpilotCarState", now_ns)


def bearing(gps):
  value = float(getattr(gps, "bearingDeg", float("nan")))
  accuracy = float(getattr(gps, "bearingAccuracyDeg", 0.))
  return value if math.isfinite(value) and 0 <= value < 360 and math.isfinite(accuracy) and 0 <= accuracy < 180 else None
