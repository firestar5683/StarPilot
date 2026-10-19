from types import SimpleNamespace

import pytest

from opendbc.car.gm.values import CAR as GM_CAR, GMFlags
from opendbc.car.hyundai.values import CAR as HYUNDAI_CAR
from opendbc.car.honda.values import CAR as HONDA_CAR
from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import get_planner_v_ego


@pytest.mark.parametrize("fingerprint,pedal,flags,expected", [
  (HYUNDAI_CAR.KIA_RAY_EV, True, 0, 12.0),
  (HYUNDAI_CAR.KIA_RAY_EV, False, 0, 13.0),
  (HYUNDAI_CAR.HYUNDAI_KONA_EV_NON_SCC, True, 0, 13.0),
  (GM_CAR.CHEVROLET_BOLT_CC_2022_2023, True, GMFlags.PEDAL_LONG.value, 12.0),
  (GM_CAR.CHEVROLET_BOLT_CC_2022_2023, False, GMFlags.PEDAL_LONG.value, 13.0),
  (GM_CAR.CHEVROLET_BOLT_CC_2022_2023, True, 0, 13.0),
  (HONDA_CAR.HONDA_CIVIC, False, 0, 13.0),
])
def test_ray_and_bolt_pedal_planner_use_measured_speed(fingerprint, pedal, flags, expected):
  CP = SimpleNamespace(
    brand="gm" if fingerprint == GM_CAR.CHEVROLET_BOLT_CC_2022_2023 else "hyundai",
    carFingerprint=fingerprint, enableGasInterceptorDEPRECATED=pedal, flags=flags,
  )
  CS = SimpleNamespace(vEgo=12.0, vEgoCluster=13.0)
  assert get_planner_v_ego(CP, CS) == expected
