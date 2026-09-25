from contextlib import ExitStack
from dataclasses import replace

import pytest
from openpilot.cereal import messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE, intent
from openpilot.starpilot.aol.wire import decode_safety, encode_safety


@pytest.mark.parametrize('condition', ['healthy', 'native_denial', 'native_invalid', 'native_expired',
                                      'inventory', 'epoch', 'hard_event', 'mismatched_event', 'stale_off_proof'])
def test_verified_intent_continuation_past_old_source_bound_has_current_vetoes(condition):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=True)
    original, _, _ = drive(2, state_stamp=BASE, offset_ns=4_497_535, intent_message=intent(BASE, 3))
    assert receive(BASE+4_497_535, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    original_deadline = original.validUntilMonoTime
    axis, _, command = drive(5, timeout=True, offset_ns=5_399_000, intent_message=intent(BASE, 3))
    assert axis.sourceCarStateMonoTime == 0 and not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    assert receive(BASE+35_399_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    feedback = card.aol_transport_feedback
    assert feedback.retention_verified
    baseline = (feedback.lateral_source_ns, feedback.lateral_baseline_ns)
    # Continue with fresh OFF proofs and native grants, beyond the ORIGINAL
    # source/command lifetime, while ordinary StateMachine remains responsible.
    for tick in range(6, 31):
      axis, _, command = drive(tick, timeout=True, intent_message=intent(BASE, 3))
      if tick < 30:
        assert receive(10_000_000_000+tick*10_000_000,
          axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    now = 10_300_000_000
    assert now > baseline[0]+200_000_000 and now > original_deadline
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    proof = sd.pm.messages['aolAxisState'].as_builder()
    event = sd.pm.messages['onroadEvents'].as_builder()
    if condition in ('native_denial', 'native_expired', 'inventory', 'native_invalid'):
      native = decode_safety(sd.sm['aolSafetyWire'])
      if condition == 'native_denial':
        native = replace(native, lateralAllowed=False)
      elif condition == 'native_expired':
        native = replace(native, observedMonoTime=now-200_000_001, validUntilMonoTime=now-1)
      elif condition == 'inventory':
        native = replace(native, pandaSerial='other-native',
          pandaInventory=tuple(replace(slot, hardwareSerial='other-native') for slot in native.pandaInventory))
      message = messaging.new_message('aolSafetyWire', 0, valid=condition != 'native_invalid',
                                      logMonoTime=native.observedMonoTime)
      message.aolSafetyWire = encode_safety(native)
      sd.sm.update_msgs(now/1e9, [message.as_reader()])
    elif condition == 'epoch':
      proof.aolAxisState.intentIntegrityEpoch += 1
    elif condition == 'hard_event':
      event = messaging.new_message('onroadEvents', 1, valid=True, logMonoTime=proof.aolAxisState.faultEventMonoTime)
      event.onroadEvents[0].name = 'controlsMismatch'
      event.onroadEvents[0].immediateDisable = True
    elif condition == 'mismatched_event':
      # A new event whose prior unmatched join already exceeded its immutable
      # 30ms bound cannot inherit the continuing verified episode indefinitely.
      event.logMonoTime = proof.aolAxisState.faultEventMonoTime+1
      assert receive(now, axis=proof.as_reader(), event=event.as_reader())
      join_start = feedback.retention_started_ns
      assert join_start == now
      now += 30_000_001
      # Keep the OFF proof itself fresh, so failure isolates the prior join
      # bound instead of accidentally retesting ordinary proof expiry.
      proof.logMonoTime = proof.aolAxisState.observedMonoTime = now
      proof.aolAxisState.validUntilMonoTime = now+30_000_000
      proof.aolAxisState.sequence += 1
    elif condition == 'stale_off_proof':
      now = proof.aolAxisState.validUntilMonoTime+1
    latched = receive(now, axis=proof.as_reader(), event=event.as_reader())
    assert latched == (condition == 'healthy')
    assert card.aol_card_intent.allowed_latch == (condition == 'healthy')
    if condition == 'healthy':
      assert baseline == (feedback.lateral_source_ns, feedback.lateral_baseline_ns)
      assert original.validUntilMonoTime == original_deadline
