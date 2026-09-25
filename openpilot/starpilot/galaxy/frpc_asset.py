"""Verified, offline FRPC executable for Galaxy's Linux ARM64 device."""

import hashlib
import platform
from pathlib import Path
import stat


FRPC_VERSION = "0.67.0"
FRPC_RELEASE_URL = "https://github.com/fatedier/frp/releases/download/v0.67.0/frp_0.67.0_linux_arm64.tar.gz"
FRPC_RELEASE_SHA256 = "0e9683226acdcbbb2ac8d073f35ba8be2a8b1e7584684d2073f39d337ebd6de7"
FRPC_BINARY_SHA256 = "3cac9073e39f5c3044b291dcb9f96b4d4af4788db95ad763872dde4eb0a2f25b"
FRPC_BINARY = Path(__file__).resolve().parent / "bin" / "frpc_linux_arm64"


def bundled_frpc_path() -> str | None:
  """Return the bundled executable only on its target platform with its pinned digest."""
  if platform.system() != "Linux" or platform.machine().lower() not in ("aarch64", "arm64"):
    return None
  try:
    info = FRPC_BINARY.lstat()
    if not stat.S_ISREG(info.st_mode) or not info.st_mode & 0o111:
      return None
    digest = hashlib.sha256()
    with FRPC_BINARY.open("rb") as stream:
      for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
    return str(FRPC_BINARY) if digest.hexdigest() == FRPC_BINARY_SHA256 else None
  except OSError:
    return None
