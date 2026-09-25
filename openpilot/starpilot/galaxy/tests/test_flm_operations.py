"""Authenticated FLM dispatch, exact inventory identity and owned shutdown."""

import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from openpilot.starpilot.flm.operation_owner import FlmOperationError
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.flm_operations import FlmOperations
from openpilot.starpilot.galaxy.server import make_server


OPERATION = 'a' * 32 + ':1'
SEGMENT = '1234abcd--0123456789--0'


class FlmHTTPTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.access = GalaxyAccessOwner(Path(temporary.name) / 'access')
    self.operations = mock.Mock()
    self.operations.request.return_value = {'version': 1, 'operationId': OPERATION, 'state': 'running'}
    self.server = make_server(port=0, owner=self.access, flm_operations=self.operations)
    self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
    self.thread.start()
    self.addCleanup(self.stop)
    self.cookie = None

  def stop(self):
    self.server.shutdown()
    self.thread.join(2)
    self.server.server_close()

  def request(self, path, *, payload=None, raw=None, headers=None):
    # Exercise the password-backed forwarded path.
    selected = {'Forwarded': 'for=203.0.113.8', **({'Cookie': self.cookie} if self.cookie else {})}
    method = 'GET'
    if payload is not None or raw is not None:
      method = 'POST'
      selected.update({'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{self.server.server_port}'})
      raw = raw if raw is not None else json.dumps(payload)
    selected.update(headers or {})
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
    try:
      connection.request(method, path, body=raw, headers=selected)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()

  def login(self):
    self.assertTrue(self.access.configure('password123', lambda: True))
    status, _, headers = self.request('/api/auth/login', payload={'password': 'password123'})
    self.assertEqual(status, 200)
    self.cookie = headers['Set-Cookie'].split(';', 1)[0]

  def test_authentication_and_origin_precede_every_operation(self):
    routes = (('/api/flm/status', None), (f'/api/flm/report?operationId={OPERATION}', None),
              ('/api/flm/start', {'segments': [SEGMENT]}), ('/api/flm/cancel', {'operationId': OPERATION}))
    for path, payload in routes:
      self.assertEqual(self.request(path, payload=payload)[0], 503)
    self.login()
    cookie, self.cookie = self.cookie, None
    for path, payload in routes:
      self.assertEqual(self.request(path, payload=payload)[0], 401)
    self.cookie = cookie
    self.assertEqual(self.request('/api/flm/start', payload={'segments': [SEGMENT]},
                                  headers={'Origin': 'http://foreign.example'})[0], 403)
    self.operations.request.assert_not_called()
    for path, payload in routes:
      status, _, headers = self.request(path, payload=payload)
      self.assertEqual(status, 200)
      self.assertEqual(headers['Cache-Control'], 'no-store')
    self.assertEqual([c.args[0] for c in self.operations.request.call_args_list], ['status', 'report', 'start', 'cancel'])

  def test_closed_segment_identity_and_operation_input_are_strict(self):
    self.login()
    for payload in ([], {}, {'segments': []}, {'segments': [SEGMENT] * 2}, {'segments': ['../rlog']},
                    {'segments': [False]}, {'segments': [SEGMENT], 'root': '/private'},
                    {'segments': ['https://example.invalid/log']}):
      self.assertEqual(self.request('/api/flm/start', payload=payload)[0], 400)
    self.assertEqual(self.request('/api/flm/start', raw='{"segments":[],"segments":[]}')[0], 400)
    for query in ('', '?operationId=../all', f'?operationId={OPERATION}&operationId={OPERATION}',
                  f'?operationId={OPERATION}&root=private', '?a=1&b=2&c=3'):
      self.assertEqual(self.request('/api/flm/report' + query)[0], 400)
    self.assertEqual(self.request('/api/flm/status?root=private')[0], 400)
    self.assertEqual(self.request('/api/flm/cancel', payload={'operationId': OPERATION, 'all': True})[0], 400)
    self.operations.request.assert_not_called()

  def test_owner_refusals_and_logout_during_report_discard_sensitive_output(self):
    self.login()
    for code, expected in (('busy', 409), ('not_parked', 409), ('operation_changed', 409),
                           ('invalid_request', 400), ('deadline', 503)):
      self.operations.request.side_effect = FlmOperationError(code)
      status, body, _ = self.request('/api/flm/start', payload={'segments': [SEGMENT]})
      self.assertEqual(status, expected)
      self.assertEqual(body['code'], code)
    entered, release = threading.Event(), threading.Event()
    def read_report(*args):
      entered.set()
      release.wait(2)
      return {'privateDiagnostic': True}
    self.operations.request.side_effect = read_report
    replies = []
    worker = threading.Thread(target=lambda: replies.append(self.request(f'/api/flm/report?operationId={OPERATION}')))
    worker.start()
    try:
      self.assertTrue(entered.wait(1))
      self.assertEqual(self.request('/api/auth/logout', payload={})[0], 200)
    finally:
      release.set()
      worker.join(2)
    self.assertEqual(replies[0][0], 401)
    self.assertNotIn('privateDiagnostic', replies[0][1])

  def test_cleanup_retires_child_and_all_other_sources_even_if_one_fails(self):
    self.server.shutdown()
    self.thread.join(2)
    events = []
    self.operations.close.side_effect = lambda: events.append('analysis')
    self.server.plots_source = mock.Mock()
    self.server.plots_source.close.side_effect = RuntimeError('reader unavailable')
    self.server.settings_source = mock.Mock()
    self.server.settings_source.close.side_effect = lambda: events.append('settings')
    with self.assertRaises(RuntimeError):
      self.server.server_close()
    self.assertEqual(events, ['analysis', 'settings'])
    self.assertEqual(self.server.socket.fileno(), -1)
    self.server.plots_source.close.side_effect = None


def test_adapter_uses_shared_fresh_parked_owner_and_closes_reader_last(tmp_path):
  events = []
  context = mock.Mock()
  owner = mock.Mock()
  context.close.side_effect = lambda: events.append('context')
  owner.close.side_effect = lambda: events.append('child')
  bridge = FlmOperations(tmp_path, context=context, owner=owner)
  bridge.request('start', {'segments': [SEGMENT]})
  owner.start.assert_called_once_with((SEGMENT,))
  bridge.request('report', {'operationId': OPERATION})
  owner.report.assert_called_once_with(OPERATION)
  bridge.close()
  assert events == ['child', 'context']
