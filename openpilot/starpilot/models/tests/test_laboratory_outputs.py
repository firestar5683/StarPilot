import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

import numpy as np

from openpilot.starpilot.models.laboratory_outputs import (
  CURRENT_FRAME_OUTPUT_KEYS, LATERAL_OUTPUT_KEYS, LATERAL_PLAN_COLUMNS, compose_model_outputs, hybrid_action_values,
)


def normalized_fixture(offset):
  keys = (*LATERAL_OUTPUT_KEYS, *CURRENT_FRAME_OUTPUT_KEYS, "lead", "lead_prob", "meta", "planplus", "raw_pred", "unknown_extra")
  outputs = {key: np.arange(6, dtype=np.float32).reshape(1, 2, 3) + offset + index for index, key in enumerate(keys)}
  outputs["plan"] = np.arange(495, dtype=np.float32).reshape(1, 33, 15) + offset
  outputs["plan_stds"] = outputs["plan"] / 100
  return outputs


def output_digest(array):
  return hashlib.sha256(array.tobytes()).hexdigest()


class TestLaboratoryOutputs(unittest.TestCase):
  def test_frozen_original_normalized_composition(self):
    frozen = json.loads(Path(__file__).with_name("fixtures").joinpath("laboratory_outputs_original.json").read_text())
    self.assertEqual(frozen["original_source_sha256"], "f0210b2ca26a1b9c4adbcf5825d0d01851254dbfbdbc54595c16d9d77d71731f")
    for case in frozen["cases"]:
      with self.subTest(versions=case["versions"]):
        result = compose_model_outputs(normalized_fixture(case["lateral_offset"]), normalized_fixture(case["longitudinal_offset"]))
        self.assertEqual({key: output_digest(value) for key, value in result.items()}, case["expected"])

  def test_every_axis_and_head_owner(self):
    lateral, longitudinal = normalized_fixture(1000), normalized_fixture(2000)
    result = compose_model_outputs(lateral, longitudinal)
    for column in range(15):
      owner = lateral if column in LATERAL_PLAN_COLUMNS else longitudinal
      for key in ("plan", "plan_stds"):
        np.testing.assert_array_equal(result[key][..., column], owner[key][..., column])
    for key in LATERAL_OUTPUT_KEYS:
      np.testing.assert_array_equal(result[key], lateral[key])
    for key in (*CURRENT_FRAME_OUTPUT_KEYS, "lead", "lead_prob", "meta", "planplus", "raw_pred", "unknown_extra"):
      np.testing.assert_array_equal(result[key], longitudinal[key])

  def test_absent_lateral_and_frame_heads_remove_longitudinal_values(self):
    lateral, longitudinal = normalized_fixture(10), normalized_fixture(20)
    for key in LATERAL_OUTPUT_KEYS:
      del lateral[key]
    result = compose_model_outputs(lateral, longitudinal, {})
    self.assertTrue(set(LATERAL_OUTPUT_KEYS + CURRENT_FRAME_OUTPUT_KEYS).isdisjoint(result))
    explicit_frame = {"pose": np.ones((1, 6))}
    np.testing.assert_array_equal(compose_model_outputs(lateral, longitudinal, explicit_frame)["pose"], explicit_frame["pose"])

  def test_arrays_independent_in_both_directions(self):
    lateral, longitudinal = normalized_fixture(10), normalized_fixture(20)
    result = compose_model_outputs(lateral, longitudinal)
    for key, value in result.items():
      for inputs in (lateral, longitudinal):
        self.assertFalse(np.shares_memory(value, inputs[key]))
    original = {key: value.copy() for key, value in result.items()}
    for value in lateral.values():
      value.fill(-1)
    for value in longitudinal.values():
      value.fill(-2)
    for key in result:
      np.testing.assert_array_equal(result[key], original[key])
      result[key].fill(-3)
    self.assertTrue(all(np.all(value == -1) for value in lateral.values()))
    self.assertTrue(all(np.all(value == -2) for value in longitudinal.values()))

  def test_missing_or_incompatible_plan_and_uncertainty_fail(self):
    for key, value in (("plan", None), ("plan", np.zeros((1, 32, 15))), ("plan", np.zeros((15,))),
                       ("plan", np.zeros((1, 33, 14))), ("plan_stds", None), ("plan_stds", np.zeros((1, 32, 15)))):
      lateral, longitudinal = normalized_fixture(10), normalized_fixture(20)
      if value is None:
        del lateral[key]
      else:
        lateral[key] = value
      with self.subTest(key=key, shape=None if value is None else value.shape), self.assertRaises(ValueError):
        compose_model_outputs(lateral, longitudinal)
    lateral, longitudinal = normalized_fixture(10), normalized_fixture(20)
    del lateral["plan_stds"], longitudinal["plan_stds"]
    self.assertNotIn("plan_stds", compose_model_outputs(lateral, longitudinal))

  def test_nonfinite_even_unselected_arrays_fail(self):
    for role in (0, 1, 2):
      for value in (np.nan, np.inf, -np.inf):
        outputs = [normalized_fixture(10), normalized_fixture(20), normalized_fixture(30)]
        outputs[role]["unknown_extra"].flat[0] = value
        with self.subTest(role=role, value=value), self.assertRaises(ValueError):
          compose_model_outputs(*outputs)

  def test_raw_actions_omitted_with_mixed_head_presence(self):
    lateral, longitudinal = normalized_fixture(10), normalized_fixture(20)
    for outputs in (lateral, longitudinal):
      outputs["action"] = np.array([[10, 20]], dtype=np.float32)
      outputs["action_stds"] = np.ones((1, 2), dtype=np.float32)
    for present in (True, False):
      if not present:
        del lateral["action"], lateral["action_stds"]
      result = compose_model_outputs(lateral, longitudinal)
      self.assertNotIn("action", result)
      self.assertNotIn("action_stds", result)

  def test_decoded_actions_have_explicit_owners_and_finite_guard(self):
    lateral = SimpleNamespace(desiredCurvature=.012, desiredAcceleration=99, shouldStop=False)
    longitudinal = SimpleNamespace(desiredCurvature=99, desiredAcceleration=-.25, shouldStop=True)
    self.assertEqual(hybrid_action_values(lateral, longitudinal), {"desiredCurvature": .012, "desiredAcceleration": -.25, "shouldStop": True})
    for action, field in ((lateral, "desiredCurvature"), (longitudinal, "desiredAcceleration")):
      setattr(action, field, np.nan)
      with self.assertRaises(ValueError):
        hybrid_action_values(lateral, longitudinal)
      setattr(action, field, 0)

  def test_mixed_v14_v15_actions_decoded_before_composition(self):
    from openpilot.cereal import log
    from openpilot.starpilot.models.runner import action_from_outputs
    previous = log.ModelDataV2.Action()
    lateral = action_from_outputs({"action": np.array([[2., 80.]])}, "v14", previous, .2, .2, 10, long_smooth_seconds=0)
    longitudinal = action_from_outputs({"action": np.array([[40., -.5]])}, "v15", previous, .2, .2, 10, long_smooth_seconds=0)
    result = hybrid_action_values(lateral, longitudinal)
    self.assertAlmostEqual(result["desiredCurvature"], .02)
    self.assertAlmostEqual(result["desiredAcceleration"], -.5)
    self.assertFalse(result["shouldStop"])

  def test_mixed_v15_v9_actions_allow_different_head_presence(self):
    from openpilot.cereal import log
    from openpilot.starpilot.models.runner import action_from_outputs
    previous = log.ModelDataV2.Action()
    lateral, longitudinal = normalized_fixture(10), normalized_fixture(20)
    lateral["action"] = np.array([[3., 80.]])
    longitudinal["plan"] = np.zeros((1, 33, 15))
    longitudinal["plan"][..., 3] = 10
    longitudinal.pop("planplus")
    longitudinal["desired_curvature"] = np.array([[.8]])
    lat_action = action_from_outputs(lateral, "v15", previous, .2, .2, 10, long_smooth_seconds=0)
    long_action = action_from_outputs(longitudinal, "v9", previous, .2, .2, 10, long_smooth_seconds=0)
    self.assertNotIn("action", compose_model_outputs(lateral, longitudinal))
    result = hybrid_action_values(lat_action, long_action)
    self.assertAlmostEqual(result["desiredCurvature"], .03)
    self.assertEqual(result["desiredAcceleration"], 0.)
    self.assertFalse(result["shouldStop"])
