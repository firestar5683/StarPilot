"""Pure Ioniq 6 FLM surface math; no controller or saved-state authority.

The controller owns its PID, filters, active state, and torque-source selection.
These functions return values at the existing Ioniq-specific shaping stages.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from openpilot.starpilot.lateral import ioniq6_policy as base


PROFILE = "hyundai_ioniq_6"
SPEED_KNOTS = (0.0, 5.0, 10.0, 15.0, 25.0)
_BOUNDS = {
  "ff_gain_left": (0.0, 0.60), "ff_gain_right": (0.0, 0.60),
  "turn_in_boost_left": (0.40, 2.80), "turn_in_boost_right": (0.40, 2.80),
  "unwind_taper_left": (0.0, 12.0), "unwind_taper_right": (0.0, 12.0),
  "center_taper_max": (0.0, 0.18), "highway_center_taper_max": (0.0, 0.18),
  "turn_in_threshold_reduction_left": (0.0, 2.0), "turn_in_threshold_reduction_right": (0.0, 2.0),
  "unwind_threshold_increase_left": (0.0, 12.0), "unwind_threshold_increase_right": (0.0, 12.0),
  "crawl_turn_in_ff_boost_left": (0.0, 0.50), "crawl_turn_in_ff_boost_right": (0.0, 0.50),
  "low_speed_angle_assist_max_torque": (0.0, 0.80),
  "curvy_speed_min": (4.0, 12.0), "curvy_speed_max": (14.0, 25.0),
  "curvy_turn_in_trim_speed_min": (8.0, 16.0), "curvy_turn_in_trim_speed_max": (14.0, 25.0),
  "curvy_turn_in_trim_left": (0.0, 0.20), "curvy_turn_in_trim_right": (0.0, 0.20),
  "curvy_unwind_floor_relief_left": (0.0, 0.45), "curvy_unwind_floor_relief_right": (0.0, 0.45),
  "curvy_unwind_extra_reduction_left": (0.0, 0.45), "curvy_unwind_extra_reduction_right": (0.0, 0.45),
  "center_deadband_crawl_deg": (0.0, 0.30), "center_deadband_low_deg": (0.0, 0.30),
  "center_deadband_mid_deg": (0.0, 0.20), "center_deadband_fast_deg": (0.0, 0.12),
  "center_deadband_highway_deg": (0.0, 0.08),
}

_DEFAULTS = {
  "ff_gain_left": base.IONIQ_6_FF_GAIN_LEFT, "ff_gain_right": base.IONIQ_6_FF_GAIN_RIGHT,
  "turn_in_boost_left": base.IONIQ_6_TURN_IN_BOOST_LEFT, "turn_in_boost_right": base.IONIQ_6_TURN_IN_BOOST_RIGHT,
  "unwind_taper_left": base.IONIQ_6_UNWIND_TAPER_LEFT, "unwind_taper_right": base.IONIQ_6_UNWIND_TAPER_RIGHT,
  "center_taper_max": base.IONIQ_6_CENTER_TAPER_MAX,
  "highway_center_taper_max": base.IONIQ_6_HIGHWAY_CENTER_TAPER_MAX,
  "turn_in_threshold_reduction_left": base.IONIQ_6_TURN_IN_THRESHOLD_REDUCTION_LEFT,
  "turn_in_threshold_reduction_right": base.IONIQ_6_TURN_IN_THRESHOLD_REDUCTION_RIGHT,
  "unwind_threshold_increase_left": base.IONIQ_6_UNWIND_THRESHOLD_INCREASE_LEFT,
  "unwind_threshold_increase_right": base.IONIQ_6_UNWIND_THRESHOLD_INCREASE_RIGHT,
  "crawl_turn_in_ff_boost_left": base.IONIQ_6_CRAWL_TURN_IN_FF_BOOST_LEFT,
  "crawl_turn_in_ff_boost_right": base.IONIQ_6_CRAWL_TURN_IN_FF_BOOST_RIGHT,
  "low_speed_angle_assist_max_torque": base.IONIQ_6_LOW_SPEED_ANGLE_ASSIST_MAX_TORQUE,
  "curvy_speed_min": base.IONIQ_6_CURVY_SPEED_MIN, "curvy_speed_max": base.IONIQ_6_CURVY_SPEED_MAX,
  "curvy_turn_in_trim_speed_min": base.IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_MIN,
  "curvy_turn_in_trim_speed_max": base.IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_MAX,
  "curvy_turn_in_trim_left": base.IONIQ_6_CURVY_TURN_IN_TRIM_LEFT,
  "curvy_turn_in_trim_right": base.IONIQ_6_CURVY_TURN_IN_TRIM_RIGHT,
  "curvy_unwind_floor_relief_left": base.IONIQ_6_CURVY_UNWIND_FLOOR_RELIEF_LEFT,
  "curvy_unwind_floor_relief_right": base.IONIQ_6_CURVY_UNWIND_FLOOR_RELIEF_RIGHT,
  "curvy_unwind_extra_reduction_left": base.IONIQ_6_CURVY_UNWIND_EXTRA_REDUCTION_LEFT,
  "curvy_unwind_extra_reduction_right": base.IONIQ_6_CURVY_UNWIND_EXTRA_REDUCTION_RIGHT,
  "center_deadband_crawl_deg": 0.0, "center_deadband_low_deg": 0.0,
  "center_deadband_mid_deg": 0.0, "center_deadband_fast_deg": 0.0,
  "center_deadband_highway_deg": 0.0,
}


@dataclass(frozen=True, init=False)
class Ioniq6Surface:
  variant: str
  knobs: Mapping[str, float]

  def __init__(self, variant: str, knobs: Mapping[str, object]):
    object.__setattr__(self, 'variant', variant)
    object.__setattr__(self, 'knobs', knobs)
    self.__post_init__()

  def __post_init__(self):
    if self.variant not in ("standard", "firmware_2025") or not isinstance(self.knobs, Mapping):
      raise ValueError("unsupported Ioniq 6 surface")
    values = dict(_DEFAULTS)
    for name, raw in self.knobs.items():
      if name not in _BOUNDS or isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError("unknown or nonnumeric surface knob")
      try:
        value = float(raw)
      except (OverflowError, ValueError) as exc:
        raise ValueError("surface knob outside frozen bounds") from exc
      low, high = _BOUNDS[name]
      if not math.isfinite(value) or not low <= value <= high:
        raise ValueError("surface knob outside frozen bounds")
      values[name] = value
    if values["curvy_speed_min"] >= values["curvy_speed_max"] or values["curvy_turn_in_trim_speed_min"] >= values["curvy_turn_in_trim_speed_max"]:
      raise ValueError("inverted speed window")
    object.__setattr__(self, "knobs", MappingProxyType(values))

  @classmethod
  def validated(cls, variant: str, knobs: Mapping[str, object]) -> "Ioniq6Surface":
    return cls(variant, knobs)

  def value(self, name: str) -> float:
    return self.knobs[name]


@dataclass(frozen=True)
class SurfaceInput:
  """Pure stage sample with the controller-owned directional filter output.

  Live integration must filter directional_taper_target before evaluating FF.
  The standard-only 2023 unwind multiplier and firmware-2025 output cap remain
  in the caller. Variant is an applicability tag, not a substitute for FW proof.
  """
  speed: float
  setpoint: float
  jerk: float
  desired_angle_deg: float
  actual_angle_deg: float
  output_torque: float
  steering_pressed: bool
  filtered_directional_taper: float

  def __post_init__(self):
    values = (self.speed, self.setpoint, self.jerk, self.desired_angle_deg,
              self.actual_angle_deg, self.output_torque)
    if (type(self.steering_pressed) is not bool or
        any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in values) or
        isinstance(self.filtered_directional_taper, bool) or not isinstance(self.filtered_directional_taper, (int, float))):
      raise ValueError("invalid surface input type")
    try:
      finite = all(math.isfinite(x) for x in values)
    except (OverflowError, ValueError) as exc:
      raise ValueError("invalid surface input") from exc
    if (not finite or not 0.0 <= self.speed <= 90.0 or abs(self.setpoint) > 20.0 or abs(self.jerk) > 20.0 or
        abs(self.desired_angle_deg) > 1080.0 or abs(self.actual_angle_deg) > 1080.0 or abs(self.output_torque) > 1.0):
      raise ValueError("invalid surface input")
    try:
      valid_filtered = math.isfinite(self.filtered_directional_taper) and -2.0 <= self.filtered_directional_taper <= 2.0
    except (OverflowError, ValueError) as exc:
      raise ValueError("invalid filtered directional taper") from exc
    if not valid_filtered:
      raise ValueError("invalid filtered directional taper")


@dataclass(frozen=True)
class SurfaceShape:
  """Controller stage values, not a final torque command.

  FF stage = feedforward_scale * center_taper exactly once, followed by the
  caller's standard-only 2023 unwind multiplier. friction_threshold already
  includes division by center_taper. The directional target must be passed
  through the existing live filter before making SurfaceInput.
  """
  center_deadband_deg: float
  center_taper: float
  directional_taper_target: float
  feedforward_scale: float
  friction_threshold: float
  output_after_angle_assist: float


def _sigmoid(x: float) -> float:
  return base._ioniq_6_sigmoid(x)


def _side(s: Ioniq6Surface, accel: float, name: str) -> float:
  return s.value(f"{name}_{'left' if accel >= 0.0 else 'right'}")


def _window(speed: float, minimum: float, maximum: float, onset_width: float, cutoff_width: float | None = None) -> float:
  return _sigmoid((speed - minimum) / onset_width) * _sigmoid((maximum - speed) / (cutoff_width or onset_width))


def _curvy_turn_in(s: Ioniq6Surface, speed: float, accel: float, turn_in: float) -> float:
  return (_window(speed, s.value("curvy_turn_in_trim_speed_min"), s.value("curvy_turn_in_trim_speed_max"),
                  base.IONIQ_6_CURVY_TURN_IN_TRIM_SPEED_WIDTH) *
          _sigmoid((abs(accel) - base.IONIQ_6_CURVY_TURN_IN_TRIM_LAT_START) / base.IONIQ_6_CURVY_TURN_IN_TRIM_LAT_ONSET_WIDTH) *
          _sigmoid((base.IONIQ_6_CURVY_TURN_IN_TRIM_LAT_END - abs(accel)) / base.IONIQ_6_CURVY_TURN_IN_TRIM_LAT_CUTOFF_WIDTH) * turn_in)


def directional_taper_target(s: Ioniq6Surface, speed: float, accel: float, jerk: float) -> float:
  if accel == 0.0:
    return 1.0
  magnitude = abs(accel)
  phase = math.tanh(accel * jerk / base.IONIQ_6_DIRECTIONAL_TAPER_PHASE_SCALE)
  unwind = max(-phase, 0.0) * _sigmoid((abs(jerk) - base.IONIQ_6_DIRECTIONAL_TAPER_JERK_ONSET) /
                                      base.IONIQ_6_DIRECTIONAL_TAPER_JERK_WIDTH)
  low_relief = (base.IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF *
                _sigmoid((base.IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF_SPEED - speed) /
                         base.IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF_SPEED_WIDTH) *
                _sigmoid((magnitude - base.IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF_LAT) /
                         base.IONIQ_6_DIRECTIONAL_TAPER_LOW_SPEED_RELIEF_LAT_WIDTH) * (1.0 - unwind))
  band = (_sigmoid((magnitude - base.IONIQ_6_DIRECTIONAL_TAPER_LAT_START) / base.IONIQ_6_DIRECTIONAL_TAPER_LAT_WIDTH) *
          _sigmoid((base.IONIQ_6_DIRECTIONAL_TAPER_LAT_END - magnitude) / base.IONIQ_6_DIRECTIONAL_TAPER_LAT_WIDTH))
  heavy = _sigmoid((magnitude - base.IONIQ_6_HEAVY_DIRECTIONAL_TAPER_LAT_START) /
                   base.IONIQ_6_HEAVY_DIRECTIONAL_TAPER_LAT_WIDTH)
  def pick(left: float, right: float) -> float:
    return left if accel >= 0.0 else right
  reduction = band * (pick(base.IONIQ_6_DIRECTIONAL_TAPER_BASE_LEFT, base.IONIQ_6_DIRECTIONAL_TAPER_BASE_RIGHT) * (1.0 - low_relief) +
                      pick(base.IONIQ_6_DIRECTIONAL_TAPER_UNWIND_LEFT, base.IONIQ_6_DIRECTIONAL_TAPER_UNWIND_RIGHT) * unwind)
  reduction += heavy * (pick(base.IONIQ_6_HEAVY_DIRECTIONAL_TAPER_BASE_LEFT, base.IONIQ_6_HEAVY_DIRECTIONAL_TAPER_BASE_RIGHT) * (1.0 - low_relief) +
                        pick(base.IONIQ_6_HEAVY_DIRECTIONAL_TAPER_UNWIND_LEFT, base.IONIQ_6_HEAVY_DIRECTIONAL_TAPER_UNWIND_RIGHT) * unwind)
  reduction += _side(s, accel, "curvy_turn_in_trim") * _curvy_turn_in(s, speed, accel, max(phase, 0.0))
  curvy_phase = unwind if accel >= 0.0 else max(-phase, 0.0) * _sigmoid(
    (abs(jerk) - base.IONIQ_6_CURVY_RIGHT_UNWIND_JERK_ONSET) / base.IONIQ_6_CURVY_RIGHT_UNWIND_JERK_WIDTH)
  curvy_unwind = (_window(speed, s.value("curvy_speed_min"), s.value("curvy_speed_max"),
                           base.IONIQ_6_CURVY_SPEED_MIN_WIDTH, base.IONIQ_6_CURVY_SPEED_MAX_WIDTH) *
                  _sigmoid((magnitude - base.IONIQ_6_CURVY_UNWIND_LAT_START) / base.IONIQ_6_CURVY_UNWIND_LAT_ONSET_WIDTH) *
                  _sigmoid((base.IONIQ_6_CURVY_UNWIND_LAT_END - magnitude) / base.IONIQ_6_CURVY_UNWIND_LAT_CUTOFF_WIDTH) * curvy_phase)
  reduction += _side(s, accel, "curvy_unwind_extra_reduction") * curvy_unwind
  floor = pick(base.IONIQ_6_DIRECTIONAL_TAPER_FLOOR_LEFT, base.IONIQ_6_DIRECTIONAL_TAPER_FLOOR_RIGHT)
  floor -= pick(base.IONIQ_6_DIRECTIONAL_TAPER_UNWIND_FLOOR_LEFT, base.IONIQ_6_DIRECTIONAL_TAPER_UNWIND_FLOOR_RIGHT) * unwind
  floor -= _side(s, accel, "curvy_unwind_floor_relief") * curvy_unwind
  return max(1.0 - reduction, floor)


def center_taper(s: Ioniq6Surface, speed: float, accel: float) -> float:
  magnitude = abs(accel)
  standard = s.value("center_taper_max") * _sigmoid((speed - base.IONIQ_6_CENTER_TAPER_SPEED) / base.IONIQ_6_CENTER_TAPER_SPEED_WIDTH) * _sigmoid(
    (base.IONIQ_6_CENTER_TAPER_LAT - magnitude) / base.IONIQ_6_CENTER_TAPER_LAT_WIDTH)
  highway = s.value("highway_center_taper_max") * _sigmoid((speed - base.IONIQ_6_HIGHWAY_CENTER_TAPER_SPEED) /
    base.IONIQ_6_HIGHWAY_CENTER_TAPER_SPEED_WIDTH) * _sigmoid((base.IONIQ_6_HIGHWAY_CENTER_TAPER_LAT - magnitude) /
    base.IONIQ_6_HIGHWAY_CENTER_TAPER_LAT_WIDTH)
  low_mid = (base.IONIQ_6_LOW_MID_CENTER_TAPER_MAX *
             _window(speed, base.IONIQ_6_LOW_MID_CENTER_TAPER_SPEED_MIN, base.IONIQ_6_LOW_MID_CENTER_TAPER_SPEED_MAX,
                     base.IONIQ_6_LOW_MID_CENTER_TAPER_SPEED_WIDTH) *
             _sigmoid((base.IONIQ_6_LOW_MID_CENTER_TAPER_LAT - magnitude) / base.IONIQ_6_LOW_MID_CENTER_TAPER_LAT_WIDTH))
  return 1.0 - min(standard + highway + low_mid, 0.12)


def center_deadband(s: Ioniq6Surface, speed: float) -> float:
  values = [s.value(f"center_deadband_{name}_deg") for name in ("crawl", "low", "mid", "fast", "highway")]
  return float(np.interp(speed, SPEED_KNOTS, values))


def feedforward_scale(s: Ioniq6Surface, speed: float, accel: float, jerk: float, filtered_directional: float) -> float:
  if accel == 0.0:
    return 1.0
  magnitude = abs(accel)
  gain = _side(s, accel, "ff_gain")
  extra = gain * _sigmoid((magnitude - base.IONIQ_6_FF_ONSET) / base.IONIQ_6_FF_ONSET_WIDTH) * _sigmoid(
    (base.IONIQ_6_FF_CUTOFF - magnitude) / base.IONIQ_6_FF_CUTOFF_WIDTH)
  phase = base._ioniq_6_transition_phase(accel, jerk)
  low = base._ioniq_6_low_speed_factor(speed)
  boost = 1.0 + _side(s, accel, "turn_in_boost") * max(phase, 0.0) * low
  unwind = max(1.0 - _side(s, accel, "unwind_taper") * max(-phase, 0.0) * (0.30 + 0.70 * low), 0.0)
  crawl = 0.0
  if accel * jerk > 0.0:
    crawl = (_side(s, accel, "crawl_turn_in_ff_boost") *
             _sigmoid((base.IONIQ_6_CRAWL_TURN_IN_FF_SPEED - speed) / base.IONIQ_6_CRAWL_TURN_IN_FF_SPEED_WIDTH) *
             _sigmoid((magnitude - base.IONIQ_6_CRAWL_TURN_IN_FF_LAT) / base.IONIQ_6_CRAWL_TURN_IN_FF_LAT_WIDTH))
  right_high = 0.0
  if accel < 0.0 and accel * jerk > 0.0:
    right_high = (base.IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_BOOST *
                  _sigmoid((speed - base.IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_SPEED) /
                           base.IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_SPEED_WIDTH) *
                  _sigmoid((magnitude - base.IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_LAT_START) /
                           base.IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_LAT_WIDTH) *
                  _sigmoid((base.IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_LAT_END - magnitude) /
                           base.IONIQ_6_HIGH_SPEED_RIGHT_TURN_IN_FF_LAT_WIDTH))
  return (1.0 + crawl + right_high + extra * boost * unwind) * filtered_directional


def friction_threshold(s: Ioniq6Surface, speed: float, accel: float, jerk: float) -> float:
  threshold = max(base.get_hkg_canfd_base_friction_threshold(speed), base.IONIQ_6_BASE_FRICTION_THRESHOLD)
  envelope = base._ioniq_6_transition_envelope(speed, accel, jerk)
  phase = base._ioniq_6_transition_phase(accel, jerk)
  unwind_speed = _sigmoid((speed - base.IONIQ_6_UNWIND_HIGH_SPEED_SPEED) / base.IONIQ_6_UNWIND_HIGH_SPEED_SPEED_WIDTH)
  scale = 1.0 - _side(s, accel, "turn_in_threshold_reduction") * envelope * max(phase, 0.0)
  scale += _side(s, accel, "unwind_threshold_increase") * envelope * max(-phase, 0.0) * unwind_speed
  return threshold * min(max(scale, 0.82), 1.18)


def low_speed_output(s: Ioniq6Surface, i: SurfaceInput) -> float:
  if i.steering_pressed:
    return i.output_torque
  # Only the turn-in maximum is profile-controlled; keep the unwind and pose gates.
  angle_error = i.desired_angle_deg - i.actual_angle_deg
  if i.desired_angle_deg * angle_error <= 0.0:
    return base.get_ioniq_6_low_speed_angle_assist_torque(i.desired_angle_deg, i.actual_angle_deg, i.output_torque, i.speed)
  speed_weight = _sigmoid((base.IONIQ_6_LOW_SPEED_ANGLE_ASSIST_SPEED - i.speed) / base.IONIQ_6_LOW_SPEED_ANGLE_ASSIST_SPEED_WIDTH)
  error_weight = _sigmoid((abs(angle_error) - base.IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ERROR) / base.IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ERROR_WIDTH)
  desired_weight = _sigmoid((abs(i.desired_angle_deg) - base.IONIQ_6_LOW_SPEED_ANGLE_ASSIST_DESIRED_ANGLE) /
                            base.IONIQ_6_LOW_SPEED_ANGLE_ASSIST_DESIRED_ANGLE_WIDTH)
  tracking_ratio = abs(i.actual_angle_deg) / max(abs(i.desired_angle_deg), 1e-3)
  tracking = max(1.0 - _sigmoid((tracking_ratio - base.IONIQ_6_LOW_SPEED_ANGLE_ASSIST_TRACK_RATIO_START) /
                                base.IONIQ_6_LOW_SPEED_ANGLE_ASSIST_TRACK_RATIO_WIDTH),
                 base.IONIQ_6_LOW_SPEED_ANGLE_ASSIST_TRACK_RATIO_FLOOR)
  assist = math.copysign(s.value("low_speed_angle_assist_max_torque") * speed_weight * error_weight * desired_weight * tracking,
                         -angle_error)
  if abs(assist) < 1e-4:
    return i.output_torque
  if i.output_torque * assist >= 0.0:
    assist *= float(np.interp(abs(i.output_torque), base.IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ADD_BP,
                              base.IONIQ_6_LOW_SPEED_ANGLE_ASSIST_ADD_V))
  return float(np.clip(i.output_torque + assist, -1.0, 1.0))


def evaluate(s: Ioniq6Surface, i: SurfaceInput) -> SurfaceShape:
  taper = directional_taper_target(s, i.speed, i.setpoint, i.jerk)
  center = center_taper(s, i.speed, i.setpoint)
  return SurfaceShape(center_deadband(s, i.speed), center, taper,
                      feedforward_scale(s, i.speed, i.setpoint, i.jerk, i.filtered_directional_taper),
                      friction_threshold(s, i.speed, i.setpoint, i.jerk) / max(center, 1e-3),
                      low_speed_output(s, i))
