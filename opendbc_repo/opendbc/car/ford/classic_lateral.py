"""Shared source-derived classic Ford family; model transport stays outside opendbc.

The reused extended strategy derives from BluePilot Ford work by Alan Polk and
contributors. Its original attribution and licenses remain in lateral_strategy.py,
CREDITS.md and THIRD_PARTY_NOTICES.md; this module only selects admitted callers.
"""

from opendbc.car import structs
from opendbc.car.ford.explorer_lateral import ExplorerLateralController, bounded_command as bounded_command, qualified as explorer_qualified
from opendbc.car.ford.lateral_strategy import FordLateralController
from opendbc.car.ford.values import CAR, FordFlags, FordSafetyFlags

GENERIC_CLASSIC_CARS = frozenset({CAR.FORD_BRONCO_SPORT_MK1, CAR.FORD_ESCAPE_MK4,
                                CAR.FORD_FOCUS_MK4, CAR.FORD_MAVERICK_MK1})
CLASSIC_EXTENDED_CARS = GENERIC_CLASSIC_CARS | {CAR.FORD_EXPLORER_MK6}


def qualified(cp):
  if cp.carFingerprint == CAR.FORD_EXPLORER_MK6:
    return explorer_qualified(cp)
  if (cp.brand != "ford" or cp.carFingerprint not in GENERIC_CLASSIC_CARS or
      cp.flags & ~int(FordFlags.HAS_BSM) or cp.passive or cp.dashcamOnly or cp.notCar or
      cp.alternativeExperience != 0 or len(cp.safetyConfigs) not in (1, 2)):
    return False
  if len(cp.safetyConfigs) == 2 and (cp.safetyConfigs[0].safetyModel != structs.CarParams.SafetyModel.noOutput or
                                   cp.safetyConfigs[0].safetyParam != 0):
    return False
  safety = cp.safetyConfigs[-1]
  expected = int(FordSafetyFlags.CLASSIC_EXTENDED | (FordSafetyFlags.LONG_CONTROL if cp.openpilotLongitudinalControl else 0))
  return safety.safetyModel == structs.CarParams.SafetyModel.ford and safety.safetyParam == expected


class GenericClassicLateralController(FordLateralController):
  """Original generic liveDelay preview; no Explorer fixed-delay or Mach-E latch."""

  def __init__(self, cp):
    if not qualified(cp) or cp.carFingerprint not in GENERIC_CLASSIC_CARS:
      raise ValueError("Generic classic controller requires the exact admitted family")
    super().__init__(cp)
    self.manual_turn_detected = False

  def _manual_turn(self, CC, CS, desired, driver_assisting):
    self.manual_turn_detected = super()._manual_turn(CC, CS, desired, driver_assisting)
    return self.manual_turn_detected


def create_controller(cp):
  if not qualified(cp):
    return None
  return ExplorerLateralController(cp) if cp.carFingerprint == CAR.FORD_EXPLORER_MK6 else GenericClassicLateralController(cp)
