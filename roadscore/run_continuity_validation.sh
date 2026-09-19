#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${ROADSCORE_CURVE_ROUTE:?Set private fixture}" "${ROADSCORE_ARRIVAL_ROUTE:?Set private fixture}" "${ROADSCORE_OTHER_ROUTE:?Set private fixture}"
# Reproducible private captures; all normal wrappers mute the physical speaker.
# The existing worker must already be ready; no duplicate GPU ownership.
ssh comma@192.168.3.111 'python3 - <<"PY"
import time
from pathlib import Path
p=Path("/data/roadscore/generated/worker_ready")
end=time.monotonic()+300
while not p.exists():
 if time.monotonic()>end:raise SystemExit("Worker readiness timed out")
 time.sleep(1)
PY'
for spec in "live_curve ${ROADSCORE_CURVE_ROUTE##*/} 110 100" "live_arrival ${ROADSCORE_ARRIVAL_ROUTE##*/} 170 87" "other_route ${ROADSCORE_OTHER_ROUTE##*/} 100 120" "live_development ${ROADSCORE_CURVE_ROUTE##*/} 110 210"; do
 read -r name route start duration <<< "$spec"
 test ! -e "results/continuity/$name" || { echo "Preserving existing $name"; exit 1; }
 if test -d results/latest; then mv results/latest "results/continuity/prior_latest_$(date +%s)"; fi
 ./run_roadscore_demo.sh "$route" "$start" "$duration"
 mv results/latest "results/continuity/$name"
done
