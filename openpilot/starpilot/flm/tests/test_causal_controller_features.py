"""Actual registered controller filter regression; CAN closure is covered separately."""
import math
from types import SimpleNamespace

import pytest

from opendbc.car import structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR
from openpilot.starpilot.flm.controller_replay import (
  ControllerReplay, ReplayFrame, SelectedControllerFactory, _run, capture_snapshot,
  final_command, frame_input, restore_snapshot,
)
from openpilot.starpilot.flm.torque_adapter import Objective


@pytest.mark.parametrize('fingerprint', [CAR.GENESIS_G70_2020, CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN])
def test_high_speed_causal_features_preserve_selected_filter_across_actual_checkpoint(fingerprint):
  cp = interfaces[fingerprint].get_non_essential_params(fingerprint)
  factory = SelectedControllerFactory(cp, 'starpilot')
  objective = Objective('feedforward', 'high', 'steady')
  engine = ControllerReplay(factory, objective)
  controller, vm = factory.create()
  params = SimpleNamespace(angleOffsetDeg=0.0, roll=0.0)
  desired = .001
  cs = structs.CarState(vEgo=30.0, vEgoRaw=30.0, canValid=True,
                        gearShifter=structs.CarState.GearShifter.drive)
  cs.steeringAngleDeg = math.degrees(vm.get_steer_from_curvature(-desired, 30.0, 0.0))
  for _ in range(240):
    controller.update(True, cs, vm, params, False, desired, False, .1)
  first = 10_000_000_000
  initial = capture_snapshot(controller, vm)
  engine.checkpoint(first, initial)
  for tick in range(120):
    stamp = first + tick * 10_000_000
    if tick == 100:
      engine.checkpoint(stamp, capture_snapshot(controller, vm))
    inputs = frame_input(cs, vm, params, active=True, safety_limited=False,
                         desired_curvature=desired, curvature_limited=False, lat_delay=.1)
    raw, _, _ = controller.update(True, cs, vm, params, False, desired, False, .1)
    point = ReplayFrame(stamp, inputs, final_command(raw), (0.0, 0.0),
                        frame_sequence=tick + 1, actual_lac_command=raw)
    local = engine.normalize(point, epsilon=.01)
    assert local is not None and local.verified
  local_gain = local.features[0]
  engine.replay_windows = ((first, stamp),)
  assert engine.rebuild_causal_features(epsilon=.01) == 0  # Controller-only case.
  expected = []
  for coefficients in ((.01, 0.0), (-.01, 0.0)):
    branch, branch_vm = factory.create()
    restore_snapshot(branch, branch_vm, initial)
    for point in engine.records:
      value, _ = _run(branch, branch_vm, point.inputs, objective, coefficients, point.torque_values)
    expected.append(final_command(value))
  causal = engine.normalized[stamp]
  assert causal.plus_commands[0] == expected[0]
  assert causal.minus_commands[0] == expected[1]
  assert causal.features[0] == (expected[0] - expected[1]) / .02
  assert abs(causal.features[0]) > 1.5 * abs(local_gain)
