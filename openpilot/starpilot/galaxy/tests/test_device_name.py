import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.starpilot.galaxy.device_name import DeviceName


class DeviceNameTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name) / 'galaxy'
    self.store = DeviceName(self.root)

  def test_name_survives_new_owner_and_does_not_change_pairing(self):
    self.assertEqual(self.store.read(), '')
    self.assertEqual(self.store.save('  Road comma 🟣  '), 'Road comma 🟣')
    self.assertEqual(DeviceName(self.root).read(), 'Road comma 🟣')
    identity = self.root / 'remote-v1.json'
    identity.write_bytes(b'unchanged pairing')
    self.assertEqual(self.store.save(''), '')
    self.assertEqual(identity.read_bytes(), b'unchanged pairing')
    self.assertEqual((self.root / self.store.FILE).stat().st_mode & 0o777, 0o600)
    self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)

  def test_rejects_controls_oversize_and_non_text_without_replacing_name(self):
    self.store.save('Desk')
    for value in ('x' * 41, 'new\nname', 'name\x00', 'name\x85', '\ud800', None, 4, {}):
      with self.subTest(value=repr(value)), self.assertRaises(ValueError):
        self.store.save(value)
      self.assertEqual(self.store.read(), 'Desk')

  def test_failed_replace_preserves_previous_name(self):
    self.store.save('Desk')
    with patch('openpilot.starpilot.galaxy.device_name.os.replace', side_effect=OSError('disk full')):
      with self.assertRaises(OSError):
        self.store.save('Road')
    self.assertEqual(self.store.read(), 'Desk')
    self.assertEqual(list(self.root.iterdir()), [self.root / self.store.FILE])

  def test_rejects_symlink_and_unreadable_record(self):
    self.store.save('Desk')
    path = self.root / self.store.FILE
    path.unlink()
    target = self.root / 'unrelated'
    target.write_text('other data')
    path.symlink_to(target)
    with self.assertRaises(OSError):
      self.store.read()
    path.unlink()
    path.write_text('{"version":1,"name":"Desk","extra":true}')
    os.chmod(path, 0o600)
    with self.assertRaises(ValueError):
      self.store.read()
    os.chmod(self.root, 0o755)
    with self.assertRaises(OSError):
      self.store.save('Road')
    self.assertEqual(target.read_text(), 'other data')
