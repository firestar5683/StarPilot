#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
cd "$DIR"

if [ -n "${STARPILOT_CI_BUILD_MANIFEST:-}" ]; then
  python3 "$DIR/build_manifest.py" --manifest "$STARPILOT_CI_BUILD_MANIFEST"
  exit 0
fi

if [ ! -z "$(git status --porcelain)" ]; then
  echo "Dirty working tree after build:"
  git status --porcelain
  exit 1
fi
