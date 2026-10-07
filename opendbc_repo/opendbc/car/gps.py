import math

from dataclasses import dataclass
from datetime import UTC, datetime
from collections.abc import Callable, Mapping
from typing import Any

from opendbc.car.common.conversions import Conversions as CV
from opendbc.car import Bus
from opendbc.car.ford.values import DBC as FORD_DBC
from opendbc.car.gm.values import DBC as GM_DBC
from opendbc.car.volkswagen.values import DBC as VW_DBC, VolkswagenFlags


CarGpsSample = dict[str, Any]
CanGpsDecoder = Callable[..., CarGpsSample | None]


@dataclass(frozen=True)
class CarGpsConfig:
  """Vehicle-specific CAN GPS inputs and decoder."""

  brand: str
  messages: tuple[str, ...]
  decoder: CanGpsDecoder


def _dop_accuracy(dop: float, default: float = 500.0) -> float:
  """Convert Ford's dimensionless DOP into a conservative meter estimate."""
  return max(1.0, dop * 5.0) if 0.0 <= dop <= 5.8 else default


def parse_ford_can_gps(nav1: Mapping[str, float], nav2: Mapping[str, float], nav3: Mapping[str, float]) -> CarGpsSample | None:
  """Decode the Ford APIM GPS messages into the fields used by gpsLocationExternal."""
  year = int(nav2["GpsUtcYr_No_Actl"])
  month = int(nav2["GpsUtcMnth_No_Actl"])
  day = int(nav2["GpsUtcDay_No_Actl"])
  hour = int(nav2["GPS_UTC_hours"])
  minute = int(nav2["GPS_UTC_minutes"])
  second = int(nav2["GPS_UTC_seconds"])
  try:
    timestamp_ms = int(datetime(year, month, day, hour, minute, second, tzinfo=UTC).timestamp() * 1000)
  except ValueError:
    return None

  latitude_direction = int(nav1["GpsHsphLattSth_D_Actl"])
  longitude_direction = int(nav1["GpsHsphLongEast_D_Actl"])
  latitude_degrees = abs(float(nav1["GPS_Latitude_Degrees"]))
  longitude_degrees = abs(float(nav1["GPS_Longitude_Degrees"]))
  latitude_minutes = float(nav1["GPS_Latitude_Minutes"]) + float(nav1["GPS_Latitude_Min_dec"])
  longitude_minutes = float(nav1["GPS_Longitude_Minutes"]) + float(nav1["GPS_Longitude_Min_dec"])

  coordinates_valid = (
    latitude_direction in (1, 2) and longitude_direction in (1, 2) and
    0.0 <= latitude_degrees <= 90.0 and 0.0 <= longitude_degrees <= 180.0 and
    0.0 <= latitude_minutes < 60.0 and 0.0 <= longitude_minutes < 60.0
  )
  latitude = (1.0 if latitude_direction == 2 else -1.0) * (latitude_degrees + latitude_minutes / 60.0) if coordinates_valid else 0.0
  longitude = (1.0 if longitude_direction == 1 else -1.0) * (longitude_degrees + longitude_minutes / 60.0) if coordinates_valid else 0.0

  dimension = int(nav3["GPS_dimension"])
  has_fix = (coordinates_valid and -90. <= latitude <= 90. and -180. <= longitude <= 180. and
             dimension in (1, 2) and int(nav2["Gps_B_Falt"]) == 0)

  speed_mph = float(nav3["GPS_Speed"])
  speed_mps = speed_mph * CV.MPH_TO_MS
  heading = float(nav3["GPS_Heading"])
  if speed_mph in (254.0, 255.0) or not math.isfinite(speed_mps) or not 0.0 <= speed_mps <= 200.0:
    speed_mps = 0.0
  if not math.isfinite(heading) or not 0.0 <= heading < 360.0:
    heading = 0.0

  vertical_accuracy = _dop_accuracy(float(nav3["GPS_Vdop"]))
  horizontal_accuracy = _dop_accuracy(float(nav3["GPS_Hdop"]))
  satellite_count = int(nav3["GPS_Sat_num_in_view"])
  if not 0 <= satellite_count < 30:  # 30 and 31 are Ford's unknown/invalid values.
    satellite_count = 0

  motion_valid = has_fix and speed_mph not in (254., 255.) and 0. <= float(nav3["GPS_Speed"]) * CV.MPH_TO_MS <= 200.
  motion_valid = motion_valid and math.isfinite(float(nav3["GPS_Heading"])) and 0. <= float(nav3["GPS_Heading"]) < 360.
  if not motion_valid:
    speed_mps = 0.
  altitude = float(nav3["GPS_MSL_altitude"]) * .3048
  altitude_valid = math.isfinite(altitude)
  heading_rad = math.radians(heading)
  return {
    "latitude": latitude,
    "longitude": longitude,
    "altitude": altitude if has_fix and altitude_valid else 0.0,
    "speed": speed_mps,
    "bearingDeg": heading,
    "horizontalAccuracy": horizontal_accuracy,
    "unixTimestampMillis": timestamp_ms,
    "verticalAccuracy": vertical_accuracy if altitude_valid else 500.,
    "bearingAccuracyDeg": max(5.0, horizontal_accuracy * 2.0) if speed_mps > 1.0 else 180.0,
    "speedAccuracy": max(0.5, horizontal_accuracy) if motion_valid else 100.,
    "hasFix": has_fix,
    "satelliteCount": satellite_count,
    "vNED": [speed_mps * math.cos(heading_rad), speed_mps * math.sin(heading_rad), 0.0],
  }


def parse_chevrolet_bolt_can_gps(position: Mapping[str, float]) -> CarGpsSample | None:
  """Decode the Bolt's OnStar GPS position message."""
  try:
    latitude = float(position["GPSLatitude"]) / 3_600_000.0
    longitude = float(position["GPSLongitude"]) / 3_600_000.0
  except (KeyError, TypeError, ValueError):
    return None

  coordinates_valid = (
    math.isfinite(latitude) and math.isfinite(longitude) and
    -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0 and
    (latitude != 0.0 or longitude != 0.0)
  )
  if not coordinates_valid:
    latitude = longitude = 0.0

  return {
    "latitude": latitude,
    "longitude": longitude,
    "altitude": 0.0,
    "speed": 0.0,
    "bearingDeg": 0.0,
    "horizontalAccuracy": 6.0,
    "unixTimestampMillis": 0,
    "verticalAccuracy": 10.0,
    "bearingAccuracyDeg": 180.0,
    "speedAccuracy": 0.5,
    "hasFix": coordinates_valid,
    "satelliteCount": 0,
    "vNED": [0.0, 0.0, 0.0],
  }


def parse_volkswagen_taos_can_gps(position: Mapping[str, float], motion: Mapping[str, float],
                                altitude: Mapping[str, float], status: Mapping[str, float]) -> CarGpsSample | None:
  packet_ids = (position["GNSS_Nachrichtenpaket_ID1"], motion["GNSS_Nachrichtenpaket_ID2"],
                altitude["GNSS_Nachrichtenpaket_ID4"], status["GNSS_Nachrichtenpaket_ID5"])
  if len(set(packet_ids)) != 1:
    return None

  timestamp_ms = int(status["GNSS_UTC_Zeit"]) * 1000
  if timestamp_ms == 0:
    return None

  latitude = float(position["GNSS_LatitudeMagnitude"])
  longitude = float(position["GNSS_LongitudeMagnitude"])
  coordinates_valid = (math.isfinite(latitude) and math.isfinite(longitude) and
                       0.0 <= latitude <= 90.0 and 0.0 <= longitude <= 180.0 and (latitude != 0.0 or longitude != 0.0))
  if coordinates_valid:
    latitude *= -1.0 if position["GNSS_LatitudeSouth"] else 1.0
    longitude *= -1.0 if position["GNSS_LongitudeWest"] else 1.0
  else:
    latitude = longitude = 0.0

  satellite_count = int(status["GNSS_Genutzte_Satelliten"])
  hemisphere_validated = position["GNSS_LatitudeSouth"] == 0 and position["GNSS_LongitudeWest"] == 1
  has_fix = (coordinates_valid and hemisphere_validated and position["GNSS_PositionStatus"] == 3 and
             status["GNSS_Empfaenger_Status"] == 1 and
             bool(status["GNSS_GPS_in_Nutzung"] or status["GNSS_GLONASS_in_Nutzung"]) and 4 <= satellite_count <= 31)

  speed = float(motion["GNSS_Speed"])
  bearing = float(motion["GNSS_Bearing"])
  speed_valid = math.isfinite(speed) and 0.0 <= speed <= 127.5
  bearing_valid = math.isfinite(bearing) and 0.0 <= bearing < 360.0
  speed = speed if has_fix and speed_valid else 0.0
  bearing = bearing if has_fix and bearing_valid else 0.0
  height = float(altitude["GNSS_Ortung_Hoehe"])
  height_valid = math.isfinite(height) and -500.0 <= height <= 7686.0
  heading_rad = math.radians(bearing)

  return {
    "latitude": latitude,
    "longitude": longitude,
    "altitude": height if has_fix and height_valid else 0.0,
    "speed": speed,
    "bearingDeg": bearing,
    "horizontalAccuracy": 20.0,
    "unixTimestampMillis": timestamp_ms,
    "verticalAccuracy": 50.0 if height_valid else 500.0,
    "bearingAccuracyDeg": 10.0 if has_fix and bearing_valid and speed > 1.0 else 180.0,
    "speedAccuracy": 1.5 if speed_valid and bearing_valid else 100.0,
    "hasFix": has_fix,
    "satelliteCount": satellite_count if 0 <= satellite_count <= 31 else 0,
    "vNED": [speed * math.cos(heading_rad), speed * math.sin(heading_rad), 0.0] if bearing_valid else [0.0, 0.0, 0.0],
  }


FORD_MACH_E_GPS_MESSAGES = (
  "APIMGPS_Data_Nav_1_FD1",
  "APIMGPS_Data_Nav_2_FD1",
  "APIMGPS_Data_Nav_3_FD1",
)
CHEVROLET_BOLT_GPS_MESSAGES = ("TCICOnStarGPSPosition",)
VOLKSWAGEN_TAOS_GPS_MESSAGES = ("GNSS_01", "GNSS_02", "GNSS_04", "GNSS_05")

def get_car_gps_config(CP) -> CarGpsConfig | None:
  # These are optional decode candidates, not proof that a vehicle broadcasts GPS.
  mappings = {"gm": GM_DBC, "ford": FORD_DBC, "volkswagen": VW_DBC}
  dbc = mappings.get(CP.brand, {}).get(CP.carFingerprint, {}).get(Bus.pt)
  if CP.brand == "gm" and dbc in ("gm_global_a_powertrain_generated", "cadillac_ct6_powertrain"):
    return CarGpsConfig("gm", CHEVROLET_BOLT_GPS_MESSAGES, parse_chevrolet_bolt_can_gps)
  if CP.brand == "ford" and dbc == "ford_lincoln_base_pt":
    return CarGpsConfig("ford", FORD_MACH_E_GPS_MESSAGES, parse_ford_can_gps)
  if CP.brand == "volkswagen" and dbc == "vw_mqb" and not CP.flags & (
      VolkswagenFlags.PQ | VolkswagenFlags.MLB | VolkswagenFlags.MEB):
    return CarGpsConfig("volkswagen", VOLKSWAGEN_TAOS_GPS_MESSAGES, parse_volkswagen_taos_can_gps)
  return None


class CarGpsTracker:
  MAX_AGE_NS = 2_500_000_000
  MAX_SKEW_NS = 2_000_000_000

  def __init__(self, CP):
    self.config = get_car_gps_config(CP)
    self.sample: CarGpsSample | None = None
    self.timestamps: tuple[int, ...] = ()
    self.now_ns = 0
    self.previous_position: tuple[float, float] | None = None
    self.bearing: float | None = None
    self.bearing_ns = 0
    self.vw_fix_utc_ms = 0

  def update(self, parser, *, speed: float = 0., backward: bool = False) -> None:
    now = parser._last_update_nanos
    if now < self.now_ns:
      self.sample = None
      self.previous_position = self.bearing = None
      return
    self.now_ns = now
    if self.config is None:
      return
    stamps = tuple(max(parser.ts_nanos[name].values(), default=0) for name in self.config.messages)
    current = (all(0 < stamp <= now and now - stamp <= self.MAX_AGE_NS for stamp in stamps) and
               max(stamps) - min(stamps) <= self.MAX_SKEW_NS)
    if not current:
      self.sample = None
      self.previous_position = self.bearing = None
      return
    if self.timestamps and not all(a > b for a, b in zip(stamps, self.timestamps, strict=True)):
      return
    self.timestamps = stamps
    try:
      sample = self.config.decoder(*(parser.vl[name] for name in self.config.messages))
    except (KeyError, TypeError, ValueError, OverflowError):
      sample = None
    if sample is None:
      self.sample = None
      self.previous_position = self.bearing = None
      return
    if self.config.brand == "volkswagen" and sample["hasFix"]:
      if sample["unixTimestampMillis"] <= self.vw_fix_utc_ms:
        return
      self.vw_fix_utc_ms = sample["unixTimestampMillis"]
    sample["timestamp_nanos"] = min(stamps)
    if self.config.brand == "gm":
      sample.update(altitude=0., verticalAccuracy=500., speed=0., speedAccuracy=100.,
                    bearingDeg=0., bearingAccuracyDeg=180., vNED=[0., 0., 0.])
      if sample["hasFix"]:
        position = sample["latitude"], sample["longitude"]
        if backward or now - self.bearing_ns > self.MAX_AGE_NS:
          self.bearing = None
        moving = math.isfinite(speed) and 1. < speed <= 100. and not backward
        if self.previous_position is not None and moving:
          dy = (position[0] - self.previous_position[0]) * 111139.
          dx = (position[1] - self.previous_position[1]) * 111139. * math.cos(math.radians(position[0]))
          if math.hypot(dx, dy) > 1.5:
            self.bearing = math.degrees(math.atan2(dx, dy)) % 360.
            self.bearing_ns = now
        self.previous_position = position
        if self.bearing is not None and moving:
          angle = math.radians(self.bearing)
          sample.update(speed=speed, speedAccuracy=1.5, bearingDeg=self.bearing, bearingAccuracyDeg=10.,
                        vNED=[speed * math.cos(angle), speed * math.sin(angle), 0.])
      else:
        self.previous_position = self.bearing = None
    self.sample = sample

  def get(self) -> CarGpsSample | None:
    if self.sample is None or not 0 <= self.now_ns - self.sample["timestamp_nanos"] <= self.MAX_AGE_NS:
      return None
    return self.sample
