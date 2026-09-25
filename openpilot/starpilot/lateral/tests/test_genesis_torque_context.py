"""Actual Genesis controller proof for exact mapped Dom leaves."""

from collections import deque
from types import SimpleNamespace
import math
import pytest
from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR
from opendbc.car.vehicle_model import VehicleModel
from openpilot.cereal import log
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.starpilot.lateral.controller_selection import ControllerMode
from openpilot.starpilot.lateral import genesis_gv70_policy as gv70
from openpilot.starpilot.lateral import genesis_g70_policy as g70


@pytest.mark.parametrize('direction', [-1.0, 1.0])
def test_gv70_actual_undertracking_curve_matches_undamped_policy(monkeypatch, direction):
  cp = interfaces[CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN].get_non_essential_params(CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN)

  def run():
    controller = LatControlTorque(cp.as_reader(), interfaces[cp.carFingerprint](cp), 0.01, controller_mode=ControllerMode.STARPILOT)
    vm = VehicleModel(cp)
    cs = SimpleNamespace(vEgo=30.0, steeringAngleDeg=math.degrees(vm.get_steer_from_curvature(-direction * 0.6 / 900.0, 30.0, 0.0)), steeringPressed=False)
    params = log.VehicleParameters.new_message(angleOffsetDeg=0.0, roll=0.0)
    request = direction * 0.8 / 900.0
    policy = controller.starpilot_extension.policy
    policy.curvature_request_buffer = deque([request] * policy.request_buffer_len, maxlen=policy.request_buffer_len)
    rows = []
    for _ in range(100):
      out, _, state = controller.update(True, cs, vm, params, False, request, False, 0.2)
      assert math.isfinite(out) and abs(out) <= controller.steer_max + 1e-6
      rows.append((out, state.desiredLateralAccel, state.p, state.i, state.d, state.f))
    return rows, controller.torque_params.to_dict(), (controller.pid.pos_limit, controller.pid.neg_limit)

  actual = run()
  for name in ('get_genesis_gv70_unwind_ff_scale', 'get_genesis_gv70_high_speed_error_scale', 'get_genesis_gv70_reversal_output_scale'):
    monkeypatch.setattr(gv70, name, lambda *_: 1.0)
  assert actual == run()


@pytest.mark.parametrize('direction', [-1.0, 1.0])
@pytest.mark.parametrize('pressed', [False, True])
def test_g70_actual_friction_receives_traffic_increment_only_without_driver_override(monkeypatch, direction, pressed):
  cp = interfaces[CAR.GENESIS_G70_2020].get_non_essential_params(CAR.GENESIS_G70_2020)
  actual = LatControlTorque(cp.as_reader(), interfaces[cp.carFingerprint](cp), 0.01, controller_mode=ControllerMode.STARPILOT)
  actual.update_torque_parameters(3.0, 0.02, 0.12)
  tune = actual.torque_params.to_dict()
  limits = (actual.pid.pos_limit, actual.pid.neg_limit, actual.steer_max)
  cs = SimpleNamespace(vEgo=5.0, steeringAngleDeg=0.0, steeringPressed=pressed)
  params = log.VehicleParameters.new_message(angleOffsetDeg=0.0, roll=0.0)
  vm = VehicleModel(cp)
  calls = []
  original = g70.get_friction

  def capture(error, deadzone, threshold, tune):
    calls.append(threshold)
    return original(error, deadzone, threshold, tune)

  monkeypatch.setattr(g70, 'get_friction', capture)
  for _ in range(100):
    out, _, state = actual.update(True, cs, vm, params, False, direction * 0.0001, False, 0.2)
    assert math.isfinite(out) and abs(out) <= actual.steer_max + 1e-6
  base = g70.get_genesis_g70_friction_threshold(cs.vEgo, state.desiredLateralAccel, state.desiredLateralJerk)
  inc = (
    0.0 if pressed else g70.get_genesis_g70_traffic_friction_increment(cs.vEgo, state.desiredLateralAccel, state.desiredLateralJerk, direction * 0.0001, 0.0)
  )
  assert calls[-1] == pytest.approx(base + inc)
  assert (inc == 0.0) is pressed
  assert actual.torque_params.to_dict() == tune
  assert (actual.pid.pos_limit, actual.pid.neg_limit, actual.steer_max) == limits
  calls.clear()
  out, _, state = actual.update(False, cs, vm, params, False, direction * 0.0001, False, 0.2)
  assert out == 0.0 and not state.active and calls == []
