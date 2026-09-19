import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from prepare import cache_local, normalize, normalize_all, prepare, selected_segments, fetch_remote
from analyze import summarize

ROUTE = '0000000000000000/2026-01-01--00-00-00'


class PreparationTests(unittest.TestCase):
  def test_normalization_and_duplicate_provenance(self):
    result = normalize_all([ROUTE, ROUTE.replace('/', '|'), 'https://connect.comma.ai/' + ROUTE + '/'])
    self.assertEqual(len(result['routes']), 1)
    self.assertEqual(len(result['duplicates']), 2)
    self.assertEqual(result['errors'], [])

  def test_segment_semantics(self):
    self.assertEqual(normalize(ROUTE + '--3')['selection']['segments'], [3])
    self.assertEqual(normalize(ROUTE + '/3:5')['selection']['segments'], [3, 4])
    for suffix in ('/3-5', '/3:', '/5:3', '?t=3', '/-1'):
      with self.assertRaises(ValueError):
        normalize('https://connect.comma.ai/' + ROUTE + suffix)
    with self.assertRaises(ValueError):
      normalize({'route': ROUTE + '--3', 'segments': [4]})
    with self.assertRaises(ValueError):
      normalize({'route': ROUTE, 'start_s': float('nan')})

  def test_connect_seconds_are_not_segment_numbers(self):
    item = normalize('https://connect.comma.ai/' + ROUTE + '/60')
    self.assertEqual(item['selection']['start_s'], 60)
    self.assertIsNone(item['selection']['segments'])
    self.assertIn('pending', item['range_resolution'])
    item = normalize('https://connect.comma.ai/' + ROUTE + '/1572/2029')
    self.assertEqual(item['selection']['end_s'] - item['selection']['start_s'], 457)
    self.assertEqual(selected_segments(item, range(41)), list(range(26, 34)))

  def test_ranges_are_distinct_not_silently_merged(self):
    report = normalize_all([ROUTE, ROUTE + '/2', ROUTE + '/3'])
    self.assertEqual(len(report['routes']), 3)
    self.assertEqual(len(report['same_route_different_selection']), 3)
    row = normalize({'route': ROUTE, 'start_s': 60, 'end_s': 120})
    self.assertEqual(selected_segments(row, [0, 1, 2]), [1])

  def test_frozen_mapping_and_blind_boundary(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      source = root / 'input.json'
      source.write_text(json.dumps([f'{i:016x}/2026-01-01--00-00-00' for i in range(11)]))
      output = root / 'batch'
      result = prepare(source, output)
      self.assertEqual([x['label'] for x in result['routes']], list('ABCDEFGHIJK'))
      self.assertFalse(result['generation_authorized'])
      with self.assertRaises(ValueError):
        prepare(source, output)
      for f in (output / 'blind').iterdir():
        self.assertNotIn('2026-01-01', f.read_text())
        self.assertNotIn('submitter', f.read_text())

  def test_wrong_count_and_invalid_input_block_mapping(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp); source = root / 'input.json'
      source.write_text(json.dumps([ROUTE, 'invalid']))
      with self.assertRaises(ValueError):
        prepare(source, root / 'batch')
      self.assertFalse((root / 'batch/blind_mapping.private.json').exists())
      self.assertTrue((root / 'batch/normalization.private.json').exists())

  def test_cache_gap_and_corruption(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp); sources = root / 'sources'; manifest = root / 'manifest.private.json'
      for segment in [0, 2]:
        folder = sources / (ROUTE.split('/')[1] + '--' + str(segment)); folder.mkdir(parents=True)
        (folder / 'rlog').write_bytes(b'original log')
        (folder / 'fcamera.hevc').write_bytes(b'original video')
      row = normalize(ROUTE); row['label'] = 'A'
      manifest.write_text(json.dumps({'routes': [row]}))
      cached = cache_local(manifest, [sources])['routes'][0]
      self.assertEqual(cached['cache_status'], 'incomplete')
      self.assertEqual(cached['cache']['selected_segments'], [0, 1, 2])
      target = root / cached['cache']['files'][0]['path']; target.write_bytes(b'corrupt')
      cache_local(manifest, [sources])
      self.assertEqual(target.read_bytes(), b'original log')

  def test_fetch_preserves_clock_reference_and_resumes_without_download(self):
    class Response:
      def __enter__(self): return self
      def __exit__(self, *args): pass
      def raise_for_status(self): pass
      def iter_content(self, size): return iter([b'original route log'])
    listing = {'rlogs': [f'https://example.com/route/{n}/rlog.zst' for n in range(3)]}
    class API:
      def __init__(self, *args, **kwargs): pass
      def get(self, *args, **kwargs): return listing
    with tempfile.TemporaryDirectory() as tmp:
      manifest = Path(tmp) / 'manifest.private.json'
      row = normalize({'route': ROUTE, 'start_s': 120, 'end_s': 180}); row['label'] = 'A'
      manifest.write_text(json.dumps({'routes': [row]}))
      modules = {'openpilot.tools.lib.api': SimpleNamespace(APIError=RuntimeError, CommaApi=API, route_api_hosts=lambda: ['https://api.example.com']),
                 'openpilot.tools.lib.auth_config': SimpleNamespace(get_token=lambda host: None)}
      with patch.dict('sys.modules', modules), patch('requests.get', return_value=Response()) as get:
        result = fetch_remote(manifest, logs_only=True, reserve_gib=0)['routes'][0]
        self.assertEqual(get.call_count, 2)
        self.assertEqual(result['cache']['selected_segments'], [2])
        self.assertTrue(result['cache']['files'][0]['clock_reference_only'])
        self.assertEqual(result['cache_status'], 'incomplete')  # no video, never a replay pass
        fetch_remote(manifest, logs_only=True, reserve_gib=0)
        self.assertEqual(get.call_count, 2)

  def test_technical_analysis_does_not_count_invalid_or_future_data(self):
    events = [(0, 'carState', True, {'vEgo': 1}), (1_000_000_000, 'modelV2', False, {}),
              (2_000_000_000, 'carState', True, {'vEgo': 5}), (3_000_000_000, 'carState', True, {'vEgo': 100})]
    result = summarize(events, end_s=3)
    self.assertEqual(result['speed_m_s']['max'], 5)
    self.assertFalse(result['required_valid_messages_present'])


if __name__ == '__main__':
  unittest.main()
