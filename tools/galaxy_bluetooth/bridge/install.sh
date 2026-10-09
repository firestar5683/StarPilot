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

# AGNOS may omit ensurepip. Create the bridge environment without it, then
# install into that explicit environment using an existing package installer.
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
if [ ! -f "$data_dir/pairing.json" ]; then
  printf '\nPairing key: paste this into the iPhone app and keep it private.\n'
  "$data_dir/venv/bin/python" "$bridge_dir/server.py" --key-file "$data_dir/pairing.json" --init-key
else
  printf '\nExisting pairing key preserved.\n'
fi
printf '\nStart the bridge with:\n'
printf '"%s" "%s" --key-file "%s"\n' "$data_dir/venv/bin/python" "$bridge_dir/server.py" "$data_dir/pairing.json"
