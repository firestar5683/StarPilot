"""Ordinary camera acceleration owner in normalized GM wire units."""
from opendbc.car.gm.values import CAR, is_ordinary_camera_profile, camera_acc_pedal_profile
from opendbc.car.gm.longitudinal import GMOrdinaryLongitudinalPolicy, GMVoltLongitudinalPolicy, _GMDefaultStopPolicy, AscmStopEvidence
import numpy as np

from opendbc.car.gm.truck_longitudinal import GMTruckLongitudinalPolicy


class CameraLongitudinalPolicy(GMOrdinaryLongitudinalPolicy):
  def stop_policy(self):
    return _GMDefaultStopPolicy(.25, AscmStopEvidence)


class TruckCameraLongitudinalPolicy(GMTruckLongitudinalPolicy):
  def stop_policy(self):
    return _GMDefaultStopPolicy(.25, AscmStopEvidence)


class CameraPedalLongitudinalPolicy(CameraLongitudinalPolicy):
  stopping_decel_rate = float(np.float32(.8))
  kp = ((0., 5., 15., 35.), tuple(float(np.float32(value)) for value in (.09, .08, .06, .045)))

  def feedforward(self, target, speed, last_output):
    return target * float(np.float32(.25))


def policy_for(cp):
  profile = camera_acc_pedal_profile(cp)
  if profile is not None and profile.longitudinal:
    return GMVoltLongitudinalPolicy(gateway=True) if profile.topology == "gateway" else CameraPedalLongitudinalPolicy()

  if not is_ordinary_camera_profile(cp, longitudinal=True):
    return None
  return TruckCameraLongitudinalPolicy() if cp.carFingerprint == CAR.CHEVROLET_SILVERADO else CameraLongitudinalPolicy()
