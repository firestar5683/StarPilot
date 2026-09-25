"""Reuse the current Ford curvature strategy for exact Edge/Mondeo callers.

Only scalar curvature crosses the existing native boundary; no protocol extension.
The reused strategy retains its required provenance and notices in lateral_strategy.py.
"""
from dataclasses import replace
import math

from opendbc.car import structs
from opendbc.car.ford.explorer_lateral import bounded_command as shared_bound
from opendbc.car.ford.lateral_strategy import FordLateralController, FordLateralResult
from opendbc.car.ford.values import CAR, FordFlags

PROFILES = {
  CAR.FORD_EDGE_MK2: (int(FordFlags.NEW_PORT | FordFlags.ALT_STEER_ANGLE), 8),
  CAR.FORD_MONDEO_MK5: (int(FordFlags.NEW_PORT | FordFlags.CANFD), 10),
}


def qualified(cp):
  profile = PROFILES.get(cp.carFingerprint)
  if (profile is None or cp.brand != "ford" or cp.passive or cp.dashcamOnly or cp.notCar or
      cp.alternativeExperience not in (0, 32) or not cp.pcmCruise or
      cp.steerControlType != structs.CarParams.SteerControlType.angle or
      len(cp.safetyConfigs) not in (1, 2) or (cp.alternativeExperience == 32 and len(cp.safetyConfigs) != 1)):
    return False
  flags, word = profile
  if (int(cp.flags) & ~int(FordFlags.HAS_BSM)) != flags:
    return False
  if len(cp.safetyConfigs) == 2 and (cp.safetyConfigs[0].safetyModel != structs.CarParams.SafetyModel.noOutput or
                                   cp.safetyConfigs[0].safetyParam != 0):
    return False
  safety = cp.safetyConfigs[-1]
  return safety.safetyModel == structs.CarParams.SafetyModel.ford and safety.safetyParam == word + int(cp.openpilotLongitudinalControl)


class NewPortCurvatureController(FordLateralController):
  def __init__(self, cp):
    if not qualified(cp):
      raise ValueError("Edge/Mondeo curvature requires its exact current native profile")
    super().__init__(cp)
    self.manual_turn_detected = False

  def _manual_turn(self, CC, CS, desired: float, driver_assisting: bool = False) -> bool:
    self.manual_turn_detected = super()._manual_turn(CC, CS, desired, driver_assisting)
    return self.manual_turn_detected

  def update(self, CC, CS, actuators):
    out = CS.out
    if (not CC.latActive or not out.canValid or out.canTimeout or out.steerFaultTemporary or
        out.steerFaultPermanent or out.vehicleSensorsInvalid or
        not all(math.isfinite(value) for value in (out.vEgoRaw, out.yawRate, out.steeringAngleDeg, actuators.curvature))):
      self.human_turn.reset()
      self.curvature_samples.clear()
      self.curvature_last = self.path_angle_last = 0.0
      self.manual_turn_detected = False
      return FordLateralResult()
    return super().update(CC, CS, actuators)


def create_controller(cp):
  return NewPortCurvatureController(cp) if qualified(cp) else None


def bounded_command(owner, demanded, previous, speed, measured):
  cap = (3.0 - 9.81 * .06) / max(speed, 1.) ** 2 if owner.CP.flags & FordFlags.CANFD else None
  command = shared_bound(owner, demanded, previous, speed, measured, absolute_cap=cap)
  # These profiles keep their current curvature-only native/codec contract.
  return replace(command, curvature_rate=0.0, path_angle=0.0, ramp_type=0, precision_type=1)
