"""Setup is offroad-only and never turns on the shared Bluetooth radio."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from openpilot.starpilot.galaxy_bluetooth.bootstrap import Bootstrap, UNIT, refresh_pairing


class BootstrapTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.data = self.root / 'data'
    self.data.mkdir()
    self.bridge = self.root / 'bridge'
    self.bridge.mkdir()
    (self.bridge / 'requirements.txt').write_text('test requirements')
    self.params = Mock()
    self.params.get_bool.return_value = True
    self.calls = []
    def run(args, **kwargs):
      self.calls.append(args)
      return SimpleNamespace(stdout='1', returncode=0)
    self.uplink = False
    self.worker = Bootstrap(self.params, self.data, self.bridge, run, uplink_active=lambda: self.uplink)

  def installed(self):
    python = self.data / 'venv/bin/python'
    python.parent.mkdir(parents=True)
    python.touch()
    (self.data / 'installed-requirements').write_text(hashlib.sha256((self.bridge / 'requirements.txt').read_bytes()).hexdigest())
    (self.data / 'pairing.json').write_text('{}')

  def test_missing_dependencies_wait_until_offroad(self):
    self.params.get_bool.return_value = False
    self.worker.step()
    self.assertFalse(self.calls)
    self.assertEqual(json.loads((self.data / 'setup-status.json').read_text())['state'], 'waiting')

  def test_missing_dependencies_wait_while_phone_shares_internet(self):
    self.uplink = True
    self.worker.step()
    self.assertFalse(self.calls)
    status = json.loads((self.data / 'setup-status.json').read_text())
    self.assertEqual(status['state'], 'waiting')
    self.assertIn('phone internet sharing', status['message'])

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
    self.assertFalse(any('install.sh' in ' '.join(call) for call in self.calls))

  def test_pairing_refresh_restarts_only_bridge_and_only_offroad(self):
    self.installed()
    refresh_pairing(self.data)
    self.params.get_bool.return_value = False
    with patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=True):
      self.worker.step()
      self.assertFalse(any('restart' in call for call in self.calls))
      self.assertTrue((self.data / 'refresh-pairing.json').exists())
      self.params.get_bool.return_value = True
      self.worker.step()
      self.assertEqual([call for call in self.calls if 'restart' in call], [['sudo', '-n', 'systemctl', 'restart', UNIT]])
      self.assertFalse((self.data / 'refresh-pairing.json').exists())
      self.worker.step()
      self.assertEqual(sum('restart' in call for call in self.calls), 1)
    self.assertFalse(any('bluetooth.service' in call for call in self.calls))

  def test_pairing_refresh_respects_radio_off(self):
    self.installed()
    refresh_pairing(self.data)
    with patch('openpilot.starpilot.bluetooth.radio_preference.RadioPreference.enabled', return_value=False):
      self.worker.step()
    self.assertFalse(any('restart' in call for call in self.calls))


if __name__ == '__main__': unittest.main()
