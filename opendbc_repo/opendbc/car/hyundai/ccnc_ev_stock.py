"""Exact stock-SCC CCNC EV ordinary steering transport contract."""

from opendbc.car import structs
from opendbc.car.hyundai.values import CAR, HyundaiFlags

STOCK_SAFETY_PARAMS = {CAR.HYUNDAI_IONIQ_5_PE: 0x5491, CAR.KIA_EV9: 0x5c91}
_REQUIRED = (HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CCNC | HyundaiFlags.CANFD_ANGLE_STEERING |
             HyundaiFlags.CANFD_LKA_STEER_MSG | HyundaiFlags.CANFD_LKA_STEER_MSG_ALT)

# These generic metadata flags never select the EV gear decoder.
_IGNORED_EV_GEAR_FLAGS = HyundaiFlags.CANFD_ALT_GEARS | HyundaiFlags.CANFD_ALT_GEARS_2


def qualified(cp):
  return (cp.carFingerprint in STOCK_SAFETY_PARAMS and cp.brand == "hyundai" and
          not (cp.notCar or cp.passive or cp.dashcamOnly or cp.openpilotLongitudinalControl) and cp.pcmCruise and
          cp.alternativeExperience == 0 and int(cp.flags) & ~int(_IGNORED_EV_GEAR_FLAGS) == int(_REQUIRED) and
          len(cp.safetyConfigs) == 1 and cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.hyundaiCanfd and
          cp.safetyConfigs[0].safetyParam == STOCK_SAFETY_PARAMS[cp.carFingerprint])


def request_allowed(cp, state):
  return (qualified(cp) and state.canValid and not state.canTimeout and state.cruiseState.enabled and
          state.gearShifter == structs.CarState.GearShifter.drive and not state.standstill and
          not (state.brakePressed or state.gasPressed or state.steerFaultTemporary or state.steerFaultPermanent))


def replacement_requested(cp, control, state):
  from opendbc.car.hyundai.canfd_angle_aol import qualified as angle_qualified, command_allowed

  if angle_qualified(cp, marked_only=True):
    return command_allowed(cp, state) and control.latActive
  return request_allowed(cp, state) and control.latActive
