from types import SimpleNamespace

import pytest

from opendbc.car import Bus, ButtonType, gen_empty_fingerprint, structs
from opendbc.car.can_definitions import CanData
from opendbc.car.nissan.carstate import CarState
from opendbc.car.nissan.interface import CarInterface, LEAF_2025_SV_PLUS_CAMERA_FW, leaf_adas_commands_present, \
                                          leaf_adas_commands_silent, restore_leaf_adas_tx
from opendbc.car.nissan.values import CAR, CarControllerParams, NissanSafetyFlags


TEST_TOGGLES = SimpleNamespace(force_torque_controller=False, nnff=False, nnff_lite=False, trailer_load_kg=0)
SUPPORTED_LEAF_FW = [structs.CarParams.CarFw(
  ecu=structs.CarParams.Ecu.fwdCamera,
  fwVersion=LEAF_2025_SV_PLUS_CAMERA_FW,
  address=0x707,
)]


def run_controller(alpha_long, accel=0.0, long_active=True, long_state=structs.CarControl.Actuators.LongControlState.pid):
  CP = CarInterface.get_params(CAR.NISSAN_LEAF, gen_empty_fingerprint(), SUPPORTED_LEAF_FW, alpha_long, False, False, TEST_TOGGLES)
  FPCP = CarInterface.get_starpilot_params(CAR.NISSAN_LEAF, gen_empty_fingerprint(), SUPPORTED_LEAF_FW, CP, TEST_TOGGLES)
  CI = CarInterface(CP, FPCP)
  CI.update([], TEST_TOGGLES)

  CC = structs.CarControl()
  CC.enabled = True
  CC.longActive = long_active
  CC.actuators.accel = accel
  CC.actuators.longControlState = long_state
  _, can_sends = CI.apply(CC.as_reader(), 0, TEST_TOGGLES)
  return {msg[0]: msg for msg in can_sends}


def test_leaf_2025_sv_plus_alpha_long_params():
  stock = CarInterface.get_params(CAR.NISSAN_LEAF, gen_empty_fingerprint(), SUPPORTED_LEAF_FW, False, False, False, None)
  alpha_long = CarInterface.get_params(CAR.NISSAN_LEAF, gen_empty_fingerprint(), SUPPORTED_LEAF_FW, True, False, False, None)

  assert stock.alphaLongitudinalAvailable
  assert not stock.openpilotLongitudinalControl
  assert stock.pcmCruise
  assert not (stock.safetyConfigs[-1].safetyParam & NissanSafetyFlags.LONG_CONTROL)

  assert alpha_long.alphaLongitudinalAvailable
  assert alpha_long.openpilotLongitudinalControl
  assert not alpha_long.pcmCruise
  assert alpha_long.autoResumeSng
  assert alpha_long.safetyConfigs[-1].safetyParam & NissanSafetyFlags.LONG_CONTROL
  assert CarInterface.get_pid_accel_limits(alpha_long, 0, 0) == (CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX)


@pytest.mark.parametrize(("candidate", "car_fw"), [
  (CAR.NISSAN_LEAF, []),
  (CAR.NISSAN_LEAF, [structs.CarParams.CarFw(address=0x707, fwVersion=b"different firmware")]),
  (CAR.NISSAN_LEAF_IC, SUPPORTED_LEAF_FW),
])
def test_other_leaf_variants_do_not_offer_alpha_long(candidate, car_fw):
  CP = CarInterface.get_params(candidate, gen_empty_fingerprint(), car_fw, True, False, False, None)

  assert not CP.alphaLongitudinalAvailable
  assert not CP.openpilotLongitudinalControl
  assert CP.pcmCruise
  assert not (CP.safetyConfigs[-1].safetyParam & NissanSafetyFlags.LONG_CONTROL)


def test_non_leaf_does_not_offer_alpha_long():
  CP = CarInterface.get_params(CAR.NISSAN_ROGUE, gen_empty_fingerprint(), [], True, False, False, None)

  assert not CP.alphaLongitudinalAvailable
  assert not CP.openpilotLongitudinalControl
  assert CP.pcmCruise
  assert not (CP.safetyConfigs[-1].safetyParam & NissanSafetyFlags.LONG_CONTROL)


def test_stock_controller_does_not_send_longitudinal_messages():
  can_sends = run_controller(False)

  assert not ({0x2B0, 0x1C3, 0x707} & can_sends.keys())


def test_alpha_long_controller_sends_stock_shaped_commands_and_keepalive():
  can_sends = run_controller(True)

  assert can_sends[0x2B0][1].hex() == "ff6090ac5b000e03"
  assert can_sends[0x1C3][1].hex() == "000000006400ff27"
  assert can_sends[0x707][1].hex() == "023e010000000000"
  assert all(can_sends[addr][2] == 1 for addr in (0x2B0, 0x1C3))
  assert can_sends[0x707][2] == 0


def test_alpha_long_controller_clamps_to_panda_accel_limit():
  can_sends = run_controller(True, accel=5.0)

  assert can_sends[0x2B0][1].hex() == "007f8fac5b000e0c"


def test_alpha_long_controller_blends_friction_brake_below_regen_limit():
  can_sends = run_controller(True, accel=-2.0)

  assert can_sends[0x2B0][1].hex() == "a827d5ac5b000e09"
  brake = can_sends[0x1C3][1]
  assert ((brake[0] & 0x3F) << 4) | (brake[1] >> 4) == 264
  assert brake[5] & 0x84 == 0x84


def test_alpha_long_controller_sends_inactive_commands_when_disengaged():
  can_sends = run_controller(True, accel=1.0, long_active=False)

  assert can_sends[0x2B0][1].hex() == "dc53a2ac1b000e03"
  assert can_sends[0x1C3][1].hex() == "000000006400ff27"


@pytest.mark.parametrize(("signal", "button_type"), [("SET_BUTTON", ButtonType.decelCruise),
                                                        ("RES_BUTTON", ButtonType.accelCruise)])
def test_leaf_set_resume_release_enables_alpha_long(signal, button_type):
  CP = CarInterface.get_params(CAR.NISSAN_LEAF, gen_empty_fingerprint(), SUPPORTED_LEAF_FW, True, False, False, TEST_TOGGLES)
  FPCP = CarInterface.get_starpilot_params(CAR.NISSAN_LEAF, gen_empty_fingerprint(), SUPPORTED_LEAF_FW, CP, TEST_TOGGLES)
  CS = CarState(CP, FPCP)
  parsers = CS.get_can_parsers(CP)

  parsers[Bus.pt].vl["CRUISE_THROTTLE"][signal] = 1
  pressed, _ = CS.update(parsers, TEST_TOGGLES)
  parsers[Bus.pt].vl["CRUISE_THROTTLE"][signal] = 0
  released, _ = CS.update(parsers, TEST_TOGGLES)

  assert any(event.type == button_type and event.pressed for event in pressed.buttonEvents)
  assert any(event.type == button_type and not event.pressed for event in released.buttonEvents)
  assert CS.update_button_enable(released.buttonEvents)


@pytest.mark.parametrize("ecu_disabled", [False, True])
def test_leaf_ecu_disable_is_strict_and_falls_back(monkeypatch, ecu_disabled):
  CP = CarInterface.get_params(CAR.NISSAN_LEAF, gen_empty_fingerprint(), SUPPORTED_LEAF_FW, True, False, False, None)
  calls = []

  def fake_disable_ecu(*args, **kwargs):
    calls.append(kwargs)
    return ecu_disabled

  monkeypatch.setattr("opendbc.car.nissan.interface.disable_ecu", fake_disable_ecu)
  monkeypatch.setattr("opendbc.car.nissan.interface.leaf_adas_commands_silent", lambda *_: ecu_disabled)
  monkeypatch.setattr("opendbc.car.nissan.interface.restore_leaf_adas_tx", lambda *_: True)
  monkeypatch.setattr("opendbc.car.nissan.interface.ecu_log", lambda *_: None)
  CarInterface.init(CP, None, None)

  assert len(calls) == 1
  assert calls[0]["addr"] == 0x707
  assert calls[0]["bus"] == 0
  assert calls[0]["response_offset"] == 0x20
  assert calls[0]["require_response"] is True
  assert calls[0]["diag_request"] == b"\x10\xf0"
  assert calls[0]["diag_response"] == b"\x50\xf0"
  assert calls[0]["com_cont_req"] == b"\x28\x01"
  assert calls[0]["retry"] == 1
  assert CP.openpilotLongitudinalControl is ecu_disabled
  assert CP.pcmCruise is not ecu_disabled
  assert bool(CP.safetyConfigs[-1].safetyParam & NissanSafetyFlags.LONG_CONTROL) is ecu_disabled


def test_leaf_kwp_data_monitor_session_can_confirm_ecu_disable(monkeypatch):
  CP = CarInterface.get_params(CAR.NISSAN_LEAF, gen_empty_fingerprint(), SUPPORTED_LEAF_FW, True, False, False, None)

  monkeypatch.setattr("opendbc.car.nissan.interface.disable_ecu", lambda *args, **kwargs: True)
  monkeypatch.setattr("opendbc.car.nissan.interface.leaf_adas_commands_silent", lambda *_: True)
  monkeypatch.setattr("opendbc.car.nissan.interface.ecu_log", lambda *_: None)
  CarInterface.init(CP, None, None)

  assert CP.openpilotLongitudinalControl
  assert not CP.pcmCruise
  assert CP.safetyConfigs[-1].safetyParam & NissanSafetyFlags.LONG_CONTROL


def test_leaf_positive_disable_response_without_command_silence_falls_back(monkeypatch):
  CP = CarInterface.get_params(CAR.NISSAN_LEAF, gen_empty_fingerprint(), SUPPORTED_LEAF_FW, True, False, False, None)
  restore_calls = []

  monkeypatch.setattr("opendbc.car.nissan.interface.disable_ecu", lambda *args, **kwargs: True)
  monkeypatch.setattr("opendbc.car.nissan.interface.leaf_adas_commands_silent", lambda *_: False)
  monkeypatch.setattr("opendbc.car.nissan.interface.restore_leaf_adas_tx", lambda *args: restore_calls.append(args) or True)
  monkeypatch.setattr("opendbc.car.nissan.interface.ecu_log", lambda *_: None)
  CarInterface.init(CP, None, None)

  assert len(restore_calls) == 1
  assert not CP.openpilotLongitudinalControl
  assert CP.pcmCruise
  assert not (CP.safetyConfigs[-1].safetyParam & NissanSafetyFlags.LONG_CONTROL)


def test_leaf_adas_command_silence_requires_live_bus_without_stock_commands(monkeypatch):
  monkeypatch.setattr("opendbc.car.nissan.interface.ecu_log", lambda *_: None)

  def unrelated_bus_traffic(wait_for_one=False):
    return [] if not wait_for_one else [[CanData(0x123, b"\x00", 1)]]

  assert leaf_adas_commands_silent(unrelated_bus_traffic, settle_time=0, observe_time=0.001)

  def stock_command_traffic(wait_for_one=False):
    return [] if not wait_for_one else [[CanData(0x2B0, b"\x00" * 8, 1)]]

  assert not leaf_adas_commands_silent(stock_command_traffic, settle_time=0, observe_time=0.001)
  assert not leaf_adas_commands_silent(lambda wait_for_one=False: [], settle_time=0, observe_time=0.001)


def test_leaf_adas_command_recovery_requires_stock_command(monkeypatch):
  monkeypatch.setattr("opendbc.car.nissan.interface.ecu_log", lambda *_: None)

  def stock_command_traffic(wait_for_one=False):
    return [] if not wait_for_one else [[CanData(0x1C3, b"\x00" * 8, 1)]]

  assert leaf_adas_commands_present(stock_command_traffic, settle_time=0, observe_time=0.001)
  assert not leaf_adas_commands_present(lambda wait_for_one=False: [], settle_time=0, observe_time=0.001)


def test_leaf_adas_restore_returns_to_kwp_default_session(monkeypatch):
  queries = []

  class FakeQuery:
    def __init__(self, can_send, can_recv, bus, addrs, request, response, response_offset):
      queries.append((bus, addrs, request, response, response_offset))

    def get_data(self, timeout):
      return {(0x707, None): b""}

  monkeypatch.setattr("opendbc.car.nissan.interface.IsoTpParallelQuery", FakeQuery)
  monkeypatch.setattr("opendbc.car.nissan.interface.leaf_adas_commands_present", lambda *_: True)
  monkeypatch.setattr("opendbc.car.nissan.interface.ecu_log", lambda *_: None)

  assert restore_leaf_adas_tx(lambda **kwargs: [], lambda msgs: None)
  assert queries == [(0, [0x707], [b"\x10\x81"], [b"\x50\x81"], 0x20)]
