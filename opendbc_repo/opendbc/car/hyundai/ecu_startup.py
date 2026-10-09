"""Hyundai prepublication ECU transaction; sent disable is not confirmed ownership."""
from enum import Enum
from copy import deepcopy
import time

from opendbc.car import structs
from opendbc.car.disable_ecu import disable_ecu
from opendbc.car.hyundai.values import HyundaiSafetyFlags
from opendbc.car.isotp_parallel_query import IsoTpParallelQuery


class Outcome(Enum):
  STOCK_UNTOUCHED = 'stock_untouched'
  SENT_UNCONFIRMED = 'sent_unconfirmed'
  STOCK_RESTORED = 'stock_restored'
  ABORT_UNCERTAIN = 'abort_uncertain'


def stock_copy(cp):
  with structs.CarParams.from_bytes(cp.to_bytes()) as reader:
    stock = reader.as_builder()
  stock.openpilotLongitudinalControl = False
  stock.pcmCruise = True
  for config in stock.safetyConfigs:
    config.safetyParam &= ~HyundaiSafetyFlags.LONG.value
  return stock


class HyundaiECUStartup:
  def __init__(self, cp, callbacks, *, address, bus, label):
    self.address, self.bus, self.label = address, bus, label
    self.cp = cp
    self.callbacks = callbacks
    self.outcome = None
    self.disable_attempted = False
    self.restored = False
    self.admission = None
    self.floor_ns = 0
    self.published = False
    self.ci = None
    self.closed = False
    self.ready = False
    self.prepared_cp = None

  def _disable(self, *args, **kwargs):
    return disable_ecu(*args, **kwargs)

  def _query(self, *args, **kwargs):
    return IsoTpParallelQuery(*args, **kwargs)

  def _warm_stock(self, ci):
    raise NotImplementedError

  def _send(self, frames):
    # The exact3-byte UDS request fits an ISO-TP single frame. Mark before
    # invoking transport: a callback exception cannot prove no ECU mutation.
    for address, data, bus in frames:
      if address == self.address and bus == self.bus and len(data) >= 4 and data[:4] == b'\x03\x28\x83\x01':
        self.disable_attempted = True
    self.callbacks[1](frames)

  def _restore(self):
    if not self.admission():
      return False
    recv, send = self.callbacks
    session = self._query(send, recv, self.bus, [(self.address, None)], [b'\x10\x03'], [b'\x50\x03'])
    if not session.get_data(.1):
      return False
    # Restore is deliberately unsuppressed; a sent288001 cannot prove stock.
    restore = self._query(send, recv, self.bus, [(self.address, None)], [b'\x28\x00\x01'], [b'\x68\x00'])
    if not restore.get_data(.1):
      return False
    self.restored = True
    self.floor_ns = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    return True

  def prepare(self, *, admission):
    self.admission = admission
    self.floor_ns = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if not admission():
      self.outcome = Outcome.STOCK_UNTOUCHED
      self.cp = stock_copy(self.cp)
      self.prepared_cp = deepcopy(self.cp.to_dict())
      return self.cp
    try:
      success = self._disable(self.callbacks[0], self._send, bus=self.bus, addr=self.address, com_cont_req=b'\x28\x83\x01')
    except Exception:
      success = False
    if success and self.disable_attempted:
      self.outcome = Outcome.SENT_UNCONFIRMED
      self.prepared_cp = deepcopy(self.cp.to_dict())
      return self.cp
    if not self.disable_attempted:
      self.outcome = Outcome.STOCK_UNTOUCHED
    else:
      try:
        restored = self._restore()
      except Exception:
        restored = False
      if not restored:
        self.outcome = Outcome.ABORT_UNCERTAIN
        raise RuntimeError(f'{self.label} disable failed; stock ECU restoration unverified')
      self.outcome = Outcome.STOCK_RESTORED
    self.cp = stock_copy(self.cp)
    self.prepared_cp = deepcopy(self.cp.to_dict())
    return self.cp

  def prepared_for(self, cp):
    return (self.outcome is not None and self.outcome is not Outcome.ABORT_UNCERTAIN and
            self.prepared_cp is not None and cp.to_dict() == self.prepared_cp)

  def configure(self, ci):
    if not self.prepared_for(ci.CP):
      raise RuntimeError(f'{self.label} prepared startup does not match constructed CP')
    self.ci = ci
    if self.outcome is Outcome.SENT_UNCONFIRMED:
      self.ready = True
      return  # Preserve ordinary controller commands and1Hz tester cadence.
    self._warm_stock(ci)

  def finalize_aol_configuration(self, ci):
    """Finalize only the supported stock AOL marker before publication."""
    if self.published or self.closed or ci is not self.ci or not self.ready:
      raise RuntimeError('Hyundai AOL finalization requires configured startup')
    if self.prepared_for(ci.CP):
      return
    from opendbc.car.hyundai.ev6_aol import qualified as ev6_aol_qualified
    if self.outcome is Outcome.SENT_UNCONFIRMED and ev6_aol_qualified(ci.CP, marked_only=True):
      expected = deepcopy(self.prepared_cp)
      configs = expected.get('safetyConfigs', [])
      if len(configs) != 1 or configs[0]['safetyParam'] != 0x15 or expected['alternativeExperience'] != 0:
        raise RuntimeError('EV6 prepared LONG profile cannot be finalized')
      configs[0]['safetyParam'] |= 0x0800
      expected['alternativeExperience'] = 32
      if ci.CP.to_dict() != expected:
        raise RuntimeError('EV6 AOL finalization changed unrelated CarParams')
      self.prepared_cp = expected
      return
    from opendbc.car.hyundai.canfd_stock_aol import qualified as stock_aol_qualified
    if (self.outcome not in (Outcome.STOCK_UNTOUCHED, Outcome.STOCK_RESTORED) or
        not stock_aol_qualified(ci.CP, marked_only=True)):
      raise RuntimeError('Hyundai startup does not admit this AOL configuration')
    expected = deepcopy(self.prepared_cp)
    configs = expected.get('safetyConfigs', [])
    if len(configs) != 1 or configs[0]['safetyParam'] not in (0x11, 0x91):
      raise RuntimeError('Hyundai startup stock profile cannot be finalized')
    configs[0]['safetyParam'] |= 0x0800
    if ci.CP.to_dict() != expected:
      raise RuntimeError('Hyundai AOL finalization changed unrelated CarParams')
    self.prepared_cp = expected

  def seal_publication(self):
    self.check()
    if self.ci is None or not self.ready:
      raise RuntimeError(f'{self.label} startup requires configure before publication')
    if not self.prepared_for(self.ci.CP):
      raise RuntimeError(f'{self.label} CP differs from its prepared startup decision')
    self.published = True

  def check(self):
    if self.outcome is None or self.outcome is Outcome.ABORT_UNCERTAIN:
      raise RuntimeError('Unresolved Hyundai startup')

  def close(self):
    if self.closed:
      return
    self.closed = True
    if self.disable_attempted and not self.published and not self.restored:
      try:
        restored = self._restore()
      except Exception:
        restored = False
      if not restored:
        self.outcome = Outcome.ABORT_UNCERTAIN
        raise RuntimeError(f'{self.label} unpublished startup cleanup could not confirm stock restoration')

  def after_state(self, **context):
    pass

  def consume_cruise_resume(self):
    return None

  def before_control(self, **context):
    self.check()
    return True

  def sources_current(self, ci, now_ns):
    return True

  def maintain(self, *, configured):
    pass

  def sent(self, frames, *, valid):
    pass
