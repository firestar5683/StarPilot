import numpy as np

from opendbc.car.common.conversions import Conversions as CV


STEERING_MAPS = {
  "HONDA_ACCORD_11G": ([0, 12789], [0, 12789]),
  "ACURA_RDX_3G": ([0, 4095], [0, 4095]),
  "ACURA_RDX_3G_MMR": ([0, 3840], [0, 3840]),
  "HONDA_PILOT_4G": ([0, 4096], [0, 4096]),
  "ACURA_MDX_4G": ([0, 2560, 4209], [0, 2560, 9150]),
  "ACURA_MDX_4G_MMR": ([0, 2560, 4920], [0, 2560, 12000]),
  "ACURA_TLX_2G_MMR": ([0, 4096], [0, 4096]),
  "HONDA_PASSPORT_4G": ([0, 2560, 5120], [0, 2560, 12789]),
}


def apply_steering_profile(params, cp):
  mapping = STEERING_MAPS.get(cp.carFingerprint)
  if mapping is None:
    return
  bp, values = mapping
  params.STEER_MAX = bp[-1]
  params.STEER_LOOKUP = [-x for x in reversed(bp[1:])] + list(bp)
  params.STEER_LOOKUP_V = [-x for x in reversed(values[1:])] + list(values)


def apply_factory_profile(cp, candidate):
  if candidate == "HONDA_HRV_3G":
    cp.longitudinalActuatorDelay = 0.4
  if candidate in ("HONDA_PILOT", "HONDA_PILOT_4G", "ACURA_TLX_2G_MMR"):
    cp.lateralTuning.init("pid")
    cp.lateralTuning.pid.kf = 0.00006
    cp.lateralTuning.pid.kpBP = [0, 10]
    cp.lateralTuning.pid.kpV = [0.05, 0.5]
    cp.lateralTuning.pid.kiBP = [0, 10]
    cp.lateralTuning.pid.kiV = [0.0125, 0.125]
  if candidate in ("ACURA_RDX_3G_MMR", "HONDA_PILOT_4G", "ACURA_MDX_4G_MMR"):
    cp.steerActuatorDelay = 0.1
  if candidate == "ACURA_RDX_3G_MMR" and not cp.openpilotLongitudinalControl:
    cp.minSteerSpeed = 70.0 * CV.KPH_TO_MS


def longitudinal_eligible(cp):
  return (cp.brand == "honda" and cp.openpilotLongitudinalControl and
          not cp.passive and not cp.dashcamOnly and not cp.notCar)


def stopping_decel_rate(cp):
  return 0.3 if longitudinal_eligible(cp) else None


def forecast_should_stop(cp, speeds, time_indices, action_t):
  if cp.carFingerprint != "HONDA_CITY_7G" or not longitudinal_eligible(cp):
    return None
  if len(speeds) != len(time_indices) or not len(speeds):
    return None
  target = np.interp(action_t, time_indices, speeds)
  future = np.interp(action_t + 1.0, time_indices, speeds)
  return bool(target < 2.0 and future < 2.0)
