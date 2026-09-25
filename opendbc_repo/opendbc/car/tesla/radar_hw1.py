from opendbc.can import CANParser
from opendbc.car import Bus, structs
from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.car.tesla.values import CANBUS, DBC

_BOSCH_RADAR_STATUS_MSG = 769
_BOSCH_RADAR_POINT_A_BASE = 784
_BOSCH_RADAR_POINT_B_BASE = 785
_BOSCH_RADAR_POINT_STRIDE = 3
_BOSCH_RADAR_POINTS = 32
_BOSCH_TRIGGER_MSG = _BOSCH_RADAR_POINT_B_BASE + ((_BOSCH_RADAR_POINTS - 1) * _BOSCH_RADAR_POINT_STRIDE)


class HW1RadarInterface(RadarInterfaceBase):
  def __init__(self, CP):
    super().__init__(CP)

    self.radar_off_can = CP.radarUnavailable or Bus.radar not in DBC[CP.carFingerprint]
    self.updated_messages: set[int] = set()
    self.track_id = 0
    self.radar_offset = 0.0

    if self.radar_off_can:
      self.rcp = None
    else:
      messages = [(_BOSCH_RADAR_STATUS_MSG, 8)]
      for i in range(_BOSCH_RADAR_POINTS):
        messages.append((_BOSCH_RADAR_POINT_A_BASE + (i * _BOSCH_RADAR_POINT_STRIDE), 8))
        messages.append((_BOSCH_RADAR_POINT_B_BASE + (i * _BOSCH_RADAR_POINT_STRIDE), 8))
      self.rcp = CANParser(DBC[CP.carFingerprint][Bus.radar], messages, CANBUS.vehicle)

    self.trigger_msg = _BOSCH_TRIGGER_MSG

  def update(self, can_strings):
    if self.radar_off_can or self.rcp is None:
      return super().update(None)

    vls = self.rcp.update(can_strings)
    self.updated_messages.update(vls)

    if self.trigger_msg not in self.updated_messages:
      return None

    ret = structs.RadarData()
    if not self.rcp.can_valid:
      ret.errors.canError = True

    radar_status = self.rcp.vl[_BOSCH_RADAR_STATUS_MSG]
    ret.errors.radarFault = bool(radar_status["RADC_HWFail"])
    ret.errors.radarUnavailableTemporary = False

    current_points: set[int] = set()
    for i in range(_BOSCH_RADAR_POINTS):
      msg_a_id = _BOSCH_RADAR_POINT_A_BASE + (i * _BOSCH_RADAR_POINT_STRIDE)
      msg_b_id = _BOSCH_RADAR_POINT_B_BASE + (i * _BOSCH_RADAR_POINT_STRIDE)

      msg_a = self.rcp.vl[msg_a_id]
      msg_b = self.rcp.vl[msg_b_id]
      if msg_a["Index"] != msg_b["Index2"]:
        continue

      if not msg_a["Tracked"] or msg_a["LongDist"] <= 0.0 or msg_a["LongDist"] > 250.0 or msg_a["ProbExist"] < 50.0:
        self.pts.pop(i, None)
        continue

      current_points.add(i)
      if i not in self.pts:
        self.pts[i] = structs.RadarData.RadarPoint()
        self.pts[i].trackId = self.track_id
        self.track_id += 1

      point = self.pts[i]
      point.dRel = msg_a["LongDist"]
      point.yRel = msg_a["LatDist"] + self.radar_offset
      point.vRel = msg_a["LongSpeed"]

    for point_id in list(self.pts.keys()):
      if point_id not in current_points:
        del self.pts[point_id]

    ret.points = list(self.pts.values())
    self.updated_messages.clear()
    return ret
