"""Angle-primary Ford steering adapted from Alan Polk's BluePilot bp-7.0.

Source e1d051d7ba270261b4455068bd68f1a58db15a4a lateral_angle_ext.py.
See ../LICENSE, ../LICENSE.md and ../CREDITS.md. This core has no vehicle,
openpilot, Params, messaging or model-constant imports.
"""
from dataclasses import dataclass
import math
from ..params import limits as bounds
from .trim import LaneCenterTrim, LaneGeometry, TrimConfig


def clip(value, low, high):
  return max(low, min(high, value))


def interp(value, xs, ys):
  if value <= xs[0]:
    return ys[0]
  for i in range(1, len(xs)):
    if value < xs[i]:
      return ys[i - 1] + (ys[i] - ys[i - 1]) * (value - xs[i - 1]) / (xs[i] - xs[i - 1])
  return ys[-1]


@dataclass(frozen=True)
class Inputs:
  active: bool
  speed: float
  measured_curvature: float
  desired_curvature: float
  steering_pressed: bool = False
  steering_angle: float = 0.0
  yaw_predictions: tuple = ()
  time_indices: tuple = ()
  lateral_delay: float = 0.15
  lane_change: bool = False
  lane_direction: int = 0
  limit_status: int = 0
  geometry: LaneGeometry | None = None


@dataclass(frozen=True)
class Command:
  active: bool = False
  path_angle: float = 0.0
  shadow_curvature: float = 0.0
  precision: int = 1


class AngleController:
  def __init__(self, *, low_gain=1.0, high_gain=1.15, trim_config=None):
    self.trim_config = TrimConfig() if trim_config is None else trim_config
    self.trim = LaneCenterTrim()
    self.low_gain = low_gain
    self.high_gain = high_gain
    self.path_last = 0.0
    self.speed_last = 0.1
    self.desired_last = 0.0
    self.human_timer = 0.0
    self.press_last = False
    self.preturned = False
    self.press_timer = 0.0
    self.blip_frames = 0
    self.blip_cooldown = 0.0
    self.blip_hold = 0.0
    self.blip_count = 0

  def reset(self):
    self.trim.reset()
    self.path_last = 0.0
    self.speed_last = 0.1
    self.desired_last = 0.0
    self.human_timer = 0.0
    self.press_last = False
    self.preturned = False
    self.press_timer = 0.0
    self.blip_frames = 0
    self.blip_cooldown = 0.0
    self.blip_hold = 0.0
    self.blip_count = 0

  def step(self, i: Inputs) -> Command:
    values = (i.speed, i.measured_curvature, i.desired_curvature, i.steering_angle, i.lateral_delay)
    if not i.active or not all(math.isfinite(v) for v in values) or i.speed < 0.0:
      self.reset()
      return Command()
    if i.steering_pressed and not self.press_last:
      self.preturned = abs(i.steering_angle) > 45.0
    self.press_last = i.steering_pressed
    self.human_timer = self.human_timer + 0.05 if i.steering_pressed and abs(i.steering_angle) > 45.0 else 0.0
    if self.human_timer + 1e-9 >= (3.0 if self.preturned else 1.5):
      self.trim.reset()
      self.path_last = 0.0
      self.desired_last = i.desired_curvature
      self.blip_frames = self.blip_count = 0
      self.blip_hold = self.blip_cooldown = self.press_timer = 0.0
      return Command()
    if i.steering_pressed:
      self.press_timer += 0.05
    else:
      if self.press_timer >= 0.5 and self.blip_cooldown <= 0.0 and self.blip_frames <= 0 and abs(self.path_last) < 0.1:
        self.blip_frames = 6
      self.press_timer = 0.0
    if self.blip_frames > 0:
      self.blip_frames -= 1
      self.trim.reset()
      self.path_last = 0.0
      self.desired_last = i.desired_curvature
      if self.blip_frames == 0:
        self.blip_cooldown = 2.0
      return Command()

    base = clip(i.lateral_delay, 0.1, 0.15) + 0.05
    predictions_valid = (len(i.yaw_predictions) == len(i.time_indices) and len(i.time_indices) >= 17 and
                         all(math.isfinite(v) for v in (*i.yaw_predictions, *i.time_indices)) and
                         all(b > a for a, b in zip(i.time_indices, i.time_indices[1:], strict=False)))
    curves = tuple(y / max(0.01, i.speed) for y in i.yaw_predictions) if predictions_valid else ()
    entering = bool(curves) and abs(interp(base, i.time_indices, curves)) > abs(i.desired_curvature)
    factor = 1.0 if entering else interp(abs(i.desired_curvature), (0.005, 0.020), (1.0, 0.0))
    lookup = base + bounds.VLT_EXTRA * interp(i.speed, (11.176, 24.5872), (1.0, 0.0)) * factor
    predicted = interp(lookup, i.time_indices, curves) if curves else i.desired_curvature
    saturated = i.limit_status >= 2 or self.path_last >= 0.5235 * 0.9 or self.path_last <= -0.5 * 0.9
    falling = abs(i.desired_curvature) < abs(self.desired_last) - 0.010
    blend = bounds.BLEND * 0.25 if not entering and (i.limit_status >= 1 or saturated or falling) else bounds.BLEND
    requested = predicted * blend + i.desired_curvature * (1.0 - blend)
    self.desired_last = i.desired_curvature
    precision = 0 if i.lane_change and ((i.lane_direction == 1 and requested < 0) or
                                      (i.lane_direction == 2 and requested > 0)) else 1
    # BluePilot's default lane-change factors are both 1.0.
    # Trim requested curvature before every existing actuator/safety limiter.
    requested = self.trim.update(requested, i.speed, i.geometry, self.trim_config,
                                 active=i.active, lane_change=i.lane_change, steering_pressed=i.steering_pressed)
    kappa = clip(requested, i.measured_curvature - 0.002, i.measured_curvature + 0.002) if i.speed > 9.0 else requested
    low = interp(i.speed, (13.5, 26.82), (1.0, self.low_gain))
    high = interp(i.speed, (13.5, 26.82), (1.3, self.high_gain))
    gain = interp(abs(kappa), (0.0007, 0.001), (low, high))
    path = kappa * i.speed * gain
    if saturated:
      last_mag, magnitude = abs(self.path_last), abs(path)
      if magnitude > last_mag:
        path = self.path_last
      elif last_mag - magnitude > 0.02:
        path = math.copysign(last_mag - 0.02, self.path_last)
    elif i.limit_status >= 1:
      path = clip(path, -abs(self.path_last), abs(self.path_last))
    roc = interp(i.speed, (10.0, 15.0, 25.0), (0.055, 0.0425, 0.009))
    path = clip(clip(path, -0.5235, 0.5), self.path_last - roc, self.path_last + roc)

    # Tightening relative to bp-7.0: the shadow describes the final actuator,
    # including ROC/saturation. A truthful derived curvature must fit both the
    # measured-curvature interval and the modern ISO envelope. If those bands
    # cannot meet the previous actuator ROC, send a neutral mode-0 frame.
    effective_speed = max(i.speed, 0.1)
    cap = min(bounds.CURVATURE_MAX, bounds.LATERAL_ACCEL / max(i.speed, 1.0) ** 2)
    low_kappa, high_kappa = -cap, cap
    if i.speed > 9.0:
      low_kappa = max(low_kappa, i.measured_curvature - 0.0018)
      high_kappa = min(high_kappa, i.measured_curvature + 0.0018)
    # Native cannot trust a host-selected feel gain. Intersect every admitted
    # gain (0.95..1.3), so the worst equivalent curvature remains bounded.
    lower_gain = bounds.GAIN_MAX if low_kappa >= 0.0 else bounds.GAIN_MIN
    upper_gain = bounds.GAIN_MIN if high_kappa >= 0.0 else bounds.GAIN_MAX
    lower = max(-bounds.PATH_MAX, low_kappa * effective_speed * lower_gain, self.path_last - roc)
    upper = min(-bounds.PATH_MIN, high_kappa * effective_speed * upper_gain, self.path_last + roc)
    # Bound the actual-angle equivalent derivative at the worst admitted gain.
    # 45ms core margin remains inside the native elapsed-time/50ms cap.
    jerk_delta = bounds.LATERAL_JERK / max(i.speed - 1.0, 1.0) ** 2 * bounds.CORE_STEER_PERIOD_S * bounds.GAIN_MIN * effective_speed
    jerk_center = self.path_last / self.speed_last * effective_speed
    lower = max(lower, jerk_center - jerk_delta)
    upper = min(upper, jerk_center + jerk_delta)
    lower += bounds.PATH_ROUNDING_MARGIN
    upper -= bounds.PATH_ROUNDING_MARGIN
    if lower > upper:
      self.trim.reset()
      self.path_last = 0.0
      return Command()
    path = clip(path, lower, upper)
    self.path_last = path
    self.speed_last = effective_speed
    shadow = path / (effective_speed * gain)

    self.blip_cooldown = max(0.0, self.blip_cooldown - 0.05)
    gap = i.desired_curvature - i.measured_curvature
    stalled = (not i.steering_pressed and not i.lane_change and i.speed > 9.0 and abs(gap) > 0.004 and
               abs(i.desired_curvature) > abs(i.measured_curvature))
    if stalled:
      if abs(kappa - requested) > 1e-9 and self.blip_cooldown <= 0.0:
        self.blip_hold += 0.05
      if self.blip_hold >= 0.5 and self.blip_count < 3 and abs(path) < 0.1:
        self.blip_frames = 6
        self.blip_hold = 0.0
        self.blip_count += 1
    else:
      self.blip_hold = 0.0
      if i.steering_pressed or abs(gap) < 0.002:
        self.blip_count = 0
    return Command(True, path, shadow, precision)
