#!/usr/bin/env bash
# Build in a staged checkout on actual AGNOS/aarch64 hardware.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
[[ -f /AGNOS && "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || {
  echo "ERROR: native build requires AGNOS/aarch64 hardware" >&2
  exit 1
}
cd "${ROOT_DIR}"

if [[ -x /usr/local/venv/bin/scons ]]; then
  SCONS=/usr/local/venv/bin/scons
elif [[ -x "${ROOT_DIR}/.venv/bin/scons" ]]; then
  SCONS="${ROOT_DIR}/.venv/bin/scons"
else
  echo "ERROR: SCons is missing from the device Python environment" >&2
  exit 1
fi

# Bind vendored build imports to this checkout, not an editable active install.
export PYTHONPATH="${ROOT_DIR}:${ROOT_DIR}/msgq_repo:${ROOT_DIR}/opendbc_repo:${ROOT_DIR}/rednose_repo:${ROOT_DIR}/teleoprtc_repo:${ROOT_DIR}/tinygrad_repo"
export PATH="$(dirname "${SCONS}"):${PATH}"

mode="${1:-}"
shift || true
for arg in "$@"; do
  case "${arg}" in
    RELEASE=*|CERT=*)
      echo "ERROR: RELEASE and CERT must be environment variables, not SCons arguments." >&2
      echo "Use: RELEASE=1 CERT=/path/to/certificate ./build --panda 4" >&2
      exit 2
      ;;
  esac
done
case "${mode}" in
  scons)
    if [[ "${1:-}" == --no-scrub ]]; then
      shift
    fi
    exec "${SCONS}" "$@"
    ;;
  build)
    jobs=4
    if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
      jobs="$1"
      shift
    fi
    [[ "${jobs}" -gt 0 ]] || { echo "ERROR: jobs must be positive" >&2; exit 2; }
    rm -f prebuilt
    "${SCONS}" "-j${jobs}" "$@"
    if [[ "$#" -ne 0 ]]; then
      echo "Build options/targets were supplied; prebuilt remains unset."
      exit 0
    fi
    python3 -m tools.laptop_device_build.package_model_chunks --source "${ROOT_DIR}/openpilot/selfdrive/modeld/models" --destination "${ROOT_DIR}/openpilot/selfdrive/modeld/models"
    python3 "${ROOT_DIR}/tools/laptop_device_build/validate_artifacts.py" "${ROOT_DIR}"
    python3 "${ROOT_DIR}/tools/laptop_device_build/validate_params_registry.py" "${ROOT_DIR}"
    python3 "${ROOT_DIR}/openpilot/common/prebuilt_manifest.py" "${ROOT_DIR}"
    touch prebuilt
    ;;
  *)
    echo "ERROR: native build accepts only build or scons" >&2
    exit 2
    ;;
esac
