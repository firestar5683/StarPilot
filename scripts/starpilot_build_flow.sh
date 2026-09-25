#!/usr/bin/env bash
# Compatibility entry point for the historical build-flow commands.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

usage() {
  cat <<'EOF'
Usage: scripts/starpilot_build_flow.sh {verify|mac|device|laptop-setup|laptop-device} [jobs]

verify        Validate the local build entry points and current target files.
mac           Run local Python compilation checks (no device binaries).
device        Build on AGNOS/aarch64 hardware and set prebuilt on success.
laptop-setup  Explicitly prepare image and sysroot; may access network/device.
laptop-device Run the complete device-target container build.
EOF
}

case "${1:-}" in
  verify)
    bash -n build scripts/laptop_device_build.sh "$0"
    for path in SConstruct openpilot/common/SConscript openpilot/cereal/SConscript \
                panda/SConscript openpilot/selfdrive/modeld/SConscript \
                tools/laptop_device_build/Dockerfile; do
      [[ -f "${path}" ]] || { echo "Missing ${path}" >&2; exit 1; }
    done
    echo "Build entry points and current target files found."
    ;;
  mac)
    [[ -x .venv/bin/python ]] || { echo "Missing .venv/bin/python" >&2; exit 1; }
    .venv/bin/python -m py_compile openpilot/system/timed.py openpilot/common/spinner.py openpilot/common/text_window.py
    .venv/bin/python -m compileall -q openpilot/starpilot openpilot/selfdrive openpilot/system
    .venv/bin/python -c 'import openpilot.system.loggerd.xattr_cache'
    echo "Local Python compilation passed; this does not produce device binaries."
    ;;
  device)
    [[ -f /AGNOS && "$(uname -m)" == aarch64 ]] || { echo "device mode requires AGNOS/aarch64 hardware" >&2; exit 1; }
    [[ -x .venv/bin/scons ]] || { echo "Missing .venv/bin/scons" >&2; exit 1; }
    jobs="${2:-4}"
    [[ "${jobs}" =~ ^[0-9]+$ ]] || { echo "jobs must be numeric" >&2; exit 1; }
    rm -f prebuilt
    .venv/bin/scons "-j${jobs}"
    scripts/laptop_device_build.sh verify-artifacts
    touch prebuilt
    ;;
  laptop-setup)
    shift
    exec scripts/laptop_device_build.sh setup "$@"
    ;;
  laptop-device)
    shift
    exec scripts/laptop_device_build.sh build "$@"
    ;;
  *) usage; exit 1 ;;
esac
