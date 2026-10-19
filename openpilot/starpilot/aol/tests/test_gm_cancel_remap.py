"""Actual parser/native/ordinary event boundaries for optional GM Cancel mapping."""
from contextlib import ExitStack
import pytest
from opendbc.car.gm.tests.test_bolt_cc import native
from opendbc.car.gm.tests.test_bolt_pedal import params
from opendbc.car.gm.values import CAR
from opendbc.safety.tests.libsafety import libsafety_py
from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car.car_events import CarEvents
from openpilot.starpilot.aol.tests.test_gm import TestGmAol as GmCardFixture
from openpilot.starpilot.aol.tests.test_gm_held_native import NOW, parse as source_fixture
from openpilot.starpilot.nostalgia import physical_cancel

IDS = (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021,
       CAR.CHEVROLET_BOLT_CC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)


@pytest.fixture(autouse=True)
def restore_native_configuration():
  safety = libsafety_py.libsafety
  safety.set_alternative_experience(0)
  try:
    yield
  finally:
    safety.set_alternative_experience(0)
    assert safety.set_safety_hooks(19, 0) == 0


def parse(card, now, gesture=None, counter=0, *, belt_unlatched=False, packets_only=False):
  from opendbc.can import CANPacker
  from opendbc.car import Bus
  from opendbc.car.gm.values import DBC
  packets = source_fixture(card, now, gesture, counter, belt_unlatched=belt_unlatched, packets_only=True)
  if card.CP.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
    packer = CANPacker(DBC[card.CP.carFingerprint][Bus.pt])
    packets.append(packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCmdActive': 0}))
  if packets_only:
    return packets
  if now == NOW:
    card.CI.update([(now - 1_000_000, packets)])
  observed = card.CI.update([(now, packets)])
  assert observed.canValid and not observed.canTimeout
  assert observed.brakePressed == (gesture == 'brake')
  assert observed.regenBraking == (gesture == 'paddle')
  assert observed.seatbeltUnlatched == belt_unlatched
  card._aol_can_observation = (observed, now, now, now)
  return observed


@pytest.mark.parametrize('candidate', IDS)
@pytest.mark.parametrize('remap', [False, True])
def test_actual_card_parser_native_and_event_cancel_contract(candidate, remap):
  with ExitStack() as cleanup:
    cleanup.enter_context(OpenpilotPrefix())
    saved = Params()
    saved.put_bool('AlwaysOnLateral', True, block=True)
    saved.put_bool('RemapCancelToDistance', remap, block=True)
    cp = params(candidate, pedal=True, camera=True)
    card = GmCardFixture.card(cp, saved)
    cleanup.callback(card.vehicle_startup.close)
    assert card.CP.alternativeExperience == (96 if remap else 32)
    safety = libsafety_py.libsafety
    safety.init_tests()
    safety.set_alternative_experience(card.CP.alternativeExperience)
    assert safety.set_safety_hooks(4, card.CP.safetyConfigs[0].safetyParam) == 0
    for tick in range(10):
      now = NOW + tick * 10_000_000
      for packet in parse(card, now, counter=tick % 4, packets_only=True):
        assert native('rx', packet, now // 1000)
      parse(card, now, counter=tick % 4)
      safety.set_aol_test_heartbeat(True)
      safety.aol_set_host_request(3)
    safety.set_controls_allowed(True)
    assert safety.aol_get_permission_mask() == 3
    cancel_packet = (0x1E1, bytes.fromhex('00000000016490'), 0)
    assert native('rx', cancel_packet, (NOW + 95_000_000) // 1000)
    assert bool(safety.get_controls_allowed()) is remap
    assert safety.aol_get_permission_mask() == (3 if remap else 1)
    previous = parse(card, NOW + 100_000_000, counter=2)
    observed = parse(card, NOW + 110_000_000, gesture='cancel', counter=3)
    # Raw parser input stays visible for the existing secondary-action tracker.
    assert any(str(event.type) == 'cancel' for event in observed.buttonEvents)
    assert physical_cancel(observed, card.CP) is (not remap)
    events = CarEvents(card.CP).update(observed, previous, card.CC_prev)
    assert (log.OnroadEvent.EventName.buttonCancel in events.names) is (not remap)
    card.aol_card_intent.update(previous, fault_active=False, now_ns=NOW + 100_000_000)
    assert card.aol_card_intent.allowed_latch
    card.aol_card_intent.update(observed, fault_active=False, now_ns=NOW + 110_000_000)
    assert card.aol_card_intent.allowed_latch
    # The remap never exempts a real regen withdrawal.
    assert native('rx', (0xBD, bytes.fromhex('20000000000000'), 0), (NOW + 115_000_000) // 1000)
    assert not safety.get_controls_allowed() and safety.aol_get_permission_mask() == 1


@pytest.mark.parametrize('candidate', IDS)
@pytest.mark.parametrize('remap', [False, True])
def test_actual_selfdrived_controls_preserve_full_op_only_for_configured_remap(candidate, remap):
  from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
  from opendbc.car.gm.cancel_remap import prepare
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    saved = Params()
    saved.put_bool('RemapCancelToDistance', remap, block=True)
    cp = params(candidate, pedal=True, camera=True)
    prepare(cp, remap)
    sd, _, step = case._authority_callers(True, cp=cp, genuine_events=True)
    card = GmCardFixture.card(cp, saved)
    cleanup.callback(card.vehicle_startup.close)
    for tick in range(10):
      parse(card, NOW + tick * 10_000_000, counter=tick % 4)
      axis, state, command = step(tick)
      assert state.enabled and axis.lateralActive and axis.longitudinalActive
      assert command.latActive and command.longActive
    observed = parse(card, NOW + 100_000_000, gesture='cancel', counter=2)
    axis, state, command = step(10, observed_state=observed, allowed=True,
      native_request_lat=True, native_request_long=True, long_allowed=remap,
      panda_controls_allowed=remap)
    assert bool(state.enabled) is remap
    assert bool(axis.longitudinalActive) is remap and bool(command.longActive) is remap
    assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
    if remap:
      assert axis.lateralActive and command.latActive


@pytest.mark.parametrize('candidate', [IDS[1], IDS[3]])
@pytest.mark.parametrize('remap', [False, True])
@pytest.mark.parametrize('slot,frames', [(0, 1), (1, 50), (2, 250)])
def test_actual_card_parser_dispatches_auxiliary_action_only_when_remapped(candidate, remap, slot, frames):
  from openpilot.starpilot.aol.intent import read_settings
  with ExitStack() as cleanup:
    cleanup.enter_context(OpenpilotPrefix())
    saved = Params()
    saved.put_bool('AlwaysOnLateral', True, block=True)
    saved.put_bool('RemapCancelToDistance', remap, block=True)
    keys = ('CancelButtonControl', 'LongCancelButtonControl', 'VeryLongCancelButtonControl')
    for index, key in enumerate(keys):
      saved.put(key, 3 if index == slot else 0, block=True)
    card = GmCardFixture.card(params(candidate, pedal=True, camera=True), saved)
    cleanup.callback(card.vehicle_startup.close)
    owner = card.aol_card_intent
    assert owner.settings == read_settings(saved)
    neutral = parse(card, NOW, counter=0)
    owner.update_auxiliary(neutral)
    for tick in range(frames):
      observed = parse(card, NOW + (tick + 1) * 10_000_000, gesture='cancel', counter=(tick + 1) % 4)
      before = observed.to_dict()
      owner.update_auxiliary(observed)
      assert observed.to_dict() == before
    release = parse(card, NOW + (frames + 1) * 10_000_000, counter=(frames + 1) % 4)
    owner.update_auxiliary(release)
    assert owner.pause_lateral is remap


@pytest.mark.parametrize('candidate', [IDS[1], IDS[3]])
@pytest.mark.parametrize('remap', [False, True])
@pytest.mark.parametrize('slot,frames', [(0, 1), (1, 50), (2, 250)])
def test_actual_card_parser_and_wheel_publisher_dispatch_once(candidate, remap, slot, frames):
  from openpilot.starpilot.controllers.wheel_actions import WheelPublisher
  with ExitStack() as cleanup:
    cleanup.enter_context(OpenpilotPrefix())
    saved = Params()
    saved.put_bool('RemapCancelToDistance', remap, block=True)
    keys = ('CancelButtonControl', 'LongCancelButtonControl', 'VeryLongCancelButtonControl')
    for index, key in enumerate(keys):
      saved.put(key, 8 if index == slot else 0, block=True)
    card = GmCardFixture.card(params(candidate, pedal=True, camera=True), saved)
    cleanup.callback(card.vehicle_startup.close)
    publisher = WheelPublisher(saved)
    commands = []
    drive_id = NOW - 1_000_000
    neutral = parse(card, NOW, counter=0)
    publisher.observe(saved, card.CP, neutral, now_ns=NOW, drive_id=drive_id)
    for tick in range(frames):
      now = NOW + (tick + 1) * 10_000_000
      observed = parse(card, now, gesture='cancel', counter=(tick + 1) % 4)
      commands.extend(publisher.observe(saved, card.CP, observed, now_ns=now, drive_id=drive_id))
    now = NOW + (frames + 1) * 10_000_000
    released = parse(card, now, counter=(frames + 1) % 4)
    commands.extend(publisher.observe(saved, card.CP, released, now_ns=now, drive_id=drive_id))
    actions = [(key, action) for key, action in commands if key]
    assert actions == ([(keys[slot], 8)] if remap else [])
    assert all((key, action) == ('', 0) for key, action in commands if not key)


@pytest.mark.parametrize('candidate', IDS)
@pytest.mark.parametrize('remap', [False, True])
def test_actual_card_parser_native_and_event_cancel_contract_aol_off(candidate, remap):
  """Ordinary Card/native operation has no AOL owner or request at experience0/64."""
  with ExitStack() as cleanup:
    cleanup.enter_context(OpenpilotPrefix())
    saved = Params()
    saved.put_bool('AlwaysOnLateral', False, block=True)
    saved.put_bool('RemapCancelToDistance', remap, block=True)
    cp = params(candidate, pedal=True, camera=True)
    card = GmCardFixture.card(cp, saved)
    cleanup.callback(card.vehicle_startup.close)
    assert not saved.get_bool('AlwaysOnLateral')
    assert card.CP.alternativeExperience == (64 if remap else 0)
    assert not card.aol_qualified and card.aol_card_intent is None
    safety = libsafety_py.libsafety
    safety.init_tests()
    safety.set_alternative_experience(card.CP.alternativeExperience)
    assert safety.set_safety_hooks(4, card.CP.safetyConfigs[0].safetyParam) == 0
    for tick in range(10):
      now = NOW + tick * 10_000_000
      for packet in parse(card, now, counter=tick % 4, packets_only=True):
        assert native('rx', packet, now // 1000)
      parse(card, now, counter=tick % 4)
    # The established ordinary full-engagement starting condition is explicit;
    # unlike the AOL cases, this path never issues an AOL host request.
    safety.set_controls_allowed(True)
    assert safety.aol_get_request_mask() == 0
    assert safety.aol_get_permission_mask() == 0
    cancel_packet = (0x1E1, bytes.fromhex('00000000016490'), 0)
    assert native('rx', cancel_packet, (NOW + 95_000_000) // 1000)
    assert bool(safety.get_controls_allowed()) is remap
    assert safety.aol_get_request_mask() == 0
    assert safety.aol_get_permission_mask() == 0
    previous = parse(card, NOW + 100_000_000, counter=2)
    observed = parse(card, NOW + 110_000_000, gesture='cancel', counter=3)
    assert any(str(event.type) == 'cancel' for event in observed.buttonEvents)
    assert physical_cancel(observed, card.CP) is (not remap)
    events = CarEvents(card.CP).update(observed, previous, card.CC_prev)
    assert (log.OnroadEvent.EventName.buttonCancel in events.names) is (not remap)
    assert card.aol_card_intent is None
    assert native('rx', (0xBD, bytes.fromhex('20000000000000'), 0), (NOW + 115_000_000) // 1000)
    assert not safety.get_controls_allowed()
    assert safety.aol_get_request_mask() == 0
    assert safety.aol_get_permission_mask() == 0
