"""Stock-cruise AOL for the shared EV CAN FD torque/button layout."""
from opendbc.car.structs import CarParams
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from opendbc.car.hyundai.hyundaicanfd import CanBus

STOCK_AOL_MARKER = 0x0800
STOCK_AOL_WORDS = frozenset((0x0811, 0x0891))
# Ioniq 6 retains its existing stock/longitudinal owner and settings.
STOCK_EV_CARS = frozenset((CAR.HYUNDAI_KONA_EV_2ND_GEN, CAR.HYUNDAI_IONIQ_5,
  CAR.HYUNDAI_IONIQ_5_N, CAR.KIA_NIRO_EV_2ND_GEN, CAR.KIA_EV6,
  CAR.GENESIS_GV60_EV_1ST_GEN, CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN))


def qualified(cp, *, marked_only=False):
  required = HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEER_MSG
  allowed = (required | HyundaiFlags.CANFD_LKA_STEER_MSG_ALT | HyundaiFlags.CANFD_ALT_GEARS |
             HyundaiFlags.CANFD_ALT_GEARS_2 | HyundaiFlags.CANFD_NO_RADAR_DISABLE | HyundaiFlags.CCNC)
  if (cp.brand != 'hyundai' or cp.carFingerprint not in STOCK_EV_CARS or
      cp.passive or cp.dashcamOnly or cp.notCar or cp.alternativeExperience != 0 or
      cp.openpilotLongitudinalControl or not cp.pcmCruise or
      cp.steerControlType != CarParams.SteerControlType.torque or
      int(cp.flags) & int(required) != int(required) or int(cp.flags) & ~int(allowed) or
      len(cp.safetyConfigs) != 1):
    return False
  bus = CanBus(cp)
  if (bus.ACAN, bus.ECAN, bus.CAM) != (0, 1, 2):
    return False
  safety = cp.safetyConfigs[0]
  base = 0x91 if cp.flags & HyundaiFlags.CANFD_LKA_STEER_MSG_ALT else 0x11
  return (safety.safetyModel == CarParams.SafetyModel.hyundaiCanfd and
          (safety.safetyParam == (base | STOCK_AOL_MARKER) or
           (not marked_only and safety.safetyParam == base)))
