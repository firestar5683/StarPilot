from opendbc.car.tesla.preap.aol import qualified, temporary_restriction
from openpilot.starpilot.aol.policy import AolVehiclePolicy
from openpilot.starpilot.car.tesla.stock_intent import TeslaPreapCardIntent


def policy_for(cp):
  admitted = qualified(cp)
  return AolVehiclePolicy(intent_supported=admitted, settings_supported=admitted,
                          runtime_supported=admitted, normal_runtime_supported=admitted,
                          ordinary_axis_ack_required=qualified(cp, marked_only=True),
                          explicit_latch=admitted, physical_stalk_owner=admitted, fixed_cruise_buttons=admitted,
                          alternative_experience_addition=32 if admitted else 0)


def native_profile_supported(model, param):
  return model == 39 and param == 0


def native_accepts_cp(cp, model, param):
  return qualified(cp, marked_only=True) and native_profile_supported(model, param)


def native_latch_rejected(cp, native):
  return qualified(cp, marked_only=True) and native.requestedLateral and not native.lateralAllowed


def ordinary_axis_request_allowed(cp, state):
  return qualified(cp, marked_only=True) and state.canValid and not state.canTimeout and not state.steerFaultPermanent


def retain_on_native_denial(cp, native, state):
  return temporary_restriction(cp, state)


def create_intent(cp, settings):
  return TeslaPreapCardIntent(cp, settings)
