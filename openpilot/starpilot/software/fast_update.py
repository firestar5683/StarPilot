import os
from pathlib import Path
import re
import subprocess
import time
import selectors
import signal

from openpilot.common.vendor_manifest import validate_revision
from openpilot.common.prebuilt_manifest import revision_digest, valid_receipt


class FastUpdateError(RuntimeError):
  pass


def _stop_process(process):
  try:
    os.killpg(process.pid, signal.SIGTERM)
  except ProcessLookupError:
    pass
  deadline = time.monotonic() + 5
  while time.monotonic() < deadline:
    process.poll()
    try:
      os.killpg(process.pid, 0)
    except ProcessLookupError:
      break
    time.sleep(0.05)
  try:
    os.killpg(process.pid, signal.SIGKILL)
  except ProcessLookupError:
    pass
  process.wait(timeout=5)


def run(command, cwd, progress=None, *, timeout=None):
  environment = dict(os.environ, GIT_LFS_SKIP_SMUDGE='1', GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='/bin/false', SSH_ASKPASS='/bin/false')
  if timeout is None:
    timeout = 120 if "fetch" in command or "reset" in command or "checkout" in command else 30
  output = bytearray()
  with subprocess.Popen(command, cwd=cwd, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True) as process:
    assert process.stdout is not None
    with selectors.DefaultSelector() as selector:
      selector.register(process.stdout, selectors.EVENT_READ)
      deadline = time.monotonic() + timeout
      pending = b""
      try:
        while selector.get_map():
          if time.monotonic() >= deadline:
            raise subprocess.TimeoutExpired(command, timeout, output=bytes(output))
          for key, _ in selector.select(min(0.1, max(0.0, deadline - time.monotonic()))):
            chunk = os.read(key.fileobj.fileno(), 4096)
            if not chunk:
              selector.unregister(key.fileobj)
              continue
            output.extend(chunk)
            pending += chunk
            lines = re.split(b'[\r\n]', pending)
            pending = lines.pop()
            for line in lines:
              detail = line.decode('utf-8', errors='replace')
              pattern = r'(?:remote: )?(?:Enumerating objects|Counting objects|Compressing objects|Receiving objects|Resolving deltas|Total|Updating files):'
              if progress is not None and re.match(pattern, detail):
                progress(detail[-512:])
        result = process.wait(timeout=max(0.01, deadline - time.monotonic()))
        if result:
          raise subprocess.CalledProcessError(result, command, output=bytes(output))
      except BaseException:
        _stop_process(process)
        raise
  return output.decode('utf-8', errors='replace')


_DEFAULT_RUN = run


def fast_update(repo, branch, *, params, parked, expected_commit, current_os=None, invalidate=None, run=run, rollback=False, progress=None, sleep=None):
  repo = Path(repo)

  def notify(stage, detail):
    if progress is not None:
      progress(stage, detail)

  notify('preparing', 'Resolving active branch...')

  def git(*arguments):
    command = [
      'git',
      '-c',
      'gc.auto=0',
      '-c',
      'maintenance.auto=false',
      '-c',
      'core.hooksPath=/dev/null',
      '-c',
      'submodule.recurse=false',
      '-c',
      'filter.lfs.required=false',
      '-c',
      'filter.lfs.smudge=',
      '-c',
      'filter.lfs.process=',
      *arguments,
    ]
    if run is _DEFAULT_RUN:
      return run(command, cwd=str(repo), progress=(lambda detail: notify('fetching', detail)) if 'fetch' in arguments else None)
    return run(command, cwd=str(repo))

  def admitted():
    if not parked():
      raise FastUpdateError('Fast Update requires fresh parked state')
    if git('symbolic-ref', '--short', 'HEAD').strip() != initial_branch:
      raise FastUpdateError('Installed branch changed; refresh and try again')
    if git('status', '--porcelain', '--untracked-files=no').strip():
      raise FastUpdateError('Tracked source has local changes')

  git('check-ref-format', '--branch', branch)
  initial_branch = git('symbolic-ref', '--short', 'HEAD').strip()
  admitted()
  previous = git('rev-parse', 'HEAD^{commit}').strip()
  if not isinstance(expected_commit, str) or not re.fullmatch(r'[0-9a-f]{40}', expected_commit) or previous != expected_commit:
    raise FastUpdateError('Approved source revision changed; refresh and try again')
  if rollback:
    target = git('rev-parse', '--verify', 'refs/starpilot/previous^{commit}').strip()
    saved = git('config', '--local', '--get', 'starpilot.previousVersion').strip().split(' ', 1)
    if len(saved) != 2 or saved[0] != target:
      raise FastUpdateError('Previous version receipt is incomplete; use a full validated update')
    branch = saved[1]
    git('check-ref-format', '--branch', branch)
    notify('fetching', 'Previous installed version is available locally.')
  else:
    notify('fetching', f'Fetching latest shallow commit on {branch}...')
    git('fetch', '--progress', '--depth=1', '--no-tags', '--no-recurse-submodules', 'origin', f'refs/heads/{branch}')
    target = git('rev-parse', 'FETCH_HEAD^{commit}').strip()
  notify('validating', 'Checking downloaded operating system and native artifacts...')
  validate_revision(repo, target)
  launch = git('show', f'{target}:launch_env.sh')
  versions = re.findall(r'^\s*export\s+AGNOS_VERSION=["\']([^"\'\n]+)["\']\s*$', launch, re.MULTILINE)
  if len(versions) != 1 or not current_os or versions[0] != current_os:
    raise FastUpdateError('Update requires a different or unverified operating system')
  if target == previous and branch == initial_branch:
    notify('complete', 'Already up to date.')
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

  def optional(*arguments):
    try:
      return git(*arguments).strip()
    except subprocess.CalledProcessError:
      return None

  retained = optional('rev-parse', '--verify', 'refs/starpilot/previous^{commit}')
  retained_branch = optional('config', '--local', '--get', 'starpilot.previousVersion')
  git('update-ref', 'refs/starpilot/previous', previous)
  git('config', '--local', 'starpilot.previousVersion', f'{previous} {initial_branch}')
  try:
    invalidate()
    admitted()
    if git('rev-parse', 'HEAD^{commit}').strip() != previous:
      raise FastUpdateError('Source changed before installation')
    notify('applying', 'Applying fetched commit...')
    if branch != initial_branch:
      git('checkout', '--force', '--no-recurse-submodules', '-B', branch, target)
    else:
      git('reset', '--hard', '--no-recurse-submodules', target)
    if git('rev-parse', 'HEAD^{commit}').strip() != target:
      raise FastUpdateError('Applied source revision does not match download')
    validate_revision(repo, 'HEAD')
    if not parked():
      raise FastUpdateError('Parked state changed before restart')
    notify('submodules', 'No submodules configured; dependencies are vendored in this release.')
    notify('rebooting', 'Update complete. Device is rebooting; please wait for reconnection.')
    (sleep or time.sleep)(6.0)
    if not parked():
      raise FastUpdateError('Parked state changed before restart')
    notify('complete', 'Update installed. Device is restarting; please wait for reconnection.')
    params.put_bool('DoReboot', True, block=True)
  except Exception:
    notify('error', 'Update failed; restoring the previous installed version.')
    if git('symbolic-ref', '--short', 'HEAD').strip() != initial_branch:
      git('checkout', '--force', '--no-recurse-submodules', '-B', initial_branch, previous)
    else:
      git('reset', '--hard', '--no-recurse-submodules', previous)
    if git('rev-parse', 'HEAD^{commit}').strip() != previous:
      raise FastUpdateError('Source rollback failed') from None
    if retained is None:
      git('update-ref', '-d', 'refs/starpilot/previous')
    else:
      git('update-ref', 'refs/starpilot/previous', retained)
    if retained_branch is None:
      optional('config', '--local', '--unset', 'starpilot.previousVersion')
    else:
      git('config', '--local', 'starpilot.previousVersion', retained_branch)
    raise
  return 'reboot-requested'
