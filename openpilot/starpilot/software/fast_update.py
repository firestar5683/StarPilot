import os
from pathlib import Path
import re
import subprocess

from openpilot.common.vendor_manifest import validate_revision
from openpilot.common.prebuilt_manifest import revision_digest, valid_receipt


class FastUpdateError(RuntimeError):
  pass


def run(command, cwd):
  environment = dict(os.environ, GIT_LFS_SKIP_SMUDGE='1', GIT_TERMINAL_PROMPT='0')
  return subprocess.check_output(command, cwd=cwd, env=environment, stderr=subprocess.STDOUT,
                                 timeout=120 if "fetch" in command or "reset" in command else 30).decode()


def fast_update(repo, branch, *, params, parked, expected_commit, current_os=None, invalidate=None, run=run):
  repo = Path(repo)

  def git(*arguments):
    return run(['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c', 'core.hooksPath=/dev/null', '-c', 'submodule.recurse=false', '-c', 'filter.lfs.required=false',
                '-c', 'filter.lfs.smudge=', '-c', 'filter.lfs.process=', *arguments], cwd=str(repo))

  def admitted():
    if not parked():
      raise FastUpdateError('Fast Update requires fresh parked state')
    if git('symbolic-ref', '--short', 'HEAD').strip() != branch:
      raise FastUpdateError('Fast Update only updates the current branch')
    if git('status', '--porcelain', '--untracked-files=no').strip():
      raise FastUpdateError('Tracked source has local changes')

  git('check-ref-format', '--branch', branch)
  admitted()
  previous = git('rev-parse', 'HEAD^{commit}').strip()
  if not isinstance(expected_commit, str) or not re.fullmatch(r'[0-9a-f]{40}', expected_commit) or previous != expected_commit:
    raise FastUpdateError('Approved source revision changed; refresh and try again')
  git('fetch', '--depth=1', '--no-tags', '--no-recurse-submodules', 'origin', f'refs/heads/{branch}')
  target = git('rev-parse', 'FETCH_HEAD^{commit}').strip()
  validate_revision(repo, target)
  launch = git('show', f'{target}:launch_env.sh')
  versions = re.findall(r'^\s*export\s+AGNOS_VERSION=["\']([^"\'\n]+)["\']\s*$', launch, re.MULTILINE)
  if len(versions) != 1 or not current_os or versions[0] != current_os:
    raise FastUpdateError('Update requires a different or unverified operating system')
  if target == previous:
    return 'up-to-date'
  for revision in (previous, target):
    if git('ls-tree', revision, '--', 'prebuilt').strip().split()[:1] != ['100644']:
      raise FastUpdateError('Fast Update requires prebuilt releases; use a full validated update')
  if not valid_receipt(git, target) and revision_digest(git, previous) != revision_digest(git, target):
    raise FastUpdateError('Native build inputs or artifacts changed without a matching build receipt; use a full validated update')
  tracked = set(git('ls-tree', '-rz', '--name-only', target).split('\0')) - {''}
  untracked = set(git('ls-files', '--others', '-z').split('\0')) - {''}
  directories = {str(parent) for name in tracked for parent in Path(name).parents if str(parent) != '.'}
  for name in untracked:
    if name in tracked or name in directories or any(str(parent) in tracked for parent in Path(name).parents):
      raise FastUpdateError('Update would overwrite untracked data')
  admitted()
  if git('rev-parse', 'HEAD^{commit}').strip() != previous:
    raise FastUpdateError('Source changed during download')
  if invalidate is None:
    raise FastUpdateError('Update staging invalidation is unavailable')
  git('update-ref', 'refs/starpilot/previous', previous)
  invalidate()
  admitted()
  if git('rev-parse', 'HEAD^{commit}').strip() != previous:
    raise FastUpdateError('Source changed before installation')
  try:
    git('reset', '--hard', '--no-recurse-submodules', target)
    if git('rev-parse', 'HEAD^{commit}').strip() != target:
      raise FastUpdateError('Applied source revision does not match download')
    validate_revision(repo, 'HEAD')
    if not parked():
      raise FastUpdateError('Parked state changed before restart')
    params.put_bool('DoReboot', True, block=True)
  except Exception:
    git('reset', '--hard', '--no-recurse-submodules', previous)
    if git('rev-parse', 'HEAD^{commit}').strip() != previous:
      raise FastUpdateError('Source rollback failed')
    raise
  return 'reboot-requested'
