import fcntl
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.starpilot.curve_speed.preferences import DOCUMENT_KEY, LEGACY_KEY, MASTER_KEY, NO_LEAD_KEY, PreferenceHost, read_learning


class TestCurvePreferences(unittest.TestCase):
  def setUp(self):
    self.directory = tempfile.TemporaryDirectory()
    self.addCleanup(self.directory.cleanup)
    self.params = Params(self.directory.name)

  def host(self, params=None):
    owner = PreferenceHost(params or self.params)
    self.addCleanup(owner.close)
    return owner, owner.make_host(replay=True)

  def finish(self, owner, host, now_ns):
    deadline = time.monotonic() + 2
    while owner.worker is not None and owner.completed.empty() and time.monotonic() < deadline:
      time.sleep(0.005)
    self.assertFalse(owner.completed.empty(), 'background persistence did not complete')
    owner.persist(host, SimpleNamespace(dirty_revision=None), now_ns)

  def test_defaults_flags_and_unreadable_choice(self):
    owner, host = self.host()
    owner.refresh(host, 1_000_000_000)
    self.assertFalse(host.runtime.enabled)
    self.params.put_bool(MASTER_KEY, True, block=True)
    self.params.put_bool(NO_LEAD_KEY, True, block=True)
    owner.refresh(host, 2_000_000_000)
    self.assertTrue(host.runtime.enabled and host.runtime.no_lead)
    Path(self.params.get_param_path(NO_LEAD_KEY)).write_bytes(b'false')
    owner.refresh(host, 3_000_000_000)
    self.assertFalse(host.runtime.enabled)

  def test_legacy_data_is_preserved_and_new_document_roundtrips(self):
    legacy = {'0.01': {'average': 2.1, 'count': 100}}
    self.params.put(LEGACY_KEY, legacy, block=True)
    original = Path(self.params.get_param_path(LEGACY_KEY)).read_bytes()
    owner, host = self.host()
    self.assertTrue(host.runtime.document_valid)
    self.assertIsNone(self.params.get(DOCUMENT_KEY))
    host.runtime.curve.observe(0.01, 2.4)
    revision = host.runtime.curve.revision
    owner.persist(host, SimpleNamespace(dirty_revision=revision), 1_000_000_000)
    self.finish(owner, host, 1_050_000_000)
    self.assertEqual(owner.status, 'saved')
    self.assertFalse(host.runtime.curve.dirty)
    self.assertEqual(self.params.get(DOCUMENT_KEY), host.runtime.curve.document())
    self.assertEqual(Path(self.params.get_param_path(LEGACY_KEY)).read_bytes(), original)
    self.assertEqual(read_learning(self.params).document, host.runtime.curve.document())

  def test_malformed_document_cannot_be_replaced_by_fresh_learning(self):
    for raw in (b'null', b'{}', b'{', b'{"version":1,"version":1,"buckets":{}}'):
      with self.subTest(raw=raw):
        Path(self.params.get_param_path(DOCUMENT_KEY)).write_bytes(raw)
        owner, host = self.host()
        self.assertFalse(host.runtime.document_valid)
        host.runtime.curve.observe(0.01, 2.0)
        owner.persist(host, SimpleNamespace(dirty_revision=host.runtime.curve.revision), 1_000_000_000)
        self.assertIsNone(owner.worker)
        self.assertEqual(Path(self.params.get_param_path(DOCUMENT_KEY)).read_bytes(), raw)

  def test_external_edit_wins_and_disables_this_session(self):
    owner, host = self.host()
    host.runtime.curve.observe(0.01, 2.0)
    external = {'version': 1, 'buckets': {'0.01': {'average': 3.0, 'count': 800}}}
    self.params.put(DOCUMENT_KEY, external, block=True)
    owner.persist(host, SimpleNamespace(dirty_revision=host.runtime.curve.revision), 1_000_000_000)
    self.finish(owner, host, 1_050_000_000)
    self.assertEqual(owner.status, 'external_edit')
    self.assertFalse(host.runtime.enabled)
    self.assertTrue(host.runtime.curve.dirty)
    self.assertEqual(self.params.get(DOCUMENT_KEY), external)

  def test_pending_write_is_nonblocking_bounded_and_preserves_new_samples(self):
    entered, release = threading.Event(), threading.Event()
    fsync = os.fsync

    def slow_sync(fd):
      entered.set()
      if not release.wait(2):
        raise OSError('write interrupted')
      fsync(fd)

    owner, host = self.host()
    with patch('openpilot.starpilot.curve_speed.preferences.os.fsync', side_effect=slow_sync):
      host.runtime.curve.observe(0.01, 2.0)
      owner.persist(host, SimpleNamespace(dirty_revision=1), 1_000_000_000)
      self.assertTrue(entered.wait(1))
      worker = owner.worker
      try:
        host.runtime.curve.observe(0.01, 3.0)
        for index in range(10):
          owner.persist(host, SimpleNamespace(dirty_revision=2), 2_000_000_000 + index)
          self.assertIs(owner.worker, worker)
      finally:
        release.set()
      self.finish(owner, host, 2_100_000_000)
    self.assertTrue(host.runtime.curve.dirty)
    saved = json.loads(Path(self.params.get_param_path(DOCUMENT_KEY)).read_bytes())['buckets']
    self.assertEqual(len(saved), 1)
    self.assertEqual(sum(item['count'] for item in saved.values()), 1)

  def test_failed_write_keeps_dirty_revision_for_retry(self):
    owner, host = self.host()
    host.runtime.curve.observe(0.01, 2.0)
    with patch('openpilot.starpilot.curve_speed.preferences.os.fsync', side_effect=OSError('disk unavailable')):
      owner.persist(host, SimpleNamespace(dirty_revision=1), 1_000_000_000)
      self.finish(owner, host, 1_050_000_000)
    self.assertEqual(owner.status, 'write_failed')
    self.assertTrue(host.runtime.curve.dirty)
    self.assertIsNone(self.params.get(DOCUMENT_KEY))
    self.assertEqual(list(Path(self.directory.name).glob('.tmp_curve_*')), [])

  def test_in_flight_external_params_edit_is_not_overwritten(self):
    prepared, release = threading.Event(), threading.Event()
    fsync = os.fsync

    def slow_sync(fd):
      prepared.set()
      if not release.wait(2):
        raise OSError('write interrupted')
      fsync(fd)

    external = {'version': 1, 'buckets': {'0.01': {'average': 3.0, 'count': 800}}}
    owner, host = self.host()
    host.runtime.curve.observe(0.01, 2.0)
    with patch('openpilot.starpilot.curve_speed.preferences.os.fsync', side_effect=slow_sync):
      owner.persist(host, SimpleNamespace(dirty_revision=1), 1_000_000_000)
      self.assertTrue(prepared.wait(1))
      try:
        self.params.put(DOCUMENT_KEY, external, block=True)
      finally:
        release.set()
      self.finish(owner, host, 1_050_000_000)
    self.assertEqual(owner.status, 'external_edit')
    self.assertTrue(host.runtime.curve.dirty)
    self.assertEqual(self.params.get(DOCUMENT_KEY), external)

  def test_ordinary_params_writer_waits_for_conditional_commit_then_wins(self):
    committing, release, external_done = threading.Event(), threading.Event(), threading.Event()
    replace = os.replace

    def slow_replace(source, destination):
      committing.set()
      if not release.wait(2):
        raise OSError('write interrupted')
      replace(source, destination)

    external = {'version': 1, 'buckets': {'0.01': {'average': 3.0, 'count': 800}}}
    def edit():
      self.params.put(DOCUMENT_KEY, external, block=True)
      external_done.set()

    owner, host = self.host()
    host.runtime.curve.observe(0.01, 2.0)
    with patch('openpilot.starpilot.curve_speed.preferences.os.replace', side_effect=slow_replace):
      owner.persist(host, SimpleNamespace(dirty_revision=1), 1_000_000_000)
      self.assertTrue(committing.wait(1))
      editor = threading.Thread(target=edit)
      editor.start()
      try:
        self.assertFalse(external_done.wait(0.05), 'Params did not honor the shared root lock')
      finally:
        release.set()
      editor.join(timeout=2)
      self.assertFalse(editor.is_alive())
      self.finish(owner, host, 1_050_000_000)
    self.assertEqual(self.params.get(DOCUMENT_KEY), external)
    host.runtime.curve.observe(0.01, 2.1)
    owner.persist(host, SimpleNamespace(dirty_revision=2), 3_000_000_000)
    self.finish(owner, host, 3_050_000_000)
    self.assertEqual(owner.status, 'external_edit')
    self.assertEqual(self.params.get(DOCUMENT_KEY), external)

  def test_close_cancels_prepared_write_before_it_can_replace(self):
    prepared, release = threading.Event(), threading.Event()
    fsync = os.fsync

    def slow_sync(fd):
      prepared.set()
      if not release.wait(2):
        raise OSError('write interrupted')
      fsync(fd)

    owner, host = self.host()
    host.runtime.curve.observe(0.01, 2.0)
    with patch('openpilot.starpilot.curve_speed.preferences.os.fsync', side_effect=slow_sync):
      owner.persist(host, SimpleNamespace(dirty_revision=1), 1_000_000_000)
      self.assertTrue(prepared.wait(1))
      try:
        owner.close()
        self.assertIsNone(self.params.get(DOCUMENT_KEY))
        self.assertFalse(host.runtime.enabled)
      finally:
        release.set()
      self.finish(owner, host, 1_050_000_000)
    self.assertEqual(owner.status, 'cancelled')
    self.assertIsNone(self.params.get(DOCUMENT_KEY))
    self.assertTrue(host.runtime.curve.dirty)
    self.assertEqual(list(Path(self.directory.name).glob('.tmp_curve_*')), [])

  def test_close_cancels_while_another_params_owner_holds_lock(self):
    owner, host = self.host()
    host.runtime.curve.observe(0.01, 2.0)
    with open(Path(self.directory.name) / '.lock', 'a') as lock:
      fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
      owner.persist(host, SimpleNamespace(dirty_revision=1), 1_000_000_000)
      owner.close()
      self.finish(owner, host, 1_050_000_000)
      self.assertEqual(owner.status, 'cancelled')
    self.assertIsNone(self.params.get(DOCUMENT_KEY))

  def test_directory_sync_failure_retains_dirty_and_can_retry_own_committed_bytes(self):
    owner, host = self.host()
    host.runtime.curve.observe(0.01, 2.0)
    fsync = os.fsync
    calls = 0

    def fail_directory_sync(fd):
      nonlocal calls
      calls += 1
      if calls == 2:
        raise OSError('directory sync failed')
      fsync(fd)

    with patch('openpilot.starpilot.curve_speed.preferences.os.fsync', side_effect=fail_directory_sync):
      owner.persist(host, SimpleNamespace(dirty_revision=1), 1_000_000_000)
      self.finish(owner, host, 1_050_000_000)
    self.assertEqual(owner.status, 'write_failed')
    self.assertTrue(host.runtime.curve.dirty)
    self.assertEqual(self.params.get(DOCUMENT_KEY), host.runtime.curve.document())
    owner.persist(host, SimpleNamespace(dirty_revision=1), 3_000_000_000)
    self.finish(owner, host, 3_050_000_000)
    self.assertEqual(owner.status, 'saved')
    self.assertFalse(host.runtime.curve.dirty)
