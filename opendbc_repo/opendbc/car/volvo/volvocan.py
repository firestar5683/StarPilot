from opendbc.car.volvo.helpers import (checksum_lca_2_message, checksum_2_0x69_message, checksum_1_pscm_related_message,
                                       checksum_2_pscm_related_message, checksum_lca_5_message)
from opendbc.car.carlog import carlog


def create_c1_pscm_message(packer, msg_pscm: dict):
  values = {
    "LKATorque": 0,
    "SteeringAngleServo": msg_pscm["SteeringAngleServo"],
    "byte0": msg_pscm["byte0"],
    "byte3": msg_pscm["byte3"],
    "byte4": msg_pscm["byte4"],
    "byte7": msg_pscm["byte7"],
    "LKAActive": int(msg_pscm["LKAActive"]) & 0xD,
  }
  return packer.make_can_msg("PSCM1", 2, values)


def create_c1_checksum(data: bytes) -> int:
  angle_raw = ((data[4] & 0x3F) << 8) | data[5]
  direction = data[7] & 0x3
  checksum_sum = (data[3] + direction + angle_raw + (angle_raw >> 8)) & 0xFF
  return checksum_sum ^ 0xFF


def create_c1_steering_control(packer, apply_angle: float, lat_active: bool):
  values = {
    "SET_X_E3": 0xE3,
    "SET_X_B4": 0xB4,
    "SET_X_08": 0x08,
    "TrqLim": 0,
    "LKAAngleReq": apply_angle,
    "LKASteerDirection": 3 if lat_active else 0,
    "SET_X_25": 0x25,
    "SET_X_02": 0x02,
  }
  data = packer.make_can_msg("FSM1", 0, values)[1]
  values["Checksum"] = create_c1_checksum(data)
  return packer.make_can_msg("FSM1", 0, values)


def create_c1_cancel(packer):
  return packer.make_can_msg("CCButtons", 0, {"ACCStopBtn": 1})


def create_lca_message(packer, lat_active: bool, apply_angle: float, msg_lca: dict,
                       authority_pos: int = 614, authority_neg: int = -614,
                       overrides: dict | None = None):
  """
  Create LCA (Lane Centering Assist) steering command for Volvo CMA platform.
  Uses angle-based control via the LCA_STEER signal.

  NOTE: This message must be sent continuously (even when inactive) because
  stock LCA is permanently blocked by panda safety. When lat_active=False,
  we send a safe/inactive LCA message to maintain PSCM communication.

  Args:
    packer: CAN packer instance
    lat_active: Whether lateral control is active
    apply_angle: Steering angle in degrees (positive = left, negative = right)
    msg_lca: Dictionary containing LCA message values
    authority_pos: LCA_STEER_LOOSELY value [0..614] — right-pull torque-authority
                   envelope. Saturated (614) for stock-equivalent stiff feel; the
                   carcontroller envelope tracker collapses this on driver override
                   and rebuilds slowly to reproduce stock PA's easy-override feel.
    authority_neg: LCA_STEER_LOOSELY_INV value [-614..0] — left-pull authority.
    overrides: Optional dict of signal overrides (keys are UPPERCASE DBC signal names)
  """
  if not lat_active:
    return packer.make_can_msg('LCA', 2, msg_lca)

  # In openpilot, a positive angle corresponds to a LEFT turn.
  # In Volvo, a positive LCA_STEER value corresponds to a LEFT turn.

  values = {
    'NEW_SIGNAL_1': 3,
    'LCA_ENABLE_INV': 0 if lat_active else 1,
    'LANE_KEEP_ACTIVE_INV': 3,
    'LCA_STEER_LOOSELY': int(authority_pos) if lat_active else 0,
    'NEW_SIGNAL_7': 7,
    'LCA_STEER_LOOSELY_INV': int(authority_neg) if lat_active else 0,
    # Steering rate - Stock LCA increased from 35 to 39 steppedly when steering request was overridden by openpilot that couldn't steer enough
    'LCA_RATE_OF_CHANGE': 80 if lat_active else 251,
    'LCA_STEER': msg_lca['LCA_STEER'],
    'NEW_SIGNAL_6': 15,
  }

  # Apply any overrides from live testing config
  if overrides:
    for key, val in overrides.items():
      values[key] = val

  return packer.make_can_msg('LCA', 2, values)

def create_pscm_message(packer, lat_active: bool, msg_pscm: dict, frame: int):
  values = {
    'PSCM_ANGLE_SENSOR': msg_pscm['PSCM_ANGLE_SENSOR'],
    'BIT_0': msg_pscm['BIT_0'],
    'HANDS_ON_STEERING_WHEEL_A': msg_pscm['HANDS_ON_STEERING_WHEEL_A'],
    'HANDS_ON_STEERING_WHEEL_B': msg_pscm['HANDS_ON_STEERING_WHEEL_B'],
    'BYTE_4': msg_pscm['BYTE_4'],
    'DRIVER_INPUT_DEVIATION': msg_pscm['DRIVER_INPUT_DEVIATION'],
    'BYTE_6': msg_pscm['BYTE_6'],
    'BYTE_7': msg_pscm['BYTE_7'],
  }

  # Spoof hands on wheel while openpilot is actively steering, so the stock EPS
  # doesn't fault/nag on torque that didn't come from a human.
  if lat_active:
    values['HANDS_ON_STEERING_WHEEL_B'] = 186 if frame % 2 == 0 else 154 # msg_pscm['HANDS_ON_STEERING_WHEEL_B']
    values['HANDS_ON_STEERING_WHEEL_A'] = 195 if frame % 2 == 0 else 249 # msg_pscm['HANDS_ON_STEERING_WHEEL_A']

  return packer.make_can_msg('PSCM', 0, values)

def create_lca_3_message(packer, lat_active: bool, apply_angle: float, msg_lca_3: dict, counter_value: int):
  """
  Create LCA_3 message for Volvo CMA platform.
  This message enables PSCM to accept LCA commands.

  Args:
    packer: CAN packer instance
    lat_active: Whether lateral control is active
    apply_angle: Steering angle in degrees (used for direction indicator)
    msg_lca_3: Dictionary containing LCA_3 message values
    counter_value: Counter value to use (from pattern or stock)
  """
  values = {
    'NEW_SIGNAL_3': 0 if lat_active else msg_lca_3['NEW_SIGNAL_3'],
    'LCA_ACCEPT_COMMANDS_RELATED': 15 if lat_active else msg_lca_3['LCA_ACCEPT_COMMANDS_RELATED'],
    'NEW_SIGNAL_2': 0 if lat_active else msg_lca_3['NEW_SIGNAL_2'],
    'NEW_SIGNAL_5': 30 if lat_active else msg_lca_3['NEW_SIGNAL_5'],
    'LCA_ACCEPT_COMMANDS_INV': 0 if lat_active else msg_lca_3['LCA_ACCEPT_COMMANDS_INV'],
    'NEW_SIGNAL_4': 3 if lat_active else msg_lca_3['NEW_SIGNAL_4'],
    'SPEED_A': msg_lca_3['SPEED_A'],
    'SPEED_B': msg_lca_3['SPEED_B'],
    'NEW_SIGNAL_8': 1 if lat_active else msg_lca_3['NEW_SIGNAL_8'],
    'NEW_SIGNAL_7': 3 if lat_active else msg_lca_3['NEW_SIGNAL_7'],
    'NEW_SIGNAL_9': msg_lca_3['NEW_SIGNAL_9'],
    'COUNTER_1': counter_value,
  }

  return packer.make_can_msg('LCA_3', 2, values)

def diff_dicts(a, b):
  only_in_a = a.keys() - b.keys()
  only_in_b = b.keys() - a.keys()
  in_both = a.keys() & b.keys()

  changed = {k: (a[k], b[k]) for k in in_both if a[k] != b[k]}

  return {
    "only_in_a": {k: a[k] for k in only_in_a},
    "only_in_b": {k: b[k] for k in only_in_b},
    "changed": changed,
  }

def create_lca_2_message(packer, lat_active: bool, msg_lca_2: dict, counter_1: int, counter_2: int):
  """
  Create LCA_2 message to spoof PILOT_ASSIST_ENGAGED when openpilot is active.

  When lat_active=True, we set PILOT_ASSIST_ENGAGED=1 to make PSCM accept LCA commands,
  even if the driver has disabled stock Pilot Assist.

  Args:
    packer: CAN packer instance
    lat_active: Whether lateral control is active
    msg_lca_2: Dictionary containing LCA_2 message values from car
    counter_1: Managed COUNTER_1 value (increments by +2 mod 16)
    counter_2: Managed COUNTER_2 value (increments by +4 mod 16)
  """
  #return packer.make_can_msg('LCA_2', 2, msg_lca_2)
  #if not lat_active:
  #  return packer.make_can_msg('LCA_2', 2, msg_lca_2)

  #values = dict(msg_lca_2)

  values = {
    'BYTE_0': 24 if lat_active else msg_lca_2['BYTE_0'], # 24 always
    'COUNTER_1': msg_lca_2['COUNTER_1'], # Byte 1 Low Nibble [5:8] - 4-bit counter that increments by +2 (modulo 16)
    'PILOT_ASSIST_ENGAGED': 1 if lat_active else msg_lca_2['PILOT_ASSIST_ENGAGED'], # Byte 1 [4]
    'BYTE_1_BITFIELD_0': msg_lca_2['BYTE_1_BITFIELD_0'],
    'ESC_ACTUATING': msg_lca_2['ESC_ACTUATING'],
    'ESC_ELIGIBLE': msg_lca_2['ESC_ELIGIBLE'],
    'CHECKSUM_2': msg_lca_2['CHECKSUM_2'], # Checksum on bytes 0 and 1
    'NEW_SIGNAL_2': 0 if lat_active else msg_lca_2['NEW_SIGNAL_2'],
    'COUNTER_2': msg_lca_2['COUNTER_2'], # Byte 5 Low Nibble - 4-bit counter that increments by +4 (modulo 16)
    'NEW_SIGNAL_3': 3 if lat_active else msg_lca_2['NEW_SIGNAL_3'],
    'BRAKE_PEDAL_PRESSED_B': msg_lca_2['BRAKE_PEDAL_PRESSED_B'],
    'BRAKE_PEDAL_PRESSED_A': msg_lca_2['BRAKE_PEDAL_PRESSED_A'],
    'CHECKSUM_1': msg_lca_2['CHECKSUM_1'], # Byte 6 is a checksum based on Bytes 1, 2, and 5 only
    'BYTE_7': 0 if lat_active else msg_lca_2['BYTE_7'],
  }

  dat = packer.make_can_msg('LCA_2', 2, values)

  built_bytes = dat[1]  # dat is (addr, bytes, bus) tuple - extract bytes
  b0 = built_bytes[0]
  b1 = built_bytes[1]
  b2 = built_bytes[2]
  b3 = built_bytes[3]
  b4 = built_bytes[4]
  b5 = built_bytes[5]

  values['CHECKSUM_1'] = checksum_lca_2_message(b0, b5)

  # Only validate when not active and message is valid (BYTE_0 should be 24, not 0)
  if not lat_active:
    #assert values['CHECKSUM_1'] == msg_lca_2['CHECKSUM_1']
    if values['CHECKSUM_1'] != msg_lca_2['CHECKSUM_1']:
      carlog.warning("[volvocan.py] LCA_2 CHECKSUM mismatch")
      print(f"b0={b0}, b1={b1}, b2={b2}, b5={b5}, calculated={values['CHECKSUM_1']}, expected={msg_lca_2['CHECKSUM_1']}")
      #assert False

  # Checksum 2 - depends on bytes 0, 1, 3, and 4
  checksum_2 = checksum_2_0x69_message(b0, b1, b3, b4)
  values['CHECKSUM_2'] = checksum_2
  if not lat_active:
    if values['CHECKSUM_2'] != msg_lca_2['CHECKSUM_2']:
      carlog.warning("[volvocan.py] LCA_2 CHECKSUM_2 mismatch")
      print(f"b0={b0}, b1={b1}, b3={b3}, b4={b4}, calculated={values['CHECKSUM_2']}, expected={msg_lca_2['CHECKSUM_2']}")
      #assert False
  values['COUNTER_1'] = counter_1
  values['COUNTER_2'] = counter_2
  # Re-pack with updated counters to get correct bytes for checksum calculation
  dat = packer.make_can_msg('LCA_2', 2, values)
  built_bytes = dat[1]  # dat is (addr, bytes, bus) tuple - extract bytes
  b0 = built_bytes[0]
  b1 = built_bytes[1]
  b3 = built_bytes[3]
  b4 = built_bytes[4]
  b5 = built_bytes[5]
  values['CHECKSUM_1'] = checksum_lca_2_message(b0, b5)
  values['CHECKSUM_2'] = checksum_2_0x69_message(b0, b1, b3, b4)
  return packer.make_can_msg('LCA_2', 2, values)

def create_lca_5_message(packer, lat_active: bool, target_angle_deg: float, msg_lca_5: dict, counter: int,
                         overrides: dict | None = None):
  """
  Create LCA_5 message (0x67) with angle-based steering control.

  Args:
    packer: CAN packer instance
    lat_active: Whether lateral control is active
    target_angle_deg: Target steering angle in degrees (positive = left, negative = right)
    msg_lca_5: Stock LCA_5 values from car
    counter: Counter value (0-15, increments by 4)
    overrides: Optional dict of signal overrides (keys are UPPERCASE DBC signal names)

  Returns:
    CAN message for LCA_5 on bus 2
  """

  # DBC defines LCA_5_STEER as 15-bit signed with scale 0.05596 deg/count
  # Packer handles the encoding automatically - just pass the angle in degrees

  # Build values dictionary (wheel speeds and counter unchanged)
  values = {
    'WHEEL_SPEED_1': msg_lca_5['WHEEL_SPEED_1'],
    'NEW_SIGNAL_4': msg_lca_5['NEW_SIGNAL_4'],
    'NEW_SIGNAL_1': msg_lca_5['NEW_SIGNAL_1'],
    'WHEEL_SPEED_2': msg_lca_5['WHEEL_SPEED_2'],
    'NEW_SIGNAL_5': msg_lca_5['NEW_SIGNAL_5'],
    'NEW_SIGNAL_2': msg_lca_5['NEW_SIGNAL_2'],
    'LCA_5_STEER': target_angle_deg if lat_active else msg_lca_5['LCA_5_STEER'],
    'COUNTER': counter,
  }

  # Apply any overrides from live testing config
  if overrides:
    for key, val in overrides.items():
      values[key] = val

  dat = packer.make_can_msg('LCA_5', 2, values)
  built_bytes = dat[1]  # dat is (addr, bytes, bus) tuple - extract bytes
  values['CHECKSUM'] = checksum_lca_5_message(built_bytes[0], built_bytes[1], built_bytes[3], built_bytes[4], built_bytes[5])
  return packer.make_can_msg('LCA_5', 2, values)

def create_speed_message(packer, msg_speed: dict):
  """
  Forward SPEED message (0x60) by copying all bytes.

  Args:
    packer: CAN packer instance
    msg_speed: Dictionary containing SPEED message values from car
  """
  values = {
    'SPEED': msg_speed['SPEED'],
    'NEW_SIGNAL_1': msg_speed['NEW_SIGNAL_1'],
    'NEW_SIGNAL_2': msg_speed['NEW_SIGNAL_2'],
    'NEW_SIGNAL_3': msg_speed['NEW_SIGNAL_3'],
    'NEW_SIGNAL_4': msg_speed['NEW_SIGNAL_4'],
    'NEW_SIGNAL_5': msg_speed['NEW_SIGNAL_5'],
    'NEW_SIGNAL_6': msg_speed['NEW_SIGNAL_6'],
  }

  return packer.make_can_msg('SPEED', 2, values)

def create_speed_2_message(packer, msg_speed_2: dict):
  """
  Forward SPEED_2 message (0x68) by copying all bytes.

  Args:
    packer: CAN packer instance
    msg_speed_2: Dictionary containing SPEED_2 message values from car
  """
  values = {
    'WHEEL_SPEED_LEFT': msg_speed_2['WHEEL_SPEED_LEFT'],
    'WHEEL_SPEED_RIGHT': msg_speed_2['WHEEL_SPEED_RIGHT'],
    'NEW_SIGNAL_1': msg_speed_2['NEW_SIGNAL_1'],
    'NEW_SIGNAL_2': msg_speed_2['NEW_SIGNAL_2'],
    'NEW_SIGNAL_3': msg_speed_2['NEW_SIGNAL_3'],
    'NEW_SIGNAL_4': msg_speed_2['NEW_SIGNAL_4'],
    'COUNTER_1': msg_speed_2['COUNTER_1'],
    'COUNTER_2': msg_speed_2['COUNTER_2'],
  }

  return packer.make_can_msg('SPEED_2', 2, values)

def create_speed_3_message(packer, msg_speed_3: dict):
  """
  Forward SPEED_3 message (0x60) by copying all bytes.

  Args:
    packer: CAN packer instance
    msg_speed_3: Dictionary containing SPEED_3 message values from car
  """
  values = {
    'ALL_BYTES': msg_speed_3['ALL_BYTES'],
  }

  return packer.make_can_msg('SPEED_3', 2, values)

def create_0x1a_message(packer, msg_0x1a: dict):
  """
  Forward 0x1A message by copying all bytes.

  Args:
    packer: CAN packer instance
    msg_0x1a: Dictionary containing 0x1A message values from car
  """
  values = {
    'ALL_BYTES': msg_0x1a['ALL_BYTES'],
  }
  return packer.make_can_msg('NEW_MSG_1A', 2, values)

def create_gear_position_message(packer, msg_gear_position: dict):
  """
  Forward GEAR_POSITION message by copying all bytes.

  Args:
    packer: CAN packer instance
    msg_gear_position: Dictionary containing GEAR_POSITION message values from car
  """
  values = dict(msg_gear_position)
  values['GEAR_POSITION'] = msg_gear_position['GEAR_POSITION'] # 3
  return packer.make_can_msg('GEAR_POSITION', 2, values)

def create_egsm_message(packer, msg_egsm: dict):
  """
  Forward EGSM message by copying all bytes.

  Args:
    packer: CAN packer instance
    msg_egsm: Dictionary containing EGSM message values from car
  """
  values = {
    'ALL_BYTES': msg_egsm['ALL_BYTES'],
  }
  return packer.make_can_msg('EGSM', 0, values)

def create_pscm_related_message(packer, lat_active: bool, stock_lca_engaged: bool, msg_pscm_related: dict, sig1_counter: int):
  # BO_ 23 PSCM_RELATED: 8 XXX
  # SG_ CHECKSUM : 7|8@0+ (1,0) [0|255] "" XXX
  # SG_ LCA_ENABLED_ECHO : 11|4@0+ (1,0) [0|15] "" XXX
  # SG_ SIG1_BYTE_1_HI_NIBBLE : 15|4@0+ (1,0) [0|15] "" XXX
  # SG_ SIG1_REPLICA_BYTE_2_LO_NIBLE : 19|4@0+ (1,0) [0|15] "" XXX
  # SG_ NEW_SIGNAL_2 : 23|4@0+ (1,0) [0|15] "" XXX
  # SG_ BYTE_3 : 31|8@0+ (1,0) [0|255] "" XXX
  # SG_ BYTE_4_5 : 39|16@0+ (1,0) [0|65535] "" XXX
  # SG_ BYTE_6 : 55|8@0+ (1,0) [0|255] "" XXX
  # SG_ BYTE_7 : 63|8@0+ (1,0) [0|255] "" XXX
  values = dict(msg_pscm_related)

  # Update SIG1 counter (same value in both locations for redundancy)
  values['SIG1_BYTE_1_HI_NIBBLE'] = sig1_counter
  values['SIG1_REPLICA_BYTE_2_LO_NIBLE'] = sig1_counter

  dat = packer.make_can_msg('PSCM_RELATED', 0, values)
  built_bytes = dat[1]  # dat is (addr, bytes, bus) tuple - extract bytes
  b1 = built_bytes[1]
  b2 = built_bytes[2]
  values['CHECKSUM_1'] = checksum_1_pscm_related_message(b1, b2)
  values['CHECKSUM_2'] = checksum_2_pscm_related_message(b2)
  #assert values['CHECKSUM_1'] == msg_pscm_related['CHECKSUM_1']
  #assert values['CHECKSUM_2'] == msg_pscm_related['CHECKSUM_2']
  if lat_active and not stock_lca_engaged:
    values['LCA_ENABLED_ECHO'] = 0
    b1 = packer.make_can_msg('PSCM_RELATED', 0, values)[1][1]
    values['CHECKSUM_1'] = checksum_1_pscm_related_message(b1, b2)
  return packer.make_can_msg('PSCM_RELATED', 0, values)

def create_lca_4_message(packer, lat_active: bool, msg_lca_4: dict, lca_4_steer: int,
                         overrides: dict | None = None):
  """
  Create LCA_4 (0x90) message to maintain Pilot Assist state when openpilot is active.

  Critical: LCA_ENABLE (byte 1 bits 0-1) must be held at 3 (both bits=1) when lat_active.
  When PA turns off, these bits start varying (become counters). We need to keep them
  stable at 3 to fool PSCM into thinking PA is still on, allowing LCA commands to be accepted.

  Based on analysis from route_analysis/pilot_assist_off/BASELINE_FILTERED_FINDINGS.md:
  - Message 0x090 byte 1 bits 0-1 are PA state signals
  - During PA ON: bits are stable at 3 (binary 11)
  - During PA OFF: bits start varying (counters)
  - PSCM uses this to determine whether to accept LCA steering commands

  Args:
    packer: CAN packer instance
    lat_active: Whether lateral control is active
    msg_lca_4: Dictionary containing LCA_4 message values from car
    lca_4_steer: Pre-computed signed angle with hysteresis applied
    overrides: Optional dict of signal overrides (keys are UPPERCASE DBC signal names)

  Returns:
    CAN message for LCA_4 on bus 2
  """
  if not lat_active:
    # When not active, just relay stock message unchanged
    return packer.make_can_msg('LCA_4', 2, msg_lca_4)

  # When lat_active, force LCA_ENABLE to 3 (PA ON state)
  values = {
    'BYTE_0': msg_lca_4['BYTE_0'],
    'LCA_ENABLE': 3,  # Force bits 0-1 to 1 (value=3 means both bits set)
    'BYTE_1_FLAGS': msg_lca_4['BYTE_1_FLAGS'],
    'BYTE_1_NIBBLE_HI': msg_lca_4['BYTE_1_NIBBLE_HI'],
    'BYTE_2_3': msg_lca_4['BYTE_2_3'],
    'YAW_RATE': msg_lca_4['YAW_RATE'],
    'BYTE_6': msg_lca_4['BYTE_6'],
    'BYTE_7_NIBBLE_LO': msg_lca_4['BYTE_7_NIBBLE_LO'],
    'BYTE_7_NIBBLE_HI': msg_lca_4['BYTE_7_NIBBLE_HI'],
  }

  # Apply any overrides from live testing config
  if overrides:
    for key, val in overrides.items():
      values[key] = val

  # TODO: Add checksum calculation when checksum function is implemented
  # If message has a checksum signal, it would be calculated here like:
  # values['CHECKSUM'] = checksum_lca_4_message(...)

  # TODO: Add checksum validation when not active (once checksum is known)
  # if not lat_active and 'CHECKSUM' in msg_lca_4:
  #   if values['CHECKSUM'] != msg_lca_4['CHECKSUM']:
  #     carlog.warning("[volvocan.py] LCA_4 CHECKSUM mismatch")

  return packer.make_can_msg('LCA_4', 2, values)

def create_lca_6_message(packer, lat_active: bool, msg_lca_6: dict, lca_6_steer: int,
                         overrides: dict | None = None):

  if not lat_active:
    # When not active, just relay stock message unchanged
    return packer.make_can_msg('LCA_6', 2, msg_lca_6)

  values = {
    'LCA_6_STEER': msg_lca_6['LCA_6_STEER'],
    'LCA_6_STEER_2': msg_lca_6['LCA_6_STEER_2'],
    'NEW_SIGNAL_1': msg_lca_6['NEW_SIGNAL_1'],
    'NEW_SIGNAL_2': msg_lca_6['NEW_SIGNAL_2'],
    'NEW_SIGNAL_3': msg_lca_6['NEW_SIGNAL_3'],
    'NEW_SIGNAL_4': msg_lca_6['NEW_SIGNAL_4'],
    'NEW_SIGNAL_5': msg_lca_6['NEW_SIGNAL_5'],
  }

  # Apply any overrides from live testing config
  if overrides:
    for key, val in overrides.items():
      values[key] = val

  return packer.make_can_msg('LCA_6', 2, values)

def create_lca_7_message(packer, lat_active: bool, msg_lca_7: dict, lca_7_steer: int, lca_7_delta_steer: int,
                         overrides: dict | None = None, steer_active: bool = False):

  if not lat_active:
    # When not active, just relay stock message unchanged
    return packer.make_can_msg('LCA_7', 2, msg_lca_7)

  values = {
    'LCA_7_STEER': msg_lca_7['LCA_7_STEER'],
    'LCA_7_DELTA_STEER': msg_lca_7['LCA_7_DELTA_STEER'],
    'NEW_SIGNAL_1': msg_lca_7['NEW_SIGNAL_1'],
    'NEW_SIGNAL_2': msg_lca_7['NEW_SIGNAL_2'],
    'NEW_SIGNAL_3': msg_lca_7['NEW_SIGNAL_3'],
    'NEW_SIGNAL_4': msg_lca_7['NEW_SIGNAL_4'],
  }

  # Apply any overrides from live testing config
  if overrides:
    for key, val in overrides.items():
      values[key] = val

  return packer.make_can_msg('LCA_7', 2, values)
