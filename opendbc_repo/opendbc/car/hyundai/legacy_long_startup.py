"""Legacy radar transaction with exact stock fallback before publication."""
from copy import deepcopy
import time

from opendbc.car import Bus
from opendbc.can.parser import MAX_BAD_COUNTER
from opendbc.car.hyundai.values import HyundaiFlags
from opendbc.car.hyundai.ecu_startup import HyundaiECUStartup, Outcome
from opendbc.car.hyundai.g90_startup import G90Startup
from opendbc.car.hyundai.legacy_long_aol import candidate, qualified, CARS, ordinary_word, aol_word
from opendbc.car.hyundai.classic_scc_aol import qualified as stock_qualified, stock_word, aol_word as stock_aol_word


def required(cp):
  return cp.carFingerprint in CARS and cp.openpilotLongitudinalControl


class LegacyLongStartup(G90Startup):
  def __init__(self, cp, callbacks, *, stock_cp):
    expected = candidate(stock_cp, requested=True)
    if expected is None or expected.to_dict() != cp.to_dict():
      raise ValueError('Legacy LONG candidate differs from exact stock configuration')
    HyundaiECUStartup.__init__(self, cp, callbacks, address=0x7d0, bus=0, label='Legacy LONG')
    self.stock_cp = stock_cp.as_reader().as_builder()

  def prepare(self, *, admission):
    super().prepare(admission=admission)
    if self.outcome in (Outcome.STOCK_UNTOUCHED, Outcome.STOCK_RESTORED):
      self.cp = self.stock_cp.as_reader().as_builder()
      self.prepared_cp = deepcopy(self.cp.to_dict())
    elif self.outcome is Outcome.SENT_UNCONFIRMED:
      self.floor_ns = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    return self.cp

  def sources_current(self, ci, now_ns):
    if self.outcome is not Outcome.SENT_UNCONFIRMED:
      return True
    if not ci.CS.out.canValid or ci.CS.out.canTimeout:
      return False
    parser = ci.can_parsers[Bus.pt]
    gas = 'E_EMS11' if ci.CP.flags & HyundaiFlags.HYBRID else 'EMS16'
    for name in (gas, 'WHL_SPD11', 'TCS13', 'MDPS12', 'CLU11'):
      source = parser.message_states.get(parser.dbc.name_to_msg[name].address)
      if (source is None or not source.timestamps or source.counter_fail >= MAX_BAD_COUNTER
          or not self.floor_ns < int(source.timestamps[-1]) <= now_ns
          or now_ns - int(source.timestamps[-1]) > source.timeout_threshold):
        return False
    return True

  def before_control(self, *, configured, sources_current, control_current):
    self.check()
    return self.outcome is not Outcome.SENT_UNCONFIRMED or (configured and sources_current and control_current)

  def finalize_aol_configuration(self, ci):
    if self.published or self.closed or ci is not self.ci or not self.ready:
      raise RuntimeError('Legacy LONG AOL finalization requires configured startup')
    if self.prepared_for(ci.CP):
      return
    if self.outcome is Outcome.SENT_UNCONFIRMED and qualified(ci.CP, marked_only=True):
      before_word, after_word = ordinary_word(ci.CP), aol_word(ci.CP)
    elif self.outcome in (Outcome.STOCK_UNTOUCHED, Outcome.STOCK_RESTORED) and stock_qualified(ci.CP, marked_only=True):
      before_word, after_word = stock_word(ci.CP), stock_aol_word(ci.CP)
    else:
      raise RuntimeError('Legacy startup does not admit this AOL configuration')
    expected = deepcopy(self.prepared_cp)
    config = expected['safetyConfigs'][0]
    if config['safetyModel'] != 'hyundaiLegacy' or config['safetyParam'] != before_word or expected['alternativeExperience'] != 0:
      raise RuntimeError('Legacy prepared profile cannot be finalized')
    config['safetyParam'] = after_word
    expected['alternativeExperience'] = 32
    if ci.CP.to_dict() != expected:
      raise RuntimeError('Legacy AOL finalization changed unrelated CarParams')
    self.prepared_cp = expected
