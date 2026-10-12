"""Real GM parser/Card sources with controlled native peers; no transport claim."""
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm.bolt_cc import button_bytes
from opendbc.car.gm.gmcan import pedal_crc
from opendbc.car.gm.tests.test_bolt_cc import feed
from opendbc.car.gm.tests.test_bolt_pedal import params
from opendbc.car.gm.values import CAR, DBC, CruiseButtons
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.runtime import decide_axes
from openpilot.starpilot.aol.transport_pause import TransportPauseFeedback
from openpilot.starpilot.aol.wire import PandaSlot, SafetyState, encode_safety

NOW = 10_000_000_000


class Peers:
  def __init__(self, messages):
    self.messages = {m.which(): m for m in messages}
    self.logMonoTime = {n: int(m.logMonoTime) for n, m in self.messages.items()}
    self.seen = dict.fromkeys(self.messages, True)
    self.valid = dict(self.seen)
    self.alive = dict(self.seen)

  def __getitem__(self, name):
    return getattr(self.messages[name], name)


def parse(card, now, gesture=None, counter=0):
  packer = CANPacker(DBC[card.CP.carFingerprint][Bus.pt])
  _, packets = feed(SimpleNamespace(update=lambda _: None), packer, now, counter=counter,
                    active=False, speed=20., brake=gesture == 'brake', regen=gesture == 'paddle')
  packets = [p for p in packets if p[0] not in (0x1E1, 0x1F5)]
  packets += [packer.make_can_msg('BCMBlindSpotMonitor', 0, {}),
              packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 6}),
              (0x1E1, button_bytes(CruiseButtons.CANCEL if gesture == 'cancel' else CruiseButtons.UNPRESS, counter), 0)]
  sensor = bytearray(packer.make_can_msg('GAS_SENSOR', 0,
                     {'INTERCEPTOR_GAS': 0., 'INTERCEPTOR_GAS2': 0., 'STATE': 0, 'COUNTER_PEDAL': counter})[1])
  sensor[5] = pedal_crc(sensor)
  packets.append((0x201, bytes(sensor), 0))
  if now == NOW:
    card.CI.update([(now - 1_000_000, packets)])
  cs = card.CI.update([(now, packets)])
  assert cs.canValid and not cs.canTimeout
  assert cs.brakePressed == (gesture == 'brake')
  assert cs.regenBraking == (gesture == 'paddle')
  card._aol_can_observation = (cs, now, now, now)
  return cs


def peers(cp, producer, now, *, controls=True, native=None, sequence=1, long_active=True):
  config = cp.safetyConfigs[0]
  if native is None:
    slot = PandaSlot(0, 'gm-unit', config.safetyModel.raw, config.safetyParam, 32, True)
    native = SafetyState(1, True, now, now + 200_000_000, config.safetyModel.raw, config.safetyParam,
                         True, True, True, True, 'gm-unit', 'gm-session',
                         sourcePandaStatesMonoTime=now, pandaInventory=(slot,))
  wire = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=native.observedMonoTime)
  wire.aolSafetyWire = encode_safety(native)
  pandas = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=now)
  p = pandas.pandaStates[0]
  p.safetyModel, p.safetyParam, p.alternativeExperience = config.safetyModel, config.safetyParam, 32
  p.controlsAllowed = controls
  axis = messaging.new_message('aolAxisState', valid=True, logMonoTime=now)
  a = axis.aolAxisState
  a.sessionId = a.faultSessionId = 'gm-session'
  a.sequence, a.qualified, a.faultReason = sequence, True, 'none'
  a.observedMonoTime, a.validUntilMonoTime, a.sourceCarStateMonoTime = now, now + 30_000_000, now
  a.desiredLateral = a.lateralActive = a.nativeAcknowledged = True
  a.desiredLongitudinal = a.longitudinalActive = long_active
  a.intentProducerSessionId, a.intentIntegrityEpoch = producer, 1
  events = messaging.new_message('onroadEvents', 0, valid=True, logMonoTime=now)
  return Peers([wire.as_reader(), pandas.as_reader(), axis.as_reader(), events.as_reader()]), native


def baseline():
  from openpilot.starpilot.aol.tests.test_gm import TestGmAol
  settings = Params()
  settings.put_bool('AlwaysOnLateral', True, block=True)
  settings.put_bool('AlphaLongitudinalEnabled', True, block=True)
  cp = params(CAR.CHEVROLET_BOLT_CC_2018_2021, pedal=True, camera=True)
  card = TestGmAol.card(cp, settings)
  cs = parse(card, NOW)
  card.aol_card_intent.update(cs, fault_active=False, now_ns=NOW)
  assert card.aol_card_intent.allowed_latch
  sm, native = peers(card.CP, card.slc_producer_session, NOW)
  feedback = TransportPauseFeedback(card.CP)
  assert not feedback.observe(sm, card.CP, cs, NOW, latched=True,
                              intent_producer_session=card.slc_producer_session)
  assert feedback.session == 'gm-session' and feedback.healthy_inventory
  return card, feedback, native


@pytest.mark.parametrize('gesture', ['brake', 'paddle', 'cancel'])
def test_real_physical_withdrawal_retains_latch_with_held_long_wire(gesture):
  with OpenpilotPrefix():
    card, feedback, native = baseline()
    now = NOW + 10_000_000
    cs = parse(card, now, gesture, counter=1)
    source = card.aol_gm_withdrawal_source(cs, now)
    assert source == now
    sm, _ = peers(card.CP, card.slc_producer_session, now, controls=False, native=native, sequence=2)
    reset = feedback.observe(sm, card.CP, cs, now, latched=True, gm_withdrawal_source_ns=source,
                             intent_producer_session=card.slc_producer_session)
    card.aol_card_intent.update(cs, fault_active=reset, now_ns=now)
    assert not reset and not feedback.failed and card.aol_card_intent.allowed_latch
    assert feedback.gm_withdrawal_ns == source
    # The prior LONG wire and latest raw withdrawal are untouched. Ordinary
    # runtime keeps LONG off even though accepted driver LAT intent survives.
    intent = SimpleNamespace(allowedLatch=True, pauseLateral=False, pauseLongitudinal=False)
    decision = decide_axes(standard_lateral=False, standard_longitudinal=False, intent=intent,
      native=native, car_state=cs, initialized=True, model_ready=True, no_entry=False,
      immediate_disable=False, dm_lockout=False, pause_brake_mps=5.)
    assert decision.lateral_active and not decision.longitudinal_active
    assert native.requestedLongitudinal and native.longitudinalAllowed
    assert native.validUntilMonoTime == NOW + 200_000_000
    # Held and release samples retain one original occurrence; the actual
    # native LAT-only acknowledgement ends the exception on the normal path.
    for offset, physical in ((20_000_000, gesture), (30_000_000, None)):
      later = NOW + offset
      cs = parse(card, later, physical, counter=2)
      sm, _ = peers(card.CP, card.slc_producer_session, later, controls=False, native=native,
                    sequence=offset // 10_000_000 + 1, long_active=False)
      assert not feedback.observe(sm, card.CP, cs, later, latched=True,
        gm_withdrawal_source_ns=card.aol_gm_withdrawal_source(cs, later), intent_producer_session=card.slc_producer_session)
      assert feedback.gm_withdrawal_ns == source
    lat_only = replace(native, observedMonoTime=NOW + 40_000_000, validUntilMonoTime=NOW + 240_000_000,
                       requestedLongitudinal=False, longitudinalAllowed=False,
                       pandaInventory=(replace(native.pandaInventory[0], controlsAllowed=False),))
    sm, _ = peers(card.CP, card.slc_producer_session, NOW + 40_000_000, controls=False,
                  native=lat_only, sequence=5, long_active=False)
    assert not feedback.observe(sm, card.CP, cs, NOW + 40_000_000, latched=True,
                                intent_producer_session=card.slc_producer_session)
    assert feedback.gm_withdrawal_ns == 0


@pytest.mark.parametrize('fault', ['no_source', 'stale_source', 'future_source', 'producer', 'epoch',
  'session', 'serial', 'inventory', 'owner', 'config', 'rx_fault', 'heartbeat', 'lat_denied', 'no_lat',
  'native_expired', 'can_invalid', 'eps', 'event', 'axis_expired', 'sequence', 'main',
  'seatbelt', 'seatbelt_event', 'door', 'gear'])
def test_physical_withdrawal_keeps_identity_freshness_and_health_vetoes(fault):
  with OpenpilotPrefix():
    card, feedback, native = baseline()
    now = NOW + 10_000_000
    cs = parse(card, now, 'brake', counter=1)
    source = card.aol_gm_withdrawal_source(cs, now)
    if fault == 'no_source':
      source = 0
    elif fault == 'stale_source':
      source = now - 30_000_001
    elif fault == 'future_source':
      source = now + 1
    elif fault == 'session':
      native = replace(native, axisSessionId='other')
    elif fault == 'serial':
      native = replace(native, pandaSerial='other')
    elif fault == 'inventory':
      native = replace(native, pandaInventory=(replace(native.pandaInventory[0], hardwareSerial='other'),))
    elif fault == 'owner':
      card.CP.alternativeExperience = 0
    elif fault == 'no_lat':
      native = replace(native, requestedLateral=False)
    elif fault == 'native_expired':
      native = replace(native, validUntilMonoTime=now - 1)
    elif fault == 'main':
      cs.cruiseState.available = False
    elif fault == 'lat_denied':
      native = replace(native, lateralAllowed=False)
    elif fault == 'can_invalid':
      cs.canValid = False
    elif fault == 'eps':
      cs.steerFaultPermanent = True
    elif fault == 'seatbelt':
      cs.seatbeltUnlatched = True
    elif fault == 'door':
      cs.doorOpen = True
    elif fault == 'gear':
      from opendbc.car.structs import car
      cs.gearShifter = car.CarState.GearShifter.park
    sm, _ = peers(card.CP, card.slc_producer_session, now, controls=False, native=native, sequence=2)
    axis = sm.messages['aolAxisState'].as_builder()
    pandas = sm.messages['pandaStates'].as_builder()
    events = sm.messages['onroadEvents'].as_builder()
    if fault == 'producer':
      axis.aolAxisState.intentProducerSessionId = 'other'
    elif fault == 'epoch':
      axis.aolAxisState.intentIntegrityEpoch = 2
    elif fault == 'sequence':
      axis.aolAxisState.sequence = 1
    elif fault == 'axis_expired':
      axis.aolAxisState.validUntilMonoTime = now - 1
    elif fault == 'config':
      pandas.pandaStates[0].safetyParam ^= 1
    elif fault == 'rx_fault':
      pandas.pandaStates[0].safetyRxChecksInvalid = True
    elif fault == 'heartbeat':
      pandas.pandaStates[0].heartbeatLost = True
    elif fault == 'seatbelt_event':
      events.init('onroadEvents', 1)
      events.onroadEvents[0].name, events.onroadEvents[0].softDisable = 'seatbeltNotLatched', True
    elif fault == 'event':
      events.init('onroadEvents', 1)
      events.onroadEvents[0].name, events.onroadEvents[0].immediateDisable = 'controlsMismatch', True
    sm = Peers([sm.messages['aolSafetyWire'], pandas.as_reader(), axis.as_reader(), events.as_reader()])
    assert feedback.observe(sm, card.CP, cs, now, latched=True, gm_withdrawal_source_ns=source,
                            intent_producer_session=card.slc_producer_session)
    assert feedback.failed


def test_held_and_duplicate_samples_cannot_extend_withdrawal_deadline():
  with OpenpilotPrefix():
    card, feedback, native = baseline()
    occurrence = NOW + 10_000_000
    for tick in range(1, 23):
      now = NOW + tick * 10_000_000
      cs = parse(card, now, 'brake', counter=tick % 4)
      if tick > 1:
        native = replace(native, observedMonoTime=now, validUntilMonoTime=now + 200_000_000)
      sm, _ = peers(card.CP, card.slc_producer_session, now, controls=False, native=native,
                    sequence=tick + 1, long_active=tick == 1)
      source = card.aol_gm_withdrawal_source(cs, now)
      for _ in range(2):
        failed = feedback.observe(sm, card.CP, cs, now, latched=True, gm_withdrawal_source_ns=source,
                                  intent_producer_session=card.slc_producer_session)
        assert failed == (tick == 22)
        assert feedback.gm_withdrawal_ns == occurrence
    assert feedback.failed


@pytest.mark.parametrize('fault', ['different_cs', 'old_receipt', 'future_receipt', 'stale_parser', 'future_parser'])
def test_physical_receipt_requires_same_parsed_batch_and_separate_clock_freshness(fault):
  with OpenpilotPrefix():
    card, _, _ = baseline()
    now = NOW + 10_000_000
    cs = parse(card, now, 'brake', counter=1)
    assert card.aol_gm_withdrawal_source(cs, now) == now
    if fault == 'different_cs':
      card._aol_can_observation = (cs.as_reader().as_builder(), now, now, now)
    elif fault == 'old_receipt':
      card._aol_can_observation = (cs, now - 30_000_001, now, now)
    elif fault == 'future_receipt':
      card._aol_can_observation = (cs, now + 1, now, now)
    elif fault == 'stale_parser':
      card._aol_can_observation = (cs, now, now + 30_000_001, now + 30_000_001)
    elif fault == 'future_parser':
      card._aol_can_observation = (cs, now, now - 1, now)
    assert card.aol_gm_withdrawal_source(cs, now) == 0


@pytest.mark.parametrize('owner', ['qualified', 'unmarked', 'wrong_profile'])
def test_actual_card_state_update_captures_boot_clock_only_for_physical_gm_owner(owner):
  # Stop immediately after the production clock gate. The real joined Card.step
  # transport cases separately exercise installation/consumption of the receipt.
  class ClockBoundaryReached(Exception):
    pass

  def stop_after_clock(*_):
    raise ClockBoundaryReached

  with OpenpilotPrefix():
    card, _, _ = baseline()
    cs = parse(card, NOW + 10_000_000, 'brake', counter=1)
    if owner == 'unmarked':
      card.CP.alternativeExperience = 0
    elif owner == 'wrong_profile':
      card.CP.flags = 0
    with patch('openpilot.selfdrive.car.card.messaging.drain_sock_raw', return_value=[]), \
         patch('openpilot.selfdrive.car.card.can_capnp_to_list', return_value=[(NOW + 10_000_000, [])]), \
         patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=NOW + 10_000_000), \
         patch('openpilot.selfdrive.car.card.time.clock_gettime_ns', return_value=NOW + 10_000_000) as clock, \
         patch.object(card.CI, 'update', return_value=cs), \
         patch.object(card, 'observe_ioniq6_long_authority', side_effect=stop_after_clock):
      with pytest.raises(ClockBoundaryReached):
        card.state_update()
      if owner == 'qualified':
        from openpilot.selfdrive.car.card import time
        clock.assert_called_once_with(time.CLOCK_BOOTTIME)
      else:
        clock.assert_not_called()


@pytest.mark.parametrize('fault', [None, 'unmarked', 'wrong_owner', 'unlatched', 'unarmed', 'source_mismatch',
  'source_expired', 'future_source', 'no_cancel', 'can_invalid', 'eps', 'no_native', 'lat_denied', 'native_inventory'])
def test_gm_cancel_exempts_only_current_armed_lateral_no_entry(fault):
  from openpilot.starpilot.aol.wire import IntentState
  from openpilot.starpilot.car.gm.aol import physical_cancel_lateral_allowed
  from openpilot.selfdrive.selfdrived.events import ET, EVENTS, EventName
  from openpilot.starpilot.nostalgia import aol_no_entry
  with OpenpilotPrefix():
    card, _, native = baseline()
    now = NOW + 10_000_000
    cs = parse(card, now, 'cancel', counter=1)
    intent = IntentState(card.slc_producer_session, 2, now, now, now + 30_000_000, True, False, False, True, True)
    source = now
    if fault == 'unmarked':
      card.CP.alternativeExperience = 0
    elif fault == 'wrong_owner':
      card.CP.flags = 0
    elif fault == 'unlatched':
      intent = replace(intent, allowedLatch=False)
    elif fault == 'unarmed':
      intent = replace(intent, lateralArmed=False)
    elif fault == 'source_mismatch':
      source -= 1
    elif fault == 'source_expired':
      now += 30_000_001
    elif fault == 'future_source':
      source += 1
    elif fault == 'no_cancel':
      cs.buttonEvents = []
    elif fault == 'can_invalid':
      cs.canValid = False
    elif fault == 'eps':
      cs.steerFaultPermanent = True
    elif fault == 'no_native':
      native = None
    elif fault == 'lat_denied':
      native = replace(native, lateralAllowed=False)
    elif fault == 'native_inventory':
      native = replace(native, pandaInventory=(replace(native.pandaInventory[0], hardwareSerial='other'),))
    allowed = physical_cancel_lateral_allowed(card.CP, cs, intent, native, source_ns=source, now_ns=now)
    assert allowed == (fault is None)
    assert aol_no_entry([EventName.buttonCancel], cs, paddle_only_cancel=False)
    assert aol_no_entry([EventName.buttonCancel], cs, paddle_only_cancel=False, allow_lateral_cancel=allowed) == (fault is not None)
    assert ET.USER_DISABLE in EVENTS[EventName.buttonCancel]
    assert aol_no_entry([EventName.buttonCancel, EventName.doorOpen], cs,
                        paddle_only_cancel=False, allow_lateral_cancel=allowed)


def test_native_lat_only_after_long_belt_loss_keeps_saved_lateral_intent():
  from openpilot.starpilot.aol.intent import disarming_fault
  from openpilot.starpilot.nostalgia import aol_no_entry
  from openpilot.selfdrive.selfdrived.events import Events, EventName
  with OpenpilotPrefix():
    card, feedback, native = baseline()
    for tick, unlatched in ((1, True), (2, True), (3, False)):
      now = NOW + tick * 10_000_000
      cs = parse(card, now, counter=tick)
      cs.seatbeltUnlatched = unlatched
      native = replace(native, observedMonoTime=now, validUntilMonoTime=now + 200_000_000,
        requestedLongitudinal=False, longitudinalAllowed=False,
        pandaInventory=(replace(native.pandaInventory[0], controlsAllowed=False),))
      sm, _ = peers(card.CP, card.slc_producer_session, now, controls=False, native=native,
                    sequence=tick + 1, long_active=False)
      events = Events()
      if unlatched:
        events.add(EventName.seatbeltNotLatched)
        wire_events = sm.messages['onroadEvents'].as_builder()
        wire_events.onroadEvents = events.to_msg()
        sm = Peers([sm.messages['aolSafetyWire'], sm.messages['pandaStates'],
                    sm.messages['aolAxisState'], wire_events.as_reader()])
      reset = feedback.observe(sm, card.CP, cs, now, latched=True,
                               intent_producer_session=card.slc_producer_session)
      card.aol_card_intent.update(cs, fault_active=reset or disarming_fault(events.to_msg(), cs), now_ns=now)
      assert not reset and not feedback.failed and card.aol_card_intent.allowed_latch
      allowed, pause_lat, pause_long = card.aol_card_intent.output(cs)
      decision = decide_axes(standard_lateral=True, standard_longitudinal=unlatched,
        intent=SimpleNamespace(allowedLatch=allowed, pauseLateral=pause_lat, pauseLongitudinal=pause_long),
        native=native, car_state=cs, initialized=True, model_ready=True,
        no_entry=aol_no_entry(events.names, cs, paddle_only_cancel=False),
        immediate_disable=False, dm_lockout=False, pause_brake_mps=0.)
      assert decision.lateral_active
      assert not decision.desired_longitudinal and not decision.longitudinal_active
      assert feedback.gm_withdrawal_ns == 0


@pytest.mark.parametrize('fault', [None, 'stale_source', 'future_source', 'future_observation',
  'excessive_lease', 'expired', 'no_expiry'])
def test_real_card_published_cancel_intent_preserves_producer_lease_and_freshness(fault):
  from openpilot.starpilot.aol.runtime import current_intent
  from openpilot.starpilot.aol.wire import decode_intent
  from openpilot.starpilot.car.gm.aol import physical_cancel_lateral_allowed

  class PublishedCarState(Exception):
    pass

  with OpenpilotPrefix():
    card, _, native = baseline()
    now = NOW + 10_000_000
    cs = parse(card, now, 'cancel', counter=1)
    published = {}
    real_new_message = messaging.new_message

    def stamped_message(service=None, size=None, **kwargs):
      return real_new_message(service, size, **({'logMonoTime': now} | kwargs))

    def capture(service, message):
      wire = message if isinstance(message, bytes) else message.to_bytes()
      published[service] = messaging.log_from_bytes(wire)
      if service == 'carState':
        raise PublishedCarState

    with patch('openpilot.selfdrive.car.card.messaging.new_message', side_effect=stamped_message), \
         patch.object(card.pm, 'send', side_effect=capture):
      with pytest.raises(PublishedCarState):
        card.state_publish(cs, None)
    source = int(published['carState'].logMonoTime)
    cs = published['carState'].carState
    intent = decode_intent(published['aolIntentWire'].aolIntentWire)
    assert intent is not None
    assert intent.carStateLogMonoTime == intent.observedMonoTime == source == now
    assert intent.validUntilMonoTime - intent.observedMonoTime == 200_000_000
    admitted = current_intent(Peers([published['aolIntentWire']]), car_state_ns=source, now_ns=now)
    assert admitted == intent
    # Faults modify only the negative cases after the actual producer boundary.
    if fault == 'stale_source':
      now += 30_000_001
    elif fault == 'future_source':
      source += 1
    elif fault == 'future_observation':
      intent = replace(intent, observedMonoTime=now + 1)
    elif fault == 'excessive_lease':
      intent = replace(intent, validUntilMonoTime=intent.observedMonoTime + 200_000_001)
    elif fault == 'expired':
      intent = replace(intent, validUntilMonoTime=now - 1)
    elif fault == 'no_expiry':
      intent = replace(intent, validUntilMonoTime=0)
    assert physical_cancel_lateral_allowed(card.CP, cs, intent, native,
      source_ns=source, now_ns=now) == (fault is None)
