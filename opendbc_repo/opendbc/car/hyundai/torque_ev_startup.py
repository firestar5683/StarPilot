"""Torque EV HDAII startup transaction.

Ioniq 5 and second-generation Kona EV share the original session and suppressed
communication-control request. No SecurityAccess key exchange is implied.
"""

from copy import deepcopy
import time

from opendbc.car import Bus, make_tester_present_msg
from opendbc.car.hyundai.canfd_stock_aol import qualified as stock_qualified
from opendbc.car.hyundai.ecu_startup import HyundaiECUStartup, Outcome
from opendbc.car.hyundai.ev9_keeper import EV9Keeper as StartupKeeper
from opendbc.car.hyundai.values import CAR, HyundaiFlags, HyundaiSafetyFlags
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.structs import CarParams
from opendbc.can.parser import MAX_BAD_COUNTER

CARS = frozenset((CAR.HYUNDAI_IONIQ_5, CAR.HYUNDAI_KONA_EV_2ND_GEN))


def topology_owned(cp):
  required_flags = HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEER_MSG
  allowed = (
    required_flags
    | HyundaiFlags.CANFD_LKA_STEER_MSG_ALT
    | HyundaiFlags.CANFD_ALT_GEARS
    | HyundaiFlags.CANFD_ALT_GEARS_2
    | HyundaiFlags.CANFD_NO_RADAR_DISABLE
    | HyundaiFlags.CCNC
  )
  if (
    cp.carFingerprint not in CARS
    or cp.brand != "hyundai"
    or cp.passive
    or cp.dashcamOnly
    or cp.notCar
    or cp.steerControlType != CarParams.SteerControlType.torque
    or int(cp.flags) & int(required_flags) != int(required_flags)
    or int(cp.flags) & ~int(allowed)
    or len(cp.safetyConfigs) != 1
    or cp.safetyConfigs[0].safetyModel != CarParams.SafetyModel.hyundaiCanfd
  ):
    return False
  bus = CanBus(cp)
  return (bus.ACAN, bus.ECAN, bus.CAM) == (0, 1, 2)


def required(cp):
  return cp.carFingerprint in CARS and cp.openpilotLongitudinalControl and bool(cp.flags & HyundaiFlags.CANFD_LKA_STEER_MSG)


def candidate(stock, *, requested, is_release):
  # Restrict takeover to the supported stock HDAII torque topology.
  if not requested or is_release or not stock.alphaLongitudinalAvailable or not topology_owned(stock) or not stock_qualified(stock):
    return None
  cp = stock.as_reader().as_builder()
  cp.alphaLongitudinalAvailable = True
  cp.openpilotLongitudinalControl = True
  cp.pcmCruise = False
  cp.safetyConfigs[0].safetyParam = (int(cp.safetyConfigs[0].safetyParam) & ~0x0800) | HyundaiSafetyFlags.LONG.value
  return cp


class TorqueEVStartup(HyundaiECUStartup):
  def __init__(self, cp, callbacks, *, stock_cp, clock=time.monotonic, keeper_factory=StartupKeeper):
    if stock_cp.carFingerprint not in CARS or not stock_qualified(stock_cp):
      raise ValueError("Exact torque EV stock CP required")
    expected = candidate(stock_cp, requested=True, is_release=False)
    if expected is None or cp.to_dict() != expected.to_dict():
      raise ValueError("Torque EV LONG candidate does not match stock contract")
    super().__init__(cp, callbacks, address=0x730, bus=1, label="Torque EV")
    self.stock_cp = stock_cp.as_reader().as_builder()
    self.clock = clock
    self.keeper_factory = keeper_factory
    self.keeper = None
    self.handed_off = False

  def _disable(self, can_recv, can_send, **kwargs):
    # Existing generic helper returns after send without inspecting negatives.
    # Preserve original explicit rejection vs expected suppressed silence.
    self.disable_response = None
    for _ in range(10):
      try:
        session = self._query(can_send, can_recv, self.bus, [(self.address, None)], [b"\x10\x03"], [b"\x50\x03"])
        if not session.get_data(0.1):
          time.sleep(0.1)
          continue
        time.sleep(0.05)
        command = self._query(can_send, can_recv, self.bus, [(self.address, None)], [b"\x28\x83\x01"], [b""])
        replies = command.get_data(0.1)
        if not replies:
          self.disable_response = "suppressed_reply_sent_unconfirmed"
          return True
        for payload in replies.values():
          if payload == b"\x68\x03":
            self.disable_response = "positive_communication_control"
          elif len(payload) == 3 and payload[:2] == b"\x7f\x28":
            self.disable_response = "negative_communication_control"
            return False
          else:
            self.disable_response = "unexpected_or_malformed_reply"
            return False
        return True
      except Exception:
        if self.disable_attempted:
          return False
    return False

  def prepare(self, *, admission):
    super().prepare(admission=admission)
    if self.outcome in (Outcome.STOCK_UNTOUCHED, Outcome.STOCK_RESTORED):
      # Retain every stock field/marker, not a partly reconstructed fallback.
      self.cp = self.stock_cp.as_reader().as_builder()
      self.prepared_cp = deepcopy(self.cp.to_dict())
    elif self.outcome is Outcome.SENT_UNCONFIRMED:
      self.keeper = self.keeper_factory(lambda: self.callbacks[1]([make_tester_present_msg(self.address, self.bus, suppress_response=True)]), clock=self.clock)
      self.keeper.start()
    return self.cp

  def finalize_aol_configuration(self, ci):
    if self.published or self.closed or ci is not self.ci or not self.ready:
      raise RuntimeError("Torque EV AOL finalization requires configured startup")
    if self.prepared_for(ci.CP):
      return
    if self.outcome in (Outcome.STOCK_UNTOUCHED, Outcome.STOCK_RESTORED):
      return super().finalize_aol_configuration(ci)
    from opendbc.car.hyundai.canfd_stock_aol import qualified_long

    if self.outcome is not Outcome.SENT_UNCONFIRMED or not qualified_long(ci.CP, marked_only=True):
      raise RuntimeError("Torque EV startup does not admit this AOL configuration")
    expected = deepcopy(self.prepared_cp)
    configs = expected.get("safetyConfigs", [])
    if (
      len(configs) != 1
      or configs[0]["safetyModel"] != "hyundaiCanfd"
      or configs[0]["safetyParam"] not in (0x15, 0x95)
      or expected["alternativeExperience"] != 0
    ):
      raise RuntimeError("Torque EV prepared safety profile cannot be finalized")
    configs[0]["safetyParam"] |= 0x0800
    expected["alternativeExperience"] = 32
    if ci.CP.to_dict() != expected:
      raise RuntimeError("Torque EV AOL finalization changed unrelated CarParams")
    self.prepared_cp = expected

  def check(self):
    super().check()
    if self.keeper is not None and self.keeper.abort_reason is not None:
      self.keeper.stop()
      # Main thread alone performs receive/restore; worker only marks abort.
      if self.disable_attempted and not self.restored:
        try:
          self._restore()
        except Exception:
          pass
      self.outcome = Outcome.ABORT_UNCERTAIN
      raise RuntimeError("Torque EV startup handoff aborted")

  def sources_current(self, ci, now_ns):
    if not ci.CS.out.canValid or ci.CS.out.canTimeout:
      return False
    parser = ci.can_parsers[Bus.pt]
    for name in ("MDPS", "ACCELERATOR", "WHEEL_SPEEDS", "TCS"):
      source = parser.message_states.get(parser.dbc.name_to_msg[name].address)
      if (
        source is None
        or not source.timestamps
        or source.counter_fail >= MAX_BAD_COUNTER
        or not self.floor_ns < int(source.timestamps[-1]) <= now_ns
        or now_ns - int(source.timestamps[-1]) > source.timeout_threshold
      ):
        return False
    return True

  def before_control(self, *, configured, sources_current, control_current):
    self.check()
    if self.outcome is not Outcome.SENT_UNCONFIRMED:
      return True
    if not (configured and sources_current and control_current):
      return False
    if not self.handed_off:
      self.keeper.stop()  # Never join while holding sender callback lock.
      self.check()
      self.handed_off = True
    return True

  def _warm_stock(self, ci):
    deadline = self.clock() + 3.0
    while self.clock() < deadline:
      packets = self.callbacks[0]()
      stamped = [(int(getattr(p, "log_mono_time_ns", 0)), list(p)) for p in packets]
      if any(stamp <= 0 for stamp, _ in stamped):
        raise RuntimeError("Stock warmup requires actual timestamped CAN")
      state = ci.update(stamped)
      now = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
      parser = ci.can_parsers[Bus.pt]
      scc = parser.message_states.get(parser.dbc.name_to_msg["SCC_CONTROL"].address)
      if (
        state.canValid
        and not state.canTimeout
        and parser.bus == self.bus
        and self.sources_current(ci, now)
        and scc is not None
        and scc.timestamps
        and scc.counter_fail < MAX_BAD_COUNTER
        and self.floor_ns < int(scc.timestamps[-1]) <= now
        and now - int(scc.timestamps[-1]) <= scc.timeout_threshold
      ):
        self.ready = True
        return
      time.sleep(0.005)
    self.outcome = Outcome.ABORT_UNCERTAIN
    raise RuntimeError("Stock sources did not resume before publication")

  def close(self):
    if self.keeper is not None:
      self.keeper.stop()
    super().close()
