import http.client
import json
import tempfile
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from openpilot.starpilot.bluetooth.owner import BluetoothRejected, BluetoothUnavailable
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server


class FakeBluetooth:
  def __init__(self):
    self.parked = True
    self.calls = []
    self.canceled = []

  def snapshot(self, *, session=None):
    return {'version': 1, 'available': True, 'parked': self.parked, 'powered': True,
            'discovering': False, 'devices': [], 'errorCode': None, 'pairing': None}

  def request(self, operation, *, address=None, enabled=None, session=None, prompt_id=None, accepted=None, value=''):
    if not self.parked:
      raise BluetoothRejected('Park required')
    self.calls.append((operation, address, enabled, session, prompt_id, accepted, value))
    return self.snapshot()

  def cancel_session(self, identity):
    self.canceled.append(identity)


class BluetoothHttpTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    access = GalaxyAccessOwner(Path(temporary.name) / 'access')
    self.assertTrue(access.configure('password123', lambda: True))
    self.access = access
    self.bluetooth = FakeBluetooth()
    self.server = make_server(port=0, owner=access, bluetooth=self.bluetooth)
    self.worker = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
    self.worker.start()
    self.addCleanup(self.stop)

  def stop(self):
    self.server.shutdown()
    self.worker.join(timeout=2)
    self.server.server_close()

  def request(self, path, payload=None, cookie=''):
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
    headers = {'Cookie': cookie}
    if payload is not None:
      headers.update({'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{self.server.server_port}'})
    try:
      connection.request('POST' if payload is not None else 'GET', path,
                         body=json.dumps(payload) if payload is not None else None, headers=headers)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()

  def test_authenticated_status_and_parked_mutation(self):
    self.assertEqual(self.request('/api/bluetooth/status')[0], 401)
    code, _, headers = self.request('/api/auth/login', {'password': 'password123'})
    self.assertEqual(code, 200)
    cookie = headers['Set-Cookie'].split(';', 1)[0]
    self.assertEqual(self.request('/api/bluetooth/status', cookie=cookie)[1]['powered'], True)
    self.assertEqual(self.request('/api/bluetooth/action', {'operation': 'connect', 'address': 'AA:BB:CC:DD:EE:FF'}, cookie)[0], 200)
    self.assertEqual(self.bluetooth.calls[0][:3], ('connect', 'AA:BB:CC:DD:EE:FF', None))
    self.bluetooth.parked = False
    self.assertEqual(self.request('/api/bluetooth/action', {'operation': 'disconnect', 'address': 'AA:BB:CC:DD:EE:FF'}, cookie)[0], 409)
    self.assertEqual(len(self.bluetooth.calls), 1)
    self.assertEqual(self.request('/api/bluetooth/action', {'operation': 'pair', 'address': 'AA:BB:CC:DD:EE:FF'}, cookie)[0], 409)
    self.assertEqual(self.request('/api/bluetooth/action', {'operation': 'connect', 'address': 'bad'}, cookie)[0], 400)
    self.assertEqual(self.request('/api/auth/logout', {}, cookie)[0], 200)
    self.assertEqual(self.request('/api/bluetooth/action', {'operation': 'pair', 'address': '11:22:33:44:55:66'}, cookie)[0], 401)
    self.assertEqual(self.bluetooth.canceled, [self.bluetooth.calls[0][3]])
    self.assertEqual(self.request('/api/bluetooth/status', cookie=cookie)[0], 401)

  def test_radio_errors_keep_their_cause_without_exposing_internal_details(self):
    _, _, headers = self.request('/api/auth/login', {'password': 'password123'})
    cookie = headers['Set-Cookie'].split(';', 1)[0]
    for error, expected_status, expected_code in (
      (BluetoothRejected('private owner detail', code='busy'), 409, 'busy'),
      (BluetoothRejected('private state detail', code='park_required'), 409, 'park_required'),
      (BluetoothUnavailable('private system bus detail'), 503, 'service_unavailable'),
      (BluetoothUnavailable('private adapter detail', code='adapter_unavailable'), 503, 'adapter_unavailable'),
    ):
      with mock.patch.object(self.bluetooth, 'request', side_effect=error):
        code, body, _ = self.request('/api/bluetooth/action', {'operation': 'power', 'enabled': True}, cookie)
      self.assertEqual(code, expected_status)
      self.assertEqual(body['code'], expected_code)
      self.assertNotIn('private', json.dumps(body))

  def test_pairing_actions_are_scoped_and_strict(self):
    code, _, headers = self.request('/api/auth/login', {'password': 'password123'})
    self.assertEqual(code, 200)
    cookie = headers['Set-Cookie'].split(';', 1)[0]
    self.assertEqual(self.request('/api/bluetooth/action', {'operation': 'pair', 'address': '11:22:33:44:55:66'}, cookie)[0], 200)
    self.assertEqual(self.bluetooth.calls[-1][:2], ('pair', '11:22:33:44:55:66'))
    self.assertIsNotNone(self.bluetooth.calls[-1][3])
    self.assertEqual(self.request('/api/bluetooth/action', {'operation': 'pairing_response', 'promptId': 'a' * 32,
                                                              'accepted': True, 'value': '123456'}, cookie)[0], 200)
    self.assertEqual(self.bluetooth.calls[-1][4:], ('a' * 32, True, '123456'))
    self.assertEqual(self.request('/api/bluetooth/action', {'operation': 'cancel_pair'}, cookie)[0], 200)
    for payload in ({'operation': 'pairing_response', 'promptId': 'bad', 'accepted': True},
                    {'operation': 'pairing_response', 'promptId': 'a' * 32, 'accepted': 1},
                    {'operation': 'pair', 'address': '11:22:33:44:55:66', 'enabled': True}):
      self.assertEqual(self.request('/api/bluetooth/action', payload, cookie)[0], 400)
    self.assertEqual(self.request('/api/auth/logout', {}, cookie)[0], 200)

  def test_revoked_during_status_read_returns_401_without_pairing_prompt(self):
    code, _, headers = self.request('/api/auth/login', {'password': 'password123'})
    self.assertEqual(code, 200)
    cookie = headers['Set-Cookie'].split(';', 1)[0]
    with ExitStack() as stack:
      def revoke_during_snapshot(*, session=None):
        stack.enter_context(mock.patch.object(self.access, 'current_generation', return_value=None))
        return {'version': 1, 'available': True, 'parked': True, 'powered': True,
                'discovering': False, 'devices': [], 'errorCode': None,
                'pairing': {'address': '11:22:33:44:55:66', 'state': 'pairing',
                            'prompt': {'id': 'a' * 32, 'kind': 'pin', 'value': 'private', 'displayOnly': False}}}
      stack.enter_context(mock.patch.object(self.bluetooth, 'snapshot', side_effect=revoke_during_snapshot))
      status, body, _ = self.request('/api/bluetooth/status', cookie=cookie)
    self.assertEqual(status, 401)
    self.assertNotIn('private', json.dumps(body))


if __name__ == '__main__':
  unittest.main()
