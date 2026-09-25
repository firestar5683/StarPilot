"""Local access owner tests use only disposable directories and no service."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from openpilot.starpilot.galaxy.access import AccessStatus, GalaxyAccessOwner


class TestGalaxyAccess(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.base = Path(self.temp.name)
    self.owner = GalaxyAccessOwner(self.base / "new", legacy_root=self.base / "old")
    self.parked = lambda: True

  def test_versioned_private_atomic_store_and_no_remote_claim(self):
    self.assertEqual(self.owner.status().status, AccessStatus.UNCONFIGURED)
    self.assertFalse(self.owner.configure("password123", lambda: False))
    self.assertTrue(self.owner.configure("password123", self.parked))
    path = self.owner.root / self.owner.FILE
    record = json.loads(path.read_text())
    self.assertEqual(set(record), {"version", "algorithm", "salt", "verifier"})
    self.assertNotIn("password123", path.read_text())
    self.assertEqual(record["version"], 1)
    self.assertEqual(path.stat().st_mode & 0o777, 0o600)
    self.assertEqual(self.owner.root.stat().st_mode & 0o777, 0o700)
    self.assertTrue(self.owner.verify("password123"))
    self.assertFalse(self.owner.verify("wrong"))
    self.assertEqual(self.owner.status().status, AccessStatus.CONFIGURED_LOCAL)
    self.assertFalse(self.owner.remove(lambda: False))
    self.assertTrue(path.exists())
    self.assertTrue(self.owner.remove(self.parked))
    self.assertEqual(self.owner.status().status, AccessStatus.UNCONFIGURED)

  def test_unpaired_local_pairing_can_replace_verifier_only_while_parked(self):
    self.assertTrue(self.owner.configure("first-password", self.parked))
    old_generation = self.owner.current_generation()
    self.assertFalse(self.owner.replace_for_pairing("next-password", lambda: False))
    self.assertFalse(self.owner.replace_for_pairing("short", self.parked))
    self.assertTrue(self.owner.verify("first-password"))
    self.assertTrue(self.owner.replace_for_pairing("next-password", self.parked))
    self.assertNotEqual(self.owner.current_generation(), old_generation)
    self.assertFalse(self.owner.verify("first-password"))
    self.assertTrue(self.owner.verify("next-password"))
    self.assertEqual((self.owner.root / self.owner.FILE).stat().st_mode & 0o777, 0o600)

  def test_corrupt_partial_symlink_and_permissions_are_unavailable(self):
    self.owner.root.mkdir(mode=0o700)
    path = self.owner.root / self.owner.FILE
    path.write_text('{"version":1}')
    os.chmod(path, 0o600)
    self.assertEqual(self.owner.status().status, AccessStatus.UNAVAILABLE)
    self.assertFalse(self.owner.configure("password123", self.parked))
    path.unlink()
    path.symlink_to(self.base / "elsewhere")
    self.assertEqual(self.owner.status().status, AccessStatus.UNAVAILABLE)
    path.unlink()
    os.chmod(self.owner.root, 0o755)
    self.assertEqual(self.owner.status().status, AccessStatus.UNAVAILABLE)
    os.chmod(self.owner.root, 0o700)
    path.write_text("{}")
    os.chmod(path, 0o644)
    self.assertEqual(self.owner.status().status, AccessStatus.UNAVAILABLE)

  def test_legacy_import_requires_explicit_password_and_leaves_old_files(self):
    old = self.base / "old"
    old.mkdir()
    (old / "glxyauth").write_text(hashlib.sha256(b"oldpass123").hexdigest())
    (old / "glxysession").write_text("old-session")
    (old / "glxyslug").write_text("old-slug")
    self.assertEqual(self.owner.status().status, AccessStatus.LEGACY_IMPORT_AVAILABLE)
    self.assertFalse(self.owner.configure("newpass123", self.parked))
    self.assertFalse(self.owner.import_legacy("wrongpass", self.parked))
    self.assertFalse(self.owner.import_legacy("oldpass123", lambda: False))
    self.assertTrue(self.owner.import_legacy("oldpass123", self.parked))
    self.assertTrue(self.owner.verify("oldpass123"))
    self.assertTrue((old / "glxysession").exists())
    self.assertNotIn("old-session", (self.owner.root / self.owner.FILE).read_text())

  def test_partial_legacy_record_is_not_treated_as_fresh_unconfigured(self):
    old = self.base / "old"
    old.mkdir()
    (old / "glxyauth").write_text("a" * 64)
    self.assertEqual(self.owner.status().status, AccessStatus.UNAVAILABLE)
    self.assertFalse(self.owner.configure("password123", self.parked))

  def test_interrupted_atomic_write_is_unavailable(self):
    self.owner.root.mkdir(mode=0o700)
    partial = self.owner.root / ".access-interrupted"
    partial.write_text("partial")
    os.chmod(partial, 0o600)
    self.assertEqual(self.owner.status().status, AccessStatus.UNAVAILABLE)
    self.assertFalse(self.owner.configure("password123", self.parked))

  def test_noncanonical_hex_cannot_appear_configured(self):
    self.assertTrue(self.owner.configure("password123", self.parked))
    path = self.owner.root / self.owner.FILE
    original = json.loads(path.read_text())
    for key, malformed in (("salt", " " + original["salt"][1:]),
                           ("verifier", " " + original["verifier"][1:]),
                           ("salt", "A" * 32)):
      with self.subTest(key=key, malformed=malformed):
        record = dict(original, **{key: malformed})
        path.write_text(json.dumps(record))
        self.assertEqual(self.owner.status().status, AccessStatus.UNAVAILABLE)
        self.assertFalse(self.owner.verify("password123"))

  def test_parked_guard_rechecked_at_exact_mutation(self):
    calls = 0
    def only_first_check():
      nonlocal calls
      calls += 1
      return calls == 1

    self.assertFalse(self.owner.configure("password123", only_first_check))
    self.assertFalse(self.owner.root.exists())
    self.assertFalse((self.owner.root / self.owner.FILE).exists())
    self.assertEqual(self.owner.status().status, AccessStatus.UNCONFIGURED)
    calls = 0
    def only_first_two_checks():
      nonlocal calls
      calls += 1
      return calls <= 2

    self.assertFalse(self.owner.configure("password123", only_first_two_checks))
    self.assertFalse((self.owner.root / self.owner.FILE).exists())
    self.assertEqual(self.owner.status().status, AccessStatus.UNCONFIGURED)
    self.assertTrue(self.owner.configure("password123", self.parked))
    calls = 0
    self.assertFalse(self.owner.remove(only_first_check))
    self.assertTrue((self.owner.root / self.owner.FILE).exists())

  def test_legacy_raw_and_trimmed_password_forms_are_imported_as_verified(self):
    for password, stored in ((" edge pass ", " edge pass "), (" edge pass ", "edge pass")):
      with self.subTest(stored=stored), tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        old = base / "old"
        old.mkdir()
        (old / "glxyauth").write_text(hashlib.sha256(stored.encode()).hexdigest())
        (old / "glxysession").write_text("legacy-session")
        (old / "glxyslug").write_text("legacy-slug")
        owner = GalaxyAccessOwner(base / "new", legacy_root=old)
        self.assertTrue(owner.import_legacy(password, self.parked))
        self.assertTrue(owner.verify(stored))
        if stored != password.strip():
          self.assertFalse(owner.verify(password.strip()))

  def test_legacy_import_rechecks_parked_before_new_record_link(self):
    old = self.base / "old"
    old.mkdir()
    (old / "glxyauth").write_text(hashlib.sha256(b"oldpass123").hexdigest())
    (old / "glxysession").write_text("old-session")
    (old / "glxyslug").write_text("old-slug")
    calls = 0
    def only_first_check():
      nonlocal calls
      calls += 1
      return calls == 1

    self.assertFalse(self.owner.import_legacy("oldpass123", only_first_check))
    self.assertFalse(self.owner.root.exists())
    self.assertFalse((self.owner.root / self.owner.FILE).exists())
    self.assertEqual(self.owner.status().status, AccessStatus.LEGACY_IMPORT_AVAILABLE)
