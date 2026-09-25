"""Adjacent radar-track ambiguity for conditional mode decisions.

This consumes radard's raw Track values before they are reduced to leadOne/Two.
It is a diagnostic verdict only; no radar, messaging, or control ownership here.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import math

from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.starpilot.model_geometry import normalized_origin


SOURCE_MAX_AGE_NS = 250_000_000
MODEL_MAX_AGE_NS = 150_000_000
MODEL_EOF_MAX_AGE_NS = 150_000_000
CLOCK_PAIR_MAX_SKEW_NS = 1_000_000
MAX_TRACKS = 256


@dataclass(frozen=True)
class MonoSource:
  producer_ns: int
  receipt_ns: int


@dataclass(frozen=True)
class AdjacentTrack:
  track_id: int
  distance_m: float
  lateral_m: float  # radard Track.yRel; model-lateral coordinate is -yRel.
  speed_mps: float


@dataclass(frozen=True)
class AdjacentFrame:
  model: object
  tracks: tuple[AdjacentTrack, ...]
  primary_track_ids: frozenset[int]
  radar_available: bool
  radar_valid: bool
  radar_error_free: bool
  model_valid: bool
  car_valid: bool
  standstill: bool
  ego_speed_mps: float
  radar: MonoSource
  model_source: MonoSource
  car: MonoSource
  model_eof_boot_ns: int
  now_mono_ns: int
  now_boot_ns: int
  expected_boot_minus_mono_ns: int
  barrier_mono_ns: int
  barrier_boot_ns: int
  sample_skew_ns: int


@dataclass(frozen=True)
class AdjacentCandidate:
  track_id: int
  distance_m: float
  lateral_m: float
  speed_mps: float


@dataclass(frozen=True)
class AdjacentObservation:
  ambiguous: bool | None
  left: AdjacentCandidate | None
  right: AdjacentCandidate | None
  observed_mono_ns: int | None


UNKNOWN = AdjacentObservation(None, None, None, None)


def _finite(value: object, low: float, high: float) -> float | None:
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    return None
  try:
    number = float(value)
  except (OverflowError, ValueError):
    return None
  return number if math.isfinite(number) and low <= number <= high else None


def _mono_fresh(source: MonoSource, now_ns: int, barrier_ns: int, max_age_ns: int) -> bool:
  return all(type(stamp) is int and barrier_ns < stamp <= now_ns and now_ns - stamp <= max_age_ns for stamp in (source.producer_ns, source.receipt_ns))


def _geometry(model: object) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...], tuple[float, ...]] | None:
  try:
    lines = model.laneLines
    if len(lines) < 3:
      return None
    left_x = normalized_origin(tuple(lines[1].x))
    right_x = normalized_origin(tuple(lines[2].x))
    left_y = tuple(lines[1].y)
    right_y = tuple(lines[2].y)
  except (AttributeError, TypeError, ValueError, OverflowError):
    return None
  if any(len(values) != ModelConstants.IDX_N for values in (left_x, right_x, left_y, right_y)):
    return None
  xs = tuple(_finite(value, 0.0, 500.0) for value in left_x + right_x)
  ys = tuple(_finite(value, -30.0, 30.0) for value in left_y + right_y)
  if any(value is None for value in xs + ys):
    return None
  lx = tuple(value for value in xs[: ModelConstants.IDX_N] if value is not None)
  rx = tuple(value for value in xs[ModelConstants.IDX_N :] if value is not None)
  ly = tuple(value for value in ys[: ModelConstants.IDX_N] if value is not None)
  ry = tuple(value for value in ys[ModelConstants.IDX_N :] if value is not None)
  if any(b <= a for values in (lx, rx) for a, b in zip(values, values[1:], strict=False)):
    return None
  common_end = min(lx[-1], rx[-1])
  for distance in sorted({0.0, *(x for x in lx + rx if x <= common_end)}):
    if _at(lx, ly, distance) >= _at(rx, ry, distance):
      return None
  return lx, ly, rx, ry


def _at(xs: tuple[float, ...], ys: tuple[float, ...], distance: float) -> float:
  # Clamp outside the modeled x range.
  if distance <= xs[0]:
    return ys[0]
  if distance >= xs[-1]:
    return ys[-1]
  index = min(max(bisect_right(xs, distance) - 1, 0), len(xs) - 2)
  span = xs[index + 1] - xs[index]
  return ys[index] + (ys[index + 1] - ys[index]) * (distance - xs[index]) / span


def _track_valid(track: AdjacentTrack) -> bool:
  return (
    isinstance(track, AdjacentTrack)
    and type(track.track_id) is int
    and 0 <= track.track_id <= 2**32 - 1
    and _finite(track.distance_m, 0.0, 500.0) is not None
    and _finite(track.lateral_m, -30.0, 30.0) is not None
    and _finite(track.speed_mps, -30.0, 100.0) is not None
  )


def evaluate(frame: AdjacentFrame) -> AdjacentObservation:
  """Frozen side selection and CCM veto, subject to explicit source validity."""
  if (
    not isinstance(frame, AdjacentFrame)
    or type(frame.radar_available) is not bool
    or not frame.radar_available
    or type(frame.radar_valid) is not bool
    or not frame.radar_valid
    or type(frame.radar_error_free) is not bool
    or not frame.radar_error_free
    or type(frame.model_valid) is not bool
    or not frame.model_valid
    or type(frame.car_valid) is not bool
    or not frame.car_valid
    or type(frame.standstill) is not bool
    or _finite(frame.ego_speed_mps, 0.0, 80.0) is None
    or type(frame.now_mono_ns) is not int
    or type(frame.now_boot_ns) is not int
    or type(frame.expected_boot_minus_mono_ns) is not int
    or type(frame.barrier_mono_ns) is not int
    or type(frame.barrier_boot_ns) is not int
    or type(frame.sample_skew_ns) is not int
    or not 0 <= frame.sample_skew_ns <= CLOCK_PAIR_MAX_SKEW_NS
    or frame.now_mono_ns <= frame.barrier_mono_ns
    or frame.now_boot_ns <= frame.barrier_boot_ns
    or abs(frame.now_boot_ns - frame.now_mono_ns - frame.expected_boot_minus_mono_ns) > max(CLOCK_PAIR_MAX_SKEW_NS, frame.sample_skew_ns * 2)
    or not isinstance(frame.radar, MonoSource)
    or not isinstance(frame.model_source, MonoSource)
    or not isinstance(frame.car, MonoSource)
    or not _mono_fresh(frame.radar, frame.now_mono_ns, frame.barrier_mono_ns, SOURCE_MAX_AGE_NS)
    or not _mono_fresh(frame.model_source, frame.now_mono_ns, frame.barrier_mono_ns, MODEL_MAX_AGE_NS)
    or not _mono_fresh(frame.car, frame.now_mono_ns, frame.barrier_mono_ns, SOURCE_MAX_AGE_NS)
    or type(frame.model_eof_boot_ns) is not int
    or not frame.barrier_boot_ns < frame.model_eof_boot_ns <= frame.now_boot_ns
    or frame.now_boot_ns - frame.model_eof_boot_ns > MODEL_EOF_MAX_AGE_NS
    or not isinstance(frame.tracks, tuple)
    or len(frame.tracks) > MAX_TRACKS
    or not isinstance(frame.primary_track_ids, frozenset)
    or any(type(track_id) is not int for track_id in frame.primary_track_ids)
  ):
    return UNKNOWN
  geometry = _geometry(frame.model)
  if geometry is None or any(not _track_valid(track) for track in frame.tracks):
    return UNKNOWN
  left_x, left_y, right_x, right_y = geometry
  coverage = min(left_x[-1], right_x[-1])
  max_distance = min(65.0, max(25.0, frame.ego_speed_mps * 3.5))
  if any(
    track.distance_m < max_distance
    and track.distance_m > coverage
    and track.speed_mps > 1.0
    and abs(track.lateral_m) <= 5.5
    and track.track_id not in frame.primary_track_ids
    for track in frame.tracks
  ):
    return UNKNOWN
  left = None
  right = None
  ambiguous = False
  if not frame.standstill:
    for track in frame.tracks:
      if track.speed_mps < 1.0 or track.track_id in frame.primary_track_ids or track.distance_m > coverage:
        continue
      model_y = -track.lateral_m
      candidate = AdjacentCandidate(track.track_id, track.distance_m, track.lateral_m, track.speed_mps)
      if model_y < _at(left_x, left_y, track.distance_m):
        if left is None or track.distance_m < left.distance_m:
          left = candidate
        ambiguous |= abs(track.lateral_m) <= 5.5 and track.speed_mps > 1.0 and track.distance_m < max_distance
      if model_y > _at(right_x, right_y, track.distance_m):
        if right is None or track.distance_m < right.distance_m:
          right = candidate
        ambiguous |= abs(track.lateral_m) <= 5.5 and track.speed_mps > 1.0 and track.distance_m < max_distance
  observed = min(
    frame.radar.producer_ns,
    frame.radar.receipt_ns,
    frame.model_source.producer_ns,
    frame.model_source.receipt_ns,
    frame.model_eof_boot_ns - frame.expected_boot_minus_mono_ns,
    frame.car.producer_ns,
    frame.car.receipt_ns,
  )
  return AdjacentObservation(ambiguous, left, right, observed)
