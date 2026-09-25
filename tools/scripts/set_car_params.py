#!/usr/bin/env python3
import sys

from opendbc.car.structs import car
from openpilot.common.params import Params
from openpilot.starpilot.schema_cache import put_cache


def main(args: list[str]) -> None:
  if args:
    raise SystemExit("Route-derived CarParams require source schema provenance and explicit conversion before cache seeding")
  CP = car.CarParams.new_message()
  CP.openpilotLongitudinalControl = True
  CP.alphaLongitudinalAvailable = False
  params = Params()
  params.put("CarParams", CP.to_bytes(), block=True)
  for key in ("CarParamsCache", "CarParamsPersistent"):
    put_cache(params, key, CP, block=True)


if __name__ == "__main__":
  main(sys.argv[1:])
