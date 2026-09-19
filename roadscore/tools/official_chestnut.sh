#!/usr/bin/env bash
# Representative official YOLO example on the selected event unit, physically silent.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd -P)"
repo="$root/external/comma_hack_7"
cd /data/openpilot
env -u OPENPILOT_PREFIX -u PARAMS_ROOT /usr/local/venv/bin/python -c 'from openpilot.common.params import Params; assert not Params().get_bool("IsOnroad")'
mkdir -p "$root/generated" "$root/results/event_night_one"
exec 9>"$root/generated/gpu.lock"
flock -n 9 || { echo 'Chestnut is owned by another task'; exit 1; }
[ -x "$repo/.venv/bin/python" ] && [ -f "$repo/models/yolo26n.onnx" ] || { echo 'Finish official setup and stage YOLO26n first'; exit 1; }
out="$root/results/event_night_one/official_$(date +%s)"
mkdir "$out"
cd "$repo"
git rev-parse HEAD > "$out/revision.txt"
timeout 180 env DEV=USB+AMD:LLVM .venv/bin/python tools/usb.py > "$out/usb.log" 2>&1
timeout 300 env DEV=USB+AMD:LLVM .venv/bin/python examples/02_vision.py zidane.jpg --output "$out/boxes.jpg" > "$out/example.log" 2>&1
printf '%s\n' "$out"
