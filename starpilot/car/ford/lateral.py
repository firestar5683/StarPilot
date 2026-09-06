"""Ford lateral-control extensions.

The four-signal curvature strategy, path-angle-primary strategy, manual-turn detector, platform
gains, and related safety protocol are substantially adapted from BluePilot's Ford work, principally
by Alan Polk and additional contributors. The audited bp-7.0 reference is
e1d051d7ba270261b4455068bd68f1a58db15a4a; the missing original source SHA is reconstructed in
CREDITS.md. StarPilot reorganized that work for its own architecture and has since changed its
tuning, lookahead, driver-override handoff, and recovery behavior.

See CREDITS.md for feature-level authorship and upstream commits, and THIRD_PARTY_NOTICES.md for the
published upstream license notices. Upstream contributors do not maintain this adaptation.
"""

from collections import deque
from dataclasses import dataclass
from enum import IntEnum

import numpy as np

from opendbc.car import ACCELERATION_DUE_TO_GRAVITY, DT_CTRL
from opendbc.car.ford.values import CAR, CarControllerParams, FordFlags
from opendbc.car.lateral import AngleSteeringLimits, ISO_LATERAL_ACCEL, apply_std_steer_angle_limits
from openpilot.common.params import Params
from openpilot.selfdrive.modeld.constants import ModelConstants


class FordLateralMode(IntEnum):
  native = 0
  curvature = 1
  angle = 2


# These rate-limit values descend from BluePilot's ``values_ext.py``, which carries the Haibin Wen
# and sunnypilot contributors copyright notice reproduced in THIRD_PARTY_NOTICES.md.
FORD_ANGLE_LIMITS = AngleSteeringLimits(
  0.02,
  ([5, 16, 25], [0.0025, 0.0012, 0.00008]),
  ([5, 16, 25], [0.0025, 0.0014, 0.00018]),
)

MAX_LATERAL_ACCEL = ISO_LATERAL_ACCEL - ACCELERATION_DUE_TO_GRAVITY * 0.06
PATH_ANGLE_MIN = -0.5
PATH_ANGLE_MAX = 0.5235
STEER_DT = CarControllerParams.STEER_STEP * DT_CTRL
CURVATURE_LOOKAHEAD_MIN = 0.20
CURVATURE_LOOKAHEAD_MAX = 0.40
FORD_CURVATURE_LOOKAHEAD = {
  CAR.FORD_EXPLORER_MK6: 0.20,
}
ANGLE_HANDOFF_RECOVERY_SECONDS = 0.75
HANDOFF_PAUSE_MIN_FRAMES = 3
HANDOFF_PAUSE_FRAMES = 6
HANDOFF_COOLDOWN_SECONDS = 2.0
HANDOFF_MAX_PATH_ANGLE = 0.10
LAT_CTL_STATUS_AVAILABLE = 1
STALL_GAP_MIN = 2.0 * CarControllerParams.CURVATURE_ERROR
STALL_HOLD_SECONDS = 0.5
STALL_MAX_RECOVERIES = 3

CANFD_BODY_ON_FRAME = frozenset({
  CAR.FORD_F_150_MK14,
  CAR.FORD_F_150_LIGHTNING_MK1,
  CAR.FORD_EXPEDITION_MK4,
  CAR.FORD_RANGER_MK2,
})
CANFD_UNIBODY = frozenset({
  CAR.FORD_MUSTANG_MACH_E_MK1,
  CAR.FORD_ESCAPE_MK4_5,
})


@dataclass(frozen=True)
class FordLateralResult:
  curvature: float = 0.0
  curvature_rate: float = 0.0
  path_offset: float = 0.0
  path_angle: float = 0.0
  ramp_type: int = 0
  precision_type: int = 1
  active: bool = False
  shadow_curvature: float = 0.0


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
  """Ford polynomial lateral strategies kept outside the native car implementation."""

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

    self.mode = FordLateralMode.curvature
    self.hands_free_cluster_enabled = False
    self.human_turn_enabled = True
    self.curvature_blend_low = 0.4
    self.curvature_blend_high = 0.4
    self.angle_blend = 0.5
    self.curvature_lane_change_factor = 0.85
    self.angle_lane_change_factor = 1.0
    self.angle_low_speed_factor = 1.0
    self.angle_high_speed_factor = 1.0
    self.angle_high_speed_damping = 1.0

    self.human_turn = HumanTurnDetector()
    self.curvature_samples = deque(maxlen=max(2, round(0.3 / STEER_DT)))
    self.path_angle_last = 0.0
    self.curvature_last = 0.0
    self.angle_pause_frames = 0
    self.angle_pause_cooldown = 0.0
    self.angle_handoff_recovery = 0.0
    self.angle_stall_timer = 0.0
    self.angle_stall_recoveries = 0
    self._frame = 0
    self._update_params()

  def _update_params(self):
    try:
      self.mode = FordLateralMode(int(np.clip(self.params.get_int("FordLateralMode", return_default=True), 0, 2)))
    except ValueError:
      self.mode = FordLateralMode.native

    self.hands_free_cluster_enabled = bool(
      self.CP.flags & FordFlags.CANFD and self.params.get_bool("FordHandsFreeCluster"))
    self.human_turn_enabled = self.params.get_bool("FordHumanTurnDetection")
    self.curvature_blend_low = float(np.clip(self.params.get_float("FordCurvatureBlendLow", return_default=True), 0.0, 1.0))
    self.curvature_blend_high = float(np.clip(self.params.get_float("FordCurvatureBlendHigh", return_default=True), 0.0, 1.0))
    self.angle_blend = float(np.clip(self.params.get_float("FordAngleBlend", return_default=True), 0.0, 1.0))
    self.curvature_lane_change_factor = float(np.clip(
      self.params.get_float("FordCurvatureLaneChangeFactor", return_default=True), 0.5, 1.25))
    self.angle_lane_change_factor = float(np.clip(
      self.params.get_float("FordAngleLaneChangeFactor", return_default=True), 0.5, 1.5))
    self.angle_low_speed_factor = float(np.clip(
      self.params.get_float("FordAngleLowSpeedFactor", return_default=True), 0.5, 1.5))
    self.angle_high_speed_factor = float(np.clip(
      self.params.get_float("FordAngleHighSpeedFactor", return_default=True), 0.5, 1.5))
    self.angle_high_speed_damping = float(np.clip(
      self.params.get_float("FordAngleHighSpeedDamping", return_default=True), 0.25, 1.25))

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

  def _blend_and_scale(self, desired: float, predicted: float, v_ego: float, angle_mode: bool) -> tuple[float, int]:
    if angle_mode:
      blend = self.angle_blend
      high_factor = self.angle_lane_change_factor
    else:
      blend = float(np.interp(abs(desired), [0.0, 0.001], [self.curvature_blend_low, self.curvature_blend_high]))
      high_factor = self.curvature_lane_change_factor

    requested = predicted * blend + desired * (1.0 - blend)
    lane_change, direction = self._lane_change()
    precision = 1
    if lane_change:
      factor = float(np.interp(v_ego, [4.4, 40.23], [0.95, high_factor]))
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

  def _reset_handoff(self):
    self.angle_pause_frames = 0
    self.angle_pause_cooldown = 0.0
    self.angle_handoff_recovery = 0.0
    self.angle_stall_timer = 0.0
    self.angle_stall_recoveries = 0

  def _update_angle_driver_override(self, steering_pressed: bool) -> bool:
    if steering_pressed:
      self.angle_handoff_recovery = ANGLE_HANDOFF_RECOVERY_SECONDS
    return steering_pressed

  def _angle_stall_pause_active(self, CS) -> bool:
    self.angle_pause_cooldown = max(0.0, self.angle_pause_cooldown - STEER_DT)
    if self.angle_pause_frames > 0:
      pause_frames_sent = HANDOFF_PAUSE_FRAMES - self.angle_pause_frames
      pscm_available = getattr(CS, "lateral_control_status", None) == LAT_CTL_STATUS_AVAILABLE
      # CAN-FD reports when the mode-0 reset has reached the PSCM. Keep a short minimum
      # dwell, then resume immediately on that acknowledgement; retain the full pulse
      # as a fallback for platforms without the status signal.
      if pause_frames_sent >= HANDOFF_PAUSE_MIN_FRAMES and pscm_available:
        self.angle_pause_frames = 0
        self.angle_pause_cooldown = HANDOFF_COOLDOWN_SECONDS
        return False

      self.angle_pause_frames -= 1
      if self.angle_pause_frames == 0:
        self.angle_pause_cooldown = HANDOFF_COOLDOWN_SECONDS
      return True
    return False

  def _recover_angle_handoff(self, requested: float, current: float) -> float:
    if self.angle_handoff_recovery <= 0.0:
      return requested

    authority = 1.0 - self.angle_handoff_recovery / ANGLE_HANDOFF_RECOVERY_SECONDS
    recovered = current + float(np.clip(authority, 0.0, 1.0)) * (requested - current)
    self.angle_handoff_recovery = max(0.0, self.angle_handoff_recovery - STEER_DT)
    return recovered

  def _inactive_angle_result(self, current_curvature: float) -> FordLateralResult:
    self.path_angle_last = 0.0
    return FordLateralResult(shadow_curvature=current_curvature)

  def update_curvature(self, CC, CS, actuators) -> FordLateralResult:
    current = self._current_curvature(CS)
    if not CC.latActive:
      self.human_turn.reset()
      self._reset_handoff()
      self.curvature_samples.clear()
      self.curvature_last = 0.0
      return FordLateralResult(shadow_curvature=current)

    if self._manual_turn(CC, CS) or CS.out.vEgoRaw < 0.1:
      self._reset_handoff()
      self.curvature_samples.clear()
      self.curvature_last = 0.0
      return FordLateralResult(active=True, shadow_curvature=current)

    v_ego = float(CS.out.vEgoRaw)
    predicted = self._predicted_curvature(v_ego, self._curvature_lookahead())
    requested, precision = self._blend_and_scale(float(actuators.curvature), predicted, v_ego, False)

    if v_ego > 9.0:
      requested = float(np.clip(requested, current - CarControllerParams.CURVATURE_ERROR,
                                current + CarControllerParams.CURVATURE_ERROR))
    applied = float(apply_std_steer_angle_limits(
      requested, self.curvature_last, v_ego, CS.out.steeringAngleDeg, True, FORD_ANGLE_LIMITS))
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

  # Platform grouping and baseline gains descend from Alan Polk's angle-primary implementation
  # (d0aac605f99d37e9da205e419f7989c1e9eaa386); StarPilot applies its own runtime factors below.
  def _platform_angle_gains(self) -> tuple[float, float]:
    if self.CP.carFingerprint in CANFD_BODY_ON_FRAME:
      return 0.95, 0.95
    if self.CP.carFingerprint in CANFD_UNIBODY:
      return 1.0, 1.05
    return 1.0, 1.15

  def update_angle(self, CC, CS, actuators) -> FordLateralResult:
    current = self._current_curvature(CS)
    if not CC.latActive:
      self.human_turn.reset()
      self._reset_handoff()
      return self._inactive_angle_result(current)

    driver_override = self._update_angle_driver_override(bool(CS.out.steeringPressed))
    if self._angle_stall_pause_active(CS):
      return self._inactive_angle_result(current)

    v_ego = float(CS.out.vEgoRaw)
    live_delay = 0.12 if self.sm is None else float(np.clip(self.sm["liveDelay"].lateralDelay, 0.1, 0.15))
    speed_factor = float(np.interp(v_ego, [11.176, 24.587], [1.0, 0.0]))
    curvature_factor = float(np.interp(abs(actuators.curvature), [0.005, 0.02], [1.0, 0.0]))
    lookup_time = live_delay + 0.05 + 0.10 * speed_factor * curvature_factor
    predicted = self._predicted_curvature(v_ego, lookup_time)
    requested, precision = self._blend_and_scale(float(actuators.curvature), predicted, v_ego, True)

    requested_before_deviation_limit = requested
    if v_ego > 9.0:
      requested = float(np.clip(requested, current - CarControllerParams.CURVATURE_ERROR,
                                current + CarControllerParams.CURVATURE_ERROR))
    deviation_limited = abs(requested - requested_before_deviation_limit) > 1e-9

    measured_curvature = float(getattr(CC, "currentCurvature", current))
    if not np.isfinite(measured_curvature):
      measured_curvature = current
    requested = measured_curvature if driver_override else self._recover_angle_handoff(requested, measured_curvature)

    low_gain_high_speed, high_gain_high_speed = self._platform_angle_gains()
    low_gain = float(np.interp(v_ego, [13.5, 26.82],
                               [1.0, low_gain_high_speed * self.angle_high_speed_damping]))
    high_gain = float(np.interp(v_ego, [13.5, 26.82],
                                [1.30 * self.angle_low_speed_factor,
                                 high_gain_high_speed * self.angle_high_speed_factor]))
    gain = float(np.interp(abs(requested), [0.0007, 0.001], [low_gain, high_gain]))
    path_angle = float(np.clip(requested * v_ego * gain, PATH_ANGLE_MIN, PATH_ANGLE_MAX))

    max_delta = float(np.interp(v_ego, [9.0, 10.0, 15.0, 25.0], [0.055, 0.055, 0.0425, 0.009]))
    path_angle = float(np.clip(path_angle, self.path_angle_last - max_delta, self.path_angle_last + max_delta))
    self.path_angle_last = path_angle

    lane_change = self._lane_change()[0]
    # The anti-stall concept and initial thresholds trace to John Christman's upstream work
    # (9012f76666a5c90764fcaec40832b9a607488c27). This active-session recovery is StarPilot-specific.
    stall_gap = float(actuators.curvature) - current
    stalled = (self.human_turn_enabled and not CS.out.steeringPressed and not lane_change and v_ego > 9.0
               and abs(stall_gap) > STALL_GAP_MIN
               and abs(float(actuators.curvature)) > abs(current))
    if stalled:
      if deviation_limited and self.angle_pause_cooldown <= 0.0:
        self.angle_stall_timer += STEER_DT
      if (self.angle_stall_timer + 1e-9 >= STALL_HOLD_SECONDS
          and self.angle_stall_recoveries < STALL_MAX_RECOVERIES
          and abs(self.path_angle_last) < HANDOFF_MAX_PATH_ANGLE):
        self.angle_pause_frames = HANDOFF_PAUSE_FRAMES
        self.angle_stall_timer = 0.0
        self.angle_stall_recoveries += 1
    else:
      self.angle_stall_timer = 0.0
      if CS.out.steeringPressed or abs(stall_gap) < 0.5 * STALL_GAP_MIN:
        self.angle_stall_recoveries = 0

    shadow = current if CS.out.steeringPressed else requested
    return FordLateralResult(
      path_angle=path_angle,
      ramp_type=2,
      precision_type=precision,
      active=True,
      shadow_curvature=shadow,
    )
