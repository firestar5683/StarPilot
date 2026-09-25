"""A device-owned display name, independent of driving preferences and pairing credentials."""

import json
import os
from pathlib import Path
import stat
import tempfile


def validate_name(value: str) -> str:
  if type(value) is not str or len(value) > 40 or any(ord(char) < 32 or 127 <= ord(char) < 160 or 0xD800 <= ord(char) <= 0xDFFF for char in value):
    raise ValueError('Use a name of up to 40 characters without control characters')
  return value.strip()


class DeviceName:
  FILE = 'device-name.json'

  def __init__(self, root: Path):
    self.root = root

  def _directory(self) -> None:
    info = self.root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
      raise OSError('Device name storage is unavailable')

  def read(self) -> str:
    if not self.root.exists():
      return ''
    self._directory()
    try:
      fd = os.open(self.root / self.FILE, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
      return ''
    with os.fdopen(fd, encoding='utf-8') as stream:
      info = os.fstat(stream.fileno())
      if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077 or info.st_size > 512:
        raise OSError('Device name storage is unavailable')
      data = json.load(stream)
    if type(data) is not dict or set(data) != {'version', 'name'} or type(data['version']) is not int or data['version'] != 1:
      raise ValueError('Invalid device name')
    return validate_name(data['name'])

  def save(self, name: str) -> str:
    name = validate_name(name)
    self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
    self._directory()
    fd, temporary = tempfile.mkstemp(prefix='.device-name-', dir=self.root)
    try:
      with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump({'version': 1, 'name': name}, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
      os.replace(temporary, self.root / self.FILE)
      directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
      try:
        os.fsync(directory)
      finally:
        os.close(directory)
    finally:
      if os.path.exists(temporary):
        os.unlink(temporary)
    return self.read()
