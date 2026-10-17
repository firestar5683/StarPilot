"""Galaxy routes a phone pairing window to Android Auto while it projects; radio and AA IPC are fakes."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server

PROMPT = '0123456789abcdef0123456789abcdef'
PHONE = '11:22:33:44:55:66'


class Params:
  def __init__(self, root): self.root, self.enabled = root, True
  def get(self, key): return None
  def get_param_path(self, key): return str(self.root / key)
  def get_bool(self, key): return self.enabled


class Bluetooth:
  def __init__(self): self.calls = []
  def snapshot(self, **kwargs):
    return {'version': 1, 'available': True, 'parked': True, 'powered': True,
            'discovering': False, 'devices': [], 'errorCode': None, 'pairing': None}
  def request(self, operation, **kwargs):
    self.calls.append(operation)
    return self.snapshot()
  def cancel_session(self, identity): pass


class AA:
  def __init__(self):
    self.calls, self.window, self.http, self.paired = [], True, None, None
  def call(self, command, **kwargs):
    assert command == 'phone_window'
    self.calls.append(kwargs)
    code, data, _ = self.http('/api/android-auto/source/' + kwargs['source'])
    assert code == 200 and data == {'valid': True}, 'Source proof was not live'
    if not self.window:
      return {'handled': False}
    pairing = {'address': PHONE, 'state': 'pairing', 'incoming': True, 'name': 'iPhone',
               'prompt': {'id': PROMPT, 'kind': 'confirmation', 'value': '123456'}}
    return {'handled': True, 'bluetooth': {'version': 1, 'devices': [], 'pairing': pairing, 'windowPaired': self.paired}}


class ProjectionPhoneWindowHttpTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    root = Path(temporary.name)
    self.params = Params(root)
    self.access = GalaxyAccessOwner(root / 'access')
    self.assertTrue(self.access.configure('password123', lambda: True))
    self.bluetooth, self.aa = Bluetooth(), AA()
    self.spotify = SimpleNamespace(prepared=[], adopted=[])
    self.spotify.prepare_phone_pairing = lambda: self.spotify.prepared.append(True)
    self.spotify.adopt_phone = lambda *args: self.spotify.adopted.append(args)
    self.server = make_server(port=0, owner=self.access, parked=lambda: True,
                              android_auto_setup=SimpleNamespace(enabled=lambda: self.params.enabled),
                              android_auto_client=self.aa, bluetooth=self.bluetooth, spotify_setup=self.spotify)
    self.worker = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    self.worker.start()
    self.addCleanup(self.stop)
    self.aa.http = self.http
    code, _, headers = self.http('/api/auth/login', {'password': 'password123'})
    self.assertEqual(code, 200)
    self.cookie = headers['Set-Cookie'].split(';', 1)[0]

  def stop(self):
    self.server.shutdown()
    self.worker.join(timeout=2)
    self.server.server_close()

  def http(self, path, payload=None, cookie=None):
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=4)
    headers = {'Cookie': self.cookie if cookie is None and hasattr(self, 'cookie') else cookie or ''}
    if payload is not None:
      headers.update({'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{self.server.server_port}'})
    try:
      connection.request('POST' if payload is not None else 'GET', path,
                         body=json.dumps(payload) if payload is not None else None, headers=headers)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()

  def action(self, payload):
    return self.http('/api/bluetooth/action', payload)

  def test_window_opens_answers_and_reports_through_android_auto_while_projecting(self):
    code, result, _ = self.action({'operation': 'accept_pair'})
    self.assertEqual(code, 200)
    self.assertTrue(result['pairing']['incoming'])
    self.assertNotIn('windowPaired', result)
    self.assertEqual(self.bluetooth.calls, [])
    self.assertEqual(self.spotify.prepared, [True])
    code, status, _ = self.http('/api/bluetooth/status')
    self.assertEqual((code, status['pairing']['prompt']['value']), (200, '123456'))
    self.aa.paired = {'address': PHONE, 'name': 'iPhone', 'uuids': ['0000110a-0000-1000-8000-00805f9b34fb']}
    code, _, _ = self.action({'operation': 'pairing_response', 'promptId': PROMPT, 'accepted': True})
    self.assertEqual(code, 200)
    self.assertEqual(self.spotify.adopted, [(PHONE, 'iPhone', ('0000110a-0000-1000-8000-00805f9b34fb',))])
    sources = {call['source'] for call in self.aa.calls}
    self.assertEqual(len(sources), 1, 'every window request must reuse one source')
    self.assertEqual(self.aa.calls[2]['prompt_id'], PROMPT)
    self.assertEqual(self.bluetooth.calls, [])

  def test_without_projection_the_comma_owner_opens_the_window(self):
    self.aa.window = False
    code, _, _ = self.action({'operation': 'accept_pair'})
    self.assertEqual(code, 200)
    self.assertEqual(self.bluetooth.calls, ['accept_pair'])
    self.aa.calls.clear()
    self.http('/api/bluetooth/status')
    self.assertEqual(self.aa.calls, [], 'an unhandled window must not keep a source alive')

  def test_android_auto_off_never_contacts_the_daemon(self):
    self.params.enabled = False
    self.assertEqual(self.action({'operation': 'accept_pair'})[0], 200)
    self.assertEqual(self.aa.calls, [])
    self.assertEqual(self.bluetooth.calls, ['accept_pair'])


if __name__ == '__main__':
  unittest.main()
