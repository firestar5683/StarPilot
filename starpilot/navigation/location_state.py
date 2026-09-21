import json
import math
import time


LOCATION_STATE_STALE_SECONDS = 2.5


def finite_number(value):
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    return None
  try:
    number = float(value)
  except OverflowError:
    return None
  return number if math.isfinite(number) else None


def parse_location_state(raw, *, now=None):
  if isinstance(raw, (str, bytes)):
    try:
      raw = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
      return None
  if not isinstance(raw, dict) or raw.get("hasFix") is not True:
    return None

  latitude = finite_number(raw.get("latitude"))
  longitude = finite_number(raw.get("longitude"))
  bearing = finite_number(raw.get("bearing"))
  speed = finite_number(raw.get("speed"))
  updated_at = finite_number(raw.get("updatedAtMonotonic"))
  if latitude is None or longitude is None or bearing is None or speed is None or updated_at is None:
    return None
  if not -90 <= latitude <= 90 or not -180 <= longitude <= 180 or speed < 0:
    return None
  if abs(latitude) < 1e-6 and abs(longitude) < 1e-6:
    return None
  now = time.monotonic() if now is None else now
  if updated_at <= 0 or not 0 <= now - updated_at <= LOCATION_STATE_STALE_SECONDS:
    return None
  return raw


def gps_position_from_service(sm, service, speed):
  # Reusing a cached SubMaster message must not renew its lifetime.
  if not sm.alive[service] or not sm.valid[service]:
    return None
  gps = sm[service]
  return parse_location_state({
    "latitude": gps.latitude,
    "longitude": gps.longitude,
    "bearing": gps.bearingDeg,
    "speed": speed,
    "hasFix": bool(gps.hasFix),
    "updatedAtMonotonic": sm.logMonoTime[service] / 1e9,
    "updatedAtSec": gps.unixTimestampMillis / 1000.0,
  })
