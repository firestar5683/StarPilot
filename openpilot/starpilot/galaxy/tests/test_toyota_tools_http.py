"""Toyota credentials require the existing authenticated, origin-checked Galaxy session."""

import http.client
import json
import threading

from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.galaxy.tests.test_toyota_tools import SavedParams
from openpilot.starpilot.galaxy.toyota_tools import ToyotaTools
from types import SimpleNamespace


def test_http_session_origin_and_secret_free_readback(tmp_path):
  params = SavedParams(tmp_path)
  cp = CarInterface.get_non_essential_params(CAR.TOYOTA_RAV4_PRIME)
  cp_raw = cp.to_bytes()
  context = SimpleNamespace(sample=lambda: SimpleNamespace(cp=cp, cp_raw=cp_raw, parked=True), close=lambda: None)
  tools = ToyotaTools(params, context)
  access = GalaxyAccessOwner(tmp_path / 'access')
  assert access.configure('password123', lambda: True)
  server = make_server(port=0, owner=access, parked=lambda: True, toyota_tools=tools)
  worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
  worker.start()
  def request(path, payload=None, cookie='', origin=True):
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
    headers = {'Cookie': cookie}
    if payload is not None:
      headers['Content-Type'] = 'application/json'
      headers['Origin'] = f'http://127.0.0.1:{server.server_port}' if origin else 'https://external.invalid'
    try:
      connection.request('POST' if payload is not None else 'GET', path, json.dumps(payload) if payload is not None else None, headers)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()
  try:
    assert request('/api/toyota-tools')[0] == 401
    code, _, headers = request('/api/auth/login', {'password': 'password123'})
    assert code == 200
    cookie = headers['Set-Cookie'].split(';', 1)[0]
    code, page, _ = request('/api/toyota-tools', cookie=cookie)
    assert code == 200 and page['visible'] and page['security']
    payload = {'view': page['view'], 'action': 'save_key', 'confirmed': True, 'name': 'My Toyota', 'value': 'ab' * 16}
    assert request('/api/toyota-tools/action', payload)[0] == 401
    assert request('/api/toyota-tools/action', payload, cookie, origin=False)[0] == 403
    assert request('/api/toyota-tools/action', payload, cookie)[0] == 200
    code, page, _ = request('/api/toyota-tools', cookie=cookie)
    assert code == 200 and page['keys'] == [{'name': 'My Toyota', 'active': False}]
    assert 'ab' * 16 not in json.dumps(page)
    request('/api/auth/logout', {}, cookie)
    assert request('/api/toyota-tools/action', {'view': page['view'], 'action': 'use_key', 'confirmed': True, 'name': 'My Toyota'}, cookie)[0] == 401
  finally:
    server.shutdown()
    worker.join(timeout=2)
    server.server_close()
