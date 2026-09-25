"""Map GET results belong to the same authenticated request generation."""

import http.client
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.map_operations import MapOperationError
from openpilot.starpilot.galaxy.server import make_server


class MapOperationsHTTPTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.access = GalaxyAccessOwner(Path(self.temp.name))
    self.access.configure('test-password-123', lambda: True)
    self.operations = SimpleNamespace(request=lambda _operation: {'fixture': 'map-read'})
    self.maps = SimpleNamespace(snapshot=lambda: {'fixture': 'status-read'})
    self.server = make_server(port=0, owner=self.access, parked=lambda: True, map_operations=self.operations, maps=self.maps)
    self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
    self.thread.start()
    self.cookie = ''

  def tearDown(self):
    self.server.shutdown()
    self.thread.join(2)
    self.server.server_close()
    self.temp.cleanup()

  def request(self, path, method='GET', payload=None):
    headers = {
      'Origin': f'http://127.0.0.1:{self.server.server_port}',
      'Forwarded': 'for=203.0.113.8',
      'Content-Type': 'application/json',
      'Cookie': self.cookie,
    }
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=4)
    try:
      connection.request(method, path, None if payload is None else json.dumps(payload), headers)
      response = connection.getresponse()
      cookie = response.getheader('Set-Cookie')
      return response.status, json.loads(response.read()), cookie.split(';')[0] if cookie else ''
    finally:
      connection.close()

  def login(self):
    status, _, self.cookie = self.request('/api/auth/login', 'POST', {'password': 'test-password-123'})
    self.assertEqual(status, 200)

  def test_map_get_success_and_errors_require_same_session(self):
    paths = ['/api/maps/status', '/api/maps/catalog', '/api/maps/operation', '/api/maps/setup']
    for path in paths:
      with self.subTest(path=path):
        self.login()
        self.assertEqual(self.request(path)[0], 200)
        entered, release = threading.Event(), threading.Event()

        def waiting(_operation=None, *, entered=entered, release=release):
          entered.set()
          release.wait(2)
          return {'private': 'old-session-output'}

        original = self.maps.snapshot if path.endswith('/status') else self.operations.request
        if path.endswith('/status'):
          self.maps.snapshot = waiting
        else:
          self.operations.request = waiting
        responses = []
        thread = threading.Thread(target=lambda path=path, responses=responses: responses.append(self.request(path)))
        thread.start()
        self.assertTrue(entered.wait(2))
        self.assertEqual(self.request('/api/auth/logout', 'POST', {})[0], 200)
        self.login()  # A new valid session cannot inherit the in-flight response.
        release.set()
        thread.join(3)
        self.assertEqual(responses[0][0], 401)
        self.assertNotIn('old-session-output', json.dumps(responses))
        if path.endswith('/status'):
          self.maps.snapshot = original
        else:
          self.operations.request = original

  def test_map_error_response_discards_revoked_generation(self):
    self.login()
    entered, release = threading.Event(), threading.Event()

    def waiting(_operation):
      entered.set()
      release.wait(2)
      raise MapOperationError(503, 'package_unavailable')

    self.operations.request = waiting
    responses = []
    thread = threading.Thread(target=lambda: responses.append(self.request('/api/maps/setup')))
    thread.start()
    self.assertTrue(entered.wait(2))
    self.assertEqual(self.request('/api/auth/logout', 'POST', {})[0], 200)
    self.login()
    release.set()
    thread.join(3)
    self.assertEqual(responses[0][0], 401)
    self.assertNotIn('package_unavailable', json.dumps(responses))
    self.operations.request = lambda _operation: (_ for _ in ()).throw(MapOperationError(503, 'package_unavailable'))
    self.assertEqual(self.request('/api/maps/setup')[0:2], (503, {'error': 'Map management is unavailable', 'code': 'package_unavailable'}))
