#!/usr/bin/env bash
# Called automatically by the comma companion supervisor. Also usable for diagnostics.
set -euo pipefail
COMPANION_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPANION_VENV="${COMPANION_VENV:-/data/galaxy-ble/stardust-venv}"
if command -v uv >/dev/null 2>&1; then
  # AGNOS provides uv; its system Python deliberately has no pip/ensurepip.
  export UV_HTTP_TIMEOUT=10 UV_HTTP_RETRIES=1
  uv venv --no-project --no-config --allow-existing --no-python-downloads --python "$(command -v python3)" "$COMPANION_VENV"
  uv pip install --no-config --no-progress --no-python-downloads --only-binary :all: --python "$COMPANION_VENV/bin/python" \
    -r "$COMPANION_DIR/upstream/tools/galaxy_bluetooth/bridge/requirements.txt"
else
  python3 -m venv "$COMPANION_VENV"
  "$COMPANION_VENV/bin/python" -m pip install --no-input --disable-pip-version-check --only-binary :all: --retries 1 --timeout 10 \
    -r "$COMPANION_DIR/upstream/tools/galaxy_bluetooth/bridge/requirements.txt"
fi
"$COMPANION_VENV/bin/python" -c 'import dbus_next; import zeroconf; from Crypto.Cipher import AES'
printf '%s\n' 'LAN discovery and Bluetooth environment ready. Keep Galaxy enabled and connect the phone and comma to the same trusted LAN. Bluetooth pairing is optional.'
