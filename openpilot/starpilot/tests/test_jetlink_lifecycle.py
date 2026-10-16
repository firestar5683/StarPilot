"""Opt-in process ownership and remote shutdown before manager cleanup."""
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
  def jetlink(self, on):
    link = Mock()
    for name, value in (('hooks', lambda: link), ('link_on', lambda: on)):
      patcher = patch(f'openpilot.starpilot.models.jetlink_adapter.{name}', value)
      patcher.start()
      self.addCleanup(patcher.stop)
    return link

  def test_with_the_link_off_jetlink_is_never_bound(self):
    from jetlink.openpilot.hooks import Hooks
    from openpilot.starpilot.models.jetlink_adapter import API
    self.jetlink(False)
    factory = Mock()
    with patch('openpilot.starpilot.models.jetlink_adapter.hooks', lambda: Hooks(API, factory, link_on=lambda: False)):
      self.assertFalse(lifecycle.enabled(None))
      lifecycle.shutdown(SimpleNamespace(get_bool=lambda key: key == 'DoShutdown'))
    factory.assert_not_called()

  def test_the_owner_follows_jetlink(self):
    link = self.jetlink(True)
    for available in (True, False):
      link.should_run.return_value = available
      self.assertEqual(lifecycle.enabled(None), available)

  def test_only_power_off_asks_the_host_and_is_capped(self):
    link = self.jetlink(True)
    for reason in (None, 'DoReboot', 'DoUninstall', 'DoShutdown'):
      link.shutdown_step.reset_mock()
      link.shutdown_step.return_value = True
      params = SimpleNamespace(get_bool=lambda key, reason=reason: key == reason)
      lifecycle.shutdown(params)
      if reason == 'DoShutdown':
        link.shutdown_step.assert_called_once_with(True, 'DoShutdown')
      else:
        link.shutdown_step.assert_not_called()

    # a host that never answers holds the power-off for the cap, no longer
    now, waits = [0.], []

    def sleep(seconds):
      waits.append(seconds)
      if len(waits) > 1000:
        raise AssertionError("the power-off wait has no cap")
      now[0] += seconds
    link.shutdown_step.return_value = False
    lifecycle.shutdown(params, clock=lambda: now[0], sleep=sleep)
    self.assertGreaterEqual(now[0], lifecycle.SHUTDOWN_CAP_S)
    self.assertLess(now[0], lifecycle.SHUTDOWN_CAP_S + 1)

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
      from openpilot.starpilot.models import jetlink_adapter
      jetlink_adapter.hooks.cache_clear()
      self.addCleanup(jetlink_adapter.hooks.cache_clear)
      with patch('jetlink.openpilot.parts.Parts.chestnut_fitted', return_value=False), \
           patch('openpilot.common.hardware.HARDWARE.get_device_type', return_value='tizi'):
        for value, mode in ((0, 'off'), (1, 'usb'), (2, 'ios'), (3, 'off'), (-1, 'off')):
          with self.subTest(value=value):
            params.put('JetlinkMode', value, block=True)
            self.assertIs(type(params.get('JetlinkMode')), int)
            self.assertEqual(params.get('JetlinkMode'), value)
            self.assertEqual(FileParams(config.params_dir).get_int('JetlinkMode'), value)
            self.assertEqual(settings.mode(), mode)
            self.assertEqual(jetlink_adapter.link_on(), value in (1, 2))
            self.assertEqual(lifecycle.enabled(params), value in (1, 2))
        params.put('JetlinkMode', 1, block=True)
        Path(params.get_param_path('JetlinkMode')).write_bytes(b'corrupt')
        self.assertEqual(settings.mode(), 'off')
        self.assertFalse(lifecycle.enabled(params))

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
