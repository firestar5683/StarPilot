import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess


def git(root, *args):
  return subprocess.check_output(['git', '-C', str(root), *args])


def tracked(root):
  return [os.fsdecode(path) for path in git(root, 'ls-files', '-z').split(b'\0') if path]


def fingerprint(path):
  mode = path.lstat().st_mode
  if stat.S_ISLNK(mode):
    return {'kind': 'symlink', 'mode': stat.S_IMODE(mode), 'sha256': hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()}
  if not stat.S_ISREG(mode):
    raise ValueError(f'Not a regular file: {path}')
  return {'kind': 'file', 'mode': stat.S_IMODE(mode), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def read_manifest(path):
  path = Path(path)
  metadata = path.lstat()
  if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
    raise ValueError('Unsafe build manifest')
  if metadata.st_size > 16 * 1024 * 1024:
    raise ValueError('Oversized build manifest')
  value = json.loads(path.read_text())
  if value.get('format') != 'starpilot-ci-build' or value.get('version') != 1:
    raise ValueError('Unsupported build manifest')
  return value


def capture(root, destination, outputs, config):
  root = Path(root).resolve()
  destination = Path(destination).absolute()
  if destination.resolve().is_relative_to(root):
    raise ValueError('Build manifest must be outside checkout')
  revision = git(root, 'rev-parse', 'HEAD').decode().strip()
  if destination.exists():
    existing = read_manifest(destination)
    if existing['root'] != str(root) or existing['revision'] != revision or existing['config'] != config:
      raise ValueError('Stale build manifest')
    return
  if git(root, 'status', '--porcelain', '--untracked-files=all'):
    raise ValueError('Checkout must be clean before build')
  files = {name: fingerprint(root / name) for name in tracked(root)}
  selected = sorted(set(outputs) & files.keys())
  if any(files[name]['kind'] != 'file' for name in selected):
    raise ValueError('Derived output is not a regular file')
  value = {'format': 'starpilot-ci-build', 'version': 1, 'root': str(root), 'revision': revision,
           'config': config, 'files': files, 'outputs': selected}
  with open(destination, 'x', opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
    json.dump(value, stream, sort_keys=True)
    stream.flush()
    os.fsync(stream.fileno())


def verify(root, manifest):
  root = Path(root).resolve()
  value = read_manifest(manifest)
  if value['root'] != str(root) or value['revision'] != git(root, 'rev-parse', 'HEAD').decode().strip():
    raise ValueError('Build manifest belongs to a different checkout or revision')
  files = value['files']
  outputs = set(value['outputs'])
  if not outputs <= files.keys() or set(tracked(root)) != files.keys():
    raise ValueError('Tracked inventory changed')
  if git(root, 'diff', '--cached', '--name-only'):
    raise ValueError('Index changed during build')
  if git(root, 'ls-files', '--others', '--exclude-standard', '-z'):
    raise ValueError('Untracked files created during build')
  for name, before in files.items():
    if Path(name).is_absolute() or '..' in Path(name).parts:
      raise ValueError('Unsafe manifest path')
    after = fingerprint(root / name)
    if after['kind'] != before['kind'] or after['mode'] != before['mode']:
      raise ValueError(f'File type or mode changed: {name}')
    if name in outputs:
      if after['kind'] != 'file' or (root / name).stat().st_size == 0:
        raise ValueError(f'Missing or empty derived output: {name}')
    elif after != before:
      raise ValueError(f'Source or undeclared output changed: {name}')


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--manifest', required=True)
  args = parser.parse_args()
  verify(git(Path.cwd(), 'rev-parse', '--show-toplevel').decode().strip(), args.manifest)
