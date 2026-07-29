import struct
from pathlib import Path

import pytest

from panda import DLC_TO_LEN, Panda
from panda.tests.libpanda import libpanda_py


ffi = libpanda_py.ffi
lpp = libpanda_py.libpanda

COLLECTING = 0
WAIT_SESSION = 1
WAIT_COMM_CONTROL = 2
WAIT_SUPPRESSION = 3
ACTIVE = 4
HANDOFF = 5
ABORTED = 6
RESTORING = 7
READY_PENDING_RESPONSE = 8

FLAG_SUPPRESSION_CONFIRMED = 0x04
FLAG_BRIDGE_ACTIVE = 0x08
FLAG_HOST_HANDOFF = 0x10
FLAG_DEADLINE_MISSED = 0x20
FLAG_RESTORE_SENT = 0x40
FLAG_INTERNAL_TX_REJECTED = 0x80
FP_STATIONARY = 0x80
LIFECYCLE_RELEASE_REQUESTED = 0x01
LIFECYCLE_RELEASE_COMPLETE = 0x02
LIFECYCLE_CAN_RESET_FAILED = 0x04
SAFETY_SILENT = 0
SAFETY_ELM327 = 3
SAFETY_ALLOUTPUT = 17
SAFETY_NOOUTPUT = 19

REPLAY = (
  (0x12A, 16), (0xCB, 24), (0x160, 16), (0x161, 32),
  (0x162, 32), (0x1A0, 32), (0x1BA, 24), (0x1DA, 32),
  (0x1E0, 16), (0x1E5, 16), (0x1EA, 32), (0x200, 8),
  (0x345, 8), (0x38C, 32),
)
FORCED_NEUTRAL_TEMPLATES = {
  0x12A: bytes.fromhex("00000002400008000000000000640000"),
  0xCB: bytes.fromhex("00000010fb3f000000000000000000000000000000000000"),
  0x160: bytes.fromhex("0000000100000000fffc0100a8001000"),
  0x161: bytes.fromhex("0000004100000000c0fff0c003000000000000000000000000ff000000000000"),
  0x162: bytes.fromhex("0000002700000000c0ff00000000000000000000000000000000000000000000"),
  0x1A0: bytes.fromhex("000000fef77f64000000000000080000fff33f1e0a000000fe07000000000000"),
  0x1BA: bytes.fromhex("00000000000000880200000000000000000000000000000f"),
  0x1E5: bytes.fromhex("00000000000000000000220300000080"),
}
EV9_HEARTBEAT_TEMPLATE = bytes.fromhex("00000000ff006f00e80400001201030055ffff0000000000")
EV9_STOCK_HEARTBEAT = bytes.fromhex("000000000500e6ff00000000183c000070ffff0000000000")
EV9_POWERTRAIN_IDENTITY = bytes.fromhex("00000001100030050000001000400040020100df013d01000000000000000000")
EV9_SCC_IDENTITY = bytes.fromhex("000000103501000000000000000000000000000000000000")


def status():
  ret = ffi.new("ev9_long_preinit_status_t *")
  lpp.ev9_test_get_status(ret)
  return ret[0]


def raw_timing():
  ret = ffi.new("ev9_long_preinit_timing_t *")
  lpp.ev9_test_get_timing(ret)
  return ret[0]


def timing():
  # Page zero explicitly starts/replaces the coherent two-page snapshot.
  status()
  return raw_timing()


def canfd(addr, bus, length, updates=None):
  identity_bodies = {
    (0x100, 0, 24): EV9_HEARTBEAT_TEMPLATE,
    (0x35, 1, 32): EV9_POWERTRAIN_IDENTITY,
    (0xCB, 1, 24): EV9_SCC_IDENTITY,
  }
  body = identity_bodies.get((addr, bus, length), bytes(length))
  packet = libpanda_py.make_CANPacket(addr, bus, body)
  packet.fd = 1
  for index, value in (updates or {}).items():
    packet.data[index] = value
  lpp.ev9_test_update_crc(packet)
  return packet


def classic_can(addr, bus, updates=None):
  packet = libpanda_py.make_CANPacket(addr, bus, bytes(8))
  for index, value in (updates or {}).items():
    packet.data[index] = value
  return packet


def generic_hda2_heartbeat():
  packet = libpanda_py.make_CANPacket(0x100, 0, bytes(24))
  packet.fd = 1
  lpp.ev9_test_update_crc(packet)
  return packet


def wheel_speeds(raw=0):
  return canfd(0xA0, 1, 24, {
    8: raw & 0xFF, 9: (raw >> 8) & 0x3F,
    10: raw & 0xFF, 11: (raw >> 8) & 0x3F,
    12: raw & 0xFF, 13: (raw >> 8) & 0x3F,
    14: raw & 0xFF, 15: (raw >> 8) & 0x3F,
  })


def diag(*data):
  return libpanda_py.make_CANPacket(0x738, 1, bytes(data).ljust(8, b"\x00"))


def diag_fd(*data):
  packet = diag(*data)
  packet.fd = 1
  return packet


def pop_bus(bus):
  queues = (lpp.tx1_q, lpp.tx2_q, lpp.tx3_q)
  packet = ffi.new("CANPacket_t *")
  ret = []
  while lpp.can_pop(queues[bus], packet):
    length = DLC_TO_LEN[packet.data_len_code]
    ret.append((packet.addr, bytes(ffi.buffer(packet.data, length)), bool(packet.fd)))
  return ret


def saturate_bus(bus):
  queues = (lpp.tx1_q, lpp.tx2_q, lpp.tx3_q)
  packet = libpanda_py.make_CANPacket(0x321, bus, b"\x00" * 8)
  count = 0
  while lpp.can_push(queues[bus], packet):
    count += 1
  assert count > 100


def feed_identity(state=0x45, base=1_000):
  # Route 144/16e/170 evidence: this fast tuple is available in the first
  # batch, while the old full fingerprint is too late for the READY race.
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), base)
  assert pop_bus(1) == []
  lpp.ev9_test_rx(canfd(0x100, 0, 24), base + 100)
  assert pop_bus(1) == []
  lpp.ev9_test_rx(wheel_speeds(), base + 150)
  assert pop_bus(1) == []
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: state}), base + 200)


def pop_diag(expected):
  sent = pop_bus(1)
  matching = [frame for frame in sent if frame[0] == 0x730 and frame[1][:len(expected)] == expected]
  assert len(matching) == 1
  return [frame for frame in sent if frame is not matching[0]]


def pop_single_diag(expected):
  assert pop_diag(expected) == []


def enter_wait_comm(base=1_000):
  feed_identity(base=base)
  assert status().state == WAIT_SESSION
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), base + 10_000)
  assert status().state == WAIT_COMM_CONTROL
  pop_single_diag(b"\x03\x28\x01\x01")
  assert pop_bus(0) == []
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  assert not status().flags & FLAG_SUPPRESSION_CONFIRMED
  assert timing().comm_control_us == base + 10_000
  assert timing().first_replacement_us == 0


def expire_unanswered_session(first_timeout_us=51_200):
  lpp.ev9_test_tick(first_timeout_us, False)
  assert status().state == WAIT_SESSION
  assert status().attempts == 2
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_tick(first_timeout_us + 50_000, False)
  assert status().state == ABORTED


@pytest.fixture(autouse=True)
def reset_preinit():
  lpp.ev9_test_init()


def test_fast_tuple_exact_responses_and_neutral_bridge():
  feed_identity(state=0x45)
  assert status().state == WAIT_SESSION
  assert status().fingerprint & 0x07 == 0x07
  pop_single_diag(b"\x02\x10\x03")

  # Exact 50 03 chains 28 01 01 in the same RX hook.
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 10_000)
  pop_single_diag(b"\x03\x28\x01\x01")
  assert status().state == WAIT_COMM_CONTROL
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  assert not status().flags & FLAG_SUPPRESSION_CONFIRMED

  # 0x45 is eligible and not a terminal READY state.
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x45}), 15_000)
  assert status().state == WAIT_COMM_CONTROL

  # Exact 68 01 is the only transition into suppression confirmation. Missing
  # fallbacks are seeded here with their normal periods rather than burst.
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 20_000)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & FLAG_BRIDGE_ACTIVE
  radar_tx = pop_bus(0)
  ecan_tx = pop_bus(1)
  assert any(addr == 0x100 for addr, _, _ in radar_tx)
  assert {addr for addr, _, _ in ecan_tx} == {0xCB}
  assert all(addr != 0x57A for addr, _, _ in radar_tx + ecan_tx)
  assert not lpp.ev9_test_internal_bridge_allowed(canfd(0x57A, 1, 24))

  lpp.ev9_test_tick(80_000, False)
  assert status().state == ACTIVE
  assert status().flags & FLAG_SUPPRESSION_CONFIRMED
  ecan_tx += pop_bus(1)
  by_addr = {addr: dat for addr, dat, _ in ecan_tx}
  for addr, template in FORCED_NEUTRAL_TEMPLATES.items():
    assert by_addr[addr][3:] == template[3:]

  # The synthesized SCC command is neutral, and 0x57A is never internally
  # allowlisted even though the physical ECU keeps publishing it under 0x28.
  scc = by_addr[0x1A0]
  assert ((int.from_bytes(scc, "little") >> 68) & 0x7) == 0
  assert ((int.from_bytes(scc, "little") >> 128) & 0x7FF) == 1023
  assert ((int.from_bytes(scc, "little") >> 140) & 0x7FF) == 1023
  assert timing().first_replacement_us == 20_000
  assert timing().suppression_confirmed_us == 80_000


def test_knockout_requires_fresh_stationary_wheel_speed_proof():
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 1_000)
  lpp.ev9_test_rx(canfd(0x100, 0, 24), 1_100)
  lpp.ev9_test_rx(wheel_speeds(13), 1_150)
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x45}), 1_200)

  assert status().state == COLLECTING
  assert not status().fingerprint & FP_STATIONARY
  assert status().attempts == 0
  assert pop_bus(1) == []

  lpp.ev9_test_rx(wheel_speeds(12), 1_250)
  assert status().state == WAIT_SESSION
  assert status().fingerprint & FP_STATIONARY
  pop_single_diag(b"\x02\x10\x03")


def test_start_cue_deadline_is_not_reset_when_stationary_identity_completes():
  lpp.ev9_test_rx(canfd(0x175, 1, 24, {10: 0x02}), 1_000)
  feed_identity(base=2_000)
  assert status().state == WAIT_SESSION
  assert status().trigger == 3  # DRIVER_BRAKE
  assert status().trigger_us == 1_000
  assert timing().session_request_us == 2_200
  pop_single_diag(b"\x02\x10\x03")

  lpp.ev9_test_init()
  lpp.ev9_test_rx(canfd(0x175, 1, 24, {10: 0x02}), 1_000)
  feed_identity(base=302_000)
  assert status().state == ABORTED
  assert status().flags & FLAG_DEADLINE_MISSED
  assert timing().session_request_us == 0
  assert pop_bus(1) == []


def test_physical_ignition_dispatches_before_pre_ready_without_brake():
  # Routes 191/192/194/195/197/198 proved that waiting for pre-READY loses to
  # temporary ELM327 safety. Physical ignition establishes the deadline, and
  # the first complete stationary identity dispatches without a brake edge.
  lpp.ev9_test_tick(1_000, True)
  feed_identity(state=0x01, base=100_000)
  assert status().state == WAIT_SESSION
  assert status().attempts == 1
  assert status().trigger == 2  # IGNITION
  assert status().trigger_us == 1_000
  assert timing().session_request_us == 100_200
  pop_single_diag(b"\x02\x10\x03")

  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 120_000)
  pop_single_diag(b"\x03\x28\x01\x01")
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 140_000)
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x51}), 429_000)
  assert status().state == ACTIVE
  assert status().attempts == 1
  assert timing().ready_us == 429_000


def test_fob_identity_delay_keeps_response_sequence_inside_global_deadline():
  # Route 19c: raw ignition preceded complete stationary identity by 177.443
  # ms. Exact 50 03 arrived at +194.592 ms, leaving too little time for 68 01
  # under the old 200 ms policy despite healthy P2 windows and distant READY.
  lpp.ev9_test_tick_once(1_000, True)
  feed_identity(state=0x01, base=178_243)
  assert timing().session_request_us == 178_443
  pop_single_diag(b"\x02\x10\x03")

  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 195_592)
  assert timing().comm_control_us == 195_592
  pop_single_diag(b"\x03\x28\x01\x01")

  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 215_000)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & FLAG_BRIDGE_ACTIVE
  assert timing().comm_control_response_us == 215_000


def test_remote_wake_dispatches_on_ignition_rise_without_brake_or_door():
  # Routes 194/195: fob remote start supplies the same 0x384 remote-wake fact
  # that boots the comma, then raises physical ignition with no brake or door
  # edge. Dispatch at that rise instead of waiting for pre-READY under ELM327.
  feed_identity(state=0x01, base=100_000)
  assert status().state == COLLECTING
  assert pop_bus(1) == []

  lpp.ev9_test_rx(classic_can(0x384, 1, {3: 0x01}), 200_000)
  lpp.ev9_test_rx(wheel_speeds(), 219_999)
  assert status().state == COLLECTING
  assert pop_bus(1) == []

  lpp.ev9_test_tick(220_000, True)
  assert status().state == WAIT_SESSION
  assert status().trigger == 5  # CLIMATE_TAKEOVER
  assert status().trigger_us == 220_000
  assert timing().session_request_us == 220_000
  pop_single_diag(b"\x02\x10\x03")


def test_hkg_remote_wake_latch_survives_first_canfd_cycle_reset():
  # Route 197: the classic 0x384 wake arrived before the first valid CAN-FD
  # frame. Resident cycle rearm cleared the local timestamp, but the selected
  # HKG boot latch must remain authoritative through the ignition edge.
  lpp.ev9_test_rx(classic_can(0x384, 1, {3: 0x01}), 100_000)
  lpp.ev9_test_reset_cycle()
  feed_identity(state=0x01, base=110_000)
  lpp.ev9_test_rx(wheel_speeds(), 119_999)

  lpp.ev9_test_tick(120_000, True)
  assert status().state == WAIT_SESSION
  assert status().trigger == 5
  assert status().trigger_us == 120_000
  assert timing().session_request_us == 120_000
  pop_single_diag(b"\x02\x10\x03")


def test_fob_ignition_preempts_elm_before_identity_then_dispatches_from_rx():
  # Pre-ignition capture 3 / route 199: body CAN woke ~4.08 s before ignition,
  # pandad entered ELM327, and raw ignition preceded its publication by only
  # ~103 ms while the resident fingerprint was still empty.
  assert lpp.set_safety_hooks(SAFETY_ELM327, 1) == 0
  lpp.ev9_test_tick_once(1_000, True)
  assert lpp.ev9_test_current_safety_mode() == SAFETY_NOOUTPUT
  assert status().state == COLLECTING
  assert status().trigger == 2  # IGNITION
  assert status().fingerprint == 0
  assert timing().session_request_us == 0

  feed_identity(state=0x01, base=2_000)
  assert status().state == WAIT_SESSION
  assert status().trigger == 2
  assert status().trigger_us == 1_000
  assert timing().session_request_us == 2_200
  pop_single_diag(b"\x02\x10\x03")


def test_elm_is_not_preempted_by_body_wake_without_ignition():
  assert lpp.set_safety_hooks(SAFETY_ELM327, 1) == 0
  feed_identity(state=0x01, base=1_000)
  lpp.ev9_test_tick_once(2_000, False)

  assert lpp.ev9_test_current_safety_mode() == SAFETY_ELM327
  assert status().state == COLLECTING
  assert status().trigger == 0
  assert timing().session_request_us == 0
  assert pop_bus(1) == []


def test_late_host_elm_query_is_blocked_during_ignition_collection():
  lpp.ev9_test_tick_once(1_000, True)
  assert status().state == COLLECTING
  assert status().trigger == 2  # IGNITION
  assert not lpp.ev9_test_usb_request_allowed(0xDC, SAFETY_ELM327, 1)

  # With the late host mutation rejected, identity can dispatch directly from
  # RX while the resident remains in stable NOOUTPUT.
  feed_identity(state=0x01, base=2_000)
  assert status().state == WAIT_SESSION
  assert status().attempts == 1
  assert timing().session_request_us == 2_200
  pop_single_diag(b"\x02\x10\x03")


def test_host_elm_query_remains_allowed_without_start_or_after_terminal_ready():
  assert lpp.ev9_test_usb_request_allowed(0xDC, SAFETY_ELM327, 1)

  lpp.ev9_test_tick_once(1_000, True)
  feed_identity(state=0x51, base=2_000)
  assert status().state == ABORTED
  assert lpp.ev9_test_usb_request_allowed(0xDC, SAFETY_ELM327, 1)


def test_ignition_preemption_never_knocks_out_terminal_ready_identity():
  assert lpp.set_safety_hooks(SAFETY_ELM327, 1) == 0
  lpp.ev9_test_tick_once(1_000, True)
  assert lpp.ev9_test_current_safety_mode() == SAFETY_NOOUTPUT
  feed_identity(state=0x51, base=2_000)

  assert status().state == ABORTED
  assert status().attempts == 0
  assert timing().session_request_us == 0
  assert pop_bus(1) == []


def test_climate_takeover_survives_temporary_elm327_safety():
  assert lpp.set_safety_hooks(SAFETY_ELM327, 1) == 0
  feed_identity(state=0x01, base=100_000)
  lpp.ev9_test_rx(classic_can(0x384, 1, {3: 0x01}), 200_000)
  lpp.ev9_test_rx(wheel_speeds(), 219_999)

  # The first firmware-main pass records the ignition-qualified takeover and
  # requests NOOUTPUT; the next zero-elapsed pass dispatches after CAN reset.
  lpp.ev9_test_tick(220_000, True)
  assert status().state == WAIT_SESSION
  assert status().trigger == 5
  assert timing().session_request_us == 220_000
  pop_single_diag(b"\x02\x10\x03")


def test_stale_remote_wake_falls_back_to_physical_ignition_trigger():
  feed_identity(state=0x01, base=100_000)
  lpp.ev9_test_rx(classic_can(0x384, 1, {3: 0x01}), 1_000)
  # The production 1 Hz HKG latch expires independently of resident timing.
  lpp.ev9_test_rx(classic_can(0x384, 1, {3: 0x00}), 3_100_000)

  lpp.ev9_test_rx(wheel_speeds(), 3_100_000)
  lpp.ev9_test_tick(3_100_001, True)
  assert status().state == WAIT_SESSION
  assert status().trigger == 2
  assert status().attempts == 1
  assert timing().session_request_us == 3_100_001
  pop_single_diag(b"\x02\x10\x03")


def test_remote_wake_remains_passive_without_ignition():
  feed_identity(state=0x01, base=100_000)
  lpp.ev9_test_rx(classic_can(0x384, 1, {3: 0x01}), 200_000)
  lpp.ev9_test_tick(220_000, False)

  assert status().state == COLLECTING
  assert status().trigger == 0
  assert status().attempts == 0
  assert timing().session_request_us == 0
  assert pop_bus(1) == []


def test_remote_wake_still_requires_fresh_stationary_proof():
  feed_identity(state=0x01, base=100_000)
  lpp.ev9_test_rx(classic_can(0x384, 1, {3: 0x01}), 200_000)
  lpp.ev9_test_rx(wheel_speeds(13), 219_999)
  lpp.ev9_test_tick(220_000, True)

  assert status().state == COLLECTING
  assert status().trigger == 5
  assert status().attempts == 0
  assert timing().session_request_us == 0
  assert pop_bus(1) == []


def test_pre_ready_never_retimes_driver_brake_or_in_flight_attempt():
  lpp.ev9_test_rx(canfd(0x175, 1, 24, {10: 0x02}), 1_000)
  lpp.ev9_test_tick(1_001, True)
  feed_identity(state=0x01, base=2_000)
  assert status().state == WAIT_SESSION
  assert status().trigger == 3  # DRIVER_BRAKE
  assert status().trigger_us == 1_000
  assert timing().session_request_us == 2_200
  pop_single_diag(b"\x02\x10\x03")

  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x45}), 10_000)
  assert status().state == WAIT_SESSION
  assert status().trigger == 3
  assert status().trigger_us == 1_000
  assert timing().session_request_us == 2_200
  assert pop_bus(1) == []


def test_motion_before_session_response_vetoes_communication_control():
  feed_identity()
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_rx(wheel_speeds(13), 5_000)
  assert status().state == WAIT_SESSION

  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 10_000)
  assert status().state == ABORTED
  sent = pop_bus(1)
  assert all(dat[:4] != b"\x03\x28\x01\x01" for _, dat, _ in sent)
  assert [dat[:3] for addr, dat, _ in sent if addr == 0x730] == [b"\x02\x10\x01"]


def test_live_oem_streams_are_never_duplicated_before_exact_68():
  feed_identity()
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 10_000)
  pop_single_diag(b"\x03\x28\x01\x01")

  # Capture shape from the failed trial: OEM streams continue inside the P2
  # window. Panda must remain diagnostic-only instead of publishing a second
  # body at the same address/counter.
  for now in (20_000, 30_000, 40_000, 45_000):
    lpp.ev9_test_rx(canfd(0x100, 0, 24), now)
    lpp.ev9_test_rx(canfd(0xCB, 1, 24), now)
    lpp.ev9_test_rx(canfd(0x12A, 1, 16), now)
    lpp.ev9_test_rx(canfd(0x160, 1, 16), now)
    lpp.ev9_test_rx(canfd(0x1A0, 1, 32), now)
    assert pop_bus(0) == []
    assert pop_bus(1) == []
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  assert timing().first_replacement_us == 0

  # Exact ownership starts the bridge, still respecting each physical stream's
  # next deadline rather than colliding at the response instant.
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 50_000)
  assert status().state == WAIT_SUPPRESSION
  assert pop_bus(0) == []
  assert pop_bus(1) == []
  lpp.ev9_test_tick(55_000, False)
  assert any(addr == 0x100 for addr, _, _ in pop_bus(0))
  assert {addr for addr, _, _ in pop_bus(1)} == {0x12A, 0xCB}


def test_pre_ready_request_accepts_post_ready_response():
  enter_wait_comm()
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x51}), 20_000)
  assert status().state == READY_PENDING_RESPONSE
  assert status().ready_us == 20_000

  # Acceptance is determined by when 0x28 was requested, not whether its exact
  # positive response is scheduled just after the terminal frame.
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 30_000)
  assert status().state == WAIT_SUPPRESSION
  assert not status().flags & (FLAG_DEADLINE_MISSED | FLAG_RESTORE_SENT)
  lpp.ev9_test_tick(90_000, False)
  assert status().state == ACTIVE


def test_ready_without_positive_response_never_retries_disable_after_ready():
  enter_wait_comm()
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x51}), 20_000)
  assert status().state == READY_PENDING_RESPONSE
  pop_bus(0)
  pop_bus(1)

  lpp.ev9_test_tick(60_999, False)
  assert status().state == READY_PENDING_RESPONSE
  assert all(dat[:4] != b"\x03\x28\x01\x01" for _, dat, _ in pop_bus(1))

  lpp.ev9_test_tick(301_200, False)
  assert status().state == RESTORING
  assert pop_bus(1) == []
  lpp.ev9_test_tick(351_199, False)
  assert pop_bus(1) == []
  lpp.ev9_test_tick(351_200, False)
  sent = pop_bus(1)
  assert any(dat[:4] == b"\x03\x28\x00\x01" for _, dat, _ in sent)
  assert all(dat[:4] != b"\x03\x28\x01\x01" for _, dat, _ in sent)


def test_only_exact_68_01_activates_bridge_and_tester_present_is_1hz():
  enter_wait_comm()
  lpp.ev9_test_rx(diag(3, 0x68, 0x01, 0), 15_000)
  assert status().state == WAIT_COMM_CONTROL
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  assert not status().flags & FLAG_SUPPRESSION_CONFIRMED
  lpp.ev9_test_rx(diag(2, 0x68, 0x00), 16_000)
  assert status().state == WAIT_COMM_CONTROL
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 20_000)
  assert status().state == WAIT_SUPPRESSION
  pop_bus(0)
  pop_bus(1)
  lpp.ev9_test_tick(80_000, False)
  assert status().state == ACTIVE
  pop_bus(0)
  pop_bus(1)

  lpp.ev9_test_tick(1_019_999, False)
  assert all(dat[:3] != b"\x02\x3e\x80" for _, dat, _ in pop_bus(1))
  lpp.ev9_test_tick(1_020_000, False)
  assert any(dat[:3] == b"\x02\x3e\x80" for _, dat, _ in pop_bus(1))
  assert not status().flags & FLAG_DEADLINE_MISSED


def test_unrelated_nrc_never_drops_suppressed_or_restoring_bridge():
  enter_wait_comm()
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 20_000)
  lpp.ev9_test_rx(diag(3, 0x7F, 0x28, 0x22), 21_000)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & FLAG_BRIDGE_ACTIVE

  lpp.ev9_test_tick(80_000, False)
  assert status().state == ACTIVE
  lpp.ev9_test_rx(diag(3, 0x7F, 0x28, 0x22), 81_000)
  assert status().state == ACTIVE
  assert status().flags & FLAG_BRIDGE_ACTIVE

  # Sustained stock reappearance enters live restore containment. A negative
  # reply to restore must not abort while the ECU may still be suppressed.
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 100_000)
  pop_bus(0)
  pop_bus(1)
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 200_001)
  assert status().state == RESTORING
  lpp.ev9_test_tick(250_001, True)
  pop_single_diag(b"\x03\x28\x00\x01")
  restore_flags = status().flags
  lpp.ev9_test_rx(diag(3, 0x7F, 0x28, 0x22), 251_000)
  assert status().state == RESTORING
  assert status().flags == restore_flags


def test_unrelated_diagnostic_reply_does_not_overwrite_preinit_outcome():
  enter_wait_comm()
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 20_000)
  assert status().last_response == 0x68
  assert status().last_nrc == 0
  lpp.ev9_test_tick(80_000, False)
  assert status().state == ACTIVE

  # Later firmware-identification traffic shares 0x738 but is not a response
  # to this state machine's in-flight service.
  lpp.ev9_test_rx(diag(4, 0x62, 0xF1, 0xB0), 81_000)
  assert status().state == ACTIVE
  assert status().last_response == 0x68
  assert status().last_nrc == 0


def test_route144_ready_tuple_never_starts_diagnostics():
  feed_identity(state=0x51)
  assert status().state == ABORTED
  assert status().ready_us == 1_200
  assert pop_bus(1) == []

  lpp.ev9_test_tick(2_000, True)
  lpp.ev9_test_rx(canfd(0x175, 1, 24, {10: 0x02}), 3_000)
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 4_000)
  lpp.ev9_test_tick(100_000, True)
  assert status().state == ABORTED
  assert timing().session_request_us == 0
  assert timing().comm_control_us == 0
  assert pop_bus(0) == []
  assert pop_bus(1) == []


def test_ready_before_session_response_never_sends_communication_control():
  feed_identity()
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x55}), 5_000)
  assert status().state == ABORTED
  pop_single_diag(b"\x02\x10\x01")

  # A late/malformed session response cannot originate 0x28 after READY.
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 10_000)
  assert pop_bus(1) == []
  assert status().state == ABORTED


def test_nrc22_then_ready_aborts_without_retrying_28():
  enter_wait_comm()
  lpp.ev9_test_rx(diag(3, 0x7F, 0x28, 0x22), 20_000)
  assert status().state == WAIT_COMM_CONTROL
  assert pop_bus(1) == []
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x51}), 25_000)
  assert status().state == ABORTED
  sent = pop_bus(1)
  assert any(dat[:3] == b"\x02\x10\x01" for _, dat, _ in sent)
  assert all(dat[:4] != b"\x03\x28\x01\x01" for _, dat, _ in sent)


def test_completed_nrc_retry_does_not_seed_unseen_fallbacks_as_p2_loss():
  enter_wait_comm()
  lpp.ev9_test_rx(diag(3, 0x7F, 0x28, 0x22), 20_000)
  pop_bus(0)
  assert pop_bus(1) == []

  # A completed negative closes correlation for the old request.
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 25_000)
  assert status().state == WAIT_COMM_CONTROL
  assert status().last_response == 0x7F
  assert status().last_nrc == 0x22
  assert not status().flags & FLAG_BRIDGE_ACTIVE

  lpp.ev9_test_tick(29_999, False)
  assert pop_bus(1) == []
  lpp.ev9_test_tick(30_000, False)
  assert pop_diag(b"\x03\x28\x01\x01") == []

  # An explicit NRC is not ownership; no replacement stream starts while the
  # bounded diagnostic retry remains unresolved.
  lpp.ev9_test_tick(79_999, False)
  assert pop_bus(1) == []
  lpp.ev9_test_tick(80_000, False)
  assert pop_bus(1) == []
  assert status().state == READY_PENDING_RESPONSE


def test_session_nrc22_retries_are_bounded():
  feed_identity()
  pop_single_diag(b"\x02\x10\x03")
  for response_us, retry_us in ((10_000, 20_000), (30_000, 40_000)):
    lpp.ev9_test_rx(diag(3, 0x7F, 0x10, 0x22), response_us)
    assert pop_bus(1) == []
    lpp.ev9_test_tick(retry_us, False)
    pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_rx(diag(3, 0x7F, 0x10, 0x22), 50_000)
  assert status().state == ABORTED
  assert pop_bus(1) == []


def test_rejected_nrc_retry_cannot_reopen_response_correlation():
  enter_wait_comm()
  lpp.ev9_test_rx(diag(3, 0x7F, 0x28, 0x22), 20_000)
  saturate_bus(1)
  lpp.ev9_test_tick(30_000, False)
  assert status().state == WAIT_COMM_CONTROL
  assert status().attempts == 1
  assert status().last_response == 0x7F
  assert status().last_nrc == 0x22

  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x51}), 35_000)
  assert status().state == ABORTED
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  pop_bus(1)
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 40_000)
  assert status().state == ABORTED
  assert not status().flags & FLAG_BRIDGE_ACTIVE


def test_session_positive_requires_successfully_enqueued_request():
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 1_000)
  lpp.ev9_test_rx(canfd(0x100, 0, 24), 1_100)
  lpp.ev9_test_rx(wheel_speeds(), 1_150)
  saturate_bus(1)
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x45}), 1_200)
  assert status().state == WAIT_SESSION
  assert status().attempts == 0
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 2_000)
  assert status().state == WAIT_SESSION
  assert timing().session_response_us == 0
  assert timing().comm_control_us == 0
  assert not status().flags & FLAG_BRIDGE_ACTIVE


def test_session_positive_at_global_deadline_cannot_originate_disable():
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 1_000)
  lpp.ev9_test_rx(canfd(0x100, 0, 24), 1_100)
  lpp.ev9_test_rx(wheel_speeds(), 1_150)
  saturate_bus(1)
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x45}), 1_200)
  for now in (51_200, 101_200, 151_200, 201_200):
    lpp.ev9_test_rx(wheel_speeds(), now - 1)
    lpp.ev9_test_tick(now, False)
  pop_bus(1)

  # A late successful enqueue can still have a P2-valid 50 03 exactly at the
  # cycle deadline. The response must not synchronously create 28 01 01.
  lpp.ev9_test_rx(wheel_speeds(), 251_201)
  lpp.ev9_test_tick(251_202, False)
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 301_200)
  assert status().state == ABORTED
  assert timing().session_response_us == 0
  assert timing().comm_control_us == 0
  sent = pop_bus(1)
  assert all(dat[:4] != b"\x03\x28\x01\x01" for _, dat, _ in sent)


def test_malformed_and_missing_session_response_abort_bounded():
  feed_identity()
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_rx(diag(6, 0x50, 0x02, 0, 0x32, 1, 0xF4), 10_000)
  assert pop_bus(1) == []

  lpp.ev9_test_tick(51_200, False)
  assert status().state == WAIT_SESSION
  assert status().attempts == 2
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_tick(101_200, False)
  assert status().state == ABORTED
  assert status().attempts == 2
  pop_single_diag(b"\x02\x10\x01")


def test_direct_identity_enqueues_session_at_rx_boundary_with_full_p2_window():
  lpp.ev9_test_rx_isr_only(canfd(0xCB, 1, 24), 1_000)
  lpp.ev9_test_rx_isr_only(canfd(0x100, 0, 24), 1_100)
  lpp.ev9_test_rx_isr_only(wheel_speeds(), 1_150)
  lpp.ev9_test_rx_isr_only(canfd(0x35, 1, 32, {3: 0x45}), 1_200)

  # The restored route-17a/17b path has no deferred-main timestamp skew: the
  # pre-READY confirmation and physical diagnostic enqueue share the RX
  # boundary. Stationary identity alone is intentionally passive.
  assert status().state == WAIT_SESSION
  assert status().trigger == 4  # PRE_READY
  assert status().trigger_us == 1_200
  assert timing().session_request_us == 1_200
  pop_single_diag(b"\x02\x10\x03")

  lpp.ev9_test_tick(51_199, False)
  assert status().state == WAIT_SESSION
  assert pop_bus(1) == []
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 51_199)
  assert status().state == WAIT_COMM_CONTROL
  pop_single_diag(b"\x03\x28\x01\x01")


def test_canfd_marked_ev9_diag_responses_follow_working_route17_path():
  feed_identity()
  pop_single_diag(b"\x02\x10\x03")

  # The live direct-RX capture returned this exact 8-byte 50 03 body with
  # packet.fd set. The route-17a/17b firmware accepted either controller
  # format and immediately chained CommunicationControl from the response.
  lpp.ev9_test_rx_isr_only(diag_fd(6, 0x50, 0x03, 0, 0x32, 1, 0xF4, 0xAA), 30_000)
  assert status().state == WAIT_COMM_CONTROL
  assert timing().session_response_us == 30_000
  pop_single_diag(b"\x03\x28\x01\x01")

  lpp.ev9_test_rx_isr_only(diag_fd(2, 0x68, 0x01, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA), 50_000)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & FLAG_BRIDGE_ACTIVE
  assert timing().comm_control_response_us == 50_000


def test_one_unanswered_session_retry_can_complete_knockout_without_overlap():
  feed_identity()
  pop_single_diag(b"\x02\x10\x03")

  # The retry begins only after the first complete P2 interval. A successful
  # second session request can still advance to CommunicationControl only from
  # an exact positive response.
  lpp.ev9_test_tick(51_200, False)
  assert status().state == WAIT_SESSION
  assert status().attempts == 2
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 70_000)
  assert status().state == WAIT_COMM_CONTROL
  assert status().attempts == 1
  pop_single_diag(b"\x03\x28\x01\x01")
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 90_000)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & FLAG_BRIDGE_ACTIVE


@pytest.mark.parametrize("response_us", [
  301_198,  # trigger -> 68 = 299,998 us
  301_200,  # exact positive at hard policy boundary still proves ownership
])
def test_global_diagnostic_deadline(response_us):
  feed_identity()
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 10_000)
  pop_single_diag(b"\x03\x28\x01\x01")
  lpp.ev9_test_tick(60_000, False)
  assert status().state == READY_PENDING_RESPONSE
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), response_us)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & FLAG_BRIDGE_ACTIVE
  assert timing().comm_control_response_us == response_us
  assert timing().first_replacement_us == response_us
  assert status().flags & FLAG_DEADLINE_MISSED  # both responses are beyond P2
  assert not status().flags & FLAG_RESTORE_SENT
  assert all(dat[:4] != b"\x03\x28\x00\x01" for _, dat, _ in pop_bus(1))


def test_exact_positive_after_deadline_tick_recovers_before_restore_enqueue():
  enter_wait_comm()
  lpp.ev9_test_tick(301_200, False)
  assert status().state == RESTORING
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  assert pop_bus(1) == []

  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 301_201)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & (FLAG_BRIDGE_ACTIVE | FLAG_DEADLINE_MISSED) == (
    FLAG_BRIDGE_ACTIVE | FLAG_DEADLINE_MISSED
  )
  assert timing().comm_control_response_us == 301_201
  assert not status().flags & FLAG_RESTORE_SENT
  assert all(dat[:4] != b"\x03\x28\x00\x01" for _, dat, _ in pop_bus(1))


def test_late_positive_before_global_deadline_activates_without_same_hook_restore():
  enter_wait_comm()
  lpp.ev9_test_tick(61_000, False)
  assert status().state == READY_PENDING_RESPONSE
  assert pop_bus(1) == []

  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 100_000)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & (FLAG_BRIDGE_ACTIVE | FLAG_DEADLINE_MISSED) == (
    FLAG_BRIDGE_ACTIVE | FLAG_DEADLINE_MISSED
  )
  assert not status().flags & FLAG_RESTORE_SENT
  assert timing().comm_control_response_us == 100_000
  assert timing().first_replacement_us == 100_000
  assert all(dat[:4] != b"\x03\x28\x00\x01" for _, dat, _ in pop_bus(1))


def test_deferred_session_never_transmits_after_global_deadline():
  lpp.set_safety_hooks(SAFETY_SILENT, 0)
  feed_identity()
  assert status().state == COLLECTING
  assert pop_bus(1) == []

  lpp.ev9_test_tick(301_200, False)
  assert status().state == ABORTED
  assert status().flags & FLAG_DEADLINE_MISSED
  sent = pop_bus(1)
  assert all(dat[:3] not in (b"\x02\x10\x03", b"\x02\x10\x01") for _, dat, _ in sent)


def enter_active():
  enter_wait_comm()
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 20_000)
  pop_bus(0)
  pop_bus(1)
  lpp.ev9_test_tick(80_000, False)
  assert status().state == ACTIVE
  pop_bus(0)
  pop_bus(1)


def enter_handoff(now_us=200_000):
  enter_active()
  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), now_us)
  lpp.ev9_test_host_tx(
    libpanda_py.make_CANPacket(0x730, 1, b"\x02\x3e\x80".ljust(8, b"\x00")), now_us,
  )
  for addr, length in REPLAY:
    lpp.ev9_test_host_tx(canfd(addr, 1, length), now_us)
  assert status().state == HANDOFF
  assert timing().handoff_us == now_us
  pop_bus(0)
  pop_bus(1)


def test_completed_stationary_knockout_allows_host_handoff_while_moving():
  enter_active()
  lpp.ev9_test_rx(wheel_speeds(100), 100_000)
  assert status().state == ACTIVE
  assert status().fingerprint & FP_STATIONARY  # records the stationary UDS boundary

  now_us = 200_000
  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), now_us)
  lpp.ev9_test_host_tx(
    libpanda_py.make_CANPacket(0x730, 1, b"\x02\x3e\x80".ljust(8, b"\x00")), now_us,
  )
  for addr, length in REPLAY:
    lpp.ev9_test_host_tx(canfd(addr, 1, length), now_us)

  assert status().state == HANDOFF
  assert status().flags & FLAG_HOST_HANDOFF
  assert timing().handoff_us == now_us


def enter_off_restore_from_handoff(handoff_us=200_000):
  enter_handoff(handoff_us)
  ignition_high_us = handoff_us + 1
  ignition_low_us = ignition_high_us + 1
  ignition_fall_us = ignition_low_us + 20_000
  lpp.ev9_test_tick(ignition_high_us, True)
  lpp.ev9_test_tick(ignition_low_us, False)
  assert status().state == HANDOFF
  assert lpp.ev9_test_ignition_low_handoff_candidate()
  lpp.ev9_test_tick(ignition_fall_us, False)
  assert status().state == RESTORING
  assert pop_bus(0) == []
  assert pop_bus(1) == []
  return ignition_fall_us


def prove_off_restore_exact(ignition_fall_us):
  restore_request_us = ignition_fall_us + 50_000
  lpp.ev9_test_tick(restore_request_us, False)
  pop_single_diag(b"\x03\x28\x00\x01")
  response_us = restore_request_us + 1
  lpp.ev9_test_rx(diag(2, 0x68, 0x00), response_us)
  assert status().state == ABORTED
  assert timing().abort_us == response_us
  return response_us


def enter_restoring_live():
  enter_active()
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 100_000)
  pop_bus(0)
  pop_bus(1)
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 200_001)
  assert status().state == RESTORING
  assert status().flags & FLAG_BRIDGE_ACTIVE


def test_per_address_host_claims_and_complete_handoff():
  enter_active()
  host_12a = libpanda_py.make_CANPacket(0x12A, 1, FORCED_NEUTRAL_TEMPLATES[0x12A])
  # Production sendcan reaches Panda as classic-shaped fd=0 and is promoted
  # by canfd_auto only after the preinit gate.
  host_12a.fd = 0
  lpp.ev9_test_update_crc(host_12a)
  lpp.ev9_test_host_tx(host_12a, 80_000)
  lpp.ev9_test_tick(90_000, False)
  assert all(addr != 0x12A for addr, _, _ in pop_bus(1))

  # This address resumes independently after its 100 ms host lease expires.
  lpp.ev9_test_tick(181_000, False)
  resumed = [dat for addr, dat, _ in pop_bus(1) if addr == 0x12A]
  assert len(resumed) == 1
  assert resumed[0][2] == 1

  now = 200_000
  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), now)
  lpp.ev9_test_host_tx(libpanda_py.make_CANPacket(0x730, 1, b"\x02\x3e\x80".ljust(8, b"\x00")), now)
  for addr, length in REPLAY:
    if addr != 0x1DA:
      lpp.ev9_test_host_tx(canfd(addr, 1, length), now)
  assert status().state == ACTIVE
  lpp.ev9_test_host_tx(canfd(0x57A, 1, 24), now)
  assert status().state == ACTIVE
  lpp.ev9_test_host_tx(canfd(0x1DA, 1, 32), now)
  assert status().state == HANDOFF


def test_inactive_host_cb_uses_fresh_physical_angle_before_safety():
  enter_active()
  # Route 1a7 crossed the active-command ceiling at parking lock. The inactive
  # mirror must still use the exact physical 14-bit value before safety.
  measured_angle = -3947  # 0.1-degree signed value from MDPS_0xEA
  raw_measured = measured_angle & 0xFFFF
  measured = canfd(0xEA, 1, 24, {12: raw_measured & 0xFF, 13: raw_measured >> 8})
  lpp.ev9_test_rx(measured, 180_000)

  host_cb = libpanda_py.make_CANPacket(0xCB, 1, FORCED_NEUTRAL_TEMPLATES[0xCB])
  host_cb.fd = 0
  assert lpp.ev9_test_prepare_host_tx(host_cb, 1, False, 200_000)
  assert host_cb.fd == 1
  desired_angle = ((host_cb.data[5] & 0x3F) << 8) | host_cb.data[4]
  assert desired_angle == (measured_angle & 0x3FFF)


def test_host_cb_angle_canonicalization_requires_inactive_shape_and_fresh_measurement():
  enter_active()
  measured = canfd(0xEA, 1, 24, {12: 0x34, 13: 0x01})
  lpp.ev9_test_rx(measured, 100_000)

  active_body = bytearray(FORCED_NEUTRAL_TEMPLATES[0xCB])
  active_body[3] = 0x20
  active_body[4] = 0x78
  active_body[5] = (active_body[5] & 0xC0) | 0x02
  active_cb = libpanda_py.make_CANPacket(0xCB, 1, bytes(active_body))
  active_cb.fd = 0
  assert lpp.ev9_test_prepare_host_tx(active_cb, 1, False, 200_000)
  assert active_cb.data[4] == 0x78
  assert active_cb.data[5] & 0x3F == 0x02

  # A later inactive attempt cannot reuse the now-stale physical sample.
  inactive_cb = libpanda_py.make_CANPacket(0xCB, 1, FORCED_NEUTRAL_TEMPLATES[0xCB])
  inactive_cb.fd = 0
  assert lpp.ev9_test_prepare_host_tx(inactive_cb, 1, False, 310_001)
  assert inactive_cb.data[4] == FORCED_NEUTRAL_TEMPLATES[0xCB][4]
  assert inactive_cb.data[5] & 0x3F == FORCED_NEUTRAL_TEMPLATES[0xCB][5] & 0x3F


@pytest.mark.parametrize(("bus", "bus_off", "error_passive", "transmit_error_cnt"), [
  (0, True, False, 0),
  (0, False, True, 0),
  (0, False, False, 128),
  (1, True, False, 0),
  (1, False, True, 0),
  (1, False, False, 128),
])
def test_handoff_requires_clean_managed_can_health(bus, bus_off, error_passive, transmit_error_cnt):
  enter_active()
  now_us = 200_000
  lpp.ev9_test_set_can_health(bus, bus_off, error_passive, transmit_error_cnt)
  heartbeat = canfd(0x100, 0, 24)
  lpp.ev9_test_host_tx(heartbeat, now_us)
  lpp.ev9_test_host_tx(
    libpanda_py.make_CANPacket(0x730, 1, b"\x02\x3e\x80".ljust(8, b"\x00")), now_us,
  )
  for addr, length in REPLAY:
    lpp.ev9_test_host_tx(canfd(addr, 1, length), now_us)

  # Every exact claim reached TXBAR, but unhealthy transport cannot transfer
  # ownership away from the resident bridge.
  assert status().state == ACTIVE

  lpp.ev9_test_set_can_health(bus, False, False, 0)
  lpp.ev9_test_hw_tx(heartbeat, now_us + 1)
  assert status().state == HANDOFF


def test_complete_cumulative_mask_waits_for_fresh_full_lease():
  enter_active()
  first_claim = 200_000
  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), first_claim)
  for addr, length in REPLAY:
    if addr != 0x1DA:
      lpp.ev9_test_host_tx(canfd(addr, 1, length), first_claim)

  # Completing the cumulative mask much later must not publish a transient
  # HANDOFF while the fast-stream and Tester Present leases are stale.
  late_claim = 2_000_000
  lpp.ev9_test_host_tx(libpanda_py.make_CANPacket(0x730, 1, b"\x02\x3e\x80".ljust(8, b"\x00")), late_claim)
  lpp.ev9_test_host_tx(canfd(0x1DA, 1, 32), late_claim)
  assert status().state == ACTIVE
  assert timing().handoff_us == 0

  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), late_claim)
  for addr, length in REPLAY:
    lpp.ev9_test_host_tx(canfd(addr, 1, length), late_claim)
  assert status().state == HANDOFF
  assert timing().handoff_us == late_claim


def test_resident_firmware_is_sole_host_diagnostic_owner():
  session = libpanda_py.make_CANPacket(0x730, 1, b"\x02\x10\x03".ljust(8, b"\x00"))
  disable = libpanda_py.make_CANPacket(0x730, 1, b"\x03\x28\x01\x01".ljust(8, b"\x00"))
  restore = libpanda_py.make_CANPacket(0x730, 1, b"\x03\x28\x00\x01".ljust(8, b"\x00"))
  tester_present = libpanda_py.make_CANPacket(0x730, 1, b"\x02\x3e\x80".ljust(8, b"\x00"))

  for packet in (session, disable, restore, tester_present):
    assert not lpp.ev9_test_external_tx_allowed(packet, 1, False)
    assert lpp.ev9_test_external_tx_allowed(packet, 1, True)

  enter_active()
  assert lpp.ev9_test_external_tx_allowed(tester_present, 1, False)
  for packet in (session, disable, restore):
    assert not lpp.ev9_test_external_tx_allowed(packet, 1, False)

  # The dedicated origin still traverses the queue-boundary state allowlist.
  assert not lpp.can_send_ev9_preinit_with_result(disable, 1)
  assert lpp.can_send_ev9_preinit_with_result(tester_present, 1)


def test_saturated_tx_queue_does_not_claim_dropped_host_frame():
  enter_active()
  saturate_bus(1)
  lpp.ev9_test_set_time(90_000)
  assert lpp.set_safety_hooks(17, 0) == 0  # SAFETY_ALLOUTPUT in test firmware
  assert not lpp.can_send_with_result(canfd(0x12A, 1, 16), 1, False)
  assert timing().last_host_tx_us == 0

  pop_bus(1)
  lpp.ev9_test_tick(100_000, False)
  assert any(addr == 0x12A for addr, _, _ in pop_bus(1))


def test_host_counter_is_atomically_normalized_to_resident_phase():
  enter_active()
  lpp.ev9_test_tick(90_000, False)
  resident_12a = [dat for addr, dat, _ in pop_bus(1) if addr == 0x12A]
  assert len(resident_12a) == 1

  host_12a = libpanda_py.make_CANPacket(0x12A, 1, FORCED_NEUTRAL_TEMPLATES[0x12A])
  host_12a.fd = 1
  host_12a.data[2] = 0xE7
  lpp.ev9_test_update_crc(host_12a)
  assert lpp.set_safety_hooks(17, 0) == 0  # SAFETY_ALLOUTPUT in test firmware
  lpp.ev9_test_set_time(99_000)
  assert lpp.can_send_with_result(host_12a, 1, False)
  queued = [dat for addr, dat, _ in pop_bus(1) if addr == 0x12A]
  assert len(queued) == 1
  assert host_12a.fd == 1
  assert queued[0][2] == (resident_12a[0][2] + 1) & 0xFF


def test_early_host_frame_is_silently_deferred_until_stream_phase_is_due():
  enter_active()
  assert lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0) == 0
  host = libpanda_py.make_CANPacket(0x12A, 1, FORCED_NEUTRAL_TEMPLATES[0x12A])
  lpp.ev9_test_update_crc(host)

  lpp.ev9_test_set_time(88_000)
  assert not lpp.can_send_with_result(host, 1, False)
  assert timing().last_host_tx_us == 0
  assert pop_bus(1) == []

  # The takeover tolerance permits the host at 90% of the 10 ms period.
  lpp.ev9_test_set_time(89_000)
  assert lpp.can_send_with_result(host, 1, False)
  assert timing().last_host_tx_us == 89_000
  assert len([frame for frame in pop_bus(1) if frame[0] == 0x12A]) == 1


def test_route17b_all_stream_retry_claims_phase_starved_345_at_90_percent_boundary():
  enter_active()
  assert lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0) == 0

  # Route 17b's native 0x345 attempt came 176.582 ms after the resident body,
  # just before Panda's 180 ms admission boundary. Reproduce the silent filter
  # after a resident fallback has reset that stream's phase.
  lpp.ev9_test_tick(220_000, False)
  resident = [frame for frame in pop_bus(1) if frame[0] == 0x345]
  assert len(resident) == 1
  host_345 = libpanda_py.make_CANPacket(0x345, 1, bytes.fromhex("0000001500560000"))
  lpp.ev9_test_update_crc(host_345)
  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), 390_000)
  lpp.ev9_test_set_time(396_582)
  assert not lpp.can_send_with_result(host_345, 1, False)
  assert status().state == ACTIVE
  assert pop_bus(1) == []

  # The one-shot slow reservation holds the 200 ms resident deadline against
  # a bounded host scheduling stall. It never counts this pre-safety attempt
  # as ownership and never moves the original cadence-based deadline.
  lpp.ev9_test_tick(420_000, False)
  assert all(frame[0] != 0x345 for frame in pop_bus(1))

  # Keep every other lease current as the all-managed retry batch does. The
  # next 0x345 retry inside the bounded hold traverses the unchanged
  # safety hook, enters the hardware queue, and completes HANDOFF.
  now_us = 430_000
  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), now_us)
  lpp.ev9_test_host_tx(
    libpanda_py.make_CANPacket(0x730, 1, b"\x02\x3e\x80".ljust(8, b"\x00")), now_us,
  )
  for addr, length in REPLAY:
    if addr != 0x345:
      lpp.ev9_test_host_tx(canfd(addr, 1, length), now_us)
  assert status().state == ACTIVE

  lpp.ev9_test_set_time(now_us)
  assert lpp.can_send_with_result(host_345, 1, False)
  assert status().state == ACTIVE  # software FIFO acceptance is not ownership
  lpp.ev9_test_hw_tx(host_345, now_us)
  assert status().state == HANDOFF
  claimed = [frame for frame in pop_bus(1) if frame[0] == 0x345]
  assert len(claimed) == 1


def test_slow_claim_reservation_expires_at_original_period_plus_25ms_and_is_one_shot():
  enter_active()
  assert lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0) == 0
  lpp.ev9_test_tick(220_000, False)
  assert len([frame for frame in pop_bus(1) if frame[0] == 0x345]) == 1

  host_345 = libpanda_py.make_CANPacket(0x345, 1, bytes.fromhex("0000001500560000"))
  lpp.ev9_test_update_crc(host_345)
  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), 390_000)
  for now_us in (396_582, 399_000):
    lpp.ev9_test_set_time(now_us)
    assert not lpp.can_send_with_result(host_345, 1, False)

  for now_us in (420_000, 444_999):
    lpp.ev9_test_tick(now_us, False)
    assert all(frame[0] != 0x345 for frame in pop_bus(1))
  lpp.ev9_test_tick(445_000, False)
  assert len([frame for frame in pop_bus(1) if frame[0] == 0x345]) == 1

  # A second early attempt in the same ACTIVE claim cannot reserve again.
  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), 620_000)
  lpp.ev9_test_set_time(621_582)
  assert not lpp.can_send_with_result(host_345, 1, False)
  lpp.ev9_test_tick(645_000, False)
  assert len([frame for frame in pop_bus(1) if frame[0] == 0x345]) == 1


def test_slow_claim_reservation_requires_recent_managed_host_and_exact_body():
  enter_active()
  assert lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0) == 0
  lpp.ev9_test_tick(220_000, False)
  pop_bus(1)

  host_345 = libpanda_py.make_CANPacket(0x345, 1, bytes.fromhex("0000001500560000"))
  lpp.ev9_test_update_crc(host_345)
  lpp.ev9_test_set_time(396_582)
  assert not lpp.can_send_with_result(host_345, 1, False)
  lpp.ev9_test_tick(420_000, False)
  assert len([frame for frame in pop_bus(1) if frame[0] == 0x345]) == 1

  # Reset the epoch, then provide recent accepted managed traffic but a body
  # that differs from the resident neutral source. It may not reserve.
  lpp.ev9_test_init()
  enter_active()
  lpp.ev9_test_tick(220_000, False)
  pop_bus(1)
  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), 390_000)
  wrong_body = libpanda_py.make_CANPacket(0x345, 1, bytes.fromhex("0000009500560000"))
  lpp.ev9_test_update_crc(wrong_body)
  lpp.ev9_test_set_time(396_582)
  assert not lpp.can_send_with_result(wrong_body, 1, False)
  lpp.ev9_test_tick(420_000, False)
  assert len([frame for frame in pop_bus(1) if frame[0] == 0x345]) == 1


def test_fast_claim_stream_never_reserves_resident_deadline():
  enter_active()
  assert lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0) == 0
  lpp.ev9_test_tick(90_000, False)
  pop_bus(1)
  host_12a = libpanda_py.make_CANPacket(0x12A, 1, FORCED_NEUTRAL_TEMPLATES[0x12A])
  lpp.ev9_test_update_crc(host_12a)
  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), 95_000)
  lpp.ev9_test_set_time(98_000)
  assert not lpp.can_send_with_result(host_12a, 1, False)
  lpp.ev9_test_tick(100_000, False)
  assert len([frame for frame in pop_bus(1) if frame[0] == 0x12A]) == 1


@pytest.mark.parametrize("addr,bus,length,period_us", [
  (0x100, 0, 24, 10_000),
  (0x12A, 1, 16, 10_000),
  (0xCB, 1, 24, 10_000),
  (0x160, 1, 16, 20_000),
  (0x161, 1, 32, 50_000),
])
def test_three_ms_claim_retry_escapes_hostile_fast_stream_phase(addr, bus, length, period_us):
  enter_active()
  assert lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0) == 0

  # Establish an exact resident phase for the stream under test. All queues
  # are drained at each tick so only a newly emitted target can seal it.
  resident_us = None
  for now_us in range(81_000, 201_000, 1_000):
    lpp.ev9_test_tick(now_us, False)
    target_frames = [frame for frame in pop_bus(bus) if frame[0] == addr]
    if target_frames:
      assert len(target_frames) == 1
      resident_us = now_us
      break
  assert resident_us is not None

  host = canfd(addr, bus, length)
  next_host_us = resident_us + 1_000
  accepted_us = None
  resident_wins = 0
  # Tick first at coincident timestamps: this gives the resident deadline the
  # most adversarial ordering. A fixed 10 ms retry at this +1 ms phase can
  # starve forever; 3 ms must enter every 90%-period window within two periods.
  for now_us in range(resident_us + 1_000, resident_us + (2 * period_us) + 1_000, 1_000):
    lpp.ev9_test_tick(now_us, False)
    resident_wins += len([frame for frame in pop_bus(bus) if frame[0] == addr])
    if now_us == next_host_us:
      lpp.ev9_test_set_time(now_us)
      if lpp.can_send_with_result(host, bus, False):
        accepted_us = now_us
        break
      next_host_us += 3_000

  assert resident_wins <= 1
  assert accepted_us is not None
  assert accepted_us - resident_us <= 2 * period_us


def test_host_tester_present_inherits_resident_phase_without_duplicate():
  enter_active()
  assert lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0) == 0
  tester_present = libpanda_py.make_CANPacket(0x730, 1, b"\x02\x3e\x80".ljust(8, b"\x00"))

  lpp.ev9_test_set_time(919_999)
  assert not lpp.can_send_with_result(tester_present, 1, False)
  assert pop_bus(1) == []

  lpp.ev9_test_set_time(920_000)
  assert lpp.can_send_with_result(tester_present, 1, False)
  assert timing().last_tester_present_us == 920_000
  queued = [frame for frame in pop_bus(1) if frame[0] == 0x730]
  assert len(queued) == 1


def test_retried_slow_claim_streams_handoff_at_first_safe_phase():
  enter_active()
  assert lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0) == 0

  # Claim every fast stream directly so this test isolates the two 1 Hz bits
  # that were phase-starved in route 177.
  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), 200_000)
  for addr, length in REPLAY:
    if addr != 0x1DA:
      lpp.ev9_test_host_tx(canfd(addr, 1, length), 200_000)

  host_1da = canfd(0x1DA, 1, 32)
  tester_present = libpanda_py.make_CANPacket(0x730, 1, b"\x02\x3e\x80".ljust(8, b"\x00"))
  for now_us in range(200_000, 900_001, 50_000):
    # The real claim loop keeps every faster tuple fresh while retrying the
    # phase-sensitive pair.
    lpp.ev9_test_host_tx(canfd(0x100, 0, 24), now_us)
    for addr, length in REPLAY:
      if addr != 0x1DA:
        lpp.ev9_test_host_tx(canfd(addr, 1, length), now_us)
    lpp.ev9_test_set_time(now_us)
    assert not lpp.can_send_with_result(host_1da, 1, False)
    assert not lpp.can_send_with_result(tester_present, 1, False)
    assert status().state == ACTIVE
    assert pop_bus(1) == []

  # The resident published both at 20 ms, making 920 ms their first 90%-phase
  # host slot. The first due retries enter hardware and complete the mask.
  lpp.ev9_test_set_time(920_000)
  assert lpp.can_send_with_result(host_1da, 1, False)
  assert status().state == ACTIVE
  assert lpp.can_send_with_result(tester_present, 1, False)
  assert status().state == ACTIVE
  lpp.ev9_test_hw_tx(host_1da, 920_000)
  lpp.ev9_test_hw_tx(tester_present, 920_000)
  assert status().state == HANDOFF
  queued = [(addr, dat) for addr, dat, _ in pop_bus(1)]
  assert [addr for addr, _ in queued] == [0x1DA, 0x730]


def test_dynamic_host_bodies_resume_with_safe_resident_fallbacks():
  enter_active()
  assert lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0) == 0
  lpp.ev9_test_set_time(130_000)
  for addr, template in FORCED_NEUTRAL_TEMPLATES.items():
    host = libpanda_py.make_CANPacket(addr, 1, template)
    host.fd = 0
    host.data[3] ^= 0x80
    lpp.ev9_test_update_crc(host)
    assert lpp.can_send_with_result(host, 1, False)

  host_frames = {addr: dat for addr, dat, _ in pop_bus(1) if addr in FORCED_NEUTRAL_TEMPLATES}
  assert set(host_frames) == set(FORCED_NEUTRAL_TEMPLATES)

  # 50 ms streams use a three-period lease (150 ms); cross every per-address
  # expiry before checking that the resident bridge has resumed all of them.
  lpp.ev9_test_tick(281_000, False)
  resumed = {addr: dat for addr, dat, _ in pop_bus(1) if addr in FORCED_NEUTRAL_TEMPLATES}
  assert set(resumed) == set(FORCED_NEUTRAL_TEMPLATES)
  for addr, template in FORCED_NEUTRAL_TEMPLATES.items():
    assert resumed[addr][2] == (host_frames[addr][2] + 1) & 0xFF
    assert resumed[addr][3:] == template[3:]
  assert not status().flags & FLAG_INTERNAL_TX_REJECTED


def test_161_icons_are_canonicalized_only_before_one_way_handoff():
  enter_active()
  assert lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0) == 0

  active_161 = libpanda_py.make_CANPacket(0x161, 1, bytes(32))
  active_161.data[3] = 0xFF
  active_161.data[4] = 0xFF
  lpp.ev9_test_update_crc(active_161)
  lpp.ev9_test_set_time(125_000)
  assert lpp.can_send_with_result(active_161, 1, False)
  queued_active = [dat for addr, dat, _ in pop_bus(1) if addr == 0x161]
  assert len(queued_active) == 1
  assert queued_active[0][3] == 0x41  # FCA orange + LKA orange, no alternate/fault scene
  assert queued_active[0][4] & 0x01 == 0

  handoff_us = 250_000
  lpp.ev9_test_host_tx(canfd(0x100, 0, 24), handoff_us)
  lpp.ev9_test_host_tx(
    libpanda_py.make_CANPacket(0x730, 1, b"\x02\x3e\x80".ljust(8, b"\x00")), handoff_us,
  )
  for addr, length in REPLAY:
    lpp.ev9_test_host_tx(canfd(addr, 1, length), handoff_us)
  assert status().state == HANDOFF
  pop_bus(0)
  pop_bus(1)
  handoff_161 = libpanda_py.make_CANPacket(0x161, 1, bytes(32))
  handoff_161.data[3] = 0xFF
  handoff_161.data[4] = 0xFF
  lpp.ev9_test_update_crc(handoff_161)
  lpp.ev9_test_set_time(295_000)
  assert lpp.can_send_with_result(handoff_161, 1, False)
  queued_handoff = [dat for addr, dat, _ in pop_bus(1) if addr == 0x161]
  assert len(queued_handoff) == 1
  assert queued_handoff[0][3] == 0x01  # bounded claim/status transition keeps truthful FCA
  assert queued_handoff[0][4] & 0x01 == 0

  # Host lease expiry cannot re-enter resident publication during this ignition
  # epoch. Ignition OFF is the only rearm boundary after a complete handoff.
  lpp.ev9_test_tick(351_000, False)
  assert status().state == HANDOFF
  assert status().flags & FLAG_HOST_HANDOFF
  pop_bus(1)
  lpp.ev9_test_tick(446_000, False)
  resumed = [dat for addr, dat, _ in pop_bus(1) if addr == 0x161]
  assert resumed == []

  live_161 = libpanda_py.make_CANPacket(0x161, 1, bytes(32))
  live_161.fd = 0
  live_161.data[3] = 0xFF
  live_161.data[4] = 0xFF
  lpp.ev9_test_update_crc(live_161)
  lpp.ev9_test_set_time(750_001)
  assert lpp.can_send_with_result(live_161, 1, False)
  queued_live = [dat for addr, dat, _ in pop_bus(1) if addr == 0x161]
  assert len(queued_live) == 1
  assert queued_live[0][3] == 0xFF  # ordinary host body is untouched after settle
  assert queued_live[0][4] == 0xFF


def test_handoff_preserves_only_counter_crc_continuity():
  enter_handoff()
  assert lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0) == 0

  # Card learns HANDOFF through a 10 Hz status publication. Until that bounded
  # observation window closes, retain the normal phase gate so its 333 Hz claim
  # retries cannot burst onto CAN.
  claim_cb = libpanda_py.make_CANPacket(0xCB, 1, FORCED_NEUTRAL_TEMPLATES[0xCB])
  claim_cb.fd = 0
  lpp.ev9_test_set_time(210_000)
  assert lpp.can_send_with_result(claim_cb, 1, False)
  pop_bus(1)
  lpp.ev9_test_set_time(213_000)
  assert not lpp.can_send_with_result(claim_cb, 1, False)
  assert pop_bus(1) == []

  lpp.ev9_test_set_time(700_001)
  bodies = []
  for input_counter in (7, 201):
    host_cb = libpanda_py.make_CANPacket(0xCB, 1, FORCED_NEUTRAL_TEMPLATES[0xCB])
    host_cb.fd = 0
    host_cb.data[2] = input_counter
    host_cb.data[3] = 0x10
    host_cb.data[4] = 0x34
    host_cb.data[5] = 0x01
    lpp.ev9_test_update_crc(host_cb)
    assert lpp.can_send_with_result(host_cb, 1, False)
    queued = [dat for addr, dat, _ in pop_bus(1) if addr == 0xCB]
    assert len(queued) == 1
    bodies.append(queued[0])

  assert bodies[1][2] == (bodies[0][2] + 1) & 0xFF
  assert bodies[0][2] != 7
  assert bodies[1][2] != 201
  assert bodies[0][3:] == bytes(host_cb.data)[3:24]
  assert bodies[1][3:] == bytes(host_cb.data)[3:24]
  for body in bodies:
    packet = libpanda_py.make_CANPacket(0xCB, 1, body)
    packet.fd = 1
    lpp.ev9_test_update_crc(packet)
    assert bytes(packet.data)[:24] == body


def test_resident_161_icon_canonicalization_does_not_depend_on_fallback_body():
  enter_wait_comm()
  oem_161 = canfd(0x161, 1, 32, {3: 0x00, 4: 0x01, 15: 0xA5})
  lpp.ev9_test_rx(oem_161, 15_000)
  lpp.ev9_test_tick(16_000, False)
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 20_000)
  pop_bus(0)
  pop_bus(1)

  lpp.ev9_test_tick(80_000, False)
  resident_161 = [dat for addr, dat, _ in pop_bus(1) if addr == 0x161]

  assert len(resident_161) == 1
  assert resident_161[0][3] == 0x41
  assert resident_161[0][4] & 0x01 == 0


def test_production_shaped_heartbeat_and_dynamic_status_resume_as_canfd():
  enter_active()
  assert lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0) == 0
  lpp.ev9_test_set_time(1_100_000)

  heartbeat = libpanda_py.make_CANPacket(0x100, 0, bytes(24))
  heartbeat.fd = 0
  lpp.ev9_test_update_crc(heartbeat)
  dynamic_1da_body = bytes.fromhex(
    "000000a255aa0000000000000000000000000000000000000000000000000000",
  )
  dynamic_1da = libpanda_py.make_CANPacket(0x1DA, 1, dynamic_1da_body)
  dynamic_1da.fd = 0
  lpp.ev9_test_update_crc(dynamic_1da)
  assert lpp.can_send_with_result(heartbeat, 0, False)
  assert lpp.can_send_with_result(dynamic_1da, 1, False)

  host_heartbeat = [frame for frame in pop_bus(0) if frame[0] == 0x100]
  host_1da = [frame for frame in pop_bus(1) if frame[0] == 0x1DA]
  assert len(host_heartbeat) == len(host_1da) == 1
  assert host_heartbeat[0][2] and host_1da[0][2]

  lpp.ev9_test_tick(4_200_000, False)
  resumed_heartbeat = [frame for frame in pop_bus(0) if frame[0] == 0x100]
  resumed_1da = [frame for frame in pop_bus(1) if frame[0] == 0x1DA]
  assert len(resumed_heartbeat) == len(resumed_1da) == 1
  assert resumed_heartbeat[0][2] and resumed_1da[0][2]
  assert resumed_1da[0][1][3:] == dynamic_1da_body[3:]
  assert not status().flags & FLAG_INTERNAL_TX_REJECTED


def test_saturated_tx_queue_is_reported_and_internal_retry_remains_due():
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 1_000)
  lpp.ev9_test_rx(canfd(0x100, 0, 24), 1_100)
  lpp.ev9_test_rx(wheel_speeds(), 1_150)
  saturate_bus(1)
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x45}), 1_200)
  assert status().state == WAIT_SESSION
  assert status().flags & FLAG_INTERNAL_TX_REJECTED
  assert status().attempts == 0
  assert timing().session_request_us == 0

  pop_bus(1)
  lpp.ev9_test_tick(51_199, False)
  assert pop_bus(1) == []
  lpp.ev9_test_tick(51_200, False)
  pop_single_diag(b"\x02\x10\x03")
  assert status().attempts == 1
  assert timing().session_request_us == 51_200


def test_rejected_communication_control_only_counts_when_enqueued():
  feed_identity()
  pop_single_diag(b"\x02\x10\x03")
  saturate_bus(1)
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 10_000)
  assert status().state == WAIT_COMM_CONTROL
  assert status().flags & FLAG_INTERNAL_TX_REJECTED
  assert status().attempts == 0
  assert timing().comm_control_us == 0

  pop_bus(1)
  lpp.ev9_test_tick(59_999, False)
  assert pop_bus(1) == []
  lpp.ev9_test_tick(60_000, False)
  pop_single_diag(b"\x03\x28\x01\x01")
  assert status().attempts == 1
  assert timing().comm_control_us == 60_000


def test_rejected_bridge_enqueue_is_paced_instead_of_retried_per_rx():
  enter_active()
  saturate_bus(0)
  saturate_bus(1)

  # Fast streams are due at 90 ms, but the full queue rejects them. Freeing a
  # slot and receiving more CAN must not turn that rejection into an RX-rate
  # retry loop; each address waits its own period.
  lpp.ev9_test_tick(90_000, False)
  assert status().flags & FLAG_INTERNAL_TX_REJECTED
  pop_bus(0)
  pop_bus(1)
  lpp.ev9_test_rx(canfd(0x35, 1, 32), 90_001)
  assert pop_bus(0) == []
  assert pop_bus(1) == []
  lpp.ev9_test_rx(canfd(0x175, 1, 24), 99_999)
  assert pop_bus(0) == []
  assert pop_bus(1) == []

  lpp.ev9_test_tick(100_000, False)
  heartbeat = [dat for addr, dat, _ in pop_bus(0) if addr == 0x100]
  assert len(heartbeat) == 1
  assert heartbeat[0][2] == 3
  assert {addr for addr, _, _ in pop_bus(1)}.issuperset({0x12A, 0xCB})


def test_ambiguous_communication_timeout_restores_without_unproven_bridge():
  enter_wait_comm()
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  assert timing().first_replacement_us == 0

  lpp.ev9_test_tick(60_999, False)
  assert status().state == WAIT_COMM_CONTROL
  lpp.ev9_test_tick(61_000, False)
  assert status().state == READY_PENDING_RESPONSE
  assert pop_bus(1) == []
  assert pop_bus(0) == []

  # The unanswered request remains the only accepted 28 through the global
  # deadline. RESTORING first quiesces both CAN TX paths.
  lpp.ev9_test_tick(301_200, False)
  assert status().state == RESTORING
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  assert not status().flags & FLAG_RESTORE_SENT
  assert timing().restore_us == 0
  assert timing().first_replacement_us == 0
  assert pop_bus(1) == []

  lpp.ev9_test_tick(351_199, False)
  assert pop_bus(1) == []
  lpp.ev9_test_tick(351_200, False)
  pop_single_diag(b"\x03\x28\x00\x01")
  assert status().flags & FLAG_RESTORE_SENT
  assert timing().restore_us == 351_200

  # Physical stock convergence proves communication is already enabled. Since
  # no 68 01 ever proved ownership, do not append 10 01.
  lpp.ev9_test_rx(canfd(0x100, 0, 24), 360_000)
  for i, (addr, bus, length) in enumerate((
    (0x12A, 1, 16), (0xCB, 1, 24), (0x160, 1, 16), (0x1A0, 1, 32),
  )):
    lpp.ev9_test_rx(canfd(addr, bus, length), 361_000 + i * 1_000)
  assert status().state == ABORTED
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  assert all(dat[:3] != b"\x02\x10\x01" for _, dat, _ in pop_bus(1))


def test_restore_queue_rejection_retries_then_bounds_successful_requests():
  enter_restoring_live()
  saturate_bus(1)

  # The 50 ms quiesce boundary cannot enqueue restore while either software TX
  # queue is nonempty.
  lpp.ev9_test_tick(250_001, True)
  assert not status().flags & FLAG_RESTORE_SENT
  assert timing().restore_us == 0
  assert status().flags & FLAG_BRIDGE_ACTIVE

  pop_bus(1)
  lpp.ev9_test_tick(250_002, True)
  sent = pop_bus(1)
  assert sum(dat[:4] == b"\x03\x28\x00\x01" for _, dat, _ in sent) == 1
  assert status().flags & FLAG_RESTORE_SENT
  assert timing().restore_us == 250_002

  # No proof causes two more diagnostic-only retries. RESTORING never publishes
  # a replacement on either bus.
  for now in (300_002, 350_002):
    lpp.ev9_test_tick(now, True)
    assert pop_bus(0) == []
    sent = pop_bus(1)
    assert sum(dat[:4] == b"\x03\x28\x00\x01" for _, dat, _ in sent) == 1
  lpp.ev9_test_tick(400_002, True)
  sent = pop_bus(1)
  assert all(dat[:4] != b"\x03\x28\x00\x01" for _, dat, _ in sent)
  assert status().state == RESTORING
  assert status().flags & FLAG_BRIDGE_ACTIVE

  # An exact restore ACK releases only after the diagnostic TX queue is empty.
  lpp.ev9_test_rx(diag(2, 0x68, 0x00), 401_000)
  assert status().state == ABORTED
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  assert any(dat[:3] == b"\x02\x10\x01" for _, dat, _ in pop_bus(1))


def test_exhausted_restore_without_stock_resumes_proven_owned_bridge():
  enter_restoring_live()
  for now in (250_001, 300_001, 350_001):
    lpp.ev9_test_tick(now, True)
    sent = pop_bus(1)
    assert sum(dat[:4] == b"\x03\x28\x00\x01" for _, dat, _ in sent) == 1
    assert pop_bus(0) == []

  lpp.ev9_test_tick(450_001, True)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & (FLAG_BRIDGE_ACTIVE | FLAG_DEADLINE_MISSED) == (
    FLAG_BRIDGE_ACTIVE | FLAG_DEADLINE_MISSED
  )
  assert status().flags & FLAG_RESTORE_SENT
  assert pop_bus(0)  # heartbeat publication resumed
  assert all(dat[:4] != b"\x03\x28\x00\x01" for _, dat, _ in pop_bus(1))


def test_disable_positive_after_restore_enqueue_is_recorded_for_fallback():
  enter_wait_comm()
  lpp.ev9_test_tick(301_200, False)
  assert status().state == RESTORING
  lpp.ev9_test_tick(351_200, False)
  pop_single_diag(b"\x03\x28\x00\x01")

  # 0x730 wins arbitration over 0x738, so this disable ACK can arrive behind
  # the first restore request. Record ownership but do not publish yet.
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 351_201)
  assert status().state == RESTORING
  assert timing().comm_control_response_us == 351_201
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  assert timing().first_replacement_us == 0

  for now in (401_200, 451_200):
    lpp.ev9_test_tick(now, False)
    pop_single_diag(b"\x03\x28\x00\x01")
  lpp.ev9_test_tick(551_200, False)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & FLAG_BRIDGE_ACTIVE
  assert pop_bus(0)
  assert pop_bus(1)


def test_generic_hda2_tuples_cannot_start_ev9_diagnostics():
  # These IDs/lengths are shared by other HDA2 Hyundai/Kia platforms. Even a
  # complete, CRC-valid common tuple must remain silent without the EV9 body
  # signature on the radar heartbeat.
  for now, packet in enumerate((
    canfd(0xCB, 1, 24), generic_hda2_heartbeat(), canfd(0x35, 1, 32),
    canfd(0xA0, 1, 24), canfd(0x1A0, 1, 32), canfd(0x160, 1, 16),
    canfd(0x1BA, 1, 24),
  ), start=1_000):
    lpp.ev9_test_rx(packet, now)

  assert status().state == COLLECTING
  assert not status().fingerprint & 0x01
  assert pop_bus(0) == []
  assert pop_bus(1) == []


def test_ev9_heartbeat_signature_allows_route_backed_dynamic_fields():
  for index, value in ((4, 0xFE), (5, 0xFF), (6, 0xE6), (12, 0x18), (18, 0x04)):
    lpp.ev9_test_init()
    lpp.ev9_test_rx(canfd(0xCB, 1, 24), 1_000)
    lpp.ev9_test_rx(canfd(0x100, 0, 24, {index: value}), 1_100)
    lpp.ev9_test_rx(wheel_speeds(), 1_150)
    lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x45}), 1_200)
    assert status().state == WAIT_SESSION
    pop_single_diag(b"\x02\x10\x03")

  lpp.ev9_test_init()
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 1_000)
  lpp.ev9_test_rx(canfd(0x100, 0, 24, {3: 0x01}), 1_100)
  lpp.ev9_test_rx(canfd(0x35, 1, 32), 1_200)
  assert status().state == COLLECTING
  assert not status().fingerprint & 0x01
  assert pop_bus(1) == []


def test_physical_route_181_heartbeat_completes_identity():
  lpp.ev9_test_init()
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 1_000)
  heartbeat = libpanda_py.make_CANPacket(0x100, 0, EV9_STOCK_HEARTBEAT)
  heartbeat.fd = 1
  lpp.ev9_test_update_crc(heartbeat)
  lpp.ev9_test_rx(heartbeat, 1_100)
  lpp.ev9_test_rx(wheel_speeds(), 1_150)
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x45}), 1_200)
  assert status().state == WAIT_SESSION
  pop_single_diag(b"\x02\x10\x03")


def test_physical_identity_body_does_not_replace_radar_alive_heartbeat():
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 1_000)
  physical = libpanda_py.make_CANPacket(0x100, 0, EV9_STOCK_HEARTBEAT)
  physical.fd = 1
  physical.data[2] = 0x84
  lpp.ev9_test_update_crc(physical)
  lpp.ev9_test_rx(physical, 1_100)
  lpp.ev9_test_rx(wheel_speeds(), 1_150)
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x45}), 1_200)
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 11_000)
  pop_single_diag(b"\x03\x28\x01\x01")
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 21_000)

  heartbeats = [dat for addr, dat, _ in pop_bus(0) if addr == 0x100]
  assert len(heartbeats) == 1
  heartbeat = heartbeats[0]
  expected = bytearray(EV9_HEARTBEAT_TEMPLATE)
  expected[2] = 0x85
  # EV9_STOCK_HEARTBEAT carries the physical brake bit set.
  expected[4] |= 0x01
  assert heartbeat[2:] == expected[2:]


def test_powertrain_and_scc_identity_bodies_are_both_required():
  for address in (0x35, 0xCB):
    lpp.ev9_test_init()
    lpp.ev9_test_rx(canfd(0x100, 0, 24), 1_000)
    lpp.ev9_test_rx(canfd(0x35, 1, 32, {31: 0x01}) if address == 0x35 else canfd(0x35, 1, 32), 1_100)
    lpp.ev9_test_rx(canfd(0xCB, 1, 24, {23: 0x01}) if address == 0xCB else canfd(0xCB, 1, 24), 1_200)
    assert status().state == COLLECTING
    assert pop_bus(1) == []


def test_late_restore_positive_after_fallback_stops_bridge_and_quarantines_host():
  enter_restoring_live()
  for now in (250_001, 300_001, 350_001):
    lpp.ev9_test_tick(now, True)
    pop_single_diag(b"\x03\x28\x00\x01")
  lpp.ev9_test_tick(450_001, True)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & FLAG_BRIDGE_ACTIVE

  # Keep fallback replacements queued to prove the ACK cannot release stock
  # until both software TX queues have drained.
  lpp.ev9_test_rx(diag(2, 0x68, 0x00), 450_002)
  assert status().state == RESTORING
  assert status().flags & FLAG_BRIDGE_ACTIVE
  assert lpp.ev9_test_get_freeze_count() >= 1
  assert lpp.can_slots_empty(lpp.tx1_q) < lpp.tx1_q.fifo_size - 1
  assert lpp.can_slots_empty(lpp.tx2_q) < lpp.tx2_q.fifo_size - 1
  assert lpp.ev9_test_get_cancel_count(0) == 0
  assert lpp.ev9_test_get_cancel_count(1) == 0
  lpp.ev9_test_tick(450_003, True)
  assert lpp.ev9_test_get_cancel_count(0) == 1
  assert lpp.ev9_test_get_cancel_count(1) == 1
  assert pop_bus(0) == []
  assert pop_bus(1)[0][1][:3] == b"\x02\x10\x01"
  assert status().state == ABORTED
  assert not status().flags & FLAG_BRIDGE_ACTIVE

  lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0)
  managed = libpanda_py.make_CANPacket(0x12A, 1, b"\x00" * 16)
  unrelated = libpanda_py.make_CANPacket(0x321, 1, b"\x00" * 8)
  assert not lpp.ev9_test_external_tx_allowed(managed, 1, False)
  assert not lpp.can_send_with_result(managed, 1, False)
  assert pop_bus(1) == []
  assert lpp.ev9_test_external_tx_allowed(unrelated, 1, False)
  assert lpp.can_send_with_result(unrelated, 1, False)
  assert len(pop_bus(1)) == 1
  assert lpp.ev9_test_external_tx_allowed(managed, 1, True)
  assert lpp.can_send_with_result(managed, 1, True)
  assert len(pop_bus(1)) == 1


def test_first_stock_frame_after_restore_fallback_immediately_quiesces_bridge():
  enter_restoring_live()
  for now in (250_001, 300_001, 350_001):
    lpp.ev9_test_tick(now, True)
    pop_single_diag(b"\x03\x28\x00\x01")
  lpp.ev9_test_tick(450_001, True)
  assert status().state == WAIT_SUPPRESSION

  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 450_002)
  assert status().state == RESTORING
  assert lpp.ev9_test_get_freeze_count() >= 1
  assert lpp.ev9_test_get_cancel_count(0) == 0
  assert lpp.ev9_test_get_cancel_count(1) == 0
  lpp.ev9_test_tick(450_003, True)
  assert lpp.ev9_test_get_cancel_count(0) == 1
  assert lpp.ev9_test_get_cancel_count(1) == 1
  assert pop_bus(0) == []
  assert pop_bus(1) == []


def test_malformed_stock_frame_cannot_cancel_restore_fallback_bridge():
  enter_restoring_live()
  for now in (250_001, 300_001, 350_001):
    lpp.ev9_test_tick(now, True)
    pop_single_diag(b"\x03\x28\x00\x01")
  lpp.ev9_test_tick(450_001, True)
  pop_bus(0)
  pop_bus(1)
  assert status().state == WAIT_SUPPRESSION

  corrupted = canfd(0xCB, 1, 24)
  corrupted.data[3] ^= 0x01
  lpp.ev9_test_rx(corrupted, 450_002)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & FLAG_BRIDGE_ACTIVE
  assert lpp.ev9_test_get_freeze_count() == 0
  assert lpp.ev9_test_get_cancel_count(0) == 0
  assert lpp.ev9_test_get_cancel_count(1) == 0


@pytest.mark.parametrize("late_proof", ["ack", "stock"])
def test_restore_fallback_proof_after_active_still_quiesces_immediately(late_proof):
  enter_restoring_live()
  for now in (250_001, 300_001, 350_001):
    lpp.ev9_test_tick(now, True)
    pop_single_diag(b"\x03\x28\x00\x01")
  lpp.ev9_test_tick(450_001, True)
  assert status().state == WAIT_SUPPRESSION

  # Fresh non-ADAS vehicle traffic can confirm ACTIVE before a delayed restore
  # ACK or stock ADAS stream appears. Fallback containment must remain armed.
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x45}), 460_000)
  lpp.ev9_test_tick(520_001, True)
  assert status().state == ACTIVE
  assert status().flags & FLAG_BRIDGE_ACTIVE

  if late_proof == "ack":
    lpp.ev9_test_rx(diag(2, 0x68, 0x00), 520_002)
  else:
    lpp.ev9_test_rx(canfd(0xCB, 1, 24), 520_002)
  assert status().state == RESTORING
  assert lpp.ev9_test_get_freeze_count() >= 1
  lpp.ev9_test_tick(520_003, True)
  assert lpp.ev9_test_get_cancel_count(0) == 1
  assert lpp.ev9_test_get_cancel_count(1) == 1


def test_restore_and_rearm_block_host_vehicle_bus_tx():
  enter_restoring_live()
  lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0)
  vehicle_tx = libpanda_py.make_CANPacket(0x321, 1, b"\x00" * 8)
  aux_tx = libpanda_py.make_CANPacket(0x321, 2, b"\x00" * 8)

  assert not lpp.ev9_test_external_tx_allowed(vehicle_tx, 1, False)
  assert not lpp.can_send_with_result(vehicle_tx, 1, False)
  assert pop_bus(1) == []
  assert lpp.ev9_test_external_tx_allowed(aux_tx, 2, False)
  assert lpp.can_send_with_result(aux_tx, 2, False)
  assert len(pop_bus(2)) == 1

  # Forwarding uses the actual destination and is also quiesced in RESTORING.
  forwarded_tx = libpanda_py.make_CANPacket(0x321, 0, b"\x00" * 8)
  assert not lpp.ev9_test_external_tx_allowed(forwarded_tx, 1, True)
  assert not lpp.can_send_with_result(forwarded_tx, 1, True)
  assert pop_bus(1) == []

  # Internal origin is not a generic bypass: only the exact state-appropriate
  # restore request may pass the queue-boundary allowlist.
  assert not lpp.can_send_ev9_preinit_with_result(vehicle_tx, 1)
  restore = libpanda_py.make_CANPacket(0x730, 1, b"\x03\x28\x00\x01".ljust(8, b"\x00"))
  assert lpp.can_send_ev9_preinit_with_result(restore, 1)
  assert len(pop_bus(1)) == 1

  lpp.ev9_test_tick(5_200_002, False)
  assert lpp.ev9_test_get_cancel_count(0) == 1
  assert lpp.ev9_test_get_cancel_count(1) == 1
  assert not lpp.ev9_test_external_tx_allowed(vehicle_tx, 1, False)
  assert not lpp.can_send_with_result(vehicle_tx, 1, False)
  assert pop_bus(1) == []
  for now in range(5_200_003, 5_200_103):
    lpp.ev9_test_tick(now, False)
  assert lpp.ev9_test_get_cancel_count(0) == 1
  assert lpp.ev9_test_get_cancel_count(1) == 1


def test_suppression_timeout_without_post_ownership_oem_keeps_bridge():
  enter_wait_comm()
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 20_000)
  pop_bus(0)
  pop_bus(1)

  lpp.ev9_test_tick(400_000, True)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & FLAG_BRIDGE_ACTIVE
  assert timing().restore_us == 0
  assert pop_bus(0)
  assert pop_bus(1)


def test_wait_suppression_full_off_drains_and_rearms():
  enter_wait_comm()
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 20_000)
  pop_bus(0)
  pop_bus(1)
  assert status().state == WAIT_SUPPRESSION

  lpp.ev9_test_tick(5_020_001, False)
  assert status().state == RESTORING
  lpp.ev9_test_tick(5_070_001, False)
  assert lpp.ev9_test_get_cancel_count(0) == 1
  assert lpp.ev9_test_get_cancel_count(1) == 1
  assert status().state == RESTORING

  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 5_080_000)
  assert status().state == COLLECTING
  assert status().fingerprint == 0x04


def test_failed_restore_enqueue_never_starts_the_release_lease():
  enter_restoring_live()
  saturate_bus(1)
  lpp.ev9_test_tick(250_002, True)
  assert status().state == RESTORING
  assert status().flags & FLAG_BRIDGE_ACTIVE
  assert not status().flags & FLAG_RESTORE_SENT
  assert timing().restore_us == 0

  # Stock convergence is proof of enabled communication, but release still
  # waits until the stale software queue is actually empty.
  lpp.ev9_test_rx(canfd(0x100, 0, 24), 251_000)
  for i, (addr, bus, length) in enumerate((
    (0x12A, 1, 16), (0xCB, 1, 24), (0x160, 1, 16), (0x1A0, 1, 32),
  )):
    lpp.ev9_test_rx(canfd(addr, bus, length), 252_000 + i * 1_000)
  assert status().state == RESTORING
  assert timing().restore_us == 0

  pop_bus(1)
  lpp.ev9_test_tick(256_000, True)
  assert status().state == ABORTED
  sent = pop_bus(1)
  assert all(dat[:4] != b"\x03\x28\x00\x01" for _, dat, _ in sent)
  assert any(dat[:3] == b"\x02\x10\x01" for _, dat, _ in sent)


def test_restore_queue_and_silence_never_release_confirmed_bridge_without_proof():
  enter_active()
  lpp.ev9_test_tick(5_020_001, False)
  assert status().state == RESTORING
  assert status().flags & FLAG_BRIDGE_ACTIVE
  assert not status().flags & FLAG_RESTORE_SENT
  assert pop_bus(0) == []
  assert pop_bus(1) == []

  # After a full off epoch and drain guard, stale software/hardware TX is
  # cancelled. State remains contained until the next valid physical frame.
  lpp.ev9_test_tick(5_070_001, False)
  assert status().state == RESTORING
  assert status().flags & FLAG_BRIDGE_ACTIVE
  assert pop_bus(0) == []
  assert pop_bus(1) == []

  # The next valid CAN-FD frame starts a clean cycle and cannot inherit queued
  # replacements or the old fingerprint.
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 5_080_000)
  assert status().state == COLLECTING
  assert status().fingerprint == 0x04
  lpp.ev9_test_rx(canfd(0x100, 0, 24), 5_080_100)
  lpp.ev9_test_rx(wheel_speeds(), 5_080_150)
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x45}), 5_080_200)
  assert status().state == WAIT_SESSION
  pop_single_diag(b"\x02\x10\x03")


def test_partial_collecting_identity_is_cleared_across_bus_sleep():
  lpp.ev9_test_rx(canfd(0x100, 0, 24), 1_000)
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 1_100)
  assert status().state == COLLECTING
  assert status().fingerprint == 0x05

  lpp.ev9_test_tick(5_001_101, False)
  assert status().state == COLLECTING
  assert status().fingerprint == 0
  assert status().first_can_us == 0

  # One powertrain frame on the next wake cannot complete the previous tuple.
  lpp.ev9_test_rx(canfd(0x35, 1, 32), 5_002_000)
  assert status().state == COLLECTING
  assert status().fingerprint == 0x02
  assert pop_bus(1) == []


def test_fresh_critical_traffic_prevents_aborted_cycle_false_sleep_reset():
  feed_identity()
  pop_single_diag(b"\x02\x10\x03")
  expire_unanswered_session()
  pop_single_diag(b"\x02\x10\x01")
  original_first_can = status().first_can_us
  original_abort = timing().abort_us

  # The failed capture reset from inside this fresh physical critical RX hook
  # because 0x35/0xA0 alone had been quiet for five seconds.
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 5_201_201)
  assert status().state == ABORTED
  assert status().first_can_us == original_first_can
  assert timing().abort_us == original_abort

  # Genuine silence still rearms the next fully-off cycle.
  lpp.ev9_test_tick(10_201_202, False)
  assert status().state == ABORTED
  assert lpp.ev9_test_get_cancel_count(0) == 1
  assert lpp.ev9_test_get_cancel_count(1) == 1
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 10_201_203)
  assert status().state == COLLECTING
  assert status().first_can_us == 10_201_203


def test_aborted_cleanup_is_drained_and_rearm_resets_only_once():
  feed_identity()
  pop_single_diag(b"\x02\x10\x03")
  expire_unanswered_session()
  # Deliberately leave the queued 10 01 cleanup in bus 1.
  assert any(dat[:3] == b"\x02\x10\x01" for _, dat, _ in pop_bus(1))
  cleanup = libpanda_py.make_CANPacket(0x730, 1, b"\x02\x10\x01" + b"\x00" * 5)
  lpp.can_push(lpp.tx2_q, cleanup)

  lpp.ev9_test_tick(5_201_201, False)
  assert status().state == ABORTED
  assert pop_bus(0) == []
  assert pop_bus(1) == []
  assert lpp.ev9_test_get_cancel_count(0) == 1
  assert lpp.ev9_test_get_cancel_count(1) == 1

  for now in range(5_201_202, 5_201_302):
    lpp.ev9_test_tick(now, False)
  assert lpp.ev9_test_get_cancel_count(0) == 1
  assert lpp.ev9_test_get_cancel_count(1) == 1

  # The physical ignition line can rise before CAN wakes. It must not reuse the
  # old fingerprint or dispatch diagnostics ahead of the first new frame.
  lpp.ev9_test_tick(5_201_400, True)
  assert status().state == ABORTED
  assert pop_bus(1) == []
  assert lpp.ev9_test_get_cancel_count(0) == 1
  assert lpp.ev9_test_get_cancel_count(1) == 1

  feed_identity(base=5_202_000)
  sent = pop_bus(1)
  assert sum(dat[:3] == b"\x02\x10\x03" for _, dat, _ in sent) == 1
  assert all(dat[:3] != b"\x02\x10\x01" for _, dat, _ in sent)


def test_pending_rx_blocks_off_cycle_core_flush():
  feed_identity()
  pop_single_diag(b"\x02\x10\x03")
  expire_unanswered_session()

  lpp.ev9_test_set_rx_idle(1, False)
  lpp.ev9_test_tick(5_201_201, False)
  assert lpp.ev9_test_get_cancel_count(0) == 0
  assert lpp.ev9_test_get_cancel_count(1) == 0
  lpp.set_safety_hooks(SAFETY_ALLOUTPUT, 0)
  vehicle_tx = libpanda_py.make_CANPacket(0x321, 1, b"\x00" * 8)
  assert not lpp.ev9_test_external_tx_allowed(vehicle_tx, 1, False)
  assert not lpp.can_send_with_result(vehicle_tx, 1, False)
  assert not lpp.ev9_test_tx_drain_allowed(0)
  assert not lpp.ev9_test_tx_drain_allowed(1)
  assert lpp.ev9_test_tx_drain_allowed(2)

  # A wake already captured before both cores froze is drained from RX but may
  # not drive the old fingerprint while the atomic purge is pending.
  original_first_can = status().first_can_us
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 5_201_201)
  assert status().state == ABORTED
  assert status().first_can_us == original_first_can

  lpp.ev9_test_set_rx_idle(1, True)
  lpp.ev9_test_tick(5_201_202, False)
  assert lpp.ev9_test_get_cancel_count(0) == 1
  assert lpp.ev9_test_get_cancel_count(1) == 1
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 5_201_203)
  assert status().state == COLLECTING
  assert status().fingerprint == 0x04


def test_fresh_critical_traffic_prevents_restoring_cycle_false_sleep_reset():
  enter_wait_comm()
  lpp.ev9_test_tick(61_000, False)
  assert status().state == READY_PENDING_RESPONSE
  lpp.ev9_test_tick(301_200, False)
  assert status().state == RESTORING
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  lpp.ev9_test_tick(351_200, False)
  pop_single_diag(b"\x03\x28\x00\x01")
  original_first_can = status().first_can_us
  original_restore = timing().restore_us

  lpp.ev9_test_rx(canfd(0x100, 0, 24), 5_201_201)
  assert status().state == RESTORING
  assert status().first_can_us == original_first_can
  assert timing().restore_us == original_restore
  pop_bus(1)

  lpp.ev9_test_tick(10_201_202, False)
  assert status().state == RESTORING
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 10_201_203)
  assert status().state == COLLECTING
  assert status().first_can_us == 10_201_203
  assert status().fingerprint == 0x04


def test_ignition_held_start_gap_preserves_ambiguous_cycle_until_true_off():
  enter_wait_comm()
  lpp.ev9_test_tick(61_000, False)
  assert status().state == READY_PENDING_RESPONSE
  lpp.ev9_test_tick(301_200, False)
  assert status().state == RESTORING
  lpp.ev9_test_tick(351_200, False)
  pop_single_diag(b"\x03\x28\x00\x01")
  original_session_request = timing().session_request_us
  original_outcome = status().outcome_us

  # This is the failed capture's ordering: a fresh critical frame arrives just
  # after the five-second vehicle-clock gap, before the host ignition tick.
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 5_201_201)
  lpp.ev9_test_tick(5_201_202, True)
  pop_bus(0)
  pop_bus(1)

  # Keep ignition asserted across the measured 5.162-second startup blackout.
  lpp.ev9_test_tick(10_363_202, True)
  assert status().state == RESTORING
  assert timing().session_request_us == original_session_request
  assert status().outcome_us == original_outcome

  # Later READY/brake/wake/session evidence must never reopen diagnostics in
  # the same failed cycle.
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x51}), 10_364_000)
  lpp.ev9_test_rx(canfd(0x175, 1, 24, {10: 0x02}), 10_364_100)
  lpp.ev9_test_rx(canfd(0x100, 0, 24), 10_364_200)
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 10_364_300)
  lpp.ev9_test_tick(10_500_000, True)
  sent = pop_bus(1)
  assert all(dat[:3] != b"\x02\x10\x03" for _, dat, _ in sent)
  assert all(dat[:4] != b"\x03\x28\x01\x01" for _, dat, _ in sent)
  assert status().state == RESTORING

  # Ignition-low plus genuine all-CAN silence cancels stale TX and arms the
  # next physical frame as a new cycle.
  lpp.ev9_test_tick(10_500_001, False)
  lpp.ev9_test_tick(10_520_001, False)
  lpp.ev9_test_tick(15_364_301, False)
  assert status().state == RESTORING
  feed_identity(base=15_365_000)
  pop_single_diag(b"\x02\x10\x03")


def test_ignition_preserves_confirmed_bridge_through_direct_start_blackout():
  enter_active()
  lpp.ev9_test_tick(100_000, True)
  pop_bus(0)
  pop_bus(1)

  # The direct trial had a 5.162 s 0x35/0xA0 gap. Confirmed ownership must not
  # restore or reinitialize while the physical ignition line remains asserted.
  lpp.ev9_test_tick(5_300_000, True)
  assert status().state == ACTIVE
  assert status().flags & FLAG_BRIDGE_ACTIVE
  assert timing().restore_us == 0

  # Once ignition drops, the same stale clocks represent a real shutdown and
  # enter ordered stock restoration after the raw GPIO debounce.
  lpp.ev9_test_tick(5_300_001, False)
  assert status().state == ACTIVE
  lpp.ev9_test_tick(5_320_001, False)
  assert status().state == RESTORING
  assert status().flags & FLAG_BRIDGE_ACTIVE
  assert timing().restore_us == 0
  lpp.ev9_test_tick(5_370_001, False)
  assert status().state == RESTORING
  assert timing().restore_us == 0
  assert pop_bus(0) == []
  assert pop_bus(1) == []


def test_ignition_fall_restores_once_and_blocks_awake_off_cycle_restart():
  enter_active()
  lpp.ev9_test_tick(100_000, True)
  pop_bus(0)
  pop_bus(1)
  freeze_before = lpp.ev9_test_get_freeze_count()
  cancels_before = (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1))

  lpp.ev9_test_tick(100_001, False)
  assert status().state == ACTIVE
  lpp.ev9_test_tick(120_001, False)
  assert status().state == RESTORING
  assert lpp.ev9_test_get_freeze_count() > freeze_before
  assert lpp.ev9_test_get_cancel_count(0) == cancels_before[0] + 1
  assert lpp.ev9_test_get_cancel_count(1) == cancels_before[1] + 1

  lpp.ev9_test_tick(170_001, False)
  pop_single_diag(b"\x03\x28\x00\x01")
  lpp.ev9_test_rx(diag(2, 0x68, 0x00), 170_002)
  lpp.ev9_test_tick(170_003, False)
  assert status().state == ABORTED
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  pop_bus(1)

  # Door/lock traffic can repeat the complete identity tuple while ignition
  # remains low. It must not restart diagnostics or reset the CAN cores again.
  cancels = (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1))
  for base in (200_000, 500_000, 800_000):
    feed_identity(state=0x01, base=base)
    assert status().state == ABORTED
    assert pop_bus(1) == []
  assert (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1)) == cancels

  # Genuine all-CAN silence arms exactly one new epoch, but another complete
  # door identity still cannot originate diagnostics without occupant-start
  # proof.
  lpp.ev9_test_tick(5_800_201, False)
  assert status().state == ABORTED
  feed_identity(state=0x01, base=5_801_000)
  assert status().state == COLLECTING
  assert pop_bus(1) == []

  # A real warm start supplies fresh brake plus ignition and uses the already
  # collected stationary identity for one bounded request.
  lpp.ev9_test_rx(canfd(0x175, 1, 24, {10: 0x02}), 5_802_000)
  lpp.ev9_test_tick(5_802_001, True)
  lpp.ev9_test_rx(wheel_speeds(), 5_802_002)
  assert status().state == WAIT_SESSION
  pop_single_diag(b"\x02\x10\x03")


@pytest.mark.parametrize("ready_pending", [False, True])
def test_off_latched_late_disable_positive_stays_quiescent_restoring(ready_pending):
  enter_wait_comm()
  ignition_high_us = 61_000 if ready_pending else 12_000
  lpp.ev9_test_tick(ignition_high_us, True)
  assert status().state == (READY_PENDING_RESPONSE if ready_pending else WAIT_COMM_CONTROL)
  pop_bus(0)
  pop_bus(1)

  ignition_low_us = ignition_high_us + 1
  lpp.ev9_test_tick(ignition_low_us, False)
  assert status().state == (READY_PENDING_RESPONSE if ready_pending else WAIT_COMM_CONTROL)
  ignition_fall_us = ignition_low_us + 20_000
  lpp.ev9_test_tick(ignition_fall_us, False)
  assert status().state == RESTORING
  assert pop_bus(0) == []
  assert pop_bus(1) == []

  response_us = ignition_fall_us + 1
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), response_us)
  assert status().state == RESTORING
  assert not status().flags & FLAG_BRIDGE_ACTIVE
  assert status().last_response == 0x68
  assert timing().comm_control_response_us == response_us
  assert timing().first_replacement_us == 0
  assert pop_bus(0) == []
  assert pop_bus(1) == []

  lpp.ev9_test_tick(ignition_fall_us + 50_000, False)
  assert status().state == RESTORING
  assert pop_bus(0) == []
  pop_single_diag(b"\x03\x28\x00\x01")


def test_off_latched_exhausted_restore_never_resumes_fallback_bridge():
  enter_active()
  lpp.ev9_test_tick(100_000, True)
  pop_bus(0)
  pop_bus(1)

  lpp.ev9_test_tick(100_001, False)
  assert status().state == ACTIVE
  lpp.ev9_test_tick(120_001, False)
  assert status().state == RESTORING
  assert pop_bus(0) == []
  assert pop_bus(1) == []

  for now_us in (170_001, 220_001, 270_001):
    lpp.ev9_test_tick(now_us, False)
    assert status().state == RESTORING
    assert pop_bus(0) == []
    pop_single_diag(b"\x03\x28\x00\x01")

  # Normal READY containment resumes the bridge after this timeout. OFF is a
  # terminal epoch: stay quiescent until stock proof or a true sleep rearm.
  for now_us in (370_001, 470_001):
    lpp.ev9_test_tick(now_us, False)
    assert status().state == RESTORING
    assert status().flags & FLAG_BRIDGE_ACTIVE
    assert pop_bus(0) == []
    assert pop_bus(1) == []


def test_unqualified_active_off_restore_cannot_warm_rearm():
  enter_active()
  lpp.ev9_test_tick(100_000, True)
  pop_bus(0)
  pop_bus(1)

  lpp.ev9_test_tick(100_001, False)
  assert status().state == ACTIVE
  lpp.ev9_test_tick(120_001, False)
  lpp.ev9_test_tick(170_001, False)
  pop_single_diag(b"\x03\x28\x00\x01")
  lpp.ev9_test_rx(diag(2, 0x68, 0x00), 170_002)
  lpp.ev9_test_tick(170_003, False)
  assert status().state == ABORTED
  pop_bus(0)
  pop_bus(1)
  cancels = (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1))

  # This cycle never reached a fresh host HANDOFF. Even a genuine rise after
  # the cleanup P2 window cannot create a warm epoch.
  lpp.ev9_test_tick(230_003, True)
  lpp.ev9_test_tick(230_004, False)
  lpp.ev9_test_tick(250_004, False)
  assert status().state == ABORTED
  assert (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1)) == cancels
  assert pop_bus(0) == []
  assert pop_bus(1) == []

  for now_us in (260_000, 270_000, 280_000, 290_000):
    lpp.ev9_test_tick(now_us, False)
    assert status().state == ABORTED
    assert (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1)) == cancels
    assert pop_bus(0) == []
    assert pop_bus(1) == []


def test_raw_off_edge_retains_warm_token_after_one_way_handoff():
  enter_handoff()
  ignition_high_us = 200_001
  ignition_low_us = ignition_high_us + 1
  lpp.ev9_test_tick(ignition_high_us, True)
  lpp.ev9_test_tick(ignition_low_us, False)
  assert status().state == HANDOFF

  # Route 18a published raw ignition low before the firmware's debounced OFF
  # transition. A host watchdog notification must not undo the completed
  # handoff while that OFF edge is being debounced.
  delayed_fall_us = ignition_low_us + 120_000
  lpp.ev9_test_host_watchdog_lost(delayed_fall_us - 1, True)
  assert status().state == HANDOFF
  assert status().flags & FLAG_HOST_HANDOFF
  assert lpp.ev9_test_ignition_low_handoff_candidate()
  lpp.ev9_test_tick(delayed_fall_us, False)
  assert status().state == RESTORING
  assert lpp.ev9_test_warm_rearm_candidate()

  response_us = prove_off_restore_exact(delayed_fall_us)
  assert lpp.ev9_test_warm_rearm_candidate()
  pop_single_diag(b"\x02\x10\x01")
  cancels = (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1))

  # Five seconds of OFF silence and later body-network identity remain
  # quiescent. Only a future physical ignition rise may consume this token.
  quiet_us = response_us + 5_000_001
  lpp.ev9_test_tick(quiet_us, False)
  feed_identity(base=quiet_us + 1_000)
  assert status().state == ABORTED
  assert pop_bus(0) == []
  assert pop_bus(1) == []
  assert (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1)) == cancels


def test_fresh_handoff_exact_restore_warm_rearm_starts_one_fresh_diag_epoch():
  ignition_fall_us = enter_off_restore_from_handoff()
  response_us = prove_off_restore_exact(ignition_fall_us)
  assert lpp.can_slots_empty(lpp.tx2_q) < lpp.tx2_q.fifo_size - 1  # queued cleanup 10 01
  pop_single_diag(b"\x02\x10\x01")
  cancels = (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1))

  # A fresh HANDOFF has a dedicated warm token. Even a five-second quiet
  # interval followed by a complete restored stock identity must stay latched
  # while ignition remains low. This is the seated OFF boundary observed live:
  # stock 0x100/12A/CB/160/1A0 returned, then body-network wake chatter caused
  # an immediate off-state re-knockout before this guard existed.
  quiet_us = response_us + 5_000_001
  lpp.ev9_test_tick(quiet_us, False)
  assert status().state == ABORTED
  assert (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1)) == cancels
  feed_identity(base=quiet_us + 1_000)
  assert status().state == ABORTED
  assert pop_bus(0) == []
  assert pop_bus(1) == []

  # The cleanup transaction gets its complete P2 window. At the boundary a
  # genuine ignition rise atomically purges the old epoch before accepting CAN.
  rise_us = quiet_us + 10_000
  lpp.ev9_test_tick(rise_us, True)
  assert lpp.ev9_test_get_cancel_count(0) == cancels[0] + 1
  assert lpp.ev9_test_get_cancel_count(1) == cancels[1] + 1
  assert pop_bus(0) == []
  assert pop_bus(1) == []
  lpp.ev9_test_tick(rise_us + 1, True)
  assert lpp.ev9_test_get_cancel_count(0) == cancels[0] + 1
  assert lpp.ev9_test_get_cancel_count(1) == cancels[1] + 1

  # Classic/stale diagnostics cannot open the epoch. The first valid physical
  # CAN-FD frame performs a full init and contributes only its current bit.
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), rise_us + 2)
  assert status().state == ABORTED
  first_can_us = rise_us + 3
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), first_can_us)
  fresh = status()
  fresh_timing = timing()
  assert fresh.state == COLLECTING
  assert fresh.fingerprint == 0x04
  assert fresh.attempts == 0
  assert fresh.last_service == 0
  assert fresh.first_can_us == first_can_us
  assert fresh_timing.cycle_started_us == first_can_us
  assert fresh_timing.session_request_us == 0
  assert fresh_timing.comm_control_us == 0
  assert fresh_timing.handoff_us == 0
  assert fresh_timing.restore_us == 0
  assert fresh_timing.abort_us == 0

  lpp.ev9_test_tick(first_can_us + 1, True)
  lpp.ev9_test_rx(canfd(0x175, 1, 24, {10: 0x02}), first_can_us + 1)
  lpp.ev9_test_rx(canfd(0x100, 0, 24), first_can_us + 1)
  assert pop_bus(1) == []
  lpp.ev9_test_rx(wheel_speeds(), first_can_us + 2)
  lpp.ev9_test_rx(canfd(0x35, 1, 32), first_can_us + 3)
  assert status().state == WAIT_SESSION
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), first_can_us + 10_000)
  assert status().state == WAIT_COMM_CONTROL
  pop_single_diag(b"\x03\x28\x01\x01")
  lpp.ev9_test_tick(first_can_us + 10_001, True)
  assert pop_bus(1) == []


def test_fresh_stock_convergence_also_proves_warm_rearm():
  ignition_fall_us = enter_off_restore_from_handoff()
  stock_us = ignition_fall_us + 1_000
  stock_frames = (
    canfd(0x100, 0, 24), canfd(0x12A, 1, 16), canfd(0xCB, 1, 24),
    canfd(0x160, 1, 16), canfd(0x1A0, 1, 32),
  )
  for offset, packet in enumerate(stock_frames):
    lpp.ev9_test_rx(packet, stock_us + offset)
  assert status().state == ABORTED
  assert timing().restore_us == 0  # no 28 00 was needed for observable stock

  cancels = (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1))
  rise_us = stock_us + len(stock_frames) - 1 + 50_000
  lpp.ev9_test_tick(rise_us, True)
  assert lpp.ev9_test_get_cancel_count(0) == cancels[0] + 1
  assert lpp.ev9_test_get_cancel_count(1) == cancels[1] + 1
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), rise_us + 1)
  assert status().state == COLLECTING
  assert status().fingerprint == 0x04


def test_warm_rise_before_cleanup_p2_is_not_deferred():
  ignition_fall_us = enter_off_restore_from_handoff()
  response_us = prove_off_restore_exact(ignition_fall_us)
  cancels = (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1))

  lpp.ev9_test_tick(response_us + 49_999, True)
  assert (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1)) == cancels
  lpp.ev9_test_tick(response_us + 60_000, True)
  assert status().state == ABORTED
  assert (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1)) == cancels

  # Holding high past P2 must not remember the rejected rise. A fresh,
  # debounced low followed by another rise is required.
  lpp.ev9_test_tick(response_us + 60_001, False)
  lpp.ev9_test_tick(response_us + 80_001, False)
  lpp.ev9_test_tick(response_us + 80_002, True)
  assert lpp.ev9_test_get_cancel_count(0) == cancels[0] + 1
  assert lpp.ev9_test_get_cancel_count(1) == cancels[1] + 1


def test_rise_before_restore_proof_requires_a_second_real_edge():
  ignition_fall_us = enter_off_restore_from_handoff()
  restore_request_us = ignition_fall_us + 50_000
  lpp.ev9_test_tick(restore_request_us, False)
  pop_single_diag(b"\x03\x28\x00\x01")
  cancels = (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1))

  first_rise_us = restore_request_us + 10_000
  lpp.ev9_test_tick(first_rise_us, True)
  assert status().state == RESTORING
  assert (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1)) == cancels
  proof_us = first_rise_us + 1
  lpp.ev9_test_rx(diag(2, 0x68, 0x00), proof_us)
  assert status().state == ABORTED
  lpp.ev9_test_tick(proof_us + 50_000, True)
  assert (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1)) == cancels

  lpp.ev9_test_tick(proof_us + 50_001, False)
  lpp.ev9_test_tick(proof_us + 70_001, False)
  lpp.ev9_test_tick(proof_us + 70_002, True)
  assert lpp.ev9_test_get_cancel_count(0) == cancels[0] + 1
  assert lpp.ev9_test_get_cancel_count(1) == cancels[1] + 1


def test_unproven_off_restore_never_warm_rearms():
  ignition_fall_us = enter_off_restore_from_handoff()
  cancels = (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1))
  for attempt, now_us in enumerate((ignition_fall_us + 50_000,
                                    ignition_fall_us + 100_000,
                                    ignition_fall_us + 150_000)):
    lpp.ev9_test_tick(now_us, False)
    pop_single_diag(b"\x03\x28\x00\x01")
    if attempt == 0:
      lpp.ev9_test_rx(diag(3, 0x7F, 0x28, 0x22), now_us + 1)
    elif attempt == 1:
      lpp.ev9_test_rx(diag(2, 0x68, 0x01), now_us + 1)
    else:
      lpp.ev9_test_rx(canfd(0xCB, 1, 24), now_us + 1)  # incomplete stock tuple
    assert status().state == RESTORING

  lpp.ev9_test_tick(ignition_fall_us + 250_000, True)
  assert status().state == RESTORING
  assert (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1)) == cancels
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), ignition_fall_us + 250_001)
  assert status().state == RESTORING
  assert pop_bus(0) == []
  assert pop_bus(1) == []


def test_one_way_handoff_remains_qualified_until_later_off_edge():
  enter_handoff()
  stale_high_us = 300_001
  lpp.ev9_test_tick(stale_high_us, True)
  assert status().state == HANDOFF
  assert status().flags & FLAG_HOST_HANDOFF
  pop_bus(0)
  pop_bus(1)

  lpp.ev9_test_tick(stale_high_us + 1, False)
  ignition_fall_us = stale_high_us + 20_001
  lpp.ev9_test_tick(ignition_fall_us, False)
  assert status().state == RESTORING
  response_us = prove_off_restore_exact(ignition_fall_us)
  pop_bus(1)
  cancels = (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1))
  lpp.ev9_test_tick(response_us + 50_000, True)
  assert status().state == ABORTED
  assert (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1)) == cancels


def test_warm_rearm_waits_for_atomic_rx_idle_cleanup_and_preserves_bus_two():
  ignition_fall_us = enter_off_restore_from_handoff()
  response_us = prove_off_restore_exact(ignition_fall_us)
  bus_two = libpanda_py.make_CANPacket(0x321, 2, b"bus-two!")
  assert lpp.can_push(lpp.tx3_q, bus_two)
  cancels = (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1))
  freeze_before = lpp.ev9_test_get_freeze_count()
  lpp.ev9_test_set_rx_idle(1, False)

  rise_us = response_us + 50_000
  lpp.ev9_test_tick(rise_us, True)
  assert lpp.ev9_test_get_freeze_count() > freeze_before
  assert (lpp.ev9_test_get_cancel_count(0), lpp.ev9_test_get_cancel_count(1)) == cancels
  assert not lpp.ev9_test_tx_drain_allowed(0)
  assert not lpp.ev9_test_tx_drain_allowed(1)
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), rise_us + 1)
  assert status().state == ABORTED

  lpp.ev9_test_set_rx_idle(1, True)
  lpp.ev9_test_tick(rise_us + 2, True)
  assert lpp.ev9_test_get_cancel_count(0) == cancels[0] + 1
  assert lpp.ev9_test_get_cancel_count(1) == cancels[1] + 1
  assert pop_bus(0) == []
  assert pop_bus(1) == []
  assert pop_bus(2) == [(0x321, b"bus-two!", False)]

  # A classic packet still cannot initialize after the purge; the next valid
  # CAN-FD packet creates exactly one fresh epoch.
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), rise_us + 3)
  assert status().state == ABORTED
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), rise_us + 4)
  assert status().state == COLLECTING
  assert status().fingerprint == 0x04
  lpp.ev9_test_tick(rise_us + 5, True)
  assert lpp.ev9_test_get_cancel_count(0) == cancels[0] + 1
  assert lpp.ev9_test_get_cancel_count(1) == cancels[1] + 1


def test_pending_start_ignition_fall_aborts_before_session_dispatch():
  assert lpp.set_safety_hooks(SAFETY_SILENT, 0) == 0
  lpp.ev9_test_tick(500, True)
  feed_identity(base=1_000)
  assert status().state == COLLECTING
  assert status().attempts == 0
  assert timing().session_request_us == 0
  assert pop_bus(0) == []
  assert pop_bus(1) == []

  lpp.ev9_test_tick(1_300, False)
  assert status().state == COLLECTING
  assert status().attempts == 0
  assert timing().session_request_us == 0
  lpp.ev9_test_tick(21_300, False)
  assert status().state == ABORTED
  assert status().attempts == 0
  assert status().last_service == 0
  assert timing().session_request_us == 0
  assert pop_bus(0) == []
  assert pop_bus(1) == []


def test_door_wake_is_passive_until_brake_plus_ignition_confirm_start():
  feed_identity(state=0x01)
  assert status().state == COLLECTING
  assert status().fingerprint == 0x8F
  assert status().attempts == 0
  assert pop_bus(1) == []

  # Brake without ignition still cannot originate diagnostics.
  lpp.ev9_test_rx(canfd(0x175, 1, 24, {10: 0x02}), 110_000)
  assert status().state == COLLECTING
  assert pop_bus(1) == []

  # A later physical ignition rise completes occupant-start proof. The next
  # ordinary physical frame dispatches exactly one bounded session request.
  lpp.ev9_test_tick(110_001, True)
  lpp.ev9_test_rx(wheel_speeds(), 110_002)
  assert status().state == WAIT_SESSION
  assert status().trigger == 3  # DRIVER_BRAKE
  pop_single_diag(b"\x02\x10\x03")
  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 120_000)
  pop_single_diag(b"\x03\x28\x01\x01")
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 130_000)
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x45}), 131_000)
  lpp.ev9_test_tick(192_000, False)
  assert status().state == ACTIVE


def test_graceful_release_is_cycle_bound_and_requires_exact_stock_proof():
  enter_handoff()
  cycle_started_us = timing().cycle_started_us
  live_us = 200_001
  lpp.ev9_test_tick(live_us, True)

  # A cycle token is authentication, not a safe mid-drive restore boundary.
  assert not lpp.ev9_test_request_release((cycle_started_us + 1) & 0xFFFF, live_us)
  assert not lpp.ev9_test_request_release(cycle_started_us & 0xFFFF, live_us)
  assert status().state == HANDOFF

  lpp.ev9_test_tick(live_us + 1, False)
  release_us = live_us + 20_001
  lpp.ev9_test_tick(release_us, False)
  assert status().state == RESTORING
  assert lpp.ev9_test_request_release(cycle_started_us & 0xFFFF, release_us)
  assert lpp.ev9_test_must_preserve()
  assert timing().reserved & LIFECYCLE_RELEASE_REQUESTED
  assert not timing().reserved & LIFECYCLE_RELEASE_COMPLETE

  lpp.ev9_test_tick(release_us + 50_000, False)
  pop_single_diag(b"\x03\x28\x00\x01")
  assert lpp.ev9_test_must_preserve()

  proof_us = release_us + 50_001
  lpp.ev9_test_rx(diag(2, 0x68, 0x00), proof_us)
  assert status().state == ABORTED
  pop_single_diag(b"\x02\x10\x01")
  assert lpp.ev9_test_must_preserve()
  lpp.ev9_test_tick(proof_us + 50_000, False)
  assert timing().reserved & LIFECYCLE_RELEASE_COMPLETE
  assert not lpp.ev9_test_must_preserve()


def test_firmware_usb_gate_blocks_disruptive_mutations_until_release():
  enter_active()
  assert lpp.ev9_test_must_preserve()

  for request, param1, param2 in (
    (0xC5, 0, 0), (0xD1, 1, 0), (0xD8, 0, 0), (0xDB, 1, 0),
    (0xDC, 28, 0x8495), (0xDC, 36, 0x8494), (0xDE, 0, 2500),
    (0xE5, 1, 0), (0xE7, 1, 0), (0xE8, 0, 1), (0xF1, 0, 0), (0xF1, 1, 0),
    (0xF8, 0, 0), (0xF9, 1, 50000), (0xFC, 1, 1),
  ):
    assert not lpp.ev9_test_usb_request_allowed(request, param1, param2)

  assert lpp.ev9_test_usb_request_allowed(0xDC, 36, 0x8495)
  assert lpp.ev9_test_usb_request_allowed(0xDC, 36, 0x8C95)
  assert lpp.ev9_test_usb_request_allowed(0xE7, 0, 0)
  assert lpp.ev9_test_preserve_can_on_safety_transition(36, 0x8495)
  assert not lpp.ev9_test_preserve_can_on_safety_transition(36, 0x494)
  assert not lpp.ev9_test_preserve_can_on_safety_transition(28, 0x8495)
  assert lpp.ev9_test_usb_request_allowed(0xDE, 0, 5000)
  assert lpp.ev9_test_usb_request_allowed(0xE8, 0, 0)
  assert lpp.ev9_test_usb_request_allowed(0xF1, 0xFFFF, 0)
  assert lpp.ev9_test_usb_request_allowed(0xF1, 2, 0)
  assert lpp.ev9_test_usb_request_allowed(0xEA, 1, 0)


def test_session_request_is_preserved_across_initial_host_configuration():
  feed_identity()
  assert status().state == WAIT_SESSION
  assert lpp.ev9_test_must_preserve()
  assert lpp.ev9_test_preserve_can_on_safety_transition(36, 0x8495)
  assert not lpp.ev9_test_usb_request_allowed(0xD8, 0, 0)
  assert not lpp.ev9_test_usb_request_allowed(0xDE, 0, 2500)
  pop_single_diag(b"\x02\x10\x03")


def test_session_deadline_starts_only_after_temporary_elm327_becomes_nooutput():
  assert lpp.set_safety_hooks(SAFETY_ELM327, 1) == 0
  feed_identity()
  assert status().state == COLLECTING
  assert status().attempts == 0
  assert timing().session_request_us == 0
  assert pop_bus(1) == []

  # Route 183 returned 10 03 and its timeout cleanup in the same hardware
  # batch because the diagnostic clock started while ELM327 was reconfiguring
  # CAN. The resident main loop must establish NOOUTPUT before enqueue/time.
  lpp.ev9_test_tick(2_000, False)
  assert status().state == WAIT_SESSION
  assert status().attempts == 1
  assert timing().session_request_us == 2_000
  pop_single_diag(b"\x02\x10\x03")

  lpp.ev9_test_rx(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 22_000)
  assert status().state == WAIT_COMM_CONTROL
  assert timing().session_response_us == 22_000
  pop_single_diag(b"\x03\x28\x01\x01")


def test_host_watchdog_loss_after_handoff_does_not_restart_resident_bridge():
  enter_handoff()
  assert lpp.set_safety_hooks(36, 0x8495) == 0
  lpp.ev9_test_set_heartbeat_counter(5)
  watchdog_us = 200_001
  lpp.ev9_test_host_watchdog_lost(watchdog_us, True)
  current = status()
  assert current.state == HANDOFF
  assert current.flags & FLAG_BRIDGE_ACTIVE
  assert current.flags & FLAG_SUPPRESSION_CONFIRMED
  assert current.flags & FLAG_HOST_HANDOFF
  assert not timing().reserved & LIFECYCLE_RELEASE_REQUESTED
  assert lpp.ev9_test_must_preserve()

  heartbeat = canfd(0x100, 0, 24)
  tester_present = libpanda_py.make_CANPacket(0x730, 1, b"\x02\x3e\x80".ljust(8, b"\x00"))
  assert lpp.ev9_test_external_tx_allowed(heartbeat, 0, False)
  assert lpp.ev9_test_external_tx_allowed(tester_present, 1, False)

  # Repeated watchdog samples neither restore the ECU nor synthesize neutral
  # traffic. Normal host/process safety behavior owns the post-handoff path.
  lpp.ev9_test_host_watchdog_lost(watchdog_us + 1, True)
  lpp.ev9_test_tick(watchdog_us + 20_000, True)
  sent = pop_bus(0) + pop_bus(1)
  assert all(dat[:4] != b"\x03\x28\x00\x01" for _, dat, _ in sent)
  assert all(addr != 0x1A0 for addr, _, _ in sent)

  # Host traffic remains on the normal safety path without a second claim.
  lpp.ev9_test_set_heartbeat_counter(0)
  lpp.ev9_test_tick(watchdog_us + 20_001, True)
  assert lpp.ev9_test_external_tx_allowed(heartbeat, 0, False)
  assert lpp.ev9_test_external_tx_allowed(tester_present, 1, False)


def test_tx_queue_clear_after_handoff_does_not_restart_resident_bridge():
  enter_handoff()
  lpp.ev9_test_tx_queue_cleared(0)
  lpp.ev9_test_tx_queue_cleared(1)
  assert status().state == HANDOFF
  assert status().flags & FLAG_HOST_HANDOFF

  lpp.ev9_test_tick(400_000, True)
  assert pop_bus(0) == []
  assert pop_bus(1) == []


def test_host_watchdog_loss_after_proven_off_keeps_off_restore():
  ignition_fall_us = enter_off_restore_from_handoff()
  lpp.ev9_test_host_watchdog_lost(ignition_fall_us + 1, False)
  assert status().state == RESTORING
  assert timing().reserved & LIFECYCLE_RELEASE_REQUESTED

  lpp.ev9_test_tick(ignition_fall_us + 50_000, False)
  pop_single_diag(b"\x03\x28\x00\x01")


def test_staged_reset_failure_latches_quiescent_fault_without_retry_loop():
  enter_active()
  lpp.ev9_test_tick(100_000, True)
  pop_bus(0)
  pop_bus(1)
  lpp.ev9_test_set_reset_failed(True)
  lpp.ev9_test_tick(100_001, False)
  lpp.ev9_test_tick(120_001, False)

  assert status().state == RESTORING
  assert status().flags & FLAG_INTERNAL_TX_REJECTED
  assert timing().reserved & LIFECYCLE_CAN_RESET_FAILED
  assert not lpp.ev9_test_tx_drain_allowed(0)
  assert not lpp.ev9_test_tx_drain_allowed(1)
  freezes = lpp.ev9_test_get_freeze_count()
  for now_us in range(120_002, 120_102):
    lpp.ev9_test_tick(now_us, False)
  assert lpp.ev9_test_get_freeze_count() == freezes


def test_led_fast_service_completes_off_reset_before_next_outer_loop():
  enter_handoff()
  lpp.ev9_test_tick_once(200_001, True)
  lpp.ev9_test_tick_once(200_002, False)
  lpp.ev9_test_tick_once(220_002, False)
  assert status().state == RESTORING
  assert lpp.ev9_test_get_cancel_count(0) == 0
  assert lpp.ev9_test_get_cancel_count(1) == 0

  # This is the only work run from the LED fade. It completes the requested
  # purge without advancing diagnostics or publishing a bridge.
  lpp.ev9_test_service_tx_cancel(220_003)
  assert lpp.ev9_test_get_cancel_count(0) == 1
  assert lpp.ev9_test_get_cancel_count(1) == 1
  assert status().state == RESTORING
  assert timing().restore_us == 0
  assert not status().flags & FLAG_INTERNAL_TX_REJECTED

  # The normal outer state-machine tick retains sole ownership of 28 00.
  lpp.ev9_test_tick_once(270_002, False)
  pop_single_diag(b"\x03\x28\x00\x01")
  assert timing().restore_us == 270_002


def test_production_led_fades_service_only_pending_tx_cancel():
  main = (Path(__file__).parents[1] / "board" / "main.c").read_text()
  assert main.count("ev9_long_preinit_service_tx_cancel(microsecond_timer_get())") == 2


def test_ready_missing_adas_after_panda_reset_runs_restore_only_recovery():
  lpp.ev9_test_rx(canfd(0xA0, 1, 24), 1_000)
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x51}), 2_000)
  assert status().state == ABORTED
  assert pop_bus(1) == []
  assert lpp.ev9_test_must_preserve()
  assert not lpp.ev9_test_usb_request_allowed(0xD8, 0, 0)
  assert not lpp.ev9_test_external_tx_allowed(canfd(0x12A, 1, 16), 1, False)

  lpp.ev9_test_tick(201_999, True)
  assert status().state == ABORTED
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x51}), 201_999)
  lpp.ev9_test_tick(202_000, True)
  assert status().state == RESTORING
  assert lpp.ev9_test_must_preserve()
  lpp.ev9_test_tick(252_000, True)
  sent = pop_bus(1)
  assert [frame[1][:4] for frame in sent if frame[0] == 0x730] == [b"\x03\x28\x00\x01"]
  assert all(frame[1][:3] != b"\x02\x10\x03" for frame in sent)
  assert all(frame[1][:4] != b"\x03\x28\x01\x01" for frame in sent)


def test_ready_with_live_stock_adas_never_enters_reset_recovery():
  lpp.ev9_test_rx(canfd(0xA0, 1, 24), 1_000)
  lpp.ev9_test_rx(canfd(0xCB, 1, 24), 1_500)
  lpp.ev9_test_rx(canfd(0x35, 1, 32, {3: 0x51}), 2_000)
  assert status().state == ABORTED
  assert not lpp.ev9_test_must_preserve()
  lpp.ev9_test_tick(302_000, True)
  assert status().state == ABORTED
  assert pop_bus(1) == []


def test_status_page_zero_latch_survives_intervening_rx_until_page_one_consumes_it():
  enter_wait_comm()
  page_zero = status()
  assert not page_zero.flags & FLAG_BRIDGE_ACTIVE

  # An RX transition between USB transfers must not replace page zero's timing.
  lpp.ev9_test_rx(diag(2, 0x68, 0x01), 20_000)
  page_one = raw_timing()
  assert page_one.flags == page_zero.flags
  assert page_one.comm_control_response_us == 0

  # The next explicit page-zero read starts the new coherent snapshot.
  current = status()
  assert current.flags & FLAG_BRIDGE_ACTIVE
  assert raw_timing().comm_control_response_us == 20_000


def test_status_struct_wire_sizes():
  assert ffi.sizeof("ev9_long_preinit_status_t") == 64
  assert ffi.sizeof("ev9_long_preinit_timing_t") == 64
  assert struct.calcsize("<14BH12I") == 64
  assert struct.calcsize("<4B15I") == 64


@pytest.mark.parametrize(("flipped", "expected"), [
  (False, (0, 1, 2)),
  (True, (2, 1, 0)),
])
def test_initial_harness_orientation_maps_first_rx_and_tx(flipped, expected):
  lpp.can_set_orientation(flipped)
  assert tuple(lpp.ev9_test_bus_from_can_num(i) for i in range(3)) == expected
  assert tuple(lpp.ev9_test_can_num_from_bus(i) for i in range(3)) == expected


def test_main_applies_detected_orientation_before_first_can_init():
  main = (Path(__file__).parents[1] / "board" / "main.c").read_text()
  tick = main.index("static void tick_handler(void)")
  assert main.index("static uint8_t prev_harness_status = HARNESS_STATUS_NC;") < tick

  harness_init = main.index("  harness_init();")
  initial_orientation = main.index(
    "  can_set_orientation(harness.status == HARNESS_STATUS_FLIPPED);", harness_init,
  )
  seed_tick_cache = main.index("  prev_harness_status = harness.status;", initial_orientation)
  first_safety_init = main.index("  set_safety_mode(SAFETY_NOOUTPUT, 0U);", seed_tick_cache)
  assert harness_init < initial_orientation < seed_tick_cache < first_safety_init


def test_preinit_can_reinit_guards_preserve_generic_panda_semantics():
  main = (Path(__file__).parents[1] / "board" / "main.c").read_text()
  comms = (Path(__file__).parents[1] / "board" / "main_comms.h").read_text()

  # Initial orientation/cache seeding is needed only by the firmware which
  # begins listening before pandad starts. Generic Panda keeps its original
  # tick-local cache and first-transition initialization behavior.
  tick = main.index("static void tick_handler(void)")
  local_cache = main.index("  static uint8_t prev_harness_status = HARNESS_STATUS_NC;", tick)
  assert "#ifndef PANDA_EV9_LONG_PREINIT" in main[tick:local_cache]
  harness_init = main.index("  harness_init();")
  orientation = main.index("  can_set_orientation(harness.status == HARNESS_STATUS_FLIPPED);", harness_init)
  assert "#ifdef PANDA_EV9_LONG_PREINIT" in main[harness_init:orientation]

  # Repeated pandad configuration must not reset EV9's resident CAN state, but
  # normal firmware retains the established set-and-reinitialize semantics.
  for request, original_action in (
    ("case 0xdc:", "set_safety_mode(req->param1, (uint16_t)req->param2);"),
    ("case 0xde:", "bus_config[req->param1].can_speed = req->param2;"),
    ("case 0xe5:", "can_loopback = req->param1 > 0U;"),
    ("case 0xf9:", "bus_config[req->param1].can_data_speed = req->param2;"),
    ("case 0xfc:", "bus_config[req->param1].canfd_non_iso = (req->param2 != 0U);"),
  ):
    start = comms.index(request)
    end = comms.index("      break;", start)
    handler = comms[start:end]
    assert "#ifdef PANDA_EV9_LONG_PREINIT" in handler
    assert "#else" in handler
    assert original_action in handler[handler.index("#else"):]


def test_heartbeat_loss_keeps_power_save_off_for_resident_bridge():
  main = (Path(__file__).parents[1] / "board" / "main.c").read_text()
  heartbeat = main.index("if (heartbeat_counter >=")
  watchdog = main.index("ev9_long_preinit_host_watchdog_lost", heartbeat)
  power_save = main.index("if (ev9_long_preinit_must_preserve())", watchdog)
  generic = main.index("#else", power_save)
  guarded = main[power_save:generic]
  assert "set_power_save_state(POWER_SAVE_STATUS_DISABLED);" in guarded
  assert "set_power_save_state(POWER_SAVE_STATUS_ENABLED);" in guarded


def test_profile_crc_init_is_one_time_and_rx_uses_proven_direct_scheduler():
  preinit = (Path(__file__).parents[1] / "board" / "ev9_long_preinit.h").read_text()
  reset = preinit.index("static void ev9_long_preinit_reset_cycle(void)")
  init = preinit.index("static void ev9_long_preinit_init(void)", reset)
  process = preinit.index("static void ev9_preinit_process_rx_sample", init)
  rx = preinit.index("static void ev9_long_preinit_rx_hook", init)
  host = preinit.index("static void ev9_preinit_maybe_complete_handoff", rx)
  assert "gen_crc_lookup_table_16" not in preinit[reset:init]
  assert "gen_crc_lookup_table_16" in preinit[init:process]
  assert "ev9_long_preinit_reset_cycle();" in preinit[process:rx]
  assert preinit[rx:host].count("ev9_preinit_is_valid_canfd(packet)") == 1
  assert "ev9_preinit_process_rx_sample(&sample);" in preinit[rx:host]
  assert "ev9_preinit_service_state(now_us, EV9_PREINIT_CAN_RESET_IDLE);" in preinit[rx:host]
  assert "ev9_preinit_enqueue_rx_event" not in preinit
  assert "ev9_preinit_service_rx_events" not in preinit
  assert "EV9_PREINIT_RX_EVENT_COUNT" not in preinit


def test_rx_isr_uses_proven_direct_preinit_path_and_chains_exact_responses():
  lpp.ev9_test_rx_isr_only(canfd(0xCB, 1, 24), 1_000)
  lpp.ev9_test_rx_isr_only(canfd(0x100, 0, 24), 1_100)
  lpp.ev9_test_rx_isr_only(wheel_speeds(), 1_150)
  lpp.ev9_test_rx_isr_only(canfd(0x35, 1, 32, {3: 0x45}), 1_200)
  assert status().state == WAIT_SESSION
  pop_single_diag(b"\x02\x10\x03")

  lpp.ev9_test_rx_isr_only(diag(6, 0x50, 0x03, 0, 0x32, 1, 0xF4), 10_000)
  assert status().state == WAIT_COMM_CONTROL
  pop_single_diag(b"\x03\x28\x01\x01")

  lpp.ev9_test_rx_isr_only(diag(2, 0x68, 0x01), 20_000)
  assert status().state == WAIT_SUPPRESSION
  assert status().flags & FLAG_BRIDGE_ACTIVE


def test_direct_rx_repetition_does_not_create_false_overflow():
  for now_us in range(1_000, 1_000 + 64):
    lpp.ev9_test_rx_isr_only(canfd(0xCB, 1, 24), now_us)
  assert not status().flags & FLAG_INTERNAL_TX_REJECTED
  assert status().fingerprint & 0x04


def test_direct_rx_uses_early_powertrain_identity_before_terminal_duplicates():
  # The proven path consumes each valid identity frame at RX time; later
  # terminal duplicates cannot displace the early 0x01 sample in a queue.
  lpp.ev9_test_rx_isr_only(canfd(0x175, 1, 24, {10: 0x02}), 900)
  lpp.ev9_test_tick(950, True)
  lpp.ev9_test_rx_isr_only(canfd(0x35, 1, 32, {3: 0x01}), 1_000)
  lpp.ev9_test_rx_isr_only(canfd(0xCB, 1, 24), 1_100)
  lpp.ev9_test_rx_isr_only(wheel_speeds(), 1_150)
  lpp.ev9_test_rx_isr_only(canfd(0x100, 0, 24), 1_200)
  assert status().state == WAIT_SESSION
  for now_us in range(1_001, 1_001 + 64):
    lpp.ev9_test_rx_isr_only(canfd(0x35, 1, 32, {3: 0x45}), 1_201 + now_us)

  assert not status().flags & FLAG_INTERNAL_TX_REJECTED
  assert status().state == WAIT_SESSION
  pop_single_diag(b"\x02\x10\x03")


def test_unmatched_direct_diagnostic_responses_do_not_mutate_ownership():
  for now_us in range(1_000, 1_000 + 32):
    lpp.ev9_test_rx_isr_only(diag(2, 0x68, 0x01), now_us)
  assert status().state == COLLECTING
  assert status().flags == 0


def test_fdcan_restore_drain_checks_and_cancels_hardware_pending():
  fdcan = (Path(__file__).parents[1] / "board" / "drivers" / "fdcan.h").read_text()
  idle = fdcan.index("bool ev9_preinit_can_tx_idle(uint8_t bus_number)")
  request = fdcan.index("void ev9_preinit_can_request_tx_reset(uint32_t now_us)")
  service = fdcan.index("ev9_preinit_can_service_tx_reset(uint32_t now_us)")
  reset_end = fdcan.index("#endif", service)
  assert "FDCANx->TXBRP == 0U" in fdcan[idle:request]
  assert "while (" not in fdcan[request:reset_end]
  assert "delay(" not in fdcan[request:reset_end]
  assert "llcan_clear_send" not in fdcan[request:reset_end]
  radar_init = fdcan.index("radar->CCCR |= FDCAN_CCCR_INIT", service)
  ecan_init = fdcan.index("ecan->CCCR |= FDCAN_CCCR_INIT", radar_init)
  final_rx_check = fdcan.index("radar->RXF0S & FDCAN_RXF0S_F0FL", ecan_init)
  radar_clear = fdcan.index("can_clear(can_queues[EV9_PREINIT_BUS_RADAR])", final_rx_check)
  ecan_clear = fdcan.index("can_clear(can_queues[EV9_PREINIT_BUS_ECAN])", radar_clear)
  radar_reset = fdcan.index("fdcan_configure_in_init(radar)", ecan_clear)
  ecan_reset = fdcan.index("fdcan_configure_in_init(ecan)", radar_reset)
  running = fdcan.index("radar->CCCR &= ~FDCAN_CCCR_INIT", ecan_reset)
  assert service < radar_init < ecan_init < final_rx_check < radar_clear < ecan_clear < radar_reset < ecan_reset < running
  assert "FDCANx->TXBCR" not in fdcan[service:reset_end]
  process = fdcan.index("void process_can(uint8_t can_number)")
  drain_gate = fdcan.index("ev9_long_preinit_tx_drain_allowed(bus_number)", process)
  tx_pop = fdcan.index("can_pop(can_queues[bus_number]", drain_gate)
  assert "FDCANx->IR |= FDCAN_IR_TFE" in fdcan[process:drain_gate]
  assert drain_gate < tx_pop

  can_common = (Path(__file__).parents[1] / "board" / "drivers" / "can_common.h").read_text()
  gate = can_common.index("ev9_long_preinit_internal_tx_allowed(to_push, bus_number)")
  enqueue = can_common.index("queued = can_push(can_queues[bus_number], to_push)", gate)
  assert gate < enqueue
  assert "ev9_preinit_internal ?" in can_common[:gate]

  preinit = (Path(__file__).parents[1] / "board" / "ev9_long_preinit.h").read_text()
  tick = preinit.index("static void ev9_long_preinit_tick(uint32_t now_us, bool ignition)")
  reset_poll = preinit.index("ev9_preinit_can_service_tx_reset(now_us)", tick)
  critical = preinit.index("ENTER_CRITICAL();", reset_poll)
  assert reset_poll < critical


class FakeControlHandle:
  def __init__(self, pages):
    self.pages = pages
    self.calls = []

  def controlRead(self, request_type, request, value, index, length):
    self.calls.append((request_type, request, value, index, length))
    return self.pages.get(value, b"")


def test_python_reader_combines_v4_pages():
  status_page = struct.pack(
    "<14BH12I",
    4, ACTIVE, 7, 2, 0x28, 0x68, 0, 1, 1, 24, 0x45, 2, 3,
    FLAG_SUPPRESSION_CONFIRMED | FLAG_BRIDGE_ACTIVE,
    0x35,
    *range(100, 112),
  )
  timing_page = struct.pack(
    "<4B15I",
    4, 1, FLAG_SUPPRESSION_CONFIRMED | FLAG_BRIDGE_ACTIVE,
    LIFECYCLE_RELEASE_REQUESTED | LIFECYCLE_RELEASE_COMPLETE,
    200, 201, 107, 108, 204, 205, 206, 207, 110, 209, 210, 211, 212, 213, 214,
  )
  panda = object.__new__(Panda)
  panda._handle = FakeControlHandle({0: status_page, 1: timing_page})
  parsed = panda.get_ev9_long_preinit_status()
  assert parsed["version"] == 4
  assert parsed["state"] == ACTIVE
  assert parsed["flags"] == FLAG_SUPPRESSION_CONFIRMED | FLAG_BRIDGE_ACTIVE
  assert parsed["outcome_us"] == 111
  assert parsed["timing_valid"]
  assert parsed["session_request_us"] == 201
  assert parsed["last_vehicle_frame_us"] == 214
  assert parsed["release_requested"]
  assert parsed["release_complete"]
  assert [call[2] for call in panda._handle.calls] == [0, 1, 0]


def test_python_reader_accepts_legacy_v3_page():
  legacy_page = struct.pack(
    "<14BH11I",
    3, ACTIVE, 7, 1, 0x28, 0x68, 0, 1, 1, 24, 0x45, 2, 3, 0,
    0x35,
    *range(300, 311),
  )
  panda = object.__new__(Panda)
  panda._handle = FakeControlHandle({0: legacy_page})
  parsed = panda.get_ev9_long_preinit_status()
  assert parsed["version"] == 3
  assert parsed["state"] == ACTIVE
  assert parsed["flags"] == 0
  assert parsed["ready_us"] == 310
  assert not parsed["timing_valid"]
  assert [call[2] for call in panda._handle.calls] == [0]


def test_python_reader_rejects_cross_cycle_timing_mix():
  first = struct.pack("<14BH12I", 4, WAIT_SUPPRESSION, 7, 1, 0x28, 0x68, 0, 1, 1, 24, 0x45, 2, 3,
                      FLAG_BRIDGE_ACTIVE, 0x35, *range(100, 112))
  second = struct.pack("<14BH12I", 4, ACTIVE, 7, 1, 0x28, 0x68, 0, 1, 1, 24, 0x45, 2, 3,
                       FLAG_BRIDGE_ACTIVE | FLAG_SUPPRESSION_CONFIRMED, 0x35, *range(100, 112))
  timing_page = struct.pack("<4B15I", 4, 1, FLAG_BRIDGE_ACTIVE, 0, *range(200, 215))

  class ChangingHandle(FakeControlHandle):
    def __init__(self):
      super().__init__({1: timing_page})
      self.status_reads = 0

    def controlRead(self, request_type, request, value, index, length):
      if value == 0:
        self.status_reads += 1
        return first if self.status_reads == 1 else second
      return super().controlRead(request_type, request, value, index, length)

  panda = object.__new__(Panda)
  panda._handle = ChangingHandle()
  parsed = panda.get_ev9_long_preinit_status()
  assert not parsed["valid"]
  assert not parsed["timing_valid"]


def test_python_release_control_uses_cycle_token():
  class ReleaseHandle:
    def __init__(self):
      self.calls = []

    def controlRead(self, request_type, request, value, index, length):
      self.calls.append((request_type, request, value, index, length))
      return b"\x01"

  panda = object.__new__(Panda)
  panda._handle = ReleaseHandle()
  assert panda.request_ev9_long_preinit_release(0x12345)
  assert panda._handle.calls == [(Panda.REQUEST_IN, 0xEA, 1, 0x2345, 1)]
