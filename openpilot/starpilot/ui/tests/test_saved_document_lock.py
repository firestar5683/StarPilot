import fcntl
from pathlib import Path
import tempfile
from threading import Timer
import time
import unittest

from openpilot.common.params import Params
from openpilot.starpilot.saved_document import LOCK_WAIT_SECONDS, commit_exact


class SavedDocumentLockTests(unittest.TestCase):
  def setUp(self):
    directory = tempfile.TemporaryDirectory()
    self.addCleanup(directory.cleanup)
    self.params = Params(directory.name)
    self.key = "TuningPreparationState"
    self.destination = Path(self.params.get_param_path(self.key))
    self.destination.write_bytes(b"prior")
    self.root = self.destination.parent.parent
    self.allowed = True

  def commit(self):
    return commit_exact(self.params, key=self.key, max_bytes=128, raw=b"next", expected=b"prior",
                        authorized=lambda: self.allowed, temp_prefix="lock-fixture-")

  def hold(self):
    lock = (self.root / ".lock").open("a")
    self.addCleanup(lock.close)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return lock

  def test_brief_native_writer_contention_commits_after_release(self):
    lock = self.hold()
    release = Timer(.05, lambda: fcntl.flock(lock, fcntl.LOCK_UN))
    release.start()
    try:
      result = self.commit()
    finally:
      release.cancel()
      release.join()
      fcntl.flock(lock, fcntl.LOCK_UN)
    self.assertTrue(result.committed and result.verified)
    self.assertEqual(self.destination.read_bytes(), b"next")

  def test_permanent_contention_is_bounded_and_preserves_bytes(self):
    self.hold()
    started = time.monotonic()
    self.assertFalse(self.commit().committed)
    elapsed = time.monotonic() - started
    self.assertGreaterEqual(elapsed, LOCK_WAIT_SECONDS)
    self.assertLess(elapsed, LOCK_WAIT_SECONDS + .5)
    self.assertEqual(self.destination.read_bytes(), b"prior")
    self.assertFalse(list(self.root.glob("lock-fixture-*")))

  def test_revoked_authority_while_waiting_cannot_commit(self):
    lock = self.hold()
    def revoke():
      self.allowed = False
      fcntl.flock(lock, fcntl.LOCK_UN)
    release = Timer(.05, revoke)
    release.start()
    try:
      self.assertFalse(self.commit().committed)
    finally:
      release.cancel()
      release.join()
      fcntl.flock(lock, fcntl.LOCK_UN)
    self.assertEqual(self.destination.read_bytes(), b"prior")
    self.assertFalse(list(self.root.glob("lock-fixture-*")))

  def test_changed_saved_source_while_waiting_cannot_commit(self):
    lock = self.hold()
    def change():
      self.destination.write_bytes(b"other")
      fcntl.flock(lock, fcntl.LOCK_UN)
    release = Timer(.05, change)
    release.start()
    try:
      self.assertFalse(self.commit().committed)
    finally:
      release.cancel()
      release.join()
      fcntl.flock(lock, fcntl.LOCK_UN)
    self.assertEqual(self.destination.read_bytes(), b"other")
    self.assertFalse(list(self.root.glob("lock-fixture-*")))
