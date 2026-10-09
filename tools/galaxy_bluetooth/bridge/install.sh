#!/bin/sh
# Run on the comma after copying the project to /data/galaxy-ble/app.
set -eu
bridge_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
data_dir=${GALAXY_BLE_DATA_DIR:-/data/galaxy-ble}
mkdir -p "$data_dir"
chmod 700 "$data_dir"
python_bin=${GALAXY_BLE_PYTHON:-}
if [ -z "$python_bin" ]; then
  for candidate in /data/openpilot/.venv-linux-arm64/bin/python /data/openpilot/.venv/bin/python /data/openpilot/.venv/bin/python3 /usr/local/venv/bin/python /usr/local/venv/bin/python3; do
    if [ -x "$candidate" ]; then
      python_bin=$candidate
      break
    fi
  done
  if [ -z "$python_bin" ]; then
    python_bin=$(command -v python3)
  fi
fi

"$python_bin" -m venv --without-pip "$data_dir/venv"
uv_bin=$(command -v uv || true)
if [ -z "$uv_bin" ] && [ -x /usr/local/venv/bin/uv ]; then
  uv_bin=/usr/local/venv/bin/uv
fi
if [ -n "$uv_bin" ]; then
  "$uv_bin" pip install --python "$data_dir/venv/bin/python" -r "$bridge_dir/requirements.txt"
elif "$python_bin" -m pip --help 2>/dev/null | grep -q -- '--python'; then
  "$python_bin" -m pip --python "$data_dir/venv/bin/python" install -r "$bridge_dir/requirements.txt"
elif "$data_dir/venv/bin/python" -m ensurepip --upgrade; then
  "$data_dir/venv/bin/python" -m pip install -r "$bridge_dir/requirements.txt"
else
  printf '\nNo usable package installer found. The bridge needs uv, pip 22.3+, or ensurepip.\n' >&2
  printf 'No packages were installed into StarPilot or the system Python.\n' >&2
  exit 1
fi
"$data_dir/venv/bin/python" -c 'import dbus_next; from Crypto.Cipher import AES'
"$data_dir/venv/bin/python" - "$bridge_dir" "$data_dir/pairing.json" <<'KEY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from pairing import ensure_key
ensure_key(Path(sys.argv[2]))
KEY
if [ "${GALAXY_BLE_QUIET:-0}" != "1" ]; then
  printf '\nBridge installed. Pair this phone from Settings → Bluetooth → Pair phone.\n'
fi
