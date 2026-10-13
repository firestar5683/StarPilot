"""Temporary lag preserves armed intent without retaining command authority."""
from contextlib import ExitStack
from unittest import mock
import pytest

from openpilot.cereal import log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture


@pytest.mark.parametrize(('full_op', 'gas'), [(False, True), (True, False)],
                         ids=['lateral_only_accelerator_override', 'ordinary_combined'])
@pytest.mark.parametrize('order', ['axis_first', 'event_first', 'together'])
def test_actual_isolated_lag_keeps_only_existing_card_intent(full_op, gas, order):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=full_op)
    feedback = card.aol_transport_feedback
    baseline = (feedback.lateral_baseline_ns, feedback.lateral_source_ns,
                feedback.lateral_native_ns, feedback.healthy_feedback_ns, feedback.healthy_native_ns)
    assert card.aol_card_intent.allowed_latch and feedback.session
    with mock.patch.object(type(sd.rk), 'lagging', new_callable=mock.PropertyMock, return_value=True):
      axis, state, command = drive(2, gas=gas, native_request_long=full_op)
    assert str(axis.faultReason) == 'critical'
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    assert sd.events.contains(fixture.ET.SOFT_DISABLE)
    assert log.OnroadEvent.EventName.selfdrivedLagging in sd.events.names
    assert state.enabled == full_op
    if full_op:
      assert state.state == log.SelfdriveState.OpenpilotState.softDisabling
      assert state.alertType == 'selfdrivedLagging/softDisable'
    proof, event = sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents']
    assert proof.aolAxisState.faultEventMonoTime == event.logMonoTime
    deliveries = [{'axis': proof}, {'event': event}] if order == 'axis_first' else \
                 [{'event': event}, {'axis': proof}] if order == 'event_first' else [{'axis': proof, 'event': event}]
    # All legitimate delivery orders retain only intent; unmatched critical
    # joins are bounded and every current command remains withdrawn.
    for index, delivery in enumerate(deliveries):
      latched = receive(10_020_000_000 + index * 100_000, **delivery)
      if order == 'axis_first' and index == 0:
        assert feedback.pending_event == proof.aolAxisState.faultEventMonoTime
        assert feedback.awaiting
      assert latched and not feedback.failed
    assert baseline == (feedback.lateral_baseline_ns, feedback.lateral_source_ns,
                         feedback.lateral_native_ns, feedback.healthy_feedback_ns, feedback.healthy_native_ns)
    assert not feedback.qualified and not feedback.awaiting and not feedback.retention_qualified
    assert proof.aolAxisState.validUntilMonoTime == 10_050_000_000
    # Clearing temporary lag does not supply an ordinary enable or native ACK.
    recovered, next_state, next_command = drive(3, allowed=False, native_request_lat=False,
                                               native_request_long=False)
    assert not recovered.lateralActive and not recovered.longitudinalActive
    assert not next_command.latActive and not next_command.longActive
    # Card has received no replacement proof/native grant; retained intent
    # cannot turn these independently blocked commands into output.
    assert card.aol_card_intent.allowed_latch
    if not full_op:
      assert not next_state.enabled


@pytest.mark.parametrize('fault', ['controls_mismatch', 'process_failure', 'overheat', 'permanent_eps',
  'invalid_can', 'can_timeout', 'invalid_native', 'native_denial', 'panda_rx', 'producer', 'epoch',
  'event_stamp', 'axis_deadline', 'source_age', 'cancel', 'settings_disabled'])
def test_temporary_lag_never_masks_real_fault_or_invalid_proof(fault):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=False)
    actual_events = sd.update_events
    def events(cs):
      result = actual_events(cs)
      extra = {'controls_mismatch': log.OnroadEvent.EventName.controlsMismatch,
               'process_failure': log.OnroadEvent.EventName.processNotRunning,
               'overheat': log.OnroadEvent.EventName.overheat}.get(fault)
      if extra is not None:
        sd.events.add(extra)
      return result
    with mock.patch.object(type(sd.rk), 'lagging', new_callable=mock.PropertyMock, return_value=True), \
         mock.patch.object(sd, 'update_events', side_effect=events):
      axis, _, command = drive(2, allowed=fault != 'native_denial',
        native_valid=fault != 'invalid_native', panda_fault=fault == 'panda_rx', native_request_long=False)
    proof = sd.pm.messages['aolAxisState'].as_builder()
    event = sd.pm.messages['onroadEvents'].as_builder()
    state = fixture.car_state()
    if fault == 'permanent_eps':
      state.steerFaultPermanent = True
    elif fault == 'invalid_can':
      state.canValid = False
    elif fault == 'can_timeout':
      state.canTimeout = True
    elif fault == 'producer':
      proof.aolAxisState.intentProducerSessionId = 'other-card'
    elif fault == 'epoch':
      proof.aolAxisState.intentIntegrityEpoch += 1
    elif fault == 'event_stamp':
      event.logMonoTime += 1
    elif fault == 'source_age':
      proof.aolAxisState.sourceCarStateMonoTime -= 30_000_001
    elif fault == 'cancel':
      from opendbc.car.structs import car
      state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
    elif fault == 'settings_disabled':
      from dataclasses import replace
      card.aol_card_intent.settings = replace(card.aol_card_intent.settings, enabled=False)
    now = 10_020_000_000 if fault != 'axis_deadline' else 10_050_000_001
    assert not command.latActive and not command.longActive
    assert not receive(now, axis=proof.as_reader(), event=event.as_reader(), state=state)
    assert not card.aol_card_intent.allowed_latch


def test_persistent_lag_keeps_latch_but_ordinary_countdown_still_disables():
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=True)
    with mock.patch.object(type(sd.rk), 'lagging', new_callable=mock.PropertyMock, return_value=True):
      for tick in range(2, 304):
        axis, state, command = drive(tick, native_request_long=False)
        assert not axis.lateralActive and not axis.longitudinalActive
        assert not command.latActive and not command.longActive
        assert receive(10_000_000_000 + tick*10_000_000,
          axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    assert not state.enabled and not state.active and sd.state_machine.soft_disable_timer == 0
    assert card.aol_card_intent.allowed_latch
    axis, state, command = drive(304, native_request_long=False)
    assert not state.enabled and not command.longActive and not axis.longitudinalActive
    # A newly current lateral native ACK alone can restore lateral output.
    assert axis.lateralActive and command.latActive


@pytest.mark.parametrize('failure', ['missing_event', 'hard_event', 'wrong_event', 'session', 'inventory'])
def test_axis_first_critical_join_never_masks_missing_or_hard_occurrence(failure):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=False)
    with mock.patch.object(type(sd.rk), 'lagging', new_callable=mock.PropertyMock, return_value=True):
      axis, _, command = drive(2, native_request_long=False)
    proof = sd.pm.messages['aolAxisState'].as_builder()
    assert receive(10_020_000_000, axis=proof.as_reader())
    anchor = card.aol_transport_feedback.pending_event
    assert anchor == proof.aolAxisState.faultEventMonoTime
    event = sd.pm.messages['onroadEvents'].as_builder()
    now = 10_020_100_000
    if failure == 'missing_event':
      now = anchor + 30_000_001
      delivery = {'axis': proof.as_reader()}
    elif failure == 'hard_event':
      from openpilot.cereal import messaging
      event = messaging.new_message('onroadEvents', 1, valid=True, logMonoTime=anchor)
      event.onroadEvents[0].name = 'controlsMismatch'
      event.onroadEvents[0].immediateDisable = True
      delivery = {'event': event.as_reader()}
    elif failure == 'wrong_event':
      event.logMonoTime += 1
      delivery = {'event': event.as_reader()}
    elif failure == 'session':
      proof.aolAxisState.sessionId = proof.aolAxisState.faultSessionId = 'other-session'
      delivery = {'axis': proof.as_reader(), 'event': event.as_reader()}
    else:
      from dataclasses import replace
      from openpilot.cereal import messaging
      from openpilot.starpilot.aol.wire import decode_safety, encode_safety
      native = decode_safety(sd.sm['aolSafetyWire'])
      bad = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=native.observedMonoTime)
      bad.aolSafetyWire = encode_safety(replace(native, pandaSerial='changed-native',
        pandaInventory=tuple(replace(slot, hardwareSerial='changed-native') for slot in native.pandaInventory)))
      sd.sm.update_msgs(10.0201, [bad.as_reader()])
      delivery = {'axis': proof.as_reader(), 'event': event.as_reader()}
    assert not command.latActive and not command.longActive
    assert not receive(now, **delivery)
    assert not card.aol_card_intent.allowed_latch


@pytest.mark.parametrize('dm', ['alert_three', 'lockout'])
def test_dm_inhibits_actual_lateral_output_during_and_after_lag(dm):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=False)
    # Fixture DM is produced at its actual 20Hz cadence. Keep the established
    # Card proof current until the next real DM publication at tick5 (10.05s).
    for tick in range(2, 5):
      axis, _, command = drive(tick, native_request_long=False)
      assert axis.lateralActive and command.latActive
      assert receive(10_000_000_000 + tick*10_000_000,
        axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    actual_update = sd.sm.update_msgs
    dm_current = [True]
    delivered = []
    def update(timestamp, messages):
      selected = []
      for message in messages:
        if message.which() == 'driverMonitoringState':
          delivered.append(int(message.logMonoTime))
          if dm_current[0]:
            message = message.as_builder()
            message.driverMonitoringState.activePolicy = 'vision'
            if dm == 'alert_three':
              message.driverMonitoringState.alertLevel = 'three'
            else:
              message.driverMonitoringState.lockout = True
            message = message.as_reader()
        selected.append(message)
      return actual_update(timestamp, selected)
    with mock.patch.object(sd.sm, 'update_msgs', side_effect=update):
      with mock.patch.object(type(sd.rk), 'lagging', new_callable=mock.PropertyMock, return_value=True):
        axis, _, command = drive(5, native_request_long=False)
      assert delivered == [10_050_000_000]
      assert sd.sm.logMonoTime['driverMonitoringState'] == 10_050_000_000
      if dm == 'alert_three':
        assert sd.sm['driverMonitoringState'].alertLevel == log.DriverMonitoringState.AlertLevel.three
      else:
        assert sd.sm['driverMonitoringState'].lockout
      assert not axis.lateralActive and not axis.longitudinalActive
      assert not command.latActive and not command.longActive
      assert sd.aol_dm_lateral_inhibit
      expected = log.OnroadEvent.EventName.driverDistracted3 if dm == 'alert_three' else log.OnroadEvent.EventName.tooDistracted
      assert expected in sd.events.names
      assert receive(10_050_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      assert card.aol_card_intent.allowed_latch
      dm_current[0] = False
      # DM remains current until its next cadence sample; neither clearing lag
      # nor a new positive native ACK removes the independent lateral inhibit.
      for tick in range(6, 11):
        axis, state, command = drive(tick, native_request_long=False)
        assert sd.aol_dm_lateral_inhibit
        assert not axis.lateralActive and not axis.longitudinalActive
        assert not command.latActive and not command.longActive and not state.enabled
      assert delivered == [10_050_000_000, 10_100_000_000]
      assert sd.sm.logMonoTime['driverMonitoringState'] == 10_100_000_000
      assert sd.sm['driverMonitoringState'].alertLevel == log.DriverMonitoringState.AlertLevel.none
      assert not sd.sm['driverMonitoringState'].lockout


@pytest.mark.parametrize('qualification', ['passive', 'unknown_brand'])
def test_unqualified_cp_cannot_use_temporary_lag_intent_exception(qualification):
  from openpilot.starpilot.aol.vehicle import policy_for
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=False)
    assert policy_for(card.CP).intent_supported
    with mock.patch.object(type(sd.rk), 'lagging', new_callable=mock.PropertyMock, return_value=True):
      axis, _, command = drive(2, native_request_long=False)
    changed = card.CP.as_reader().as_builder()
    if qualification == 'passive':
      changed.passive = True
    else:
      changed.brand = 'unregistered_vehicle'
    assert not policy_for(changed).intent_supported
    with mock.patch.object(card, 'CP', changed.as_reader()):
      assert not receive(10_020_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    assert not card.aol_card_intent.allowed_latch
    assert not command.latActive and not command.longActive


@pytest.mark.parametrize('cp', [None, {}, 'missing_brand', 'malformed_registered_brand'])
def test_missing_or_malformed_vehicle_policy_grants_no_intent_capability(cp):
  from types import SimpleNamespace
  from openpilot.starpilot.aol.vehicle import policy_for
  if cp == 'missing_brand':
    cp = SimpleNamespace()
  elif cp == 'malformed_registered_brand':
    cp = SimpleNamespace(brand='hyundai')
  assert not policy_for(cp).intent_supported
