import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from openpilot.starpilot.controllers.transport import ControllerBusy, ControllerDenied, ControllerInvalid, ControllerUnavailable
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server


class LayoutAuthority:
  def __init__(self):
    self.parked_now = True
    self.checks = 0

  def parked(self):
    self.checks += 1
    return self.parked_now


class ControllersHttpTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.socket = Path(temporary.name) / 'controller.sock'
    self.layouts = LayoutAuthority()
    self.status = patch('openpilot.starpilot.galaxy.server.controller_status', return_value={'version': 1}).start()
    self.action = patch('openpilot.starpilot.galaxy.server.controller_action', return_value={'version': 1}).start()
    self.addCleanup(patch.stopall)
    self.server = make_server(port=0, owner=GalaxyAccessOwner(Path(temporary.name) / 'access'),
                              layouts=self.layouts, controllers_socket=self.socket)
    self.worker = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    self.worker.start()
    self.addCleanup(self.stop)

  def stop(self):
    self.server.shutdown()
    self.worker.join(timeout=2)
    self.server.server_close()

  def request(self, path, payload=None, cookie='', *, origin=None, raw=None):
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
    headers = {'Cookie': cookie}
    body = raw if raw is not None else json.dumps(payload) if payload is not None else None
    if body is not None:
      headers.update({'Content-Type': 'application/json', 'Origin': origin or f'http://127.0.0.1:{self.server.server_port}'})
    try:
      connection.request('POST' if body is not None else 'GET', path, body=body, headers=headers)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()

  def login(self):
    status, _, headers = self.request('/api/auth/session')
    self.assertEqual(status, 200)
    return headers['Set-Cookie'].split(';', 1)[0]

  def test_session_origin_parked_and_exact_transport_forwarding(self):
    self.assertEqual(self.request('/api/controllers/status')[0], 401)
    cookie = self.login()
    self.assertEqual(self.request('/api/controllers/status', cookie=cookie)[0], 200)
    self.status.assert_called_once_with(self.socket)
    self.assertGreater(self.layouts.checks, 0)
    payload = {'operation': 'learn', 'revision': 'a' * 64, 'slot': 3}
    self.assertEqual(self.request('/api/controllers/action', payload, cookie)[0], 200)
    self.action.assert_called_once_with(payload, self.socket)
    self.assertEqual(self.request('/api/controllers/action', payload, cookie, origin='http://evil.example')[0], 403)
    self.assertEqual(self.action.call_count, 1)
    self.layouts.parked_now = False
    self.assertEqual(self.request('/api/controllers/action', payload, cookie)[0], 403)
    self.assertEqual(self.action.call_count, 1)
    self.assertEqual(self.request('/api/controllers/action', payload)[0], 401)

  def test_protocol_errors_and_no_button_press_route(self):
    cookie = self.login()
    payload = {'operation': 'save', 'revision': 'a' * 64, 'enabled': False, 'slots': [None] * 10}
    for error, expected in ((ControllerInvalid('bad'), 400), (ControllerDenied('park'), 403),
                            (ControllerBusy('busy'), 429), (ControllerUnavailable('offline'), 503)):
      self.action.side_effect = error
      self.assertEqual(self.request('/api/controllers/action', payload, cookie)[0], expected)
    self.assertEqual(self.request('/api/controllers/action', cookie=cookie,
                                  raw='{"operation":"test","operation":"cancel"}')[0], 400)
    self.assertEqual(self.request('/api/controllers/press', {'deviceId': 'x', 'code': 30}, cookie)[0], 405)
    self.status.side_effect = ControllerUnavailable('offline')
    self.assertEqual(self.request('/api/controllers/status', cookie=cookie)[0], 503)


if __name__ == '__main__':
  unittest.main()
