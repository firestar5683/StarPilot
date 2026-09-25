"""Exact GV70 owner for the optional camera lead decoder."""
from opendbc.car.hyundai.canfd_camera_lead import CANFDCameraLead
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.values import CAR, HyundaiFlags


def eligible(cp):
  return (cp.carFingerprint == CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN and
          cp.flags & HyundaiFlags.CANFD and cp.openpilotLongitudinalControl and
          not cp.passive and not cp.dashcamOnly and not cp.notCar)


class GV70CameraLead(CANFDCameraLead):
  def __init__(self, cp):
    if not eligible(cp):
      raise ValueError('Camera lead owner requires the exact active GV70 profile')
    buses = CanBus(cp)
    super().__init__(cp, buses.ECAN if cp.flags & HyundaiFlags.CANFD_LKA_STEER_MSG else buses.CAM)
