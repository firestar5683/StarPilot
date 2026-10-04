from opendbc.car.pedal import supported_pedal_detected
from opendbc.car.gm.values import CAR, CanBus


def pedal_candidate(candidate, fingerprint):
  stock_acc = candidate in (CAR.CHEVROLET_BOLT_EUV, CAR.CHEVROLET_BOLT_ACC_2022_2023)
  if supported_pedal_detected(fingerprint, CanBus.POWERTRAIN, supported=stock_acc):
    return CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL
  return candidate
