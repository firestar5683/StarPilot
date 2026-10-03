import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'state_migration.py'
spec = importlib.util.spec_from_file_location('isolated_state_migration', SOURCE)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class TestFirstStartMigration(unittest.TestCase):
  def setUp(self):
    self.temporary = tempfile.TemporaryDirectory()
    self.addCleanup(self.temporary.cleanup)
    self.root = Path(self.temporary.name)
    self.namespace = self.root / 'params' / 'd'
    self.namespace.mkdir(parents=True)
    self.storage = self.root / 'recovery'
    self.types = {'IsMetric': 'BOOL', 'ForceStops': 'BOOL', 'OpenpilotEnabledToggle': 'BOOL', 'SteerFriction': 'FLOAT',
                  'CalibrationParams': 'BYTES', 'CarParamsPersistent': 'BYTES', 'SecOCKey': 'BYTES'}
    self.params = SimpleNamespace(get_param_path=lambda: str(self.namespace), all_keys=lambda: list(self.types),
                                  get_type=lambda key: SimpleNamespace(name=self.types[key]))
    self.cache = SimpleNamespace(CACHE_KEYS={'CalibrationParams', 'CarParamsPersistent'},
                                 inspect_cache=lambda key, raw: SimpleNamespace(status='valid' if raw.startswith(b'envelope:') else 'legacy'))
    self.converter = SimpleNamespace(migrate_legacy_cache=lambda key, raw: b'envelope:' + raw if key == 'CalibrationParams' else None)
    self.addCleanup(patch.stopall)
    patch.dict('sys.modules', {'openpilot.starpilot.schema_cache': self.cache,
                              'openpilot.starpilot.legacy_cache_migration': self.converter}).start()

  def write(self, values):
    for key, value in values.items():
      (self.namespace / key).write_bytes(value)

  def values(self):
    return migration._read_namespace(self.namespace)

  def start(self, **kwargs):
    migration.prepare_manager_start(self.params, self.storage, auto_migrate=True, **kwargs)

  def test_migrate_preserves_known_bytes_and_calibration_before_qualifying(self):
    original = {'IsMetric': b'1', 'ForceStops': b'0', 'SteerFriction': b'0.123',
                'SecOCKey': b'private\x00bytes', 'CalibrationParams': b'legacy calibration',
                'CarParamsPersistent': b'old identity', 'OldDomSetting': b'9'}
    self.write(original)
    self.start()
    expected = {key: value for key, value in original.items() if key not in ('OldDomSetting', 'CarParamsPersistent')}
    expected['CalibrationParams'] = b'envelope:legacy calibration'
    self.assertEqual(self.values(), expected)
    snapshots = list((self.storage / 'snapshots').iterdir())
    self.assertEqual(len(snapshots), 1)
    self.assertEqual(migration.load_snapshot(snapshots[0]), original)
    receipt = json.loads((snapshots[0] / 'migration.json').read_bytes())
    self.assertEqual(receipt['status'], 'migrated')
    before = {str(path): path.read_bytes() for path in self.storage.rglob('*') if path.is_file()}
    self.start()
    self.assertEqual({str(path): path.read_bytes() for path in self.storage.rglob('*') if path.is_file()}, before)

  def test_invalid_bool_archived_valid_child_preserved(self):
    original = {'IsMetric': b'True', 'ForceStops': b'1', 'OpenpilotEnabledToggle': b'true'}
    self.write(original)
    self.start()
    self.assertEqual(self.values(), {'ForceStops': b'1', 'OpenpilotEnabledToggle': b'0'})
    self.assertEqual(migration.load_snapshot(next((self.storage / 'snapshots').iterdir())), original)

  def test_default_and_dry_run_remain_strict_without_mutation(self):
    self.write({'SteerFriction': b'0.2'})
    with self.assertRaises(migration.MigrationRequired):
      self.start(dry_run=True)
    self.assertFalse(self.storage.exists())
    with self.assertRaises(migration.MigrationRequired):
      migration.prepare_manager_start(self.params, self.storage)
    self.assertEqual(self.values(), {'SteerFriction': b'0.2'})

  def test_conversion_failure_preserves_all_bytes_and_does_not_qualify(self):
    original = {'CalibrationParams': b'bad calibration', 'OldDomSetting': b'1'}
    self.write(original)
    with patch.object(self.converter, 'migrate_legacy_cache', side_effect=ValueError('invalid calibration')):
      with self.assertRaises(ValueError):
        self.start()
    self.assertEqual(self.values(), original)
    self.assertEqual(list((self.storage / 'profiles').iterdir()), [])
    self.assertEqual(migration.load_snapshot(next((self.storage / 'snapshots').iterdir())), original)

  def test_partial_failure_snapshot_survives_retry_and_marker_is_last(self):
    original = {'CarParamsPersistent': b'old car', 'OldDomSetting': b'2', 'SecOCKey': b'credential'}
    self.write(original)
    actual_write = migration._atomic_write
    def fail_receipt(path, raw):
      if path.name == 'migration.json' and json.loads(raw).get('attempted') == ['CarParamsPersistent', 'OldDomSetting']:
        raise OSError('injected')
      return actual_write(path, raw)
    with patch.object(migration, '_atomic_write', side_effect=fail_receipt):
      with self.assertRaises((OSError, migration.MigrationRequired)):
        self.start()
    self.assertEqual(list((self.storage / 'profiles').iterdir()), [])
    self.assertIn(original, [migration.load_snapshot(path) for path in (self.storage / 'snapshots').iterdir()])
    self.start()
    self.assertEqual(self.values(), {'SecOCKey': b'credential'})
    self.assertIn(original, [migration.load_snapshot(path) for path in (self.storage / 'snapshots').iterdir()])

  def test_initialized_profile_corruption_still_rejected(self):
    self.start()
    self.write({'CarParamsPersistent': b'legacy corruption'})
    with self.assertRaises(migration.MigrationRequired):
      self.start()
    self.assertEqual(self.values(), {'CarParamsPersistent': b'legacy corruption'})

  def test_snapshot_failure_prevents_every_mutation(self):
    original = {'OldDomSetting': b'2', 'IsMetric': b'1'}
    self.write(original)
    with patch.object(migration, '_save_snapshot', side_effect=OSError('storage unavailable')):
      with self.assertRaises(OSError):
        self.start()
    self.assertEqual(self.values(), original)
    self.assertEqual(list((self.storage / 'profiles').iterdir()), [])

  def test_unqualified_converter_output_does_not_mutate(self):
    original = {'CalibrationParams': b'legacy calibration', 'OldDomSetting': b'2'}
    self.write(original)
    with patch.object(self.converter, 'migrate_legacy_cache', return_value=b'opaque'):
      with self.assertRaises(migration.MigrationRequired):
        self.start()
    self.assertEqual(self.values(), original)
    self.assertEqual(list((self.storage / 'profiles').iterdir()), [])


if __name__ == '__main__':
  unittest.main()
