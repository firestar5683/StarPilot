import unittest
from unittest.mock import patch

from tools.ci import replay_fixture_cache as fixture_cache


class TestReplayFixtureCache(unittest.TestCase):
  def test_unreviewed_recording_rejected_before_schema_load(self):
    with patch.object(fixture_cache, 'URLFile') as download:
      with self.assertRaisesRegex(ValueError, 'no reviewed immutable recording'):
        fixture_cache.verified_fixture_params('unreviewed', b'input')
      download.assert_not_called()

  def test_modified_pinned_recording_rejected_before_schema_load(self):
    segment = next(iter(fixture_cache.FIXTURES))
    with patch.object(fixture_cache, 'URLFile') as download:
      with self.assertRaisesRegex(ValueError, 'no reviewed immutable recording'):
        fixture_cache.verified_fixture_params(segment, b'changed')
      download.assert_not_called()

  def test_target_schema_drift_requires_new_review(self):
    segment = next(iter(fixture_cache.FIXTURES))
    with patch.dict(fixture_cache.FIXTURES[segment], {'input_bytes': 5}), \
         patch.object(fixture_cache, '_digest', side_effect=[fixture_cache.FIXTURES[segment]['input_sha256'], 'changed']), \
         patch.object(fixture_cache, 'URLFile') as download:
      with self.assertRaisesRegex(ValueError, 'target schema changed'):
        fixture_cache.verified_fixture_params(segment, b'input')
      download.assert_not_called()

  def test_source_schema_drift_rejected_before_decoding(self):
    segment = next(iter(fixture_cache.FIXTURES))
    with patch.dict(fixture_cache.FIXTURES[segment], {'input_bytes': 5}), \
         patch.object(fixture_cache, '_digest', side_effect=[fixture_cache.FIXTURES[segment]['input_sha256'],
                                                           fixture_cache.TARGET_CAR_SHA256, 'changed']), \
         patch.object(fixture_cache, 'URLFile') as download, \
         patch.object(fixture_cache.capnp, 'SchemaParser') as parser:
      download.return_value.read.return_value = b'changed'
      with self.assertRaisesRegex(ValueError, 'producing schema digest mismatch'):
        fixture_cache.verified_fixture_params(segment, b'input')
      parser.assert_not_called()

  def test_modified_published_reference_rejected_before_cache_creation(self):
    segment = next(iter(fixture_cache.FIXTURES))
    schema_hashes = [entry[3] for entry in fixture_cache.SOURCE_FILES.values()]
    with patch.dict(fixture_cache.FIXTURES[segment], {'input_bytes': 5}), \
         patch.object(fixture_cache, '_digest', side_effect=[fixture_cache.FIXTURES[segment]['input_sha256'],
                                                           fixture_cache.TARGET_CAR_SHA256, *schema_hashes]), \
         patch.object(fixture_cache, 'URLFile') as download, \
         patch.object(fixture_cache.capnp, 'SchemaParser'), \
         patch.object(fixture_cache, 'put_cache') as writer:
      download.return_value.read.return_value = b'changed'
      with self.assertRaisesRegex(ValueError, 'reference digest mismatch'):
        fixture_cache.verified_fixture_params(segment, b'input')
      writer.assert_not_called()

