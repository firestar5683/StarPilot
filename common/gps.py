from __future__ import annotations

from cereal import car
from openpilot.common.params import Params


def gm_car_params_present(params: Params, CP: car.CarParams | None = None) -> bool:
  if CP is not None and getattr(CP, "brand", None):
    return CP.brand == "gm"
  try:
    raw_car_params = params.get("CarParams")
    if raw_car_params is None:
      return False
    with car.CarParams.from_bytes(raw_car_params) as parsed_cp:
      return parsed_cp.brand == "gm"
  except Exception:
    return False


def get_gps_location_service(params: Params, CP: car.CarParams | None = None) -> str:
  # GM arbitrates device/PPS/OnStar through gpsLocationExternal.
  if gm_car_params_present(params, CP) or params.get_bool("UbloxAvailable") or params.get_bool("CarGpsAvailable"):
    return "gpsLocationExternal"
  else:
    return "gpsLocation"
