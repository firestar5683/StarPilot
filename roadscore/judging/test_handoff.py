import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from prepare import copy_with_reserve, digest, fetch_remote, normalize
from export_handoff import export_handoff


class HandoffTests(unittest.TestCase):
  def batch(self, root):
    rows = []
    for i, label in enumerate('ABCDEFGHIJK'):
      route = f'{i:016x}/2026-01-01--00-00-00'
      row = normalize({'route': route, 'start_s': 1572 if label == 'J' else 0,
                       'end_s': 2029 if label == 'J' else None})
      row.update(label=label, seed=i + 11, analysis_status='characterized', range_resolution='resolved by explicit decision')
      selected = list(range(26, 34)) if label == 'J' else [0]
      files = []
      for seg in sorted(set(selected) | {0}):
        for asset in ('rlog', 'fcamera.hevc'):
          p = root / 'cache' / label / f'{seg}' / asset
          p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'synthetic')
          files.append({'segment': seg, 'path': str(p.relative_to(root)), 'bytes': p.stat().st_size, 'sha256': digest(p)})
      row['cache'] = {'selected_segments': selected, 'extent_verified_against_remote_listing': True, 'files': files}
      rows.append(row)
    p = root / 'manifest.private.json'
    p.write_text(json.dumps({'configuration': {'profile': 'prism'}, 'routes': rows}))
    return p

  def test_export_preserves_full_route_excerpt_and_seeds_without_touching_source(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp); source = self.batch(root); original = source.read_bytes()
      out = root / 'export'
      result = export_handoff(source, out, materialize=True, reserve_gib=0)
      self.assertEqual(source.read_bytes(), original)
      self.assertFalse(result['generation_authorized'])
      self.assertTrue(all(r['preparation_ready'] for r in result['submissions']))
      self.assertEqual([r['seed'] for r in result['submissions']], list(range(11, 22)))
      self.assertEqual(result['submissions'][3]['start_seconds'], 0)
      excerpt = result['submissions'][9]
      self.assertEqual((excerpt['start_seconds'], excerpt['duration_seconds']), (1572, 457))
      self.assertEqual(len(list((out / 'routes').rglob('cache_manifest.json'))), 11)
      with self.assertRaises(ValueError):
        export_handoff(source, out)

  def test_incomplete_corrupt_and_plan_only_exports_cannot_be_ready(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp); source = self.batch(root)
      batch = json.loads(source.read_text())
      first = batch['routes'][0]['cache']['files'][0]
      (root / first['path']).write_bytes(b'corruption')
      batch['routes'][1]['analysis_status'] = 'incomplete'
      source.write_text(json.dumps(batch))
      result = export_handoff(source, root / 'plan')
      self.assertTrue(all(not r['preparation_ready'] for r in result['submissions']))
      result = export_handoff(source, root / 'copies', materialize=True, reserve_gib=0)
      for row in result['submissions'][:2]:
        cache = root / 'copies/routes' / row['route']
        self.assertFalse(row['preparation_ready'])
        self.assertTrue((cache / '.acquiring').exists())
        self.assertFalse((cache / 'cache_manifest.json').exists())

  def test_copy_reserve_preserves_destination_and_cleans_partial(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp); src = root / 'src'; dst = root / 'dst'
      src.write_bytes(b'new'); dst.write_bytes(b'old')
      with patch('prepare.shutil.disk_usage', side_effect=[SimpleNamespace(free=20), SimpleNamespace(free=0)]):
        with self.assertRaises(OSError):
          copy_with_reserve(src, dst, reserve_gib=0)
      self.assertEqual(dst.read_bytes(), b'old')
      self.assertFalse((root / 'dst.partial').exists())

  def test_failed_fetch_retains_unprocessed_inventory_for_next_retry(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp); manifest = self.batch(root)
      batch = json.loads(manifest.read_text()); batch['routes'] = batch['routes'][:1]
      row = batch['routes'][0]; old_paths = {f['path'] for f in row['cache']['files']}
      manifest.write_text(json.dumps(batch))
      class API:
        def __init__(self, *a, **kw): pass
        def get(self, *a, **kw): return {'rlogs': ['https://example.com/0/rlog.zst']}
      modules = {'openpilot.tools.lib.api': SimpleNamespace(APIError=RuntimeError, CommaApi=API, route_api_hosts=lambda: ['https://example.com']),
                 'openpilot.tools.lib.auth_config': SimpleNamespace(get_token=lambda host: None)}
      with patch.dict('sys.modules', modules), patch('requests.get', side_effect=OSError('synthetic network failure')):
        result = fetch_remote(manifest, logs_only=True, reserve_gib=0)
      self.assertEqual({f['path'] for f in result['routes'][0]['cache']['files']}, old_paths)
      self.assertEqual(result['routes'][0]['cache_status'], 'fetch_failed_needs_review')


if __name__ == '__main__':
  unittest.main()
