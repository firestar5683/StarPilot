"""Stock SCC engagement intent over the shared physical lateral owner."""
from openpilot.starpilot.car.hyundai.forte_intent import ForteCardIntent


class ClassicSccCardIntent(ForteCardIntent):
  observe_stock_engagement = True

  def _arm_from_full_engagement(self, CS, *, source_ns):
    if not (CS.steerFaultTemporary or CS.gasPressed or CS.brakePressed):
      super()._arm_from_full_engagement(CS, source_ns=source_ns)
