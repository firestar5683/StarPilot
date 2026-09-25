"""Exact EV9 longitudinal owner for optional camera lead data."""
from opendbc.car.hyundai.canfd_camera_lead import CANFDCameraLead
from opendbc.car.hyundai.ev9_longitudinal import qualified
from opendbc.car.hyundai.hyundaicanfd import CanBus


class EV9CameraLead(CANFDCameraLead):
  def __init__(self, cp):
    if not qualified(cp):
      raise ValueError('Camera lead owner requires the exact active EV9 longitudinal profile')
    super().__init__(cp, CanBus(cp).ECAN)
