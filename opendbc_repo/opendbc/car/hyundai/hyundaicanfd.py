import copy
import numpy as np
from opendbc.car import CanBusBase, CanData
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.crc import CRC16_XMODEM
from opendbc.car.hyundai.values import HyundaiFlags


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


class CanBus(CanBusBase):
  def __init__(self, CP, fingerprint=None, lka_steering=None) -> None:
    super().__init__(CP, fingerprint)

    if lka_steering is None:
      lka_steering = CP.flags & HyundaiFlags.CANFD_LKA_STEERING.value if CP is not None else False

    # On the CAN-FD platforms, the LKAS camera is on both A-CAN and E-CAN. LKA steering cars
    # have a different harness than the LFA steering variants in order to split
    # a different bus, since the steering is done by different ECUs.
    self._a, self._e = 1, 0
    if lka_steering:
      self._a, self._e = 0, 1

    self._a += self.offset
    self._e += self.offset
    self._cam = 2 + self.offset

  @property
  def ECAN(self):
    return self._e

  @property
  def ACAN(self):
    return self._a

  @property
  def CAM(self):
    return self._cam


def _update_checksum(packer, address: int, dat: bytearray) -> None:
  msg = packer.dbc.addr_to_msg[address]
  sig_checksum = next((s for s in msg.sigs.values() if s.calc_checksum is not None), None)
  if sig_checksum is None:
    return

  checksum = sig_checksum.calc_checksum(address, sig_checksum, dat)
  _set_value(dat, sig_checksum, checksum)


def _create_angle_lfa_msg(packer, CAN, values, apply_angle: float, lat_active: bool, torque_reduction_gain: float):
  address = packer.dbc.name_to_msg["LFA"].address
  dat = packer.pack(address, values)

  desired_angle = int(round(np.clip(apply_angle, -819.1, 819.1) * 10.0))
  if desired_angle < 0:
    desired_angle += 1 << 14

  dat[9] = (dat[9] & ~0x30) | (((2 if lat_active else 1) & 0x3) << 4)
  dat[10] = (dat[10] & 0x03) | ((desired_angle & 0x3F) << 2)
  dat[11] = (desired_angle >> 6) & 0xFF
  dat[12] = int(np.clip(round(torque_reduction_gain / 0.004), 0, 250))
  _update_checksum(packer, address, dat)

  return address, bytes(dat), CAN.ECAN


def _create_angle_adas_cmd_msg(packer, CAN, apply_angle: float, lat_active: bool, torque_reduction_gain: float):
  values = {
    "ADAS_ActvACISta": 0,
    "ADAS_ActvACILvl2Sta": 2 if lat_active else 1,
    "ADAS_StrAnglReqVal": apply_angle,
    "ADAS_ACIAnglTqRedcGainVal": torque_reduction_gain if lat_active else 0.0,
    "FCA_ESA_ActvSta": 0,
    "FCA_ESA_TqBstGainVal": 0.0,
  }
  return packer.make_can_msg("ADAS_CMD_35_10ms", CAN.ECAN, values)


def create_ev9_direct_angle_command(packer, CAN, apply_angle: float, lat_active: bool, torque_reduction_gain: float):
  """Send the safety-limited angle directly to EPS when EV9 ADAS TX is disabled."""
  return _create_angle_adas_cmd_msg(packer, CAN, apply_angle, lat_active, torque_reduction_gain)


def create_steering_messages(packer, CP, CAN, enabled, lat_active, apply_torque, apply_angle,
                             lfa_base_values=None, lkas_base_values=None, lka_icon=None):
  if lka_icon is None:
    lka_icon = 2 if enabled else 1
  angle_lkas_alt = CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING and CP.flags & HyundaiFlags.CANFD_LKA_STEERING_ALT
  if angle_lkas_alt and not lat_active:
    lka_icon = 1

  control_values = {
    "LKA_MODE": 2,
    "LKA_ICON": lka_icon,
    "TORQUE_REQUEST": 0 if CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING else apply_torque,
    "LKA_ASSIST": 0,
    "STEER_REQ": 0 if CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING else (1 if lat_active else 0),
    "STEER_MODE": 0,
  }

  if lkas_base_values:
    lkas_values = {k: v for k, v in lkas_base_values.items() if k not in ("CHECKSUM", "COUNTER")}
    lkas_values.update(control_values)
  else:
    lkas_values = copy.copy(control_values)
    lkas_values["LKA_AVAILABLE"] = 0

  if lfa_base_values:
    # Preserve stock UI/status fields and only override the actuation-relevant signals.
    lfa_values = {k: v for k, v in lfa_base_values.items() if k not in ("CHECKSUM", "COUNTER")}
    lfa_values.update(control_values)
  else:
    lfa_values = copy.copy(control_values)
    lfa_values["HAS_LANE_SAFETY"] = 0  # hide LKAS settings
    lfa_values["NEW_SIGNAL_1"] = 0
    lfa_values["NEW_SIGNAL_2"] = 0
    lfa_values["DAMP_FACTOR"] = 100  # can potentially tuned for better perf [3, 200]

  if angle_lkas_alt:
    lkas_values["ADAS_StrAnglReqVal"] = apply_angle
    lkas_values["LKAS_ANGLE_ACTIVE"] = 2 if lat_active else 1
    lkas_values["ADAS_ACIAnglTqRedcGainVal"] = apply_torque if lat_active else 0.0
    if lat_active:
      lkas_values = {
        "LKA_OptUsmSta": 0,
        "LKA_RcgSta": 3,
        "LKA_LHLnWrnSta": 0,
        "LKA_RHLnWrnSta": 0,
        "LKA_HndsoffSnd": 0,
        "LKA_StrSnd": 0,
        "LKA_SysIndReq": 2,
        "StrTqReqVal": 0,
        "ActToiSta": 0,
        "ToiFltSta": 0,
        "LFA_BUTTON": 0,
        "LKA_SysWrn": 0,
        "Damping_Gain": 100,
        "LKAS_ANGLE_ACTIVE": 2,
        "LKA_UsmMod": 0,
        "ADAS_StrAnglReqVal": apply_angle,
        "ADAS_ACIAnglTqRedcGainVal": apply_torque,
      }
    elif lkas_base_values:
      # Match the common HKG path: preserve the camera's UI/status template and
      # override only the steering command fields while openpilot owns the bus.
      lkas_values["ADAS_StrAnglReqVal"] = lkas_base_values.get("ADAS_StrAnglReqVal", apply_angle)

  ret = []
  if CP.flags & HyundaiFlags.CANFD_LKA_STEERING:
    lkas_msg = "LKAS_ALT" if CP.flags & HyundaiFlags.CANFD_LKA_STEERING_ALT else "LKAS"
    if CP.openpilotLongitudinalControl:
      ret.append(packer.make_can_msg("LFA", CAN.ECAN, lfa_values))
    ret.append(packer.make_can_msg(lkas_msg, CAN.ACAN, lkas_values))
  else:
    if CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING:
      if CP.flags & HyundaiFlags.SEND_LFA:
        # Some CAN-FD angle-steering trims still expect the stock-style LFA status/UI
        # message to remain present even though angle actuation comes through ADAS_CMD.
        ret.append(packer.make_can_msg("LFA", CAN.ECAN, lfa_values))
        ret.append(_create_angle_adas_cmd_msg(packer, CAN, apply_angle, lat_active, apply_torque))
      else:
        ret.append(_create_angle_lfa_msg(packer, CAN, lfa_values, apply_angle, lat_active, apply_torque))
    else:
      ret.append(packer.make_can_msg("LFA", CAN.ECAN, lfa_values))

  return ret


def create_ev9_inactive_steering_messages(packer, CAN, steering_angle: float):
  """Recreate the EV9's parked ECAN steering status without actuation.

  The stock ADAS ECU broadcasts both frames at 100 Hz. Keep every actuation
  bit inactive, use the live measured angle for the redundant angle field,
  and request zero torque-reduction gain.
  """
  lfa_values = {
    "LKA_MODE": 2,
    "LKA_ICON": 1,
    "TORQUE_REQUEST": 0,
    "LKA_ASSIST": 0,
    "STEER_REQ": 0,
    "STEER_MODE": 0,
    "HAS_LANE_SAFETY": 0,
    "NEW_SIGNAL_1": 0,
    "NEW_SIGNAL_2": 0,
    "DAMP_FACTOR": 100,
  }
  return [
    packer.make_can_msg("LFA", CAN.ECAN, lfa_values),
    _create_angle_adas_cmd_msg(packer, CAN, steering_angle, False, 0.0),
  ]


def create_suppress_lfa(packer, CAN, lfa_block_msg, lka_steering_alt):
  suppress_msg = "CAM_0x362" if lka_steering_alt else "CAM_0x2a4"
  msg_bytes = 32 if lka_steering_alt else 24

  values = {f"BYTE{i}": lfa_block_msg[f"BYTE{i}"] for i in range(3, msg_bytes) if i != 7}
  values["COUNTER"] = lfa_block_msg["COUNTER"]
  values["SET_ME_0"] = 0
  values["SET_ME_0_2"] = 0
  values["LEFT_LANE_LINE"] = 0
  values["RIGHT_LANE_LINE"] = 0
  return packer.make_can_msg(suppress_msg, CAN.ACAN, values)


def create_buttons(packer, CP, CAN, cnt, btn=0, base_values=None, left_paddle=False, right_paddle=False):
  values = {k: v for k, v in base_values.items() if k not in ("_CHECKSUM", "COUNTER")} if base_values else {}
  values.update({
    "COUNTER": cnt,
    "SET_ME_1": 1,
    "CRUISE_BUTTONS": btn,
    "LEFT_PADDLE": int(left_paddle),
    "RIGHT_PADDLE": int(right_paddle),
  })

  bus = CAN.ECAN if CP.flags & HyundaiFlags.CANFD_LKA_STEERING else CAN.CAM
  return packer.make_can_msg("CRUISE_BUTTONS", bus, values)


def create_acc_cancel(packer, CP, CAN, cruise_info_copy):
  # TODO: why do we copy different values here?
  if CP.flags & HyundaiFlags.CANFD_CAMERA_SCC.value:
    values = {s: cruise_info_copy[s] for s in [
      "COUNTER",
      "CHECKSUM",
      "NEW_SIGNAL_1",
      "MainMode_ACC",
      "ACCMode",
      "ZEROS_9",
      "CRUISE_STANDSTILL",
      "ZEROS_5",
      "DISTANCE_SETTING",
      "VSetDis",
    ]}
  else:
    values = {s: cruise_info_copy[s] for s in [
      "COUNTER",
      "CHECKSUM",
      "ACCMode",
      "VSetDis",
      "CRUISE_STANDSTILL",
    ]}
  values.update({
    "ACCMode": 4,
    "aReqRaw": 0.0,
    "aReqValue": 0.0,
  })
  return packer.make_can_msg("SCC_CONTROL", CAN.ECAN, values)


def create_lfahda_cluster(packer, CAN, enabled, base_values=None, lfa_icon=None):
  if lfa_icon is None:
    lfa_icon = 2 if enabled else 0

  values = {k: v for k, v in base_values.items() if k not in ("CHECKSUM", "COUNTER")} if base_values else {}
  values.update({
    "HDA_ICON": 1 if enabled else 0,
    "LFA_ICON": lfa_icon,
  })
  return packer.make_can_msg("LFAHDA_CLUSTER", CAN.ECAN, values)


def create_ccnc(packer, CAN, openpilot_longitudinal, enabled, hud, left_blinker, right_blinker, msg_161, msg_162, msg_1b5,
                is_metric, out, main_cruise_enabled, lfa_icon):
  for fault in ("FAULT_LSS", "FAULT_HDA", "FAULT_DAS", "FAULT_LFA", "FAULT_DAW", "FAULT_ESS"):
    msg_162[fault] = 0

  if msg_161["ALERTS_2"] == 5:
    msg_161.update({"ALERTS_2": 0, "SOUNDS_2": 0})
  if msg_161["ALERTS_3"] == 17:
    msg_161["ALERTS_3"] = 0
  if msg_161["ALERTS_5"] in (2, 5):
    msg_161["ALERTS_5"] = 0
  if msg_161["SOUNDS_4"] == 2 and msg_161["LFA_ICON"] in (3, 0):
    msg_161["SOUNDS_4"] = 0

  lane_change_speed_min = 8.9408
  any_blinker = left_blinker or right_blinker
  curvature = {i: (31 if i == -1 else 13 - abs(i + 15)) if i < 0 else 15 + i for i in range(-15, 16)}

  msg_161.update({
    "DAW_ICON": 0,
    "LKA_ICON": 0,
    "LFA_ICON": 2 if lfa_icon else 0,
    "CENTERLINE": 1 if lfa_icon else 0,
    "LANELINE_CURVATURE": curvature.get(max(-15, min(int(out.steeringAngleDeg / 4.5), 15)), 14) if lfa_icon and not any_blinker else 15,
    "LANELINE_LEFT": 0 if not lfa_icon else 1 if not hud.leftLaneVisible else 4 if hud.leftLaneDepart else 6 if any_blinker else 2,
    "LANELINE_RIGHT": 0 if not lfa_icon else 1 if not hud.rightLaneVisible else 4 if hud.rightLaneDepart else 6 if any_blinker else 2,
    "LCA_LEFT_ICON": 0 if not lfa_icon or out.vEgo < lane_change_speed_min else 1 if out.leftBlindspot else 2 if any_blinker else 4,
    "LCA_RIGHT_ICON": 0 if not lfa_icon or out.vEgo < lane_change_speed_min else 1 if out.rightBlindspot else 2 if any_blinker else 4,
    "LCA_LEFT_ARROW": 2 if left_blinker else 0,
    "LCA_RIGHT_ARROW": 2 if right_blinker else 0,
  })

  if lfa_icon and any_blinker:
    left_lane_raw = msg_1b5["Info_LftLnPosVal"]
    right_lane_raw = msg_1b5["Info_RtLnPosVal"]
    scale_per_m = 15 / 1.7
    left_lane = abs(int(round(15 + (left_lane_raw - 1.7) * scale_per_m)))
    right_lane = abs(int(round(15 + (right_lane_raw - 1.7) * scale_per_m)))

    if msg_1b5["Info_LftLnQualSta"] not in (2, 3):
      left_lane = 0
    if msg_1b5["Info_RtLnQualSta"] not in (2, 3):
      right_lane = 0

    if left_lane_raw == -2.0248375:
      left_lane = 30 - right_lane
    if right_lane_raw == 2.0248375:
      right_lane = 30 - left_lane

    if left_lane_raw == right_lane_raw == 0:
      left_lane = right_lane = 15
    elif left_lane_raw == 0:
      left_lane = 30 - right_lane
    elif right_lane_raw == 0:
      right_lane = 30 - left_lane

    total = left_lane + right_lane
    if total == 0:
      left_lane = right_lane = 15
    else:
      left_lane = round((left_lane / total) * 30)
      right_lane = 30 - left_lane

    msg_161["LANELINE_LEFT_POSITION"] = left_lane
    msg_161["LANELINE_RIGHT_POSITION"] = right_lane

  if hud.leftLaneDepart or hud.rightLaneDepart:
    msg_162["VIBRATE"] = 1

  if openpilot_longitudinal:
    if msg_161["ALERTS_3"] in (1, 2, 3, 4, 7, 8, 9, 10):
      msg_161["ALERTS_3"] = 0
    if msg_161["ALERTS_5"] == 4:
      msg_161["ALERTS_5"] = 0
    if msg_161["SOUNDS_3"] == 5:
      msg_161["SOUNDS_3"] = 0

    cruise_speed = round(out.vCruiseCluster * (1 if is_metric else CV.KPH_TO_MPH))
    msg_161.update({
      "SETSPEED": 3 if enabled else 1,
      "SETSPEED_HUD": 0 if not main_cruise_enabled else 2 if enabled else 1,
      "SETSPEED_SPEED": 255 if not main_cruise_enabled else (40 if is_metric else 25) if cruise_speed > (145 if is_metric else 90) else cruise_speed,
      "DISTANCE": hud.leadDistanceBars,
      "DISTANCE_SPACING": 0 if not main_cruise_enabled else 1 if enabled else 3,
      "DISTANCE_LEAD": 0 if not main_cruise_enabled else 2 if enabled and hud.leadVisible else 1 if hud.leadVisible else 0,
      "DISTANCE_CAR": 0 if not main_cruise_enabled else 2 if enabled else 1,
      "SLA_ICON": 0,
      "NAV_ICON": 0,
      "TARGET": 0,
    })
    msg_162["LEAD"] = 0 if not main_cruise_enabled else 2 if enabled else 1
    msg_162["LEAD_DISTANCE"] = msg_1b5["Longitudinal_Distance"]

  return [packer.make_can_msg(msg, CAN.ECAN, values) for msg, values in (("CCNC_0x161", msg_161), ("CCNC_0x162", msg_162))]


def create_blindspot_status_messages(packer, CAN, rear_values, front_corner_values,
                                     left_blindspot=False, right_blindspot=False,
                                     left_blinker=False, right_blinker=False):
  # Reuse the last known-good payload but regenerate the rolling counter/checksum.
  rear = {k: v for k, v in rear_values.items() if k not in ("CHECKSUM", "COUNTER")}
  front = {k: v for k, v in front_corner_values.items() if k not in ("CHECKSUM", "COUNTER")}
  left_state = 2 if left_blindspot and left_blinker else (1 if left_blindspot else 0)
  right_state = 2 if right_blindspot and right_blinker else (1 if right_blindspot else 0)

  rear["BCW_Sta"] = int(left_blindspot or right_blindspot)
  rear["BCW_LtIndSta"] = left_state
  rear["BCW_RtIndSta"] = right_state
  rear["BCW_IndSta"] = max(int(rear.get("BCW_IndSta", 0)), left_state, right_state)
  rear["OSMrrLamp_LtIndSta"] = left_state
  rear["OSMrrLamp_RtIndSta"] = right_state
  # Keep the older fields aligned where they still correlate on some platforms.
  rear["FL_INDICATOR"] = left_state
  rear["FR_INDICATOR"] = right_state
  if "NEW_SIGNAL_3" not in front:
    front["NEW_SIGNAL_3"] = 1

  return [
    packer.make_can_msg("BLINDSPOTS_REAR_CORNERS", CAN.ECAN, rear),
    packer.make_can_msg("BLINDSPOTS_FRONT_CORNER_1", CAN.ECAN, front),
  ]


def create_ev9_blindspot_status_messages(packer, CAN, counter, left_blindspot=False, right_blindspot=False,
                                          left_escalated=False, right_escalated=False,
                                          left_warning_active=False, right_warning_active=False,
                                          left_flash_phase=0, right_flash_phase=0,
                                          left_sound_active=False, right_sound_active=False):
  """Recreate the stock-correlated subset of EV9 BSM output fields."""
  # Overwrite the verified fields in the complete captured payload. A delta
  # cannot be XORed onto the body: the live pre-suppression payload can already
  # contain nonzero OSM lamp state, which made a requested neutral value decode
  # as 3 and held both mirror lamps on throughout route 00000108. Unlike the
  # generic Ioniq 6 helper, EV9 stock routes kept BCW_Sta and FL/FR_INDICATOR at
  # zero through genuine lamp events, so they must not be synthesized here.
  left_state = 2 if left_blindspot and left_escalated else (1 if left_blindspot else 0)
  right_state = 2 if right_blindspot and right_escalated else (1 if right_blindspot else 0)
  # The validated EV9 warning scene holds BCW at state 2 while the matching
  # blinker is active, but flashes only the outside-mirror lamp: 0.8 s on,
  # 0.2 s off at this helper's 20 Hz call rate. Hazard suppression is decided
  # upstream; this helper accepts explicit escalation state and never infers it
  # from turn lamps.
  # Each side owns a warning-relative 20-sample phase. Stock keeps the first
  # 16 samples on and the next 4 off; using the global 8-bit rolling counter
  # breaks this cadence whenever that counter wraps.
  left_flash_on = int(left_flash_phase) % 20 < 16
  right_flash_on = int(right_flash_phase) % 20 < 16
  left_osm_state = 2 if left_warning_active and left_flash_on else 1 if left_state == 1 else 0
  right_osm_state = 2 if right_warning_active and right_flash_on else 1 if right_state == 1 else 0
  desired_fields = {
    "BCW_LtIndSta": left_state,
    "BCW_RtIndSta": right_state,
    "BCW_LtSndWrngSta": int(left_sound_active),
    "BCW_RtSndWrngSta": int(right_sound_active),
    "OSMrrLamp_LtIndSta": left_osm_state,
    "OSMrrLamp_RtIndSta": right_osm_state,
  }

  return [
    _create_ev9_adrv_message_with_signals(
      packer, CAN, 0x1BA, counter, "BLINDSPOTS_REAR_CORNERS", desired_fields,
    ),
    create_ev9_adrv_message(0x1E5, CAN.ECAN, counter),
  ]


IONIQ_6_CLUSTER_BLINDSPOT_31A = {
  "right": (
    bytes.fromhex("fa7c10f0f0ffff03898aff0b0a8678ff000000007e0055550000000000000000"),
    bytes.fromhex("ac0e11f0f0ffff03898aff0c0a8678ff000000007e0055550000000000000000"),
    bytes.fromhex("76ce12f0f0ffff03898aff0b0a8678ff000000007e0055550000000000000000"),
    bytes.fromhex("309713f0f0ffff03898aff0b0a8678ff000000007e0055550000000000000000"),
    bytes.fromhex("d32214f0f0ffff03898aff0c0a8678ff000000007e0055550000000000000000"),
    bytes.fromhex("957b15f0f0ffff03898aff0c0a8678ff000000007e0055550000000000000000"),
  ),
  "left": (
    bytes.fromhex("851828f0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
    bytes.fromhex("c34129f0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
    bytes.fromhex("09aa2af0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
    bytes.fromhex("4ff32bf0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
    bytes.fromhex("bc6d2cf0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
    bytes.fromhex("fa342df0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
  ),
}

IONIQ_6_CLUSTER_BLINDSPOT_3B5 = {
  "right": (
    bytes.fromhex("caa95c00000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("8cf05d00000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("461b5e00000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("00425f00000000464600000000000000d7020000000069070000000000000000"),
  ),
  "left": (
    bytes.fromhex("2c69c500000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("e682c600000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("21afc800000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("67f6c900000000464600000000000000da020000000069070000000000000000"),
  ),
}


IONIQ_6_CLUSTER_LANE_CHANGE_3C1 = {
  "right": {
    "trigger": bytes.fromhex("e910300041000000"),
    "steady": bytes.fromhex("ab20300001000000"),
  },
  "left": {
    "trigger": bytes.fromhex("3d40304010000000"),
    "steady": bytes.fromhex("3e50300000000000"),
  },
}

# Captured from a stock Ioniq 6 route that shows the cluster lane-change animation
# on ECAN after the trigger/hold 0x3C1 states above.
IONIQ_6_CLUSTER_LANE_CHANGE_3B5 = {
  "right": (
    bytes.fromhex("9f687600000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("d9317700000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("58457800000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("1e1c7900000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("d4f77a00000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("92ae7b00000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("61307c00000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("27697d00000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("ed827e00000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("abdb7f00000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("dd978000000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("9bce8100000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("51258200000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("177c8300000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("e4e28400000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("18ba8500000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("68508600000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("94088700000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("157c8800000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("53258900000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("99ce8a00000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("df978b00000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("2c098c00000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("6a508d00000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("a0bb8e00000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("e6e28f00000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("a2529000000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("e40b9100000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("2ee09200000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("d2b89300000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("9b279400000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("677f9500000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("17959600000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("ebcd9700000000464600000000000000d7020000000069070000000000000000"),
    bytes.fromhex("d0b89800000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("96e19900000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("5c0a9a00000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("1a539b00000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("e9cd9c00000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("af949d00000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("657f9e00000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("23269f00000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("cc0fa000000000464600000000000000d8020000000069070000000000000000"),
    bytes.fromhex("bba6a100000000464600000000000000d9020000000069070000000000000000"),
    bytes.fromhex("714da200000000464600000000000000d9020000000069070000000000000000"),
    bytes.fromhex("3714a300000000464600000000000000d9020000000069070000000000000000"),
  ),
  "left": (
    bytes.fromhex("e682c600000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("d2dbc700000000464600000000000000d9020000000069070000000000000000"),
    bytes.fromhex("21afc800000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("67f6c900000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("ad1dca00000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("eb44cb00000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("18dacc00000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("5e83cd00000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("9468ce00000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("d231cf00000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("9681d000000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("d0d8d100000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("1a33d200000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("5c6ad300000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("ddf4d400000000464600000000000000d9020000000069070000000000000000"),
    bytes.fromhex("e9add500000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("2346d600000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("651fd700000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("e46bd800000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("d032d900000000464600000000000000d9020000000069070000000000000000"),
    bytes.fromhex("68d9da00000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("2e80db00000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("dd1edc00000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("9b47dd00000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("51acde00000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("17f5df00000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("f8dce000000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("be85e100000000464600000000000000da020000000069070000000000000000"),
    bytes.fromhex("746ee200000000464600000000000000da020000000069070000000000000000"),
  ),
}

IONIQ_6_CLUSTER_LANE_CHANGE_31A = {
  "right": (
    bytes.fromhex("eb4518f0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
    bytes.fromhex("757119f0f0ffff03898aff0a088678ff000000007e0055550000000000000000"),
    bytes.fromhex("bf9a1af0f0ffff03898aff0a088678ff000000007e0055550000000000000000"),
    bytes.fromhex("f9c31bf0f0ffff03898aff0a088678ff000000007e0055550000000000000000"),
    bytes.fromhex("0a5d1cf0f0ffff03898aff0a088678ff000000007e0055550000000000000000"),
    bytes.fromhex("4c041df0f0ffff03898aff0a088678ff000000007e0055550000000000000000"),
    bytes.fromhex("86ef1ef0f0ffff03898aff0a088678ff000000007e0055550000000000000000"),
    bytes.fromhex("18db1ff0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
    bytes.fromhex("f7f220f0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
  ),
  "left": (
    bytes.fromhex("851828f0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
    bytes.fromhex("c34129f0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
    bytes.fromhex("09aa2af0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
    bytes.fromhex("4ff32bf0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
    bytes.fromhex("bc6d2cf0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
    bytes.fromhex("fa342df0f0ffff03898aff0a098678ff000000007e0055550000000000000000"),
  ),
}

IONIQ_6_CLUSTER_LANE_CHANGE_3C1_BURST = {
  0: "trigger",
  4: "trigger",
  7: "steady",
  10: "steady",
  13: "steady",
  16: "steady",
}

IONIQ_6_CLUSTER_LANE_CHANGE_3C1_STEADY_START = 34
IONIQ_6_CLUSTER_LANE_CHANGE_3B5_START = 4
IONIQ_6_CLUSTER_LANE_CHANGE_31A_START = 30


def create_ioniq_6_cluster_blindspot_messages(CAN, frame, left_blindspot=False, right_blindspot=False,
                                              left_blinker=False, right_blinker=False):
  side = None
  if left_blindspot and not right_blindspot:
    side = "left"
  elif right_blindspot and not left_blindspot:
    side = "right"
  elif left_blindspot and right_blindspot:
    if left_blinker and not right_blinker:
      side = "left"
    elif right_blinker and not left_blinker:
      side = "right"

  if side is None:
    return []

  ret = []
  if frame % 20 == 0:
    seq_3b5 = IONIQ_6_CLUSTER_BLINDSPOT_3B5[side]
    ret.append((0x3B5, seq_3b5[(frame // 20) % len(seq_3b5)], CAN.ECAN))
  if frame % 100 == 0:
    seq_31a = IONIQ_6_CLUSTER_BLINDSPOT_31A[side]
    ret.append((0x31A, seq_31a[(frame // 100) % len(seq_31a)], CAN.ECAN))

  return ret


def create_ioniq_6_cluster_lane_change_messages(CAN, frame, side=None):
  if side not in IONIQ_6_CLUSTER_LANE_CHANGE_3C1:
    return []

  ret = []
  frame_phase = IONIQ_6_CLUSTER_LANE_CHANGE_3C1_BURST.get(frame)
  if frame_phase is None and frame >= IONIQ_6_CLUSTER_LANE_CHANGE_3C1_STEADY_START and \
     (frame - IONIQ_6_CLUSTER_LANE_CHANGE_3C1_STEADY_START) % 20 == 0:
    frame_phase = "steady"
  if frame_phase is not None:
    ret.append((0x3C1, IONIQ_6_CLUSTER_LANE_CHANGE_3C1[side][frame_phase], CAN.ECAN))

  if frame >= IONIQ_6_CLUSTER_LANE_CHANGE_3B5_START and (frame - IONIQ_6_CLUSTER_LANE_CHANGE_3B5_START) % 20 == 0:
    seq_3b5 = IONIQ_6_CLUSTER_LANE_CHANGE_3B5[side]
    ret.append((0x3B5, seq_3b5[((frame - IONIQ_6_CLUSTER_LANE_CHANGE_3B5_START) // 20) % len(seq_3b5)], CAN.ECAN))
  if frame >= IONIQ_6_CLUSTER_LANE_CHANGE_31A_START and (frame - IONIQ_6_CLUSTER_LANE_CHANGE_31A_START) % 100 == 0:
    seq_31a = IONIQ_6_CLUSTER_LANE_CHANGE_31A[side]
    ret.append((0x31A, seq_31a[((frame - IONIQ_6_CLUSTER_LANE_CHANGE_31A_START) // 100) % len(seq_31a)], CAN.ECAN))

  return ret


def create_acc_control(packer, CAN, enabled, accel_last, accel, stopping, gas_override, set_speed, hud_control,
                       main_mode_acc=1, jerk_lower=None, jerk_upper=None, direct_accel=False,
                       lead_distance=None, lead_rel_speed=None, lead_visible=None, cruise_info=None):
  jerk = 5
  jn = jerk / 50
  if not enabled or gas_override:
    a_val, a_raw = 0, 0
  elif direct_accel:
    a_raw = accel
    a_val = accel
  else:
    a_raw = accel
    a_val = np.clip(accel, accel_last - jn, accel_last + jn)

  if lead_distance is None and lead_rel_speed is None and lead_visible is None:
    acc_obj_dist = 1.0
    acc_obj_rel_spd = 0.0
    obj_valid = 0
    obj_status = 2
  else:
    lead_visible = bool(lead_visible)
    acc_obj_dist = float(np.clip(lead_distance if lead_visible else 0.0, 0.0, 204.7))
    acc_obj_rel_spd = float(np.clip(lead_rel_speed if lead_visible else 0.0, -16.4, 34.7))
    obj_valid = int(not lead_visible)
    obj_status = 0 if not (enabled and lead_visible) else (1 if gas_override else 2)

  values = {
    "ACCMode": 0 if not enabled else (2 if gas_override else 1),
    "MainMode_ACC": main_mode_acc,
    "StopReq": 1 if stopping else 0,
    "aReqValue": a_val,
    "aReqRaw": a_raw,
    "VSetDis": set_speed,
    "JerkLowerLimit": jerk_lower if jerk_lower is not None else (jerk if enabled else 1),
    "JerkUpperLimit": jerk_upper if jerk_upper is not None else 3.0,

    "ACC_ObjDist": acc_obj_dist,
    "ACC_ObjRelSpd": acc_obj_rel_spd,
    "ObjValid": obj_valid,
    "OBJ_STATUS": obj_status,
    "SET_ME_2": 0x4,
    "SET_ME_3": 0x3,
    "SET_ME_TMP_64": 0x64,
    "DISTANCE_SETTING": hud_control.leadDistanceBars,
  }
  if cruise_info:
    values.update({s: cruise_info[s] for s in ("ACC_ObjDist", "ACC_ObjRelSpd")})

  return packer.make_can_msg("SCC_CONTROL", CAN.ECAN, values)


def create_spas_messages(packer, CAN, left_blink, right_blink):
  ret = []

  values = {
  }
  ret.append(packer.make_can_msg("SPAS1", CAN.ECAN, values))

  blink = 0
  if left_blink:
    blink = 3
  elif right_blink:
    blink = 4
  values = {
    "BLINKER_CONTROL": blink,
  }
  ret.append(packer.make_can_msg("SPAS2", CAN.ECAN, values))

  return ret


def create_fca_warning_light(packer, CAN, frame):
  ret = []

  if frame % 2 == 0:
    values = {
      'AEB_SETTING': 0x1,  # show AEB disabled icon
      'SET_ME_2': 0x2,
      'SET_ME_FF': 0xff,
      'SET_ME_FC': 0xfc,
      'SET_ME_9': 0x9,
    }
    ret.append(packer.make_can_msg("ADRV_0x160", CAN.ECAN, values))
  return ret


def create_adrv_messages(packer, CAN, frame):
  # messages needed to car happy after disabling
  # the ADAS Driving ECU to do longitudinal control

  ret = []

  values = {
  }
  ret.append(packer.make_can_msg("ADRV_0x51", CAN.ACAN, values))

  ret.extend(create_fca_warning_light(packer, CAN, frame))

  if frame % 5 == 0:
    values = {
      'SET_ME_1C': 0x1c,
      'SET_ME_FF': 0xff,
      'SET_ME_TMP_F': 0xf,
      'SET_ME_TMP_F_2': 0xf,
    }
    ret.append(packer.make_can_msg("ADRV_0x1ea", CAN.ECAN, values))

    values = {
      'SET_ME_E1': 0xe1,
      'SET_ME_3A': 0x3a,
    }
    ret.append(packer.make_can_msg("ADRV_0x200", CAN.ECAN, values))

  if frame % 20 == 0:
    values = {
      'SET_ME_15': 0x15,
    }
    ret.append(packer.make_can_msg("ADRV_0x345", CAN.ECAN, values))

  if frame % 100 == 0:
    values = {
      'SET_ME_22': 0x22,
      'SET_ME_41': 0x41,
    }
    ret.append(packer.make_can_msg("ADRV_0x1da", CAN.ECAN, values))

  return ret


def hkg_can_fd_checksum(address: int, sig, d: bytearray) -> int:
  crc = 0
  for i in range(2, len(d)):
    crc = ((crc << 8) ^ CRC16_XMODEM[(crc >> 8) ^ d[i]]) & 0xFFFF
  crc = ((crc << 8) ^ CRC16_XMODEM[(crc >> 8) ^ ((address >> 0) & 0xFF)]) & 0xFFFF
  crc = ((crc << 8) ^ CRC16_XMODEM[(crc >> 8) ^ ((address >> 8) & 0xFF)]) & 0xFFFF
  if len(d) == 8:
    crc ^= 0x5F29
  elif len(d) == 16:
    crc ^= 0x041D
  elif len(d) == 24:
    crc ^= 0x819D
  elif len(d) == 32:
    crc ^= 0x9F5B
  return crc


# Ioniq 5/6 / HKG LKA-steering: ADAS_DRV broadcasts ACCELERATOR_BRAKE_ALT (0x100) on bus 0.
# The front radar uses this as its "host alive" heartbeat. When we disable ADAS_DRV the
# radar stops publishing real object tracks. Spoof this message ourselves with valid CRC
# and current pedal state so the radar keeps tracking.
# Length is 24 bytes on Ioniq 6 (DBC declares 32 for ICE Hyundais, but EV firmware uses 24).
# Byte templates captured from real ADAS broadcasts; only checksum, counter,
# brake, and accelerator bits are updated for the radar heartbeat.
_ACCEL_BRAKE_ALT_TEMPLATE = bytes.fromhex("000000020000fcff000000000020000055ff000068000000")
_KIA_EV9_ACCEL_BRAKE_ALT_TEMPLATE = bytes.fromhex("00000000ff006f00e80400001201030055ffff0000000000")
_KIA_EV9_ADRV_TEMPLATES = {
  0x160: bytes.fromhex("0000000100000000fffc0100a8001000"),
  0x1DA: bytes.fromhex("0000002200110000000000000000000000000000000000000000000000000000"),
  0x1EA: bytes.fromhex("000000080000000000000000000000ff000000000000000000000000000f0f00"),
  0x200: bytes.fromhex("00000014801a0000"),
  0x345: bytes.fromhex("0000001500560000"),
  # Neutral parked-state bodies captured immediately before suppressing the
  # EV9 ADAS ECU. Bytes 0-2 are regenerated as CRC/counter below.
  0x161: bytes.fromhex("0000000000000000c0fff0c003000000000000000000000000ff000000000000"),
  0x162: bytes.fromhex("0000002700000000c0ff00000000000000000000000000000000000000000000"),
  0x1BA: bytes.fromhex("00000000000000880200000000000000000000000000000f"),
  0x1E5: bytes.fromhex("00000000000000000000220300000080"),
  0x1E0: bytes.fromhex("00000002000000000000000000000000"),
  0x38C: bytes.fromhex("000000f71f000000000000000000000000000000000000000000000000000000"),
}

# 0x57A does not use the standard Hyundai CAN-FD CRC/counter convention. Both
# checksum bytes and byte 2 remained constant in the stock route, so preserve
# the complete ignition-on payload rather than fabricating a rolling counter.
_KIA_EV9_RAW_ADRV_TEMPLATES = {
  0x57A: bytes.fromhex("7a50000800000000000001000000000000000000000000000000000000000000"),
}

# Per-process OFF -> READY continuity captured immediately before suppressing
# ADAS_DRV. These are reset on every pre-fingerprint attempt. Preserve the
# READY-state body and continue its rolling counter instead of jumping back to
# an ignition-on template/counter zero.
_KIA_EV9_ADRV_LIVE_TEMPLATES: dict[int, bytes] = {}
_KIA_EV9_ADRV_COUNTER_BASES: dict[int, int] = {}
_KIA_EV9_RAW_ADRV_LIVE_TEMPLATES: dict[int, bytes] = {}
_KIA_EV9_SCC_CONTROL_LIVE_TEMPLATE: bytes | None = None
_KIA_EV9_SCC_CONTROL_COUNTER_BASE = 0


def ev9_scc_control_baseline_available() -> bool:
  return _KIA_EV9_SCC_CONTROL_LIVE_TEMPLATE is not None


def set_ev9_adrv_baselines(messages: list[CanData]) -> None:
  global _KIA_EV9_SCC_CONTROL_LIVE_TEMPLATE, _KIA_EV9_SCC_CONTROL_COUNTER_BASE
  _KIA_EV9_ADRV_LIVE_TEMPLATES.clear()
  _KIA_EV9_ADRV_COUNTER_BASES.clear()
  _KIA_EV9_RAW_ADRV_LIVE_TEMPLATES.clear()
  _KIA_EV9_SCC_CONTROL_LIVE_TEMPLATE = None
  _KIA_EV9_SCC_CONTROL_COUNTER_BASE = 0
  for msg in messages:
    if msg.src != 1:
      continue
    dat = bytes(msg.dat)
    if msg.address in _KIA_EV9_ADRV_TEMPLATES and len(dat) == len(_KIA_EV9_ADRV_TEMPLATES[msg.address]):
      _KIA_EV9_ADRV_COUNTER_BASES[msg.address] = dat[2]
      # 0x160 deliberately reports AEB unavailable after suppression; only
      # inherit its counter. Every other support/status frame inherits the
      # complete READY-state body.
      if msg.address != 0x160:
        _KIA_EV9_ADRV_LIVE_TEMPLATES[msg.address] = dat
    elif msg.address in _KIA_EV9_RAW_ADRV_TEMPLATES and len(dat) == len(_KIA_EV9_RAW_ADRV_TEMPLATES[msg.address]):
      _KIA_EV9_RAW_ADRV_LIVE_TEMPLATES[msg.address] = dat
    elif msg.address == 0x1A0 and len(dat) == 32:
      _KIA_EV9_SCC_CONTROL_LIVE_TEMPLATE = dat
      _KIA_EV9_SCC_CONTROL_COUNTER_BASE = dat[2]

def create_accelerator_brake_alt_spoof(bus: int, counter: int, brake_pressed: bool, accelerator_pressed: bool,
                                       car_fingerprint=None) -> CanData:
  template = _KIA_EV9_ACCEL_BRAKE_ALT_TEMPLATE if str(car_fingerprint) == "KIA_EV9" else _ACCEL_BRAKE_ALT_TEMPLATE
  d = bytearray(template)
  d[2] = counter & 0xFF                              # COUNTER (bit 16, 8-bit)
  d[4] = (d[4] & ~0x01) | (0x01 if brake_pressed else 0x00)         # BRAKE_PRESSED (bit 32)
  d[22] = (d[22] & ~0x01) | (0x01 if accelerator_pressed else 0x00) # ACCELERATOR_PEDAL_PRESSED (bit 176)
  crc = hkg_can_fd_checksum(0x100, None, d)
  d[0] = crc & 0xFF
  d[1] = (crc >> 8) & 0xFF
  return CanData(0x100, bytes(d), bus)


def create_ev9_adrv_message(address: int, bus: int, counter: int) -> CanData:
  """Recreate a captured EV9 ADAS support payload with a fresh counter and CRC."""
  d = bytearray(_KIA_EV9_ADRV_LIVE_TEMPLATES.get(address, _KIA_EV9_ADRV_TEMPLATES[address]))
  if address in _KIA_EV9_ADRV_COUNTER_BASES:
    counter += _KIA_EV9_ADRV_COUNTER_BASES[address] + 1
  d[2] = counter & 0xFF
  crc = hkg_can_fd_checksum(address, None, d)
  d[0] = crc & 0xFF
  d[1] = (crc >> 8) & 0xFF
  return CanData(address, bytes(d), bus)


def _create_ev9_adrv_message_with_signals(packer, CAN, address: int, counter: int,
                                           message_name: str, values: dict) -> CanData:
  """Apply only decoded signal deltas to the complete captured EV9 payload."""
  msg = create_ev9_adrv_message(address, CAN.ECAN, counter)
  dat = bytearray(msg.dat)
  dbc_msg = packer.dbc.name_to_msg[message_name]
  # Preserve every unknown bit in the captured body and overwrite only the
  # explicitly named DBC signals. XOR deltas are not valid when a captured
  # field already contains a nonzero value.
  for name, value in values.items():
    sig = dbc_msg.sigs[name]
    ival = int(np.floor((value - sig.offset) / sig.factor + 0.5))
    if ival < 0:
      ival = (1 << sig.size) + ival
    _set_value(dat, sig, ival)
  crc = hkg_can_fd_checksum(address, None, dat)
  dat[0] = crc & 0xFF
  dat[1] = (crc >> 8) & 0xFF
  return CanData(address, bytes(dat), CAN.ECAN)


def create_ev9_acc_control(packer, CAN, counter: int, enabled: bool, accel_raw: float, accel_value: float,
                           stop_request: bool, cruise_standstill: bool, gas_override: bool, set_speed: float,
                           main_mode_acc: int, lead_distance: float, lead_rel_speed: float, lead_visible: bool,
                           v_ego: float, jerk_lower: float = 0.7, jerk_upper: float = 0.7) -> CanData:
  """Patch an EV9 SCC_CONTROL command into the last stock payload.

  The stock EV9 routes use different constants and object sentinels than the
  generic EV6 path. Preserve every unnamed bit, overwrite the complete command
  surface, continue the captured counter, and regenerate the CRC.
  """
  if not enabled or gas_override or stop_request:
    accel_raw = 0.0
    accel_value = 0.0

  lead_visible = bool(lead_visible)
  desired_headway = min(max(round(1.625 * max(v_ego, 0.0), 1), 3.5), 204.6) if enabled else 204.6
  values = {
    "ACCMode": 0 if not enabled else (2 if gas_override else 1),
    "MainMode_ACC": int(bool(main_mode_acc)),
    "StopReq": 1 if stop_request and enabled else 0,
    "CRUISE_STANDSTILL": 1 if cruise_standstill and stop_request and enabled else 0,
    "aReqValue": accel_value,
    "aReqRaw": accel_raw,
    "VSetDis": set_speed,
    "JerkLowerLimit": jerk_lower if enabled else 1.0,
    "JerkUpperLimit": jerk_upper if enabled else 3.0,
    "ACC_ObjDist": float(np.clip(lead_distance, 0.0, 204.7)) if lead_visible else 204.6,
    "ACC_ObjRelSpd": float(np.clip(lead_rel_speed, -16.4, 34.7)) if lead_visible else 34.6,
    "ObjValid": 0 if lead_visible else 1,
    "OBJ_STATUS": 2 if enabled and lead_visible else 0,
    "NEW_SIGNAL_3": 2 if lead_visible else 0,
    "NEW_SIGNAL_15": desired_headway,
    "SET_ME_2": 4,
    "SET_ME_3": 3,
    "SET_ME_TMP_64": 0x64,
    # The EV9 stock routes use raw 7. The DBC's physical range is stale.
    "DISTANCE_SETTING": 7 if enabled else 0,
  }

  if _KIA_EV9_SCC_CONTROL_LIVE_TEMPLATE is None:
    return packer.make_can_msg("SCC_CONTROL", CAN.ECAN, values)

  dat = bytearray(_KIA_EV9_SCC_CONTROL_LIVE_TEMPLATE)
  dbc_msg = packer.dbc.name_to_msg["SCC_CONTROL"]
  for name, value in values.items():
    sig = dbc_msg.sigs[name]
    ival = int(np.floor((value - sig.offset) / sig.factor + 0.5))
    if ival < 0:
      ival = (1 << sig.size) + ival
    _set_value(dat, sig, ival)
  dat[2] = (_KIA_EV9_SCC_CONTROL_COUNTER_BASE + counter + 1) & 0xFF
  crc = hkg_can_fd_checksum(0x1A0, None, dat)
  dat[0] = crc & 0xFF
  dat[1] = (crc >> 8) & 0xFF
  return CanData(0x1A0, bytes(dat), CAN.ECAN)


def sanitize_ev9_cluster_speed_limit(raw_speed_limit: int | float) -> int:
  """CCNC reserves 254/255; camera values 0 through 253 are literal."""
  try:
    speed_limit = int(raw_speed_limit)
  except (TypeError, ValueError):
    return 0
  return speed_limit if 0 <= speed_limit <= 253 else 0


def create_ev9_ccnc_status_messages(packer, CAN, counter: int, enabled: bool, lat_active: bool, hud, out,
                                     main_cruise_enabled: bool, lead_visible: bool, lead_distance: float,
                                     lead_two_visible: bool = False, lead_two_distance: float = 0.0,
                                     lead_two_lateral: float = 0.0,
                                     lead_left_visible: bool = False, lead_left_distance: float = 0.0,
                                     lead_left_lateral: float = 0.0,
                                     lead_right_visible: bool = False, lead_right_distance: float = 0.0,
                                     lead_right_lateral: float = 0.0,
                                     left_blindspot: bool = False, right_blindspot: bool = False,
                                     is_metric: bool = True, hud_enabled: bool | None = None,
                                     objects_enabled: bool = True, alternate_enabled: bool = False,
                                     objects_on_main_enabled: bool = False,
                                     rear_bsm_fallback_enabled: bool = False,
                                     steering_icon_active: bool | None = None,
                                     speed_limit_raw: int = 0,
                                     speed_limit_enabled: bool = False,
                                     neutral_lane_curvature_enabled: bool = True,
                                     lead_left_selected: bool = False,
                                     lead_right_selected: bool = False) -> list[CanData]:
  """Recreate EV9 CCNC engagement icons and the supported radar-object slots.

  This intentionally renders only fields whose stock EV9 meanings were seen in
  routes. It does not invent a target-distance value or claim that all radar
  tracks can be represented by the cluster's limited object slots.
  """
  # Separate the reconstruction feature gate from vehicle state. This permits
  # a synthetic EV6-style Main standby indication without falsely claiming
  # active HDA, while matching stock active values after SET/RES engagement.
  hud_feature_enabled = bool(True if hud_enabled is None else hud_enabled)
  hda_active = bool(hud_feature_enabled and enabled)
  main_standby = bool(hud_feature_enabled and main_cruise_enabled and not enabled)
  objects_active = bool(objects_enabled and (hda_active or (main_standby and objects_on_main_enabled)))
  cruise_speed = round(out.vCruiseCluster * (1 if is_metric else CV.KPH_TO_MPH))
  display_speed = 255 if not main_cruise_enabled else \
    (40 if is_metric else 25) if cruise_speed > (145 if is_metric else 90) else max(cruise_speed, 0)
  lfa_active = bool(hud_feature_enabled and lat_active)
  lfa_icon = (2 if steering_icon_active else 1) if lfa_active and steering_icon_active is not None else \
    1 if lfa_active else 0
  # No stock EV9 reference used LEAD_ALT; leadTwo is often the same fused car.
  alternate_active = False

  def object_distance(distance: float) -> float:
    return min(max(distance - 0.2, 0.1), 204.7)

  cluster_speed_limit = sanitize_ev9_cluster_speed_limit(speed_limit_raw) if speed_limit_enabled else 0
  values_161 = {
    "DAW_ICON": 0,
    "LKA_ICON": 0,
    "LFA_ICON": lfa_icon,
    "HDA_ICON": 2 if hda_active else 1 if main_standby else 0,
    # Stock EV9 HDA leaves these lane-rendering fields neutral. The cluster
    # renders its own lane geometry from the HDA/LFA state.
    "CENTERLINE": 0,
    "TARGET": 3 if hda_active else 0,
    # Stock copies SCC's desired following-headway marker. The captured EV9
    # setting is 1.626 seconds and has near-unity correlation with ego speed,
    # not lead range or stopping distance.
    "TARGET_DISTANCE": min(max(float(getattr(out, "vEgo", 0.0)) * 1.626, 0.1), 204.7) if hda_active else 204.6,
    # This DBC represents the stock raw-zero neutral value as physical 15.
    # Physical zero packs raw 17, which the cluster renders as a right curve.
    "LANELINE_CURVATURE": 15 if neutral_lane_curvature_enabled else 0,
    "LANELINE_LEFT": 0,
    "LANELINE_RIGHT": 0,
    # Value 1 means that lane-change assistance is available, not that a
    # vehicle occupies the corresponding blind spot.
    "LCA_LEFT_ICON": 1 if hda_active or main_standby else 0,
    "LCA_RIGHT_ICON": 1 if hda_active or main_standby else 0,
    "SETSPEED": 3 if hda_active else 1 if main_standby else 0,
    "SETSPEED_HUD": 2 if hda_active else 1 if main_standby else 0,
    "SETSPEED_SPEED": display_speed if hda_active or main_standby else 255,
    "DISTANCE": hud.leadDistanceBars if hda_active else 0,
    "DISTANCE_SPACING": 3 if hda_active or main_standby else 0,
    "DISTANCE_LEAD": 2 if objects_active and lead_visible else 0,
    "DISTANCE_CAR": 2 if hda_active else 1 if main_standby else 0,
    "SLA_ICON": 0,
    "NAV_ICON": 0,
    # Stock EV9 warning scenes kept BCA, arrows, sounds, and VIBRATE neutral.
    # Genuine/synthetic 0x1BA is the independently reconstructed BSM path.
    "BCA_LEFT": 0,
    "BCA_RIGHT": 0,
  }

  values_162 = {fault: 0 for fault in ("FAULT_FSS", "FAULT_FCA", "FAULT_LSS", "FAULT_SLA",
                                                   "FAULT_HDA", "FAULT_DAS", "FAULT_LFA", "FAULT_DAW", "FAULT_ESS")}
  values_162.update({
    # EV9 stock routes observed this field at zero, including lane/BSM events.
    # Do not claim steering-wheel vibration until an EV9 route proves its use.
    "VIBRATE": 0,
    # The fused/selected primary is the white box used in stock display data;
    # generic adjacent tracks remain gray boxes.
    "LEAD": 2 if objects_active and lead_visible else 0,
    "LEAD_DISTANCE": object_distance(lead_distance) if objects_active and lead_visible else 0.0,
    "LEAD_LATERAL": 0.0,
    "LEAD_ALT": 1 if alternate_active else 0,
    "LEAD_ALT_DISTANCE": min(max(lead_two_distance, 0.0), 204.7) if alternate_active else 0.0,
    "LEAD_ALT_LATERAL": min(abs(lead_two_lateral), 12.7) if alternate_active else 0.0,
    "LEAD_LEFT": (2 if lead_left_selected else 1) if objects_active and lead_left_visible else 0,
    "LEAD_LEFT_DISTANCE": object_distance(lead_left_distance) if objects_active and lead_left_visible else 0.0,
    "LEAD_LEFT_LATERAL": 3.0 if objects_active and lead_left_visible else 0.0,
    "LEAD_RIGHT": (2 if lead_right_selected else 1) if objects_active and lead_right_visible else 0,
    "LEAD_RIGHT_DISTANCE": object_distance(lead_right_distance) if objects_active and lead_right_visible else 0.0,
    "LEAD_RIGHT_LATERAL": 3.0 if objects_active and lead_right_visible else 0.0,
    # The stock route uses a fixed near-field marker for rear BSM objects; it
    # does not provide a measured range, so retain that honest UI convention.
    "LEAD_LEFT_REAR_STATUS": 1 if objects_active and rear_bsm_fallback_enabled and left_blindspot else 0,
    "LEAD_LEFT_REAR_DISTANCE": 25.0 if objects_active and rear_bsm_fallback_enabled and left_blindspot else 0.0,
    "LEAD_LEFT_REAR_LATERAL": 3.0 if objects_active and rear_bsm_fallback_enabled and left_blindspot else 0.0,
    "LEAD_RIGHT_REAR_STATUS": 1 if objects_active and rear_bsm_fallback_enabled and right_blindspot else 0,
    "LEAD_RIGHT_REAR_DISTANCE": 25.0 if objects_active and rear_bsm_fallback_enabled and right_blindspot else 0.0,
    "LEAD_RIGHT_REAR_LATERAL": 3.0 if objects_active and rear_bsm_fallback_enabled and right_blindspot else 0.0,
    # Stock EV9 passes the camera's displayed number through literally. Sign
    # classes remain zero until their camera-to-CCNC mapping is decoded.
    "SPEEDLIMIT": cluster_speed_limit,
    "SPEEDLIMIT_FLASH": 2 if speed_limit_enabled else 0,
    "COUNTRY": 7 if speed_limit_enabled else 0,
    "SPEEDLIMIT_WEATHER": 0,
    "SIGNS": 0,
  })

  return [
    _create_ev9_adrv_message_with_signals(packer, CAN, 0x161, counter, "CCNC_0x161", values_161),
    _create_ev9_adrv_message_with_signals(packer, CAN, 0x162, counter, "CCNC_0x162", values_162),
  ]


def create_ev9_adrv_160(bus: int, counter: int) -> CanData:
  """Recreate EV9 0x160 while truthfully showing AEB disabled."""
  return create_ev9_adrv_message(0x160, bus, counter)


def create_ev9_raw_adrv_message(address: int, bus: int) -> CanData:
  """Replay an EV9 ADAS status frame that has no standard rolling CRC."""
  dat = _KIA_EV9_RAW_ADRV_LIVE_TEMPLATES.get(address, _KIA_EV9_RAW_ADRV_TEMPLATES[address])
  return CanData(address, dat, bus)
