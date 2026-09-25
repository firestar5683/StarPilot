"""Bounded, read-only access to reports written by the current tombstoned service."""

from __future__ import annotations

import base64
import binascii
import json
import os
from pathlib import Path
import stat

from openpilot.common.hardware.hw import Paths


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

  def _root(self, *, missing_ok: bool = False) -> tuple[int, os.stat_result] | None:
    try:
      fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
      if missing_ok:
        return None
      raise CrashMissing from None
    except OSError:
      raise CrashUnavailable from None
    try:
      info = os.fstat(fd)
      self._check_root(info)
      return fd, info
    except Exception:
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
        value[0] in ("", ".", "..") or "/" in value[0] or "\\" in value[0] or "\0" in value[0] or
        len(value[0]) > 255 or any(type(part) is not int for part in value[1:]) or
        any(part < 0 for part in value[1:6])):
      raise CrashMissing
    return value[0], (value[1], value[2]), tuple(value[3:])

  def list(self) -> dict:
    opened = self._root(missing_ok=True)
    if opened is None:
      return {"schemaVersion": 1, "reports": [], "scanIncomplete": False, "listLimited": False}
    fd, root = opened
    try:
      reports: list[tuple[int, str, dict]] = []
      scanned = 0
      with os.scandir(fd) as entries:
        for entry in entries:
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
      self._check_root(root)
      reports.sort(key=lambda report: (-report[0], report[1]))
      return {"schemaVersion": 1, "reports": [report[2] for report in reports[:MAX_LIST]],
              "scanIncomplete": scanned > MAX_SCAN, "listLimited": len(reports) > MAX_LIST}
    except OSError:
      raise CrashUnavailable from None
    finally:
      os.close(fd)

  def preview(self, token: str) -> dict:
    name, root_id, selected = self._decode(token)
    opened = self._root()
    assert opened is not None
    root_fd, root = opened
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
      os.close(root_fd)
