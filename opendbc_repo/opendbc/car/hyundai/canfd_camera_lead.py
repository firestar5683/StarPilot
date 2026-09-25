"""Optional isolated CANFD camera lead decoding, outside required controls health."""
import math
import time
from dataclasses import dataclass

from opendbc.can.parser import CANParser
from opendbc.car import Bus
from opendbc.car.hyundai.hyundaicanfd import hkg_can_fd_checksum
from opendbc.car.hyundai.values import DBC

CAMERA_ADDRESS = 0x1B5
CAMERA_MAX_AGE_NS = 300_000_000


@dataclass(frozen=True)
class CameraLeadObservation:
  producer_boot_ns: int
  visible: bool
  distance_m: float
  relative_speed_mps: float


class CANFDCameraLead:
  def __init__(self, cp, bus):
    self.bus = bus
    self.parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [('FR_CMR_03_50ms', math.nan)], self.bus)
    self.observation = None
    self.last_packet_ns = 0
    self.last_counter = None

  def update(self, can_packets):
    boot_clock = getattr(time, "CLOCK_BOOTTIME", None)
    if boot_clock is None:
      return
    try:
      now_boot_ns = time.clock_gettime_ns(boot_clock)
    except OSError:
      return
    for stamp, frames in can_packets:
      if type(stamp) is not int or not self.last_packet_ns < stamp <= now_boot_ns:
        continue
      for address, data, bus in frames:
        if address != CAMERA_ADDRESS or bus != self.bus or len(data) != 32 or stamp <= self.last_packet_ns:
          continue
        self.last_packet_ns = stamp
        # Semantic camera field names do not opt the shared parser into integrity
        # checks. Keep validation local so existing CCNC controls health is unchanged.
        if int.from_bytes(data[:2], 'little') != hkg_can_fd_checksum(CAMERA_ADDRESS, None, bytearray(data)):
          continue
        counter = data[2]
        advancing = self.last_counter is None or counter == (self.last_counter + 1) % 256
        self.last_counter = counter
        if not advancing:
          continue
        previous = self.parser.ts_nanos['FR_CMR_03_50ms']['FR_CMR_Crc3Val']
        accepted = self.parser.update([(stamp, [(address, data, bus)])])
        if CAMERA_ADDRESS not in accepted or stamp <= previous:
          continue
        if self.observation is not None and stamp <= self.observation.producer_boot_ns:
          continue
        values = self.parser.vl['FR_CMR_03_50ms']
        distance = float(values['Longitudinal_Distance'])
        relative = float(values['Relative_Velocity'])
        if not math.isfinite(distance) or not math.isfinite(relative):
          continue
        visible = distance > .1
        self.observation = CameraLeadObservation(stamp, visible, distance if visible else 0., relative if visible else 0.)

  def current(self, now_boot_ns, floor_boot_ns=0):
    observation = self.observation
    if (type(now_boot_ns) is not int or type(floor_boot_ns) is not int or observation is None or
        not max(0, floor_boot_ns) < observation.producer_boot_ns <= now_boot_ns or
        now_boot_ns - observation.producer_boot_ns > CAMERA_MAX_AGE_NS):
      return None
    return observation
