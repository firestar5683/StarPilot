from opendbc.car.hyundai.blended_stock_aol import (
  qualified as qualified_blended_stock, qualified_alpha as qualified_blended_alpha,
  WORDS as BLENDED_STOCK_WORDS, ALPHA_WORDS as BLENDED_ALPHA_WORDS,
)
from opendbc.car.hyundai.canfd_angle_aol import qualified as qualified_angle_aol, temporary_restriction, ANGLE_AOL_WORDS
from opendbc.car.hyundai.classic_long_aol import (
  qualified as qualified_classic_long,
  aol_word as classic_long_word,
  native_accepts as classic_long_accepts,
  LONG_AOL_WORDS,
)
from opendbc.car.hyundai.classic_scc_aol import (
  qualified as qualified_classic_scc,
  aol_word as classic_aol_word,
  native_accepts as classic_native_accepts,
  native_profile_supported as classic_native_profile_supported,
)
from opendbc.car.hyundai.canfd_stock_aol import (
  qualified as qualified_canfd_stock, qualified_long as qualified_canfd_long,
  LONG_AOL_WORDS as CANFD_LONG_AOL_WORDS, STOCK_AOL_MARKER, STOCK_AOL_WORDS,
)
from opendbc.car.hyundai.non_scc_aol import qualified as qualified_non_scc, aol_word, AOL_MARKER, AOL_EXPERIENCE, AOL_WORDS
from opendbc.car.hyundai.kona_aol import allow_lateral_onset as kona_lateral_onset
from opendbc.car.structs import car
from opendbc.car.hyundai.values import CAR as HyundaiCAR, HyundaiFlags
from opendbc.car.hyundai.ccnc_ev_stock import qualified as qualified_ccnc_ev_stock, request_allowed, STOCK_SAFETY_PARAMS
from opendbc.car.hyundai.ioniq6_handoff import IONIQ6_LONG_PREARM_ENABLED
from openpilot.starpilot.aol.policy import AolVehiclePolicy
from openpilot.starpilot.longitudinal.ioniq6_start import eligible as ioniq6_long_eligible


IONIQ6_STOCK_AOL_SAFETY_PARAMS = frozenset((0x0811, 0x0891))
IONIQ6_AOL_SAFETY_PARAMS = frozenset((0x0811, 0x0891, 0x8815, 0x8895))
IONIQ6_STOCK_SAFETY_PARAMS = frozenset((0x11, 0x91))
_REQUIRED_FLAGS = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEER_MSG)
_FORBIDDEN_FLAGS = int(HyundaiFlags.CANFD_ALT_BUTTONS | HyundaiFlags.CANFD_ANGLE_STEERING | HyundaiFlags.CANFD_CAMERA_SCC)


def _ioniq6_hda2_base(CP) -> bool:
  if (
    str(CP.carFingerprint) != str(HyundaiCAR.HYUNDAI_IONIQ_6)
    or CP.brand != 'hyundai'
    or CP.radarUnavailable
    or CP.notCar
    or CP.passive
    or CP.dashcamOnly
    or len(CP.safetyConfigs) != 1
    or CP.safetyConfigs[0].safetyModel != car.CarParams.SafetyModel.hyundaiCanfd
  ):
    return False
  flags = int(CP.flags)
  return flags & _REQUIRED_FLAGS == _REQUIRED_FLAGS and not flags & _FORBIDDEN_FLAGS


def _stock_ioniq6(CP, *, marked_only=False) -> bool:
  if not _ioniq6_hda2_base(CP) or CP.openpilotLongitudinalControl or not CP.pcmCruise:
    return False
  stock = 0x91 if int(CP.flags) & int(HyundaiFlags.CANFD_LKA_STEER_MSG_ALT) else 0x11
  raw = int(CP.safetyConfigs[0].safetyParam)
  return raw == (stock | 0x0800) or (not marked_only and raw == stock)


def qualified_ioniq6(CP) -> bool:
  if _stock_ioniq6(CP, marked_only=True):
    return True
  if not _ioniq6_hda2_base(CP) or not CP.openpilotLongitudinalControl or CP.pcmCruise:
    return False
  flags = int(CP.flags)
  raw = int(CP.safetyConfigs[0].safetyParam)
  return raw == (0x8895 if flags & int(HyundaiFlags.CANFD_LKA_STEER_MSG_ALT) else 0x8815)


def ioniq6_settings_capable(CP) -> bool:
  # Stock ACC lateral settings are independent of the experimental LONG opt-in.
  return _stock_ioniq6(CP) or (IONIQ6_LONG_PREARM_ENABLED and ioniq6_long_eligible(CP))


def policy_for(CP) -> AolVehiclePolicy:
  if qualified_blended_alpha(CP):
    return AolVehiclePolicy(intent_supported=True, settings_supported=True, runtime_supported=True,
                            normal_runtime_supported=True, ordinary_axis_ack_required=qualified_blended_alpha(CP, marked_only=True),
                            full_axis_runtime_required=qualified_blended_alpha(CP, marked_only=True),
                            explicit_latch=True, alternative_experience_addition=32)
  if qualified_blended_stock(CP):
    return AolVehiclePolicy(intent_supported=True, settings_supported=True, runtime_supported=True,
                            normal_runtime_supported=True, explicit_latch=True, alternative_experience_addition=32)
  if qualified_angle_aol(CP):
    return AolVehiclePolicy(
      intent_supported=True,
      settings_supported=True,
      runtime_supported=True,
      normal_runtime_supported=True,
      ordinary_axis_ack_required=qualified_ccnc_ev_stock(CP),
      explicit_latch=True,
      alternative_experience_addition=32,
    )
  if qualified_classic_long(CP):
    return AolVehiclePolicy(
      intent_supported=True,
      settings_supported=True,
      runtime_supported=True,
      normal_runtime_supported=True,
      explicit_latch=True,
      safety_param_addition=classic_long_word(CP) ^ int(CP.safetyConfigs[0].safetyParam),
      alternative_experience_addition=AOL_EXPERIENCE,
    )
  if qualified_classic_scc(CP):
    return AolVehiclePolicy(
      intent_supported=True,
      settings_supported=True,
      runtime_supported=True,
      normal_runtime_supported=True,
      explicit_latch=True,
      safety_param_addition=classic_aol_word(CP) ^ int(CP.safetyConfigs[0].safetyParam),
      alternative_experience_addition=AOL_EXPERIENCE,
    )
  if qualified_canfd_long(CP):
    return AolVehiclePolicy(intent_supported=True, settings_supported=True, runtime_supported=True,
                            normal_runtime_supported=True, explicit_latch=True, safety_param_addition=0x0800,
                            alternative_experience_addition=32)
  if qualified_canfd_stock(CP):
    return AolVehiclePolicy(
      intent_supported=True,
      settings_supported=True,
      runtime_supported=True,
      normal_runtime_supported=True,
      explicit_latch=True,
      safety_param_addition=STOCK_AOL_MARKER,
    )
  if qualified_non_scc(CP):
    return AolVehiclePolicy(
      intent_supported=True,
      settings_supported=True,
      runtime_supported=True,
      normal_runtime_supported=True,
      explicit_latch=True,
      safety_param_addition=AOL_MARKER | (aol_word(CP) & 0x0800),
      alternative_experience_addition=AOL_EXPERIENCE,
    )
  if qualified_ccnc_ev_stock(CP):
    return AolVehiclePolicy(ordinary_axis_ack_required=True)
  stock = _stock_ioniq6(CP)
  qualified = qualified_ioniq6(CP) or stock
  settings = ioniq6_settings_capable(CP) or qualified
  distance_personality = ioniq6_long_eligible(CP)
  return AolVehiclePolicy(
    intent_supported=qualified,
    settings_supported=settings,
    runtime_supported=qualified,
    normal_runtime_supported=qualified and (stock or distance_personality),
    explicit_latch=qualified,
    distance_personality=distance_personality,
    safety_param_addition=0x0800 if stock else 0,
    fixed_cruise_buttons=settings,
    distance_pause_only=settings,
    paddle_pause=settings,
  )


def native_profile_supported(model: int, param: int) -> bool:
  return (
    (model == int(car.CarParams.SafetyModel.hyundai) and param in LONG_AOL_WORDS | BLENDED_STOCK_WORDS | BLENDED_ALPHA_WORDS)
    or classic_native_profile_supported(model, param)
    or (
      model == int(car.CarParams.SafetyModel.hyundaiCanfd)
      and param in IONIQ6_AOL_SAFETY_PARAMS | CANFD_LONG_AOL_WORDS | ANGLE_AOL_WORDS | STOCK_AOL_WORDS | set(STOCK_SAFETY_PARAMS.values())
    )
    or (model == int(car.CarParams.SafetyModel.hyundai) and param in AOL_WORDS)
  )


def native_accepts_cp(CP, model: int, param: int) -> bool:
  if qualified_blended_alpha(CP, marked_only=True) or qualified_blended_stock(CP, marked_only=True):
    return model == int(car.CarParams.SafetyModel.hyundai) and param == CP.safetyConfigs[0].safetyParam
  if qualified_angle_aol(CP, marked_only=True):
    return model == int(car.CarParams.SafetyModel.hyundaiCanfd) and param == CP.safetyConfigs[0].safetyParam
  if qualified_classic_long(CP, marked_only=True):
    return classic_long_accepts(CP, model, param)
  if qualified_classic_scc(CP, marked_only=True):
    return classic_native_accepts(CP, model, param)
  if qualified_canfd_long(CP, marked_only=True):
    return model == int(car.CarParams.SafetyModel.hyundaiCanfd) and param == CP.safetyConfigs[0].safetyParam
  if qualified_canfd_stock(CP, marked_only=True):
    return model == int(car.CarParams.SafetyModel.hyundaiCanfd) and param == CP.safetyConfigs[0].safetyParam
  if qualified_non_scc(CP):
    return CP.alternativeExperience == AOL_EXPERIENCE and model == int(car.CarParams.SafetyModel.hyundai) and param == aol_word(CP)
  return (
    qualified_ccnc_ev_stock(CP) and model == int(car.CarParams.SafetyModel.hyundaiCanfd) and param == STOCK_SAFETY_PARAMS[CP.carFingerprint]
  ) or qualified_ioniq6(CP)


def native_latch_rejected(CP, native) -> bool:
  # In this exact native policy a requested lateral axis remains permitted
  # through pedal override; denial means the physical authorization was lost.
  return (
    (
      qualified_angle_aol(CP, marked_only=True)
      or qualified_blended_stock(CP, marked_only=True)
      or qualified_blended_alpha(CP, marked_only=True)
      or qualified_classic_long(CP, marked_only=True)
      or qualified_ioniq6(CP)
      or qualified_non_scc(CP)
      or qualified_canfd_long(CP, marked_only=True)
      or qualified_canfd_stock(CP, marked_only=True)
      or qualified_classic_scc(CP, marked_only=True)
    )
    and native.requestedLateral
    and not native.lateralAllowed
  )


def create_intent(CP, settings):
  if qualified_blended_alpha(CP) or qualified_classic_long(CP):
    from openpilot.starpilot.car.hyundai.classic_long_intent import ClassicLongCardIntent

    return ClassicLongCardIntent(CP, settings)
  if qualified_classic_scc(CP):
    from openpilot.starpilot.car.hyundai.classic_scc_intent import ClassicSccCardIntent

    return ClassicSccCardIntent(CP, settings)
  if qualified_non_scc(CP):
    from openpilot.starpilot.car.hyundai.forte_intent import ForteCardIntent

    return ForteCardIntent(CP, settings)
  from openpilot.starpilot.aol.intent import AolCardIntent

  return AolCardIntent(settings, explicit_latch=policy_for(CP).explicit_latch)


def ordinary_axis_request_allowed(CP, CS) -> bool:
  return bool(request_allowed(CP, CS))


def allow_lateral_onset(CP, *, requested, normal_enabled, steering_pressed, previous_active):
  if not (qualified_non_scc(CP) and CP.carFingerprint == HyundaiCAR.HYUNDAI_KONA_NON_SCC):
    return bool(requested)
  return kona_lateral_onset(permitted=requested, normal_enabled=normal_enabled, steering_pressed=steering_pressed, previous_active=previous_active)


def retain_on_native_denial(CP, native, state):
  return bool(qualified_angle_aol(CP, marked_only=True) and native.requestedLateral and not native.lateralAllowed and temporary_restriction(CP, state))
