from cereal import log
import numpy as np

from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.drive_helpers import smooth_value


_MIN_V_EGO = 5.0
_MIN_LANE_PROB = 0.6
_MAX_LANE_STD = 0.3
_MIN_LANE_WIDTH = 2.6
_MAX_LANE_WIDTH = 4.8
_MAX_OFFSET = 0.3
_MIN_CENTER_TO_LINE = 1.1
_MAX_RAW_CORRECTION = 0.004
_MAX_GAIN = 0.30
_SMOOTH_TAU = 0.4
_SIGNAL_RELEASE_TAU = 0.20

_E2E_MAX_PATH_STD = 0.35
_E2E_BREAK_IN_START = 0.25
_E2E_BREAK_IN_FULL = 0.75


class LaneCenteringController:
  def __init__(self) -> None:
    self._correction = 0.0

  def reset(self) -> None:
    self._correction = 0.0

  def update(self, model_curvature, model_v2, v_ego, enabled, offset, e2e_authority, lat_active, model_valid,
             pause_on_signal=False, turn_signal_active=False) -> float:
    model_curvature = float(model_curvature)

    try:
      v_ego = float(v_ego)
      offset = float(offset)
      e2e_authority = float(e2e_authority)
    except (TypeError, ValueError):
      self.reset()
      return model_curvature

    if not np.isfinite([v_ego, offset, e2e_authority]).all():
      self.reset()
      return model_curvature

    if not model_valid or not enabled or not lat_active or v_ego < _MIN_V_EGO:
      self.reset()
      return model_curvature

    if pause_on_signal and turn_signal_active:
      self._correction = float(smooth_value(0.0, self._correction, _SIGNAL_RELEASE_TAU, dt=DT_CTRL))
      return model_curvature + self._correction

    try:
      if model_v2.meta.laneChangeState != log.LaneChangeState.off:
        self.reset()
        return model_curvature
    except (AttributeError, TypeError, ValueError):
      self.reset()
      return model_curvature

    valid, raw_correction = self._raw_correction(
      model_v2,
      v_ego,
      float(np.clip(offset, -_MAX_OFFSET, _MAX_OFFSET)),
      float(np.clip(e2e_authority, 0.0, 1.0)),
    )
    if not valid:
      self.reset()
      return model_curvature

    target = float(np.clip(raw_correction, -_MAX_RAW_CORRECTION, _MAX_RAW_CORRECTION)) * _MAX_GAIN
    self._correction = float(smooth_value(target, self._correction, _SMOOTH_TAU, dt=DT_CTRL))
    return model_curvature + self._correction

  @staticmethod
  def _valid_path(x, y) -> bool:
    return x.size >= 2 and x.size == y.size and np.isfinite(x).all() and np.isfinite(y).all() and np.all(np.diff(x) > 0)

  @staticmethod
  def _covers(x, distance: float) -> bool:
    return bool(x[0] <= distance <= x[-1])

  def _raw_correction(self, model_v2, v_ego: float, offset: float, e2e_authority: float) -> tuple[bool, float]:
    try:
      lane_lines = model_v2.laneLines
      probs = np.asarray(model_v2.laneLineProbs, dtype=float)
      stds = np.asarray(model_v2.laneLineStds, dtype=float)
      if len(lane_lines) < 3 or probs.size < 3 or stds.size < 3:
        return False, 0.0
      if not np.isfinite(probs[[1, 2]]).all() or not np.isfinite(stds[[1, 2]]).all():
        return False, 0.0
      if np.any(probs[[1, 2]] < _MIN_LANE_PROB) or np.any(probs[[1, 2]] > 1.0):
        return False, 0.0
      if np.any(stds[[1, 2]] < 0.0) or np.any(stds[[1, 2]] > _MAX_LANE_STD):
        return False, 0.0

      left_x = np.asarray(lane_lines[1].x, dtype=float)
      left_y = np.asarray(lane_lines[1].y, dtype=float)
      right_x = np.asarray(lane_lines[2].x, dtype=float)
      right_y = np.asarray(lane_lines[2].y, dtype=float)
      pos_x = np.asarray(model_v2.position.x, dtype=float)
      pos_y = np.asarray(model_v2.position.y, dtype=float)
      if not (self._valid_path(left_x, left_y) and self._valid_path(right_x, right_y) and self._valid_path(pos_x, pos_y)):
        return False, 0.0

      lookahead = float(np.clip(v_ego, 8.0, 35.0))
      if not all(self._covers(x, lookahead) for x in (left_x, right_x, pos_x)):
        return False, 0.0

      left = float(np.interp(lookahead, left_x, left_y))
      right = float(np.interp(lookahead, right_x, right_y))
      width = right - left
      if not _MIN_LANE_WIDTH <= width <= _MAX_LANE_WIDTH:
        return False, 0.0

      max_safe_offset = min(_MAX_OFFSET, max(0.0, width * 0.5 - _MIN_CENTER_TO_LINE))
      target_y = 0.5 * (left + right) + float(np.clip(offset, -max_safe_offset, max_safe_offset))
      model_y = float(np.interp(lookahead, pos_x, pos_y))
      error = target_y - model_y

      try:
        pos_y_std = np.asarray(model_v2.position.yStd, dtype=float)
        if self._valid_path(pos_x, pos_y_std):
          path_std = float(np.interp(lookahead, pos_x, pos_y_std))
          if 0.0 <= path_std <= _E2E_MAX_PATH_STD:
            break_in = np.clip(
              (abs(error) - _E2E_BREAK_IN_START) / (_E2E_BREAK_IN_FULL - _E2E_BREAK_IN_START),
              0.0,
              1.0,
            )
            error *= 1.0 - e2e_authority * float(break_in)
      except (AttributeError, TypeError, ValueError):
        pass

      return True, float(2.0 * error / lookahead ** 2)
    except (AttributeError, IndexError, TypeError, ValueError):
      return False, 0.0
