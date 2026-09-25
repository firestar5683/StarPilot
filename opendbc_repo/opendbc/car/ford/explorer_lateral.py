"""Explorer/Aviator source-derived demand and exact native profile contract.

The inherited strategy is adapted from BluePilot Ford work. Attribution and
license notices are preserved in lateral_strategy.py, CREDITS.md and
THIRD_PARTY_NOTICES.md.
"""

from dataclasses import replace

import numpy as np

from opendbc.car import structs
from opendbc.car.ford.lateral_strategy import FordLateralController, FordLateralResult, FORD_CURVATURE_LIMITS, STEER_DT
from opendbc.car.ford.values import CAR, CarControllerParams, FordFlags, FordSafetyFlags


class ExplorerLateralController(FordLateralController):
  """Exact classic Explorer family, including the Aviator identity alias."""

  def __init__(self, CP):
    if CP.carFingerprint != CAR.FORD_EXPLORER_MK6 or CP.flags & ~int(FordFlags.HAS_BSM):
      raise ValueError("Explorer demand strategy requires the exact classic family")
    super().__init__(CP)
    self.manual_turn_detected = False

  def _manual_turn(self, CC, CS, desired, driver_assisting) -> bool:
    self.manual_turn_detected = super()._manual_turn(CC, CS, desired, driver_assisting)
    return self.manual_turn_detected

  def _curvature_lookahead(self) -> float:
    # Original reached family override precedes liveDelay inspection.
    return 0.20


def qualified(CP) -> bool:
  if (CP.brand != "ford" or CP.carFingerprint != CAR.FORD_EXPLORER_MK6 or
      CP.flags & ~int(FordFlags.HAS_BSM) or CP.passive or CP.dashcamOnly or CP.notCar or
      CP.alternativeExperience != 0 or len(CP.safetyConfigs) not in (1, 2)):
    return False
  if len(CP.safetyConfigs) == 2 and (CP.safetyConfigs[0].safetyModel != structs.CarParams.SafetyModel.noOutput or
                                  CP.safetyConfigs[0].safetyParam != 0):
    return False
  safety = CP.safetyConfigs[-1]
  expected = int(FordSafetyFlags.EXPLORER_EXTENDED | (FordSafetyFlags.LONG_CONTROL if CP.openpilotLongitudinalControl else 0))
  return safety.safetyModel == structs.CarParams.SafetyModel.ford and safety.safetyParam == expected


def bounded_command(owner: ExplorerLateralController, demanded: FordLateralResult,
                    previous: float, speed: float, measured: float) -> FordLateralResult:
  """Keep classic demand inside the modern common ISO/jerk envelope."""
  limits = CarControllerParams.CURVATURE_LIMITS
  cap = min(limits.CURVATURE_MAX, limits.MAX_LATERAL_ACCEL / max(speed, 1.0) ** 2)
  modern_delta = limits.MAX_LATERAL_JERK / max(speed, 1.0) ** 2 * STEER_DT
  source_up = FORD_CURVATURE_LIMITS.ANGLE_RATE_LIMIT_UP
  source_down = FORD_CURVATURE_LIMITS.ANGLE_RATE_LIMIT_DOWN
  rise = float(np.interp(speed, source_up[0], source_up[1]))
  fall = float(np.interp(speed, source_down[0], source_down[1]))
  # Same sign plus increasing magnitude uses rise; unwind/opposite uses fall.
  source_low = previous - (fall if previous > 0.0 else rise)
  source_high = previous + (fall if previous < 0.0 else rise)
  low = max(-cap, previous - modern_delta, source_low)
  high = min(cap, previous + modern_delta, source_high)
  # Match modern recovery toward the actual measured-curvature error window.
  # Outside the window, require directional progress without jumping into it.
  if speed > 10.0:
    error_low = measured - CarControllerParams.CURVATURE_ERROR
    error_high = measured + CarControllerParams.CURVATURE_ERROR
    if previous < error_low:
      low = max(low, min(previous + modern_delta, error_low, cap))
    elif previous > error_high:
      high = min(high, max(previous - modern_delta, error_high, -cap))
    else:
      low = max(low, error_low)
      high = min(high, error_high)
  if not demanded.active or owner.manual_turn_detected or low > high:
    command = FordLateralResult()
  else:
    command = replace(demanded, curvature=float(np.clip(demanded.curvature, low, high)), path_angle=0.0)
  owner.curvature_last = command.curvature
  owner.path_angle_last = 0.0
  return command
