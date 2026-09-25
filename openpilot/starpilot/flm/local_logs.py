"""Admit one immutable, closed local rlog for offline analysis; never download."""

from collections.abc import Callable
from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import stat

from openpilot.starpilot.galaxy.drive_history import MAX_SEGMENT_ENTRIES, SEGMENT_NAME


MAX_COMPRESSED_BYTES = 32 * 1024 * 1024
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
RLOGS = {"rlog.zst": "zst", "rlog.bz2": "bz2"}


class LocalLogUnavailable(Exception):
  pass


@dataclass(frozen=True)
class ClosedLog:
  segment_name: str
  codec: str
  compressed: bytes = field(repr=False)
  sha256: str
  size: int


def _identity(info: os.stat_result) -> tuple[int, int]:
  return info.st_dev, info.st_ino


def _revision(info: os.stat_result) -> tuple[int, ...]:
  return (*_identity(info), info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _allowed(permitted: Callable[[], bool]) -> None:
  if not permitted():
    raise LocalLogUnavailable("Analysis is no longer allowed")


def _closed_rlog(fd: int) -> str:
  found = []
  with os.scandir(fd) as entries:
    for count, entry in enumerate(entries, 1):
      if count > MAX_SEGMENT_ENTRIES or entry.name.endswith(".lock"):
        raise LocalLogUnavailable("Segment is open or unavailable")
      if entry.name in RLOGS:
        found.append(entry.name)
  if len(found) != 1:
    raise LocalLogUnavailable("Select a segment with exactly one closed full rlog")
  return found[0]


def read_closed_rlog(root: Path, segment_name: str, *, permitted: Callable[[], bool]) -> ClosedLog:
  """Revalidate an inventory choice, then bind its receipt to the bytes read.

  The inventory is not authority: locks, file type, bounds and inode revisions
  are checked again at admission and after the complete read. The supplied
  root is the locally configured recording directory, never an HTTP input.
  No decoded events or successful receipt escape a partial/cancelled read.
  """
  matched = SEGMENT_NAME.fullmatch(segment_name) if type(segment_name) is str and len(segment_name) <= 180 else None
  if matched is None or len(matched.group("number")) > 6 or not root.is_absolute() or ".." in root.parts:
    raise LocalLogUnavailable("Invalid local segment selection")
  fds = []
  try:
    _allowed(permitted)
    root_fd = os.open(root, DIR_FLAGS)
    fds.append(root_fd)
    root_info = os.fstat(root_fd)
    segment_fd = os.open(segment_name, DIR_FLAGS, dir_fd=root_fd)
    fds.append(segment_fd)
    segment_info = os.fstat(segment_fd)
    filename = _closed_rlog(segment_fd)
    source_fd = os.open(filename, FILE_FLAGS, dir_fd=segment_fd)
    fds.append(source_fd)
    before = os.fstat(source_fd)
    if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_COMPRESSED_BYTES:
      raise LocalLogUnavailable("Full rlog is empty, oversized or not a regular file")
    chunks = []
    remaining = before.st_size
    while remaining:
      _allowed(permitted)
      chunk = os.read(source_fd, min(1024 * 1024, remaining))
      if not chunk:
        raise LocalLogUnavailable("Full rlog changed while reading")
      chunks.append(chunk)
      remaining -= len(chunk)
    if os.read(source_fd, 1):
      raise LocalLogUnavailable("Full rlog grew while reading")
    _allowed(permitted)
    after = os.fstat(source_fd)
    current = os.stat(filename, dir_fd=segment_fd, follow_symlinks=False)
    segment_now = os.stat(segment_name, dir_fd=root_fd, follow_symlinks=False)
    root_now = os.stat(root, follow_symlinks=False)
    if (_revision(before) != _revision(after) or _revision(after) != _revision(current) or
        not stat.S_ISREG(current.st_mode) or not stat.S_ISDIR(segment_now.st_mode) or
        not stat.S_ISDIR(root_now.st_mode) or _identity(segment_now) != _identity(segment_info) or
        _identity(root_now) != _identity(root_info) or _closed_rlog(segment_fd) != filename):
      raise LocalLogUnavailable("Local recording identity changed")
    raw = b"".join(chunks)
    _allowed(permitted)
    return ClosedLog(segment_name, RLOGS[filename], raw, hashlib.sha256(raw).hexdigest(), len(raw))
  except (OSError, ValueError) as error:
    raise LocalLogUnavailable("Local recording is unavailable") from error
  finally:
    for fd in reversed(fds):
      os.close(fd)
