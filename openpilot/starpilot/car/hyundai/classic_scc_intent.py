"""Stock SCC engagement intent over the shared physical lateral owner."""
from opendbc.car.structs import car
from openpilot.starpilot.aol.intent import AOL_TOGGLE
from openpilot.starpilot.car.hyundai.forte_intent import ForteCardIntent

ButtonType = car.CarState.ButtonEvent.Type


class ClassicSccCardIntent(ForteCardIntent):
  observe_stock_engagement = True

  def __init__(self, cp, settings):
    super().__init__(cp, settings)
    self._normal_previous = False

  def update(self, CS, *, consumed_buttons=frozenset(), fault_active=None,
             now_ns=0, native_rejection_ns=0, standard_enabled=False):
    rejected = self._native_rejection_ns < native_rejection_ns <= now_ns
    super().update(CS, consumed_buttons=consumed_buttons, fault_active=fault_active,
                   now_ns=now_ns, native_rejection_ns=native_rejection_ns,
                   standard_enabled=standard_enabled)
    normal = bool(standard_enabled and CS.cruiseState.enabled and CS.canValid and not CS.canTimeout)
    # A deliberate physical press wins over automatic engagement in this frame.
    pressed = any(event.pressed and event.type in (ButtonType.lkas, ButtonType.cancel)
                  for event in CS.buttonEvents)
    if (normal and not self._normal_previous and self.has_lkas and self.settings.enabled and
        self.settings.lkas_action == AOL_TOGGLE and not pressed and not rejected and
        not fault_active and not self.fault_rearm and not CS.steerFaultTemporary and
        not CS.steerFaultPermanent and not CS.gasPressed and not CS.brakePressed):
      # This is intent only: native SCC/recent-button controls authority and the
      # current heartbeat/request acknowledgement still gate actual steering.
      self.physical_latch = True
      self.allowed_latch = True
      self.pause_lateral = False
      self._last_latch_edge_ns = now_ns
    self._normal_previous = normal
