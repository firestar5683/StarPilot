import os

from openpilot.common.params import Params

GPS_SOURCE_PARAM = "GpsSource"
GPS_SOURCES = ("auto", "device", "car")


def ublox_present() -> bool:
  return os.path.exists('/dev/ttyHS0') and not os.path.exists('/persist/comma/use-quectel-gps')


def gps_source_preference(params: Params) -> str:
  """User override: "device", "car", or "auto" (default, also used if the param is unset)."""
  try:
    value = params.get(GPS_SOURCE_PARAM)
  except Exception:  # param not registered on this build
    return "auto"
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="replace")
  return value if value in GPS_SOURCES else "auto"


def use_car_gps(params: Params, CP) -> bool:
  """Whether car GPS (from CAN) should be the gpsLocationExternal source instead of the device's u-blox.

  auto: use car GPS when the device has no u-blox, or when the car's GPS carries real UTC time.
  A car source without time (e.g. the Bolt's OnStar position, stamped with the device clock)
  can't correct a stale clock after a cold boot, so the u-blox is preferred when present.
  """
  from opendbc.car.gps import car_gps_available, car_gps_provides_time

  if not car_gps_available(CP):
    return False
  if not ublox_present():
    return True
  preference = gps_source_preference(params)
  if preference != "auto":
    return preference == "car"
  return car_gps_provides_time(CP)



def get_gps_location_service(params: Params) -> str:
  if params.get_bool("UbloxAvailable") or params.get_bool("CarGpsAvailable"):
    return "gpsLocationExternal"
  else:
    return "gpsLocation"
