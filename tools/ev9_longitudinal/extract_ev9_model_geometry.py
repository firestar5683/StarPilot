#!/usr/bin/env python3
"""Align model/lane geometry with an EV9 BSM CAN sample dataset.

Run this with the StarPilot virtualenv (it needs pycapnp):

  .venv/bin/python tools/ev9_longitudinal/extract_ev9_model_geometry.py \
    --can-npz /tmp/ev9_bsm_stock.npz \
    --rlog-root /Users/brenrid/Code/EV9-Route-References/stock-rlogs \
    --output /tmp/ev9_bsm_model_geometry.npz

The output rows exactly match the input NPZ rows.  This is intentionally an
offline analysis tool; none of the features are used by vehicle control code.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from tools.lib.logreader import LogReader


PATH_IDXS = (0, 5, 10, 20, 32)


def padded(values, length: int, fill: float = 0.0) -> list[float]:
  out = [float(x) for x in list(values)[:length]]
  return out + [fill] * (length - len(out))


def indexed(values, idxs=PATH_IDXS, fill: float = 0.0) -> list[float]:
  vals = list(values)
  return [float(vals[i]) if i < len(vals) else fill for i in idxs]


def model_features(model) -> tuple[list[float], list[str]]:
  values: list[float] = []
  names: list[str] = []

  for axis in ("x", "y", "z"):
    values.extend(indexed(getattr(model.position, axis)))
    names.extend(f"path_{axis}_{i}" for i in PATH_IDXS)

  for axis in ("x", "y", "z"):
    values.extend(indexed(getattr(model.orientation, axis)))
    names.extend(f"orientation_{axis}_{i}" for i in PATH_IDXS)

  for axis in ("x", "y", "z"):
    values.extend(indexed(getattr(model.orientationRate, axis)))
    names.extend(f"orientation_rate_{axis}_{i}" for i in PATH_IDXS)

  for lane_idx, lane in enumerate(model.laneLines):
    values.extend(indexed(lane.y))
    names.extend(f"lane_{lane_idx}_y_{i}" for i in PATH_IDXS)

  lane_count = len(model.laneLines)
  values.extend(padded(model.laneLineProbs, lane_count))
  names.extend(f"lane_{i}_prob" for i in range(lane_count))
  values.extend(padded(model.laneLineStds, lane_count, 99.0))
  names.extend(f"lane_{i}_std" for i in range(lane_count))

  for edge_idx, edge in enumerate(model.roadEdges):
    values.extend(indexed(edge.y))
    names.extend(f"road_edge_{edge_idx}_y_{i}" for i in PATH_IDXS)
  edge_count = len(model.roadEdges)
  values.extend(padded(model.roadEdgeStds, edge_count, 99.0))
  names.extend(f"road_edge_{i}_std" for i in range(edge_count))

  values.extend(padded(model.meta.desireState, 8))
  names.extend(f"desire_state_{i}" for i in range(8))
  values.extend(padded(model.meta.desirePrediction, 32))
  names.extend(f"desire_prediction_{i}" for i in range(32))
  values.extend((float(model.meta.engagedProb),
                 float(model.meta.hardBrakePredicted),
                 float(model.meta.laneChangeState.raw),
                 float(model.meta.laneChangeDirection.raw)))
  names.extend(("engaged_prob", "hard_brake", "lane_change_state", "lane_change_direction"))
  return values, names


def find_rlog(root: Path, route_prefix: str, segment: int) -> Path:
  matches = list(root.glob(f"{route_prefix}--*--{segment}/rlog.zst"))
  if len(matches) != 1:
    raise RuntimeError(f"expected one rlog for {route_prefix} segment {segment}, got {matches}")
  return matches[0]


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--can-npz", type=Path, required=True)
  parser.add_argument("--rlog-root", type=Path, required=True)
  parser.add_argument("--output", type=Path, required=True)
  args = parser.parse_args()

  can = np.load(args.can_npz, allow_pickle=True)
  routes = can["routes"]
  segments = can["segs"]
  sample_times = can["times"]
  route_names = can["route_names"]

  aligned: np.ndarray | None = None
  feature_names: list[str] | None = None
  model_age_s = np.full(len(sample_times), np.nan, dtype=np.float32)

  for route_idx in np.unique(routes):
    for segment in np.unique(segments[routes == route_idx]):
      row_idx = np.flatnonzero((routes == route_idx) & (segments == segment))
      rlog = find_rlog(args.rlog_root, str(route_names[route_idx]), int(segment))
      model_times: list[int] = []
      rows: list[list[float]] = []
      for msg in LogReader(str(rlog)):
        if msg.which() != "modelV2":
          continue
        vals, names = model_features(msg.modelV2)
        if feature_names is None:
          feature_names = names
          aligned = np.full((len(sample_times), len(names)), np.nan, dtype=np.float32)
        elif names != feature_names:
          raise RuntimeError(f"model feature schema changed in {rlog}")
        model_times.append(int(msg.logMonoTime))
        rows.append(vals)

      if not model_times:
        continue
      mt = np.asarray(model_times, dtype=np.int64)
      mr = np.asarray(rows, dtype=np.float32)
      selected = np.searchsorted(mt, sample_times[row_idx], side="right") - 1
      selected = np.clip(selected, 0, len(mt) - 1)
      assert aligned is not None
      aligned[row_idx] = mr[selected]
      model_age_s[row_idx] = (sample_times[row_idx] - mt[selected]) / 1e9
      print(f"aligned {route_names[route_idx]} segment {int(segment):02d}: "
            f"{len(row_idx)} CAN samples, {len(mt)} model frames")

  if aligned is None or feature_names is None:
    raise RuntimeError("no modelV2 messages found")
  np.savez_compressed(args.output, X=aligned, age_s=model_age_s,
                      features=np.asarray(feature_names), routes=routes, segs=segments,
                      times=sample_times)
  print(f"wrote {args.output}: {aligned.shape}")


if __name__ == "__main__":
  main()
