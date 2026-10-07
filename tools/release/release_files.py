#!/usr/bin/env python3
import os
import re
import subprocess
import sys

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))

blacklist = [
  ".git/",
  ".venv/",
  r"^\.github/workflows/",

  "matlab.*.md",

  # Obsolete checkout metadata is never packaged
  ".lfsconfig",
  ".git$",
  ".gitmodules",
]

# Dependency sources are ordinary tracked files. A gitlink cannot be packaged
# without a separate checkout, so fail rather than silently omitting its source.
def release_files(root: str, include_big_model: bool = False, *, require_provider: bool = False) -> list[bytes]:
  entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=root).split(b"\0")
  files = []
  modes = {}
  for entry in entries:
    if not entry:
      continue

    metadata, tracked_file = entry.split(b"\t", 1)
    mode, _, stage = metadata.split()
    rf = os.fsdecode(tracked_file)
    if mode == b"160000":
      raise ValueError(f"Cannot package gitlink: {rf}; dependency sources must be tracked files")
    if stage != b"0":
      raise ValueError(f"Cannot package unresolved merge: {rf}")
    if rf == "openpilot/selfdrive/modeld/models/big_driving_tinygrad.pkl":
      continue
    if not include_big_model and rf.startswith("openpilot/selfdrive/modeld/models/big_"):
      continue
    blacklisted = any(re.search(p, rf) for p in blacklist)
    if blacklisted:
      continue

    modes[tracked_file] = mode
    files.append(tracked_file)
  if require_provider or b"openpilot/starpilot/maps/shadow_lifecycle.py" in files:
    for name, mode in ((b"openpilot/starpilot/maps/provider/mapd", b"100755"),
                       (b"openpilot/starpilot/maps/provider/manifest.json", b"100644")):
      if modes.get(name) != mode:
        raise ValueError(f"Mapd Git package missing or invalid mode: {os.fsdecode(name)}; track the verified provider package")
  return files


if __name__ == "__main__":
  for tracked_file in release_files(ROOT, bool(os.getenv("INCLUDE_BIG_MODEL"))):
    sys.stdout.buffer.write(tracked_file + b"\0")
