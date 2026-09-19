#!/usr/bin/env bash
# Run from the checked-out event repo on an offroad comma. No GPU/audio stream.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd -P)"
[ -f /TICI ] || { echo 'Run on the event comma'; exit 1; }
cd /data/openpilot
env -u OPENPILOT_PREFIX -u PARAMS_ROOT /usr/local/venv/bin/python -c 'from openpilot.common.params import Params; assert not Params().get_bool("IsOnroad"), "Requires real offroad state"'
if [ -e /data/roadscore ]; then
  [ "$(readlink -f /data/roadscore)" = "$root" ] || { echo '/data/roadscore already belongs to another checkout'; exit 1; }
else
  ln -s "$root" /data/roadscore
fi
mkdir -p "$root"/{generated,results/event_night_one,routes,assets,.cache/uv,tmp} /data/roadscore-feasibility/{cache,tmp} /data/sa3-feasibility
# AGNOS /home has only a small overlay. Never use it for package downloads.
export UV_CACHE_DIR="$root/.cache/uv" TMPDIR="$root/tmp"
if [ ! -x /data/sa3-feasibility/venv/bin/python ]; then
  uv venv --system-site-packages --python /usr/local/venv/bin/python /data/sa3-feasibility/venv
fi
uv pip install --python /data/sa3-feasibility/venv/bin/python numpy==2.5.3 scipy==1.18.1 soundfile==0.14.0 sounddevice
if [ ! -e /data/roadscore-feasibility/venv ]; then
  ln -s /data/sa3-feasibility/venv /data/roadscore-feasibility/venv
fi
if [ ! -e /data/sa3-feasibility/native_sa3.py ]; then
  ln -s "$root/chestnut_stable_audio/native_sa3.py" /data/sa3-feasibility/native_sa3.py
fi
# This establishes an automated session lock, not a product-wide audio default.
touch "$root/.session-muted"
if [ ! -f "$root/runtime.json" ]; then cp "$root/tools/event_runtime.json" "$root/runtime.json"; fi
/usr/local/venv/bin/python "$root/tools/event_inventory.py" > "$root/results/event_night_one/inventory.json"
/usr/local/venv/bin/python "$root/prototype/build_native_replay.py" > "$root/results/event_night_one/replay_build.log" 2>&1
printf '%s\n' 'Software prepared. Stage trained assets, then run the official Chestnut gate before starting Prism.'
