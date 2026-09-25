"""Exact native planner behavior when unchanged MPC cost writes are skipped."""

from collections import Counter
from typing import Any, cast
import unittest
from unittest.mock import patch

import numpy as np

from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.selfdrive.controls.lib import longitudinal_planner as planner_module
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib import long_mpc
from openpilot.starpilot.longitudinal.profile_runtime import ProfileTuning
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import messages


WRITES_PER_UPDATE = 2 * (long_mpc.N + 1)


class SolverRecorder:
  def __init__(self, native=None):
    self.native = native
    self.writes = Counter()
    self.resets = 0
    self.costs = {}
    self.fail_at = None

  def __getattr__(self, name):
    return getattr(self.native, name)

  def reset(self):
    self.resets += 1
    self.costs.clear()
    return self.native.reset()

  def cost_set(self, stage, field, data):
    if field in ('W', 'Zl'):
      self.writes[field] += 1
      if sum(self.writes.values()) == self.fail_at:
        raise RuntimeError('injected native cost write failure')
      self.costs[stage, field] = np.array(data, copy=True)
    if self.native is not None:
      return self.native.cost_set(stage, field, data)


class AlwaysWriteMpc(long_mpc.LongitudinalMpc):
  def set_cost_weights(self, cost_weights, constraint_cost_weights):
    self._cached_cost_weights = None
    super().set_cost_weights(cost_weights, constraint_cost_weights)


class TestMpcCostCache(unittest.TestCase):
  def recording_mpc(self):
    mpc = cast(Any, long_mpc.LongitudinalMpc.__new__(long_mpc.LongitudinalMpc))
    mpc.solver = SolverRecorder()
    mpc._cached_cost_weights = None
    return mpc

  def assert_array_bytes_equal(self, left, right):
    self.assertEqual(left.shape, right.shape)
    self.assertEqual(left.dtype, right.dtype)
    self.assertTrue(np.isfinite(left).all())
    self.assertTrue(np.isfinite(right).all())
    self.assertEqual(left.tobytes(), right.tobytes())

  def test_full_vectors_and_in_place_mutations_write_immediately(self):
    mpc = self.recording_mpc()
    cost, constraint = [3.0, 0.0, 0.0, 0.0, 200.0, 5.0], [1e6, 1e6, 1e6, 100.0]
    mpc.set_cost_weights(cost, constraint)
    count = WRITES_PER_UPDATE
    self.assertEqual(sum(mpc.solver.writes.values()), count)
    mpc.set_cost_weights(list(cost), list(constraint))
    self.assertEqual(sum(mpc.solver.writes.values()), count)
    for vector in (cost, constraint):
      for index in range(len(vector)):
        with self.subTest(vector='cost' if vector is cost else 'constraint', index=index):
          vector[index] += 0.125
          mpc.set_cost_weights(cost, constraint)
          count += WRITES_PER_UPDATE
          self.assertEqual(sum(mpc.solver.writes.values()), count)
          mpc.set_cost_weights(cost, constraint)
          self.assertEqual(sum(mpc.solver.writes.values()), count)

  def test_partial_failed_write_invalidates_previous_key_before_restoring_it(self):
    mpc = self.recording_mpc()
    a, constraints = [3.0, 0.0, 0.0, 0.0, 200.0, 5.0], [1e6, 1e6, 1e6, 100.0]
    b = [value + 1.0 for value in a]
    mpc.set_cost_weights(a, constraints)
    original = {key: value.copy() for key, value in mpc.solver.costs.items()}
    mpc.solver.fail_at = WRITES_PER_UPDATE + long_mpc.N + 3
    with self.assertRaisesRegex(RuntimeError, 'injected native'):
      mpc.set_cost_weights(b, [value + 1.0 for value in constraints])
    self.assertIsNone(mpc._cached_cost_weights)
    self.assertNotEqual(mpc.solver.costs[0, 'W'].tobytes(), original[0, 'W'].tobytes())
    count = sum(mpc.solver.writes.values())
    mpc.set_cost_weights(a, constraints)
    self.assertEqual(sum(mpc.solver.writes.values()), count + WRITES_PER_UPDATE)
    for key, expected in original.items():
      self.assert_array_bytes_equal(mpc.solver.costs[key], expected)
    mpc.set_cost_weights(a, constraints)
    self.assertEqual(sum(mpc.solver.writes.values()), count + WRITES_PER_UPDATE)

  def test_native_reset_rewrites_unchanged_costs(self):
    factory = long_mpc.AcadosOcpSolverCython
    with patch.object(long_mpc, 'AcadosOcpSolverCython', side_effect=lambda *args: SolverRecorder(factory(*args))):
      mpc = long_mpc.LongitudinalMpc()
    recorder = cast(Any, mpc.solver)
    self.assertEqual(sum(recorder.writes.values()), WRITES_PER_UPDATE)
    mpc.set_weights()
    self.assertEqual(sum(recorder.writes.values()), WRITES_PER_UPDATE)
    mpc.reset()
    self.assertEqual(recorder.resets, 2)
    self.assertEqual(sum(recorder.writes.values()), 2 * WRITES_PER_UPDATE)
    self.assertEqual(len(recorder.costs), WRITES_PER_UPDATE)

  def test_actual_native_outputs_survive_settings_sources_and_resets_unchanged(self):
    cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    factory = long_mpc.AcadosOcpSolverCython
    with patch.object(long_mpc, 'AcadosOcpSolverCython', side_effect=lambda *args: SolverRecorder(factory(*args))):
      actual = planner_module.LongitudinalPlanner(cp, init_v=20.0)
      with patch.object(planner_module, 'LongitudinalMpc', AlwaysWriteMpc):
        reference = planner_module.LongitudinalPlanner(cp, init_v=20.0)
    sources = set()
    for frame in range(320):
      lead = 120 <= frame < 160 or 220 <= frame < 240
      e2e, off, traffic = 160 <= frame < 200, 200 <= frame < 220, 240 <= frame < 280
      personality = 'aggressive' if 220 <= frame < 240 else 'standard'
      tuning = None
      if 60 <= frame < 280:
        tuning = ProfileTuning('traffic' if traffic else personality, 0.9 if traffic else 1.6,
                               1.3, 0.8, 1.2, 0.7, 1.1, 1.0 if traffic else 1.2, 0.42 if traffic else 1.1)
      if frame in (180, 300):
        reference.mpc.reset()
        actual.mpc.reset()
      for planner in (reference, actual):
        sm, _ = messages(lead=lead, e2e=e2e, off=off)
        sm['selfdriveState'].personality = personality
        sm['carControl'].longActive = not off
        sm['carState'].canValid = True
        sm['carState'].aEgo = 0.01 if frame // 10 % 2 else -0.01
        planner.update(sm, profile_tuning=tuning, traffic_mode=traffic, now_ns=100_000_000_000 + frame * 50_000_000)
        self.assertEqual(planner.mpc.solution_status, 0)
      with self.subTest(frame=frame):
        for name in ('v_desired_trajectory', 'a_desired_trajectory', 'j_desired_trajectory'):
          self.assert_array_bytes_equal(getattr(reference, name), getattr(actual, name))
        for name in ('x_sol', 'u_sol', 'params', 'a_prev', 'x0'):
          self.assert_array_bytes_equal(getattr(reference.mpc, name), getattr(actual.mpc, name))
        for name in ('output_a_target', 'output_should_stop', 'a_cruise', 'allow_throttle', 'fcw', 'last_profile'):
          self.assertEqual(getattr(reference, name), getattr(actual, name))
        self.assertEqual(reference.mpc.source, actual.mpc.source)
        expected_solver, actual_solver = cast(Any, reference.mpc.solver), cast(Any, actual.mpc.solver)
        self.assertEqual(expected_solver.costs.keys(), actual_solver.costs.keys())
        for key in expected_solver.costs:
          self.assert_array_bytes_equal(expected_solver.costs[key], actual_solver.costs[key])
        sources.add(actual.mpc.source)
    self.assertEqual(sources, {long_mpc.LongitudinalPlanSource.cruise, long_mpc.LongitudinalPlanSource.lead0,
                              long_mpc.LongitudinalPlanSource.e2e})
    self.assertEqual(expected_solver.resets, 3)
    self.assertEqual(actual_solver.resets, 3)
    self.assertEqual(sum(expected_solver.writes.values()), 323 * WRITES_PER_UPDATE)
    self.assertEqual(sum(actual_solver.writes.values()), 33 * WRITES_PER_UPDATE)


if __name__ == '__main__':
  unittest.main()
