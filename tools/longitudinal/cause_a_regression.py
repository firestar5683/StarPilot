#!/usr/bin/env python3
"""Build and evaluate StarPilot Cause-A longitudinal regression dataset.

This tool consumes timeline.csv outputs produced by Karl's OpenPilot log extractor
and the checkpoint-02 throttle scan. It never modifies source logs.

Outputs (default):
  D:/OpenPilot/Output/Regression/A/
    manifest.csv
    manifest.json
    criteria.json
    variant_summary.csv
    summary.txt
    T0004/timeline.csv
    ...

Cause A signature:
  gasPressProb[1] low long enough to close model_allow_throttle,
  no StarPilot disableThrottle/lead/stop/brake reason,
  aTarget is clamped near physical coast accel while longitudinal demand remains
  more positive.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

CASE_IDS = ("T0004", "T0008", "T0063", "T0064", "T0084", "T0132")
HISTORICAL_T0004_SEGMENT = "000002a8--80038629ff--5"
HISTORICAL_T0004_SEARCH = (330.0, 350.0)

MODEL_DISABLE_THRESHOLD = 0.35
MODEL_ENABLE_THRESHOLD = 0.45
MIN_ALLOW_THROTTLE_SPEED = 5.0
BASELINE_CONFIRM_S = 0.25
COAST_MATCH_TOLERANCE = 0.08
CLEAN_SPEED_GAP_KPH = 7.0
POSITIVE_DEMAND_MPS2 = 0.05
DEFAULT_PRE_S = 3.0
DEFAULT_POST_S = 3.0

BOOL_TRUE = {"true", "1", "yes", "on", "enabled", "active"}
BOOL_FALSE = {"false", "0", "no", "off", "disabled", "inactive", ""}


@dataclass
class Episode:
  case_id: str
  segment: str
  start_s: float
  end_s: float
  source: str


@dataclass
class VariantResult:
  case_id: str
  variant: str
  model_gate_false_frames: int
  effective_gate_false_frames: int
  clean_false_coast_frames: int
  clean_false_coast_seconds: float
  bypass_frames: int


def finite(v: Any) -> bool:
  try:
    return math.isfinite(float(v))
  except (TypeError, ValueError):
    return False


def fnum(v: Any, default: float | None = None) -> float | None:
  if not finite(v):
    return default
  return float(v)


def bval(v: Any, default: bool = False) -> bool:
  if isinstance(v, bool):
    return v
  if v is None:
    return default
  if isinstance(v, (int, float)) and finite(v):
    return float(v) != 0.0
  s = str(v).strip().lower()
  if s in BOOL_TRUE:
    return True
  if s in BOOL_FALSE:
    return False
  return default


def safe_mean(values: Iterable[Any]) -> float | None:
  vals = [float(v) for v in values if finite(v)]
  return mean(vals) if vals else None


def safe_min(values: Iterable[Any]) -> float | None:
  vals = [float(v) for v in values if finite(v)]
  return min(vals) if vals else None


def safe_max(values: Iterable[Any]) -> float | None:
  vals = [float(v) for v in values if finite(v)]
  return max(vals) if vals else None


def ratio(rows: list[dict[str, str]], col: str) -> float:
  if not rows:
    return 0.0
  return sum(1 for r in rows if bval(r.get(col))) / len(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
  with path.open("r", newline="", encoding="utf-8-sig") as f:
    return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  if fieldnames is None:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
      for k in row:
        if k not in seen:
          seen.add(k)
          keys.append(k)
    fieldnames = keys
  with path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)


def default_output_root() -> Path:
  env = os.getenv("OPENPILOT_OUTPUT")
  if env:
    return Path(env)
  win = Path(r"D:\OpenPilot\Output")
  if win.exists():
    return win
  return Path("Output")


def candidate_episode_csvs(output_root: Path) -> list[Path]:
  names = [
    output_root / "Analysis" / "ThrottleScan" / "checkpoint02_candidates_full.csv",
    output_root / "Analysis" / "ThrottleScan" / "checkpoint02_throttle_block_episodes.csv",
    output_root / "Analysis" / "ThrottleScan" / "throttle_block_episodes.csv",
    output_root / "Analysis" / "ThrottleScan" / "throttle_block_candidates.csv",
    output_root / "Analysis" / "checkpoint02_candidates_full.csv",
    output_root / "checkpoint02_candidates_full.csv",
  ]
  return [p for p in names if p.exists()]


def parse_episode_row(row: dict[str, str], source: Path) -> Episode | None:
  case_id = (row.get("episode_id") or row.get("case_id") or row.get("id") or "").strip()
  segment = (row.get("segment") or row.get("segment_id") or "").strip()
  start_s = fnum(row.get("start_s") or row.get("event_start_s") or row.get("start"))
  end_s = fnum(row.get("end_s") or row.get("event_end_s") or row.get("end"))
  if not case_id or not segment or start_s is None:
    return None
  if end_s is None:
    end_s = start_s
  return Episode(case_id, segment, start_s, end_s, str(source))


def find_episode_table(output_root: Path, explicit: Path | None) -> tuple[Path | None, dict[str, Episode]]:
  candidates = [explicit] if explicit else candidate_episode_csvs(output_root)
  candidates = [p for p in candidates if p and p.exists()]
  best_path: Path | None = None
  best: dict[str, Episode] = {}
  for path in candidates:
    found: dict[str, Episode] = {}
    try:
      for row in read_csv(path):
        ep = parse_episode_row(row, path)
        if ep:
          found[ep.case_id] = ep
    except Exception:
      continue
    hits = sum(1 for cid in CASE_IDS if cid in found)
    best_hits = sum(1 for cid in CASE_IDS if cid in best)
    if hits > best_hits:
      best_path, best = path, found
  return best_path, best


def timeline_path(output_root: Path, segment: str) -> Path:
  return output_root / "Segments" / segment / "timeline.csv"


def infer_step(rows: list[dict[str, str]]) -> float:
  ts = [float(r["t_rel_s"]) for r in rows if finite(r.get("t_rel_s"))]
  ds = [b - a for a, b in zip(ts, ts[1:]) if 0 < b - a < 1.0]
  return median(ds) if ds else 0.05


def speed_gap_kph(row: dict[str, str]) -> float | None:
  if finite(row.get("cruiseGapKph")):
    return float(row["cruiseGapKph"])
  v_ego = fnum(row.get("vEgo"))
  sp = fnum(row.get("spVCruise"))
  if v_ego is not None and sp is not None:
    return (sp - v_ego) * 3.6
  vcruise = fnum(row.get("vCruise"))
  if v_ego is not None and vcruise is not None:
    return vcruise - v_ego * 3.6
  return None


def clean_context(row: dict[str, str]) -> bool:
  return not any((
    bval(row.get("brakePressed")),
    bval(row.get("spDisableThrottle")),
    bval(row.get("spPulseGlideCoasting")),
    bval(row.get("spTrackingLead")),
    bval(row.get("spForcingStop")),
    bval(row.get("spRedLight")),
    bval(row.get("shouldStop")),
    bval(row.get("hasLead")),
    bval(row.get("leadOneStatus")),
  ))


def coast_match(row: dict[str, str]) -> bool:
  a_target = fnum(row.get("aTarget"))
  coast = fnum(row.get("estimatedCoastAccel"))
  return a_target is not None and coast is not None and abs(a_target - coast) <= COAST_MATCH_TOLERANCE


def positive_demand(row: dict[str, str]) -> bool:
  # aPlan0 is the closest extracted proxy for the planner/MPC request. If it is
  # absent, a large positive cruise speed deficit is a conservative fallback.
  a_plan = fnum(row.get("aPlan0"))
  if a_plan is not None:
    return a_plan > POSITIVE_DEMAND_MPS2
  gap = speed_gap_kph(row)
  return gap is not None and gap >= CLEAN_SPEED_GAP_KPH


def contiguous_false_groups(rows: list[dict[str, str]]) -> list[tuple[int, int]]:
  step = infer_step(rows)
  join_gap = max(0.12, step * 2.2)
  groups: list[list[int]] = []
  prev_i: int | None = None
  prev_t: float | None = None
  for i, row in enumerate(rows):
    if bval(row.get("allowThrottle"), default=True):
      continue
    t = fnum(row.get("t_rel_s"))
    if t is None:
      continue
    if prev_i is None or prev_t is None or t - prev_t > join_gap + 1e-9:
      groups.append([i])
    else:
      groups[-1].append(i)
    prev_i, prev_t = i, t
  return [(g[0], g[-1]) for g in groups]


def discover_t0004(output_root: Path) -> Episode | None:
  path = timeline_path(output_root, HISTORICAL_T0004_SEGMENT)
  if not path.exists():
    return None
  rows = [r for r in read_csv(path) if finite(r.get("t_rel_s"))]
  lo, hi = HISTORICAL_T0004_SEARCH
  best: tuple[float, float, float] | None = None
  for s, e in contiguous_false_groups(rows):
    start = float(rows[s]["t_rel_s"])
    end = float(rows[e]["t_rel_s"])
    if end < lo or start > hi:
      continue
    frame = rows[s:e + 1]
    low_prob = any(finite(r.get("modelGasPressProb1")) and float(r["modelGasPressProb1"]) <= MODEL_DISABLE_THRESHOLD for r in frame)
    clean_ratio = sum(clean_context(r) for r in frame) / max(len(frame), 1)
    coast_ratio = sum(coast_match(r) for r in frame) / max(len(frame), 1)
    demand_ratio = sum(positive_demand(r) for r in frame) / max(len(frame), 1)
    if not low_prob or clean_ratio < 0.8:
      continue
    score = coast_ratio + demand_ratio - abs(((start + end) / 2.0) - 339.5) / 100.0
    if best is None or score > best[0]:
      best = (score, start, end)
  if best is None:
    return None
  return Episode("T0004", HISTORICAL_T0004_SEGMENT, best[1], best[2], "auto-discovered historical timeline")


def enumerate_timeline_episodes(output_root: Path) -> dict[str, Episode]:
  """Fallback reconstruction of scanner episode IDs from all extracted timelines."""
  episodes: list[Episode] = []
  for path in sorted((output_root / "Segments").glob("*/timeline.csv")):
    try:
      rows = [r for r in read_csv(path) if finite(r.get("t_rel_s"))]
    except Exception:
      continue
    step = infer_step(rows)
    for s, e in contiguous_false_groups(rows):
      start = float(rows[s]["t_rel_s"])
      end = float(rows[e]["t_rel_s"])
      duration = end - start + step
      if duration + 1e-9 < 0.20:
        continue
      episodes.append(Episode("", path.parent.name, start, end, "fallback timeline enumeration"))
  def key(ep: Episode):
    parts = ep.segment.rsplit("--", 1)
    route = parts[0]
    try:
      idx = int(parts[1])
    except (IndexError, ValueError):
      idx = 10**9
    return route, idx, ep.start_s
  episodes.sort(key=key)
  return {f"T{i:04d}": Episode(f"T{i:04d}", ep.segment, ep.start_s, ep.end_s, ep.source)
          for i, ep in enumerate(episodes, 1)}


def resolve_episodes(output_root: Path, explicit_csv: Path | None) -> tuple[dict[str, Episode], list[str]]:
  notes: list[str] = []
  table_path, table = find_episode_table(output_root, explicit_csv)
  if table_path:
    notes.append(f"episode table: {table_path}")
  resolved = {cid: table[cid] for cid in CASE_IDS if cid in table}

  if "T0004" not in resolved:
    hist = discover_t0004(output_root)
    if hist:
      resolved["T0004"] = hist
      notes.append("T0004 auto-discovered in historical segment")

  missing = [cid for cid in CASE_IDS if cid not in resolved]
  if missing:
    fallback = enumerate_timeline_episodes(output_root)
    for cid in missing:
      if cid in fallback:
        resolved[cid] = fallback[cid]
        notes.append(f"{cid} resolved by fallback episode enumeration")

  return resolved, notes


def select_window(rows: list[dict[str, str]], start_s: float, end_s: float, pre: float, post: float) -> list[dict[str, str]]:
  lo, hi = start_s - pre, end_s + post
  return [r for r in rows if finite(r.get("t_rel_s")) and lo <= float(r["t_rel_s"]) <= hi]


def event_rows(rows: list[dict[str, str]], start_s: float, end_s: float) -> list[dict[str, str]]:
  return [r for r in rows if finite(r.get("t_rel_s")) and start_s <= float(r["t_rel_s"]) <= end_s]


def episode_metrics(ep: Episode, rows: list[dict[str, str]], step: float) -> dict[str, Any]:
  frame = event_rows(rows, ep.start_s, ep.end_s)
  gas = [r.get("modelGasPressProb1") for r in frame]
  at = [r.get("aTarget") for r in frame]
  ap = [r.get("aPlan0") for r in frame]
  coast = [r.get("estimatedCoastAccel") for r in frame]
  gaps = [speed_gap_kph(r) for r in frame]
  clean_ratio = sum(clean_context(r) for r in frame) / max(len(frame), 1)
  coast_ratio = sum(coast_match(r) for r in frame) / max(len(frame), 1)
  demand_ratio = sum(positive_demand(r) for r in frame) / max(len(frame), 1)
  gas_min = safe_min(gas)
  cause_a = (
    gas_min is not None and gas_min <= MODEL_DISABLE_THRESHOLD and
    clean_ratio >= 0.80 and coast_ratio >= 0.50 and demand_ratio >= 0.20
  )
  return {
    "case_id": ep.case_id,
    "segment": ep.segment,
    "event_start_s": round(ep.start_s, 3),
    "event_end_s": round(ep.end_s, 3),
    "event_duration_s": round(ep.end_s - ep.start_s + step, 3),
    "resolution_source": ep.source,
    "rows": len(frame),
    "gasPressProb_min": gas_min,
    "gasPressProb_mean": safe_mean(gas),
    "aTarget_min_mps2": safe_min(at),
    "aTarget_mean_mps2": safe_mean(at),
    "aPlan0_max_mps2": safe_max(ap),
    "aPlan0_mean_mps2": safe_mean(ap),
    "estimatedCoastAccel_mean_mps2": safe_mean(coast),
    "speed_gap_max_kph": safe_max(gaps),
    "clean_context_ratio": round(clean_ratio, 4),
    "coast_match_ratio": round(coast_ratio, 4),
    "positive_demand_ratio": round(demand_ratio, 4),
    "brake_pressed_ratio": round(ratio(frame, "brakePressed"), 4),
    "lead_ratio": round(max(ratio(frame, "hasLead"), ratio(frame, "leadOneStatus")), 4),
    "should_stop_ratio": round(ratio(frame, "shouldStop"), 4),
    "sp_disable_throttle_ratio": round(ratio(frame, "spDisableThrottle"), 4),
    "sp_forcing_stop_ratio": round(ratio(frame, "spForcingStop"), 4),
    "sp_red_light_ratio": round(ratio(frame, "spRedLight"), 4),
    "baseline_signature_pass": cause_a,
  }


def simulate_variant(rows: list[dict[str, str]], ep: Episode, name: str, confirm_s: float,
                     contextual_bypass: bool = False) -> VariantResult:
  step = infer_step(rows)
  model_allow = True
  transition_t = 0.0
  model_false = 0
  effective_false = 0
  clean_false = 0
  bypass_frames = 0

  for row in rows:
    v_ego = fnum(row.get("vEgo"), 0.0) or 0.0
    p = fnum(row.get("modelGasPressProb1"), 1.0)
    if p is None:
      p = 1.0

    if v_ego <= MIN_ALLOW_THROTTLE_SPEED:
      model_allow = True
      transition_t = 0.0
    else:
      requested = p <= MODEL_DISABLE_THRESHOLD if model_allow else p > MODEL_ENABLE_THRESHOLD
      if requested:
        transition_t += step
        if transition_t + 1e-6 >= confirm_s:
          model_allow = not model_allow
          transition_t = 0.0
      else:
        transition_t = 0.0

    model_effective = model_allow
    if not model_effective:
      model_false += 1

    bypass = False
    if contextual_bypass and not model_effective and not bval(row.get("spDisableThrottle")):
      gap = speed_gap_kph(row)
      bypass = bool(
        clean_context(row) and positive_demand(row) and
        gap is not None and gap >= CLEAN_SPEED_GAP_KPH
      )
      if bypass:
        bypass_frames += 1

    effective = (model_effective or bypass) and not bval(row.get("spDisableThrottle"))
    if not effective:
      effective_false += 1

    if (
      not effective and clean_context(row) and positive_demand(row) and
      coast_match(row)
    ):
      clean_false += 1

  return VariantResult(
    case_id=ep.case_id,
    variant=name,
    model_gate_false_frames=model_false,
    effective_gate_false_frames=effective_false,
    clean_false_coast_frames=clean_false,
    clean_false_coast_seconds=round(clean_false * step, 3),
    bypass_frames=bypass_frames,
  )


def criteria() -> dict[str, Any]:
  return {
    "dataset": "Cause A",
    "cases": list(CASE_IDS),
    "baseline_signature": {
      "gasPressProb_min_lte": MODEL_DISABLE_THRESHOLD,
      "clean_context_ratio_gte": 0.80,
      "coast_match_tolerance_mps2": COAST_MATCH_TOLERANCE,
      "coast_match_ratio_gte": 0.50,
      "positive_demand_ratio_gte": 0.20,
    },
    "patch_pass": {
      "primary": "reduce clean_false_coast_seconds versus baseline on every resolved Cause-A case",
      "must_preserve": [
        "explicit StarPilot disableThrottle",
        "driver brake",
        "lead/stop/forcingStop/redLight protections",
        "physical acceleration/deceleration limits",
      ],
      "final_selection_requires_negative_controls": True,
    },
    "variants": {
      "baseline_250ms": {"confirm_s": 0.25},
      "confirm_500ms": {"confirm_s": 0.50},
      "confirm_750ms": {"confirm_s": 0.75},
      "context_bypass_250ms": {
        "confirm_s": 0.25,
        "speed_gap_kph_gte": CLEAN_SPEED_GAP_KPH,
        "positive_demand_mps2_gt": POSITIVE_DEMAND_MPS2,
        "requires_clean_context": True,
      },
    },
  }


def main() -> int:
  p = argparse.ArgumentParser(description="Build/evaluate StarPilot Cause-A regression dataset")
  p.add_argument("--output-root", type=Path, default=default_output_root())
  p.add_argument("--episodes-csv", type=Path, default=None)
  p.add_argument("--dataset-dir", type=Path, default=None)
  p.add_argument("--pre", type=float, default=DEFAULT_PRE_S)
  p.add_argument("--post", type=float, default=DEFAULT_POST_S)
  args = p.parse_args()

  output_root: Path = args.output_root
  dataset_dir = args.dataset_dir or output_root / "Regression" / "A"
  dataset_dir.mkdir(parents=True, exist_ok=True)

  resolved, notes = resolve_episodes(output_root, args.episodes_csv)
  missing = [cid for cid in CASE_IDS if cid not in resolved]

  manifest: list[dict[str, Any]] = []
  variants: list[dict[str, Any]] = []

  for cid in CASE_IDS:
    ep = resolved.get(cid)
    if ep is None:
      manifest.append({"case_id": cid, "status": "UNRESOLVED"})
      continue
    src = timeline_path(output_root, ep.segment)
    if not src.exists():
      manifest.append({
        "case_id": cid, "segment": ep.segment, "status": "TIMELINE_MISSING",
        "source_timeline": str(src),
      })
      continue

    all_rows = read_csv(src)
    all_rows = sorted((r for r in all_rows if finite(r.get("t_rel_s"))), key=lambda r: float(r["t_rel_s"]))
    step = infer_step(all_rows)
    window = select_window(all_rows, ep.start_s, ep.end_s, args.pre, args.post)
    case_dir = dataset_dir / cid
    case_dir.mkdir(parents=True, exist_ok=True)
    write_csv(case_dir / "timeline.csv", window)

    metrics = episode_metrics(ep, all_rows, step)
    metrics.update({
      "status": "OK",
      "source_timeline": str(src),
      "window_start_s": round(ep.start_s - args.pre, 3),
      "window_end_s": round(ep.end_s + args.post, 3),
      "timeline_hz": round(1.0 / step, 3) if step > 0 else None,
    })
    manifest.append(metrics)

    for name, confirm_s, bypass in (
      ("baseline_250ms", 0.25, False),
      ("confirm_500ms", 0.50, False),
      ("confirm_750ms", 0.75, False),
      ("context_bypass_250ms", 0.25, True),
    ):
      result = simulate_variant(window, ep, name, confirm_s, contextual_bypass=bypass)
      variants.append(asdict(result))

  write_csv(dataset_dir / "manifest.csv", manifest)
  (dataset_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
  (dataset_dir / "criteria.json").write_text(json.dumps(criteria(), indent=2, ensure_ascii=False), encoding="utf-8")
  write_csv(dataset_dir / "variant_summary.csv", variants)

  lines = [
    "StarPilot Cause-A regression dataset",
    "==================================",
    f"Output root : {output_root}",
    f"Dataset dir : {dataset_dir}",
    f"Resolved    : {len(CASE_IDS) - len(missing)}/{len(CASE_IDS)}",
  ]
  lines.extend(f"Note        : {n}" for n in notes)
  if missing:
    lines.append("Missing     : " + ", ".join(missing))
  lines += ["", "Cases:"]
  for row in manifest:
    lines.append(
      f"  {row.get('case_id')}: {row.get('status')} "
      f"segment={row.get('segment', '-')} "
      f"event={row.get('event_start_s', '-')}->{row.get('event_end_s', '-')} "
      f"signature={row.get('baseline_signature_pass', '-')}"
    )
  lines += ["", "Variant clean false-coast seconds:"]
  for cid in CASE_IDS:
    case_results = [r for r in variants if r["case_id"] == cid]
    if case_results:
      lines.append("  " + cid + ": " + ", ".join(
        f"{r['variant']}={r['clean_false_coast_seconds']:.3f}s" for r in case_results
      ))
  lines += [
    "",
    "Final patch selection is intentionally blocked until negative-control regression",
    "is run against non-Cause-A lead/stop/brake/disableThrottle episodes.",
  ]
  (dataset_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
  print("\n".join(lines))
  return 2 if missing else 0


if __name__ == "__main__":
  raise SystemExit(main())
