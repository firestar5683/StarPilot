"""Ford angle codecs, adapted from BluePilot fordcan_ext.py at e1d051d7.

Core commands use planner signs; path and shadow are negated on the wire.
The v1 side channel retains byte4 bit1 for StarPilot's curvature announcement.
"""
from opendbc.bluepilot_lateral.params import protocol as p


def checksum4(dat):
  return (15 - (sum(dat[:7]) & 15)) & 15


def lka(packer, bus, shadow, counter):
  addr, original, _ = packer.make_can_msg("Lane_Assist_Data1", bus, {"LaRefAng_No_Req": 0., "LaCurvature_No_Calc": 0.})
  dat = bytearray(original)
  raw = max(-20000, min(20000, round(-shadow / p.SHADOW_SCALE))) & 0xFFFF
  dat[4] |= p.ANGLE_MASK | ((counter % p.COUNTER_MODULUS) << p.COUNTER_SHIFT)
  dat[5], dat[6] = raw >> 8, raw & 255
  dat[7] = p.VERSION | (checksum4(dat) << p.CHECKSUM_SHIFT)
  return addr, bytes(dat), bus


def lateral(packer, bus, command, *, canfd, counter):
  values = {"HandsOffCnfm_B_Rq": 0, "LatCtlRampType_D_Rq": 2 if command.active else 0,
            "LatCtlPrecision_D_Rq": command.precision, "LatCtlPathOffst_L_Actl": 0.0,
            "LatCtlPath_An_Actl": -command.path_angle, "LatCtlCurv_No_Actl": 0.0}
  if canfd:
    values.update({"LatCtl_D2_Rq": int(command.active), "LatCtlCrv_NoRate2_Actl": 0.0,
                   "LatCtlPath_No_Cnt": counter % 16, "LatCtlPath_No_Cs": 0})
    dat = packer.make_can_msg("LateralMotionControl2", bus, values)[1]
    fields = ((dat[2] << 3) | (dat[3] >> 5), (dat[6] << 3) | (dat[7] >> 5),
              ((dat[3] & 31) << 6) | (dat[4] >> 2), ((dat[4] & 3) << 8) | dat[5])
    total = int(command.active) + counter % 16 + sum(v + (v >> 8) for v in fields)
    values["LatCtlPath_No_Cs"] = 255 - (total & 255)
    return packer.make_can_msg("LateralMotionControl2", bus, values)
  values.update({"LatCtl_D_Rq": int(command.active), "LatCtlRng_L_Max": 0, "LatCtlCurv_NoRate_Actl": 0.0})
  return packer.make_can_msg("LateralMotionControl", bus, values)
