"""Independent known-plant fit and bounded stage application; pure Python only.

This does not stand in for native Controls/CAN or physical vehicle tests.
"""

from dataclasses import replace
import json
import math
import os
from pathlib import Path
import statistics
import time
from types import SimpleNamespace

from openpilot.starpilot.flm.adaptive_profile import Block, Sample, evaluate, ReplayValidation
from openpilot.starpilot.flm.physical_response import PhysicalRow, fit_physical
from openpilot.starpilot.flm.torque_adapter import Objective, TorqueStageOwner, Admission
from openpilot.starpilot.flm.torque_stages import apply_stages


def known_fit(block_count=8):
  identity = 'a' * 64
  physical = tuple(
    PhysicalRow(
      str(block),
      1_000_000_000 + (block * 40 + j) * 50_000_000,
      1_100_000_000 + (block * 40 + j) * 50_000_000,
      (-1 if block % 2 else 1) * (0.1 + j * 0.01),
      2 * (-1 if block % 2 else 1) * (0.1 + j * 0.01) + 0.01,
      'calibration-v1',
      'left' if block % 2 else 'right',
      True,
      False,
      False,
    )
    for block in range(8)
    for j in range(40)
  )
  model = fit_physical(
    identity, 'normalized_torque', 'calibration-v1', physical, lag_ns=100_000_000, min_excitation=0.05, max_rmse=0.001, now_ns=18_000_000_000
  )
  assert model is not None
  objective = Objective('feedforward', 'high', 'steady')
  blocks = []
  for block in range(block_count):
    sign = 1 if block % 2 else -1
    samples = []
    for j in range(80):
      stamp = 20_000_000_000 + (block * 80 + j) * 10_000_000
      command = sign * (0.1 + j * 0.003)
      desired_response = model.slope * command * 1.02 + model.intercept
      target = model.inverse(desired_response)
      assert target is not None
      features = (command, 0.0) if sign > 0 else (0.0, command)
      samples.append(Sample(stamp + 2_000_000, stamp, stamp + 1_000_000, features, target - command, 1.0))
    cohort = 'high.' + ('left' if sign > 0 else 'right') + '.steady'
    blocks.append(Block(identity, 'stage-' + str(block), cohort, objective.parameters[0].stage_revision, 'measured-model-v1', tuple(samples)))
  result = evaluate(
    identity,
    objective.parameters,
    tuple(blocks),
    now_ns=30_000_000_000,
    required_cohorts=objective.required_cohorts,
    response_revision='measured-model-v1',
    ridge=0.000001,
  )
  return objective, result


def test_known_plant_convergence_confidence_and_scoped_bounds():
  objective, result = known_fit()
  assert result.profile is not None, result
  assert all(0.019 < value <= 0.02 for value in result.profile.coefficients)
  assert all(value > 0 for _, value in result.profile.cohort_improvements)
  assert result.profile.candidate_loss < result.profile.baseline_loss
  assert len(result.profile.train_ids) == len(result.profile.heldout_ids) == 4
  # A missing direction cannot be turned into global confidence.
  _, insufficient = known_fit(block_count=3)
  assert insufficient.profile is None


def test_stage_gradual_application_and_exact_invalid_fallback():
  objective, result = known_fit()
  profile = result.profile
  replay = ReplayValidation(profile, 'baseline', 'model', True, True, profile.baseline_loss - profile.candidate_loss)
  source = TorqueStageOwner(profile.identity, objective, baseline_revision='baseline', physical_model_revision='model')
  parent = SimpleNamespace(automatic_flm_stages=source)
  cs = SimpleNamespace(vEgo=30.0, steeringPressed=False)
  baseline = (1.0, 0.3)
  now = profile.observed_ns
  for index in range(40):
    source.prepare(Admission(profile, now + index * 10_000_000, True, False, True, replay))
    ff, threshold = apply_stages(parent, cs, 0.5, 0.0, *baseline, active=True, limited=False)
    assert 1.0 < ff <= 1.0021 and threshold == baseline[1]
    assert max(source.applied_coordinates) <= (index + 1) * 0.00005 + 1e-12
  for invalid in ('override', 'limited', 'inactive', 'off', 'manual', 'fault', 'stale', 'identity'):
    current = replace(profile, identity='b' * 64) if invalid == 'identity' else profile
    source.prepare(
      Admission(current, now + (600_000_000 if invalid == 'stale' else 410_000_000), invalid != 'off', invalid == 'manual', invalid != 'fault', replay)
    )
    cs.steeringPressed = invalid == 'override'
    actual = apply_stages(parent, cs, 0.5, 0.0, *baseline, active=invalid != 'inactive', limited=invalid == 'limited')
    assert actual == baseline, invalid
  assert not hasattr(parent, 'torque_params')  # This stage never owns native tuning or permissions.


def test_added_stage_cost_has_fixed_work_and_record_measurement():
  # Controls/CAN qualification has a separate native performance gate. This
  # measures only the added finite stage guard and arithmetic on this host.
  class Source:
    applied_coordinates = (0.01, 0.01)

    def torque_residual(self, frame, *, stage_revision):
      return 0.01, 0.0

  parent = SimpleNamespace(automatic_flm_stages=Source())
  cs = SimpleNamespace(vEgo=30.0, steeringPressed=False)
  durations = []
  cpu_start = time.thread_time_ns()
  wall_start = time.perf_counter_ns()
  for _ in range(20000):
    start = time.perf_counter_ns()
    assert apply_stages(parent, cs, 0.5, 0.0, 1.0, 0.3, active=True, limited=False) == (1.01, 0.3)
    durations.append(time.perf_counter_ns() - start)
  wall, cpu = time.perf_counter_ns() - wall_start, time.thread_time_ns() - cpu_start
  ordered = sorted(durations)
  report = {
    'scope': 'pure stage helper only; not native Controls/CAN qualification',
    'iterations': len(durations),
    'wall_ns': wall,
    'thread_cpu_ns': cpu,
    'mean_call_ns': statistics.mean(durations),
    'p99_call_ns': ordered[int(0.99 * len(ordered))],
    'max_call_ns': max(durations),
    'fixed_parameters_max': 2,
  }
  destination = os.environ.get('FLM_STAGE_PERFORMANCE_REPORT')
  if destination:
    Path(destination).write_text(json.dumps(report, indent=2) + '\n')
  assert math.isfinite(report['mean_call_ns'])
  assert report['p99_call_ns'] < 250_000, report
