#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" =~ ^[0-9]+$ ]]; then shift; fi
exec "${VIRTUAL_ENV:?Host Python environment required}/bin/python" -m openpilot.starpilot.ui.host_launch large "$@"
