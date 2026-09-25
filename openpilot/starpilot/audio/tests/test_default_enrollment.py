from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import ast
import tempfile
import unittest
from unittest.mock import patch

from openpilot.starpilot.audio import default_enrollment as enrollment


class FilesystemParams:
  def __init__(self, namespace):
    self.namespace = namespace

  def get_param_path(self):
    return str(self.namespace)


class SoundDefaultEnrollmentTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)
    self.target = self.root / "params" / ".namespace"
    self.target.mkdir(parents=True)
    self.namespace = self.target.parent / "d"
    self.namespace.symlink_to(self.target, target_is_directory=True)
    self.params = FilesystemParams(self.namespace)
    self.storage = self.root / "storage"

  def selection(self, value):
    if value is None:
      (self.namespace / "SoundPack").unlink(missing_ok=True)
    else:
      (self.namespace / "SoundPack").write_bytes(value)

  def enroll(self):
    return enrollment.enroll_default_sounds(self.params, self.storage)

  def marker(self):
    return next((self.storage / "sound-default-once").iterdir())

  def test_first_enrollment_replaces_all_selections_and_preserves_volumes(self):
    for raw in (None, b"", b"default", b"stock", b"custom", b"starpilot", b"frog", b"\xff"):
      with self.subTest(raw=raw), tempfile.TemporaryDirectory() as storage:
        self.selection(raw)
        volume = self.namespace / "EngageVolume"
        volume.write_bytes(b"37")
        self.assertTrue(enrollment.enroll_default_sounds(self.params, Path(storage)))
        self.assertEqual((self.namespace / "SoundPack").read_bytes(), b"starpilot")
        self.assertEqual(volume.read_bytes(), b"37")

  def test_completed_enrollment_preserves_menu_optout_across_restarts(self):
    self.enroll()
    marker_bytes = self.marker().read_bytes()
    for choice in (b"stock", b"custom", b"another-custom"):
      self.selection(choice)
      with patch.object(enrollment, "_write_selection", side_effect=AssertionError("repeat enrollment")):
        for _ in range(3):
          self.assertFalse(self.enroll())
      self.assertEqual((self.namespace / "SoundPack").read_bytes(), choice)
      self.assertEqual(self.marker().read_bytes(), marker_bytes)

  def test_new_resolved_namespace_at_same_path_enrolls(self):
    self.enroll()
    self.selection(b"stock")
    old_target = self.target
    self.target = old_target.parent / ".fresh"
    self.target.mkdir()
    self.namespace.unlink()
    self.namespace.symlink_to(self.target, target_is_directory=True)
    self.selection(b"custom")
    self.assertTrue(self.enroll())
    self.assertEqual((self.namespace / "SoundPack").read_bytes(), b"starpilot")
    self.assertEqual((old_target / "SoundPack").read_bytes(), b"stock")

  def test_failed_pending_marker_does_not_change_selection_and_retries(self):
    self.selection(b"stock")
    with patch.object(enrollment, "_atomic_write", side_effect=OSError("disk full")):
      with self.assertRaises(OSError):
        self.enroll()
    self.assertEqual((self.namespace / "SoundPack").read_bytes(), b"stock")
    self.assertTrue(self.enroll())

  def test_failed_selection_retries_without_marking_complete(self):
    self.selection(b"custom")
    with patch.object(enrollment, "_write_selection", side_effect=OSError("disk full")):
      with self.assertRaises(OSError):
        self.enroll()
    self.assertIn(b'"pending"', self.marker().read_bytes())
    self.assertEqual((self.namespace / "SoundPack").read_bytes(), b"custom")
    self.assertTrue(self.enroll())

  def test_failed_completion_retries_without_rewriting_soundpack(self):
    self.selection(b"stock")
    writer = enrollment._atomic_write

    def fail_complete(path, raw):
      if b'"complete"' in raw:
        raise OSError("disk full")
      writer(path, raw)

    with patch.object(enrollment, "_atomic_write", side_effect=fail_complete):
      with self.assertRaises(OSError):
        self.enroll()
    self.assertEqual((self.namespace / "SoundPack").read_bytes(), b"starpilot")
    with patch.object(enrollment, "_write_selection", side_effect=AssertionError("already selected")):
      self.assertTrue(self.enroll())
    self.selection(b"stock")
    self.assertFalse(self.enroll())
    self.assertEqual((self.namespace / "SoundPack").read_bytes(), b"stock")

  def test_changed_choice_during_pending_retry_is_preserved(self):
    self.selection(b"stock")
    with patch.object(enrollment, "_write_selection", side_effect=OSError("disk full")):
      with self.assertRaises(OSError):
        self.enroll()
    self.selection(b"custom")
    self.assertFalse(self.enroll())
    self.assertEqual((self.namespace / "SoundPack").read_bytes(), b"custom")
    self.assertFalse(self.enroll())

  def test_concurrent_enrollments_only_select_once(self):
    self.selection(b"custom")
    with ThreadPoolExecutor(max_workers=8) as pool:
      results = list(pool.map(lambda _: self.enroll(), range(16)))
    self.assertEqual(results.count(True), 1)
    self.assertEqual((self.namespace / "SoundPack").read_bytes(), b"starpilot")

  def test_selection_stages_outside_namespace_and_cleans_failed_write(self):
    self.selection(b"stock")
    replace = enrollment.os.replace
    observed = []

    def fail_selection(source, destination):
      if Path(destination) == self.namespace / "SoundPack":
        observed.append(Path(source))
        self.assertEqual(Path(source).parent, self.namespace.parent)
        self.assertEqual({path.name for path in self.target.iterdir()}, {"SoundPack"})
        raise OSError("replace failure")
      replace(source, destination)

    with patch.object(enrollment.os, "replace", side_effect=fail_selection):
      with self.assertRaises(OSError):
        self.enroll()
    self.assertEqual(len(observed), 1)
    self.assertFalse(observed[0].exists())
    self.assertEqual({path.name for path in self.target.iterdir()}, {"SoundPack"})
    self.assertTrue(self.enroll())

  def test_corrupt_marker_preserves_optout(self):
    self.enroll()
    self.selection(b"stock")
    self.marker().write_bytes(b"invalid")
    with self.assertRaises(ValueError):
      self.enroll()
    self.assertEqual((self.namespace / "SoundPack").read_bytes(), b"stock")

  def test_symlink_selection_is_not_followed_or_replaced(self):
    external = self.root / "external"
    external.write_bytes(b"custom")
    (self.namespace / "SoundPack").symlink_to(external)
    with self.assertRaises(OSError):
      self.enroll()
    self.assertEqual(external.read_bytes(), b"custom")
    self.assertTrue((self.namespace / "SoundPack").is_symlink())

  def test_manager_runs_after_admission_before_cleanup_and_warns_on_failure(self):
    # Inspect the real startup call without importing its hardware/process graph.
    manager = Path(enrollment.__file__).parents[2] / "system/manager/manager.py"
    tree = ast.parse(manager.read_text())
    init = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "manager_init")
    calls = [node for node in ast.walk(init) if isinstance(node, ast.Call)]
    def line(name):
      return next(node.lineno for node in calls if isinstance(node.func, ast.Name) and node.func.id == name)
    self.assertLess(line("prepare_manager_start"), line("enroll_default_sounds"))
    cleanup = next(node.lineno for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "clear_all")
    self.assertLess(line("enroll_default_sounds"), cleanup)
    guard = next(node for node in init.body if isinstance(node, ast.Try) and any(
      isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "enroll_default_sounds" for call in ast.walk(node)))
    self.assertEqual(ast.unparse(guard.handlers[0].type), "(OSError, ValueError)")
    self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "warning"
                        for node in ast.walk(guard.handlers[0])))


if __name__ == "__main__":
  unittest.main()
