import dataclasses
import unittest

from openpilot.starpilot.flm.automatic import (AcceptancePolicy, EvidenceWindow, PhysicalPoint,
  admit_linear_factor, evaluate_linear_factor, identity_digest, linear_policy)
from openpilot.starpilot.flm.gm_evidence import FLMSample


IDENTITY = {'vehicle': 'test-linear', 'conversionVersion': 'opendbc.linear_inverse_v1', 'basis': [2., 0., .1]}


def windows(factor=2.1):
  result = []
  torques = [.05] * 80 + [.15] * 80 + [.25] * 56 + [.35] * 24
  for block in range(20):
    side, speed = ((1, 20.), (-1, 20.), (1, 30.), (-1, 30.))[block % 4]
    slope = factor if isinstance(factor, float) else factor(block)
    start = 10_000_000_000 + block * 15_000_000_000
    rows, points = [], []
    for index, torque in enumerate(torques):
      stamp = start + index * 50_000_000
      torque *= side
      accel = slope * torque + side * .02
      rows.append(FLMSample('drive', block, stamp / 1e9, speed, True, False, False,
        accel, accel, 0., 0., 0., 0., 0., 0., 0., torque, 0., None, torque, torque, 0.))
      points.append(PhysicalPoint(stamp, torque, accel))
    result.append(EvidenceWindow(identity_digest(IDENTITY), f'block-{block}', tuple(rows), tuple(points),
                                 start - 2_000_000_000, 0))
  return tuple(result)


def evaluate(evidence, **kwargs):
  return evaluate_linear_factor(IDENTITY, evidence, baseline_factor=2., vehicle_factor=2.,
                                linear_conversion_verified=True, **kwargs)


class TestAutomaticLinearFactor(unittest.TestCase):
  def test_physical_fit_independent_blocks_freezes_other_coefficients(self):
    result = evaluate(windows())
    self.assertEqual(result.status, 'qualified_fit')
    self.assertEqual(result.family, 'linearFactor')
    self.assertEqual(result.acceptance_policy_id, linear_policy().identifier)
    self.assertEqual(len(result.candidate), 1)
    self.assertEqual(result.candidate[0][0], 'latAccelFactor')
    self.assertAlmostEqual(result.candidate[0][1], 2.1)
    metrics = dict(result.metrics)
    self.assertEqual(metrics['trainWindows'], 10)
    self.assertEqual(metrics['heldoutWindows'], 10)
    self.assertLess(metrics['heldoutFitMSE'], metrics['heldoutBaselineMSE'])
    self.assertGreater(metrics['heldoutImprovementLowerBound'], 0)

  def test_nearest_past_response_join_includes_final_real_control_row(self):
    evidence = windows()
    aligned = tuple(dataclasses.replace(w, response=tuple(dataclasses.replace(point, mono_ns=point.mono_ns + 20_000_000)
                    for point in w.response)) for w in evidence)
    self.assertEqual(evaluate(aligned).status, 'qualified_fit')
    expired = tuple(dataclasses.replace(w, response=tuple(dataclasses.replace(point, mono_ns=point.mono_ns + 31_000_000)
                    for point in w.response)) for w in evidence)
    self.assertEqual(evaluate(expired).status, 'rejected')

  def test_shared_physical_response_cannot_cross_independent_blocks(self):
    evidence = windows()
    first = dataclasses.replace(evidence[0], response=tuple(dataclasses.replace(point, mono_ns=point.mono_ns + 20_000_000)
                               for point in evidence[0].response))
    second = evidence[1]
    control_shift = first.response[-1].mono_ns - 10_000_000 - round(second.controls[0].t * 1e9)
    response_shift = first.response[-1].mono_ns - second.response[0].mono_ns
    second = dataclasses.replace(second,
      controls=tuple(dataclasses.replace(row, t=(round(row.t * 1e9) + control_shift) / 1e9) for row in second.controls),
      response=tuple(dataclasses.replace(point, mono_ns=point.mono_ns + response_shift) for point in second.response),
      active_since_ns=second.active_since_ns + response_shift)
    self.assertGreater(second.controls[0].t, first.controls[-1].t)
    self.assertEqual(second.response[0].mono_ns, first.response[-1].mono_ns)
    self.assertEqual(evaluate((first, second) + evidence[2:]).status, 'rejected')

  def test_heldout_cohort_regression_is_not_training_success(self):
    for heldout in (lambda block: 2.1 if block < 10 else 1.9,
                    lambda block: 1.8 if block >= 10 and block % 4 == 0 else 2.1):
      with self.subTest(heldout=heldout):
        result = evaluate(windows(heldout))
        self.assertEqual(result.status, 'rejected')
        self.assertEqual(result.candidate, ())
        self.assertEqual(result.reason, 'heldout_direction_speed_regression')

  def test_maturity_and_identifiability_do_not_default_to_confidence(self):
    self.assertEqual(evaluate(windows()[:12]).status, 'collecting')
    self.assertEqual(evaluate(windows(2.)).reason, 'factor_change_not_identified')
    evidence = windows()
    sparse = tuple(dataclasses.replace(w, controls=w.controls[:160], response=w.response[:160]) for w in evidence)
    self.assertEqual(evaluate(sparse).reason, 'physical_excitation_insufficient')
    one_cohort = tuple(dataclasses.replace(w, controls=tuple(dataclasses.replace(row, v_ego=20.) for row in w.controls))
                       for w in evidence)
    self.assertEqual(evaluate(one_cohort).reason, 'independent_direction_speed_support_insufficient')
    self.assertEqual(evaluate(windows(2.7)).reason, 'factor_envelope_or_step')

  def test_source_override_alignment_and_duplicate_blocks_deny(self):
    evidence = windows()
    first = evidence[0]
    changes = (
      dataclasses.replace(first, identity_sha256='0' * 64),
      dataclasses.replace(first, controls=(dataclasses.replace(first.controls[0], t=1e308),) + first.controls[1:]),
      dataclasses.replace(first, active_since_ns=first.response[0].mono_ns),
      dataclasses.replace(first, alignment_lag_ns=1),
      dataclasses.replace(first, controls=(dataclasses.replace(first.controls[0], steering_pressed=True),) + first.controls[1:]),
      dataclasses.replace(first, controls=(dataclasses.replace(first.controls[0], saturated=True),) + first.controls[1:]),
      dataclasses.replace(first, response=(dataclasses.replace(first.response[0], mono_ns=first.response[0].mono_ns - 1),) + first.response[1:]),
    )
    for changed in changes:
      with self.subTest(changed=changed):
        result = evaluate((changed,) + evidence[1:])
        self.assertEqual(result.status, 'rejected')
        self.assertEqual(result.candidate, ())
    self.assertEqual(evaluate((first, first) + evidence[2:]).reason, 'window_limit_or_duplicate')
    self.assertEqual(evaluate((evidence[1], evidence[0]) + evidence[2:]).status, 'rejected')

  def test_block_uncertainty_can_prevent_an_apparent_average_change(self):
    result = evaluate(windows(lambda block: 1.75 if block < 5 else 2.35))
    self.assertEqual(result.reason, 'factor_change_not_identified')
    self.assertEqual(result.candidate, ())

  def test_conversion_policy_and_existing_envelope_are_required(self):
    result = evaluate_linear_factor(IDENTITY, windows(), baseline_factor=2., vehicle_factor=2.,
                                    linear_conversion_verified=False)
    self.assertEqual(result.status, 'unavailable')
    self.assertEqual(evaluate(windows(), policy=None).status, 'unavailable')
    self.assertEqual(evaluate(windows(), policy=AcceptancePolicy(max_step_fraction=.08)).status, 'unavailable')
    self.assertTrue(admit_linear_factor(1.4, 2., 2., .3))
    self.assertTrue(admit_linear_factor(2.6, 2., 2., .3))
    for value in (1.399, 2.601, float('nan'), True):
      self.assertFalse(admit_linear_factor(value, 2., 2., .3))


if __name__ == '__main__':
  unittest.main()
