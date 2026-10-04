from opendbc.car.tesla.values import CANBUS

_STW_CRC_POLY = 0x1D
_STW_DEFAULTS = {
  "VSL_Enbl_Rq": 1, "DTR_Dist_Rq": 0, "TurnIndLvr_Stat": 0,
  "HiBmLvr_Stat": 0, "WprWashSw_Psd": 0, "WprWash_R_Sw_Posn_V2": 0,
  "StW_Lvr_Stat": 0, "StW_Cond_Flt": 0, "StW_Cond_Psd": 0,
  "HrnSw_Psd": 0, "StW_Sw00_Psd": 0, "StW_Sw01_Psd": 0,
  "StW_Sw02_Psd": 0, "StW_Sw03_Psd": 0, "StW_Sw04_Psd": 0,
  "StW_Sw05_Psd": 0, "StW_Sw06_Psd": 0,
  "WprSw6Posn": 0,
}

def _crc8_stw(data: bytes) -> int:
  crc = 0xFF
  for b in data:
    crc ^= b
    for _ in range(8):
      crc = ((crc << 1) ^ _STW_CRC_POLY) & 0xFF if (crc & 0x80) else (crc << 1) & 0xFF
  return crc ^ 0xFF

class TeslaCANPreAP:
  def __init__(self, packer):
    self.packer = packer

  @staticmethod
  def checksum(msg_id: int, dat: bytes) -> int:
    return ((msg_id & 0xFF) + ((msg_id >> 8) & 0xFF) + sum(dat)) & 0xFF

  def create_steering_control(self, counter: int, angle: float, enabled: bool):
    values = {
      "DAS_steeringControlCounter": counter,
      "DAS_steeringAngleRequest": -angle,
      "DAS_steeringHapticRequest": 0,
      "DAS_steeringControlType": 1 if enabled else 0,
    }
    data = self.packer.make_can_msg("DAS_steeringControl", CANBUS.party, values)[1]
    values["DAS_steeringControlChecksum"] = self.checksum(0x488, data[:3])
    return self.packer.make_can_msg("DAS_steeringControl", CANBUS.party, values)

  def create_epas_control(self, counter: int, mode: int):
    values = {
      "EPB_epasEACAllow": mode,
      "EPB_epasControlCounter": counter,
      "EPB_epasControlChecksum": 0,
    }
    data = self.packer.make_can_msg("EPB_epasControl", CANBUS.party, values)[1]
    values["EPB_epasControlChecksum"] = self.checksum(0x214, data)
    return self.packer.make_can_msg("EPB_epasControl", CANBUS.party, values)

  def create_action_request(self, button_to_press: int, bus: int, counter: int, msg_stw=None):
    values = {"MC_STW_ACTN_RQ": counter, "CRC_STW_ACTN_RQ": 0, "SpdCtrlLvr_Stat": button_to_press}
    values.update(_STW_DEFAULTS if msg_stw is None else msg_stw)
    values["MC_STW_ACTN_RQ"] = counter
    values["CRC_STW_ACTN_RQ"] = 0
    values["SpdCtrlLvr_Stat"] = button_to_press
    values["VSL_Enbl_Rq"] = 1

    data = self.packer.make_can_msg("STW_ACTN_RQ", bus, values)[1]
    values["CRC_STW_ACTN_RQ"] = _crc8_stw(data[:7])
    return self.packer.make_can_msg("STW_ACTN_RQ", bus, values)
