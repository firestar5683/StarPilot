"""Control owners for the ordinary Suburban gateway profile."""

from dataclasses import dataclass
import numpy as np

from opendbc.car import structs
from opendbc.car.gm.values import control_flags, CAR
from opendbc.car.gm.longitudinal import GMOrdinaryLongitudinalPolicy, _GMDefaultStopPolicy


def supported_cp(cp):
  try:
    safety = cp.safetyConfigs
    return (cp.carFingerprint == CAR.CHEVROLET_SUBURBAN and cp.brand == "gm" and
            cp.networkLocation == structs.CarParams.NetworkLocation.gateway and
            cp.openpilotLongitudinalControl and not cp.pcmCruise and len(safety) == 1 and
            safety[0].safetyModel == structs.CarParams.SafetyModel.gm and safety[0].safetyParam == 0 and
            not cp.notCar and not cp.passive and not cp.dashcamOnly and control_flags(cp) == 0 and
            not cp.deprecated.enableGasInterceptor and not getattr(cp, "enableGasInterceptorDEPRECATED", False))
  except (AttributeError, TypeError, ValueError, OverflowError):
    return False


def stopping_decel_rate(cp):
  return float(np.float32(0.8)) if supported_cp(cp) else None


@dataclass(frozen=True)
class SuburbanStopEvidence:
  drive_id: int
  observed_ns: int
  has_lead: bool


class SuburbanLongitudinalPolicy(GMOrdinaryLongitudinalPolicy):
  stopping_decel_rate = float(np.float32(0.8))

  def stop_policy(self):
    return _GMDefaultStopPolicy(0.5, SuburbanStopEvidence)


def policy_for(cp):
  return SuburbanLongitudinalPolicy() if supported_cp(cp) else None
