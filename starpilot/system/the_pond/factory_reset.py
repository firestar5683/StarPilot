import subprocess
import time


_DELETE_TIMEOUT_S = 1800
_DELETE_RETRY_ATTEMPTS = 20
_DELETE_RETRY_DELAY_S = 0.25
_DIRECTORY_NOT_EMPTY_ERROR = "directory not empty"


def remove_path(path):
  # Managed processes can recreate entries under /data/params while rm is finishing.
  for attempt in range(_DELETE_RETRY_ATTEMPTS):
    result = subprocess.run(
      ["sudo", "rm", "-rf", "--", path],
      capture_output=True,
      text=True,
      timeout=_DELETE_TIMEOUT_S,
      check=False,
    )
    if result.returncode == 0:
      return

    error_text = (result.stderr or result.stdout or "sudo rm -rf failed").strip()
    can_retry = _DIRECTORY_NOT_EMPTY_ERROR in error_text.lower()
    if not can_retry or attempt == _DELETE_RETRY_ATTEMPTS - 1:
      raise RuntimeError(f"Failed to remove {path}: {error_text}")

    time.sleep(_DELETE_RETRY_DELAY_S)
