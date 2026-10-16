import http.client
import json
from pathlib import Path
import sys
import threading
from unittest.mock import Mock, patch

import pytest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.companion import CompanionRegistry
from openpilot.starpilot.galaxy.server import make_server


@pytest.fixture
def companion_http(tmp_path):
  registry = CompanionRegistry(tmp_path / 'settings', tmp_path / 'lease', tmp_path / 'status')
  access = GalaxyAccessOwner(tmp_path / 'access')
  access.configure('password123', lambda: True)
  aa = Mock()
  aa.enabled.return_value = False
  parked = Mock(return_value=True)
  server = make_server(port=0, owner=access, companion=registry, parked=parked, android_auto_setup=aa)
  server.test_parked = parked
  worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
  worker.start()

  def request(path, payload=None, cookie='', origin=None, method=None):
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
    headers = {'Cookie': cookie}
    if payload is not None:
      headers.update({'Content-Type': 'application/json', 'Origin': origin or f'http://127.0.0.1:{server.server_port}'})
    try:
      connection.request(method or ('POST' if payload is not None else 'GET'), path,
                         json.dumps(payload) if payload is not None else None, headers)
      response = connection.getresponse()
      return response.status, response.read(), dict(response.getheaders())
    finally:
      connection.close()
  try:
    yield request, registry, server
  finally:
    server.shutdown()
    worker.join(timeout=2)
    server.server_close()


def test_auth_and_local_mutations(companion_http):
  request, registry, _ = companion_http
  assert request('/api/companion/status')[0] == 401
  assert request('/api/companion/settings', {'enabled': True})[0] == 401
  with patch('openpilot.starpilot.galaxy.server.direct_local_connection', return_value=True):
    status, _, headers = request('/api/auth/session')
    assert status == 200
    cookie = headers['Set-Cookie'].split(';', 1)[0]
    assert request('/api/companion/settings', {'enabled': True}, cookie, 'https://evil.test')[0] == 403
    assert not registry.enabled()
    assert request('/api/companion/settings', {'enabled': True}, cookie)[0] == 200
    assert registry.enabled()
    assert request('/api/companion/settings', {'enabled': 1}, cookie)[0] == 400
    # A signed-in LAN client still cannot register a SOCKS endpoint outside galaxy0.
    payload = {'port': 1080, 'user': 'a' * 32, 'pass': 'b' * 32, 'version': '1.0.0', 'protocol': 1}
    assert request('/api/companion/uplink', payload, cookie)[0] == 400
    assert registry.lease() is None
    status, body, _ = request('/api/companion/status', cookie=cookie)
    assert status == 200 and json.loads(body)['enabled']
    assert b'pass' not in body
    assert request('/api/companion/qr.svg', cookie=cookie)[0] == 200


def test_apk_direct_download_without_cookie_and_head(companion_http, tmp_path):
  request, _, server = companion_http
  apk = tmp_path / 'sample.apk'
  apk.write_bytes(b'APK' * 30000)
  # Path is captured during server construction; patch its file operation.
  from openpilot.starpilot.galaxy.companion import APK_PATH
  real_open = type(APK_PATH).open

  def open_apk(path, *args, **kwargs):
    return real_open(apk if path == APK_PATH else path, *args, **kwargs)

  with patch('openpilot.starpilot.galaxy.server.direct_local_connection', return_value=True), patch('pathlib.Path.open', open_apk):
    code, body, headers = request('/app.apk')
    assert code == 200 and body == apk.read_bytes()
    assert headers['Content-Type'] == 'application/vnd.android.package-archive'
    code, body, headers = request('/api/companion/app.apk', method='HEAD')
    assert code == 200 and body == b'' and headers['Content-Length'] == '90000'
    server.remote_transport = True
    assert request('/app.apk')[0] == 403


def test_bluetooth_pairing_requires_session_origin_local_and_parked(companion_http, tmp_path):
  request, _, server = companion_http
  from openpilot.starpilot.galaxy.companion import bluetooth_pairing
  key_file = tmp_path / 'pairing.json'
  with patch('openpilot.starpilot.galaxy.companion.bluetooth_pairing', side_effect=lambda rotate: bluetooth_pairing(rotate, path=key_file)):
    assert request('/api/companion/bluetooth', {'rotate': False})[0] == 401
    cookie = request('/api/auth/session')[2]['Set-Cookie'].split(';', 1)[0]
    assert request('/api/companion/bluetooth', {'rotate': False}, cookie, 'https://evil.test')[0] == 403
    assert not key_file.exists()
    assert request('/api/companion/bluetooth', {'rotate': 1}, cookie)[0] == 400
    server.test_parked.return_value = False
    assert request('/api/companion/bluetooth', {'rotate': False}, cookie)[0] == 409
    assert not key_file.exists()
    server.test_parked.return_value = True
    status, data, _ = request('/api/companion/bluetooth', {'rotate': False}, cookie)
    assert status == 200 and json.loads(data)['type'] == 'galaxy-bluetooth'
    first = json.loads(data)['key']
    status, data, _ = request('/api/companion/bluetooth', {'rotate': False}, cookie)
    assert status == 200 and json.loads(data)['key'] != first  # each phone gets its own key
    assert len(json.loads(key_file.read_text())['phones']) == 2
    first = key_file.read_bytes()
    server.remote_transport = True
    assert request('/api/companion/bluetooth', {'rotate': True}, cookie)[0] == 403
    assert key_file.read_bytes() == first


def phone_bridge_proxy(port):
  # The phone bridge imports its siblings directly, exactly as it runs on comma.
  bridge = str(Path(__file__).resolve().parents[2] / 'galaxy_bluetooth/bridge')
  if bridge not in sys.path:
    sys.path.insert(0, bridge)
  from proxy import GalaxyProxy
  return GalaxyProxy(port)


def test_phone_bridge_against_current_galaxy(companion_http):
  _, registry, server = companion_http
  proxy = phone_bridge_proxy(server.server_port)
  request = {'id': 'test', 'method': 'GET', 'path': '/api/companion/status'}
  assert proxy.handle(request)['status'] == 200
  token = proxy.cookie
  assert token.startswith('galaxy_session=')
  import base64
  request.update(method='POST', path='/api/companion/settings', headers={'Content-Type': 'application/json'},
                 body=base64.b64encode(b'{"enabled":true}').decode())
  assert proxy.handle(request)['status'] == 200
  assert registry.enabled()
  assert proxy.cookie == token
  for path in ('/api/companion/bluetooth', '/api/companion/uplink', '/api/companion/app.apk'):
    request['path'] = path
    assert proxy.handle(request)['status'] == 501


def test_bluetooth_runtime_tracks_upstream_restart_and_blocks_replay(companion_http):
  import base64
  request, _, server = companion_http
  proxy = phone_bridge_proxy(server.server_port)
  for instance in ('before-restart', 'after-restart'):
    with patch('openpilot.starpilot.galaxy.server.INSTANCE', instance):
      result = proxy.handle({'id': 'runtime', 'method': 'GET', 'path': '/api/companion/runtime'})
      assert result['status'] == 200
      runtime = json.loads(base64.b64decode(result['body']))
      assert runtime == json.loads(request('/data/runtime.json')[1])
      assert runtime['instance'] == instance
  for path in ('/api/replay/start', '/api/replay/media?sequence=1'):
    assert proxy.handle({'id': 'replay', 'method': 'POST', 'path': path})['status'] == 501
