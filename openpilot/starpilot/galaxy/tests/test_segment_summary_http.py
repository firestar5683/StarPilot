"""Authenticated local summary HTTP, including revocation during decode."""

import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.drive_history import DriveHistory
from openpilot.starpilot.galaxy.segment_summary import SegmentSummary
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.galaxy.tests.test_segment_summary import NAME, car, control, write


class SegmentSummaryHttpTest(unittest.TestCase):
  def test_authenticated_real_serialized_summary_and_bad_selection(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      recordings = root / 'recordings'
      recordings.mkdir()
      write(recordings, [car(1_000_000_000, 10), control(1_000_000_000, True, False),
                         car(2_000_000_000, 10), control(2_000_000_000, False, True)])
      access = GalaxyAccessOwner(root / 'access')
      access.configure('password123', lambda: True)
      server = make_server(port=0, owner=access, recordings=DriveHistory(recordings))
      worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
      worker.start()

      def request(method, path, cookie=''):
        conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        headers = {'Cookie': cookie} if cookie else {}
        if method == 'POST':
          headers.update({'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{server.server_port}'})
        try:
          payload = {'password': 'password123'} if path.endswith('/login') else {}
          conn.request(method, path, json.dumps(payload) if method == 'POST' else None, headers)
          response = conn.getresponse()
          return response.status, response.read(), dict(response.getheaders())
        finally:
          conn.close()

      path = f'/api/recordings/segment-summary?segmentName={NAME}'
      try:
        self.assertEqual(request('GET', path)[0], 401)
        _, _, headers = request('POST', '/api/auth/login')
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        status, body, _ = request('GET', path, cookie)
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual(result['estimatedDistanceMeters'], 10)
        self.assertEqual(result['observedLatActiveSeconds'], 1)
        self.assertEqual(result['observedLongActiveSeconds'], 0)
        self.assertEqual(request('GET', path + '&other=x', cookie)[0], 400)
        self.assertEqual(request('GET', '/api/recordings/segment-summary?segmentName=../x', cookie)[0], 400)
        logout = request('POST', '/api/auth/logout', cookie)
        self.assertEqual(logout[0], 200, logout[1])
        self.assertEqual(request('GET', path, cookie)[0], 401)
      finally:
        server.shutdown()
        worker.join(2)
        server.server_close()

  def test_revoked_session_during_summary_sends_no_metrics(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      recordings = root / 'recordings'
      recordings.mkdir()
      write(recordings, [car(1_000_000_000, 10), car(2_000_000_000, 10)])
      access = GalaxyAccessOwner(root / 'access')
      access.configure('password123', lambda: True)
      entered, release = threading.Event(), threading.Event()

      class PausedSummary(SegmentSummary):
        def snapshot(self, segment_name, *, permitted):
          result = super().snapshot(segment_name, permitted=permitted)
          entered.set()
          release.wait(2)
          return result

      server = make_server(port=0, owner=access, recordings=DriveHistory(recordings),
                           segment_summary=PausedSummary(recordings))
      worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
      worker.start()

      def request(path, cookie='', body=None):
        conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        method = 'POST' if body is not None else 'GET'
        headers = {'Cookie': cookie} if cookie else {}
        if body is not None:
          headers.update({'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{server.server_port}'})
        try:
          conn.request(method, path, json.dumps(body) if body is not None else None, headers)
          response = conn.getresponse()
          return response.status, response.read(), dict(response.getheaders())
        finally:
          conn.close()

      try:
        _, _, headers = request('/api/auth/login', body={'password': 'password123'})
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        outcome = []
        blocked = threading.Thread(target=lambda: outcome.append(request(f'/api/recordings/segment-summary?segmentName={NAME}', cookie)))
        blocked.start()
        self.assertTrue(entered.wait(2))
        self.assertEqual(request('/api/auth/logout', cookie, {})[0], 200)
        release.set()
        blocked.join(3)
        self.assertEqual(outcome[0][0], 401)
        self.assertNotIn(b'estimatedDistanceMeters', outcome[0][1])
      finally:
        release.set()
        server.shutdown()
        worker.join(2)
        server.server_close()
