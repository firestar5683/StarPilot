"""Runtime provisioning for the existing statistics service."""
import os
from pathlib import Path
import stat


TOKEN_FILE = Path('/data/starpilot/analytics/token')


def _token(value):
  if not isinstance(value, str):
    return None
  value = value.strip()
  return value if 16 <= len(value) <= 4096 and all(33 <= ord(c) <= 126 for c in value) else None


def read_token():
  value = os.environ.get('STARPILOT_STATS_TOKEN')
  if value is not None:
    return _token(value)
  path = Path(os.environ.get('STARPILOT_STATS_TOKEN_FILE', str(TOKEN_FILE)))
  descriptor = None
  try:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    info = os.fstat(descriptor)
    if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or
        info.st_uid not in (0, os.getuid()) or not 16 <= info.st_size <= 4097):
      return None
    return _token(os.read(descriptor, 4097).decode('ascii'))
  except (OSError, UnicodeError):
    return None
  finally:
    if descriptor is not None:
      os.close(descriptor)
