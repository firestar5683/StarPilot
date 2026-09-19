#!/usr/bin/env bash
set -euo pipefail
cd /data/openpilot
export OPENPILOT_PREFIX=roadscore
export PYTHONPATH=/data/openpilot:/data/roadscore/prototype:/data/roadscore-feasibility/venv/lib/python3.12/site-packages
env -u OPENPILOT_PREFIX /usr/local/venv/bin/python -c 'from openpilot.common.params import Params; assert not Params().get_bool("IsOnroad")'
mkdir -p /dev/shm/msgq_roadscore
cd /data/roadscore
if [ -d results/current ]; then mv results/current "results/run_$(date +%Y%m%d_%H%M%S)"; fi
mkdir -p results/current
/usr/local/venv/bin/python -u prototype/app.py > results/current/app.log 2>&1 &
audio_pid=$!
trap 'kill "$audio_pid" 2>/dev/null || true; wait "$audio_pid" 2>/dev/null || true' EXIT
for attempt in $(seq 1 60); do
  [ -f results/current/ready ] && break
  kill -0 "$audio_pid" 2>/dev/null || { cat results/current/app.log; exit 1; }
  sleep 1
done
[ -f results/current/ready ] || { echo 'Audio startup timed out'; exit 1; }
/usr/local/venv/bin/python -u prototype/replay.py --route "${1:?Provide a private cached route name}" --start "${2:-110}" --duration "${3:-100}" > results/current/replay.log 2>&1
wait "$audio_pid"
