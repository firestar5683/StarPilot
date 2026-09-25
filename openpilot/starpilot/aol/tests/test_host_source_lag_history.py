"""Host source loss and loop-lag lifecycle regression coverage."""
from contextlib import ExitStack
from dataclasses import replace
from unittest import mock

import pytest
from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE
from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings
from openpilot.starpilot.aol.wire import decode_safety, encode_safety, decode_intent, encode_intent


FAULTS = ['current_mismatch', 'current_user', 'current_steer_temp',
          'prior_mismatch', 'prior_user', 'prior_steer_temp', 'authority_lost',
          'native_lat_denied', 'inventory_changed', 'dm_lockout', 'cp_changed', 'session_changed',
          'prior_desired_lat', 'prior_desired_long', 'prior_ack', 'fault_event_zero',
          'unpublished_critical', 'physical_brake', 'physical_cancel', 'restrictive_burst']


@pytest.mark.parametrize('fault', FAULTS)
def test_prior_real_lag_off_proof_does_not_excuse_fault_or_forged_marker(fault):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, _, _ = case._ioniq_availability_callers(full_op=False)
    drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings('lateral_only', BASE, 3))
    source = BASE + 10_000_000
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, state, _ = drive(3, state_stamp=source, **settings('lateral_only', source, 4))
      # A genuine independent AOL-only lag still publishes critical/OFF;
      # ordinary fresh active proofs now follow the existing SOFT lifecycle.
      assert not state.enabled and not state.active
      assert str(axis.faultReason) == 'critical' and not sd.aol_authority_lost
      assert not axis.desiredLateral and not axis.desiredLongitudinal and not axis.nativeAcknowledged
      assert sd.aol_published_fault_reason == 'critical' and sd.aol_fault_event_ns > 0
      prior_published = sd.aol_published_fault_proof
      assert prior_published[:4] == (sd.aol_session_id, 'critical', sd.aol_fault_event_ns, tuple(sd.events_prev))
      assert not any(prior_published[4:])
      original_events = sd.update_events
      def events(cs):
        result = original_events(cs)
        event_map = {'mismatch': log.OnroadEvent.EventName.controlsMismatch,
                     'user': log.OnroadEvent.EventName.pedalPressed,
                     'steer_temp': log.OnroadEvent.EventName.steerTempUnavailable}
        if fault.startswith('current_'):
          sd.events.add(event_map[fault[len('current_'):]])
        elif fault.startswith('prior_') and fault[len('prior_'):] in event_map:
          sd.events_prev.append(event_map[fault[len('prior_'):]])
        elif fault == 'authority_lost':
          sd.aol_authority_lost = True
        elif fault == 'dm_lockout':
          dm = messaging.new_message('driverMonitoringState', valid=True, logMonoTime=now)
          dm.driverMonitoringState.lockout = True
          sd.sm.update_msgs(now / 1e9, [dm.as_reader()])
        elif fault == 'inventory_changed':
          wire = decode_safety(sd.sm['aolSafetyWire'])
          slots = tuple(replace(slot, hardwareSerial='changed-panda') for slot in wire.pandaInventory)
          wire = replace(wire, pandaSerial='changed-panda', pandaInventory=slots)
          message = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=now)
          message.aolSafetyWire = encode_safety(wire)
          sd.sm.update_msgs(now / 1e9, [message.as_reader()])
        elif fault == 'cp_changed':
          changed = sd.CP.as_builder()
          changed.safetyConfigs[-1].safetyParam ^= 1
          sd.CP = changed.as_reader()
        elif fault == 'session_changed':
          sd.aol_session_id = 'changed-axis-session'
        elif fault in ('prior_desired_lat', 'prior_desired_long', 'prior_ack'):
          field = {'prior_desired_lat': 4, 'prior_desired_long': 5, 'prior_ack': 8}[fault]
          changed = list(prior_published)
          changed[field] = True
          sd.aol_published_fault_proof = tuple(changed)
        elif fault == 'fault_event_zero':
          sd.aol_fault_event_ns = 0
        elif fault == 'unpublished_critical':
          sd.aol_published_fault_reason = 'none'
        return result
      now = BASE + 55_399_000
      options = settings('lateral_only', source, 4)
      if fault == 'native_lat_denied':
        options.update(native_request_lat=True, allowed=False)
      observed = fixture.car_state()
      if fault == 'physical_brake':
        observed.brakePressed = True
      if fault == 'physical_cancel':
        observed.buttonEvents = [fixture.car.CarState.ButtonEvent(type=fixture.car.CarState.ButtonEvent.Type.cancel, pressed=True)]
      if fault == 'restrictive_burst':
        queue = []
        for index, pause in enumerate((True, False)):
          stamp = BASE + 29_000_000 + index * 1_000_000
          message = settings('lateral_only', stamp, 5 + index)['intent_message']
          message.aolIntentWire = encode_intent(replace(decode_intent(message.aolIntentWire), pauseLongitudinal=pause))
          queue.append(message.as_reader())
        original_receive = messaging.recv_one_or_none
        def receive(sock):
          if sock is sd.aol_intent_companion.sock:
            return queue.pop(0) if queue else None
          return original_receive(sock)
        cleanup.enter_context(mock.patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none', side_effect=receive))
      with mock.patch.object(sd, 'update_events', side_effect=events):
        axis, state, command = drive(7, timeout=fault not in ('physical_brake', 'physical_cancel'),
          state_stamp=source, offset_ns=5_399_000, observed_state=observed, **options)
      assert not axis.lateralActive and not axis.longitudinalActive
      assert not command.latActive and not command.longActive
      assert not sd.aol_ordinary_source_pause
      assert not state.enabled
      if fault == 'restrictive_burst':
        assert sd.aol_step_intent_drain_count == 2
        assert any(value.pauseLongitudinal for value, _, _ in sd.aol_intent_companion.raw_projections.values())


@pytest.mark.parametrize('mode', ['long_only', 'combined', 'combined_unarmed'])
def test_real_host_lag_countdown_then_fresh_source_does_not_auto_enable(mode):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, _, _ = case._ioniq_availability_callers(full_op=True)
    old, _, _ = drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings(mode, BASE, 3))
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, state, command = drive(5, timeout=True, offset_ns=5_399_000, **settings(mode, BASE, 3))
      assert state.enabled and sd.state_machine.soft_disable_timer == 300
      for tick in range(6, 307):
        axis, state, command = drive(tick, timeout=True, **settings(mode, BASE, 3))
        assert not axis.lateralActive and not axis.longitudinalActive
        assert not command.latActive and not command.longActive
        assert old.validUntilMonoTime < axis.observedMonoTime
      assert not state.enabled and not state.active and sd.state_machine.soft_disable_timer == 0
    fresh = BASE + 3_060_000_000
    axis, state, command = drive(308, state_stamp=fresh, **settings(mode, fresh, 4))
    assert not state.enabled and not state.active
    assert not axis.longitudinalActive and not command.longActive
    assert not sd.events.contains(fixture.ET.ENABLE)
    assert old.validUntilMonoTime < axis.observedMonoTime
