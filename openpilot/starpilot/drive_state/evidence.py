"""Fresh physical vehicle evidence independent of the requested pipeline mode."""

import threading
import time

from openpilot.starpilot.parked_evidence import DEVICE_TTL_NS, PANDA_TTL_NS, RESUME_SKEW_NS


PYTHON_TTL_NS = 300_000_000


class PhysicalSource:
  def __init__(self, messages=None, *, owns_messages=False, mono=time.monotonic_ns,
               boot=lambda: time.clock_gettime_ns(getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC))):
    self.messages, self.owns_messages = messages, owns_messages
    self.mono, self.boot = mono, boot
    self.floor = getattr(messages, "after_mono_ns", mono())
    self.offset = None
    self.lock = threading.Lock()
    self.closed = False

  def allowed(self) -> bool:
    with self.lock:
      if self.closed:
        return False
      try:
        if self.messages is None:
          from openpilot.cereal import messaging
          self.messages = messaging.SubMaster(['deviceState', 'pandaStates', 'carState', 'selfdriveState'])
          self.owns_messages = True
        snapshot = getattr(self.messages, "snapshot", None)
        sm = snapshot() if callable(snapshot) else self.messages
        if sm is None:
          return False
        self.floor = max(self.floor, getattr(sm, "after_mono_ns", self.floor))
        if self.owns_messages:
          sm.update(0)
        before, boot, now = self.mono(), self.boot(), self.mono()
        if not 0 <= now - before <= RESUME_SKEW_NS:
          self.floor, self.offset = now, None
          return False
        offset = boot - (before + now) // 2
        if self.offset is not None and abs(offset - self.offset) > RESUME_SKEW_NS:
          self.floor = now
        self.offset = offset

        def fresh(service, python=False):
          stamp = int(sm.logMonoTime[service])
          receipt = int(sm.recv_time[service] * 1e9)
          if not all((sm.seen[service], sm.alive[service], sm.valid[service])) or receipt <= self.floor:
            return False
          if python and stamp <= self.floor:
            return False
          age = now - stamp if python else boot - stamp
          ttl = PYTHON_TTL_NS if python else PANDA_TTL_NS
          return stamp > 0 and 0 <= age <= ttl and 0 <= now - receipt <= ttl

        if not fresh('pandaStates'):
          return False
        pandas = sm['pandaStates']
        if len(pandas) == 0 or any(str(p.pandaType) == 'unknown' for p in pandas):
          return False
        ignition = any(p.ignitionLine or p.ignitionCan for p in pandas)
        if not ignition:
          return all(str(p.safetyModel) == 'noOutput' and not p.controlsAllowed for p in pandas)
        if not fresh('carState', True) or not fresh('selfdriveState', True):
          return False
        car, selfdrive = sm['carState'], sm['selfdriveState']
        return (car.canValid and not car.canTimeout and car.standstill and str(car.gearShifter) == 'park' and
                not selfdrive.enabled and not selfdrive.active)
      except (OSError, RuntimeError, AttributeError, KeyError, TypeError, ValueError, OverflowError):
        return False

  def effective(self):
    with self.lock:
      if self.closed or self.messages is None or self.offset is None:
        return None
      try:
        before, boot, now = self.mono(), self.boot(), self.mono()
        offset = boot - (before + now) // 2
        if not 0 <= now - before <= RESUME_SKEW_NS or abs(offset - self.offset) > RESUME_SKEW_NS:
          self.floor, self.offset = now, None
          return None
        snapshot = getattr(self.messages, "snapshot", None)
        sm = snapshot() if callable(snapshot) else self.messages
        if sm is None:
          return None
        self.floor = max(self.floor, getattr(sm, "after_mono_ns", self.floor))
        stamp, receipt = int(sm.logMonoTime['deviceState']), int(sm.recv_time['deviceState'] * 1e9)
        if (not all((sm.seen['deviceState'], sm.alive['deviceState'], sm.valid['deviceState'])) or
            stamp <= self.floor or receipt <= self.floor or
            not 0 <= now - stamp <= DEVICE_TTL_NS or not 0 <= now - receipt <= DEVICE_TTL_NS):
          return None
        return bool(sm['deviceState'].started)
      except (OSError, RuntimeError, AttributeError, KeyError, TypeError, ValueError, OverflowError):
        return None

  def close(self):
    with self.lock:
      self.closed = True
      if self.owns_messages and self.messages is not None:
        for socket in getattr(self.messages, 'sock', {}).values():
          close = getattr(socket, 'close', None)
          if close is not None:
            close()
      self.messages = None
