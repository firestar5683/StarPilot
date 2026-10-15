#!/usr/bin/env bash
# On comma, once. Does not change the other companion's venv, units, key or Bluetooth bonds.
set -euo pipefail
COMPANION_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPANION_VENV=/data/galaxy-ble/stardust-venv
python3 -m venv "$COMPANION_VENV"
"$COMPANION_VENV/bin/python" -m pip install -r "$COMPANION_DIR/upstream/tools/galaxy_bluetooth/bridge/requirements.txt"
"$COMPANION_VENV/bin/python" -c 'import dbus_next; from Crypto.Cipher import AES'
printf '%s\n' 'Bluetooth environment ready. Enable Bluetooth on comma, then pair from the Android app over Wi-Fi while parked.'
