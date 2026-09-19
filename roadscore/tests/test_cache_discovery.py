import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototype'))
from cache_discovery import manifest_source, prepared_source


class PreparedCacheTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.manifest = self.root / 'results' / 'batch' / 'manifest.private.json'
    self.manifest.parent.mkdir(parents=True)
    self.route = '0123456789abcdef/00000001--1234567890'
    self.source = self.manifest.parent / 'cache' / 'blind'
    files = []
    for segment in (0, 1):
      for name in ('rlog.zst', 'qcamera.ts'):
        path = self.source / (self.route.split('/')[1] + '--' + str(segment)) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'asset')
        files.append(dict(path=str(path.relative_to(self.manifest.parent)), bytes=5, segment=segment))
    self.entry = dict(route=self.route, selection=dict(start_s=0, end_s=None, segments=None),
                      cache=dict(remote_segments=[0, 1], selected_segments=[0, 1],
                                 extent_verified_against_remote_listing=True, files=files))

  def write(self):
    self.manifest.write_text(json.dumps(dict(routes=[self.entry])))

  def test_complete_qcamera_cache_discovered_without_label_or_seed_dependency(self):
    self.write()
    with patch('cache_discovery.preparation_roots', return_value=[self.root]):
      self.assertEqual(prepared_source(self.route, self.root), self.source)
    self.assertIsNone(manifest_source(self.manifest, 'another/route'))

  def test_excerpt_or_unverified_extent_never_substitutes_full_route(self):
    for changes in ({'start_s': 60}, {'end_s': 120}, {'segments': [0]}):
      with self.subTest(changes=changes):
        self.entry['selection'] = dict(start_s=0, end_s=None, segments=None)
        self.entry['selection'].update(changes)
        self.write()
        self.assertIsNone(manifest_source(self.manifest, self.route))
    self.entry['selection'] = dict(start_s=0, end_s=None, segments=None)
    self.entry['cache']['extent_verified_against_remote_listing'] = False
    self.write()
    self.assertIsNone(manifest_source(self.manifest, self.route))

  def test_missing_camera_truncated_asset_and_acquisition_rejected(self):
    self.write()
    path = self.manifest.parent / self.entry['cache']['files'][0]['path']
    path.write_bytes(b'x')
    self.assertIsNone(manifest_source(self.manifest, self.route))
    path.write_bytes(b'asset')
    (self.source / '.acquiring').touch()
    self.assertIsNone(manifest_source(self.manifest, self.route))
    (self.source / '.acquiring').unlink()
    self.entry['cache']['files'] = [f for f in self.entry['cache']['files'] if not f['path'].endswith('qcamera.ts')]
    self.write()
    self.assertIsNone(manifest_source(self.manifest, self.route))

  def test_partial_segment_set_and_malformed_manifest_rejected(self):
    self.entry['cache']['selected_segments'] = [0]
    self.write()
    self.assertIsNone(manifest_source(self.manifest, self.route))
    self.manifest.write_text('broken')
    self.assertIsNone(manifest_source(self.manifest, self.route))


if __name__ == '__main__':
  unittest.main()
