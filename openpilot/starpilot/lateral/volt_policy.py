"""Vehicle-owned default torque controller for the five Volt identities."""

import math

import numpy as np

from opendbc.car import structs
from opendbc.car.gm.values import CAR
from openpilot.starpilot.lateral.gm_ordinary_policy import GMOrdinaryTorquePolicy

VOLT_IDENTITIES = {
  CAR.CHEVROLET_VOLT,
  CAR.CHEVROLET_VOLT_ASCM,
  CAR.CHEVROLET_VOLT_CAMERA,
  CAR.CHEVROLET_VOLT_CC,
  CAR.CHEVROLET_VOLT_2019,
}


def supported_cp(cp):
  return (
    cp.brand == 'gm'
    and cp.carFingerprint in VOLT_IDENTITIES
    and not cp.notCar
    and not cp.passive
    and not cp.dashcamOnly
    and cp.steerControlType == structs.CarParams.SteerControlType.torque
    and cp.lateralTuning.which() == 'torque'
    and math.isfinite(cp.lateralTuning.torque.latAccelFactor)
    and cp.lateralTuning.torque.latAccelFactor > 0
    and math.isfinite(cp.lateralTuning.torque.latAccelOffset)
    and math.isfinite(cp.lateralTuning.torque.friction)
    and cp.lateralTuning.torque.friction >= 0
  )


class VoltTorquePolicy(GMOrdinaryTorquePolicy):
  def __init__(self, parent, cp):
    self.parent = parent
    if not supported_cp(cp):
      raise ValueError('Unsupported Volt torque profile')
    self.dt = parent.dt
    coefficients = ((1.525, 1.05, 0.155, 0.0), (1.525, 0.95, 0.150, 0.0))
    lateral_values = np.arange(-5.0, 5.0, 0.01)
    torque_values = []
    for value in lateral_values:
      a, b, c, d = coefficients[0 if value >= 0 else 1]
      sig_input = a * value
      sigmoid = np.sign(sig_input) * (1 / (1 + math.exp(-abs(sig_input))) - 0.5)
      torque_values.append(float(sigmoid * b + value * c + d))
    parent.torque_from_lateral_accel = lambda value, tune: np.interp(value, lateral_values, torque_values)
    parent.lateral_accel_from_torque = lambda value, tune: np.interp(value, torque_values, lateral_values)
    super().__init__(parent, cp)
