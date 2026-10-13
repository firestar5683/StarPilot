from contextlib import ExitStack
from dataclasses import replace
from unittest import mock

import pytest

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE, intent
from openpilot.starpilot.aol.tests.test_long_only_input_wait import intent as long_intent
from openpilot.starpilot.aol.wire import decode_intent, encode_intent


def settings(mode, stamp, sequence):
  long_only = mode == 'long_only'
  unarmed = mode in ('long_only', 'combined_unarmed')
  wire = long_intent(stamp, sequence) if long_only else intent(stamp, sequence)
  if mode == 'combined_unarmed':
    wire.aolIntentWire = encode_intent(replace(decode_intent(wire.aolIntentWire), allowedLatch=False, lateralArmed=False))
  return {'latched': not unarmed, 'pause': long_only, 'native_request_lat': not long_only,
              'allowed': not long_only, 'native_request_long': mode != 'lateral_only', 'intent_message': wire}


@pytest.mark.parametrize('mode', ['long_only', 'combined', 'combined_unarmed', 'lateral_only'])
def test_expired_commands_withdraw_but_host_loss_keeps_ordinary_soft_state(mode):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, controls, drive, card, receive = case._ioniq_availability_callers(full_op=mode != 'lateral_only')
    old, _, command = drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings(mode, BASE, 3))
    assert old.longitudinalActive == (mode != 'lateral_only')
    deadline = old.validUntilMonoTime
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=deadline + 1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
    decision = BASE + 35_399_000
    axis, state, command = drive(5, timeout=True, state_stamp=BASE, offset_ns=5_399_000,
                                 **settings(mode, BASE, 3))
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    assert old.validUntilMonoTime == deadline < decision
    assert log.OnroadEvent.EventName.commIssue in sd.events.names or mode == 'lateral_only'
    if mode != 'lateral_only':
      assert state.enabled and state.active
      assert state.state == log.SelfdriveState.OpenpilotState.softDisabling
      assert state.alertType == 'commIssue/softDisable'
      assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
      assert not sd.aol_authority_lost and not getattr(sd, 'aol_availability_long_inhibit', False)
      assert axis.sourceCarStateMonoTime == 0
      assert not sd.conditional_car_state_valid
    else:
      # This proposal adds no ordinary engagement to an existing AOL-only path.
      assert not state.enabled and not command.longActive
    if mode == 'combined':
      assert receive(decision, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      assert card.aol_card_intent.allowed_latch
    fresh = BASE + 40_000_000
    recovered, recovered_state, recovered_command = drive(6, state_stamp=fresh,
                                                          **settings(mode, fresh, 4))
    assert recovered.longitudinalActive == (mode != 'lateral_only')
    assert recovered_command.longActive == (mode != 'lateral_only')
    assert recovered_state.enabled == (mode != 'lateral_only')
    assert recovered.sourceCarStateMonoTime == fresh
    assert recovered.observedMonoTime >= fresh and recovered.validUntilMonoTime > recovered.observedMonoTime


@pytest.mark.parametrize('mode', ['long_only', 'combined', 'combined_unarmed'])
def test_normal_soft_countdown_disables_and_fresh_input_cannot_auto_enable_long(mode):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, _, _ = case._ioniq_availability_callers(full_op=True)
    drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings(mode, BASE, 3))
    axis, state, command = drive(5, timeout=True, offset_ns=5_399_000, **settings(mode, BASE, 3))
    assert state.enabled and sd.state_machine.soft_disable_timer == 300
    for tick in range(6, 307):
      axis, state, command = drive(tick, timeout=True, **settings(mode, BASE, 3))
      assert not axis.lateralActive and not axis.longitudinalActive
      assert not command.latActive and not command.longActive
    assert not state.enabled and not state.active and sd.state_machine.soft_disable_timer == 0
    fresh = BASE + 3_060_000_000
    axis, state, command = drive(308, state_stamp=fresh, **settings(mode, fresh, 4))
    assert not state.enabled and not command.longActive and not axis.longitudinalActive
    assert not sd.events.contains(fixture.ET.ENABLE)


@pytest.mark.parametrize('fault', ['native_invalid', 'panda_rx', 'relay', 'permanent_eps', 'can_invalid',
                                  'cancel', 'driver_lockout', 'producer_epoch'])
def test_host_classification_does_not_exempt_hard_fault_or_changed_provenance(fault):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, _, _ = case._ioniq_availability_callers(full_op=True)
    drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings('long_only', BASE, 3))
    options = settings('long_only', BASE, 3)
    observed = fixture.car_state()
    if fault == 'permanent_eps':
      observed.steerFaultPermanent = True
    elif fault == 'can_invalid':
      observed.canValid = False
    elif fault == 'cancel':
      observed.buttonEvents = [fixture.car.CarState.ButtonEvent(type=fixture.car.CarState.ButtonEvent.Type.cancel, pressed=True)]
    elif fault == 'producer_epoch':
      options['intent_message'] = long_intent(BASE, 40, producer='changed-card')
    original_events = sd.update_events
    def events(cs):
      if fault == 'driver_lockout':
        dm = messaging.new_message('driverMonitoringState', valid=True, logMonoTime=BASE + 35_399_000)
        dm.driverMonitoringState.lockout = True
        sd.sm.update_msgs((BASE + 35_399_000) / 1e9, [dm.as_reader()])
      return original_events(cs)
    with mock.patch.object(sd, 'update_events', side_effect=events):
      axis, state, command = drive(5, state_stamp=BASE, offset_ns=5_399_000, observed_state=observed,
        native_valid=fault != 'native_invalid', panda_fault=fault == 'panda_rx', relay_fault=fault == 'relay', **options)
    assert not axis.longitudinalActive and not command.longActive
    assert not state.enabled and not sd.aol_ordinary_source_pause



def test_sustained_full_mode_source_pause_preserves_only_established_card_latch():
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, controls, drive, card, receive = case._ioniq_availability_callers(full_op=True)
    old, _, command = drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings('combined', BASE, 3))
    assert old.lateralActive and old.longitudinalActive and card.aol_card_intent.allowed_latch
    deadline = old.validUntilMonoTime
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=deadline + 1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
    previous_clear_count = card.aol_card_intent.latch_clear_count
    for tick in range(5, 306):
      offset = 5_399_000 if tick == 5 else 0
      now = BASE + (tick - 2) * 10_000_000 + offset
      axis, state, command = drive(tick, timeout=True, offset_ns=offset, **settings('combined', BASE, 3))
      assert not axis.lateralActive and not axis.longitudinalActive
      assert not command.latActive and not command.longActive
      latched = receive(now, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      assert latched, {'tick': tick, 'source_age_ns': now - BASE, 'clear_reason': card.aol_card_intent.latch_clear_reason,
                       'axis_fault': str(axis.faultReason), 'driver_enabled': state.enabled}
      assert card.aol_card_intent.latch_clear_count == previous_clear_count
    assert not state.enabled and not state.active
    fresh = BASE + 3_050_000_000
    axis, state, command = drive(307, state_stamp=fresh, **settings('combined', fresh, 4))
    assert not state.enabled and not command.longActive and not axis.longitudinalActive
    assert old.validUntilMonoTime == deadline



@pytest.mark.parametrize('shape', ['valid_new', 'expired_new', 'zero_ttl', 'overlong_ttl', 'future_observation'])
def test_new_raw_without_cs_needs_its_own_valid_original_intent_shape(shape):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, _, _ = case._ioniq_availability_callers(full_op=True)
    drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings('long_only', BASE, 3))
    decision = BASE + 35_399_000
    stamp = BASE + 34_000_000
    wire = long_intent(stamp, 4)
    decoded = decode_intent(wire.aolIntentWire)
    changes = {'expired_new': {'validUntilMonoTime': decision - 1},
               'zero_ttl': {'validUntilMonoTime': decoded.observedMonoTime},
               'overlong_ttl': {'validUntilMonoTime': decoded.observedMonoTime + 200_000_001},
               'future_observation': {'observedMonoTime': decision + 1}}.get(shape, {})
    wire.aolIntentWire = encode_intent(replace(decoded, **changes))
    options = settings('long_only', BASE, 3)
    options['intent_message'] = wire
    axis, state, command = drive(5, timeout=True, state_stamp=BASE, offset_ns=5_399_000, **options)
    assert not axis.longitudinalActive and not command.longActive
    assert state.enabled == (shape == 'valid_new')
    assert sd.aol_ordinary_source_pause == (shape == 'valid_new')
    if state.enabled:
      assert axis.sourceCarStateMonoTime == 0 and not sd.conditional_car_state_valid
      assert state.state == log.SelfdriveState.OpenpilotState.softDisabling


@pytest.mark.parametrize('mode', ['long_only', 'combined'])
def test_inactive_host_pause_cannot_claim_withdrawn_native_lateral_ack(mode):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, _, _ = case._ioniq_availability_callers(full_op=True)
    drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings(mode, BASE, 3))
    options = settings(mode, BASE, 3)
    options.update(native_request_lat=False, allowed=False, native_request_long=False)
    axis, state, command = drive(5, timeout=True, offset_ns=5_399_000, **options)
    assert state.enabled and state.state == log.SelfdriveState.OpenpilotState.softDisabling
    assert axis.sourceCarStateMonoTime == 0
    assert not axis.nativeAcknowledged and not axis.desiredLateral
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive


@pytest.mark.parametrize('mode', ['long_only', 'combined_unarmed'])
def test_fresh_admission_crossing_cutoff_during_publication_withdraws_without_rewriting_state_timer(mode):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, controls, drive, _, _ = case._ioniq_availability_callers(full_op=True)
    old, _, _ = drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings(mode, BASE, 3))
    old_deadline = old.validUntilMonoTime
    fresh = BASE + 40_000_000
    clock = [fresh + 29_999_000]
    original_transition = sd.state_machine.update
    crossed = [False]
    def transition(events):
      result = original_transition(events)
      clock[0] = fresh + 30_001_000
      crossed[0] = True
      return result
    with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: clock[0]), \
         mock.patch.object(sd.state_machine, 'update', side_effect=transition) as updates:
      axis, state, command = drive(6, state_stamp=fresh, offset_ns=29_999_000, **settings(mode, fresh, 4))
    assert crossed[0] and updates.call_count == 1
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    assert axis.sourceCarStateMonoTime == 0 and not sd.conditional_car_state_valid
    assert state.enabled and state.active
    assert state.state == log.SelfdriveState.OpenpilotState.enabled
    assert sd.state_machine.soft_disable_timer == 0
    assert log.OnroadEvent.EventName.commIssue in sd.events.names
    assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
    assert sd.aol_ordinary_source_anchor[0][3] == old_deadline
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=old_deadline + 1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
    # The normal NEXT StateMachine transition owns the countdown. Nothing in
    # the publication helper writes state, replays ENABLE, or extends old proof.
    with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=fresh + 40_000_000):
      axis, state, command = drive(7, timeout=True, state_stamp=fresh, offset_ns=30_000_000, **settings(mode, fresh, 4))
    assert state.enabled and state.state == log.SelfdriveState.OpenpilotState.softDisabling
    assert sd.state_machine.soft_disable_timer == 300
    assert not axis.longitudinalActive and not command.longActive


@pytest.mark.parametrize('mode', ['long_only', 'combined_unarmed'])
def test_fresh_native_request_return_renews_only_a_fresh_source_before_actual_disable(mode):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, controls, drive, _, _ = case._ioniq_availability_callers(full_op=True)
    old, _, _ = drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings(mode, BASE, 3))
    options = settings(mode, BASE, 3)
    options.update(native_request_lat=False, allowed=False, native_request_long=False, long_allowed=False)
    axis, state, command = drive(5, timeout=True, offset_ns=5_399_000, **options)
    assert state.enabled and state.state == log.SelfdriveState.OpenpilotState.softDisabling
    assert not axis.nativeAcknowledged and not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=old.validUntilMonoTime + 1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
    fresh = BASE + 40_000_000
    axis, state, command = drive(6, state_stamp=fresh, **settings(mode, fresh, 4))
    assert state.enabled and state.state == log.SelfdriveState.OpenpilotState.enabled
    assert axis.sourceCarStateMonoTime == fresh and axis.longitudinalActive and command.longActive
    assert not sd.events.contains(fixture.ET.ENABLE)
