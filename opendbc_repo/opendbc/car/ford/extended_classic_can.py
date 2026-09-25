"""Source-derived classic Ford extended lateral constructor.

Adapted from BluePilot fordcan_ext.py; see CREDITS.md and
THIRD_PARTY_NOTICES.md. This codec does not grant native authority.
"""

from opendbc.car.ford.fordcan import CanBus


def create_extended_classic_lat_ctl_msg(packer, CAN: CanBus, active: bool, ramp_type: int, precision_type: int,
                       curvature: float, curvature_rate: float):
  # 13-bit DBC endpoint: positive .001024 would wrap to negative .001024.
  curvature_rate = max(-0.001024, min(curvature_rate, 0.00102375))
  values = {
    "LatCtlRng_L_Max": 0,
    "HandsOffCnfm_B_Rq": 0,
    "LatCtl_D_Rq": 1 if active else 0,
    "LatCtlRampType_D_Rq": ramp_type,
    "LatCtlPrecision_D_Rq": precision_type,
    "LatCtlPathOffst_L_Actl": 0.0,
    "LatCtlPath_An_Actl": 0.0,
    "LatCtlCurv_NoRate_Actl": curvature_rate,
    "LatCtlCurv_No_Actl": curvature,
  }
  return packer.make_can_msg("LateralMotionControl", CAN.main, values)
