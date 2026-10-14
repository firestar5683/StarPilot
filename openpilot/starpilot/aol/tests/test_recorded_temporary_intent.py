from contextlib import ExitStack
from unittest import mock

import pytest

from openpilot.cereal import log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_temporary_steering_sequence import baseline, leases


def test_actual_eps_recovered_car_state_before_withdrawal_feedback():
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = baseline(case)
    original = leases(card.aol_transport_feedback)
    temporary = fixture.car_state()
    temporary.gasPressed = temporary.steerFaultTemporary = True
    for tick in range(152, 166):
      axis, _, command = drive(tick, gas=True, observed_state=temporary, allowed=False,
                               native_request_lat=False, native_request_long=False)
      assert not command.latActive and not command.longActive
      assert not axis.lateralActive and not axis.longitudinalActive
      assert receive(10_000_000_000 + tick * 10_000_000, axis=sd.pm.messages['aolAxisState'],
                     event=sd.pm.messages['onroadEvents'], state=temporary)
    recovered = fixture.car_state()
    recovered.gasPressed = True
    assert receive(11_655_000_000, state=recovered)
    assert card.aol_card_intent.allowed_latch
    assert leases(card.aol_transport_feedback) == original
    assert not card.sm['aolAxisState'].lateralActive and not card.sm['carControl'].longActive


@pytest.mark.parametrize('event_name', ['selfdrivedLagging', 'locationdTemporaryError'])
def test_actual_temporary_host_event_keeps_only_armed_intent(event_name):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=False)
    original = leases(card.aol_transport_feedback)
    axis, state, command = drive(2, gas=True, critical_event=getattr(log.OnroadEvent.EventName, event_name),
                                 native_request_long=False)
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive and not state.enabled
    assert receive(10_020_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    assert card.aol_card_intent.allowed_latch
    assert leases(card.aol_transport_feedback) == original


@pytest.mark.parametrize('fault', ['native_denial', 'panda_fault', 'permanent_eps', 'invalid_can', 'hard_event'])
def test_recorded_temporary_host_path_never_masks_native_or_hard_fault(fault):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=False)
    axis, _, command = drive(2, gas=True, critical_event=log.OnroadEvent.EventName.locationdTemporaryError,
                             allowed=fault != 'native_denial', panda_fault=fault == 'panda_fault', native_request_long=False)
    state = fixture.car_state()
    state.steerFaultPermanent = fault == 'permanent_eps'
    state.canValid = fault != 'invalid_can'
    proof, event = sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents']
    if fault == 'hard_event':
      event = event.as_builder()
      event.onroadEvents[0].immediateDisable = True
    assert not receive(10_020_000_000, axis=proof, event=event, state=state)
    assert not command.longActive


def test_actual_ordinary_brake_with_current_lateral_grant_never_reenables_long():
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, controls, drive, card, receive = case._ioniq_availability_callers(full_op=True)
    axis, state, command = drive(2, brake=True, native_request_long=False)
    assert axis.lateralActive and not axis.longitudinalActive
    assert command.latActive and not command.longActive
    assert not state.enabled
    actual_control = controls.pm.messages['carControl']
    assert actual_control.logMonoTime == 10_020_000_000
    assert not actual_control.carControl.longActive
    sd.sm.update_msgs(10.02, [actual_control])
    observed = fixture.car_state(brake=True)
    assert receive(10_020_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'], state=observed)
    assert card.aol_card_intent.allowed_latch
    assert not card.sm['carControl'].longActive


@pytest.mark.parametrize('event_first', [False, True])
def test_actual_repeated_lag_after_healthy_pulse_and_native_withdrawal(event_first):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=False)
    with mock.patch.object(type(sd.rk), 'lagging', new_callable=mock.PropertyMock, return_value=True):
      axis, _, command = drive(2, gas=True, native_request_long=False)
    assert not axis.lateralActive and not command.latActive and not command.longActive
    assert receive(10_020_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    healthy, _, command = drive(3, gas=True, native_request_long=False)
    assert healthy.lateralActive and command.latActive and not command.longActive
    healthy_proof = sd.pm.messages['aolAxisState']
    assert receive(10_030_000_000, axis=healthy_proof, event=sd.pm.messages['onroadEvents'])
    original = leases(card.aol_transport_feedback)
    with mock.patch.object(type(sd.rk), 'lagging', new_callable=mock.PropertyMock, return_value=True):
      axis, _, command = drive(4, gas=True, native_request_long=False)
    proof, event = sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents']
    assert not axis.lateralActive and not command.latActive and not command.longActive
    if event_first:
      assert receive(10_040_000_000, axis=healthy_proof, event=event)
    assert receive(10_040_100_000, axis=proof, event=event)
    assert leases(card.aol_transport_feedback) == original
    with mock.patch.object(type(sd.rk), 'lagging', new_callable=mock.PropertyMock, return_value=True):
      axis, state, command = drive(5, gas=True, allowed=False, native_request_lat=False, native_request_long=False)
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive and not state.enabled
    assert receive(10_050_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    assert card.aol_card_intent.allowed_latch


@pytest.mark.parametrize('fault', ['none', 'native_lat_denial', 'extra_user', 'hard', 'source_reorder', 'epoch', 'session', 'expired'])
def test_actual_brake_old_combined_native_and_new_panda_long_withdrawal(fault):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, controls, drive, card, receive = case._ioniq_availability_callers(full_op=True)
    old_native = sd.sm['aolSafetyWire']
    old_native_stamp = sd.sm.logMonoTime['aolSafetyWire']
    assert card.aol_transport_feedback.signature[10]
    axis, state, command = drive(2, brake=True, native_request_long=False)
    assert axis.lateralActive and not axis.longitudinalActive
    assert command.latActive and not command.longActive and not state.enabled
    proof = sd.pm.messages['aolAxisState'].as_builder()
    event = sd.pm.messages['onroadEvents'].as_builder()
    if fault == 'source_reorder':
      proof.aolAxisState.sourceCarStateMonoTime = card.aol_transport_feedback.lateral_source_ns - 5_000_000
    elif fault == 'epoch':
      proof.aolAxisState.intentIntegrityEpoch += 1
    elif fault == 'session':
      proof.aolAxisState.sessionId = proof.aolAxisState.faultSessionId = 'wrong'
    elif fault == 'expired':
      proof.aolAxisState.validUntilMonoTime = 10_019_999_999
    elif fault in ('extra_user', 'hard'):
      event.onroadEvents[0].name = log.OnroadEvent.EventName.buttonCancel if fault == 'extra_user' else log.OnroadEvent.EventName.controlsMismatch
      event.onroadEvents[0].userDisable = fault == 'extra_user'
      event.onroadEvents[0].immediateDisable = fault == 'hard'
    from openpilot.cereal import messaging
    native = messaging.new_message('aolSafetyWire', len(old_native), valid=True, logMonoTime=old_native_stamp)
    native.aolSafetyWire = old_native
    if fault == 'native_lat_denial':
      from dataclasses import replace
      from openpilot.starpilot.aol.wire import decode_safety, encode_safety
      decoded = decode_safety(native.aolSafetyWire)
      native.aolSafetyWire = encode_safety(replace(decoded, lateralAllowed=False))
    panda = messaging.new_message('pandaStates', len(sd.sm['pandaStates']), valid=True, logMonoTime=10_020_000_000)
    panda.pandaStates = sd.sm['pandaStates']
    for slot in panda.pandaStates:
      slot.controlsAllowed = False
    sd.sm.update_msgs(10.02, [native.as_reader(), panda.as_reader()])
    actual_control = controls.pm.messages['carControl']
    assert actual_control.logMonoTime == 10_020_000_000
    assert not actual_control.carControl.longActive
    sd.sm.update_msgs(10.02, [actual_control])
    observed = fixture.car_state(brake=True)
    latched = receive(10_020_000_000, axis=proof.as_reader(), event=event.as_reader(), state=observed)
    assert latched == (fault == 'none')
    assert not card.sm['carControl'].longActive
    if fault != 'none':
      assert not card.aol_transport_feedback.temporary_host_qualified


@pytest.mark.parametrize('reset', ['session', 'configuration', 'rearm'])
def test_verified_eps_marker_cannot_cross_owner_reset(reset):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = baseline(case)
    temporary = fixture.car_state()
    temporary.steerFaultTemporary = True
    axis, _, command = drive(152, gas=True, observed_state=temporary, allowed=False,
                             native_request_lat=False, native_request_long=False)
    proof = sd.pm.messages['aolAxisState'].as_builder()
    event = sd.pm.messages['onroadEvents']
    assert receive(11_520_000_000, axis=proof.as_reader(), event=event, state=temporary)
    assert card.aol_transport_feedback.temporary_eps_event_ns
    if reset == 'session':
      proof.aolAxisState.sessionId = proof.aolAxisState.faultSessionId = 'different-session'
    elif reset == 'configuration':
      cp = card.CP.as_reader().as_builder()
      cp.alternativeExperience ^= 1
      card.CP = cp.as_reader()
    else:
      from opendbc.car.structs import car
      cancel = fixture.car_state()
      cancel.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
      card.aol_card_intent.update(cancel, now_ns=11_520_050_000)
      assert not card.aol_card_intent.allowed_latch
    receive(11_520_100_000, axis=proof.as_reader(), event=event, state=temporary)
    assert card.aol_transport_feedback.temporary_eps_event_ns == 0
    assert not command.latActive and not command.longActive


def test_full_long_location_error_event_first_withdraw_recover_brake_and_lkas_off():
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, controls, drive, card, receive = case._ioniq_availability_callers(full_op=True)
    actual_events = sd.update_events
    location_error = [True]

    def events(cs):
      result = actual_events(cs)
      if location_error[0]:
        sd.events.add(log.OnroadEvent.EventName.locationdTemporaryError)
      return result

    def publish_to_card(tick, *, axis=None, event=None, state=None):
      actual_control = controls.pm.messages['carControl']
      assert actual_control.logMonoTime == 10_000_000_000 + tick * 10_000_000
      actual_update = card.sm.update_msgs

      def transport(timestamp, frames):
        return actual_update(timestamp, [actual_control if frame.which() == 'carControl' else frame for frame in frames])

      with mock.patch.object(card.sm, 'update_msgs', side_effect=transport):
        return receive(actual_control.logMonoTime, axis=axis, event=event, state=state)

    from openpilot.cereal import messaging
    from openpilot.cereal.services import SERVICE_LIST
    optional_due = {}
    optional = [name for name in ('alertDebug', 'lateralManeuverPlan', 'laneChangeAssistWire',
                'starpilotLongitudinalPlan', 'slcState', sd.gps_location_service) if name in sd.sm.data]

    def drive_with_sources(tick, **kwargs):
      now = 10_000_000_000 + tick * 10_000_000
      frames = []
      for name in optional:
        frequency = SERVICE_LIST[name].frequency
        if frequency <= 0 or now < optional_due.get(name, 0):
          continue
        optional_due[name] = now + round(1e9 / frequency)
        if name == 'laneChangeAssistWire':
          from openpilot.starpilot.lateral.lane_change_status_wire import LaneChangeStatus, Phase, Direction, encode
          payload = encode(LaneChangeStatus('fixture-model', tick, tick * 5, now, now, now + 100_000_000,
                                           Phase.MANUAL_REQUIRED, Direction.NONE, False, False))
          sample = messaging.new_message(name, len(payload), valid=True, logMonoTime=now)
          sample.laneChangeAssistWire = payload
        else:
          sample = messaging.new_message(name, valid=True, logMonoTime=now)
        frames.append(sample.as_reader())
      actual_update = sd.sm.update_msgs
      delivered = [False]

      def transport(timestamp, messages):
        if not delivered[0]:
          delivered[0] = True
          messages = list(messages) + frames
        return actual_update(timestamp, messages)

      with mock.patch.object(sd.sm, 'update_msgs', side_effect=transport):
        return drive(tick, **kwargs)

    old_proof = sd.pm.messages['aolAxisState']
    with mock.patch.object(sd, 'update_events', side_effect=events):
      axis, state, command = drive_with_sources(2)
      assert state.enabled and state.active
      assert state.state == log.SelfdriveState.OpenpilotState.softDisabling
      assert state.alertType == 'locationdTemporaryError/softDisable'
      assert not axis.lateralActive and not axis.longitudinalActive
      assert not command.latActive and not command.longActive
      assert sd.state_machine.soft_disable_timer == 300
      # The actual newer event/command arrive before the new axis publication.
      assert publish_to_card(2, axis=old_proof, event=sd.pm.messages['onroadEvents'])
      assert card.aol_card_intent.allowed_latch
      assert card.aol_transport_feedback.signature[4] == old_proof.aolAxisState.validUntilMonoTime
      assert receive(10_020_100_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      assert card.aol_card_intent.allowed_latch
      # Follow the unchanged ordinary SOFT countdown, not a forced fixture disable.
      for tick in range(3, 303):
        axis, state, command = drive_with_sources(tick)
        assert publish_to_card(tick, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      assert not state.enabled and not state.active
      assert not axis.lateralActive and not axis.longitudinalActive
      assert not command.latActive and not command.longActive
      assert card.aol_card_intent.allowed_latch
      location_error[0] = False
      axis, state, command = drive_with_sources(303, native_request_long=False)
      assert not state.enabled and not state.active
      assert axis.lateralActive and not axis.longitudinalActive
      assert command.latActive and not command.longActive
      assert publish_to_card(303, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      axis, state, command = drive_with_sources(304, brake=True, native_request_long=False)
      assert not state.enabled and not axis.longitudinalActive and not command.longActive
      assert publish_to_card(304, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'],
                             state=fixture.car_state(brake=True))
      from opendbc.car.structs import car
      release = fixture.car_state()
      release.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=False)]
      assert receive(13_040_050_000, state=release)
      assert not card.aol_card_intent._lkas_held
      off = fixture.car_state()
      off.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
      assert not receive(13_040_100_000, state=off)
      assert not card.aol_card_intent.allowed_latch
      axis, state, command = drive_with_sources(305, native_request_long=False)
      assert not axis.lateralActive and not axis.longitudinalActive
      assert not command.latActive and not command.longActive and not state.enabled
