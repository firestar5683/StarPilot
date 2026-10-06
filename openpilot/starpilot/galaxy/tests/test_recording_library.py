import os
import io
import tarfile
import http.client
import json
import threading
from pathlib import Path
import tempfile
import unittest

from openpilot.starpilot.galaxy.drive_history import DriveHistory
from openpilot.starpilot.galaxy.recording_library import RecordingLibrary
from openpilot.starpilot.galaxy.recording_media import RecordingMediaChanged

ROUTE = '00000042--abcdef1234'


class RecordingLibraryTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.segment = self.root / (ROUTE + '--0')
    self.segment.mkdir()
    (self.segment / 'rlog.zst').write_bytes(b'log')
    (self.segment / 'fcamera.hevc').write_bytes(b'camera')
    self.history = DriveHistory(self.root)
    self.library = RecordingLibrary(self.history)

  def test_metadata_rename_preserve_delete_and_legacy_names(self):
    (self.segment / 'Old_name').touch()
    self.assertEqual(self.library.describe(self.history.snapshot())['routes'][0]['displayName'], 'Old_name')
    self.library.action({'action': 'rename', 'routeId': ROUTE, 'name': 'Trip to the beach'}, permitted=lambda: True)
    self.library.action({'action': 'preserve', 'routeId': ROUTE, 'preserved': True}, permitted=lambda: True)
    route = self.library.describe(self.history.snapshot())['routes'][0]
    self.assertEqual(route['displayName'], 'Trip to the beach')
    self.assertTrue(route['preserved'])
    self.assertEqual(route['segments'][0]['logFiles'], ['rlog.zst'])
    self.assertEqual(os.getxattr(self.segment, 'user.preserve'), b'1')
    with self.assertRaises(ValueError):
      self.library.action({'action': 'delete', 'routeId': ROUTE, 'confirmed': False}, permitted=lambda: True)
    self.library.action({'action': 'delete', 'routeId': ROUTE, 'confirmed': True}, permitted=lambda: True)
    self.assertFalse(self.segment.exists())

  def test_authority_active_segment_and_late_lock_prevent_deletion(self):
    payload = {'action': 'delete', 'routeId': ROUTE, 'confirmed': True}
    with self.assertRaises(PermissionError):
      self.library.action(payload, permitted=lambda: False)
    active = self.root / (ROUTE + '--1')
    active.mkdir()
    (active / 'rlog.lock').touch()
    with self.assertRaises(ValueError):
      self.library.action(payload, permitted=lambda: True)
    self.assertTrue(self.segment.exists())
    (active / 'rlog.lock').unlink()
    active.rmdir()
    calls = 0
    def permitted():
      nonlocal calls
      calls += 1
      if calls == 2:
        (self.segment / 'rlog.lock').touch()
      return True
    with self.assertRaises(PermissionError):
      self.library.action(payload, permitted=permitted)
    self.assertTrue((self.segment / 'fcamera.hevc').exists())

  def test_bulk_delete_keeps_preserved_routes_unless_explicitly_included(self):
    self.library.action({'action': 'preserve', 'routeId': ROUTE, 'preserved': True}, permitted=lambda: True)
    other = self.root / '00000043--abcdef1234--0'
    other.mkdir()
    (other / 'fcamera.hevc').write_bytes(b'camera')
    result = self.library.action({'action': 'delete-all', 'confirmed': True, 'includePreserved': False}, permitted=lambda: True)
    self.assertEqual(result['deleted'], 1)
    self.assertTrue(self.segment.exists())
    self.assertFalse(other.exists())
    self.library.action({'action': 'delete-all', 'confirmed': True, 'includePreserved': True}, permitted=lambda: True)
    self.assertFalse(self.segment.exists())

  def test_log_archive_contents_and_changed_sources(self):
    lease = self.library.open_archive(ROUTE, permitted=lambda: True)
    try:
      with tarfile.open(fileobj=io.BytesIO(os.pread(lease.video_fd, lease.size, 0))) as archive:
        self.assertEqual(archive.getnames(), [ROUTE + '--0/rlog.zst'])
        self.assertEqual(archive.extractfile(archive.getnames()[0]).read(), b'log')
      self.assertTrue(lease.source.current())
      (self.segment / 'rlog.lock').touch()
      self.assertFalse(lease.source.current())
    finally:
      lease.close()
    (self.segment / 'rlog.lock').unlink()
    with self.assertRaises(RecordingMediaChanged):
      self.library.open_archive(ROUTE, permitted=lambda: False)
    with self.assertRaises(ValueError):
      self.library.open_archive('../escape', permitted=lambda: True)

  def test_authenticated_http_actions_inventory_and_original_downloads(self):
    from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
    from openpilot.starpilot.galaxy.server import make_server
    access = GalaxyAccessOwner(self.root / 'access')
    access.configure('password123', lambda: True)
    parked = True
    server = make_server(port=0, owner=access, recordings=self.history, parked=lambda: parked)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    def request(path, payload=None, cookie='', range_header=None):
      headers = {'Cookie': cookie}
      if payload is not None:
        headers.update({'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{server.server_port}'})
      if range_header:
        headers['Range'] = range_header
      connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
      try:
        connection.request('POST' if payload is not None else 'GET', path, json.dumps(payload) if payload is not None else None, headers)
        response = connection.getresponse()
        return response.status, response.read(), dict(response.getheaders())
      finally:
        connection.close()
    try:
      self.assertEqual(request('/api/recordings/action', {'action': 'delete', 'routeId': ROUTE, 'confirmed': True})[0], 401)
      _, _, headers = request('/api/auth/login', {'password': 'password123'})
      cookie = headers['Set-Cookie'].split(';', 1)[0]
      self.assertEqual(request('/api/recordings/action', {'action': 'rename', 'routeId': ROUTE, 'name': 'Vacation'}, cookie)[0], 200)
      status, body, _ = request('/api/recordings/local', cookie=cookie)
      self.assertEqual(status, 200)
      self.assertEqual(json.loads(body)['routes'][0]['displayName'], 'Vacation')
      self.assertEqual(request(f'/api/recordings/files/{ROUTE}--0/rlog.zst', cookie=cookie)[:2], (200, b'log'))
      status, body, _ = request(f'/api/recordings/logs/{ROUTE}', cookie=cookie)
      self.assertEqual(status, 200)
      with tarfile.open(fileobj=io.BytesIO(body)) as archive:
        self.assertEqual(archive.extractfile(ROUTE + '--0/rlog.zst').read(), b'log')
      parked = False
      self.assertEqual(request('/api/recordings/action', {'action': 'delete', 'routeId': ROUTE, 'confirmed': True}, cookie)[0], 409)
      self.assertTrue(self.segment.exists())
      self.assertEqual(request('/api/auth/logout', {}, cookie)[0], 200)
      self.assertEqual(request(f'/api/recordings/files/{ROUTE}--0/rlog.zst', cookie=cookie)[0], 401)
    finally:
      server.shutdown()
      thread.join(2)
      server.server_close()
