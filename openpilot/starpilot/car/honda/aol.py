from opendbc.car.structs import car
from opendbc.car.honda.values import CAR, HondaFlags, HondaSafetyFlags
from openpilot.starpilot.aol.policy import AolVehiclePolicy


CLASSIC_BOSCH_AOL_CARS = frozenset((
  CAR.HONDA_NBOX_2G, CAR.HONDA_ACCORD, CAR.HONDA_CIVIC_BOSCH, CAR.HONDA_CIVIC_BOSCH_DIESEL,
  CAR.HONDA_CRV_5G, CAR.HONDA_CRV_HYBRID, CAR.ACURA_RDX_3G, CAR.HONDA_INSIGHT,
  CAR.HONDA_E, CAR.HONDA_E_ADVANCE,
))
_CLASSIC_BOSCH_AOL_IDS = frozenset(str(candidate) for candidate in CLASSIC_BOSCH_AOL_CARS)
_NON_CLASSIC_BOSCH_FLAGS = HondaFlags.BOSCH_RADARLESS | HondaFlags.BOSCH_CANFD | HondaFlags.BOSCH_ALT_RADAR
_AOL_SAFETY_PARAMS = frozenset((
  int(HondaSafetyFlags.BOSCH_LONG),
  int(HondaSafetyFlags.BOSCH_LONG | HondaSafetyFlags.ALT_BRAKE),
  int(HondaSafetyFlags.BOSCH_LONG | HondaSafetyFlags.AOL_BOSCH_LONG),
  int(HondaSafetyFlags.BOSCH_LONG | HondaSafetyFlags.ALT_BRAKE | HondaSafetyFlags.AOL_BOSCH_LONG),
))


def qualified_honda(CP) -> bool:
  return (str(CP.carFingerprint) in _CLASSIC_BOSCH_AOL_IDS and
          CP.brand == 'honda' and bool(CP.flags & HondaFlags.BOSCH) and
          not bool(CP.flags & _NON_CLASSIC_BOSCH_FLAGS) and
          bool(CP.openpilotLongitudinalControl) and not bool(CP.pcmCruise) and
          not bool(CP.notCar) and not bool(CP.passive) and not bool(CP.dashcamOnly) and
          len(CP.safetyConfigs) == 1 and
          CP.safetyConfigs[0].safetyModel == car.CarParams.SafetyModel.hondaBosch and
          int(CP.safetyConfigs[0].safetyParam) in _AOL_SAFETY_PARAMS)


def policy_for(CP) -> AolVehiclePolicy:
  qualified = qualified_honda(CP)
  return AolVehiclePolicy(
    intent_supported=qualified, settings_supported=qualified,
    runtime_supported=qualified and bool(int(CP.safetyConfigs[0].safetyParam) & 0x20),
    distance_personality=qualified,
    safety_param_addition=0x20 if qualified else 0,
  )


def native_profile_supported(model: int, param: int) -> bool:
  return (model == int(car.CarParams.SafetyModel.hondaBosch) and
          param in (34, 35))


def native_accepts_cp(CP, model: int, param: int) -> bool:
  # Honda's native receipt checks the safety profile, then the shared exact CP match.
  return native_profile_supported(model, param)
