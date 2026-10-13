"""Native, physical and monitoring faults block source retention."""
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


@pytest.mark.parametrize('phase', ['source_gap', 'publication'])
@pytest.mark.parametrize('fault', ['lat_denied', 'lat_withdrawn', 'native_invalid', 'inventory_changed',
                                  'dm_lockout', 'physical_cancel', 'restrictive_burst', 'producer_changed', 'mixed_hard'])
def test_lat_only_and_first_publication_host_source_retention_refuse_real_veto(phase, fault):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, _, _ = case._ioniq_availability_callers(full_op=False)
    old, state, _ = drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings('lateral_only', BASE, 3))
    assert old.lateralActive and not old.longitudinalActive and not state.enabled
    source = BASE if phase == 'source_gap' else BASE + 40_000_000
    sequence = 3 if phase == 'source_gap' else 4
    now = BASE + 35_399_000 if phase == 'source_gap' else source + 30_001_000
    options = settings('lateral_only', source, sequence)
    if fault in ('lat_denied', 'lat_withdrawn'):
      options.update(native_request_lat=fault != 'lat_withdrawn', allowed=False)
    options['native_valid'] = fault != 'native_invalid'
    observed = fixture.car_state()
    if fault == 'physical_cancel':
      observed.buttonEvents = [fixture.car.CarState.ButtonEvent(type=fixture.car.CarState.ButtonEvent.Type.cancel, pressed=True)]
    queue = []
    if fault in ('restrictive_burst', 'producer_changed'):
      for index in range(2 if fault == 'restrictive_burst' else 1):
        stamp = BASE + 29_000_000 + index * 1_000_000 if phase == 'source_gap' else source + 10_000 + index * 10_000
        message = settings('lateral_only', stamp, sequence + index + 1)['intent_message']
        value = decode_intent(message.aolIntentWire)
        value = replace(value, pauseLongitudinal=index == 0) if fault == 'restrictive_burst' else replace(value, producerSessionId='changed-card')
        message.aolIntentWire = encode_intent(value)
        queue.append(message.as_reader())
      original_receive = messaging.recv_one_or_none
      def receive(sock):
        if sock is sd.aol_intent_companion.sock:
          return queue.pop(0) if queue else None
        return original_receive(sock)
      cleanup.enter_context(mock.patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none', side_effect=receive))
    def inject():
      if fault == 'inventory_changed':
        value = decode_safety(sd.sm['aolSafetyWire'])
        slots = tuple(replace(slot, hardwareSerial='changed-panda') for slot in value.pandaInventory)
        value = replace(value, pandaSerial='changed-panda', pandaInventory=slots)
        message = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=now)
        message.aolSafetyWire = encode_safety(value)
        sd.sm.update_msgs(now / 1e9, [message.as_reader()])
      elif fault == 'dm_lockout':
        dm = messaging.new_message('driverMonitoringState', valid=True, logMonoTime=now)
        dm.driverMonitoringState.lockout = True
        sd.sm.update_msgs(now / 1e9, [dm.as_reader()])
      elif fault == 'mixed_hard':
        sd.events.add(log.OnroadEvent.EventName.controlsMismatch)
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      if phase == 'source_gap':
        original_events = sd.update_events
        def events(cs):
          result = original_events(cs)
          inject()
          return result
        with mock.patch.object(sd, 'update_events', side_effect=events):
          axis, state, command = drive(5, timeout=fault != 'physical_cancel', state_stamp=source,
            offset_ns=5_399_000, observed_state=observed, **options)
      else:
        # The producer/native/physical veto is delivered through the actual
        # fresh sample/transport before any decision; later crossing grants none.
        clock = [source + 29_999_000]
        original_publish = sd.publish_axis_proof
        def publish(cs, **kwargs):
          clock[0] = now
          inject()
          if fault in ('restrictive_burst', 'producer_changed'):
            assert sd.drain_axis_intent(sd.aol_intent_companion)
          return original_publish(cs, **kwargs)
        # Delay raw delivery until AFTER fresh admission, proving the exact
        # publication helper still honors newly received restrictive evidence.
        pending = []
        if fault in ('restrictive_burst', 'producer_changed'):
          pending = queue[:]
          queue.clear()
        def deliver(cs, **kwargs):
          queue.extend(pending)
          return publish(cs, **kwargs)
        with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: clock[0]), \
             mock.patch.object(sd, 'publish_axis_proof', side_effect=deliver):
          axis, state, command = drive(6, state_stamp=source, offset_ns=29_999_000,
                                      observed_state=observed, **options)
    assert not state.enabled and not state.active and not axis.longitudinalActive and not command.longActive
    assert not axis.lateralActive and not command.latActive
    assert not sd.aol_ordinary_source_pause
    assert not sd.events.contains(fixture.ET.ENABLE)
    assert old.validUntilMonoTime < axis.observedMonoTime
    if fault == 'restrictive_burst':
      assert sd.aol_step_intent_drain_count == 2
      assert any(value.pauseLongitudinal for value, _, _ in sd.aol_intent_companion.raw_projections.values())
    if fault == 'producer_changed':
      assert sd.aol_intent_companion.integrity_epoch > 0
