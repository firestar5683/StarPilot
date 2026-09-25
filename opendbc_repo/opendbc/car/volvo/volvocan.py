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
