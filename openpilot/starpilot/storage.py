"""Writable StarPilot state location, separate from upstream read-only persist."""

import os
from pathlib import Path
import re

from openpilot.common.hardware import PC
from openpilot.common.hardware.hw import Paths


_PREFIX = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_DEVICE_ROOT = Path("/data/starpilot")


def starpilot_storage_root() -> Path:
  """Return the StarPilot-owned state root for this Params/IPC namespace.

  Desktop retains its existing per-user persist path. On devices /persist is
  read-only; a named OPENPILOT_PREFIX gets a separate /data root so a desk
  instance cannot read or replace the normal instance's Galaxy credentials.
  """
  if PC:
    return Path(Paths.persist_root()) / "starpilot"
  prefix = os.environ.get("OPENPILOT_PREFIX", "")
  if not prefix:
    return _DEVICE_ROOT
  if not _PREFIX.fullmatch(prefix):
    raise ValueError("Invalid OPENPILOT_PREFIX for StarPilot storage")
  return _DEVICE_ROOT.with_name(f"{_DEVICE_ROOT.name}-{prefix}")


def galaxy_storage_root() -> Path:
  """Keep the shared history and credential directory private, including older caches."""
  root = starpilot_storage_root() / "galaxy"
  try:
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
      info = os.fstat(fd)
      if info.st_uid == os.geteuid() and not info.st_mode & 0o022 and info.st_mode & 0o077:
        os.fchmod(fd, 0o700)
    finally:
      os.close(fd)
  except OSError:
    # Credential owners still reject inaccessible or unsafe storage.
    pass
  return root
