"""Refuse destructive checkout when ordinary patches cannot preserve local files."""
import pytest

from test_version_install_index import checkout, git, install, installer, repository_snapshot


@pytest.mark.parametrize('flag', ['assume-unchanged', 'skip-worktree'])
def test_hidden_index_flags_refuse_install_without_mutation(checkout, flag):
  repo, data, old, latest = checkout
  git(repo, 'update-index', '--' + flag, 'tracked.txt')
  (repo / 'tracked.txt').write_bytes(b'valuable hidden working edit\n')
  before = repository_snapshot(repo, data)
  flags = git(repo, 'ls-files', '-v', '-z')
  with pytest.raises(installer.InstallError, match='assume-unchanged|skip-worktree'):
    install(checkout)
  assert repository_snapshot(repo, data) == before
  assert git(repo, 'ls-files', '-v', '-z') == flags
  assert not (data / 'starpilot/version-backups').exists()


@pytest.mark.parametrize('flag', ['assume-unchanged', 'skip-worktree'])
def test_hidden_index_flags_refuse_restore_without_mutation(checkout, flag):
  repo, data, old, latest = checkout
  backup = install(checkout)
  git(repo, 'update-index', '--' + flag, 'tracked.txt')
  (repo / 'tracked.txt').write_bytes(b'valuable hidden post-install edit\n')
  before = repository_snapshot(repo, data)
  flags = git(repo, 'ls-files', '-v', '-z')
  with pytest.raises(installer.InstallError, match='assume-unchanged|skip-worktree'):
    installer.restore(backup, check_parked=lambda: installer.require_parked(data))
  assert repository_snapshot(repo, data) == before
  assert git(repo, 'ls-files', '-v', '-z') == flags


def ignored_checkout(checkout, shape):
  repo, data, old, latest = checkout
  target_path = 'hidden-local/child.txt' if shape == 'ancestor' else 'hidden-local'
  target = repo / target_path
  target.parent.mkdir(parents=True, exist_ok=True)
  target.write_bytes(b'target committed content\n')
  git(repo, 'add', target_path)
  git(repo, 'commit', '-m', 'Target containing collision path')
  target_sha = git(repo, 'rev-parse', 'HEAD').decode().strip()
  git(repo, 'rm', target_path)
  git(repo, 'commit', '-m', 'Current without collision path')
  current = git(repo, 'rev-parse', 'HEAD').decode().strip()
  (repo / '.git/info/exclude').write_text('hidden-local\n')
  local = repo / ('hidden-local/child.txt' if shape == 'descendant' else 'hidden-local')
  local.parent.mkdir(parents=True, exist_ok=True)
  outside = data / 'outside-sentinel'
  outside.write_bytes(b'valuable local ignored content\n')
  if shape == 'symlink':
    local.symlink_to(outside)
  else:
    local.write_bytes(outside.read_bytes())
  return (repo, data, target_sha, current), local, outside


@pytest.mark.parametrize('shape', ['exact', 'ancestor', 'descendant', 'symlink'])
def test_ignored_conflicts_refuse_install_before_backup(checkout, shape):
  state, local, outside = ignored_checkout(checkout, shape)
  repo, data, old, latest = state
  before = repository_snapshot(repo, data)
  with pytest.raises(installer.InstallError, match='[Ii]gnored'):
    install(state)
  assert repository_snapshot(repo, data) == before
  assert local.read_bytes() == outside.read_bytes() == b'valuable local ignored content\n'
  assert local.is_symlink() == (shape == 'symlink')
  assert not (data / 'starpilot/version-backups').exists()


@pytest.mark.parametrize('shape', ['exact', 'ancestor', 'descendant', 'symlink'])
def test_ignored_conflicts_refuse_restore_without_mutation(checkout, shape):
  state, local, outside = ignored_checkout(checkout, shape)
  repo, data, target, current = state
  # Save source that tracks the conflicting path, then mimic a later checkout
  # with a newly created ignored file. Restore must inspect that live state.
  if local.is_symlink() or local.is_file():
    local.unlink()
  else:
    raise AssertionError('Expected a file or symlink')
  if shape == 'descendant':
    local.parent.rmdir()
  git(repo, 'checkout', '--force', '-B', 'Dom', target)
  backup = installer._backup(repo, {'branch': 'Dom', 'commit': current, 'pinned': False}, data)
  git(repo, 'checkout', '--force', '-B', 'Dom', current)
  local.parent.mkdir(parents=True, exist_ok=True)
  if shape == 'symlink':
    local.symlink_to(outside)
  else:
    local.write_bytes(outside.read_bytes())
  before = repository_snapshot(repo, data)
  with pytest.raises(installer.InstallError, match='[Ii]gnored'):
    installer.restore(backup, check_parked=lambda: installer.require_parked(data))
  assert repository_snapshot(repo, data) == before
  assert local.read_bytes() == outside.read_bytes() == b'valuable local ignored content\n'
  assert local.is_symlink() == (shape == 'symlink')


def test_nonconflicting_ignored_files_allow_install_and_restore(checkout):
  repo, data, old, latest = checkout
  (repo / '.git/info/exclude').write_text('local-cache/\ntracked.txt.extra\n')
  paths = [repo / 'local-cache/data.bin', repo / 'tracked.txt.extra']
  for path in paths:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'kept ignored content\n')
  backup = install(checkout)
  installer.restore(backup, check_parked=lambda: installer.require_parked(data))
  assert all(path.read_bytes() == b'kept ignored content\n' for path in paths)
