from opendbc.car import structs
from openpilot.selfdrive.car.cruise import CRUISE_LONG_PRESS
from openpilot.starpilot.aol.intent import AolCardIntent, AOL_TOGGLE, ButtonType


class HondaStockCardIntent(AolCardIntent):
  observe_stock_engagement = True
  observe_active_engagement = True

  def __init__(self, cp, settings):
    super().__init__(settings, explicit_latch=True)
    self.main_seen = False
    self.main_available = False
    self.main_neutral = False
    self.main_pulse = False
    self.cancel_held = False
    self.cancel_ticks = 0
    self._active_previous = False
    self.auto_main = settings.lkas_action != AOL_TOGGLE and settings.main_action != AOL_TOGGLE

  def cancel_action(self, action):
    if action == AOL_TOGGLE and self.settings.enabled:
      self.allowed_latch = not self.allowed_latch
      if self.allowed_latch:
        self.pause_lateral = False
    else:
      self._perform(action)

  def update(self, CS, *, standard_active=False, **kwargs):
    engagement_started = bool(standard_active and not self._active_previous)
    self._active_previous = bool(standard_active)
    now_ns = kwargs.get("now_ns", 0)
    rejected = self._native_rejection_ns < kwargs.get("native_rejection_ns", 0) <= now_ns
    state = structs.CarState(**CS.to_dict())
    events = []
    for event in CS.buttonEvents:
      if event.type == ButtonType.cancel:
        if event.pressed:
          self.cancel_held = True
          self.cancel_ticks = 0
        else:
          if self.cancel_held and 0 < self.cancel_ticks < CRUISE_LONG_PRESS:
            self.cancel_action(self.settings.cancel_actions[0])
          self.cancel_held = False
          self.cancel_ticks = 0
      elif event.type in (ButtonType.mainCruise, ButtonType.lkas):
        action = self.settings.main_action if event.type == ButtonType.mainCruise else self.settings.lkas_action
        if action == AOL_TOGGLE:
          events.append(structs.CarState.ButtonEvent(**event.to_dict()))
        elif event.pressed:
          self._perform(action)
      else:
        events.append(structs.CarState.ButtonEvent(**event.to_dict()))
    available = bool(state.cruiseState.available)
    healthy = state.canValid and not state.canTimeout
    if healthy:
      if self.main_pulse:
        events.append(structs.CarState.ButtonEvent(type=ButtonType.mainCruise, pressed=False))
        self.main_pulse = False
      if not available:
        self.main_neutral = True
      elif self.auto_main and self.main_seen and self.main_neutral and not self.main_available:
        events.append(structs.CarState.ButtonEvent(type=ButtonType.mainCruise, pressed=True))
        self.main_pulse = True
        self.main_neutral = False
      self.main_seen = True
      self.main_available = available
    else:
      self.cancel_held = False
      self.cancel_ticks = 0
      self.main_neutral = False
    state.buttonEvents = events
    super().update(state.as_reader(), **kwargs)
    if not available:
      self.allowed_latch = False
    if self.cancel_held:
      self.cancel_ticks += 1
      if self.cancel_ticks == CRUISE_LONG_PRESS:
        self.cancel_action(self.settings.cancel_actions[1])
      elif self.cancel_ticks == CRUISE_LONG_PRESS * 5:
        self.cancel_action(self.settings.cancel_actions[2])
    manual = self._main_held or self._lkas_held or self.cancel_held or any(
      event.type in (ButtonType.mainCruise, ButtonType.lkas, ButtonType.cancel) for event in CS.buttonEvents)
    driving = state.gearShifter not in (structs.CarState.GearShifter.park, structs.CarState.GearShifter.neutral,
                                       structs.CarState.GearShifter.reverse, structs.CarState.GearShifter.unknown)
    if (engagement_started and self.settings.enabled and self.settings.lkas_action == AOL_TOGGLE and
        available and healthy and driving and not state.accFaulted and not state.steerFaultPermanent and
        not self._fault_inhibit and not rejected and not manual):
      # Match the normal active engagement edge from Dom. Temporary restrictions
      # and existing pause flags still gate output without erasing this intent.
      self.allowed_latch = True
      self._last_latch_edge_ns = now_ns
