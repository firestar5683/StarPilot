#!/usr/bin/env bash
set -euo pipefail
cd /data/openpilot/tinygrad_repo
export DEV=USB+AMD:LLVM MAX_JOBS=1 CXX=clang++ OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export PYTHONPATH="${ROADSCORE_TINYGRAD_PATH:-/data/openpilot/tinygrad_repo}"
export XDG_CACHE_HOME=/data/roadscore-feasibility/cache TMPDIR=/data/roadscore-feasibility/tmp
worker="${ROADSCORE_WORKER:-$(/usr/local/venv/bin/python /data/roadscore/prototype/composer_choice.py)}"
exec /data/sa3-feasibility/venv/bin/python -u "$worker"
