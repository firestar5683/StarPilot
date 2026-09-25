"""Actual authenticated HTTP dispatch to the single parked map owner."""

import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.map_operations import MapOperations
from openpilot.starpilot.galaxy.server import make_server


class MapOperationsHTTPTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.owner = GalaxyAccessOwner(Path(temporary.name) / 'access')
    self.calls = []
    self.reply = lambda command: {'version': 1, 'ok': True, 'result': {'schemaVersion': 1, 'state': 'idle'}}

    def request_owner(command):
      self.calls.append(command)
      return self.reply(command)

    self.server = make_server(port=0, owner=self.owner, map_operations=MapOperations(request_owner))
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
    request_headers = {'Forwarded': 'for=203.0.113.8'}
    if self.cookie:
      request_headers['Cookie'] = self.cookie
    method = 'GET'
    if payload is not None or raw is not None:
      method = 'POST'
      request_headers.update({'Content-Type': 'application/json',
                              'Origin': f'http://127.0.0.1:{self.server.server_port}'})
      raw = raw if raw is not None else json.dumps(payload)
    request_headers.update(headers or {})
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
    try:
      connection.request(method, path, body=raw, headers=request_headers)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()

  def login(self):
    self.assertTrue(self.owner.configure('password123', lambda: True))
    status, _, headers = self.request('/api/auth/login', payload={'password': 'password123'})
    self.assertEqual(status, 200)
    self.cookie = headers['Set-Cookie'].split(';', 1)[0]

  @staticmethod
  def start_payload():
    return {'regionToken': 'us_state.Iowa', 'maxTransferBytes': 1 << 30,
            'maxNewDiskBytes': 2 << 30, 'expectedCurrentGeneration': ''}

  def test_setup_is_authenticated_read_only_owner_projection(self):
    self.login()
    self.reply = lambda command: {'version': 1, 'ok': True, 'result': {
      'schemaVersion': 1, 'packageReady': False, 'packageState': 'invalid_package',
      'snapshotReady': True, 'selectedGeneration': 'a' * 64, 'parked': True,
      'freeDiskBytes': 2 << 30, 'maxTransferBytes': 8 << 30, 'maxNewDiskBytes': 16 << 30}}
    status, body, _ = self.request('/api/maps/setup')
    self.assertEqual(status, 200)
    self.assertEqual(body['packageState'], 'invalid_package')
    self.assertEqual(body['selectedGeneration'], 'a' * 64)
    self.assertEqual(self.calls, [{'version': 1, 'op': 'setup'}])

  def test_session_and_same_origin_precede_every_owner_call(self):
    routes = (('/api/maps/setup', None), ('/api/maps/catalog', None), ('/api/maps/operation', None),
              ('/api/maps/start', self.start_payload()), ('/api/maps/cancel', {'operationId': 'a' * 32 + ':1'}))
    for path, payload in routes:
      self.assertEqual(self.request(path, payload=payload)[0], 503)
    self.login()
    cookie, self.cookie = self.cookie, None
    for path, payload in routes:
      self.assertEqual(self.request(path, payload=payload)[0], 401)
    self.cookie = cookie
    self.assertEqual(self.request('/api/maps/start', payload=self.start_payload(),
                                  headers={'Origin': 'http://foreign.example'})[0], 403)
    self.assertEqual(self.calls, [])
    for path, payload in routes:
      status, body, headers = self.request(path, payload=payload)
      self.assertEqual(status, 200)
      self.assertEqual(body['state'], 'idle')
      self.assertEqual(headers['Cache-Control'], 'no-store')
    self.assertEqual([item['op'] for item in self.calls], ['setup', 'catalog', 'status', 'start', 'cancel'])
    self.assertEqual(next(item for item in self.calls if item['op'] == 'start'), {'version': 1, 'op': 'start', **self.start_payload()})

  def test_invalid_actions_never_reach_owner(self):
    self.login()
    payload = self.start_payload()
    invalid = [[], {**payload, 'url': 'https://foreign.example'}, {**payload, 'maxTransferBytes': True},
               {**payload, 'maxNewDiskBytes': 0}, {**payload, 'maxTransferBytes': 9 << 30},
               {**payload, 'expectedCurrentGeneration': '../current'},
               {**payload, 'expectedCurrentGeneration': None}]
    for value in invalid:
      self.assertEqual(self.request('/api/maps/start', payload=value)[0], 400)
    self.assertEqual(self.request('/api/maps/start', raw='{"regionToken":"a","regionToken":"b"}')[0], 400)
    self.assertEqual(self.request('/api/maps/cancel', payload={'operationId': '../all'})[0], 400)
    self.assertEqual(self.request('/api/maps/cancel', payload={'operationId': 'op', 'all': True})[0], 400)
    self.assertEqual(self.calls, [])

  def test_owner_refusals_remain_distinct_from_acceptance(self):
    self.login()
    for code, expected in (('not_parked', 409), ('busy', 409), ('selection_changed', 409),
                           ('invalid_region', 400), ('package_unavailable', 503)):
      self.reply = lambda command, code=code: {'version': 1, 'ok': False, 'error': {'code': code, 'message': 'private detail'}}
      status, body, _ = self.request('/api/maps/start', payload=self.start_payload())
      self.assertEqual(status, expected)
      self.assertEqual(body['code'], code)
      self.assertNotIn('private detail', json.dumps(body))
    self.reply = lambda command: {'version': 1, 'ok': True, 'result': ['invalid']}
    self.assertEqual(self.request('/api/maps/catalog')[0], 503)

  def test_revoke_during_read_discards_owner_result(self):
    self.login()
    entered, release = threading.Event(), threading.Event()
    def paused(command):
      entered.set()
      release.wait(2)
      return {'version': 1, 'ok': True, 'result': {'selectedGeneration': 'a' * 64}}
    self.reply = paused
    responses = []
    worker = threading.Thread(target=lambda: responses.append(self.request('/api/maps/operation')))
    worker.start()
    try:
      self.assertTrue(entered.wait(1))
      self.assertEqual(self.request('/api/auth/logout', payload={})[0], 200)
    finally:
      release.set()
      worker.join(2)
    self.assertEqual(responses[0][0], 401)
    self.assertNotIn('selectedGeneration', responses[0][1])
    self.assertEqual(self.request('/api/maps/start', payload=self.start_payload())[0], 401)
    self.assertEqual(len(self.calls), 1)

  def test_logout_waits_for_authorized_dispatch_then_blocks_later_start(self):
    self.login()
    entered, release, logged_out = threading.Event(), threading.Event(), threading.Event()
    def paused(command):
      entered.set()
      release.wait(2)
      return {'version': 1, 'ok': True, 'result': {'schemaVersion': 1, 'state': 'transferring'}}
    self.reply = paused
    starts, logouts = [], []
    starter = threading.Thread(target=lambda: starts.append(self.request('/api/maps/start', payload=self.start_payload())))
    def logout():
      logouts.append(self.request('/api/auth/logout', payload={}))
      logged_out.set()
    quitter = threading.Thread(target=logout)
    starter.start()
    try:
      self.assertTrue(entered.wait(1))
      quitter.start()
      self.assertFalse(logged_out.wait(0.05))
    finally:
      release.set()
      starter.join(2)
      if quitter.ident is not None:
        quitter.join(2)
    self.assertEqual(logouts[0][0], 200)
    self.assertIn(starts[0][0], (200, 401))  # Revocation may win before the response is sent.
    self.assertEqual(self.request('/api/maps/start', payload=self.start_payload())[0], 401)
    self.assertEqual(len(self.calls), 1)
