"""Ford physical cancel/resume switch context; no new cruise authority."""

from opendbc.car import structs
from opendbc.car.ford.values import CAR, FordFlags, FordSafetyFlags
from opendbc.car.ford.classic_lateral import CLASSIC_EXTENDED_CARS
from opendbc.car.ford.generic_canfd_lateral import qualified as generic_canfd_qualified


class FordStockCruiseButton:
  """Resolve Ford's context-sensitive cancel/resume switch for stock ACC."""

  def __init__(self):
    self.pressed = False
    self.cancel = False
    self.resume = False

  def update(self, pressed: bool, cruise_available: bool, cruise_enabled: bool) -> tuple[bool, bool]:
    if pressed and not self.pressed:
      self.cancel = cruise_available and cruise_enabled
      self.resume = cruise_available and not cruise_enabled
    elif not pressed:
      self.cancel = False
      self.resume = False

    self.pressed = pressed
    return self.cancel, self.resume


def qualified(CP) -> bool:
  if CP.alternativeExperience == 32 and len(CP.safetyConfigs) != 1:
    return False
  """Existing stock profiles with the paired physical-driver button contract."""
  if (CP.brand != "ford" or CP.carFingerprint not in tuple(CAR) or CP.openpilotLongitudinalControl or CP.alternativeExperience not in (0, 32) or
      CP.passive or CP.dashcamOnly or CP.notCar or len(CP.safetyConfigs) not in (1, 2) or
      CP.flags & ~int(FordFlags.CANFD | FordFlags.HAS_BSM | FordFlags.ALT_STEER_ANGLE | FordFlags.NEW_PORT | FordFlags.LKA_STEERING)):
    return False
  if len(CP.safetyConfigs) == 2 and (CP.safetyConfigs[0].safetyModel != structs.CarParams.SafetyModel.noOutput or
                                  CP.safetyConfigs[0].safetyParam != 0):
    return False
  safety = CP.safetyConfigs[-1]
  if safety.safetyModel != structs.CarParams.SafetyModel.ford or safety.safetyParam not in (2, 8, 10, 12, 18, 32, 66):
    return False
  if safety.safetyModel == structs.CarParams.SafetyModel.ford and safety.safetyParam == 32:
    return CP.carFingerprint in CLASSIC_EXTENDED_CARS and not CP.flags & ~int(FordFlags.HAS_BSM)
  if safety.safetyParam == 66:
    return generic_canfd_qualified(CP)
  expected = (int(FordSafetyFlags.CANFD) if CP.flags & FordFlags.CANFD else 0)
  expected |= int(FordSafetyFlags.NEW_PORT) if CP.flags & FordFlags.NEW_PORT else 0
  expected |= int(FordSafetyFlags.LKA_STEERING) if CP.flags & FordFlags.LKA_STEERING else 0
  if safety.safetyParam == 18:
    if CP.carFingerprint != CAR.FORD_MUSTANG_MACH_E_MK1 or expected != int(FordSafetyFlags.CANFD):
      return False
    expected |= int(FordSafetyFlags.MACH_E_EXTENDED)
  return safety.safetyParam == expected
