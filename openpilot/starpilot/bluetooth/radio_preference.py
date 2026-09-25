"""The registered AGNOS radio preference in the global Params namespace.

The service uses /data/params/d independently of named application prefixes.
The key has no manager default: absence must not create or disable the radio."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile


RADIO_PREFERENCE = Path('/data/params/d/BluetoothEnabled')


class RadioPreference:
  def __init__(self, path: Path = RADIO_PREFERENCE):
    self.path = path

  @staticmethod
  def _read(path: Path) -> tuple[bytes | None, tuple | None]:
    try:
      fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
      return None, None
    with os.fdopen(fd, 'rb') as stream:
      info = os.fstat(stream.fileno())
      if not stat.S_ISREG(info.st_mode) or info.st_size > 16:
        raise OSError('Invalid Bluetooth enable file')
      value = stream.read(17)
      if len(value) > 16:
        raise OSError('Invalid Bluetooth enable file')
      return value, (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size)

  def enabled(self) -> bool:
    value, _ = self._read(self.path)
    return value is not None and value.rstrip(b'\n') == b'1'

  def begin(self, enabled: bool) -> RadioPreferenceChange:
    return RadioPreferenceChange(self.path, b'1' if enabled else b'0')


class RadioPreferenceChange:
  def __init__(self, path: Path, value: bytes):
    self.path = path
    self.directory = path.parent.resolve(strict=True)
    info = self.directory.stat()
    self.directory_identity = (info.st_dev, info.st_ino)
    self.target = self.directory / path.name
    self.previous, self.previous_identity = RadioPreference._read(self.target)
    self.value = value
    self.owned_identity = None

  def apply(self) -> None:
    self._write(self.value, self.previous, self.previous_identity)
    self.verify()

  def current(self, value: bytes | None, identity: tuple | None) -> bool:
    try:
      directory = self.path.parent.resolve(strict=True)
      info = directory.stat()
      return (directory == self.directory and (info.st_dev, info.st_ino) == self.directory_identity and
              RadioPreference._read(self.target) == (value, identity))
    except OSError:
      return False

  def _write(self, value: bytes, expected: bytes | None, identity: tuple | None) -> None:
    fd, temporary = tempfile.mkstemp(prefix='.bluetooth-enable-', dir=self.directory)
    try:
      with os.fdopen(fd, 'wb') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
        info = os.fstat(stream.fileno())
        written_identity = (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size)
      if not self.current(expected, identity):
        raise OSError('Bluetooth preference changed')
      os.replace(temporary, self.target)
      self.owned_identity = written_identity
      self._sync()
    finally:
      if os.path.exists(temporary):
        os.unlink(temporary)

  def _sync(self) -> None:
    fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
      os.fsync(fd)
    finally:
      os.close(fd)

  def verify(self) -> None:
    if not self.current(self.value, self.owned_identity):
      raise OSError('Bluetooth preference changed')

  def rollback(self) -> bool:
    if not self.current(self.value, self.owned_identity):
      return False
    if self.previous is None:
      self.target.unlink()
      self._sync()
    else:
      self._write(self.previous, self.value, self.owned_identity)
    return True
