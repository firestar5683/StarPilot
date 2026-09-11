"""Preserve Git's index and working tree independently through local recovery."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile

import pytest


SPEC = importlib.util.spec_from_file_location('index_installer', Path(__file__).resolve().parents[1] / 'version_install.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def git(repo, *args):
  return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.STDOUT)


@pytest.fixture
def checkout(monkeypatch):
  monkeypatch.setenv('GIT_ALLOW_PROTOCOL', 'file')
  monkeypatch.setenv('GIT_CONFIG_NOSYSTEM', '1')
  monkeypatch.setenv('GIT_CONFIG_GLOBAL', '/dev/null')
  with tempfile.TemporaryDirectory(prefix='galaxy-index-recovery-') as directory:
    root = Path(directory)
    repo = root / 'repo'
    repo.mkdir()
    git(repo, 'init', '-b', 'Dom')
    git(repo, 'config', 'user.email', 'test@example.invalid')
    git(repo, 'config', 'user.name', 'Index recovery test')
    files = {
      'launch_env.sh': b'export AGNOS_VERSION="19.6.20"\n',
      'launch_chffrplus.sh': b'#!/bin/sh\n',
      'common/params_keys.h': b'AutomaticUpdates\n',
      'starpilot/common/starpilot_variables.py': b'automatic_updates\n',
      'system/updated/updated.py': b'automatic_updates_enabled\n',
      'system/hardware/tici/agnos.json': b'[]\n',
      'tracked.txt': b'one\ntwo\nthree\n',
      'binary.bin': b'\x00original\xff',
      'removed.txt': b'keep staged deletion\n',
    }
    for name, content in files.items():
      path = repo / name
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_bytes(content)
    (repo / 'tracked-link').symlink_to('tracked.txt')
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'Historical')
    old = git(repo, 'rev-parse', 'HEAD').decode().strip()
    (repo / 'latest.txt').write_bytes(b'latest\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'Current')
    latest = git(repo, 'rev-parse', 'HEAD').decode().strip()
    data = root / 'data'
    params = data / 'params/d'
    params.mkdir(parents=True)
    for key, value in {'AutomaticUpdates': b'1', 'IsOnroad': b'0', 'IsOffroad': b'1', 'KeepSetting': b'yes'}.items():
      (params / key).write_bytes(value)
    yield repo, data, old, latest
  assert not root.exists(), 'Disposable index recovery fixture was not removed'
  print('CLEANUP VERIFIED: ' + str(root))


def install(checkout):
  repo, data, old, latest = checkout
  return Path(installer.install(
    repo, {'branch': 'Dom', 'commit': old, 'head': latest, 'pinned': True}, data_root=data,
    check_parked=lambda: installer.require_parked(data), progress=lambda *args: None,
    require_device_binaries=False)['backup'])


@pytest.mark.parametrize('changes', ['staged_only', 'partially_staged', 'binary_modes_symlink_add_remove'])
def test_recovery_round_trips_index_and_worktree_separately(checkout, changes):
  repo, data, old, latest = checkout
  original = (repo / 'tracked.txt').read_bytes()
  if changes == 'staged_only':
    (repo / 'tracked.txt').write_bytes(b'staged value absent from worktree\n')
    git(repo, 'add', 'tracked.txt')
    (repo / 'tracked.txt').write_bytes(original)
    assert git(repo, 'diff', '--binary', 'HEAD') == b''
    assert git(repo, 'diff', '--cached', '--binary', 'HEAD')
  elif changes == 'partially_staged':
    (repo / 'tracked.txt').write_bytes(b'ONE\ntwo\nthree\n')
    git(repo, 'add', 'tracked.txt')
    (repo / 'tracked.txt').write_bytes(b'ONE\ntwo\nTHREE\n')
  else:
    (repo / 'binary.bin').write_bytes(b'\x00staged binary\xfe')
    (repo / 'binary.bin').chmod(0o755)
    (repo / 'tracked-link').unlink()
    (repo / 'tracked-link').symlink_to('binary.bin')
    (repo / 'added.bin').write_bytes(b'\x00new staged file\xff')
    git(repo, 'add', 'binary.bin', 'tracked-link', 'added.bin')
    git(repo, 'rm', 'removed.txt')
    (repo / 'binary.bin').write_bytes(b'\x00unstaged binary\xfd')
    (repo / 'added.bin').write_bytes(b'\x00new staged plus working edit\xfd')
    # A staged deletion may coexist with an untracked recreation of that path.
    (repo / 'removed.txt').write_bytes(b'new untracked replacement\n')
    (repo / 'tool.sh').write_bytes(b'#!/bin/sh\nexit 0\n')
    (repo / 'tool.sh').chmod(0o755)
  index_before = git(repo, 'ls-files', '--stage', '-z')
  staged_before = git(repo, 'diff', '--cached', '--binary', 'HEAD')
  working_before = git(repo, 'diff', '--binary')
  status_before = git(repo, 'status', '--porcelain=v1', '--untracked-files=all')
  backup = install(checkout)
  assert git(repo, 'rev-parse', 'HEAD').decode().strip() == old
  installer.restore(backup, check_parked=lambda: installer.require_parked(data))
  assert git(repo, 'rev-parse', 'HEAD').decode().strip() == latest
  assert git(repo, 'ls-files', '--stage', '-z') == index_before
  assert git(repo, 'diff', '--cached', '--binary', 'HEAD') == staged_before
  assert git(repo, 'diff', '--binary') == working_before
  assert git(repo, 'status', '--porcelain=v1', '--untracked-files=all') == status_before
  assert (data / 'params/d/KeepSetting').read_bytes() == b'yes'
  if changes == 'binary_modes_symlink_add_remove':
    assert (repo / 'tracked-link').readlink() == Path('binary.bin')
    assert (repo / 'removed.txt').read_bytes() == b'new untracked replacement\n'
    assert (repo / 'tool.sh').stat().st_mode & 0o111 == 0o111


def test_legacy_combined_patch_backup_still_restores_worktree(checkout):
  repo, data, old, latest = checkout
  (repo / 'tracked.txt').write_bytes(b'legacy combined local changes\n')
  combined = git(repo, 'diff', '--binary', 'HEAD')
  backup = install(checkout)
  # Before index preservation, working.patch represented HEAD -> worktree.
  (backup / 'index.patch').unlink(missing_ok=True)
  (backup / 'working.patch').write_bytes(combined)
  installer.restore(backup, check_parked=lambda: installer.require_parked(data))
  assert git(repo, 'rev-parse', 'HEAD').decode().strip() == latest
  assert git(repo, 'diff', '--binary', 'HEAD') == combined
  assert git(repo, 'diff', '--cached', 'HEAD') == b''


def repository_snapshot(repo, data):
  return {
    'head': git(repo, 'rev-parse', 'HEAD'),
    'index': git(repo, 'ls-files', '--stage', '-z'),
    'status': git(repo, 'status', '--porcelain=v1', '--untracked-files=all'),
    'working': (repo / 'tracked.txt').read_bytes(),
    'params': {path.name: path.read_bytes() for path in (data / 'params/d').iterdir()},
  }


def test_conflicted_merge_is_rejected_without_losing_index_stages(checkout):
  repo, data, old, latest = checkout
  git(repo, 'checkout', '-b', 'conflicting-side')
  (repo / 'tracked.txt').write_bytes(b'other branch content\n')
  git(repo, 'commit', '-am', 'Other side')
  git(repo, 'checkout', 'Dom')
  (repo / 'tracked.txt').write_bytes(b'current branch content\n')
  git(repo, 'commit', '-am', 'Current side')
  merge = subprocess.run(['git', '-C', str(repo), 'merge', 'conflicting-side'], capture_output=True)
  assert merge.returncode == 1
  assert git(repo, 'ls-files', '--unmerged')
  before = repository_snapshot(repo, data)
  with pytest.raises(installer.InstallError, match='unmerged|operation in progress'):
    install(checkout)
  assert repository_snapshot(repo, data) == before
  assert not (data / 'starpilot/version-backups').exists()
  # Also prove an unmerged index is rejected when MERGE_HEAD is absent (for
  # example, externally constructed conflict stages or a damaged operation).
  (repo / '.git/MERGE_HEAD').unlink()
  with pytest.raises(installer.InstallError, match='unmerged'):
    install(checkout)
  assert repository_snapshot(repo, data) == before
  assert not (data / 'starpilot/version-backups').exists()


@pytest.mark.parametrize('marker', [
  'MERGE_HEAD', 'REBASE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD',
  'rebase-merge', 'rebase-apply', 'sequencer', 'BISECT_LOG',
])
def test_active_git_operation_markers_are_rejected_before_mutation(checkout, marker):
  repo, data, old, latest = checkout
  (repo / 'tracked.txt').write_bytes(b'valuable local edits\n')
  marker_path = Path(git(repo, 'rev-parse', '--git-path', marker).decode().strip())
  if not marker_path.is_absolute():
    marker_path = repo / marker_path
  if marker in ('rebase-merge', 'rebase-apply', 'sequencer'):
    marker_path.mkdir()
    sentinel = marker_path / 'rehearsal-sentinel'
  else:
    sentinel = marker_path
  sentinel.write_bytes((latest + '\n').encode())
  before = repository_snapshot(repo, data)
  with pytest.raises(installer.InstallError, match='operation in progress'):
    install(checkout)
  assert repository_snapshot(repo, data) == before
  assert sentinel.read_bytes() == (latest + '\n').encode()
  assert not (data / 'starpilot/version-backups').exists()
