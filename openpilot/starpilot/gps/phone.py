import math
import threading
import time

FIELDS = {"latitude", "longitude", "altitude", "speed", "bearing", "horizontalAccuracy", "verticalAccuracy",
          "speedAccuracy", "bearingAccuracy", "timestamp", "ageMs"}
MAX_AGE_MS = 2000


def _number(payload, key, required=False):
  value = payload.get(key)
  if value is None and not required:
    return math.nan
  if type(value) not in (int, float) or not math.isfinite(value):
    raise ValueError(f"Invalid {key}")
  return float(value)


def _optional(payload, key, low, high):
  # Phones report an unknown value as null or a negative number.
  value = _number(payload, key)
  return value if low <= value < high else math.nan


def phone_gps(payload, now_ns):
  if not isinstance(payload, dict) or set(payload) - FIELDS:
    raise ValueError("Unexpected location fields")
  latitude, longitude = _number(payload, "latitude", True), _number(payload, "longitude", True)
  accuracy, age_ms = _number(payload, "horizontalAccuracy", True), _number(payload, "ageMs", True)
  if not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or (latitude == 0 and longitude == 0):
    raise ValueError("Invalid position")
  if not 0 < accuracy <= 10_000:
    raise ValueError("Invalid accuracy")
  if not 0 <= age_ms <= MAX_AGE_MS:
    raise ValueError("Location is too old")
  timestamp = payload.get("timestamp", 0)
  if type(timestamp) is not int or not 0 <= timestamp < 2 ** 53:
    raise ValueError("Invalid timestamp")
  bearing_accuracy = _optional(payload, "bearingAccuracy", 0, 180)
  return {
    "sourceMonoTime": now_ns - int(age_ms * 1e6),
    "latitude": latitude,
    "longitude": longitude,
    "altitude": _optional(payload, "altitude", -1000, 10_000),
    "speed": _optional(payload, "speed", 0, 100),
    "bearingDeg": _optional(payload, "bearing", 0, 360) if math.isfinite(bearing_accuracy) else math.nan,
    "horizontalAccuracy": accuracy,
    "verticalAccuracy": _optional(payload, "verticalAccuracy", 0, 10_000),
    "bearingAccuracyDeg": bearing_accuracy,
    "speedAccuracy": _optional(payload, "speedAccuracy", 0, 100),
    "unixTimestampMillis": timestamp,
    "hasFix": True,
  }


class PhoneGpsPublisher:
  def __init__(self, pm_factory=None, mono_clock=time.monotonic_ns):
    self._pm_factory, self._mono_clock = pm_factory, mono_clock
    self._pm = None
    self._lock = threading.Lock()

  def publish(self, payload):
    from openpilot.cereal import messaging
    now = self._mono_clock()
    gps = phone_gps(payload, now)
    message = messaging.new_message("phoneGps", valid=True, logMonoTime=now)
    message.phoneGps.gps = gps
    with self._lock:
      if self._pm is None:
        self._pm = self._pm_factory() if self._pm_factory is not None else messaging.PubMaster(["phoneGps"])
      self._pm.send("phoneGps", message)
    return {"ok": True}
