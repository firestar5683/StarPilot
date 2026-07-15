from collections.abc import Sequence
from dataclasses import dataclass
import math
from typing import Any


KPH_TO_MS = 1.0 / 3.6
RAW_BASE_MASK = 0x02
RAW_RIGHT_MASK = 0x08
RAW_LEFT_MASK = 0x10


@dataclass(frozen=True)
class Ev9SoftwareBsmProfile:
  """Versioned, immutable thresholds for the EV9 shadow estimator.

  Scores describe retained-signal evidence only. They are deliberately not a
  probability or a claim that the result matches the missing ADAS_DRV fusion.
  """
  version: str = "ev9-retained-signals-v1"
  update_hz: int = 20
  acquire_samples: int = 2
  hold_samples: int = 4
  left_hold_samples: int | None = None
  right_hold_samples: int | None = None
  ego_acquire_speed: float = 40.0 * KPH_TO_MS
  ego_reset_speed: float = 20.0 * KPH_TO_MS
  target_min_abs_speed: float = 10.0 * KPH_TO_MS
  max_steering_angle_deg: float = 10.0
  track_ego_min_speed: float = 0.0
  track_max_steering_angle_deg: float = math.inf
  track_min_distance: float = 0.0
  track_max_distance: float = 50.0
  left_track_min_lateral: float = 2.5
  left_track_max_lateral: float = 3.5
  right_track_min_lateral: float = -3.5
  right_track_max_lateral: float = -2.5
  left_track_required: bool = True
  right_track_required: bool = False
  left_raw_required: bool = True
  right_raw_required: bool = True
  left_raw_score: float = 0.34
  right_raw_score: float = 0.54
  left_track_score: float = 0.34
  right_track_score: float = 0.06
  left_candidate_score: float = 0.68
  right_candidate_score: float = 0.54


EV9_SOFTWARE_BSM_PROFILE_V1 = Ev9SoftwareBsmProfile()

# Experimental second shadow only. This deliberately favors touching every
# stock warning episode over matching the native lamp frame-by-frame. It is
# never selected by any comma, vehicle, mirror, sound, or haptic output gate.
EV9_SOFTWARE_BSM_EPISODE_PROFILE_V1 = Ev9SoftwareBsmProfile(
  version="ev9-episode-recall-shadow-v1",
  acquire_samples=1,
  left_hold_samples=30 * 20,
  right_hold_samples=25 * 20,
  ego_acquire_speed=0.0,
  ego_reset_speed=0.0,
  max_steering_angle_deg=math.inf,
  track_ego_min_speed=40.0 * KPH_TO_MS,
  track_max_steering_angle_deg=10.0,
  left_track_required=False,
  left_raw_required=False,
  left_raw_score=0.5,
  left_track_score=0.5,
  left_candidate_score=0.5,
)


@dataclass(frozen=True)
class Ev9SoftwareBsmSideDiagnostics:
  profile_version: str = EV9_SOFTWARE_BSM_PROFILE_V1.version
  raw_candidate: bool = False
  track_candidate: bool = False
  candidate: bool = False
  score: float = 0.0
  reject_reason: str = "not_evaluated"
  acquire_samples: int = 0
  hold_samples: int = 0


@dataclass(frozen=True)
class Ev9SoftwareBsmSideResult:
  detected: bool = False
  escalated: bool = False
  source: str = "neutral"
  confidence: float = 0.0
  diagnostics: Ev9SoftwareBsmSideDiagnostics = Ev9SoftwareBsmSideDiagnostics()


@dataclass(frozen=True)
class Ev9SoftwareBsmResult:
  left: Ev9SoftwareBsmSideResult = Ev9SoftwareBsmSideResult()
  right: Ev9SoftwareBsmSideResult = Ev9SoftwareBsmSideResult()
  # This estimator is not equivalent to the ADAS_DRV BCW decision. Integration
  # must opt in separately before using it for a vehicle-facing display.
  shadow_only: bool = True


@dataclass(frozen=True)
class Ev9SoftwareBsmOutputs:
  comma_override: bool = False
  comma_left: bool = False
  comma_right: bool = False
  vehicle_left: bool = False
  vehicle_right: bool = False
  vehicle_left_escalated: bool = False
  vehicle_right_escalated: bool = False


def select_ev9_software_bsm_outputs(result: Ev9SoftwareBsmResult, *, detector_enabled: bool,
                                    comma_output_enabled: bool, vehicle_output_enabled: bool,
                                    native_fresh: bool, native_left: bool, native_right: bool) -> Ev9SoftwareBsmOutputs:
  """Apply the independent publication gates while preserving fresh native BSM."""
  comma_override = bool(detector_enabled and comma_output_enabled and not native_fresh)
  vehicle_allowed = bool(vehicle_output_enabled and (native_fresh or detector_enabled))
  if native_fresh:
    vehicle_left, vehicle_right = bool(native_left), bool(native_right)
    left_escalated = right_escalated = False
  else:
    vehicle_left, vehicle_right = result.left.detected, result.right.detected
    left_escalated, right_escalated = result.left.escalated, result.right.escalated

  return Ev9SoftwareBsmOutputs(
    comma_override=comma_override,
    comma_left=result.left.detected if comma_override else False,
    comma_right=result.right.detected if comma_override else False,
    vehicle_left=vehicle_left if vehicle_allowed else False,
    vehicle_right=vehicle_right if vehicle_allowed else False,
    vehicle_left_escalated=left_escalated if vehicle_allowed else False,
    vehicle_right_escalated=right_escalated if vehicle_allowed else False,
  )


@dataclass
class _SideState:
  acquire_samples: int = 0
  hold_samples: int = 0
  detected: bool = False

  def reset(self) -> None:
    self.acquire_samples = 0
    self.hold_samples = 0
    self.detected = False


class Ev9SoftwareBsmDetector:
  """Experimental, display-only EV9 blind-spot estimator.

  The retained EV9 CAN streams contain object geometry but not ADAS_DRV's
  fused BCW decision. Cross-route stock comparisons found that raw 0x36A and
  radar geometry have limited recall and asymmetric precision. This class is
  therefore intentionally shadow-only by default and must never feed
  longitudinal actuation, AEB, or BCA behavior. A separately gated comma
  output can conservatively inhibit lane changes after shadow validation.

  The right side uses the conservative raw-0x36A correlation. The left side
  additionally requires the narrow measured-track gate that removed the
  all-negative-route ghosts in the reference data. That asymmetry is empirical,
  not a claimed physical interpretation of the radar track.
  """

  UPDATE_HZ = 20
  ACQUIRE_SAMPLES = 2   # 0.10 s at 20 Hz
  HOLD_SAMPLES = 4      # 0.20 s at 20 Hz

  # Stock/owner-manual-style speed hysteresis: acquire at 40 km/h and clear
  # immediately below 20 km/h. Existing state may remain between the two.
  EGO_ACQUIRE_SPEED = 40.0 * KPH_TO_MS
  EGO_RESET_SPEED = 20.0 * KPH_TO_MS
  TARGET_MIN_ABS_SPEED = 10.0 * KPH_TO_MS
  MAX_STEERING_ANGLE_DEG = 10.0

  TRACK_MIN_DISTANCE = 0.0
  TRACK_MAX_DISTANCE = 50.0
  LEFT_TRACK_MIN_LATERAL = 2.5
  LEFT_TRACK_MAX_LATERAL = 3.5

  LEFT_CONFIDENCE = 0.68
  RIGHT_CONFIDENCE = 0.54
  RIGHT_TRACK_CONFIDENCE = 0.60

  def __init__(self, profile: Ev9SoftwareBsmProfile = EV9_SOFTWARE_BSM_PROFILE_V1) -> None:
    self.profile = profile
    self._left = _SideState()
    self._right = _SideState()

  @staticmethod
  def _value(track: Any, name: str, default: Any) -> Any:
    return track.get(name, default) if isinstance(track, dict) else getattr(track, name, default)

  def _qualified_track(self, track: Any, v_ego: float, left: bool) -> bool:
    if not bool(self._value(track, "measured", False)):
      return False

    distance = float(self._value(track, "dRel", math.nan))
    lateral = float(self._value(track, "yRel", math.nan))
    relative_speed = float(self._value(track, "vRel", math.nan))
    if not all(math.isfinite(value) for value in (distance, lateral, relative_speed)):
      return False
    if not self.profile.track_min_distance <= distance <= self.profile.track_max_distance:
      return False
    if v_ego + relative_speed < self.profile.target_min_abs_speed:
      return False

    if left:
      return self.profile.left_track_min_lateral <= lateral <= self.profile.left_track_max_lateral
    return self.profile.right_track_min_lateral <= lateral <= self.profile.right_track_max_lateral

  def _track_sides(self, tracks: Sequence[Any], v_ego: float) -> tuple[bool, bool]:
    return (any(self._qualified_track(track, v_ego, True) for track in tracks),
            any(self._qualified_track(track, v_ego, False) for track in tracks))

  def _update_side(self, state: _SideState, candidate: bool, acquire_allowed: bool, hold_samples: int) -> bool:
    if candidate and (acquire_allowed or state.detected):
      state.acquire_samples += 1
      if state.detected or state.acquire_samples >= self.profile.acquire_samples:
        state.detected = True
        state.hold_samples = hold_samples
      return state.detected

    state.acquire_samples = 0
    if state.detected and state.hold_samples > 0:
      state.hold_samples -= 1
      return True

    state.detected = False
    state.hold_samples = 0
    return False

  def reset(self) -> None:
    self._left.reset()
    self._right.reset()

  def _hold_samples(self, left: bool) -> int:
    side_override = self.profile.left_hold_samples if left else self.profile.right_hold_samples
    return self.profile.hold_samples if side_override is None else side_override

  def _diagnostics(self, state: _SideState, *, raw: bool, track: bool, left: bool,
                   candidate: bool, score: float, context_reject_reason: str | None,
                   acquire_allowed: bool) -> Ev9SoftwareBsmSideDiagnostics:
    if context_reject_reason is not None:
      reject_reason = context_reject_reason
    elif state.detected and not candidate:
      reject_reason = "holding"
    elif (self.profile.left_raw_required if left else self.profile.right_raw_required) and not raw:
      reject_reason = "no_raw_candidate"
    elif (self.profile.left_track_required if left else self.profile.right_track_required) and not track:
      reject_reason = "track_required"
    elif not raw and not track:
      reject_reason = "no_evidence"
    elif not candidate:
      reject_reason = "below_score_threshold"
    elif not acquire_allowed and not state.detected:
      reject_reason = "below_acquire_speed"
    elif not state.detected:
      reject_reason = "acquiring"
    else:
      reject_reason = "active"

    return Ev9SoftwareBsmSideDiagnostics(
      profile_version=self.profile.version,
      raw_candidate=raw,
      track_candidate=track,
      candidate=candidate,
      score=score,
      reject_reason=reject_reason,
      acquire_samples=state.acquire_samples,
      hold_samples=state.hold_samples,
    )

  def update(self, *, raw_left: bool, raw_right: bool, fresh: bool, drive: bool,
             v_ego: float, steering_angle_deg: float, left_blinker: bool = False,
             right_blinker: bool = False, hazard: bool = False, reverse: bool = False,
             radar_tracks: Sequence[Any] | None = None) -> Ev9SoftwareBsmResult:
    v_ego = float(v_ego)
    steering_angle_deg = float(steering_angle_deg)
    context_reject_reason = None
    if not fresh:
      context_reject_reason = "stale_raw"
    elif reverse:
      context_reject_reason = "reverse"
    elif not drive:
      context_reject_reason = "not_drive"
    elif not math.isfinite(v_ego):
      context_reject_reason = "invalid_speed"
    elif v_ego < self.profile.ego_reset_speed:
      context_reject_reason = "below_reset_speed"
    elif not math.isfinite(steering_angle_deg):
      context_reject_reason = "invalid_steering_angle"
    elif abs(steering_angle_deg) >= self.profile.max_steering_angle_deg:
      context_reject_reason = "steering_angle"

    if context_reject_reason is not None:
      self.reset()
      left_score = self.profile.left_raw_score if raw_left else 0.0
      right_score = self.profile.right_raw_score if raw_right else 0.0
      left_diagnostics = self._diagnostics(self._left, raw=bool(raw_left), track=False, left=True,
                                           candidate=False, score=left_score,
                                           context_reject_reason=context_reject_reason, acquire_allowed=False)
      right_diagnostics = self._diagnostics(self._right, raw=bool(raw_right), track=False, left=False,
                                            candidate=False, score=right_score,
                                            context_reject_reason=context_reject_reason, acquire_allowed=False)
      return Ev9SoftwareBsmResult(Ev9SoftwareBsmSideResult(diagnostics=left_diagnostics),
                                  Ev9SoftwareBsmSideResult(diagnostics=right_diagnostics))

    tracks = radar_tracks or ()
    left_track, right_track = self._track_sides(tracks, v_ego)
    if v_ego < self.profile.track_ego_min_speed or abs(steering_angle_deg) >= self.profile.track_max_steering_angle_deg:
      left_track = right_track = False
    acquire_allowed = v_ego >= self.profile.ego_acquire_speed

    left_score = min(1.0, (self.profile.left_raw_score if raw_left else 0.0) +
                     (self.profile.left_track_score if left_track else 0.0))
    right_score = min(1.0, (self.profile.right_raw_score if raw_right else 0.0) +
                      (self.profile.right_track_score if right_track else 0.0))
    left_candidate = bool((raw_left or not self.profile.left_raw_required) and
                          (left_track or not self.profile.left_track_required) and
                          left_score >= self.profile.left_candidate_score)
    right_candidate = bool((raw_right or not self.profile.right_raw_required) and
                           (right_track or not self.profile.right_track_required) and
                           right_score >= self.profile.right_candidate_score)

    # The default profile keeps the empirical left measured-track gate that
    # removed repeated raw-bit ghosts. Experimental profiles may deliberately
    # choose a different evidence policy while remaining shadow-only.
    left_detected = self._update_side(self._left, left_candidate, acquire_allowed, self._hold_samples(True))
    right_detected = self._update_side(self._right, right_candidate, acquire_allowed, self._hold_samples(False))

    left_diagnostics = self._diagnostics(self._left, raw=bool(raw_left), track=left_track, left=True,
                                         candidate=left_candidate, score=left_score,
                                         context_reject_reason=None, acquire_allowed=acquire_allowed)
    right_diagnostics = self._diagnostics(self._right, raw=bool(raw_right), track=right_track, left=False,
                                          candidate=right_candidate, score=right_score,
                                          context_reject_reason=None, acquire_allowed=acquire_allowed)

    simultaneous_blinkers = bool(left_blinker and right_blinker)
    escalation_allowed = not hazard and not simultaneous_blinkers
    left_escalated = bool(left_detected and left_blinker and escalation_allowed)
    right_escalated = bool(right_detected and right_blinker and escalation_allowed)

    left_source = "raw36a_left+measured_track" if left_detected and raw_left and left_track else \
      "raw36a_left" if left_detected and raw_left else "measured_track_left" if left_detected and left_track else \
      "held" if left_detected else "neutral"
    left = Ev9SoftwareBsmSideResult(left_detected, left_escalated, left_source,
                                    self.LEFT_CONFIDENCE if left_detected else 0.0, left_diagnostics)
    right_source = "raw36a_right+measured_track" if right_detected and right_track else \
      "raw36a_right" if right_detected and raw_right else "held" if right_detected else "neutral"
    right_confidence = self.RIGHT_TRACK_CONFIDENCE if right_detected and right_track else \
      self.RIGHT_CONFIDENCE if right_detected else 0.0
    right = Ev9SoftwareBsmSideResult(right_detected, right_escalated, right_source, right_confidence,
                                     right_diagnostics)
    return Ev9SoftwareBsmResult(left, right)
