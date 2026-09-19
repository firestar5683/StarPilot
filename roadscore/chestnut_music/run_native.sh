#!/usr/bin/env bash
set -euo pipefail
cd /data/openpilot/tinygrad_repo
export PATH=/data/roadscore-feasibility/venv/bin:/usr/bin:/bin
export PYTHONPATH=/data/openpilot/tinygrad_repo
export DEV=USB+AMD:LLVM
export MAX_JOBS=1 CXX=clang++
export TORCH_EXTENSIONS_DIR=/data/roadscore-feasibility/cache/torch_extensions
export XDG_CACHE_HOME=/data/roadscore-feasibility/cache
export HF_HOME=/data/roadscore-feasibility/cache/huggingface
export TMPDIR=/data/roadscore-feasibility/tmp
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
exec timeout 900 python -u /data/roadscore-feasibility/musicgen_native.py "$@"
