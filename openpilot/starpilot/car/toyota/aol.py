from dataclasses import replace

from opendbc.car import structs
from opendbc.car.toyota.values import CAR, ToyotaFlags, EPS_SCALE
from openpilot.starpilot.aol.policy import AolVehiclePolicy
from openpilot.starpilot.aol.intent import AolCardIntent, AOL_TOGGLE

AOL_WORDS = frozenset((73,))


def qualified(cp, *, marked_only=False):
  if (cp is None or cp.brand != 'toyota' or cp.carFingerprint != CAR.TOYOTA_HIGHLANDER_TSS2 or
      cp.notCar or cp.passive or cp.dashcamOnly or not cp.pcmCruise or not cp.openpilotLongitudinalControl or
      cp.steerControlType != structs.CarParams.SteerControlType.torque or
      not cp.flags & ToyotaFlags.TSS2 or cp.flags & (ToyotaFlags.SECOC | ToyotaFlags.ANGLE_CONTROL | ToyotaFlags.UNSUPPORTED_DSU) or
      len(cp.safetyConfigs) != 1 or cp.alternativeExperience not in ((32, 160) if marked_only else (0, 32, 128, 160))):
    return False
  from opendbc.car.toyota.interface import toyota_auto_hold_supported
  hold = bool(cp.flags & ToyotaFlags.AUTO_BRAKE_HOLD)
  if ((cp.alternativeExperience & 128 and not hold) or
      (hold and (not toyota_auto_hold_supported(cp) or cp.alternativeExperience not in (0, 128, 160)))):
    return False
  required_flags = ToyotaFlags.TSS2 | ToyotaFlags.NO_DSU | ToyotaFlags.RAISED_ACCEL_LIMIT
  allowed_flags = required_flags | ToyotaFlags.HYBRID | ToyotaFlags.HAS_BSM
  if cp.flags & required_flags != required_flags or int(cp.flags) & ~int(allowed_flags | ToyotaFlags.AUTO_BRAKE_HOLD):
    return False
  config = cp.safetyConfigs[0]
  expected = EPS_SCALE[CAR.TOYOTA_HIGHLANDER_TSS2]
  return config.safetyModel == structs.CarParams.SafetyModel.toyota and config.safetyParam == expected


def policy_for(cp):
  admitted = qualified(cp)
  return AolVehiclePolicy(intent_supported=admitted, settings_supported=admitted, runtime_supported=admitted,
                          normal_runtime_supported=admitted, ordinary_axis_ack_required=qualified(cp, marked_only=True),
                          full_axis_runtime_required=admitted, fixed_cruise_buttons=admitted, distance_pause_only=admitted,
                          alternative_experience_addition=32 if admitted else 0)


def native_profile_supported(model, param):
  return model == int(structs.CarParams.SafetyModel.toyota) and param in AOL_WORDS


def native_accepts_cp(cp, model, param):
  return qualified(cp, marked_only=True) and native_profile_supported(model, param)


def native_latch_rejected(cp, native):
  return qualified(cp, marked_only=True) and native.requestedLateral and not native.lateralAllowed


def ordinary_axis_request_allowed(cp, state):
  return qualified(cp, marked_only=True) and state.canValid and not state.canTimeout and not state.steerFaultPermanent


def retain_on_native_denial(cp, native, state):
  gears = structs.CarState.GearShifter
  return bool(state is not None and qualified(cp, marked_only=True) and state.canValid and not state.canTimeout and
              not state.steerFaultPermanent and
              (state.gearShifter not in (gears.drive, gears.sport, gears.low) or state.steerFaultTemporary or state.vehicleSensorsInvalid))


class ToyotaCardIntent(AolCardIntent):
  def __init__(self, settings):
    effective = replace(settings, lkas_action=0, main_action=0,
                        distance_actions=tuple(0 if action == AOL_TOGGLE else action for action in settings.distance_actions),
                        cancel_actions=tuple(0 if action == AOL_TOGGLE else action for action in settings.cancel_actions),
                        mode_actions=tuple(0 if action == AOL_TOGGLE else action for action in settings.mode_actions),
                        custom_actions=tuple(0 if action == AOL_TOGGLE else action for action in settings.custom_actions))
    super().__init__(effective)


def create_intent(cp, settings):
  return ToyotaCardIntent(settings)
