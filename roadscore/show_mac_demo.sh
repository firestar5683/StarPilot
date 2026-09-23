#!/usr/bin/env bash
set -euo pipefail
project="$(cd "$(dirname "$0")/.." && pwd)"
archive="${ROADSCORE_DEMO_ARCHIVE:-$HOME/Desktop/RoadScore/demos/showcase-rehearsal/gold-route5}"
python="${project}/.host_runtime/darwin/venv/bin/python"
exec "$python" "$project/roadscore/prototype/mac_showcase.py" route5 \
  --score-archive "$archive" --unpaired --fullscreen --port 56976 "$@"
