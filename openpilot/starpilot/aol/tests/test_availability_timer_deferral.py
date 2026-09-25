from contextlib import ExitStack
from dataclasses import replace
from unittest import mock

import pytest
from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.selfdrived import selfdrived as owner
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_long_only_input_wait import intent
from openpilot.starpilot.aol.wire import decode_intent, encode_intent, decode_safety, encode_safety


SOURCE = 10_030_000_000
PUB = SOURCE + 4_837_661
DECISION = SOURCE + 31_625_140


def wire(stamp, seq):
  message = intent(stamp, seq, pause_lat=False)
  value = decode_intent(message.aolIntentWire)
  message.aolIntentWire = encode_intent(replace(value, allowedLatch=True, lateralArmed=True))
  return message


def prepare(stack):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  stack.callback(case.doCleanups)
  stack.enter_context(OpenpilotPrefix())
  sd, controls, drive, card, receive = case._ioniq_availability_callers(full_op=True)
  axis, state, command = drive(2, car_output_valid=False)
  assert str(axis.faultReason) == 'availabilityPause'
  assert state.alertType == 'commIssue/softDisable'
  assert not state.enabled and not state.active and not command.latActive and not command.longActive
  assert sd.state_machine.state == log.SelfdriveState.OpenpilotState.disabled
  assert sd.state_machine.soft_disable_timer == 300
  axis, state, command = drive(3, state_stamp=SOURCE, offset_ns=4_837_661,
                              intent_message=wire(SOURCE, 4), native_request_long=False)
  assert axis.lateralActive and command.latActive
  assert not axis.desiredLongitudinal and not axis.longitudinalActive and not command.longActive
  assert not state.enabled and not state.active and sd.aol_availability_long_inhibit
  assert str(axis.faultReason) == 'none' and axis.nativeAcknowledged and axis.qualified
  assert axis.sourceCarStateMonoTime == SOURCE and axis.observedMonoTime == PUB
  assert axis.validUntilMonoTime == PUB + 30_000_000
  assert sd.state_machine.soft_disable_timer == 299
  return sd, controls, drive, axis


def test_first_pause_then_recovered_lateral_source_cutoff():
  with ExitStack() as stack:
    sd, controls, drive, original = prepare(stack)
    previous_axis = original.to_dict()
    timer_before = sd.state_machine.soft_disable_timer
    attempts = []
    actual_defer = sd.defer_expired_axis_publication
    now = [SOURCE + 29_900_000]
    actual_events = sd.update_events

    def events(cs):
      result = actual_events(cs)
      now[0] = DECISION
      return result

    sd.car_state_poller = mock.Mock()
    sd.car_state_poller.poll.return_value = []

    def defer(cs, initial, **kwargs):
      result = actual_defer(cs, initial, **kwargs)
      attempts.append(result)
      return result

    with mock.patch.object(owner.time, 'monotonic_ns', side_effect=lambda: now[0]), \
         mock.patch.object(sd, 'defer_expired_axis_publication', side_effect=defer), \
         mock.patch.object(sd, 'update_events', side_effect=events):
      axis, state, command = drive(6, timeout=True, offset_ns=-100_000,
                                  intent_message=wire(SOURCE, 4), native_request_long=False)
    assert sd.aol_axis_publication_deferred
    assert not state.enabled and not state.active and not command.longActive and not axis.longitudinalActive
    assert sd.state_machine.soft_disable_timer == timer_before == 299
    assert axis.to_dict() == previous_axis and command.latActive
    assert attempts == [True]
    # One tick only, even before the original proof's unchanged deadline.
    with mock.patch.object(owner.time, 'monotonic_ns', return_value=SOURCE + 33_000_000):
      next_axis, _, next_command = drive(6, timeout=True, offset_ns=3_000_000,
        intent_message=wire(SOURCE, 4), native_request_long=False)
    assert not sd.aol_axis_publication_deferred
    assert sd.state_machine.soft_disable_timer == 298
    assert not next_axis.lateralActive and not next_command.latActive and not next_command.longActive


@pytest.mark.parametrize('condition', ['current_soft', 'current_immediate', 'current_enable', 'current_user',
  'deadline', 'initial_state_changed', 'invalid_carstate', 'settings_revoked', 'intent_pause',
  'intent_unlatched', 'producer_changed', 'session_changed', 'active_soft_disabling',
  'native_denial', 'native_invalid', 'can_invalid', 'can_timeout', 'eps_temp', 'eps_perm',
  'dm_event_changed', 'lagging', 'thermal', 'wrong_gear', 'physical_cancel',
  'no_inhibit', 'authority_lost', 'proof_changed', 'integrity_epoch'])
def test_timer_fix_retains_fault_identity_and_original_deadline_gates(condition):
  with ExitStack() as stack:
    sd, _, _, axis = prepare(stack)
    previous = axis.to_dict()
    source_proof = sd.aol_published_input_proof
    sd.aol_step_input_proof = source_proof
    sd.aol_step_deferral_checked = False
    sd.aol_step_intent_drain_count = 0
    now = DECISION
    cs = sd.CS_prev
    event = {'current_soft': owner.EventName.commIssue,
             'current_immediate': owner.EventName.controlsMismatch,
             'current_enable': owner.EventName.buttonEnable,
             'current_user': owner.EventName.buttonCancel}.get(condition)
    if event is not None:
      sd.events.add(event)
      # Keep event-set equality so the actual event-kind guards are exercised.
      sd.events_prev = sd.events.names.copy()
    elif condition == 'deadline':
      now = source_proof[3]
    elif condition == 'invalid_carstate':
      sd.conditional_car_state_valid = False
    elif condition in ('settings_revoked', 'intent_pause', 'intent_unlatched', 'producer_changed'):
      latest = sd.aol_intent_companion.latest
      changes = {'settings_revoked': {'settingsQualified': False}, 'intent_pause': {'pauseLateral': True},
                 'intent_unlatched': {'allowedLatch': False}, 'producer_changed': {'producerSessionId': 'other-card'}}[condition]
      sd.aol_intent_companion.latest = (latest[0], latest[1], replace(latest[2], **changes))
    elif condition == 'session_changed':
      sd.aol_session_id = 'other-owner'
    elif condition == 'active_soft_disabling':
      # Reach the genuine production soft-disabling state and countdown.
      sd.state_machine.state = log.SelfdriveState.OpenpilotState.enabled
      sd.events.add(owner.EventName.commIssue)
      sd.enabled, sd.active = sd.state_machine.update(sd.events)
      assert sd.enabled and sd.active and sd.state_machine.soft_disable_timer == 300
      assert sd.state_machine.state == log.SelfdriveState.OpenpilotState.softDisabling
      sd.events_prev = sd.events.names.copy()
    if condition in ('can_invalid', 'can_timeout', 'eps_temp', 'eps_perm', 'wrong_gear', 'physical_cancel'):
      from opendbc.car.structs import car
      cs = sd.CS_prev.as_builder()
      if condition == 'can_invalid':
        cs.canValid = False
      elif condition == 'can_timeout':
        cs.canTimeout = True
      elif condition == 'eps_temp':
        cs.steerFaultTemporary = True
      elif condition == 'eps_perm':
        cs.steerFaultPermanent = True
      elif condition == 'wrong_gear':
        cs.gearShifter = car.CarState.GearShifter.park
      else:
        cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
      sd.car_state_samples = ((cs, True),)
    elif condition == 'native_denial':
      native = decode_safety(sd.sm['aolSafetyWire'])
      message = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=PUB)
      message.aolSafetyWire = encode_safety(replace(native, lateralAllowed=False))
      sd.sm.update_msgs(PUB / 1e9, [message.as_reader()])
    elif condition == 'native_invalid':
      sd.sm.valid['aolSafetyWire'] = False
    elif condition == 'dm_event_changed':
      sd.events.add(owner.EventName.driverDistracted3)
    elif condition == 'lagging':
      stack.enter_context(mock.patch.object(type(sd.rk), 'lagging', new_callable=mock.PropertyMock, return_value=True))
    elif condition == 'thermal':
      message = messaging.new_message('deviceState', valid=True, logMonoTime=PUB)
      message.deviceState = sd.sm['deviceState']
      message.deviceState.thermalStatus = 'overheated'
      sd.sm.update_msgs(PUB / 1e9, [message.as_reader()])
    elif condition == 'no_inhibit':
      sd.aol_availability_long_inhibit = False
    elif condition == 'authority_lost':
      sd.aol_authority_lost = True
    elif condition == 'proof_changed':
      sd.aol_step_input_proof = (*source_proof[:3], source_proof[3] + 1, *source_proof[4:])
    elif condition == 'integrity_epoch':
      sd.aol_intent_companion.integrity_epoch += 1
    initial = (sd.state_machine.state, sd.state_machine.soft_disable_timer, sd.enabled, sd.active)
    if condition == 'initial_state_changed':
      sd.state_machine.soft_disable_timer += 1
    with mock.patch.object(owner.time, 'monotonic_ns', return_value=now), \
         mock.patch.object(messaging, 'recv_one_or_none', return_value=None):
      result = sd.defer_expired_axis_publication(cs, initial, now_ns=now)
    assert not result
    assert sd.pm.messages['aolAxisState'].aolAxisState.to_dict() == previous
    assert sd.aol_published_input_proof == source_proof
