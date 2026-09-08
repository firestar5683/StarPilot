"""Ford lateral-control extensions.

The extended curvature strategy, manual-turn detector, and related safety protocol are substantially
adapted from BluePilot's Ford work, principally by Alan Polk and additional contributors. The audited
bp-7.0 reference is e1d051d7ba270261b4455068bd68f1a58db15a4a; the missing original source SHA is
reconstructed in CREDITS.md. StarPilot reorganized that work for its own architecture and has since
changed its tuning and lookahead behavior.

See CREDITS.md for feature-level authorship and upstream commits, and THIRD_PARTY_NOTICES.md for the
published upstream license notices. Upstream contributors do not maintain this adaptation.
"""

from collections import deque
from dataclasses import dataclass

import numpy as np

from opendbc.car import ACCELERATION_DUE_TO_GRAVITY, DT_CTRL
from opendbc.car.ford.values import CAR, CarControllerParams, FordFlags
from opendbc.car.lateral import AngleSteeringLimits, ISO_LATERAL_ACCEL, apply_std_steer_angle_limits
from openpilot.common.params import Params
from openpilot.selfdrive.modeld.constants import ModelConstants


# These rate-limit values descend from BluePilot's ``values_ext.py``, which carries the Haibin Wen
# and sunnypilot contributors copyright notice reproduced in THIRD_PARTY_NOTICES.md.
FORD_CURVATURE_LIMITS = AngleSteeringLimits(
  0.02,
  ([5, 16, 25], [0.0025, 0.0012, 0.00008]),
  ([5, 16, 25], [0.0025, 0.0014, 0.00018]),
)

MAX_LATERAL_ACCEL = ISO_LATERAL_ACCEL - ACCELERATION_DUE_TO_GRAVITY * 0.06
STEER_DT = CarControllerParams.STEER_STEP * DT_CTRL
CURVATURE_LOOKAHEAD_MIN = 0.20
CURVATURE_LOOKAHEAD_MAX = 0.40
FORD_CURVATURE_LOOKAHEAD = {
  CAR.FORD_EXPLORER_MK6: 0.20,
}


@dataclass(frozen=True)
class FordLateralResult:
  curvature: float = 0.0
  curvature_rate: float = 0.0
  ramp_type: int = 0
  precision_type: int = 1
  active: bool = False


# Adapted from BluePilot HumanTurnDetector (Alan Polk, 97867c1eb57b7472f6fc3de62f0fef576e5a5497).
class HumanTurnDetector:
  ANGLE_DEG = 45.0
  HOLD_SECONDS = 1.5
  PRETURNED_HOLD_SECONDS = 3.0

  def __init__(self):
    self.timer = 0.0
    self.active = False
    self._pressed_last = False
    self._press_started_preturned = False

  def update(self, enabled: bool, steering_pressed: bool, steering_angle_deg: float) -> bool:
    if steering_pressed and not self._pressed_last:
      self._press_started_preturned = abs(steering_angle_deg) > self.ANGLE_DEG
    self._pressed_last = steering_pressed

    if enabled and steering_pressed and abs(steering_angle_deg) > self.ANGLE_DEG:
      self.timer += STEER_DT
    else:
      self.timer = 0.0

    hold_time = self.PRETURNED_HOLD_SECONDS if self._press_started_preturned else self.HOLD_SECONDS
    self.active = self.timer + 1e-9 >= hold_time
    return self.active

  def reset(self):
    self.timer = 0.0
    self.active = False
    self._pressed_last = False
    self._press_started_preturned = False


class FordLateralController:

  def __init__(self, CP):
    self.CP = CP
    self.params = Params(return_defaults=True)
    try:
      import cereal.messaging as messaging
      self.sm = messaging.SubMaster(["modelV2", "liveDelay"])
    except ImportError:
      # The host interface tests don't load the device messaging extension.
      self.sm = None
    self.model = None

    self.hands_free_cluster_enabled = False
    self.human_turn_enabled = True
    self.curvature_blend_low = 0.4
    self.curvature_blend_high = 0.4
    self.curvature_lane_change_factor = 0.85

    self.human_turn = HumanTurnDetector()
    self.curvature_samples = deque(maxlen=max(2, round(0.3 / STEER_DT)))
    self.curvature_last = 0.0
    self._frame = 0
    self._update_params()

  def _update_params(self):
    self.hands_free_cluster_enabled = bool(
      self.CP.flags & FordFlags.CANFD and self.params.get_bool("FordHandsFreeCluster"))
    self.human_turn_enabled = self.params.get_bool("FordHumanTurnDetection")
    self.curvature_blend_low = float(np.clip(self.params.get_float("FordCurvatureBlendLow", return_default=True), 0.0, 1.0))
    self.curvature_blend_high = float(np.clip(self.params.get_float("FordCurvatureBlendHigh", return_default=True), 0.0, 1.0))
    self.curvature_lane_change_factor = float(np.clip(
      self.params.get_float("FordCurvatureLaneChangeFactor", return_default=True), 0.5, 1.25))

  def update_inputs(self):
    if self.sm is not None:
      self.sm.update(0)
      if self.sm.updated["modelV2"]:
        self.model = self.sm["modelV2"]
    if self._frame % 100 == 0:
      self._update_params()
    self._frame += 1

  def _predicted_curvature(self, v_ego: float, lookup_time: float) -> float:
    if self.model is None or len(self.model.orientationRate.z) < 17:
      return 0.0
    curvatures = np.asarray(self.model.orientationRate.z) / max(v_ego, 0.01)
    return float(np.interp(lookup_time, ModelConstants.T_IDXS, curvatures))

  def _curvature_lookahead(self) -> float:
    if self.CP.carFingerprint in FORD_CURVATURE_LOOKAHEAD:
      return FORD_CURVATURE_LOOKAHEAD[self.CP.carFingerprint]
    if self.sm is None:
      return CURVATURE_LOOKAHEAD_MIN
    live_delay = float(self.sm["liveDelay"].lateralDelay)
    if not np.isfinite(live_delay):
      return CURVATURE_LOOKAHEAD_MIN
    return float(np.clip(live_delay, CURVATURE_LOOKAHEAD_MIN, CURVATURE_LOOKAHEAD_MAX))

  def _lane_change(self) -> tuple[bool, int]:
    if self.model is None:
      return False, 0
    state = int(getattr(self.model.meta.laneChangeState, "raw", self.model.meta.laneChangeState))
    direction = int(getattr(self.model.meta.laneChangeDirection, "raw", self.model.meta.laneChangeDirection))
    return state in (1, 2, 3), direction

  @staticmethod
  def _current_curvature(CS) -> float:
    return -CS.out.yawRate / max(CS.out.vEgoRaw, 0.1)

  def _blend_and_scale(self, desired: float, predicted: float, v_ego: float) -> tuple[float, int]:
    blend = float(np.interp(abs(desired), [0.0, 0.001], [self.curvature_blend_low, self.curvature_blend_high]))
    requested = predicted * blend + desired * (1.0 - blend)
    lane_change, direction = self._lane_change()
    precision = 1
    if lane_change:
      factor = float(np.interp(v_ego, [4.4, 40.23], [0.95, self.curvature_lane_change_factor]))
      if (direction == 1 and requested < 0.0) or (direction == 2 and requested > 0.0):
        requested *= factor
        precision = 0
    return requested, precision

  def _manual_turn(self, CC, CS) -> bool:
    if not CC.latActive:
      self.human_turn.reset()
      return False
    return self.human_turn.update(
      self.human_turn_enabled, CS.out.steeringPressed, CS.out.steeringAngleDeg)

  def update(self, CC, CS, actuators) -> FordLateralResult:
    current = self._current_curvature(CS)
    if not CC.latActive:
      self.human_turn.reset()
      self.curvature_samples.clear()
      self.curvature_last = 0.0
      return FordLateralResult()

    if self._manual_turn(CC, CS) or CS.out.vEgoRaw < 0.1:
      self.curvature_samples.clear()
      self.curvature_last = 0.0
      return FordLateralResult(active=True)

    v_ego = float(CS.out.vEgoRaw)
    predicted = self._predicted_curvature(v_ego, self._curvature_lookahead())
    requested, precision = self._blend_and_scale(float(actuators.curvature), predicted, v_ego)

    if v_ego > 9.0:
      requested = float(np.clip(requested, current - CarControllerParams.CURVATURE_ERROR,
                                current + CarControllerParams.CURVATURE_ERROR))
    applied = float(apply_std_steer_angle_limits(
      requested, self.curvature_last, v_ego, CS.out.steeringAngleDeg, True, FORD_CURVATURE_LIMITS))
    if self.CP.flags & FordFlags.CANFD:
      max_curvature = MAX_LATERAL_ACCEL / max(v_ego, 1.0) ** 2
      applied = float(np.clip(applied, -max_curvature, max_curvature))

    self.curvature_samples.append(predicted)
    curvature_rate = 0.0
    if len(self.curvature_samples) > 1:
      sample_time = (len(self.curvature_samples) - 1) * STEER_DT
      curvature_rate = (self.curvature_samples[-1] - self.curvature_samples[0]) / max(sample_time * v_ego, 0.01)
      curvature_rate *= float(np.interp(abs(predicted), [0.0, 0.008, 0.01], [0.0, 0.0, 1.0]))
      curvature_rate *= float(np.interp(v_ego, [0.0, 14.5, 15.5], [1.0, 1.0, 0.0]))
      if self._lane_change()[0]:
        curvature_rate = 0.0

    self.curvature_last = float(np.clip(applied, -0.02, 0.02))
    curvature_rate = float(np.clip(curvature_rate, -0.001024, 0.001023))
    return FordLateralResult(
      curvature=self.curvature_last,
      curvature_rate=curvature_rate,
      ramp_type=2,
      precision_type=precision,
      active=True,
    )
