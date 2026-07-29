import time
from dataclasses import dataclass
from enum import IntEnum

from cereal import car, custom

from opendbc.car import CanData, make_tester_present_msg
from opendbc.car.hyundai import hyundaicanfd
from opendbc.car.hyundai.interface import EV9_OPTIONAL_SAFETY_PARAM, EV9_PANDA_PREINIT_STATUS_VERSION, \
                                            EV9_PRODUCTION_SAFETY_PARAM, EV9PandaPreinitOwner, EV9PandaPreinitState, \
                                            invalidate_ev9_panda_preinit_handoff, \
                                            update_ev9_panda_preinit_handoff
from openpilot.common.swaglog import cloudlog


class EV9PreinitTakeoverState(IntEnum):
  INACTIVE = 0
  WAIT_SAFETY = 1
  CLAIMING = 2
  CONFIRMED = 3
  FAULTED = 4
  OFF = 5


class EV9PreinitOffSample(IntEnum):
  NONE = 0
  SAME_TERMINAL_LOW = 1
  SAME_TERMINAL_HIGH = 2
  FRESH_PENDING = 3
  FRESH_ACTIVE = 4
  FRESH_FAILED = 5


EV9_PREINIT_MANAGED_FRAMES = {
  (0, 0x100): (24, 0.01),
  (1, 0x12A): (16, 0.01),
  (1, 0xCB): (24, 0.01),
  (1, 0x160): (16, 0.02),
  (1, 0x161): (32, 0.05),
  (1, 0x162): (32, 0.05),
  (1, 0x1A0): (32, 0.02),
  (1, 0x1BA): (24, 0.05),
  (1, 0x1DA): (32, 1.0),
  (1, 0x1E0): (16, 0.05),
  (1, 0x1E5): (16, 0.05),
  (1, 0x1EA): (32, 0.05),
  (1, 0x200): (8, 0.05),
  (1, 0x345): (8, 0.2),
  (1, 0x38C): (32, 0.2),
}
EV9_PREINIT_CLAIM_RECEIPTS = set(EV9_PREINIT_MANAGED_FRAMES) | {(1, 0x730)}
EV9_PREINIT_RECOVERED_CAN3_IRQ_MAX = 8000
EV9_PREINIT_RECOVERED_INTERRUPT_LOAD_MAX = 0.75
EV9_PREINIT_RECOVERED_FAULT_DWELL_S = 2.25


def _ev9_preinit_valid_resident_panda(panda_states, handoff):
  residents = [panda_state for panda_state in (panda_states or ())
               if bool(getattr(getattr(panda_state, "ev9LongPreinitStatus", None), "resident", False))]
  if len(residents) != 1 or not handoff.resident or not handoff.sample_valid:
    return None

  panda_state = residents[0]
  status = panda_state.ev9LongPreinitStatus
  if (not bool(getattr(status, "valid", False)) or
      int(getattr(status, "version", -1)) != EV9_PANDA_PREINIT_STATUS_VERSION or
      int(getattr(status, "communicationType", -1)) != 0x01 or
      int(getattr(status, "state", -1)) != int(handoff.state)):
    return None
  return panda_state


def ev9_preinit_warm_start_pending(armed: bool, handoff, panda_states) -> bool:
  """Wait briefly for resident firmware to advance an ignition-high ABORTED sample."""
  if not armed or handoff.state != int(EV9PandaPreinitState.ABORTED):
    return False
  panda_state = _ev9_preinit_valid_resident_panda(panda_states, handoff)
  return panda_state is not None and bool(panda_state.ignitionLine or panda_state.ignitionCan)


def ev9_preinit_refreshed_takeover_allowed(armed: bool, handoff, long_init_succeeded: bool) -> bool:
  """Bind host takeover to the handoff sample CI.init actually consumed."""
  return armed and handoff.adoptable and long_init_succeeded


def ev9_preinit_terminal_ignition_on(handoff, panda_states) -> bool | None:
  """Read ignition from a valid terminal page-0 sample without requiring timing-page coherence."""
  if handoff.state not in (int(EV9PandaPreinitState.RESTORING), int(EV9PandaPreinitState.ABORTED)):
    return None
  panda_state = _ev9_preinit_valid_resident_panda(panda_states, handoff)
  if panda_state is None:
    return None
  return bool(panda_state.ignitionLine or panda_state.ignitionCan)


def ev9_preinit_resident_ignition_on(handoff, panda_states) -> bool | None:
  """Read ignition from any valid resident page before state/timing pages catch up."""
  panda_state = _ev9_preinit_valid_resident_panda(panda_states, handoff)
  if panda_state is None:
    return None
  return bool(panda_state.ignitionLine or panda_state.ignitionCan)


def ev9_preinit_classify_off_sample(handoff, panda_states, completed_cycle_started_us: int) -> EV9PreinitOffSample:
  """Classify one coherent publication relative to the completed ownership epoch."""
  if completed_cycle_started_us == 0:
    return EV9PreinitOffSample.NONE
  panda_state = _ev9_preinit_valid_resident_panda(panda_states, handoff)
  if panda_state is None:
    return EV9PreinitOffSample.NONE
  status = panda_state.ev9LongPreinitStatus
  cycle_started_us = int(getattr(status, "cycleStartedUs", 0))
  if not bool(getattr(status, "timingValid", False)) or cycle_started_us == 0:
    return EV9PreinitOffSample.NONE

  ignition_on = bool(panda_state.ignitionLine or panda_state.ignitionCan)
  if cycle_started_us == completed_cycle_started_us:
    if handoff.state in (int(EV9PandaPreinitState.RESTORING), int(EV9PandaPreinitState.ABORTED)):
      return EV9PreinitOffSample.SAME_TERMINAL_HIGH if ignition_on else EV9PreinitOffSample.SAME_TERMINAL_LOW
    return EV9PreinitOffSample.NONE

  if handoff.owner == EV9PandaPreinitOwner.PANDA and handoff.state == int(EV9PandaPreinitState.ACTIVE) and ignition_on:
    return EV9PreinitOffSample.FRESH_ACTIVE
  if handoff.owner == EV9PandaPreinitOwner.FAILED:
    return EV9PreinitOffSample.FRESH_FAILED
  if handoff.owner == EV9PandaPreinitOwner.PANDA_PENDING:
    return EV9PreinitOffSample.FRESH_PENDING
  return EV9PreinitOffSample.NONE


def ev9_preinit_expected_off_transition(takeover_state: EV9PreinitTakeoverState, off_sample: EV9PreinitOffSample,
                                        terminal_ignition_on: bool | None,
                                        resident_ignition_on: bool | None = None) -> bool:
  """Recognize the terminal edge of an adopted transaction before health deltas."""
  return takeover_state in (EV9PreinitTakeoverState.CLAIMING, EV9PreinitTakeoverState.CONFIRMED) and \
    (resident_ignition_on is False or
     off_sample in (EV9PreinitOffSample.SAME_TERMINAL_LOW, EV9PreinitOffSample.SAME_TERMINAL_HIGH) or
     (off_sample == EV9PreinitOffSample.NONE and terminal_ignition_on is not None))


def ev9_preinit_off_reclaim_ready(takeover_state: EV9PreinitTakeoverState, handoff, panda_states,
                                  completed_cycle_started_us: int) -> bool:
  """Require a coherent new resident ACTIVE epoch before leaving output-quiescent OFF."""
  return takeover_state == EV9PreinitTakeoverState.OFF and \
    ev9_preinit_classify_off_sample(handoff, panda_states, completed_cycle_started_us) == EV9PreinitOffSample.FRESH_ACTIVE


def ev9_preinit_off_reclaim_failed(takeover_state: EV9PreinitTakeoverState, handoff, panda_states,
                                   completed_cycle_started_us: int) -> bool:
  """Identify a coherent new epoch which terminated before Panda established ownership."""
  return takeover_state == EV9PreinitTakeoverState.OFF and \
    ev9_preinit_classify_off_sample(handoff, panda_states, completed_cycle_started_us) == EV9PreinitOffSample.FRESH_FAILED


def ensure_ev9_preinit_claim_retries(messages: list[CanData], templates: dict[tuple[int, int], CanData]) -> bool:
  """Retry every validated neutral tuple while Panda arbitrates its safe on-wire phase."""
  required = set(EV9_PREINIT_MANAGED_FRAMES)
  if set(templates) != required:
    return False
  if any(template.src != key[0] or template.address != key[1] or
         len(template.dat) != EV9_PREINIT_MANAGED_FRAMES[key][0]
         for key, template in templates.items()):
    return False

  present = set()
  for msg in messages:
    key = (msg.src, msg.address)
    if key in required and len(msg.dat) == EV9_PREINIT_MANAGED_FRAMES[key][0]:
      # CI.apply is authoritative for current neutral FCA/display fields. Keep
      # its newest exact body, while retaining the resident baseline for every
      # tuple that is not native-due in this batch.
      templates[key] = CanData(msg.address, bytes(msg.dat), msg.src)
      present.add(key)
  for key in EV9_PREINIT_MANAGED_FRAMES:
    template = templates[key]
    if key not in present:
      messages.append(CanData(template.address, bytes(template.dat), template.src))

  tester_present = b"\x02\x3e\x80".ljust(8, b"\x00")
  if not any(msg.src == 1 and msg.address == 0x730 and msg.dat == tester_present for msg in messages):
    messages.append(make_tester_present_msg(0x730, 1, suppress_response=True))
  return True


def collect_ev9_preinit_baselines(baselines: dict, messages: list[CanData], now: float) -> None:
  """Keep only valid resident TX receipts; physical and rejected frames cannot seed takeover."""
  for msg in messages:
    if not 0x80 <= msg.src < 0xC0:
      continue
    bus = msg.src - 0x80
    spec = EV9_PREINIT_MANAGED_FRAMES.get((bus, msg.address))
    dat = bytes(msg.dat)
    if spec is None or len(dat) != spec[0]:
      continue
    expected_crc = dat[0] | (dat[1] << 8)
    if hyundaicanfd.hkg_can_fd_checksum(msg.address, None, dat) != expected_crc:
      continue
    baselines[(bus, msg.address)] = (CanData(msg.address, dat, bus), now)


def complete_ev9_preinit_baselines(baselines: dict, now: float) -> list[CanData] | None:
  if set(baselines) != set(EV9_PREINIT_MANAGED_FRAMES):
    return None
  for key, (_, period) in EV9_PREINIT_MANAGED_FRAMES.items():
    _, observed_at = baselines[key]
    if now - observed_at > max(0.15, period * 2.5):
      return None
  return [baselines[key][0] for key in EV9_PREINIT_MANAGED_FRAMES]


def collect_ev9_preinit_claim_receipts(receipts: set, messages: list[CanData]) -> None:
  """Record only frames that Panda has moved from its software queue to a CAN core."""
  for msg in messages:
    if not 0x80 <= msg.src < 0xC0:
      continue
    bus = msg.src - 0x80
    dat = bytes(msg.dat)
    if (bus, msg.address) == (1, 0x730):
      if dat == b"\x02\x3e\x80".ljust(8, b"\x00"):
        receipts.add((bus, msg.address))
      continue
    spec = EV9_PREINIT_MANAGED_FRAMES.get((bus, msg.address))
    if spec is None or len(dat) != spec[0]:
      continue
    expected_crc = dat[0] | (dat[1] << 8)
    if hyundaicanfd.hkg_can_fd_checksum(msg.address, None, dat) == expected_crc:
      receipts.add((bus, msg.address))


def complete_ev9_preinit_claim_receipts(receipts: set) -> bool:
  return receipts == EV9_PREINIT_CLAIM_RECEIPTS


def ev9_preinit_parser_packets(packets: list[list[CanData]], now: float) -> list[tuple[int, list[CanData]]]:
  """Restore the timestamp envelope discarded by the fingerprint CAN callback."""
  now_nanos = int(now * 1e9)
  return [(now_nanos, packet) for packet in packets]


def ev9_preinit_recovered_fault_dwell_complete(allowed: bool, started_at: float | None, now: float) -> bool:
  return not allowed or (started_at is not None and now - started_at >= EV9_PREINIT_RECOVERED_FAULT_DWELL_S)


def _ev9_preinit_bus_healthy(can_state) -> bool:
  return (can_state is not None and not can_state.busOff and not can_state.errorWarning and
          not can_state.errorPassive and int(can_state.receiveErrorCnt) == 0 and
          int(can_state.transmitErrorCnt) == 0)


def ev9_preinit_panda_has_recoverable_can3_fault(panda_state) -> bool:
  faults = {str(fault) for fault in getattr(panda_state, "faults", ())}
  return (str(getattr(panda_state, "faultStatus", "")) == "faultTemp" and
          faults == {"interruptRateCan3"})


def ev9_preinit_panda_fault_recovered(panda_state) -> bool:
  """Recognize only the observed, ended EV9 CAN3 interrupt-rate storm."""
  can3 = getattr(panda_state, "canState2", None)
  irq0 = int(getattr(can3, "irq0CallRate", EV9_PREINIT_RECOVERED_CAN3_IRQ_MAX))
  irq1 = int(getattr(can3, "irq1CallRate", EV9_PREINIT_RECOVERED_CAN3_IRQ_MAX))
  return (ev9_preinit_panda_has_recoverable_can3_fault(panda_state) and can3 is not None and
          float(getattr(panda_state, "interruptLoad", 1.0)) < EV9_PREINIT_RECOVERED_INTERRUPT_LOAD_MAX and
          (irq0 > 0 or irq1 > 0) and irq0 < EV9_PREINIT_RECOVERED_CAN3_IRQ_MAX and
          irq1 < EV9_PREINIT_RECOVERED_CAN3_IRQ_MAX and
          _ev9_preinit_bus_healthy(can3))


def ev9_preinit_panda_fault_acceptable(panda_state) -> bool:
  faults = tuple(getattr(panda_state, "faults", ()))
  # Panda's temporary faultStatus is historical for the entire MCU boot; only
  # the faults bitmap is cleared by fault_recovered(). Route 1aa had an empty
  # bitmap with faultTemp still latched and was incorrectly rejected on every
  # warm start until the Panda was unplugged. A permanent status remains
  # fail-closed even if a malformed publication ever omits its bitmap.
  return ((str(getattr(panda_state, "faultStatus", "")) not in ("faultPerm", "2") and len(faults) == 0) or
          ev9_preinit_panda_fault_recovered(panda_state))


@dataclass
class EV9PreinitFaultHistory:
  initialized: bool = False
  recovered_fault_allowed: bool = False
  recovered_fault_cleared: bool = False

  @property
  def recovered_fault_authorized(self) -> bool:
    """Keep the startup-only recovered-fault exception one-way and cycle-bound."""
    return self.recovered_fault_allowed and not self.recovered_fault_cleared

  def update(self, panda_states, initialize: bool = False) -> bool:
    residents = [panda_state for panda_state in (panda_states or ())
                 if bool(getattr(getattr(panda_state, "ev9LongPreinitStatus", None), "resident", False))]
    if len(residents) != 1:
      return False

    panda_state = residents[0]
    recoverable_can3_fault = ev9_preinit_panda_has_recoverable_can3_fault(panda_state)
    clean = str(panda_state.faultStatus) not in ("faultPerm", "2") and len(panda_state.faults) == 0
    if not self.initialized:
      if not initialize:
        return clean
      self.initialized = True
      self.recovered_fault_allowed = recoverable_can3_fault

    if recoverable_can3_fault:
      return self.recovered_fault_authorized
    if clean:
      if self.recovered_fault_allowed:
        self.recovered_fault_cleared = True
      return True
    return False


def ev9_preinit_health_snapshot(panda_states) -> tuple[int, ...] | None:
  residents = [panda_state for panda_state in (panda_states or ())
               if bool(getattr(getattr(panda_state, "ev9LongPreinitStatus", None), "resident", False))]
  if len(residents) != 1:
    return None
  panda_state = residents[0]
  if any(not hasattr(panda_state, field) for field in ("rxBufferOverflow", "txBufferOverflow", "safetyTxBlocked")):
    return None
  # All values are monotonic for a Panda boot. safetyTxBlocked is a cumulative
  # safety-enforcement counter, not a live fault bit, so seal its value with
  # the other immutable takeover-health counters instead of requiring zero.
  snapshot = [int(panda_state.rxBufferOverflow), int(panda_state.txBufferOverflow),
              int(panda_state.safetyTxBlocked)]
  for index in range(3):
    can_state = getattr(panda_state, f"canState{index}", None)
    if can_state is None:
      return None
    snapshot.extend((int(getattr(can_state, "canCoreResetCnt", 0)),
                     int(can_state.busOffCnt), int(can_state.totalErrorCnt),
                     int(can_state.totalTxLostCnt), int(can_state.totalRxLostCnt)))
  return tuple(snapshot)


def ev9_preinit_health_unchanged(panda_states, baseline: tuple[int, ...] | None) -> bool:
  return baseline is not None and ev9_preinit_health_snapshot(panda_states) == baseline


EV9_PREINIT_SAFETY_TX_BLOCKED_INDEX = 2
# Route 187 produced three queued 100 Hz direct-angle frames and one 20 Hz
# companion at the permission edge. Eight permits one additional scheduler
# period of each stream without turning an arbitrary rejection burst into a
# recoverable transition.
EV9_PREINIT_SAFETY_WITHDRAWAL_MAX_BLOCKED = 8
EV9_PREINIT_REJECTED_RECEIPT_MAX_AGE_S = 1.0


def collect_ev9_preinit_rejected_outputs(rejections: list[tuple[float, CanData]],
                                         messages: list[CanData], now: float) -> None:
  """Retain a bounded receipt window for explaining a Panda safety-counter delta."""
  rejections[:] = [(observed_at, msg) for observed_at, msg in rejections
                  if now - observed_at <= EV9_PREINIT_REJECTED_RECEIPT_MAX_AGE_S]
  rejections.extend((now, msg) for msg in messages if 0xC0 <= msg.src < 0x100)


def _ev9_preinit_expected_lateral_rejection(msg: CanData) -> bool:
  """Recognize a non-emergency EV9 direct-angle safety rejection.

  Mode 2 is an active command. Mode 1 is the inactive physical-angle mirror;
  route 1a7 proved that the legacy 360-degree inactive clamp could reject it
  briefly while the driver turned through parking-lock angles.
  """
  dat = bytes(msg.dat)
  angle_mode = ((dat[3] >> 4) & 0xF) if len(dat) == 24 else 0
  return (msg.src - 0xC0, msg.address) == (1, 0xCB) and len(dat) == 24 and \
    angle_mode in (1, 2) and (dat[3] & 0xF) == 0 and \
    (angle_mode == 2 or dat[6] == 0) and (dat[7] & 0x3) == 0 and dat[8] == 0


def ev9_preinit_expected_safety_rejection(panda_states, baseline: tuple[int, ...] | None,
                                          rejected_outputs: list[tuple[float, CanData]]) -> tuple[int, ...] | None:
  """Return a bounded new baseline candidate for proven EV9 angle rejections.

  Normal Panda safety enforcement can reject an active 0xCB command at the
  vehicle-model angle limit or when lateral permission ends. Those packets
  never reach the vehicle, but the cumulative safety counter advances. CAN
  receipts and the 10 Hz Panda health page are asynchronous: a newer rejected
  receipt can already be queued while the published counter still reflects the
  preceding rejection. Accept that one-way publication lead only when every
  receipt is the exact non-emergency EV9 0xCB active/inactive shape, only the
  safety counter changed, and the complete bounded burst fits the allowance.
  A later identical Panda publication is still required before rebaselining.
  """
  current = ev9_preinit_health_snapshot(panda_states)
  if baseline is None or current is None or len(current) != len(baseline):
    return None

  index = EV9_PREINIT_SAFETY_TX_BLOCKED_INDEX
  delta = current[index] - baseline[index]
  immutable_match = current[:index] == baseline[:index] and current[index + 1:] == baseline[index + 1:]
  receipt_count = len(rejected_outputs)
  receipt_match = delta <= receipt_count <= EV9_PREINIT_SAFETY_WITHDRAWAL_MAX_BLOCKED and all(
    _ev9_preinit_expected_lateral_rejection(msg) for _, msg in rejected_outputs
  )
  if immutable_match and receipt_match and 0 < delta <= EV9_PREINIT_SAFETY_WITHDRAWAL_MAX_BLOCKED:
    return current
  return None


def ev9_preinit_safety_ready(panda_states, expected_model, expected_param: int,
                             expected_alternative_experience: int) -> bool:
  residents = []
  for panda_state in panda_states or ():
    status = getattr(panda_state, "ev9LongPreinitStatus", None)
    if status is not None and bool(getattr(status, "resident", False)):
      residents.append(panda_state)
  if len(residents) != 1:
    return False

  panda_state = residents[0]
  return (panda_state.safetyModel == expected_model and
          int(panda_state.safetyParam) == int(expected_param) and
          int(panda_state.alternativeExperience) == int(expected_alternative_experience) and
          ev9_preinit_panda_fault_acceptable(panda_state) and
          not panda_state.heartbeatLost and not panda_state.safetyRxChecksInvalid and
          int(panda_state.safetyRxInvalid) == 0 and
          _ev9_preinit_bus_healthy(getattr(panda_state, "canState0", None)) and
          _ev9_preinit_bus_healthy(getattr(panda_state, "canState1", None)) and
          _ev9_preinit_bus_healthy(getattr(panda_state, "canState2", None)))


def load_cached_car_params(params):
  """Read the newest usable cache without letting corrupt persistence crash card."""
  for key in ("CarParamsCache", "CarParamsPersistent"):
    raw = params.get(key)
    if raw is None:
      continue
    try:
      with car.CarParams.from_bytes(raw) as cached:
        return cached.as_builder()
    except Exception:
      cloudlog.exception(f"Ignoring corrupt {key}")
  return None


def load_cached_starpilot_car_params(params):
  raw = params.get("StarPilotCarParamsPersistent")
  if raw is None:
    return None
  try:
    with custom.StarPilotCarParams.from_bytes(raw) as cached:
      return cached.as_builder()
  except Exception:
    cloudlog.exception("Ignoring corrupt StarPilotCarParamsPersistent")
    return None


def normalize_ev9_cached_starpilot_safety(cached_params, cached_starpilot_params):
  """Strip stale cross-model safety flags before adopting a cached EV9 interface."""
  if cached_params is None or cached_starpilot_params is None or \
      str(getattr(cached_params, "carFingerprint", "")) != "KIA_EV9":
    return cached_starpilot_params

  safety_configs = list(getattr(cached_params, "safetyConfigs", ()))
  starpilot_safety_configs = list(getattr(cached_starpilot_params, "safetyConfigs", ()))
  if len(safety_configs) != 1 or len(starpilot_safety_configs) != 1 or \
      safety_configs[0].safetyModel != car.CarParams.SafetyModel.hyundaiCanfdEv9 or \
      (int(safety_configs[0].safetyParam) & ~EV9_OPTIONAL_SAFETY_PARAM) != EV9_PRODUCTION_SAFETY_PARAM:
    cloudlog.error("Ignoring StarPilotCarParamsPersistent with incompatible EV9 safety shape")
    return None

  expected_param = int(safety_configs[0].safetyParam) | \
    (int(starpilot_safety_configs[0].safetyParam) & EV9_OPTIONAL_SAFETY_PARAM)
  stale_param = int(starpilot_safety_configs[0].safetyParam)
  if stale_param != expected_param:
    cloudlog.warning(f"Canonicalizing cached EV9 StarPilot safetyParam {stale_param:#06x} -> {expected_param:#06x}")
    cached_starpilot_params.safetyConfigs[0].safetyParam = expected_param
  return cached_starpilot_params


def ev9_preinit_allows_fw_query(params, handoff) -> bool:
  """Do not let fallback fingerprinting compete with resident preinit UDS."""
  return not params.get_bool("EV9LongPreinitPanda") and not handoff.host_uds_veto


def revalidate_ev9_panda_preinit_handoff(sm, timeout_ms: int = 250):
  """Require a new ownership sample immediately before starting host takeover."""
  deadline = time.monotonic() + max(timeout_ms, 0) / 1000.0
  try:
    while True:
      remaining = deadline - time.monotonic()
      if remaining <= 0.0:
        break
      sm.update(max(1, int(remaining * 1000)))
      if sm.updated['pandaStates']:
        return update_ev9_panda_preinit_handoff(sm['pandaStates'])
  except Exception:
    cloudlog.exception("EV9 Panda preinit revalidation failed")
  return invalidate_ev9_panda_preinit_handoff("no fresh Panda preinit status before host takeover")
