import http.client
import io
import json
import threading

import pytest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.galaxy.spotify_setup import SetupRejected, SpotifySetup
from openpilot.starpilot.soloist import credentials, preferences
from openpilot.starpilot.soloist.paths import Layout

SESSION = ('token', 1)
DEVICES = [{'address': 'AA:BB:CC:DD:EE:FF', 'name': 'My Car', 'paired': True, 'connected': True},
           {'address': '11:22:33:44:55:66', 'name': 'Nearby', 'paired': False, 'connected': False}]


class FakeImport:
  def __init__(self, layout):
    self.work_dir = layout.imports
    self.started = []
    self.running = False
  def busy(self): return self.running
  def status(self): return {'state': 'running' if self.running else 'idle'}
  def start(self, *, path, enabled, may_activate):
    self.started.append(path.read_bytes())
    self.running = True


class FakeClient:
  def __init__(self):
    self.available = False
    self.calls = []
  def call(self, command, **payload):
    if not self.available:
      raise RuntimeError('Spotify isn’t running')
    self.calls.append((command, payload))
    if command == 'status':
      return {'status': {'state': 'ready', 'player': None}}
    return {'ok': True}


@pytest.fixture
def owner(tmp_path):
  state = {'parked': True, 'valid': True}
  layout = Layout(tmp_path / 'soloist')
  client = FakeClient()
  setup = SpotifySetup(parked=lambda: state['parked'], session_valid=lambda _s: state['valid'], layout=layout, client=client,
                       import_job=FakeImport(layout), paired_devices=lambda _s: DEVICES)
  return setup, state, layout, client


def test_status_never_contains_the_key(owner):
  setup, _, layout, _ = owner
  setup.set_key(SESSION, 'sk_live_0123456789abcdef')
  status = setup.status(SESSION)
  assert status['keyPresent'] is True and 'sk_live' not in json.dumps(status)
  assert status['devices'] == [{'address': 'AA:BB:CC:DD:EE:FF', 'name': 'My Car', 'connected': True}]
  assert status['links']['download'].startswith('https://developer.spotify.com/')
  with pytest.raises(SetupRejected):
    setup.set_key(SESSION, 'bad key')


def test_output_must_be_a_paired_device_and_needs_park(owner):
  setup, state, layout, _ = owner
  with pytest.raises(SetupRejected):
    setup.save_preferences(SESSION, {'output': 'bluetooth', 'outputAddress': '11:22:33:44:55:66'})
  setup.save_preferences(SESSION, {'output': 'bluetooth', 'outputAddress': 'aa:bb:cc:dd:ee:ff'})
  assert preferences.load(layout).output_name == 'My Car'
  state['parked'] = False
  with pytest.raises(SetupRejected):
    setup.save_preferences(SESSION, {'output': 'test', 'outputAddress': ''})
  setup.save_preferences(SESSION, {'deviceName': 'Civic'})  # naming is not configuration of the player output
  assert preferences.load(layout).device_name == 'Civic'
  with pytest.raises(SetupRejected):
    setup.save_preferences(SESSION, {'apiKey': 'x'})


def test_upload_streams_to_the_import_job_only_when_parked(owner):
  setup, state, _, _ = owner
  setup.upload(SESSION, io.BytesIO(b'\x1f\x8bdata'), 6)
  assert setup.job.started == [b'\x1f\x8bdata']
  setup.job.running = False
  state['parked'] = False
  with pytest.raises(SetupRejected):
    setup.upload(SESSION, io.BytesIO(b'x'), 1)
  state['parked'], state['valid'] = True, False
  with pytest.raises(SetupRejected):
    setup.upload(SESSION, io.BytesIO(b'x'), 1)


def test_remove_deletes_only_feature_data(owner, monkeypatch):
  setup, _, layout, _ = owner
  credentials.store('sk_live_0123456789abcdef', layout)
  preferences.set_enabled(True, layout)
  monkeypatch.setattr('openpilot.starpilot.soloist.supervisor.reap_orphans', lambda _l: 0)
  status = setup.remove(SESSION)
  assert not layout.root.exists() and status['enabled'] is False and status['keyPresent'] is False


def test_controls_go_through_the_supervisor(owner):
  setup, _, _, client = owner
  client.available = True
  setup.control(SESSION, 'pause', {})
  assert client.calls[-1] == ('control', {'action': 'pause', 'args': {}})
  with pytest.raises(SetupRejected):
    setup.control(SESSION, 'pause', [])


@pytest.fixture
def api(tmp_path, owner):
  setup, state, layout, client = owner
  access = GalaxyAccessOwner(tmp_path / 'access')
  assert access.configure('password123', lambda: True)
  server = make_server(port=0, owner=access, parked=lambda: state['parked'], spotify_setup=setup)
  worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
  worker.start()
  def request(method, path, body=None, *, cookie='', content_type='application/json'):
    conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
    headers = {'Cookie': cookie}
    if method != 'GET':
      headers['Origin'] = f'http://127.0.0.1:{server.server_port}'
    if body is not None:
      headers['Content-Type'] = content_type
    try:
      conn.request(method, path, body=body, headers=headers)
      response = conn.getresponse()
      return response.status, json.loads(response.read())
    finally:
      conn.close()
  conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
  conn.request('POST', '/api/auth/login', body=json.dumps({'password': 'password123'}),
               headers={'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{server.server_port}'})
  response = conn.getresponse()
  response.read()
  cookie = response.getheader('Set-Cookie').split(';', 1)[0]
  conn.close()
  yield request, cookie, setup, layout
  server.shutdown()
  worker.join(timeout=2)
  server.server_close()


def test_routes_require_a_session(api):
  request, _, _, _ = api
  assert request('GET', '/api/spotify/setup')[0] == 401
  assert request('POST', '/api/spotify/key', json.dumps({'key': 'sk_live_0123456789abcdef'}))[0] == 401
  assert request('POST', '/api/spotify/upload', b'\x1f\x8b', content_type='application/octet-stream')[0] == 401
  assert request('DELETE', '/api/spotify')[0] == 401


def test_routes_round_trip(api):
  request, cookie, setup, layout = api
  code, status = request('GET', '/api/spotify/setup', cookie=cookie)
  assert code == 200 and status['release'] == {'installed': False}
  code, status = request('POST', '/api/spotify/key', json.dumps({'key': 'sk_live_0123456789abcdef'}), cookie=cookie)
  assert code == 200 and status['keyPresent'] is True and 'sk_live' not in json.dumps(status)
  assert request('POST', '/api/spotify/key', json.dumps({'key': 'nope'}), cookie=cookie)[0] == 409
  assert request('POST', '/api/spotify/key', json.dumps({'key': 'sk_live_0123456789abcdef', 'x': 1}), cookie=cookie)[0] == 400
  code, status = request('POST', '/api/spotify/enable', json.dumps({'enabled': True}), cookie=cookie)
  assert code == 200 and status['enabled'] is True and layout.enabled_flag.exists()
  code, status = request('POST', '/api/spotify/preferences', json.dumps({'output': 'test', 'outputAddress': ''}), cookie=cookie)
  assert code == 200 and status['preferences']['output'] == 'test'
  assert request('POST', '/api/spotify/upload', b'\x1f\x8bxx', cookie=cookie, content_type='application/json')[0] == 415
  code, status = request('POST', '/api/spotify/upload', b'\x1f\x8bxx', cookie=cookie, content_type='application/octet-stream')
  assert code == 202 and setup.job.started == [b'\x1f\x8bxx']
  assert request('POST', '/api/spotify/control', json.dumps({'action': 'pause'}), cookie=cookie)[0] == 409  # not running
