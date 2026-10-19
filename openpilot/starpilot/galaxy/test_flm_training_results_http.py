"""Authenticated training-results read never requires parked state or mutations."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server


class TrainingResultsHTTPTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.access = GalaxyAccessOwner(Path(temporary.name) / 'access')
    self.results = mock.Mock()
    self.results.snapshot.return_value = {'version': 1, 'current': {'fresh': True, 'progress': {'blocks': 3}}, 'history': []}
    self.parked = mock.Mock(return_value=False)
    self.server = make_server(port=0, owner=self.access, training_results=self.results,
                              parked=self.parked)
    self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    self.thread.start()
    self.addCleanup(self.stop)
    self.cookie = None
    self.parked.reset_mock()

  def stop(self):
    self.server.shutdown()
    self.thread.join(2)
    self.server.server_close()

  def request(self, path='/api/flm/training-results', *, payload=None, origin=None):
    headers = {'Forwarded': 'for=203.0.113.8', **({'Cookie': self.cookie} if self.cookie else {})}
    if payload is not None:
      headers.update({'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{self.server.server_port}'})
    if origin is not None:
      headers['Origin'] = origin
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
    try:
      connection.request('POST' if payload is not None else 'GET', path,
                         body=None if payload is None else json.dumps(payload), headers=headers)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()

  def login(self):
    assert self.access.configure('password123', lambda: True)
    status, _, headers = self.request('/api/auth/login', payload={'password': 'password123'})
    assert status == 200
    self.cookie = headers['Set-Cookie'].split(';', 1)[0]

  def test_authenticated_read_works_driving_or_offroad_without_any_mutation_owner(self):
    assert self.request()[0] == 503
    self.results.snapshot.assert_not_called()
    self.login()
    cookie, self.cookie = self.cookie, None
    assert self.request()[0] == 401
    self.cookie = cookie
    for parked in (False, True):
      self.parked.return_value = parked
      status, body, headers = self.request()
      assert status == 200 and body == self.results.snapshot.return_value
      assert headers['Cache-Control'] == 'no-store'
    self.parked.assert_not_called()
    assert self.results.snapshot.call_count == 2

  def test_queries_and_cross_origin_are_rejected_before_report_read(self):
    self.login()
    for path in ('/api/flm/training-results?path=/private', '/api/flm/training-results?x=1'):
      assert self.request(path)[0] == 400
    assert self.request(origin='http://foreign.invalid')[0] == 403
    self.results.snapshot.assert_not_called()

  def test_removed_manual_flm_workflow_is_unavailable(self):
    self.login()
    for name in ('status', 'report', 'live', 'start', 'cancel', 'live-action', 'train', 'recommend', 'save-report'):
      for payload in (None, {}):
        status, _, _ = self.request('/api/flm/' + name, payload=payload)
        assert status == 404
    self.results.snapshot.assert_not_called()
    self.parked.assert_not_called()

  def test_logout_during_snapshot_discards_report(self):
    self.login()
    entered, release = threading.Event(), threading.Event()

    def snapshot():
      entered.set()
      release.wait(2)
      return {'privateTrainingDetails': True}

    self.results.snapshot.side_effect = snapshot
    replies = []
    worker = threading.Thread(target=lambda: replies.append(self.request()))
    worker.start()
    try:
      assert entered.wait(1)
      assert self.request('/api/auth/logout', payload={})[0] == 200
    finally:
      release.set()
      worker.join(2)
    assert replies and replies[0][0] == 401
    assert 'privateTrainingDetails' not in replies[0][1]
