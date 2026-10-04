from opendbc.car import get_safety_config, structs
from opendbc.car.tesla.values import CAR
from opendbc.car.tesla.preap.aol import qualified
from openpilot.starpilot.saved_source import read_saved

KEYS = ("NAPPedalEnabled", "NAPRadarEnabled", "NAPRadarBehindNosecone")


def stock_configuration(params):
  try:
    return all(read_saved(params, key, 8) in ((None, True), (b"0", True)) for key in KEYS)
  except (OSError, TypeError, ValueError):
    return False


def prepare_stock(cp, admitted):
  if cp.brand == "tesla" and cp.carFingerprint == CAR.TESLA_MODEL_S_PREAP and (not admitted or not qualified(cp)):
    cp.dashcamOnly = True
    cp.alternativeExperience = 0
    cp.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.noOutput)]
  return cp
