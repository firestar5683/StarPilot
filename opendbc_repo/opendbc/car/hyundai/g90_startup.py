"""Exact G90 prepublication failure fallback; sent disable is not confirmed ownership."""
from copy import deepcopy
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

  def finalize_aol_configuration(self, ci):
    if self.published or self.closed or ci is not self.ci or not self.ready:
      raise RuntimeError('G90 AOL finalization requires configured startup')
    if self.prepared_for(ci.CP):
      return
    from opendbc.car.hyundai.classic_long_aol import qualified as long_qualified, ordinary_word, aol_word as long_word
    from opendbc.car.hyundai.classic_scc_aol import qualified as stock_qualified, stock_word, aol_word as stock_aol_word
    if self.outcome is Outcome.SENT_UNCONFIRMED and long_qualified(ci.CP, marked_only=True):
      before_word, after_word = ordinary_word(ci.CP), long_word(ci.CP)
    elif self.outcome in (Outcome.STOCK_UNTOUCHED, Outcome.STOCK_RESTORED) and stock_qualified(ci.CP, marked_only=True):
      before_word, after_word = stock_word(ci.CP), stock_aol_word(ci.CP)
    else:
      raise RuntimeError('G90 startup does not admit this AOL configuration')
    if ci.CP.carFingerprint != CAR.GENESIS_G90 or ci.CP.alternativeExperience != 32:
      raise RuntimeError('G90 AOL configuration identity does not match')
    expected = deepcopy(self.prepared_cp)
    configs = expected.get('safetyConfigs', [])
    if len(configs) != 1 or configs[0]['safetyModel'] != 'hyundai' or configs[0]['safetyParam'] != before_word or expected['alternativeExperience'] != 0:
      raise RuntimeError('G90 prepared safety profile cannot be finalized')
    configs[0]['safetyParam'] = after_word
    expected['alternativeExperience'] = 32
    if ci.CP.to_dict() != expected:
      raise RuntimeError('G90 AOL finalization changed unrelated CarParams')
    self.prepared_cp = expected

  def _warm_stock(self, ci):
    deadline = time.monotonic() + 3.
    while time.monotonic() < deadline:
      packets = self.callbacks[0]()
      stamped = [(int(getattr(packet, 'log_mono_time_ns', 0)), list(packet)) for packet in packets]
      if any(stamp <= 0 for stamp, _ in stamped):
        raise RuntimeError(f'{self.label} stock warmup requires actual timestamped CAN')
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
    raise RuntimeError(f'{self.label} stock SCC sources did not become fresh before publication')
