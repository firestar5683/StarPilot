from collections import defaultdict
from types import SimpleNamespace

from opendbc.car.volvo.carcontroller import CarController
from opendbc.car.volvo.helpers import checksum_lca_5_message
from opendbc.car.volvo.interface import CarInterface
from opendbc.car.volvo.values import CAR, DBC
from opendbc.car.volvo.volvocan import create_c1_checksum


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


def test_controller_relays_stock_lca5_angle_when_inactive():
  cp = CarInterface.get_non_essential_params("VOLVO_XC40_RECHARGE")
  controller = CarController(DBC[cp.carFingerprint], cp)
  cs = _state()
  cs.msg_lca_5["LCA_5_STEER"] = 12.0
  cc = SimpleNamespace(latActive=False, actuators=_Actuators())

  _, can_sends = controller.update(cc, cs, 0, None)
  lca5 = next(msg for msg in can_sends if msg[0] == 0x67)

  # The inactive path must not manufacture a new angle command.
  raw = ((lca5[1][6] & 0x7F) << 8) | lca5[1][7]
  if raw & (1 << 14):
    raw -= 1 << 15
  assert abs(raw * 0.05596 - 12.0) < 0.1


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
