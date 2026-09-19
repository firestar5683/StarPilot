#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export ROADSCORE_DISPLAY=1
exec ./run_roadscore_demo.sh "$@"
