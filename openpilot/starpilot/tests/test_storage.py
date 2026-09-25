"""StarPilot writable state shares one namespace without touching /persist."""

import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.starpilot.galaxy.access import AccessStatus, default_owner
from openpilot.starpilot.galaxy.drive_stats import DriveStatsOwner
from openpilot.starpilot.galaxy.remote import default_remote_pairing
from openpilot.starpilot.state_migration import prepare_manager_start
from openpilot.starpilot import storage


class TestStarPilotStorage(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.base = Path(temporary.name)
    for context in (patch('openpilot.common.hardware.PC', False),
                    patch.dict(os.environ, {'OPENPILOT_PREFIX': 'storage-test'})):
      context.start()
      self.addCleanup(context.stop)

  def test_desktop_keeps_existing_persist_location(self):
    with patch.object(storage, 'PC', True), patch.object(storage.Paths, 'persist_root', return_value=str(self.base / 'persist')):
      self.assertEqual(storage.starpilot_storage_root(), self.base / 'persist' / 'starpilot')

  def test_device_default_and_isolated_prefix(self):
    with patch.object(storage, 'PC', False), patch.object(storage, '_DEVICE_ROOT', self.base / 'data' / 'starpilot'):
      with patch.dict(os.environ, {'OPENPILOT_PREFIX': ''}):
        self.assertEqual(storage.starpilot_storage_root(), self.base / 'data' / 'starpilot')
      with patch.dict(os.environ, {'OPENPILOT_PREFIX': 'desk-123'}):
        self.assertEqual(storage.starpilot_storage_root(), self.base / 'data' / 'starpilot-desk-123')
      for unsafe in ('../other', '/tmp/other', 'a.b', 'x' * 65):
        with self.subTest(prefix=unsafe), patch.dict(os.environ, {'OPENPILOT_PREFIX': unsafe}):
          with self.assertRaises(ValueError):
            storage.starpilot_storage_root()

  def test_device_migration_and_galaxy_use_same_private_root(self):
    params = Params(str(self.base / 'params'))
    device_root = self.base / 'data' / 'starpilot'
    device_root.parent.mkdir()
    with patch.object(storage, 'PC', False), patch('openpilot.common.hardware.PC', False), \
         patch.object(storage, '_DEVICE_ROOT', device_root), \
         patch.dict(os.environ, {'OPENPILOT_PREFIX': 'desk'}):
      root = storage.starpilot_storage_root()
      prepare_manager_start(params, root)
      self.assertTrue((root / 'profiles').is_dir())
      owner = default_owner()
      self.assertEqual(owner.root, root / 'galaxy')
      self.assertIsNone(owner.legacy_root)
      self.assertTrue(owner.configure('fixture-password', lambda: True))
      self.assertEqual(owner.status().status, AccessStatus.CONFIGURED_LOCAL)
      self.assertEqual(owner.root.stat().st_mode & 0o777, 0o700)
      self.assertFalse(device_root.exists())

  def test_home_history_before_first_pairing_keeps_shared_storage_private(self):
    logs = self.base / 'logs'
    logs.mkdir()
    with patch.object(storage, 'starpilot_storage_root', return_value=self.base):
      history = DriveStatsOwner(root=logs, permitted=lambda: True)
      self.addCleanup(history.close)
      history.snapshot()
      deadline = time.monotonic() + 3
      while not history.store.exists() and time.monotonic() < deadline:
        time.sleep(.01)
      self.assertTrue(history.store.is_file())
      saved_history = history.store.read_bytes()
      owner = default_owner()
      pairing = default_remote_pairing()
      self.assertEqual(owner.status().status, AccessStatus.UNCONFIGURED)
      self.assertTrue(owner.configure('fixture-password', lambda: True))
      self.assertIsNotNone(pairing.pair('a' * 64))
      self.assertEqual(history.store.read_bytes(), saved_history)
      self.assertEqual(owner.root.stat().st_mode & 0o777, 0o700)

  def test_old_history_directory_permissions_are_tightened_without_changing_files(self):
    root = self.base / 'galaxy'
    root.mkdir(mode=0o700)
    with patch.object(storage, 'starpilot_storage_root', return_value=self.base):
      owner = default_owner()
      self.assertTrue(owner.configure('fixture-password', lambda: True))
      pairing = default_remote_pairing()
      self.assertIsNotNone(pairing.pair('a' * 64))
      (root / 'drive-stats.json').write_text('{"schemaVersion":1}')
      saved = {path.name: path.read_bytes() for path in root.iterdir()}
      root.chmod(0o755)
      self.assertEqual(default_owner().status().status, AccessStatus.CONFIGURED_LOCAL)
      self.assertTrue(owner.verify('fixture-password'))
      self.assertIsNotNone(default_remote_pairing().read())
      self.assertEqual(root.stat().st_mode & 0o777, 0o700)
      self.assertEqual({path.name: path.read_bytes() for path in root.iterdir()}, saved)

  def test_shared_storage_does_not_repair_symlink_or_writable_directory(self):
    outside = self.base / 'outside'
    outside.mkdir(mode=0o755)
    root = self.base / 'galaxy'
    root.symlink_to(outside, target_is_directory=True)
    with patch.object(storage, 'starpilot_storage_root', return_value=self.base):
      self.assertEqual(default_owner().status().status, AccessStatus.UNAVAILABLE)
      self.assertEqual(outside.stat().st_mode & 0o777, 0o755)
      root.unlink()
      root.mkdir()
      root.chmod(0o777)
      self.assertEqual(default_owner().status().status, AccessStatus.UNAVAILABLE)
      self.assertEqual(root.stat().st_mode & 0o777, 0o777)

  def test_private_directory_migration_does_not_admit_unsafe_credential_file(self):
    root = self.base / 'galaxy'
    root.mkdir(mode=0o755)
    (root / 'access-v1.json').write_text('{}')
    (root / 'access-v1.json').chmod(0o644)
    with patch.object(storage, 'starpilot_storage_root', return_value=self.base):
      self.assertEqual(default_owner().status().status, AccessStatus.UNAVAILABLE)
      self.assertEqual((root / 'access-v1.json').read_text(), '{}')
