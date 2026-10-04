"""Regression coverage for inferred overrides and source-bound editor actions."""
import json
from pathlib import Path
import tempfile
import unittest

from openpilot.starpilot.lateral.torque_runtime import read_settings
from openpilot.starpilot.lateral.torque_tuning import TorqueSource, TorqueTuning
from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, parse_document
from openpilot.starpilot.ui.torque_feature import TorqueFeature
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest


class SavedParams:
  def __init__(self, root):
    self.root = Path(root)
  def get_param_path(self, key):
    return str(self.root / key)
  def put(self, key, value, block=True):
    raw = json.dumps(value).encode() if isinstance(value, dict) else str(value).encode()
    (self.root / key).write_bytes(raw)
  def get(self, key):
    p = self.root / key
    return p.read_bytes() if p.exists() else None
  def put_bool(self, key, value, block=True):
    self.put(key, int(value))
  def remove(self, key):
    (self.root / key).unlink(missing_ok=True)


class Owner:
  def __init__(self, params):
    self.params = params
    self.capability = ('HYUNDAI_IONIQ_6', '', '', '', '', 3.0, 0.0, 0.1)
  def authority(self, group):
    return True
  def vehicle_fingerprint(self):
    return self.capability[0]
  def _capability(self, group):
    return self.capability
  def _raw(self, key):
    return self.params.get(key)
  def _readable(self, key):
    return True
  def _dependents(self, *keys):
    return tuple((key, self._raw(key)) for key in keys)


class TestInferredTorque(unittest.TestCase):
  def setUp(self):
    self.directory = tempfile.TemporaryDirectory()
    self.addCleanup(self.directory.cleanup)
    self.params = SavedParams(self.directory.name)
    self.vehicle = TorqueTuning(TorqueSource.VEHICLE, 'HYUNDAI_IONIQ_6', 3.0, 0.0, 0.1)
    self.owner = Owner(self.params)
    self.editor = TorqueFeature(self.owner)
  def rows(self):
    valid, rows = self.editor.rows(self.owner.capability, True)
    self.assertTrue(valid)
    return {row.key: row for row in rows}
  def request(self, key, value):
    row = self.rows()[key]
    return FeatureSettingsRequest(key, row.source, value, vehicle_fingerprint=self.owner.vehicle_fingerprint(),
                                  capability=row.capability, dependencies=row.dependencies)
  def test_saved_deviations_apply_without_boolean(self):
    self.params.put('SteerLatAccel', 3.2)
    self.params.put('SteerFriction', 0.15)
    for retired in (None, '0', '1', 'malformed'):
      if retired is not None:
        self.params.put('AdvancedLateralTune', retired)
      settings = read_settings(self.params, self.vehicle)
      self.assertTrue(settings.valid)
      self.assertEqual((settings.user_factor, settings.user_friction), (3.2, 0.15))
  def test_supplied_and_tracked_values_are_not_overrides(self):
    self.params.put('SteerLatAccel', 3.0)
    self.params.put('SteerFriction', 0.12)
    self.params.put('SteerFrictionStock', 0.12)
    settings = read_settings(self.params, self.vehicle)
    self.assertTrue(settings.valid)
    self.assertEqual((settings.user_factor, settings.user_friction), (None, None))
  def test_direct_edit_preserves_other_legacy_value_and_controller(self):
    self.params.put('SteerFriction', 0.15)
    self.params.put('LateralControllerSelection', 'independent')
    self.assertTrue(self.editor.apply(self.request('torque:factor:value', '3.2')))
    settings = read_settings(self.params, self.vehicle)
    self.assertEqual((settings.user_factor, settings.user_friction), (3.2, 0.15))
    self.assertEqual(self.params.get('LateralControllerSelection'), b'independent')
    self.assertTrue(self.editor.apply(self.request('torque:factor:reset', 'Reset')))
    settings = read_settings(self.params, self.vehicle)
    self.assertEqual((settings.user_factor, settings.user_friction), (None, 0.15))
    self.assertEqual(self.params.get('LateralControllerSelection'), b'independent')
  def test_default_edit_releases_override_and_stale_edit_rejected(self):
    stale = self.request('torque:factor:value', '3.3')
    self.assertTrue(self.editor.apply(self.request('torque:factor:value', '3.2')))
    self.assertFalse(self.editor.apply(stale))
    self.assertTrue(self.editor.apply(self.request('torque:factor:value', '3.0')))
    self.assertIsNone(read_settings(self.params, self.vehicle).user_factor)
    profile = parse_document(self.params.get(DOCUMENT_KEY))['HYUNDAI_IONIQ_6']
    self.assertEqual(profile.factor.mode, 'source')
  def test_invalid_values_fail_closed_without_erasure(self):
    self.params.put('SteerLatAccel', 'nan')
    self.assertFalse(read_settings(self.params, self.vehicle).valid)
    self.assertEqual(self.params.get('SteerLatAccel'), b'nan')


if __name__ == '__main__':
  unittest.main()
