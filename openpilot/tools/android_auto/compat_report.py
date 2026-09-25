#!/usr/bin/env python3
"""Summarize Android Auto session logs into a shareable compatibility report.

On the comma, with no arguments it reports the newest session:

  cd /data/openpilot
  PYTHONPATH=/data/openpilot /usr/local/venv/bin/python openpilot/tools/android_auto/compat_report.py
  ... compat_report.py --all                 # every kept session, newest first
  ... compat_report.py session-000012-*.jsonl --json
  ... compat_report.py --bundle /tmp/android_auto.zip  # logs, reports and settings in one zip

Logs pulled to another machine work too: pass their paths.
"""

import argparse
import json
import sys
from pathlib import Path

from openpilot.starpilot.system.android_auto import compat_report


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("logs", nargs="*", type=Path, help="session logs (default: the newest on this comma)")
  parser.add_argument("--all", action="store_true", help="every kept session on this comma")
  parser.add_argument("--json", action="store_true", help="print the report as JSON")
  parser.add_argument("--bundle", type=Path, help="write a zip of every log, report and the settings here")
  args = parser.parse_args()

  if args.bundle:
    args.bundle.write_bytes(compat_report.bundle())
    print(f"wrote {args.bundle}")
    return 0
  logs = args.logs or (compat_report.session_logs() if args.all else compat_report.session_logs()[:1])
  if not logs:
    print("No Android Auto session logs found.", file=sys.stderr)
    return 1
  for path in logs:
    report = compat_report.summarize(compat_report.load_events(path))
    print(json.dumps({"log": path.name, **report}, indent=2, default=str) if args.json else compat_report.render_text(report, path.name))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
