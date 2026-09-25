"""Desktop-only FLM diagnostic report from explicitly selected closed rlogs."""

import argparse
from collections.abc import Callable, Sequence
from dataclasses import asdict
import json
from pathlib import Path
import sys

from openpilot.common.hardware import PC
from openpilot.starpilot.galaxy.drive_history import SEGMENT_NAME
from openpilot.starpilot.flm.local_logs import LocalLogUnavailable, read_closed_rlog
from openpilot.starpilot.flm.log_decode import LogDecodeError, decode_segment
from openpilot.starpilot.flm.offline import MAX_SEGMENTS, SegmentInput, analyze_segments


def analyze_local(root: Path, names: Sequence[str], *, cancelled: Callable[[], bool] = lambda: False) -> dict:
  """Process one bounded segment at a time; never return a partial report."""
  if not PC:
    raise ValueError("Use a desktop: device analysis needs a separate parked operation owner")
  if not 1 <= len(names) <= MAX_SEGMENTS or len(set(names)) != len(names):
    raise ValueError("Select one to five distinct closed segments")
  reports = []
  for name in names:
    source = read_closed_rlog(root, name, permitted=lambda: not cancelled())
    match = SEGMENT_NAME.fullmatch(name)
    assert match is not None
    events = decode_segment(source.compressed, source.codec, cancelled=cancelled)
    report = analyze_segments((SegmentInput(match.group("route"), int(match.group("number")), events),), cancelled=cancelled)
    reports.append({"source": {"segmentName": source.segment_name, "sha256": source.sha256,
                               "compressedBytes": source.size, "codec": source.codec},
                    "analysis": asdict(report.segments[0])})
    del events, source
  if cancelled():
    raise ValueError("Analysis cancelled")
  return {"schemaVersion": 1, "purpose": "offline_tracking_diagnostics", "segments": reports,
          "tuneRecommendation": None, "vehicleQualification": False}


def main(argv: Sequence[str] | None = None) -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--log-root", required=True, type=Path, help="Absolute local recording directory; no remote routes")
  parser.add_argument("--output", type=Path, help="Create a new JSON report file; never overwrite an existing file")
  parser.add_argument("segments", nargs="+", help="Closed segment directory names under --log-root (at most five)")
  args = parser.parse_args(argv)
  try:
    result = analyze_local(args.log_root, args.segments)
    payload = json.dumps(result, allow_nan=False, indent=2)
    if args.output is not None:
      with args.output.open("x", encoding="utf-8") as destination:
        destination.write(payload + "\n")
    else:
      print(payload)
  except (LocalLogUnavailable, LogDecodeError, OSError, ValueError, RuntimeError) as error:
    print(f"FLM analysis unavailable: {error}", file=sys.stderr)
    return 1
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
