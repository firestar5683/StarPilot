#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -x "${ROOT_DIR}/.venv/bin/python3" ]]; then
  exec "${ROOT_DIR}/.venv/bin/python3" "${ROOT_DIR}/tools/host_runtime.py" "$@"
fi
exec python3 "${ROOT_DIR}/tools/host_runtime.py" "$@"
