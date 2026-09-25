"""Ordinary SDGM torque selection; factory PID identity stays on PID."""

import math
import numpy as np

from opendbc.car.structs import CarParams
from opendbc.car.gm.values import CAR, is_ordinary_sdgm_profile
from openpilot.starpilot.lateral.gm_ordinary_policy import GMOrdinaryTorquePolicy


def supported_cp(cp):
  if not (is_ordinary_sdgm_profile(cp, longitudinal=False) or is_ordinary_sdgm_profile(cp, longitudinal=True)):
    return False
  if cp.steerControlType != CarParams.SteerControlType.torque or cp.lateralTuning.which() != "torque":
    return False
  tune = cp.lateralTuning.torque
  return (math.isfinite(tune.latAccelFactor) and tune.latAccelFactor > 0 and
          math.isfinite(tune.latAccelOffset) and math.isfinite(tune.friction) and tune.friction >= 0)


class SdgmTorquePolicy(GMOrdinaryTorquePolicy):
  def __init__(self, parent, cp):
    if not supported_cp(cp):
      raise ValueError("Unsupported ordinary SDGM torque profile")
    if cp.carFingerprint == CAR.CADILLAC_XT4:
      lateral_values = np.arange(-5.0, 5.0, 0.01)
      torque_values = []
      for value in lateral_values:
        sig_input = 2.4 * value
        sigmoid = np.sign(sig_input) * (1 / (1 + math.exp(-abs(sig_input))) - 0.5)
        torque_values.append(float(sigmoid * .95 + value * .28))
      parent.torque_from_lateral_accel = lambda value, tune: np.interp(value, lateral_values, torque_values)
      parent.lateral_accel_from_torque = lambda value, tune: np.interp(value, torque_values, lateral_values)
    super().__init__(parent, cp)
