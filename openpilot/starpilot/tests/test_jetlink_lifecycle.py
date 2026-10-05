"""Opt-in process ownership and remote shutdown before manager cleanup."""
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from openpilot.starpilot.system.jetlink import lifecycle


def _cleanup_child(ready, cleaned, release):
  import signal
  import time
  stopping = False

  def stop(signum, frame):
    nonlocal stopping
    stopping = True

  signal.signal(signal.SIGINT, stop)
  ready.set()
  while not stopping:
    time.sleep(.01)
  release.wait(2)
  cleaned.set()


class TestJetlinkLifecycle(unittest.TestCase):
  def setUp(self):
    hardware = patch('openpilot.common.hardware.HARDWARE.get_device_type', return_value='tizi')
    hardware.start()
    self.addCleanup(hardware.stop)

  def test_disabled_or_malformed_mode_never_imports_adapter(self):
    for mode in (None, 0, -1, 3, True, False, b'1', b'2', b'corrupt'):
      params = SimpleNamespace(get=lambda key, mode=mode: mode)
      with self.subTest(mode=mode), patch.dict(sys.modules, {'openpilot.starpilot.models.jetlink_adapter': None}):
        self.assertFalse(lifecycle.enabled(params))

  def test_selected_owner_requires_available_transport_without_chestnut(self):
    params = SimpleNamespace(get=lambda key: 1)
    link = Mock()
    adapter = SimpleNamespace(get_jetlink=Mock(return_value=link), supported_device=lambda: True)
    with patch.dict(sys.modules, {'openpilot.starpilot.models.jetlink_adapter': adapter}):
      for available in (True, False):
        link.enabled.return_value = available
        self.assertEqual(lifecycle.enabled(params), available)
      adapter.get_jetlink.return_value = None
      self.assertFalse(lifecycle.enabled(params))

  def test_only_power_actions_request_bounded_remote_shutdown(self):
    link = Mock()
    link.enabled.return_value = True
    adapter = SimpleNamespace(get_jetlink=lambda: link, supported_device=lambda: True)
    with patch.dict(sys.modules, {'openpilot.starpilot.models.jetlink_adapter': adapter}):
      for reason in (None, 'DoShutdown', 'DoReboot', 'DoUninstall'):
        link.shutdown.reset_mock()
        params = SimpleNamespace(get=lambda key: 2, get_bool=lambda key, reason=reason: key == reason)
        lifecycle.shutdown(params)
        if reason is None:
          link.shutdown.assert_not_called()
        else:
          link.shutdown.assert_called_once_with(reason, timeout=25.0)
      link.enabled.return_value = False
      link.shutdown.reset_mock()
      lifecycle.shutdown(params)
      link.shutdown.assert_not_called()

  def test_registered_native_int_and_owner_file_reader_agree(self):
    from pathlib import Path
    from jetlink.openpilot.settings import FileParams, Settings
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.starpilot.models.jetlink_adapter import owner_config

    with OpenpilotPrefix():
      params = Params()
      config = owner_config()
      settings = Settings(FileParams(config.params_dir), config.keys)
      link = Mock()
      link.enabled.return_value = True
      with patch('openpilot.starpilot.models.jetlink_adapter.get_jetlink', return_value=link):
        for value, mode in ((0, 'off'), (1, 'usb'), (2, 'ios'), (3, 'off'), (-1, 'off')):
          with self.subTest(value=value):
            params.put('JetlinkMode', value, block=True)
            self.assertIs(type(params.get('JetlinkMode')), int)
            self.assertEqual(params.get('JetlinkMode'), value)
            self.assertEqual(FileParams(config.params_dir).get_int('JetlinkMode'), value)
            self.assertEqual(settings.mode(), mode)
            self.assertEqual(lifecycle.enabled(params), value in (1, 2))
        params.put('JetlinkMode', 1, block=True)
        for device, supported in (('tizi', True), ('mici', True), ('tici', False), ('pc', False)):
          with self.subTest(device=device), patch('openpilot.common.hardware.HARDWARE.get_device_type', return_value=device):
            self.assertEqual(lifecycle.enabled(params), supported)
        Path(params.get_param_path('JetlinkMode')).write_bytes(b'corrupt')
        self.assertEqual(settings.mode(), 'off')
        self.assertFalse(lifecycle.enabled(params))

  def test_owner_releases_resources_before_blocked_worker_wait(self):
    import subprocess
    from openpilot.starpilot.system.jetlink.daemon import owner_class
    from jetlink.comma import owner as upstream
    from jetlink.comma import root
    from unittest.mock import call

    owner = owner_class()([], settings=SimpleNamespace(mode=lambda: 'usb'), chestnut_ids=frozenset())
    owner.stop = True
    owner.tuned = 'ios'
    owner.port = Mock()
    owner.close_link = Mock()
    owner.beat = Mock()
    order = Mock()
    order.attach_mock(owner.port.off, 'port')
    order.attach_mock(owner.close_link, 'close')
    worker = Mock()
    owner.worker = worker
    with patch.object(root, 'run', return_value=True) as restore, patch.object(upstream, 'WORKER_GRACE', 0):
      order.attach_mock(restore, 'restore')
      order.attach_mock(worker.wait, 'wait')
      worker.wait.side_effect = subprocess.TimeoutExpired('provision', .5)
      owner.stop_worker()
    self.assertEqual(order.mock_calls[:6], [call.port(), call.close(), call.restore('vm', 'restore', timeout=1.0),
                                         call.restore('udc', 'restore', timeout=1.0), call.restore('draw', 'on', timeout=1.0),
                                         call.wait(upstream.POLL)])
    worker.terminate.assert_called_once()
    worker.kill.assert_called_once()
    self.assertIsNone(owner.worker)
    self.assertIsNone(owner.tuned)

  def test_process_nonblocking_stop_and_blocking_signal_cleanup(self):
    import multiprocessing
    import time
    from openpilot.starpilot.system.jetlink.process import JetlinkProcess

    context = multiprocessing.get_context('spawn')
    ready = context.Event()
    cleaned = context.Event()
    release = context.Event()

    process = context.Process(target=_cleanup_child, args=(ready, cleaned, release))
    process.start()
    def cleanup():
      if process.is_alive():
        process.kill()
      process.join(.5)

    self.addCleanup(cleanup)
    self.assertTrue(ready.wait(2))
    owner = JetlinkProcess('jetlinkd', 'unused', lambda *args: True)
    vars(owner)['proc'] = process
    start = time.monotonic()
    owner.stop(block=False)
    owner.stop(block=False)
    self.assertLess(time.monotonic() - start, .5)
    self.assertTrue(owner.shutting_down)
    release.set()
    owner.stop(block=True)
    self.assertTrue(cleaned.is_set())
    self.assertEqual(process.exitcode, 0)
    self.assertIsNone(owner.proc)
    self.assertLess(time.monotonic() - start, 2)
