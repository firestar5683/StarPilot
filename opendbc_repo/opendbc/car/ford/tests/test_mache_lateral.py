"""Original-derived Mach-E demand and driver handoff regressions."""
from types import SimpleNamespace
import pytest
from opendbc.car import Bus, structs
from opendbc.car.lateral import MAX_LATERAL_JERK
from opendbc.can import CANParser
from opendbc.car.ford.values import CAR, DBC, FordFlags, FordSafetyFlags
from opendbc.car.ford.mache_lateral import MachELateralController, FordLateralResult, bounded_command, STEER_DT, MAX_LATERAL_ACCEL, qualified
from opendbc.car.ford import mache_can as fordcan
from opendbc.car.ford.tests.test_three_ports import params
from opendbc.car.ford.carcontroller import CarController
from opendbc.car.ford.carstate import CarState


@pytest.fixture
def controller():
  owner = MachELateralController(SimpleNamespace(flags=FordFlags.CANFD, carFingerprint=CAR.FORD_MUSTANG_MACH_E_MK1))
  model = SimpleNamespace(orientationRate=SimpleNamespace(z=[0.]*33),
                          meta=SimpleNamespace(laneChangeState=0, laneChangeDirection=0))
  owner.set_inputs(model, tuple(i*.1 for i in range(33)), .2, True)
  return owner


def car_state(speed=15.0, accel=0.0, curvature=0.0, steering_pressed=False, steering_angle=0.0,
              steering_torque=0.0, left_blinker=False, right_blinker=False, gas_pressed=False, brake_pressed=False,
              cruise_enabled=False):
  return SimpleNamespace(out=SimpleNamespace(vEgoRaw=speed, aEgo=accel, yawRate=-curvature*speed,
    steeringPressed=steering_pressed, steeringAngleDeg=steering_angle, steeringTorque=steering_torque,
    leftBlinker=left_blinker, rightBlinker=right_blinker, gasPressed=gas_pressed, brakePressed=brake_pressed,
    cruiseState=SimpleNamespace(enabled=cruise_enabled)))


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("speed,weight", ((4.0, 0.0), (5.0, 0.0), (6.0, 0.5), (7.0, 1.0),
                                         (12.0, 1.0), (13.5, 0.5), (15.0, 0.0), (20.0, 0.0)))
def test_mach_e_unwind_preview_speed_and_direction(controller, monkeypatch, sign, speed, weight):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.desired_curvature_last = sign * 0.011
  monkeypatch.setattr(controller, "_predicted_curvature", lambda *_: sign * 0.004)
  result = controller._unwind_preview(sign * 0.010, sign * 0.009, sign * 0.011, speed)
  assert result == pytest.approx(sign * (0.009 - 0.005 * weight))

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
  controller.set_inputs(controller.model, controller.time_indices, .4, True)
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
def test_mach_e_reversal_does_not_reapply_old_direction_at_desired_zero_crossing(controller, monkeypatch, sign):
  controller.CP.carFingerprint = CAR.FORD_MUSTANG_MACH_E_MK1
  controller.CP.flags = FordFlags.CANFD
  controller.set_inputs(controller.model, controller.time_indices, 0.4, True)
  controller.desired_curvature_last = sign * 0.00155
  controller.curvature_last = -sign * 0.00065
  monkeypatch.setattr(controller, "_predicted_curvature",
                      lambda _v, t: sign * 0.0007 if t < 1.0 else -sign * 0.005)
  result = controller.update(SimpleNamespace(latActive=True), car_state(speed=12.0, curvature=sign * 0.00462),
                             SimpleNamespace(curvature=-sign * 0.00034))
  assert result.active
  assert result.curvature == pytest.approx(-sign * 0.00034)
  assert result.path_angle == 0.0

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


def test_exact_profile_rejects_collision_and_siblings():
  cp = params(CAR.FORD_MUSTANG_MACH_E_MK1)
  for word in (18, 19):
    cp.openpilotLongitudinalControl = word == 19
    cp.safetyConfigs[0].safetyParam = word
    assert qualified(cp)
  for word in (2, 3, 10, 11, 22, 26, 34):
    cp.safetyConfigs[0].safetyParam = word
    assert not qualified(cp)
  cp.safetyConfigs[0].safetyParam = 19
  cp.passive = True
  assert not qualified(cp)
  neighbor = params(CAR.FORD_F_150_MK14)
  neighbor.safetyConfigs[0].safetyParam = 18
  assert not qualified(neighbor)


def test_actual_controller_announces_before_full_physical_frame_and_resets_off():
  cp = params(CAR.FORD_MUSTANG_MACH_E_MK1)
  cp.openpilotLongitudinalControl = False
  cp.safetyConfigs[0].safetyParam = 18
  cc = CarController(DBC[cp.carFingerprint], cp)
  cs = CarState(cp)
  cs.update(cs.get_can_parsers(cp))
  cs.out = structs.CarState(vEgoRaw=7.).as_reader()
  command = structs.CarControl(latActive=True)
  command.actuators.curvature = .008
  model = SimpleNamespace(orientationRate=SimpleNamespace(z=[.07]*33),
                          meta=SimpleNamespace(laneChangeState=0, laneChangeDirection=0))
  times = tuple(i*.1 for i in range(33))
  cc.manual_turn_inputs = SimpleNamespace(update=lambda: None, apply_blend_settings=lambda owner: None, enabled=True,
                                        lateral_snapshot=lambda speed: (model, times, .2, True))
  _, frames = cc.update(command.as_reader(), cs, 0)
  first = next(data for addr, data, _ in frames if addr == 0x3d6)
  assert (first[0] >> 4) & 7 == 0
  announcement = next(data for addr, data, _ in frames if addr == 0x3ca)
  assert announcement[4] & 2
  cc.frame = 5
  actual, frames = cc.update(command.as_reader(), cs, 50_000_000)
  frame = next(data for addr, data, _ in frames if addr == 0x3d6)
  assert (frame[0] >> 4) & 7 == 1
  assert frame[1] == fordcan.calculate_lat_ctl2_checksum(1, 1, frame)
  parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [('LateralMotionControl2', 20)], cc.CAN.main)
  parser.update([(50_000_000, frames)])
  assert parser.vl['LateralMotionControl2']['LatCtlCurv_No_Actl'] == pytest.approx(-actual.curvature, abs=1.01e-5)
  command.latActive = False
  cc.frame = 10
  actual, frames = cc.update(command.as_reader(), cs, 100_000_000)
  assert actual.curvature == 0
  assert cc.mache_lateral.path_angle_last == 0
  assert cc.mache_lateral.desired_curvature_last == 0


def test_modern_transient_bound_updates_emitted_history_without_hidden_windup():
  owner = MachELateralController(SimpleNamespace(flags=FordFlags.CANFD, carFingerprint=CAR.FORD_MUSTANG_MACH_E_MK1))
  raw = FordLateralResult(curvature=.006, path_angle=.16, active=True)
  command = bounded_command(owner, raw, .001, 15.)
  assert command.curvature < raw.curvature
  assert abs(command.curvature-.001) <= MAX_LATERAL_JERK / 15.**2 * STEER_DT + 1e-12
  assert command.path_angle == 0.
  assert owner.curvature_last == command.curvature
  assert owner.path_angle_last == command.path_angle
  assert raw.curvature == .006 and raw.path_angle == .16
  slow = bounded_command(owner, FordLateralResult(curvature=.02, active=True), .02, 15.)
  assert not slow.active and slow.curvature == slow.path_angle == slow.curvature_rate == 0.
  assert owner.curvature_last == 0.


@pytest.mark.parametrize("sign", (-1, 1))
def test_speed_changes_intersect_bounds_or_withdraw_and_preserve_path_headroom(sign):
  owner = MachELateralController(SimpleNamespace(flags=FordFlags.CANFD, carFingerprint=CAR.FORD_MUSTANG_MACH_E_MK1))
  previous, path = sign * .0198, sign * .055
  for speed in (5., 5.1, 5.2, 5.3, 8., 15., 5.):
    demand = FordLateralResult(curvature=sign*.02, path_angle=sign*.16, active=True)
    emitted = bounded_command(owner, demand, previous, speed, path)
    if emitted.active:
      assert abs(emitted.curvature-previous) <= MAX_LATERAL_JERK / speed**2 * STEER_DT + 1e-12
      assert abs(emitted.curvature) <= MAX_LATERAL_ACCEL / speed**2 + 1e-12
      if emitted.path_angle:
        assert abs(emitted.path_angle-path) <= .055+1e-12
        assert (abs(emitted.curvature)+abs(emitted.path_angle)/speed)*speed**2 <= MAX_LATERAL_ACCEL+1e-12
    else:
      assert emitted.curvature == emitted.path_angle == emitted.curvature_rate == 0.
    previous, path = emitted.curvature, emitted.path_angle


def test_final_typed_cp_binds_real_provider_and_freshness():
  import tempfile
  from unittest.mock import patch
  import openpilot.cereal.messaging as messaging
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.starpilot.controller_extensions import configure_controller, ManualTurnInputs
  from openpilot.selfdrive.modeld.constants import ModelConstants
  from opendbc.car.ford.interface import CarInterface
  cp = params(CAR.FORD_MUSTANG_MACH_E_MK1)
  assert cp.safetyConfigs[0].safetyParam == (19 if cp.openpilotLongitudinalControl else 18)
  ci = CarInterface(cp)
  with OpenpilotPrefix(), tempfile.TemporaryDirectory() as directory:
    preferences = Params(directory)
    preferences.put_bool('FordHumanTurnDetection', True, block=True)
    configure_controller(ci, preferences)
    provider = ci.CC.manual_turn_inputs
    assert isinstance(provider, ManualTurnInputs)
    try:
      event = messaging.new_message('modelV2')
      event.valid = True
      event.logMonoTime = 1_000_000_000
      event.modelV2.orientationRate.z = [.07] * len(ModelConstants.T_IDXS)
      event.modelV2.meta.laneChangeState = 0
      event.modelV2.meta.laneChangeDirection = 0
      provider.sm.update_msgs(1., [event.as_reader()])
      with patch('openpilot.starpilot.controller_extensions.time.monotonic_ns', return_value=1_000_000_000):
        sample = provider.lateral_snapshot(7.)
        assert sample is not None
        assert sample[0].orientationRate.z[0] == pytest.approx(.07)
      with patch('openpilot.starpilot.controller_extensions.time.monotonic_ns', return_value=1_200_000_000):
        assert provider.lateral_snapshot(7.) is None
    finally:
      ci.CC.manual_turn_inputs = None
      del provider


def test_real_offset_cp_keeps_owner_and_invalid_extended_cp_never_falls_back_active():
  from opendbc.car import gen_empty_fingerprint
  from opendbc.car.ford.interface import CarInterface
  fingerprint = gen_empty_fingerprint()
  fingerprint[4][0x5a] = 8
  fingerprint[6][0x3d6] = 8
  fingerprint[6][0x186] = 8
  cp = CarInterface.get_params(CAR.FORD_MUSTANG_MACH_E_MK1, fingerprint, [], False, False, False)
  assert len(cp.safetyConfigs) == 2
  assert cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.noOutput
  assert cp.safetyConfigs[-1].safetyParam == 18
  assert qualified(cp)
  controller = CarController(DBC[cp.carFingerprint], cp)
  assert controller.mache_lateral is not None and controller.CAN.main == 4
  cp.passive = True
  controller = CarController(DBC[cp.carFingerprint], cp)
  assert controller.mache_lateral is None
  state = CarState(cp)
  state.update(state.get_can_parsers(cp))
  state.out = structs.CarState(vEgoRaw=10.).as_reader()
  command = structs.CarControl(latActive=True)
  command.actuators.curvature = .008
  actual, frames = controller.update(command.as_reader(), state, 0)
  frame = next(data for addr, data, _ in frames if addr == 0x3d6)
  assert frame[0] >> 4 & 7 == 0
  assert actual.curvature == 0


@pytest.mark.parametrize("sign", (-1, 1))
def test_real_controller_gas_permission_loss_withdraws_path_only(sign):
  cp = params(CAR.FORD_MUSTANG_MACH_E_MK1)
  owner = CarController(DBC[cp.carFingerprint], cp)
  state = CarState(cp)
  state.update(state.get_can_parsers(cp))
  control = structs.CarControl(latActive=True, enabled=True)
  control.actuators.curvature = sign * .03
  states, healthy = [SimpleNamespace(safetyModel=structs.CarParams.SafetyModel.ford, controlsAllowed=True,
                                    safetyParam=FordSafetyFlags.CANFD | FordSafetyFlags.MACH_E_EXTENDED)], True
  model = SimpleNamespace(orientationRate=SimpleNamespace(z=[sign * .28] * 33),
                          meta=SimpleNamespace(laneChangeState=0, laneChangeDirection=0))
  owner.manual_turn_inputs = SimpleNamespace(update=lambda: None, apply_blend_settings=lambda _: None, enabled=True,
    lateral_snapshot=lambda _: (model, tuple(i*.1 for i in range(33)), .2, True),
    assist_permission=lambda: (states, healthy))
  parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [('LateralMotionControl2', 20)], owner.CAN.main)
  out = structs.CarState(vEgoRaw=7., yawRate=-sign * .049)
  out.cruiseState.enabled = True
  state.out = out.as_reader()
  # First production frame announces the extension; subsequent commands run the actual demand and envelope.
  owner.update(control.as_reader(), state, 0)
  assert owner.mache_lateral is not None
  owner.mache_lateral.curvature_last = sign * .02
  for tick, (gas, allowed, valid, enabled, brake, cruise) in enumerate((
    (False, True, True, True, False, True), (True, True, True, True, False, True),
    (False, True, True, True, False, True), (True, False, True, True, False, True),
    (True, True, True, True, False, True), (True, True, False, True, False, True),
    (True, True, True, True, False, False),
    (False, True, True, False, False, True), (False, True, True, True, True, True),
  ), 1):
    out.gasPressed, out.brakePressed = gas, brake
    out.cruiseState.enabled = cruise
    state.out = out.as_reader()
    control.enabled = enabled
    states[0].controlsAllowed, healthy = allowed, valid
    owner.frame = tick * 5
    _, frames = owner.update(control.as_reader(), state, tick * 50_000_000)
    parser.update([(tick * 50_000_000, frames)])
    fields = parser.vl['LateralMotionControl2']
    permitted = enabled and not brake and (not gas or (cruise and allowed and valid))
    assert fields['LatCtl_D2_Rq'] == 1
    assert fields['LatCtlCurv_No_Actl'] == pytest.approx(-sign * .02, abs=1.01e-5)
    assert (fields['LatCtlPath_An_Actl'] != 0.) == permitted
    assert (owner.mache_lateral.path_angle_last != 0.) == permitted
  owner.manual_turn_inputs = None
  out.gasPressed, out.brakePressed, control.enabled = True, False, True
  state.out = out.as_reader()
  owner.frame = 50
  owner.update(control.as_reader(), state, 500_000_000)
  assert not owner.mache_lateral.assist_engagement_retained
  assert owner.mache_lateral.path_angle_last == 0.


@pytest.mark.parametrize("sign", (-1, 1))
def test_real_controller_recovers_opposite_curve_after_continuous_agreement(sign):
  cp = params(CAR.FORD_MUSTANG_MACH_E_MK1)
  owner = CarController(DBC[cp.carFingerprint], cp)
  state = CarState(cp)
  state.update(state.get_can_parsers(cp))
  control = structs.CarControl(latActive=True, enabled=True)
  control.actuators.curvature = sign * .006
  model = SimpleNamespace(orientationRate=SimpleNamespace(z=[0.] * 33),
                          meta=SimpleNamespace(laneChangeState=0, laneChangeDirection=0))
  owner.manual_turn_inputs = SimpleNamespace(update=lambda: None, apply_blend_settings=lambda _: None, enabled=True,
    lateral_snapshot=lambda _: (model, tuple(i*.1 for i in range(33)), .2, True))
  out = structs.CarState(vEgoRaw=9.5, yawRate=-sign * .038, steeringPressed=True,
                         steeringAngleDeg=-sign * 30., steeringTorque=-sign * 2.,
                         leftBlinker=sign < 0, rightBlinker=sign > 0)
  state.out = out.as_reader()
  owner.update(control.as_reader(), state, 0)
  owner.frame = 5
  owner.update(control.as_reader(), state, 50_000_000)
  assert owner.mache_lateral.manual_turn_latched
  out.yawRate, out.steeringAngleDeg, out.steeringTorque = sign * .038, sign * 20., sign * 2.
  out.leftBlinker = out.rightBlinker = False
  state.out = out.as_reader()
  control.actuators.curvature = -sign * .006
  model.orientationRate.z = [-sign * .095] * 33
  # An opposing driver torque after four agreeing frames must restart the full dwell.
  for tick, (torque, recovered) in enumerate([(2., False)] * 4 + [(-2., False)] + [(2., False)] * 4 + [(2., True)], 1):
    out.steeringTorque = sign * torque
    state.out = out.as_reader()
    owner.frame = (tick + 1) * 5
    actual, frames = owner.update(control.as_reader(), state, (tick + 1) * 50_000_000)
    active = next(data for address, data, _ in frames if address == 0x3d6)[0] >> 4 & 7
    assert bool(active) == recovered
    assert owner.mache_lateral.path_angle_last == 0.
    if recovered:
      assert -sign * actual.curvature > 0.
      assert not owner.mache_lateral.manual_turn_latched
