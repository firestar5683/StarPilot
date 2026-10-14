"""Continental ARS510 ACC-target radar, one point per radar cycle.

Adapted from ds-sebastian/ars510-radar at fb5b29c2b5999f34afeb6f7ac494a73949d66c67.
Copyright (c) 2026 ARS510 radar contributors. MIT license; see THIRD_PARTY_NOTICES.md.
"""

from math import nan

from opendbc.can import CANParser
from opendbc.car.structs import RadarData
from opendbc.car.interfaces import RadarInterfaceBase

RADAR_DBC = "toyota_tss2_ars510"
TARGET_ADDRS = {0x235, 0x237, 0x239}


class RadarInterface(RadarInterfaceBase):
  def __init__(self, CP):
    super().__init__(CP)
    self.rcp = CANParser(RADAR_DBC, [("ACC_TARGET_1", 50), ("ACC_TARGET_2", 50), ("ACC_TARGET_3", 50)], 1)
    self.trigger_msg = 0x237
    self.updated_messages = set()
    self.cycle = None
    self.last_record_t = None

  def update(self, can_strings):
    self.frame += 1
    packets = [(nanos, [(addr, dat, src) for addr, dat, src in frames if addr not in TARGET_ADDRS or len(dat) == 8]) for nanos, frames in can_strings]
    self.updated_messages.update(self.rcp.update(packets))
    t = can_strings[-1][0] * 1e-9 if can_strings else None
    cycle = self.rcp.vl["ACC_TARGET_3"]["TIMESTAMP"]
    clock_seen = bool(self.rcp.ts_nanos["ACC_TARGET_3"]["TIMESTAMP"])
    if self.trigger_msg not in self.updated_messages or not clock_seen or cycle == self.cycle:
      # Keep card publishing through startup or a stopped cycle clock, without erasing healthy tracks between scans.
      if t is None or self.frame % 5 != 0 or (self.last_record_t is not None and t - self.last_record_t <= 0.5):
        return None
      ret = RadarData()
      ret.errors.radarUnavailableTemporary = self.last_record_t is not None
      return ret

    self.cycle = cycle
    self.updated_messages.clear()
    self.last_record_t = t
    ret = RadarData()
    if not self.rcp.can_valid:
      ret.errors.canError = True
      return ret

    target, position = self.rcp.vl["ACC_TARGET_1"], self.rcp.vl["ACC_TARGET_2"]
    if target["STATE"] == 5 and position["PRESENT"]:
      pt = RadarData.RadarPoint()
      pt.trackId = int(target["TARGET_ID"])
      pt.dRel = position["LONG_DIST"]
      pt.yRel = position["LAT_DIST"]
      pt.vRel = target["REL_SPEED"]
      pt.deprecated.aRel = pt.deprecated.yvRel = nan
      pt.deprecated.measured = True
      ret.points = [pt]
    return ret
