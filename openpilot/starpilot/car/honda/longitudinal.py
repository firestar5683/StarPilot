import math


class BoschLearningParams:
  def __init__(self, params, owner):
    self.params = params
    self.owner = owner
    factors = []
    for key in ("HondaGasFactorParams", "HondaWindFactorParams"):
      try:
        value = float(params.get(key, return_default=True))
        if not math.isfinite(value):
          value = 1.0
      except (TypeError, ValueError, OverflowError, RuntimeError):
        value = 1.0
      factors.append(value)
    owner.set_factors(*factors)

  def persist(self, frame):
    if frame > 0 and frame % 6000 == 0:
      self.params.put("HondaGasFactorParams", self.owner.bosch_gas_factor)
      self.params.put("HondaWindFactorParams", self.owner.bosch_wind_factor)
