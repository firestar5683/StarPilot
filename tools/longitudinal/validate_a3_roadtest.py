#!/usr/bin/env python3
"""Validate the A3 CE-off positive-demand throttle bypass on post-drive timelines.

This script deliberately analyses only the segments listed in a checkpoint's
checkpoint_transfer.csv, avoiding contamination from older routes that may
already live in the checkpoint directory.

It reconstructs the 250 ms model gas-probability throttle gate route-continuously
and asks the key road-test question:

  when the baseline model gate would be CLOSED, longitudinal is active, cruise
  demand is >= 7 km/h, and no hard protection context exists, did the installed
  A3 build keep allowThrottle=True?

It also reports any observed clean positive-demand false-coast frames and writes
frame-level evidence CSVs for review.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import io
import zipfile
from pathlib import Path
from statistics import median
from typing import Any

MODEL_DISABLE_THRESHOLD = 0.35
MODEL_ENABLE_THRESHOLD = 0.45
MODEL_CONFIRM_S = 0.25
MIN_ALLOW_THROTTLE_SPEED_MPS = 5.0
MIN_GAP_KPH = 7.0
COAST_TOL = 0.08


def fnum(value: Any, default: float | None = None) -> float | None:
  try:
    v = float(value)
    return v if math.isfinite(v) else default
  except (TypeError, ValueError):
    return default


def bval(value: Any, default: bool = False) -> bool:
  if value is None:
    return default
  s = str(value).strip().lower()
  if s in {"1", "true", "t", "yes", "y", "on"}:
    return True
  if s in {"0", "false", "f", "no", "n", "off", ""}:
    return False
  try:
    return float(s) != 0.0
  except ValueError:
    return default


def read_csv(path: Path) -> list[dict[str, str]]:
  with path.open("r", newline="", encoding="utf-8-sig") as f:
    return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  keys: list[str] = []
  seen: set[str] = set()
  for row in rows:
    for key in row:
      if key not in seen:
        seen.add(key)
        keys.append(key)
  with path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)


def default_output_root() -> Path:
  env = os.getenv("OPENPILOT_OUTPUT")
  if env:
    return Path(env)
  win = Path(r"D:\OpenPilot\Output")
  return win if win.exists() else Path("Output")


def route_and_index(segment: str) -> tuple[str, int]:
  parts = segment.rsplit("--", 1)
  if len(parts) != 2:
    return segment, 0
  try:
    idx = int(parts[1])
  except ValueError:
    idx = 0
  return parts[0], idx


def infer_step(rows: list[dict[str, str]]) -> float:
  ts = [fnum(r.get("t_rel_s")) for r in rows]
  vals = [t for t in ts if t is not None]
  ds = [b - a for a, b in zip(vals, vals[1:]) if 0.0 < b - a < 1.0]
  return median(ds) if ds else 0.05


def speed_gap_kph(row: dict[str, str]) -> float | None:
  gap = fnum(row.get("cruiseGapKph"))
  if gap is not None:
    return gap
  v_ego = fnum(row.get("vEgo"))
  sp = fnum(row.get("spVCruise"))
  if v_ego is not None and sp is not None:
    return (sp - v_ego) * 3.6
  vcruise = fnum(row.get("vCruise"))
  if v_ego is not None and vcruise is not None:
    return vcruise - v_ego * 3.6
  return None


def is_active(row: dict[str, str]) -> bool:
  return any((
    bval(row.get("longActive")),
    bval(row.get("spLongActive")),
    bval(row.get("active")),
    bval(row.get("spActive")),
  ))


def hard_protected(row: dict[str, str]) -> bool:
  return any((
    bval(row.get("brakePressed")),
    bval(row.get("spBrakePressed")),
    bval(row.get("spDisableThrottle")),
    bval(row.get("spPulseGlideCoasting")),
    bval(row.get("spTrackingLead")),
    bval(row.get("spForcingStop")),
    bval(row.get("shouldStop")),
    bval(row.get("hasLead")),
    bval(row.get("leadOneStatus")),
    bval(row.get("leadTwoStatus")),
    bval(row.get("stopSignConfirmed")),
    bval(row.get("spStopSignConfirmed")),
    bval(row.get("forceSlowDecel")),
    bval(row.get("forceDecel")),
  ))


def coast_match(row: dict[str, str]) -> bool:
  a = fnum(row.get("aTarget"))
  c = fnum(row.get("estimatedCoastAccel"))
  return a is not None and c is not None and abs(a - c) <= COAST_TOL


def frame_record(segment: str, row: dict[str, str], model_allow: bool, gap: float | None,
                 kind: str) -> dict[str, Any]:
  return {
    "kind": kind,
    "segment": segment,
    "t_rel_s": fnum(row.get("t_rel_s")),
    "active": is_active(row),
    "model_allow_sim": model_allow,
    "allowThrottle_actual": bval(row.get("allowThrottle"), default=True),
    "speed_gap_kph": gap,
    "vEgoKph": fnum(row.get("vEgoKph")),
    "vCruise": fnum(row.get("vCruise")),
    "modelGasPressProb1": fnum(row.get("modelGasPressProb1")),
    "aTarget": fnum(row.get("aTarget")),
    "aPlan0": fnum(row.get("aPlan0")),
    "estimatedCoastAccel": fnum(row.get("estimatedCoastAccel")),
    "spRedLight": bval(row.get("spRedLight")),
    "brakePressed": bval(row.get("brakePressed")),
    "hasLead": bval(row.get("hasLead")),
    "leadOneStatus": bval(row.get("leadOneStatus")),
    "leadTwoStatus": bval(row.get("leadTwoStatus")),
    "shouldStop": bval(row.get("shouldStop")),
    "spDisableThrottle": bval(row.get("spDisableThrottle")),
    "spTrackingLead": bval(row.get("spTrackingLead")),
    "spForcingStop": bval(row.get("spForcingStop")),
  }


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--output-root", type=Path, default=default_output_root())
  ap.add_argument("--checkpoint-dir", type=Path, required=True)
  ap.add_argument("--min-gap-kph", type=float, default=MIN_GAP_KPH)
  ap.add_argument("--confirm-s", type=float, default=MODEL_CONFIRM_S)
  args = ap.parse_args()

  transfer = args.checkpoint_dir / "checkpoint_transfer.csv"
  transfer_rows: list[dict[str, str]]

  if transfer.exists():
    transfer_rows = read_csv(transfer)
    transfer_source = str(transfer)
  else:
    recursive = list(args.checkpoint_dir.rglob("checkpoint_transfer.csv"))
    if recursive:
      transfer = recursive[0]
      transfer_rows = read_csv(transfer)
      transfer_source = str(transfer)
    else:
      bundles = sorted(args.checkpoint_dir.glob("*CHATGPT_BUNDLE.zip"))
      found = False
      transfer_rows = []
      transfer_source = ""
      for bundle in bundles:
        try:
          with zipfile.ZipFile(bundle) as zf:
            member = next(
              (name for name in zf.namelist() if Path(name).name == "checkpoint_transfer.csv"),
              None,
            )
            if member is None:
              continue
            text = zf.read(member).decode("utf-8-sig")
            transfer_rows = list(csv.DictReader(io.StringIO(text)))
            transfer_source = f"{bundle}!{member}"
            found = True
            break
        except (OSError, zipfile.BadZipFile, UnicodeDecodeError):
          continue
      if not found:
        raise SystemExit(
          f"Could not find checkpoint_transfer.csv under {args.checkpoint_dir} "
          f"or inside a *CHATGPT_BUNDLE.zip"
        )

  print(f"Transfer source                : {transfer_source}")
  segments = sorted({
    str(r.get("segment", "")).strip()
    for r in transfer_rows
    if str(r.get("status", "")).strip().upper() == "OK" and str(r.get("segment", "")).strip()
  })
  if not segments:
    raise SystemExit("No transferred OK segments found")

  by_route: dict[str, list[tuple[int, str]]] = {}
  for segment in segments:
    route, idx = route_and_index(segment)
    by_route.setdefault(route, []).append((idx, segment))
  for items in by_route.values():
    items.sort()

  opportunities: list[dict[str, Any]] = []
  violations: list[dict[str, Any]] = []
  protected_closed: list[dict[str, Any]] = []
  unprotected_gate_closed: list[dict[str, Any]] = []
  clean_false_coast: list[dict[str, Any]] = []

  total_rows = 0
  active_rows = 0
  actual_gate_false_active = 0
  model_gate_false_active = 0

  for route, items in sorted(by_route.items()):
    model_allow = True
    transition_t = 0.0

    for _, segment in items:
      path = args.output_root / "Segments" / segment / "timeline.csv"
      if not path.exists():
        print(f"[MISSING] {path}")
        continue

      rows = sorted(
        (r for r in read_csv(path) if fnum(r.get("t_rel_s")) is not None),
        key=lambda r: float(r["t_rel_s"]),
      )
      step = infer_step(rows)

      for row in rows:
        total_rows += 1
        active = is_active(row)
        if active:
          active_rows += 1

        v_ego = fnum(row.get("vEgo"), 0.0) or 0.0
        p = fnum(row.get("modelGasPressProb1"), 1.0)
        if p is None:
          p = 1.0

        if v_ego <= MIN_ALLOW_THROTTLE_SPEED_MPS:
          model_allow = True
          transition_t = 0.0
        else:
          requested = p <= MODEL_DISABLE_THRESHOLD if model_allow else p > MODEL_ENABLE_THRESHOLD
          if requested:
            transition_t += step
            if transition_t + 1e-6 >= args.confirm_s:
              model_allow = not model_allow
              transition_t = 0.0
          else:
            transition_t = 0.0

        actual_allow = bval(row.get("allowThrottle"), default=True)
        gap = speed_gap_kph(row)
        protected = hard_protected(row)

        if active and not actual_allow:
          actual_gate_false_active += 1
        if active and not model_allow:
          model_gate_false_active += 1

        opportunity = bool(
          active and
          not model_allow and
          not protected and
          gap is not None and
          gap >= args.min_gap_kph
        )
        if opportunity:
          rec = frame_record(segment, row, model_allow, gap, "a3_opportunity")
          opportunities.append(rec)
          if not actual_allow:
            violations.append({**rec, "kind": "A3_VIOLATION_allowThrottle_false"})

        if active and not model_allow and protected:
          rec = frame_record(segment, row, model_allow, gap, "protected_model_gate_closed")
          protected_closed.append(rec)

        if active and not model_allow and not protected:
          unprotected_gate_closed.append(
            frame_record(segment, row, model_allow, gap, "unprotected_model_gate_closed")
          )

        if (
          active and not protected and gap is not None and gap >= args.min_gap_kph and
          not actual_allow and coast_match(row)
        ):
          clean_false_coast.append(
            frame_record(segment, row, model_allow, gap, "clean_positive_demand_false_coast")
          )

  out_dir = args.checkpoint_dir / "a3_roadtest_validation"
  out_dir.mkdir(parents=True, exist_ok=True)
  write_csv(out_dir / "a3_opportunity_frames.csv", opportunities)
  write_csv(out_dir / "a3_violation_frames.csv", violations)
  write_csv(out_dir / "protected_model_gate_frames.csv", protected_closed)
  write_csv(out_dir / "unprotected_model_gate_frames.csv", unprotected_gate_closed)
  write_csv(out_dir / "clean_positive_demand_false_coast_frames.csv", clean_false_coast)

  opportunity_pass = len(opportunities) > 0 and len(violations) == 0
  no_false_coast_pass = len(clean_false_coast) == 0
  verdict = (
    "PASS_A3_EXERCISED"
    if opportunity_pass and no_false_coast_pass
    else "PASS_NO_FALSE_COAST_BUT_A3_NOT_EXERCISED"
    if len(opportunities) == 0 and no_false_coast_pass
    else "FAIL"
  )

  unprotected_gaps = sorted(
    float(r["speed_gap_kph"])
    for r in unprotected_gate_closed
    if r.get("speed_gap_kph") is not None
  )

  def percentile(values: list[float], pct: float) -> float | None:
    if not values:
      return None
    if len(values) == 1:
      return values[0]
    pos = (len(values) - 1) * pct
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
      return values[lo]
    frac = pos - lo
    return values[lo] * (1.0 - frac) + values[hi] * frac

  max_gap_record = None
  if unprotected_gate_closed:
    with_gap = [r for r in unprotected_gate_closed if r.get("speed_gap_kph") is not None]
    if with_gap:
      max_gap_record = max(with_gap, key=lambda r: float(r["speed_gap_kph"]))

  summary = {
    "verdict": verdict,
    "checkpoint_dir": str(args.checkpoint_dir),
    "output_root": str(args.output_root),
    "routes": sorted(by_route),
    "segments": len(segments),
    "total_rows": total_rows,
    "active_rows": active_rows,
    "model_gate_false_active_frames": model_gate_false_active,
    "actual_allowThrottle_false_active_frames": actual_gate_false_active,
    "a3_opportunity_frames": len(opportunities),
    "a3_opportunity_seconds_approx": round(len(opportunities) * 0.05, 3),
    "a3_violations": len(violations),
    "clean_positive_demand_false_coast_frames": len(clean_false_coast),
    "protected_model_gate_closed_frames": len(protected_closed),
    "unprotected_model_gate_closed_frames": len(unprotected_gate_closed),
    "unprotected_gate_speed_gap": {
      "max_kph": max(unprotected_gaps) if unprotected_gaps else None,
      "p95_kph": percentile(unprotected_gaps, 0.95),
      "p50_kph": percentile(unprotected_gaps, 0.50),
      "frames_gap_ge_1_kph": sum(g >= 1.0 for g in unprotected_gaps),
      "frames_gap_ge_3_kph": sum(g >= 3.0 for g in unprotected_gaps),
      "frames_gap_ge_5_kph": sum(g >= 5.0 for g in unprotected_gaps),
      "frames_gap_ge_7_kph": sum(g >= 7.0 for g in unprotected_gaps),
      "max_gap_segment": max_gap_record.get("segment") if max_gap_record else None,
      "max_gap_t_rel_s": max_gap_record.get("t_rel_s") if max_gap_record else None,
    },
    "criteria": {
      "min_speed_gap_kph": args.min_gap_kph,
      "model_disable_threshold": MODEL_DISABLE_THRESHOLD,
      "model_enable_threshold": MODEL_ENABLE_THRESHOLD,
      "confirm_s": args.confirm_s,
      "coast_tolerance_mps2": COAST_TOL,
    },
    "note": (
      "PASS_A3_EXERCISED means the post-drive corpus contained frames where the reconstructed "
      "baseline model gate would have been closed in clean positive-demand context, and the "
      "installed A3 build kept allowThrottle true on every such frame."
    ),
  }
  (out_dir / "a3_roadtest_summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
  )

  print("A3 ROAD-TEST VALIDATION")
  print("=" * 64)
  print(f"Routes                         : {len(by_route)}")
  print(f"Segments                       : {len(segments)}")
  print(f"Active rows                    : {active_rows}")
  print(f"Reconstructed gate-false rows : {model_gate_false_active}")
  print(f"A3 opportunity frames          : {len(opportunities)}")
  print(f"A3 violations                  : {len(violations)}")
  print(f"Clean positive-demand coast    : {len(clean_false_coast)}")
  print(f"Protected gate-closed frames   : {len(protected_closed)}")
  print(f"Unprotected gate-closed frames : {len(unprotected_gate_closed)}")
  print(f"Unprotected max speed gap      : {max(unprotected_gaps):.3f} km/h" if unprotected_gaps else "Unprotected max speed gap      : n/a")
  print(f"Unprotected p95 speed gap      : {percentile(unprotected_gaps, 0.95):.3f} km/h" if unprotected_gaps else "Unprotected p95 speed gap      : n/a")
  print(f"Gap >=1 / >=3 / >=5 / >=7     : {sum(g >= 1.0 for g in unprotected_gaps)} / {sum(g >= 3.0 for g in unprotected_gaps)} / {sum(g >= 5.0 for g in unprotected_gaps)} / {sum(g >= 7.0 for g in unprotected_gaps)}")
  if max_gap_record:
    print(f"Max-gap frame                  : {max_gap_record['segment']} @ {max_gap_record['t_rel_s']}s")
  print(f"VERDICT                        : {verdict}")
  print(f"Output                         : {out_dir}")
  return 0 if verdict != "FAIL" else 2


if __name__ == "__main__":
  raise SystemExit(main())
