from opendbc.car.tesla.preap.aol import qualified, temporary_restriction
from openpilot.starpilot.aol.policy import AolVehiclePolicy
from openpilot.starpilot.car.tesla.stock_intent import TeslaPreapCardIntent
from opendbc.car.tesla.screen_button import screen_tap_supported, screen_qualified, SCREEN_WORDS
from openpilot.starpilot.car.tesla.screen_intent import TeslaScreenCardIntent


def policy_for(cp):
  if screen_tap_supported(cp):
    admitted = screen_qualified(cp)
    return AolVehiclePolicy(intent_supported=admitted, settings_supported=True,
                            runtime_supported=admitted, normal_runtime_supported=admitted,
                            ordinary_axis_ack_required=screen_qualified(cp, marked_only=True),
                            full_axis_runtime_required=admitted,
                            cruise_main_required=not screen_qualified(cp, marked_only=True),
                            explicit_latch=admitted, alternative_experience_addition=32 if admitted else 0)
  admitted = qualified(cp)
  return AolVehiclePolicy(intent_supported=admitted, settings_supported=admitted,
                          runtime_supported=admitted, normal_runtime_supported=admitted,
                          ordinary_axis_ack_required=qualified(cp, marked_only=True),
                          explicit_latch=admitted, physical_stalk_owner=admitted, fixed_cruise_buttons=admitted,
                          alternative_experience_addition=32 if admitted else 0)


def native_profile_supported(model, param):
  return (model == 39 and param == 0) or (model == 10 and param in SCREEN_WORDS)


def native_accepts_cp(cp, model, param):
  return (qualified(cp, marked_only=True) or screen_qualified(cp, marked_only=True)) and native_profile_supported(model, param)


def native_latch_rejected(cp, native):
  return (qualified(cp, marked_only=True) or screen_qualified(cp, marked_only=True)) and native.requestedLateral and not native.lateralAllowed


def ordinary_axis_request_allowed(cp, state):
  return bool((qualified(cp, marked_only=True) or screen_qualified(cp, marked_only=True)) and
              state.canValid and not state.canTimeout and not state.steerFaultPermanent)


def retain_on_native_denial(cp, native, state):
  return temporary_restriction(cp, state)


def create_intent(cp, settings):
  return TeslaScreenCardIntent(cp, settings) if screen_qualified(cp) else TeslaPreapCardIntent(cp, settings)
