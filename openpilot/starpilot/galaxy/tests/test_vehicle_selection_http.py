import http.client
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

from openpilot.common.params import Params
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.galaxy.vehicle_selection import VehicleSelectionGateway
from openpilot.starpilot.saved_document import WriteResult
from openpilot.starpilot.vehicle_selection import KEY, VehicleSelectionOwner, read_selection


class Context:
  def __init__(self):
    self.allowed = True
    self.reported = None

  def parked(self):
    return self.allowed

  def sample(self):
    return SimpleNamespace(cp=self.reported)


class VehicleSelectionHttpTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.context = Context()
    self.gateway = VehicleSelectionGateway(self.params, self.context)
    access = GalaxyAccessOwner(Path(temporary.name) / 'access')
    self.assertTrue(access.configure('password123', lambda: True))
    self.server = make_server(port=0, owner=access, vehicle_selection=self.gateway)
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

  def login(self):
    code, _, headers = self.request('/api/auth/login', {'password': 'password123'})
    self.assertEqual(code, 200)
    return headers['Set-Cookie'].split(';', 1)[0]

  def test_authenticated_auto_manual_confirmation_and_reported_identity(self):
    self.assertEqual(self.request('/api/vehicle-selection')[0], 401)
    cookie = self.login()
    code, page, _ = self.request('/api/vehicle-selection', cookie=cookie)
    self.assertEqual(code, 200)
    self.assertTrue(page['parked'] and page['valid'])
    self.assertIsNone(page['selected'])
    self.assertEqual(page['selectedLabel'], 'Auto detection')
    self.assertIsNone(page['reported'])
    self.assertNotIn('MOCK', [item['platform'] for item in page['choices']])
    selected = page['choices'][0]
    self.context.reported = SimpleNamespace(carFingerprint=selected['platform'], notCar=False)
    other_cookie = self.login()
    self.assertEqual(self.request('/api/vehicle-selection/preview',
                                  {'view': page['view'], 'platform': selected['platform']}, other_cookie)[0], 409)
    code, preview, _ = self.request('/api/vehicle-selection/preview', {'view': page['view'], 'platform': selected['platform']}, cookie)
    self.assertEqual(code, 200)
    self.assertIn('next start', preview['question'])
    self.assertIsNone(read_selection(self.params).raw)
    self.assertEqual(self.request('/api/vehicle-selection/confirm', {'intent': preview['intent'], 'confirmed': True}, cookie)[0], 200)
    self.assertEqual(self.request('/api/vehicle-selection/confirm', {'intent': preview['intent'], 'confirmed': True}, cookie)[0], 409)
    readback = self.request('/api/vehicle-selection', cookie=cookie)[1]
    self.assertEqual(readback['selected'], selected['platform'])
    self.assertEqual(readback['reported']['platform'], selected['platform'])
    self.assertNotEqual(readback['selectedLabel'], 'Auto detection')
    self.assertEqual(self.request('/api/auth/logout', {}, cookie)[0], 200)
    self.assertEqual(self.request('/api/vehicle-selection', cookie=cookie)[0], 401)
    self.assertEqual(self.request('/api/vehicle-selection/confirm', {'intent': preview['intent'], 'confirmed': True}, cookie)[0], 401)

  def test_invalid_saved_source_explicit_auto_repair_and_parked_revocation(self):
    cookie = self.login()
    Path(self.params.get_param_path(KEY)).write_bytes(b'bad-document')
    page = self.request('/api/vehicle-selection', cookie=cookie)[1]
    self.assertFalse(page['valid'])
    self.assertEqual(page['selectedLabel'], 'Needs review')
    self.assertEqual(self.request('/api/vehicle-selection/preview',
                                  {'view': page['view'], 'platform': page['choices'][0]['platform']}, cookie)[0], 409)
    code, repair, _ = self.request('/api/vehicle-selection/preview', {'view': page['view'], 'platform': None}, cookie)
    self.assertEqual(code, 200)
    self.context.allowed = False
    self.assertEqual(self.request('/api/vehicle-selection/confirm', {'intent': repair['intent'], 'confirmed': True}, cookie)[0], 409)
    self.assertEqual(Path(self.params.get_param_path(KEY)).read_bytes(), b'bad-document')
    self.context.allowed = True
    page = self.request('/api/vehicle-selection', cookie=cookie)[1]
    repair = self.request('/api/vehicle-selection/preview', {'view': page['view'], 'platform': None}, cookie)[1]
    self.assertEqual(self.request('/api/vehicle-selection/confirm', {'intent': repair['intent'], 'confirmed': True}, cookie)[0], 200)
    self.assertTrue(read_selection(self.params).valid)
    self.assertIsNone(read_selection(self.params).platform)

  def test_stale_view_and_bad_request_never_write(self):
    cookie = self.login()
    page = self.request('/api/vehicle-selection', cookie=cookie)[1]
    self.params.put(KEY, {'version': 1, 'platform': None}, block=True)
    self.assertEqual(self.request('/api/vehicle-selection/preview', {'view': page['view'], 'platform': None}, cookie)[0], 409)
    self.assertEqual(self.request('/api/vehicle-selection/preview', {'view': 123, 'platform': None}, cookie)[0], 400)
    self.assertEqual(self.request('/api/vehicle-selection/confirm', {'intent': 'unknown', 'confirmed': True}, cookie)[0], 409)
    self.assertIsNone(read_selection(self.params).platform)

  def test_postcommit_uncertainty_requires_readback_before_retry(self):
    cookie = self.login()
    page = self.request('/api/vehicle-selection', cookie=cookie)[1]
    intent = self.request('/api/vehicle-selection/preview', {'view': page['view'], 'platform': None}, cookie)[1]['intent']
    with patch.object(VehicleSelectionOwner, 'choose', return_value=WriteResult(True, False)):
      code, result, _ = self.request('/api/vehicle-selection/confirm', {'intent': intent, 'confirmed': True}, cookie)
    self.assertEqual(code, 409)
    self.assertEqual(result['code'], 'unverified')
    self.assertEqual(self.request('/api/vehicle-selection/confirm', {'intent': intent, 'confirmed': True}, cookie)[0], 409)


if __name__ == '__main__':
  unittest.main()
