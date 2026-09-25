import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.starpilot.bluetooth.radio_preference import RADIO_PREFERENCE, RadioPreference


class RadioPreferenceTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.namespace = self.root / 'd_tmp'
    self.namespace.mkdir()
    (self.root / 'd').symlink_to(self.namespace.name)
    self.preference = RadioPreference(self.root / 'd' / 'BluetoothEnabled')

  def test_service_file_is_global_not_application_prefix(self):
    with patch.dict(os.environ, {'OPENPILOT_PREFIX': 'private-drive'}):
      self.assertEqual(RadioPreference().path, Path('/data/params/d/BluetoothEnabled'))
      self.assertEqual(RADIO_PREFERENCE, RadioPreference().path)

  def test_read_does_not_create_or_enable_and_matches_service_newline_semantics(self):
    self.assertFalse(self.preference.enabled())
    self.assertFalse(self.preference.path.exists())
    for value, enabled in ((b'1', True), (b'1\n\n', True), (b'0', False), (b'1 ', False), (b'', False)):
      with self.subTest(value=value):
        self.preference.path.write_bytes(value)
        self.assertEqual(self.preference.enabled(), enabled)
        self.assertEqual(self.preference.path.read_bytes(), value)

  def test_explicit_change_is_atomic_and_rollback_restores_exact_bytes(self):
    for previous in (None, b'0\n', b'1\n\n', b''):
      with self.subTest(previous=previous):
        self.preference.path.unlink(missing_ok=True)
        if previous is not None:
          self.preference.path.write_bytes(previous)
        change = self.preference.begin(True)
        self.assertEqual(self.preference.path.read_bytes() if self.preference.path.exists() else None, previous)
        change.apply()
        self.assertEqual(self.preference.path.read_bytes(), b'1')
        change.verify()
        self.assertTrue(change.rollback())
        self.assertEqual(self.preference.path.read_bytes() if self.preference.path.exists() else None, previous)
        self.assertFalse(list(self.namespace.glob('.bluetooth-enable-*')))

  def test_namespace_switch_never_writes_or_rolls_back_into_new_namespace(self):
    next_namespace = self.root / 'next'
    next_namespace.mkdir()
    change = self.preference.begin(True)
    change.apply()
    self.preference.path.parent.unlink()
    self.preference.path.parent.symlink_to(next_namespace.name)
    with self.assertRaises(OSError):
      change.verify()
    self.assertFalse(change.rollback())
    self.assertEqual((self.namespace / 'BluetoothEnabled').read_bytes(), b'1')
    self.assertFalse((next_namespace / 'BluetoothEnabled').exists())

  def test_namespace_switch_before_apply_is_rejected(self):
    change = self.preference.begin(True)
    next_namespace = self.root / 'next'
    next_namespace.mkdir()
    self.preference.path.parent.unlink()
    self.preference.path.parent.symlink_to(next_namespace.name)
    with self.assertRaises(OSError):
      change.apply()
    self.assertFalse((self.namespace / 'BluetoothEnabled').exists())
    self.assertFalse((next_namespace / 'BluetoothEnabled').exists())

  def test_external_replace_with_same_bytes_is_not_owned_for_rollback(self):
    change = self.preference.begin(True)
    change.apply()
    replacement = self.namespace / 'external'
    replacement.write_bytes(b'1')
    replacement.replace(self.preference.path)
    self.assertFalse(change.rollback())
    self.assertEqual(self.preference.path.read_bytes(), b'1')

  def test_external_change_before_apply_is_not_overwritten(self):
    change = self.preference.begin(True)
    self.preference.path.write_bytes(b'0\n')
    with self.assertRaises(OSError):
      change.apply()
    self.assertEqual(self.preference.path.read_bytes(), b'0\n')

  def test_unsafe_or_oversized_files_are_rejected_before_changes(self):
    target = self.root / 'other'
    target.write_bytes(b'0')
    self.preference.path.symlink_to(target)
    with self.assertRaises(OSError):
      self.preference.begin(True)
    self.assertEqual(target.read_bytes(), b'0')
    self.preference.path.unlink()
    self.preference.path.write_bytes(b'0' * 17)
    with self.assertRaises(OSError):
      self.preference.begin(True)
    self.assertEqual(self.preference.path.read_bytes(), b'0' * 17)

  def test_failed_replace_preserves_original_bytes(self):
    self.preference.path.write_bytes(b'0\n')
    change = self.preference.begin(True)
    with patch('openpilot.starpilot.bluetooth.radio_preference.os.replace', side_effect=OSError('disk full')):
      with self.assertRaises(OSError):
        change.apply()
    self.assertFalse(change.rollback())
    self.assertEqual(self.preference.path.read_bytes(), b'0\n')
    self.assertFalse(list(self.namespace.glob('.bluetooth-enable-*')))
