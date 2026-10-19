"""The current log directory and the two recording roots used by older StarPilot."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat

from openpilot.common.hardware.hw import Paths

DEFAULT_LOG_ROOT = '/data/media/0/realdata'
LEGACY_NAMES = ('realdata_HD', 'realdata_konik')
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
_LOCAL = r'(?:[a-f0-9]{8}--[a-f0-9]{10}|[0-9]{4}-[0-9]{2}-[0-9]{2}--[0-9]{2}-[0-9]{2}-[0-9]{2})'
_SEGMENT = re.compile(rf'(?:{_LOCAL}|[a-f0-9]{{16}}[|_]{_LOCAL})--(?:0|[1-9][0-9]{{0,5}})\Z')
MAX_NOTICE_ENTRIES = 2048


@dataclass(frozen=True)
class RecordingRoot:
  path: str
  device: int
  inode: int
  legacy: bool = False


def _root_path(path: str | Path) -> str:
  value = os.fspath(path).rstrip('/') or '/'
  return value if os.path.isabs(value) else os.path.join(os.getcwd(), value)


def open_recording_root(path: str) -> int:
  path = _root_path(path)
  default = Path(DEFAULT_LOG_ROOT)
  if path != str(default) and path not in {str(default.parent / name) for name in LEGACY_NAMES}:
    return os.open(path, DIR_FLAGS)
  # Do not follow a symlink in any component of an automatically admitted root.
  fd = os.open('/', DIR_FLAGS)
  try:
    for component in Path(path).parts[1:]:
      child = os.open(component, DIR_FLAGS, dir_fd=fd)
      os.close(fd)
      fd = child
    result, fd = fd, -1
    return result
  finally:
    if fd >= 0:
      os.close(fd)


def root_current(root: RecordingRoot, fd: int) -> bool:
  current_fd = -1
  try:
    opened = os.fstat(fd)
    if (opened.st_dev, opened.st_ino) != (root.device, root.inode):
      return False
    current_fd = open_recording_root(root.path)
    current = os.fstat(current_fd)
    return (current.st_dev, current.st_ino) == (root.device, root.inode)
  except OSError:
    return False
  finally:
    if current_fd >= 0:
      os.close(current_fd)


def recording_roots(current: str | Path | None = None) -> tuple[RecordingRoot, ...]:
  path = _root_path(Paths.log_root() if current is None else current)
  default = _root_path(DEFAULT_LOG_ROOT)
  names = [path]
  if not os.environ.get('LOG_ROOT') and path == default:
    names += [str(Path(default).parent / name) for name in LEGACY_NAMES]
  roots = []
  identities = set()
  for name in names:
    fd = -1
    try:
      fd = open_recording_root(name)
      info = os.fstat(fd)
      identity = (info.st_dev, info.st_ino)
      if not roots and name != path:
        break
      if (roots and info.st_dev != roots[0].device) or identity in identities:
        continue
      root = RecordingRoot(name, *identity, legacy=name != path)
      if not stat.S_ISDIR(info.st_mode) or not root_current(root, fd):
        continue
      roots.append(root)
      identities.add(identity)
    except OSError:
      if name == path:
        break
    finally:
      if fd >= 0:
        os.close(fd)
  return tuple(roots)


def legacy_segment(name: str) -> bool:
  return _SEGMENT.fullmatch(name) is not None


def legacy_recordings_present(current: str | Path) -> bool:
  for root in recording_roots(current):
    if not root.legacy:
      continue
    fd = -1
    try:
      fd = open_recording_root(root.path)
      if not root_current(root, fd):
        continue
      with os.scandir(fd) as entries:
        for count, entry in enumerate(entries, 1):
          if count > MAX_NOTICE_ENTRIES:
            break
          if legacy_segment(entry.name) and entry.is_dir(follow_symlinks=False):
            return root_current(root, fd)
    except OSError:
      continue
    finally:
      if fd >= 0:
        os.close(fd)
  return False
