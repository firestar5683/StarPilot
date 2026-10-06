import math

from opendbc.car import structs
from openpilot.starpilot.lateral.ioniq6_policy import get_ioniq_6_low_speed_angle_assist_torque


class TorqueTurnAssist:
  def __init__(self, cp):
    minimum = float(cp.minSteerSpeed)
    self.minimum_speed = max(0.044704, minimum) if math.isfinite(minimum) else math.inf

  def apply(self, cs, vm, params, curvature, output, limit):
    if (not math.isfinite(cs.vEgo) or cs.vEgo < self.minimum_speed or cs.standstill or cs.steeringPressed or
        cs.steerFaultTemporary or cs.steerFaultPermanent or cs.gearShifter not in (structs.CarState.GearShifter.drive, structs.CarState.GearShifter.low)):
      return output
    desired = math.degrees(vm.get_steer_from_curvature(-curvature, cs.vEgo, params.roll))
    actual = cs.steeringAngleDeg - params.angleOffsetDeg
    if not all(math.isfinite(value) for value in (desired, actual, output, limit)) or limit < 0:
      return output
    adjusted = get_ioniq_6_low_speed_angle_assist_torque(desired, actual, output, cs.vEgo)
    return max(-limit, min(limit, adjusted))
