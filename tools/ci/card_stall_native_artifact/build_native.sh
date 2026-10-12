#!/usr/bin/env bash
# Artifact-only preparation. Run only after explicit CI execution approval.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
: "${PYTHON:?Set the absolute native ARM CPython 3.12.13 interpreter}"
: "${EXPECTED_SOURCE_COMMIT:?Set the exact approved diagnostics commit SHA}"
: "${EXPECTED_BASE_COMMIT:?Set the exact reviewed e838 baseline commit SHA}"
: "${EXPECTED_GCC_VERSION:?Set the explicitly reviewed GCC 13 full version}"
exec "$PYTHON" "$(dirname "$0")/build_native.py" "$@"
