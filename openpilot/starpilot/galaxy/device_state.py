"""Lightweight vehicle status for Galaxy's header; never grants control authority."""

import threading
import time

from openpilot.starpilot.parked_evidence import RESUME_SKEW_NS, host_parked


TTL_NS = 3_000_000_000


class DeviceStateSource:
  def __init__(self, messages=None, *, mono=time.monotonic_ns,
               boot=lambda: time.clock_gettime_ns(getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC))):
    self.messages, self.mono, self.boot = messages, mono, boot
    self.lock = threading.Lock()
    self.floor = getattr(messages, "after_mono_ns", mono())
    self.offset = None
    self.device_offset = None
    self.closed = False

  def sample(self):
    unknown = {'state': None, 'maxAgeMs': 0}
    with self.lock:
      if self.closed:
        return unknown
      if host_parked():
        return {'state': 'parked', 'maxAgeMs': TTL_NS // 1_000_000}
      try:
        if self.messages is None:
          from openpilot.cereal import messaging
          self.messages = messaging.SubMaster(['deviceState', 'pandaStates'])
        snapshot = getattr(self.messages, 'snapshot', None)
        if callable(snapshot):
          sm = snapshot()
          if sm is None:
            return unknown
          self.floor = max(self.floor, sm.after_mono_ns)
          self.device_offset = sm.device_offset_ns
        else:
          sm = self.messages
          sm.update(0)
        before, boot, now = self.mono(), self.boot(), self.mono()
        if not 0 <= now - before <= RESUME_SKEW_NS:
          return unknown
        offset = boot - (before + now) // 2
        if self.offset is not None and abs(offset - self.offset) > RESUME_SKEW_NS:
          self.floor, self.device_offset = now, None
        self.offset = offset
        if sm.updated['deviceState'] and int(sm.logMonoTime['deviceState']) > self.floor:
          self.device_offset = offset
        if self.device_offset is None or not all(sm.seen[key] and sm.valid[key] for key in ('deviceState', 'pandaStates')):
          return unknown
        stamp = int(sm.logMonoTime['deviceState'])
        if stamp <= self.floor:
          return unknown
        ages = (now - stamp, boot - (stamp + self.device_offset), boot - int(sm.logMonoTime['pandaStates']),
                now - int(sm.recv_time['deviceState'] * 1e9), now - int(sm.recv_time['pandaStates'] * 1e9))
        if not all(0 <= age < TTL_NS for age in ages) or not len(sm['pandaStates']):
          return unknown
        state = ('driving' if sm['deviceState'].started else
                 'standby' if any(p.ignitionLine or p.ignitionCan for p in sm['pandaStates']) else 'parked')
        return {'state': state, 'maxAgeMs': (TTL_NS - max(ages)) // 1_000_000}
      except (OSError, RuntimeError, AttributeError, TypeError, ValueError, OverflowError):
        return unknown

  def close(self):
    with self.lock:
      self.closed = True
      if self.messages is not None:
        for socket in getattr(self.messages, 'sock', {}).values():
          close = getattr(socket, 'close', None)
          if close is not None:
            close()
        self.messages = None
        self.floor, self.offset, self.device_offset = self.mono(), None, None
