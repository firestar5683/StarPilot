"""Default lateral law for exact GM camera and Silverado interceptor configurations."""
import math
import numpy as np

from opendbc.car.gm.values import CAR, is_ordinary_camera_profile, is_silverado_cc_pedal_profile
from opendbc.car.structs import CarParams
from openpilot.starpilot.lateral.gm_ordinary_policy import GMOrdinaryTorquePolicy


def supported_cp(cp):
  if not (is_ordinary_camera_profile(cp, longitudinal=cp.openpilotLongitudinalControl) or is_silverado_cc_pedal_profile(cp)):
    return False
  if cp.steerControlType != CarParams.SteerControlType.torque or cp.lateralTuning.which() != 'torque':
    return False
  tune = cp.lateralTuning.torque
  return (math.isfinite(tune.latAccelFactor) and tune.latAccelFactor > 0 and
          math.isfinite(tune.latAccelOffset) and math.isfinite(tune.friction) and tune.friction >= 0)


def sigmoid(value):
  z = math.exp(-value) if value >= 0 else math.exp(value)
  return 1 / (1 + z) if value >= 0 else z / (1 + z)


class CameraTorquePolicy(GMOrdinaryTorquePolicy):
  def __init__(self, parent, cp):
    if not supported_cp(cp):
      raise ValueError('Unsupported GM camera or Silverado interceptor torque profile')
    self.silverado = cp.carFingerprint in (CAR.CHEVROLET_SILVERADO, CAR.CHEVROLET_SILVERADO_CC)
    coefficients = ((3.8, .81, .24, .0465122) if self.silverado else
                    (3.8060, .8282, .1702, 0.) if cp.carFingerprint == CAR.CHEVROLET_TRAX else None)
    if coefficients is not None:
      a, b, c, d = coefficients
      lateral = np.arange(-5., 5., .01)
      torque = []
      for value in lateral:
        x = a * value
        curve = np.sign(x) * (1 / (1 + math.exp(-abs(x))) - .5)
        torque.append(float(curve * b + value * c + d))
      parent.torque_from_lateral_accel = lambda value, tune: np.interp(value, lateral, torque)
      parent.lateral_accel_from_torque = lambda value, tune: np.interp(value, torque, lateral)
    super().__init__(parent, cp)

  def taper(self, setpoint, speed):
    return 1 - .22 * sigmoid((speed - 12.) / 2.5) * sigmoid((.18 - abs(setpoint)) / .05) if self.silverado else 1.

  def feedforward(self, value, setpoint, jerk, speed):
    return value * self.taper(setpoint, speed)

  def output(self, value, setpoint, speed):
    return value * self.taper(setpoint, speed)
