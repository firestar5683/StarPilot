from opendbc.car import structs
from opendbc.car.honda.values import CAR, HondaFlags

CLASSIC_BOSCH = frozenset((CAR.HONDA_NBOX_2G, CAR.HONDA_ACCORD, CAR.HONDA_CIVIC_BOSCH,
  CAR.HONDA_CIVIC_BOSCH_DIESEL, CAR.HONDA_CRV_5G, CAR.HONDA_CRV_HYBRID, CAR.ACURA_RDX_3G,
  CAR.HONDA_INSIGHT, CAR.HONDA_E, CAR.HONDA_E_ADVANCE))
RADARLESS = frozenset((CAR.HONDA_CIVIC_2022, CAR.HONDA_HRV_3G, CAR.HONDA_CITY_7G,
  CAR.HONDA_FIT_4G, CAR.ACURA_INTEGRA, CAR.ACURA_ADX))
NIDEC = frozenset((
  CAR.ACURA_ILX,
  CAR.HONDA_CRV,
  CAR.HONDA_CRV_EU,
  CAR.HONDA_CRV_SA,
  CAR.HONDA_FIT,
  CAR.HONDA_FREED,
  CAR.HONDA_HRV,
  CAR.HONDA_CLARITY,
  CAR.HONDA_ODYSSEY,
  CAR.HONDA_ODYSSEY_TWN,
  CAR.ACURA_RDX,
  CAR.HONDA_PILOT,
  CAR.HONDA_RIDGELINE,
  CAR.HONDA_CIVIC,
  CAR.HONDA_ACCORD_9G,
  CAR.ACURA_MDX_3G,
  CAR.ACURA_MDX_3G_MMR,
  CAR.ACURA_TLX_1G,
))
BOSCH_WORDS = frozenset((0, 1, 8, 9, 10, 11))
NIDEC_WORDS = frozenset((0, 4, 260))


def qualified(cp, *, marked_only=False):
  if (cp.brand != 'honda' or cp.passive or cp.notCar or cp.dashcamOnly or len(cp.safetyConfigs) != 1 or
      cp.fingerprintSource == structs.CarParams.FingerprintSource.fixed or
      cp.transmissionType not in (structs.CarParams.TransmissionType.automatic, structs.CarParams.TransmissionType.cvt) or
      cp.alternativeExperience not in ((32,) if marked_only else (0, 32))):
    return False
  safety = cp.safetyConfigs[0]
  identity = next((candidate for candidate in CLASSIC_BOSCH | NIDEC | RADARLESS if candidate == cp.carFingerprint), None)
  if identity is None:
    return False
  detected = int(HondaFlags.BOSCH_EXT_HUD | HondaFlags.BOSCH_ALT_BRAKE | HondaFlags.HAS_BSM | HondaFlags.EPS_MODIFIED | HondaFlags.HYBRID)
  if int(cp.flags) & ~(int(identity.config.flags) | detected):
    return False
  flags = HondaFlags(cp.flags)
  if flags & (HondaFlags.BOSCH_CANFD | HondaFlags.BOSCH_ALT_RADAR):
    return False
  if cp.carFingerprint in NIDEC and flags & HondaFlags.NIDEC and not flags & HondaFlags.BOSCH:
    expected = 4 if flags & HondaFlags.NIDEC_ALT_SCM_MESSAGES else 0
    if cp.carFingerprint == CAR.HONDA_ODYSSEY_TWN and cp.alternativeExperience == 32:
      expected |= 256
    return (cp.pcmCruise and cp.openpilotLongitudinalControl and
            safety.safetyModel == structs.CarParams.SafetyModel.hondaNidec and safety.safetyParam == expected)
  if cp.carFingerprint in CLASSIC_BOSCH and flags & HondaFlags.BOSCH and not flags & HondaFlags.BOSCH_RADARLESS:
    expected = int(bool(flags & HondaFlags.BOSCH_ALT_BRAKE))
    return (cp.pcmCruise and not cp.openpilotLongitudinalControl and
            safety.safetyModel == structs.CarParams.SafetyModel.hondaBosch and safety.safetyParam == expected)
  if cp.carFingerprint in RADARLESS and flags & HondaFlags.BOSCH_RADARLESS:
    expected = 8 | int(bool(flags & HondaFlags.BOSCH_ALT_BRAKE)) | (2 if cp.openpilotLongitudinalControl else 0)
    return (bool(cp.pcmCruise) == (not cp.openpilotLongitudinalControl) and
            safety.safetyModel == structs.CarParams.SafetyModel.hondaBosch and safety.safetyParam == expected)
  return False


def temporary_restriction(cp, state):
  gears = structs.CarState.GearShifter
  return bool(state is not None and qualified(cp, marked_only=True) and state.canValid and not state.canTimeout
              and not state.steerFaultPermanent and
              (state.gearShifter not in (gears.drive, gears.sport, gears.low, gears.brake) or state.steerFaultTemporary))


def native_observation(native, *, latched, panda_ready, restricted, now_ns, pending_since_ns):
  lost = not panda_ready or native is None
  if not latched or lost or restricted:
    return 0, lost, False
  if native.requestedLateral and native.lateralAllowed:
    return 0, False, False
  pending_since_ns = pending_since_ns or now_ns
  return pending_since_ns, False, now_ns - pending_since_ns >= 200_000_000
