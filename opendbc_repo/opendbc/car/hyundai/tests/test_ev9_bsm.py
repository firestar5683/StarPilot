from types import SimpleNamespace

import pytest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, CanData
from opendbc.car.structs import CarParams
from opendbc.car.hyundai import hyundaicanfd
from opendbc.car.hyundai.carcontroller import BlindspotWarningState, get_ev9_blindspot_warning_inputs, \
                                                    update_blindspot_warning
from opendbc.car.hyundai.carstate import CANFD_NATIVE_BLINDSPOT_STALE_NS, EV9_RAW_BLINDSPOT_STALE_NS, \
                                           decode_canfd_blinker_stalks, resolve_canfd_native_blindspot_state
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags


def test_ev9_blindspot_builder_uses_route_companion_bytes_and_continues_1e5():
  CP = CarParams.new_message()
  CP.carFingerprint = CAR.KIA_EV9
  CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING)
  packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
  can_bus = CanBus(CP)
  parser = CANParser(DBC[CP.carFingerprint][Bus.pt], [("BLINDSPOTS_REAR_CORNERS", 0)], can_bus.ECAN)

  left = hyundaicanfd.create_ccnc_blindspot_status_messages(
    packer, CP, can_bus, 7, left_blindspot=True, left_escalated=True,
    drive_gear=True, left_warning_lamp=True, left_sound_active=True,
  )
  parser.update([(1, left)])
  rear = parser.vl["BLINDSPOTS_REAR_CORNERS"]
  assert rear["BCW_LtIndSta"] == 2
  assert rear["OSMrrLamp_LtIndSta"] == 2
  assert rear["BCW_LtSndWrngSta"] == 1
  assert rear["BCA_Sta"] == 1
  assert left[0].dat[17] == 0x09
  assert left[0].dat[21:23] == bytes.fromhex("6008")
  assert left[1].address == 0x1E5

  quiet = hyundaicanfd.create_ccnc_blindspot_status_messages(
    packer, CP, can_bus, 8, left_blindspot=True, drive_gear=True,
  )
  assert quiet[0].dat[17] == 0x05
  assert quiet[0].dat[21:23] == bytes.fromhex("0000")

  right = hyundaicanfd.create_ccnc_blindspot_status_messages(
    packer, CP, can_bus, 9, right_blindspot=True, right_escalated=True,
    drive_gear=True, right_warning_lamp=True, right_sound_active=True,
  )
  assert right[0].dat[17] == 0x41
  assert right[0].dat[21:23] == bytes.fromhex("6008")


def test_ev9_blindspot_companion_preserves_live_1e5_body():
  CP = CarParams.new_message()
  CP.carFingerprint = CAR.KIA_EV9
  CP.flags = int(HyundaiFlags.CANFD | HyundaiFlags.CANFD_LKA_STEERING)
  packer = CANPacker(DBC[CP.carFingerprint][Bus.pt])
  can_bus = CanBus(CP)
  live_1e5 = bytes.fromhex("00002a1020304050607022038090a080")

  try:
    hyundaicanfd.set_ev9_adrv_baselines([CanData(0x1E5, live_1e5, can_bus.ECAN)])
    messages = hyundaicanfd.create_ccnc_blindspot_status_messages(packer, CP, can_bus, 3)
    assert messages[1].address == 0x1E5
    assert messages[1].dat[2] == 0x2E
    assert messages[1].dat[3:] == live_1e5[3:]
  finally:
    hyundaicanfd.set_ev9_adrv_baselines([])


def test_canfd_blinker_stalks_use_physical_0x413_bits():
  assert decode_canfd_blinker_stalks(1, 0) == (True, False)
  assert decode_canfd_blinker_stalks(0, 1) == (False, True)
  assert decode_canfd_blinker_stalks(0, 0) == (False, False)
  assert decode_canfd_blinker_stalks(2, 2) == (False, False)


@pytest.mark.parametrize("state", [1, 2])
def test_native_blindspot_accepts_valid_0x1ba_lamp_states(state):
  timestamp_nanos = 1_000_000_000
  assert resolve_canfd_native_blindspot_state(
    state, 0, timestamp_nanos, timestamp_nanos + CANFD_NATIVE_BLINDSPOT_STALE_NS,
  ) == (True, False, True)


@pytest.mark.parametrize("timestamp_nanos,now_nanos", [
  (0, 0),
  (1_000_000_000, 999_999_999),
  (1_000_000_000, 1_000_000_000 + CANFD_NATIVE_BLINDSPOT_STALE_NS + 1),
])
def test_native_blindspot_fails_neutral_when_missing_or_stale(timestamp_nanos, now_nanos):
  assert resolve_canfd_native_blindspot_state(1, 2, timestamp_nanos, now_nanos) == (False, False, False)


def test_native_blindspot_rejects_unvalidated_state_three():
  assert resolve_canfd_native_blindspot_state(3, 3, 1_000_000_000, 1_000_000_000) == (False, False, True)


def test_ev9_warning_uses_native_lamp_and_physical_stalk():
  cs = SimpleNamespace(
    native_left_blindspot_state=1,
    native_right_blindspot_state=0,
    native_blindspot_ts=1_000_000_000,
    left_blinker_stalk=True,
    right_blinker_stalk=False,
    # The retained 0x36A proxy must not influence a native warning decision.
    left_blindspot_from_radar=False,
    right_blindspot_from_radar=True,
  )
  inputs = get_ev9_blindspot_warning_inputs(cs, 1_050_000_000)
  assert inputs.source_fresh
  assert inputs.left_detected and inputs.left_stalk_active
  assert not inputs.right_detected and not inputs.right_stalk_active


def test_ev9_warning_ignores_ungated_legacy_raw_proxy_without_native_0x1ba():
  cs = SimpleNamespace(
    native_left_blindspot_state=0,
    native_right_blindspot_state=0,
    native_blindspot_ts=0,
    left_blinker_stalk=True,
    right_blinker_stalk=False,
    left_blindspot_from_radar=True,
    right_blindspot_from_radar=False,
  )
  assert get_ev9_blindspot_warning_inputs(cs, 1_000_000_000).source_fresh is False
  assert get_ev9_blindspot_warning_inputs(cs, 1_000_000_000).left_detected is False


def test_ev9_warning_uses_fresh_distance_gated_fallback_and_matching_stalk():
  timestamp_nanos = 1_000_000_000
  cs = SimpleNamespace(
    native_left_blindspot_state=0,
    native_right_blindspot_state=0,
    native_blindspot_ts=0,
    ev9_reconstructed_left_blindspot=False,
    ev9_reconstructed_right_blindspot=True,
    ev9_reconstructed_blindspot_ts=timestamp_nanos,
    left_blinker_stalk=False,
    right_blinker_stalk=True,
  )
  inputs = get_ev9_blindspot_warning_inputs(cs, timestamp_nanos + EV9_RAW_BLINDSPOT_STALE_NS)
  assert inputs.source_fresh
  assert inputs.right_detected and inputs.right_stalk_active
  assert not inputs.left_detected and not inputs.left_stalk_active

  warning = update_blindspot_warning(
    BlindspotWarningState(), inputs.right_detected and inputs.right_stalk_active, inputs.right_stalk_active,
  )
  assert warning.mirror_lamp_active
  assert warning.sound_active


def test_fresh_native_blindspot_remains_authoritative_over_distance_gated_fallback():
  timestamp_nanos = 1_000_000_000
  cs = SimpleNamespace(
    native_left_blindspot_state=1,
    native_right_blindspot_state=0,
    native_blindspot_ts=timestamp_nanos,
    ev9_reconstructed_left_blindspot=False,
    ev9_reconstructed_right_blindspot=True,
    ev9_reconstructed_blindspot_ts=timestamp_nanos,
    left_blinker_stalk=False,
    right_blinker_stalk=True,
  )
  inputs = get_ev9_blindspot_warning_inputs(cs, timestamp_nanos)
  assert inputs.left_detected
  assert not inputs.right_detected


def test_stale_distance_gated_fallback_fails_neutral():
  timestamp_nanos = 1_000_000_000
  cs = SimpleNamespace(
    native_left_blindspot_state=0,
    native_right_blindspot_state=0,
    native_blindspot_ts=0,
    ev9_reconstructed_left_blindspot=True,
    ev9_reconstructed_right_blindspot=False,
    ev9_reconstructed_blindspot_ts=timestamp_nanos,
    left_blinker_stalk=True,
    right_blinker_stalk=False,
  )
  inputs = get_ev9_blindspot_warning_inputs(cs, timestamp_nanos + EV9_RAW_BLINDSPOT_STALE_NS + 1)
  assert not inputs.source_fresh
  assert not inputs.left_detected


def test_ev9_warning_suppresses_ambiguous_dual_stalk_state():
  cs = SimpleNamespace(
    native_left_blindspot_state=1,
    native_right_blindspot_state=2,
    native_blindspot_ts=1_000_000_000,
    left_blinker_stalk=True,
    right_blinker_stalk=True,
  )
  inputs = get_ev9_blindspot_warning_inputs(cs, 1_000_000_000)
  assert inputs.left_detected and inputs.right_detected
  assert not inputs.left_stalk_active and not inputs.right_stalk_active


def test_stale_native_state_hard_resets_warning_envelope():
  state = BlindspotWarningState()
  assert update_blindspot_warning(state, escalated=True, blinker=True).sound_active

  cs = SimpleNamespace(
    native_left_blindspot_state=2,
    native_right_blindspot_state=0,
    native_blindspot_ts=1_000_000_000,
    left_blinker_stalk=True,
    right_blinker_stalk=False,
  )
  inputs = get_ev9_blindspot_warning_inputs(
    cs, 1_000_000_000 + CANFD_NATIVE_BLINDSPOT_STALE_NS + 1,
  )
  output = update_blindspot_warning(
    state, escalated=inputs.left_detected and inputs.left_stalk_active,
    blinker=inputs.left_stalk_active,
  )
  assert not output.mirror_lamp_active
  assert not output.sound_active
