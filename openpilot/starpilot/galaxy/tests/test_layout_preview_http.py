import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from openpilot.common.params import Params
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.onroad_layout import OnroadLayoutOwner
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.ui.layout_preview_transport import PreviewService
from openpilot.starpilot.ui.onroad_customization import PARAM_KEY, default_document
from openpilot.starpilot.ui.tests.test_layout_preview_transport import png


class TestLayoutPreviewHttp(unittest.TestCase):
  def setUp(self):
    temp = tempfile.TemporaryDirectory()
    self.addCleanup(temp.cleanup)
    root = Path(temp.name)
    self.socket_path = root / 'ui.sock'
    self.params = Params(str(root / 'params'))
    self.parked = True
    self.owner = OnroadLayoutOwner(self.params, lambda: self.parked)
    self.rendered = []
    self.preview = PreviewService(lambda payload: self.rendered.append(payload) or png(),
                                  lambda: self.parked, self.socket_path, active_profile='large')
    self.preview.start()
    self.addCleanup(self.preview.close)
    self.server = make_server(port=0, owner=GalaxyAccessOwner(root / 'access'), layouts=self.owner,
                              layout_preview_socket=self.socket_path)
    self.worker = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    self.worker.start()
    self.addCleanup(self.stop)
    self.payload = {'document': default_document(), 'profile': 'large', 'scene': 'aol'}

  def stop(self):
    self.server.shutdown()
    self.worker.join(timeout=2)
    self.server.server_close()

  def request(self, path, payload=None, cookie='', *, origin=None, raw=None):
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=4)
    headers = {'Cookie': cookie}
    body = raw if raw is not None else json.dumps(payload) if payload is not None else None
    if body is not None:
      headers.update({'Content-Type': 'application/json', 'Origin': origin or f'http://127.0.0.1:{self.server.server_port}'})
    try:
      connection.request('POST' if body is not None else 'GET', path, body=body, headers=headers)
      response = connection.getresponse()
      return response.status, response.read(), dict(response.getheaders())
    finally:
      connection.close()

  def login(self):
    status, _, headers = self.request('/api/auth/session')
    self.assertEqual(status, 200)
    return headers['Set-Cookie'].split(';', 1)[0]

  def preview_with_pump(self, cookie):
    outcome = {}
    client = threading.Thread(target=lambda: outcome.setdefault('response', self.request('/api/ui/layout/preview', self.payload, cookie)))
    client.start()
    deadline = time.monotonic() + 4
    while client.is_alive() and time.monotonic() < deadline:
      self.preview.poll()
      client.join(0.01)
    self.assertFalse(client.is_alive())
    return outcome['response']

  def test_live_profile_png_and_no_saved_write(self):
    cookie = self.login()
    status, body, _ = self.request('/api/ui/layout', cookie=cookie)
    self.assertEqual(status, 200)
    self.assertEqual(json.loads(body)['activeProfile'], 'large')
    status, body, headers = self.preview_with_pump(cookie)
    self.assertEqual(status, 200)
    self.assertEqual(headers['Content-Type'], 'image/png')
    self.assertEqual(headers['Cache-Control'], 'no-store')
    self.assertEqual(body, png())
    self.assertEqual(self.rendered, [self.payload])
    self.assertIsNone(self.params.get(PARAM_KEY))
    self.preview.close()
    status, body, _ = self.request('/api/ui/layout', cookie=cookie)
    self.assertEqual(status, 200)
    self.assertIsNone(json.loads(body)['activeProfile'])
    self.assertEqual(self.request('/api/ui/layout/preview', self.payload, cookie)[0], 503)

  def test_auth_shape_origin_and_fresh_parked_guards(self):
    cookie = self.login()
    self.assertEqual(self.request('/api/ui/layout/preview', self.payload)[0], 401)
    self.assertEqual(self.request('/api/ui/layout/preview', self.payload, cookie, origin='http://evil.example')[0], 403)
    self.assertEqual(self.request('/api/ui/layout/preview', {**self.payload, 'extra': 1}, cookie)[0], 400)
    self.assertEqual(self.request('/api/ui/layout/preview', {**self.payload, 'scene': 'unknown'}, cookie)[0], 400)
    self.assertEqual(self.request('/api/ui/layout/preview', {**self.payload, 'document': {'version': 99}}, cookie)[0], 400)
    self.assertEqual(self.request('/api/ui/layout/preview', cookie=cookie,
                                  raw='{"scene":"aol","scene":"engaged"}')[0], 400)
    self.parked = False
    self.assertEqual(self.request('/api/ui/layout/preview', self.payload, cookie)[0], 403)
    self.assertEqual(self.rendered, [])
    self.parked = True
    self.preview.renderer = lambda payload: (setattr(self, 'parked', False), png())[1]
    self.assertEqual(self.preview_with_pump(cookie)[0], 403)
    self.assertIsNone(self.params.get(PARAM_KEY))


if __name__ == '__main__':
  unittest.main()
