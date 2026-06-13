import math
from dataclasses import dataclass, replace

from opendbc.can import CANParser
from opendbc.can.dbc import DBC as DBCReader
from opendbc.can.parser import get_raw_value
from opendbc.car import Bus, structs
from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags, HYUNDAI_MANDO_FRONT_RADAR_DBC, HYUNDAI_MRREVO14F_RADAR_DBC, \
                                       HYUNDAI_MRR30_RADAR_DBC, HYUNDAI_MRR35_RADAR_DBC
from openpilot.common.swaglog import cloudlog

RADAR_START_ADDR = 0x500
RADAR_MSG_COUNT = 32
G90_RADAR_MSG_COUNT = 64
MRREVO14F_RADAR_START_ADDR = 0x602
MRREVO14F_RADAR_MSG_COUNT = 16
MRR30_RADAR_START_ADDR = 0x210
MRR30_RADAR_MSG_COUNT = 16
MRR35_RADAR_START_ADDR = 0x3A5
MRR35_RADAR_MSG_COUNT = 32


@dataclass(frozen=True)
class RadarTrackConfig:
  start_addr: int
  msg_count: int
  radar_type: str
  bus: int = 1
  frequency: int = 50
  parser_msg_count: int | None = None
  expected_length: int | None = None

  @property
  def can_parser_msg_count(self) -> int:
    return self.parser_msg_count if self.parser_msg_count is not None else self.msg_count


RADAR_TRACK_CONFIGS = {
  HYUNDAI_MANDO_FRONT_RADAR_DBC: RadarTrackConfig(RADAR_START_ADDR, RADAR_MSG_COUNT, "mando"),
  HYUNDAI_MRREVO14F_RADAR_DBC: RadarTrackConfig(MRREVO14F_RADAR_START_ADDR, MRREVO14F_RADAR_MSG_COUNT, "mrrevo14f"),
  HYUNDAI_MRR30_RADAR_DBC: RadarTrackConfig(MRR30_RADAR_START_ADDR, MRR30_RADAR_MSG_COUNT, "mrr30", bus=0, expected_length=32),
  HYUNDAI_MRR35_RADAR_DBC: RadarTrackConfig(MRR35_RADAR_START_ADDR, MRR35_RADAR_MSG_COUNT, "mrr35", bus=0, frequency=20, expected_length=24),
}

# POC for parsing corner radars: https://github.com/commaai/openpilot/pull/24221/


def get_radar_track_config(car_fingerprint, flags: int = 0) -> RadarTrackConfig | None:
  radar_dbc = DBC[car_fingerprint].get(Bus.radar)
  if car_fingerprint == CAR.GENESIS_G90 and radar_dbc == HYUNDAI_MANDO_FRONT_RADAR_DBC:
    return RadarTrackConfig(RADAR_START_ADDR, G90_RADAR_MSG_COUNT, "mando", parser_msg_count=RADAR_MSG_COUNT)

  radar_config = RADAR_TRACK_CONFIGS.get(radar_dbc)
  if radar_config is None:
    return None

  if car_fingerprint == CAR.HYUNDAI_IONIQ_6 and flags & HyundaiFlags.CANFD_CAMERA_SCC:
    return replace(radar_config, bus=1)

  return radar_config


def radar_tracks_available(radar_config: RadarTrackConfig | None, fingerprint) -> bool:
  if radar_config is None:
    return False

  msg_len = fingerprint[radar_config.bus].get(radar_config.start_addr)
  if msg_len is None:
    return False

  return radar_config.expected_length is None or msg_len == radar_config.expected_length


def get_radar_can_parser(CP, radar_config):
  if radar_config is None:
    return None

  messages = [(f"RADAR_TRACK_{addr:x}", radar_config.frequency)
              for addr in range(radar_config.start_addr, radar_config.start_addr + radar_config.can_parser_msg_count)]
  return CANParser(DBC[CP.carFingerprint][Bus.radar], messages, radar_config.bus)


class RadarInterface(RadarInterfaceBase):
  def __init__(self, CP):
    super().__init__(CP)
    self.radar_config = get_radar_track_config(CP.carFingerprint, CP.flags)
    self.updated_messages = set()
    self.trigger_msg = (self.radar_config.start_addr + self.radar_config.can_parser_msg_count - 1
                        if self.radar_config is not None else RADAR_START_ADDR)
    self.track_id = 0
    self.g90_extended_mando = (CP.carFingerprint == CAR.GENESIS_G90 and self.radar_config is not None and
                               self.radar_config.msg_count > self.radar_config.can_parser_msg_count)
    self.g90_mando_signals = []
    if self.g90_extended_mando:
      radar_dbc = DBCReader(DBC[CP.carFingerprint][Bus.radar])
      self.g90_mando_signals = list(radar_dbc.addr_to_msg[RADAR_START_ADDR].sigs.values())

    self.radar_off_can = CP.radarUnavailable
    # Probe whether radar tracks still exist on the Ioniq 6 while OP long is active,
    # without changing planner behavior yet.
    self.ioniq_6_radar_probe = CP.carFingerprint == CAR.HYUNDAI_IONIQ_6 and CP.openpilotLongitudinalControl and self.radar_off_can
    self.ioniq_6_radar_probe_logged = False
    self.ioniq_6_radar_probe_updates = 0
    self.rcp = get_radar_can_parser(CP, self.radar_config)

    # Precompute (addr, "RADAR_TRACK_xxx") pairs once. _update runs on the
    # CAN-driven card loop (core 4, shared with controlsd/selfdrived), so avoid
    # rebuilding 32 f-strings per radar frame.
    self.track_addrs: list[tuple[int, str]] = []
    if self.radar_config is not None:
      self.track_addrs = [(addr, f"RADAR_TRACK_{addr:x}")
                          for addr in range(self.radar_config.start_addr,
                                            self.radar_config.start_addr + self.radar_config.can_parser_msg_count)]

  def update(self, can_strings):
    if self.ioniq_6_radar_probe and self.rcp is not None and not self.ioniq_6_radar_probe_logged:
      vls = self.rcp.update(can_strings)
      self.updated_messages.update(vls)
      self.ioniq_6_radar_probe_updates += 1

      if self.trigger_msg in self.updated_messages:
        rr = self._update(self.updated_messages)
        cloudlog.warning(f"Ioniq 6 radar probe: saw {len(rr.points)} radar tracks with radarUnavailable forced on")
        self.updated_messages.clear()
        self.ioniq_6_radar_probe_logged = True
      elif self.ioniq_6_radar_probe_updates >= 500:
        cloudlog.warning("Ioniq 6 radar probe: no radar track frames observed after startup")
        self.ioniq_6_radar_probe_logged = True
        self.updated_messages.clear()

    if self.radar_off_can or (self.rcp is None):
      return super().update(None)

    vls = self.rcp.update(can_strings)
    self.updated_messages.update(vls)
    if self.g90_extended_mando:
      self._update_g90_extended_mando_tracks(can_strings)

    if self.trigger_msg not in self.updated_messages:
      return None

    rr = self._update(self.updated_messages)
    self.updated_messages.clear()

    return rr

  def _decode_g90_mando_values(self, dat: bytes):
    vals = {}
    for sig in self.g90_mando_signals:
      raw = get_raw_value(dat, sig)
      if sig.is_signed:
        raw -= ((raw >> (sig.size - 1)) & 1) * (1 << sig.size)
      vals[sig.name] = raw * sig.factor + sig.offset
    return vals

  def _update_g90_extended_mando_tracks(self, can_strings):
    if self.radar_config is None:
      return

    start_addr = self.radar_config.start_addr + self.radar_config.can_parser_msg_count
    end_addr = self.radar_config.start_addr + self.radar_config.msg_count

    for _, frames in can_strings:
      for address, dat, src in frames:
        if src != self.radar_config.bus or not (start_addr <= address < end_addr) or len(dat) < 8:
          continue

        self.updated_messages.add(address)
        msg = self._decode_g90_mando_values(dat)
        valid = msg["STATE"] in (3, 4)
        if valid:
          if address not in self.pts:
            self.pts[address] = structs.RadarData.RadarPoint()
            self.pts[address].trackId = self.track_id
            self.track_id += 1

          azimuth = math.radians(msg["AZIMUTH"])
          self.pts[address].measured = True
          self.pts[address].dRel = math.cos(azimuth) * msg["LONG_DIST"]
          self.pts[address].yRel = 0.5 * -math.sin(azimuth) * msg["LONG_DIST"]
          self.pts[address].vRel = msg["REL_SPEED"]
          self.pts[address].aRel = msg["REL_ACCEL"]
          self.pts[address].yvRel = float("nan")
        elif address in self.pts:
          del self.pts[address]

  def _update(self, updated_messages):
    ret = structs.RadarData()
    if self.rcp is None:
      return ret

    if not self.rcp.can_valid:
      ret.errors.canError = True

    if self.radar_config is None:
      return ret

    radar_type = self.radar_config.radar_type
    vl = self.rcp.vl

    for addr, track_name in self.track_addrs:
      msg = vl[track_name]

      if radar_type == "mrr30":
        for i in ("1", "2"):
          track_key = addr * 2 + int(i) - 1
          if track_key not in self.pts:
            self.pts[track_key] = structs.RadarData.RadarPoint()
            self.pts[track_key].trackId = self.track_id
            self.track_id += 1

          valid = msg[f"{i}_STATE"] in (3, 4)
          if valid:
            pt = self.pts[track_key]
            pt.measured = True
            pt.dRel = msg[f"{i}_LONG_DIST"]
            pt.yRel = msg[f"{i}_LAT_DIST"]
            pt.vRel = msg[f"{i}_REL_SPEED"]
            pt.aRel = float("nan")
            pt.yvRel = float("nan")
          else:
            del self.pts[track_key]
        continue

      if radar_type == "mrrevo14f":
        for i in ("1", "2"):
          track_key = addr * 2 + int(i) - 1
          valid = msg[f"{i}_DISTANCE"] != 255.75
          if valid:
            pt = self.pts.get(track_key)
            if pt is None:
              pt = structs.RadarData.RadarPoint()
              pt.trackId = self.track_id
              self.track_id += 1
              self.pts[track_key] = pt
            pt.measured = True
            pt.dRel = msg[f"{i}_DISTANCE"]
            pt.yRel = msg[f"{i}_LATERAL"]
            pt.vRel = msg[f"{i}_SPEED"]
            pt.aRel = float("nan")
            pt.yvRel = float("nan")
          elif track_key in self.pts:
            del self.pts[track_key]
        continue

      if radar_type == "mrr35":
        # Most of the 32 channels are empty each frame. Only allocate a point
        # when the channel is valid; drop it otherwise. Avoids the per-frame
        # alloc-then-delete churn on the ~27 idle channels.
        if msg["STATE"] in (3, 4):
          pt = self.pts.get(addr)
          if pt is None:
            pt = structs.RadarData.RadarPoint()
            pt.trackId = self.track_id
            self.track_id += 1
            self.pts[addr] = pt
          pt.measured = True
          pt.dRel = msg["LONG_DIST"]
          pt.yRel = msg["LAT_DIST"]
          pt.vRel = msg["REL_SPEED"]
          pt.aRel = msg["REL_ACCEL"]
          pt.yvRel = float("nan")
        elif addr in self.pts:
          del self.pts[addr]
        continue

      if addr not in self.pts:
        self.pts[addr] = structs.RadarData.RadarPoint()
        self.pts[addr].trackId = self.track_id
        self.track_id += 1

      valid = msg['STATE'] in (3, 4)
      if valid:
        azimuth = math.radians(msg['AZIMUTH'])
        self.pts[addr].measured = True
        self.pts[addr].dRel = math.cos(azimuth) * msg['LONG_DIST']
        self.pts[addr].yRel = 0.5 * -math.sin(azimuth) * msg['LONG_DIST']
        self.pts[addr].vRel = msg['REL_SPEED']
        self.pts[addr].aRel = msg['REL_ACCEL']
        self.pts[addr].yvRel = float('nan')

      else:
        del self.pts[addr]

    ret.points = list(self.pts.values())
    return ret
