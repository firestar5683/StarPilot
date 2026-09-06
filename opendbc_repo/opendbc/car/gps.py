import math

from dataclasses import dataclass
from datetime import UTC, datetime
from collections.abc import Callable, Mapping
from typing import Any

from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.ford.values import CAR as FORD_CAR
from opendbc.car.gm.values import CAR as GM_CAR


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
  has_fix = coordinates_valid and dimension in (1, 2) and int(nav2["Gps_B_Falt"]) == 0

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

  heading_rad = math.radians(heading)
  return {
    "latitude": latitude,
    "longitude": longitude,
    "altitude": (float(nav3["GPS_MSL_altitude"]) * 0.3048) if has_fix else 0.0,
    "speed": speed_mps,
    "bearingDeg": heading,
    "horizontalAccuracy": horizontal_accuracy,
    "unixTimestampMillis": timestamp_ms,
    "verticalAccuracy": vertical_accuracy,
    "bearingAccuracyDeg": max(5.0, horizontal_accuracy * 2.0) if speed_mps > 1.0 else 180.0,
    "speedAccuracy": max(0.5, horizontal_accuracy),
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
    "unixTimestampMillis": int(datetime.now(UTC).timestamp() * 1000),
    "verticalAccuracy": 10.0,
    "bearingAccuracyDeg": 180.0,
    "speedAccuracy": 0.5,
    "hasFix": coordinates_valid,
    "satelliteCount": 0,
    "vNED": [0.0, 0.0, 0.0],
  }


FORD_MACH_E_GPS_MESSAGES = (
  "APIMGPS_Data_Nav_1_FD1",
  "APIMGPS_Data_Nav_2_FD1",
  "APIMGPS_Data_Nav_3_FD1",
)
CHEVROLET_BOLT_GPS_MESSAGES = ("TCICOnStarGPSPosition",)

CHEVROLET_BOLT_GPS_CARS = (
  GM_CAR.CHEVROLET_BOLT_ACC_2022_2023,
  GM_CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  GM_CAR.CHEVROLET_BOLT_CC_2022_2023,
  GM_CAR.CHEVROLET_BOLT_CC_2018_2021,
  GM_CAR.CHEVROLET_BOLT_CC_2017,
)


CAR_GPS_CONFIGS: dict[str, CarGpsConfig] = {
  FORD_CAR.FORD_MUSTANG_MACH_E_MK1: CarGpsConfig(
    brand="ford",
    messages=FORD_MACH_E_GPS_MESSAGES,
    decoder=parse_ford_can_gps,
  ),
  **{
    car: CarGpsConfig(
      brand="gm",
      messages=CHEVROLET_BOLT_GPS_MESSAGES,
      decoder=parse_chevrolet_bolt_can_gps,
    )
    for car in CHEVROLET_BOLT_GPS_CARS
  },
}


def get_car_gps_config(CP) -> CarGpsConfig | None:
  config = CAR_GPS_CONFIGS.get(CP.carFingerprint)
  return config if config is not None and config.brand == CP.brand else None


def car_gps_available(CP) -> bool:
  return get_car_gps_config(CP) is not None
