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
    routes = (('/api/flm/live', None), ('/api/flm/live-action', {'action': 'disable', 'token': 'a'*64}), ('/api/flm/status', None),
      (f'/api/flm/report?operationId={OPERATION}', None),
              ('/api/flm/start', {'segments': [SEGMENT]}), ('/api/flm/cancel', {'operationId': OPERATION}),
              ('/api/flm/train', {'segments': [SEGMENT], 'token': 'a'*64}),
              ('/api/flm/recommend', {'operationId': OPERATION, 'feedback': {}}),
              ('/api/flm/save-report', {'operationId': OPERATION, 'feedback': {}, 'generatedId': 'report:cleanup_pass:conservative',
                                       'id': 'one', 'label': 'One', 'token': 'a'*64}))
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
    self.assertEqual([c.args[0] for c in self.operations.request.call_args_list],
                     ['live', 'live-action', 'status', 'report', 'start', 'cancel', 'train', 'recommend', 'save-report'])

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
    self.assertEqual(self.request('/api/flm/train', payload={'segments': [SEGMENT], 'token': 'stale'})[0], 400)
    self.assertEqual(self.request('/api/flm/recommend', payload={'operationId': OPERATION, 'feedback': {'root': '/private'}})[0], 400)
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


def test_train_passes_the_same_effect_guard_that_serializes_logout():
  # Reuse the actual HTTP server/session owner rather than a synthetic lock.
  case = FlmHTTPTest()
  case.setUp()
  try:
    case.login()
    case.request('/api/flm/train', payload={'segments': [SEGMENT], 'token': 'a'*64})
    kwargs = case.operations.request.call_args.kwargs
    guard, session_valid = kwargs['session_guard'], kwargs['session_valid']
    assert session_valid()
    entered = threading.Event()
    replies = []
    def logout():
      entered.set()
      replies.append(case.request('/api/auth/logout', payload={}))
    with guard:
      thread = threading.Thread(target=logout)
      thread.start()
      assert entered.wait(1)
      thread.join(.05)
      assert thread.is_alive() and session_valid(), 'logout cannot retire the session during the guarded effect'
    thread.join(2)
    assert not thread.is_alive() and replies[0][0] == 200 and not session_valid()
  finally:
    case.doCleanups()


def test_completion_effect_guard_lifecycle(tmp_path):
  import sys
  from openpilot.common.params import Params
  from openpilot.common.prefix import OpenpilotPrefix
  from opendbc.car.gm.tests.test_ascm_intercept import params as ordinary_params
  from opendbc.car.gm.values import CAR
  from openpilot.starpilot.flm.gm_recommend import source_context
  from openpilot.starpilot.flm.tests.test_operation_owner import terminal
  from openpilot.starpilot.lateral.torque_settings import PlatformProfile, FieldChoice
  cp = ordinary_params(CAR.CHEVROLET_MALIBU_ASCM).as_reader()
  tune = cp.lateralTuning.torque
  with OpenpilotPrefix():
    context = source_context(cp, 'starpilot', Params(), 'a'*64,
                             PlatformProfile((tune.latAccelFactor, tune.latAccelOffset, tune.friction), FieldChoice(), FieldChoice()))
  # Lifecycle-only worker: real child/reap/monitor with source-valid metadata,
  # explicitly not measured evidence or a vehicle/actuator qualification.
  worker = (sys.executable, '-c',
            "import sys,json;v=json.load(sys.stdin);r={'schemaVersion':1,'purpose':'gm_flm_evidence_profiles'," +
            "'tuneRecommendation':None,'vehicleQualification':False,'segments':[{'source':{'segmentName':n}} " +
            "for n in v['segments']],'gmEvidence':{'context':v['gmContext'],'fit':False,'vehicleQualification':False}};" +
            "print(json.dumps({'kind':'result','report':r}))")
  for scenario in ('success', 'busy', 'logout', 'cancel', 'close', 'stale'):
    parked = mock.Mock()
    parked.parked.return_value = True
    bridge = FlmOperations(tmp_path, context=parked)
    bridge.owner._worker_argv = worker
    bridge.live = mock.Mock()
    bridge.live.training_context.return_value = context
    guard = threading.Lock()
    authenticated = [True]
    entered, release = threading.Event(), threading.Event()
    original = bridge._record_progress
    def completion(report, entered=entered, release=release, scenario=scenario, original=original):
      entered.set()
      assert release.wait(2)
      if scenario == 'stale':
        report = {**report, 'operationId': 'f'*32+':99'}
      return original(report)
    bridge.owner._completed = completion
    def record(report, *, session_valid, guard=guard, bridge=bridge):
      assert session_valid()
      assert not guard.acquire(blocking=False), 'same HTTP guard remains held through metadata commit'
      acquired = []
      def probe(bridge=bridge, acquired=acquired):
        available = bridge.owner._lock.acquire(blocking=False)
        acquired.append(available)
        if available:
          bridge.owner._lock.release()
      probe_thread = threading.Thread(target=probe)
      probe_thread.start()
      probe_thread.join(1)
      assert acquired == [False], 'cancel/close owner lock remains held through metadata commit'
      return True
    bridge.live.record_cleanup.side_effect = record
    retirement = None
    try:
      with guard:
        token = bridge.request('train', {'segments': [SEGMENT], 'token': 'a'*64},
                               session_valid=lambda authenticated=authenticated: authenticated[0], session_guard=guard)['operationId']
      assert entered.wait(1)
      # Completion must be outside the owner lock: an independent observer can
      # read lifecycle state before the effect guard has even been acquired.
      observed = []
      observer = threading.Thread(target=lambda observed=observed, bridge=bridge: observed.append(bridge.owner.snapshot()['state']))
      observer.start()
      observer.join(1)
      assert not observer.is_alive() and observed == ['running']
      if scenario in ('cancel', 'close'):
        with guard:
          retirement = threading.Thread(target=(lambda bridge=bridge, token=token: bridge.owner.cancel(token)) if scenario == 'cancel' else bridge.owner.close)
          retirement.start()
          assert bridge.owner._cancel.wait(1)
          release.set()
          retirement.join(1)
          assert not retirement.is_alive(), 'cancel holding effect guard must not deadlock with monitor completion'
      elif scenario == 'busy':
        with guard:
          release.set()
          assert terminal(bridge.owner)['state'] == 'completed'
      else:
        if scenario == 'logout':
          with guard:
            authenticated[0] = False
        release.set()
      status = terminal(bridge.owner)
      if scenario in ('cancel', 'close'):
        assert status['state'] == ('canceled' if scenario == 'cancel' else 'unavailable')
        with unittest.TestCase().assertRaises(FlmOperationError):
          bridge.owner.report(token)
      else:
        assert status['state'] == 'completed'
        assert bridge.owner.report(token)['gmEvidence']['progressRecorded'] is (scenario == 'success')
      assert bridge.live.record_cleanup.call_count == int(scenario == 'success')
    finally:
      release.set()
      if retirement is not None:
        retirement.join(2)
      bridge.close()
