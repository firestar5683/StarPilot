"""Exact G90 prepublication failure fallback; sent disable is not confirmed ownership."""
import time

from opendbc.car import Bus
from opendbc.car.disable_ecu import disable_ecu
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from opendbc.car.isotp_parallel_query import IsoTpParallelQuery
from opendbc.can.parser import MAX_BAD_COUNTER
from opendbc.car.hyundai.ecu_startup import HyundaiECUStartup, Outcome, stock_copy as stock_copy


def required(cp):
  return (cp.carFingerprint == CAR.GENESIS_G90 and cp.openpilotLongitudinalControl and
          not cp.passive and not cp.dashcamOnly and
          not cp.flags & (HyundaiFlags.CANFD | HyundaiFlags.CAMERA_SCC | HyundaiFlags.CANFD_CAMERA_SCC))


class G90Startup(HyundaiECUStartup):
  def __init__(self, cp, callbacks):
    super().__init__(cp, callbacks, address=0x7d0, bus=0, label='G90')

  def _disable(self, *args, **kwargs):
    return disable_ecu(*args, **kwargs)

  def _query(self, *args, **kwargs):
    return IsoTpParallelQuery(*args, **kwargs)

  def _warm_stock(self, ci):
    deadline = time.monotonic() + 3.
    while time.monotonic() < deadline:
      packets = self.callbacks[0]()
      stamped = [(int(getattr(packet, 'log_mono_time_ns', 0)), list(packet)) for packet in packets]
      if any(stamp <= 0 for stamp, _ in stamped):
        raise RuntimeError('G90 stock warmup requires actual timestamped CAN')
      state = ci.update(stamped)
      now = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
      parser = ci.can_parsers[Bus.pt]
      ready = state.canValid and not state.canTimeout and parser.bus == 0
      for name in ('SCC11', 'SCC12'):
        source = parser.message_states.get(parser.dbc.name_to_msg[name].address)
        if source is None or not source.timestamps or source.counter_fail >= MAX_BAD_COUNTER:
          ready = False
          continue
        stamp = int(source.timestamps[-1])
        if not self.floor_ns < stamp <= now or now - stamp > source.timeout_threshold:
          ready = False
      if ready:
        self.ready = True
        return
      time.sleep(.005)
    self.outcome = Outcome.ABORT_UNCERTAIN
    raise RuntimeError('G90 stock SCC sources did not become fresh before publication')
