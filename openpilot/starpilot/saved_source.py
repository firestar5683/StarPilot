"""Bounded saved-setting reads for the shared feature owner."""

import os
import stat


def read_saved(params, key: str, limit: int) -> tuple[bytes | None, bool]:
  """Return complete bytes/absence and readability; never authorize a prefix."""
  path = params.get_param_path(key)
  flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
  try:
    fd = os.open(path, flags)
  except FileNotFoundError:
    return None, True
  except OSError:
    return b"", False
  try:
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
      return b"", False
    with os.fdopen(fd, "rb", closefd=False) as source:
      raw = source.read(limit + 1)
    after = os.fstat(fd)
    current = os.stat(path, follow_symlinks=False)
    if (len(raw) > limit or not stat.S_ISREG(after.st_mode) or
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
        (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or
        (current.st_dev, current.st_ino) != (after.st_dev, after.st_ino)):
      return b"", False
    return raw, True
  except OSError:
    return b"", False
  finally:
    os.close(fd)
