#!/usr/bin/env bash
# StarPilot live MetaDrive simulator launcher.
#
# Runs the ENTIRE openpilot stack (manager.py -> modeld/controlsd/plannerd/...) on
# the host RTX GPU, bridged to a straight-road MetaDrive world, in one of three
# longitudinal modes.
#
# Usage:
#   ./tools/sim/starpilot_sim.sh {exp|chill|cem|hem} [--headless] [--joystick] [--cpu]
#
#   exp   : standard Experimental mode      (ConditionalExperimental=off, ConditionalChill=off, HybridExperimental=off)
#   chill : pure Chill / CCM mode           (ConditionalChill=on)
#   cem   : Conditional Experimental mode   (ConditionalExperimental=on)
#   hem   : Hybrid Experimental mode        (HybridExperimental=on)
#
# The model runs on the RTX GPU (tinygrad CUDA) by default. Pass --cpu to force
# the CPU backend instead (fragile in this fork; not recommended).
#
# By default the model is traced LIVE from driving_supercombo.onnx inside modeld
# (Option 1: no tinygrad-JIT pickling, so no JIT-unpickle corruption). Pass --pkl
# to fall back to the precompiled pickle artifact instead.
#
# The stack runs from the isolated host worktree (.host_runtime/linux/worktree),
# which is synced from this repo by `./dev sync` (run automatically below).
set -euo pipefail

# Clean up any stale openpilot/sim processes and shared-memory sockets from a
# previous run. pkill on "manager.py" alone misses the the_galaxy/galaxy Flask
# processes (different proctitles) which otherwise hold port 8083 and crash-loop,
# and stale msgq sockets in /dev/shm collide with fresh publishers.
pkill -9 -f "system/manager/manager.py" 2>/dev/null || true
pkill -9 -f "run_bridge.py" 2>/dev/null || true
pkill -9 -f "metadrive" 2>/dev/null || true
pkill -9 -f "the_galaxy" 2>/dev/null || true
pkill -9 -f "galaxy.galaxy" 2>/dev/null || true
sleep 1
rm -rf /dev/shm/msgq* /dev/shm/visionipc* /tmp/openpilot* 2>/dev/null || true

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

MODE="${1:-hem}"
ARGS=("${@:2}")
HEADLESS=0
JOYSTICK=0
SIM_DEV="CUDA"
LIVE_ONNX=1
for a in "${ARGS[@]}"; do
  case "$a" in
    --headless) HEADLESS=1 ;;
    --joystick) JOYSTICK=1 ;;
    --cpu) SIM_DEV="CPU" ;;
    --pkl) LIVE_ONNX=0 ;;
    *) echo "unknown arg: $a" >&2; exit 1 ;;
  esac
done

case "$MODE" in
  exp|chill|cem|hem) : ;;
  *) echo "usage: $0 {exp|chill|cem|hem} [--headless] [--joystick] [--cpu]" >&2; exit 1 ;;
esac

# 1. Sync main repo -> host worktree so our sim/mode changes land there.
"${ROOT_DIR}/dev" sync shared >/dev/null 2>&1 || true

HOST_WORKTREE="${ROOT_DIR}/.host_runtime/linux/worktree"
HOST_PY="${HOST_WORKTREE}/.venv/bin/python3"
MODEL_STORE="${HOME}/.comma/starpilot/data/models"

echo "==> StarPilot sim mode: ${MODE}  (model device: ${SIM_DEV})  (host worktree: ${HOST_WORKTREE})"

# 2. Make sure the builtin model is present where modeld loads it. Sync wipes the
#    worktree copy, so re-copy it from the model store on every launch. With the
#    live-ONNX path (default) modeld ignores the pkl and traces the ONNX instead,
#    but keep the pkl in place so --pkl still works.
MODEL_SRC="${MODEL_STORE}/rdf43_driving_tinygrad.pkl"
MODEL_DST="${HOST_WORKTREE}/selfdrive/modeld/models/driving_tinygrad.pkl"
if [[ -f "${MODEL_SRC}" ]]; then
  if ! cmp -s "${MODEL_SRC}" "${MODEL_DST}"; then
    cp -f "${MODEL_SRC}" "${MODEL_DST}"
    echo "==> Copied builtin model to ${MODEL_DST}"
  fi
else
  echo "!! builtin model not found at ${MODEL_SRC}" >&2
fi

# Option 1 (live-ONNX): modeld traces driving_supercombo.onnx in-memory on the
# RTX, so the tinygrad-JIT pickle round-trip (and its QCOM-rewrite bug) never
# happens. Falls back to the pkl artifact when --pkl is passed or the onnx is
# missing.
# Locate the source ONNX: prefer the model store copy, fall back to the repo root.
ONNX_SRC="${MODEL_STORE}/driving_supercombo.onnx"
if [[ ! -f "${ONNX_SRC}" ]] && [[ -f "${ROOT_DIR}/driving_supercombo.onnx" ]]; then
  ONNX_SRC="${ROOT_DIR}/driving_supercombo.onnx"
fi
if [[ "$LIVE_ONNX" == "1" ]]; then
  if [[ -f "${ONNX_SRC}" ]]; then
    export STARPIOT_LIVE_ONNX="${ONNX_SRC}"
    echo "==> modeld will trace ${ONNX_SRC} live on ${SIM_DEV}"
  else
    echo "!! driving_supercombo.onnx NOT found (checked model store and repo root)." >&2
    echo "   Falling back to the precompiled pkl, which CRASHES with CUDA_ERROR_INVALID_IMAGE." >&2
    echo "   Place the onnx at ${MODEL_STORE}/driving_supercombo.onnx and re-run." >&2
  fi
fi

# 3. Set the longitudinal mode params (mutually exclusive).
# ForceOnroad: on a PC host there is no real panda/ignition, so hardwared never
# transitions the device onroad by itself; force it so modeld/controlsd/plannerd
# come up and the sim can engage and drive.
"${HOST_PY}" - "${MODE}" <<'PY'
import sys
from openpilot.common.params import Params
p = Params()
mode = sys.argv[1]
p.put_bool_nonblocking("ConditionalExperimental", mode == "cem")
p.put_bool_nonblocking("ConditionalChill", mode == "chill")
p.put_bool_nonblocking("HybridExperimental", mode == "hem")
p.put_bool_nonblocking("ForceOnroad", True)
print(f"params: ConditionalExperimental={p.get_bool('ConditionalExperimental')} "
      f"ConditionalChill={p.get_bool('ConditionalChill')} "
      f"HybridExperimental={p.get_bool('HybridExperimental')} "
      f"ForceOnroad={p.get_bool('ForceOnroad')}")
PY

# 4. Sim environment (mirrors tools/sim/launch_openpilot.sh) + GPU selection.
export PASSIVE="0"
export NOBOARD="1"
export SIMULATION="1"
export SKIP_FW_QUERY="1"
export FINGERPRINT="HONDA_CIVIC_2022"
export BLOCK="camerad,loggerd,encoderd,micd,logmessaged,soundd,mapd"
if [[ "$HEADLESS" == "1" ]]; then
  export BLOCK="${BLOCK},ui"
fi
export DEV="${SIM_DEV}"
export STARPIOT_SIM_DEV="${SIM_DEV}"
# The supercombo artifact is compiled all-CUDA (warp + policy on the RTX). The
# warp device must be CUDA so the precompiled kernels match; modeld copies the
# host-memory camera frames onto the GPU before the warp.
if [[ "${SIM_DEV}" == "CPU" ]]; then
  export WARP_DEV="CPU"
  export QUEUE_DEV="CPU"
else
  export WARP_DEV="${SIM_DEV}"
  export QUEUE_DEV="${SIM_DEV}"
fi

# 5. Launch the full openpilot stack in the background, then the bridge in the foreground.
cat <<'HELP'
==> Controls (focus the terminal that launched this script):
    i : toggle ignition   (starts ON by default; if the status line shows
                            Ignition: False, press i once to turn it back on)
    2 : cruise Set  (engage lateral + longitudinal)      1 : cruise Resume / accel
    3 : cruise Cancel                                     r : reset simulation
    w/a/s/d : manual throttle / steer / brake             q : quit everything
    z/x : blinker left / right
HELP
cd "${HOST_WORKTREE}"
MANAGER_LOG="${HOST_WORKTREE}/.host_sim_manager.log"
"${HOST_PY}" -c "from openpilot.selfdrive.test.helpers import set_params_enabled; set_params_enabled()"
echo "==> Starting openpilot stack (manager.py) ..."
"${HOST_PY}" system/manager/manager.py >"${MANAGER_LOG}" 2>&1 &
MANAGER_PID=$!
echo "==> manager.py pid ${MANAGER_PID} (log: ${MANAGER_LOG})"
trap 'echo "==> stopping manager (${MANAGER_PID})"; kill "${MANAGER_PID}" 2>/dev/null || true' EXIT

# modeld blocks on the camerad visionipc stream before it starts tracing the
# ONNX, and that stream is published by the bridge. The bridge MUST come up
# promptly or modeld never loads, so keep the startup delay short and let the
# bridge auto-engage once controls report engageable.
sleep 8

# Single-camera mode: MetaDrive must render only the road viewport. Dual-camera
# renders a second wide viewpoint every frame, roughly halving frame rate. The
# driving pipeline (modeld) consumes roadCameraState only, so the wide cam adds
# no control value in sim.
BRIDGE_ARGS=()
if [[ "$JOYSTICK" == "1" ]]; then
  BRIDGE_ARGS+=(--joystick)
fi
echo "==> Starting MetaDrive bridge (${BRIDGE_ARGS[*]}) ..."
"${HOST_PY}" tools/sim/run_bridge.py "${BRIDGE_ARGS[@]}" || true
echo "==> Bridge exited."
