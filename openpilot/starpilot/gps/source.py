import json
import math
import time

GPS_SOURCES = {"gpsLocationExternal": "ublox", "gpsLocation": "qcomdiag", "starpilotCarState": "car", "phoneGps": "phone"}
GPS_PRIORITY = {"gpsLocationExternal": 2, "gpsLocation": 2, "starpilotCarState": 1, "phoneGps": 0}
WRAPPED_SOURCES = ("starpilotCarState", "phoneGps")
GPS_MAX_AGE_NS = 2_500_000_000
PHONE_MAX_AGE_NS = 10_000_000_000  # phones in the background send sparsely; keep the last fix this long
SOURCE_SERVICES = {"phoneGps": "starpilotNavigation"}  # rides inside the navigation message
GPS_SERVICES = tuple(dict.fromkeys(SOURCE_SERVICES.get(name, name) for name in GPS_SOURCES))
# backup: phone only without comma or car GPS; comma: never the phone; phone: the phone whenever it has a fix.
GPS_MODES = ("backup", "comma", "phone")
SOURCE_NAMES = {"gpsLocationExternal": "comma", "gpsLocation": "comma", "starpilotCarState": "car", "phoneGps": "phone"}
_mode: list = [-math.inf, "backup"]


def gps_mode(now=None):
  """The GPS source chosen in Galaxy navigation settings, reread at most once a second."""
  now = time.monotonic() if now is None else now
  if now - _mode[0] >= 1.:
    try:
      from openpilot.starpilot.storage import starpilot_storage_root
      with (starpilot_storage_root() / "navigation" / "settings.json").open("rb") as source:
        value = json.loads(source.read(1 << 20)).get("gpsSource", "backup")
    except (OSError, ValueError, AttributeError):
      value = "backup"
    _mode[:] = [now, value if value in GPS_MODES else "backup"]
  return _mode[1]


def gps_priority(service, mode):
  """Rank of a source under the chosen mode, or None when it must not be used."""
  if service == "phoneGps":
    return None if mode == "comma" else 3 if mode == "phone" else 0
  return GPS_PRIORITY[service]


def max_age_ns(service):
  return PHONE_MAX_AGE_NS if service == "phoneGps" else GPS_MAX_AGE_NS


def valid_fix(gps, stamp, envelope, now_ns, max_age):
  if (not gps.hasFix or not 0 < stamp <= envelope <= now_ns <= stamp + max_age or
      not all(math.isfinite(v) for v in (gps.latitude, gps.longitude, gps.horizontalAccuracy)) or
      not (-90 <= gps.latitude <= 90 and -180 <= gps.longitude <= 180 and 0 < gps.horizontalAccuracy <= 25)):
    return None
  return stamp, gps


def observation(sm, service, now_ns):
  try:
    carrier = SOURCE_SERVICES.get(service, service)
    gps = (sm[carrier].phoneGps if service == "phoneGps" else sm[carrier].gps if service in WRAPPED_SOURCES else sm[carrier])
    envelope = int(sm.logMonoTime[carrier])
    stamp = int(gps.sourceMonoTime) if service in WRAPPED_SOURCES else envelope
    if not sm.valid[carrier] or valid_fix(gps, stamp, envelope, now_ns, max_age_ns(service)) is None:
      return None
    if service not in WRAPPED_SOURCES and str(gps.source) != GPS_SOURCES[service]:
      return None
    return stamp, gps
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError, RuntimeError):
    return None


def select_source(sm, now_ns, mode=None, phone_fix=None):
  """The chosen fix and where it came from: (comma|car|phone, (stamp, gps)), or None."""
  mode = mode or gps_mode()
  phone = None if mode == "comma" else phone_fix or observation(sm, "phoneGps", now_ns)
  if mode == "phone" and phone is not None:
    return "phone", phone
  native = [fix for service in ("gpsLocationExternal", "gpsLocation")
            if (fix := observation(sm, service, now_ns)) is not None]
  if native:
    return "comma", max(native, key=lambda fix: fix[0])
  if (car := observation(sm, "starpilotCarState", now_ns)) is not None:
    return "car", car
  return ("phone", phone) if phone is not None else None


def select_location(sm, now_ns, mode=None, phone_fix=None):
  """phone_fix: the navigation process's own phone fix, which it has before it publishes it."""
  selected = select_source(sm, now_ns, mode, phone_fix)
  return selected[1] if selected is not None else None


def bearing(gps):
  value = float(getattr(gps, "bearingDeg", float("nan")))
  accuracy = float(getattr(gps, "bearingAccuracyDeg", 0.))
  return value if math.isfinite(value) and 0 <= value < 360 and math.isfinite(accuracy) and 0 <= accuracy < 180 else None
