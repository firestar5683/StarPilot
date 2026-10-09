import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.hotspot import HotspotSettings
from openpilot.starpilot.galaxy.server import make_server


class TestHotspotHttp(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    root = Path(self.temp.name)
    self.access = GalaxyAccessOwner(root / 'access')
    self.access.configure('password123', lambda: True)
    self.settings = HotspotSettings(root / 'hotspot', root / 'status', dongle_id=lambda: 'b0c4a280b2f96b86')
    self.parked = True
    aa = Mock()
    aa.enabled.return_value = False
    self.server = make_server(port=0, owner=self.access, hotspot=self.settings,
                              parked=lambda: self.parked, android_auto_setup=aa)
    self.worker = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
    self.worker.start()
    self.addCleanup(self.stop)

  def stop(self):
    self.server.shutdown()
    self.worker.join(timeout=2)
    self.server.server_close()

  def request(self, path='/api/galaxy/hotspot', payload=None, cookie='', origin=None):
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
    headers = {'Cookie': cookie}
    if payload is not None:
      headers.update({'Content-Type': 'application/json', 'Origin': origin or f'http://127.0.0.1:{self.server.server_port}'})
    try:
      connection.request('POST' if payload is not None else 'GET', path,
                         body=json.dumps(payload) if payload is not None else None, headers=headers)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()

  def login(self):
    status, _, headers = self.request('/api/auth/login', {'password': 'password123'})
    self.assertEqual(status, 200)
    return headers['Set-Cookie'].split(';', 1)[0]

  def test_auth_parked_revision_and_logout(self):
    self.assertEqual(self.request()[0], 401)
    self.assertEqual(self.request(payload={})[0], 401)
    cookie = self.login()
    status, value, _ = self.request(cookie=cookie)
    self.assertEqual(status, 200)
    self.assertEqual(value['config']['ssid'], 'TheGalaxy-6b86')
    payload = {'revision': value['revision'], 'config': {**value['config'], 'enabled': True}}
    self.parked = False
    self.assertEqual(self.request(cookie=cookie)[1]['editable'], False)
    self.assertEqual(self.request(payload=payload, cookie=cookie)[0], 409)
    self.assertFalse(self.settings.path.exists())
    self.parked = True
    spoofed = {**payload, 'config': {**payload['config'], 'ssid': 'Other network'}}
    self.assertEqual(self.request(payload=spoofed, cookie=cookie)[0], 400)
    self.assertEqual(self.request(payload=payload, cookie=cookie, origin='https://evil.example')[0], 403)
    self.assertFalse(self.settings.path.exists())
    code, saved, _ = self.request(payload=payload, cookie=cookie)
    self.assertEqual(code, 200)
    self.assertEqual(len(saved['config']['password']), 24)
    self.assertEqual(self.request(payload=payload, cookie=cookie)[0], 409)
    self.request('/api/auth/logout', {}, cookie)
    status, data, _ = self.request(cookie=cookie)
    self.assertEqual(status, 401)
    self.assertNotIn('config', data)

  def test_revocation_during_save_and_bad_input(self):
    cookie = self.login()
    value = self.request(cookie=cookie)[1]
    payload = {'revision': value['revision'], 'config': {**value['config'], 'enabled': 'yes'}}
    self.assertEqual(self.request(payload=payload, cookie=cookie)[0], 400)
    original = self.settings.save
    def revoked(payload, permitted):
      self.parked = False
      return original(payload, permitted)
    self.settings.save = revoked
    payload['config']['enabled'] = True
    self.assertEqual(self.request(payload=payload, cookie=cookie)[0], 409)
    self.assertFalse(self.settings.path.exists())
