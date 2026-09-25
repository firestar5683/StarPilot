import math

from opendbc.can import CANParser
from opendbc.car import Bus, structs
from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags, HYUNDAI_MRR35_RADAR_DBC, HYUNDAI_MRR30_RADAR_DBC, HYUNDAI_GV70_RADAR_DBC, HYUNDAI_G90_RADAR_DBC

RADAR_START_ADDR = 0x500
RADAR_MSG_COUNT = 32
G90_RADAR_MSG_COUNT = 64
G90_RADAR_CYCLE_NS = 20_000_000
MRREVO14F_RADAR_START_ADDR = 0x602
MRREVO14F_RADAR_MSG_COUNT = 16
MRREVO14F_RADAR_CYCLE_NS = 20_000_000  # track messages are published at 50 Hz
MRR30_RADAR_START_ADDR = 0x210
MRR30_RADAR_MSG_COUNT = 16
MRR30_RADAR_CYCLE_NS = 20_000_000
GV70_RADAR_CYCLE_NS = 50_000_000
MRR35_RADAR_START_ADDR = 0x3A5
MRR35_RADAR_MSG_COUNT = 32
MRR35_RADAR_CYCLE_NS = 50_000_000  # 20 Hz


def radar_bus(CP) -> int:
  # Frozen Ioniq 6 camera-SCC wiring exposes the MRR35 object bank on bus 1;
  # its LKA/HDA-II wiring and the other MRR35 cars expose it on bus 0.
  if CP.carFingerprint == CAR.HYUNDAI_IONIQ_6 and CP.flags & HyundaiFlags.CANFD_CAMERA_SCC:
    return 1
  return 0

# POC for parsing corner radars: https://github.com/commaai/openpilot/pull/24221/


def get_radar_can_parser(CP):
  if Bus.radar not in DBC[CP.carFingerprint]:
    return None

  start, count = radar_message_range(CP)
  mrr35 = DBC[CP.carFingerprint].get(Bus.radar) == HYUNDAI_MRR35_RADAR_DBC
  g90 = DBC[CP.carFingerprint].get(Bus.radar) == HYUNDAI_G90_RADAR_DBC
  gv70 = DBC[CP.carFingerprint].get(Bus.radar) == HYUNDAI_GV70_RADAR_DBC
  messages = [(f"RADAR_TRACK_{addr:x}",
               20 if mrr35 and addr == start + count - 1 else
               float("nan") if mrr35 or g90 and addr >= start + RADAR_MSG_COUNT else 20 if gv70 else 50) for addr in range(start, start + count)]
  mrr30 = DBC[CP.carFingerprint].get(Bus.radar) == HYUNDAI_MRR30_RADAR_DBC
  return CANParser(DBC[CP.carFingerprint][Bus.radar], messages, radar_bus(CP) if mrr35 or mrr30 or gv70 else 1)


def radar_message_range(CP) -> tuple[int, int]:
  if DBC[CP.carFingerprint].get(Bus.radar) == HYUNDAI_G90_RADAR_DBC:
    return RADAR_START_ADDR, G90_RADAR_MSG_COUNT
  if DBC[CP.carFingerprint].get(Bus.radar) in (HYUNDAI_MRR30_RADAR_DBC, HYUNDAI_GV70_RADAR_DBC):
    return MRR30_RADAR_START_ADDR, MRR30_RADAR_MSG_COUNT
  if DBC[CP.carFingerprint].get(Bus.radar) == HYUNDAI_MRR35_RADAR_DBC:
    return MRR35_RADAR_START_ADDR, MRR35_RADAR_MSG_COUNT
  if DBC[CP.carFingerprint].get(Bus.radar) == "hyundai_mrrevo14f_radar_generated":
    return MRREVO14F_RADAR_START_ADDR, MRREVO14F_RADAR_MSG_COUNT
  return RADAR_START_ADDR, RADAR_MSG_COUNT


class RadarInterface(RadarInterfaceBase):
  def __init__(self, CP):
    super().__init__(CP)
    self.updated_messages = set()
    self.start_addr, self.msg_count = radar_message_range(CP)
    self.g90 = DBC[CP.carFingerprint].get(Bus.radar) == HYUNDAI_G90_RADAR_DBC
    self.mrrevo14f = self.start_addr == MRREVO14F_RADAR_START_ADDR
    self.mrr35 = self.start_addr == MRR35_RADAR_START_ADDR
    self.gv70 = DBC[CP.carFingerprint].get(Bus.radar) == HYUNDAI_GV70_RADAR_DBC
    self.mrr30 = self.start_addr == MRR30_RADAR_START_ADDR and not self.gv70
    self.last_mrr35_trigger_ns = 0
    self.trigger_msg = self.start_addr + (RADAR_MSG_COUNT if self.g90 else self.msg_count) - 1

    self.radar_off_can = CP.radarUnavailable
    self.rcp = get_radar_can_parser(CP)

  def update(self, can_strings):
    if self.radar_off_can or (self.rcp is None):
      return super().update(None)

    if (self.g90 or self.mrr30 or self.gv70 or self.mrr35 and self.CP.carFingerprint == CAR.HYUNDAI_IONIQ_6) and can_strings:
      expected_length = 8 if self.g90 else 32 if self.mrr30 or self.gv70 else 24
      entries = [can_strings] if not isinstance(can_strings[0], list | tuple) else can_strings
      can_strings = [(timestamp, [(addr, data, bus) for addr, data, bus in frames
                                  if not (bus == self.rcp.bus and self.start_addr <= addr < self.start_addr + self.msg_count and len(data) != expected_length)])
                     for timestamp, frames in entries]

    vls = self.rcp.update(can_strings)
    self.updated_messages.update(vls)

    if self.trigger_msg not in self.updated_messages:
      return None

    if self.mrr35:
      trigger_ns = self.rcp.ts_nanos[self.trigger_msg]["LONG_DIST"]
      if trigger_ns <= self.last_mrr35_trigger_ns:
        self.updated_messages.clear()
        return None
      self.last_mrr35_trigger_ns = trigger_ns

    rr = self._update(self.updated_messages)
    self.updated_messages.clear()

    return rr

  def _update(self, updated_messages):
    ret = structs.RadarData()
    if self.rcp is None:
      return ret

    if not self.rcp.can_valid:
      ret.errors.canError = True

    for addr in range(self.start_addr, self.start_addr + self.msg_count):
      msg = self.rcp.vl[f"RADAR_TRACK_{addr:x}"]

      if self.mrr30 or self.gv70:
        trigger_time = self.rcp.ts_nanos[self.trigger_msg]["1_LONG_DIST"]
        source_time = self.rcp.ts_nanos[addr]["1_LONG_DIST"]
        cycle_ns = GV70_RADAR_CYCLE_NS if self.gv70 else MRR30_RADAR_CYCLE_NS
        fresh = addr in updated_messages and 0 <= trigger_time - source_time <= cycle_ns
        for index in (1, 2):
          track_key = addr * 2 + index - 1
          if fresh and msg[f"{index}_STATE"] in (3, 4):
            point = self.pts.get(track_key)
            if point is None:
              point = structs.RadarData.RadarPoint()
              point.trackId = self.track_id
              self.track_id += 1
              self.pts[track_key] = point
            point.dRel = msg[f"{index}_LONG_DIST"]
            point.yRel = msg[f"{index}_LAT_DIST"]
            point.vRel = msg[f"{index}_REL_SPEED"]
          elif track_key in self.pts:
            del self.pts[track_key]
        continue

      if self.mrr35:
        trigger_ns = self.last_mrr35_trigger_ns
        source_ns = self.rcp.ts_nanos[addr]["LONG_DIST"]
        fresh = addr in updated_messages and 0 <= trigger_ns - source_ns <= MRR35_RADAR_CYCLE_NS
        if fresh and msg["STATE"] in (3, 4):
          point = self.pts.get(addr)
          if point is None:
            point = structs.RadarData.RadarPoint()
            point.trackId = self.track_id
            self.track_id += 1
            self.pts[addr] = point
          point.dRel = msg["LONG_DIST"]
          point.yRel = msg["LAT_DIST"]
          point.vRel = msg["REL_SPEED"]
        elif addr in self.pts:
          del self.pts[addr]
        continue

      if self.mrrevo14f:
        trigger_time = self.rcp.ts_nanos[self.trigger_msg]["1_DISTANCE"]
        source_time = self.rcp.ts_nanos[addr]["1_DISTANCE"]
        fresh = addr in updated_messages and 0 <= trigger_time - source_time <= MRREVO14F_RADAR_CYCLE_NS
        for index in (1, 2):
          track_key = addr * 2 + index - 1
          valid = fresh and msg[f"{index}_DISTANCE"] != 255.75
          if valid:
            point = self.pts.get(track_key)
            if point is None:
              point = structs.RadarData.RadarPoint()
              point.trackId = self.track_id
              self.track_id += 1
              self.pts[track_key] = point
            point.dRel = msg[f"{index}_DISTANCE"]
            point.yRel = msg[f"{index}_LATERAL"]
            point.vRel = msg[f"{index}_SPEED"]
          elif track_key in self.pts:
            del self.pts[track_key]
        continue

      if self.g90 and addr >= self.start_addr + RADAR_MSG_COUNT:
        trigger_time = self.rcp.ts_nanos[self.trigger_msg]["LONG_DIST"]
        source_time = self.rcp.ts_nanos[addr]["LONG_DIST"]
        if addr not in updated_messages or not 0 <= trigger_time - source_time <= G90_RADAR_CYCLE_NS:
          self.pts.pop(addr, None)
          continue

      if addr not in self.pts:
        self.pts[addr] = structs.RadarData.RadarPoint()
        self.pts[addr].trackId = self.track_id
        self.track_id += 1

      valid = msg['STATE'] in (3, 4)
      if valid:
        azimuth = math.radians(msg['AZIMUTH'])
        self.pts[addr].dRel = math.cos(azimuth) * msg['LONG_DIST']
        self.pts[addr].yRel = 0.5 * -math.sin(azimuth) * msg['LONG_DIST']
        self.pts[addr].vRel = msg['REL_SPEED']

      else:
        del self.pts[addr]

    ret.points = list(self.pts.values())
    return ret
