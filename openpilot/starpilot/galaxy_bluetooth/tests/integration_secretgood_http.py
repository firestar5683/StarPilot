"""Run on a SecretGood runtime: real settings preview/confirm through BLE proxy.

All settings and access credentials are in a temporary directory. No device
Params, vehicle behavior, radio or hardware connections are changed.
"""
import base64
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from proxy import GalaxyProxy
from openpilot.common.params import Params
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.galaxy.settings import AuthorityContext, SettingsGateway


class Context:
  def __init__(self): self.value = AuthorityContext(True, None, None)
  def sample(self): return self.value


class SecretGoodHTTPTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.params = Params(str(Path(self.temp.name) / 'params'))
    self.context = Context()
    self.settings = SettingsGateway(self.params, self.context)
    self.access = GalaxyAccessOwner(Path(self.temp.name) / 'access')
    self.server = make_server(port=0, owner=self.access, settings=self.settings)
    self.worker = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    self.worker.start()
    self.proxy = GalaxyProxy(self.server.server_port)
    self.addCleanup(self.stop)

  def stop(self):
    self.server.shutdown()
    self.worker.join(timeout=2)
    self.server.server_close()

  def request(self, path, payload=None, proxy=None):
    response = (proxy or self.proxy).handle({'id': 'test', 'path': path, 'method': 'GET' if payload is None else 'POST',
      'body': '' if payload is None else base64.b64encode(json.dumps(payload).encode()).decode()})
    return response['status'], json.loads(base64.b64decode(response['body']))

  def test_native_ui_and_runtime_identity(self):
    status, runtime = self.request('/data/runtime.json')
    self.assertEqual(status, 200)
    self.assertEqual(runtime['monitor'], 'local')
    self.assertEqual(len(runtime['instance']), 16)
    status, hub = self.request('/api/settings/pages/hub')
    self.assertEqual(status, 200)
    self.assertTrue(hub['rows'])
    self.assertTrue(any(row.get('page') for row in hub['rows']))

  def test_display_preference_round_trip_and_cookie_isolation(self):
    status, page = self.request('/api/settings/pages/display')
    self.assertEqual(status, 200)
    index = next(i for i, row in enumerate(page['rows']) if row['label'] == 'Custom Display Settings')
    status, preview = self.request('/api/settings/preview', {'view': page['view'], 'row': index, 'direction': 1})
    self.assertEqual(status, 200)
    self.assertFalse(self.params.get_bool('StarPilotDisplayPreferencesEnabled'))
    other = self.proxy.new_session()
    status, _ = self.request('/api/settings/confirm', {'intent': preview['intent'], 'confirmed': True}, proxy=other)
    self.assertNotEqual(status, 200)
    status, result = self.request('/api/settings/confirm', {'intent': preview['intent'], 'confirmed': True})
    self.assertEqual((status, result), (200, {'saved': True}))
    self.assertTrue(self.params.get_bool('StarPilotDisplayPreferencesEnabled'))
    self.assertNotEqual(self.proxy.cookie, other.cookie)

  def test_fresh_handshake_rejects_old_preview(self):
    status, page = self.request('/api/settings/pages/display')
    self.assertEqual(status, 200)
    index = next(i for i, row in enumerate(page['rows']) if row['label'] == 'Custom Display Settings')
    status, preview = self.request('/api/settings/preview', {'view': page['view'], 'row': index, 'direction': 1})
    self.assertEqual(status, 200)
    # A fresh encrypted handshake must not reuse an old page's mutation intent.
    other = self.proxy.new_session()
    status, _ = self.request('/api/settings/confirm', {'intent': preview['intent'], 'confirmed': True}, proxy=other)
    self.assertNotEqual(status, 200)
    self.assertFalse(self.params.get_bool('StarPilotDisplayPreferencesEnabled'))


if __name__ == '__main__':
  unittest.main()
