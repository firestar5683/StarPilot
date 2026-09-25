import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.ci import run_recorded_vehicle_tests as recorded


class RecordedVehicleRunnerTests(unittest.TestCase):
  def test_manifest_pins_stock_and_debug_only_alpha_long(self):
    fixtures = recorded.load_fixtures()
    self.assertEqual({f['id'] for f in fixtures}, {'model_y_stock', 'model_y_alpha_long'})
    self.assertEqual([f['id'] for f in fixtures if 'release' in f['variants']], ['model_y_stock'])
    self.assertEqual({f['safety_model'] for f in fixtures}, {'tesla'})
    self.assertTrue(all(f['pcm_cruise'] for f in fixtures))

  def test_malformed_or_weakened_manifest_fails(self):
    original = {'schema_version': 1, 'fixtures': recorded.load_fixtures()}
    mutations = (
      lambda d: d['fixtures'][1].update(id=d['fixtures'][0]['id']),
      lambda d: d['fixtures'][1].update(variants=['debug', 'debug']),
      lambda d: d['fixtures'][0].update(pcm_cruise=1),
      lambda d: d['fixtures'][0].update(safety_model='other'),
      lambda d: d['fixtures'][0].update(bytes=True),
    )
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'fixtures.json'
      for mutation in mutations:
        document = copy.deepcopy(original)
        mutation(document)
        path.write_text(json.dumps(document))
        with self.assertRaises(ValueError):
          recorded.load_fixtures(path)

  def test_offline_fixture_must_be_exact_regular_file(self):
    data = b'public-recorded-fixture'
    fixture = {'id': 'fixture', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    with tempfile.TemporaryDirectory() as directory:
      cache = Path(directory)
      with self.assertRaises(FileNotFoundError):
        recorded.get_fixture(fixture, cache, download=False)
      path = cache / (fixture['sha256'] + '.zst')
      path.write_bytes(data)
      self.assertEqual(recorded.get_fixture(fixture, cache, download=False), path)
      path.write_bytes(data + b'!')
      with self.assertRaises(ValueError):
        recorded.verify_fixture(path, fixture)
      path.unlink()
      other = cache / 'other'
      other.write_bytes(data)
      path.symlink_to(other)
      with self.assertRaises(OSError):
        recorded.verify_fixture(path, fixture)

  def test_no_skip_error_or_missing_case_can_pass(self):
    ids = ['a', 'b']
    self.assertEqual(recorded.execution_errors(ids, [{'id': 'a', 'status': 'passed'}, {'id': 'b', 'status': 'passed'}]), [])
    for status in ('skipped', 'error', 'failed'):
      self.assertEqual(len(recorded.execution_errors(ids, [{'id': 'a', 'status': 'passed'}, {'id': 'b', 'status': status}])), 1)
    self.assertEqual(len(recorded.execution_errors(ids, [{'id': 'a', 'status': 'passed'}])), 1)


if __name__ == '__main__':
  unittest.main()
