#!/usr/bin/env bash
# Build the existing WebRTC backend with the ICE role-presence correction.
# Requires git, uv, a C/C++ compiler, and Python 3.12+. Does not install anything
# into the running device environment. The output wheel is architecture-specific.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PATCH_DIR="$SCRIPT_DIR/patches"
OUTPUT_DIR="${1:?usage: bash tools/webrtc/build_libdatachannel.sh OUTPUT_DIR [PYTHON]}"
BUILD_PYTHON="${2:-python3.12}"
SOURCE_REV="989d29a32968046a002b5b9deb7a00f5012c530c"
BUILD_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/starpilot-webrtc.XXXXXX")"
echo "Build directory (retained for inspection): $BUILD_ROOT"
mkdir -p -- "$OUTPUT_DIR"
OUTPUT_DIR="$(cd -- "$OUTPUT_DIR" && pwd)"

git clone --depth 1 --branch 2026.1.0.dev2 https://github.com/shiguredo/libdatachannel-py.git "$BUILD_ROOT/source"
[[ "$(git -C "$BUILD_ROOT/source" rev-parse HEAD)" == "$SOURCE_REV" ]]
git -C "$BUILD_ROOT/source" apply "$PATCH_DIR/libdatachannel-build.patch"
cp "$PATCH_DIR/libjuice-zero-tiebreaker.patch" "$BUILD_ROOT/source/"

uv venv --python "$BUILD_PYTHON" "$BUILD_ROOT/venv"
uv pip install --python "$BUILD_ROOT/venv/bin/python" \
  build==1.6.0 scikit-build-core==1.0.3 nanobind==3.0.1 cmake==4.4.3 ninja==1.13.2
export PATH="$BUILD_ROOT/venv/bin:$PATH"
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-2}"
cd -- "$BUILD_ROOT/source"
python -m build --wheel --no-isolation --outdir "$OUTPUT_DIR"
uv pip install --python "$BUILD_ROOT/venv/bin/python" --no-index --find-links "$OUTPUT_DIR" \
  'libdatachannel-py==2026.1.0.dev2+starpilot.ice1'
python "$SCRIPT_DIR/check_ice.py"
echo "Validated wheel written to $OUTPUT_DIR; the running environment was not modified."
