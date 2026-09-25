"""Frozen CEM curve predicate and filter, without mode or actuator authority."""

from __future__ import annotations

import math

from openpilot.common.realtime import DT_MDL
from openpilot.starpilot.model_geometry import road_curvature as frozen_road_curvature


CRUISING_SPEED_MPS = 5.0
MIN_LATERAL_ACCEL_MPS2 = 1.3
FILTER_THRESHOLD = 1.0 - 1.0 / math.e
INITIAL_FILTER_TIME_S = 0.8
MAX_FRAME_GAP_NS = 250_000_000
MPS_TO_MPH = 1.0 / 0.44704


def _finite(value: object, *, low: float, high: float) -> float | None:
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    return None
  try:
    result = float(value)
  except (OverflowError, ValueError):
    return None
  return result if math.isfinite(result) and low <= result <= high else None


def frozen_raw_curve(model: object, speed_mps: float, curvature: float, left_blinker: bool, right_blinker: bool) -> tuple[bool, bool] | None:
  """Return (predicted road curve, measured curve), before CEM filtering."""
  speed = _finite(speed_mps, low=0.0, high=80.0)
  measured = _finite(curvature, low=-1.0, high=1.0)
  if speed is None or measured is None or type(left_blinker) is not bool or type(right_blinker) is not bool:
    return None
  road = frozen_road_curvature(model, speed)
  if road is None:
    return None
  road_curvature, _ = road
  # Algebraically equivalent to sqrt(1 / abs(curvature)) < vEgo,
  # including the zero-curvature false case without division by zero.
  predicted = speed > CRUISING_SPEED_MPS and abs(road_curvature) * speed * speed > 1.0 and not (left_blinker or right_blinker)
  driving = abs(speed * speed * measured) >= MIN_LATERAL_ACCEL_MPS2
  return predicted, driving


def _filter_time_no_traffic(speed_mps: float) -> float:
  speed_mph = speed_mps * MPS_TO_MPH
  if speed_mph <= 35.0:
    return 0.0
  if speed_mph >= 45.0:
    return INITIAL_FILTER_TIME_S
  return INITIAL_FILTER_TIME_S * (speed_mph - 35.0) / 10.0


class CurveDetector:
  """One CEM model-tick filter. Reset on missing evidence or frame discontinuity."""

  def __init__(self):
    self.reset()

  def reset(self) -> None:
    self.value = 0.0
    self.filter_time_s = INITIAL_FILTER_TIME_S
    self.last_observed_mono_ns: int | None = None

  def step(self, *, observed_mono_ns: int, speed_mps: float, raw_curve: tuple[bool, bool] | None, traffic_mode: bool | None) -> bool | None:
    observed = observed_mono_ns if type(observed_mono_ns) is int and 0 <= observed_mono_ns <= 10**21 else None
    speed = _finite(speed_mps, low=0.0, high=80.0)
    if (
      observed is None
      or speed is None
      or raw_curve is None
      or len(raw_curve) != 2
      or any(type(item) is not bool for item in raw_curve)
      or type(traffic_mode) is not bool
    ):
      self.reset()
      return None
    if self.last_observed_mono_ns is not None:
      interval = observed - self.last_observed_mono_ns
      if interval <= 0:
        return None  # Re-reading one model event does not advance the filter.
      if interval > MAX_FRAME_GAP_NS:
        self.reset()
        return None  # Expired scene history cannot seed a new observation.
    # Use the previous alpha; stop detection updates it for the next model tick.
    alpha = DT_MDL / (self.filter_time_s + DT_MDL)
    self.value = (1.0 - alpha) * self.value + alpha * float(any(raw_curve))
    self.last_observed_mono_ns = observed
    if not traffic_mode:
      self.filter_time_s = _filter_time_no_traffic(speed)
    return self.value >= FILTER_THRESHOLD and speed > CRUISING_SPEED_MPS
