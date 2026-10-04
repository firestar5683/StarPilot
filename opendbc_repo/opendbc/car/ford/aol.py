from opendbc.car import structs
from opendbc.car.ford.values import CAR, FordFlags

AOL_EXPERIENCE = 32
CLASSIC = frozenset((CAR.FORD_BRONCO_SPORT_MK1, CAR.FORD_ESCAPE_MK4, CAR.FORD_FOCUS_MK4,
                     CAR.FORD_MAVERICK_MK1, CAR.FORD_EXPLORER_MK6))
GENERIC_CANFD = frozenset((CAR.FORD_ESCAPE_MK4_5, CAR.FORD_EXPEDITION_MK4, CAR.FORD_F_150_MK14,
                         CAR.FORD_F_150_LIGHTNING_MK1, CAR.FORD_RANGER_MK2))
AOL_WORDS = frozenset((8, 9, 10, 11, 12, 13, 18, 19, 32, 33, 66, 67))


def qualified(cp, *, marked_only=False):
  if (cp.brand != 'ford' or cp.carFingerprint not in tuple(CAR) or cp.passive or cp.notCar or cp.dashcamOnly or
      cp.steerControlType != structs.CarParams.SteerControlType.angle or
      cp.transmissionType != structs.CarParams.TransmissionType.automatic or len(cp.safetyConfigs) != 1 or
      cp.alternativeExperience not in ((32,) if marked_only else (0, 32))):
    return False
  flags = int(cp.flags) & ~int(FordFlags.HAS_BSM)
  if cp.carFingerprint in CLASSIC and flags == 0:
    base = 32
  elif cp.carFingerprint == CAR.FORD_MUSTANG_MACH_E_MK1 and flags == int(FordFlags.CANFD):
    base = 18
  elif cp.carFingerprint in GENERIC_CANFD and flags == int(FordFlags.CANFD):
    base = 66
  elif cp.carFingerprint == CAR.FORD_EDGE_MK2 and flags == int(FordFlags.NEW_PORT | FordFlags.ALT_STEER_ANGLE):
    base = 8
  elif cp.carFingerprint == CAR.FORD_MONDEO_MK5 and flags == int(FordFlags.NEW_PORT | FordFlags.CANFD):
    base = 10
  elif cp.carFingerprint == CAR.FORD_TRANSIT_MK5 and flags == int(FordFlags.NEW_PORT | FordFlags.LKA_STEERING):
    base = 12
  else:
    return False
  safety = cp.safetyConfigs[0]
  return (cp.pcmCruise and
          safety.safetyModel == structs.CarParams.SafetyModel.ford and
          safety.safetyParam == (base | int(cp.openpilotLongitudinalControl)))


def temporary_restriction(cp, state):
  gears = structs.CarState.GearShifter
  return bool(state is not None and qualified(cp, marked_only=True) and state.canValid and not state.canTimeout
              and not state.steerFaultPermanent and
              (state.gearShifter not in (gears.drive, gears.sport, gears.low) or state.steerFaultTemporary or state.vehicleSensorsInvalid))


def native_observation(native, *, latched, panda_ready, restricted, now_ns, pending_since_ns):
  lost = not panda_ready or native is None
  if not latched or lost or restricted:
    return 0, lost, False
  if native.requestedLateral and native.lateralAllowed:
    return 0, False, False
  pending_since_ns = pending_since_ns or now_ns
  return pending_since_ns, False, now_ns - pending_since_ns >= 200_000_000
