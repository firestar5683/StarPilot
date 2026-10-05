#!/usr/bin/env python3
"""Check tracked dependency folders, locally or at a fetched revision."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from openpilot.common.vendor_manifest import dependency_entries, validate_revision, validate_worktree


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--revision", help="Validate a committed revision instead of the working tree")
  args = parser.parse_args()
  try:
    manifest = validate_revision(ROOT, args.revision) if args.revision else validate_worktree(ROOT)
  except (ValueError, OSError, subprocess.CalledProcessError) as e:
    print(f"Source validation failed: {e}", file=sys.stderr)
    return 1
  print(f"Source layout valid: {len(dependency_entries(manifest))} tracked dependency folders")
  return 0


if __name__ == "__main__":
  sys.exit(main())
