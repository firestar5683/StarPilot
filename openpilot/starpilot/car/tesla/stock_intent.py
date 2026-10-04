from dataclasses import replace

from opendbc.car import structs
from openpilot.starpilot.aol.intent import AolCardIntent, ButtonType


class TeslaPreapCardIntent(AolCardIntent):
  observe_stock_engagement = True

  @property
  def settings(self):
    return self._settings

  @settings.setter
  def settings(self, value):
    self._settings = replace(value, enabled=True, main_action=0, lkas_action=0)

  def __init__(self, cp, settings):
    # The physical stalk owner is independent of the saved global AOL switch.
    super().__init__(settings, explicit_latch=True)
    self.pull_held = False
    self.pull_neutral = False

  def update(self, CS, **kwargs):
    state = structs.CarState(**CS.to_dict())
    pull = False
    cancel = False
    events = []
    for event in CS.buttonEvents:
      if event.type == ButtonType.setCruise:
        if event.pressed:
          pull = self.pull_neutral and not self.pull_held
          self.pull_held = True
          self.pull_neutral = False
        else:
          self.pull_held = False
          self.pull_neutral = True
      else:
        cancel |= event.type == ButtonType.cancel and event.pressed
        events.append(structs.CarState.ButtonEvent(**event.to_dict()))
    state.buttonEvents = events
    super().update(state.as_reader(), **kwargs)
    healthy = bool(CS.canValid and not CS.canTimeout)
    fault = bool(kwargs.get('fault_active') or CS.accFaulted or CS.steerFaultPermanent or CS.steeringDisengage or
                 CS.doorOpen or CS.seatbeltUnlatched or CS.gearShifter != structs.CarState.GearShifter.drive)
    if not healthy or fault or cancel:
      self.allowed_latch = False
      self.pull_neutral = False
    elif pull and not self._fault_inhibit:
      self.allowed_latch = True
      self.pause_lateral = False
      self._last_latch_edge_ns = kwargs.get('now_ns', 0)
    elif not self.pull_held:
      self.pull_neutral = True
