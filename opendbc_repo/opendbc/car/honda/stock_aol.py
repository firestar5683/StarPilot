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

# qualified() runs several times per 100 Hz frame in card and selfdrived, so
# everything that depends only on this module is computed once, and its flag
# tests use plain ints: IntFlag operators cost microseconds each in Python.
_DETECTED = int(HondaFlags.BOSCH_EXT_HUD | HondaFlags.BOSCH_ALT_BRAKE | HondaFlags.HAS_BSM | HondaFlags.EPS_MODIFIED | HondaFlags.HYBRID)
_ALLOWED_FLAGS = {str(car): int(car.config.flags) | _DETECTED for car in CLASSIC_BOSCH | NIDEC | RADARLESS}
_BOSCH, _BOSCH_RADARLESS, _BOSCH_ALT_BRAKE = int(HondaFlags.BOSCH), int(HondaFlags.BOSCH_RADARLESS), int(HondaFlags.BOSCH_ALT_BRAKE)
_NIDEC, _NIDEC_ALT_SCM_MESSAGES = int(HondaFlags.NIDEC), int(HondaFlags.NIDEC_ALT_SCM_MESSAGES)
_UNSUPPORTED = int(HondaFlags.BOSCH_CANFD | HondaFlags.BOSCH_ALT_RADAR)
_FIXED = structs.CarParams.FingerprintSource.fixed
_TRANSMISSIONS = (structs.CarParams.TransmissionType.automatic, structs.CarParams.TransmissionType.cvt)
_HONDA_NIDEC, _HONDA_BOSCH = structs.CarParams.SafetyModel.hondaNidec, structs.CarParams.SafetyModel.hondaBosch


def qualified(cp, *, marked_only=False):
  if (cp.brand != 'honda' or cp.passive or cp.notCar or cp.dashcamOnly or len(cp.safetyConfigs) != 1 or
      cp.fingerprintSource == _FIXED or cp.transmissionType not in _TRANSMISSIONS or
      cp.alternativeExperience not in ((32,) if marked_only else (0, 32))):
    return False
  safety = cp.safetyConfigs[0]
  fingerprint = str(cp.carFingerprint)
  allowed = _ALLOWED_FLAGS.get(fingerprint)
  if allowed is None:
    return False
  flags = int(cp.flags)
  if flags & ~allowed:
    return False
  if flags & _UNSUPPORTED:
    return False
  if fingerprint in NIDEC and flags & _NIDEC and not flags & _BOSCH:
    expected = 4 if flags & _NIDEC_ALT_SCM_MESSAGES else 0
    if fingerprint == CAR.HONDA_ODYSSEY_TWN and cp.alternativeExperience == 32:
      expected |= 256
    return (cp.pcmCruise and cp.openpilotLongitudinalControl and
            safety.safetyModel == _HONDA_NIDEC and safety.safetyParam == expected)
  if fingerprint in CLASSIC_BOSCH and flags & _BOSCH and not flags & _BOSCH_RADARLESS:
    expected = int(bool(flags & _BOSCH_ALT_BRAKE))
    return (cp.pcmCruise and not cp.openpilotLongitudinalControl and
            safety.safetyModel == _HONDA_BOSCH and safety.safetyParam == expected)
  if fingerprint in RADARLESS and flags & _BOSCH_RADARLESS:
    expected = 8 | int(bool(flags & _BOSCH_ALT_BRAKE)) | (2 if cp.openpilotLongitudinalControl else 0)
    return (bool(cp.pcmCruise) == (not cp.openpilotLongitudinalControl) and
            safety.safetyModel == _HONDA_BOSCH and safety.safetyParam == expected)
  return False


def temporary_restriction(cp, state):
  gears = structs.CarState.GearShifter
  return bool(state is not None and qualified(cp, marked_only=True) and state.canValid and not state.canTimeout
              and not state.steerFaultPermanent and
              (state.gearShifter not in (gears.drive, gears.sport, gears.low, gears.brake) or state.steerFaultTemporary))


def native_observation(native, *, latched, panda_ready, restricted, now_ns, pending_since_ns,
                       previously_acknowledged=False, host_requested_lateral=False):
  lost = not panda_ready or native is None
  if not latched or lost or restricted:
    return 0, lost, False
  if native.requestedLateral and native.lateralAllowed:
    return 0, False, False
  if (previously_acknowledged and host_requested_lateral and
      not native.requestedLateral and not native.lateralAllowed):
    # A current host request lost an established grant, not a cold handshake.
    return 0, False, True
  pending_since_ns = pending_since_ns or now_ns
  return pending_since_ns, False, now_ns - pending_since_ns >= 200_000_000
