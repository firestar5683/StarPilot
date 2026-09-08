import sys
from types import SimpleNamespace

import pytest

from opendbc.can import CANPacker
from opendbc.car.ford.fordcan import CanBus
from opendbc.car.ford.values import CAR, FordFlags
from .. import fordcan
from ..lateral import FordLateralController, HumanTurnDetector


class FakeSubMaster(dict):
  def __init__(self, services):
    super().__init__({"liveDelay": SimpleNamespace(lateralDelay=0.12)})
    self.updated = dict.fromkeys(services, False)

  def update(self, timeout):
    pass


@pytest.fixture
def controller(monkeypatch):
  messaging = SimpleNamespace(SubMaster=FakeSubMaster)
  monkeypatch.setitem(sys.modules, "cereal.messaging", messaging)
  CP = SimpleNamespace(flags=0, carFingerprint="FORD_EDGE_MK2")
  controller = FordLateralController(CP)
  controller.sm = FakeSubMaster(["modelV2", "liveDelay"])
  controller.curvature_blend_low = 0.4
  controller.curvature_blend_high = 0.4
  controller.curvature_lane_change_factor = 0.85
  return controller


def car_state(speed=15.0, curvature=0.0, steering_pressed=False, steering_angle=0.0):
  return SimpleNamespace(out=SimpleNamespace(
    vEgoRaw=speed,
    yawRate=-curvature * speed,
    steeringPressed=steering_pressed,
    steeringAngleDeg=steering_angle,
  ))


def test_human_turn_requires_sustained_input():
  detector = HumanTurnDetector()
  assert not detector.update(True, True, 0.0)
  for _ in range(29):
    assert not detector.update(True, True, 50.0)
  assert detector.update(True, True, 50.0)
  assert not detector.update(True, False, 50.0)


@pytest.mark.parametrize("canfd", (False, True))
def test_extended_messages_are_curvature_only(canfd):
  CP = SimpleNamespace(flags=FordFlags.CANFD if canfd else 0, safetyConfigs=[SimpleNamespace()])
  packer = CANPacker("ford_lincoln_base_pt")
  can_bus = CanBus(CP)

  _, lka_data, _ = fordcan.create_lka_msg(packer, can_bus)
  assert lka_data[4] & 0x3 == 0x2

  if canfd:
    _, lateral_data, _ = fordcan.create_lat_ctl2_msg(packer, can_bus, 1, 2, 1, 0.001, 0.0, 0)
    raw_path_angle = ((lateral_data[3] & 0x1F) << 6) | (lateral_data[4] >> 2)
    raw_path_offset = ((lateral_data[4] & 0x3) << 8) | lateral_data[5]
  else:
    _, lateral_data, _ = fordcan.create_lat_ctl_msg(packer, can_bus, True, 2, 1, 0.001, 0.0)
    raw_path_angle = (lateral_data[3] << 3) | (lateral_data[4] >> 5)
    raw_path_offset = (lateral_data[5] << 2) | (lateral_data[6] >> 6)

  assert raw_path_angle == 1000
  assert raw_path_offset == 512


def test_curvature_strategy_uses_polynomial_signals(controller):
  result = controller.update(
    SimpleNamespace(latActive=True), car_state(), SimpleNamespace(curvature=0.001))
  assert result.active
  assert 0.0 < result.curvature <= 0.001
  assert result.ramp_type == 2


def test_curvature_lookahead_tracks_bounded_live_delay(controller):
  controller.sm["liveDelay"].lateralDelay = 0.38
  assert controller._curvature_lookahead() == pytest.approx(0.38)

  controller.sm["liveDelay"].lateralDelay = 0.1
  assert controller._curvature_lookahead() == pytest.approx(0.2)

  controller.sm["liveDelay"].lateralDelay = 0.6
  assert controller._curvature_lookahead() == pytest.approx(0.4)


def test_explorer_curvature_lookahead_does_not_follow_actuator_delay(monkeypatch):
  messaging = SimpleNamespace(SubMaster=FakeSubMaster)
  monkeypatch.setitem(sys.modules, "cereal.messaging", messaging)
  CP = SimpleNamespace(flags=0, carFingerprint=CAR.FORD_EXPLORER_MK6)
  controller = FordLateralController(CP)
  controller.sm = FakeSubMaster(["modelV2", "liveDelay"])
  controller.sm["liveDelay"].lateralDelay = 0.42

  assert controller._curvature_lookahead() == pytest.approx(0.20)


def test_curvature_strategy_uses_learned_lookahead(controller, monkeypatch):
  controller.sm["liveDelay"].lateralDelay = 0.38
  lookaheads = []
  monkeypatch.setattr(controller, "_predicted_curvature",
                      lambda _v_ego, lookahead: lookaheads.append(lookahead) or 0.0)

  controller.update(SimpleNamespace(latActive=True), car_state(),
                    SimpleNamespace(curvature=0.001))

  assert lookaheads == [pytest.approx(0.38)]


def test_lane_change_accepts_capnp_enum_wrappers(controller):
  controller.model = SimpleNamespace(meta=SimpleNamespace(
    laneChangeState=SimpleNamespace(raw=2),
    laneChangeDirection=SimpleNamespace(raw=1),
  ))
  assert controller._lane_change() == (True, 1)


def test_curvature_control_stays_active_during_driver_correction(controller):
  controller.human_turn_enabled = True
  CC = SimpleNamespace(latActive=True)
  actuators = SimpleNamespace(curvature=0.001)

  for _ in range(20):
    result = controller.update(
      CC, car_state(steering_pressed=True, steering_angle=10.0), actuators)
    assert result.active


def test_curvature_manual_turn_keeps_session_active_with_neutral_command(controller):
  controller.human_turn_enabled = True
  CC = SimpleNamespace(latActive=True)
  actuators = SimpleNamespace(curvature=0.001)

  controller.update(
    CC, car_state(steering_pressed=True, steering_angle=0.0), actuators)
  for _ in range(30):
    result = controller.update(
      CC, car_state(steering_pressed=True, steering_angle=50.0), actuators)

  assert result.active
  assert result.curvature == 0.0
