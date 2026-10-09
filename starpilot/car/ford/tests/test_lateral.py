import sys
from types import SimpleNamespace

import pytest

from opendbc.can import CANPacker
from opendbc.car import structs
from opendbc.car.ford.fordcan import CanBus
from opendbc.car.ford.values import CAR, FordFlags, FordSafetyFlags
from .. import fordcan
from ..lateral import FordLateralController, HumanTurnDetector, STEER_DT


class FakeSubMaster(dict):
  def __init__(self, services):
    super().__init__({"liveDelay": SimpleNamespace(lateralDelay=0.12)})
    self.updated = dict.fromkeys(services, False)
    self.alive = dict.fromkeys(services, True)
    self.valid = dict.fromkeys(services, True)
    self.freq_ok = dict.fromkeys(services, True)
    if "pandaStates" in services:
      self["pandaStates"] = []

  def update(self, timeout):
    pass

  def all_checks(self, services):
    return all(self.alive[s] and self.valid[s] and self.freq_ok[s] for s in services)


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


def car_state(speed=15.0, accel=0.0, curvature=0.0, steering_pressed=False, steering_angle=0.0,
              steering_torque=0.0, left_blinker=False, right_blinker=False, gas_pressed=False, brake_pressed=False,
              cruise_enabled=False):
  return SimpleNamespace(out=SimpleNamespace(
    vEgoRaw=speed,
    aEgo=accel,
    yawRate=-curvature * speed,
    steeringPressed=steering_pressed,
    steeringAngleDeg=steering_angle,
    steeringTorque=steering_torque,
    leftBlinker=left_blinker,
    rightBlinker=right_blinker,
    gasPressed=gas_pressed,
    brakePressed=brake_pressed,
    cruiseState=SimpleNamespace(enabled=cruise_enabled),
  ))


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("speed,weight", ((4.0, 0.0), (5.0, 0.0), (6.0, 0.5), (7.0, 1.0),
                                         (12.0, 1.0), (13.5, 0.5), (15.0, 0.0), (20.0, 0.0)))
def test_mach_e_unwind_preview_speed_and_direction(controller, monkeypatch, sign, speed, weight):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = sign * 0.011
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.004)
  result = controller._unwind_preview(sign * 0.010, sign * 0.009, sign * 0.011, speed)
  assert result == pytest.approx(sign * (0.009 - 0.005 * weight))


@pytest.mark.parametrize("desired,last,current,preview", (
  (0.010, 0.009, 0.011, 0.004),
  (0.010, 0.010, 0.011, 0.004),
  (0.010, 0.011, 0.003, 0.004),
  (0.010, 0.011, 0.004, 0.004),
  (0.010, -0.011, 0.011, 0.004),
  (0.010, 0.011, -0.011, 0.004),
  (0.010, 0.011, 0.011, -0.004),
  (0.010, 0.011, 0.011, 0.009),
  (0.010, 0.011, 0.011, 0.012),
  (0.001, 0.002, 0.003, 0.0005),
))
def test_mach_e_unwind_preserves_other_phases(controller, monkeypatch, desired, last, current, preview):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = last
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: preview)
  assert controller._unwind_preview(desired, 0.009, current, 10.0) == 0.009


@pytest.mark.parametrize("fingerprint", (CAR.FORD_EDGE_MK2, CAR.FORD_EXPLORER_MK6, CAR.FORD_F_150_MK14))
def test_unwind_preview_does_not_change_other_fords(controller, fingerprint):
  controller.CP.carFingerprint = fingerprint
  controller.desired_curvature_last = 0.011
  assert controller._unwind_preview(0.010, 0.009, 0.011, 10.0) == 0.009


def test_mach_e_unwind_lag_ramps_continuously(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = 0.011
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: 0.004)
  assert controller._unwind_preview(0.010, 0.009, 0.005, 10.0) == pytest.approx(0.0065)
  assert controller._unwind_preview(0.010, 0.009, 0.01025, 10.0) == pytest.approx(0.004)
  assert controller._unwind_preview(0.010, -0.009, 0.011, 10.0) == -0.009


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_turn_in_preview_holds_one_repeated_sample(controller, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.desired_curvature_last = sign * 0.003
  assert not controller._turn_in_preview_plateau(sign * 0.004, sign * 0.001, 6.0, False, False)
  controller.desired_curvature_last = sign * 0.004
  assert controller._turn_in_preview_plateau(sign * 0.004, sign * 0.001, 6.0, False, False)
  assert controller._turn_in_preview_weight(sign * 0.004, sign * 0.03, sign * 0.001, True) == 1.0
  assert not controller._turn_in_preview_plateau(sign * 0.004, sign * 0.001, 6.0, False, False)
  assert controller._turn_in_preview_weight(sign * 0.004, sign * 0.03, sign * 0.001) == 0.0


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("current", (0.0036, 0.004, 0.005))
def test_mach_e_turn_in_plateau_requires_tracking_lag(controller, sign, current):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.desired_curvature_last = sign * 0.004
  controller.turn_in_preview_hold_timer = 0.1
  assert not controller._turn_in_preview_plateau(sign * 0.004, sign * current, 6.0, False, False)


@pytest.mark.parametrize("desired", (0.003, -0.004, 0.0))
def test_mach_e_turn_in_plateau_resets_on_unwind_and_reversal(controller, desired):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.desired_curvature_last = 0.004
  controller.turn_in_preview_hold_timer = 0.1
  assert not controller._turn_in_preview_plateau(desired, 0.001, 6.0, False, False)
  assert controller.turn_in_preview_hold_timer == 0.0


@pytest.mark.parametrize("fingerprint,flags,speed,driver,lane_change", (
  (CAR.FORD_EDGE_MK2, FordFlags.CANFD, 6.0, False, False),
  (CAR.FORD_EXPLORER_MK6, FordFlags.CANFD, 6.0, False, False),
  (CAR.FORD_F_150_MK14, FordFlags.CANFD, 6.0, False, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, 0, 6.0, False, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, 1.99, False, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, 15.0, False, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, 6.0, True, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, 6.0, False, True),
))
def test_turn_in_plateau_preserves_other_fords_and_handoffs(controller, fingerprint, flags, speed, driver, lane_change):
  controller.CP.carFingerprint = fingerprint
  controller.CP.flags = flags
  controller.desired_curvature_last = 0.004
  controller.turn_in_preview_hold_timer = 0.1
  assert not controller._turn_in_preview_plateau(0.004, 0.001, speed, driver, lane_change)
  assert controller.turn_in_preview_hold_timer == 0.0


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_repeated_turn_in_sample_preserves_extended_preview(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = sign * 0.003
  controller.curvature_last = sign * 0.012
  monkeypatch.setattr(controller, "_predicted_curvature",
                      lambda _v, t: sign * (0.002 if t < 1.0 else 0.01 if t < 1.5 else 0.03))
  state = car_state(speed=6.0, curvature=sign * 0.001)
  cc = SimpleNamespace(latActive=True, enabled=False)
  actuators = SimpleNamespace(curvature=sign * 0.004)
  first = controller.update(cc, state, actuators)
  repeated = controller.update(cc, state, actuators)
  assert sign * repeated.curvature >= sign * first.curvature
  assert sign * repeated.curvature == pytest.approx(0.0144)
  expired = controller.update(cc, state, actuators)
  assert sign * expired.curvature < sign * repeated.curvature
  assert repeated.path_angle == 0.0
  controller.update(SimpleNamespace(latActive=False), state, actuators)
  assert controller.turn_in_preview_hold_timer == 0.0
  controller.update(cc, state, actuators)
  assert controller.turn_in_preview_hold_timer > 0.0
  controller.update(cc, car_state(speed=0.0), actuators)
  assert controller.turn_in_preview_hold_timer == 0.0


@pytest.mark.parametrize("speed,weight", ((1.99, 0.0), (2.0, 0.0), (2.5, 0.5), (3.0, 1.0),
                                         (14.0, 1.0), (14.5, 0.5), (15.0, 0.0), (16.0, 0.0)))
def test_mach_e_turn_in_plateau_speed_boundaries_are_continuous(controller, speed, weight):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.desired_curvature_last = 0.004
  controller.turn_in_preview_hold_timer = 0.1
  actual_weight = controller._turn_in_preview_plateau(0.004, 0.001, speed, False, False)
  assert actual_weight == pytest.approx(weight)
  assert controller._turn_in_preview_weight(0.004, 0.03, 0.001, actual_weight) == pytest.approx(weight)


@pytest.mark.parametrize("speed,desired,requested,current,driver,lane_change,expected", (
  (12.0, 0.012, 0.012, 0.004, False, False, 0.006),
  (12.0, -0.012, -0.012, 0.004, False, False, 0.006),
  (12.0, 0.012, 0.012, 0.010, False, False, 0.002),
  (12.0, 0.012, 0.012, 0.014, False, False, 0.002),
  (9.5, 0.012, 0.012, 0.004, False, False, 0.006),
  (15.0, 0.012, 0.012, 0.004, False, False, 0.004),
  (16.0, 0.012, 0.012, 0.004, False, False, 0.002),
  (12.0, 0.012, 0.012, 0.004, True, False, 0.002),
  (12.0, 0.012, 0.012, 0.004, False, True, 0.002),
  (12.0, 0.012, -0.004, 0.004, False, False, 0.002),
))
def test_mach_e_understeer_error_scope(controller, speed, desired, requested, current,
                                      driver, lane_change, expected):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  assert controller._curvature_error_limit(
    requested, desired, current, speed, driver, lane_change) == pytest.approx(expected)


def test_understeer_error_preserves_other_fords(controller):
  controller.CP.flags = FordFlags.CANFD
  assert controller._curvature_error_limit(0.012, 0.012, 0.004, 12.0, False, False) == 0.002


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("speed,expected", ((8.0, 0.002), (8.5, 0.004), (9.0, 0.006), (12.0, 0.006),
                                          (14.0, 0.006), (15.0, 0.004), (16.0, 0.002)))
def test_mach_e_unwind_error_tracks_opening_path_before_direction_changes(controller, sign, speed, expected):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.model = SimpleNamespace(orientationRate=SimpleNamespace(z=[0.0] * 33))
  assert controller._curvature_error_limit(
    sign * 0.001, sign * 0.002, sign * 0.005, speed, False, False, sign * 0.001) == pytest.approx(expected)


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("requested,preview,expected", ((0.003, 0.001, 0.002), (0.002, 0.001, 0.004),
                                                       (0.001, 0.001, 0.006), (0.001, 0.004, 0.002),
                                                       (0.001, 0.003, 0.002), (0.001, 0.002, 0.004),
                                                       (0.001, -0.0002, 0.006), (0.001, 0.0, 0.006),
                                                       (0.0, 0.0, 0.006)))
def test_mach_e_unwind_error_requires_measured_lag_and_opening_preview(controller, sign, requested, preview, expected):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.model = SimpleNamespace(orientationRate=SimpleNamespace(z=[0.0] * 33))
  assert controller._curvature_error_limit(
    sign * requested, sign * 0.002, sign * 0.005, 12.0, False, False, sign * preview) == pytest.approx(expected)


@pytest.mark.parametrize("fingerprint,flags,driver,lane_change", (
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, True, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, False, True),
  (CAR.FORD_MUSTANG_MACH_E_MK1, 0, False, False),
  (CAR.FORD_EDGE_MK2, FordFlags.CANFD, False, False),
  (CAR.FORD_EXPLORER_MK6, FordFlags.CANFD, False, False),
  (CAR.FORD_F_150_MK14, FordFlags.CANFD, False, False),
))
def test_unwind_error_preserves_takeover_lane_changes_and_other_fords(controller, fingerprint, flags, driver, lane_change):
  controller.CP.carFingerprint = fingerprint
  controller.CP.flags = flags
  controller.model = SimpleNamespace(orientationRate=SimpleNamespace(z=[0.0] * 33))
  assert controller._curvature_error_limit(0.001, 0.002, 0.005, 12.0, driver, lane_change, 0.001) == 0.002


@pytest.mark.parametrize("model", (None, SimpleNamespace(orientationRate=SimpleNamespace(z=[0.0] * 16))))
def test_mach_e_unwind_error_requires_model_preview(controller, model):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.model = model
  assert controller._curvature_error_limit(0.001, 0.002, 0.005, 12.0, False, False, 0.001) == 0.002


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_curve_exit_releases_without_waiting_for_left_right_reversal(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.model = SimpleNamespace(orientationRate=SimpleNamespace(z=[0.0] * 33),
                                     meta=SimpleNamespace(laneChangeState=0, laneChangeDirection=0))
  controller.curvature_last = sign * 0.004
  controller.desired_curvature_last = sign * 0.003
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.001)
  commands = []
  for _ in range(4):
    result = controller.update(SimpleNamespace(latActive=True), car_state(speed=12.0, curvature=sign * 0.005),
                               SimpleNamespace(curvature=sign * 0.002))
    assert result.active
    assert result.path_angle == 0.0
    commands.append(sign * result.curvature)
  assert commands[0] == pytest.approx(0.004 - 0.0018)
  assert commands[-1] == pytest.approx(0.0016)
  assert commands[-1] < 0.005 - 0.002


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("speed,expected", ((8.0, 0.002), (8.5, 0.004), (9.0, 0.006), (9.5, 0.006), (10.0, 0.006),
                                          (12.0, 0.006), (15.0, 0.004), (16.0, 0.002)))
def test_mach_e_planned_curve_error_uses_preview_request_before_action_builds(controller, sign, speed, expected):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  assert controller._curvature_error_limit(
    sign * 0.006, sign * 0.001, sign * 0.0005, speed, False, False, sign * 0.012) == pytest.approx(expected)


@pytest.mark.parametrize("requested,desired,preview", ((0.006, 0.001, -0.012),
                                                     (0.006, 0.001, 0.0),
                                                     (0.006, -0.001, 0.012),
                                                     (0.0029, 0.001, 0.012)))
def test_mach_e_planned_curve_error_requires_curve_size_and_direction_agreement(controller, requested, desired, preview):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  assert controller._curvature_error_limit(requested, desired, 0.0005, 12.0, False, False, preview) == 0.002


@pytest.mark.parametrize("fingerprint,flags,driver,lane_change", (
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, True, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, False, True),
  (CAR.FORD_MUSTANG_MACH_E_MK1, 0, False, False),
  (CAR.FORD_EDGE_MK2, FordFlags.CANFD, False, False),
  (CAR.FORD_EXPLORER_MK6, FordFlags.CANFD, False, False),
  (CAR.FORD_F_150_MK14, FordFlags.CANFD, False, False),
))
def test_planned_curve_error_preserves_takeover_lane_changes_and_other_fords(controller, fingerprint, flags, driver, lane_change):
  controller.CP.carFingerprint = fingerprint
  controller.CP.flags = flags
  assert controller._curvature_error_limit(0.006, 0.001, 0.0005, 12.0, driver, lane_change, 0.012) == 0.002


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_medium_speed_turn_in_lead_is_not_clipped_by_small_action_curvature(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = sign * 0.0003
  controller.curvature_last = sign * 0.003
  monkeypatch.setattr(controller, "_predicted_curvature",
                      lambda _v, t: sign * (0.0007 if t < 1.0 else 0.0053 if t < 1.5 else 0.011))
  result = controller.update(SimpleNamespace(latActive=True), car_state(speed=11.8, curvature=sign * 0.00027),
                             SimpleNamespace(curvature=sign * 0.0004))
  assert result.active
  assert 0.004 < sign * result.curvature <= 0.00627
  assert result.path_angle == 0.0


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_curve_request_does_not_collapse_when_speed_crosses_curvature_clamp(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.006)
  controller.curvature_last = sign * 0.006
  controller.desired_curvature_last = sign * 0.006
  commands = []
  for speed in (8.9, 9.0, 9.01, 9.2, 9.5, 10.0):
    result = controller.update(SimpleNamespace(latActive=True), car_state(speed=speed),
                               SimpleNamespace(curvature=sign * 0.006))
    assert result.active
    assert result.path_angle == 0.0
    commands.append(result.curvature)
  assert commands == pytest.approx([sign * 0.006] * 6)


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_reversal_request_does_not_collapse_at_curvature_clamp(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: -sign * 0.004)
  monkeypatch.setattr(controller, "_blend_and_scale", lambda *_: (-sign * 0.005, 1))
  controller.curvature_last = -sign * 0.005
  for speed in (8.9, 9.01, 9.5, 10.0):
    result = controller.update(SimpleNamespace(latActive=True), car_state(speed=speed, curvature=sign * 0.001),
                               SimpleNamespace(curvature=sign * 0.002))
    assert result.curvature == pytest.approx(-sign * 0.005)
    assert result.path_angle == 0.0


@pytest.mark.parametrize("fingerprint,flags,driver,lane_change", (
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, True, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, False, True),
  (CAR.FORD_MUSTANG_MACH_E_MK1, 0, False, False),
  (CAR.FORD_EDGE_MK2, FordFlags.CANFD, False, False),
  (CAR.FORD_EXPLORER_MK6, FordFlags.CANFD, False, False),
  (CAR.FORD_F_150_MK14, FordFlags.CANFD, False, False),
))
def test_curve_clamp_transition_preserves_driver_lane_change_and_other_fords(controller, fingerprint, flags, driver, lane_change):
  controller.CP.carFingerprint = fingerprint
  controller.CP.flags = flags
  for speed in (9.01, 9.5):
    assert controller._curvature_error_limit(0.006, 0.006, 0.0, speed, driver, lane_change, 0.006) == 0.002


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("speed,preview,expected", (
  (8.0, -0.004, 0.002),
  (8.5, -0.004, 0.004),
  (9.0, -0.004, 0.006),
  (9.5, -0.004, 0.006),
  (10.0, -0.004, 0.006),
  (12.0, -0.004, 0.006),
  (14.0, -0.004, 0.006),
  (15.0, -0.004, 0.004),
  (16.0, -0.004, 0.002),
  (12.0, -0.0005, 0.002),
  (12.0, -0.00125, 0.004),
  (12.0, 0.004, 0.002),
  (12.0, 0.0, 0.002),
))
def test_mach_e_reversal_error_releases_measured_curvature_clamp(controller, sign, speed, preview, expected):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  assert controller._curvature_error_limit(
    sign * 0.001, sign * 0.002, sign * 0.005, speed, False, False, sign * preview) == pytest.approx(expected)


@pytest.mark.parametrize("fingerprint,flags,driver,lane_change", (
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, True, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, False, True),
  (CAR.FORD_MUSTANG_MACH_E_MK1, 0, False, False),
  (CAR.FORD_EDGE_MK2, FordFlags.CANFD, False, False),
  (CAR.FORD_EXPLORER_MK6, FordFlags.CANFD, False, False),
  (CAR.FORD_F_150_MK14, FordFlags.CANFD, False, False),
))
def test_reversal_error_preserves_takeover_lane_changes_and_other_fords(controller, fingerprint, flags, driver, lane_change):
  controller.CP.carFingerprint = fingerprint
  controller.CP.flags = flags
  assert controller._curvature_error_limit(0.001, 0.002, 0.005, 12.0, driver, lane_change, -0.004) == 0.002


def test_mach_e_reversal_error_does_not_increase_old_direction_command(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  assert controller._curvature_error_limit(0.008, 0.002, 0.005, 12.0, False, False, -0.004) == 0.002


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("preview,expected", ((-0.004, 0.006), (-0.0005, 0.002), (0.004, 0.002)))
def test_mach_e_reversal_error_requires_preview_agreement_after_desired_crosses_zero(
    controller, monkeypatch, sign, preview, expected):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * preview)
  assert controller._curvature_error_limit(
    -sign * 0.00034, -sign * 0.00034, sign * 0.00462, 12.0, False, False, sign * 0.0007) == pytest.approx(expected)


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_reversal_does_not_reapply_old_direction_at_desired_zero_crossing(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = sign * 0.00155
  controller.curvature_last = -sign * 0.00065
  monkeypatch.setattr(controller, "_predicted_curvature",
                      lambda _v, t: sign * 0.0007 if t < 1.0 else -sign * 0.005)
  result = controller.update(SimpleNamespace(latActive=True), car_state(speed=12.0, curvature=sign * 0.00462),
                             SimpleNamespace(curvature=-sign * 0.00034))
  assert result.active
  assert result.curvature == pytest.approx(-sign * 0.00034)
  assert result.path_angle == 0.0


def test_mach_e_path_angle_assist_at_curvature_limit(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  outputs = [controller._path_angle_assist(0.04, 0.04, 0.02, 0.02, 7.5, False, False) for _ in range(3)]
  assert outputs == pytest.approx([0.055, 0.110, 0.150])
  assert controller._path_angle_assist(0.018, 0.018, 0.018, 0.018, 7.5, False, False) == 0.0
  assert controller._path_angle_assist(-0.04, -0.04, -0.02, -0.02, 7.5, False, False) == pytest.approx(-0.055)
  assert controller._path_angle_assist(-0.04, -0.04, -0.02, -0.02, 7.5, True, False) == 0.0


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_path_angle_assist_starts_at_saturation_and_releases_after_driver(controller, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  request = (sign * 0.0205, sign * 0.019, sign * 0.02, sign * 0.007, 7.0)
  assert controller._path_angle_assist(*request, False, False) == pytest.approx(sign * 0.055)
  assert controller._path_angle_assist(*request, True, False) == 0.0
  for _ in range(round(0.75 / STEER_DT) - 1):
    assert controller._path_angle_assist(*request, False, False) == 0.0
  assert controller._path_angle_assist(*request, False, False) == pytest.approx(sign * 0.055)
  assert controller._path_angle_assist(
    sign * 0.0205, sign * 0.019, sign * 0.02, sign * 0.021, 7.0, False, False) == 0.0


@pytest.mark.parametrize("speed,requested,desired,applied,driver,lane_change", (
  (9.0, 0.04, 0.04, 0.02, False, False),
  (7.5, 0.0197, 0.04, 0.02, False, False),
  (7.5, 0.04, 0.007, 0.02, False, False),
  (7.5, 0.04, 0.04, 0.018, False, False),
  (7.5, 0.04, 0.04, 0.02, True, False),
  (7.5, 0.04, 0.04, 0.02, False, True),
))
def test_mach_e_path_angle_assist_is_scoped(controller, speed, requested, desired, applied, driver, lane_change):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  assert controller._path_angle_assist(requested, desired, applied, 0.01, speed, driver, lane_change) == 0.0


def test_path_angle_assist_preserves_other_fords(controller):
  controller.CP.flags = FordFlags.CANFD
  assert controller._path_angle_assist(0.04, 0.04, 0.02, 0.01, 7.5, False, False) == 0.0


def test_mach_e_path_angle_assist_is_encoded_with_curvature(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  assist = controller._path_angle_assist(0.04, 0.04, 0.02, 0.02, 7.5, False, False)
  packer = CANPacker("ford_lincoln_base_pt")
  can_bus = CanBus(SimpleNamespace(flags=FordFlags.CANFD, safetyConfigs=[SimpleNamespace()]))
  _, data, _ = fordcan.create_lat_ctl2_msg(packer, can_bus, 1, 2, 1, -0.02, 0.0, 0, -assist)
  encoded_angle = (((data[3] & 0x1f) << 6) | (data[4] >> 2)) * 0.0005 - 0.5
  assert encoded_angle == pytest.approx(-assist)


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("enabled,gas_pressed,brake_pressed", (
  (False, False, False),
  (False, True, False),
  (True, True, False),
  (True, False, True),
))
def test_mach_e_assist_falls_back_to_curvature_when_not_permitted(
    controller, monkeypatch, sign, enabled, gas_pressed, brake_pressed):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.curvature_last = sign * 0.02
  controller.path_angle_last = sign * 0.16
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.04)
  state = car_state(speed=7.0, curvature=sign * 0.007,
                    gas_pressed=gas_pressed, brake_pressed=brake_pressed)
  actuators = SimpleNamespace(curvature=sign * 0.03)
  CC = SimpleNamespace(latActive=True, enabled=enabled)
  for _ in range(10):
    result = controller.update(CC, state, actuators)
    assert result.active
    assert result.curvature == pytest.approx(sign * 0.02)
    assert result.path_angle == controller.path_angle_last == 0.0

  CC.enabled = True
  state.out.gasPressed = state.out.brakePressed = False
  result = controller.update(CC, state, actuators)
  assert result.curvature == pytest.approx(sign * 0.02)
  assert result.path_angle == pytest.approx(sign * 0.055)


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("blocked", ("disengaged", "cruise", "brake", "denied", "stale", "invalid",
                                   "frequency", "empty", "wrong_model", "second_ford", "missing_sm",
                                   "no_canfd", "no_mach_e", "angle_mode"))
def test_mach_e_accelerator_assist_requires_live_full_permission(controller, monkeypatch, sign, blocked):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.sm = FakeSubMaster(["modelV2", "liveDelay", "pandaStates"])
  panda = SimpleNamespace(safetyModel=structs.CarParams.SafetyModel.ford, controlsAllowed=True,
                         safetyParam=FordSafetyFlags.CANFD | FordSafetyFlags.MACH_E_CURVATURE)
  controller.sm["pandaStates"] = [panda]
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.04)
  controller.curvature_last = sign * 0.02
  state = car_state(speed=7.0, curvature=sign * 0.007, gas_pressed=True, cruise_enabled=True)
  CC = SimpleNamespace(latActive=True, enabled=True)
  actuators = SimpleNamespace(curvature=sign * 0.03)
  result = controller.update(CC, state, actuators)
  assert result.curvature == pytest.approx(sign * 0.02)
  assert result.path_angle == pytest.approx(sign * 0.055)

  if blocked == "disengaged":
    CC.enabled = False
  elif blocked == "cruise":
    state.out.cruiseState.enabled = False
  elif blocked == "brake":
    state.out.brakePressed = True
  elif blocked == "denied":
    panda.controlsAllowed = False
  elif blocked in ("stale", "invalid", "frequency"):
    getattr(controller.sm, {"stale": "alive", "invalid": "valid", "frequency": "freq_ok"}[blocked])["pandaStates"] = False
  elif blocked == "empty":
    controller.sm["pandaStates"] = []
  elif blocked == "wrong_model":
    panda.safetyModel = structs.CarParams.SafetyModel.toyota
  elif blocked == "second_ford":
    controller.sm["pandaStates"].append(SimpleNamespace(
      safetyModel=structs.CarParams.SafetyModel.ford, controlsAllowed=False, safetyParam=panda.safetyParam))
  elif blocked == "missing_sm":
    controller.sm = None
  elif blocked == "no_canfd":
    panda.safetyParam &= ~FordSafetyFlags.CANFD
  elif blocked == "no_mach_e":
    panda.safetyParam &= ~FordSafetyFlags.MACH_E_CURVATURE
  elif blocked == "angle_mode":
    panda.safetyParam |= FordSafetyFlags.LKA_STEERING
  for _ in range(5):
    result = controller.update(CC, state, actuators)
    assert result.active
    assert result.curvature == pytest.approx(sign * 0.02)
    assert result.path_angle == controller.path_angle_last == 0.0


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_accelerator_does_not_interrupt_permitted_assist(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.sm = FakeSubMaster(["modelV2", "liveDelay", "pandaStates"])
  panda = SimpleNamespace(safetyModel=structs.CarParams.SafetyModel.ford, controlsAllowed=True,
                         safetyParam=FordSafetyFlags.CANFD | FordSafetyFlags.MACH_E_CURVATURE)
  controller.sm["pandaStates"] = [SimpleNamespace(safetyModel=structs.CarParams.SafetyModel.silent,
                                                 controlsAllowed=False), panda]
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.04)
  controller.curvature_last = sign * 0.02
  state = car_state(speed=7.0, curvature=sign * 0.007, cruise_enabled=True)
  CC = SimpleNamespace(latActive=True, enabled=True)
  actuators = SimpleNamespace(curvature=sign * 0.03)
  for i in range(10):
    state.out.gasPressed = i % 2 == 0
    result = controller.update(CC, state, actuators)
    assert sign * result.path_angle > 0.0
    assert abs(result.path_angle) <= 0.16
    assert result.curvature == pytest.approx(sign * 0.02)
  panda.controlsAllowed = False
  state.out.gasPressed = True
  assert controller.update(CC, state, actuators).path_angle == 0.0
  panda.controlsAllowed = True
  assert controller.update(CC, state, actuators).path_angle == pytest.approx(sign * 0.055)
  assert controller.update(SimpleNamespace(latActive=False), state, actuators).path_angle == 0.0
  assert controller.path_angle_last == 0.0


@pytest.mark.parametrize("fingerprint,flags,subscribed", (
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, True),
  (CAR.FORD_MUSTANG_MACH_E_MK1, 0, False),
  (CAR.FORD_EDGE_MK2, FordFlags.CANFD, False),
  (CAR.FORD_F_150_MK14, FordFlags.CANFD, False),
))
def test_pedal_assist_permission_subscription_is_mach_e_canfd_only(controller, fingerprint, flags, subscribed):
  instance = FordLateralController(SimpleNamespace(carFingerprint=fingerprint, flags=flags))
  assert ("pandaStates" in instance.sm.updated) is subscribed

@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("speed,expected", ((1.9, False), (2.0, True), (3.0, True), (7.0, True),
                                          (11.0, True), (14.9, True), (15.0, False)))
def test_mach_e_driver_curve_assistance_scope(controller, monkeypatch, sign, speed, expected):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.02)
  state = car_state(speed=speed, curvature=sign * 0.003, steering_pressed=True,
                    steering_torque=-sign * 2.0)
  assert controller._driver_assisting_curve(state, sign * 0.004) is expected


@pytest.mark.parametrize("driver,torque,current,desired,preview,lane_change", (
  (False, -2.0, 0.008, 0.020, 0.025, False),
  (True, 2.0, 0.008, 0.020, 0.025, False),
  (True, -3.6, 0.008, 0.020, 0.025, False),
  (True, -2.0, -0.008, 0.020, 0.025, False),
  (True, -2.0, 0.023, 0.020, 0.025, False),
  (True, -2.0, 0.001, 0.0019, 0.025, False),
  (True, -2.0, 0.008, 0.020, -0.025, False),
  (True, -2.0, 0.008, 0.020, 0.007, False),
  (True, -2.0, 0.008, 0.020, 0.025, True),
))
def test_mach_e_driver_curve_assistance_requires_path_agreement(
    controller, monkeypatch, driver, torque, current, desired, preview, lane_change):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: preview)
  monkeypatch.setattr(controller, "_lane_change", lambda: (lane_change, 0))
  state = car_state(speed=7.0, curvature=current, steering_pressed=driver, steering_torque=torque)
  assert not controller._driver_assisting_curve(state, desired)


@pytest.mark.parametrize("fingerprint,flags", ((CAR.FORD_EDGE_MK2, FordFlags.CANFD),
                                            (CAR.FORD_F_150_MK14, FordFlags.CANFD),
                                            (CAR.FORD_MUSTANG_MACH_E_MK1, 0)))
def test_driver_curve_assistance_preserves_other_fords(controller, monkeypatch, fingerprint, flags):
  controller.CP.carFingerprint = fingerprint
  controller.CP.flags = flags
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: 0.025)
  state = car_state(speed=7.0, curvature=0.008, steering_pressed=True, steering_torque=-2.0)
  assert not controller._driver_assisting_curve(state, 0.020)


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_driver_assistance_handoff_and_takeover(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.curvature_last = sign * 0.020
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.030)
  CC = SimpleNamespace(latActive=True, enabled=True)
  actuators = SimpleNamespace(curvature=sign * 0.022)
  helping = car_state(speed=7.0, curvature=sign * 0.008, steering_pressed=True,
                      steering_angle=-sign * 50.0, steering_torque=-sign * 2.0,
                      left_blinker=sign < 0, right_blinker=sign > 0)
  for _ in range(round(3.5 / STEER_DT)):
    result = controller.update(CC, helping, actuators)
    assert result.active
    assert result.curvature == pytest.approx(sign * 0.020)
    assert sign * result.path_angle > 0.0
    assert not controller.manual_turn_latched

  helping.out.steeringPressed = False
  helping.out.steeringTorque = 0.0
  result = controller.update(CC, helping, actuators)
  assert result.active
  assert sign * result.path_angle > 0.0
  assert controller.path_angle_driver_cooldown == 0.0

  helping.out.steeringPressed = True
  helping.out.steeringTorque = sign * 2.0
  result = controller.update(CC, helping, actuators)
  assert result.path_angle == 0.0
  assert controller.path_angle_driver_cooldown > 0.0

  helping.out.steeringTorque = -sign * 3.6
  result = controller.update(CC, helping, actuators)
  assert not result.active
  assert result.curvature == result.path_angle == 0.0
  assert controller.manual_turn_latched
  helping.out.steeringTorque = -sign * 2.0
  assert not controller.update(CC, helping, actuators).active

  controller.update(SimpleNamespace(latActive=False), helping, actuators)
  helping.out.steeringTorque = -sign * 2.0
  helping.out.yawRate = -sign * 0.025 * helping.out.vEgoRaw
  result = controller.update(CC, helping, actuators)
  assert not result.active
  assert result.curvature == result.path_angle == 0.0
  assert controller.manual_turn_latched

  controller.update(SimpleNamespace(latActive=False), helping, actuators)
  assert not controller.manual_turn_latched
  assert controller.path_angle_driver_cooldown == 0.0


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_driver_help_at_early_curve_entry(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.030)
  state = car_state(speed=2.7, curvature=sign * 0.003, steering_pressed=True,
                    steering_torque=-sign * 2.0, steering_angle=-sign * 15.0,
                    left_blinker=sign < 0, right_blinker=sign > 0)
  CC = SimpleNamespace(latActive=True, enabled=True)
  assert controller.update(CC, state, SimpleNamespace(curvature=sign * 0.004)).active
  state.out.vEgoRaw = 3.5
  state.out.yawRate = -sign * 0.004 * state.out.vEgoRaw
  for _ in range(8):
    result = controller.update(CC, state, SimpleNamespace(curvature=sign * 0.022))
    assert result.active
  assert result.curvature == pytest.approx(sign * 0.020)
  assert sign * result.path_angle > 0.0


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_driver_help_preserves_curvature_error_authority(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.curvature_last = sign * 0.010
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.018)
  state = car_state(speed=11.0, curvature=sign * 0.006, steering_pressed=True,
                    steering_torque=-sign * 2.0, steering_angle=-sign * 20.0)
  result = controller.update(SimpleNamespace(latActive=True), state, SimpleNamespace(curvature=sign * 0.012))
  assert result.active
  assert sign * result.curvature > 0.010
  assert result.path_angle == 0.0


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_unwind_anticipates_opening_curve_before_current_request_is_met(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = sign * 0.012
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.006)
  assert controller._unwind_preview(sign * 0.011, sign * 0.009, sign * 0.008, 11.0) == pytest.approx(sign * 0.006)
  controller.desired_curvature_last = sign * 0.010
  assert controller._unwind_preview(sign * 0.011, sign * 0.009, sign * 0.008, 11.0) == sign * 0.009


def test_mach_e_unwind_preserves_existing_release_when_current_exceeds_desired(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = 0.009
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: 0.0079)
  assert controller._unwind_preview(0.008, 0.008, 0.0085, 10.0) == pytest.approx(0.0079)


@pytest.mark.parametrize("driver,lane_change,active", ((False, False, True), (True, False, True),
                                                    (False, True, True), (False, False, False)))
def test_mach_e_unwind_update_scope_and_rate(controller, monkeypatch, driver, lane_change, active):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.desired_curvature_last = 0.011
  controller.curvature_last = 0.010
  controller.curvature_samples.append(0.010)
  monkeypatch.setattr(controller, "_lane_change", lambda: (lane_change, 0))
  monkeypatch.setattr(controller, "_predicted_curvature", lambda v, t: 0.010 if t < 0.5 else 0.004)
  result = controller.update(SimpleNamespace(latActive=active),
                             car_state(speed=10.0, curvature=0.011, steering_pressed=driver),
                             SimpleNamespace(curvature=0.010))
  assert result.curvature_rate == 0.0
  if not active:
    assert not result.active
    assert controller.desired_curvature_last == 0.0
  else:
    assert result.curvature == pytest.approx(0.010 if driver or lane_change else 0.009)


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


@pytest.mark.parametrize("requested_rate", (-0.002, -0.001024, -0.001023, -0.0005, 0.0, 0.0005, 0.001023, 0.002))
def test_mach_e_canfd_curvature_rate_survives_wire_sign_conversion(controller, monkeypatch, requested_rate):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  speed = 8.0
  predicted = -0.012
  controller.curvature_last = predicted
  controller.desired_curvature_last = predicted
  controller.curvature_samples.append(predicted - requested_rate * STEER_DT * speed)
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_args: predicted)

  result = controller.update(
    SimpleNamespace(latActive=True), car_state(speed=speed, curvature=predicted),
    SimpleNamespace(curvature=predicted))
  expected = max(-0.001023, min(0.001023, requested_rate))
  assert result.curvature == pytest.approx(predicted)
  assert result.curvature_rate == pytest.approx(expected)

  packer = CANPacker("ford_lincoln_base_pt")
  can_bus = CanBus(SimpleNamespace(flags=FordFlags.CANFD, safetyConfigs=[SimpleNamespace()]))
  _, data, _ = fordcan.create_lat_ctl2_msg(
    packer, can_bus, 1, result.ramp_type, result.precision_type,
    -result.curvature, -result.curvature_rate, 0)
  decoded_rate = ((data[6] << 3) | (data[7] >> 5)) * 1e-6 - 0.001024
  assert -decoded_rate == pytest.approx(expected, abs=0.5e-6)


@pytest.mark.parametrize("fingerprint,flags", (
  (CAR.FORD_MUSTANG_MACH_E_MK1, 0),
  (CAR.FORD_EXPLORER_MK6, FordFlags.CANFD),
  (CAR.FORD_EDGE_MK2, 0),
))
def test_mach_e_canfd_rate_bound_preserves_other_paths(controller, monkeypatch, fingerprint, flags):
  controller.CP.carFingerprint = fingerprint
  controller.CP.flags = flags
  controller.desired_curvature_last = -0.012
  controller.curvature_samples.append(0.0)
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_args: -0.012)

  result = controller.update(
    SimpleNamespace(latActive=True), car_state(speed=8.0), SimpleNamespace(curvature=-0.012))

  assert result.curvature_rate == pytest.approx(-0.001024)


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


@pytest.mark.parametrize("speed,expected", ((0.0, 0.0), (15.0, 0.0), (16.0, 0.0), (19.5, 0.2),
                                         (23.0, 0.4), (30.0, 0.4), (40.0, 0.4)))
def test_mach_e_high_speed_preview_ramps_continuously(controller, speed, expected):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  assert controller._high_speed_lookahead_extra(speed, False, False) == pytest.approx(expected)


@pytest.mark.parametrize("fingerprint,flags,driver,lane_change", (
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, True, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, False, True),
  (CAR.FORD_MUSTANG_MACH_E_MK1, 0, False, False),
  (CAR.FORD_EXPLORER_MK6, FordFlags.CANFD, False, False),
  (CAR.FORD_F_150_MK14, FordFlags.CANFD, False, False),
  (CAR.FORD_EDGE_MK2, 0, False, False),
))
def test_high_speed_preview_preserves_takeover_lane_changes_and_other_fords(controller, fingerprint, flags, driver, lane_change):
  controller.CP.carFingerprint = fingerprint
  controller.CP.flags = flags
  assert controller._high_speed_lookahead_extra(30.0, driver, lane_change) == 0.0


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("speed", (16.0, 19.5, 23.0, 30.0))
def test_mach_e_high_speed_preview_preserves_constant_curve_authority(controller, monkeypatch, sign, speed):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  curvature = sign * 0.001
  controller.curvature_last = curvature
  controller.desired_curvature_last = curvature
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: curvature)
  result = controller.update(SimpleNamespace(latActive=True), car_state(speed=speed, curvature=curvature),
                             SimpleNamespace(curvature=curvature))
  assert result.curvature == pytest.approx(curvature)
  assert result.curvature_rate == 0.0
  assert result.path_angle == 0.0


@pytest.mark.parametrize("driver,lane_change", ((False, False), (True, False), (False, True)))
def test_mach_e_high_speed_preview_update_uses_bounded_horizon(controller, monkeypatch, driver, lane_change):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.sm["liveDelay"].lateralDelay = 0.38
  monkeypatch.setattr(controller, "_lane_change", lambda: (lane_change, 0))
  lookaheads = []
  monkeypatch.setattr(controller, "_predicted_curvature", lambda v, t: lookaheads.append(t) or 0.0)
  controller.update(SimpleNamespace(latActive=True), car_state(speed=30.0, steering_pressed=driver),
                    SimpleNamespace(curvature=0.0001))
  assert lookaheads[0] == pytest.approx(0.38 if driver or lane_change else 0.78)
  assert controller._curvature_lookahead() == pytest.approx(0.38)


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("conflicting_rate", (False, True))
@pytest.mark.parametrize("fingerprint,flags,driver,lane_change", (
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, False, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, True, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, False, True),
  (CAR.FORD_MUSTANG_MACH_E_MK1, 0, False, False),
  (CAR.FORD_EXPLORER_MK6, FordFlags.CANFD, False, False),
  (CAR.FORD_EDGE_MK2, 0, False, False),
))
def test_mach_e_unwind_rate_does_not_fight_selected_release(controller, monkeypatch, sign, conflicting_rate,
                                                          fingerprint, flags, driver, lane_change):
  controller.CP.carFingerprint = fingerprint
  controller.CP.flags = flags
  controller.desired_curvature_last = sign * 0.013
  controller.curvature_last = sign * 0.012
  predicted = sign * 0.011
  rate = sign * 0.0002 * (1 if conflicting_rate else -1)
  controller.curvature_samples.append(predicted - rate * STEER_DT * 8.0)
  monkeypatch.setattr(controller, "_predicted_curvature", lambda v, t: predicted if t < 0.5 else sign * 0.006)
  monkeypatch.setattr(controller, "_lane_change", lambda: (lane_change, 0))
  result = controller.update(SimpleNamespace(latActive=True),
                             car_state(speed=8.0, curvature=sign * 0.012, steering_pressed=driver),
                             SimpleNamespace(curvature=sign * 0.012))
  suppress = fingerprint == CAR.FORD_MUSTANG_MACH_E_MK1 and flags & FordFlags.CANFD and not driver and not lane_change
  assert result.curvature_rate == pytest.approx(0.0 if lane_change or suppress and conflicting_rate else rate)
  assert result.path_angle == 0.0


def test_mach_e_preview_does_not_override_opposite_current_path(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1

  requested, _ = controller._blend_and_scale(-0.0001, 0.002, 20.0)

  assert requested == pytest.approx(-0.0001)


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("last,desired,current,preview,rate,suppress", (
  (0.011, 0.012, 0.004, 0.014, -0.001023, True),
  (0.012, 0.012, 0.004, 0.014, -0.001023, True),
  (0.011, 0.012, -0.004, 0.014, -0.001023, True),
  (0.013, 0.012, 0.004, 0.014, -0.001023, False),
  (-0.011, 0.012, 0.004, 0.014, -0.001023, False),
  (0.011, 0.012, 0.011, 0.014, -0.001023, False),
  (0.011, 0.012, 0.004, 0.005, -0.001023, False),
  (0.011, 0.012, 0.004, 0.010, -0.001023, False),
  (0.011, 0.012, 0.004, -0.014, -0.001023, False),
  (0.011, 0.012, 0.004, 0.000, -0.001023, False),
  (0.011, 0.012, 0.004, 0.014, 0.001023, False),
  (0.011, 0.012, 0.004, 0.014, 0.000000, False),
))
def test_mach_e_turn_in_rate_preserves_entry_and_opening_phases(controller, monkeypatch, sign,
                                                             last, desired, current, preview, rate, suppress):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.desired_curvature_last = sign * last
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * preview)
  result = controller._turn_in_curvature_rate(sign * desired, sign * current, sign * rate, 8.0, 0.4, False, False)
  assert result == pytest.approx(0.0 if suppress else sign * rate)


@pytest.mark.parametrize("fingerprint,flags,driver,lane_change", (
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, True, False),
  (CAR.FORD_MUSTANG_MACH_E_MK1, FordFlags.CANFD, False, True),
  (CAR.FORD_MUSTANG_MACH_E_MK1, 0, False, False),
  (CAR.FORD_EXPLORER_MK6, FordFlags.CANFD, False, False),
  (CAR.FORD_EDGE_MK2, 0, False, False),
))
@pytest.mark.parametrize("sign", (-1, 1))
def test_turn_in_rate_preserves_driver_lane_change_and_other_fords(controller, monkeypatch, sign,
                                                                fingerprint, flags, driver, lane_change):
  controller.CP.carFingerprint = fingerprint
  controller.CP.flags = flags
  controller.desired_curvature_last = sign * 0.011
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.014)
  rate = -sign * 0.001023
  assert controller._turn_in_curvature_rate(sign * 0.012, sign * 0.004, rate, 8.0, 0.4, driver, lane_change) == rate


@pytest.mark.parametrize("speed,suppress", ((0.3, False), (2.9, False), (3.0, True), (14.9, True), (15.0, False), (25.0, False)))
@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_turn_in_rate_does_not_use_near_zero_speed_yaw_or_change_highway_behavior(controller, monkeypatch,
                                                                                     sign, speed, suppress):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.desired_curvature_last = sign * 0.011
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.014)
  rate = -sign * 0.001023
  result = controller._turn_in_curvature_rate(sign * 0.012, sign * 0.004, rate, speed, 0.4, False, False)
  assert result == pytest.approx(0.0 if suppress else rate)


@pytest.mark.parametrize("sign", (-1, 1))
def test_mach_e_turn_in_rate_update_uses_previous_desired_and_preserves_unwind(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.desired_curvature_last = sign * 0.011
  controller.curvature_last = sign * 0.012
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.014)
  rate = -sign * 0.0002
  for desired in (0.012, 0.012, 0.011):
    controller.curvature_samples.clear()
    controller.curvature_samples.append(sign * 0.014 - rate * STEER_DT * 8.0)
    result = controller.update(SimpleNamespace(latActive=True), car_state(speed=8.0, curvature=sign * 0.004),
                               SimpleNamespace(curvature=sign * desired))
    assert result.curvature_rate == pytest.approx(rate if desired == 0.011 else 0.0)
    assert controller.desired_curvature_last == sign * desired
    assert result.active and result.path_angle == 0.0


def test_mach_e_preview_is_reduced_when_ahead_of_current_path(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1

  requested, _ = controller._blend_and_scale(0.0005, 0.002, 20.0, current=0.0015)

  assert requested == pytest.approx(0.00065)


def test_mach_e_preview_remains_available_on_curve_entry(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1

  requested, _ = controller._blend_and_scale(0.0005, 0.002, 20.0, current=0.0002)

  assert requested == pytest.approx(0.0011)


def test_mach_e_turn_in_preview_leads_when_path_lags(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = 0.004

  weight = controller._turn_in_preview_weight(
    desired=0.005, preview=0.005, current=0.002)

  assert weight == pytest.approx(0.25)


def test_mach_e_turn_in_preview_leads_opposite_measured_curvature(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = 0.001

  weight = controller._turn_in_preview_weight(
    desired=0.003, preview=0.009, current=-0.003)

  assert weight == pytest.approx(1.0)


def test_mach_e_turn_in_preview_is_not_carried_into_unwind(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = 0.010

  assert controller._turn_in_preview_weight(
    desired=0.008, preview=0.009, current=0.004) == 0.0


@pytest.mark.parametrize("speed,expected", (
  (1.0, 0.80),
  (2.0, 0.80),
  (2.5, 1.20),
  (3.0, 1.60),
  (8.0, 1.60),
  (9.0, 1.60),
  (10.5, 1.60),
  (11.0, 1.60),
  (12.0, 1.60),
  (13.0, 4.0 / 3.0),
  (14.0, 16.0 / 15.0),
  (15.0, 0.80),
  (16.0, 0.80),
))
def test_mach_e_turn_in_lookahead_extra_fades_by_speed(controller, speed, expected):
  assert controller._turn_in_lookahead_extra(speed) == pytest.approx(expected)


@pytest.mark.parametrize("speed,expected", (
  (8.0, 0.80),
  (9.0, 0.80),
  (9.5, 1.60),
  (10.0, 2.40),
  (12.0, 2.40),
  (13.5, 1.60),
  (15.0, 0.80),
  (16.0, 0.80),
))
def test_mach_e_direction_change_lookahead_extra_fades_by_speed(controller, speed, expected):
  assert controller._direction_change_lookahead_extra(speed) == pytest.approx(expected)


@pytest.mark.parametrize("speed,desired,expected", (
  (1.8, 0.0010, 0.0),
  (1.9, 0.0010, 0.5),
  (2.0, 0.0010, 1.0),
  (2.8, 0.0010, 1.0),
  (3.15, 0.0010, 0.5),
  (3.5, 0.0010, 0.0),
  (2.5, 0.0004, 0.0),
  (2.5, 0.0005, 0.5),
  (2.5, 0.0006, 1.0),
))
def test_mach_e_low_speed_direction_change_weight(controller, speed, desired, expected):
  assert controller._low_speed_direction_change_weight(speed, desired) == pytest.approx(expected)


@pytest.mark.parametrize("speed,accel,desired,preview,expected", (
  (1.5, 2.4, 0.0006, -0.012, 0.0),
  (1.8, 1.8, 0.0006, -0.012, 0.0),
  (1.8, 2.0, 0.0006, -0.012, 0.5),
  (1.8, 2.2, 0.0002, -0.012, 0.0),
  (1.8, 2.2, 0.00035, -0.012, 0.5),
  (1.8, 2.2, 0.0006, -0.010, 0.5),
  (3.5, 2.2, 0.0006, -0.012, 0.5),
  (4.0, 2.2, 0.0006, -0.012, 0.0),
))
def test_mach_e_sharp_direction_change_weight(controller, speed, accel, desired, preview, expected):
  assert controller._sharp_direction_change_weight(speed, accel, desired, preview) == pytest.approx(expected)


@pytest.mark.parametrize("sign", (1.0, -1.0))
def test_mach_e_direction_change_preview_leads_a_lagging_unwind(controller, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = sign * 0.002

  weight = controller._direction_change_preview_weight(
    desired=sign * 0.0015, preview=-sign * 0.002, current=sign * 0.003)

  assert weight == pytest.approx(1.0)


def test_mach_e_low_speed_direction_change_preview_can_lead_a_rising_near_path(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = 0.0006

  assert controller._direction_change_preview_weight(
    desired=0.0008, preview=-0.002, current=0.003, allow_rising_desired=True) == pytest.approx(1.0)
  assert controller._direction_change_preview_weight(
    desired=0.0008, preview=-0.002, current=0.003) == 0.0


def test_mach_e_low_speed_direction_change_preview_rejects_large_rising_near_path(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = 0.0014

  assert controller._direction_change_preview_weight(
    desired=0.0016, preview=-0.002, current=0.003, allow_rising_desired=True) == 0.0


def test_mach_e_extended_direction_preview_begins_before_measured_curvature_catches_desired(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = 0.0148

  assert controller._direction_change_preview_weight(
    desired=0.0147, preview=-0.002, current=0.0140, early_handoff_weight=1.0) == pytest.approx(1.0 / 6.0)
  assert controller._direction_change_preview_weight(
    desired=0.0147, preview=-0.002, current=0.0140) == 0.0


def test_mach_e_extended_direction_preview_tolerates_small_desired_jitter(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = 0.0146

  assert controller._direction_change_preview_weight(
    desired=0.0147, preview=-0.002, current=0.0141, early_handoff_weight=1.0) == pytest.approx(2.0 / 9.0)
  assert controller._direction_change_preview_weight(
    desired=0.0147, preview=-0.002, current=0.0141) == 0.0


def test_mach_e_extended_direction_preview_preserves_turn_in_when_vehicle_lags(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = 0.0146

  assert controller._direction_change_preview_weight(
    desired=0.0147, preview=-0.002, current=0.0130, early_handoff_weight=1.0) == 0.0


@pytest.mark.parametrize("desired,preview,current,last", (
  (0.0015, 0.002, 0.003, 0.002),     # no predicted direction change
  (0.002, -0.002, 0.003, 0.0015),    # desired curvature is still rising
  (0.0015, -0.002, -0.001, 0.002),   # vehicle already changed direction
  (0.0015, -0.002, 0.0022, 0.002),   # measured unwind lag is too small
))
def test_mach_e_direction_change_preview_rejects_unrelated_states(
    controller, desired, preview, current, last):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = last

  assert controller._direction_change_preview_weight(desired, preview, current) == 0.0


def test_mach_e_direction_change_preview_can_cross_the_current_desired_path(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1

  requested, _ = controller._blend_and_scale(
    0.0015, -0.002, 15.0, current=0.003, allow_opposite_preview=True)

  assert requested == pytest.approx(0.0001)


def test_mach_e_direction_change_preview_uses_far_path_when_unwind_lags(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.002
  blend_inputs = []
  monkeypatch.setattr(
    controller, "_predicted_curvature",
    lambda _v_ego, lookahead: 0.002 if lookahead < 1.0 else -0.002,
  )
  monkeypatch.setattr(
    controller, "_blend_and_scale",
    lambda desired, predicted, v_ego, current, allow_opposite_preview=False:
      blend_inputs.append((desired, predicted, v_ego, current, allow_opposite_preview)) or (0.0, 1),
  )

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=15.0, curvature=0.003),
    SimpleNamespace(curvature=0.0015),
  )

  assert blend_inputs == [(pytest.approx(0.0015), pytest.approx(-0.002), pytest.approx(15.0),
                           pytest.approx(0.003), True)]


def test_mach_e_direction_change_preview_leads_low_speed_handoff(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.002
  blend_inputs = []
  monkeypatch.setattr(
    controller, "_predicted_curvature",
    lambda _v_ego, lookahead: 0.002 if lookahead < 1.0 else -0.002,
  )
  monkeypatch.setattr(
    controller, "_blend_and_scale",
    lambda desired, predicted, v_ego, current, allow_opposite_preview=False:
      blend_inputs.append((desired, predicted, v_ego, current, allow_opposite_preview)) or (0.0, 1),
  )

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=2.5, curvature=0.003),
    SimpleNamespace(curvature=0.0015),
  )

  assert blend_inputs == [(pytest.approx(0.0015), pytest.approx(-0.002), pytest.approx(2.5),
                           pytest.approx(0.003), True)]


def test_mach_e_direction_change_preview_leads_rising_low_speed_handoff(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.0006
  blend_inputs = []
  monkeypatch.setattr(
    controller, "_predicted_curvature",
    lambda _v_ego, lookahead: 0.0008 if lookahead < 1.0 else -0.002,
  )
  monkeypatch.setattr(
    controller, "_blend_and_scale",
    lambda desired, predicted, v_ego, current, allow_opposite_preview=False:
      blend_inputs.append((desired, predicted, v_ego, current, allow_opposite_preview)) or (0.0, 1),
  )

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=2.5, curvature=0.003),
    SimpleNamespace(curvature=0.0008),
  )

  assert blend_inputs == [(pytest.approx(0.0008), pytest.approx(-0.002), pytest.approx(2.5),
                           pytest.approx(0.003), True)]


def test_mach_e_sharp_accelerating_direction_change_leads_below_existing_speed_gate(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.0010
  blend_inputs = []

  def predicted_curvature(_v_ego, lookahead):
    return {0.4: 0.0005, 1.2: -0.0106}[round(lookahead, 1)]

  monkeypatch.setattr(controller, "_predicted_curvature", predicted_curvature)
  monkeypatch.setattr(
    controller, "_blend_and_scale",
    lambda desired, predicted, v_ego, current, allow_opposite_preview=False:
      blend_inputs.append((desired, predicted, v_ego, current, allow_opposite_preview)) or (0.0, 1),
  )

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=1.85, accel=2.4, curvature=0.00075),
    SimpleNamespace(curvature=0.000426),
  )

  assert len(blend_inputs) == 1
  assert blend_inputs[0][0] == pytest.approx(0.000426)
  assert blend_inputs[0][1] < 0.0
  assert blend_inputs[0][2:] == (pytest.approx(1.85), pytest.approx(0.00075), True)


def test_mach_e_sharp_direction_change_requires_hard_acceleration(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.0010
  blend_inputs = []

  def predicted_curvature(_v_ego, lookahead):
    return {0.4: 0.0005, 1.2: -0.0106}[round(lookahead, 1)]

  monkeypatch.setattr(controller, "_predicted_curvature", predicted_curvature)
  monkeypatch.setattr(
    controller, "_blend_and_scale",
    lambda desired, predicted, v_ego, current, allow_opposite_preview=False:
      blend_inputs.append((desired, predicted, v_ego, current, allow_opposite_preview)) or (0.0, 1),
  )

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=1.85, accel=1.5, curvature=0.00075),
    SimpleNamespace(curvature=0.000426),
  )

  assert blend_inputs == [(pytest.approx(0.000426), pytest.approx(0.0005), pytest.approx(1.85),
                           pytest.approx(0.00075), False)]


def test_mach_e_direction_change_preview_does_not_lead_rising_high_speed_path(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.0006
  blend_inputs = []
  monkeypatch.setattr(controller, "_predicted_curvature", lambda _v_ego, _lookahead: -0.002)
  monkeypatch.setattr(
    controller, "_blend_and_scale",
    lambda desired, predicted, v_ego, current, allow_opposite_preview=False:
      blend_inputs.append((desired, predicted, v_ego, current, allow_opposite_preview)) or (0.0, 1),
  )

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=15.0, curvature=0.003),
    SimpleNamespace(curvature=0.0008),
  )

  assert blend_inputs == [(pytest.approx(0.0008), pytest.approx(-0.002), pytest.approx(15.0),
                           pytest.approx(0.003), False)]


def test_mach_e_direction_change_preview_uses_extended_horizon_at_medium_speed(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.002
  lookaheads = []
  blend_inputs = []

  def predicted_curvature(_v_ego, lookahead):
    lookaheads.append(lookahead)
    return {0.4: 0.002, 1.2: 0.001, 2.8: -0.002}[round(lookahead, 1)]

  monkeypatch.setattr(controller, "_predicted_curvature", predicted_curvature)
  monkeypatch.setattr(
    controller, "_blend_and_scale",
    lambda desired, predicted, v_ego, current, allow_opposite_preview=False:
      blend_inputs.append((desired, predicted, v_ego, current, allow_opposite_preview)) or (0.0, 1),
  )

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=10.5, curvature=0.003),
    SimpleNamespace(curvature=0.0015),
  )

  assert lookaheads == [pytest.approx(0.4), pytest.approx(1.2), pytest.approx(2.8)]
  assert blend_inputs == [(pytest.approx(0.0015), pytest.approx(-0.002), pytest.approx(10.5),
                           pytest.approx(0.003), True)]


def test_mach_e_extended_direction_preview_advances_large_curve_exit(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.0146
  blend_inputs = []

  def predicted_curvature(_v_ego, lookahead):
    return {0.4: 0.0144, 1.2: 0.011, 2.8: -0.002}[round(lookahead, 1)]

  monkeypatch.setattr(controller, "_predicted_curvature", predicted_curvature)
  monkeypatch.setattr(
    controller, "_blend_and_scale",
    lambda desired, predicted, v_ego, current, allow_opposite_preview=False:
      blend_inputs.append((desired, predicted, v_ego, current, allow_opposite_preview)) or (0.0, 1),
  )

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=12.0, curvature=0.0141),
    SimpleNamespace(curvature=0.0147),
  )

  assert len(blend_inputs) == 1
  assert blend_inputs[0][0] == pytest.approx(0.0147)
  assert blend_inputs[0][1] < 0.0144
  assert blend_inputs[0][4]


def test_mach_e_extended_direction_preview_preserves_small_medium_speed_path(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.0007
  blend_inputs = []

  def predicted_curvature(_v_ego, lookahead):
    return 0.0008 if lookahead < 2.0 else -0.002

  monkeypatch.setattr(controller, "_predicted_curvature", predicted_curvature)
  monkeypatch.setattr(
    controller, "_blend_and_scale",
    lambda desired, predicted, v_ego, current, allow_opposite_preview=False:
      blend_inputs.append((desired, predicted, v_ego, current, allow_opposite_preview)) or (0.0, 1),
  )

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=12.0, curvature=0.0014),
    SimpleNamespace(curvature=0.0008),
  )

  assert blend_inputs == [(pytest.approx(0.0008), pytest.approx(0.0008), pytest.approx(12.0),
                           pytest.approx(0.0014), False)]


def test_mach_e_extended_direction_horizon_does_not_replace_turn_in_preview(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.007
  blend_inputs = []

  def predicted_curvature(_v_ego, lookahead):
    return {0.4: 0.006, 1.2: 0.010, 2.0: 0.004, 2.8: -0.002}[round(lookahead, 1)]

  monkeypatch.setattr(controller, "_predicted_curvature", predicted_curvature)
  monkeypatch.setattr(
    controller, "_blend_and_scale",
    lambda desired, predicted, v_ego, current, allow_opposite_preview=False:
      blend_inputs.append((desired, predicted, allow_opposite_preview)) or (0.0, 1),
  )

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=10.5, curvature=0.002),
    SimpleNamespace(curvature=0.008),
  )

  assert blend_inputs == [(pytest.approx(0.008), pytest.approx(0.010), False)]


@pytest.mark.parametrize("speed,steering_pressed,lane_change", (
  (1.8, False, False),
  (3.5, False, False),
  (8.0, False, False),
  (9.0, False, False),
  (2.5, True, False),
  (2.5, False, True),
  (15.0, True, False),
  (15.0, False, True),
))
def test_mach_e_direction_change_preview_is_bypassed_outside_its_operating_state(
    controller, monkeypatch, speed, steering_pressed, lane_change):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = 0.002
  monkeypatch.setattr(controller, "_predicted_curvature", lambda _v_ego, lookahead: -0.002)
  monkeypatch.setattr(controller, "_lane_change", lambda: (lane_change, 2 if lane_change else 0))
  monkeypatch.setattr(
    controller, "_direction_change_preview_weight",
    lambda *_args: pytest.fail("direction-change preview must be bypassed"),
  )

  controller.update(
    SimpleNamespace(latActive=True),
    car_state(speed=speed, curvature=0.003, steering_pressed=steering_pressed),
    SimpleNamespace(curvature=0.0015),
  )


def test_non_mach_e_direction_change_preview_is_unchanged(controller):
  controller.desired_curvature_last = 0.002

  assert controller._direction_change_preview_weight(
    desired=0.0015, preview=-0.002, current=0.003) == 0.0


def test_non_mach_e_bypasses_low_speed_direction_change_preview(controller, monkeypatch):
  controller.desired_curvature_last = 0.002
  lookaheads = []
  monkeypatch.setattr(
    controller, "_predicted_curvature",
    lambda _v_ego, lookahead: lookaheads.append(lookahead) or -0.002,
  )
  monkeypatch.setattr(
    controller, "_low_speed_direction_change_weight",
    lambda *_args: pytest.fail("low-speed direction-change preview must remain Mach-E-only"),
  )

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=2.5, curvature=0.003),
    SimpleNamespace(curvature=0.0015),
  )

  assert lookaheads == [pytest.approx(0.2)]


def test_mach_e_turn_in_preview_uses_extra_model_horizon(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.007
  lookaheads = []
  monkeypatch.setattr(controller, "_predicted_curvature",
                      lambda _v_ego, lookahead: lookaheads.append(lookahead) or 0.012)

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=8.0, curvature=0.002),
    SimpleNamespace(curvature=0.010),
  )

  assert lookaheads == [pytest.approx(0.4), pytest.approx(1.2), pytest.approx(2.0)]


def test_mach_e_turn_in_preview_keeps_existing_horizon_above_fade_speed(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.007
  lookaheads = []
  monkeypatch.setattr(controller, "_predicted_curvature",
                      lambda _v_ego, lookahead: lookaheads.append(lookahead) or 0.012)

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=15.0, curvature=0.002),
    SimpleNamespace(curvature=0.010),
  )

  assert lookaheads == [pytest.approx(0.4), pytest.approx(1.2)]


def test_mach_e_low_speed_turn_in_preview_cannot_weaken_existing_preview(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.sm["liveDelay"].lateralDelay = 0.4
  controller.desired_curvature_last = 0.007
  blend_inputs = []

  def predicted_curvature(_v_ego, lookahead):
    return {0.4: 0.006, 1.2: 0.010, 2.0: 0.004}[round(lookahead, 1)]

  monkeypatch.setattr(controller, "_predicted_curvature", predicted_curvature)
  monkeypatch.setattr(
    controller, "_blend_and_scale",
    lambda desired, predicted, v_ego, current, allow_opposite_preview=False:
      blend_inputs.append((desired, predicted)) or (0.0, 1),
  )

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=8.0, curvature=0.002),
    SimpleNamespace(curvature=0.008),
  )

  assert blend_inputs == [(pytest.approx(0.008), pytest.approx(0.010))]


def test_non_mach_e_does_not_request_extra_model_horizon(controller, monkeypatch):
  controller.sm["liveDelay"].lateralDelay = 0.4
  lookaheads = []
  monkeypatch.setattr(controller, "_predicted_curvature",
                      lambda _v_ego, lookahead: lookaheads.append(lookahead) or 0.007)

  controller.update(
    SimpleNamespace(latActive=True), car_state(speed=8.0, curvature=0.002),
    SimpleNamespace(curvature=0.010),
  )

  assert lookaheads == [pytest.approx(0.4)]


def test_non_mach_e_turn_in_preview_is_unchanged(controller):
  controller.desired_curvature_last = 0.007

  assert controller._turn_in_preview_weight(
    desired=0.010, preview=0.007, current=0.004) == 0.0


def test_non_mach_e_preview_blend_is_unchanged(controller):
  requested, _ = controller._blend_and_scale(-0.0001, 0.002, 20.0, current=0.0015)

  assert requested == pytest.approx(0.00074)


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


def test_mach_e_signaled_manual_turn_yields_until_inputs_settle(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.human_turn_enabled = True
  CC = SimpleNamespace(latActive=True)
  actuators = SimpleNamespace(curvature=0.006)

  result = controller.update(CC, car_state(
    steering_pressed=True, steering_angle=-15.0, steering_torque=-2.0,
    right_blinker=True), actuators)
  assert not result.active
  assert result.curvature == 0.0

  result = controller.update(CC, car_state(
    steering_pressed=True, steering_angle=5.0, steering_torque=2.0,
    right_blinker=True), actuators)
  assert not result.active

  for _ in range(4):
    result = controller.update(CC, car_state(), actuators)
    assert not result.active

  result = controller.update(CC, car_state(curvature=0.006), actuators)
  assert result.active
  assert result.curvature > 0.0


def test_mach_e_manual_turn_waits_for_wheel_to_unwind(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  CC = SimpleNamespace(latActive=True)
  actuators = SimpleNamespace(curvature=0.006)

  assert not controller.update(CC, car_state(
    steering_pressed=True, steering_angle=-30.0, steering_torque=-2.0,
    right_blinker=True), actuators).active

  for _ in range(8):
    result = controller.update(CC, car_state(steering_angle=-35.0), actuators)
    assert not result.active

  for _ in range(4):
    result = controller.update(CC, car_state(steering_angle=-10.0), actuators)
    assert not result.active
  result = controller.update(CC, car_state(curvature=0.006, steering_angle=-10.0), actuators)
  assert result.active


def test_mach_e_left_manual_turn_waits_for_wheel_to_unwind(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  CC = SimpleNamespace(latActive=True)
  actuators = SimpleNamespace(curvature=-0.006)

  assert not controller.update(CC, car_state(
    steering_pressed=True, steering_angle=30.0, steering_torque=2.0,
    left_blinker=True), actuators).active

  for _ in range(8):
    result = controller.update(CC, car_state(steering_angle=35.0), actuators)
    assert not result.active

  for _ in range(4):
    result = controller.update(CC, car_state(steering_angle=10.0), actuators)
    assert not result.active
  result = controller.update(CC, car_state(curvature=-0.006, steering_angle=10.0), actuators)
  assert result.active


@pytest.mark.parametrize("sign", (-1.0, 1.0))
def test_mach_e_manual_turn_waits_for_path_agreement_after_driver_release(controller, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  CC = SimpleNamespace(latActive=True, actuators=SimpleNamespace(curvature=sign * 0.009))
  turning = car_state(steering_pressed=True, steering_angle=-sign * 30.0,
                      steering_torque=-sign * 2.0, left_blinker=sign < 0.0,
                      right_blinker=sign > 0.0)
  assert not controller.update(CC, turning, CC.actuators).active
  for _ in range(40):
    result = controller.update(CC, car_state(curvature=sign * 0.001,
                                              steering_angle=-sign * 5.0), CC.actuators)
    assert not result.active
    assert result.curvature == 0.0
  assert controller.manual_turn_direction == sign

  result = controller.update(CC, car_state(curvature=sign * 0.008,
                                            steering_angle=-sign * 5.0), CC.actuators)
  assert result.active
  assert controller.manual_turn_direction == 0.0


def test_mach_e_manual_turn_releases_for_opposite_path_request(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  CC = SimpleNamespace(latActive=True, actuators=SimpleNamespace(curvature=-0.009))
  assert not controller.update(CC, car_state(steering_pressed=True, steering_angle=30.0,
                                              steering_torque=2.0, left_blinker=True), CC.actuators).active
  CC.actuators.curvature = 0.009
  for _ in range(4):
    assert not controller.update(CC, car_state(curvature=-0.001), CC.actuators).active
  assert controller.update(CC, car_state(curvature=-0.001), CC.actuators).active


@pytest.mark.parametrize("sign", (-1.0, 1.0))
@pytest.mark.parametrize("speed", (9.0, 9.5, 14.99))
def test_mach_e_manual_turn_hands_off_to_driver_assisted_opposite_curve(controller, monkeypatch, sign, speed):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  CC = SimpleNamespace(latActive=True, enabled=True)
  actuators = SimpleNamespace(curvature=sign * 0.006)
  turning = car_state(speed=speed, curvature=sign * 0.004, steering_pressed=True,
                      steering_angle=-sign * 30.0, steering_torque=-sign * 2.0,
                      left_blinker=sign < 0.0, right_blinker=sign > 0.0)
  assert not controller.update(CC, turning, actuators).active
  assert controller.manual_turn_direction == sign
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: -sign * 0.010)
  actuators.curvature = -sign * 0.006
  following = car_state(speed=speed, curvature=-sign * 0.004, steering_pressed=True,
                        steering_angle=sign * 20.0, steering_torque=sign * 2.0)
  for _ in range(4):
    assert not controller.update(CC, following, actuators).active
  result = controller.update(CC, following, actuators)
  assert result.active
  assert -sign * result.curvature > 0.0
  assert abs(result.curvature) <= 0.0025
  assert result.path_angle == 0.0
  assert not controller.manual_turn_latched
  assert controller.manual_turn_direction == 0.0
  assert controller.manual_turn_recovery_timer == 0.0


@pytest.mark.parametrize("sign", (-1.0, 1.0))
@pytest.mark.parametrize("speed,current,torque,preview,left,right,lane_change", (
  (4.5, -0.004, 2.0, -0.010, False, False, False),
  (8.99, -0.004, 2.0, -0.010, False, False, False),
  (15.0, -0.004, 2.0, -0.010, False, False, False),
  (9.5, 0.004, 2.0, -0.010, False, False, False),
  (9.5, -0.009, 2.0, -0.010, False, False, False),
  (9.5, -0.004, -2.0, -0.010, False, False, False),
  (9.5, -0.004, 3.6, -0.010, False, False, False),
  (9.5, -0.004, 2.0, 0.010, False, False, False),
  (9.5, -0.004, 2.0, -0.007, False, False, False),
  (9.5, -0.004, 2.0, -0.010, True, False, False),
  (9.5, -0.004, 2.0, -0.010, False, True, False),
  (9.5, -0.004, 2.0, -0.010, True, True, False),
  (9.5, -0.004, 2.0, -0.010, False, False, True),
))
def test_mach_e_opposite_curve_handoff_preserves_manual_override(
    controller, monkeypatch, sign, speed, current, torque, preview, left, right, lane_change):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.manual_turn_latched = True
  controller.manual_turn_direction = sign
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * preview)
  monkeypatch.setattr(controller, "_lane_change", lambda: (lane_change, 0))
  state = car_state(speed=speed, curvature=sign * current, steering_pressed=True,
                    steering_angle=sign * 25.0, steering_torque=sign * torque,
                    left_blinker=left, right_blinker=right)
  for _ in range(8):
    result = controller.update(SimpleNamespace(latActive=True, enabled=True), state,
                               SimpleNamespace(curvature=-sign * 0.006))
    assert not result.active
    assert result.curvature == result.path_angle == 0.0
    assert controller.manual_turn_recovery_timer == 0.0


def test_mach_e_opposite_curve_handoff_requires_uninterrupted_agreement(controller, monkeypatch):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.manual_turn_latched = True
  controller.manual_turn_direction = 1.0
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: -0.010)
  CC = SimpleNamespace(latActive=True, enabled=True)
  actuators = SimpleNamespace(curvature=-0.006)
  state = car_state(speed=9.5, curvature=-0.004, steering_pressed=True,
                    steering_angle=20.0, steering_torque=2.0)
  for _ in range(4):
    assert not controller.update(CC, state, actuators).active
  state.out.steeringTorque = -2.0
  assert not controller.update(CC, state, actuators).active
  assert controller.manual_turn_recovery_timer == 0.0
  state.out.steeringTorque = 2.0
  for _ in range(4):
    assert not controller.update(CC, state, actuators).active
  assert controller.update(CC, state, actuators).active


def test_non_mach_e_signaled_turn_does_not_latch(controller):
  CC = SimpleNamespace(latActive=True)
  result = controller.update(CC, car_state(
    steering_pressed=True, steering_angle=30.0, steering_torque=2.0,
    left_blinker=True), SimpleNamespace(curvature=-0.006))

  assert result.active


def test_mach_e_opposite_blinker_correction_does_not_start_manual_turn(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1

  result = controller.update(
    SimpleNamespace(latActive=True),
    car_state(steering_pressed=True, steering_angle=-15.0, steering_torque=2.0,
              right_blinker=True),
    SimpleNamespace(curvature=0.001),
  )

  assert result.active


def test_mach_e_lane_change_nudge_does_not_start_manual_turn(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.model = SimpleNamespace(
    orientationRate=SimpleNamespace(z=[0.0] * 33),
    meta=SimpleNamespace(
      laneChangeState=SimpleNamespace(raw=2),
      laneChangeDirection=SimpleNamespace(raw=2),
    ),
  )

  result = controller.update(
    SimpleNamespace(latActive=True),
    car_state(steering_pressed=True, steering_angle=-15.0, steering_torque=-2.0,
              right_blinker=True),
    SimpleNamespace(curvature=0.001),
  )

  assert result.active


def test_mach_e_small_blinker_nudge_does_not_start_manual_turn(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1

  result = controller.update(
    SimpleNamespace(latActive=True),
    car_state(steering_pressed=True, steering_angle=-5.0, steering_torque=-2.0,
              right_blinker=True),
    SimpleNamespace(curvature=0.001),
  )

  assert result.active


def test_mach_e_manual_turn_latch_resets_with_lateral_control(controller):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  actuators = SimpleNamespace(curvature=0.001)
  turning = car_state(
    steering_pressed=True, steering_angle=-15.0, steering_torque=-2.0,
    right_blinker=True)

  assert not controller.update(SimpleNamespace(latActive=True), turning, actuators).active
  assert controller.manual_turn_direction == 1.0
  assert not controller.update(SimpleNamespace(latActive=False), turning, actuators).active
  assert controller.manual_turn_direction == 0.0
  assert controller.update(SimpleNamespace(latActive=True), car_state(), actuators).active
