"""Exact legacy radar takeover and typed-axis configuration."""
from opendbc.car import structs
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from opendbc.car.hyundai.classic_scc_aol import qualified as stock_qualified

CARS = frozenset((CAR.GENESIS_G80, CAR.KIA_XCEED_PHEV))
LEGACY_LONG_AOL_WORDS = frozenset((0xE902, 0xE903, 0xE912, 0xE913))


def ordinary_word(cp):
  return (0xE900 if cp.carFingerprint == CAR.GENESIS_G80 else 0xE901) + (0x10 if cp.flags & HyundaiFlags.HAS_LDA_BUTTON else 0)


def aol_word(cp):
  return ordinary_word(cp) + 2


def topology_owned(cp):
  if cp.carFingerprint not in CARS or cp.brand != 'hyundai':
    return False
  declared = int(CAR[cp.carFingerprint].config.flags)
  dynamic = int(HyundaiFlags.HAS_LDA_BUTTON | HyundaiFlags.USE_FCA | HyundaiFlags.SEND_LFA)
  return (int(cp.flags) & ~dynamic == declared and not cp.passive and not cp.notCar and not cp.dashcamOnly
          and cp.steerControlType == structs.CarParams.SteerControlType.torque and len(cp.safetyConfigs) == 1
          and cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.hyundaiLegacy)


def qualified(cp, *, marked_only=False):
  if not topology_owned(cp) or not cp.alphaLongitudinalAvailable or not cp.openpilotLongitudinalControl or cp.pcmCruise:
    return False
  word = int(cp.safetyConfigs[0].safetyParam)
  return ((cp.alternativeExperience == 32 and word == aol_word(cp)) or
          (not marked_only and cp.alternativeExperience == 0 and word == ordinary_word(cp)))


def candidate(stock, *, requested):
  if not requested or not stock.alphaLongitudinalAvailable or not topology_owned(stock) or not stock_qualified(stock):
    return None
  cp = stock.as_reader().as_builder()
  cp.openpilotLongitudinalControl = True
  cp.pcmCruise = False
  if cp.carFingerprint == CAR.GENESIS_G80:
    cp.radarUnavailable = True
  cp.safetyConfigs[0].safetyParam = ordinary_word(cp)
  cp.alternativeExperience = 0
  return cp


def stopping_decel_rate(cp):
  return 0.8 if qualified(cp) else None
