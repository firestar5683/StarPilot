import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("diagnostics_settings", Path(__file__).resolve().parents[1] / "diagnostics_settings.py")
settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings)


class DiagnosticsSettingsTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    original = settings.ENABLED
    self.addCleanup(setattr, settings, "ENABLED", original)
    settings.ENABLED = Path(temporary.name) / "galaxy-ble" / "diagnostics-enabled"

  def test_defaults_off_and_persists_after_reload(self):
    self.assertFalse(settings.diagnostics_enabled())
    self.assertTrue(settings.set_diagnostics_enabled(True, offroad=True))
    reloaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reloaded)
    reloaded.ENABLED = settings.ENABLED
    self.assertTrue(reloaded.diagnostics_enabled())

  def test_onroad_never_changes_permission(self):
    self.assertFalse(settings.set_diagnostics_enabled(True, offroad=False))
    self.assertFalse(settings.ENABLED.parent.exists())
    settings.set_diagnostics_enabled(True, offroad=True)
    self.assertFalse(settings.set_diagnostics_enabled(False, offroad=False))
    self.assertTrue(settings.diagnostics_enabled())

  def test_preserves_manual_opt_in_and_other_files(self):
    settings.ENABLED.parent.mkdir()
    settings.ENABLED.touch()
    key = settings.ENABLED.parent / "pairing-key.json"
    key.write_bytes(b"existing key")
    self.assertTrue(settings.diagnostics_enabled())
    settings.set_diagnostics_enabled(False, offroad=True)
    self.assertFalse(settings.diagnostics_enabled())
    self.assertEqual(key.read_bytes(), b"existing key")
    settings.set_diagnostics_enabled(True, offroad=True)
    self.assertTrue(settings.diagnostics_enabled())
