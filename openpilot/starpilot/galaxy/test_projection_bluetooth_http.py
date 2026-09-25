from unittest.mock import Mock
"""Real Galaxy HTTP/auth and file-owner regressions; radio/AA IPC replaced by fakes."""
import copy
import http.client
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.projection_layout import ProjectionLayoutOwner
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.system.android_auto.display_profile import record_screen
from openpilot.starpilot.system.android_auto.projection_layout import ProjectionLayoutSource
from openpilot.starpilot.ui.onroad_customization import default_document

CAR = '02:00:00:00:00:01'
SCREEN = {'version': 1, 'width': 1280, 'height': 720, 'margin_width': 0,
          'margin_height': 240, 'fps': 60, 'config_index': 0}

class Params:
  def __init__(self, root): self.root, self.enabled = root, True
  def get_param_path(self, key): return str(self.root / key)
  def get_bool(self, key):
    assert key == 'AndroidAutoEnabled'
    return self.enabled

class Bluetooth:
  def __init__(self): self.calls = []
  def snapshot(self, **kwargs):
    return {'version': 1, 'available': True, 'parked': True, 'powered': True,
            'discovering': False, 'devices': [], 'errorCode': None, 'pairing': None}
  def request(self, operation, **kwargs):
    self.calls.append((operation, kwargs))
    return self.snapshot()
  def cancel_session(self, identity): pass

class AA:
  def __init__(self):
    self.calls = []
    self.result: dict = {'handled': False}
    self.error = None
    self.http = None
  def call(self, command, **kwargs):
    self.calls.append((command, kwargs))
    assert command == 'bluetooth_action'
    assert set(kwargs) == {'source', 'operation', 'address'}
    assert self.http is not None
    code, data, _ = self.http('/api/android-auto/source/' + kwargs['source'])
    assert code == 200 and data == {'valid': True}, 'Real minted source proof was not live'
    if self.error:
      raise self.error
    return copy.deepcopy(self.result)

class ProjectionBluetoothHttpTest(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)
    self.params = Params(self.root)
    self.native = self.root / 'OnroadCustomizations'
    self.native.write_text(json.dumps(default_document()))
    self.native_before = self.native.read_bytes()
    self.screen = self.root / 'screen.json'
    record_screen(SCREEN, self.screen)
    self.layout_source = ProjectionLayoutSource(self.root / 'projection/document.json')
    self.parked = True
    self.layout = ProjectionLayoutOwner(self.params, lambda: self.parked, self.layout_source, self.screen)
    self.access = GalaxyAccessOwner(self.root / 'access')
    self.assertTrue(self.access.configure('password123', lambda: True))
    self.bluetooth, self.aa = Bluetooth(), AA()
    self.native_layout = SimpleNamespace(snapshot=lambda: {'document': default_document(), 'editable': True, 'revision': 'native'})
    self.server = make_server(port=0, owner=self.access, projection_layout=self.layout, layouts=self.native_layout,
      android_auto_setup=SimpleNamespace(enabled=lambda: self.params.enabled),
      android_auto_client=self.aa, bluetooth=self.bluetooth)
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

  def http(self, path, payload=None, cookie=''):
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=4)
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

  def layout_payload(self):
    code, value, _ = self.http('/api/android-auto/layout', cookie=self.cookie)
    self.assertEqual(code, 200)
    return {'revision': value['revision'], 'document': copy.deepcopy(value['document'])}

  def action(self, operation='connect', cookie=None):
    return self.http('/api/bluetooth/action', {'operation': operation, 'address': CAR},
                     self.cookie if cookie is None else cookie)

  def test_layout_requires_actual_auth_then_saves_only_projection_document(self):
    self.assertEqual(self.http('/api/android-auto/layout')[0], 401)
    payload = self.layout_payload()
    payload['document']['widgets']['current_speed']['x'] += 10
    self.assertEqual(self.http('/api/android-auto/layout', payload)[0], 401)
    code, result, _ = self.http('/api/android-auto/layout', payload, self.cookie)
    self.assertEqual(code, 200)
    self.assertTrue(result['valid'])
    self.assertEqual(json.loads(self.layout_source.path.read_bytes()), payload['document'])
    self.assertEqual(self.native.read_bytes(), self.native_before)

  def test_layout_stale_screen_revision_and_unpark_do_not_replace_saved_document(self):
    payload = self.layout_payload()
    self.assertEqual(self.http('/api/android-auto/layout', payload, self.cookie)[0], 200)
    before = self.layout_source.path.read_bytes()
    stale = self.layout_payload()
    record_screen(SCREEN | {'config_index': 1}, self.screen)
    self.assertEqual(self.http('/api/android-auto/layout', stale, self.cookie)[0], 409)
    fresh = self.layout_payload()
    self.parked = False
    self.assertEqual(self.http('/api/android-auto/layout', fresh, self.cookie)[0], 409)
    self.assertEqual(self.layout_source.path.read_bytes(), before)
    self.assertEqual(self.native.read_bytes(), self.native_before)

  def test_logged_out_session_cannot_save_layout_or_delegate_bluetooth(self):
    payload = self.layout_payload()
    self.assertEqual(self.http('/api/auth/logout', {}, self.cookie)[0], 200)
    self.assertEqual(self.http('/api/android-auto/layout', payload, self.cookie)[0], 401)
    self.assertEqual(self.action()[0], 401)
    self.assertEqual(self.aa.calls, [])
    self.assertEqual(self.bluetooth.calls, [])
    self.assertFalse(self.layout_source.path.exists())
    self.assertEqual(self.native.read_bytes(), self.native_before)

  def test_active_aa_handled_snapshot_never_calls_generic_controller(self):
    snapshot = self.bluetooth.snapshot()
    snapshot['devices'] = [{'address': CAR, 'name': 'IONIQ 6',
      'paired': True, 'trusted': True, 'connected': True}]
    self.aa.result = {'handled': True, 'bluetooth': snapshot}
    code, result, _ = self.action()
    self.assertEqual(code, 200)
    self.assertEqual(result, snapshot)
    self.assertEqual(self.bluetooth.calls, [])
    command, arguments = self.aa.calls[0]
    self.assertEqual((command, arguments['operation'], arguments['address']), ('bluetooth_action', 'connect', CAR))
    self.assertEqual(self.http('/api/android-auto/source/' + arguments['source'])[0], 410)

  def test_no_aa_lease_falls_back_once_and_disabled_aa_does_not_contact_daemon(self):
    self.assertEqual(self.action()[0], 200)
    self.assertEqual(len(self.aa.calls), 1)
    self.assertEqual(len(self.bluetooth.calls), 1)
    self.params.enabled = False
    self.assertEqual(self.action('disconnect')[0], 200)
    self.assertEqual(len(self.aa.calls), 1)
    self.assertEqual(len(self.bluetooth.calls), 2)
    self.assertEqual(self.bluetooth.calls[-1][0], 'disconnect')

  def test_owner_busy_and_error_codes_never_fall_back(self):
    for error, code in [('busy', 409), ('park_required', 409), ('changed', 409), ('service_unavailable', 503)]:
      self.aa.result = {'handled': True, 'error_code': error}
      actual, result, _ = self.action()
      self.assertEqual(actual, code)
      self.assertEqual(result['code'], error)
      self.assertEqual(self.bluetooth.calls, [])

  def test_unknown_or_malformed_delegated_error_fails_closed_without_fallback(self):
    for error in ('unexpected_internal_error', '', None, 4, {'private': 'detail'}):
      self.aa.result = {'handled': True, 'error_code': error}
      code, result, _ = self.action()
      self.assertEqual(code, 503)
      self.assertEqual(result['code'], 'service_unavailable')
      self.assertNotIn('unexpected_internal_error', json.dumps(result))
      self.assertEqual(self.bluetooth.calls, [])

  def test_native_layout_optional_projection_failure_preserves_native_snapshot(self):
    self.assertEqual(self.http('/api/ui/layout')[0], 401)
    for error in (OSError('saved screen unavailable'), ValueError('invalid screen'), RuntimeError('projection owner unavailable')):
      def unavailable(error=error):
        raise error
      self.layout.snapshot = Mock(side_effect=unavailable)
      code, result, _ = self.http('/api/ui/layout', cookie=self.cookie)
      self.assertEqual(code, 200)
      self.assertFalse(result['projectionAvailable'])
      self.assertEqual(result['document'], default_document())
      self.assertEqual(result['revision'], 'native')
      self.assertEqual(self.native.read_bytes(), self.native_before)
      self.assertEqual(self.aa.calls, [])

  def test_daemon_transport_failure_and_malformed_reply_never_fall_back(self):
    self.aa.error = TimeoutError('private IPC failure')
    code, result, _ = self.action()
    self.assertEqual(code, 503)
    self.assertEqual(result['code'], 'service_unavailable')
    self.assertNotIn('private', json.dumps(result))
    self.assertEqual(self.bluetooth.calls, [])
    self.aa.error = None
    for malformed in ({}, {'handled': 'yes'}, {'handled': True}, {'handled': True, 'bluetooth': []}):
      self.aa.result = malformed
      self.assertEqual(self.action()[0], 503)
      self.assertEqual(self.bluetooth.calls, [])

if __name__ == '__main__':
  unittest.main()
