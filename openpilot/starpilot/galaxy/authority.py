"""Fresh configuration authority without loading settings pages or graphics libraries."""

from collections.abc import Callable
from dataclasses import dataclass
import threading
import time
from typing import cast

from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.parked_evidence import ParkedEvidence, RESUME_SKEW_NS, fresh_offroad, host_parked


def boot_time_ns() -> int:
  return time.clock_gettime_ns(getattr(time, "CLOCK_BOOTTIME", time.CLOCK_MONOTONIC))


@dataclass(frozen=True)
class AuthorityContext:
  parked: bool
  cp: object | None
  cp_raw: bytes | None
  metric: bool = False
  editing_saved_vehicle: bool = False
  configuration_longitudinal: bool = False
  configuration_vehicle: bool = False


class LiveContextSource:
  """Samples registered Params and the two actual publisher clock domains."""

  MAX_CP_BYTES = 1_048_576
  MAX_LIVE_CP_AGE_NS = 100_000_000_000  # Card republishes finalized parameters every 50 seconds.

  def __init__(self, params, messages=None, *, mono_clock=time.monotonic_ns, boot_clock=boot_time_ns,
               evidence_wait_ms=750, wait_clock=time.monotonic, borrowed_messages=False):
    if borrowed_messages and messages is None:
      raise ValueError("Borrowed authority requires a message source")
    self.borrowed_messages = borrowed_messages
    self.params = params
    self.messages = messages
    self.mono_clock = mono_clock
    self.boot_clock = boot_clock
    self.evidence_wait_ms = evidence_wait_ms
    self.wait_clock = wait_clock
    self.lock = threading.Lock()
    self.closed = False
    self.physical = None
    self.device_offset_ns: int | None = None
    # A pre-start cached Python message can look mono-fresh after suspend.
    # Require a publisher stamp strictly after this collector starts.
    self.device_after_mono_ns = getattr(messages, "after_mono_ns", mono_clock())
    self.last_pair_offset_ns: int | None = None

  def _messages(self):
    if self.closed:
      return None
    if self.messages is None:
      from openpilot.cereal import messaging
      self.messages = messaging.SubMaster(["deviceState", "pandaStates", "carState", "selfdriveState", "carParams"])
    return cast(Callable[[], object], self.messages.snapshot)() if hasattr(self.messages, "snapshot") else self.messages

  def close(self) -> None:
    with self.lock:
      self.closed = True
      if self.physical is not None:
        self.physical.close()
        self.physical = None
      if self.messages is not None and not self.borrowed_messages:
        for sock in getattr(self.messages, "sock", {}).values():
          close = getattr(sock, "close", None)
          if close is not None:
            close()
      self.messages = None

  def observe_borrowed_device_clock(self) -> None:
    """Capture device publisher clock evidence at the collector's update frame.

    A borrowed collector's updated flag lasts only one UI frame. This observes
    clock metadata without advancing sockets or reading saved settings.
    """
    if not self.borrowed_messages:
      return
    with self.lock:
      if self.closed or self.messages is None:
        return
      before = self.mono_clock()
      boot = self.boot_clock()
      now = self.mono_clock()
      if now < before or now - before > RESUME_SKEW_NS:
        self.device_after_mono_ns = max(self.device_after_mono_ns, now)
        self.device_offset_ns = None
        return
      offset = boot - ((before + now) // 2)
      if self.last_pair_offset_ns is not None and abs(offset - self.last_pair_offset_ns) > RESUME_SKEW_NS:
        self.device_after_mono_ns = max(self.device_after_mono_ns, now)
        self.device_offset_ns = None
      self.last_pair_offset_ns = offset
      sm = self.messages
      if sm.updated['deviceState'] and int(sm.logMonoTime['deviceState']) > self.device_after_mono_ns:
        self.device_offset_ns = offset

  def parked(self) -> bool:
    """Settings and offroad operations follow the effective drive state."""
    return self.offroad()

  def offroad(self) -> bool:
    """Effective offroad mode also permits setup with the car powered on."""
    if host_parked():
      return not self.closed
    offroad, readable = read_saved(self.params, "IsOffroad", 8)
    if not readable or offroad != b"1":
      return False
    with self.lock:
      if self.closed:
        return False
      try:
        deadline = self.wait_clock() + self.evidence_wait_ms / 1000
        sm = self._messages()
        timeout = 0
        while True:
          if sm is None:
            return False
          if hasattr(sm, "after_mono_ns"):
            self.device_after_mono_ns = max(self.device_after_mono_ns, sm.after_mono_ns)
            self.device_offset_ns = sm.device_offset_ns
          elif not self.borrowed_messages:
            sm.update(timeout)
          mono_before = self.mono_clock()
          boot_now = self.boot_clock()
          mono_now = self.mono_clock()
          if mono_now < mono_before or mono_now - mono_before > RESUME_SKEW_NS:
            return False
          pair_offset = boot_now - ((mono_before + mono_now) // 2)
          if self.last_pair_offset_ns is not None and abs(pair_offset - self.last_pair_offset_ns) > RESUME_SKEW_NS:
            self.device_after_mono_ns = max(self.device_after_mono_ns, mono_now)
            self.device_offset_ns = None
          self.last_pair_offset_ns = pair_offset
          if sm.updated["deviceState"] and int(sm.logMonoTime["deviceState"]) > self.device_after_mono_ns:
            self.device_offset_ns = pair_offset
          pandas = sm["pandaStates"]
          if sm.seen["deviceState"] and sm["deviceState"].started:
            return False
          evidence = ParkedEvidence(
            True, bool(sm.seen["deviceState"]), bool(sm.alive["deviceState"]), bool(sm.valid["deviceState"]),
            bool(sm["deviceState"].started), int(sm.logMonoTime["deviceState"]),
            int(sm.recv_time["deviceState"] * 1e9), self.device_offset_ns, self.device_after_mono_ns,
            bool(sm.seen["pandaStates"]), bool(sm.alive["pandaStates"]), bool(sm.valid["pandaStates"]),
            int(sm.logMonoTime["pandaStates"]), int(sm.recv_time["pandaStates"] * 1e9),
            tuple(bool(p.ignitionLine or p.ignitionCan) for p in pandas),
          )
          if fresh_offroad(evidence, now_mono_ns=mono_now, now_boot_ns=boot_now):
            offroad, readable = read_saved(self.params, "IsOffroad", 8)
            return bool(readable and offroad == b"1")
          remaining_ms = int((deadline - self.wait_clock()) * 1000)
          if remaining_ms <= 0:
            return False
          timeout = min(50, remaining_ms)
      except (OSError, RuntimeError, AttributeError, TypeError, ValueError, OverflowError):
        return False

  def configuration_allowed(self) -> bool:
    """Allow configuration in effective offroad mode or a fresh stationary Park."""
    if self.offroad():
      return True
    with self.lock:
      if self.closed:
        return False
      try:
        self._messages()
        if not self.borrowed_messages and not hasattr(self.messages, 'snapshot'):
          self.messages.update(0)
        if self.physical is None:
          from openpilot.starpilot.drive_state.evidence import PhysicalSource
          self.physical = PhysicalSource(self.messages, mono=self.mono_clock, boot=self.boot_clock)
        return self.physical.allowed()
      except (OSError, RuntimeError, AttributeError, KeyError, TypeError, ValueError):
        return False

  def runtime_vehicle(self):
    try:
      with self.lock:
        if self.closed:
          return None, None
        sm = self._messages() if self.messages is not None else None
        if sm is not None:
          if not self.borrowed_messages and not hasattr(self.messages, 'snapshot'):
            sm.update(0)
          now = self.mono_clock()
          stamp = int(sm.logMonoTime.get('carParams', 0))
          floor = max(self.device_after_mono_ns, getattr(sm, 'after_mono_ns', 0))
          if (sm.seen.get('carParams', False) and sm.valid.get('carParams', False) and sm.alive.get('carParams', False) and
              floor < stamp <= now and now - stamp <= self.MAX_LIVE_CP_AGE_NS):
            from opendbc.car.values import PLATFORMS
            from opendbc.car.mock.values import CAR as MOCK
            from opendbc.car.structs import car
            cp = sm['carParams']
            if (cp.schema.node.id == car.CarParams.schema.node.id and not cp.notCar and
                cp.carFingerprint in PLATFORMS and cp.carFingerprint != MOCK.MOCK):
              raw = cp.as_builder().to_bytes()
              if len(raw) <= self.MAX_CP_BYTES:
                return cp, b'live-vehicle:' + raw
    except (OSError, RuntimeError, AttributeError, KeyError, TypeError, ValueError, OverflowError):
      pass
    cp_raw, readable = read_saved(self.params, "CarParamsPersistent", self.MAX_CP_BYTES)
    cp = None
    if readable and cp_raw is not None:
      try:
        from openpilot.cereal import messaging
        from opendbc.car.structs import car
        from openpilot.starpilot.schema_cache import inspect_cache
        inspected = inspect_cache("CarParamsPersistent", cp_raw)
        if inspected.status == "valid" and inspected.payload is not None:
          cp = messaging.log_from_bytes(inspected.payload, car.CarParams)
      except (OSError, RuntimeError, TypeError, ValueError, OverflowError):
        cp = None
    return cp, cp_raw if readable else None

  def sample(self) -> AuthorityContext:
    parked = self.configuration_allowed()
    cp, cp_raw = self.runtime_vehicle()
    readable = True
    editing_saved = configurable_long = configuration_vehicle = False
    if parked and self.offroad():
      from openpilot.starpilot.galaxy.vehicle_configuration import settings_configuration
      cp, cp_raw, editing_saved, configurable_long = settings_configuration(self.params, cp, cp_raw if readable else None)
      configuration_vehicle = cp is not None
      readable = True
    units, unit_readable = read_saved(self.params, "IsMetric", 8)
    return AuthorityContext(parked, cp, cp_raw if readable else None, bool(unit_readable and units == b"1"),
                            editing_saved, configurable_long, configuration_vehicle)
