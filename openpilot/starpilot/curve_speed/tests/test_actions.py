import fcntl
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.starpilot.curve_speed.actions import apply_learning, learning_snapshot
from openpilot.starpilot.curve_speed.learning import LearnedCurve
from openpilot.starpilot.curve_speed.preferences import (
  DOCUMENT_KEY, LEGACY_KEY, MASTER_KEY, PreferenceHost, learning_lock_path,
)


class TestLearningActions(unittest.TestCase):
  def setUp(self):
    self.directory = tempfile.TemporaryDirectory()
    self.addCleanup(self.directory.cleanup)
    self.params = Params(self.directory.name)
    self.legacy = {'0.01': {'average': 2.2, 'count': 100}}
    self.params.put(LEGACY_KEY, self.legacy, block=True)

  def raw(self, key):
    path = Path(self.params.get_param_path(key))
    return path.read_bytes() if path.exists() else None

  def apply(self, kind='curve_reset', snapshot=None, authorized=lambda: True):
    snapshot = snapshot or learning_snapshot(self.params)
    return apply_learning(self.params, kind, snapshot.sources, authorized=authorized)

  def owner(self):
    owner = PreferenceHost(self.params)
    self.addCleanup(owner.close)
    return owner

  def test_snapshot_is_read_only_and_adoption_preserves_legacy(self):
    before = self.raw(LEGACY_KEY)
    snapshot = learning_snapshot(self.params)
    self.assertFalse(learning_lock_path(self.params).exists())
    self.assertTrue(snapshot.valid and snapshot.has_samples and snapshot.adoptable and snapshot.resettable)
    loaded = LearnedCurve.load(self.legacy).curve
    assert snapshot.progress is not None and snapshot.comfort is not None
    self.assertAlmostEqual(snapshot.progress, loaded.progress)
    self.assertAlmostEqual(snapshot.comfort, loaded.average_comfort)
    result = self.apply('curve_adopt', snapshot)
    self.assertTrue(result.committed)
    self.assertEqual(result.reason, 'saved')
    self.assertEqual(json.loads(self.raw(DOCUMENT_KEY)), loaded.document())
    self.assertEqual(self.raw(LEGACY_KEY), before)
    self.assertIsNone(self.raw(MASTER_KEY))
    self.assertFalse(learning_snapshot(self.params).adoptable)

  def test_reset_recovers_invalid_canonical_without_reviving_legacy(self):
    Path(self.params.get_param_path(DOCUMENT_KEY)).write_bytes(b'{')
    snapshot = learning_snapshot(self.params)
    self.assertFalse(snapshot.valid or snapshot.adoptable)
    self.assertIsNone(snapshot.progress)
    self.assertTrue(snapshot.resettable)
    before = self.raw(LEGACY_KEY)
    self.assertEqual(self.apply(snapshot=snapshot).reason, 'saved')
    reset = learning_snapshot(self.params)
    self.assertTrue(reset.valid)
    self.assertFalse(reset.has_samples or reset.adoptable)
    self.assertEqual(reset.progress, 0.0)
    self.assertEqual(json.loads(self.raw(DOCUMENT_KEY)), LearnedCurve().document())
    self.assertEqual(self.raw(LEGACY_KEY), before)

  def test_enabled_malformed_master_unreadable_source_and_no_authority_cannot_edit(self):
    for master in (b'1', b'', b'false'):
      with self.subTest(master=master):
        Path(self.params.get_param_path(MASTER_KEY)).write_bytes(master)
        self.assertFalse(learning_snapshot(self.params).resettable)
        self.assertFalse(self.apply().committed)
        self.assertIsNone(self.raw(DOCUMENT_KEY))
    self.params.put_bool(MASTER_KEY, False, block=True)
    self.assertFalse(self.apply(authorized=lambda: False).committed)
    Path(self.params.get_param_path(DOCUMENT_KEY)).write_bytes(b'x' * 32769)
    snapshot = learning_snapshot(self.params)
    self.assertFalse(snapshot.readable or snapshot.resettable)
    self.assertFalse(self.apply(snapshot=snapshot).committed)
    self.assertEqual(len(self.raw(DOCUMENT_KEY)), 32769)

  def test_stale_snapshot_cannot_adopt_reset_or_turn_master_on(self):
    for key, replacement in ((LEGACY_KEY, b'{}'), (DOCUMENT_KEY, b'{'), (MASTER_KEY, b'1')):
      with self.subTest(changed=key):
        snapshot = learning_snapshot(self.params)
        Path(self.params.get_param_path(key)).write_bytes(replacement)
        for kind in ('curve_reset', 'curve_adopt'):
          self.assertFalse(self.apply(kind, snapshot).committed)
        self.assertEqual(self.raw(key), replacement)
        self.params.remove(DOCUMENT_KEY)
        self.params.remove(MASTER_KEY)
        self.params.put(LEGACY_KEY, self.legacy, block=True)

  def test_active_learning_session_and_second_owner_are_excluded(self):
    snapshot = learning_snapshot(self.params)
    owner = self.owner()
    host = owner.make_host(replay=True)
    self.assertTrue(host.runtime.document_valid)
    self.assertFalse(learning_snapshot(self.params).resettable)
    self.assertEqual(self.apply(snapshot=snapshot).reason, 'learning_active')
    second = self.owner()
    other = second.make_host(replay=True)
    self.params.put_bool(MASTER_KEY, True, block=True)
    second.refresh(other, 1_000_000_000)
    self.assertFalse(other.runtime.enabled or other.runtime.document_valid)
    other.runtime.curve.observe(0.01, 2.0)
    second.persist(other, SimpleNamespace(dirty_revision=1), 1_000_000_000)
    self.assertIsNone(second.worker)
    second.close()
    self.params.put_bool(MASTER_KEY, False, block=True)
    owner.close()
    self.assertEqual(self.apply().reason, 'saved')

  def test_new_owner_captures_document_after_lease_not_constructor(self):
    owner = self.owner()
    self.assertEqual(self.apply().reason, 'saved')
    host = owner.make_host(replay=True)
    self.assertEqual(host.runtime.curve.progress, 0)
    self.assertEqual(host.runtime.curve.document(), LearnedCurve().document())

  def test_edit_and_authority_are_rechecked_after_staging_io(self):
    fsync = os.fsync
    for change in ('document', 'master', 'authority'):
      with self.subTest(change=change):
        self.params.remove(DOCUMENT_KEY)
        self.params.remove(MASTER_KEY)
        authority = [True]
        called = False

        def intervene(fd, changed=change, allowed=authority):
          nonlocal called
          if not called:
            called = True
            if changed == 'authority':
              allowed[0] = False
            else:
              if changed == 'document':
                self.params.put(DOCUMENT_KEY, LearnedCurve().document(), block=True)
              else:
                self.params.put_bool(MASTER_KEY, True, block=True)
          fsync(fd)

        with patch('openpilot.starpilot.curve_speed.actions.os.fsync', side_effect=intervene):
          result = self.apply('curve_adopt', authorized=lambda allowed=authority: allowed[0])
        self.assertFalse(result.committed)
        self.assertEqual(self.raw(LEGACY_KEY), json.dumps(self.legacy).encode())

  def test_busy_params_lock_does_not_block_or_change_data(self):
    with open(Path(self.directory.name) / '.lock', 'a') as lock:
      fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
      self.assertEqual(self.apply().reason, 'storage_busy')
    self.assertIsNone(self.raw(DOCUMENT_KEY))
    self.assertEqual(list(Path(self.directory.name).glob('.tmp_curve_action_*')), [])

  def test_sync_failure_distinguishes_before_and_after_commit(self):
    original_sync = os.fsync
    for fail_at in (1, 2):
      with self.subTest(fail_at=fail_at):
        self.params.remove(DOCUMENT_KEY)
        calls = 0

        def sync(fd, failure_call=fail_at):
          nonlocal calls
          calls += 1
          if calls == failure_call:
            raise OSError('storage unavailable')
          original_sync(fd)

        with patch('openpilot.starpilot.curve_speed.actions.os.fsync', side_effect=sync):
          result = self.apply()
        self.assertEqual(result.committed, fail_at == 2)
        self.assertEqual(result.reason, 'sync_failed' if fail_at == 2 else 'write_failed')
        self.assertEqual(self.raw(DOCUMENT_KEY) is not None, fail_at == 2)
        self.assertEqual(list(Path(self.directory.name).glob('.tmp_curve_action_*')), [])

  def test_close_cancelled_writer_cannot_overwrite_later_reset(self):
    prepared, release = threading.Event(), threading.Event()
    original_sync = os.fsync

    def sync(fd):
      if threading.current_thread().name == 'curve-learning':
        prepared.set()
        if not release.wait(2):
          raise OSError('interrupted')
      original_sync(fd)

    owner = self.owner()
    host = owner.make_host(replay=True)
    host.runtime.curve.observe(0.01, 2.8)
    with patch('openpilot.starpilot.curve_speed.preferences.os.fsync', side_effect=sync):
      owner.persist(host, SimpleNamespace(dirty_revision=1), 1_000_000_000)
      self.assertTrue(prepared.wait(1))
      writer = owner.worker
      try:
        owner.close()
        self.assertEqual(self.apply().reason, 'saved')
      finally:
        release.set()
      writer.join(timeout=2)
      self.assertFalse(writer.is_alive())
    self.assertEqual(json.loads(self.raw(DOCUMENT_KEY)), LearnedCurve().document())
    self.assertTrue(host.runtime.curve.dirty)
    self.assertEqual(list(Path(self.directory.name).glob('.tmp_curve_*')), [])

  def test_lease_contention_stays_disabled_until_a_new_session(self):
    path = learning_lock_path(self.params)
    with open(path, 'a') as editor:
      fcntl.flock(editor.fileno(), fcntl.LOCK_EX)
      owner = self.owner()
      host = owner.make_host(replay=True)
    self.params.put_bool(MASTER_KEY, True, block=True)
    owner.refresh(host, 1_000_000_000)
    self.assertFalse(host.runtime.enabled or host.runtime.document_valid)
    self.assertEqual(host.runtime.document_reason, 'learning_active')
    owner.close()
    replacement = self.owner()
    ready = replacement.make_host(replay=True)
    replacement.refresh(ready, 2_000_000_000)
    self.assertTrue(ready.runtime.enabled and ready.runtime.document_valid)

  def test_closed_writer_directory_sync_keeps_editor_serialized(self):
    syncing, release = threading.Event(), threading.Event()
    original_sync = os.fsync
    writer_calls = 0

    def sync(fd):
      nonlocal writer_calls
      if threading.current_thread().name == 'curve-learning':
        writer_calls += 1
        if writer_calls == 2:
          syncing.set()
          if not release.wait(2):
            raise OSError('interrupted')
      original_sync(fd)

    owner = self.owner()
    host = owner.make_host(replay=True)
    host.runtime.curve.observe(0.01, 2.8)
    with patch('openpilot.starpilot.curve_speed.preferences.os.fsync', side_effect=sync):
      owner.persist(host, SimpleNamespace(dirty_revision=1), 1_000_000_000)
      self.assertTrue(syncing.wait(1))
      writer = owner.worker
      try:
        owner.close()
        committed = self.raw(DOCUMENT_KEY)
        self.assertIsNotNone(committed)
        self.assertEqual(self.apply().reason, 'storage_busy')
        self.assertEqual(self.raw(DOCUMENT_KEY), committed)
      finally:
        release.set()
      writer.join(timeout=2)
      self.assertFalse(writer.is_alive())
    self.assertEqual(self.apply().reason, 'saved')
    self.assertEqual(json.loads(self.raw(DOCUMENT_KEY)), LearnedCurve().document())
