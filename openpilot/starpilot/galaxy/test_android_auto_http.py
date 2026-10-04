from unittest.mock import Mock
import http.client
import json
import threading

import pytest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.android_auto_setup import AndroidAutoSetup
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.system.android_auto.source_verifier import GalaxySourceVerifier


class FakeImport:
  def __init__(self, root):
    self.work_dir = root
    self.calls = []
    self.running = False
  def busy(self): return self.running
  def status(self): return {'state': 'running' if self.running else 'idle'}
  def start(self, *, path, enabled):
    self.calls.append((path.read_bytes(), enabled))
    self.running = True


@pytest.fixture
def api(tmp_path):
  access = GalaxyAccessOwner(tmp_path / 'access')
  assert access.configure('password123', lambda: True)
  state = {'parked': True, 'identity_installed': True, 'bluetooth_enabled': True, 'enabled': True}
  job = FakeImport(tmp_path / 'imports')
  setup = AndroidAutoSetup(parked=lambda: state['parked'], enabled=lambda: state['enabled'], session_valid=lambda _identity: True,
                           import_job=Mock(wraps=job, work_dir=job.work_dir), identity_status=lambda: {'installed': state['identity_installed'],
                                                                     'message': 'Package status'},
                           bluetooth_enabled=lambda: state['bluetooth_enabled'], install_ready=lambda: True,
                           service_ready=lambda: True, set_enabled=lambda value: state.update(enabled=value))
  class FakeClient:
    def __init__(self):
      self.calls = []
      self.verifier = None
      self.receiver = ''
      self.running = False
      self.auto_connect = False
    def call(self, command, **kwargs):
      assert command == 'status' or self.verifier.valid(kwargs['source'])
      self.calls.append((command, dict(kwargs)))
      if command == 'status':
        return {'status': {'receiver_address': self.receiver, 'receiver_name': 'My car', 'state': 'streaming' if self.running else 'idle',
                           'running': self.running, 'auto_connect': self.auto_connect, 'pairing_ready': False}}
      if command == 'devices':
        return {'devices': [{'address': 'AA:BB:CC:DD:EE:FF', 'name': 'Saved car', 'paired': True, 'android_auto': True}]}
      if command == 'select_receiver':
        self.receiver = kwargs['address']
      if command == 'set_auto_connect':
        self.auto_connect = kwargs['enabled']
      if command == 'start':
        self.running = True
      if command == 'stop':
        self.running = False
      return {'pairing': {'active': True, 'receiver': {'address': 'AA:BB:CC:DD:EE:FF', 'name': 'Car'},
                          'prompt': {'id': 'a' * 32, 'kind': 'confirmation', 'value': '123456'},
                          'approved': False}} if command == 'pairing_status' else {}
  client = FakeClient()
  server = make_server(port=0, owner=access, parked=lambda: state['parked'], android_auto_setup=setup,
                       android_auto_client=client)
  client.verifier = GalaxySourceVerifier(port=server.server_port)
  worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
  worker.start()
  def request(method, path, body=None, *, cookie='', content_type='application/octet-stream'):
    conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
    headers = {'Cookie': cookie}
    if method != 'GET':
      headers['Origin'] = f'http://127.0.0.1:{server.server_port}'
    if body is not None:
      headers['Content-Type'] = content_type
    try:
      conn.request(method, path, body=body, headers=headers)
      response = conn.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      conn.close()
  yield request, job, state, client
  server.shutdown()
  worker.join(timeout=2)
  server.server_close()


def test_galaxy_upload_requires_session_and_exact_binary_body(api):
  request, job, state, _ = api
  assert request('GET', '/api/android-auto/setup')[0] == 401
  assert request('POST', '/api/android-auto/upload', b'fake-apk')[0] == 401
  code, _, headers = request('POST', '/api/auth/login', json.dumps({'password': 'password123'}),
                              content_type='application/json')
  assert code == 200
  cookie = headers['Set-Cookie'].split(';', 1)[0]
  code, status, _ = request('GET', '/api/android-auto/setup', cookie=cookie)
  assert code == 200 and status['wiredAvailable'] is False
  assert request('POST', '/api/android-auto/upload', b'fake-apk', cookie=cookie,
                 content_type='application/json')[0] == 415
  assert request('POST', '/api/android-auto/upload', b'fake-apk', cookie=cookie)[0] == 202
  assert job.calls[0][0] == b'fake-apk'
  state['parked'] = False
  assert job.calls[0][1]() is False
  assert request('POST', '/api/android-auto/upload', b'other', cookie=cookie)[0] == 409


def test_galaxy_rejects_upload_after_logout(api):
  request, job, _, _ = api
  code, _, headers = request('POST', '/api/auth/login', json.dumps({'password': 'password123'}),
                              content_type='application/json')
  assert code == 200
  cookie = headers['Set-Cookie'].split(';', 1)[0]
  assert request('POST', '/api/auth/logout', '{}', cookie=cookie, content_type='application/json')[0] == 200
  assert request('POST', '/api/android-auto/upload', b'fake-apk', cookie=cookie)[0] == 401
  assert job.calls == []


def test_enable_requires_session_and_park_but_disable_revokes_without_park(api):
  request, _, state, _ = api
  def body(enabled):
    return json.dumps({'enabled': enabled})
  assert request('POST', '/api/android-auto/enable', body(True), content_type='application/json')[0] == 401
  code, _, headers = request('POST', '/api/auth/login', json.dumps({'password': 'password123'}),
                              content_type='application/json')
  assert code == 200
  cookie = headers['Set-Cookie'].split(';', 1)[0]
  assert request('POST', '/api/android-auto/enable', '{"enabled":1}', cookie=cookie,
                 content_type='application/json')[0] == 400
  state['parked'] = False
  assert request('POST', '/api/android-auto/enable', body(True), cookie=cookie,
                 content_type='application/json')[0] == 409
  assert request('POST', '/api/android-auto/enable', body(False), cookie=cookie,
                 content_type='application/json')[1]['enabled'] is False
  state['parked'] = True
  assert request('POST', '/api/android-auto/enable', body(True), cookie=cookie,
                 content_type='application/json')[1]['enabled'] is True


def test_identity_removal_is_authenticated_and_refuses_active_import(api, monkeypatch):
  from openpilot.starpilot.system.android_auto import apk_identity
  request, job, _, _ = api
  removed = []
  monkeypatch.setattr(apk_identity, 'remove_identity', lambda: removed.append(True))
  assert request('DELETE', '/api/android-auto/identity')[0] == 401
  code, _, headers = request('POST', '/api/auth/login', json.dumps({'password': 'password123'}),
                              content_type='application/json')
  assert code == 200
  cookie = headers['Set-Cookie'].split(';', 1)[0]
  job.running = True
  assert request('DELETE', '/api/android-auto/identity', cookie=cookie)[0] == 409
  assert removed == []
  job.running = False
  assert request('DELETE', '/api/android-auto/identity', cookie=cookie)[0] == 200
  assert removed == [True]


def test_pairing_source_is_minted_only_for_authenticated_parked_session_and_revoked_on_logout(api):
  request, _, state, client = api
  assert request('POST', '/api/android-auto/pairing', '{}', content_type='application/json')[0] == 401
  code, _, headers = request('POST', '/api/auth/login', json.dumps({'password': 'password123'}),
                              content_type='application/json')
  assert code == 200
  cookie = headers['Set-Cookie'].split(';', 1)[0]
  state['parked'] = False
  assert request('POST', '/api/android-auto/pairing', '{}', cookie=cookie, content_type='application/json')[0] == 403
  state['parked'] = True
  state['identity_installed'] = False
  assert request('POST', '/api/android-auto/pairing', '{}', cookie=cookie, content_type='application/json')[0] == 409
  state['identity_installed'] = True
  state['bluetooth_enabled'] = False
  assert request('POST', '/api/android-auto/pairing', '{}', cookie=cookie, content_type='application/json')[0] == 409
  state['bluetooth_enabled'] = True
  code, result, _ = request('POST', '/api/android-auto/pairing', '{}', cookie=cookie, content_type='application/json')
  assert code == 200 and result == {'pairing': True, 'seconds': 180}
  source = next(kwargs['source'] for command, kwargs in client.calls if command == 'prepare_pairing')
  assert source not in json.dumps(result) and client.verifier.valid(source)
  assert request('POST', '/api/auth/logout', '{}', cookie=cookie, content_type='application/json')[0] == 200
  assert not client.verifier.valid(source)


def test_incoming_prompt_requires_same_session_park_and_current_source(api):
  request, _, state, client = api
  assert request('GET', '/api/android-auto/pairing/status')[0] == 401
  code, _, headers = request('POST', '/api/auth/login', json.dumps({'password': 'password123'}),
                              content_type='application/json')
  assert code == 200
  cookie = headers['Set-Cookie'].split(';', 1)[0]
  assert request('GET', '/api/android-auto/pairing/status', cookie=cookie)[1]['pairing']['active'] is False
  assert request('POST', '/api/android-auto/pairing', '{}', cookie=cookie,
                 content_type='application/json')[0] == 200
  code, status, _ = request('GET', '/api/android-auto/pairing/status', cookie=cookie)
  assert code == 200 and status['pairing']['prompt']['kind'] == 'confirmation'
  source = next(kwargs['source'] for command, kwargs in client.calls if command == 'prepare_pairing')
  assert source not in json.dumps(status)
  assert request('POST', '/api/android-auto/pairing/response',
                 json.dumps({'prompt_id': 'bad', 'accepted': True, 'value': ''}), cookie=cookie,
                 content_type='application/json')[0] == 400
  assert [command for command, _kwargs in client.calls if command != 'status'] == ['prepare_pairing', 'pairing_status']
  payload = {'prompt_id': 'a' * 32, 'accepted': True, 'value': ''}
  assert request('POST', '/api/android-auto/pairing/response', json.dumps(payload), cookie=cookie,
                 content_type='application/json')[0] == 200
  assert client.calls[-1][0] == 'pairing_response'
  client.receiver = 'AA:BB:CC:DD:EE:FF'
  code, selected, _ = request('GET', '/api/android-auto/pairing/status', cookie=cookie)
  assert code == 200 and selected['selectedReceiver'] == {'address': client.receiver, 'name': 'My car'}
  state['parked'] = False
  assert request('POST', '/api/android-auto/pairing/response', json.dumps(payload), cookie=cookie,
                 content_type='application/json')[0] == 403
  state['parked'] = True
  assert request('POST', '/api/android-auto/pairing/cancel', '{}', cookie=cookie,
                 content_type='application/json')[0] == 200
  assert not client.verifier.valid(source)
  assert request('POST', '/api/android-auto/pairing/response', json.dumps(payload), cookie=cookie,
                 content_type='application/json')[0] == 409


def test_existing_paired_car_controls_are_local_authenticated_and_source_bound(api):
  request, _, state, client = api
  assert request('GET', '/api/android-auto/receivers')[0] == 401
  assert request('POST', '/api/android-auto/control', json.dumps({'action': 'start'}),
                 content_type='application/json')[0] == 401
  code, _, headers = request('POST', '/api/auth/login', json.dumps({'password': 'password123'}),
                              content_type='application/json')
  assert code == 200
  cookie = headers['Set-Cookie'].split(';', 1)[0]
  code, available, _ = request('GET', '/api/android-auto/receivers', cookie=cookie)
  assert code == 200 and available['receivers'] == [{'address': 'AA:BB:CC:DD:EE:FF', 'name': 'Saved car'}]
  source = next(kwargs['source'] for command, kwargs in client.calls if command == 'devices')
  assert source not in json.dumps(available) and not client.verifier.valid(source)
  assert request('POST', '/api/android-auto/control', json.dumps({'action': 'select_receiver', 'address': 'bad'}),
                 cookie=cookie, content_type='application/json')[0] == 400
  assert request('POST', '/api/android-auto/control', json.dumps({'action': 'start'}),
                 cookie=cookie, content_type='application/json')[0] == 409
  code, result, _ = request('POST', '/api/android-auto/control',
                            json.dumps({'action': 'select_receiver', 'address': 'AA:BB:CC:DD:EE:FF'}),
                            cookie=cookie, content_type='application/json')
  assert code == 200 and result['status']['receiver_address'] == 'AA:BB:CC:DD:EE:FF'
  state['parked'] = False
  assert request('POST', '/api/android-auto/control', json.dumps({'action': 'auto_connect', 'enabled': True}),
                 cookie=cookie, content_type='application/json')[0] == 403
  assert request('POST', '/api/android-auto/control', json.dumps({'action': 'start'}),
                 cookie=cookie, content_type='application/json')[0] == 200
  assert client.running
  assert request('POST', '/api/android-auto/control', json.dumps({'action': 'stop'}),
                 cookie=cookie, content_type='application/json')[0] == 200
  assert not client.running
  state['parked'] = True
  assert request('POST', '/api/android-auto/control', json.dumps({'action': 'auto_connect', 'enabled': True}),
                 cookie=cookie, content_type='application/json')[0] == 200
  assert client.auto_connect
  assert request('POST', '/api/auth/logout', '{}', cookie=cookie, content_type='application/json')[0] == 200
  assert request('POST', '/api/android-auto/control', json.dumps({'action': 'start'}),
                 cookie=cookie, content_type='application/json')[0] == 401


def test_local_enable_then_upload_bundle_preserves_binary_bytes(api):
  import io
  import zipfile

  request, job, state, _ = api
  state['enabled'] = False
  code, _, headers = request('POST', '/api/auth/login', json.dumps({'password': 'password123'}),
                             content_type='application/json')
  assert code == 200
  cookie = headers['Set-Cookie'].split(';', 1)[0]
  code, before, _ = request('GET', '/api/android-auto/setup', cookie=cookie)
  assert code == 200 and not before['enabled'] and before['installReady']
  code, enabled, _ = request('POST', '/api/android-auto/enable', json.dumps({'enabled': True}),
                            cookie=cookie, content_type='application/json')
  assert code == 200 and enabled['enabled']
  archive = io.BytesIO()
  with zipfile.ZipFile(archive, 'w') as bundle:
    bundle.writestr('base.apk', b'package-content')
  payload = archive.getvalue()
  code, uploaded, _ = request('POST', '/api/android-auto/upload', payload, cookie=cookie)
  assert code == 202 and uploaded['import']['state'] == 'running'
  assert job.calls[0][0] == payload
  assert job.calls[0][1]() is True
  code, status, _ = request('GET', '/api/android-auto/setup', cookie=cookie)
  assert code == 200 and status['import']['state'] == 'running'


def test_outgoing_car_selection_requires_current_pairing_session_and_valid_address(api):
  request, _, state, client = api
  path = '/api/android-auto/pairing/select'
  selected = json.dumps({'address': 'aa:bb:cc:dd:ee:ff'})
  assert request('POST', path, selected, content_type='application/json')[0] == 401
  code, _, headers = request('POST', '/api/auth/login', json.dumps({'password': 'password123'}),
                              content_type='application/json')
  assert code == 200
  cookie = headers['Set-Cookie'].split(';', 1)[0]
  def select(body=selected):
    return request('POST', path, body, cookie=cookie, content_type='application/json')[0]
  assert select() == 409
  assert request('POST', '/api/android-auto/pairing', '{}', cookie=cookie, content_type='application/json')[0] == 200
  for body in ('{}', '{"address":1}', '{"address":"bad"}', '{"address":"AA:BB:CC:DD:EE:FF","force":true}'):
    assert select(body) == 400
  assert select() == 200
  assert client.calls[-1][0] == 'pair_device'
  assert client.calls[-1][1]['address'] == 'AA:BB:CC:DD:EE:FF'
  assert client.verifier.valid(client.calls[-1][1]['source'])
  state['parked'] = False
  assert select() == 403
  state['parked'] = True
  assert request('POST', '/api/android-auto/pairing/cancel', '{}', cookie=cookie, content_type='application/json')[0] == 200
  assert select() == 409
