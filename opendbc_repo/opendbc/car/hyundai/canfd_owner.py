"""Selected safety slot for the exact first-generation captured CANFD owner."""
from opendbc.car.structs import CarParams
from opendbc.car.hyundai.values import CAR, HyundaiFlags


def topology_index(cp):
  if len(cp.safetyConfigs) == 1:
    return 0 if cp.safetyConfigs[0].safetyModel == CarParams.SafetyModel.hyundaiCanfd else None
  if len(cp.safetyConfigs) != 2:
    return None
  auxiliary, owner = cp.safetyConfigs
  required = HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEER_MSG
  excluded = (HyundaiFlags.CANFD_ANGLE_STEERING | HyundaiFlags.CANFD_LKA_STEER_MSG_ALT |
              HyundaiFlags.CANFD_ALT_BUTTONS | HyundaiFlags.CANFD_CAMERA_SCC | HyundaiFlags.CCNC | HyundaiFlags.HYBRID)
  if (cp.brand != 'hyundai' or cp.carFingerprint not in (CAR.KIA_EV6, CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN) or
      cp.passive or cp.dashcamOnly or cp.notCar or cp.steerControlType != CarParams.SteerControlType.torque or
      cp.flags & required != required or cp.flags & excluded or
      auxiliary.safetyModel != CarParams.SafetyModel.noOutput or auxiliary.safetyParam != 0 or
      owner.safetyModel != CarParams.SafetyModel.hyundaiCanfd):
    return None
  return 1


def config_index(cp):
  owner = topology_index(cp)
  if owner != 1:
    return owner
  raw = int(cp.safetyConfigs[owner].safetyParam)
  if cp.openpilotLongitudinalControl and not cp.pcmCruise:
    if raw == 0x15 and cp.alternativeExperience == 0:
      return 1
    if cp.carFingerprint == CAR.KIA_EV6 and raw == 0x815 and cp.alternativeExperience == 32:
      return 1
  elif not cp.openpilotLongitudinalControl and cp.pcmCruise and cp.alternativeExperience == 0 and raw in (0x11, 0x811):
    return 1
  return None
