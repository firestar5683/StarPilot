"""Short, namespaced camera leases. Manager alone owns camera processes."""
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import tempfile
import time

TTL_NS = 15_000_000_000
FRAME_TTL_NS = 5_000_000_000


def boot_ns():
  return time.clock_gettime_ns(getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC))


def _path(name):
  prefix = os.environ.get('OPENPILOT_PREFIX', 'd')
  namespace = hashlib.sha256(prefix.encode()).hexdigest()[:16]
  return Path('/dev/shm') / f'starpilot-camera-{os.getuid()}-{namespace}' / name


def _read(path):
  fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
  try:
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > 32:
      raise ValueError('Invalid camera lease')
    return int(os.read(fd, 32))
  finally:
    os.close(fd)


def _write(path, value):
  path = Path(path)
  path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
  info = path.parent.lstat()
  if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
    raise OSError('Camera lease directory is not private')
  lock = os.open(path.with_name(path.name + '.lock'), os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
  temporary = None
  try:
    info = os.fstat(lock)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
      raise OSError('Invalid camera lease lock')
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
      previous = _read(path)
      if abs(previous - value) <= TTL_NS:
        value = max(value, previous)
    except (OSError, ValueError):
      pass
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
      os.write(fd, str(value).encode())
    finally:
      os.close(fd)
    os.replace(temporary, path)
    temporary = None
  finally:
    if temporary is not None:
      os.unlink(temporary)
    os.close(lock)


def request(clock=boot_ns, path=None):
  _write(path or _path('lease'), clock() + TTL_NS)


def requested(clock=boot_ns, path=None):
  try:
    remaining = _read(path or _path('lease')) - clock()
    return 0 < remaining <= TTL_NS
  except (OSError, ValueError):
    return False


def mark_frame(clock=boot_ns, path=None):
  _write(path or _path('cabin-frame'), clock())


def frame_available(clock=boot_ns, path=None):
  try:
    return 0 <= clock() - _read(path or _path('cabin-frame')) <= FRAME_TTL_NS
  except (OSError, ValueError):
    return False
