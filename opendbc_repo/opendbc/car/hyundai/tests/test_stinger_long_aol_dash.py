import pytest

from opendbc.can import CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.hyundai.carcontroller import classic_aol_dash_enabled
from opendbc.car.hyundai.classic_long_aol import CLASSIC_LONG_IDS, aol_word, independent_buttons_qualified
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC


def controller(car=CAR.KIA_STINGER_2022, *, alpha=True, marked=True):
  fp = gen_empty_fingerprint()
  fp[0][0x391] = 8
  fp[0][0x38d] = 8
  fp[2][0x485] = 4  # LFAHDA_MFC from the camera: enables SEND_LFA
  cp = CarInterface.get_params(car, fp, [], alpha, False, False)
  if alpha and marked:
    cp.safetyConfigs[0].safetyParam = aol_word(cp)
    cp.alternativeExperience = 32
  ci = CarInterface(cp)
  ci.update([])
  return ci


def step(ci, cc, parser):
  stamp = 10_000_000_000 + ci.CC.frame * 10_000_000
  _, packets = ci.CC.update(cc.as_reader(), ci.CS, stamp)
  parser.update((stamp, packets))


def parser(car):
  return CANParser(DBC[car][Bus.pt], [('LKAS11', 0), ('LFAHDA_MFC', 0)], 0)


def test_stinger_long_params_qualify_for_dash_icons():
  ci = controller()
  assert ci.CP.openpilotLongitudinalControl
  assert independent_buttons_qualified(ci.CP, marked_only=True)
  assert classic_aol_dash_enabled(ci.CP)


def test_stinger_long_aol_lateral_only_icon_is_green():
  ci, can = controller(), parser(CAR.KIA_STINGER_2022)
  step(ci, structs.CarControl(enabled=False, latActive=True), can)
  assert can.vl['LKAS11']['CF_Lkas_FcwOpt_USM'] == 2
  assert can.vl['LFAHDA_MFC']['LFA_Icon_State'] == 2


def test_stinger_long_aol_blinks_after_lateral_drops_then_clears():
  ci, can = controller(), parser(CAR.KIA_STINGER_2022)
  for frame in range(101):
    step(ci, structs.CarControl(latActive=frame == 0), can)
    icon = 2 if frame == 0 else 3 if frame < 100 else 0
    assert can.vl['LKAS11']['CF_Lkas_FcwOpt_USM'] == (icon or 1)
    if frame % 5 == 0:
      assert can.vl['LFAHDA_MFC']['LFA_Icon_State'] == icon


def test_stinger_long_lateral_off_icon_is_off():
  ci, can = controller(), parser(CAR.KIA_STINGER_2022)
  for _ in range(10):
    step(ci, structs.CarControl(enabled=False, latActive=False), can)
  assert can.vl['LKAS11']['CF_Lkas_FcwOpt_USM'] == 1
  assert can.vl['LFAHDA_MFC']['LFA_Icon_State'] == 0


def test_stinger_stock_cruise_does_not_use_long_aol_dash_path():
  ci = controller(alpha=False)
  assert not ci.CP.openpilotLongitudinalControl
  assert not independent_buttons_qualified(ci.CP, marked_only=True)
  assert not classic_aol_dash_enabled(ci.CP)
  assert ci.CC.classic_dash_icons is None


@pytest.mark.parametrize('car', sorted(c for c in CLASSIC_LONG_IDS if c not in (CAR.HYUNDAI_ELANTRA_2021, CAR.KIA_STINGER_2022))[:1])
def test_other_classic_long_car_unchanged(car):
  ci, can = controller(car), parser(car)
  assert independent_buttons_qualified(ci.CP, marked_only=True)
  assert not classic_aol_dash_enabled(ci.CP)
  step(ci, structs.CarControl(enabled=False, latActive=True), can)
  assert can.vl['LFAHDA_MFC']['LFA_Icon_State'] == 0
