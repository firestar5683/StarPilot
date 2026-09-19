#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
route="${1:?Provide a private cached route name}"
[[ "$route" =~ ^[0-9a-f]{8}--[0-9a-f]{10}$ ]] || { echo 'Expected a native cached route name'; exit 2; }
start="${2:-110}"
duration="${3:-100}"
[[ "$start" =~ ^[0-9]+([.][0-9]+)?$ && "$duration" =~ ^[0-9]+([.][0-9]+)?$ ]] || { echo 'Start and duration must be positive numbers'; exit 2; }
# No downloads, dependency installation, external services or public-tree edits.
rsync -a prototype/ comma@192.168.3.111:/data/roadscore/prototype/
display=0
[[ "${ROADSCORE_DISPLAY:-0}" == "1" ]] && display=1
ssh comma@192.168.3.111 "ROADSCORE_DISPLAY=$display /usr/local/venv/bin/python -u /data/roadscore/prototype/supervisor.py $route $start $duration"
mkdir -p results/latest
rsync -a comma@192.168.3.111:/data/roadscore/results/current/ results/latest/
printf '%s\n' 'Private rendered audio and traces copied to results/latest/. Bench playback was muted.'
