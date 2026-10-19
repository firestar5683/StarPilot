from collections import defaultdict
from types import SimpleNamespace

import pytest

from opendbc.can.parser import CANParser
from opendbc.car.volvo.carcontroller import CarController
from opendbc.car.volvo.helpers import checksum_lca_5_message
from opendbc.car.volvo.interface import CarInterface
from opendbc.car.volvo.values import CAR, DBC
from opendbc.car.volvo.volvocan import create_c1_checksum
from opendbc.safety.tests.libsafety import libsafety_py


def _zero_message():
  return defaultdict(int)


def _state():
  return SimpleNamespace(
    out=SimpleNamespace(steeringAngleDeg=0.0, vEgoRaw=12.0, steeringTorque=0.0),
    msg_lca=_zero_message(),
    msg_pscm=_zero_message(),
    msg_pscm_related=_zero_message(),
    msg_lca_3=_zero_message(),
    msg_lca_2=_zero_message(),
    msg_lca_5=_zero_message(),
    msg_lca_4=_zero_message(),
    msg_lca_6=_zero_message(),
    msg_lca_7=_zero_message(),
    pilot_assist_engaged=False,
  )


class _Actuators:
  steeringAngleDeg = 30.0

  def as_builder(self):
    return SimpleNamespace(steeringAngleDeg=self.steeringAngleDeg)


def test_controller_emits_valid_eight_byte_messages_and_lca5_checksum():
  cp = CarInterface.get_non_essential_params("POLESTAR_2")
  controller = CarController(DBC[cp.carFingerprint], cp)
  cs = _state()
  cc = SimpleNamespace(latActive=True, actuators=_Actuators())

  actuators, can_sends = controller.update(cc, cs, 0, None)

  assert can_sends
  assert {msg[2] for msg in can_sends} == {0, 2}
  assert all(len(msg[1]) == 8 for msg in can_sends)
  assert 0.0 < actuators.steeringAngleDeg < 540.0

  lca5 = next(msg for msg in can_sends if msg[0] == 0x67)
  data = lca5[1]
  assert data[2] == checksum_lca_5_message(data[0], data[1], data[3], data[4], data[5])


@pytest.mark.parametrize("fingerprint", [CAR.POLESTAR_2, CAR.VOLVO_XC40_RECHARGE])
def test_controller_relays_complete_stock_lca5_when_inactive(fingerprint):
  cp = CarInterface.get_non_essential_params(fingerprint)
  controller = CarController(DBC[cp.carFingerprint], cp)
  parser = CANParser("volvo_mid_1", [("LCA_5", 50)], 0)
  stock_data = bytes.fromhex("88c04cef1190ba00")
  parser.update([0, [(0x67, stock_data, 0)]])
  cs = _state()
  cs.msg_lca_5 = parser.vl["LCA_5"]
  cc = SimpleNamespace(latActive=False, actuators=_Actuators())
  safety = libsafety_py.libsafety
  config = cp.safetyConfigs[0]
  assert safety.set_safety_hooks(config.safetyModel.raw, config.safetyParam) == 0
  safety.init_tests()
  safety.set_controls_allowed(False)
  safety.safety_rx_hook(libsafety_py.make_CANPacket(0x67, 0, stock_data))

  _, can_sends = controller.update(cc, cs, 0, None)
  lca5 = next(msg for msg in can_sends if msg[0] == 0x67)
  assert lca5[1] == stock_data
  assert safety.safety_tx_hook(libsafety_py.make_CANPacket(lca5[0], lca5[2], lca5[1]))

  cs.msg_lca_5["COUNTER"] = 7
  controller.update(cc, cs, 0, None)
  controller.update(cc, cs, 0, None)
  controller.update(cc, cs, 0, None)
  cc.latActive = True
  _, can_sends = controller.update(cc, cs, 0, None)
  active_lca5 = next(msg for msg in can_sends if msg[0] == 0x67)
  assert active_lca5[1][3] >> 4 == 11


@pytest.mark.parametrize("fingerprint", [CAR.POLESTAR_2, CAR.VOLVO_XC40_RECHARGE])
@pytest.mark.parametrize("driver_torque", [20.0, -20.0, 128.0, -127.0])
def test_override_lca_stream_passes_safety_and_recovers(fingerprint, driver_torque):
  cp = CarInterface.get_non_essential_params(fingerprint)
  controller = CarController(DBC[cp.carFingerprint], cp)
  cs = _state()
  cc = SimpleNamespace(latActive=True, actuators=_Actuators())
  safety = libsafety_py.libsafety
  config = cp.safetyConfigs[0]
  assert safety.set_safety_hooks(config.safetyModel.raw, config.safetyParam) == 0
  safety.init_tests()
  safety.set_controls_allowed(True)

  for active, torque in [(True, 0), (True, driver_torque), (True, -driver_torque),
                        (True, 0), (False, 0), (True, 0)]:
    cc.latActive = active
    cs.out.steeringTorque = torque
    for _ in range(350):
      _, messages = controller.update(cc, cs, 0, None)
      address, data, bus = next(msg for msg in messages if msg[0] == 0x58)
      assert safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data)), (
        active, torque, controller.frame, controller.lca_auth_pos, controller.lca_auth_neg)
    if active and torque == 0:
      assert controller.lca_auth_pos == 614
      assert controller.lca_auth_neg == -614
    elif active:
      assert min(abs(controller.lca_auth_pos), abs(controller.lca_auth_neg)) == 0


def _c1_state():
  return SimpleNamespace(
    out=SimpleNamespace(steeringAngleDeg=10.0, vEgo=12.0, vEgoRaw=12.0),
    c1_lka_torque=5,
    c1_msg_pscm=_zero_message(),
  )


def test_c1_controller_emits_checked_steering_and_pscm_relay():
  cp = CarInterface.get_non_essential_params(CAR.VOLVO_V40)
  controller = CarController(DBC[cp.carFingerprint], cp)
  cc = SimpleNamespace(
    latActive=True,
    actuators=_Actuators(),
    cruiseControl=SimpleNamespace(cancel=False),
  )

  actuators, can_sends = controller.update(cc, _c1_state(), 0, None)
  assert [(msg[0], msg[2]) for msg in can_sends] == [(0x125, 2), (0xD0, 0)]

  fsm = can_sends[1][1]
  assert fsm[7] & 0x3 == 3
  assert fsm[6] == create_c1_checksum(fsm)
  assert 0.0 < actuators.steeringAngleDeg <= 2.0


def test_c1_controller_sends_only_cancel_button():
  cp = CarInterface.get_non_essential_params(CAR.VOLVO_V40)
  controller = CarController(DBC[cp.carFingerprint], cp)
  cc = SimpleNamespace(
    latActive=False,
    actuators=_Actuators(),
    cruiseControl=SimpleNamespace(cancel=True),
  )

  _, can_sends = controller.update(cc, _c1_state(), 0, None)
  buttons = next(msg for msg in can_sends if msg[0] == 0x10)
  assert buttons[2] == 0
  assert buttons[1][7] == 0x10
  assert buttons[1][6] == 0


def test_c1_controller_temporarily_drops_steering_on_zero_torque_fault():
  cp = CarInterface.get_non_essential_params(CAR.VOLVO_V40)
  controller = CarController(DBC[cp.carFingerprint], cp)
  cs = _c1_state()
  cs.c1_lka_torque = 0
  cc = SimpleNamespace(
    latActive=True,
    actuators=_Actuators(),
    cruiseControl=SimpleNamespace(cancel=False),
  )

  directions = []
  for _ in range(23):
    _, can_sends = controller.update(cc, cs, 0, None)
    directions.extend(msg[1][7] & 0x3 for msg in can_sends if msg[0] == 0xD0)

  assert directions[:-1] == [3] * 11
  assert directions[-1] == 0

  while controller.frame <= 122:
    _, can_sends = controller.update(cc, cs, 0, None)
  fsm = next(msg for msg in can_sends if msg[0] == 0xD0)
  assert fsm[1][7] & 0x3 == 3
