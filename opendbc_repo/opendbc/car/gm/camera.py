"""Ordinary camera acceleration owner in normalized GM wire units."""
from opendbc.car.gm.values import CAR, is_ordinary_camera_profile
from opendbc.car.gm.longitudinal import GMOrdinaryLongitudinalPolicy, _GMDefaultStopPolicy, AscmStopEvidence
from opendbc.car.gm.truck_longitudinal import GMTruckLongitudinalPolicy


class CameraLongitudinalPolicy(GMOrdinaryLongitudinalPolicy):
  def stop_policy(self):
    return _GMDefaultStopPolicy(.25, AscmStopEvidence)


class TruckCameraLongitudinalPolicy(GMTruckLongitudinalPolicy):
  def stop_policy(self):
    return _GMDefaultStopPolicy(.25, AscmStopEvidence)


def policy_for(cp):
  if not is_ordinary_camera_profile(cp, longitudinal=True):
    return None
  return TruckCameraLongitudinalPolicy() if cp.carFingerprint == CAR.CHEVROLET_SILVERADO else CameraLongitudinalPolicy()
