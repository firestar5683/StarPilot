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
    self.saved = (owner.bosch_gas_factor, owner.bosch_wind_factor)

  def persist(self, frame):
    if frame > 0 and frame % 6000 == 0:
      # Learning only moves while openpilot drives the pedals; skip rewriting unchanged values.
      factors = (self.owner.bosch_gas_factor, self.owner.bosch_wind_factor)
      if factors == self.saved:
        return
      self.params.put("HondaGasFactorParams", factors[0])
      self.params.put("HondaWindFactorParams", factors[1])
      self.saved = factors
