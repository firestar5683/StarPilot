#!/usr/bin/env python3
import fcntl
import os
import shutil
import stat
import threading
from openpilot.common.hardware.hw import Paths
from openpilot.common.swaglog import cloudlog
from openpilot.system.loggerd.config import get_available_bytes, get_available_percent
from openpilot.system.loggerd.uploader import get_directory_sort, listdir_by_creation
from openpilot.system.loggerd.xattr_cache import getxattr

MIN_BYTES = 5 * 1024 * 1024 * 1024
MIN_PERCENT = 10

DELETE_LAST = ['boot', 'crash']

PRESERVE_ATTR_NAME = 'user.preserve'
PRESERVE_ATTR_VALUE = b'1'
PRESERVE_COUNT = 5


def has_preserve_xattr(d: str) -> bool:
  return getxattr(os.path.join(Paths.log_root(), d), PRESERVE_ATTR_NAME) == PRESERVE_ATTR_VALUE


def _recorded_time(root: str, d: str) -> float:
  for name in ('qlog.zst', 'qlog.bz2', ''):
    try:
      return os.stat(os.path.join(root, d, name)).st_mtime
    except OSError:
      continue
  return 0.


def listdir_by_age(root: str) -> list[str]:
  # RouteCount resets on migration, so order routes by newest qlog time instead of name.
  dirs = listdir_by_creation(root)
  route_times: dict[str, float] = {}
  for d in dirs:
    route = d.rpartition('--')[0] or d
    route_times[route] = max(route_times.get(route, 0.), _recorded_time(root, d))
  return sorted(dirs, key=lambda d: (route_times[d.rpartition('--')[0] or d], get_directory_sort(d)))


def get_preserved_segments(dirs_by_creation: list[str]) -> set[str]:
  # skip deleting most recent N preserved segments (and their prior segment)
  preserved = set()
  for n, d in enumerate(filter(has_preserve_xattr, reversed(dirs_by_creation))):
    if n == PRESERVE_COUNT:
      break
    date_str, _, seg_str = d.rpartition("--")

    # ignore non-segment directories
    if not date_str:
      continue
    try:
      seg_num = int(seg_str)
    except ValueError:
      continue

    # preserve segment and two prior
    for _seg_num in range(max(0, seg_num - 2), seg_num + 1):
      preserved.add(f"{date_str}--{_seg_num}")

  return preserved


def deleter_step() -> tuple[bool, str | None]:
  out_of_bytes = get_available_bytes(default=MIN_BYTES + 1) < MIN_BYTES
  out_of_percent = get_available_percent(default=MIN_PERCENT + 1) < MIN_PERCENT
  out_of_space = out_of_percent or out_of_bytes
  if not out_of_space:
    return False, None

  dirs = listdir_by_age(Paths.log_root())
  preserved_dirs = get_preserved_segments(dirs)

  # remove the earliest directory we can
  for delete_dir in sorted(dirs, key=lambda d: (d in DELETE_LAST, d in preserved_dirs)):
    delete_path = os.path.join(Paths.log_root(), delete_dir)

    root_fd = fd = -1
    try:
      flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
      root_fd = os.open(Paths.log_root(), flags)
      fd = os.open(delete_dir, flags, dir_fd=root_fd)
      try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
      except BlockingIOError:
        continue
      if any(name.endswith(".lock") for name in os.listdir(fd)):
        continue
      opened = os.fstat(fd)
      current = os.stat(delete_dir, dir_fd=root_fd, follow_symlinks=False)
      root = os.fstat(root_fd)
      current_root = os.stat(Paths.log_root(), follow_symlinks=False)
      if (root.st_dev, root.st_ino) != (current_root.st_dev, current_root.st_ino):
        continue
      if not stat.S_ISDIR(current.st_mode) or (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
        continue
      cloudlog.info(f"deleting {delete_path}")
      shutil.rmtree(delete_dir, dir_fd=root_fd)
      return True, delete_path
    except FileNotFoundError:
      continue
    except OSError:
      cloudlog.exception(f"issue deleting {delete_path}")
    finally:
      if fd >= 0:
        os.close(fd)
      if root_fd >= 0:
        os.close(root_fd)
  return True, None


def deleter_thread(exit_event: threading.Event):
  while not exit_event.is_set():
    out_of_space, _ = deleter_step()
    exit_event.wait(.1 if out_of_space else 30)


def main():
  deleter_thread(threading.Event())


if __name__ == "__main__":
  main()
