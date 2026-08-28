from opendbc.car import CanBusBase
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.honda.values import (HondaFlags, HONDA_BOSCH, HONDA_BOSCH_ALT_RADAR, HONDA_BOSCH_RADARLESS,
                                      HONDA_BOSCH_CANFD, CarControllerParams)
from opendbc.car.honda.values import CAR

# CAN bus layout with relay
# 0 = ACC-CAN - radar side
# 1 = F-CAN B - powertrain
# 2 = ACC-CAN - camera side
# 3 = F-CAN A - OBDII port


class CanBus(CanBusBase):
  def __init__(self, CP=None, fingerprint=None) -> None:
    # use fingerprint if specified
    super().__init__(CP if fingerprint is None else None, fingerprint)

    # powertrain bus is split instead of radar on radarless and CAN FD Bosch
    if CP.carFingerprint in (HONDA_BOSCH - HONDA_BOSCH_RADARLESS - HONDA_BOSCH_CANFD):
      self._pt, self._radar = self.offset + 1, self.offset
      # normally steering commands are sent to radar, which forwards them to powertrain bus
      # when radar is disabled, steering commands are sent directly to powertrain bus
      self._lkas = self._pt if CP.openpilotLongitudinalControl else self._radar
    else:
      self._pt, self._radar, self._lkas = self.offset, self.offset + 1, self.offset

  @property
  def pt(self) -> int:
    return self._pt

  @property
  def radar(self) -> int:
    return self._radar

  @property
  def camera(self) -> int:
    return self.offset + 2

  @property
  def lkas(self) -> int:
    return self._lkas

  # B-CAN is forwarded to ACC-CAN radar side (CAN 0 on fake ethernet port)
  @property
  def body(self) -> int:
    return self.offset


def create_brake_command(packer, CAN, apply_brake, pump_on, pcm_override, pcm_cancel_cmd, fcw, car_fingerprint, stock_brake):
  # TODO: do we loose pressure if we keep pump off for long?
  brakelights = apply_brake > 0
  brake_rq = apply_brake > 0
  pcm_fault_cmd = False

  values = {
    "COMPUTER_BRAKE": apply_brake,
    "BRAKE_PUMP_REQUEST": pump_on,
    "CRUISE_OVERRIDE": pcm_override,
    "CRUISE_FAULT_CMD": pcm_fault_cmd,
    "CRUISE_CANCEL_CMD": pcm_cancel_cmd,
    "COMPUTER_BRAKE_REQUEST": brake_rq,
    "SET_ME_1": 1,
    "BRAKE_LIGHTS": brakelights,
    "CHIME": stock_brake["CHIME"] if fcw else 0,  # send the chime for stock fcw
    "FCW": fcw << 1,  # TODO: Why are there two bits for fcw?
    "AEB_REQ_1": 0,
    "AEB_REQ_2": 0,
    "AEB_STATUS": 0,
  }
  return packer.make_can_msg("BRAKE_COMMAND", CAN.pt, values)


def create_acc_commands(packer, CAN, enabled, active, accel, gas, stopping_counter, CP, gas_force=None):
  commands = []
  min_gas_accel = CarControllerParams.BOSCH_GAS_LOOKUP_BP[0]

  control_on = 5 if enabled else 0
  if gas_force is None:
    gas_force = accel
  gas_command = gas if active and gas_force > min_gas_accel else -30000
  accel_command = accel if active else 0
  braking = 1 if active and gas_force < min_gas_accel else 0
  standstill = 1 if active and stopping_counter > 0 else 0
  standstill_release = 1 if active and stopping_counter == 0 else 0

  # common ACC_CONTROL values
  acc_control_values = {
    'ACCEL_COMMAND': accel_command,
    'STANDSTILL': standstill,
  }

  if CP.carFingerprint in HONDA_BOSCH_RADARLESS:
    acc_control_values.update({
      "CONTROL_ON": enabled,
      "IDLESTOP_ALLOW": stopping_counter > 200,  # allow idle stop after 4 seconds (50 Hz)
    })
  else:
    acc_control_values.update({
      # setting CONTROL_ON causes car to set POWERTRAIN_DATA->ACC_STATUS = 1
      "CONTROL_ON": control_on,
      "GAS_COMMAND": gas_command,  # used for gas
      "BRAKE_LIGHTS": braking,
      "BRAKE_REQUEST": braking,
      "STANDSTILL_RELEASE": standstill_release,
    })
    acc_control_on_values = {
      "SET_TO_3": 0x03,
      "CONTROL_ON": enabled,
      "SET_TO_FF": 0xff,
      "SET_TO_75": 0x75,
      "SET_TO_30": 0x30,
    }
    commands.append(packer.make_can_msg("ACC_CONTROL_ON", CAN.pt, acc_control_on_values))

  commands.append(packer.make_can_msg("ACC_CONTROL", CAN.pt, acc_control_values))
  return commands


def create_steering_control(packer, CAN, apply_torque, lkas_active, tja_control):
  values = {
    "STEER_TORQUE": apply_torque if lkas_active else 0,
    "STEER_TORQUE_REQUEST": lkas_active,
  }

  if tja_control:
    values["STEER_DOWN_TO_ZERO"] = lkas_active

  return packer.make_can_msg("STEERING_CONTROL", CAN.lkas, values)


def create_bosch_supplemental_1(packer, CAN):
  # non-active params
  values = {
    "SET_ME_X04": 0x04,
    "SET_ME_X80": 0x80,
    "SET_ME_X10": 0x10,
  }
  return packer.make_can_msg("BOSCH_SUPPLEMENTAL_1", CAN.lkas, values)


def create_acc_hud(packer, bus, CP, enabled, pcm_speed, pcm_accel, hud_control, hud_v_cruise, is_metric, acc_hud):
  acc_hud_values = {
    'CRUISE_SPEED': hud_v_cruise,
    'ENABLE_MINI_CAR': 1 if enabled else 0,
    # only moves the lead car without ACC_ON
    'HUD_DISTANCE': hud_control.leadDistanceBars,  # wraps to 0 at 4 bars
    'IMPERIAL_UNIT': int(not is_metric),
    'HUD_LEAD': 2 if enabled and hud_control.leadVisible else 1 if enabled else 0,
    'SET_ME_X01_2': 1,
  }

  if CP.carFingerprint == CAR.HONDA_ACCORD_11G:
    # Stock CAN-FD radar toggles these together with ACC/lead/braking state. Keeping them low when
    # neither lead nor braking is present matches MVL's observed CAN-FD payload shape.
    set_me = int(enabled and (bool(acc_hud_values['HUD_LEAD']) or (pcm_accel < 0.2)))
    acc_hud_values['SET_ME_X01'] = set_me
    acc_hud_values['SET_ME_X01_2'] = set_me

  if CP.carFingerprint in HONDA_BOSCH:
    acc_hud_values['ACC_ON'] = int(enabled)
    # Preserve StarPilot's existing Bosch HUD behavior outside CAN-FD. MVL's CAN-FD
    # replacement radar expects FCW/CMBS enabled, while legacy Bosch keeps them off.
    canfd = CP.carFingerprint == CAR.HONDA_ACCORD_11G
    acc_hud_values['FCM_OFF'] = 0 if canfd else 1
    acc_hud_values['FCM_OFF_2'] = 0 if canfd else 1
  else:
    # Shows the distance bars, TODO: stock camera shows updates temporarily while disabled
    acc_hud_values['ACC_ON'] = int(enabled)
    acc_hud_values['PCM_SPEED'] = pcm_speed * CV.MS_TO_KPH
    acc_hud_values['PCM_GAS'] = pcm_accel
    acc_hud_values['SET_ME_X01'] = 1
    acc_hud_values['FCM_OFF'] = acc_hud['FCM_OFF']
    acc_hud_values['FCM_OFF_2'] = acc_hud['FCM_OFF_2']
    acc_hud_values['FCM_PROBLEM'] = acc_hud['FCM_PROBLEM']
    acc_hud_values['ICONS'] = acc_hud['ICONS']

  return packer.make_can_msg("ACC_HUD", bus, acc_hud_values)


def create_lkas_hud(packer, bus, CP, hud_control, lat_active, steering_available, reduced_steering, alert_steer_required, lkas_hud,
                    lkas_state_change=None):
  commands = []
  lanes_visible = bool(hud_control.lanesVisible or lat_active)

  lkas_hud_values = {
    'LKAS_READY': 1,
    'LKAS_STATE_CHANGE': 1,
    'STEERING_REQUIRED': alert_steer_required,
    'SOLID_LANES': lanes_visible,
    'BEEP': 0,
  }

  # Preserve historical behavior for existing callers.
  # Accord 11G explicitly supplies the stock-style pulse.
  if lkas_state_change is not None:
    lkas_hud_values['LKAS_STATE_CHANGE'] = int(lkas_state_change)

  if CP.carFingerprint in (HONDA_BOSCH_RADARLESS | HONDA_BOSCH_CANFD):
    lkas_hud_values['LANE_LINES'] = 3
    lkas_hud_values['DASHED_LANES'] = lanes_visible

    # car likely needs to see LKAS_PROBLEM fall within a specific time frame, so forward from camera
    # TODO: needed for Bosch CAN FD?
    if CP.carFingerprint in HONDA_BOSCH_RADARLESS:
      lkas_hud_values['LKAS_PROBLEM'] = lkas_hud['LKAS_PROBLEM']

  if not (CP.flags & HondaFlags.BOSCH_EXT_HUD):
    lkas_hud_values['RDM_OFF'] = 1
    lkas_hud_values['LANE_ASSIST_BEEP_OFF'] = 1

  # New HUD concept for selected Bosch cars, overwrites some of the above
  # TODO: make global across all Honda if feedback is favorable
  if CP.carFingerprint in HONDA_BOSCH_ALT_RADAR:
    lkas_hud_values['DASHED_LANES'] = bool(steering_available or lanes_visible)
    lkas_hud_values['SOLID_LANES'] = lanes_visible
    lkas_hud_values['LKAS_PROBLEM'] = lat_active and reduced_steering

  if CP.flags & HondaFlags.BOSCH_EXT_HUD and not CP.openpilotLongitudinalControl:
    commands.append(packer.make_can_msg('LKAS_HUD_A', bus, lkas_hud_values))
    commands.append(packer.make_can_msg('LKAS_HUD_B', bus, lkas_hud_values))
  else:
    commands.append(packer.make_can_msg('LKAS_HUD', bus, lkas_hud_values))

  return commands


def create_radar_hud(packer, bus):
  radar_hud_values = {
    'CMBS_OFF': 0x01,
    'SET_TO_1': 0x01,
  }

  return packer.make_can_msg('RADAR_HUD', bus, radar_hud_values)


def create_legacy_brake_command(packer, bus):
  return packer.make_can_msg("LEGACY_BRAKE_COMMAND", bus, {})


def spam_buttons_command(packer, CAN, button_val, car_fingerprint, cruise_setting=0, ambient_light=None, bus=None):
  values = {
    'CRUISE_BUTTONS': button_val,
    'CRUISE_SETTING': cruise_setting,
  }
  # Existing StarPilot callers should retain their previous payload; only the CAN-FD camera
  # takeover path explicitly echoes the live ambient-light byte.
  if ambient_light is not None:
    values['AMBIENT_LIGHT_MAYBE'] = ambient_light
  if bus is None:
    # send buttons to camera on radarless (camera does ACC) cars
    bus = CAN.camera if car_fingerprint in HONDA_BOSCH_RADARLESS else CAN.pt
  return packer.make_can_msg("SCM_BUTTONS", bus, values)


def create_radar_hud_canfd(packer, bus, acc, acc_pulse=False):
  values = {
    'CMBS_ENABLED_MAYBE': 1 if (acc and acc_pulse) else 0,
    'ACC_ON': acc,
    'SET_ME_X01': 0x01,
    'SET_ME_X01_2': 0x01,
  }
  return packer.make_can_msg("RADAR_HUD_CANFD", bus, values)


def create_canfd_supplemental(packer, bus):
  values = {
    'SET_ME_X01': 0x01,
    'SET_ME_X41': 0x41,
  }
  return packer.make_can_msg("BOSCH_SUPPLEMENTAL_CANFD", bus, values)


RADAR_MUX_BANK_STARTS = (1, 17, 33, 49)
PATH_OFFSET_INVALID = 2047
# These extended IDs use the CAN-FD checksum offset used by the Accord 11G
# replacement-radar stream. Keep the legacy Honda offset for existing high-ID
# messages on other Honda platforms.
HONDA_CANFD_MVL_CHECKSUM_IDS = frozenset((
  0x6CD5558, 0x6CD5559, 0xF31AA52, 0xF31AA5C, 0x1A45AA4E,
))


def _lane_path_offsets(radar_mux):
  pos = next((radar_mux - start for start in RADAR_MUX_BANK_STARTS if start <= radar_mux <= start + 9), 0)
  if pos == 0:
    return (0, 0, 0, 0)
  if pos == 1:
    return (0, 0, PATH_OFFSET_INVALID, PATH_OFFSET_INVALID)
  return (PATH_OFFSET_INVALID,) * 4


def create_canfd_50hz_radar_messages(packer, bus, radar_mux):
  offsets = _lane_path_offsets(radar_mux)
  lane_path_values = {
    'MUX': radar_mux,
    'PATH_OFFSET_1': offsets[0],
    'PATH_OFFSET_2': offsets[1],
    'PATH_OFFSET_3': offsets[2],
    'PATH_OFFSET_4': offsets[3],
  }
  hud_objects_values = {
    'MUX': radar_mux,
    'OBJECT_ID': 0,
    'IS_LEAD_CAR': 0,
    'CAR_TYPE': -1,
    'ROTATION': -128,
    'LONG_DIST': 196.9,
    'LAT_DIST': 204.7,
  }
  return [
    packer.make_can_msg('LANE_PATH', bus, lane_path_values),
    packer.make_can_msg('HUD_OBJECTS', bus, hud_objects_values),
  ]


def create_canfd_5hz_radar_messages(packer, bus, radar_ref_cntr):
  radar_lead_values = {
    'CNTR_REF': radar_ref_cntr,
    'SET_ME_X01': 0x01,
    'TARGET_SPEED_MAYBE': 140,
    # v3 initially sends MVL's stock-like idle lane state. Model-derived dash rendering can be added
    # separately after the DTC/ownership handover is proven on-car.
    'LEFT_LANE': 0,
    'RIGHT_LANE': 0,
    'LANE_PATH_LENGTH': 6,
  }
  radar_lead2_values = {
    'SET_ME_X88': 136,
    'SET_ME_X78': 120,
    'LEAD_DISTANCE_MAYBE': 0,
  }
  return [
    packer.make_can_msg('RADAR_LEAD', bus, radar_lead_values),
    packer.make_can_msg('RADAR_LEAD2', bus, radar_lead2_values),
  ]


def honda_checksum(address: int, sig, d: bytearray) -> int:
  s = 0
  extended = address > 0x7FF
  addr = address
  while addr:
    s += addr & 0xF
    addr >>= 4
  for i in range(len(d)):
    x = d[i]
    if i == len(d) - 1:
      x >>= 4
    s += (x & 0xF) + (x >> 4)
  s = 8 - s
  if extended:
    s += 10 if address in HONDA_CANFD_MVL_CHECKSUM_IDS else 3
  return s & 0xF
