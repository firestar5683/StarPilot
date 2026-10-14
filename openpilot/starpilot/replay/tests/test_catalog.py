"""Disposable route trees; no log decoding, driving services, or network access."""

import fcntl
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from openpilot.starpilot.galaxy.drive_history import DriveHistory, SegmentInUse
from openpilot.starpilot.galaxy.recording_library import RecordingLibrary
from openpilot.starpilot.replay import catalog
from openpilot.starpilot.replay.catalog import CatalogError, ReplayCatalog

ROUTE = '00000042--abcdef1234'


class ReplayCatalogTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.catalog = ReplayCatalog(self.root)

  def segment(self, number=0, *files, route=ROUTE):
    path = self.root / f'{route}--{number}'
    path.mkdir()
    for name in files or ('rlog.zst', 'fcamera.hevc'):
      (path / name).write_bytes(b'fixture')
    return path

  def test_summary_preserves_labels_and_never_invents_timing_or_decode_success(self):
    segment = self.segment()
    (segment / 'Beach trip').touch()
    result = self.catalog.catalog()
    self.assertEqual(result['schemaVersion'], 1)
    self.assertFalse(result['scanIncomplete'])
    route = result['routes'][0]
    self.assertEqual((route['availability'], route['playable'], route['displayName']), ('ready', True, 'Beach trip'))
    self.assertNotIn('segments', route)
    self.assertIsNone(route['startTime'])
    self.assertIsNone(route['endTime'])
    detail = self.catalog.detail(ROUTE)
    self.assertEqual(detail['segments'][0]['sourceFiles'], ['fcamera.hevc', 'rlog.zst'])
    self.assertIsNone(detail['segments'][0]['endTime'])
    # Deliberately non-decodable bytes are an inventory result, not a decoder assertion.
    with self.catalog.lease(ROUTE) as lease:
      self.assertTrue(lease.current())

  def test_reduced_logs_camera_intervals_and_gaps_are_explicit(self):
    self.segment(0, 'qlog.bz2', 'qcamera.ts')
    self.segment(2, 'rlog.zst')
    route = self.catalog.detail(ROUTE)
    self.assertTrue(route['playable'])
    self.assertEqual(route['availability'], 'limited')
    self.assertEqual(len(route['warnings']), 4)
    self.assertEqual([segment['number'] for segment in route['segments']], [0, 2])

  def test_logs_without_road_footage_are_unavailable(self):
    self.segment(0, 'rlog.zst', 'dcamera.hevc')
    self.assertFalse(self.catalog.detail(ROUTE)['playable'])
    with self.assertRaises(CatalogError) as error:
      self.catalog.lease(ROUTE)
    self.assertEqual(error.exception.code, 'route_unavailable')

  def test_locked_tail_is_found_even_when_ordinary_history_omits_it(self):
    self.segment()
    tail = self.segment(1, 'rlog.lock')
    self.assertEqual(DriveHistory(self.root).snapshot()['routes'][0]['segmentCount'], 1)
    route = self.catalog.detail(ROUTE)
    self.assertFalse(route['playable'])
    self.assertEqual(route['reasonCode'], 'in_progress')
    self.assertEqual(route['segmentCount'], 2)
    with self.assertRaises(CatalogError) as error:
      self.catalog.lease(ROUTE)
    self.assertEqual(error.exception.code, 'in_progress')
    self.assertTrue((tail / 'rlog.lock').exists())

  def test_empty_tail_cannot_be_assumed_closed(self):
    self.segment()
    (self.root / (ROUTE + '--1')).mkdir()
    self.assertFalse(self.catalog.detail(ROUTE)['playable'])
    with self.assertRaises(CatalogError):
      self.catalog.lease(ROUTE)

  def test_long_selected_route_and_unrelated_inventory_limits(self):
    for number in range(65):
      self.segment(number)
    self.assertTrue(DriveHistory(self.root).snapshot()['scanIncomplete'])
    self.assertEqual(self.catalog.detail(ROUTE)['segmentCount'], 65)
    with self.catalog.lease(ROUTE) as lease:
      self.assertTrue(lease.current())
    (self.root / '00000041--abcdef1234--0').symlink_to(self.root, target_is_directory=True)
    self.assertTrue(self.catalog.detail(ROUTE)['playable'])
    with patch.object(catalog, 'MAX_ROOT_ENTRIES', 2):
      with self.assertRaises(CatalogError) as error:
        self.catalog.detail(ROUTE)
      self.assertEqual(error.exception.code, 'scan_incomplete')

  def test_catalog_budget_does_not_block_selected_detail(self):
    self.segment()
    self.segment(route='00000043--abcdef1234')
    with patch.object(catalog, 'MAX_CATALOG_SEGMENTS', 1):
      result = self.catalog.catalog()
    self.assertTrue(result['scanIncomplete'])
    self.assertEqual(len(result['routes']), 2)
    self.assertEqual(result['routes'][1]['reasonCode'], 'scan_incomplete')
    self.assertTrue(self.catalog.detail('00000043--abcdef1234')['playable'])

  def test_optional_fifo_metadata_does_not_block_or_invent_provider(self):
    segment = self.segment()
    os.mkfifo(segment / '.cloud-provider')
    route = self.catalog.detail(ROUTE)
    self.assertTrue(route['playable'])
    self.assertIsNone(route['provider'])

  def test_maximum_detail_fits_owner_response_bound(self):
    for number in range(512):
      self.segment(number, *catalog.FILES)
    detail = self.catalog.detail(ROUTE)
    raw = json.dumps({'ok': True, 'result': detail}, separators=(',', ':')).encode()
    self.assertLess(len(raw), 262144)

  def test_exact_names_reject_duplicates_malformed_suffixes_and_path_inputs(self):
    downloaded = '0123456789abcdef_' + ROUTE
    self.segment(route=downloaded)
    route_id = downloaded.replace('_', '|')
    self.assertTrue(self.catalog.detail(route_id)['playable'])
    self.segment(route=route_id)
    self.assertFalse(self.catalog.detail(route_id)['playable'])
    self.segment()
    self.segment('not-a-segment')
    self.assertFalse(self.catalog.detail(ROUTE)['playable'])
    for invalid in (None, True, '../' + ROUTE, ROUTE + '/x', ROUTE + '--0', ROUTE + '\n'):
      with self.assertRaises(CatalogError) as error:
        self.catalog.detail(invalid)
      self.assertEqual(error.exception.code, 'invalid_route')

  def test_symlink_empty_nonregular_sources_and_replaced_root_are_rejected(self):
    segment = self.segment()
    source = segment / 'rlog.zst'
    source.write_bytes(b'')
    self.assertFalse(self.catalog.detail(ROUTE)['playable'])
    source.unlink()
    source.symlink_to(segment / 'fcamera.hevc')
    self.assertFalse(self.catalog.detail(ROUTE)['playable'])
    source.unlink()
    os.mkfifo(source)
    self.assertFalse(self.catalog.detail(ROUTE)['playable'])
    link = self.root / 'root-link'
    link.symlink_to(self.root, target_is_directory=True)
    with self.assertRaises(CatalogError):
      ReplayCatalog(link).catalog()

  def test_lease_detects_file_replacement_late_tail_and_directory_replacement(self):
    segment = self.segment()
    with self.catalog.lease(ROUTE) as lease:
      old = segment / 'rlog.zst'
      old.rename(segment / 'old-log')
      old.write_bytes(b'fixture')
      self.assertFalse(lease.current())
    with self.catalog.lease(ROUTE) as lease:
      tail = self.segment(1, 'rlog.lock')
      self.assertFalse(lease.current())
    (tail / 'rlog.lock').unlink()
    tail.rmdir()
    with self.catalog.lease(ROUTE) as lease:
      segment.rename(self.root / 'moved')
      self.segment()
      self.assertFalse(lease.current())
    self.assertFalse(lease.current())
    lease.close()

  def test_upload_status_metadata_keeps_lease_but_content_append_revokes_it(self):
    segment = self.segment()
    source = segment / 'rlog.zst'
    with self.catalog.lease(ROUTE) as lease:
      before = source.stat()
      os.setxattr(source, 'user.upload', b'1')
      self.assertNotEqual(source.stat().st_ctime_ns, before.st_ctime_ns)
      self.assertTrue(lease.current())
      os.setxattr(source, 'user.upload', b'0')
      self.assertTrue(lease.current())
      os.removexattr(source, 'user.upload')
      self.assertTrue(lease.current())
      with source.open('ab') as stream:
        stream.write(b'changed')
      self.assertFalse(lease.current())

  def test_shared_lease_conflicts_with_exclusive_delete_and_releases_without_sentinels(self):
    segment = self.segment()
    fd = os.open(segment, catalog.DIR_FLAGS)
    self.addCleanup(os.close, fd)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with self.assertRaises(CatalogError) as error:
      self.catalog.lease(ROUTE)
    self.assertEqual(error.exception.code, 'source_busy')
    fcntl.flock(fd, fcntl.LOCK_UN)
    with self.catalog.lease(ROUTE) as first, self.catalog.lease(ROUTE) as second:
      self.assertTrue(first.current() and second.current())
      with self.assertRaises(SegmentInUse):
        DriveHistory(self.root).delete_videos(segment.name)
      self.assertFalse(any(name.endswith('.lock') for name in os.listdir(segment)))
    self.assertEqual(DriveHistory(self.root).delete_videos(segment.name)['deleted'], ['fcamera'])

  def test_galaxy_route_delete_acquires_all_locks_before_deleting_any_segment(self):
    first = self.segment()
    second = self.segment(1)
    fd = os.open(second, catalog.DIR_FLAGS)
    self.addCleanup(os.close, fd)
    fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    payload = {'action': 'delete', 'routeId': ROUTE, 'confirmed': True}
    library = RecordingLibrary(DriveHistory(self.root))
    with self.assertRaisesRegex(ValueError, 'replayed'):
      library.action(payload, permitted=lambda: True)
    self.assertTrue(first.exists() and second.exists())
    fcntl.flock(fd, fcntl.LOCK_UN)
    library.action(payload, permitted=lambda: True)
    self.assertFalse(first.exists() or second.exists())

  def test_logger_deleter_skips_replay_leases_then_reclaims_after_release(self):
    # Load the actual deleter without importing the uploader's native messaging runtime.
    uploader = ModuleType('openpilot.system.loggerd.uploader')
    uploader.get_directory_sort = lambda value: value
    uploader.listdir_by_creation = lambda root: sorted(os.listdir(root))
    path = Path(__file__).resolve().parents[3] / 'system/loggerd/deleter.py'
    spec = importlib.util.spec_from_file_location('replay_fixture_deleter', path)
    assert spec is not None and spec.loader is not None
    deleter = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'openpilot.system.loggerd.uploader': uploader}):
      spec.loader.exec_module(deleter)
    segment = self.segment()
    with patch.object(deleter.Paths, 'log_root', return_value=str(self.root)), \
         patch.object(deleter, 'get_available_bytes', return_value=0), \
         patch.object(deleter, 'get_available_percent', return_value=0):
      with self.catalog.lease(ROUTE):
        self.assertEqual(deleter.deleter_step(), (True, None))
        self.assertTrue(segment.exists())
      self.assertEqual(deleter.deleter_step(), (True, str(segment)))
      self.assertFalse(segment.exists())


if __name__ == '__main__':
  unittest.main()
