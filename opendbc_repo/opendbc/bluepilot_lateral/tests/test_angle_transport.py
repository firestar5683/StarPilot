"""Mach-E route 0000000d: refresh before publication; neutral restarts from zero."""
import pytest

from collections import defaultdict
from types import SimpleNamespace

from opendbc.car import structs, Bus
from opendbc.car.ford.values import CAR
from opendbc.car.ford.carcontroller import CarController
from opendbc.bluepilot_lateral import BluePilotLateral
from opendbc.bluepilot_lateral.core.angle import AngleController, Inputs, Command


class CoreHost:
  def __init__(self):
    self.controller = AngleController(low_gain=1., high_gain=1.05, recovery_blips=False)
    self.steering_rejected = False
    self.steering_pressed = False
    self.steering_angle = 0.

  def update(self, cc, cs):
    active = cc.latActive and not self.steering_rejected
    self.steering_rejected = False
    return self.controller.step(Inputs(active, 32.6, 0., .0012, steering_pressed=self.steering_pressed, steering_angle=self.steering_angle))


def setup(canfd=True):
  cp = structs.CarParams(brand='ford', carFingerprint=CAR.FORD_MUSTANG_MACH_E_MK1 if canfd else CAR.FORD_FOCUS_MK4,
                        flags=3 if canfd else 2, pcmCruise=True, alternativeExperience=32,
                        transmissionType=structs.CarParams.TransmissionType.automatic,
                        steerControlType=structs.CarParams.SteerControlType.angle,
                        openpilotLongitudinalControl=True)
  cp.safetyConfigs = [structs.CarParams.SafetyConfig(safetyModel=structs.CarParams.SafetyModel.ford, safetyParam=147 if canfd else 161)]
  owner = CarController({Bus.pt:'ford_lincoln_base_pt'}, cp)
  owner.bp_lat = BluePilotLateral(cp, host=CoreHost())
  cc = structs.CarControl(latActive=True)
  state = structs.CarState(vEgo=32.6, vEgoRaw=32.6, canValid=True,
                           gearShifter=structs.CarState.GearShifter.drive)
  state.cruiseState.available = True
  cs = SimpleNamespace(out=state.as_reader(), buttons_stock_values=defaultdict(int),
                       acc_tja_status_stock_values=defaultdict(int), lkas_status_stock_values=defaultdict(int))
  return owner, cc.as_reader(), cs


def control_active(message):
  return ((message[1][0] >> 4) if message[0] == 0x3D6 else (message[1][4] >> 2)) & 7


def shadow_echo(owner, messages, now):
  returned = [(address, data, bus | 0x80) for address, data, bus in messages if address == 0x3CA]
  owner.bp_lat.observe_can([(now, returned)], 0)


def prime(owner, cc, cs):
  for now in range(1_000_000_000, 2_000_000_000, 10_000_000):
    _, messages = owner.update(cc, cs, now)
    shadow_echo(owner, messages, now + 1)
  assert not owner.bp_lat.step_lka(owner.packer, owner.CAN, now + 1)
  assert owner.bp_lat.pending.active
  assert abs(owner.bp_lat.host.controller.path_last) > .015


def test_due_shadow_precedes_control_after_recorded_72ms_gap():
  owner, cc, cs = setup()
  prime(owner, cc, cs)
  bp = owner.bp_lat
  now = max(bp.shadow_sent_ns, bp.control_sent_ns) + 72_000_000
  _, messages = owner.update(cc, cs, now)
  angle = [m for m in messages if m[0] in (0x3CA, 0x3D6)]
  assert [m[0] for m in angle] == [0x3CA, 0x3D6]
  assert control_active(angle[-1]) == 1
  assert bp.announced_ns == now


def test_unrefreshable_stale_lease_neutral_clears_pending_actuator_history():
  owner, cc, cs = setup()
  prime(owner, cc, cs)
  bp = owner.bp_lat
  now = max(bp.shadow_sent_ns, bp.control_sent_ns) + 72_000_000
  # A newly consumed late shadow echo still enforces its pacing delay.
  bp.shadow_echo_pending = True
  _, messages = owner.update(cc, cs, now)
  angle = [m for m in messages if m[0] in (0x3CA, 0x3D6)]
  assert [m[0] for m in angle] == [0x3D6]
  assert control_active(angle[0]) == 0
  assert bp.pending == Command()
  assert bp.host.controller.path_last == 0.
  # A subsequent announcement cannot revive the old nonzero actuator.
  seen = []
  for t in range(now + 10_000_000, now + 300_000_000, 10_000_000):
    _, messages = owner.update(cc, cs, t)
    shadow_echo(owner, messages, t + 1)
    seen.extend(m for m in messages if m[0] == 0x3D6 and control_active(m))
  assert seen
  sig = owner.packer.dbc.name_to_msg['LateralMotionControl2'].sigs['LatCtlPath_An_Actl']
  first_path = sig.get_raw_value(seen[0][1]) * sig.factor + sig.offset
  assert abs(first_path) <= .005


@pytest.mark.parametrize('canfd, word', [(True, 147), (False, 161)])
def test_aol_native_accepts_due_refresh_and_stale_restart_without_relaxation(canfd, word):
  from opendbc.safety.tests.test_ford_aol import TestFordAolDriverIntent
  from opendbc.safety.tests.libsafety import libsafety_py
  native = TestFordAolDriverIntent()
  native.setUp()
  native.reset(word)
  native.arm()
  native.pump(30, speed=32.6, mask=1)
  owner, cc, cs = setup(canfd)
  active = 0
  try:
    for tick in range(200):
      native.pump(1, speed=32.6, mask=1)
      now = (1_000_000 + native.tick * 10_000) * 1000
      if tick in (110, 150):
        # No host update for 70ms, but native receives fresh vehicle sources.
        native.pump(7, speed=32.6, mask=1)
        now = (1_000_000 + native.tick * 10_000) * 1000
      if tick == 150:
        owner.bp_lat.shadow_echo_pending = True
      _, messages = owner.update(cc, cs, now)
      for address, data, bus in messages:
        if address not in (0x3CA, 0x3D6, 0x3D3):
          continue
        assert native.safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data)), (tick, hex(address), data.hex())
        if address == 0x3CA:
          owner.bp_lat.observe_can([(now + 1, [(address, data, bus | 0x80)])], 0)
        active += address in (0x3D6, 0x3D3) and bool(control_active((address, data, bus)))
    assert active > 20
  finally:
    native.tearDown()


def test_rejected_shadow_is_not_an_ack_and_withdraws_next_control():
  owner, cc, cs = setup()
  prime(owner, cc, cs)
  bp = owner.bp_lat
  now = max(bp.shadow_sent_ns, bp.control_sent_ns) + 72_000_000
  payload = bp.step_lka(owner.packer, owner.CAN, now)[0][1]
  bp.observe_can([(now, [(0x3CA, payload, 0xC0)])], 0)
  assert bp.host.steering_rejected
  assert not bp.shadow_echo_pending
  assert bp.shadow_return_payload is None
  _, messages = owner.update(cc, cs, now)
  controls = [m for m in messages if m[0] == 0x3D6]
  assert controls and control_active(controls[0]) == 0
  assert bp.host.controller.path_last == 0.


def test_unrelated_or_out_of_order_returns_do_not_refresh_shadow_time():
  owner, cc, cs = setup()
  prime(owner, cc, cs)
  bp = owner.bp_lat
  sent = max(bp.shadow_sent_ns, bp.control_sent_ns) + 72_000_000
  payload = bp.step_lka(owner.packer, owner.CAN, sent)[0][1]
  bp.shadow_returned_ns = sent + 10_000_000
  bp.observe_can([(sent, [(0x3CA, payload, 0x80)])], 0)
  bp.observe_can([(sent + 20_000_000, [(0x3CA, bytes(8), 0x80)])], 0)
  assert not bp.shadow_echo_pending
  assert bp.announced_ns == sent


def test_permission_withdrawal_does_not_publish_active_even_with_due_shadow():
  owner, cc, cs = setup()
  prime(owner, cc, cs)
  now = max(owner.bp_lat.shadow_sent_ns, owner.bp_lat.control_sent_ns) + 72_000_000
  _, messages = owner.update(structs.CarControl().as_reader(), cs, now)
  controls = [m for m in messages if m[0] == 0x3D6]
  assert controls and control_active(controls[0]) == 0
  assert owner.bp_lat.pending == Command()


def test_stale_transport_reset_preserves_continuous_manual_turn_pause():
  owner, cc, cs = setup()
  prime(owner, cc, cs)
  host = owner.bp_lat.host
  host.steering_pressed = True
  host.steering_angle = 60.
  for _ in range(70):
    command = host.update(cc, cs)
  assert not command.active
  assert host.controller.human_timer >= 3.
  now = max(owner.bp_lat.shadow_sent_ns, owner.bp_lat.control_sent_ns) + 72_000_000
  owner.bp_lat.shadow_echo_pending = True
  _, messages = owner.update(cc, cs, now)
  assert not any(control_active(m) for m in messages if m[0] == 0x3D6)
  assert host.controller.human_timer >= 3.
  assert host.controller.press_last and host.controller.preturned
  for t in range(now + 10_000_000, now + 500_000_000, 10_000_000):
    _, messages = owner.update(cc, cs, t)
    assert not any(control_active(m) for m in messages if m[0] == 0x3D6)


def test_shadow_waits_for_return_before_another_request():
  owner, _, _ = setup()
  bp = owner.bp_lat
  bp.pending = Command(True, .02, .001)
  sent = 1_000_000_000
  first = bp.step_lka(owner.packer, owner.CAN, sent)[0]
  assert not bp.step_lka(owner.packer, owner.CAN, sent + 30_000_000)
  assert not bp.step_lka(owner.packer, owner.CAN, sent + 60_000_000)
  bp.observe_can([(sent + 60_000_001, [(first[0], first[1], 0x80)])], 0)
  assert not bp.step_lka(owner.packer, owner.CAN, sent + 70_000_000)
  assert not bp.step_lka(owner.packer, owner.CAN, sent + 90_000_000)
  second = bp.step_lka(owner.packer, owner.CAN, sent + 100_000_000)[0]
  assert ((second[1][4] >> 2) & 7) == 1


def test_native_rejected_shadow_retries_the_unaccepted_counter():
  from opendbc.safety.tests.test_ford_aol import TestFordAolDriverIntent
  from opendbc.safety.tests.libsafety import libsafety_py
  native = TestFordAolDriverIntent()
  native.setUp()
  try:
    native.reset(147)
    owner, _, _ = setup()
    bp = owner.bp_lat
    bp.pending = Command(True, .02, .001)
    sent = 1_000_000_000
    first = bp.step_lka(owner.packer, owner.CAN, sent)[0]
    native.safety.set_timer(1_000_000)
    assert native.safety.safety_tx_hook(libsafety_py.make_CANPacket(first[0], first[2], first[1]))
    bp.observe_can([(sent + 1, [(first[0], first[1], 0x80)])], 0)
    bp.step_lka(owner.packer, owner.CAN, sent + 10_000_000)
    second = bp.step_lka(owner.packer, owner.CAN, sent + 40_000_000)[0]
    # Independent MCU time reproduces two queued packets arriving only 12 ms apart.
    native.safety.set_timer(1_012_000)
    assert not native.safety.safety_tx_hook(libsafety_py.make_CANPacket(second[0], second[2], second[1]))
    bp.observe_can([(sent + 40_000_001, [(second[0], second[1], 0xC0)])], 0)
    assert bp.host.steering_rejected
    assert not bp.step_lka(owner.packer, owner.CAN, sent + 50_000_000)
    retry = bp.step_lka(owner.packer, owner.CAN, sent + 80_000_000)[0]
    assert ((retry[1][4] >> 2) & 7) == ((second[1][4] >> 2) & 7)
    native.safety.set_timer(1_080_000)
    assert native.safety.safety_tx_hook(libsafety_py.make_CANPacket(retry[0], retry[2], retry[1]))
  finally:
    native.tearDown()
