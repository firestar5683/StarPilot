"""Setup never downloads packages and never turns on the shared Bluetooth radio."""
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

  def test_power_off_never_starts_bluetooth_or_bridge(self):
    self.installed()
    with patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=False):
      self.worker.step()
    self.assertFalse(any('start' in call and UNIT in call for call in self.calls))
    self.assertFalse(any('bluetooth.service' in call for call in self.calls))
    self.assertTrue(any('stop' in call and UNIT in call for call in self.calls))

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
