#!/usr/bin/env python3
"""Route-held-out evaluation for interpretable EV9 BSM heuristics.

This tool consumes the NPZ produced by ``extract_ev9_bsm_can_labels.py`` and
scores fixed, human-readable candidates against native 0x1BA lamp state.  It
does not fit a model or choose a threshold.  Choose/tune a configuration using
some routes, then treat every other route row as the held-out result.

Inputs are deliberately divided into two classes:

* ``deployable`` candidates use signals observed after ADAS transmit-disable:
  0x36A, MRR35 0x3A5--0x3C4, 0x235--0x248, and vehicle state.
* ``stock-only`` candidates use ADAS-originated 0x1E5.  Route 109 proved that
  0x1E5 disappears after suppression, so it is diagnostic evidence only.

The ``current-proxy`` candidate mirrors the software detector's interpretable
logic as closely as the aligned stock NPZ permits.  The NPZ has no gear or CAN
freshness columns, so it assumes fresh Drive data; its name is intentionally
not ``current`` to avoid claiming bit-for-bit runtime replay.

Examples:

  .venv/bin/python tools/ev9_longitudinal/evaluate_ev9_bsm_heuristics.py \
    --npz /tmp/ev9_bsm_stock.npz

  .venv/bin/python tools/ev9_longitudinal/evaluate_ev9_bsm_heuristics.py \
    --npz /tmp/ev9_bsm_stock.npz --candidate current-proxy \
    --candidate raw-and-mrr --max-steering-angle 12 --json

  .venv/bin/python tools/ev9_longitudinal/evaluate_ev9_bsm_heuristics.py \
    --self-check
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path

import numpy as np


RAW_BASE_MASK = 0x02
RAW_RIGHT_MASK = 0x08
RAW_LEFT_MASK = 0x10
CAR_COLUMNS = ("vEgo", "aEgo", "steeringAngleDeg", "steeringRateDeg",
               "steeringTorque", "yawRate", "leftBlinker", "rightBlinker")

DEPLOYABLE_CANDIDATES = (
  "raw36a",
  "gated36a",
  "current-proxy",
  "mrr",
  "raw-and-mrr",
  "camera",
  "raw-and-camera",
)
STOCK_ONLY_CANDIDATES = ("stock-rcta-right",)
ALL_CANDIDATES = DEPLOYABLE_CANDIDATES + STOCK_ONLY_CANDIDATES


@dataclass(frozen=True)
class Config:
  min_speed: float
  reset_speed: float
  max_steering_angle: float
  target_min_speed: float
  track_min_x: float
  track_max_x: float
  track_min_y: float
  track_max_y: float
  camera_min_quality: int
  acquire_seconds: float
  hold_seconds: float


@dataclass(frozen=True)
class Interval:
  group: tuple[int, int]
  start: float
  end: float


@dataclass(frozen=True)
class Metrics:
  frames: int
  positive_frames: int
  predicted_frames: int
  frame_tp: int
  frame_fp: int
  frame_fn: int
  frame_precision: float
  frame_recall: float
  frame_f1: float
  truth_episodes: int
  predicted_episodes: int
  matched_truth_episodes: int
  matched_predicted_episodes: int
  episode_precision: float
  episode_recall: float
  episode_f1: float
  onset_lag_median_s: float
  onset_lag_mean_s: float
  onset_lag_p90_s: float
  false_on_seconds: float
  evaluated_seconds: float
  false_on_fraction: float


def _ratio(numerator: float, denominator: float) -> float:
  return float(numerator / denominator) if denominator else math.nan


def _f1(precision: float, recall: float) -> float:
  if not (math.isfinite(precision) and math.isfinite(recall)):
    return math.nan
  return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0


def _required_feature_index(names: np.ndarray, name: str) -> int:
  matches = np.flatnonzero(names == name)
  if len(matches) != 1:
    raise ValueError(f"expected exactly one feature named {name!r}, found {len(matches)}")
  return int(matches[0])


def _prefix_indices(names: np.ndarray, prefix: str, expected: int) -> np.ndarray:
  indices = np.flatnonzero(np.char.startswith(names.astype(str), prefix))
  if len(indices) != expected:
    raise ValueError(f"expected {expected} {prefix!r} features, found {len(indices)}")
  return indices


def validate_npz(data: np.lib.npyio.NpzFile) -> None:
  required = {"X", "Y", "routes", "segs", "times", "car", "features", "route_names"}
  missing = required - set(data.files)
  if missing:
    raise ValueError(f"NPZ is missing arrays: {', '.join(sorted(missing))}")

  rows = len(data["X"])
  for name in ("Y", "routes", "segs", "times", "car"):
    if len(data[name]) != rows:
      raise ValueError(f"{name} has {len(data[name])} rows, expected {rows}")
  if data["X"].ndim != 2 or data["X"].shape[1] != len(data["features"]):
    raise ValueError("X columns do not match features")
  if data["Y"].shape != (rows, 2):
    raise ValueError(f"Y must have shape ({rows}, 2), got {data['Y'].shape}")
  if data["car"].ndim != 2 or data["car"].shape[1] < len(CAR_COLUMNS):
    raise ValueError(f"car must contain at least {len(CAR_COLUMNS)} columns")
  if np.any(data["routes"] >= len(data["route_names"])):
    raise ValueError("route index exceeds route_names")

  names = data["features"].astype(str)
  _required_feature_index(names, "front2:b1:0x36a:byte3")
  _prefix_indices(names, "mrr35:", 32 * 21)
  _prefix_indices(names, "corner:", 20 * 29)
  _prefix_indices(names, "front1:", 13)

  # Temporal filters may never carry state across a segment.  Within a segment
  # the extracted labels must be monotonic for duration and onset calculations.
  for route, segment in np.unique(np.column_stack((data["routes"], data["segs"])), axis=0):
    idx = np.flatnonzero((data["routes"] == route) & (data["segs"] == segment))
    if np.any(np.diff(data["times"][idx]) < 0):
      raise ValueError(f"timestamps decrease in route={route}, segment={segment}")


def _little_endian_signal(payload: np.ndarray, start_bit: int, size: int, *, signed: bool = False,
                          factor: float = 1.0) -> np.ndarray:
  """Vectorized Intel signal extraction from payloads whose byte zero is CAN byte 3."""
  relative_start = start_bit - 24
  if relative_start < 0:
    raise ValueError("the extracted NPZ omits CAN bytes 0..2")
  first_byte, bit_offset = divmod(relative_start, 8)
  bytes_needed = (bit_offset + size + 7) // 8
  if first_byte + bytes_needed > payload.shape[-1]:
    raise ValueError("signal exceeds retained payload")

  raw = np.zeros(payload.shape[:-1], dtype=np.uint64)
  for offset in range(bytes_needed):
    raw |= payload[..., first_byte + offset].astype(np.uint64) << (8 * offset)
  raw = (raw >> bit_offset) & ((1 << size) - 1)
  if signed:
    sign = np.uint64(1 << (size - 1))
    raw = (raw ^ sign).astype(np.int64) - int(sign)
  return raw.astype(np.float64) * factor


def decode_mrr35(data: np.lib.npyio.NpzFile) -> dict[str, np.ndarray]:
  names = data["features"].astype(str)
  raw = data["X"][:, _prefix_indices(names, "mrr35:", 32 * 21)].reshape(len(data["X"]), 32, 21)
  return {
    "state": _little_endian_signal(raw, 54, 3),
    "x": _little_endian_signal(raw, 63, 12, factor=0.05),
    "y": _little_endian_signal(raw, 76, 12, signed=True, factor=0.05),
    "v_rel": _little_endian_signal(raw, 88, 14, signed=True, factor=0.01),
    "discriminator": _little_endian_signal(raw, 152, 10),
  }


def decode_camera_objects(data: np.lib.npyio.NpzFile) -> dict[str, np.ndarray]:
  """Decode the first object in each retained Zendar-layout 0x235--0x248 frame."""
  names = data["features"].astype(str)
  raw = data["X"][:, _prefix_indices(names, "corner:", 20 * 29)].reshape(len(data["X"]), 20, 29).astype(np.int32)

  def byte(index: int) -> np.ndarray:
    return raw[:, :, index]

  quality = byte(0) & 0x7f
  object_id = (byte(2) >> 4) | ((byte(3) & 0x7) << 4)
  classification = (byte(4) >> 4) & 0x7
  x = (byte(5) | ((byte(6) & 0x1f) << 8)) * 0.05
  y_raw = (byte(6) >> 6) | (byte(7) << 2) | ((byte(8) & 0x3) << 10)
  y = y_raw * 0.05 - 102.4
  v_rel = ((byte(8) >> 3) | ((byte(9) & 0x7f) << 5)) * 0.05 - 100.0
  absolute_vx = (byte(13) | ((byte(14) & 0xf) << 8)) * 0.05 - 102.4
  valid = ((quality > 0) & (object_id > 0) & (x > 0.2) & (x < 350.0) &
           (np.abs(y) < 60.0) & (v_rel > -99.0))
  return {
    "quality": quality,
    "object_id": object_id,
    "classification": classification,
    "x": x,
    "y": y,
    "v_rel": v_rel,
    "absolute_vx": absolute_vx,
    "valid": valid,
  }


def _same_side_track_candidates(x: np.ndarray, y: np.ndarray, absolute_speed: np.ndarray,
                                valid: np.ndarray, config: Config) -> tuple[np.ndarray, np.ndarray]:
  common = (valid & (x >= config.track_min_x) & (x <= config.track_max_x) &
            (absolute_speed >= config.target_min_speed))
  left = np.any(common & (y >= config.track_min_y) & (y <= config.track_max_y), axis=1)
  right = np.any(common & (y <= -config.track_min_y) & (y >= -config.track_max_y), axis=1)
  return left, right


def mrr_candidates(data: np.lib.npyio.NpzFile, config: Config) -> tuple[np.ndarray, np.ndarray]:
  radar = decode_mrr35(data)
  valid = np.isin(radar["state"], (3, 4))
  absolute_speed = data["car"][:, 0, None] + radar["v_rel"]
  return _same_side_track_candidates(radar["x"], radar["y"], absolute_speed, valid, config)


def camera_candidates(data: np.lib.npyio.NpzFile, config: Config) -> tuple[np.ndarray, np.ndarray]:
  objects = decode_camera_objects(data)
  valid = objects["valid"] & (objects["quality"] >= config.camera_min_quality)
  # absolute_vx is decoded directly when plausible; otherwise retain the
  # explicit vEgo + relative-velocity estimate as a conservative fallback.
  estimated = data["car"][:, 0, None] + objects["v_rel"]
  absolute_speed = np.where(np.abs(objects["absolute_vx"]) < 90.0,
                            objects["absolute_vx"], estimated)
  return _same_side_track_candidates(objects["x"], objects["y"], absolute_speed, valid, config)


def _iter_groups(routes: np.ndarray, segments: np.ndarray, selected: np.ndarray | None = None) -> Iterable[np.ndarray]:
  mask = np.ones(len(routes), dtype=bool) if selected is None else selected
  for route, segment in np.unique(np.column_stack((routes[mask], segments[mask])), axis=0):
    yield np.flatnonzero(mask & (routes == route) & (segments == segment))


def _stateful_filter(candidate: np.ndarray, valid: np.ndarray, acquire_allowed: np.ndarray,
                     times: np.ndarray, routes: np.ndarray, segments: np.ndarray,
                     acquire_seconds: float, hold_seconds: float) -> np.ndarray:
  output = np.zeros(len(candidate), dtype=bool)
  for idx in _iter_groups(routes, segments):
    group_times = times[idx].astype(np.float64) * 1e-9
    positive_dt = np.diff(group_times)
    positive_dt = positive_dt[(positive_dt > 0.0) & (positive_dt < 1.0)]
    dt = float(np.median(positive_dt)) if len(positive_dt) else 0.1
    acquire_samples = max(1, int(math.ceil(acquire_seconds / dt - 1e-9)))
    hold_samples = max(0, int(math.ceil(hold_seconds / dt - 1e-9)))
    acquired = held = 0
    detected = False
    for row in idx:
      if not valid[row]:
        acquired = held = 0
        detected = False
        continue
      if candidate[row] and (acquire_allowed[row] or detected):
        acquired += 1
        if detected or acquired >= acquire_samples:
          detected = True
          held = hold_samples
        output[row] = detected
      else:
        acquired = 0
        if detected and held > 0:
          held -= 1
          output[row] = True
        else:
          detected = False
          held = 0
  return output


def build_candidates(data: np.lib.npyio.NpzFile, config: Config) -> dict[str, tuple[np.ndarray, np.ndarray]]:
  names = data["features"].astype(str)
  state = data["X"][:, _required_feature_index(names, "front2:b1:0x36a:byte3")]
  base = (state & RAW_BASE_MASK) != 0
  raw_left = base & ((state & RAW_LEFT_MASK) != 0)
  raw_right = base & ((state & RAW_RIGHT_MASK) != 0)

  v_ego = data["car"][:, 0]
  steering_angle = data["car"][:, 2]
  finite = np.isfinite(v_ego) & np.isfinite(steering_angle)
  instant_gate = finite & (v_ego >= config.min_speed) & (np.abs(steering_angle) < config.max_steering_angle)
  stateful_valid = finite & (v_ego >= config.reset_speed) & (np.abs(steering_angle) < config.max_steering_angle)
  acquire_allowed = v_ego >= config.min_speed

  mrr_left, mrr_right = mrr_candidates(data, config)
  camera_left, camera_right = camera_candidates(data, config)
  current_left = _stateful_filter(raw_left & mrr_left, stateful_valid, acquire_allowed,
                                  data["times"], data["routes"], data["segs"],
                                  config.acquire_seconds, config.hold_seconds)
  current_right = _stateful_filter(raw_right, stateful_valid, acquire_allowed,
                                   data["times"], data["routes"], data["segs"],
                                   config.acquire_seconds, config.hold_seconds)

  # RCTA_TARGET_STATE is original CAN byte 4 bits 0..1. The extraction omits
  # bytes 0..2, making it front1 byte4 in the feature-name schema.
  rcta_byte = data["X"][:, _required_feature_index(names, "front1:b1:0x1e5:byte4")]
  rcta_right = (rcta_byte & 0x3) == 1
  zero = np.zeros(len(state), dtype=bool)
  return {
    "raw36a": (raw_left, raw_right),
    "gated36a": (raw_left & instant_gate, raw_right & instant_gate),
    "current-proxy": (current_left, current_right),
    "mrr": (mrr_left & instant_gate, mrr_right & instant_gate),
    "raw-and-mrr": (raw_left & mrr_left & instant_gate, raw_right & mrr_right & instant_gate),
    "camera": (camera_left & instant_gate, camera_right & instant_gate),
    "raw-and-camera": (raw_left & camera_left & instant_gate, raw_right & camera_right & instant_gate),
    "stock-rcta-right": (zero, rcta_right),
  }


def _sample_durations(times: np.ndarray, routes: np.ndarray, segments: np.ndarray,
                      selected: np.ndarray) -> np.ndarray:
  durations = np.zeros(len(times), dtype=np.float64)
  for idx in _iter_groups(routes, segments, selected):
    seconds = times[idx].astype(np.float64) * 1e-9
    delta = np.diff(seconds)
    normal = delta[(delta > 0.0) & (delta < 1.0)]
    fallback = float(np.median(normal)) if len(normal) else 0.1
    group_duration = np.r_[delta, fallback]
    group_duration[(group_duration <= 0.0) | (group_duration >= 1.0)] = fallback
    durations[idx] = group_duration
  return durations


def _episodes(mask: np.ndarray, times: np.ndarray, durations: np.ndarray,
              routes: np.ndarray, segments: np.ndarray, selected: np.ndarray) -> list[Interval]:
  result: list[Interval] = []
  for idx in _iter_groups(routes, segments, selected):
    active = mask[idx]
    starts = np.flatnonzero(active & ~np.r_[False, active[:-1]])
    ends = np.flatnonzero(active & ~np.r_[active[1:], False])
    group = (int(routes[idx[0]]), int(segments[idx[0]]))
    result.extend(Interval(group, float(times[idx[start]]) * 1e-9,
                           float(times[idx[end]]) * 1e-9 + durations[idx[end]])
                  for start, end in zip(starts, ends, strict=True))
  return result


def evaluate(truth: np.ndarray, prediction: np.ndarray, data: np.lib.npyio.NpzFile,
             selected: np.ndarray) -> Metrics:
  truth = truth.astype(bool)
  prediction = prediction.astype(bool)
  tp = int(np.sum(selected & truth & prediction))
  fp = int(np.sum(selected & ~truth & prediction))
  fn = int(np.sum(selected & truth & ~prediction))
  frame_precision = _ratio(tp, tp + fp)
  frame_recall = _ratio(tp, tp + fn)

  durations = _sample_durations(data["times"], data["routes"], data["segs"], selected)
  truth_episodes = _episodes(truth, data["times"], durations, data["routes"], data["segs"], selected)
  pred_episodes = _episodes(prediction, data["times"], durations, data["routes"], data["segs"], selected)
  truth_matches: set[int] = set()
  pred_matches: set[int] = set()
  onset_lags: list[float] = []
  for truth_index, truth_episode in enumerate(truth_episodes):
    overlaps: list[tuple[float, int]] = []
    for pred_index, pred_episode in enumerate(pred_episodes):
      if pred_episode.group != truth_episode.group:
        continue
      overlap = min(truth_episode.end, pred_episode.end) - max(truth_episode.start, pred_episode.start)
      if overlap > 0.0:
        overlaps.append((overlap, pred_index))
    if overlaps:
      _, best_pred = max(overlaps)
      truth_matches.add(truth_index)
      pred_matches.update(pred_index for _, pred_index in overlaps)
      onset_lags.append(pred_episodes[best_pred].start - truth_episode.start)

  episode_precision = _ratio(len(pred_matches), len(pred_episodes))
  episode_recall = _ratio(len(truth_matches), len(truth_episodes))
  lag = np.asarray(onset_lags, dtype=np.float64)
  evaluated_seconds = float(np.sum(durations[selected]))
  false_on_seconds = float(np.sum(durations[selected & prediction & ~truth]))
  return Metrics(
    frames=int(np.sum(selected)),
    positive_frames=int(np.sum(selected & truth)),
    predicted_frames=int(np.sum(selected & prediction)),
    frame_tp=tp,
    frame_fp=fp,
    frame_fn=fn,
    frame_precision=frame_precision,
    frame_recall=frame_recall,
    frame_f1=_f1(frame_precision, frame_recall),
    truth_episodes=len(truth_episodes),
    predicted_episodes=len(pred_episodes),
    matched_truth_episodes=len(truth_matches),
    matched_predicted_episodes=len(pred_matches),
    episode_precision=episode_precision,
    episode_recall=episode_recall,
    episode_f1=_f1(episode_precision, episode_recall),
    onset_lag_median_s=float(np.median(lag)) if len(lag) else math.nan,
    onset_lag_mean_s=float(np.mean(lag)) if len(lag) else math.nan,
    onset_lag_p90_s=float(np.quantile(lag, 0.9)) if len(lag) else math.nan,
    false_on_seconds=false_on_seconds,
    evaluated_seconds=evaluated_seconds,
    false_on_fraction=_ratio(false_on_seconds, evaluated_seconds),
  )


def _resolve_routes(data: np.lib.npyio.NpzFile, requested: list[str]) -> list[int]:
  if not requested:
    return [int(route) for route in np.unique(data["routes"])]
  result: set[int] = set()
  for value in requested:
    if value.isdigit() and int(value) < len(data["route_names"]):
      result.add(int(value))
      continue
    matches = [i for i, name in enumerate(data["route_names"].astype(str)) if value in name]
    if len(matches) != 1:
      raise ValueError(f"route selector {value!r} matched {len(matches)} routes")
    result.add(matches[0])
  return sorted(result)


def _format_metric(value: float) -> str:
  return f"{value:.3f}" if math.isfinite(value) else "-"


def _print_table(results: list[dict]) -> None:
  print("Each route is an independent holdout. Do not tune a configuration on the route used to judge it.")
  print("current-proxy assumes fresh Drive data because gear/freshness are absent from the extracted NPZ.\n")
  header = f"{'class':10} {'candidate':16} {'holdout route':22} {'side':5} "
  header += f"{'frame P/R/F1':19} {'episode P/R/F1':19} {'lag med':8} {'false-on':10}"
  print(header)
  print("-" * len(header))
  for result in results:
    metrics: Metrics = result["metrics"]
    frame = "/".join(_format_metric(v) for v in
                     (metrics.frame_precision, metrics.frame_recall, metrics.frame_f1))
    episode = "/".join(_format_metric(v) for v in
                       (metrics.episode_precision, metrics.episode_recall, metrics.episode_f1))
    lag = f"{metrics.onset_lag_median_s:+.2f}s" if math.isfinite(metrics.onset_lag_median_s) else "-"
    row = f"{result['feature_class']:10} {result['candidate']:16} {result['route_name']:22} "
    row += f"{result['side']:5} {frame:19} {episode:19} {lag:8} {metrics.false_on_seconds:8.1f}s"
    print(row)


def _json_safe(value):
  if isinstance(value, dict):
    return {key: _json_safe(item) for key, item in value.items()}
  if isinstance(value, list):
    return [_json_safe(item) for item in value]
  if isinstance(value, float) and not math.isfinite(value):
    return None
  return value


def self_check() -> None:
  # One truth and one prediction episode overlap by one 100 ms frame. Episode
  # precision/recall are both one while frame precision/recall are one-half.
  truth = np.asarray([False, True, True, False, False])
  prediction = np.asarray([False, False, True, True, False])
  selected = np.ones(5, dtype=bool)
  arrays = {
    "times": np.arange(5, dtype=np.int64) * 100_000_000,
    "routes": np.zeros(5, dtype=np.uint8),
    "segs": np.zeros(5, dtype=np.uint8),
  }
  metrics = evaluate(truth, prediction, arrays, selected)  # type: ignore[arg-type]
  assert metrics.frame_tp == metrics.frame_fp == metrics.frame_fn == 1
  assert metrics.frame_precision == metrics.frame_recall == 0.5
  assert metrics.episode_precision == metrics.episode_recall == 1.0
  assert math.isclose(metrics.onset_lag_median_s, 0.1, abs_tol=1e-9)
  assert math.isclose(metrics.false_on_seconds, 0.1, abs_tol=1e-9)

  candidate = np.asarray([True, True, False, False, False])
  valid = np.ones(5, dtype=bool)
  allowed = np.ones(5, dtype=bool)
  filtered = _stateful_filter(candidate, valid, allowed, arrays["times"], arrays["routes"], arrays["segs"], 0.2, 0.2)
  assert np.array_equal(filtered, [False, True, True, True, False])
  print("self-check passed")


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("--npz", type=Path, help="NPZ from extract_ev9_bsm_can_labels.py")
  parser.add_argument("--candidate", action="append", choices=ALL_CANDIDATES,
                      help="candidate to evaluate (repeatable; default: all)")
  parser.add_argument("--route", action="append", default=[],
                      help="route index or unique route-name substring (repeatable)")
  parser.add_argument("--side", choices=("left", "right", "both"), default="both")
  parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
  parser.add_argument("--self-check", action="store_true", help="run internal metric/filter checks")
  parser.add_argument("--min-speed", type=float, default=40.0 / 3.6, metavar="MPS")
  parser.add_argument("--reset-speed", type=float, default=20.0 / 3.6, metavar="MPS")
  parser.add_argument("--max-steering-angle", type=float, default=10.0, metavar="DEG")
  parser.add_argument("--target-min-speed", type=float, default=10.0 / 3.6, metavar="MPS")
  parser.add_argument("--track-min-x", type=float, default=0.0, metavar="M")
  parser.add_argument("--track-max-x", type=float, default=50.0, metavar="M")
  parser.add_argument("--track-min-y", type=float, default=2.5, metavar="M")
  parser.add_argument("--track-max-y", type=float, default=3.5, metavar="M")
  parser.add_argument("--camera-min-quality", type=int, default=1)
  parser.add_argument("--acquire-seconds", type=float, default=0.10)
  parser.add_argument("--hold-seconds", type=float, default=0.20)
  args = parser.parse_args()

  if args.self_check:
    self_check()
    if args.npz is None:
      return
  if args.npz is None:
    parser.error("--npz is required unless only --self-check is requested")

  config = Config(args.min_speed, args.reset_speed, args.max_steering_angle,
                  args.target_min_speed, args.track_min_x, args.track_max_x,
                  args.track_min_y, args.track_max_y, args.camera_min_quality,
                  args.acquire_seconds, args.hold_seconds)
  if not (0.0 <= config.reset_speed <= config.min_speed):
    parser.error("speeds must satisfy 0 <= reset-speed <= min-speed")
  if not (0.0 <= config.track_min_x < config.track_max_x and
          0.0 <= config.track_min_y < config.track_max_y):
    parser.error("track min bounds must be nonnegative and lower than max bounds")
  if min(config.acquire_seconds, config.hold_seconds) < 0.0:
    parser.error("acquire/hold durations must be nonnegative")

  data = np.load(args.npz, allow_pickle=True)
  validate_npz(data)
  candidates = build_candidates(data, config)
  requested_candidates = args.candidate or list(ALL_CANDIDATES)
  routes = _resolve_routes(data, args.route)
  sides = (0, 1) if args.side == "both" else ((0,) if args.side == "left" else (1,))
  side_names = ("left", "right")
  results: list[dict] = []
  for candidate_name in requested_candidates:
    feature_class = "deployable" if candidate_name in DEPLOYABLE_CANDIDATES else "stock-only"
    for route in routes:
      selected = data["routes"] == route
      for side in sides:
        metrics = evaluate(data["Y"][:, side], candidates[candidate_name][side], data, selected)
        results.append({
          "feature_class": feature_class,
          "candidate": candidate_name,
          "route_index": route,
          "route_name": str(data["route_names"][route]),
          "side": side_names[side],
          "metrics": metrics,
        })

  if args.json:
    payload = {
      "npz": str(args.npz),
      "config": asdict(config),
      "notes": {
        "held_out": "Tune on other routes; each route row is evaluated independently.",
        "current_proxy": "Assumes fresh Drive data because gear/freshness are absent from the NPZ.",
        "stock_only": "0x1E5 disappears after EV9 ADAS transmit-disable and is not deployable.",
      },
      "results": [{**result, "metrics": asdict(result["metrics"])} for result in results],
    }
    print(json.dumps(_json_safe(payload), indent=2, allow_nan=False))
  else:
    _print_table(results)


if __name__ == "__main__":
  main()
