"""The local crash collector and report cleanup share one retained directory lock."""
from contextlib import contextmanager
import errno
import fcntl
import os
from pathlib import Path
import shutil
import stat
import time


DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def open_directory(root: Path, *, create=False):
  if not root.is_absolute() or '..' in root.parts:
    raise OSError(errno.EINVAL, 'Invalid crash directory')
  directory = os.open('/', DIR_FLAGS)
  try:
    for part in root.parts[1:]:
      if create:
        try:
          os.mkdir(part, 0o755, dir_fd=directory)
        except FileExistsError:
          pass
      child = os.open(part, DIR_FLAGS, dir_fd=directory)
      os.close(directory)
      directory = child
    return directory
  except BaseException:
    os.close(directory)
    raise


def acquire_lock(directory, *, exclusive=True, timeout=1.0):
  lock = os.open('.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
  try:
    opened = os.fstat(lock)
    if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_uid != os.geteuid() or opened.st_mode & 0o077:
      raise OSError(errno.EPERM, 'Invalid crash storage lock')
    deadline = time.monotonic() + timeout
    while True:
      try:
        fcntl.flock(lock, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        break
      except BlockingIOError:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
          raise
        time.sleep(min(.01, remaining))
    current = os.stat('.lock', dir_fd=directory, follow_symlinks=False)
    if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
      raise OSError(errno.ESTALE, 'Crash storage lock changed')
    return lock
  except BaseException:
    os.close(lock)
    raise


@contextmanager
def writer(root: Path):
  directory = open_directory(root, create=True)
  lock = None
  try:
    lock = acquire_lock(directory)
    yield directory
    os.fsync(directory)
  finally:
    if lock is not None:
      os.close(lock)
    os.close(directory)


def _output(directory, name):
  if name in ('', '.', '..', '.lock') or '/' in name or '\\' in name or '\0' in name:
    raise ValueError('Invalid crash report name')
  fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o666, dir_fd=directory)
  try:
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid():
      raise OSError(errno.EPERM, 'Invalid crash report file')
    os.ftruncate(fd, 0)
    return fd
  except BaseException:
    os.close(fd)
    raise


def write_text(directory, name, text):
  with os.fdopen(_output(directory, name), 'w', encoding='utf-8') as output:
    output.write(text)
    output.flush()
    os.fsync(output.fileno())


def copy_report(directory, name, source):
  with open(source, 'rb') as input_file, os.fdopen(_output(directory, name), 'wb') as output:
    shutil.copyfileobj(input_file, output, length=1024 * 1024)
    output.flush()
    os.fchmod(output.fileno(), stat.S_IMODE(os.fstat(input_file.fileno()).st_mode))
    os.fsync(output.fileno())
