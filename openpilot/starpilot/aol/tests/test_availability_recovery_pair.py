from contextlib import ExitStack
from dataclasses import replace

import pytest

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.structs import car
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.wire import decode_safety, encode_safety


@pytest.mark.parametrize('full_op', [False, True])
@pytest.mark.parametrize('order', ['axis_first', 'event_first', 'together'])
def test_verified_availability_pause_split_healthy_recovery(full_op, order):
  _exercise_recovery(full_op, order, 'healthy')


@pytest.mark.parametrize('order', ['axis_first', 'event_first'])
@pytest.mark.parametrize('fault', ['source_zero', 'producer', 'epoch', 'event_mismatch', 'critical_event',
                                   'user_disable', 'native_wait', 'native_denial', 'cancel'])
def test_split_recovery_preserves_denial_and_provenance_checks(order, fault):
  _exercise_recovery(False, order, fault)


def _exercise_recovery(full_op, order, fault):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, card, receive = case._ioniq_availability_callers(full_op=full_op)
      paused, state, command = step(2, car_output_valid=False, gas=True)
      assert str(paused.faultReason) == 'availabilityPause'
      assert not state.enabled and not command.latActive and not command.longActive
      assert receive(10_020_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'],
                     state=sd.CS_prev.as_builder())
      assert card.aol_transport_feedback.retention_verified
      recovered, state, command = step(3, gas=True, native_request_long=False)
      assert recovered.lateralActive and command.latActive and str(recovered.faultReason) == 'none'
      assert not state.enabled and not command.longActive and not recovered.longitudinalActive
      original_proof = sd.pm.messages['aolAxisState']
      proof = original_proof.as_builder()
      event = sd.pm.messages['onroadEvents'].as_builder()
      if fault == 'source_zero':
        proof.aolAxisState.sourceCarStateMonoTime = 0
      elif fault == 'producer':
        proof.aolAxisState.intentProducerSessionId = 'replacement-card'
      elif fault == 'epoch':
        proof.aolAxisState.intentIntegrityEpoch += 1
      elif fault == 'event_mismatch':
        proof.aolAxisState.faultEventMonoTime -= 1
      elif fault in ('critical_event', 'user_disable'):
        event = messaging.new_message('onroadEvents', 1, valid=True, logMonoTime=event.logMonoTime)
        event.onroadEvents[0].name = log.OnroadEvent.EventName.buttonCancel if fault == 'user_disable' else log.OnroadEvent.EventName.canError
        event.onroadEvents[0].userDisable = fault == 'user_disable'
        event.onroadEvents[0].immediateDisable = fault == 'critical_event'
      axis_fault = fault in ('source_zero', 'producer', 'epoch', 'event_mismatch')
      if axis_fault:
        proof.aolAxisState.sequence += 1
      proof, event = proof.as_reader(), event.as_reader()
      keys = ['axis', 'event'] if order == 'axis_first' else ['event', 'axis'] if order == 'event_first' else ['both']
      for index, key in enumerate(keys):
        now = 10_030_000_000 + index * 1_000_000
        observed = sd.CS_prev.as_builder()
        if index == len(keys) - 1:
          if fault == 'cancel':
            observed.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
          elif fault in ('native_wait', 'native_denial'):
            native = decode_safety(sd.sm['aolSafetyWire'])
            denied = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=now)
            denied.aolSafetyWire = encode_safety(replace(native, observedMonoTime=now,
              validUntilMonoTime=now + 200_000_000, requestedLateral=fault == 'native_denial', lateralAllowed=False))
            sd.sm.update_msgs(now / 1e9, [denied.as_reader()])
        selected_proof = original_proof if axis_fault and index == 0 else proof
        frames = {'axis': selected_proof, 'event': event} if key == 'both' else {key: selected_proof if key == 'axis' else event}
        if axis_fault and order == 'axis_first' and index == 1:
          frames['axis'] = proof
        latch = receive(now, **frames, state=observed)
        if fault == 'healthy':
          assert latch
          if key != 'both' and index == 0:
            assert card.aol_transport_feedback.retention_started_ns == now
            assert card.aol_transport_feedback.retention_pending
      assert latch == (fault == 'healthy')
      if fault == 'healthy':
        feedback = card.aol_transport_feedback
        assert not feedback.failed and not feedback.retention_started_ns and not feedback.retention_pending
        assert receive(10_032_000_000, axis=proof, event=event, state=sd.CS_prev.as_builder())
        # The recovery join only preserves existing intent. Ordinary control
        # remains disabled and LONG cannot be restored by later healthy input.
        final, final_state, final_command = step(4, gas=True, native_request_long=False)
        assert final.lateralActive and final_command.latActive
        assert not final_state.enabled and not final.longitudinalActive and not final_command.longActive
