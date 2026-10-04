import math

from opendbc.car import structs
from opendbc.car.hyundai.values import CAR, HyundaiFlags, CANFD_ANGLE_MODEL_BITS

AOL_EXPERIENCE = 32
MODELS = frozenset(CANFD_ANGLE_MODEL_BITS)
ANGLE_AOL_WORDS = frozenset(
  (
    0x4008,
    0x4010,
    0x4028,
    0x4090,
    0x4208,
    0x4228,
    0x4408,
    0x440A,
    0x4410,
    0x4412,
    0x4428,
    0x442A,
    0x4490,
    0x4492,
    0x4608,
    0x460A,
    0x4628,
    0x462A,
    0x4809,
    0x4811,
    0x4829,
    0x4891,
    0x4A09,
    0x4A29,
    0x4C08,
    0x4C28,
    0x4E08,
    0x4E28,
    0x5008,
    0x5010,
    0x5028,
    0x5090,
    0x5208,
    0x5228,
    0x5491,
    0x5809,
    0x5811,
    0x5829,
    0x5891,
    0x5A09,
    0x5A29,
    0x5C91,
    0x6008,
    0x600A,
    0x6010,
    0x6012,
    0x6028,
    0x602A,
    0x6090,
    0x6092,
    0x6208,
    0x620A,
    0x6228,
    0x622A,
    0x6808,
    0x680A,
    0x6810,
    0x6812,
    0x6828,
    0x682A,
    0x6890,
    0x6892,
    0x6A08,
    0x6A0A,
    0x6A28,
    0x6A2A,
    0x7008,
    0x700A,
    0x7010,
    0x7012,
    0x7028,
    0x702A,
    0x7090,
    0x7092,
    0x7208,
    0x720A,
    0x7228,
    0x722A,
    0x7809,
    0x7829,
  )
)


def stock_word(cp):
  flags = int(cp.flags)
  word = 0x4000 | CANFD_ANGLE_MODEL_BITS[str(cp.carFingerprint)]
  if flags & HyundaiFlags.EV:
    word |= 1
  if flags & HyundaiFlags.HYBRID:
    word |= 2
  if flags & HyundaiFlags.CANFD_LKA_STEER_MSG:
    word |= 16
    if flags & HyundaiFlags.CANFD_LKA_STEER_MSG_ALT:
      word |= 128
  else:
    word |= 8
    if flags & HyundaiFlags.CANFD_ALT_BUTTONS:
      word |= 32
  if flags & HyundaiFlags.SEND_LFA:
    word |= 512
  return word


def qualified(cp, *, marked_only=False):
  identity = str(cp.carFingerprint)
  if identity not in MODELS or cp.brand != 'hyundai':
    return False
  declared = int(CAR(identity).config.flags)
  dynamic = int(
    HyundaiFlags.HYBRID
    | HyundaiFlags.CANFD_LKA_STEER_MSG
    | HyundaiFlags.CANFD_LKA_STEER_MSG_ALT
    | HyundaiFlags.CANFD_ALT_BUTTONS
    | HyundaiFlags.CANFD_CAMERA_SCC
    | HyundaiFlags.CANFD_ALT_GEARS
    | HyundaiFlags.CANFD_ALT_GEARS_2
    | HyundaiFlags.SEND_LFA
  )
  flags = int(cp.flags)
  if (
    flags & ~dynamic != declared & ~dynamic
    or flags & ~(declared | dynamic)
    or cp.passive
    or cp.notCar
    or cp.dashcamOnly
    or cp.openpilotLongitudinalControl
    or not cp.pcmCruise
    or cp.steerControlType != structs.CarParams.SteerControlType.angle
    or cp.alternativeExperience not in ((AOL_EXPERIENCE,) if marked_only else (0, AOL_EXPERIENCE))
    or len(cp.safetyConfigs) != 1
    or cp.safetyConfigs[0].safetyModel != structs.CarParams.SafetyModel.hyundaiCanfd
  ):
    return False
  if not flags & HyundaiFlags.EV and (not flags & HyundaiFlags.CANFD_ALT_GEARS_2 or flags & HyundaiFlags.CANFD_ALT_GEARS):
    return False
  if flags & HyundaiFlags.EV and flags & HyundaiFlags.HYBRID:
    return False
  lka = bool(flags & HyundaiFlags.CANFD_LKA_STEER_MSG)
  if (
    bool(flags & HyundaiFlags.CANFD_CAMERA_SCC) == lka
    or (flags & HyundaiFlags.CANFD_LKA_STEER_MSG_ALT and not lka)
    or (lka and flags & HyundaiFlags.CANFD_ALT_BUTTONS)
  ):
    return False
  if identity == 'KIA_SPORTAGE_2026' and (lka or flags & HyundaiFlags.HYBRID):
    return False
  if identity in ('HYUNDAI_IONIQ_5_PE', 'KIA_EV9'):
    expected = 0x5491 if identity == 'HYUNDAI_IONIQ_5_PE' else 0x5C91
    return stock_word(cp) == expected and cp.safetyConfigs[0].safetyParam == expected
  if identity == 'KIA_EV6_2025' and stock_word(cp) not in (0x7809, 0x7829):
    return False
  if flags & HyundaiFlags.HYBRID and identity not in (
    'HYUNDAI_AZERA_HEV_7TH_GEN',
    'KIA_SORENTO_HEV_4TH_GEN_LFA2',
    'KIA_SPORTAGE_HEV_2026',
    'HYUNDAI_SANTA_FE_HEV_5TH_GEN',
  ):
    return False
  return stock_word(cp) in ANGLE_AOL_WORDS and cp.safetyConfigs[0].safetyParam == stock_word(cp)


def command_allowed(cp, state):
  return (
    qualified(cp, marked_only=True)
    and state.canValid
    and not state.canTimeout
    and state.gearShifter == structs.CarState.GearShifter.drive
    and not state.standstill
    and math.isfinite(state.vEgoRaw)
    and state.vEgoRaw > 0.3
    and not (state.brakePressed or state.gasPressed or state.steerFaultTemporary or state.steerFaultPermanent)
  )


def temporary_restriction(cp, state):
  gears = structs.CarState.GearShifter
  return bool(
    state is not None
    and qualified(cp, marked_only=True)
    and state.canValid
    and not state.canTimeout
    and not state.steerFaultPermanent
    and state.gearShifter in (gears.drive, gears.reverse, gears.park, gears.neutral)
    and math.isfinite(state.vEgoRaw)
    and (state.gearShifter != gears.drive or state.standstill or state.vEgoRaw <= 0.3 or state.steerFaultTemporary or state.brakePressed or state.gasPressed)
  )


ANGLE_ACK_TIMEOUT_NS = 200_000_000


def native_observation(native, *, latched, panda_ready, restricted, now_ns, pending_since_ns):
  lost = not panda_ready or native is None
  if not latched or lost or restricted:
    return 0, lost, False
  if native.requestedLateral and native.lateralAllowed:
    return 0, False, False
  pending_since_ns = pending_since_ns or now_ns
  reset = now_ns - pending_since_ns >= ANGLE_ACK_TIMEOUT_NS
  return pending_since_ns, False, reset
