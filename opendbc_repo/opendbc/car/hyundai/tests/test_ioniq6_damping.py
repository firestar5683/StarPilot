import pytest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.structs import CarParams
from opendbc.car.hyundai import hyundaicanfd
from opendbc.car.hyundai.hyundaicanfd import CanBus, get_ioniq_6_damp_factors
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags


def _cp(fingerprint):
  CP = CarParams.new_message()
  CP.carFingerprint = fingerprint
  CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEERING |
                 HyundaiFlags.CANFD_LKA_STEERING_ALT)
  CP.openpilotLongitudinalControl = True
  return CP


def _damping(fingerprint, v_ego, torque=100):
  CP = _cp(fingerprint)
  packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
  can_bus = CanBus(CP)
  msgs = hyundaicanfd.create_steering_messages(packer, CP, can_bus, True, True, torque, 0.0, v_ego=v_ego)
  names = [(packer.dbc.addr_to_msg[addr].name, bus) for addr, _, bus in msgs]
  assert names == [("LFA", can_bus.ECAN), ("LKAS_ALT", can_bus.ACAN)]

  lfa = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LFA", 0)], can_bus.ECAN)
  lfa.update([(1, [msgs[0]])])
  lkas = CANParser(DBC[CP.carFingerprint][Bus.pt], [("LKAS_ALT", 0)], can_bus.ACAN)
  lkas.update([(1, [msgs[1]])])
  assert lfa.can_valid and lkas.can_valid
  assert lfa.vl["LFA"]["TORQUE_REQUEST"] == torque
  assert lkas.vl["LKAS_ALT"]["TORQUE_REQUEST"] == torque
  return lfa.vl["LFA"]["DAMP_FACTOR"], lkas.vl["LKAS_ALT"]["DAMP_FACTOR"], lkas.vl["LKAS_ALT"]["Damping_Gain"]


@pytest.mark.parametrize(("mph", "expected"), [
  (10, (100, 0)),     # low speed unchanged: previous LFA 100 floor, LKAS_ALT 0
  (30, (100, 0)),
  (42.5, (105, 125)), # stock medians, 40-45 mph band
  (50, (110, 130)),   # halfway between the 45-50 (107/127) and 50-55 (112/132) bands
  (72.5, (145, 144)), # stock medians, 70-75 mph band
  (95, (163, 154)),   # held beyond the last breakpoint (85-90 mph band)
])
def test_ioniq_6_damping_schedule(mph, expected):
  assert get_ioniq_6_damp_factors(mph * CV.MPH_TO_MS) == expected


def test_ioniq_6_damping_is_encoded_on_both_steering_messages():
  lfa, lkas_alt, damping_gain = _damping(CAR.HYUNDAI_IONIQ_6, 72.5 * CV.MPH_TO_MS)
  assert (lfa, lkas_alt) == (145, 144)
  assert damping_gain == lkas_alt  # same bits: Hyundai's name for the LKAS_ALT damping byte


def test_ioniq_6_without_speed_keeps_previous_values():
  assert _damping(CAR.HYUNDAI_IONIQ_6, None)[:2] == (100, 0)


def test_other_cars_unchanged():
  assert _damping(CAR.HYUNDAI_IONIQ_5, 70 * CV.MPH_TO_MS)[:2] == (100, 0)
