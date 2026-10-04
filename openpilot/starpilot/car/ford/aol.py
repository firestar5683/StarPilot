from dataclasses import replace
from opendbc.car import structs
from opendbc.car.ford.aol import qualified, AOL_WORDS, temporary_restriction
from openpilot.starpilot.aol.intent import AolCardIntent, AOL_TOGGLE
from openpilot.starpilot.aol.policy import AolVehiclePolicy


def policy_for(cp):
  if qualified(cp):
    return AolVehiclePolicy(intent_supported=True, settings_supported=True, runtime_supported=True,
                            normal_runtime_supported=True, ordinary_axis_ack_required=True, explicit_latch=True, alternative_experience_addition=32)
  return AolVehiclePolicy()


def native_profile_supported(model, param):
  return model == int(structs.CarParams.SafetyModel.ford) and param in AOL_WORDS


def native_accepts_cp(cp, model, param):
  return qualified(cp, marked_only=True) and native_profile_supported(model, param) and param == cp.safetyConfigs[0].safetyParam


def native_latch_rejected(cp, native):
  return qualified(cp, marked_only=True) and native.requestedLateral and not native.lateralAllowed


def ordinary_axis_request_allowed(cp, cs):
  return qualified(cp, marked_only=True) and cs.canValid and not cs.canTimeout and not cs.steerFaultPermanent


def retain_on_native_denial(cp, native, state):
  return temporary_restriction(cp, state)


class FordCardIntent(AolCardIntent):
  observe_stock_engagement = True
  def __init__(self, cp, settings):
    self.cp = cp
    self.main_seen = False
    self.main_available = False
    self.main_neutral = False
    self.main_pulse = False
    effective = settings
    self.auto_main = settings.lkas_action != AOL_TOGGLE and settings.main_action != AOL_TOGGLE
    if self.auto_main:
      effective = replace(settings, main_action=AOL_TOGGLE)
    super().__init__(effective, explicit_latch=True)

  def update(self, cs, **kwargs):
    state = structs.CarState(**cs.to_dict())
    events = [structs.CarState.ButtonEvent(**event.to_dict()) for event in cs.buttonEvents]
    available = bool(state.cruiseState.available)
    healthy = state.canValid and not state.canTimeout
    if healthy:
      if self.main_pulse:
        events.append(structs.CarState.ButtonEvent(type=structs.CarState.ButtonEvent.Type.mainCruise, pressed=False))
        self.main_pulse = False
      if not self.main_seen or available != self.main_available:
        if not available:
          self.main_neutral = True
        elif self.main_neutral:
          events.append(structs.CarState.ButtonEvent(type=structs.CarState.ButtonEvent.Type.mainCruise, pressed=True))
          self.main_pulse = True
      self.main_seen = True
      self.main_available = available
    if self.auto_main and not available:
      self.allowed_latch = False
    state.buttonEvents = events
    super().update(state.as_reader(), **kwargs)


def create_intent(cp, settings):
  return FordCardIntent(cp, settings)
