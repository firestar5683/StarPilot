"""Compare runtime output against frozen default original StarPilot traces."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from openpilot.cereal import log
from opendbc.car import structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR
from opendbc.car.vehicle_model import VehicleModel
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.starpilot.lateral.torque_extension import selected_policy
from openpilot.starpilot.lateral.genesis_g70_policy import supported_cp
from openpilot.starpilot.lateral import genesis_g70_policy

FIXTURE = Path(__file__).with_name('fixtures') / 'genesis_g70_ba901b5f.json'


def controller_for(car=CAR.GENESIS_G70_2020):
  cp = interfaces[car].get_non_essential_params(car)
  return cp, LatControlTorque(cp.as_reader(), interfaces[car](cp), 0.01), VehicleModel(cp)


@pytest.mark.parametrize('case_index', range(5))
def test_frozen_original_numeric_traces(case_index):
  fixture = json.loads(FIXTURE.read_text())
  cp, controller, vm = controller_for()
  assert selected_policy(controller) is not None
  params = log.VehicleParameters.new_message(angleOffsetDeg=0.3, roll=0.006)
  for index, frame in enumerate(fixture['cases'][case_index]['frames']):
    active, speed, angle, pressed, limited, curve, curve_limited, delay = frame['input']
    cs = SimpleNamespace(vEgo=speed, steeringAngleDeg=angle, steeringPressed=pressed)
    torque, desired_angle, state = controller.update(active, cs, vm, params, limited, curve, curve_limited, delay)
    assert desired_angle == 0.0
    assert torque == pytest.approx(frame['torque'], abs=1e-12, rel=0), (case_index, index)
    assert [getattr(state, field) for field in fixture['log_fields']] == pytest.approx(frame['log'], abs=1e-12, rel=0)
    assert state.active == frame['active']
    assert state.saturated == frame['saturated']
    assert abs(torque) <= 1.0
    if not active:
      assert torque == 0.0
      assert controller.pid.i == 0.0
      assert selected_policy(controller).prev_output_torque == 0.0


def test_exact_vehicle_admission_and_upstream_gains():
  cp, controller, _ = controller_for()
  assert supported_cp(cp)
  assert controller.pid._k_i[1] == [0.35]
  for field, value in [('brand', 'toyota'), ('dashcamOnly', True), ('passive', True), ('steerControlType', structs.CarParams.SteerControlType.angle)]:
    changed = cp.as_reader().as_builder()
    setattr(changed, field, value)
    assert not supported_cp(changed)
    native = LatControlTorque(changed.as_reader(), interfaces[CAR.GENESIS_G70_2020](changed), 0.01)
    assert selected_policy(native) is None
    assert native.pid._k_i[1] == [0.15]
  other_cp, other, _ = controller_for(CAR.GENESIS_G70)
  assert not supported_cp(other_cp)
  assert selected_policy(other) is None
  assert other.pid._k_i[1] == [0.15]
  non_torque = cp.as_reader().as_builder()
  non_torque.lateralTuning.init('pid')
  assert not supported_cp(non_torque)


def test_live_source_updates_keep_raw_calibration_and_limits():
  cp, controller, _ = controller_for()
  original = cp.lateralTuning.torque.latAccelFactor
  assert controller.torque_params.latAccelFactor == original
  for _ in range(3):
    controller.update_torque_parameters(original * 1.1, 0.025, 0.08)
    assert controller.torque_params.latAccelFactor == pytest.approx(original * 1.1)
    assert controller.torque_params.latAccelOffset == pytest.approx(0.025)
    assert controller.torque_params.friction == pytest.approx(0.08)
    assert controller.pid.pos_limit == controller.lateral_accel_from_torque(1.0, controller.torque_params)
    assert controller.pid.neg_limit == controller.lateral_accel_from_torque(-1.0, controller.torque_params)


def test_driver_override_and_inactive_state_reset():
  _, controller, vm = controller_for()
  params = log.VehicleParameters.new_message(angleOffsetDeg=0.3, roll=0.006)
  cs = SimpleNamespace(vEgo=4.0, steeringAngleDeg=20.3, steeringPressed=False)
  with patch.object(genesis_g70_policy, 'get_genesis_g70_low_speed_angle_damping',
                    wraps=genesis_g70_policy.get_genesis_g70_low_speed_angle_damping) as damping, \
       patch.object(genesis_g70_policy, 'get_genesis_g70_stabilized_output',
                    wraps=genesis_g70_policy.get_genesis_g70_stabilized_output) as smoothing, \
       patch.object(controller.pid, 'update', wraps=controller.pid.update) as pid_update:
    controller.update(True, cs, vm, params, False, .002, False, .2)
    damping.assert_called_once()
    smoothing.assert_called_once()
    cs.steeringPressed = True
    controller.update(True, cs, vm, params, False, .002, False, .2)
    assert damping.call_count == 1
    assert smoothing.call_count == 1
    assert pid_update.call_args.kwargs['freeze_integrator'] is True
    cs.steeringPressed = False
    controller.update(True, cs, vm, params, True, .002, False, .2)
    assert pid_update.call_args.kwargs['freeze_integrator'] is True
  torque, _, state = controller.update(False, cs, vm, params, False, .002, False, .2)
  policy = selected_policy(controller)
  assert torque == 0.0 and not state.active and controller.pid.i == 0.0
  assert policy.prev_output_torque == 0.0
  assert policy.jerk_filter.x == 0.0
  assert policy.measurement_rate_filter.x == 0.0
  assert policy.curvature_request_buffer[-1] == .002


def test_preconfigured_manual_torque_values_preserved():
  cp = interfaces[CAR.GENESIS_G70_2020].get_non_essential_params(CAR.GENESIS_G70_2020)
  cp.lateralTuning.torque.latAccelFactor = 2.45
  cp.lateralTuning.torque.latAccelOffset = -.031
  cp.lateralTuning.torque.friction = .072
  controller = LatControlTorque(cp.as_reader(), interfaces[CAR.GENESIS_G70_2020](cp), .01)
  assert controller.torque_params.latAccelFactor == cp.lateralTuning.torque.latAccelFactor
  assert controller.torque_params.latAccelOffset == cp.lateralTuning.torque.latAccelOffset
  assert controller.torque_params.friction == cp.lateralTuning.torque.friction
  assert controller.pid.pos_limit == controller.lateral_accel_from_torque(1.0, controller.torque_params)


@pytest.mark.parametrize('angle', [-85., 0., 85.])
@pytest.mark.parametrize('pid_output', [-.125, 0., .125])
def test_angle_taper_uses_actual_sent_torque_direction(angle, pid_output):
  outputs = []
  for taper in (lambda *_: 1., genesis_g70_policy.get_genesis_g70_angle_output_scale):
    _, controller, vm = controller_for()
    cs = SimpleNamespace(vEgo=15., steeringAngleDeg=angle, steeringPressed=True)
    params = log.VehicleParameters.new_message(angleOffsetDeg=0., roll=0.)
    with patch.object(controller.pid, 'update', return_value=pid_output), \
         patch.object(controller, 'torque_from_lateral_accel', side_effect=lambda value, *_: value), \
         patch.object(genesis_g70_policy, 'get_genesis_g70_angle_output_scale', taper):
      output, _, state = controller.update(True, cs, vm, params, False, 0., False, .2)
    assert state.active
    outputs.append(output)
  baseline, tapered = outputs
  if pid_output == 0:
    assert baseline == tapered == 0
  else:
    assert baseline * pid_output < 0
    if baseline * angle > 0:
      assert 0 < abs(tapered) < abs(baseline)
    else:
      assert tapered == pytest.approx(baseline)
