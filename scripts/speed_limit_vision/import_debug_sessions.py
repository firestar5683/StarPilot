#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import shutil

from pathlib import Path

if __package__ in (None, ""):
  import sys
  sys.path.insert(0, str(Path(__file__).resolve().parent))
  from common import (  # type: ignore
    BOOKMARK_MANIFEST_FIELDS,
    DEFAULT_DEBUG_BASE,
    DEFAULT_WORKSPACE,
    ensure_dir,
    latest_debug_sessions,
    read_jsonl,
    resolve_workspace,
    write_csv_header,
  )
else:
  from .common import (
    BOOKMARK_MANIFEST_FIELDS,
    DEFAULT_DEBUG_BASE,
    DEFAULT_WORKSPACE,
    ensure_dir,
    latest_debug_sessions,
    read_jsonl,
    resolve_workspace,
    write_csv_header,
  )


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Import speed-limit debug sessions into a training workspace manifest.")
  parser.add_argument("sessions", nargs="*", help="Session ids or full session paths. Defaults to the latest session under --debug-base.")
  parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE, help="Training workspace root.")
  parser.add_argument("--debug-base", type=Path, default=DEFAULT_DEBUG_BASE, help="Root directory containing vision debug sessions.")
  parser.add_argument("--latest", type=int, default=1, help="How many latest sessions to import when no session ids are provided.")
  parser.add_argument("--mode", choices=("symlink", "copy"), default="symlink", help="How to place snapshots into the workspace review/images directory.")
  parser.add_argument("--force", action="store_true", help="Overwrite snapshot links/files if they already exist.")
  parser.add_argument("--events", nargs="+", default=["bookmark", "auto_bookmark", "training_candidate", "map_transition_miss", "publish", "candidate"], help="Event types to include in the manifest.")
  return parser.parse_args()


def resolve_sessions(session_args: list[str], debug_base: Path, latest_count: int) -> list[Path]:
  if session_args:
    resolved = []
    for session_arg in session_args:
      candidate = Path(session_arg).expanduser()
      if candidate.is_dir():
        resolved.append(candidate.resolve())
        continue
      candidate = (debug_base / session_arg).resolve()
      if candidate.is_dir():
        resolved.append(candidate)
        continue
      raise FileNotFoundError(f"Debug session not found: {session_arg}")
    return resolved

  latest = latest_debug_sessions(debug_base, latest_count)
  if not latest:
    raise FileNotFoundError(f"No debug sessions found in {debug_base}")
  return latest


def load_existing_rows(manifest_path: Path) -> dict[str, dict[str, str]]:
  if not manifest_path.exists():
    return {}

  with manifest_path.open("r", encoding="utf-8", newline="") as manifest_file:
    reader = csv.DictReader(manifest_file)
    return {row["record_key"]: row for row in reader if row.get("record_key")}


def stage_snapshot(source_path: Path, dest_path: Path, mode: str, force: bool) -> None:
  ensure_dir(dest_path.parent)
  if dest_path.exists() or dest_path.is_symlink():
    if not force:
      return
    if dest_path.is_dir():
      shutil.rmtree(dest_path)
    else:
      dest_path.unlink()

  if mode == "copy":
    shutil.copy2(source_path, dest_path)
  else:
    dest_path.symlink_to(source_path)


def event_row(event: dict, session_id: str, session_path: Path, event_index: int, snapshot_path: str) -> dict[str, str]:
  return {
    "record_key": f"{session_id}:{event_index}",
    "session_id": session_id,
    "event_index": str(event_index),
    "event": str(event.get("event") or ""),
    "session_seconds": str(event.get("sessionSeconds") or ""),
    "wall_time": str(event.get("wallTime") or ""),
    "road_name": str(event.get("roadName") or ""),
    "stream": str(event.get("stream") or ""),
    "status": str(event.get("status") or ""),
    "candidate_speed_limit_mph": str(event.get("candidateSpeedLimitMph") or ""),
    "candidate_confidence": str(event.get("candidateConfidence") or ""),
    "speed_limit_mph": str(event.get("speedLimitMph") or ""),
    "confidence": str(event.get("confidence") or ""),
    "source_confidence": str(event.get("sourceConfidence") or ""),
    "source_event": str(event.get("sourceEvent") or ""),
    "published_speed_limit_mph": str(event.get("publishedSpeedLimitMph") or ""),
    "published_confidence": str(event.get("publishedConfidence") or ""),
    "map_source": str(event.get("mapSource") or ""),
    "map_current_speed_limit_mph": str(event.get("mapCurrentSpeedLimitMph") or ""),
    "map_next_speed_limit_mph": str(event.get("mapNextSpeedLimitMph") or ""),
    "map_next_speed_limit_distance_m": str(event.get("mapNextSpeedLimitDistanceM") or ""),
    "map_expected_speed_limit_mph": str(event.get("mapExpectedSpeedLimitMph") or ""),
    "map_relation": str(event.get("mapRelation") or ""),
    "previous_map_speed_limit_mph": str(event.get("previousMapSpeedLimitMph") or ""),
    "review_bucket": str(event.get("reviewBucket") or ""),
    "bookmark_count": str(event.get("bookmarkCount") or ""),
    "snapshot_path": snapshot_path,
    "source_session_path": str(session_path),
  }


def main() -> int:
  args = parse_args()
  workspace = resolve_workspace(args.workspace)
  review_image_dir = ensure_dir(workspace / "review" / "images")
  manifest_path = workspace / "review" / "bookmarks.csv"
  write_csv_header(manifest_path, BOOKMARK_MANIFEST_FIELDS)

  existing_rows = load_existing_rows(manifest_path)
  sessions = resolve_sessions(args.sessions, args.debug_base.expanduser().resolve(), args.latest)
  selected_events = set(args.events)

  for session_path in sessions:
    events_path = session_path / "events.jsonl"
    if not events_path.is_file():
      continue

    session_id = session_path.name
    for event_index, event in enumerate(read_jsonl(events_path)):
      event_type = str(event.get("event") or "")
      if event_type not in selected_events:
        continue

      snapshot_rel_path = ""
      snapshot_name = event.get("snapshot")
      if snapshot_name:
        source_snapshot = session_path / str(snapshot_name)
        if source_snapshot.is_file():
          dest_name = f"{session_id}_{event_index:04d}_{event_type}{source_snapshot.suffix.lower()}"
          dest_snapshot = review_image_dir / dest_name
          stage_snapshot(source_snapshot, dest_snapshot, args.mode, args.force)
          snapshot_rel_path = str(dest_snapshot.relative_to(workspace))

      row = event_row(event, session_id, session_path, event_index, snapshot_rel_path)
      existing_rows[row["record_key"]] = row

  with manifest_path.open("w", encoding="utf-8", newline="") as manifest_file:
    writer = csv.DictWriter(manifest_file, fieldnames=BOOKMARK_MANIFEST_FIELDS)
    writer.writeheader()
    for row in sorted(existing_rows.values(), key=lambda entry: (entry["session_id"], int(entry["event_index"]))):
      writer.writerow(row)

  print(f"Imported {len(sessions)} debug session(s) into {manifest_path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
