import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import TestCase, skipUnless
from unittest.mock import patch

from tools.ci import run_safety_qualification as qualification


class TestSafetyQualificationRunner(TestCase):
  @staticmethod
  def mutation_artifact():
    source = "opendbc/safety/helpers.h"
    def digest(path):
      return qualification.hashlib.sha256(path.read_bytes()).hexdigest()
    return {"schema_version": 1, "discovered": 1, "pruned_build_incompatible": [],
            "safety_input_sha256": digest(qualification.SAFETY_TESTS / "libsafety/safety.c"),
            "preprocessed_source_sha256": "1" * 64,
            "mutation_runner_sha256": digest(qualification.SAFETY_TESTS / "mutation.py"),
            "source_sha256": {source: digest(qualification.ROOT / "opendbc_repo" / source)},
            "baseline_sec": 1.0,
            "target_sets": [["test_mod.TestCase.test_one"]],
            "results": [{"site_id": 0, "source": source, "line": 40, "mutator": "boundary",
                         "original_op": "0", "mutated_op": "1", "outcome": "killed",
                         "selected_test_set": 0, "selected_test_count": 1, "details": "assertion",
                         "failure_kind": None, "exit_code": None, "stderr_tail": "", "stdout_tail": "",
                         "unittest_output_tail": ""}]}

  def test_coverage_instrumentation_is_required_and_does_not_leak_to_other_gates(self):
    for name, inherited in (("coverage", "0"), ("coverage", "1"), ("mutation-full", "1"), ("mutation-list", "1")):
      with self.subTest(gate=name, inherited=inherited), tempfile.TemporaryDirectory() as td, \
           patch.dict(os.environ, {"SAFETY_COVERAGE": inherited}):
        gate = qualification.Gate(name, Path(td), sys.executable)
        if name == "coverage":
          self.assertEqual(gate.env["SAFETY_COVERAGE"], "1")
        else:
          self.assertNotIn("SAFETY_COVERAGE", gate.env)

  def test_source_identity_includes_gate_and_workflow_inputs(self):
    identity = qualification.source_identity()
    self.assertFalse(any("/obj/" in path or "/gen/" in path for path in identity))
    for path in ("tools/ci/run_safety_qualification.py", "tools/ci/tests/test_safety_qualification.py",
                 ".github/workflows/safety.yaml", "pyproject.toml", "uv.lock",
                 "opendbc_repo/opendbc/safety/tests/libsafety/safety.c",
                 "openpilot/starpilot/aol/intent.py", "openpilot/cereal/SConscript",
                 "msgq_repo/msgq/ipc_pyx.pyx", "msgq_repo/SConscript", "tools/setup_dependencies.sh",
                 "openpilot/common/SConscript", "panda/tests/libpanda/SConscript",
                 "panda/board/stm32h7/stm32h7x5_flash.ld", "panda/board/stm32h7/startup_stm32h7x5xx.s",
                 "panda/tests/misra/coverage_table", "opendbc_repo/opendbc/safety/tests/misra/coverage_table"):
      self.assertEqual(identity[path], qualification.hashlib.sha256((qualification.ROOT / path).read_bytes()).hexdigest())

  def test_unittest_summary_preserves_skip_count_and_failed_state(self):
    log = "Safety qualification collected 3590 tests\nRan 3590 tests in 33.0s\n\nOK (skipped=425)\nSafety qualification suppressed 0 methods"
    self.assertEqual(qualification.parse_unittest_summary(log),
                     {"ran": 3590, "skipped": 425, "status": "OK", "collected": 3590, "suppressed": 0})
    self.assertEqual(qualification.parse_unittest_summary("Ran 1 test in 0.1s\n\nFAILED (failures=1)"),
                     {"ran": 1, "skipped": 0, "status": "FAILED", "collected": None, "suppressed": None})
    self.assertEqual(qualification.parse_unittest_summary(""), {"ran": None, "skipped": 0, "status": "missing", "collected": None, "suppressed": None})

  def test_partial_or_all_skipped_unittest_is_not_qualification(self):
    self.assertFalse(qualification.complete_unittest({"status": "OK", "collected": 2, "ran": 1, "skipped": 0, "suppressed": 0}))
    self.assertFalse(qualification.complete_unittest({"status": "OK", "collected": 2, "ran": 2, "skipped": 2, "suppressed": 0}))
    self.assertTrue(qualification.complete_unittest({"status": "OK", "collected": 2, "ran": 1, "skipped": 0, "suppressed": 1}))

  def test_mutation_summary_exposes_survivors_even_if_upstream_exempts_them(self):
    output = "Found 4461 unique candidates\n  pruned_build_incompatible: 3\n  killed: 4455\n  survived: 2\n  infra_error: 1\n"
    self.assertEqual(qualification.parse_mutation_summary(output),
                     {"candidates": 4461, "total": None, "killed": 4455, "survived": 2, "infra_error": 1, "pruned_build_incompatible": 3})

  def test_full_mutation_requires_matching_artifact_and_subprocess_success(self):
    log = "\n".join(("Found 1 unique candidates", "  pruned_build_incompatible: 0", "  total: 1",
                     "  killed: 1", "  survived: 0", "  infra_error: 0", ""))
    record = self.mutation_artifact()
    for code, write_artifact, expected in ((0, True, True), (1, True, False), (0, False, False)):
      with self.subTest(code=code, artifact=write_artifact), tempfile.TemporaryDirectory() as td:
        gate = qualification.Gate("mutation-full", Path(td), sys.executable)

        def fake_run(label, argv, *, active_gate=gate, active_code=code, should_write=write_artifact, **kwargs):
          self.assertEqual(label, "mutation")
          self.assertEqual(kwargs["cwd"], qualification.ROOT / "opendbc_repo")
          self.assertEqual(argv[-2], "--results-json")
          self.assertEqual(Path(argv[-1]), active_gate.output / "mutation-results.json")
          if should_write:
            Path(argv[-1]).write_text(json.dumps(record))
          return active_code, log

        with patch.object(gate, "run", side_effect=fake_run):
          self.assertEqual(gate.execute(), expected)
        self.assertEqual(gate.summary["artifact_valid"], write_artifact)
        self.assertEqual(bool(gate.artifacts), write_artifact)

  def test_mutation_artifact_rejects_unaccounted_or_unselected_candidate(self):
    summary = qualification.parse_mutation_summary("\n".join(
      ("Found 1 unique candidates", "  pruned_build_incompatible: 0", "  total: 1",
       "  killed: 1", "  survived: 0", "  infra_error: 0", "")))
    record = self.mutation_artifact()
    with tempfile.TemporaryDirectory() as td:
      path = Path(td) / "mutation-results.json"
      path.write_text(json.dumps(record))
      self.assertTrue(qualification.complete_mutation_artifact(path, summary))
      record["results"][0]["selected_test_count"] = 0
      path.write_text(json.dumps(record))
      self.assertFalse(qualification.complete_mutation_artifact(path, summary))
      record["results"] = []
      path.write_text(json.dumps(record))
      self.assertFalse(qualification.complete_mutation_artifact(path, summary))

  def test_mutation_artifact_rejects_malformed_ids_hashes_and_signal_as_kill(self):
    summary = {"candidates": 1, "pruned_build_incompatible": 0, "total": 1,
               "killed": 1, "survived": 0, "infra_error": 0}
    original = self.mutation_artifact()
    with tempfile.TemporaryDirectory() as td:
      path = Path(td) / "mutation-results.json"
      for label, change in (
        ("bool id", lambda item: item["results"][0].update(site_id=False)),
        ("bool version", lambda item: item.update(schema_version=True)),
        ("forged source", lambda item: item["source_sha256"].update({"opendbc/safety/helpers.h": "f" * 64})),
        ("forged runner", lambda item: item.update(mutation_runner_sha256="f" * 64)),
        ("forged safety input", lambda item: item.update(safety_input_sha256="f" * 64)),
        ("signal labeled kill", lambda item: item["results"][0].update(failure_kind="signal", exit_code=-11)),
      ):
        with self.subTest(label=label):
          record = json.loads(json.dumps(original))
          change(record)
          path.write_text(json.dumps(record))
          self.assertFalse(qualification.complete_mutation_artifact(path, summary))

  def test_mutation_artifact_rejects_special_and_oversized_files(self):
    summary = {"candidates": 1, "pruned_build_incompatible": 0, "total": 1,
               "killed": 1, "survived": 0, "infra_error": 0}
    with tempfile.TemporaryDirectory() as td:
      path = Path(td) / "mutation-results.json"
      os.mkfifo(path)
      self.assertFalse(qualification.complete_mutation_artifact(path, summary))
      path.unlink()
      target = Path(td) / "target.json"
      target.write_text(json.dumps(self.mutation_artifact()))
      path.symlink_to(target)
      self.assertFalse(qualification.complete_mutation_artifact(path, summary))
      path.unlink()
      with path.open("wb") as stream:
        stream.truncate(qualification.MAX_MUTATION_ARTIFACT_BYTES + 1)
      self.assertFalse(qualification.complete_mutation_artifact(path, summary))

  def test_mutation_full_rejects_preexisting_artifact_before_launch(self):
    with tempfile.TemporaryDirectory() as td:
      gate = qualification.Gate("mutation-full", Path(td), sys.executable)
      artifact = Path(td) / "mutation-results.json"
      artifact.symlink_to(Path(td) / "missing.json")
      with patch.object(gate, "run") as run:
        self.assertFalse(gate.execute())
      run.assert_not_called()
      self.assertFalse(gate.summary["artifact_valid"])

  def test_mutation_list_does_not_request_result_artifact(self):
    with tempfile.TemporaryDirectory() as td:
      gate = qualification.Gate("mutation-list", Path(td), sys.executable)

      def fake_run(label, argv, **_kwargs):
        self.assertEqual(label, "mutation")
        self.assertIn("--list-only", argv)
        self.assertNotIn("--results-json", argv)
        return 0, "Found 1 unique candidates\n"

      with patch.object(gate, "run", side_effect=fake_run):
        self.assertTrue(gate.execute())
      self.assertFalse((Path(td) / "mutation-results.json").exists())

  def test_origin_check_rejects_second_checkout(self):
    good = {"opendbc": str(qualification.ROOT / "opendbc_repo/opendbc/__init__.py"),
            "panda": str(qualification.ROOT / "panda/__init__.py"),
            "msgq": str(qualification.ROOT / "msgq_repo/msgq/__init__.py"),
            "openpilot": str(qualification.ROOT / "openpilot/__init__.py"),
            "libsafety_py": str(qualification.ROOT / "opendbc_repo/opendbc/safety/tests/libsafety/libsafety_py.py"),
            "can_parser": str(qualification.ROOT / "opendbc_repo/opendbc/can/parser.py"),
            "can_packer": str(qualification.ROOT / "opendbc_repo/opendbc/can/packer.py"),
            "can_dbc": str(qualification.ROOT / "opendbc_repo/opendbc/can/dbc.py"),
            "cereal_log": str(qualification.ROOT / "openpilot/cereal/log.capnp"),
            "cereal_messaging": str(qualification.ROOT / "openpilot/cereal/messaging/__init__.py"),
            "msgq_ipc": str(qualification.ROOT / "msgq_repo/msgq/ipc_pyx.so")}
    with tempfile.TemporaryDirectory() as td:
      output = Path(td) / "imports.log"
      with patch.object(qualification.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps(good), "")):
        self.assertTrue(qualification.check_import_origins("python", {}, output))
      good["opendbc"] = "/data/openpilot/opendbc_repo/opendbc/__init__.py"
      with patch.object(qualification.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps(good), "")):
        self.assertFalse(qualification.check_import_origins("python", {}, output))

  @skipUnless((qualification.ROOT / ".venv/bin/python").is_file() and
              (qualification.ROOT / "msgq_repo/msgq/ipc_pyx.so").is_file(),
              "requires the built locked environment; actual origin checks also run in every safety gate")
  def test_actual_second_checkout_import_shadow_is_rejected(self):
    with tempfile.TemporaryDirectory() as td:
      fake = Path(td) / "foreign"
      (fake / "panda").mkdir(parents=True)
      (fake / "panda/__init__.py").write_text("# second checkout shadow\n")
      gate = qualification.Gate("mutation-list", Path(td), qualification.ROOT / ".venv/bin/python")
      self.assertTrue(qualification.check_import_origins(gate.python, gate.env, Path(td) / "imports-baseline.log"))
      gate.env["PYTHONPATH"] = str(fake) + os.pathsep + gate.env["PYTHONPATH"]
      self.assertFalse(qualification.check_import_origins(gate.python, gate.env, Path(td) / "imports.log"))

  def test_timeout_fails_and_records_bounded_log(self):
    with tempfile.TemporaryDirectory() as td:
      output = Path(td)
      gate = qualification.Gate("coverage", output, "/usr/bin/python3")
      code, text = gate.run("timeout", [sys.executable, "-c", "import time; print('partial', flush=True); time.sleep(10)"], timeout=0.05)
      self.assertEqual(code, 124)
      self.assertIn("Timed out", text)
      self.assertIn("partial", (output / "timeout.log").read_text())
      self.assertEqual(gate.commands[0]["exit_code"], 124)

  def test_cppcheck_wrong_version_is_not_accepted(self):
    with tempfile.TemporaryDirectory() as td:
      gate = qualification.Gate("opendbc-misra", Path(td), "/usr/bin/python3")
      with patch.object(gate, "run", side_effect=[(0, "/tmp/cppcheck\n"), (0, "Cppcheck 2.20\n")]):
        self.assertIsNone(gate.cppcheck_dir())

  def test_misra_runs_both_debug_and_release(self):
    with tempfile.TemporaryDirectory() as td:
      gate = qualification.Gate("opendbc-misra", Path(td), "/usr/bin/python3")
      table = (qualification.ROOT / "opendbc_repo/opendbc/safety/tests/misra/coverage_table").read_text()
      calls = []

      def fake_run(label, argv, **_kwargs):
        calls.append((label, argv))
        if label == "misra-table":
          return 0, table
        if label == "compiler-include":
          return 0, "/usr/include\n"
        return 0, "Checking...\n"

      with patch.object(gate, "cppcheck_dir", return_value=Path("/tmp/cppcheck")), patch.object(gate, "run", side_effect=fake_run):
        self.assertTrue(gate.misra(False))
      variants = {label: argv for label, argv in calls if label.startswith("misra-") and label != "misra-table"}
      self.assertEqual(set(variants), {"misra-debug", "misra-release"})
      self.assertIn("-DALLOW_DEBUG", variants["misra-debug"])
      self.assertNotIn("-DALLOW_DEBUG", variants["misra-release"])

  def test_exception_still_writes_failed_results(self):
    with tempfile.TemporaryDirectory() as td:
      output = Path(td) / "evidence"
      root = Path(td) / "checkout"
      (root / ".venv/bin").mkdir(parents=True)
      (root / ".venv/bin/python").symlink_to(sys.executable)
      with patch.object(sys, "argv", ["run_safety_qualification.py", "--gate", "coverage", "--output", str(output)]), \
           patch.object(qualification, "ROOT", root), \
           patch.object(qualification, "source_identity", return_value={"source.py": "hash"}), \
           patch.object(qualification, "source_head", return_value="commit"), \
           patch.object(qualification, "generated_identity", return_value={}), \
           patch.object(qualification.Gate, "run", return_value=(0, "")) as invoke, \
           patch.object(qualification, "check_import_origins", return_value=True), \
           patch.object(qualification, "imported_module_hashes", return_value={}), \
           patch.object(qualification.Gate, "execute", side_effect=RuntimeError("fixture crash")):
        self.assertEqual(qualification.main(), 1)
        self.assertIn("openpilot/selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code/acados_ocp_solver_pyx.so",
                      invoke.call_args_list[0].args[1])
      report = json.loads((output / "results.json").read_text())
      self.assertFalse(report["passed"])
      self.assertIn("fixture crash", report["error"])
