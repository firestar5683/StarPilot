#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-comma@192.168.3.110}"
IMAGE="${2:-/Users/dominickthompson/Desktop/system17.img.xz}"
METADATA="${3:-${IMAGE}.metadata.json}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)
if [[ -n "${SSH_KEY:-}" ]]; then
  SSH_OPTS=(-i "$SSH_KEY" -o IdentitiesOnly=yes "${SSH_OPTS[@]}")
fi

for required_path in "$IMAGE" "$METADATA"; do
  [[ -f "$required_path" ]] || { echo "missing file: $required_path" >&2; exit 1; }
done

metadata_value() {
  python3 - "$METADATA" "$1" <<'PY'
import json
import sys
from pathlib import Path

metadata = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
value = metadata[sys.argv[2]]
if isinstance(value, (dict, list)):
  raise SystemExit(f"metadata field {sys.argv[2]} is not scalar")
print(value)
PY
}

BASE_VERSION="$(metadata_value base_version)"
EXPECTED_VERSION="$(metadata_value target_version)"
RAW_HASH="$(metadata_value raw_sha256)"
RAW_SIZE="$(metadata_value raw_size)"
EXPECTED_XZ_HASH="$(metadata_value xz_sha256)"
ACTUAL_XZ_HASH="$(shasum -a 256 "$IMAGE" | awk '{print $1}')"

[[ "$ACTUAL_XZ_HASH" == "$EXPECTED_XZ_HASH" ]] || {
  echo "compressed image hash mismatch: got $ACTUAL_XZ_HASH, expected $EXPECTED_XZ_HASH" >&2
  exit 1
}

SESSION="local_agnos_flash"
REMOTE_DIR="/data/local_agnos_flash"
REMOTE_MANIFEST="${REMOTE_DIR}/agnos-local-system.json"
REMOTE_RUNNER="${REMOTE_DIR}/run_flash.sh"
REMOTE_AGNOS="${REMOTE_DIR}/agnos.py"
PORT="8989"
IMAGE_NAME="$(basename "$IMAGE")"
REMOTE_IMAGE="${REMOTE_DIR}/${IMAGE_NAME}"

INSTALLED_VERSION="$(ssh "${SSH_OPTS[@]}" "$HOST" 'tr -d "\r\n" </VERSION')"
case "$INSTALLED_VERSION" in
  19.6|19.6.*) ;;
  *)
    echo "refusing flash: device is on incompatible AGNOS $INSTALLED_VERSION; candidate is based on upstream $BASE_VERSION" >&2
    exit 1
    ;;
esac

echo "[CHECK] Device AGNOS: $INSTALLED_VERSION"
echo "[CHECK] Candidate AGNOS: $EXPECTED_VERSION"
echo "[CHECK] Candidate XZ hash: $ACTUAL_XZ_HASH"

ssh "${SSH_OPTS[@]}" "$HOST" "mkdir -p '$REMOTE_DIR'"
scp "${SSH_OPTS[@]}" "$IMAGE" "$HOST:$REMOTE_IMAGE"

LOCAL_AGNOS="$(mktemp "${TMPDIR:-/tmp}/agnos-local.XXXXXX.py")"
trap 'rm -f "$LOCAL_AGNOS"' EXIT
python3 - "$REPO_ROOT/system/hardware/tici/agnos.py" "$LOCAL_AGNOS" <<'PY'
import sys
from pathlib import Path

src, dst = map(Path, sys.argv[1:])
data = src.read_text(encoding="utf-8")
needle = "import openpilot.system.updated.casync.casync as casync"
if data.count(needle) != 1:
  raise SystemExit("could not isolate the unused casync dependency in agnos.py")
data = data.replace(
  needle,
  '''class _UnusedCasync:
  ChunkReader = object
  ChunkDict = object

  def __getattr__(self, name):
    raise RuntimeError("casync support is unavailable in local AGNOS flash runner")
casync = _UnusedCasync()''',
)
dst.write_text(data, encoding="utf-8")
PY
scp "${SSH_OPTS[@]}" "$LOCAL_AGNOS" "$HOST:$REMOTE_AGNOS"

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
: "${EXPECTED_VERSION:?}"

exec > >(tee -a "${REMOTE_DIR}/flash.log") 2>&1

echo "[CHECK] Installed AGNOS: $(cat /VERSION 2>/dev/null || echo unknown)"
echo "[CHECK] Target AGNOS: ${EXPECTED_VERSION}"
echo "[CHECK] Active slot: $(abctl --boot_slot)"
df -h /data

PYTHON_BIN="/usr/local/venv/bin/python3"
[[ -x "$PYTHON_BIN" ]] || { echo "[ERROR] managed Python is unavailable" >&2; exit 1; }

pkill -f "http.server ${PORT}.*${REMOTE_DIR}" >/dev/null 2>&1 || true
"$PYTHON_BIN" -m http.server "$PORT" --bind 127.0.0.1 --directory "$REMOTE_DIR" >"${REMOTE_DIR}/http.log" 2>&1 &
http_pid="$!"
trap 'kill "$http_pid" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 20); do
  if "$PYTHON_BIN" - "$REMOTE_MANIFEST" <<'PY'
import json
import sys
import urllib.request
from pathlib import Path

for entry in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")):
  with urllib.request.urlopen(entry["url"], timeout=2) as response:
    response.read(1)
PY
  then
    http_ready=1
    break
  fi
  sleep 0.25
done

[[ "${http_ready:-0}" == "1" ]] || {
  echo "[ERROR] local image server did not become ready" >&2
  cat "${REMOTE_DIR}/http.log" >&2 || true
  exit 1
}

echo "[FLASH] Writing and verifying the candidate in the inactive system slot"
PYTHONPATH="$(dirname "$REMOTE_AGNOS")" "$PYTHON_BIN" "$REMOTE_AGNOS" --swap "$REMOTE_MANIFEST"

echo "[DONE] Candidate written, verified, and selected"
sudo reboot
REMOTE_RUNNER

ssh "${SSH_OPTS[@]}" "$HOST" "tmux kill-session -t '$SESSION' >/dev/null 2>&1 || true"
ssh "${SSH_OPTS[@]}" "$HOST" "rm -f '$REMOTE_DIR/flash.log' '$REMOTE_DIR/http.log'"
ssh "${SSH_OPTS[@]}" "$HOST" \
  "tmux new-session -d -s '$SESSION' \"REMOTE_DIR='$REMOTE_DIR' REMOTE_MANIFEST='$REMOTE_MANIFEST' REMOTE_AGNOS='$REMOTE_AGNOS' PORT='$PORT' EXPECTED_VERSION='$EXPECTED_VERSION' bash '$REMOTE_RUNNER'\""

echo "Started remote tmux session: $SESSION"
echo "After reboot, run tools/agnos/validate_agnos_runtime.sh $EXPECTED_VERSION on the device."
