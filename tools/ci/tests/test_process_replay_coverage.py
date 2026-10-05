import ast
import tempfile
import unittest
from pathlib import Path

from tools.ci.process_replay_coverage import REQUIRED_REPLAY_LABELS, VOLVO_REQUIRED_TESTS, replay_coverage, write_coverage
from tools.ci.run_vehicle_tests import ROOT, targets_for


class TestProcessReplayCoverage(unittest.TestCase):
  def report(self, platforms=None, labels=None, targets=None):
    active = {label.lower(): [label] for label in REQUIRED_REPLAY_LABELS}
    active["volvo"] = ["VOLVO_V40"]
    return replay_coverage(active if platforms is None else platforms,
                           REQUIRED_REPLAY_LABELS if labels is None else labels,
                           {suite: targets_for(suite) for suite in VOLVO_REQUIRED_TESTS} if targets is None else targets,
                           full_test=True)

  def test_available_recordings_remain_required_and_volvo_is_explicitly_unrecorded(self):
    report = self.report()
    self.assertEqual(report["errors"], [])
    self.assertEqual(report["unrecorded_gaps"][0]["status"], "unrecorded")
    for label in REQUIRED_REPLAY_LABELS:
      self.assertTrue(self.report(labels=REQUIRED_REPLAY_LABELS - {label})["errors"])

  def test_actual_vehicle_suite_targets_include_required_source_and_both_native_modes(self):
    for suite, path in VOLVO_REQUIRED_TESTS.items():
      self.assertIn(path, targets_for(suite))
    module = ast.parse((ROOT / VOLVO_REQUIRED_TESTS["interfaces"]).read_text())
    self.assertTrue(any(isinstance(node, ast.ClassDef) and node.name == "TestVolvoC1Host" for node in module.body))

  def test_unknown_brand_changed_platform_and_obsolete_exception_fail(self):
    active = self.report()["active_platforms"]
    for change in ({**active, "new_brand": ["NEW_CAR"]},
                   {**active, "volvo": ["VOLVO_V40", "VOLVO_NEW"]},
                   {brand: ids for brand, ids in active.items() if brand != "volvo"}):
      self.assertTrue(self.report(platforms=change)["errors"])
    self.assertTrue(self.report(labels=REQUIRED_REPLAY_LABELS | {"VOLVO"})["errors"])

  def test_required_alternative_suite_removal_fails(self):
    targets = {suite: targets_for(suite) for suite in VOLVO_REQUIRED_TESTS}
    for suite, path in VOLVO_REQUIRED_TESTS.items():
      removed = {**targets, suite: [target for target in targets[suite] if target != path]}
      self.assertTrue(self.report(targets=removed)["errors"])

  def test_artifact_and_summary_expose_gap_without_execution_claim(self):
    with tempfile.TemporaryDirectory() as temporary:
      destination = Path(temporary) / "coverage.json"
      summary = Path(temporary) / "summary.md"
      write_coverage(self.report(), destination, summary)
      self.assertIn('"scope": "process_replay_input_inventory"', destination.read_text())
      self.assertIn("**unrecorded**", summary.read_text())
      self.assertIn("does not qualify the fleet", summary.read_text())
