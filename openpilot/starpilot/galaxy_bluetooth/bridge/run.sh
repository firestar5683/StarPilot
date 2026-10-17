#!/bin/sh
# Run a bridge script with openpilot's Python. dbus-next and zeroconf are vendored
# beside the bridge, so nothing is downloaded or installed on comma.
set -eu
bridge_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$bridge_dir/../vendor${PYTHONPATH:+:$PYTHONPATH}"
for python_bin in /usr/local/venv/bin/python /data/openpilot/.venv/bin/python; do
  if [ -x "$python_bin" ]; then
    exec "$python_bin" "$@"
  fi
done
exec python3 "$@"
