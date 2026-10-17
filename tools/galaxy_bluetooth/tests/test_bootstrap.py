import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
  spec = importlib.util.spec_from_file_location(name, path)
  result = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(result)
  return result


boot = module('bootstrap', ROOT / 'bootstrap.py')
backup = module('settings_backup', ROOT / 'settings_backup.py')


class BootstrapTests(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.root = Path(self.tmp.name)
    self.data = self.root / 'bridge-data'
    self.data.mkdir()
    self.bridge = self.root / 'source'
    self.bridge.mkdir()
    (self.bridge / 'requirements.txt').write_text('dbus-next==0.2.3\n')
    self.key = self.data / 'pairing.json'
    self.key.write_text('existing private key')
    self.params = Mock()
    self.params.get_bool.return_value = False
    self.run = Mock(return_value=SimpleNamespace(stdout='123\n'))
    self.worker = boot.Bootstrap(self.params, self.data, self.bridge, self.run)

  def installed(self):
    python = self.data / 'venv/bin/python'
    python.parent.mkdir(parents=True)
    python.touch()
    (self.data / 'installed-requirements').write_text(hashlib.sha256((self.bridge / 'requirements.txt').read_bytes()).hexdigest())

  def installers(self):
    return [call for call in self.run.call_args_list if call.args[0][0] == 'sh']

  def test_existing_install_starts_offline_without_reinstall(self):
    self.installed()
    boot.write_json(self.data / 'bridge-ready.json', {'pid': 123})
    self.worker.step()
    self.worker.step()
    self.assertEqual(self.installers(), [])
    self.assertEqual(boot.setup_status(self.data), 'Ready to pair')
    self.assertEqual(self.key.read_text(), 'existing private key')
    self.params.put_bool.assert_not_called()
    self.params.clear_all.assert_not_called()

  def test_discovery_start_failure_does_not_block_bluetooth(self):
    self.installed()
    def run(args, **kwargs):
      if boot.LAN_UNIT in args:
        raise subprocess.CalledProcessError(1, args)
      return SimpleNamespace(stdout='123\n')
    self.run.side_effect = run
    boot.write_json(self.data / 'bridge-ready.json', {'pid': 123})
    self.worker.step()
    self.assertEqual(boot.setup_status(self.data), 'Ready to pair')
    self.assertTrue(any(call.args[0] == ['sudo', '-n', 'systemctl', 'start', boot.UNIT]
                        for call in self.run.call_args_list))
    self.assertEqual(self.key.read_text(), 'existing private key')

  def test_discovery_unit_is_linked_once_and_started_independently(self):
    self.installed()
    self.worker.step()
    self.worker.step()
    calls = [call.args[0] for call in self.run.call_args_list]
    links = [args for args in calls if 'link' in args and args[-1].endswith(boot.LAN_UNIT)]
    self.assertEqual(len(links), 1)
    self.assertEqual(calls.count(['sudo', '-n', 'systemctl', 'start', boot.LAN_UNIT]), 2)

  def test_dependency_change_waits_until_parked(self):
    self.installed()
    (self.bridge / 'requirements.txt').write_text('new version')
    self.params.get_bool.return_value = True
    self.worker.step()
    self.assertEqual(self.installers(), [])
    self.assertIn('Park', boot.setup_status(self.data))
    self.params.get_bool.return_value = False
    self.worker.step()
    self.worker.step()
    self.assertEqual(len(self.installers()), 1)
    self.assertEqual(self.key.read_text(), 'existing private key')

  def test_failure_is_retried_without_erasing_existing_data(self):
    def run(args, **kwargs):
      if args[0] == 'sh':
        raise subprocess.CalledProcessError(1, args)
      return SimpleNamespace(stdout='123\n')
    self.run.side_effect = run
    self.worker.step()
    self.worker.step()
    self.assertEqual(len(self.installers()), 1)
    self.assertFalse((self.data / 'installed-requirements').exists())
    boot.retry_setup(self.data)
    self.worker.step()
    self.assertEqual(len(self.installers()), 2)
    self.assertEqual(self.key.read_text(), 'existing private key')
    self.assertNotIn('existing private key', (self.data / 'setup.log').read_text())

  def test_stale_ready_file_does_not_claim_connected(self):
    self.installed()
    boot.write_json(self.data / 'bridge-ready.json', {'pid': 111})
    self.worker.step()
    self.assertIn('Waiting', boot.setup_status(self.data))

  def test_settings_snapshot_preserves_bytes_and_first_copy(self):
    params = self.root / 'params'
    params.mkdir()
    values = {'CalibrationParams': b'\x00\xffcalibration', 'CustomFollow': b'1.42', 'GithubSshKeys': b'private'}
    for key, value in values.items():
      (params / key).write_bytes(value)
    target = backup.backup_settings(self.data, [str(params)])
    self.assertEqual(target.stat().st_mode & 0o777, 0o600)
    with tarfile.open(target) as archive:
      for key, value in values.items():
        self.assertEqual(archive.extractfile(str(params / key).lstrip('/')).read(), value)
    original = target.read_bytes()
    (params / 'CustomFollow').write_bytes(b'2')
    backup.backup_settings(self.data, [str(params)])
    self.assertEqual(target.read_bytes(), original)
    self.assertEqual((params / 'CalibrationParams').read_bytes(), values['CalibrationParams'])


if __name__ == '__main__':
  unittest.main()

