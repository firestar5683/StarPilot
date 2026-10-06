"""Bounded lane-centering contribution for lateral control.

The caller owns model freshness, axis authority, and final curvature limiting.
This module neither reads settings nor sends commands.
"""

from dataclasses import dataclass
from enum import StrEnum
import math
from numbers import Real
from typing import Any

import capnp
import numpy as np

from openpilot.cereal import log


STRENGTH_BASELINE = 1.5
# At 8 m lookahead, keep the unsaturated error interval above the 0.08 m deadband.
STRENGTH_MAX = 1.575

MIN_SPEED = 5.0
MIN_LANE_PROB = 0.6
MAX_LANE_STD = 0.3
MIN_LANE_WIDTH = 2.6
MAX_LANE_WIDTH = 4.8
MAX_OFFSET = 0.3
MIN_CENTER_TO_LINE = 1.1
MAX_CORRECTION = 0.004 * 0.30
CENTER_ERROR_DEADBAND = 0.08
E2E_MAX_PATH_STD = 0.35
E2E_BREAK_IN_START = 0.15
E2E_BREAK_IN_FULL = 0.50
ACQUIRE_TAU = 0.4
RELEASE_TAU = 0.2


class ControlMode(StrEnum):
  OFF = "off"
  LATERAL_ONLY = "lateral_only"
  LONGITUDINAL_ONLY = "longitudinal_only"
  COMBINED = "combined"

  @property
  def lateral_authority(self) -> bool:
    return self in (ControlMode.LATERAL_ONLY, ControlMode.COMBINED)


@dataclass(frozen=True)
class LaneCenteringSettings:
  enabled: bool = False
  offset_m: float = 0.0
  e2e_authority: float = 1.0
  pause_on_signal: bool = True
  strength: float = STRENGTH_BASELINE


@dataclass(frozen=True)
class LaneCenteringRequest:
  """Optional host configuration; vehicle/model facts come from the host itself."""

  mode: ControlMode
  settings: LaneCenteringSettings
  elapsed_seconds: float
  time_discontinuity: bool = False


@dataclass(frozen=True)
class LaneCenteringInput:
  model: Any
  model_sample_id: int
  model_valid: bool
  base_curvature: float
  speed_mps: float
  mode: ControlMode
  lateral_active: bool
  settings: LaneCenteringSettings
  elapsed_seconds: float
  turn_signal_active: bool = False
  driver_override: bool = False
  time_discontinuity: bool = False


@dataclass(frozen=True)
class LaneCenteringResult:
  # None means the caller's proposed curvature was invalid and must be rejected.
  candidate_curvature: float | None
  correction: float
  direction: int
  reason: str


def _finite_number(value: Any) -> float | None:
  if isinstance(value, bool) or not isinstance(value, Real):
    return None
  try:
    result = float(value)
  except (TypeError, ValueError, OverflowError):
    return None
  return result if math.isfinite(result) else None


def _path(model_path: Any) -> tuple[np.ndarray, np.ndarray] | None:
  try:
    return _path_xy(model_path.x, model_path.y)
  except (AttributeError, TypeError, ValueError, OverflowError):
    return None


def _path_xy(xs: Any, ys: Any) -> tuple[np.ndarray, np.ndarray] | None:
  try:
    x = np.asarray(xs)
    y = np.asarray(ys)
  except (TypeError, ValueError, OverflowError):
    return None
  if x.ndim != 1 or y.ndim != 1 or len(x) < 2 or len(x) != len(y):
    return None
  if x.dtype.kind not in "fiu" or y.dtype.kind not in "fiu":
    return None
  x, y = x.astype(float), y.astype(float)
  if not np.isfinite(x).all() or not np.isfinite(y).all() or not np.all(np.diff(x) > 0):
    return None
  return x, y


def _at(path: tuple[np.ndarray, np.ndarray], distance: float) -> float | None:
  x, y = path
  if not x[0] <= distance <= x[-1]:
    return None
  return float(np.interp(distance, x, y))


def raw_correction(model: Any, speed_mps: float, offset_m: float, e2e_authority: float, *, _paths=None) -> float | None:
  """Return a finite raw curvature correction, or None for unqualified model data."""
  speed = _finite_number(speed_mps)
  offset = _finite_number(offset_m)
  authority = _finite_number(e2e_authority)
  if speed is None or offset is None or authority is None or speed < MIN_SPEED:
    return None
  try:
    lines = model.laneLines
    probs = model.laneLineProbs
    stds = model.laneLineStds
    if len(lines) < 3 or len(probs) < 3 or len(stds) < 3:
      return None
    for i in (1, 2):
      prob = _finite_number(probs[i])
      std = _finite_number(stds[i])
      if prob is None or std is None or not MIN_LANE_PROB <= prob <= 1.0 or not 0.0 <= std <= MAX_LANE_STD:
        return None
    left_path, right_path, model_path = (_path(lines[1]), _path(lines[2]), _path(model.position)) if _paths is None else _paths[:3]
    if left_path is None or right_path is None or model_path is None:
      return None
    lookahead = float(np.clip(speed, 8.0, 35.0))
    left, right, model_y = _at(left_path, lookahead), _at(right_path, lookahead), _at(model_path, lookahead)
    if left is None or right is None or model_y is None:
      return None
    width = right - left
    if not MIN_LANE_WIDTH <= width <= MAX_LANE_WIDTH:
      return None
    safe_offset = min(MAX_OFFSET, max(0.0, width * 0.5 - MIN_CENTER_TO_LINE))
    target_y = (left + right) * 0.5 + float(np.clip(offset, -safe_offset, safe_offset))
    error = target_y - model_y
    error_abs = abs(error)
    error = math.copysign(max(0.0, error_abs - CENTER_ERROR_DEADBAND), error)

    # Reduce lane authority only when path variance establishes confidence.
    try:
      std_path = _path_xy(model.position.x, model.position.yStd) if _paths is None else _paths[3]
    except (AttributeError, TypeError, ValueError, OverflowError):
      std_path = None
    if std_path is not None:
      path_std = _at(std_path, lookahead)
      if path_std is not None and 0.0 <= path_std <= E2E_MAX_PATH_STD:
        break_in = float(np.clip((error_abs - E2E_BREAK_IN_START) /
                                 (E2E_BREAK_IN_FULL - E2E_BREAK_IN_START), 0.0, 1.0))
        error *= 1.0 - float(np.clip(authority, 0.0, 1.0)) * break_in
    correction = 2.0 * error / lookahead ** 2
    return correction if math.isfinite(correction) else None
  except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
    return None


def _reader_geometry_key(model):
  if not isinstance(model, capnp.lib.capnp._DynamicStructReader):
    return None
  try:
    return (tuple(model.laneLineProbs), tuple(model.laneLineStds),
            *((tuple(line.x), tuple(line.y)) for line in (model.laneLines[1], model.laneLines[2])),
            tuple(model.position.x), tuple(model.position.y), tuple(model.position.yStd))
  except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
    return None


class LaneCenteringController:
  def __init__(self) -> None:
    self._correction = 0.0
    self._geometry_cache = None

  def reset(self) -> None:
    self._correction = 0.0
    self._geometry_cache = None

  def _result(self, base: float, reason: str) -> LaneCenteringResult:
    correction = self._correction
    return LaneCenteringResult(base + correction, correction, (correction > 0) - (correction < 0), reason)

  def _fade(self, base: float, dt: float, reason: str) -> LaneCenteringResult:
    self._correction *= math.exp(-dt / RELEASE_TAU)
    if abs(self._correction) < 1e-12:
      self._correction = 0.0
    return self._result(base, reason)

  def update(self, observation: LaneCenteringInput) -> LaneCenteringResult:
    if not isinstance(observation, LaneCenteringInput):
      self.reset()
      return LaneCenteringResult(None, 0.0, 0, "invalid_input")
    base = _finite_number(observation.base_curvature)
    speed = _finite_number(observation.speed_mps)
    dt = _finite_number(observation.elapsed_seconds)
    settings = observation.settings
    offset = _finite_number(settings.offset_m) if isinstance(settings, LaneCenteringSettings) else None
    authority = _finite_number(settings.e2e_authority) if isinstance(settings, LaneCenteringSettings) else None
    strength = _finite_number(settings.strength) if isinstance(settings, LaneCenteringSettings) else None
    if (base is None or speed is None or dt is None or dt <= 0 or
        offset is None or authority is None or strength is None or not 0.5 <= strength <= STRENGTH_MAX or type(observation.model_sample_id) is not int or
        observation.model_sample_id < 0 or not isinstance(observation.mode, ControlMode) or
        type(observation.model_valid) is not bool or type(observation.lateral_active) is not bool or
        type(observation.turn_signal_active) is not bool or type(observation.driver_override) is not bool or
        type(observation.time_discontinuity) is not bool or
        type(settings.enabled) is not bool or type(settings.pause_on_signal) is not bool):
      self.reset()
      return LaneCenteringResult(base, 0.0, 0, "invalid_input")
    if observation.time_discontinuity:
      self.reset()
      return self._result(base, "time_discontinuity")
    if not observation.mode.lateral_authority or not settings.enabled or not observation.lateral_active or \
       not observation.model_valid or speed < MIN_SPEED:
      self.reset()
      return self._result(base, "inactive")
    if observation.driver_override:
      self.reset()
      return self._result(base, "driver_override")
    if settings.pause_on_signal and observation.turn_signal_active:
      return self._fade(base, dt, "signal_release")
    try:
      if observation.model.meta.laneChangeState != log.LaneChangeState.off:
        self.reset()
        return self._result(base, "lane_change")
    except (AttributeError, TypeError, ValueError):
      self.reset()
      return self._result(base, "invalid_model")
    # Filtering runs per control tick, including repeated model samples.
    geometry = _reader_geometry_key(observation.model)
    cache_key = (observation.model_sample_id, geometry)
    cached = self._geometry_cache
    paths = None
    if geometry is not None:
      if cached is not None and cached[0] is observation.model and cached[1] == cache_key:
        paths = cached[2]
      else:
        paths = (_path_xy(*geometry[2]), _path_xy(*geometry[3]),
                 _path_xy(geometry[4], geometry[5]), _path_xy(geometry[4], geometry[6]))
        self._geometry_cache = (observation.model, cache_key, paths)
    else:
      self._geometry_cache = None
    raw = raw_correction(observation.model, speed, offset, authority, _paths=paths)
    if raw is None or not math.isfinite(raw):
      return self._fade(base, dt, "unqualified_model")
    target = float(np.clip(raw, -0.004, 0.004)) * 0.30
    if strength != 1.0:
      target = float(np.clip(target * strength, -MAX_CORRECTION, MAX_CORRECTION))
    self._correction += (target - self._correction) * (1.0 - math.exp(-dt / ACQUIRE_TAU))
    self._correction = float(np.clip(self._correction, -MAX_CORRECTION, MAX_CORRECTION))
    return self._result(base, "qualified")
