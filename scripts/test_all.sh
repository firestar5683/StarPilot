#!/usr/bin/env bash

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null && pwd)"
FAILED=0

export DEBUG=0
export PYTHONHASHSEED=0

run_group() {
  local name="$1"
  shift
  echo "[$name]"
  if ! "$@"; then
    FAILED=1
  fi
}

cd "$ROOT"

if [ "$(uname -s)" = "Darwin" ]; then
  run_group root "$ROOT/dev" pytest
else
  run_group build "$ROOT/.venv/bin/python" -m SCons -j8
  run_group root "$ROOT/.venv/bin/pytest"
fi
run_group opendbc bash "$ROOT/opendbc_repo/test.sh"
run_group safety bash "$ROOT/opendbc_repo/opendbc/safety/tests/test.sh"
run_group panda bash "$ROOT/panda/test.sh"

if [ "$(uname -s)" = "Linux" ]; then
  run_group mutation bash "$ROOT/opendbc_repo/opendbc/safety/tests/mutation.sh"
else
  echo "[mutation] requires Linux"
fi

exit "$FAILED"
