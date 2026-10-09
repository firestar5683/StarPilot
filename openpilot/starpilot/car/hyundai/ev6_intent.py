"""EV6 configured AOL desire gated by actual physical authorization."""
from opendbc.car.hyundai.values import Buttons
from opendbc.car.hyundai.ev6_aol import Ev6PhysicalAuthorization
from openpilot.starpilot.aol.intent import AolCardIntent, AOL_TOGGLE, ButtonType


class Ev6CardIntent(AolCardIntent):
  observe_stock_engagement = True
  observe_active_engagement = True

  def __init__(self, settings):
    # Explicit identifies the native-ACK contract, not a universal button mapping.
    super().__init__(settings, explicit_latch=True)
    self.physical = Ev6PhysicalAuthorization(lkas_on_engage=settings.enabled and settings.lkas_action == AOL_TOGGLE)
    self._samples = ()
    self._buttons_current = False
    self._active_previous = False
    self._raw_neutral_seen = False
    self._acc_faulted = False
    self._controller_override = None

  def observe_physical_samples(self, state, *, now_ns):
    stamp = int(state.ev6_aol_sample_stamp_ns)
    self._buttons_current = bool(state.ev6_aol_source_healthy and 0 < stamp <= now_ns and now_ns - stamp <= int(state.ev6_aol_timeout_ns))
    self._samples = state.ev6_aol_samples if self._buttons_current else ()

  def _perform(self, action):
    # Same configured desired/pause actions as canonical non-explicit intent.
    if action == AOL_TOGGLE:
      if self.allowed_latch:
        # Withdrawal is always allowed, including the press that removes physical authority.
        self.allowed_latch = False
      elif (self.settings.enabled and self._buttons_current and self.physical.authorized
            and self._last_latch_edge_ns > 0 and not self._fault_inhibit and not self._acc_faulted):
        self.allowed_latch = True
      else:
        return
      if self.settings.main_action != AOL_TOGGLE and self.settings.lkas_action != AOL_TOGGLE:
        self._controller_override = self.allowed_latch
      if self.allowed_latch:
        self.pause_lateral = False
    else:
      super()._perform(action)

  def optional_set_release_policy(self):
    return bool(self.settings.enabled and self.settings.lkas_action == AOL_TOGGLE
                and self._buttons_current and not self._fault_inhibit and not self._acc_faulted)

  def auxiliary_supported(self):
    # Canonical auxiliary proposals remain gated by this vehicle's physical owner.
    return True

  def update(self, CS, *, consumed_buttons=frozenset(), fault_active=None, now_ns=0, native_rejection_ns=0,
             standard_enabled=False, standard_active=False):
    self.physical.lkas_on_engage = self.settings.enabled and self.settings.lkas_action == AOL_TOGGLE
    self._acc_faulted = bool(CS.accFaulted)
    ordinary = CS.as_reader().as_builder()
    ordinary.buttonEvents = [event for event in CS.buttonEvents if event.type not in (ButtonType.mainCruise, ButtonType.lkas, ButtonType.cancel)]
    rejected = self._native_rejection_ns < native_rejection_ns <= now_ns
    super().update(ordinary, consumed_buttons=consumed_buttons, fault_active=fault_active, now_ns=now_ns,
                   native_rejection_ns=native_rejection_ns, standard_enabled=standard_enabled)
    healthy = (self._buttons_current and CS.canValid and not CS.canTimeout and not fault_active
               and not CS.steerFaultPermanent and not self._fault_inhibit and not self._acc_faulted)
    if not healthy or rejected:
      self.physical.revoke()
      self.allowed_latch = False
      self._last_latch_edge_ns = 0
      self._raw_neutral_seen = False
    lkas_managed = self.settings.enabled and self.settings.lkas_action == AOL_TOGGLE
    main_managed = self.settings.main_action == AOL_TOGGLE
    auto_main = self.settings.enabled and not lkas_managed and not main_managed
    if healthy and not rejected:
      for main, lkas, cruise in self._samples:
        previous_main, previous_lkas = self.physical.previous_main, self.physical.previous_lkas
        previous_cruise = self.physical.previous_cruise
        if not self._raw_neutral_seen:
          # The filtered base phase is not physical neutral. Initial/restarted
          # held packets only establish actual levels; no replayed press credit.
          self.physical.previous_main, self.physical.previous_lkas = bool(main), bool(lkas)
          self.physical.previous_cruise = cruise
          self._raw_neutral_seen = not (main or lkas) and cruise == Buttons.NONE
          continue
        self.physical.observe(main, lkas, cruise, main_available=CS.cruiseState.available)
        main_press = bool(main and not previous_main)
        lkas_press = bool(lkas and not previous_lkas)
        engagement_release = (self.physical.lkas_on_engage and cruise != previous_cruise
                              and previous_cruise in (Buttons.SET_DECEL, Buttons.RES_ACCEL))
        if main_press or lkas_press or engagement_release:
          # Fresh physical authorization never forces configured desired intent.
          self._last_latch_edge_ns = now_ns
        if main_press and int(ButtonType.mainCruise) not in consumed_buttons:
          self._perform(self.settings.main_action)
        if lkas_press and int(ButtonType.lkas) not in consumed_buttons:
          self._perform(self.settings.lkas_action)
          if lkas_managed and (CS.cruiseState.enabled or self.pause_lateral):
            self.pause_lateral = not self.allowed_latch
      if not CS.cruiseState.available:
        self.physical.main_on = False
      if auto_main:
        self.allowed_latch = bool(CS.cruiseState.available and self._controller_override is not False)
    engagement_started = bool(standard_active and not self._active_previous)
    self._active_previous = bool(standard_active)
    if (engagement_started and lkas_managed and healthy and not rejected and not self._fault_inhibit
        and not CS.accFaulted and self.physical.authorized and self._last_latch_edge_ns > 0):
      self.allowed_latch = True
    # Retain current fail-closed startup/reset contracts in addition to Dom's gate.
    if not (healthy and self.physical.authorized and self._last_latch_edge_ns > 0):
      self.allowed_latch = False
    self._samples = ()

  def output(self, CS):
    desired, pause_lateral, pause_longitudinal = super().output(CS)
    return (desired and self._buttons_current and self.physical.authorized and self._last_latch_edge_ns > 0
            and not self._fault_inhibit and not CS.accFaulted), pause_lateral, pause_longitudinal
