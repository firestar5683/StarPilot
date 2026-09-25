from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import signal
import threading
import time
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

  def test_prerequisite_transition_rejects_every_unexpected_bootstrap_change(self):
    outputs = dict.fromkeys(qualification.MPC_PREREQUISITE_OUTPUTS, "old-output")
    inputs = dict.fromkeys(("openpilot/selfdrive/controls/lib/longitudinal_mpc_lib/long_mpc.py",
                           "openpilot/selfdrive/controls/lib/longitudinal_mpc_lib/SConscript",
                           "openpilot/cereal/car.capnp", "opendbc_repo/opendbc/safety/safety.h",
                           "msgq_repo/msgq/ipc_pyx.pyx", "tools/ci/run_safety_qualification.py"), "input")
    before = {**outputs, **inputs}
    regenerated = {**dict.fromkeys(outputs, "new-output"), **inputs}
    for name in ("coverage", "mutation-full"):
      with self.subTest(gate=name):
        self.assertTrue(qualification.prerequisite_transition(before, regenerated, name))
        for path in inputs:
          with self.subTest(changed_input=path):
            self.assertFalse(qualification.prerequisite_transition(before, {**regenerated, path: "changed"}, name))
        self.assertFalse(qualification.prerequisite_transition(before, {**regenerated, "openpilot/undeclared.c": "new"}, name))
        removed = dict(regenerated)
        removed.pop(next(iter(outputs)))
        self.assertFalse(qualification.prerequisite_transition(before, removed, name))
    for name in ("panda-host", "panda-misra", "opendbc-misra", "mutation-list"):
      with self.subTest(gate=name):
        self.assertFalse(qualification.prerequisite_transition(before, regenerated, name))
        self.assertTrue(qualification.prerequisite_transition(before, before, name))

  def test_clean_checkout_bootstrap_hashes_real_files_and_rejects_generator_change(self):
    with tempfile.TemporaryDirectory() as td:
      root = Path(td)
      generator = "openpilot/selfdrive/controls/lib/longitudinal_mpc_lib/long_mpc.py"
      for path in (*qualification.MPC_PREREQUISITE_OUTPUTS, generator):
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("checked-in source fixture\n")
      subprocess.run(["git", "-c", "gc.auto=0", "init", "--quiet", str(root)], check=True)
      subprocess.run(["git", "-c", "gc.auto=0", "add", "."], cwd=root, check=True)
      with patch.object(qualification, "ROOT", root):
        before = qualification.source_identity()
        for path in qualification.MPC_PREREQUISITE_OUTPUTS:
          (root / path).write_text("regenerated output fixture\n")
        built = qualification.source_identity()
        self.assertEqual(set(before), set(built))
        self.assertEqual({path for path in before if before[path] != built[path]}, set(qualification.MPC_PREREQUISITE_OUTPUTS))
        self.assertTrue(qualification.prerequisite_transition(before, built, "coverage"))
        (root / generator).write_text("unexpected changed generator\n")
        self.assertFalse(qualification.prerequisite_transition(before, qualification.source_identity(), "coverage"))

  def test_main_pins_inputs_before_bootstrap_and_all_outputs_after_bootstrap(self):
    before = {**dict.fromkeys(qualification.MPC_PREREQUISITE_OUTPUTS, "old-output"),
              "opendbc_repo/opendbc/safety/safety.h": "input"}
    regenerated = {**dict.fromkeys(qualification.MPC_PREREQUISITE_OUTPUTS, "new-output"),
                   "opendbc_repo/opendbc/safety/safety.h": "input"}
    cases = (("fresh bootstrap", regenerated, regenerated, "commit", True, True),
             ("input mutation", {**regenerated, "opendbc_repo/opendbc/safety/safety.h": "bad"}, regenerated, "commit", False, False),
             ("head mutation", regenerated, regenerated, "other-commit", False, False),
             ("output changed after bootstrap", regenerated, before, "commit", True, False),
             ("native prerequisite changed during gate", regenerated, regenerated, "commit", True, False),
             ("solver companion changed during gate", regenerated, regenerated, "commit", True, False))
    for name, built, final, built_head, executed, passed in cases:
      with self.subTest(case=name), tempfile.TemporaryDirectory() as td:
        root = Path(td) / "checkout"
        (root / ".venv/bin").mkdir(parents=True)
        (root / ".venv/bin/python").symlink_to(sys.executable)
        output = Path(td) / "evidence"
        extension = ".dylib" if sys.platform == "darwin" else ".so"
        artifacts = (f"openpilot/common/libparams_c{extension}", "msgq_repo/msgq/ipc_pyx.so",
                     "openpilot/selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code/acados_ocp_solver_pyx.so")
        artifacts = qualification.prerequisite_artifact_paths(artifacts, "coverage")
        for path in artifacts:
          artifact = root / path
          artifact.parent.mkdir(parents=True, exist_ok=True)
          artifact.write_bytes(b"built-native")

        def execute_gate(case_name=name, case_root=root, case_artifacts=artifacts):
          if case_name == "native prerequisite changed during gate":
            (case_root / case_artifacts[2]).write_bytes(b"unexpected replacement")
          if case_name == "solver companion changed during gate":
            (case_root / case_artifacts[3]).write_bytes(b"unexpected solver replacement")
          return True

        with patch.object(sys, "argv", ["qualification", "--gate", "coverage", "--output", str(output)]), \
             patch.object(qualification, "ROOT", root), \
             patch.object(qualification, "source_identity", side_effect=(before, built, final)), \
             patch.object(qualification, "source_head", side_effect=("commit", built_head, built_head)), \
             patch.object(qualification, "generated_identity", return_value={}), \
             patch.object(qualification.Gate, "run", return_value=(0, "")), \
             patch.object(qualification.Gate, "hash_artifact"), \
             patch.object(qualification, "check_import_origins", return_value=True), \
             patch.object(qualification, "imported_module_hashes", return_value={}), \
             patch.object(qualification.Gate, "execute", side_effect=execute_gate) as execute:
          self.assertEqual(qualification.main(), 0 if passed else 1)
          self.assertEqual(execute.called, executed)
        report = json.loads((output / "results.json").read_text())
        self.assertEqual(report["passed"], passed)
        self.assertEqual(report["source_unchanged"], executed and built == final)
        self.assertEqual(report["prerequisite_artifacts_unchanged"],
                         executed and name not in ("native prerequisite changed during gate", "solver companion changed during gate"))
        if name == "fresh bootstrap":
          self.assertEqual(json.loads((output / "source-before.json").read_text()), before)
          self.assertEqual(json.loads((output / "source-after-prerequisites.json").read_text()), built)
          self.assertEqual(set(report["prerequisite_outputs"]), set(qualification.MPC_PREREQUISITE_OUTPUTS))

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
                     {"candidates": 4461, "total": None, "killed": 4455, "survived": 2, "infra_error": 1, "pruned_build_incompatible": 3,
                      "proven_equivalent": 0})

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

  def test_mutation_stream_matches_captured_text_exit_and_summary(self):
    script = ("import os,sys,time; "
              + "os.write(1,b'out\\r'); time.sleep(0.02); os.write(1,b'\\n'); "
              + "os.write(2,b'err\\r\\n'); os.write(1,b'\\xe2'); time.sleep(0.02); "
              + "os.write(1,b'\\x82\\xac\\nFound 2 unique candidates\\n  total: 2\\n  killed: 2\\n'); "
              + "sys.exit(int(sys.argv[1]))")
    for name, exit_code in (("mutation-full", 0), ("mutation-list", 7), ("coverage", 0)):
      with self.subTest(gate=name), tempfile.TemporaryDirectory() as td:
        gate = qualification.Gate(name, Path(td), sys.executable)
        argv = [sys.executable, "-c", script, str(exit_code)]
        baseline = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, env=gate.env, cwd=td, check=False)
        visible = io.StringIO()
        with redirect_stdout(visible):
          code, text = gate.run("mutation", argv, cwd=td)
        self.assertEqual((code, text), (baseline.returncode, baseline.stdout))
        self.assertEqual((Path(td) / "mutation.log").read_text(), text)
        self.assertEqual(visible.getvalue(), text if name.startswith("mutation-") else "")
        self.assertEqual(qualification.parse_mutation_summary(text), qualification.parse_mutation_summary(baseline.stdout))
        self.assertEqual(gate.commands[0]["exit_code"], exit_code)

  def test_mutation_progress_is_visible_and_logged_before_child_exits(self):
    ready = threading.Event()

    class Visible(io.StringIO):
      def write(self, text):
        count = super().write(text)
        if "ready" in self.getvalue():
          ready.set()
        return count

    with tempfile.TemporaryDirectory() as td:
      output = Path(td)
      release = output / "release"
      script = ("import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); "
                + "sys.stdout.write('ready'); sys.stdout.flush(); "
                + "exec('while not p.exists(): time.sleep(0.01)'); print(' done',flush=True)")
      gate = qualification.Gate("mutation-full", output, sys.executable)
      results, errors = [], []

      def invoke():
        try:
          results.append(gate.run("mutation", [sys.executable, "-c", script, str(release)], cwd=td, timeout=5))
        except Exception as error:
          errors.append(error)

      worker = threading.Thread(target=invoke)
      with redirect_stdout(Visible()):
        worker.start()
        try:
          self.assertTrue(ready.wait(3), "No progress until child exit")
          self.assertTrue(worker.is_alive())
          self.assertEqual((output / "mutation.log").read_text(), "ready")
        finally:
          release.touch()
          worker.join(6)
      self.assertFalse(worker.is_alive())
      self.assertEqual(errors, [])
      self.assertEqual(results, [(0, "ready done\n")])

  def test_mutation_timeout_kills_descendant_group_and_keeps_partial_text(self):
    with tempfile.TemporaryDirectory() as td:
      output = Path(td)
      marker = output / "descendant-survived"
      descendant = ("import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); "
                    + "p.with_suffix('.ready').write_text('ready'); time.sleep(3); p.write_text('alive')")
      script = ("import pathlib,subprocess,sys,time; "
                + "subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]]); "
                + "p=pathlib.Path(sys.argv[2]).with_suffix('.ready'); "
                + "exec('while not p.exists(): time.sleep(0.01)'); print('partial',flush=True); time.sleep(10)")
      gate = qualification.Gate("mutation-full", output, sys.executable)
      original_popen = subprocess.Popen
      processes = []

      def spawn(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        processes.append(process)
        return process

      visible = io.StringIO()
      start = time.monotonic()
      with redirect_stdout(visible), patch.object(qualification.subprocess, "Popen", side_effect=spawn):
        code, text = gate.run("mutation", [sys.executable, "-c", script, descendant, str(marker)], cwd=td, timeout=1)
      self.assertLess(time.monotonic() - start, 2.5)
      self.assertTrue(marker.with_suffix(".ready").exists())
      self.assertEqual(code, 124)
      self.assertEqual(processes[0].returncode, -signal.SIGKILL)
      self.assertEqual(text, "partial\n\nTimed out; process group killed\n")
      self.assertEqual(visible.getvalue(), text)
      self.assertEqual((output / "mutation.log").read_text(), text)
      self.assertEqual(gate.commands[0]["exit_code"], 124)
      time.sleep(3.2)
      self.assertFalse(marker.exists(), "Descendant survived timeout group cleanup")

  def test_mutation_sink_failure_cleans_up_child_before_returning_error(self):
    class Broken(io.StringIO):
      def write(self, text):
        raise BrokenPipeError("sink closed")

    with tempfile.TemporaryDirectory() as td:
      gate = qualification.Gate("mutation-full", Path(td), sys.executable)
      original_popen = subprocess.Popen
      processes = []

      def spawn(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        processes.append(process)
        return process

      script = "import time; print('partial',flush=True); time.sleep(10)"
      with redirect_stdout(Broken()), patch.object(qualification.subprocess, "Popen", side_effect=spawn):
        code, text = gate.run("mutation", [sys.executable, "-c", script], cwd=td, timeout=2)
      self.assertEqual((code, text), (127, "BrokenPipeError: sink closed\n"))
      self.assertEqual(processes[0].returncode, -signal.SIGKILL)
      self.assertTrue(processes[0].stdout.closed)
      self.assertEqual((Path(td) / "mutation.log").read_text(), text)

  def test_mutation_log_open_failure_does_not_launch_child(self):
    with tempfile.TemporaryDirectory() as td:
      output = Path(td)
      gate = qualification.Gate("mutation-full", output, sys.executable)
      (output / "mutation.log").mkdir()
      marker = output / "child-started"
      script = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text('started')"
      with patch.object(qualification.subprocess, "Popen", wraps=subprocess.Popen) as spawn:
        with self.assertRaises(IsADirectoryError):
          gate.run("mutation", [sys.executable, "-c", script, str(marker)], cwd=td)
      spawn.assert_not_called()
      self.assertFalse(marker.exists())

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
      source = {"source.py": "hash", **dict.fromkeys(qualification.MPC_PREREQUISITE_OUTPUTS, "generated-hash")}
      with patch.object(sys, "argv", ["run_safety_qualification.py", "--gate", "coverage", "--output", str(output)]), \
           patch.object(qualification, "ROOT", root), \
           patch.object(qualification, "source_identity", return_value=source), \
           patch.object(qualification, "source_head", return_value="commit"), \
           patch.object(qualification, "generated_identity", return_value={}), \
           patch.object(qualification, "prerequisite_artifact_identity", return_value={"fixture.so": "hash"}), \
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
