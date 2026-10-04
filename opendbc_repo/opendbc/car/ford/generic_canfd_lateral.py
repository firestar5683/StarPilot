"""Exact generic CAN FD caller; no Mach-E error, path assist, or latch.

The reused BluePilot-derived strategy retains its original attribution in
lateral_strategy.py, CREDITS.md and THIRD_PARTY_NOTICES.md.
"""
from opendbc.car import structs
from opendbc.car.ford.explorer_lateral import bounded_command as shared_bound
from opendbc.car.ford.lateral_strategy import FordLateralController
from opendbc.car.ford.values import CAR, FordFlags, FordSafetyFlags

GENERIC_CANFD_CARS = frozenset({CAR.FORD_ESCAPE_MK4_5, CAR.FORD_EXPEDITION_MK4,
  CAR.FORD_F_150_MK14, CAR.FORD_F_150_LIGHTNING_MK1, CAR.FORD_RANGER_MK2})
SOURCE_ACCEL_CAP = 3.0 - 9.81 * .06


def qualified(cp):
  if (cp.brand != "ford" or cp.carFingerprint not in GENERIC_CANFD_CARS or
      not cp.flags & FordFlags.CANFD or cp.flags & ~int(FordFlags.CANFD | FordFlags.HAS_BSM) or
      cp.passive or cp.dashcamOnly or cp.notCar or cp.alternativeExperience != 0 or
      len(cp.safetyConfigs) not in (1, 2)):
    return False
  if len(cp.safetyConfigs) == 2 and (cp.safetyConfigs[0].safetyModel != structs.CarParams.SafetyModel.noOutput or
                                   cp.safetyConfigs[0].safetyParam != 0):
    return False
  s = cp.safetyConfigs[-1]
  expected = int(FordSafetyFlags.GENERIC_CANFD_EXTENDED | FordSafetyFlags.CANFD |
                 (FordSafetyFlags.LONG_CONTROL if cp.openpilotLongitudinalControl else 0))
  return s.safetyModel == structs.CarParams.SafetyModel.ford and s.safetyParam == expected


class GenericCanfdLateralController(FordLateralController):
  def __init__(self, cp):
    if not qualified(cp):
      raise ValueError("Generic CAN FD controller requires its exact source-owned profile")
    super().__init__(cp)
    self.manual_turn_detected = False

  def _manual_turn(self, CC, CS, desired, driver_assisting):
    self.manual_turn_detected = super()._manual_turn(CC, CS, desired, driver_assisting)
    return self.manual_turn_detected


def bounded_command(owner, demanded, previous, speed, measured):
  return shared_bound(owner, demanded, previous, speed, measured,
                      absolute_cap=SOURCE_ACCEL_CAP / max(speed, 1.) ** 2)
