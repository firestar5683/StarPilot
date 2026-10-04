from opendbc.car import structs
from opendbc.car.hyundai.values import CAR, HyundaiFlags, HyundaiSafetyFlags, is_blended
from opendbc.car.hyundai.classic_scc_aol import CLASSIC_SCC_IDS, stock_word

AOL_MARKER = 0x0400
AOL_EXPERIENCE = 32
_EXCLUDED = int(HyundaiFlags.LEGACY | HyundaiFlags.UNSUPPORTED_LONGITUDINAL | HyundaiFlags.ALT_LIMITS_2 | HyundaiFlags.CAMERA_SCC)
CLASSIC_LONG_IDS = frozenset(identity for identity in CLASSIC_SCC_IDS if not int(identity.config.flags) & _EXCLUDED)
LONG_AOL_WORDS = frozenset(AOL_MARKER | 4 | gas | limits | lda for gas in (0, 1, 2) for limits in (0, 64) for lda in (0, 2048))


def ordinary_word(cp):
  return stock_word(cp) | int(HyundaiSafetyFlags.LONG)


def aol_word(cp):
  return ordinary_word(cp) | AOL_MARKER | (int(HyundaiSafetyFlags.HAS_LDA_BUTTON) if int(cp.flags) & int(HyundaiFlags.HAS_LDA_BUTTON) else 0)


def qualified(cp, *, marked_only=False):
  if cp.brand != 'hyundai' or cp.carFingerprint not in CLASSIC_LONG_IDS:
    return False
  declared = int(CAR[cp.carFingerprint].config.flags)
  allowed = declared | int(HyundaiFlags.HAS_LDA_BUTTON | HyundaiFlags.USE_FCA | HyundaiFlags.SEND_LFA)
  identity_mask = int(
    HyundaiFlags.CANFD
    | HyundaiFlags.NON_SCC
    | HyundaiFlags.FCEV
    | HyundaiFlags.LEGACY
    | HyundaiFlags.EV
    | HyundaiFlags.HYBRID
    | HyundaiFlags.ALT_LIMITS
    | HyundaiFlags.ALT_LIMITS_2
    | HyundaiFlags.CAMERA_SCC
  )
  if (
    int(cp.flags) & identity_mask != declared & identity_mask
    or int(cp.flags) & ~allowed
    or is_blended(cp)
    or cp.passive
    or cp.notCar
    or cp.dashcamOnly
    or not cp.openpilotLongitudinalControl
    or cp.pcmCruise
    or cp.steerControlType != structs.CarParams.SteerControlType.torque
    or not cp.alphaLongitudinalAvailable
    or cp.alternativeExperience not in (0, AOL_EXPERIENCE)
    or len(cp.safetyConfigs) != 1
  ):
    return False
  safety = cp.safetyConfigs[0]
  accepted = (aol_word(cp),) if marked_only else (ordinary_word(cp), aol_word(cp))
  return safety.safetyModel == structs.CarParams.SafetyModel.hyundai and int(safety.safetyParam) in accepted


def native_accepts(cp, model, param):
  return (
    qualified(cp, marked_only=True)
    and cp.alternativeExperience == AOL_EXPERIENCE
    and model == int(structs.CarParams.SafetyModel.hyundai)
    and param == aol_word(cp)
  )
