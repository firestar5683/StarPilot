"""Forte main availability and physical LKAS intent over the shared axis lease."""
from dataclasses import replace

from opendbc.car.structs import car
from opendbc.car.hyundai.values import HyundaiFlags
from openpilot.starpilot.aol.intent import AolCardIntent, AOL_TOGGLE

ButtonType = car.CarState.ButtonEvent.Type


class ForteCardIntent(AolCardIntent):
  def __init__(self, cp, settings):
    super().__init__(settings, explicit_latch=True)
    self.requires_fault_observation = True
    self.has_lkas = bool(cp.flags & HyundaiFlags.HAS_LDA_BUTTON)
    self.physical_latch = False
    self.fault_rearm = False
    self.main_off_seen = False
    self.neutral_seen = False
    self._lkas_down = False
    self._aux_original = None
    self._aux_settings = settings

  def update(self, CS, *, consumed_buttons=frozenset(), fault_active=None,
             now_ns=0, native_rejection_ns=0, standard_enabled=False):
    # Let the common owner retain distance/axis-pause gestures, without giving
    # its unified main/LKAS latch authority over this vehicle's intent.
    settings, explicit = self.settings, self.explicit_latch
    main_managed = settings.main_action == AOL_TOGGLE or (not self.has_lkas and
                                                         settings.main_action != AOL_TOGGLE and settings.lkas_action != AOL_TOGGLE)
    if self._aux_original is not settings:
      self._aux_original = settings
      self._aux_settings = replace(settings, lkas_action=0, main_action=0)
    self.settings = self._aux_settings
    self.explicit_latch = False
    try:
      super().update(CS, consumed_buttons=consumed_buttons, now_ns=now_ns, standard_enabled=standard_enabled)
    finally:
      self.settings, self.explicit_latch = settings, explicit
    invalid = not CS.canValid or CS.canTimeout
    fatal = bool(fault_active or CS.steerFaultPermanent)
    fresh_rejection = self._native_rejection_ns < native_rejection_ns <= now_ns
    rejected = fresh_rejection and self._last_latch_edge_ns < native_rejection_ns
    if fresh_rejection:
      self._native_rejection_ns = native_rejection_ns
    if invalid or fatal or rejected:
      self.physical_latch = False
      self.neutral_seen = False
      if fatal:
        self.fault_rearm = True
        self.main_off_seen = False
    if not settings.enabled:
      self.physical_latch = False
    if not invalid and not fatal and not CS.cruiseState.available:
      self.main_off_seen = True
    for event in CS.buttonEvents:
      if event.type == ButtonType.mainCruise and event.pressed and settings.main_action != AOL_TOGGLE:
        self._perform(settings.main_action)
      if event.type != ButtonType.lkas:
        continue
      if not event.pressed:
        self._lkas_down = False
        self.neutral_seen = True
      elif not self._lkas_down:
        self._lkas_down = True
        if self.neutral_seen and settings.enabled and not invalid and not fatal and not rejected:
          if settings.lkas_action == AOL_TOGGLE:
            self._last_latch_edge_ns = now_ns
            if self.fault_rearm:
              self.fault_rearm = False
            if main_managed and CS.cruiseState.available:
              # Deliberate correction: both assigned controls toggle effective
              # pause symmetrically; a main overwrite cannot make it sticky.
              self.pause_lateral = not self.pause_lateral
            else:
              self.physical_latch = not self.physical_latch
              if CS.cruiseState.enabled or self.pause_lateral:
                self.pause_lateral = not self.physical_latch
          else:
            self._perform(settings.lkas_action)
    if self.fault_rearm and self.main_off_seen and CS.cruiseState.available and not invalid and not fatal:
      self.fault_rearm = False
    allowed = CS.cruiseState.available if main_managed else self.physical_latch
    self.allowed_latch = bool(settings.enabled and allowed and not invalid and not fatal and not self.fault_rearm)
