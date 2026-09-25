import os
import threading

import pytest

from openpilot.common.hardware.hw import Paths
from openpilot.system import crash_storage, sentry
from openpilot.starpilot.galaxy import crash_reports


def test_writer_unit_excludes_delete_until_summary_is_complete(tmp_path, monkeypatch):
  monkeypatch.setattr(Paths, 'log_root', lambda: str(tmp_path))
  sentry.save_exception('old trace')
  reader = crash_reports.CrashReports(tmp_path / 'crash')
  old = next(report for report in reader.list()['reports'] if report['name'].endswith('.log'))
  paused, release, attempted = threading.Event(), threading.Event(), threading.Event()
  errors, inspected = [], []
  original_write, original_lock = sentry.write_text, crash_reports.acquire_lock
  original_summary = reader._latest_summary

  def write(directory, name, text):
    if name == 'error.txt' and text == 'new trace':
      paused.set()
      assert release.wait(2)
    return original_write(directory, name, text)

  def lock(directory, **kwargs):
    attempted.set()
    return original_lock(directory, **kwargs)

  def summary(*args):
    inspected.append(True)
    return original_summary(*args)

  def run(call):
    try:
      call()
    except BaseException as error:
      errors.append(error)

  monkeypatch.setattr(sentry, 'write_text', write)
  monkeypatch.setattr(crash_reports, 'acquire_lock', lock)
  monkeypatch.setattr(reader, '_latest_summary', summary)
  writing = threading.Thread(target=run, args=(lambda: sentry.save_exception('new trace'),))
  deleting = threading.Thread(target=run, args=(lambda: reader.delete(old['id']),))
  writing.start()
  try:
    assert paused.wait(1)
    deleting.start()
    assert attempted.wait(1)
    assert inspected == []
    assert (reader.directory / 'error.txt').read_text() == 'old trace'
  finally:
    release.set()
    writing.join(2)
    if deleting.ident is not None:
      deleting.join(2)
  assert not writing.is_alive() and not deleting.is_alive() and errors == []
  assert (reader.directory / 'error.txt').read_text() == 'new trace'
  assert not (reader.directory / old['name']).exists()
  assert reader.delete(old['id'])['reportCount'] == 2
  assert (reader.directory / 'error.txt').read_text() == 'new trace'
  lock_inode = (reader.directory / '.lock').stat().st_ino
  assert reader.delete()['reportCount'] == 0
  assert list(reader.directory.iterdir()) == [reader.directory / '.lock']
  assert (reader.directory / '.lock').stat().st_ino == lock_inode


def test_lock_wait_is_bounded_and_copy_collection_remains_functional(tmp_path):
  directory = crash_storage.open_directory(tmp_path / 'crash', create=True)
  lock = crash_storage.acquire_lock(directory)
  try:
    with pytest.raises(BlockingIOError):
      crash_storage.acquire_lock(directory, timeout=0)
  finally:
    os.close(lock)
    os.close(directory)
  source = tmp_path / 'tombstone'
  source.write_bytes(b'actual tombstone bytes')
  with crash_storage.writer(tmp_path / 'crash') as directory:
    crash_storage.copy_report(directory, 'tombstone-report', source)
  reader = crash_reports.CrashReports(tmp_path / 'crash')
  assert reader.list()['reportCount'] == 1
  assert (reader.directory / 'tombstone-report').read_bytes() == source.read_bytes()
  assert reader.delete()['storageBytes'] == 0


def test_reserved_lock_token_cannot_preview_or_remove_retained_inode(tmp_path):
  with crash_storage.writer(tmp_path / 'crash') as directory:
    crash_storage.write_text(directory, 'report', 'saved report')
  reader = crash_reports.CrashReports(tmp_path / 'crash')
  lock = reader.directory / '.lock'
  original = lock.stat()
  token = reader._token('.lock', reader.directory.stat(), original)
  with pytest.raises(crash_reports.CrashMissing):
    reader.preview(token)
  with pytest.raises(crash_reports.CrashMissing):
    reader.delete(token)
  assert lock.stat().st_ino == original.st_ino
  assert reader.list()['reportCount'] == 1
