from dataclasses import dataclass
import math
from typing import Any, Sequence


KPH_TO_MS = 1.0 / 3.6
RAW_BASE_MASK = 0x02
RAW_RIGHT_MASK = 0x08
RAW_LEFT_MASK = 0x10


@dataclass(frozen=True)
class Ev9SoftwareBsmSideResult:
  detected: bool = False
  escalated: bool = False
  source: str = "neutral"
  confidence: float = 0.0


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

  def __init__(self) -> None:
    self._left = _SideState()
    self._right = _SideState()

  @staticmethod
  def _value(track: Any, name: str, default: Any) -> Any:
    return track.get(name, default) if isinstance(track, dict) else getattr(track, name, default)

  @classmethod
  def _qualified_track(cls, track: Any, v_ego: float, left: bool) -> bool:
    if not bool(cls._value(track, "measured", False)):
      return False

    distance = float(cls._value(track, "dRel", math.nan))
    lateral = float(cls._value(track, "yRel", math.nan))
    relative_speed = float(cls._value(track, "vRel", math.nan))
    if not all(math.isfinite(value) for value in (distance, lateral, relative_speed)):
      return False
    if not cls.TRACK_MIN_DISTANCE <= distance <= cls.TRACK_MAX_DISTANCE:
      return False
    if v_ego + relative_speed < cls.TARGET_MIN_ABS_SPEED:
      return False

    if left:
      return cls.LEFT_TRACK_MIN_LATERAL <= lateral <= cls.LEFT_TRACK_MAX_LATERAL
    return -cls.LEFT_TRACK_MAX_LATERAL <= lateral <= -cls.LEFT_TRACK_MIN_LATERAL

  @classmethod
  def _track_sides(cls, tracks: Sequence[Any], v_ego: float) -> tuple[bool, bool]:
    return (any(cls._qualified_track(track, v_ego, True) for track in tracks),
            any(cls._qualified_track(track, v_ego, False) for track in tracks))

  @classmethod
  def _update_side(cls, state: _SideState, candidate: bool, acquire_allowed: bool) -> bool:
    if candidate and (acquire_allowed or state.detected):
      state.acquire_samples += 1
      if state.detected or state.acquire_samples >= cls.ACQUIRE_SAMPLES:
        state.detected = True
        state.hold_samples = cls.HOLD_SAMPLES
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

  def update(self, *, raw_left: bool, raw_right: bool, fresh: bool, drive: bool,
             v_ego: float, steering_angle_deg: float, left_blinker: bool = False,
             right_blinker: bool = False, hazard: bool = False, reverse: bool = False,
             radar_tracks: Sequence[Any] | None = None) -> Ev9SoftwareBsmResult:
    v_ego = float(v_ego)
    steering_angle_deg = float(steering_angle_deg)
    valid = fresh and drive and not reverse and math.isfinite(v_ego) and math.isfinite(steering_angle_deg) and \
      v_ego >= self.EGO_RESET_SPEED and abs(steering_angle_deg) < self.MAX_STEERING_ANGLE_DEG
    if not valid:
      self.reset()
      return Ev9SoftwareBsmResult()

    tracks = radar_tracks or ()
    left_track, right_track = self._track_sides(tracks, v_ego)
    acquire_allowed = v_ego >= self.EGO_ACQUIRE_SPEED

    # The left raw bit alone produced repeated false positives in a route with
    # no native left warning. Keep its empirical measured-track gate mandatory.
    left_detected = self._update_side(self._left, bool(raw_left and left_track), acquire_allowed)
    right_detected = self._update_side(self._right, bool(raw_right), acquire_allowed)

    simultaneous_blinkers = bool(left_blinker and right_blinker)
    escalation_allowed = not hazard and not simultaneous_blinkers
    left_escalated = bool(left_detected and left_blinker and escalation_allowed)
    right_escalated = bool(right_detected and right_blinker and escalation_allowed)

    left = Ev9SoftwareBsmSideResult(left_detected, left_escalated,
                                    "raw36a_left+measured_track" if left_detected else "neutral",
                                    self.LEFT_CONFIDENCE if left_detected else 0.0)
    right_source = "raw36a_right+measured_track" if right_detected and right_track else \
      "raw36a_right" if right_detected else "neutral"
    right_confidence = self.RIGHT_TRACK_CONFIDENCE if right_detected and right_track else \
      self.RIGHT_CONFIDENCE if right_detected else 0.0
    right = Ev9SoftwareBsmSideResult(right_detected, right_escalated, right_source, right_confidence)
    return Ev9SoftwareBsmResult(left, right)
