import pytest
import re
import importlib.util
import hashlib
import json
import os
from pathlib import Path

spec = importlib.util.spec_from_file_location('guard', Path(__file__).resolve().parents[1] / 'cache_compat.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class TestCacheCompatibility:
  @pytest.fixture(autouse=True)
  def setup(self, tmp_path):
    self.root = tmp_path
    self.primary = self.root / "params/d"
    self.secondary = self.root / 'params_cache/d'
    self.primary.parent.mkdir()
    self.secondary.parent.mkdir()
    target = self.primary.parent / '.tmp_dom'
    target.mkdir()
    self.primary.symlink_to(target)
    self.secondary.mkdir()
    self.archive = self.root / 'archive'

  def run_guard(self):
    return guard.retire_foreign_caches(self.primary, self.secondary, self.archive)

  def test_layers_preserve_valid_opposite_and_preferences(self):
    (self.primary / 'CarParamsPersistent').write_bytes(b'SPCACHE\x01foreign')
    (self.secondary / 'CarParamsPersistent').write_bytes(b'ordinary Dom raw')
    (self.primary / 'CalibrationParams').write_bytes(b'ordinary calibration')
    (self.secondary / 'LiveDelay').write_bytes(b'SPCACHE\tfuture')
    for root in (self.primary, self.secondary):
      (root / 'GithubSshKeys').write_bytes(b'auth')
      (root / 'IsMetric').write_bytes(b'1')
    records = self.run_guard()
    assert len(records) == 2
    assert not (self.primary / 'CarParamsPersistent').exists()
    assert not (self.secondary / 'LiveDelay').exists()
    assert (self.secondary / 'CarParamsPersistent').read_bytes() == b'ordinary Dom raw'
    assert (self.primary / 'CalibrationParams').read_bytes() == b'ordinary calibration'
    for record in records:
      raw = (self.archive / record['sha256']).read_bytes()
      assert raw.startswith(b'SPCACHE')
      assert (self.archive / record['sha256']).stat().st_mode & 511 == 384
    assert self.archive.stat().st_mode & 511 == 448
    assert self.run_guard() == ()
    for root in (self.primary, self.secondary):
      assert (root / 'GithubSshKeys').read_bytes() == b'auth'
      assert (root / 'IsMetric').read_bytes() == b'1'

  def test_archive_failure_before_any_deletion_then_retry(self, monkeypatch):
    files = [self.primary / 'CarParamsPersistent', self.secondary / 'LiveDelay']
    for index, file in enumerate(files):
      file.write_bytes(b'SPCACHE' + bytes([index]))
    save = guard._save
    calls = []

    def interrupted(path, raw):
      calls.append(path)
      if len(calls) == 2:
        raise OSError('disk full')
      save(path, raw)

    with monkeypatch.context() as patches:
      patches.setattr(guard, '_save', interrupted)
      with pytest.raises(OSError):
        self.run_guard()
    assert all(file.exists() for file in files)
    assert list(self.primary.parent.glob('.starpilot-dom-handoff-*')) == []
    assert len(self.run_guard()) == 2

  def test_interrupted_archive_fsync_retries(self, monkeypatch):
    file = self.primary / 'CarParamsPersistent'
    file.write_bytes(b'SPCACHEforeign')
    with monkeypatch.context() as patches:

      def interrupted(*args, **kwargs):
        raise OSError('interrupted write')

      patches.setattr(guard.os, 'fsync', interrupted)
      with pytest.raises(OSError):
        self.run_guard()
    assert file.exists()
    assert list(self.archive.iterdir()) == []
    assert len(self.run_guard()) == 1

  def test_source_symlink_refused(self):
    outside = self.root / 'outside'
    outside.write_bytes(b'SPCACHEforeign')
    (self.primary / 'CarParamsPersistent').symlink_to(outside)
    with pytest.raises(OSError):
      self.run_guard()
    assert outside.read_bytes() == b'SPCACHEforeign'

  def test_archive_symlink_refused(self):
    (self.primary / 'CarParamsPersistent').write_bytes(b'SPCACHEforeign')
    outside = self.root / 'outside'
    outside.mkdir()
    self.archive.symlink_to(outside)
    with pytest.raises(ValueError):
      self.run_guard()
    assert (self.primary / 'CarParamsPersistent').exists()

  def test_nonforeign_malformed_bytes_are_preserved(self):
    (self.primary / 'CarParamsPersistent').write_bytes(b'bad nonword bytes')
    assert self.run_guard() == ()
    assert (self.primary / 'CarParamsPersistent').read_bytes() == b'bad nonword bytes'

  def test_each_dom_start_marks_its_exact_namespace_even_without_foreign_caches(self):
    self.run_guard()
    name = '.starpilot-dom-handoff-' + hashlib.sha256(str(self.primary).encode()).hexdigest() + '.json'
    marker = self.primary.parent / name
    first = json.loads(marker.read_bytes())
    assert set(first) == {'format', 'version', 'namespace', 'target', 'token'}
    assert first['format'] == 'starpilot-dom-handoff'
    assert first['version'] == 1
    assert first['namespace'] == str(self.primary)
    assert first['target'] == str(self.primary.resolve())
    assert re.search('^[0-9a-f]{32}$', first['token'])
    assert marker.stat().st_mode & 511 == 384
    assert marker.stat().st_uid == os.getuid()
    self.run_guard()
    assert json.loads(marker.read_bytes())['token'] != first['token']

  def test_handoff_failure_keeps_archives_and_can_retry_without_foreign_caches(self, monkeypatch):
    raw = b'SPCACHEforeign'
    (self.primary / 'CarParamsPersistent').write_bytes(raw)
    with monkeypatch.context() as patches:

      def interrupted(*args, **kwargs):
        raise OSError('interrupted write')

      patches.setattr(guard, '_publish_handoff', interrupted)
      with pytest.raises(OSError):
        self.run_guard()
    assert (self.archive / hashlib.sha256(raw).hexdigest()).read_bytes() == raw
    assert list(self.primary.parent.glob('.starpilot-dom-handoff-*')) == []
    assert self.run_guard() == ()
    assert len(list(self.primary.parent.glob('.starpilot-dom-handoff-*'))) == 1

  def test_namespaces_have_independent_handoff_markers(self):
    self.run_guard()
    first = {path: path.read_bytes() for path in self.primary.parent.glob('.starpilot-dom-handoff-*')}
    named = self.primary.parent / 'test'
    named.mkdir()
    guard.retire_foreign_caches(named, self.secondary, self.archive)
    markers = list(self.primary.parent.glob('.starpilot-dom-handoff-*'))
    assert len(markers) == 2
    assert {path: path.read_bytes() for path in first} == first

  def test_handoff_symlink_is_rejected(self):
    name = '.starpilot-dom-handoff-' + hashlib.sha256(str(self.primary).encode()).hexdigest() + '.json'
    outside = self.root / 'outside'
    outside.write_bytes(b'untouched')
    (self.primary.parent / name).symlink_to(outside)
    with pytest.raises(ValueError):
      self.run_guard()
    assert outside.read_bytes() == b'untouched'
