"""Ford extended-lateral CAN constructors.

Adapted from BluePilot's ``fordcan_ext.py`` and extended-lateral protocol at bp-7.0 commit
e1d051d7ba270261b4455068bd68f1a58db15a4a, including panda integration developed principally by
Alan Polk. See CREDITS.md and THIRD_PARTY_NOTICES.md for detailed provenance and terms.
"""

from opendbc.car.ford.fordcan import CanBus, calculate_lat_ctl2_checksum


def create_lka_msg(packer, CAN: CanBus):
  addr, dat, bus = packer.make_can_msg("Lane_Assist_Data1", CAN.main, {})
  dat = bytearray(dat)
  dat[4] |= 0x2
  return addr, bytes(dat), bus


def create_lat_ctl_msg(packer, CAN: CanBus, active: bool, ramp_type: int, precision_type: int,
                       curvature: float, curvature_rate: float):
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


def create_lat_ctl2_msg(packer, CAN: CanBus, mode: int, ramp_type: int, precision_type: int,
                        curvature: float, curvature_rate: float, counter: int):
  values = {
    "LatCtl_D2_Rq": mode,
    "LatCtlRampType_D_Rq": ramp_type,
    "LatCtlPrecision_D_Rq": precision_type,
    "LatCtlPathOffst_L_Actl": 0.0,
    "LatCtlPath_An_Actl": 0.0,
    "LatCtlCurv_No_Actl": curvature,
    "LatCtlCrv_NoRate2_Actl": curvature_rate,
    "HandsOffCnfm_B_Rq": 0,
    "LatCtlPath_No_Cnt": counter,
    "LatCtlPath_No_Cs": 0,
  }
  dat = packer.make_can_msg("LateralMotionControl2", 0, values)[1]
  values["LatCtlPath_No_Cs"] = calculate_lat_ctl2_checksum(mode, counter, dat)
  return packer.make_can_msg("LateralMotionControl2", CAN.main, values)
