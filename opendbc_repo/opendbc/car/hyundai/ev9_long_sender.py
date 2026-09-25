"""EV9 CCNC LONG wire recipes from Dom2efe, with explicit current DBC aliases."""
import numpy as np
from opendbc.car import CanData
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.hyundai.values import CAR
from opendbc.car.hyundai.hyundaicanfd import hkg_can_fd_checksum

def _set_value(msg: bytearray, sig, ival: int) -> None:
  i = sig.lsb // 8
  bits = sig.size
  if sig.size < 64:
    ival &= (1 << sig.size) - 1
  while 0 <= i < len(msg) and bits > 0:
    shift = sig.lsb % 8 if (sig.lsb // 8) == i else 0
    size = min(bits, 8 - shift)
    mask = ((1 << size) - 1) << shift
    msg[i] &= ~mask
    msg[i] |= (ival & ((1 << size) - 1)) << shift
    bits -= size
    ival >>= size
    i = i + 1 if sig.is_little_endian else i - 1

def _create_angle_adas_cmd_msg(packer, CAN, apply_angle: float, lat_active: bool, torque_reduction_gain: float):
  values = {
    "ADAS_ActvACISta": 0,
    "ADAS_ActvACILvl2Sta": 2 if lat_active else 1,
    "ADAS_StrAnglReqVal": apply_angle,
    "ADAS_ACIAnglTqRedcGainVal": torque_reduction_gain if lat_active else 0.0,
    "FCA_ESA_ActvSta": 0,
    "FCA_ESA_TqBstGainVal": 0.0,
  }
  return packer.make_can_msg("LFA_ALT", CAN.ECAN, values)

def create_angle_adas_cmd(packer, CAN, apply_angle: float, lat_active: bool, torque_reduction_gain: float):
  return _create_angle_adas_cmd_msg(packer, CAN, apply_angle, lat_active, torque_reduction_gain)

def create_inactive_angle_steering_messages(packer, CAN, steering_angle: float):
  # Explicit nonzero original aliases: LKA_MODE/ICON/TORQUE_REQUEST/DAMP_FACTOR.
  neutral = packer.make_can_msg("LFA", CAN.ECAN, {"LKA_OptUsmSta": 2, "LKA_SysIndReq": 1,
                                               "StrTqReqVal": 0, "Damping_Gain": 100})
  return [neutral, create_angle_adas_cmd(packer, CAN, steering_angle, False, 0.0)]


def create_ccnc_blindspot_status_messages(packer, CP, CAN, counter, left_blindspot=False, right_blindspot=False,
                                           left_escalated=False, right_escalated=False, drive_gear=False,
                                           left_warning_lamp=False, right_warning_lamp=False,
                                           left_sound_active=False, right_sound_active=False):
  left_state = 2 if left_blindspot and left_escalated else (1 if left_blindspot else 0)
  right_state = 2 if right_blindspot and right_escalated else (1 if right_blindspot else 0)
  left_osm_state = 2 if left_warning_lamp else 1 if left_state == 1 else 0
  right_osm_state = 2 if right_warning_lamp else 1 if right_state == 1 else 0
  desired_fields = {
    "BCW_IndSta": 1,
    "BCA_OnOffEquip2Sta": 2,
    "BCA_Sta": int(drive_gear),
    "BCW_LtIndSta": left_state,
    "BCW_RtIndSta": right_state,
    "BCW_LtSndWrngSta": int(left_sound_active),
    "BCW_RtSndWrngSta": int(right_sound_active),
    "OSMrrLamp_LtIndSta": left_osm_state,
    "OSMrrLamp_RtIndSta": right_osm_state,
  }

  return [
    _create_ccnc_adrv_message_with_signals(
      packer, CP, CAN, 0x1BA, counter, "ADAS_CMD_50_50ms", desired_fields,
    ),
    # No retained radar input reproduces the stock RCTA target decision across routes.
    _create_ccnc_adrv_message(CP.carFingerprint, 0x1E5, CAN.ECAN, counter),
  ]

def create_ccnc_adrv_messages(packer, CP, CAN, frame, enabled, main_cruise_enabled, hud, out, is_metric,
                              steering_available, steering_active, left_blindspot, right_blindspot,
                              drive_gear=False,
                              hba_icon=0,
                              left_escalated=False, right_escalated=False,
                              left_warning_lamp=False, right_warning_lamp=False,
                              left_sound_active=False, right_sound_active=False):
  ret = [
    _create_ccnc_adrv_message(CP.carFingerprint, address, CAN.ECAN, frame // period)
    for address, period in _CCNC_ADRV_PERIODS[CP.carFingerprint].items() if frame % period == 0
  ]
  if frame % 5 == 0:
    ret.extend(create_ccnc_angle_long_status_messages(
      packer, CP, CAN, frame // 5, enabled, main_cruise_enabled, hud, out, is_metric,
      steering_available, steering_active, hba_icon,
    ))
    ret.extend(create_ccnc_blindspot_status_messages(
      packer, CP, CAN, frame // 5, left_blindspot, right_blindspot, left_escalated, right_escalated,
      drive_gear,
      left_warning_lamp, right_warning_lamp, left_sound_active, right_sound_active,
    ))
  return ret

_CCNC_ADRV_TEMPLATES = {CAR.KIA_EV9: {
    0x160: bytes.fromhex("0000000100000000fffc0100a8001000"),
    0x1DA: bytes.fromhex("0000002200110000000000000000000000000000000000000000000000000000"),
    0x1EA: bytes.fromhex("000000080000000000000000000000ff000000000000000000000000000f0f00"),
    0x200: bytes.fromhex("00000014801a0000"),
    0x345: bytes.fromhex("0000001500560000"),
    0x161: bytes.fromhex("0000000000000000c0fff0c003000040000000000000000000ff000000000000"),
    0x162: bytes.fromhex("0000002700000000000000000000000000000000000000000000000000000000"),
    0x1BA: bytes.fromhex("00000000000000880200000000000000000100000000000f"),
    0x1E5: bytes.fromhex("00000000000000000000220300000080"),
    0x1E0: bytes.fromhex("00000002000000000000000000000000"),
    0x38C: bytes.fromhex("000000f71f000000000000000000000000000000000000000000000000000000"),
  }}

_CCNC_ADRV_PERIODS = {CAR.KIA_EV9: {
    0x160: 2,
    0x1DA: 100,
    0x1EA: 5,
    0x200: 5,
    0x345: 20,
    0x1E0: 5,
    0x38C: 20,
  }}

def _create_ccnc_adrv_message(car_fingerprint, address: int, bus: int, counter: int) -> CanData:
  d = bytearray(_CCNC_ADRV_TEMPLATES[car_fingerprint][address])
  d[2] = counter & 0xFF
  crc = hkg_can_fd_checksum(address, None, d)
  d[0] = crc & 0xFF
  d[1] = (crc >> 8) & 0xFF
  return CanData(address, bytes(d), bus)

def _set_ccnc_message_signals(packer, message_name: str, dat: bytearray, values: dict) -> None:
  dbc_msg = packer.dbc.name_to_msg[message_name]
  for name, value in values.items():
    sig = dbc_msg.sigs[name]
    ival = int(np.floor((value - sig.offset) / sig.factor + 0.5))
    if ival < 0:
      ival = (1 << sig.size) + ival
    _set_value(dat, sig, ival)

def _create_ccnc_adrv_message_with_signals(packer, CP, CAN, address: int, counter: int,
                                            message_name: str, values: dict) -> CanData:
  msg = _create_ccnc_adrv_message(CP.carFingerprint, address, CAN.ECAN, counter)
  dat = bytearray(msg.dat)
  # Update decoded fields in the verified neutral payload.
  _set_ccnc_message_signals(packer, message_name, dat, values)
  crc = hkg_can_fd_checksum(address, None, dat)
  dat[0] = crc & 0xFF
  dat[1] = (crc >> 8) & 0xFF
  return CanData(address, bytes(dat), CAN.ECAN)

def create_ccnc_acc_control(packer, CAN, enabled: bool, accel: float,
                            stop_request: bool, cruise_standstill: bool, gas_override: bool, set_speed: float,
                            main_mode_acc: int, lead_distance: float, lead_rel_speed: float, lead_visible: bool,
                            v_ego: float, jerk_lower: float = 0.7, jerk_upper: float = 0.7):
  if not enabled or gas_override or stop_request:
    accel = 0.0

  lead_visible = bool(enabled and lead_visible)
  desired_headway = min(max(round(1.625 * max(v_ego, 0.0), 1), 3.5), 204.6) if enabled else 204.6
  values = {
    "ACCMode": 0 if not enabled else (2 if gas_override else 1),
    "MainMode_ACC": int(bool(main_mode_acc)),
    "StopReq": 1 if stop_request and enabled else 0,
    "CRUISE_STANDSTILL": 1 if cruise_standstill and stop_request and enabled else 0,
    "aReqValue": accel,
    "aReqRaw": accel,
    "VSetDis": set_speed,
    "JerkLowerLimit": jerk_lower if enabled else 1.0,
    "JerkUpperLimit": jerk_upper if enabled else 3.0,
    "ACC_ObjDist": float(np.clip(lead_distance, 0.0, 204.7)) if lead_visible else 204.6,
    "ACC_ObjRelSpd": float(np.clip(lead_rel_speed, -16.4, 34.7)) if lead_visible else 34.6,
    "ObjValid": 0 if lead_visible else 1,
    "OBJ_STATUS": 2 if enabled and lead_visible else 0,
    "NEW_SIGNAL_15": desired_headway,
    "SET_ME_2": 4,
    "SET_ME_3": 3,
    "SET_ME_TMP_64": 0x64,
    # Stock CCNC LKA-long routes use raw 7. The DBC's physical range is stale.
    "DISTANCE_SETTING": 7 if enabled else 0,
  }

  address, payload, bus = packer.make_can_msg("SCC_CONTROL", CAN.ECAN, values)
  dat = bytearray(payload)
  # Original NEW_SIGNAL_3 is bits108..109 (Motorola109|2); current SCC_ObjSta
  # additionally names bit110. Preserve the literal two-bit value, leaving110 zero.
  dat[13] = (dat[13] & ~0x30) | ((2 if lead_visible else 0) << 4)
  dat[0:2] = hkg_can_fd_checksum(address, None, dat).to_bytes(2, "little")
  return CanData(address, bytes(dat), bus)

def create_ccnc_angle_long_status_messages(packer, CP, CAN, counter: int, enabled: bool = False,
                                         main_cruise_enabled: bool = False, hud=None, out=None,
                                         is_metric: bool = True, steering_available: bool = False,
                                         steering_active: bool = False, hba_icon: int = 0) -> list[CanData]:
  cruise_speed = round(out.vCruiseCluster * (1 if is_metric else CV.KPH_TO_MPH)) if out is not None else 0
  display_speed = (40 if is_metric else 25) if cruise_speed > (145 if is_metric else 90) else max(cruise_speed, 0)
  main_standby = bool(main_cruise_enabled and not enabled)
  values_161 = {
    "FCA_ICON": 1,       # orange: FCA unavailable
    "FCA_ALT_ICON": 0,
    "FCA_IMAGE": 0,
    "ALERTS_1": 0,
    "ALERTS_2": 0,
    "ALERTS_3": 0,
    "ALERTS_4": 0,
    "ALERTS_5": 0,
    "SOUNDS_1": 0,
    "SOUNDS_2": 0,
    "SOUNDS_3": 0,
    "SOUNDS_4": 0,
    "LFA_ICON": (2 if steering_active else 1) if steering_available else 0,
    "HBA_ICON": hba_icon if hba_icon in (1, 2) else 0,
    "HDA_ICON": 2 if enabled else 1 if main_standby else 0,
    "TARGET": 3 if enabled else 0,
    "SETSPEED": 3 if enabled else 1 if main_standby else 0,
    "SETSPEED_HUD": 2 if enabled else 1 if main_standby else 0,
    "SETSPEED_SPEED": display_speed if enabled or main_standby else 255,
    "DISTANCE": hud.leadDistanceBars if enabled and hud is not None else 0,
    "DISTANCE_SPACING": 3 if enabled or main_standby else 0,
    "DISTANCE_CAR": 2 if enabled else 1 if main_standby else 0,
  }
  values_162 = {fault: 0 for fault in (
    "FAULT_FSS", "FAULT_FCA", "FAULT_LSS", "FAULT_SLA", "FAULT_HDA", "FAULT_DAS", "FAULT_LFA", "FAULT_DAW",
    "FAULT_HBA", "FAULT_ESS",
  )}
  values_162["VIBRATE"] = 0
  return [
    _create_ccnc_adrv_message_with_signals(packer, CP, CAN, 0x161, counter, "CCNC_0x161", values_161),
    _create_ccnc_adrv_message_with_signals(packer, CP, CAN, 0x162, counter, "CCNC_0x162", values_162),
  ]

def create_radar_heartbeat(counter, brake_pressed, accelerator_pressed):
  d = bytearray.fromhex("00000000ff006f00e80400001201030055ffff0000000000")
  d[2] = counter & 0xff
  d[4] = (d[4] & ~1) | int(brake_pressed)
  d[22] = (d[22] & ~1) | int(accelerator_pressed)
  crc = hkg_can_fd_checksum(0x100, None, d)
  d[0], d[1] = crc & 0xff, crc >> 8
  return CanData(0x100, bytes(d), 0)
