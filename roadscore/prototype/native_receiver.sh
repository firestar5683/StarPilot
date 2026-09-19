#!/usr/bin/env bash
set -euo pipefail
cd /data/openpilot
env -u OPENPILOT_PREFIX -u PARAMS_ROOT /usr/local/venv/bin/python -c 'from openpilot.common.params import Params; assert not Params().get_bool("IsOnroad")'
cd /data/roadscore
/usr/local/venv/bin/python prototype/persistent_assets.py
exec 9>generated/native_session.lock
flock -n 9 || { echo "Another native RoadScore session owns this bench"; exit 1; }
power_pid=""
audio_pid=""
bridge_pid=""
cleanup() {
  if [ -n "$bridge_pid" ]; then kill "$bridge_pid" 2>/dev/null || true; wait "$bridge_pid" 2>/dev/null || true; fi
  if [ -n "$audio_pid" ]; then kill "$audio_pid" 2>/dev/null || true; wait "$audio_pid" 2>/dev/null || true; fi
  if [ -n "$power_pid" ]; then kill "$power_pid" 2>/dev/null || true; wait "$power_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM
# A worker started here belongs to this run. Reused workers belong to their original supervisor.
worker_script="$(/usr/local/venv/bin/python prototype/composer_choice.py check)"
export ROADSCORE_WORKER="$worker_script"
preparation_wait=360
if [ "${ROADSCORE_COMPOSER:-ace}" = ace ]; then preparation_wait=1500; fi
if ! pgrep -f "^/data/sa3-feasibility/venv/bin/python -u ${worker_script}$" >/dev/null; then
  rm -f generated/worker_ready
  env -u OPENPILOT_PREFIX /usr/local/venv/bin/python -u prototype/power_worker.py > results/native_worker.log 2>&1 < /dev/null &
  power_pid=$!
fi
for attempt in $(seq 1 "$preparation_wait"); do
  [ -f generated/worker_ready ] && break
  if [ -n "$power_pid" ]; then kill -0 "$power_pid" 2>/dev/null || { cat results/native_worker.log; exit 1; }; fi
  if [ -z "$power_pid" ] && ! pgrep -f "^/data/sa3-feasibility/venv/bin/python -u ${worker_script}$" >/dev/null; then echo 'Resident composer exited during preparation; inspect its owned service log'; exit 1; fi
  sleep 1
done
[ -f generated/worker_ready ] || { echo 'Worker preparation timed out'; exit 1; }
if [ "${ROADSCORE_COMPOSER:-ace}" = ace ]; then /usr/local/venv/bin/python prototype/prepared_session.py; fi
export OPENPILOT_PREFIX=roadscore_native
export PYTHONPATH=/data/openpilot:/data/roadscore/prototype:/data/roadscore-feasibility/venv/lib/python3.12/site-packages
mkdir -p /dev/shm/msgq_roadscore_native
if [ -d results/current ]; then mv results/current "results/native_previous_$(date +%s)"; fi
mkdir -p results/current
/usr/local/venv/bin/python prototype/runtime_manifest.py
audio_args=()
if [ "${ROADSCORE_AUDIBLE:-0}" = 1 ]; then audio_args+=(--audible); fi
/usr/local/venv/bin/python -u prototype/app.py "${audio_args[@]}" > results/current/app.log 2>&1 < /dev/null &
audio_pid=$!
for attempt in $(seq 1 30); do
  [ -f results/current/ready ] && break
  kill -0 "$audio_pid" 2>/dev/null || { cat results/current/app.log; exit 1; }
  sleep 1
done
[ -f results/current/ready ] || { cat results/current/app.log; exit 1; }
# Supervise score failures during delivery rather than leaving silent replay running.
exec 8<&0
/usr/local/venv/bin/python -u prototype/replay_bridge.py receive --route "$1" <&8 8<&- &
bridge_pid=$!
exec 8<&-
while kill -0 "$bridge_pid" 2>/dev/null; do
  if [ -n "$audio_pid" ] && ! kill -0 "$audio_pid" 2>/dev/null; then
    if wait "$audio_pid"; then
      audio_pid=""
    else
      echo 'RoadScore audio process failed during replay; preserving its log'
      cat results/current/app.log
      exit 1
    fi
  fi
  sleep .2
done
bridge_status=0
wait "$bridge_pid" || bridge_status=$?
bridge_pid=""
for attempt in $(seq 1 8); do
  kill -0 "$audio_pid" 2>/dev/null || break
  sleep 1
done

exit "$bridge_status"
