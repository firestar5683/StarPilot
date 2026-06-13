#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ ! -f .venv/bin/activate ]]; then
  echo "Missing .venv. Run tools/install_python_dependencies.sh first."
  exit 1
fi

default_jobs() {
  if command -v nproc >/dev/null 2>&1; then
    nproc
  elif command -v sysctl >/dev/null 2>&1; then
    sysctl -n hw.ncpu
  else
    echo 8
  fi
}

env_var_truthy() {
  [[ "${1:-}" =~ ^(1|true|yes|on)$ ]]
}

usage() {
  cat <<'EOF'
Usage:
  ./onroad [jobs] (--c3 | --c4 | --raybig | --all | --replay-only) [-nav] [--prefix name] <route-or-replay-args...>

Examples:
  ./onroad --c3 <route>
  ./onroad --c4 <route> --start 30
  ./onroad --c4 -nav <route>
  ./onroad --all <route>
  ./onroad --replay-only --demo --no-vipc --no-loop

Notes:
  - This is host/dev only. It uses the isolated host worktree and does not touch the device path.
  - A private comma connect route still requires tools/lib/auth.py before replay can download it.
  - Use multiple UI flags together if you want more than one desktop UI at once.
  - -nav injects a fake navigation demo stream and blocks replay from publishing navInstruction/navRoute.
EOF
}

jobs="$(default_jobs)"
if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
  jobs="$1"
  shift || true
fi

PREFIX_ARG=""
REPLAY_ARGS=()
UI_TARGETS=()
LEGACY_UI_SELECTION=""
REPLAY_ONLY=0
NAV_DEMO=0
REPLAY_PID=""
NAV_PID=""
UI_PIDS=()

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)
        usage
        exit 0
        ;;
      --c3)
        UI_TARGETS+=(c3)
        shift
        ;;
      --c4)
        UI_TARGETS+=(c4)
        shift
        ;;
      --raybig)
        UI_TARGETS+=(raybig)
        shift
        ;;
      --all)
        UI_TARGETS+=(c3 c4 raybig)
        shift
        ;;
      --replay-only)
        REPLAY_ONLY=1
        shift
        ;;
      -nav|--nav)
        NAV_DEMO=1
        shift
        ;;
      --ui)
        if [[ $# -lt 2 ]]; then
          echo "Missing value for --ui" >&2
          exit 1
        fi
        LEGACY_UI_SELECTION="$2"
        shift 2
        ;;
      --ui=*)
        LEGACY_UI_SELECTION="${1#*=}"
        shift
        ;;
      -p|--prefix)
        if [[ $# -lt 2 ]]; then
          echo "Missing value for $1" >&2
          exit 1
        fi
        PREFIX_ARG="$2"
        shift 2
        ;;
      --prefix=*)
        PREFIX_ARG="${1#*=}"
        shift
        ;;
      --)
        shift
        REPLAY_ARGS+=("$@")
        break
        ;;
      *)
        REPLAY_ARGS+=("$1")
        shift
        ;;
    esac
  done
}

expand_ui_targets() {
  local selection="${1// /}"

  case "${selection,,}" in
    all|"")
      UI_TARGETS=(c3 c4 raybig)
      return
      ;;
    none)
      UI_TARGETS=()
      return
      ;;
  esac

  local raw_targets=()
  IFS=',' read -r -a raw_targets <<< "${selection}"

  local normalized=()
  local raw=""
  for raw in "${raw_targets[@]}"; do
    case "${raw,,}" in
      c3|c4|raybig)
        normalized+=("${raw,,}")
        ;;
      *)
        echo "Unknown UI target in --ui: ${raw}" >&2
        echo "Valid values: all, none, c3, c4, raybig" >&2
        exit 1
        ;;
    esac
  done

  local ordered_targets=(c3 c4 raybig)
  local target=""
  for target in "${ordered_targets[@]}"; do
    local candidate=""
    for candidate in "${normalized[@]}"; do
      if [[ "${candidate}" == "${target}" ]]; then
        UI_TARGETS+=("${target}")
        break
      fi
    done
  done
}

dedupe_ui_targets() {
  local ordered_targets=(c3 c4 raybig)
  local deduped=()
  local target=""
  for target in "${ordered_targets[@]}"; do
    local candidate=""
    for candidate in "${UI_TARGETS[@]-}"; do
      if [[ "${candidate}" == "${target}" ]]; then
        deduped+=("${target}")
        break
      fi
    done
  done
  UI_TARGETS=("${deduped[@]-}")
}

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM

  local pid=""
  for pid in "${UI_PIDS[@]-}"; do
    if [[ -n "${pid}" ]]; then
      kill "${pid}" >/dev/null 2>&1 || true
    fi
  done
  if [[ -n "${REPLAY_PID}" ]]; then
    kill "${REPLAY_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${NAV_PID}" ]]; then
    kill "${NAV_PID}" >/dev/null 2>&1 || true
  fi

  for pid in "${UI_PIDS[@]-}"; do
    if [[ -n "${pid}" ]]; then
      wait "${pid}" >/dev/null 2>&1 || true
    fi
  done
  if [[ -n "${REPLAY_PID}" ]]; then
    wait "${REPLAY_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${NAV_PID}" ]]; then
    wait "${NAV_PID}" >/dev/null 2>&1 || true
  fi

  if [[ -n "${OPENPILOT_PREFIX:-}" && "${OPENPILOT_PREFIX}" == desktop-onroad-* ]]; then
    echo "Cleaning up temporary prefix environment (${OPENPILOT_PREFIX})..."
    rm -rf "/dev/shm/msgq_${OPENPILOT_PREFIX}"
    rm -rf "/tmp/comma_download_cache${OPENPILOT_PREFIX}"
    rm -rf "${HOME}/.comma${OPENPILOT_PREFIX}"
  fi

  exit "${exit_code}"
}

append_blocked_service_names() {
  local existing="$1"
  local required="$2"
  local combined="${existing}"

  if [[ -n "${combined}" ]]; then
    combined+=",${required}"
  else
    combined="${required}"
  fi

  local deduped=()
  local seen=","
  local part=""
  local parts=()
  IFS=',' read -r -a parts <<< "${combined}"
  for part in "${parts[@]-}"; do
    part="${part// /}"
    if [[ -z "${part}" ]]; then
      continue
    fi
    if [[ "${seen}" != *",${part},"* ]]; then
      deduped+=("${part}")
      seen+="${part},"
    fi
  done

  local joined=""
  for part in "${deduped[@]-}"; do
    if [[ -n "${joined}" ]]; then
      joined+=","
    fi
    joined+="${part}"
  done

  printf '%s' "${joined}"
}

ensure_nav_demo_replay_blocklist() {
  local nav_services="navInstruction,navRoute"
  local idx=0

  for ((idx=0; idx<${#REPLAY_ARGS[@]}; idx++)); do
    case "${REPLAY_ARGS[$idx]}" in
      -b|--block)
        if (( idx + 1 >= ${#REPLAY_ARGS[@]} )); then
          echo "Missing value for ${REPLAY_ARGS[$idx]}" >&2
          exit 1
        fi
        REPLAY_ARGS[$((idx + 1))]="$(append_blocked_service_names "${REPLAY_ARGS[$((idx + 1))]}" "${nav_services}")"
        return
        ;;
      --block=*)
        REPLAY_ARGS[$idx]="--block=$(append_blocked_service_names "${REPLAY_ARGS[$idx]#*=}" "${nav_services}")"
        return
        ;;
    esac
  done

  REPLAY_ARGS=(-b "${nav_services}" "${REPLAY_ARGS[@]}")
}

prepare_env() {
  source .venv/bin/activate

  if [[ -d /opt/homebrew/bin ]]; then
    export PATH="/opt/homebrew/bin:${PATH}"
  fi

  export PATH="${ROOT_DIR}/.venv/bin:${PATH}"
  export PYTHONPATH="${ROOT_DIR}:${ROOT_DIR}/starpilot/third_party"
  local repo_dir=""
  for repo_dir in "${ROOT_DIR}"/*_repo; do
    [[ -d "${repo_dir}" ]] && export PYTHONPATH="${PYTHONPATH}:${repo_dir}"
  done
  [[ -d "${ROOT_DIR}/third_party/acados" ]] && export PYTHONPATH="${PYTHONPATH}:${ROOT_DIR}/third_party/acados"

  export BASEDIR="${ROOT_DIR}"
  export NOBOARD=1
  export SIMULATION=1
  export SKIP_FW_QUERY=1
  export USE_WEBCAM=1
  export SP_C3_FAKE_WIFI=0
  export SP_C4_FAKE_WIFI=0
  export SP_RAYBIG_FAKE_WIFI=0
  export SP_ALLOW_DESKTOP_FAKE_WIFI=0
  export SP_ONROAD_NAV_DEMO="${NAV_DEMO}"

  if [[ "$(uname -s)" == "Darwin" ]] || env_var_truthy "${ZMQ:-0}"; then
    export OPENPILOT_ZMQ_NAMESPACE="${PREFIX_ARG:-${OPENPILOT_ZMQ_NAMESPACE:-desktop-onroad-$$}}"
    unset OPENPILOT_PREFIX
  else
    export OPENPILOT_PREFIX="${PREFIX_ARG:-${OPENPILOT_PREFIX:-desktop-onroad-$$}}"
    mkdir -p "/dev/shm/msgq_${OPENPILOT_PREFIX}"
  fi
}

seed_params() {
  "${ROOT_DIR}/.venv/bin/python3" - <<'PY'
import os

from openpilot.common.params import Params
from openpilot.system.version import terms_version, training_version

params = Params()
params.put("HasAcceptedTerms", terms_version)
params.put("CompletedTrainingVersion", training_version)
params.put_bool("OpenpilotEnabledToggle", True)
params.put_bool("IsDriverViewEnabled", False)
params.put_bool("ForceOnroad", False)
params.put_bool("ForceOffroad", False)
if os.getenv("SP_ONROAD_NAV_DEMO", "").lower() in {"1", "true", "yes", "on"}:
  params.put_bool("NavigationUI", True)
PY
}

seed_starpilot_theme() {
  "${ROOT_DIR}/.venv/bin/python3" - <<'PY'
from openpilot.starpilot.common.starpilot_functions import seed_desktop_theme_assets

seed_desktop_theme_assets()
PY
}

build_replay() {
  SP_DISABLE_AUTO_DEVICE_SCONS=1 "${ROOT_DIR}/.venv/bin/scons" --extras -j"${jobs}" tools/replay/replay
}

prepare_c3_runtime() {
  SP_C3_COMPILE_ONLY=1 "${ROOT_DIR}/scripts/launch_ui_desktop.sh" "${jobs}"
}

prepare_python_ui_runtime() {
  SP_KEEP_DESKTOP_RUNTIME_ARTIFACTS=1 SP_C4_COMPILE_ONLY=1 "${ROOT_DIR}/scripts/launch_ui_c4_desktop.sh" "${jobs}"
}

launch_replay() {
  local replay_cmd=(
    "${ROOT_DIR}/tools/replay/replay"
    --headless
    --dcam
    --ecam
  )
  replay_cmd+=("${REPLAY_ARGS[@]}")

  "${replay_cmd[@]}" &
  REPLAY_PID=$!

  sleep 1
  if ! kill -0 "${REPLAY_PID}" >/dev/null 2>&1; then
    wait "${REPLAY_PID}"
    return 1
  fi
}

launch_nav_demo() {
  echo "Starting fake nav demo publisher..."
  "${ROOT_DIR}/.venv/bin/python3" "${ROOT_DIR}/tools/replay/fake_nav_demo.py" &
  NAV_PID=$!

  sleep 0.5
  if ! kill -0 "${NAV_PID}" >/dev/null 2>&1; then
    wait "${NAV_PID}"
    return 1
  fi
}

launch_c3_ui() {
  local os_ext="linux"
  if [[ "$(uname -s)" == "Darwin" ]]; then
    os_ext="macos"
  fi

  local host_ui="${ROOT_DIR}/selfdrive/ui/ui.${os_ext}"
  if [[ ! -x "${host_ui}" ]]; then
    echo "Missing ${host_ui}. C3 build did not produce the desktop binary." >&2
    return 1
  fi

  "${host_ui}" &
  UI_PIDS+=("$!")
}

launch_python_ui() {
  local big="$1"
  (
    export BIG="${big}"
    exec "${ROOT_DIR}/.venv/bin/python3" "${ROOT_DIR}/selfdrive/ui/ui.py"
  ) &
  UI_PIDS+=("$!")
}

launch_control_bar() {
  local watch_pids="${UI_PIDS[*]}"
  (
    export REPLAY_WATCH_PIDS="${watch_pids}"
    exec "${ROOT_DIR}/.venv/bin/python3" "${ROOT_DIR}/tools/replay/control_bar.py"
  ) &
  UI_PIDS+=("$!")
}

parse_args "$@"

if [[ -n "${LEGACY_UI_SELECTION}" ]]; then
  expand_ui_targets "${LEGACY_UI_SELECTION}"
fi

if [[ "${REPLAY_ONLY}" == "1" ]]; then
  UI_TARGETS=()
else
  dedupe_ui_targets
fi

if [[ "${NAV_DEMO}" == "1" ]]; then
  ensure_nav_demo_replay_blocklist
fi

if [[ ${#REPLAY_ARGS[@]} -eq 0 ]]; then
  usage >&2
  exit 1
fi

if [[ "${REPLAY_ONLY}" != "1" && ${#UI_TARGETS[@]} -eq 0 ]]; then
  echo "Select at least one UI with --c3, --c4, --raybig, or use --replay-only." >&2
  exit 1
fi

prepare_env
trap cleanup EXIT INT TERM

echo "Using OPENPILOT_PREFIX=${OPENPILOT_PREFIX:-<default>}"
if [[ -n "${OPENPILOT_ZMQ_NAMESPACE:-}" ]]; then
  echo "Using OPENPILOT_ZMQ_NAMESPACE=${OPENPILOT_ZMQ_NAMESPACE}"
fi
echo "Preparing replay and desktop UI runtime..."

build_replay

case " ${UI_TARGETS[*]-} " in
  *" c3 "*)
    prepare_c3_runtime
    ;;
esac

case " ${UI_TARGETS[*]-} " in
  *" c4 "*|*" raybig "*)
    prepare_python_ui_runtime
    ;;
esac

seed_params
seed_starpilot_theme

echo "Starting replay: ${REPLAY_ARGS[*]}"
launch_replay

if [[ "${NAV_DEMO}" == "1" ]]; then
  launch_nav_demo
fi

if [[ ${#UI_TARGETS[@]} -eq 0 ]]; then
  echo "Replay is running without UI windows. Press Ctrl-C to stop."
  wait "${REPLAY_PID}"
  exit 0
fi

echo "Launching UIs: ${UI_TARGETS[*]}"

local_target=""
has_raylib=0
for local_target in "${UI_TARGETS[@]}"; do
  case "${local_target}" in
    c3)
      launch_c3_ui
      ;;
    c4)
      launch_python_ui 0
      has_raylib=1
      ;;
    raybig)
      launch_python_ui 1
      has_raylib=1
      ;;
  esac
done

if [[ "${has_raylib}" == "1" ]]; then
  echo "Launching standalone replay controls bar..."
  launch_control_bar
fi

wait "${UI_PIDS[@]}"
