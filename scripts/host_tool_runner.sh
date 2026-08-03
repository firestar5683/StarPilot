#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PLATFORM_KEY="$(uname -s | tr '[:upper:]' '[:lower:]')"
HOST_PLATFORM_ROOT="${ROOT_DIR}/.host_runtime/${PLATFORM_KEY}"
HOST_ROOT=""
WORK_DIR=""
HOST_VENV=""
HOST_LOCK_DIR=""
HOST_LOCK_PID_FILE=""
HOST_LOCK_CMD_FILE=""
HOST_LOCK_HELD=0
HOST_BUCKETS=(shared cabana)

usage() {
  cat <<'EOF'
Usage:
  ./dev <command> [args...]
  ./tool <command> [args...]
  ./tools/host <command> [args...]

Commands:
  c3           Launch the desktop Qt UI from the isolated host cache.
  c4           Launch the small raylib UI from the isolated host cache.
  raybig       Launch the large raylib UI from the isolated host cache.
  onroad       Launch replay plus desktop UI(s) from the isolated host cache.
  replay       Build and run replay from the isolated host cache.
  cabana       Build and run cabana from the isolated host cache.
  plotjuggler  Run PlotJuggler helper from the isolated host cache.
  juggle       Alias for plotjuggler.
  python       Run Python from the isolated host cache with repo paths configured.
  pytest       Run pytest from the isolated host cache after building host extensions.
  sync         Refresh the isolated host cache only.
  shell        Open a shell inside the isolated host cache.
  help         Show this help text.

Notes:
  - Host-tool builds happen under ./.host_runtime/ and do not touch the main tree.
  - `cabana` uses its own host-runtime bucket, so it can run together with `plotjuggler`.
  - Other commands that share a bucket still wait on that bucket's lock.
  - `./build` remains the device-target flow.
  - For c3/c4/raybig, pass the jobs count first to preserve existing shorthand:
      ./dev c3 8
      ./dev raybig 12
  - `./onroad --c3 f08912a233c1584f/2022-08-11--18-02-41/1` launches replay plus the selected desktop UI.
  - `./dev sync` refreshes all host buckets. Use `./dev sync cabana` to sync one.
EOF
}

default_jobs() {
  if command -v nproc >/dev/null 2>&1; then
    nproc
  elif command -v sysctl >/dev/null 2>&1; then
    sysctl -n hw.ncpu
  else
    echo 8
  fi
}

resolve_host_bucket() {
  local name="${1:-shared}"

  case "${name}" in
    shared|default|ui|c3|c4|raybig|onroad|replay|shell)
      echo "shared"
      ;;
    cabana)
      echo "cabana"
      ;;
    plotjuggler|juggle)
      echo "shared"
      ;;
    *)
      return 1
      ;;
  esac
}

set_host_bucket() {
  local bucket="$1"

  if [[ "${bucket}" == "shared" ]]; then
    HOST_ROOT="${HOST_PLATFORM_ROOT}"
  else
    HOST_ROOT="${HOST_PLATFORM_ROOT}/${bucket}"
  fi
  WORK_DIR="${HOST_ROOT}/worktree"
  HOST_VENV="${HOST_ROOT}/venv"
  HOST_LOCK_DIR="${HOST_ROOT}/lock"
  HOST_LOCK_PID_FILE="${HOST_LOCK_DIR}/pid"
  HOST_LOCK_CMD_FILE="${HOST_LOCK_DIR}/command"
}

lock_owner_summary() {
  local lock_pid=""
  local lock_cmd="unknown"

  if [[ -f "${HOST_LOCK_PID_FILE}" ]]; then
    lock_pid="$(<"${HOST_LOCK_PID_FILE}")"
  fi
  if [[ -f "${HOST_LOCK_CMD_FILE}" ]]; then
    lock_cmd="$(<"${HOST_LOCK_CMD_FILE}")"
  fi

  if [[ -n "${lock_pid}" ]]; then
    echo "pid ${lock_pid} (${lock_cmd})"
  else
    echo "${lock_cmd}"
  fi
}

lock_is_stale() {
  local lock_pid=""

  if [[ ! -f "${HOST_LOCK_PID_FILE}" ]]; then
    return 1
  fi

  lock_pid="$(<"${HOST_LOCK_PID_FILE}")"
  if [[ ! "${lock_pid}" =~ ^[0-9]+$ ]]; then
    return 0
  fi

  if kill -0 "${lock_pid}" 2>/dev/null; then
    return 1
  fi

  return 0
}

release_host_lock() {
  if [[ "${HOST_LOCK_HELD}" != "1" ]]; then
    return
  fi

  rm -f "${HOST_LOCK_PID_FILE}" "${HOST_LOCK_CMD_FILE}"
  rmdir "${HOST_LOCK_DIR}" 2>/dev/null || rm -rf "${HOST_LOCK_DIR}"
  HOST_LOCK_HELD=0
}

acquire_host_lock() {
  local lock_label="$1"
  local notified=0

  mkdir -p "${HOST_ROOT}"

  while true; do
    if mkdir "${HOST_LOCK_DIR}" 2>/dev/null; then
      printf '%s\n' "$$" > "${HOST_LOCK_PID_FILE}"
      printf '%s\n' "${lock_label}" > "${HOST_LOCK_CMD_FILE}"
      HOST_LOCK_HELD=1
      trap release_host_lock EXIT
      return
    fi

    if lock_is_stale; then
      echo "Removing stale host runtime lock: $(lock_owner_summary)" >&2
      rm -rf "${HOST_LOCK_DIR}"
      continue
    fi

    if [[ "${notified}" == "0" ]]; then
      echo "Waiting for host runtime lock in ${HOST_ROOT}. Another shorthand command is using it: $(lock_owner_summary)." >&2
      notified=1
    fi
    sleep 1
  done
}

ensure_venv() {
  if [[ ! -x "${ROOT_DIR}/.venv/bin/python3" ]]; then
    echo "Missing .venv. Run tools/install_python_dependencies.sh first."
    exit 1
  fi

  if ! command -v uv >/dev/null 2>&1; then
    echo "Missing uv. Run tools/install_python_dependencies.sh first."
    exit 1
  fi
}

sync_selected_bucket() {
  local bucket="$1"

  set_host_bucket "${bucket}"
  acquire_host_lock "sync ${bucket}"
  sync_worktree
  echo "Host tool cache synced (${bucket}): ${WORK_DIR}"
  release_host_lock
}

sync_all_buckets() {
  local bucket=""
  for bucket in "${HOST_BUCKETS[@]}"; do
    sync_selected_bucket "${bucket}"
  done
}

purge_host_python_artifacts() {
  rm -f \
    "${WORK_DIR}/common/params_pyx.so" \
    "${WORK_DIR}/common/params_pyx.o" \
    "${WORK_DIR}/common/params_pyx.cpp" \
    "${WORK_DIR}/common/transformations/transformations.so" \
    "${WORK_DIR}/common/transformations/transformations.o" \
    "${WORK_DIR}/common/transformations/transformations.cpp" \
    "${WORK_DIR}/msgq_repo/msgq/ipc_pyx.so" \
    "${WORK_DIR}/msgq_repo/msgq/ipc_pyx.o" \
    "${WORK_DIR}/msgq_repo/msgq/ipc_pyx.cpp" \
    "${WORK_DIR}/msgq_repo/msgq/visionipc/visionipc_pyx.so" \
    "${WORK_DIR}/msgq_repo/msgq/visionipc/visionipc_pyx.o" \
    "${WORK_DIR}/msgq_repo/msgq/visionipc/visionipc_pyx.cpp"
}

purge_host_foreign_platform_artifacts() {
  rm -rf "${WORK_DIR}/.host_runtime"
  rm -rf "${WORK_DIR}"/.tmpcapnp*
  rm -rf "${WORK_DIR}/starpilot/system/the_pond"

  case "$(uname -s)" in
    Darwin)
      find "${WORK_DIR}" \
        \( -path "${WORK_DIR}/.venv" -o -path "${WORK_DIR}/.git" -o -path "${WORK_DIR}/.host_runtime" \) -prune -o \
        -type f \( -name '*.cpython-*-linux-gnu.so' -o -name '*.cpython-*-linux-musl.so' \) -exec rm -f {} +
      ;;
    Linux)
      find "${WORK_DIR}" \
        \( -path "${WORK_DIR}/.venv" -o -path "${WORK_DIR}/.git" -o -path "${WORK_DIR}/.host_runtime" \) -prune -o \
        -type f -name '*.cpython-*-darwin.so' -exec rm -f {} +
      ;;
  esac
}

purge_host_desktop_ui_artifacts() {
  rm -f \
    "${WORK_DIR}/selfdrive/ui/libqt_widgets.a" \
    "${WORK_DIR}/selfdrive/ui/libqt_util.a" \
    "${WORK_DIR}/selfdrive/ui/assets.o" \
    "${WORK_DIR}/selfdrive/ui/main.o" \
    "${WORK_DIR}/selfdrive/ui/moc_ui.o" \
    "${WORK_DIR}/selfdrive/ui/ui.o" \
    "${WORK_DIR}/selfdrive/ui/ui" \
    "${WORK_DIR}/cereal/gen/cpp/"*.capnp.o
}

ensure_host_python_tools() {
  ensure_venv

  local root_py_minor
  root_py_minor="$("${ROOT_DIR}/.venv/bin/python3" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

  if [[ -x "${HOST_VENV}/bin/python3" ]]; then
    local host_py_minor
    host_py_minor="$("${HOST_VENV}/bin/python3" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    if [[ "${host_py_minor}" != "${root_py_minor}" ]]; then
      rm -rf "${HOST_VENV}"
      purge_host_python_artifacts
    fi
  fi

  if [[ -x "${HOST_VENV}/bin/scons" && -x "${HOST_VENV}/bin/cythonize" && -x "${HOST_VENV}/bin/python3" ]]; then
    return
  fi

  (
    cd "${WORK_DIR}"
    UV_PROJECT_ENVIRONMENT="${HOST_VENV}" UV_PYTHON="${ROOT_DIR}/.venv/bin/python3" uv sync --frozen --all-extras
  )
}

ensure_host_python_extensions() {
  local jobs
  jobs="$(default_jobs)"

  run_host_scons "${jobs}" \
    common/params_pyx.so \
    common/transformations/transformations.so \
    msgq_repo/msgq/ipc_pyx.so \
    msgq_repo/msgq/visionipc/visionipc_pyx.so \
    rednose/helpers/ekf_sym_pyx.so \
    system/loggerd/bootlog \
    system/loggerd/loggerd \
    system/loggerd/encoderd
}

sync_host_generated_headers() {
  if ! command -v capnpc >/dev/null 2>&1; then
    return
  fi

  (
    cd "${WORK_DIR}"
    mkdir -p cereal/gen/cpp
    capnpc --src-prefix=cereal \
      cereal/log.capnp \
      cereal/car.capnp \
      cereal/legacy.capnp \
      cereal/custom.capnp \
      -o c++:cereal/gen/cpp/
  )
}

sync_worktree() {
  ensure_venv

  mkdir -p "${HOST_ROOT}"
  rm -rf "${WORK_DIR}/starpilot/system/the_pond"

  local excludes=(
    ".git/"
    ".venv/"
    ".venv-linux-arm64/"
    ".cache/"
    ".comma_sysroot/"
    ".host_runtime/"
    ".tmpcapnp*/"
    "__pycache__/"
    "*.pyc"
    "*.pyo"
    "*.cpython-*-linux-gnu.so"
    "*.cpython-*-linux-musl.so"
    "*.cpython-*-darwin.so"
    "*.o"
    "*.os"
    ".sconsign.dblite"
    "compile_commands.json"
    "tools/plotjuggler/bin/"
    "tools/replay/replay"
    "tools/replay/tests/test_replay"
    "tools/cabana/cabana"
    "tools/cabana/tests/test_cabana"
    "selfdrive/ui/ui"
    "selfdrive/ui/ui.macos"
    "selfdrive/ui/ui.larch64"
    "selfdrive/ui/libqt_widgets.a"
    "selfdrive/ui/libqt_util.a"
    "cereal/libcereal.a"
    "cereal/libsocketmaster.a"
    "cereal/messaging/bridge"
    "common/libcommon.a"
    "common/params_pyx.so"
    "common/params_pyx.cpp"
    "common/transformations/libtransformations.a"
    "common/transformations/transformations.so"
    "system/loggerd/bootlog"
    "system/loggerd/loggerd"
    "system/loggerd/encoderd"
    "system/loggerd/liblogger.a"
    "msgq_repo/libmsgq.a"
    "msgq_repo/libvisionipc.a"
    "msgq_repo/msgq/ipc_pyx.so"
    "msgq_repo/msgq/visionipc/visionipc_pyx.so"
    "rednose_repo/rednose/helpers/ekf_sym_pyx.so"
    "selfdrive/modeld/models/commonmodel_pyx.so"
    "selfdrive/pandad/libcan_list_to_can_capnp.a"
    "selfdrive/pandad/pandad_api_impl.so"
    "selfdrive/controls/lib/lateral_mpc_lib/c_generated_code/"
    "selfdrive/controls/lib/lateral_mpc_lib/c_generated_code/acados_ocp_solver_pyx.so"
    "selfdrive/controls/lib/lateral_mpc_lib/c_generated_code/libacados_ocp_solver_lat.so"
    "selfdrive/controls/lib/lateral_mpc_lib/c_generated_code/libacados_ocp_solver_lat.dylib"
    "selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code/"
    "selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code/acados_ocp_solver_pyx.so"
    "selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code/libacados_ocp_solver_long.so"
    "selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code/libacados_ocp_solver_long.dylib"
    "starpilot/tinygrad_modeld/"
    "third_party/libjson11.a"
    "third_party/libkaitai.a"
  )

  local rsync_args=(-a --delete)
  local pattern=""
  for pattern in "${excludes[@]}"; do
    rsync_args+=(--exclude "${pattern}")
  done

  local _capnp_before
  _capnp_before="$(stat -c '%Y' "${WORK_DIR}/cereal/custom.capnp" 2>/dev/null || echo 0)"
  rsync "${rsync_args[@]}" "${ROOT_DIR}/" "${WORK_DIR}/"
  if [[ ! -e "${WORK_DIR}/.git" ]]; then
    ln -s "${ROOT_DIR}/.git" "${WORK_DIR}/.git"
  fi
  local _capnp_after
  _capnp_after="$(stat -c '%Y' "${WORK_DIR}/cereal/custom.capnp" 2>/dev/null || echo 0)"
  if [[ "${_capnp_before}" != "${_capnp_after}" ]]; then
    rm -rf "${SP_SCONS_CACHE_DIR:-${HOST_ROOT}/scons_cache}"
  fi
  purge_host_desktop_ui_artifacts
  purge_host_foreign_platform_artifacts
  rm -f "${WORK_DIR}/third_party/libjson11.a" "${WORK_DIR}/third_party/libkaitai.a"
  sync_host_generated_headers
  ensure_host_python_tools
  rm -rf "${WORK_DIR}/.venv"
  ln -s "${HOST_VENV}" "${WORK_DIR}/.venv"
}

setup_build_env() {
  if [[ -d /opt/homebrew/bin ]]; then
    export PATH="/opt/homebrew/bin:${PATH}"
  fi

  mkdir -p "${HOST_ROOT}/scons_cache"
  export SP_SCONS_CACHE_DIR="${HOST_ROOT}/scons_cache"

  if [[ "$(uname -s)" == "Darwin" ]]; then
    export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:${PATH}"
    export ZMQ=1
    export CC="/usr/bin/clang"
    export CXX="/usr/bin/clang++"
    export AR="/usr/bin/ar"
    export RANLIB="/usr/bin/ranlib"
  fi

  unset CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH CPPFLAGS CFLAGS CXXFLAGS LDFLAGS
}

export_workdir_pythonpath() {
  export PYTHONPATH="${WORK_DIR}:${WORK_DIR}/starpilot/third_party"
  local repo_dir=""
  for repo_dir in "${WORK_DIR}"/*_repo; do
    [[ -d "${repo_dir}" ]] && export PYTHONPATH="${PYTHONPATH}:${repo_dir}"
  done
  [[ -d "${WORK_DIR}/third_party/acados" ]] && export PYTHONPATH="${PYTHONPATH}:${WORK_DIR}/third_party/acados"
}

run_host_scons() {
  local jobs="$1"
  shift || true

  (
    cd "${WORK_DIR}"
    setup_build_env
    source .venv/bin/activate
    SP_DISABLE_AUTO_DEVICE_SCONS=1 "${WORK_DIR}/.venv/bin/scons" --extras -j"${jobs}" "$@"
  )
}

run_in_worktree() {
  (
    cd "${WORK_DIR}"
    setup_build_env
    "$@"
  )
}

run_python_tool() {
  local script_path="$1"
  shift || true

  (
    cd "${WORK_DIR}"
    setup_build_env
    export_workdir_pythonpath
    source .venv/bin/activate
    exec "${WORK_DIR}/.venv/bin/python3" "${WORK_DIR}/${script_path}" "$@"
  )
}

run_host_python() {
  (
    cd "${WORK_DIR}"
    setup_build_env
    export_workdir_pythonpath
    source .venv/bin/activate
    exec "${WORK_DIR}/.venv/bin/python3" "$@"
  )
}

launch_c3() {
  local jobs
  jobs="$(default_jobs)"
  if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
    jobs="$1"
    shift || true
  fi

  sync_worktree
  run_in_worktree "${WORK_DIR}/scripts/launch_ui_desktop.sh" "${jobs}" "$@"
}

launch_c4() {
  local jobs
  jobs="$(default_jobs)"
  if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
    jobs="$1"
    shift || true
  fi

  sync_worktree
  run_in_worktree "${WORK_DIR}/scripts/launch_ui_c4_desktop.sh" "${jobs}" "$@"
}

launch_raybig() {
  local jobs
  jobs="$(default_jobs)"
  if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
    jobs="$1"
    shift || true
  fi

  sync_worktree
  run_in_worktree "${WORK_DIR}/scripts/launch_ui_raybig_desktop.sh" "${jobs}" "$@"
}

launch_onroad() {
  local jobs
  jobs="$(default_jobs)"
  if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
    jobs="$1"
    shift || true
  fi

  sync_worktree
  run_in_worktree "${WORK_DIR}/scripts/launch_onroad_desktop.sh" "${jobs}" "$@"
}

launch_replay() {
  local jobs
  jobs="$(default_jobs)"
  if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
    jobs="$1"
    shift || true
  fi

  sync_worktree
  run_host_scons "${jobs}" tools/replay/replay

  (
    cd "${WORK_DIR}"
    setup_build_env
    export BASEDIR="${WORK_DIR}"
    exec "${WORK_DIR}/tools/replay/replay" "$@"
  )
}

launch_cabana() {
  local jobs
  jobs="$(default_jobs)"
  if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
    jobs="$1"
    shift || true
  fi

  sync_worktree
  run_host_scons "${jobs}" tools/cabana/cabana

  (
    cd "${WORK_DIR}"
    setup_build_env
    export BASEDIR="${WORK_DIR}"
    exec "${WORK_DIR}/tools/cabana/cabana" "$@"
  )
}

launch_plotjuggler() {
  local jobs
  jobs="$(default_jobs)"
  if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
    jobs="$1"
    shift || true
  fi

  sync_worktree
  run_host_scons "${jobs}" \
    common/params_pyx.so \
    common/transformations/transformations.so \
    msgq_repo/msgq/ipc_pyx.so \
    msgq_repo/msgq/visionipc/visionipc_pyx.so
  run_python_tool "tools/plotjuggler/juggle.py" "$@"
}

launch_python() {
  sync_worktree
  ensure_host_python_extensions
  run_host_python "$@"
}

launch_pytest() {
  sync_worktree
  ensure_host_python_extensions
  if [[ "$(uname -s)" == "Darwin" ]]; then
    export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} -n0"
  fi
  run_host_python -m pytest "$@"
}

open_shell() {
  sync_worktree
  (
    cd "${WORK_DIR}"
    setup_build_env
    export_workdir_pythonpath
    source .venv/bin/activate
    exec "${SHELL:-/bin/bash}"
  )
}

main() {
  local command="${1:-help}"
  local bucket=""
  if [[ $# -gt 0 ]]; then
    shift || true
  fi

  case "${command}" in
    help|-h|--help)
      usage
      ;;
    c3|c4|raybig|onroad|replay|shell|python|pytest)
      set_host_bucket "shared"
      acquire_host_lock "${command} $*"
      ;;
    cabana)
      set_host_bucket "cabana"
      acquire_host_lock "${command} $*"
      ;;
    plotjuggler|juggle)
      set_host_bucket "shared"
      acquire_host_lock "${command} $*"
      ;;
    sync)
      if [[ $# -gt 0 ]]; then
        bucket="$(resolve_host_bucket "${1}")" || {
          echo "Unknown host bucket for sync: ${1}" >&2
          echo "Valid sync buckets: shared, cabana" >&2
          exit 1
        }
        shift || true
        sync_selected_bucket "${bucket}"
      else
        sync_all_buckets
      fi
      exit 0
      ;;
    *)
      echo "Unknown command: ${command}" >&2
      echo >&2
      usage >&2
      exit 1
      ;;
  esac

  case "${command}" in
    c3)
      launch_c3 "$@"
      ;;
    c4)
      launch_c4 "$@"
      ;;
    raybig)
      launch_raybig "$@"
      ;;
    onroad)
      launch_onroad "$@"
      ;;
    replay)
      launch_replay "$@"
      ;;
    cabana)
      launch_cabana "$@"
      ;;
    plotjuggler|juggle)
      launch_plotjuggler "$@"
      ;;
    shell)
      open_shell
      ;;
    python)
      launch_python "$@"
      ;;
    pytest)
      launch_pytest "$@"
      ;;
  esac
}

set_host_bucket "shared"
main "$@"
