#!/usr/bin/env python3
"""Evaluate whether retained EV9 data can reproduce the stock BSM lamps.

This is an offline, route-held-out analysis.  It decodes the 0x235--0x248
object payload, including the metadata fields documented by the public Zendar
front-camera DBC, constructs slot-independent spatial and ID-persistence
features, and reports precision/recall separately for the left and right stock
0x1BA BCW lamp states.

Example (run in an environment containing numpy and scikit-learn):

  PYTHONPATH=/tmp/ev9ml .venv/bin/python \
    tools/ev9_longitudinal/analyze_ev9_bsm_fusion.py \
    --can-npz /tmp/ev9_bsm_stock.npz \
    --model-npz /tmp/ev9_bsm_model_geometry.npz

The Zendar metadata layout is evidence for field decoding, not proof that its
front-camera object policy equals the EV9 ADAS ECU's BSM decision policy.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import precision_recall_curve

from openpilot.tools.ev9_longitudinal.evaluate_ev9_bsm_heuristics import evaluate


@dataclass
class Objects:
  quality: np.ndarray
  age: np.ndarray
  moving: np.ndarray
  object_id: np.ndarray
  width: np.ndarray
  classification: np.ndarray
  x: np.ndarray
  y: np.ndarray
  vx: np.ndarray
  vy: np.ndarray
  ax: np.ndarray
  absolute_vx: np.ndarray
  sync: np.ndarray
  valid: np.ndarray


def decode_object_group(raw: np.ndarray, second: bool) -> Objects:
  """Decode one of the two Zendar-layout object halves in a 32-byte frame.

  ``raw`` contains bytes 3..31 because bytes 0..2 (CRC/counter) were omitted
  when the source NPZ was built. In the observed EV9 corpus, second-half
  header bits can be nonzero but its kinematics remain invalid sentinels;
  decoding it makes that negative result explicit.
  """
  offset = 16 if second else 0
  byte = lambda n: raw[:, :, offset + n].astype(np.int32)
  quality = byte(0) & 0x7f
  age = byte(1)
  moving = byte(2) & 0xf
  object_id = (byte(2) >> 4) | ((byte(3) & 0x7) << 4)
  width = ((byte(3) >> 4) | ((byte(4) & 0x7) << 4)) * 0.05
  classification = (byte(4) >> 4) & 0x7
  x = (byte(5) | ((byte(6) & 0x1f) << 8)) * 0.05
  y_raw = (byte(6) >> 6) | (byte(7) << 2) | ((byte(8) & 0x3) << 10)
  y = y_raw * 0.05 - 102.4
  vx = ((byte(8) >> 3) | ((byte(9) & 0x7f) << 5)) * 0.05 - 100.0
  vy = (byte(10) | ((byte(11) & 0x3) << 8)) * 0.05 - 25.0
  ax_raw = (byte(11) >> 3) | ((byte(12) & 0xf) << 5)
  ax = np.where(ax_raw >= 256, ax_raw - 512, ax_raw) * 0.05
  sync = byte(12) >> 4
  if second:
    # Object two's absolute velocity precedes its quality field.
    absolute_vx = ((raw[:, :, 14].astype(np.int32) >> 4) |
                   (raw[:, :, 15].astype(np.int32) << 4)) * 0.05 - 102.4
  else:
    absolute_vx = (raw[:, :, 13].astype(np.int32) |
                   ((raw[:, :, 14].astype(np.int32) & 0xf) << 8)) * 0.05 - 102.4
  valid = ((quality > 0) & (object_id > 0) & (x > 0.2) & (x < 350.0) &
           (np.abs(y) < 60.0) & (vx > -99.0))
  return Objects(quality, age, moving, object_id, width, classification,
                 x, y, vx, vy, ax, absolute_vx, sync, valid)


def decode_objects(can: np.lib.npyio.NpzFile) -> Objects:
  names = can["features"]
  idx = np.flatnonzero(np.char.startswith(names, "corner"))
  raw = can["X"][:, idx].reshape(len(can["X"]), 20, 29)
  first = decode_object_group(raw, False)
  second = decode_object_group(raw, True)
  return Objects(*(np.concatenate((getattr(first, name), getattr(second, name)), axis=1)
                   for name in Objects.__dataclass_fields__))


def valid_lag_indices(routes: np.ndarray, segments: np.ndarray, lag: int) -> tuple[np.ndarray, np.ndarray]:
  dst = np.arange(lag, len(routes))
  src = dst - lag
  keep = (routes[dst] == routes[src]) & (segments[dst] == segments[src])
  return dst[keep], src[keep]


def sorted_snapshot(obj: Objects, side: int, top_k: int = 10) -> np.ndarray:
  sign = 1.0 if side == 0 else -1.0
  sy = sign * obj.y
  candidate = obj.valid & (sy > -2.0) & (sy < 40.0)
  # Put the nominal adjacent-lane region first, then distance and quality.
  risk = np.abs(sy - 3.2) + 0.025 * obj.x - 0.002 * obj.quality
  order = np.argsort(np.where(candidate, risk, 1e6), axis=1)[:, :top_k]
  take = lambda value: np.take_along_axis(value, order, axis=1)
  present = take(candidate)
  fields = (take(obj.quality) / 100.0, take(obj.age) / 255.0,
            take(obj.moving) / 15.0, take(obj.object_id) / 127.0,
            take(obj.width) / 6.35, take(obj.classification) / 7.0,
            take(obj.x) / 180.0, take(sy) / 40.0,
            take(obj.vx) / 100.0, take(sign * obj.vy) / 25.0,
            take(obj.ax) / 12.8, take(obj.absolute_vx) / 102.4,
            take(obj.sync) / 15.0, present.astype(np.float32))
  result = np.stack(fields, axis=2)
  result *= present[:, :, None]
  return result.reshape(len(obj.x), -1).astype(np.float32)


def spatial_aggregates(obj: Objects, side: int) -> np.ndarray:
  sign = 1.0 if side == 0 else -1.0
  sy = sign * obj.y
  x_edges = (5.0, 10.0, 20.0, 40.0, 80.0, 160.0)
  y_ranges = ((-2.0, 1.5), (0.0, 3.0), (1.5, 5.0), (3.0, 8.0),
              (5.0, 12.0), (8.0, 20.0), (0.0, 40.0))
  move_sets = (None, (3, 4, 5), (5,), (1, 2), (6, 7, 8), (0,))
  columns: list[np.ndarray] = []
  for xmax in x_edges:
    for ymin, ymax in y_ranges:
      region = obj.valid & (obj.x < xmax) & (sy >= ymin) & (sy < ymax)
      for states in move_sets:
        mask = region if states is None else region & np.isin(obj.moving, states)
        columns.append(mask.sum(axis=1).astype(np.float32) / 10.0)
      masked_x = np.where(region, obj.x, 999.0)
      columns.append(masked_x.min(axis=1).astype(np.float32) / 180.0)
      columns.append(np.where(region, obj.quality, 0).max(axis=1).astype(np.float32) / 100.0)
      columns.append(np.where(region, obj.age, 0).max(axis=1).astype(np.float32) / 255.0)
  return np.stack(columns, axis=1)


def id_persistence(obj: Objects, routes: np.ndarray, segments: np.ndarray,
                   side: int, lags=(1, 2, 5, 10, 20, 40)) -> np.ndarray:
  """Summarize how often current side objects existed under the same ID."""
  sign = 1.0 if side == 0 else -1.0
  side_now = obj.valid & (sign * obj.y > -2.0) & (sign * obj.y < 40.0)
  out = np.zeros((len(routes), len(lags) * 6), dtype=np.float32)
  for li, lag in enumerate(lags):
    dst, src = valid_lag_indices(routes, segments, lag)
    current_ids = obj.object_id[dst]
    prior_ids = obj.object_id[src]
    match = ((current_ids[:, :, None] == prior_ids[:, None, :]) &
             side_now[dst, :, None] & obj.valid[src, None, :])
    any_match = match.any(axis=2)
    # Position of the matching prior object. IDs should be unique, but max is
    # deterministic if malformed frames contain a duplicate.
    prior_x = np.max(np.where(match, obj.x[src, None, :], 0.0), axis=2)
    prior_y = np.max(np.where(match, sign * obj.y[src, None, :], -99.0), axis=2)
    denom = np.maximum(side_now[dst].sum(axis=1), 1)
    base = li * 6
    out[dst, base] = any_match.sum(axis=1) / denom
    out[dst, base + 1] = (any_match & (np.abs(obj.x[dst] - prior_x) < 5.0)).sum(axis=1) / denom
    out[dst, base + 2] = (any_match & (np.abs(sign * obj.y[dst] - prior_y) < 2.0)).sum(axis=1) / denom
    out[dst, base + 3] = np.max(np.where(any_match, obj.age[dst], 0), axis=1) / 255.0
    out[dst, base + 4] = np.max(np.where(any_match, obj.quality[dst], 0), axis=1) / 100.0
    out[dst, base + 5] = any_match.any(axis=1)
  return out


def lag_stack(current: np.ndarray, routes: np.ndarray, segments: np.ndarray,
              lags=(0, 1, 2, 5, 10, 20, 40, 50)) -> np.ndarray:
  pieces = []
  for lag in lags:
    shifted = np.zeros_like(current)
    if lag == 0:
      shifted = current
    else:
      dst, src = valid_lag_indices(routes, segments, lag)
      shifted[dst] = current[src]
    pieces.append(shifted)
  return np.concatenate(pieces, axis=1)


def build_features(can, obj: Objects, side: int, model_path: Path | None,
                   include_retained_raw: bool) -> np.ndarray:
  routes, segments = can["routes"], can["segs"]
  semantic = np.concatenate((sorted_snapshot(obj, side), spatial_aggregates(obj, side)), axis=1)
  parts = [lag_stack(semantic, routes, segments),
           id_persistence(obj, routes, segments, side),
           can["car"].astype(np.float32)]
  if include_retained_raw:
    # MRR35 and the retained 0x1E5/0x36A payloads were already tested alone;
    # include them here to test whether they add information conditionally on
    # the decoded corner objects. Avoid duplicating the 0x235 group.
    raw_idx = np.flatnonzero(~np.char.startswith(can["features"], "corner"))
    raw = can["X"][:, raw_idx].astype(np.float32) / 255.0
    parts.append(lag_stack(raw, routes, segments, (0, 5, 20)))
  if model_path is not None:
    model = np.load(model_path, allow_pickle=True)
    if not (np.array_equal(model["routes"], routes) and np.array_equal(model["segs"], segments) and
            np.array_equal(model["times"], can["times"])):
      raise RuntimeError("model geometry rows do not align with CAN NPZ")
    mx = np.nan_to_num(model["X"].astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    # Current geometry plus 0.5 s and 2 s context is enough to represent lane
    # curvature/change without allowing the model block to dominate memory.
    parts.append(lag_stack(mx, routes, segments, (0, 5, 20)))
  return np.concatenate(parts, axis=1)


def smooth_scores(scores: np.ndarray, routes: np.ndarray, segments: np.ndarray,
                  window: int, mode: str) -> np.ndarray:
  out = scores.copy()
  for route in np.unique(routes):
    for segment in np.unique(segments[routes == route]):
      idx = np.flatnonzero((routes == route) & (segments == segment))
      values = scores[idx]
      if mode == "max":
        out[idx] = [np.max(values[max(0, i - window + 1):i + 1]) for i in range(len(values))]
      elif mode == "mean":
        cs = np.r_[0.0, np.cumsum(values)]
        out[idx] = [(cs[i + 1] - cs[max(0, i - window + 1)]) /
                    (i + 1 - max(0, i - window + 1)) for i in range(len(values))]
  return out


def summarize(y: np.ndarray, scores: np.ndarray) -> dict[str, float]:
  precision, recall, thresholds = precision_recall_curve(y, scores)
  f1 = 2 * precision * recall / np.maximum(precision + recall, 1e-12)
  best = int(np.nanargmax(f1))
  recall95 = recall >= 0.95
  recall100 = recall >= 1.0 - 1e-12
  precision95 = precision >= 0.95
  result = {
    "best_f1": float(f1[best]), "best_precision": float(precision[best]),
    "best_recall": float(recall[best]),
    "threshold": float(thresholds[min(best, len(thresholds) - 1)]) if len(thresholds) else 1.0,
    "best_precision_at_recall95": float(np.max(precision[recall95])) if np.any(recall95) else 0.0,
    "best_precision_at_recall100": float(np.max(precision[recall100])) if np.any(recall100) else 0.0,
    "best_recall_at_precision95": float(np.max(recall[precision95])) if np.any(precision95) else 0.0,
  }
  result["meets_95_95"] = bool(np.any(recall95 & (precision >= 0.95)))
  return result


def full_episode_recall_threshold(y: np.ndarray, scores: np.ndarray,
                                  routes: np.ndarray, segments: np.ndarray) -> float:
  """Return the highest score threshold that touches every truth episode."""
  episode_maxima: list[float] = []
  for route, segment in np.unique(np.column_stack((routes, segments)), axis=0):
    idx = np.flatnonzero((routes == route) & (segments == segment))
    active = y[idx]
    starts = np.flatnonzero(active & ~np.r_[False, active[:-1]])
    ends = np.flatnonzero(active & ~np.r_[active[1:], False])
    episode_maxima.extend(float(np.max(scores[idx[start:end + 1]]))
                          for start, end in zip(starts, ends, strict=True))
  return min(episode_maxima) if episode_maxima else math.inf


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--can-npz", type=Path, required=True)
  parser.add_argument("--model-npz", type=Path)
  parser.add_argument("--include-retained-raw", action="store_true")
  parser.add_argument("--trees", type=int, default=180)
  args = parser.parse_args()
  can = np.load(args.can_npz, allow_pickle=True)
  obj = decode_objects(can)
  print("valid object count quantiles:", np.quantile(obj.valid.sum(axis=1), (0, .1, .5, .9, 1)))
  print("valid second objects:", int(obj.valid[:, 20:].sum()))

  for side, side_name in enumerate(("left", "right")):
    print(f"\n=== {side_name} ===")
    features = build_features(can, obj, side, args.model_npz, args.include_retained_raw)
    y_all = can["Y"][:, side].astype(bool)
    for holdout in np.unique(can["routes"]):
      test = can["routes"] == holdout
      train = ~test
      if y_all[test].sum() == 0 or y_all[train].sum() == 0:
        print(f"hold route {holdout}: skipped (no positives in train or test)")
        continue
      # Preserve every positive and sample three negatives per positive. This
      # keeps training tractable without changing full-holdout metrics.
      rng = np.random.default_rng(0xE9 + side * 10 + int(holdout))
      pos = np.flatnonzero(train & y_all)
      neg = np.flatnonzero(train & ~y_all)
      neg = rng.choice(neg, min(len(neg), 3 * len(pos)), replace=False)
      train_idx = np.r_[pos, neg]
      model = ExtraTreesClassifier(n_estimators=args.trees, max_depth=24, min_samples_leaf=4,
                                   max_features=0.3, class_weight="balanced", n_jobs=-1,
                                   random_state=0xE900 + side * 10 + int(holdout))
      model.fit(features[train_idx], y_all[train_idx])
      raw = model.predict_proba(features[test])[:, 1]
      tr, ts = can["routes"][test], can["segs"][test]
      variants = {"raw": raw}
      for window in (3, 5, 10, 20):
        variants[f"max_{window}"] = smooth_scores(raw, tr, ts, window, "max")
        variants[f"mean_{window}"] = smooth_scores(raw, tr, ts, window, "mean")
      reports = {name: summarize(y_all[test], score) for name, score in variants.items()}
      best_name = max(reports, key=lambda name: reports[name]["best_f1"])
      best = reports[best_name]
      episode_reports = {}
      for name, score in variants.items():
        threshold = full_episode_recall_threshold(y_all[test], score, tr, ts)
        prediction = np.zeros(len(y_all), dtype=bool)
        prediction[test] = score >= threshold
        metrics = evaluate(y_all, prediction, can, test)
        episode_reports[name] = (threshold, metrics)
      episode_name = max(episode_reports, key=lambda name: (
        episode_reports[name][1].episode_precision,
        -episode_reports[name][1].false_on_seconds,
        episode_reports[name][1].frame_precision,
      ))
      episode_threshold, episode_metrics = episode_reports[episode_name]
      report = f"hold route {int(holdout)} positives={int(y_all[test].sum())} "
      report += f"best={best_name}: F1={best['best_f1']:.3f}, P={best['best_precision']:.3f}, "
      report += f"R={best['best_recall']:.3f}, P@R>=.95={best['best_precision_at_recall95']:.3f}, "
      report += f"P@R=1={best['best_precision_at_recall100']:.3f}, "
      report += f"R@P>=.95={best['best_recall_at_precision95']:.3f}, meets95={best['meets_95_95']}"
      print(report)
      episode_report = f"  episode-recall=1 best={episode_name} threshold={episode_threshold:.4f}: "
      episode_report += f"episode P/R={episode_metrics.episode_precision:.3f}/{episode_metrics.episode_recall:.3f}, "
      episode_report += f"frame P/R={episode_metrics.frame_precision:.3f}/{episode_metrics.frame_recall:.3f}, "
      episode_report += f"false-on={episode_metrics.false_on_seconds:.1f}s, lag-med={episode_metrics.onset_lag_median_s:+.2f}s"
      print(episode_report)


if __name__ == "__main__":
  main()
