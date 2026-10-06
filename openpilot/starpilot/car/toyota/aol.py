from dataclasses import replace

from opendbc.car import structs
from opendbc.car.toyota.values import CAR, ToyotaFlags, ToyotaSafetyFlags, EPS_SCALE, uses_toyota_auto_hold_aeb
from openpilot.starpilot.aol.policy import AolVehiclePolicy
from openpilot.starpilot.aol.intent import AolCardIntent, AOL_TOGGLE

AOL_WORDS = frozenset((73, 585))
RADAR_TORQUE_CARS = frozenset((CAR.TOYOTA_CHR_TSS2, CAR.TOYOTA_RAV4_TSS2_2022))
CAMERA_TORQUE_CARS = frozenset((
  CAR.TOYOTA_ALPHARD_TSS2, CAR.TOYOTA_AVALON_TSS2, CAR.TOYOTA_CAMRY_TSS2, CAR.TOYOTA_COROLLA_TSS2,
  CAR.TOYOTA_HIGHLANDER_TSS2, CAR.TOYOTA_PRIUS_TSS2, CAR.TOYOTA_RAV4_TSS2, CAR.TOYOTA_MIRAI,
  CAR.LEXUS_ES_TSS2, CAR.LEXUS_NX_TSS2, CAR.LEXUS_LC_TSS2, CAR.LEXUS_RX_TSS2,
  CAR.LEXUS_IS_TSS2, CAR.LEXUS_RC_TSS2,
))


def qualified(cp, *, marked_only=False):
  if (cp is None or cp.brand != 'toyota' or cp.carFingerprint not in CAMERA_TORQUE_CARS | RADAR_TORQUE_CARS or
      cp.notCar or cp.passive or cp.dashcamOnly or not cp.pcmCruise or
      (cp.carFingerprint not in RADAR_TORQUE_CARS and not cp.openpilotLongitudinalControl) or
      cp.steerControlType != structs.CarParams.SteerControlType.torque or
      not cp.flags & ToyotaFlags.TSS2 or cp.flags & (ToyotaFlags.SECOC | ToyotaFlags.ANGLE_CONTROL | ToyotaFlags.UNSUPPORTED_DSU) or
      len(cp.safetyConfigs) != 1):
    return False
  from opendbc.car.toyota.interface import toyota_auto_hold_supported
  hold = bool(cp.flags & ToyotaFlags.AUTO_BRAKE_HOLD)
  hold_permission = 256 if uses_toyota_auto_hold_aeb(cp) else 128
  allowed_experience = (32 | hold_permission,) if hold else (32,)
  if not marked_only:
    allowed_experience += (0, hold_permission) if hold else (0,)
  if (cp.alternativeExperience not in allowed_experience or
      hold and not toyota_auto_hold_supported(cp)):
    return False
  required_flags = ToyotaFlags.TSS2 | ToyotaFlags.NO_DSU | ToyotaFlags.RAISED_ACCEL_LIMIT
  radar = cp.carFingerprint in RADAR_TORQUE_CARS
  if radar:
    required_flags |= ToyotaFlags.RADAR_ACC
    if cp.openpilotLongitudinalControl:
      required_flags |= ToyotaFlags.DISABLE_RADAR
    if hold:
      return False
  allowed_flags = required_flags | ToyotaFlags.HYBRID | ToyotaFlags.HAS_BSM
  if cp.flags & required_flags != required_flags or int(cp.flags) & ~int(allowed_flags | ToyotaFlags.AUTO_BRAKE_HOLD):
    return False
  config = cp.safetyConfigs[0]
  expected = EPS_SCALE[cp.carFingerprint] | (int(ToyotaSafetyFlags.STOCK_LONGITUDINAL) if radar and not cp.openpilotLongitudinalControl else 0)
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
