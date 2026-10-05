"""Wait for vehicle and external GPU power before opening the GPU runtime."""

from dataclasses import dataclass
import time
import sys
import traceback
from threading import Thread

from openpilot.cereal import messaging
from openpilot.common.swaglog import cloudlog
from openpilot.common.hardware import HARDWARE


POWER_MIN_MV = 10_000
POWER_STABLE_NS = 3_000_000_000
POWER_MAX_AGE_NS = 500_000_000
VEHICLE_MAX_AGE_NS = 250_000_000


@dataclass
class PowerReadiness:
  stable_since_ns: int = 0
  previous_ns: int = 0
  sample_max_age_ns: int = POWER_MAX_AGE_NS

  def update(self, now_ns: int, sample_ns: int, voltage_mv: int, vehicle_ready: bool) -> bool:
    continuous = self.previous_ns == 0 or 0 <= now_ns - self.previous_ns <= POWER_MAX_AGE_NS
    self.previous_ns = now_ns
    healthy = (0 < sample_ns <= now_ns and now_ns - sample_ns <= self.sample_max_age_ns and
               voltage_mv >= POWER_MIN_MV and vehicle_ready)
    if not continuous or not healthy:
      self.stable_since_ns = 0
    if not healthy:
      return False
    if self.stable_since_ns == 0:
      self.stable_since_ns = now_ns
    return now_ns - self.stable_since_ns >= POWER_STABLE_NS


def paired_clocks_ns() -> tuple[int, int] | None:
  before = time.monotonic_ns()
  clock = getattr(time, 'CLOCK_BOOTTIME', None)
  boot = time.clock_gettime_ns(clock) if clock is not None else before
  after = time.monotonic_ns()
  return ((before + after) // 2, boot) if 0 <= after - before <= 1_000_000 else None


def current_drive(sm, now_ns: int) -> bool:
  device = sm['deviceState']
  stamp = sm.logMonoTime['deviceState']
  return (sm.seen['deviceState'] and sm.valid['deviceState'] and device.started and
          0 < device.startedMonoTime <= stamp <= now_ns <= stamp + 2_000_000_000)


def supply_voltage(states) -> int:
  known = [state for state in states if str(state.pandaType) != 'unknown']
  return known[0].voltage if len(known) == 1 else 0


def wait_for_chestnut_power(CP, timeout: float = 30.) -> None:
  ready_bus = None
  if CP.brand == "hyundai":
    from opendbc.car.hyundai.model_startup import model_power_ready_bus, model_power_ready
    ready_bus = model_power_ready_bus(CP)

  power_service = "peripheralState" if HARDWARE.get_device_type() == "tici" else "pandaStates"
  sm = messaging.SubMaster([power_service, "deviceState"] + (["can"] if ready_bus is not None else []))
  readiness = PowerReadiness(sample_max_age_ns=1_000_000_000 if power_service == "peripheralState" else POWER_MAX_AGE_NS)
  vehicle_ready, vehicle_sample_ns = ready_bus is None, 0
  started = time.monotonic()
  cloudlog.info("waiting for Chestnut power stability")
  while time.monotonic() - started < timeout:
    sm.update(100)
    clocks = paired_clocks_ns()
    if clocks is None:
      readiness.stable_since_ns = 0
      continue
    now_mono_ns, now_ns = clocks
    drive_ready = current_drive(sm, now_mono_ns)
    if sm.seen["deviceState"] and not drive_ready:
      raise RuntimeError("drive ended while waiting for Chestnut power")
    if ready_bus is not None and sm.updated["can"]:
      ready = model_power_ready(sm["can"], ready_bus) if sm.valid["can"] else False
      if ready is not None:
        vehicle_ready, vehicle_sample_ns = ready, sm.logMonoTime["can"]
    fresh_vehicle = ready_bus is None or 0 < vehicle_sample_ns <= now_ns and now_ns - vehicle_sample_ns <= VEHICLE_MAX_AGE_NS
    states = [sm[power_service]] if power_service == "peripheralState" else sm[power_service]
    voltage = supply_voltage(states)
    if readiness.update(now_ns, sm.logMonoTime[power_service] if sm.valid[power_service] else 0,
                        voltage, drive_ready and vehicle_ready and fresh_vehicle):
      cloudlog.info("Chestnut power stable; starting GPU load")
      return
  raise TimeoutError("Chestnut power or vehicle READY did not stabilize")


def report_load_timeout(loader: Thread, timeout: float) -> None:
  frame = sys._current_frames().get(loader.ident) if loader.ident is not None else None
  stack = "".join(traceback.format_stack(frame, limit=24)) if frame is not None else "Loader already exited"
  cloudlog.event("chestnut.load_timeout", timeout_s=timeout, loader_stack=stack, error=True)
