"""Exercise native inherited Params locks on the Linux host CI filesystem."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
BINARY = ROOT / "openpilot/common/tests/bin/test_params_fork_lock"


@unittest.skipUnless(sys.platform == "linux", "Linux fork/exec and /proc descriptor contract")
class TestParamsForkLock(unittest.TestCase):
  def run_case(self, case):
    self.assertTrue(BINARY.is_file(), "Build the native regression target with existing SCons host dependencies")
    # Kernel-local /tmp is required: remote/macOS bind mounts can implement flock differently.
    with tempfile.TemporaryDirectory(prefix="params-fork-lock-", dir="/tmp") as directory:
      result = subprocess.run([str(BINARY), case, directory], cwd=ROOT,
                              capture_output=True, text=True, timeout=15, check=False)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

  def test_parent_releases_with_live_fork_child(self):
    self.run_case("inherited_release")

  def test_child_destructor_keeps_parent_exclusive(self):
    self.run_case("child_destructor")

  def test_exec_closes_lock_descriptor(self):
    self.run_case("exec")

  def test_competing_writer_exclusion_and_progress(self):
    self.run_case("competitor")

  def test_failed_lock_and_eintr_retry(self):
    self.run_case("failures_eintr")

  def test_real_params_async_batch_and_blocking_io(self):
    self.run_case("params_semantics")
