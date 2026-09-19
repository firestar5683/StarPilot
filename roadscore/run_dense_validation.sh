#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${ROADSCORE_CURVE_ROUTE:?Set private fixture}" "${ROADSCORE_ARRIVAL_ROUTE:?Set private fixture}" "${ROADSCORE_OTHER_ROUTE:?Set private fixture}"
ssh comma@192.168.3.111 'python3 - <<"PY"
import json
from pathlib import Path
Path("/data/roadscore/runtime.json").write_text(json.dumps(dict(identity="horizon_drive",musical=True,rolling=True,arrangement=True,drive_events=True,phrase_runway=True)))
PY'
for spec in "live_development ${ROADSCORE_CURVE_ROUTE##*/} 110 210" "live_curve ${ROADSCORE_CURVE_ROUTE##*/} 110 100" "live_arrival ${ROADSCORE_ARRIVAL_ROUTE##*/} 170 87" "other_route ${ROADSCORE_OTHER_ROUTE##*/} 100 60"; do
 read -r name route start duration <<< "$spec"
 test ! -e "results/dense/$name" || { echo "Preserving existing $name"; exit 1; }
 if test -d results/latest; then mv results/latest "results/dense/prior_latest_$(date +%s)"; fi
 ./run_roadscore_demo.sh "$route" "$start" "$duration"
 mv results/latest "results/dense/$name"
done
