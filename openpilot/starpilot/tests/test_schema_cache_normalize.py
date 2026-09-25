import hashlib
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import runpy
import struct
import tempfile
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.starpilot import schema_cache as cache
from openpilot.starpilot import schema_cache_normalize as normalize
from openpilot.starpilot.state_migration import load_snapshot
from tools.diagnostics.normalize_event_caches import main as cli_main


class TestCacheNormalization(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)
    self.params = Params(str(self.root / 'params'))
    self.backup = self.root / 'backup'
    cache.prewarm_cache_contracts()

  @staticmethod
  def repack(header, payload):
    encoded = json.dumps(header, sort_keys=True, separators=(',', ':')).encode()
    return cache.MAGIC + struct.pack('>I', len(encoded)) + encoded + payload

  def populate(self, version=1):
    values = {
      'CalibrationParams': {'rpyCalib': [.1, -.2, .3], 'validBlocks': 12},
      'LiveParametersV2': {'steerRatio': 15.25, 'stiffnessFactor': .875, 'roll': -.015625},
      'LiveTorqueParameters': {'latAccelFactorFiltered': 2.5, 'frictionCoefficientFiltered': .125, 'totalBucketPoints': 64},
      'LiveDelay': {'lateralDelay': .25},
    }
    result = {}
    for index, key in enumerate(normalize.EVENT_KEYS):
      contract = cache.CONTRACTS[key]
      message = contract.root.new_message(logMonoTime=1234567890 + index, valid=bool(index % 2))
      assert contract.service is not None
      message.init(contract.service)
      setattr(message, contract.service, values[key])
      payload = message.to_bytes()
      raw = self.repack(cache._header(contract, key, payload, version=version), payload)
      self.params.put(key, raw, block=True)
      result[key] = raw
    return result

  def run_normalization(self):
    return normalize.normalize_current_event_caches(self.params, self.backup, producers_stopped=True)

  def test_current_v1_all_services_values_backup_and_carparams_preserved(self):
    originals = self.populate()
    car_params = {}
    for key, contract in cache.CONTRACTS.items():
      if contract.service is None:
        cache.put_cache(self.params, key, contract.root.new_message(carFingerprint='EXACT_ORIGINAL_CAR'), block=True)
        car_params[key] = self.params.get(key)
    staged = self.root / 'staged_normalizer.py'
    staged.write_bytes(Path(normalize.__file__).read_bytes())
    api = runpy.run_path(str(staged))
    report = api['normalize_current_event_caches'](self.params, self.backup, producers_stopped=True)
    self.assertEqual(report['normalizer']['path'], str(staged))
    self.assertEqual(report['status'], 'normalized')
    self.assertEqual(report['written'], list(normalize.EVENT_KEYS))
    self.assertEqual(load_snapshot(report['backup']), originals)
    self.assertEqual(json.loads((Path(report['backup']) / 'normalization.json').read_bytes()), report)
    for key, old in originals.items():
      updated = self.params.get(key)
      self.assertNotEqual(old, updated)
      self.assertEqual(normalize._header(updated)['version'], 2)
      old_payload, new_payload = cache.inspect_cache(key, old).payload, cache.inspect_cache(key, updated).payload
      with cache.CONTRACTS[key].root.from_bytes(old_payload) as before, cache.CONTRACTS[key].root.from_bytes(new_payload) as after:
        self.assertEqual(before.to_dict(), after.to_dict())
    for key, raw in car_params.items():
      self.assertEqual(self.params.get(key), raw)

  def test_v2_and_missing_values_unchanged_without_backup_or_writes(self):
    originals = self.populate(version=2)
    self.params.remove('LiveDelay')
    originals.pop('LiveDelay')
    before = {key: Path(self.params.get_param_path(key)).stat().st_ino for key in originals}
    with patch.object(normalize, '_atomic_write', side_effect=AssertionError('unnecessary write')):
      report = self.run_normalization()
    self.assertEqual(report['status'], 'unchanged')
    self.assertEqual(report['written'], [])
    self.assertEqual(report['caches']['LiveDelay']['action'], 'missing')
    self.assertFalse(self.backup.exists())
    for key, raw in originals.items():
      self.assertEqual(self.params.get(key), raw)
      self.assertEqual(Path(self.params.get_param_path(key)).stat().st_ino, before[key])

  def test_any_incompatible_schema_or_payload_rejects_entire_batch_before_backup(self):
    for damage in ('schema', 'payload'):
      with self.subTest(damage=damage):
        originals = self.populate()
        key = normalize.EVENT_KEYS[-1]
        old = originals[key]
        header = normalize._header(old)
        payload = cache.inspect_cache(key, old).payload
        if damage == 'schema':
          header['schema_sha256'] = '0' * 64
        else:
          payload = b'not capnp'
          header.update(payload_bytes=len(payload), payload_sha256=hashlib.sha256(payload).hexdigest())
        originals[key] = self.repack(header, payload)
        self.params.put(key, originals[key], block=True)
        with patch.object(normalize, '_atomic_write', side_effect=AssertionError('write before validation')):
          with self.assertRaises(normalize.NormalizationError):
            self.run_normalization()
        self.assertFalse(self.backup.exists())
        self.assertEqual({key: self.params.get(key) for key in originals}, originals)

  def test_old_v1_writer_cannot_claim_success(self):
    originals = self.populate()
    def old_writer(params, key, message, block=False):
      params.put(key, originals[key], block=block)
    with patch.object(cache, 'put_cache', side_effect=old_writer), self.assertRaises(normalize.NormalizationError):
      self.run_normalization()
    self.assertFalse(self.backup.exists())
    self.assertEqual({key: self.params.get(key) for key in originals}, originals)

  def test_typed_traversal_refuses_lazy_invalid_service_pointer(self):
    originals = self.populate()
    key = normalize.EVENT_KEYS[-1]
    original = cache.inspect_cache(key, originals[key])
    payload = bytearray(original.payload)
    data_words = cache.CONTRACTS[key].root.schema.node.struct.dataWordCount
    struct.pack_into('<Q', payload, 16 + data_words * 8, 0xffffffffffffffff)
    payload = bytes(payload)
    raw = self.repack(cache._header(cache.CONTRACTS[key], key, payload, version=1), payload)
    self.assertEqual(cache.inspect_cache(key, raw).status, 'valid')  # Envelope and union tag alone are insufficient.
    originals[key] = raw
    self.params.put(key, raw, block=True)
    with self.assertRaises(normalize.NormalizationError):
      self.run_normalization()
    self.assertEqual({key: self.params.get(key) for key in originals}, originals)
    self.assertFalse(self.backup.exists())

  def test_changed_source_after_backup_aborts_before_first_cache_write(self):
    originals = self.populate()
    real_snapshot = normalize._save_snapshot
    changed_key = normalize.EVENT_KEYS[-1]
    replacement = b'external replacement'
    def change_after_backup(values, storage):
      backup = real_snapshot(values, storage)
      Path(self.params.get_param_path(changed_key)).write_bytes(replacement)
      return backup
    with patch.object(normalize, '_save_snapshot', side_effect=change_after_backup):
      with self.assertRaises(normalize.NormalizationError):
        self.run_normalization()
    snapshots = list(self.backup.iterdir())
    self.assertEqual(len(snapshots), 1)
    self.assertEqual(load_snapshot(snapshots[0]), originals)
    report = json.loads((snapshots[0] / 'normalization.json').read_bytes())
    self.assertEqual(report['written'], [])
    self.assertEqual(report['status'], 'failed')
    for key, raw in originals.items():
      self.assertEqual(self.params.get(key), replacement if key == changed_key else raw)

  def test_write_readback_failure_retains_originals_and_reports_attempt(self):
    originals = self.populate()
    real_write = normalize._atomic_write
    changed_key = normalize.EVENT_KEYS[0]
    def damage_write(path, raw):
      real_write(path, raw)
      if path.name == changed_key:
        path.write_bytes(b'deliberate readback mismatch')
    with patch.object(normalize, '_atomic_write', side_effect=damage_write):
      with self.assertRaises(normalize.NormalizationError):
        self.run_normalization()
    backup = next(self.backup.iterdir())
    self.assertEqual(load_snapshot(backup), originals)
    report = json.loads((backup / 'normalization.json').read_bytes())
    self.assertEqual(report['status'], 'failed')
    self.assertEqual(report['attempted'], [changed_key])
    self.assertEqual(report['written'], [changed_key])
    for key in normalize.EVENT_KEYS[1:]:
      self.assertEqual(self.params.get(key), originals[key])

  def test_offline_precondition_and_backup_location_are_explicit(self):
    originals = self.populate()
    with self.assertRaises(normalize.NormalizationError):
      normalize.normalize_current_event_caches(self.params, self.backup)
    with self.assertRaises(ValueError):
      normalize.normalize_current_event_caches(self.params, self.root / 'params' / 'backup', producers_stopped=True)
    self.assertEqual({key: self.params.get(key) for key in originals}, originals)
    self.assertFalse(self.backup.exists())

  def test_cli_rejects_nonexistent_or_empty_params_root_without_creating_namespace(self):
    for exists in (False, True):
      path = self.root / ('empty' if exists else 'typo')
      if exists:
        path.mkdir()
      arguments = ['normalize', '--params-path', str(path), '--backup-dir', str(self.backup), '--producers-stopped']
      with patch('sys.argv', arguments), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
        cli_main()
      self.assertEqual(raised.exception.code, 2)
      self.assertEqual(path.exists(), exists)
      if exists:
        self.assertEqual(list(path.iterdir()), [])


if __name__ == '__main__':
  unittest.main()
