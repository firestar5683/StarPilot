"""Route inventory is visible only to a still-valid local Galaxy session."""

import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.drive_history import DriveHistory
from openpilot.starpilot.galaxy.server import make_server


class DriveHistoryHTTPTest(unittest.TestCase):
  def test_auth_before_scan_and_recheck_after_logout(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      segment = root / 'recordings/0000021e--371eaf116b--0'
      segment.mkdir(parents=True)
      (segment / 'qlog.zst').write_bytes(b'fixture')
      reader = DriveHistory(segment.parent)
      access = GalaxyAccessOwner(root / 'access')
      calls = []
      entered, release = threading.Event(), threading.Event()
      release.set()

      class PausedInventory:
        def snapshot(self):
          calls.append(True)
          result = reader.snapshot()
          entered.set()
          release.wait(2)
          return result

      server = make_server(port=0, owner=access, recordings=PausedInventory())
      worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
      worker.start()
      def request(path, *, cookie=None, payload=None):
        # Exercise the password-backed forwarded path.
        headers = {'Forwarded': 'for=203.0.113.8', **({'Cookie': cookie} if cookie else {})}
        if payload is not None:
          headers.update({'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{server.server_port}'})
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        try:
          connection.request('GET' if payload is None else 'POST', path,
                              None if payload is None else json.dumps(payload), headers)
          response = connection.getresponse()
          return response.status, response.read(), dict(response.getheaders())
        finally:
          connection.close()
      try:
        route = '/api/recordings/local'
        self.assertEqual(request(route)[0], 503)
        access.configure('password123', lambda: True)
        self.assertEqual(request(route)[0], 401)
        self.assertEqual(calls, [])
        status, _, headers = request('/api/auth/login', payload={'password': 'password123'})
        self.assertEqual(status, 200)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        status, body, headers = request(route, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['routes'][0]['routeId'], '0000021e--371eaf116b')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        release.clear()
        entered.clear()
        responses = []
        pending = threading.Thread(target=lambda: responses.append(request(route, cookie=cookie)))
        pending.start()
        try:
          self.assertTrue(entered.wait(1))
          self.assertEqual(request('/api/auth/logout', cookie=cookie, payload={})[0], 200)
        finally:
          release.set()
          pending.join(2)
        self.assertEqual(responses[0][0], 401)
        self.assertNotIn(b'371eaf116b', responses[0][1])
      finally:
        release.set()
        server.shutdown()
        worker.join(2)
        server.server_close()

  def test_delete_videos_requires_session_and_keeps_logs(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      segment = root / 'recordings/0000021e--371eaf116b--0'
      segment.mkdir(parents=True)
      for name in ('rlog.zst', 'qlog.zst', 'fcamera.hevc', 'qcamera.ts'):
        (segment / name).write_bytes(b'fixture')
      access = GalaxyAccessOwner(root / 'access')
      access.configure('password123', lambda: True)
      parked = [True]
      server = make_server(port=0, owner=access, recordings=DriveHistory(segment.parent), parked=lambda: parked[0])
      worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
      worker.start()
      def request(path, payload, cookie=None):
        headers = {'Forwarded': 'for=203.0.113.8', 'Content-Type': 'application/json',
                   'Origin': f'http://127.0.0.1:{server.server_port}', **({'Cookie': cookie} if cookie else {})}
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        try:
          connection.request('POST', path, json.dumps(payload), headers)
          response = connection.getresponse()
          return response.status, response.read(), dict(response.getheaders())
        finally:
          connection.close()
      try:
        route = '/api/recordings/delete-videos'
        self.assertEqual(request(route, {'segmentName': segment.name})[0], 401)
        self.assertTrue((segment / 'fcamera.hevc').exists())
        cookie = request('/api/auth/login', {'password': 'password123'})[2]['Set-Cookie'].split(';', 1)[0]
        self.assertEqual(request(route, {'segmentName': '../recordings'}, cookie)[0], 400)
        self.assertEqual(request(route, {'segmentName': segment.name, 'extra': 1}, cookie)[0], 400)
        self.assertEqual(request(route, {'segmentName': '0000021e--371eaf116b--7'}, cookie)[0], 404)
        parked[0] = False
        self.assertEqual(request(route, {'segmentName': segment.name}, cookie)[0], 409)
        self.assertTrue((segment / 'fcamera.hevc').exists())
        parked[0] = True
        status, body, _ = request(route, {'segmentName': segment.name}, cookie)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['deleted'], ['fcamera', 'qcamera'])
        self.assertEqual(sorted(p.name for p in segment.iterdir()), ['qlog.zst', 'rlog.zst'])
        (segment / 'rlog.lock').write_bytes(b'')
        self.assertEqual(request(route, {'segmentName': segment.name}, cookie)[0], 409)
      finally:
        server.shutdown()
        worker.join(2)
        server.server_close()
