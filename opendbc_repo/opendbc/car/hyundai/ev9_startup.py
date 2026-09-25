"""EV9 source-selected communication-control startup, resolved before CarParams publication."""
from copy import deepcopy
import time

from opendbc.car import Bus, make_tester_present_msg
from opendbc.can.parser import MAX_BAD_COUNTER
from opendbc.car.hyundai.ecu_startup import HyundaiECUStartup, Outcome
from opendbc.car.hyundai.ev9_longitudinal import qualified, copy_cp
from opendbc.car.hyundai.ccnc_ev_stock import qualified as stock_qualified
from opendbc.car.hyundai.values import CAR
from opendbc.car.hyundai.ev9_keeper import EV9Keeper


def required(cp):
  # A malformed LONG CP still requires the owner; it must never bypass it.
  return cp.carFingerprint == CAR.KIA_EV9 and cp.openpilotLongitudinalControl


class EV9Startup(HyundaiECUStartup):
  def __init__(self, cp, callbacks, *, stock_cp, clock=time.monotonic, keeper_factory=EV9Keeper):
    super().__init__(cp, callbacks, address=0x730, bus=1, label='EV9')
    if stock_cp.carFingerprint != CAR.KIA_EV9 or not stock_qualified(stock_cp):
      raise ValueError('EV9 startup requires exact original stock CP')
    self.clock = clock
    self.stock_cp = copy_cp(stock_cp)
    self.keeper_factory = keeper_factory
    self.keeper = None
    self.handed_off = False
    self.disable_response = None


  def _send(self, frames):
    # Source-selected EV9 request is unsuppressed enable-RX/disable-TX.
    for address, data, bus in frames:
      if address == self.address and bus == self.bus and len(data) >= 4 and data[:4] == b"\x03\x28\x01\x01":
        self.disable_attempted = True
    self.callbacks[1](frames)

  def _disable(self, can_recv, can_send, **kwargs):
    # Keep the original outcome distinction: command silence is sent,
    # unconfirmed; an explicit negative reply is failure. No SecurityAccess.
    for _ in range(10):
      try:
        session = self._query(can_send, can_recv, self.bus, [(self.address, None)], [b"\x10\x03"], [b"\x50\x03"])
        if not session.get_data(.1):
          time.sleep(.1)
          continue
        time.sleep(.05)
        command = self._query(can_send, can_recv, self.bus, [(self.address, None)], [b"\x28\x01\x01"], [b""])
        replies = command.get_data(.1)
        if not replies:
          self.disable_response = 'no_reply_sent_unconfirmed'
          return True
        for payload in replies.values():
          if payload == b"\x68\x01":
            self.disable_response = 'positive_communication_control'
          elif len(payload) == 3 and payload[:2] == b"\x7f\x28":
            self.disable_response = 'negative_communication_control'
            return False
          else:
            self.disable_response = 'unexpected_or_malformed_reply'
            return False
        return True
      except Exception:
        # Once the command was emitted, do not retry into uncertain ownership.
        # The shared owner restores before attempting stock publication.
        if self.disable_attempted:
          raise
        time.sleep(.1)
    return False

  def _ready(self):
    deadline = self.clock() + 0.5
    while self.clock() < deadline:
      packets = self.callbacks[0](wait_for_one=False)
      for packet in packets:
        for message in packet:
          if message.address == 0x35 and message.src == self.bus and len(message.dat) > 3 and message.dat[3] & 0x40:
            return True
      time.sleep(.005)
    return False

  def prepare(self, *, admission):
    if not qualified(self.cp):
      raise ValueError('Unqualified EV9 LONG startup profile')
    # A READY vehicle retains stock SCC and never receives communication control.
    skip = not admission() or self._ready()
    super().prepare(admission=(lambda: False) if skip else admission)
    if self.outcome in (Outcome.STOCK_UNTOUCHED, Outcome.STOCK_RESTORED):
      self.cp = copy_cp(self.stock_cp)
      self.prepared_cp = deepcopy(self.cp.to_dict())
    elif self.outcome is Outcome.SENT_UNCONFIRMED:
      self.keeper = self.keeper_factory(
        lambda: self.callbacks[1]([make_tester_present_msg(self.address, self.bus, suppress_response=True)]), clock=self.clock)
      self.keeper.start()
    return self.cp

  def check(self):
    super().check()
    if self.keeper is not None and self.keeper.abort_reason is not None:
      self.keeper.stop()
      # Main thread alone receives CAN/restores. Never mutate published CP.
      if self.disable_attempted and not self.restored:
        try:
          self._restore()
        except Exception:
          pass
      self.outcome = Outcome.ABORT_UNCERTAIN
      raise RuntimeError('EV9 startup keeper aborted; session must stop')

  def sources_current(self, ci, now_ns):
    parser = ci.can_parsers[Bus.pt]
    for name in ('MDPS', 'ACCELERATOR', 'WHEEL_SPEEDS', 'TCS'):
      source = parser.message_states.get(parser.dbc.name_to_msg[name].address)
      if source is None or not source.timestamps or source.counter_fail >= MAX_BAD_COUNTER:
        return False
      stamp = int(source.timestamps[-1])
      if not self.floor_ns < stamp <= now_ns or now_ns - stamp > source.timeout_threshold:
        return False
    return True

  def before_control(self, *, configured, sources_current, control_current):
    self.check()
    if self.outcome is not Outcome.SENT_UNCONFIRMED:
      return True
    if not (configured and sources_current and control_current):
      return False
    if not self.handed_off:
      self.keeper.stop()  # No sender lock held; join before controller handoff.
      self.check()
      self.handed_off = True
    return True

  def close(self):
    if self.keeper is not None:
      self.keeper.stop()
      if self.keeper.abort_reason is not None and self.disable_attempted and not self.restored:
        try:
          self._restore()
        except Exception:
          pass
    super().close()

  def _warm_stock(self, ci):
    deadline = self.clock() + 3.
    while self.clock() < deadline:
      packets = self.callbacks[0]()
      stamped = [(int(getattr(packet, 'log_mono_time_ns', 0)), list(packet)) for packet in packets]
      if any(stamp <= 0 for stamp, _ in stamped):
        raise RuntimeError('EV9 stock warmup requires timestamped CAN')
      state = ci.update(stamped)
      now = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
      parser = ci.can_parsers[Bus.pt]
      ready = state.canValid and not state.canTimeout and parser.bus == 1
      for name in ('SCC_CONTROL', 'MDPS', 'ACCELERATOR', 'WHEEL_SPEEDS', 'TCS'):
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
    raise RuntimeError('EV9 stock sources did not resume before publication')
