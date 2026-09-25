"""Ioniq 6 HDA-II candidate and ECU-ownership transaction.

Select the exact opt-in DEBUG CarParams before publication. Verify live sources
and run the reversible diagnostic transaction when Card is ready to replace TX.
"""

import statistics
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from opendbc.car.can_definitions import CanData, CanRecvCallable, CanSendCallable
from opendbc.car import make_tester_present_msg
from opendbc.car.hyundai.hyundaicanfd import hkg_can_fd_checksum
from opendbc.car.isotp_parallel_query import IsoTpParallelQuery


IONIQ6_ECAN_BUS = 1
IONIQ6_ADAS_ADDR = 0x730
IONIQ6_STOCK_SCC_ADDR = 0x1A0
IONIQ6_STOCK_HEARTBEAT_ADDR = 0x100
IONIQ6_STOCK_BSM = {0x1BA: 24, 0x1E5: 16}
IONIQ6_REQUIRED_RX = {0x35: 32, 0x175: 24, 0xA0: 24, 0xEA: 24, 0x1CF: 8}
IONIQ6_LONG_PREARM_ENABLED = True
IONIQ6_DEBUG_LONG_PARAMS = frozenset((0x8015, 0x8095, 0x8815, 0x8895))


class HandoffOutcome(Enum):
  NOT_READY = auto()
  STOCK = auto()
  CONFIRMED = auto()
  UNAVAILABLE = auto()


@dataclass(frozen=True)
class HandoffResult:
  outcome: HandoffOutcome
  reason: str
  source_period: float | None = None
  disable_acknowledged: bool = False
  restore_acknowledged: bool = False


def build_ioniq6_hda2_long_candidate(stock_cp, fingerprint):
  """Prepare a separate CP only for the two observed HDA-II EV forms."""
  from opendbc.car.hyundai.radar_interface import MRR35_RADAR_START_ADDR
  from opendbc.car.hyundai.values import CAR

  if stock_cp.carFingerprint != CAR.HYUNDAI_IONIQ_6 or stock_cp.radarUnavailable:
    return None
  camera = fingerprint[2]
  direct = camera.get(0x50) == 16 and 0x110 not in camera
  alternate = camera.get(0x110) == 32 and 0x50 not in camera
  if not (direct or alternate):
    return None
  camera_support = (0x362, 32) if alternate else (0x2A4, 24)
  if (camera.get(camera_support[0]) != camera_support[1] or
      fingerprint[1].get(0x1CF) != 8 or
      fingerprint[1].get(0x35) != 32 or fingerprint[1].get(0x175) != 24 or
      fingerprint[1].get(0xA0) != 24 or fingerprint[1].get(0xEA) != 24 or
      any(fingerprint[1].get(addr) != length for addr, length in {**IONIQ6_STOCK_BSM, 0x36A: 16}.items()) or
      fingerprint[0].get(MRR35_RADAR_START_ADDR) != 24):
    return None
  if int(stock_cp.safetyConfigs[-1].safetyParam) not in (0x11, 0x91):
    return None

  long_cp = stock_cp.as_reader().as_builder()
  long_cp.alphaLongitudinalAvailable = True
  long_cp.openpilotLongitudinalControl = True
  long_cp.pcmCruise = False
  long_cp.safetyConfigs[-1].safetyParam = 0x8095 if alternate else 0x8015
  return long_cp


DiagnosticExchange = Callable[[bytes, bytes], bool]
Clock = Callable[[], float]


class TimestampedCanPacket(list[CanData]):
  """CAN event frames with an optional producer timestamp for cadence only."""

  def __init__(self, frames: list[CanData], log_mono_time_ns: int):
    super().__init__(frames)
    self.log_mono_time_ns = log_mono_time_ns


class ObservingCanRecv:
  """Keep SCC source evidence while ISO-TP consumes the shared CAN stream."""

  def __init__(self, can_recv: CanRecvCallable, clock: Clock = time.monotonic):
    self.can_recv = can_recv
    self.clock = clock
    self.source_seen_count = 0
    self.latest_source_time: float | None = None
    self.heartbeat_seen_count = 0

  def __call__(self, wait_for_one: bool = False) -> list[list[CanData]]:
    packets = self.can_recv(wait_for_one=wait_for_one)
    for packet in packets:
      for msg in packet:
        if msg.src == IONIQ6_ECAN_BUS and msg.address in (IONIQ6_STOCK_SCC_ADDR, *IONIQ6_STOCK_BSM):
          self.source_seen_count += 1
          self.latest_source_time = self.clock()
        elif msg.src == 0 and msg.address == IONIQ6_STOCK_HEARTBEAT_ADDR:
          self.heartbeat_seen_count += 1
    return packets


def query_ioniq6_adas(can_recv: CanRecvCallable, can_send: CanSendCallable, request: bytes, response: bytes) -> bool:
  """Validate the service-specific positive response from 0x738 on E-CAN.

  DiagnosticSessionControl may include four P2/P2* timing bytes after 0x50 xx;
  CommunicationControl has no corresponding response payload.
  """
  try:
    query = IsoTpParallelQuery(can_send, can_recv, IONIQ6_ECAN_BUS, [IONIQ6_ADAS_ADDR], [request], [response])
    payload = query.get_data(0.15, total_timeout=0.25).get((IONIQ6_ADAS_ADDR, None))
    if request in (b"\x10\x03", b"\x10\x01") and response == bytes((0x50, request[1])):
      return payload is not None and len(payload) in (0, 4)
    if request in (b"\x28\x01\x01", b"\x28\x00\x01") and response == bytes((0x68, request[1])):
      return payload == b""
    return False
  except Exception:
    return False


def _valid_canfd_crc(msg: CanData) -> bool:
  return len(msg.dat) >= 2 and int.from_bytes(msg.dat[:2], "little") == hkg_can_fd_checksum(msg.address, None, bytearray(msg.dat))


def _read_window(can_recv: CanRecvCallable, clock: Clock, duration: float, *, wait_for_one: bool = True) -> tuple[list[tuple[float, int, float]], set[int], set[int], int, bool, set[int]]:
  """Collect both stock ECU TX sources and required E-CAN input health."""
  source_samples: list[tuple[float, int, float]] = []
  healthy: set[int] = set()
  source_seen: set[int] = set()
  status_valid: set[int] = set()
  heartbeat_valid = 0
  heartbeat_seen = False
  deadline = clock() + duration
  while clock() < deadline:
    packets = can_recv(wait_for_one=wait_for_one)
    if not packets and not wait_for_one:
      # Polling preflight must also finish when the bus produces no frames.
      time.sleep(min(0.001, max(0.0, deadline - clock())))
    for packet in packets:
      received_at = clock()
      producer_ns = getattr(packet, "log_mono_time_ns", 0)
      sample_time = producer_ns * 1e-9 if producer_ns > 0 else received_at
      for msg in packet:
        if msg.src == 0 and msg.address == IONIQ6_STOCK_HEARTBEAT_ADDR:
          heartbeat_seen = True
          if len(msg.dat) == 24 and _valid_canfd_crc(msg):
            heartbeat_valid += 1
          continue
        if msg.src != IONIQ6_ECAN_BUS:
          continue
        if msg.address == IONIQ6_STOCK_SCC_ADDR:
          # Even a bad CRC proves the stock ECU is still transmitting.
          source_seen.add(msg.address)
          if len(msg.dat) == 32 and _valid_canfd_crc(msg):
            source_samples.append((sample_time, msg.dat[2], received_at))
        elif msg.address in IONIQ6_STOCK_BSM:
          source_seen.add(msg.address)
          if len(msg.dat) == IONIQ6_STOCK_BSM[msg.address] and _valid_canfd_crc(msg):
            status_valid.add(msg.address)
        elif msg.address in IONIQ6_REQUIRED_RX and len(msg.dat) == IONIQ6_REQUIRED_RX[msg.address]:
          if msg.address == 0x1CF or _valid_canfd_crc(msg):
            healthy.add(msg.address)
  return source_samples, healthy, source_seen, heartbeat_valid, heartbeat_seen, status_valid


def _measured_period(source_samples: list[tuple[float, int, float]]) -> float | None:
  if len(source_samples) < 4:
    return None
  # A queued old burst with valid producer spacing cannot establish current
  # stock source health. Fresh packets must reach this process across time.
  if source_samples[-1][2] - source_samples[0][2] < 0.08:
    return None
  if any((b[1] - a[1]) % 256 != 1 for a, b in zip(source_samples, source_samples[1:], strict=False)):
    return None
  periods = [b[0] - a[0] for a, b in zip(source_samples, source_samples[1:], strict=False)]
  period = statistics.median(periods)
  if not (0.012 <= period <= 0.030) or any(not (0.008 <= delta <= 0.050) for delta in periods):
    return None
  return period


def inspect_ioniq6_long_sources(can_recv: CanRecvCallable, clock: Clock = time.monotonic) -> HandoffResult:
  """Receive-only prerequisite check before selecting a longitudinal profile."""
  # Each attempt stands alone: never combine health or cadence across windows.
  # Drain fingerprint/retry backlog before measuring current SCC cadence.
  # Post-disable windows deliberately do not drain: any stock source matters.
  for _ in range(3):
    can_recv(wait_for_one=False)
    pre_times, pre_health, pre_sources, pre_heartbeat_valid, _, pre_status_valid = _read_window(
      can_recv, clock, 0.25, wait_for_one=False)
    period = _measured_period(pre_times)
    missing = []
    if period is None:
      missing.append('scc_period')
    if pre_heartbeat_valid < 4:
      missing.append('radar_heartbeat')
    if pre_health != IONIQ6_REQUIRED_RX.keys():
      missing.append('required_rx')
    if pre_sources != {IONIQ6_STOCK_SCC_ADDR, *IONIQ6_STOCK_BSM}:
      missing.append('stock_sources')
    if pre_status_valid != IONIQ6_STOCK_BSM.keys():
      missing.append('bsm_status')
    if not missing:
      return HandoffResult(HandoffOutcome.NOT_READY, 'preflight_ready', period)
  return HandoffResult(HandoffOutcome.NOT_READY, 'preflight_' + ','.join(missing))


def run_ioniq6_handoff(can_recv: CanRecvCallable, exchange: DiagnosticExchange, clock: Clock = time.monotonic) -> HandoffResult:
  """Resolve stock or long authority before constructing or publishing CarParams.

  The 50 Hz SCC source yields a provisional five-period silence/resumption
  window; these bounds require route calibration before feature activation.
  """
  preflight = inspect_ioniq6_long_sources(can_recv, clock)
  period = preflight.source_period
  if period is None:
    return preflight

  silence_window = min(max(5.0 * period, 0.10), 0.20)
  session_ack = exchange(b"\x10\x03", b"\x50\x03")
  disable_ack = session_ack and exchange(b"\x28\x01\x01", b"\x68\x01")
  if disable_ack:
    _, post_health, post_source_seen, _, post_heartbeat_seen, _ = _read_window(can_recv, clock, silence_window)
    if not post_source_seen and not post_heartbeat_seen and post_health == IONIQ6_REQUIRED_RX.keys():
      return HandoffResult(HandoffOutcome.CONFIRMED, "positive UDS response and observed SCC/heartbeat/BSM silence", period, True)

  # Even an unanswered 0x28 request might have taken effect. Restore both
  # normal-message TX and the normal diagnostic session before stock fallback.
  restore_tx_ack = exchange(b"\x28\x00\x01", b"\x68\x00")
  restore_session_ack = exchange(b"\x10\x01", b"\x50\x01")
  restored = restore_tx_ack and restore_session_ack
  restored_times, restored_health, restored_sources, restored_heartbeat_valid, _, restored_status_valid = _read_window(
    can_recv, clock, max(0.25, silence_window))
  if (restored and _measured_period(restored_times) is not None and restored_heartbeat_valid >= 4 and
      restored_health == IONIQ6_REQUIRED_RX.keys() and
      restored_sources == {IONIQ6_STOCK_SCC_ADDR, *IONIQ6_STOCK_BSM} and restored_status_valid == IONIQ6_STOCK_BSM.keys()):
    return HandoffResult(HandoffOutcome.STOCK, "restored ECU TX/session and verified stock SCC/heartbeat/BSM", period, disable_ack, True)
  return HandoffResult(HandoffOutcome.UNAVAILABLE, "ECU restore or stock SCC/heartbeat/BSM resumption unverified", period, disable_ack, restored)


def restore_ioniq6_adas(can_recv: CanRecvCallable, can_send: CanSendCallable, clock: Clock = time.monotonic) -> bool:
  """Abort a post-publication startup without ever claiming stock CP ownership."""
  observed_recv = ObservingCanRecv(can_recv, clock)
  restore_tx = query_ioniq6_adas(observed_recv, can_send, b"\x28\x00\x01", b"\x68\x00")
  restore_session = query_ioniq6_adas(observed_recv, can_send, b"\x10\x01", b"\x50\x01")
  samples, healthy, sources, heartbeat_valid, _, status_valid = _read_window(observed_recv, clock, 0.25)
  return (restore_tx and restore_session and _measured_period(samples) is not None and heartbeat_valid >= 4 and
          healthy == IONIQ6_REQUIRED_RX.keys() and sources == {IONIQ6_STOCK_SCC_ADDR, *IONIQ6_STOCK_BSM} and
          status_valid == IONIQ6_STOCK_BSM.keys())


class Ioniq6StartupKeepalive:
  """Maintain the acknowledged diagnostic session until Panda takes TX.

  A conservative 0.5-second diagnostic interval keeps the prepublication
  session alive before the controller's normal 1 Hz tester takes ownership.
  The 60-second startup bound is a development fail-closed limit, not a measured
  ECU session lifetime. Production enablement needs parked/device timing.
  """

  def __init__(self, can_send: CanSendCallable, restore: Callable[[], bool], on_abort: Callable[[], None],
               on_restore: Callable[[bool], None], clock: Clock = time.monotonic, max_startup_sec: float = 60.0):
    self.can_send = can_send
    self.restore = restore
    self.on_abort = on_abort
    self.on_restore = on_restore
    self.clock = clock
    self.max_startup_sec = max_startup_sec
    self.started_at = clock()
    self.next_tester_at = self.started_at
    self.stop_event = threading.Event()
    self.lock = threading.Lock()
    self.thread: threading.Thread | None = None
    self.completed = False

  def tick(self):
    with self.lock:
      if self.completed or self.stop_event.is_set():
        return
      now = self.clock()
      if now - self.started_at >= self.max_startup_sec:
        self._abort_locked()
      elif now >= self.next_tester_at:
        try:
          self.can_send([make_tester_present_msg(IONIQ6_ADAS_ADDR, IONIQ6_ECAN_BUS, suppress_response=True)])
          self.next_tester_at = now + 0.5
        except Exception:
          self._abort_locked()

  def _abort_locked(self):
    self.completed = True
    # The caller permanently suppresses controller TX before restoration.
    self.on_abort()
    try:
      restored = self.restore()
    except Exception:
      restored = False
    self.on_restore(restored)

  def start(self):
    def loop():
      while not self.stop_event.wait(0.05) and not self.completed:
        self.tick()

    self.tick()
    self.thread = threading.Thread(target=loop, name="ioniq6-prearm-tester", daemon=True)
    self.thread.start()

  def stop(self):
    # This is the TX ownership boundary: no keepalive or restore is in flight
    # when the caller is allowed to submit its first controller frame.
    self.stop_event.set()
    if self.thread is not None and self.thread is not threading.current_thread():
      self.thread.join()
    with self.lock:
      self.completed = True


def finalize_ioniq6_prepublication(stock_cp, long_cp, can_recv: CanRecvCallable, can_send: CanSendCallable,
                                  *, enabled: bool, is_release: bool, clock: Clock = time.monotonic):
  """Choose a prepared CP before CarInterface exists; never mutate it after arm.

  The DEBUG candidate must already be built and validated before any UDS request.
  """
  if not enabled or is_release or long_cp is None:
    return stock_cp, False, None
  raw = int(long_cp.safetyConfigs[-1].safetyParam)
  if not long_cp.openpilotLongitudinalControl or raw not in IONIQ6_DEBUG_LONG_PARAMS:
    raise ValueError("unreviewed Ioniq 6 longitudinal CarParams profile")

  observed_recv = ObservingCanRecv(can_recv, clock)
  result = run_ioniq6_handoff(
    observed_recv, lambda request, response: query_ioniq6_adas(observed_recv, can_send, request, response), clock)
  if result.outcome is HandoffOutcome.CONFIRMED:
    return long_cp, True, result
  if result.outcome is HandoffOutcome.UNAVAILABLE:
    # Card's usual passive setup will publish noOutput; do not advertise stock
    # cruise ownership when the stock SCC ECU may still be silent.
    stock_cp.dashcamOnly = True
  return stock_cp, False, result


def prepare_ioniq6_long_candidate(stock_cp, long_cp, *, enabled: bool, is_release: bool):
  """Select the immutable long CP without changing ECU communication yet."""
  if not enabled or is_release or long_cp is None:
    return stock_cp, False
  raw = int(long_cp.safetyConfigs[-1].safetyParam)
  if not long_cp.openpilotLongitudinalControl or raw not in IONIQ6_DEBUG_LONG_PARAMS:
    raise ValueError("unreviewed Ioniq 6 longitudinal CarParams profile")
  return long_cp, True


def confirm_ioniq6_prepared_takeover(can_recv: CanRecvCallable, can_send: CanSendCallable,
                                     clock: Clock = time.monotonic) -> HandoffResult:
  """Run the source/UDS transaction only when replacement TX can start."""
  observed_recv = ObservingCanRecv(can_recv, clock)
  return run_ioniq6_handoff(
    observed_recv, lambda request, response: query_ioniq6_adas(observed_recv, can_send, request, response), clock)
