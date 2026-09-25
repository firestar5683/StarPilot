"""Display-only wheel colors from caller-qualified vehicle observations."""

from dataclasses import dataclass
import math
from typing import Any


BRAKE_RGB = (255, 0, 0)
ACCEL_RGB = (22, 127, 64)


@dataclass(frozen=True)
class WheelFeedback:
  brake_pressed: bool | None = None
  regen_braking: bool | None = None
  gas_pressed: bool | None = None
  acceleration: float | None = None
  commanded_acceleration: float | None = None
  commanded_gas: float | None = None


def _boolean(value: Any) -> bool | None:
  return value if type(value) is bool else None


def _finite(value: Any) -> float | None:
  return float(value) if type(value) in (int, float) and math.isfinite(value) else None


def observe_wheel_feedback(car_state: Any, car_control: Any) -> WheelFeedback:
  """Inputs must already satisfy transport freshness and current-drive checks."""
  if (car_state is None or getattr(car_state, "canValid", None) is not True or
      getattr(car_state, "canTimeout", None) is not False):
    return WheelFeedback()
  actuators = getattr(car_control, "actuators", None) if getattr(car_control, "longActive", None) is True else None
  return WheelFeedback(
    brake_pressed=_boolean(getattr(car_state, "brakePressed", None)),
    regen_braking=_boolean(getattr(car_state, "regenBraking", None)),
    gas_pressed=_boolean(getattr(car_state, "gasPressed", None)),
    acceleration=_finite(getattr(car_state, "aEgo", None)),
    commanded_acceleration=_finite(getattr(actuators, "accel", None)),
    commanded_gas=_finite(getattr(actuators, "gas", None)),
  )


def wheel_feedback_rgb(value: WheelFeedback, enabled: bool) -> tuple[int, int, int] | None:
  if not enabled:
    return None
  if (value.brake_pressed is True or value.regen_braking is True or
      value.acceleration is not None and value.acceleration < -0.25 or
      value.commanded_acceleration is not None and value.commanded_acceleration < -0.05):
    return BRAKE_RGB
  if (value.gas_pressed is True or value.acceleration is not None and value.acceleration > 0.25 or
      value.commanded_acceleration is not None and value.commanded_acceleration > 0.05 or
      value.commanded_gas is not None and value.commanded_gas > 0.05):
    return ACCEL_RGB
  return None
