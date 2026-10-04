from opendbc.can import CANPacker
from opendbc.can.dbc import DBC


class PreAPStream:
  def __init__(self):
    self.packer = CANPacker("tesla_can")
    self.dbc = DBC("tesla_can")

  def frames(self, tick, *, lever=0, cruise=1, brake=1, gear=4, speed=80.0,
             doors=0, belt=1, eps_status=1, eps_error=0, hands=0, omit=None, wrong_bus=None):
    sources = (
      ("EPAS_sysStatus", {"EPAS_internalSAS": 0, "EPAS_torsionBarTorque": 0,
                         "EPAS_eacStatus": eps_status, "EPAS_eacErrorCode": eps_error, "EPAS_handsOnLevel": hands}),
      ("DI_torque1", {"DI_pedalPos": 0, "DI_torqueMotor": 0}),
      ("DI_torque2", {"DI_gear": gear, "DI_vehicleSpeed": speed}),
      ("BrakeMessage", {"driverBrakeStatus": brake}),
      ("DI_state", {"DI_cruiseState": cruise, "DI_speedUnits": 1, "DI_digitalSpeed": 80}),
      ("GTW_carState", {name: doors for name in ("DOOR_STATE_FL", "DOOR_STATE_FR", "DOOR_STATE_RL",
                        "DOOR_STATE_RR", "DOOR_STATE_FrontTrunk", "BOOT_STATE")}),
      ("STW_ACTN_RQ", {"SpdCtrlLvr_Stat": lever, "MC_STW_ACTN_RQ": tick % 16,
                       "CRC_STW_ACTN_RQ": 0, "VSL_Enbl_Rq": 1, "DTR_Dist_Rq": 132}),
      ("ESP_B", {"ESP_vehicleSpeed": speed}),
      ("STW_ANGLHP_STAT", {"StW_AnglHP_Spd": 0}),
      ("SDM1", {"SDM_bcklDrivStatus": belt}),
    )
    frames = []
    for name, fields in sources:
      assert fields.keys() <= self.dbc.name_to_msg[name].sigs.keys(), (name, fields)
      if name == omit:
        continue
      bus = 1 if name == wrong_bus else 0
      frame = self.packer.make_can_msg(name, bus, fields)
      if name == "STW_ACTN_RQ":
        data = bytearray(frame[1])
        crc = 0xFF
        for byte in data[:7]:
          crc ^= byte
          for _ in range(8):
            crc = ((crc << 1) ^ 0x1D) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
        data[7] = crc ^ 0xFF
        frame = frame[0], bytes(data), bus
      frames.append(frame)
    return frames
