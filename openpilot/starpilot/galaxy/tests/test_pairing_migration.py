import hashlib
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from openpilot.starpilot.galaxy.remote import RemotePairing, default_remote_pairing, gateway_cookie_valid


class TestPairingMigration(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)
    self.legacy = self.root / 'legacy'
    self.legacy.mkdir()
    self.values = {'glxyslug': 'ExistingGalaxy01', 'glxyauth': hashlib.sha256(b'old-password').hexdigest(),
                   'glxysession': 'a' * 64}
    for key, value in self.values.items():
      (self.legacy / key).write_text(value + '\n')
    self.pairing = RemotePairing(self.root / 'new')

  def test_default_startup_keeps_link_password_and_session_without_password_entry(self):
    original = {path.name: path.read_bytes() for path in self.legacy.iterdir()}
    with patch('openpilot.starpilot.storage.galaxy_storage_root', return_value=self.pairing.root), \
         patch('openpilot.starpilot.galaxy.access.legacy_galaxy_root', return_value=self.legacy):
      pairing = default_remote_pairing()
      record = pairing.read()
      self.assertEqual(record, {'version': 1, 'slug': self.values['glxyslug'], 'authHash': self.values['glxyauth'],
                                'session': self.values['glxysession']})
      self.assertEqual(pairing.url(record['slug']), 'https://galaxy.firestar.link/ExistingGalaxy01')
      self.assertTrue(gateway_cookie_valid(record['slug'] + ':' + record['session'], record))
      saved = (pairing.root / pairing.FILE).read_bytes()
      self.assertEqual(default_remote_pairing().read(), record)
      self.assertEqual((pairing.root / pairing.FILE).read_bytes(), saved)
      self.assertEqual((pairing.root / pairing.FILE).stat().st_mode & 0o777, 0o600)
    self.assertEqual({path.name: path.read_bytes() for path in self.legacy.iterdir()}, original)
    self.assertFalse((self.pairing.root / 'access-v1.json').exists())

  def test_unpair_survives_restart_and_manual_repair_rotates_identity(self):
    self.assertTrue(self.pairing.migrate_legacy(self.legacy))
    old = self.pairing.read()
    self.assertTrue(self.pairing.unpair())
    restarted = RemotePairing(self.pairing.root)
    self.assertFalse(restarted.migrate_legacy(self.legacy))
    self.assertIsNone(restarted.read())
    self.assertIsNotNone(restarted.pair(old['authHash'], legacy_root=self.legacy))
    new = restarted.read()
    self.assertNotEqual(new['slug'], old['slug'])
    self.assertNotEqual(new['session'], old['session'])
    self.assertFalse(gateway_cookie_valid(old['slug'] + ':' + old['session'], new))

  def test_existing_and_malformed_destination_are_never_replaced(self):
    self.assertIsNotNone(self.pairing.pair('b' * 64))
    path = self.pairing.root / self.pairing.FILE
    before = path.read_bytes()
    self.assertFalse(self.pairing.migrate_legacy(self.legacy))
    self.assertEqual(path.read_bytes(), before)
    path.write_text('incomplete')
    self.assertFalse(self.pairing.migrate_legacy(self.legacy))
    self.assertIsNone(self.pairing.pair('c' * 64))
    self.assertEqual(path.read_text(), 'incomplete')

  def test_partial_or_invalid_legacy_does_not_create_pairing(self):
    for name in self.values:
      path = self.legacy / name
      original = path.read_bytes()
      for raw in (None, b'bad', b'x' * 129, b'\xff'):
        with self.subTest(name=name, raw=raw):
          path.unlink(missing_ok=True)
          if raw is not None:
            path.write_bytes(raw)
          self.assertFalse(self.pairing.migrate_legacy(self.legacy))
          self.assertIsNone(self.pairing.read())
      path.write_bytes(original)

  def test_previous_local_setup_requires_explicit_pairing(self):
    from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
    owner = GalaxyAccessOwner(self.pairing.root)
    self.assertTrue(owner.configure('new-password', lambda: True))
    self.assertFalse(self.pairing.migrate_legacy(self.legacy))
    self.assertIsNone(self.pairing.read())
    self.assertTrue(owner.verify('new-password'))
    self.assertIsNotNone(self.pairing.pair(self.values['glxyauth'], legacy_root=self.legacy))

  def test_unsafe_legacy_and_destination_paths_are_not_followed(self):
    path = self.legacy / 'glxyslug'
    original = path.read_bytes()
    outside = self.root / 'outside'
    outside.write_bytes(original)
    path.unlink()
    path.symlink_to(outside)
    self.assertFalse(self.pairing.migrate_legacy(self.legacy))
    path.unlink()
    os.mkfifo(path)
    self.assertFalse(self.pairing.migrate_legacy(self.legacy))
    path.unlink()
    path.write_bytes(original)
    outside_dir = self.root / 'outside-dir'
    outside_dir.mkdir(mode=0o700)
    symlink = self.root / 'linked'
    symlink.symlink_to(outside_dir, target_is_directory=True)
    self.assertFalse(RemotePairing(symlink).migrate_legacy(self.legacy))
    self.assertEqual(list(outside_dir.iterdir()), [])

  def test_storage_failure_leaves_original_pairing_for_retry(self):
    with patch('openpilot.starpilot.galaxy.remote.os.link', side_effect=OSError('disk full')):
      self.assertFalse(self.pairing.migrate_legacy(self.legacy))
    self.assertIsNone(self.pairing.read())
    self.assertTrue(self.pairing.migrate_legacy(self.legacy))

  def test_concurrent_startups_do_not_resurrect_an_explicit_unpair(self):
    self.assertTrue(self.pairing.migrate_legacy(self.legacy))
    start = threading.Barrier(3)
    results = []
    def import_again():
      start.wait()
      results.append(RemotePairing(self.pairing.root).migrate_legacy(self.legacy))
    def unpair():
      start.wait()
      results.append(RemotePairing(self.pairing.root).unpair())
    workers = [threading.Thread(target=import_again), threading.Thread(target=unpair)]
    for worker in workers:
      worker.start()
    start.wait()
    for worker in workers:
      worker.join(2)
      self.assertFalse(worker.is_alive())
    self.assertCountEqual(results, [False, True])
    self.assertIsNone(self.pairing.read())
    self.assertFalse(self.pairing.migrate_legacy(self.legacy))

  def test_named_namespace_cannot_import_normal_pairing(self):
    from openpilot.starpilot.galaxy.access import legacy_galaxy_root
    for desktop in (False, True):
      with self.subTest(desktop=desktop), patch.dict(os.environ, {'OPENPILOT_PREFIX': 'isolated-desk'}), \
           patch('openpilot.common.hardware.PC', desktop), \
           patch('openpilot.starpilot.storage.galaxy_storage_root', return_value=self.pairing.root), \
           patch.object(RemotePairing, '_legacy_record', side_effect=AssertionError('legacy access')):
        self.assertIsNone(legacy_galaxy_root())
        self.assertIsNone(default_remote_pairing().read())


if __name__ == '__main__':
  unittest.main()
