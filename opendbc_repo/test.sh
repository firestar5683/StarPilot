#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
cd $DIR

source ./setup.sh

# *** build ***
scons -j8

# *** lint + test ***
status=0
ruff check . || status=1
git ls-files -z -- . | xargs -0 codespell -L tge,stdio -S '*.dbc' || status=1
cpplint --exclude=opendbc/safety/tests/misra/cppcheck/ --exclude=opendbc/safety/tests/.venv/ \
  --exclude=opendbc/can/*_pyx.cpp --recursive --quiet --counting=detailed --linelength=240 \
  --filter=-build,-legal,-readability,-runtime,-whitespace,+build/include_subdir,+build/forward_decl,+build/include_what_you_use,+build/deprecated,+whitespace/comma,+whitespace/line_length,+whitespace/empty_if_body,+whitespace/empty_loop_body,+whitespace/empty_conditional_body,+whitespace/forcolon,+whitespace/parens,+whitespace/semicolon,+whitespace/tab,+readability/braces opendbc/ || status=1
opendbc/safety/tests/misra/test_misra.sh || status=1
pytest -n8 || status=1

# *** all done ***
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
if [ "$status" -eq 0 ]; then
  printf "\n${GREEN}All good!${NC} Finished build, lint, and test in ${SECONDS}s\n"
else
  printf "\n${RED}Checks failed.${NC} Finished build, lint, and test in ${SECONDS}s\n"
fi
exit "$status"
