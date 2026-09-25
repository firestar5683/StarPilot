"""Optional primary-lead transport with independent current-drive context."""
from dataclasses import dataclass
import math
import os

import openpilot.cereal.messaging as messaging
from openpilot.starpilot.longitudinal.toyota_output_policy import clock_pair_ns, CLOCK_PAIR_MAX_SKEW_NS


@dataclass(frozen=True)
class PrimaryLead:
  producer_ns: int
  receipt_ns: int
  present: bool
  distance: float
  relative_speed: float


@dataclass(frozen=True)
class LeadContext:
  drive_id: int
  mono_now_ns: int
  boot_now_ns: int
  offset_ns: int
  epoch_floor_ns: int
  radar: PrimaryLead | None

  @property
  def boot_floor_ns(self):
    return max(self.epoch_floor_ns, self.drive_id) + self.offset_ns


class RadarLeadContext:
  def __init__(self, *, require_radar):
    self.sm = messaging.SubMaster(['radarState', 'deviceState', 'carState'])
    self.require_radar = require_radar
    self.offset_ns = None
    self.floor_ns = 0
    self.revoked = True
    self.drive_id = None

  def _unavailable(self, now_ns=0):
    # Preserve one barrier per lost accepted epoch; repeated100Hz polls must
    # not outrun independent lower-frequency producers.
    if not self.revoked:
      self.floor_ns = max(self.floor_ns, now_ns)
      self.revoked = True
    return None

  def _primary(self, now_ns):
    try:
      sm = self.sm
      if not (sm.seen['radarState'] and sm.alive['radarState'] and sm.valid['radarState']):
        return None
      stamp = int(sm.logMonoTime['radarState'])
      receipt = int(sm.recv_time['radarState'] * 1e9)
      if not max(self.floor_ns, self.drive_id) < stamp <= receipt <= now_ns or now_ns-stamp > 150_000_000:
        return None
      errors = sm['radarState'].radarErrors
      if errors.canError or errors.radarFault or errors.wrongConfig or errors.radarUnavailableTemporary:
        return None
      lead = sm['radarState'].leadOne
      if type(lead.present) is not bool:
        return None
      distance, relative = (float(lead.dRel), float(lead.vRel)) if lead.present else (0., 0.)
      if not math.isfinite(distance) or not math.isfinite(relative):
        return None
      return PrimaryLead(stamp, receipt, lead.present, max(distance, 0.), relative)
    except (OSError, AttributeError, KeyError, TypeError, ValueError, OverflowError):
      return None

  def update(self):
    now_ns = 0
    try:
      self.sm.update(0)
      if os.getenv('REPLAY') == '1':
        self.offset_ns = None
        return self._unavailable()
      pair = clock_pair_ns()
      if pair is None:
        self.offset_ns = None
        return self._unavailable()
      now_ns, boot_ns = pair
      offset = boot_ns-now_ns
      if self.offset_ns is None or abs(offset-self.offset_ns) > CLOCK_PAIR_MAX_SKEW_NS:
        self.offset_ns = offset
        self.floor_ns = now_ns
        self.revoked = True
        return None
      sm = self.sm
      services = ('radarState', 'deviceState', 'carState') if self.require_radar else ('deviceState', 'carState')
      if not all(sm.seen[name] and sm.alive[name] and sm.valid[name] for name in services):
        return self._unavailable(now_ns)
      stamps = {name: int(sm.logMonoTime[name]) for name in services}
      receipts = {name: int(sm.recv_time[name] * 1e9) for name in stamps}
      drive_id = int(sm['deviceState'].startedMonoTime)
      if not sm['deviceState'].started or not 0 < drive_id < stamps['deviceState']:
        return self._unavailable(now_ns)
      if self.drive_id is not None and drive_id != self.drive_id:
        self.floor_ns = now_ns
        self.revoked = True
      self.drive_id = drive_id
      for name, stamp in stamps.items():
        age = 2_000_000_000 if name == 'deviceState' else 150_000_000
        if not max(self.floor_ns, drive_id) < stamp <= receipts[name] <= now_ns or now_ns-stamp > age:
          return self._unavailable(now_ns)
      car = sm['carState']
      if not car.canValid or car.canTimeout:
        return self._unavailable(now_ns)
      primary = self._primary(now_ns)
      if self.require_radar and primary is None:
        return self._unavailable(now_ns)
      self.revoked = False
      return LeadContext(drive_id, now_ns, boot_ns, offset, self.floor_ns, primary)
    except (OSError, AttributeError, KeyError, TypeError, ValueError, OverflowError):
      if not now_ns:
        self.offset_ns = None
      return self._unavailable(now_ns)
