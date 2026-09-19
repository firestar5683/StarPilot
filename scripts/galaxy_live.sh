#!/usr/bin/env bash
# Live-reload dev launcher for The Galaxy.
# Usage:
#   scripts/galaxy_live.sh            # serve repo live on :8083
#   scripts/galaxy_live.sh 8099       # or a specific port
#   scripts/galaxy_live.sh --sync     # sync host runtime first (after big pulls)
#
# `./dev galaxy --live [port]` is the same thing and builds the host runtime first.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')"
HOST_ROOT="${ROOT}/.host_runtime/${PLATFORM}"
WT="${HOST_ROOT}/worktree"
GX="starpilot/system/the_galaxy"
PID_FILE="${HOST_ROOT}/galaxy_live.pid"
PORT="${SP_GALAXY_PORT:-8083}"
SYNC_REQUESTED=0
GALAXY_LIVE_CHILD_PID=""

galaxy_live_active_pid() {
  local pid=""
  [[ -f "${PID_FILE}" ]] || return 1
  pid="$(<"${PID_FILE}")"
  [[ "${pid}" =~ ^[0-9]+$ ]] || return 1
  kill -0 "${pid}" 2>/dev/null || return 1
  printf '%s\n' "${pid}"
}

pid_is_ancestor() {
  local target="$1" current="$$"
  while [[ "${current}" -gt 1 ]]; do
    [[ "${current}" == "${target}" ]] && return 0
    current="$(ps -o ppid= -p "${current}" 2>/dev/null | tr -d ' ')"
    [[ -n "${current}" ]] || return 1
  done
  return 1
}

kill_process_tree() {
  local parent="$1" child=""
  for child in $(pgrep -P "${parent}" 2>/dev/null || true); do
    kill_process_tree "${child}"
  done
  kill "${parent}" 2>/dev/null || true
}

# Any host_tool_runner command started from here has to take the shared bucket lock, and
# an ancestor that already holds it (typically `./dev shell`, which execs the shell while
# holding the lock) will never release it. Detect that so we fail with a message instead
# of hanging forever.
refuse_if_ancestor_holds_lock() {
  local lock_pid_file="${HOST_ROOT}/lock/pid" holder=""
  [[ -f "${lock_pid_file}" ]] || return 0
  holder="$(<"${lock_pid_file}")"
  [[ -n "${holder}" ]] || return 0
  pid_is_ancestor "${holder}" || return 0
  echo "pid ${holder} already holds the shared host lock (likely './dev shell')." >&2
  echo "Run this from a normal shell instead." >&2
  exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/galaxy_live.sh [--sync] [port]"
  exit 0
fi
if [[ "${1:-}" == "--sync" ]]; then
  SYNC_REQUESTED=1
  shift
  refuse_if_ancestor_holds_lock
  "${ROOT}/scripts/host_tool_runner.sh" sync
fi
if [[ -n "${1:-}" && "${1}" =~ ^[0-9]+$ ]]; then
  PORT="${1}"
fi

if [[ ! -d "${WT}/.venv" || ! -f "${WT}/${GX}/the_galaxy.py" ]]; then
  refuse_if_ancestor_holds_lock
  echo "Host runtime not ready. Building it once now (several minutes, first time only)..."
  "${ROOT}/scripts/host_tool_runner.sh" galaxy --prepare || true
fi
if [[ ! -d "${WT}/.venv" || ! -f "${WT}/${GX}/the_galaxy.py" ]]; then
  echo "Host runtime build did not complete. Try: ${ROOT}/dev galaxy --prepare" >&2
  exit 1
fi

# Reserve the live slot with an atomic link(2). Writing the pid into a temp file and
# hardlinking it into place means the pidfile never exists empty, so a racing second
# launch either sees a valid owner or reclaims a genuinely dead one. A plain
# check-then-create pidfile let both launches pass before either wrote its pid.
reserve_live_slot() {
  local tmp="" attempts=0

  # `ln` treats an existing directory as "link inside it" and succeeds without ever
  # creating our pidfile. Clear any non-regular file at our path so the link below is
  # a real check rather than a silent no-op.
  if [[ -e "${PID_FILE}" && ! -f "${PID_FILE}" ]]; then
    echo "Removing non-file Galaxy live pidfile at ${PID_FILE}." >&2
    rm -rf "${PID_FILE}"
  fi

  tmp="$(mktemp "${HOST_ROOT}/.galaxy_live_pid.XXXXXX")" || {
    echo "Unable to create Galaxy live pidfile in ${HOST_ROOT}." >&2
    exit 1
  }
  printf '%s\n' "$$" > "${tmp}"
  while ! ln "${tmp}" "${PID_FILE}" 2>/dev/null; do
    attempts=$((attempts + 1))
    if (( attempts > 10 )); then
      rm -f "${tmp}"
      echo "Unable to reserve Galaxy live pidfile at ${PID_FILE}; giving up." >&2
      exit 1
    fi
    local existing_pid=""
    existing_pid="$(galaxy_live_active_pid || true)"
    if [[ -n "${existing_pid}" ]]; then
      rm -f "${tmp}"
      if (( SYNC_REQUESTED )); then
        echo "Live Galaxy already running (pid ${existing_pid}); sync complete."
        exit 0
      fi
      echo "Live Galaxy already running (pid ${existing_pid}). Stop it before starting another." >&2
      exit 1
    fi
    echo "Removing stale Galaxy live pidfile." >&2
    rm -f "${PID_FILE}" 2>/dev/null || true
  done
  rm -f "${tmp}"
}

cleanup_galaxy_live() {
  trap - EXIT INT TERM
  if [[ -n "${GALAXY_LIVE_CHILD_PID}" ]] && kill -0 "${GALAXY_LIVE_CHILD_PID}" 2>/dev/null; then
    # Werkzeug's reloader runs the real server in a grandchild. Killing only the
    # supervisor leaves that grandchild holding the port, so tear down the whole tree.
    kill_process_tree "${GALAXY_LIVE_CHILD_PID}"
    sleep 0.5
    kill -KILL "${GALAXY_LIVE_CHILD_PID}" 2>/dev/null || true
  fi
  # Only drop the pidfile if it still names this process; a newer session may own it.
  if [[ "$(galaxy_live_active_pid || true)" == "$$" ]]; then
    rm -f "${PID_FILE}"
  fi
}
trap cleanup_galaxy_live EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Reserve before creating the symlink: a sync landing in between would otherwise see the
# link with no live pid and drop it.
reserve_live_slot
rm -rf "${WT}/${GX}"
ln -s "${ROOT}/${GX}" "${WT}/${GX}"

echo "Galaxy live-dev -> http://127.0.0.1:${PORT}/   (backend auto-reload ON)"
echo "Edit repo files. Backend .py restarts; frontend needs a hard-refresh. Errors print here."
echo "Hard-refresh matters: assets/service-worker.js will otherwise serve a stale frontend."
echo "Only ${GX}/ is live. Edits outside it need: scripts/galaxy_live.sh --sync"
echo "Mobile layout (assets/mobile/) is on the same URL -- use browser device emulation."
echo "Stop with Ctrl+C."

cd "${WT}"
export PYTHONPATH="${WT}:${WT}/starpilot/third_party"
for d in "${WT}"/*_repo; do
  [[ -d "${d}" ]] && export PYTHONPATH="${PYTHONPATH}:${d}"
done
export SP_GALAXY_DIR="${SP_GALAXY_DIR:-${HOME}/.comma/starpilot/data/galaxy}"
export SP_GALAXY_HOST="0.0.0.0"
export SP_GALAXY_PORT="${PORT}"
export SP_GALAXY_DEBUG="1"
export SP_GALAXY_RELOAD="1"
# Run the server as a child rather than exec so the EXIT trap can remove the lock and
# tear down the whole reloader process tree even if this script receives SIGTERM.
"${WT}/.venv/bin/python3" -m openpilot.starpilot.system.the_galaxy.the_galaxy &
GALAXY_LIVE_CHILD_PID=$!
wait "${GALAXY_LIVE_CHILD_PID}"
