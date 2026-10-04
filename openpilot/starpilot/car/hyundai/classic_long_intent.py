from opendbc.car.hyundai.values import HyundaiFlags
from openpilot.starpilot.aol.intent import AolCardIntent, AOL_TOGGLE


class ClassicLongCardIntent(AolCardIntent):
  def __init__(self, cp, settings):
    super().__init__(settings, explicit_latch=True)
    self.requires_fault_observation = True
    self.observe_stock_engagement = True
    self.has_lkas = bool(cp.flags & HyundaiFlags.HAS_LDA_BUTTON)
    self._normal_previous = False

  def update(self, CS, *, consumed_buttons=frozenset(), fault_active=None, now_ns=0, native_rejection_ns=0, standard_enabled=False):
    rejected = self._native_rejection_ns < native_rejection_ns <= now_ns
    super().update(
      CS,
      consumed_buttons=consumed_buttons,
      fault_active=fault_active,
      now_ns=now_ns,
      native_rejection_ns=native_rejection_ns,
      standard_enabled=standard_enabled,
    )
    normal = bool(standard_enabled and CS.canValid and not CS.canTimeout and CS.cruiseState.available)
    deliberate = any(event.pressed for event in CS.buttonEvents)
    if (
      normal
      and not self._normal_previous
      and self.has_lkas
      and self.settings.enabled
      and self.settings.lkas_action == AOL_TOGGLE
      and not deliberate
      and not rejected
      and not fault_active
      and not CS.steerFaultPermanent
      and not CS.steerFaultTemporary
      and not CS.gasPressed
      and not CS.brakePressed
      and not CS.accFaulted
    ):
      self.allowed_latch = True
      self.pause_lateral = False
      self._last_latch_edge_ns = now_ns
    self._normal_previous = normal
