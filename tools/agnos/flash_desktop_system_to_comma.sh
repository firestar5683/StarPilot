#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-comma@192.168.3.110}"
IMAGE="${2:-/Users/dominickthompson/Desktop/system8.img.xz}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
SSH_KEY="${SSH_KEY:-${REPO_ROOT}/system/hardware/tici/id_rsa}"
SSH_OPTS=(-i "$SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)

SESSION="local_agnos_flash"
REMOTE_DIR="/data/local_agnos_flash"
REMOTE_MANIFEST="${REMOTE_DIR}/agnos-local-system.json"
REMOTE_RUNNER="${REMOTE_DIR}/run_flash.sh"
REMOTE_AGNOS="${REMOTE_DIR}/agnos.py"
PORT="8989"

EXPECTED_VERSION="12.8.28"
RAW_HASH="4c01245932068aedfceb41cb1aab1f7f044f6659aa2fe2de558f99e2d3aa5793"
RAW_SIZE="5368709120"

if [[ ! -f "$IMAGE" ]]; then
  echo "missing image: $IMAGE" >&2
  exit 1
fi

IMAGE_NAME="$(basename "$IMAGE")"
REMOTE_IMAGE="${REMOTE_DIR}/${IMAGE_NAME}"

ssh "${SSH_OPTS[@]}" "$HOST" "mkdir -p '$REMOTE_DIR'"
scp "${SSH_OPTS[@]}" "$IMAGE" "$HOST:$REMOTE_IMAGE"

LOCAL_AGNOS="$(mktemp "${TMPDIR:-/tmp}/agnos-local.XXXXXX.py")"
python3 - "$REPO_ROOT/system/hardware/tici/agnos.py" "$LOCAL_AGNOS" <<'PY'
import sys
from pathlib import Path

src, dst = map(Path, sys.argv[1:])
data = src.read_text(encoding="utf-8")
data = data.replace(
  "import openpilot.system.updated.casync.casync as casync",
  """class _UnusedCasync:
  def __getattr__(self, name):
    raise RuntimeError("casync support is unavailable in local AGNOS flash runner")
casync = _UnusedCasync()""",
)
dst.write_text(data, encoding="utf-8")
PY
scp "${SSH_OPTS[@]}" "$LOCAL_AGNOS" "$HOST:$REMOTE_AGNOS"
rm -f "$LOCAL_AGNOS"

ssh "${SSH_OPTS[@]}" "$HOST" "cat > '$REMOTE_MANIFEST'" <<MANIFEST
[
  {
    "name": "system",
    "url": "http://127.0.0.1:${PORT}/${IMAGE_NAME}",
    "hash": "${RAW_HASH}",
    "hash_raw": "${RAW_HASH}",
    "size": ${RAW_SIZE},
    "sparse": false,
    "full_check": false,
    "has_ab": true
  }
]
MANIFEST

ssh "${SSH_OPTS[@]}" "$HOST" "cat > '$REMOTE_RUNNER' && chmod +x '$REMOTE_RUNNER'" <<'REMOTE_RUNNER'
#!/usr/bin/env bash
set -euo pipefail

: "${REMOTE_DIR:?}"
: "${REMOTE_MANIFEST:?}"
: "${REMOTE_AGNOS:?}"
: "${PORT:?}"
: "${IMAGE_NAME:?}"
: "${EXPECTED_VERSION:?}"

exec > >(tee -a "${REMOTE_DIR}/flash.log") 2>&1

echo "[STEP] Local AGNOS system flash"
echo "[CHECK] Installed AGNOS: $(cat /VERSION 2>/dev/null || echo unknown)"
echo "[CHECK] Target AGNOS: ${EXPECTED_VERSION}"

if [[ ! -f "$REMOTE_AGNOS" ]]; then
  echo "[ERROR] $REMOTE_AGNOS not found" >&2
  exit 1
fi

if [[ -x /usr/local/venv/bin/python3 ]]; then
  PYTHON_BIN="/usr/local/venv/bin/python3"
else
  PYTHON_BIN="python3"
fi

pkill -f "http.server ${PORT}.*${REMOTE_DIR}" >/dev/null 2>&1 || true
"$PYTHON_BIN" -m http.server "$PORT" --bind 127.0.0.1 --directory "$REMOTE_DIR" >"${REMOTE_DIR}/http.log" 2>&1 &
http_pid="$!"
trap 'kill "$http_pid" >/dev/null 2>&1 || true' EXIT

http_ready=0
for _ in $(seq 1 20); do
  if "$PYTHON_BIN" - "${PORT}" "${IMAGE_NAME}" <<'PY'
import sys
import urllib.request

port, image_name = sys.argv[1], sys.argv[2]
with urllib.request.urlopen(f"http://127.0.0.1:{port}/{image_name}", timeout=2) as resp:
  resp.read(1)
PY
  then
    http_ready=1
    break
  fi
  sleep 0.25
done

if [[ "$http_ready" != "1" ]]; then
  echo "[ERROR] Local image HTTP server did not become ready" >&2
  cat "${REMOTE_DIR}/http.log" >&2 || true
  exit 1
fi

echo "[FLASH] Flashing local system image to inactive AGNOS slot"
PYTHONPATH="$(dirname "$REMOTE_AGNOS")" "$PYTHON_BIN" "$REMOTE_AGNOS" --swap "$REMOTE_MANIFEST"

echo "[DONE] AGNOS flashed and slot swapped"
echo "[REBOOT] Rebooting now"
sudo reboot
REMOTE_RUNNER

ssh "${SSH_OPTS[@]}" "$HOST" "tmux kill-session -t '$SESSION' >/dev/null 2>&1 || true"
ssh "${SSH_OPTS[@]}" "$HOST" "rm -f '$REMOTE_DIR/flash.log' '$REMOTE_DIR/http.log'"
ssh "${SSH_OPTS[@]}" "$HOST" \
  "tmux new-session -d -s '$SESSION' \"REMOTE_DIR='$REMOTE_DIR' REMOTE_MANIFEST='$REMOTE_MANIFEST' REMOTE_AGNOS='$REMOTE_AGNOS' PORT='$PORT' IMAGE_NAME='$IMAGE_NAME' EXPECTED_VERSION='$EXPECTED_VERSION' bash '$REMOTE_RUNNER'\""

echo "Started remote tmux session: $SESSION"
echo "Watch it with: ssh $HOST 'tmux attach -t $SESSION'"
