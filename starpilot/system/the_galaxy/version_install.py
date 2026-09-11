"""Exact-revision checkout and local recovery. No vehicle-control dependencies.

A copy of this module is saved outside the checkout as recover.py before reset.
Run that copy with --restore while parked if the installed Galaxy lacks history.
"""
import argparse
import ast
import inspect
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import tempfile
import sqlite3
import subprocess
import tarfile
import time


OS_VERSION_FILE = Path("/VERSION")
_ACTIVE_UPDATER = ContextVar("version_install_updater", default=None)


class InstallError(RuntimeError):
  pass


def git(repo, *args, binary=False, timeout=120):
  result = subprocess.run(['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-C', str(repo), *args],
                          capture_output=True, timeout=timeout, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
  if result.returncode:
    raise InstallError(result.stderr.decode(errors='replace').strip()[-2000:] or 'Git operation failed')
  return result.stdout if binary else result.stdout.decode(errors='replace').strip()


def atomic_write(path, data):
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
  fd, name = tempfile.mkstemp(prefix=path.name + '.version-', dir=path.parent)
  temporary = Path(name)
  try:
    with os.fdopen(fd, 'wb') as stream:
      os.fchmod(stream.fileno(), mode)
      stream.write(data)
      stream.flush()
      os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
      os.fsync(fd)
    finally:
      os.close(fd)
  finally:
    temporary.unlink(missing_ok=True)


def require_parked(data_root=Path('/data')):
  params = Path(data_root) / 'params/d'
  try:
    parked = (params / 'IsOnroad').read_bytes() == b'0' and (params / 'IsOffroad').read_bytes() == b'1'
  except OSError:
    parked = False
  if not parked:
    raise InstallError('A confirmed parked device is required.')


def validate_target(target):
  if not isinstance(target, dict):
    raise InstallError('Invalid target')
  branch, commit = target.get('branch'), target.get('commit')
  if not isinstance(branch, str) or not branch or branch.startswith('-'):
    raise InstallError('Invalid target branch')
  check = subprocess.run(['git', 'check-ref-format', '--branch', branch], capture_output=True)
  if check.returncode or not isinstance(commit, str) or not re.fullmatch(r'[0-9a-f]{40}', commit):
    raise InstallError('An exact validated commit and branch are required')


def read_pin(repo, data_root=Path('/data')):
  try:
    value = json.loads((Path(data_root) / 'starpilot/version_selection.json').read_text())
    if isinstance(value, dict) and value.get('commit') == git(repo, 'rev-parse', 'HEAD') and value.get('branch') == git(repo, 'branch', '--show-current'):
      return value
  except (OSError, ValueError, InstallError):
    pass
  return None


def _agnos_version(text):
  match = re.search(r'^\s*(?:export\s+)?AGNOS_VERSION=[\"\']?([0-9][0-9A-Za-z._-]*)', text, re.M)
  if not match:
    raise InstallError('Unable to determine the selected version\'s AGNOS requirement')
  return match.group(1)


def _selected_firmware_name(app_fn, remote_start, hkg_remote_start, ignore_ignition_line, tesla_wake=False):
  if not remote_start and not hkg_remote_start and not ignore_ignition_line and not tesla_wake:
    return app_fn
  name_parts = ["panda_h7" if app_fn == "panda_h7.bin.signed" else "panda"]
  if tesla_wake:
    name_parts.extend(["tesla", "wake"])
  elif hkg_remote_start:
    name_parts.extend(["hkg", "remote"])
  elif remote_start:
    name_parts.append("remote")
  if ignore_ignition_line:
    name_parts.append("can_ignition_only")
  return "_".join(name_parts) + ".bin.signed"


def _check_firmware_settings(repo, commit, data_root):
  keys = ('TeslaWakeOnCAN', 'RemoteStartBootsComma', 'HKGRemoteStartBootsComma', 'IgnoreIgnitionLine',
          'RemoteStart', 'HkgRemoteStart')
  enabled = {key for key in keys if (Path(data_root) / 'params/d' / key).is_file()
             and (Path(data_root) / 'params/d' / key).read_bytes() == b'1'}
  if not enabled:
    return
  label = ', '.join(sorted(enabled))
  if 'TeslaWakeOnCAN' in enabled and enabled & {'RemoteStartBootsComma', 'HKGRemoteStartBootsComma', 'RemoteStart', 'HkgRemoteStart'}:
    raise InstallError('Tesla wake firmware cannot be combined with remote-start firmware')
  try:
    source = git(repo, 'show', commit + ':selfdrive/pandad/panda_firmware.py')
    # Compare syntax with a reviewed pure selector; never execute selected source.
    def normalized(node):
      node.name = 'selector'
      node.returns = None
      for arg in node.args.args:
        arg.annotation = None
      return ast.dump(node, include_attributes=False)
    selected = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'get_selected_firmware_name')
    expected = ast.parse(inspect.getsource(_selected_firmware_name)).body[0]
    reviewed = {normalized(expected)}
    # Current Dom adds this exact conflict guard to the earlier reviewed selector.
    # Accept both known trees; never evaluate code from the selected revision.
    expected.body.insert(0, ast.parse('if tesla_wake and (remote_start or hkg_remote_start):\n  raise ValueError("Tesla wake firmware cannot be combined with remote-start firmware")').body[0])
    reviewed.add(normalized(expected))
    if normalized(selected) not in reviewed:
      raise ValueError('unrecognized firmware selection logic')
    target_keys = git(repo, 'show', commit + ':common/params_keys.h')
    if any(key not in target_keys for key in enabled):
      raise ValueError('target does not preserve the enabled parameter')
    flags = (bool(enabled & {'RemoteStartBootsComma', 'RemoteStart'}),
             bool(enabled & {'HKGRemoteStartBootsComma', 'HkgRemoteStart'}),
             'IgnoreIgnitionLine' in enabled, 'TeslaWakeOnCAN' in enabled)
    for app_fn in ('panda.bin.signed', 'panda_h7.bin.signed'):
      filename = _selected_firmware_name(app_fn, *flags)
      if not git(repo, 'show', commit + ':panda/board/obj/' + filename, binary=True):
        raise ValueError('empty firmware image: ' + filename)
  except (InstallError, SyntaxError, StopIteration, ValueError) as error:
    raise InstallError(f'The selected revision cannot preserve enabled firmware settings ({label}): {error}') from error


def preflight(repo, commit, require_device_binaries=True, data_root=Path('/data')):
  target_version = _agnos_version(git(repo, 'show', commit + ':launch_env.sh'))
  if require_device_binaries:
    try:
      installed_version = OS_VERSION_FILE.read_text().strip()
    except OSError as error:
      raise InstallError('Cannot verify the installed AGNOS version') from error
    if installed_version != target_version:
      raise InstallError(f'The running device has AGNOS {installed_version}; selected revision requires {target_version}')
  current_version = _agnos_version((Path(repo) / 'launch_env.sh').read_text())
  if target_version != current_version:
    raise InstallError(f'This revision requires AGNOS {target_version}; current software requires {current_version}. OS changes are not supported by historical installation.')
  manifest = 'system/hardware/tici/agnos.json'
  try:
    target_manifest = json.loads(git(repo, 'show', commit + ':' + manifest))
    current_manifest = json.loads((Path(repo) / manifest).read_text())
  except (OSError, ValueError) as error:
    raise InstallError('Cannot verify AGNOS compatibility') from error
  if target_manifest != current_manifest:
    raise InstallError('The selected revision has a different AGNOS firmware manifest. Install a revision compatible with the current OS.')
  # Reject generations which would ignore the persistent update-pause setting.
  if ('AutomaticUpdates' not in git(repo, 'show', commit + ':common/params_keys.h') or
      'automatic_updates' not in git(repo, 'show', commit + ':starpilot/common/starpilot_variables.py') or
      'automatic_updates_enabled' not in git(repo, 'show', commit + ':system/updated/updated.py')):
    raise InstallError('This revision does not support pausing automatic updates safely')
  git(repo, 'cat-file', '-e', commit + ':launch_chffrplus.sh')
  _check_firmware_settings(repo, commit, data_root)
  if require_device_binaries:
    for name in ('common/params_pyx.so', 'selfdrive/pandad/pandad', 'system/camerad/camerad'):
      data = git(repo, 'show', commit + ':' + name, binary=True)
      if data[:4] != b'\x7fELF' or data[4:6] != b'\x02\x01' or data[18:20] != b'\xb7\x00':
        raise InstallError(f'The selected revision lacks a compatible ARM64 artifact: {name}')
  return {'agnos': target_version}


def check_repository_idle(repo):
  for name in ('index.lock', 'shallow.lock', 'config.lock', 'packed-refs.lock', 'HEAD.lock',
               'MERGE_HEAD', 'REBASE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD',
               'rebase-merge', 'rebase-apply', 'sequencer', 'BISECT_LOG'):
    path = Path(git(repo, 'rev-parse', '--git-path', name))
    if not path.is_absolute():
      path = Path(repo) / path
    if path.exists():
      if name.endswith('.lock'):
        raise InstallError(f'Repository is busy ({name}); wait for the existing Git operation to finish')
      raise InstallError(f'Repository has a Git operation in progress ({name}); finish or abort it before installing or restoring')
  # Ordinary patches cannot represent the multiple index stages of a conflict.
  # Check independently of operation markers, which may be missing or stale.
  if git(repo, 'ls-files', '--unmerged'):
    raise InstallError('Repository has unmerged index entries; resolve them before installing or restoring')


def _check_submodules(repo):
  # A superproject patch cannot preserve modified or untracked submodule files.
  if not (Path(repo) / '.gitmodules').is_file():
    return
  if any(line.startswith(('+', 'U')) for line in git(repo, 'submodule', 'status', '--recursive').splitlines()):
    raise InstallError('A submodule checkout differs from the recorded revision; save it before installing')
  dirty = git(repo, 'submodule', 'foreach', '--quiet', '--recursive',
              'git status --porcelain --untracked-files=all --ignore-submodules=none')
  if dirty:
    raise InstallError('A submodule has local changes; save them before installing')


def _backup(repo, target, data_root):
  data_root, repo = Path(data_root), Path(repo).resolve()
  folder = data_root / 'starpilot/version-backups' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + os.urandom(3).hex())
  params = data_root / 'params/d'
  # HEAD -> index and index -> worktree are separate states. A combined HEAD
  # diff can be empty even when the index contains valuable staged-only edits.
  index_patch = git(repo, 'diff', '--cached', '--binary', 'HEAD', binary=True)
  patch = git(repo, 'diff', '--binary', binary=True)
  files = [name for name in git(repo, 'ls-files', '--others', '--exclude-standard', '-z', binary=True).decode().split('\0') if name]
  for name in files:
    if not stat.S_ISREG((repo / name).lstat().st_mode):
      raise InstallError(f'Untracked recovery entry must be a regular file (no symlinks): {name}')
  size = len(index_patch) + len(patch) + sum((repo / name).lstat().st_size for name in files)
  if size > 128 * 1024 * 1024:
    raise InstallError('Local source changes exceed the recovery backup limit (128 MiB)')
  if shutil.disk_usage(data_root).free < size + 512 * 1024 * 1024:
    raise InstallError('At least 512 MiB of free space beyond local changes is required for recovery')
  folder.mkdir(parents=True, exist_ok=False)
  atomic_write(folder / 'index.patch', index_patch)
  atomic_write(folder / 'working.patch', patch)
  with tarfile.open(folder / 'untracked.tar', 'w') as archive:
    for name in files:
      archive.add(repo / name, arcname=name, recursive=False)
  shutil.copytree(params, folder / 'params', symlinks=False)
  stats = data_root / 'starpilot/model_stats.sqlite'
  if stats.is_file():
    deadline = time.monotonic() + 60
    def progress(*_):
      if time.monotonic() > deadline:
        raise InstallError('Statistics backup timed out; no source files were changed')
    with sqlite3.connect(stats.as_uri() + '?mode=ro', uri=True, timeout=10) as source, sqlite3.connect(folder / 'model_stats.sqlite') as destination:
      source.backup(destination, pages=256, progress=progress)
  old = {'repo': str(repo), 'dataRoot': str(data_root), 'branch': git(repo, 'branch', '--show-current'),
         'commit': git(repo, 'rev-parse', 'HEAD'), 'target': target, 'createdAt': datetime.now(timezone.utc).isoformat(),
         'oldPin': read_pin(repo, data_root)}
  if not old['branch']:
    raise InstallError('Detached local checkout cannot be recovered by this installer')
  git(repo, 'update-ref', 'refs/starpilot/version-backups/' + folder.name, old['commit'])
  atomic_write(folder / 'recovery.json', json.dumps(old, indent=2).encode())
  shutil.copyfile(__file__, folder / 'recover.py')
  atomic_write(folder / 'README.txt', b'Park the car, then run: python3 recover.py --restore\nThis returns to the saved source and local edits. Current settings and statistics are kept.\nSaved params and statistics are available for manual recovery; they are not automatically overwritten.\n')
  os.sync()
  return folder


def _clear_staging(data_root):
  # Invalidate the boot-time swap; never delete staged source or drive data.
  (Path(data_root) / 'safe_staging/finalized/.overlay_consistent').unlink(missing_ok=True)
  os.sync()


def restore(folder, *, check_parked, restore_data=False):
  if restore_data:
    raise InstallError('Settings/statistics restoration is manual to preserve newer data')
  folder = Path(folder)
  old = json.loads((folder / 'recovery.json').read_text())
  repo, data_root = Path(old['repo']), Path(old['dataRoot'])
  validate_target(old)
  check_parked()
  check_repository_idle(repo)
  # Validate the whole archive before changing the checkout.
  with tarfile.open(folder / 'untracked.tar') as archive:
    for member in archive.getmembers():
      if member.name.startswith('/') or '..' in Path(member.name).parts or not member.isfile():
        raise InstallError('Unsafe recovery archive entry')
  atomic_write(data_root / 'params/d/AutomaticUpdates', b'0')
  updater = _ACTIVE_UPDATER.get()
  if updater is not None:
    updater.restart_after_install()
  git(repo, 'checkout', '--force', '-B', old['branch'], old['commit'])
  git(repo, 'reset', '--hard', old['commit'])
  if (repo / '.gitmodules').is_file():
    git(repo, 'submodule', 'sync', '--recursive')
    git(repo, 'submodule', 'update', '--init', '--recursive', '--depth=1', timeout=240)
  # Older backups contain only a combined HEAD -> worktree patch. New backups
  # first restore staged content and modes, then apply only unstaged changes.
  index_patch = folder / 'index.patch'
  if index_patch.is_file() and index_patch.stat().st_size:
    git(repo, 'apply', '--index', '--binary', str(index_patch))
  patch = folder / 'working.patch'
  if patch.stat().st_size:
    git(repo, 'apply', '--binary', str(patch))
  # Archive members come from the local Git untracked list. Reject path escape
  # and links rather than letting a modified recovery archive overwrite /data.
  with tarfile.open(folder / 'untracked.tar') as archive:
    for member in archive.getmembers():
      destination = repo / member.name
      if member.name.startswith('/') or '..' in Path(member.name).parts or member.issym() or member.islnk():
        raise InstallError('Unsafe recovery archive entry')
      if member.isfile():
        if not destination.resolve().is_relative_to(repo.resolve()):
          raise InstallError('Recovery destination escapes the checkout')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with archive.extractfile(member) as source:
          atomic_write(destination, source.read())
        destination.chmod(member.mode)
  pin = data_root / 'starpilot/version_selection.json'
  if old.get('oldPin'):
    atomic_write(pin, json.dumps(old['oldPin']).encode())
  else:
    pin.unlink(missing_ok=True)
  _clear_staging(data_root)
  return old


def install(repo, target, *, data_root=Path('/data'), check_parked, progress, require_device_binaries=True):
  repo, data_root = Path(repo), Path(data_root)
  validate_target(target)
  check_parked()
  sha = target['commit']
  if git(repo, 'rev-parse', sha + '^{commit}') != sha:
    raise InstallError('Fetched revision does not match the selected commit')
  progress(2, 'Checking compatibility', 100, sha[:10])
  check_repository_idle(repo)
  _check_submodules(repo)
  preflight(repo, sha, require_device_binaries, data_root)
  check_parked()
  progress(3, 'Saving recovery backup', 0, 'Preserving local changes, settings and model statistics')
  backup = _backup(repo, target, data_root)
  check_parked()
  atomic_write(data_root / 'params/d/AutomaticUpdates', b'0')
  updater = _ACTIVE_UPDATER.get()
  if updater is not None:
    updater.restart_after_install()
  _clear_staging(data_root)
  try:
    progress(4, 'Installing selected revision', 10, target['branch'] + ' @ ' + sha[:10])
    git(repo, 'checkout', '--force', '-B', target['branch'], sha)
    git(repo, 'reset', '--hard', sha)
    git(repo, 'config', 'branch.' + target['branch'] + '.remote', 'origin')
    git(repo, 'config', 'branch.' + target['branch'] + '.merge', 'refs/heads/' + target['branch'])
    if git(repo, 'rev-parse', 'HEAD') != sha:
      raise InstallError('Installed revision failed verification')
    modules = repo / '.gitmodules'
    if modules.is_file() and '[submodule ' in modules.read_text():
      check_parked()
      git(repo, 'submodule', 'sync', '--recursive')
      git(repo, 'submodule', 'update', '--init', '--recursive', '--depth=1', timeout=240)
    for name in ('.sconsign.dblite', 'cereal/gen'):
      path = repo / name
      if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
      else:
        path.unlink(missing_ok=True)
    pin = data_root / 'starpilot/version_selection.json'
    if target['pinned']:
      atomic_write(pin, json.dumps({'branch': target['branch'], 'commit': sha, 'installedAt': datetime.now(timezone.utc).isoformat(), 'backup': str(backup)}).encode())
    else:
      pin.unlink(missing_ok=True)
    atomic_write(data_root / 'starpilot/last-version-recovery.json', json.dumps({'backup': str(backup)}).encode())
    updater = _ACTIVE_UPDATER.get()
    if updater is not None:
      updater.restart_after_install()
    progress(4, 'Installing selected revision', 100, 'Exact commit verified; automatic updates paused')
    return {'backup': str(backup), 'branch': target['branch'], 'commit': sha, 'pinned': target['pinned']}
  except Exception as error:
    try:
      restore(backup, check_parked=check_parked)
    except Exception as recovery_error:
      raise InstallError(f'Installation failed: {error}. Recovery required: {backup}/recover.py ({recovery_error})') from error
    raise InstallError(f'Installation failed; previous source restored: {error}. Backup: {backup}') from error


def _is_updater(argv):
  return any(arg in (b'system.updated.updated', b'openpilot.system.updated.updated') or
             arg.endswith(b'/system/updated/updated.py') for arg in argv)


class UpdaterMaintenance:
  def __init__(self):
    self.restart = False

  def restart_after_install(self):
    self.restart = True


def _processes():
  records = {}
  for folder in Path('/proc').iterdir():
    if not folder.name.isdigit():
      continue
    try:
      fields = (folder / 'stat').read_text().rsplit(')', 1)[1].split()
      records[int(folder.name)] = (int(fields[1]), fields[19], fields[0], (folder / 'cmdline').read_bytes().split(b'\0'))
    except (OSError, ValueError, IndexError):
      continue
  return records


@contextmanager
def suspend_updater():
  """Suspend only the background updater and its children for maintenance."""
  stopped = []
  control = UpdaterMaintenance()
  token = _ACTIVE_UPDATER.set(control)
  try:
    records = _processes()
    parents = {pid for pid, (_, _, _, argv) in records.items() if _is_updater(argv)}
    pending = parents
    while pending:
      for pid in pending:
        entry = records.get(pid)
        if entry and entry[2] not in ('T', 't'):
          try:
            os.kill(pid, signal.SIGSTOP)
            stopped.append((pid, entry[1]))
          except ProcessLookupError:
            pass
      records = _processes()
      pending = {pid for pid, entry in records.items() if entry[0] in pending}
    deadline = time.monotonic() + 2
    while True:
      records = _processes()
      if all(pid not in records or records[pid][1] != start or records[pid][2] in ('T', 't', 'Z')
             for pid, start in stopped):
        break
      if time.monotonic() >= deadline:
        raise InstallError('Updater did not stop; no installation was started')
      time.sleep(0.01)
    yield control
  finally:
    _ACTIVE_UPDATER.reset(token)
    records = _processes()
    for pid, start in reversed(stopped):
      if pid in records and records[pid][1] == start:
        try:
          # A stopped updater caches AutomaticUpdates. After source mutation,
          # let manager restart it so it reads the persisted pause setting.
          os.kill(pid, signal.SIGKILL if control.restart else signal.SIGCONT)
        except ProcessLookupError:
          pass


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--restore', action='store_true', required=True)
  args = parser.parse_args()
  saved = Path(__file__).resolve().parent
  with suspend_updater() as updater:
    result = restore(saved, check_parked=require_parked)
    updater.restart_after_install()
  print('Previous source restored. Settings and statistics retained. Reboot the device when ready.')
