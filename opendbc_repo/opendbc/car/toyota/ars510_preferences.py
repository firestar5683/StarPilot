"""Explicit startup radar selection; never changes ECU or native safety permissions."""

from opendbc.car import structs
from opendbc.car.toyota.values import ARS510_RADAR_CAR, ToyotaFlags


def supported(cp):
  return bool(
    cp.brand == "toyota"
    and cp.carFingerprint in ARS510_RADAR_CAR
    and not cp.passive
    and not cp.dashcamOnly
    and not cp.notCar
    and len(cp.safetyConfigs) == 1
    and cp.safetyConfigs[0].safetyModel == structs.CarParams.SafetyModel.toyota
  )


def apply_radar_mode(cp, mode):
  if not supported(cp) or type(mode) is not int or mode not in (1, 2):
    return False
  cp.flags |= int(ToyotaFlags.ARS510_RADAR)
  if mode == 2:
    cp.flags |= int(ToyotaFlags.ARS510_FUSED)
  else:
    cp.flags &= ~int(ToyotaFlags.ARS510_FUSED)
  cp.radarUnavailable = False
  return True
