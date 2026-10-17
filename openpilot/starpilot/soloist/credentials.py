"""Write-only storage for the user's Soloist API key. Nothing here ever returns the key to Galaxy."""
from __future__ import annotations

import os
import re

from openpilot.starpilot.soloist.paths import Layout, private_dir

# Spotify does not document the key format; accept a printable token and keep shell/argv-hostile bytes out.
KEY = re.compile(r'[A-Za-z0-9._~+/=-]{16,256}')


class InvalidKey(ValueError):
  pass


def normalized(value: object) -> str:
  if not isinstance(value, str):
    raise InvalidKey('Paste the API key from your Spotify Soloist dashboard')
  key = value.strip()
  if not KEY.fullmatch(key):
    raise InvalidKey('That doesn’t look like a Soloist API key. Copy the whole key from the Spotify dashboard and paste it again.')
  return key


def store(value: object, layout: Layout | None = None) -> None:
  layout = layout or Layout.default()
  key = normalized(value)
  private_dir(layout.api_key.parent)
  temporary = layout.api_key.with_name('.api_key.tmp')
  temporary.unlink(missing_ok=True)
  fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
  with os.fdopen(fd, 'w') as out:
    out.write(key)
    out.flush()
    os.fsync(out.fileno())
  os.replace(temporary, layout.api_key)


def load(layout: Layout | None = None) -> str | None:
  try:
    key = (layout or Layout.default()).api_key.read_text().strip()
  except OSError:
    return None
  return key if KEY.fullmatch(key) else None


def present(layout: Layout | None = None) -> bool:
  return load(layout) is not None


def remove(layout: Layout | None = None) -> None:
  (layout or Layout.default()).api_key.unlink(missing_ok=True)
