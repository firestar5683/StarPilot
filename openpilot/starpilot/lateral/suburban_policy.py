"""Ordinary Suburban torque selection."""

import math

from opendbc.car.structs import CarParams
from opendbc.car.gm.suburban import supported_cp as supported_profile
from openpilot.starpilot.lateral.gm_ordinary_policy import GMOrdinaryTorquePolicy


def supported_cp(cp):
  if not supported_profile(cp):
    return False
  if cp.steerControlType != CarParams.SteerControlType.torque or cp.lateralTuning.which() != "torque":
    return False
  tune = cp.lateralTuning.torque
  return (math.isfinite(tune.latAccelFactor) and tune.latAccelFactor > 0 and
          math.isfinite(tune.latAccelOffset) and math.isfinite(tune.friction) and tune.friction >= 0)


class SuburbanTorquePolicy(GMOrdinaryTorquePolicy):
  def __init__(self, parent, cp):
    if not supported_cp(cp):
      raise ValueError("Unsupported ordinary Suburban torque profile")
    super().__init__(parent, cp)
