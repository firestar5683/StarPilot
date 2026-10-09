#!/bin/sh
# Run on the comma after copying the project to /data/galaxy-ble/app.
set -eu
bridge_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
data_dir=/data/galaxy-ble
mkdir -p "$data_dir"
chmod 700 "$data_dir"
if [ -x /data/openpilot/.venv/bin/python ]; then
  python_bin=/data/openpilot/.venv/bin/python
elif [ -x /data/openpilot/.venv/bin/python3 ]; then
  python_bin=/data/openpilot/.venv/bin/python3
else
  python_bin=$(command -v python3)
fi
"$python_bin" -m venv --system-site-packages "$data_dir/venv"
"$data_dir/venv/bin/python" -m pip install -r "$bridge_dir/requirements.txt"
if [ ! -f "$data_dir/pairing.json" ]; then
  printf '\nPairing key: paste this into the iPhone app and keep it private.\n'
  "$data_dir/venv/bin/python" "$bridge_dir/server.py" --init-key
else
  printf '\nExisting pairing key preserved.\n'
fi
printf '\nStart the bridge with:\n'
printf '%s\n' "$data_dir/venv/bin/python $bridge_dir/server.py"
