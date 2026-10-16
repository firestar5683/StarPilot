"""Persistent, on-device permission for phone diagnostics."""
from pathlib import Path

ENABLED = Path("/data/galaxy-ble/diagnostics-enabled")


def diagnostics_enabled():
  return ENABLED.is_file()


def set_diagnostics_enabled(enabled, *, offroad):
  if not offroad:
    return False
  if enabled:
    ENABLED.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    ENABLED.touch(mode=0o600, exist_ok=True)
  else:
    ENABLED.unlink(missing_ok=True)
  return True
