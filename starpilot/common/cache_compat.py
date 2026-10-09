import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import uuid
from contextlib import ExitStack

KEYS = ('CarParamsCache', 'CarParamsPersistent', 'CarParamsPrevRoute', 'CalibrationParams',
        'LiveParametersV2', 'LiveTorqueParameters', 'LiveDelay')
PREFIX = b'SPCACHE'
MAX_BYTES = 32 * 1024 * 1024


def _sync(path):
  fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
  try:
    os.fsync(fd)
  finally:
    os.close(fd)


def _read(path):
  fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
  with os.fdopen(fd, 'rb') as source:
    if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
      raise ValueError('Cache source must be a regular file')
    raw = source.read(MAX_BYTES + 1)
  if len(raw) > MAX_BYTES:
    raise ValueError('Cache exceeds recovery limit')
  return raw


def _private(path):
  path.mkdir(mode=0o700, parents=True, exist_ok=True)
  info = path.lstat()
  if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
    raise ValueError('Recovery storage must be private and owned')
  return path


def _save(path, raw):
  fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
  temporary = Path(name)
  try:
    with os.fdopen(fd, 'wb') as output:
      output.write(raw)
      output.flush()
      os.fsync(output.fileno())
    if _read(temporary) != raw:
      raise ValueError('Recovery temporary readback failed')
    try:
      os.link(temporary, path, follow_symlinks=False)
    except FileExistsError:
      info = path.lstat()
      if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Unsafe recovery file') from None
    if _read(path) != raw:
      raise ValueError('Recovery archive readback failed')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
      os.fsync(fd)
    finally:
      os.close(fd)
  finally:
    temporary.unlink(missing_ok=True)


def _publish_handoff(namespace, target):
  name = '.starpilot-dom-handoff-' + hashlib.sha256(str(namespace).encode()).hexdigest() + '.json'
  marker = namespace.parent / name
  if marker.exists() or marker.is_symlink():
    info = marker.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
      raise ValueError('Unsafe branch handoff marker')
  value = {'format': 'starpilot-dom-handoff', 'version': 1, 'namespace': str(namespace),
           'target': str(target), 'token': uuid.uuid4().hex}
  raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
  if len(raw) > 4096:
    raise ValueError('Branch handoff marker exceeds limit')
  fd, name = tempfile.mkstemp(prefix='.handoff-', dir=namespace.parent)
  temporary = Path(name)
  try:
    with os.fdopen(fd, 'wb') as output:
      output.write(raw)
      output.flush()
      os.fsync(output.fileno())
    if namespace.resolve(strict=True) != target:
      raise ValueError('Params namespace changed during handoff')
    os.replace(temporary, marker)
    _sync(namespace.parent)
  finally:
    temporary.unlink(missing_ok=True)


def retire_foreign_caches(primary, secondary, archive):
  primary = Path(primary).absolute()
  namespaces = sorted({Path(path).absolute() for path in (primary, secondary)}, key=str)
  archive = Path(archive).absolute()
  with ExitStack() as locks:
    for root in sorted({path.parent for path in namespaces}, key=str):
      fd = os.open(root / '.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
      locks.callback(os.close, fd)
      if not stat.S_ISREG(os.fstat(fd).st_mode):
        raise ValueError('Invalid Params lock')
      fcntl.flock(fd, fcntl.LOCK_EX)
    targets = {path: path.resolve(strict=True) for path in namespaces}
    for path, target in targets.items():
      if target.parent != path.parent.resolve() or not target.is_dir():
        raise ValueError('Invalid Params namespace')
      if archive == target or target in archive.parents:
        raise ValueError('Recovery archive cannot be inside Params')
    originals = []
    for namespace in namespaces:
      for key in KEYS:
        try:
          raw = _read(targets[namespace] / key)
        except FileNotFoundError:
          continue
        if raw.startswith(PREFIX):
          originals.append((namespace, key, raw))
    if not originals:
      _publish_handoff(primary, targets[primary])
      return ()
    _private(archive)
    records = []
    for namespace, key, raw in originals:
      digest = hashlib.sha256(raw).hexdigest()
      _save(archive / digest, raw)
      records.append({'namespace': str(namespace), 'target': str(targets[namespace]), 'key': key,
                      'sha256': digest, 'size': len(raw)})
    manifest = json.dumps(records, sort_keys=True, separators=(',', ':')).encode()
    _save(archive / (hashlib.sha256(manifest).hexdigest() + '.json'), manifest)
    _sync(archive)
    _sync(archive.parent)
    for namespace, key, raw in originals:
      if namespace.resolve(strict=True) != targets[namespace] or _read(targets[namespace] / key) != raw:
        raise ValueError('Cache source changed during recovery')
    for namespace, key, _raw in originals:
      (targets[namespace] / key).unlink()
      _sync(targets[namespace])
    _publish_handoff(primary, targets[primary])
    return tuple(records)
