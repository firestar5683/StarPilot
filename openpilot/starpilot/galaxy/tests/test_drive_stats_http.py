import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server


class DriveStatsHTTPTest(unittest.TestCase):
  def test_local_access_exclusions_and_remote_auth(self):
    with tempfile.TemporaryDirectory() as tmp:
      calls = []
      closed = []
      class Statistics:
        def snapshot(self, timezone='UTC'):
          calls.append(('read', timezone))
          return {'schemaVersion': 1, 'recentDrives': [{'routeId': 'route', 'ignored': False}]}

        def ignore(self, route_id, ignored, *, authorized):
          if not authorized():
            raise PermissionError
          if route_id != 'route':
            raise ValueError
          calls.append((route_id, ignored))
          return {'schemaVersion': 1, 'recentDrives': [{'routeId': route_id, 'ignored': ignored}]}

        def close(self):
          closed.append(True)

      server = make_server(port=0, owner=GalaxyAccessOwner(Path(tmp)), drive_stats=Statistics())
      thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
      thread.start()
      cookie = ['']
      def request(path, payload=None, *, origin=None, remote=False):
        headers = {'Origin': origin or f'http://127.0.0.1:{server.server_port}', 'Content-Type': 'application/json'}
        if cookie[0]:
          headers['Cookie'] = cookie[0]
        if remote:
          headers['Forwarded'] = 'for=203.0.113.8'
        conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        try:
          conn.request('GET' if payload is None else 'POST', path, None if payload is None else json.dumps(payload), headers)
          response = conn.getresponse()
          if response.getheader('Set-Cookie'):
            cookie[0] = response.getheader('Set-Cookie').split(';', 1)[0]
          return response.status, json.loads(response.read())
        finally:
          conn.close()
      try:
        self.assertEqual(request('/api/auth/session')[0], 200)
        self.assertEqual(request('/api/drives/stats')[0], 200)
        self.assertEqual(request('/api/drives/stats?timezone=America%2FChicago')[0], 200)
        self.assertEqual(calls[-1], ('read', 'America/Chicago'))
        self.assertEqual(request('/api/drives/stats?timezone=UTC&timezone=UTC')[0], 400)
        self.assertEqual(request('/api/drives/stats?other=x')[0], 400)
        status, data = request('/api/drives/ignore', {'routeId': 'route', 'ignored': True})
        self.assertEqual(status, 200)
        self.assertTrue(data['recentDrives'][0]['ignored'])
        count = len(calls)
        self.assertEqual(request('/api/drives/ignore', {'routeId': 'route', 'ignored': False}, origin='https://example.net')[0], 403)
        self.assertEqual(request('/api/drives/ignore', {'routeId': 'route', 'ignored': 1})[0], 400)
        self.assertEqual(request('/api/drives/ignore', {'routeId': 'route', 'ignored': True, 'extra': True})[0], 400)
        self.assertEqual(request('/api/drives/stats', remote=True)[0], 503)
        self.assertEqual(len(calls), count)
        self.assertEqual(request('/api/drives/ignore', {'routeId': 'unknown', 'ignored': True})[0], 400)
      finally:
        server.shutdown()
        thread.join(2)
        server.server_close()
      self.assertEqual(closed, [True])

  def test_logout_during_snapshot_discards_private_result(self):
    with tempfile.TemporaryDirectory() as tmp:
      entered, release = threading.Event(), threading.Event()
      class Statistics:
        def snapshot(self):
          entered.set()
          release.wait(2)
          return {'privateRoute': 'must-not-escape'}

      access = GalaxyAccessOwner(Path(tmp))
      access.configure('password123', lambda: True)
      server = make_server(port=0, owner=access, drive_stats=Statistics())
      worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
      worker.start()
      def request(path, payload=None, cookie=None):
        headers = {'Forwarded': 'for=203.0.113.8', 'Origin': f'http://127.0.0.1:{server.server_port}',
                   'Content-Type': 'application/json'}
        if cookie:
          headers['Cookie'] = cookie
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        try:
          connection.request('GET' if payload is None else 'POST', path, None if payload is None else json.dumps(payload), headers)
          response = connection.getresponse()
          return response.status, response.read(), dict(response.getheaders())
        finally:
          connection.close()
      try:
        self.assertEqual(request('/api/drives/stats')[0], 401)
        self.assertFalse(entered.is_set())
        status, _, headers = request('/api/auth/login', {'password': 'password123'})
        self.assertEqual(status, 200)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        results = []
        pending = threading.Thread(target=lambda: results.append(request('/api/drives/stats', cookie=cookie)))
        pending.start()
        try:
          self.assertTrue(entered.wait(1))
          self.assertEqual(request('/api/auth/logout', {}, cookie)[0], 200)
        finally:
          release.set()
          pending.join(2)
        self.assertEqual(results[0][0], 401)
        self.assertNotIn(b'must-not-escape', results[0][1])
      finally:
        release.set()
        server.shutdown()
        worker.join(2)
        server.server_close()
