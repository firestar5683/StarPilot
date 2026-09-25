import contextlib
from concurrent.futures import Future
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from tools import test_runner


class TestRunnerAccounting(unittest.TestCase):
  def setUp(self):
    self.module = types.ModuleType("runner_accounting_fixture")
    sys.modules[self.module.__name__] = self.module
    self.addCleanup(sys.modules.pop, self.module.__name__)

  def fixture(self, name="Example", base=unittest.TestCase, **methods):
    cls = type(name, (base,), {
      "__module__": self.module.__name__,
      "test_first": lambda self: None,
      "test_second": lambda self: None,
      **methods,
    })
    setattr(self.module, name, cls)
    return list(test_runner.flatten(unittest.TestLoader().loadTestsFromTestCase(cls)))

  def run_fixture(self, tests):
    ids = [test.id() for test in tests]
    records = test_runner.run_batch(ids, capture_output=False)
    self.assertEqual([record["id"] for record in records], ids)
    return records

  def test_inherited_class_skip_accounts_for_each_selected_test(self):
    def skip(cls):
      raise unittest.SkipTest("abstract safety fixture")

    base = type("FixtureBase", (unittest.TestCase,), {"setUpClass": classmethod(skip)})
    tests = self.fixture(base=base)
    batches = test_runner.make_batches(tests, workers=8)
    self.assertEqual(batches, [[test.id() for test in tests]])
    records = self.run_fixture(tests)
    self.assertEqual([r["status"] for r in records], ["skipped", "skipped"])
    for record in records:
      self.assertIn("setUpClass (runner_accounting_fixture.Example)", record["detail"])
      self.assertIn("abstract safety fixture", record["detail"])

  def test_module_skip_and_missing_reason_are_explicit(self):
    def skip():
      raise unittest.SkipTest

    self.module.setUpModule = skip
    tests = self.fixture() + self.fixture("Another")
    self.assertEqual(len(test_runner.make_batches(tests, workers=8)), 1)
    records = self.run_fixture(tests)
    self.assertTrue(all(r["status"] == "skipped" for r in records))
    self.assertTrue(all("setUpModule" in r["detail"] and "No skip reason provided" in r["detail"] for r in records))

  def test_regular_skip_preserves_reason(self):
    tests = self.fixture(test_first=unittest.skip("not applicable")(lambda self: None))
    records = self.run_fixture(tests)
    self.assertEqual(records[0]["status"], "skipped")
    self.assertEqual(records[0]["detail"], "not applicable")
    self.assertEqual(records[1]["status"], "passed")

  def test_class_setup_and_teardown_errors_account_for_every_test(self):
    def fail(cls):
      raise RuntimeError("fixture unavailable")

    for method in ("setUpClass", "tearDownClass"):
      with self.subTest(method=method):
        tests = self.fixture(**{method: classmethod(fail)})
        records = self.run_fixture(tests)
        self.assertTrue(all(r["status"] == "error" for r in records))
        self.assertTrue(all(method in r["detail"] and "fixture unavailable" in r["detail"] for r in records))

  def test_module_setup_and_teardown_errors_account_for_every_test(self):
    def fail():
      raise RuntimeError("module unavailable")

    for method in ("setUpModule", "tearDownModule"):
      with self.subTest(method=method):
        setattr(self.module, method, fail)
        tests = self.fixture() + self.fixture("Another")
        records = self.run_fixture(tests)
        self.assertTrue(all(r["status"] == "error" for r in records))
        self.assertTrue(all(method in r["detail"] and "module unavailable" in r["detail"] for r in records))
        delattr(self.module, method)

  def test_missing_and_duplicate_outcomes_fail(self):
    records = test_runner.account_for_tests(["first", "missing"], [test_runner.make_record("first")])
    self.assertEqual([r["status"] for r in records], ["passed", "error"])
    self.assertIn("did not receive an outcome", records[1]["detail"])
    duplicate = test_runner.account_for_tests(["first"], [test_runner.make_record("first"), test_runner.make_record("first")])
    self.assertEqual(duplicate[0]["status"], "error")

  def test_loader_failure_is_reported_for_selected_id(self):
    ids = ["runner_accounting_fixture.Missing.test_missing"]
    records = test_runner.run_batch(ids, capture_output=False)
    self.assertEqual([r["id"] for r in records], ids)
    self.assertEqual(records[0]["status"], "error")
    self.assertIn("Missing", records[0]["detail"])

  def test_uncaught_batch_failure_accounts_for_all_selected_tests(self):
    def fail(self, result=None):
      raise RuntimeError("runner failure")

    records = self.run_fixture(self.fixture(run=fail))
    self.assertTrue(all(r["status"] == "error" for r in records))
    self.assertTrue(all("runner failure" in r["detail"] for r in records))

  def test_worker_failure_accounts_for_whole_batch(self):
    future = Future()
    future.set_exception(RuntimeError("worker exited"))
    with patch.object(test_runner, "ProcessPoolExecutor") as executor:
      executor.return_value.__enter__.return_value.submit.return_value = future
      records = list(test_runner.run_parallel([["first", "second"]], 2, "error", False))[0]
    self.assertEqual([r["id"] for r in records], ["first", "second"])
    self.assertTrue(all(r["status"] == "error" and "worker exited" in r["detail"] for r in records))

  def test_report_includes_skip_reasons_and_missing_result_failure(self):
    records = test_runner.account_for_tests(["skipped", "missing"], [test_runner.make_record("skipped", "skipped", "fixture reason")])
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
      status = test_runner.report(records, [], 10, 0)
    self.assertEqual(status, 1)
    self.assertIn("fixture reason", output.getvalue())
    self.assertIn("1 skipped, 1 error", output.getvalue())

  def test_json_report_preserves_accounting_and_errors(self):
    records = test_runner.account_for_tests(["skipped", "missing"], [test_runner.make_record("skipped", "skipped", "fixture reason")])
    with tempfile.TemporaryDirectory() as directory:
      report = Path(directory) / "nested/results.json"
      test_runner.write_json_report(report, ["skipped", "missing"], records, ["collection failed"], 1.25, 1)
      saved = json.loads(report.read_text())
    self.assertEqual(saved["collected"], 2)
    self.assertEqual(saved["selected_test_ids"], ["skipped", "missing"])
    self.assertEqual(saved["results"], records)
    self.assertEqual(saved["collection_errors"], ["collection failed"])
    self.assertEqual(saved["duration_seconds"], 1.25)
    self.assertEqual(saved["exit_code"], 1)

  def test_cli_json_report_smoke(self):
    with tempfile.TemporaryDirectory() as directory:
      temporary = Path(directory)
      (temporary / "runner_json_fixture.py").write_text("\n".join((
        "import unittest",
        "class Example(unittest.TestCase):",
        "  def test_pass(self): pass",
        "  @unittest.skip('fixture not applicable')",
        "  def test_skip(self): pass",
        "",
      )))
      report = temporary / "results.json"
      result = subprocess.run(
        [sys.executable, str(test_runner.ROOT / "tools/test_runner.py"), "-j1", "runner_json_fixture", "--json-output", str(report)],
        env={**os.environ, "PYTHONPATH": os.pathsep.join((str(temporary), str(test_runner.ROOT)))},
        capture_output=True, text=True, check=False,
      )
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      saved = json.loads(report.read_text())
    self.assertIn("collected 2 tests", result.stdout)
    self.assertIn("1 passed, 1 skipped", result.stdout)
    self.assertEqual(saved["collected"], len(saved["results"]))
    self.assertEqual(saved["exit_code"], result.returncode)
    self.assertEqual(saved["collection_errors"], [])
    self.assertEqual({r["id"] for r in saved["results"]}, set(saved["selected_test_ids"]))
    skipped = next(r for r in saved["results"] if r["status"] == "skipped")
    self.assertEqual(skipped["detail"], "fixture not applicable")


if __name__ == "__main__":
  unittest.main()
