import copy
import unittest

from openpilot.starpilot.validation.control_modes import (
  AXES, CONFIG_HASHES, MODES, SCENARIOS, configuration_id, validate_matrix, validate_trace,
)


def fixture(mode="combined", owner="system", kind="synthetic"):
  """A validator fixture, not a recording from a supported vehicle."""
  configuration = {
    "platform": "VALIDATOR_FIXTURE", "device": "host", "harness": "fixture", "policy_id": "fixture-policy-v1",
    "source_commit": "a" * 40, "longitudinal_owner": owner, "supported_modes": list(MODES),
    **dict.fromkeys(CONFIG_HASHES, "b" * 64),
  }
  selected = dict(zip(AXES, MODES[mode], strict=True))
  active = selected | {"longitudinal": selected["longitudinal"] and owner == "system"}
  stock = selected["longitudinal"] and owner == "stock"
  frame = {
    "time_ns": 0, "mode": mode, "event": None,
    "observed": {
      "request": active.copy(), "permission": dict.fromkeys(AXES, True), "effective": active.copy(),
      "command_active": active.copy(), "blocking_fault": dict.fromkeys(AXES, False),
      "input_fresh": dict.fromkeys(AXES, True), "displayed_active": active.copy(),
      "control_can_observed": True, "safety_feedback_fresh": True, "stock_acc_active": stock,
    },
    "expected": {"effective": active.copy(), "command_active": active.copy(), "displayed_active": active.copy(), "stock_acc_active": stock},
  }
  frames = [frame, copy.deepcopy(frame)]
  frames[1]["time_ns"] = 10_000_000
  return {
    "schema_version": 1, "case_id": "fixture-" + mode, "scenario": "mode_" + mode, "evidence_kind": kind,
    "configuration": configuration, "recording_sha256": "c" * 64,
    "requirements": {"minimum_frames": 2, "max_frame_gap_ns": 20_000_000, "required_events": []}, "frames": frames,
  }


class TestControlModeContract(unittest.TestCase):
  def test_four_modes_are_distinct(self):
    for mode in MODES:
      with self.subTest(mode=mode):
        report = validate_trace(fixture(mode))
        self.assertEqual(report["status"], "pass", report)
        self.assertEqual(report["vehicle_qualification"], "not_established")

  def test_lateral_only_rejects_longitudinal_command(self):
    trace = fixture("lateral_only")
    trace["frames"][0]["observed"]["command_active"]["longitudinal"] = True
    self.assertEqual(validate_trace(trace)["status"], "failed")

  def test_longitudinal_only_rejects_lateral_command(self):
    trace = fixture("longitudinal_only")
    trace["frames"][0]["observed"]["command_active"]["lateral"] = True
    self.assertEqual(validate_trace(trace)["status"], "failed")

  def test_off_rejects_either_axis_even_if_expected(self):
    for axis in AXES:
      trace = fixture("off")
      trace["frames"][0]["observed"]["command_active"][axis] = True
      trace["frames"][0]["expected"]["command_active"][axis] = True
      self.assertEqual(validate_trace(trace)["status"], "failed")

  def test_stock_acc_is_separate_from_host_longitudinal(self):
    trace = fixture(owner="stock")
    self.assertEqual(validate_trace(trace)["status"], "pass")
    trace["frames"][0]["observed"]["command_active"]["longitudinal"] = True
    self.assertEqual(validate_trace(trace)["status"], "failed")

  def test_unknown_axis_is_uncovered_not_false(self):
    for signal in ("permission", "command_active", "input_fresh"):
      for missing in (False, True):
        trace = fixture("off")
        if missing:
          del trace["frames"][0]["observed"][signal]["lateral"]
        else:
          trace["frames"][0]["observed"][signal]["lateral"] = None
        self.assertEqual(validate_trace(trace)["status"], "uncovered")

  def test_missing_or_stale_feedback_is_uncovered(self):
    for value in (None, False):
      trace = fixture()
      trace["frames"][0]["observed"]["safety_feedback_fresh"] = value
      self.assertEqual(validate_trace(trace)["status"], "uncovered")

  def test_absent_control_can_cannot_prove_off(self):
    for value in (None, False):
      trace = fixture("off")
      trace["frames"][0]["observed"]["control_can_observed"] = value
      self.assertEqual(validate_trace(trace)["status"], "uncovered")

  def test_active_command_needs_axis_authorization(self):
    for signal in ("permission", "request", "effective", "input_fresh"):
      trace = fixture()
      trace["frames"][0]["observed"][signal]["lateral"] = False
      self.assertEqual(validate_trace(trace)["status"], "failed")

  def test_blocking_fault_is_axis_specific(self):
    trace = fixture("longitudinal_only")
    for frame in trace["frames"]:
      frame["observed"]["blocking_fault"]["lateral"] = True
    self.assertEqual(validate_trace(trace)["status"], "pass")
    trace["frames"][0]["observed"]["blocking_fault"]["longitudinal"] = True
    self.assertEqual(validate_trace(trace)["status"], "failed")

  def test_recovery_requires_explicit_policy_expectation(self):
    trace = fixture("off")
    trace["scenario"] = "policy_recovery"
    trace["requirements"]["required_events"] = ["policy_recovery"]
    trace["frames"][1]["event"] = "policy_recovery"
    self.assertEqual(validate_trace(trace)["status"], "pass")
    del trace["frames"][1]["expected"]["effective"]
    self.assertEqual(validate_trace(trace)["status"], "uncovered")

  def test_selection_display_need_not_equal_authorization(self):
    trace = fixture("lateral_only")
    trace["scenario"] = "cancel"
    trace["requirements"]["required_events"] = ["cancel"]
    for frame in trace["frames"]:
      frame["event"] = "cancel"
      for signal in ("effective", "command_active"):
        frame["observed"][signal]["lateral"] = False
        frame["expected"][signal]["lateral"] = False
    self.assertEqual(validate_trace(trace)["status"], "pass")

  def test_active_mode_needs_observed_activity(self):
    trace = fixture()
    for frame in trace["frames"]:
      for signal in ("effective", "command_active"):
        frame["observed"][signal] = dict.fromkeys(AXES, False)
        frame["expected"][signal] = dict.fromkeys(AXES, False)
    self.assertEqual(validate_trace(trace)["status"], "uncovered")

  def test_unsupported_mode_requires_denial(self):
    trace = fixture("longitudinal_only")
    trace["configuration"]["supported_modes"] = ["off", "lateral_only"]
    self.assertEqual(validate_trace(trace)["status"], "failed")
    for frame in trace["frames"]:
      for signal in ("effective", "command_active", "displayed_active"):
        frame["observed"][signal] = dict.fromkeys(AXES, False)
        frame["expected"][signal] = dict.fromkeys(AXES, False)
    self.assertEqual(validate_trace(trace)["status"], "pass")

  def test_time_gap_is_uncovered_and_reversal_is_error(self):
    trace = fixture()
    trace["frames"][1]["time_ns"] = 100_000_000
    self.assertEqual(validate_trace(trace)["status"], "uncovered")
    trace["frames"][1]["time_ns"] = 0
    self.assertEqual(validate_trace(trace)["status"], "error")

  def test_malformed_mode_and_booleans_are_errors(self):
    trace = fixture()
    trace["frames"][0]["mode"] = []
    self.assertEqual(validate_trace(trace)["status"], "error")
    trace = fixture()
    trace["frames"][0]["observed"]["command_active"]["lateral"] = 0
    self.assertEqual(validate_trace(trace)["status"], "error")

  def test_required_event_cannot_be_omitted(self):
    trace = fixture()
    trace["scenario"] = "restart"
    trace["requirements"]["required_events"] = ["restart"]
    self.assertEqual(validate_trace(trace)["status"], "uncovered")

  def test_missing_configuration_provenance_is_uncovered(self):
    trace = fixture()
    del trace["configuration"]["policy_sha256"]
    self.assertEqual(validate_trace(trace)["status"], "uncovered")

  def test_configuration_identity_includes_settings_and_firmware(self):
    trace = fixture()
    for key in ("settings_sha256", "firmware_manifest_sha256"):
      changed = copy.deepcopy(trace["configuration"])
      changed[key] = "d" * 64
      self.assertNotEqual(configuration_id(changed), configuration_id(trace["configuration"]))

  def test_synthetic_cases_never_satisfy_recorded_coverage(self):
    documents = [fixture(mode) for mode in MODES]
    result = validate_matrix(documents, [documents[0]["configuration"]])
    self.assertEqual(result["status"], "uncovered")
    self.assertEqual(len(result["uncovered"]), len(SCENARIOS))
    self.assertTrue(all(r["status"] == "pass" for r in result["results"]))

  def test_matrix_requires_all_scenarios_for_exact_configuration(self):
    trace = fixture(kind="replay")
    result = validate_matrix([trace], [trace["configuration"]])
    self.assertEqual(result["status"], "uncovered")
    self.assertEqual(len(result["uncovered"]), len(SCENARIOS) - 1)
    other = copy.deepcopy(trace["configuration"])
    other["harness"] = "another-fixture"
    result = validate_matrix([trace], [other])
    self.assertEqual(len(result["uncovered"]), len(SCENARIOS))

  def test_failure_is_not_hidden_by_another_passing_case(self):
    failed = fixture("off", kind="replay")
    failed["frames"][0]["observed"]["command_active"]["lateral"] = True
    passed = fixture("off", kind="replay")
    self.assertEqual(validate_matrix([failed, passed], [passed["configuration"]])["status"], "failed")

  def test_empty_matrix_does_not_pass(self):
    self.assertEqual(validate_matrix([], [])["status"], "uncovered")


if __name__ == "__main__":
  unittest.main()
