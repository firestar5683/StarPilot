"""Current controller latency interpolation and bounded friction growth."""
import math
import random
from types import SimpleNamespace
from unittest import mock
import pytest
from opendbc.car import structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR
from openpilot.starpilot.flm.controller_replay import SelectedControllerFactory, capture_snapshot, restore_snapshot
from openpilot.starpilot.flm.tests.test_registered_controls_global import controls_for, frame


def actual(profile='2023'):
  cp = interfaces[CAR.HYUNDAI_IONIQ_6].get_non_essential_params(CAR.HYUNDAI_IONIQ_6)
  cp.lateralTuning.torque.latAccelFactor, cp.lateralTuning.torque.friction = 3., .09
  if profile == '2025':
    fw = cp.init('carFw', 2)
    fw[0].fwVersion, fw[1].fwVersion = b'IONIQ6-230915', b'IONIQ6-240206'
  controller, vm = SelectedControllerFactory(cp, 'starpilot', turn_assist=True).create()
  cs = structs.CarState.new_message(vEgo=30., gearShifter='drive')
  return cp, controller, vm, cs, SimpleNamespace(angleOffsetDeg=0., roll=0.)


@pytest.mark.parametrize('delay', [.01, .1, .1009, .299185186624527, .300019234418869, 1., 2., -.1])
def test_actual_controller_uses_continuous_original_delay_without_new_state(delay):
  cp, controller, vm, cs, params = actual()
  policy = controller.starpilot_extension.policy
  values = [i * .000001 for i in range(policy.request_buffer_len)]
  policy.curvature_request_buffer.extend(values)
  tune = controller.torque_params.to_dict()
  bounded = max(1., min(delay / controller.dt, float(len(values))))
  # The stored requests lie on an affine timeline: evaluate that timeline at
  # the requested fractional age independently of the two-sample implementation.
  expected = (len(values) - bounded) * .000001 * cs.vEgo ** 2
  with mock.patch.object(policy.jerk_filter, 'update', return_value=0.):
    _, _, state = controller.update(True, cs, vm, params, False, .0001, False, delay)
  assert state.desiredLateralAccel == pytest.approx(expected, abs=1e-8)
  assert controller.torque_params.to_dict() == tune
  assert cp.lateralTuning.torque.latAccelFactor == 3.


def test_actual_controller_delay_boundary_is_continuous_with_stepped_model_history():
  _, controller, vm, cs, params = actual()
  policy = controller.starpilot_extension.policy
  policy.curvature_request_buffer.extend([0.] * 100)
  policy.curvature_request_buffer[-29] = .0002
  snap = capture_snapshot(controller, vm)
  results = []
  for delay in (.299999999, .300000001):
    restore_snapshot(controller, vm, snap)
    with mock.patch.object(policy.jerk_filter, 'update', return_value=0.):
      output, _, state = controller.update(True, cs, vm, params, False, 0., False, delay)
    results.append((output, state.desiredLateralAccel))
  assert abs(results[0][0] - results[1][0]) < 1e-6
  assert abs(results[0][1] - results[1][1]) < 1e-6


@pytest.mark.parametrize('profile', ['2023', '2025'])
def test_friction_never_exceeds_current_request_or_retains_opposite_sign_and_reset_replays(profile):
  _, controller, vm, cs, params = actual(profile)
  policy = controller.starpilot_extension.policy
  tune = controller.torque_params.to_dict()
  rng = random.Random(814)
  for request in [.2, .3, .04, 0., -.2, -.3] + [rng.uniform(-.32, .32) for _ in range(300)]:
    value = policy.center_friction(request, cs, saturated=False)
    assert math.isfinite(value) and abs(value) <= abs(request)
    assert value * request >= 0.
    if request == 0.:
      assert value == 0.
  assert policy.center_friction(.7, cs, saturated=True) == .7
  assert policy.prev_center_friction is None
  empty = capture_snapshot(controller, vm)
  assert policy.center_friction(0., cs, saturated=False) == 0.
  assert policy.center_friction(.2, cs, saturated=False) == pytest.approx(.025)
  saved = capture_snapshot(controller, vm)
  assert len(saved.values) == len(empty.values)
  value = policy.prev_center_friction
  controller.update(False, cs, vm, params, False, 0., False, .1)
  assert policy.prev_center_friction is None
  restore_snapshot(controller, vm, saved)
  assert policy.prev_center_friction == value
  restore_snapshot(controller, vm, empty)
  assert policy.prev_center_friction is None
  assert controller.torque_params.to_dict() == tune


@pytest.mark.parametrize('gate', ['speed', 'override', 'manual', 'saturated'])
def test_current_raw_friction_preserved_when_growth_guard_not_eligible(gate):
  _, controller, _, cs, _ = actual()
  policy = controller.starpilot_extension.policy
  policy.prev_center_friction = -.3
  if gate == 'speed':
    cs.vEgo = 12.
  if gate == 'override':
    cs.steeringPressed = True
  if gate == 'manual':
    policy.surface = object()
  assert policy.center_friction(.25, cs, saturated=gate == 'saturated') == .25
  assert policy.prev_center_friction is None


@pytest.mark.parametrize('profile', ['2023', '2025'])
def test_actual_controls_factory_path_retains_cp_tunes_and_native_output_bounds(profile):
  cp, _, _, _, _ = actual(profile)
  with controls_for(cp, 'starpilot', True) as controls:
    original = controls.CP.as_builder().to_bytes()
    tune = controls.LaC.torque_params.to_dict()
    for tick in range(200):
      command, _ = frame(controls, 700_000_000_000 + tick * 10_000_000, tick,
                         active=tick >= 20, enabled=tick >= 20)
      assert math.isfinite(command.actuators.torque)
      assert abs(command.actuators.torque) <= controls.LaC.steer_max
      if tick < 20:
        assert not command.latActive and command.actuators.torque == 0.
      if tick >= 80:
        assert command.latActive
    assert controls.LaC.torque_params.to_dict() == tune
    assert controls.CP.as_builder().to_bytes() == original
