"""Curve envelope and bounded target dynamics, without actuator authority."""

from dataclasses import dataclass
import math

from openpilot.starpilot.curve_speed.learning import LearnedCurve, MAX_CURVATURE, finite_number
from openpilot.starpilot.model_geometry import normalized_origin


MIN_SPEED = 25 * 0.44704
APPROACH_DECEL = 0.3
TARGET_UP_RATE = 3.0
TARGET_DOWN_RATE = 2.5
FILTER_RC = 0.4
EGO_HEADROOM = 2.0
RELEASE_DEBOUNCE = 0.25
MAX_LATERAL_ACCEL = 4.0
MAX_PROFILE_POINTS = 129
MAX_STEP_SECONDS = 0.2


@dataclass(frozen=True)
class CurveProfile:
  curvatures: tuple[float, ...]
  distances: tuple[float, ...]
  observed_ns: int

  def __post_init__(self):
    if (type(self.curvatures) is not tuple or type(self.distances) is not tuple or
        not 0 < len(self.curvatures) == len(self.distances) <= MAX_PROFILE_POINTS or
        type(self.observed_ns) is not int or self.observed_ns < 0):
      raise ValueError("invalid profile shape or timestamp")
    if (any(not finite_number(k) for k in self.curvatures) or
        any(not finite_number(d) or d < 0 for d in self.distances) or
        any(b < a for a, b in zip(self.distances, self.distances[1:], strict=False))):
      raise ValueError("invalid curvature or distance")

  @classmethod
  def from_model(cls, model, observed_ns: int) -> 'CurveProfile | None':
    try:
      rates = tuple(model.orientationRate.z)
      velocities = tuple(model.velocity.x)
      distances = tuple(model.position.x)
      if (not len(rates) == len(velocities) == len(distances) or
          any(not finite_number(v) or v < 0 for v in velocities) or any(not finite_number(rate) for rate in rates)):
        return None
      # The predicted origin can round slightly below zero (observed around
      # -7e-11 meters). Accept only sub-micrometer origin roundoff; the typed
      # profile still rejects negative future points and backwards geometry.
      distances = normalized_origin(distances)
      curvatures = tuple(min(abs(rate) / v, 0.1) if v >= 3.0 else 0.0 for rate, v in zip(rates, velocities, strict=True))
      return cls(curvatures, distances, observed_ns)
    except (AttributeError, TypeError, ValueError, OverflowError):
      return None


@dataclass(frozen=True)
class Envelope:
  speed_mps: float
  binding_distance_m: float


def evaluate(profile: CurveProfile, comfort: LearnedCurve, cruise_mps: float, *, weather_reduction: float = 0.0) -> Envelope:
  """Approach envelope only. The caller must qualify freshness and ownership."""
  if not finite_number(cruise_mps) or cruise_mps <= 0 or not finite_number(weather_reduction) or not 0 <= weather_reduction <= 1:
    raise ValueError("invalid cruise or weather input")
  result = Envelope(float(cruise_mps), 0.0)
  for curvature, distance in zip(profile.curvatures, profile.distances, strict=True):
    magnitude = abs(curvature)
    if magnitude >= 0.004 and distance >= 30.0:
      magnitude *= 1.23
    magnitude = min(magnitude, MAX_CURVATURE)
    denominator = max(magnitude, 1e-4)
    lateral = comfort.comfort(magnitude) * (1 - weather_reduction)
    apex_speed = min(max(math.sqrt(lateral / denominator), MIN_SPEED), math.sqrt(MAX_LATERAL_ACCEL / denominator))
    allowed = math.sqrt(apex_speed**2 + (2 * APPROACH_DECEL) * distance)
    if allowed < result.speed_mps:
      result = Envelope(allowed, float(distance))
  return result


class TargetFilter:
  """Reset after a frame gap; never integrate a pause as control progress."""

  def __init__(self):
    self.target: float | None = None
    self._filtered = 0.0
    self._release_seconds = 0.0

  def reset(self) -> None:
    self.target = None
    self._filtered = 0.0
    self._release_seconds = 0.0

  def step(self, envelope: Envelope, *, ego_mps: float, cruise_mps: float, dt: float) -> float:
    if (not finite_number(ego_mps) or ego_mps < 0 or not finite_number(cruise_mps) or cruise_mps <= 0 or
        not finite_number(dt) or not 0 < dt <= MAX_STEP_SECONDS or
        not finite_number(envelope.speed_mps) or envelope.speed_mps <= 0 or envelope.speed_mps > cruise_mps):
      self.reset()
      raise ValueError("invalid target input or discontinuous time")
    raw = envelope.speed_mps
    if self.target is None:
      self.target = min(cruise_mps, max(raw, ego_mps + EGO_HEADROOM))
      self._filtered = self.target
    self._release_seconds = self._release_seconds + dt if raw >= ego_mps else 0.0
    alpha = dt / (FILTER_RC + dt)
    self._filtered = (1 - alpha) * self._filtered + alpha * raw
    desired = max(self._filtered, min(raw, ego_mps + EGO_HEADROOM))
    self.target = min(max(desired, self.target - TARGET_DOWN_RATE * dt), self.target + TARGET_UP_RATE * dt)
    if self._release_seconds >= RELEASE_DEBOUNCE:
      self.target = max(self.target, min(raw, ego_mps))
    # Driver lowering cruise is an immediate cap, independent of filter history.
    self.target = min(self.target, cruise_mps)
    return self.target
