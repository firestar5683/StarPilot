from opendbc.car.hyundai.values import CAR
from openpilot.starpilot.lateral import sonata_hybrid_shaping as shaping
from openpilot.starpilot.lateral.hkg_torque_policy import HKGShapedTorquePolicy, supported_torque_cp


SONATA_HYBRID_CARS = frozenset((CAR.HYUNDAI_SONATA_HYBRID,))


def supported_cp(cp):
  return supported_torque_cp(cp, SONATA_HYBRID_CARS)


class SonataHybridTorquePolicy(HKGShapedTorquePolicy):
  FACTOR_MULT = shaping.SONATA_HYBRID_BASE_LAT_ACCEL_FACTOR_MULT
  supported_cp = staticmethod(supported_cp)

  def feedforward(self, value, setpoint, jerk, speed):
    return value * shaping.get_sonata_hybrid_ff_scale(setpoint, jerk, speed) * shaping.get_sonata_hybrid_center_taper_scale(setpoint, speed)

  def friction(self, setpoint, jerk, speed):
    return shaping.get_sonata_hybrid_friction_threshold(speed, setpoint), 1.0

  def output(self, value, setpoint, speed):
    return value * shaping.get_sonata_hybrid_center_taper_scale(setpoint, speed) * shaping.get_sonata_hybrid_center_output_scale(setpoint, speed)
