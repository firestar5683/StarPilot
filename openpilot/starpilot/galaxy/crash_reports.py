"""Bounded access to reports written by the current tombstoned service."""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
from pathlib import Path
import stat

from openpilot.common.hardware.hw import Paths
from openpilot.system.crash_storage import acquire_lock, open_directory
from openpilot.starpilot.stored_artifacts import DeletionLimit, remove_entry, usage


MAX_SCAN = 1000
MAX_LIST = 200
MAX_PREVIEW = 256 * 1024
MAX_TOKEN = 4096


class CrashUnavailable(Exception):
  pass


class CrashChanged(Exception):
  pass


class CrashMissing(Exception):
  pass


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
  return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


class CrashReports:
  def __init__(self, directory: Path | None = None):
    self.directory = directory if directory is not None else Path(Paths.log_root()) / "crash"

  def _root(self, *, missing_ok: bool = False, exclusive: bool = False) -> tuple[int, os.stat_result, int] | None:
    try:
      fd = open_directory(self.directory)
    except FileNotFoundError:
      if missing_ok:
        return None
      raise CrashMissing from None
    except OSError:
      raise CrashUnavailable from None
    lock = None
    try:
      info = os.fstat(fd)
      self._check_root(info)
      lock = acquire_lock(fd, exclusive=exclusive)
      self._check_root(info)
      return fd, info, lock
    except OSError:
      if lock is not None:
        os.close(lock)
      os.close(fd)
      raise CrashUnavailable from None
    except Exception:
      if lock is not None:
        os.close(lock)
      os.close(fd)
      raise

  def _check_root(self, opened: os.stat_result) -> None:
    try:
      current = os.stat(self.directory, follow_symlinks=False)
    except OSError:
      raise CrashChanged from None
    if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
      raise CrashChanged

  @staticmethod
  def _token(name: str, root: os.stat_result, file: os.stat_result) -> str:
    value = [name, root.st_dev, root.st_ino, *_identity(file)]
    return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).decode().rstrip("=")

  @staticmethod
  def _decode(token: str) -> tuple[str, tuple[int, int], tuple[int, int, int, int, int]]:
    if not token or len(token) > MAX_TOKEN or not all(ch.isascii() and (ch.isalnum() or ch in "-_") for ch in token):
      raise CrashMissing
    try:
      raw = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
      value = json.loads(raw)
    except (ValueError, UnicodeError, binascii.Error, RecursionError):
      raise CrashMissing from None
    if (not isinstance(value, list) or len(value) != 8 or not isinstance(value[0], str) or
        value[0] in ("", ".", "..", ".lock") or "/" in value[0] or "\\" in value[0] or "\0" in value[0] or
        len(value[0]) > 255 or any(type(part) is not int for part in value[1:]) or
        any(part < 0 for part in value[1:6])):
      raise CrashMissing
    return value[0], (value[1], value[2]), tuple(value[3:])

  def list(self) -> dict:
    opened = self._root(missing_ok=True)
    if opened is None:
      return {"schemaVersion": 1, "reports": [], "scanIncomplete": False, "listLimited": False, "reportCount": 0, "storageBytes": 0, "storageIncomplete": False}
    fd, root, lock = opened
    try:
      reports: list[tuple[int, str, dict]] = []
      scanned = 0
      with os.scandir(fd) as entries:
        for entry in entries:
          if entry.name == '.lock':
            continue
          scanned += 1
          if scanned > MAX_SCAN:
            break
          try:
            info = entry.stat(follow_symlinks=False)
          except OSError:
            continue
          if not stat.S_ISREG(info.st_mode) or len(entry.name) > 255:
            continue
          reports.append((info.st_mtime_ns, entry.name,
                          {"id": self._token(entry.name, root, info), "name": entry.name,
                           "size": info.st_size, "modifiedAt": info.st_mtime_ns / 1e9}))
      stored_bytes, storage_incomplete = usage(fd)
      self._check_root(root)
      reports.sort(key=lambda report: (-report[0], report[1]))
      return {"schemaVersion": 1, "reports": [report[2] for report in reports[:MAX_LIST]],
              "scanIncomplete": scanned > MAX_SCAN, "listLimited": len(reports) > MAX_LIST,
              "reportCount": len(reports), "storageBytes": stored_bytes, "storageIncomplete": storage_incomplete}
    except OSError:
      raise CrashUnavailable from None
    finally:
      os.close(lock)
      os.close(fd)

  def preview(self, token: str) -> dict:
    name, root_id, selected = self._decode(token)
    opened = self._root()
    assert opened is not None
    root_fd, root, lock = opened
    try:
      if (root.st_dev, root.st_ino) != root_id:
        raise CrashChanged
      try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
      except FileNotFoundError:
        raise CrashMissing from None
      except OSError:
        raise CrashChanged from None
      try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or _identity(before) != selected:
          raise CrashChanged
        content = bytearray()
        while len(content) <= MAX_PREVIEW:
          chunk = os.read(fd, MAX_PREVIEW + 1 - len(content))
          if not chunk:
            break
          content.extend(chunk)
        after = os.fstat(fd)
        self._check_root(root)
        if _identity(after) != selected:
          raise CrashChanged
        try:
          current_name = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        except OSError:
          raise CrashChanged from None
        if not stat.S_ISREG(current_name.st_mode) or _identity(current_name) != selected:
          raise CrashChanged
        return {"schemaVersion": 1, "name": name,
                "text": bytes(content[:MAX_PREVIEW]).decode("utf-8", "replace"),
                "truncated": len(content) > MAX_PREVIEW or before.st_size > MAX_PREVIEW}
      except OSError:
        raise CrashUnavailable from None
      finally:
        os.close(fd)
    finally:
      os.close(lock)
      os.close(root_fd)

  def _latest_summary(self, directory, name, selected):
    # save_exception writes a timestamped log and a shared latest error.txt.
    pattern = r'[0-9]{4}-[0-9]{2}-[0-9]{2}--[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{6}\.log'
    if re.fullmatch(pattern, name) is None:
      return None
    with os.scandir(directory) as entries:
      for count, entry in enumerate(entries):
        if count >= MAX_SCAN:
          return None
        if entry.name != name and re.fullmatch(pattern, entry.name):
          try:
            info = entry.stat(follow_symlinks=False)
          except FileNotFoundError:
            continue
          if stat.S_ISREG(info.st_mode) and info.st_mtime_ns >= selected.st_mtime_ns:
            return None
    try:
      log_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
      summary_fd = os.open('error.txt', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    except OSError:
      if 'log_fd' in locals():
        os.close(log_fd)
      return None
    try:
      before = os.fstat(summary_fd)
      if not stat.S_ISREG(before.st_mode) or not selected.st_mtime_ns <= before.st_mtime_ns <= selected.st_mtime_ns + 2_000_000_000:
        return None
      log_info = os.fstat(log_fd)
      if _identity(log_info) != _identity(selected):
        return None
      os.lseek(log_fd, max(0, selected.st_size - MAX_PREVIEW), os.SEEK_SET)
      tail = os.read(log_fd, MAX_PREVIEW)
      if selected.st_size > MAX_PREVIEW and tail.count(b'\n') < 11:
        return None
      summary = os.read(summary_fd, MAX_PREVIEW + 1)
      expected = '\n'.join(tail.decode('utf-8', 'replace').splitlines()[-10:]).encode()
      if summary != expected or _identity(os.fstat(summary_fd)) != _identity(before) or _identity(os.fstat(log_fd)) != _identity(selected):
        return None
      return _identity(before)
    finally:
      os.close(log_fd)
      os.close(summary_fd)

  def delete(self, token=None, *, permitted=lambda: True):
    selection = self._decode(token) if token is not None else None
    if not permitted():
      raise PermissionError('Galaxy session expired')
    opened = self._root(missing_ok=True, exclusive=True)
    more = False
    if opened is not None:
      directory, root, lock = opened
      try:
        if not permitted():
          raise PermissionError('Galaxy session expired')
        budget = [4096]
        if selection is None:
          with os.scandir(directory) as entries:
            for entry in entries:
              if entry.name == '.lock':
                continue
              try:
                remove_entry(directory, entry.name, budget)
              except DeletionLimit:
                more = True
                break
        else:
          name, root_id, identity = selection
          if root_id != (root.st_dev, root.st_ino):
            raise CrashChanged
          try:
            current = os.stat(name, dir_fd=directory, follow_symlinks=False)
          except FileNotFoundError:
            current = None
          if current is not None:
            if not stat.S_ISREG(current.st_mode) or _identity(current) != identity:
              raise CrashChanged
            summary = self._latest_summary(directory, name, current)
            remove_entry(directory, name, budget)
            if summary is not None:
              try:
                latest = os.stat('error.txt', dir_fd=directory, follow_symlinks=False)
              except FileNotFoundError:
                latest = None
              if latest is not None and _identity(latest) == summary:
                remove_entry(directory, 'error.txt', budget)
        self._check_root(root)
        os.fsync(directory)
      except (OSError, DeletionLimit):
        raise CrashUnavailable from None
      finally:
        os.close(lock)
        os.close(directory)
    return {**self.list(), 'more': more}
