import copy
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.ci import run_vehicle_tests
from tools.ci.fleet_coverage import source_snapshot_matches


class FleetSnapshotTest(unittest.TestCase):
  def setUp(self):
    directory = TemporaryDirectory()
    self.addCleanup(directory.cleanup)
    self.root = Path(directory.name)
    self.git("init", "-q")
    self.git("config", "user.name", "test")
    self.git("config", "user.email", "test@example.invalid")
    self.source = self.root / "opendbc_repo/car.py"
    self.source.parent.mkdir()
    self.source.write_text("value = 1\n")
    self.binary = self.root / "opendbc_repo/parser.so"
    self.binary.write_bytes(b"device-native")
    self.git("add", ".")
    self.git("commit", "-qm", "baseline")
    self.source.write_text("value = 2\n")
    self.binary.write_bytes(b"host-native")
    self.before = self.snapshot()
    self.report = {"revision": self.before["revision"], "inputs": self.before}

  def git(self, *args):
    return subprocess.check_output(["git", *args], cwd=self.root)

  def snapshot(self):
    with patch.object(run_vehicle_tests, "ROOT", self.root):
      return run_vehicle_tests.source_input_snapshot()

  def test_exact_dirty_source_and_host_native_snapshot_is_admitted(self):
    self.assertTrue(source_snapshot_matches(self.report, copy.deepcopy(self.report), self.snapshot()))

  def test_source_binary_and_new_untracked_mutations_are_rejected(self):
    for path, value in ((self.source, b"value = 3\n"), (self.binary, b"different-native"),
                        (self.root / "opendbc_repo/new.py", b"new source")):
      with self.subTest(path=path.name):
        prior = path.read_bytes() if path.exists() else None
        path.write_bytes(value)
        self.assertFalse(source_snapshot_matches(self.report, self.report, self.snapshot()))
        if prior is None:
          path.unlink()
        else:
          path.write_bytes(prior)

  def test_changed_head_is_rejected(self):
    self.git("add", ".")
    self.git("commit", "-qm", "new source")
    self.assertFalse(source_snapshot_matches(self.report, self.report, self.snapshot()))

  def test_missing_malformed_and_unstable_provenance_are_rejected(self):
    self.assertFalse(source_snapshot_matches({}, self.report, self.before))
    self.assertFalse(source_snapshot_matches(self.report, None, self.before))
    changed = copy.deepcopy(self.report)
    changed["inputs"]["tracked_patch_sha256"] = "0" * 64
    self.assertFalse(source_snapshot_matches(self.report, changed, self.before))
    malformed = copy.deepcopy(self.report)
    malformed["inputs"]["paths"] = []
    self.assertFalse(source_snapshot_matches(malformed, malformed, malformed["inputs"]))
