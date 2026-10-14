"""Bounded cleanup of entries in an already opened storage-owner directory."""
import os
import stat


class DeletionLimit(Exception):
  pass


def remove_entry(directory, name, budget, *, depth=0):
  if name in ('', '.', '..') or '/' in name or '\\' in name or '\0' in name:
    raise ValueError('Invalid stored artifact name')
  if budget[0] <= 0 or depth > 8:
    raise DeletionLimit('Stored artifact cleanup limit reached')
  budget[0] -= 1
  try:
    info = os.stat(name, dir_fd=directory, follow_symlinks=False)
  except FileNotFoundError:
    return
  if stat.S_ISDIR(info.st_mode):
    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
    try:
      opened = os.fstat(child)
      if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
        raise OSError('Stored artifact changed')
      with os.scandir(child) as entries:
        for entry in entries:
          remove_entry(child, entry.name, budget, depth=depth + 1)
      os.fsync(child)
    finally:
      os.close(child)
    os.rmdir(name, dir_fd=directory)
  else:
    # Unlink a symlink itself, never its target; hard links likewise stay bounded.
    os.unlink(name, dir_fd=directory)


def usage(directory, *, budget=None, depth=0):
  budget = [4096] if budget is None else budget
  total = 0
  incomplete = False
  with os.scandir(directory) as entries:
    for entry in entries:
      if entry.name == '.lock':
        continue
      if budget[0] <= 0 or depth > 8:
        return total, True
      budget[0] -= 1
      try:
        info = entry.stat(follow_symlinks=False)
        if stat.S_ISREG(info.st_mode):
          total += info.st_size
        elif stat.S_ISDIR(info.st_mode):
          child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
          try:
            size, partial = usage(child, budget=budget, depth=depth + 1)
            total += size
            incomplete |= partial
          finally:
            os.close(child)
      except OSError:
        incomplete = True
  return total, incomplete
