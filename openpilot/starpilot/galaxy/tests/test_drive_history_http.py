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
