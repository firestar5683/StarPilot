"""Frozen CEM signal-lane width, qualified by current model and car evidence.

The four-model-frame cadence follows the frozen planner. A cached width is
usable only while consecutive source frames remain fresh; missing geometry is
unknown, not evidence that a neighboring lane is absent.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.starpilot.model_geometry import normalized_origin


MODEL_MAX_AGE_NS = 150_000_000
CAR_MAX_AGE_NS = 250_000_000
CLOCK_PAIR_MAX_SKEW_NS = 1_000_000


@dataclass(frozen=True)
class MonoSource:
  producer_ns: int
  receipt_ns: int


@dataclass(frozen=True)
class SignalLaneFrame:
  model: object
  model_valid: bool
  car_valid: bool
  ego_speed_mps: float
  minimum_lane_change_speed_mps: float
  signal_speed_mps: float
  lane_detection_width_m: float
  signal_lane_detection: bool
  left_blinker: bool
  right_blinker: bool
  model_source: MonoSource
  car_source: MonoSource
  model_eof_boot_ns: int
  now_mono_ns: int
  now_boot_ns: int
  expected_boot_minus_mono_ns: int
  barrier_mono_ns: int
  barrier_boot_ns: int
  sample_skew_ns: int


@dataclass(frozen=True)
class SignalLaneObservation:
  left_width_m: float | None
  right_width_m: float | None
  selected_width_m: float | None
  lane_available: bool | None
  signal_scene: bool | None
  observed_mono_ns: int | None
  reason: str


UNKNOWN = SignalLaneObservation(None, None, None, None, None, None, "unknown")


def _finite(value: object, low: float, high: float) -> float | None:
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    return None
  try:
    result = float(value)
  except (OverflowError, ValueError):
    return None
  return result if math.isfinite(result) and low <= result <= high else None


def _fresh(source: MonoSource, now_ns: int, barrier_ns: int, age_ns: int) -> bool:
  return isinstance(source, MonoSource) and all(
    type(stamp) is int and barrier_ns < stamp <= now_ns and now_ns - stamp <= age_ns
    for stamp in (source.producer_ns, source.receipt_ns)
  )


def _line(line: object) -> tuple[np.ndarray, np.ndarray] | None:
  try:
    xs = normalized_origin(tuple(line.x))
    ys = tuple(line.y)
  except (AttributeError, TypeError, ValueError, OverflowError):
    return None
  if len(xs) != ModelConstants.IDX_N or len(ys) != ModelConstants.IDX_N:
    return None
  x = tuple(_finite(value, 0.0, 500.0) for value in xs)
  y = tuple(_finite(value, -30.0, 30.0) for value in ys)
  if any(value is None for value in x + y):
    return None
  numeric_x = tuple(float(value) for value in x if value is not None)
  if any(b <= a for a, b in zip(numeric_x, numeric_x[1:], strict=False)):
    return None
  return np.asarray(numeric_x, dtype=float), np.asarray(y, dtype=float)


def _width(outer: object, inner: object, edge: object) -> float | None:
  first, second, road = _line(outer), _line(inner), _line(edge)
  if first is None or second is None or road is None:
    return None
  first_x, first_y = first
  second_x, second_y = second
  road_x, road_y = road
  lane_width = float(np.median(np.abs(second_y - np.interp(second_x, first_x, first_y))))
  edge_width = float(np.median(np.abs(second_y - np.interp(second_x, road_x, road_y))))
  return 0.0 if edge_width < lane_width else lane_width


def model_widths(model: object) -> tuple[float, float] | None:
  """Compute the two frozen widths, rejecting malformed geometry first."""
  try:
    lines, edges = model.laneLines, model.roadEdges
    if len(lines) != 4 or len(edges) != 2:
      return None
    left = _width(lines[0], lines[1], edges[0])
    right = _width(lines[3], lines[2], edges[1])
  except (AttributeError, TypeError, ValueError, OverflowError):
    return None
  return (left, right) if left is not None and right is not None else None


class SignalLaneTracker:
  """One drive-session owner; call once per newly received model update."""

  def __init__(self) -> None:
    self.reset()

  def reset(self) -> None:
    self._last_model_ns: int | None = None
    self._count = 0
    self._widths: tuple[float, float] | None = None

  def update(self, frame: SignalLaneFrame) -> SignalLaneObservation:
    if not isinstance(frame, SignalLaneFrame) or not self._valid(frame):
      self.reset()
      return UNKNOWN
    speed = float(frame.ego_speed_mps)
    stamp = frame.model_source.producer_ns
    if self._last_model_ns is not None and (stamp < self._last_model_ns or stamp - self._last_model_ns > MODEL_MAX_AGE_NS):
      self.reset()
      return UNKNOWN
    repeated = stamp == self._last_model_ns
    self._last_model_ns = stamp
    if speed < frame.minimum_lane_change_speed_mps:
      self._count = 0
      self._widths = (0.0, 0.0)
    elif repeated:
      if model_widths(frame.model) is None:
        self._widths = None
    elif not repeated:
      self._count += 1
      if self._count % 4 == 0:
        self._widths = model_widths(frame.model)
      elif model_widths(frame.model) is None:
        # A malformed intervening model frame cannot extend prior evidence.
        self._widths = None
    if not frame.left_blinker and not frame.right_blinker:
      return SignalLaneObservation(*(self._widths or (None, None)), None, None, False, stamp, "no_signal")
    selected = (self._widths[0] if frame.left_blinker else self._widths[1]) if self._widths is not None else None
    available = (selected >= frame.lane_detection_width_m if selected is not None else None) if frame.signal_lane_detection else True
    scene = False if speed >= frame.signal_speed_mps else (not available if available is not None else None)
    return SignalLaneObservation(*(self._widths or (None, None)), selected, available, scene, stamp,
                                 "measured" if selected is not None else "awaiting_width")

  @staticmethod
  def _valid(frame: SignalLaneFrame) -> bool:
    if any(type(value) is not bool for value in (frame.model_valid, frame.car_valid, frame.signal_lane_detection, frame.left_blinker, frame.right_blinker)):
      return False
    if not frame.model_valid or not frame.car_valid:
      return False
    if any(_finite(value, low, high) is None for value, low, high in (
      (frame.ego_speed_mps, 0.0, 80.0), (frame.minimum_lane_change_speed_mps, 0.0, 80.0),
      (frame.signal_speed_mps, 0.0, 80.0), (frame.lane_detection_width_m, 0.0, 30.0),
    )):
      return False
    if any(type(value) is not int for value in (frame.now_mono_ns, frame.now_boot_ns, frame.expected_boot_minus_mono_ns,
                                               frame.barrier_mono_ns, frame.barrier_boot_ns, frame.model_eof_boot_ns, frame.sample_skew_ns)):
      return False
    if not 0 <= frame.sample_skew_ns <= CLOCK_PAIR_MAX_SKEW_NS:
      return False
    if frame.now_mono_ns <= frame.barrier_mono_ns or frame.now_boot_ns <= frame.barrier_boot_ns:
      return False
    if abs(frame.now_boot_ns - frame.now_mono_ns - frame.expected_boot_minus_mono_ns) > max(CLOCK_PAIR_MAX_SKEW_NS, 2 * frame.sample_skew_ns):
      return False
    if not _fresh(frame.model_source, frame.now_mono_ns, frame.barrier_mono_ns, MODEL_MAX_AGE_NS):
      return False
    if not _fresh(frame.car_source, frame.now_mono_ns, frame.barrier_mono_ns, CAR_MAX_AGE_NS):
      return False
    return frame.barrier_boot_ns < frame.model_eof_boot_ns <= frame.now_boot_ns and frame.now_boot_ns - frame.model_eof_boot_ns <= MODEL_MAX_AGE_NS
