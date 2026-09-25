"""Actual local HTTP and native callback entry points, without cloud activation."""
import http.client
import json
import os
import platform
import uuid
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

from openpilot.starpilot.connect import provider
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server


class TestDeveloperProviderHTTP(unittest.TestCase):
  def test_authenticated_confirmed_offroad_pending_and_stale(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      access = GalaxyAccessOwner(root/'access')
      access.configure('password123', lambda: True)
      cloud_root = root/'cloud'
      class Cloud:
        def status(self):
          return provider.status(cloud_root)
        def select(self, name, revision, authorized):
          return provider.select_provider(name, revision, authorized, root=cloud_root, boot=lambda: 'test-boot')
      offroad = True
      server = make_server(port=0, owner=access, parked=lambda: True, cloud_offroad=lambda: offroad, cloud_provider=Cloud())
      worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
      worker.start()
      def request(path, payload=None, cookie=None):
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        headers = {'Forwarded': 'for=203.0.113.8', 'Origin': f'http://127.0.0.1:{server.server_port}', 'Content-Type': 'application/json'}
        if cookie:
          headers['Cookie'] = cookie
        try:
          connection.request('GET' if payload is None else 'POST', path, None if payload is None else json.dumps(payload), headers)
          response = connection.getresponse()
          return response.status, json.loads(response.read()), dict(response.getheaders())
        finally:
          connection.close()
      try:
        self.assertEqual(request('/api/connect/provider')[0], 401)
        code, _, headers = request('/api/auth/login', {'password': 'password123'})
        self.assertEqual(code, 200)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        code, state, _ = request('/api/connect/provider', cookie=cookie)
        self.assertEqual(code, 200)
        self.assertTrue(state['canSelect'])
        body = {'provider': 'konik', 'revision': state['revision'], 'confirmed': True}
        offroad = False
        self.assertEqual(request('/api/connect/provider', body, cookie)[0], 403)
        offroad = True
        self.assertEqual(request('/api/connect/provider', {**body, 'confirmed': False}, cookie)[0], 409)
        code, pending, _ = request('/api/connect/provider', body, cookie)
        self.assertEqual(code, 200)
        self.assertEqual(pending['active'], 'comma')
        self.assertEqual(pending['selected'], 'konik')
        self.assertTrue(pending['restartRequired'])
        self.assertEqual(request('/api/connect/provider', body, cookie)[0], 409)
      finally:
        server.shutdown()
        server.server_close()
        worker.join(2)


class TestNativeProviderCallbacks(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    # Device msgq subscribers require real publishers before native UIState import.
    # The installer test process supplies its isolated OPENPILOT_PREFIX namespace.
    cls.namespace = patch.dict(os.environ, {
      'OPENPILOT_PREFIX': os.environ.get('OPENPILOT_PREFIX') or 'connect-native-' + uuid.uuid4().hex,
      'USE_MSGQ_PREFIX': 'true',
    })
    cls.namespace.start()
    cls.addClassCleanup(cls.namespace.stop)
    shm_root = Path('/tmp' if platform.system() == 'Darwin' else '/dev/shm')
    (shm_root/('msgq_' + os.environ['OPENPILOT_PREFIX'])).mkdir(exist_ok=True)
    from openpilot.cereal import messaging
    cls.publishers = messaging.PubMaster([
      'modelV2', 'controlsState', 'onroadEvents', 'extrinsicsCalibration', 'radarState',
      'deviceState', 'pandaStates', 'carParams', 'driverMonitoringState', 'carState',
      'driverStateV2', 'narrowRoadCameraState', 'wideRoadCameraState', 'managerState',
      'selfdriveState', 'starpilotSelfdriveState', 'starpilotLateralState', 'starpilotNavigation',
      'longitudinalPlan', 'gpsLocationExternal', 'carOutput', 'carControl', 'slcState',
      'vehicleParameters', 'testJoystick', 'rawAudioData',
    ])

  @classmethod
  def tearDownClass(cls):
    del cls.publishers

  def test_confirmation_rechecks_offroad_and_revision(self):
    from openpilot.starpilot.connect import settings
    controls = []
    def accept(title, icon, callback):
      button = MagicMock()
      button.callback = callback
      controls.append(button)
      return button
    with (patch.object(settings.NavScroller, '__init__', lambda self: setattr(self, '_scroller', MagicMock())),
          patch.object(settings, 'GreyBigButton'), patch.object(settings, 'BigDialog'),
          patch.object(settings, 'BigConfirmationCircleButton', side_effect=accept),
          patch.object(settings.gui_app, 'texture'), patch.object(settings.gui_app, 'push_widget'),
          patch.object(settings.ui_state, 'is_offroad', return_value=False), patch.object(settings, 'select_provider') as select):
      page = settings.CloudProviderConfirmation('konik', 'revision', lambda: None)
      page.dismiss = MagicMock()
      def refuse(name, revision, authorized):
        self.assertEqual((name, revision), ('konik', 'revision'))
        if not authorized():
          raise ValueError('onroad')
      select.side_effect = refuse
      controls[0].callback()
      page.dismiss.assert_not_called()
      with patch.object(settings.ui_state, 'is_offroad', return_value=True):
        controls[0].callback()
      page.dismiss.assert_called_once()

  def test_pairing_url_is_provider_bound_and_offline_avoids_key(self):
    from openpilot.selfdrive.ui.widgets import pairing_dialog
    page = pairing_dialog.PairingDialog.__new__(pairing_dialog.PairingDialog)
    page.qr_texture = None
    page.params = MagicMock()
    page.params.get.return_value = '0123456789abcdef'
    with patch.object(pairing_dialog, 'Api') as api:
      api.return_value.get_token.return_value = 'pair-token'
      for name, expected in (('comma', 'https://connect.comma.ai'), ('konik', 'https://stable.konik.ai')):
        with patch.object(pairing_dialog, 'active_provider', return_value=provider.PROVIDERS[name]):
          self.assertEqual(page._get_pairing_url(), expected+'/?pair=pair-token')
      api.reset_mock()
      with patch.object(pairing_dialog, 'active_provider', return_value=provider.OFFLINE):
        with self.assertRaises(RuntimeError):
          page._get_pairing_url()
      api.assert_not_called()
