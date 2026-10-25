"""Setup never downloads packages and never turns on the shared Bluetooth radio."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from openpilot.starpilot.galaxy_bluetooth.bootstrap import Bootstrap, UNIT


class BootstrapTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.data = self.root / 'data'
    self.data.mkdir()
    self.bridge = self.root / 'bridge'
    self.bridge.mkdir()
    self.params = Mock()
    self.params.get_bool.return_value = True
    self.calls = []
    def run(args, **kwargs):
      self.calls.append(args)
      return SimpleNamespace(stdout='1', returncode=0)
    self.worker = Bootstrap(self.params, self.data, self.bridge, run)

  def installed(self):
    from openpilot.starpilot.galaxy_bluetooth.bridge.pairing import add_phone
    add_phone('iPhone', self.data / 'pairing.json')

  def test_bridge_runs_before_any_phone_is_paired(self):
    with patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=True):
      self.worker.step()
    self.assertTrue(any('start' in call and UNIT in call for call in self.calls))
    from openpilot.starpilot.galaxy_bluetooth.bridge.pairing import load_keys
    self.assertEqual(load_keys(self.data / 'pairing.json'), {})  # empty list: no phone is accepted yet

  def test_status_written_only_on_change(self):
    with patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=False):
      self.worker.step()
      path = self.data / 'setup-status.json'
      path.unlink()
      self.worker.step()
    self.assertFalse(path.exists())

  def test_paired_bridge_starts_onroad_without_downloading(self):
    self.installed()
    self.params.get_bool.return_value = False
    with patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=True):
      self.worker.step()
    self.assertTrue(any('start' in call and UNIT in call for call in self.calls))
    joined = ' '.join(' '.join(call) for call in self.calls)
    for word in ('install', 'pip', 'uv ', 'venv'):
      self.assertNotIn(word, joined)

  def test_retry_restarts_bridge(self):
    from openpilot.starpilot.galaxy_bluetooth.bootstrap import retry_setup
    self.installed()
    retry_setup(self.data)
    with patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=True):
      self.worker.step()
      self.worker.step()
    self.assertEqual([call for call in self.calls if 'restart' in call], [['sudo', '-n', 'systemctl', 'restart', UNIT]])

  def test_open_pairing_during_startup_does_not_restart(self):
    from openpilot.starpilot.galaxy_bluetooth.bootstrap import retry_setup
    self.worker.registered = True
    self.worker.discovery_registered = True
    self.worker.next_attempt = float('inf')
    retry_setup(self.data, restart=False)
    with patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=True):
      self.worker.step()
    self.assertTrue(any('start' in call and UNIT in call for call in self.calls))
    self.assertFalse(any('restart' in call or 'link' in call for call in self.calls))

  def test_wake_preserves_explicit_retry(self):
    from openpilot.starpilot.galaxy_bluetooth.bootstrap import retry_setup
    retry_setup(self.data)
    retry_setup(self.data, restart=False)
    with patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=True):
      self.worker.step()
    self.assertEqual(len([call for call in self.calls if 'restart' in call]), 1)

  def test_power_off_never_starts_bluetooth_or_bridge(self):
    self.installed()
    with patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=False):
      self.worker.step()
    self.assertFalse(any('start' in call and UNIT in call for call in self.calls))
    self.assertFalse(any('bluetooth.service' in call for call in self.calls))
    self.assertTrue(any('stop' in call and UNIT in call for call in self.calls))

  def test_host_bridge_runs_in_the_isolated_runtime_without_systemd_units(self):
    from openpilot.starpilot.galaxy_bluetooth.bridge.pairing import ensure_store
    ensure_store(self.data / 'pairing.json')
    child = Mock(pid=1234)
    child.poll.return_value = None
    with patch.dict('os.environ', SP_HOST_RUNTIME='1', SP_HOST_BLUETOOTH_PREFERENCE=str(self.root / 'bluetooth' / 'BluetoothEnabled'),
                    SP_HOST_GALAXY_BLE_DATA=str(self.data)), \
         patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=True), \
         patch('openpilot.starpilot.galaxy_bluetooth.bridge.pairing.ensure_store'), \
         patch('openpilot.starpilot.galaxy_bluetooth.bootstrap.subprocess.Popen', return_value=child) as spawn:
      self.worker.step()
    self.assertEqual([call.args[0][1].split('/')[-1] for call in spawn.call_args_list], ['lan_discovery.py', 'server.py'])
    self.assertTrue(all(call.kwargs['cwd'] == self.bridge for call in spawn.call_args_list))
    self.assertTrue(all('vendor' in call.kwargs['env']['PYTHONPATH'] for call in spawn.call_args_list))
    self.assertFalse(self.calls)
    self.assertEqual(json.loads((self.data / 'setup-status.json').read_text())['state'], 'waiting')

  def test_only_bridge_and_discovery_start_when_radio_enabled(self):
    self.installed()
    with patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=True):
      self.worker.step()
    self.assertTrue(any('start' in call and UNIT in call for call in self.calls))
    self.assertFalse(any('bluetooth.service' in call for call in self.calls))

  def test_pairing_a_phone_never_restarts_the_bridge(self):
    from openpilot.starpilot.galaxy_bluetooth.bridge.pairing import add_phone
    self.installed()
    with patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=True):
      self.worker.step()
      add_phone('Android phone', self.data / 'pairing.json')
      self.worker.step()
    self.assertFalse(any('restart' in call for call in self.calls))
    self.assertFalse(any('bluetooth.service' in call for call in self.calls))

if __name__ == '__main__':
  unittest.main()
