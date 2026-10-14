"""Real HKG callers with a controlled older SubMaster intent projection."""
from contextlib import ExitStack
from unittest.mock import Mock, patch

import pytest

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.runtime import current_intent
from openpilot.starpilot.aol.wire import IntentState, encode_intent


def intent_receive(sd, **kwargs):
  original_receive = messaging.recv_one_or_none
  intent_sock = sd.aol_intent_companion.sock
  receive_intent = Mock(**kwargs)

  def receive(sock):
    return receive_intent(sock) if sock is intent_sock else original_receive(sock)

  return patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none', side_effect=receive)


def test_actual_hkg_known_older_sm_and_raw_pair_preserve_current_axes_and_card_latch():
  from openpilot.starpilot.aol.tests.test_runtime import IpcAxisContractTests
  case = IpcAxisContractTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    # Deterministically force the possible receive order; route logs do not
    # record which intent the consumer actually read at the warning boundary.
    prior, source, latest, now = 1_081_445_990_726, 1_081_451_053_291, 1_081_455_731_297, 1_081_457_492_005
    with OpenpilotPrefix():
      pm = messaging.PubMaster(['aolIntentWire'])
      sd, controls, step, card, feedback = case._transport_callers()
      axis, _, command = step(0, offset_ns=prior - 10_000_000_000)
      case.assertTrue(axis.lateralActive and axis.longitudinalActive and command.latActive and command.longActive)
      feedback(prior, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      old = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=prior)
      old.aolIntentWire = encode_intent(sd.aol_last_intent)
      for stamp, sequence in ((source, 2), (latest, 3)):
        message = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=stamp)
        message.aolIntentWire = encode_intent(IntentState('authority-card', sequence, stamp, stamp,
          stamp + 200_000_000, True, False, False, True, True))
        pm.send('aolIntentWire', message)
      axis, state, command = step(1, state_stamp=source, intent_message=old,
        offset_ns=now - 10_010_000_000)
      case.assertEqual(sd.sm.logMonoTime['aolIntentWire'], prior)
      case.assertEqual(axis.sourceCarStateMonoTime, source)
      case.assertEqual(sd.aol_last_intent.carStateLogMonoTime, source)
      case.assertEqual(sd.aol_last_intent.observedMonoTime, source)
      case.assertEqual(sd.aol_last_intent.validUntilMonoTime, source + 200_000_000)
      case.assertTrue(axis.nativeAcknowledged and axis.lateralActive and axis.longitudinalActive)
      case.assertTrue(command.latActive and command.longActive and sd.enabled)
      case.assertFalse(sd.aol_authority_lost)
      case.assertNotIn(log.OnroadEvent.EventName.controlsMismatch, sd.events.names)
      case.assertNotEqual(state.alertText1, 'TAKE CONTROL IMMEDIATELY')
      case.assertFalse(feedback(now, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']))
      case.assertTrue(card.aol_card_intent.allowed_latch)
      case.assertFalse(current_intent(sd.sm, car_state_ns=source, now_ns=source + 30_000_001,
        companion=sd.aol_intent_companion))


@pytest.mark.parametrize('projection', ['C', 'A', 'B'])
@pytest.mark.parametrize('hard_guard', ['source_expired', 'native_invalid', 'native_deny', 'critical_event'])
def test_actual_hkg_verified_aged_sm_projection_preserves_current_axes_then_hard_guards(projection, hard_guard):
  from openpilot.starpilot.aol.tests.test_runtime import IpcAxisContractTests

  case = IpcAxisContractTests(methodName='runTest')
  c, a, b, before, now = 341_047_855_007, 341_055_154_287, 341_083_039_471, 341_059_508_728, 341_084_947_345
  def message(stamp, sequence):
    event = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=stamp)
    event.aolIntentWire = encode_intent(IntentState('authority-card', sequence, stamp, stamp,
      stamp + 200_000_000, True, False, False, True, True))
    return event
  old, source, latest = message(c, 1), message(a, 2), message(b, 3)
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, card, feedback = case._transport_callers()
      with intent_receive(sd, side_effect=[old.as_reader(), source.as_reader(), None]):
        axis, _, command = step(0, state_stamp=c, intent_message=old, offset_ns=before - 10_000_000_000)
      case.assertTrue(axis.lateralActive and axis.longitudinalActive and command.latActive and command.longActive)
      feedback(before, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      epoch = sd.aol_intent_companion.integrity_epoch
      selected = {'C': old, 'A': source, 'B': latest}[projection]
      with intent_receive(sd, side_effect=[latest.as_reader(), None]):
        axis, state, command = step(1, state_stamp=a, intent_message=selected, offset_ns=now - 10_010_000_000)
      case.assertTrue(axis.nativeAcknowledged and axis.lateralActive and axis.longitudinalActive)
      case.assertTrue(command.latActive and command.longActive and sd.enabled)
      case.assertFalse(sd.aol_authority_lost)
      case.assertEqual(sd.aol_intent_companion.integrity_epoch, epoch)
      case.assertEqual(sd.aol_last_intent.carStateLogMonoTime, a)
      case.assertNotIn(c, sd.aol_intent_companion.samples)
      case.assertNotIn(log.OnroadEvent.EventName.controlsMismatch, sd.events.names)
      case.assertNotEqual(state.alertText1, 'TAKE CONTROL IMMEDIATELY')
      case.assertFalse(feedback(now, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']))
      case.assertTrue(card.aol_card_intent.allowed_latch)
      with intent_receive(sd, return_value=None):
        repeated, _, repeated_command = step(2, state_stamp=a, intent_message=selected, offset_ns=now + 1 - 10_020_000_000)
      case.assertTrue(repeated.lateralActive and repeated.longitudinalActive and repeated_command.latActive and repeated_command.longActive)
      case.assertFalse(sd.aol_authority_lost)
      case.assertEqual(sd.aol_intent_companion.integrity_epoch, epoch)
      kwargs = ({'native_valid': False} if hard_guard == 'native_invalid' else
                {'allowed': False} if hard_guard == 'native_deny' else
                {'critical_event': log.OnroadEvent.EventName.controlsMismatch} if hard_guard == 'critical_event' else {})
      failed_at = a + 30_000_001 if hard_guard == 'source_expired' else now + 2
      with intent_receive(sd, return_value=None):
        axis, _, command = step(3, state_stamp=a, intent_message=selected, offset_ns=failed_at - 10_030_000_000, **kwargs)
      if hard_guard == 'source_expired':
        case.assertEqual(axis.sourceCarStateMonoTime, 0)
        case.assertEqual(str(axis.faultReason), 'transportPause')
        case.assertFalse(sd.enabled or sd.active or axis.lateralActive or axis.longitudinalActive or command.latActive or command.longActive)
        case.assertFalse(sd.aol_authority_lost)
        case.assertFalse(feedback(failed_at, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']))
        case.assertTrue(card.aol_card_intent.allowed_latch)
        recovered_at = failed_at + 10_000_000
        axis, _, command = step(4, offset_ns=recovered_at - 10_040_000_000, native_request_long=True)
        case.assertEqual(axis.sourceCarStateMonoTime, recovered_at)
        case.assertEqual(str(axis.faultReason), 'none')
        case.assertTrue(axis.lateralActive and command.latActive)
        case.assertFalse(sd.enabled or sd.active or axis.longitudinalActive or command.longActive)
        case.assertFalse(sd.aol_authority_lost)
        case.assertFalse(feedback(recovered_at, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']))
        case.assertTrue(card.aol_card_intent.allowed_latch)
      else:
        case.assertEqual(str(axis.faultReason), 'critical')
        case.assertFalse(axis.lateralActive or axis.longitudinalActive or command.latActive or command.longActive)
        # The global event disables current output, but a healthy source/native
        # does not create the separate sticky companion/native authority loss.
        case.assertEqual(sd.aol_authority_lost, hard_guard != 'critical_event')
        case.assertTrue(feedback(failed_at, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']))
        case.assertFalse(card.aol_card_intent.allowed_latch)


@pytest.mark.parametrize('guard', ['healthy', 'latest_deny', 'latest_pause', 'future',
                                 'native_invalid', 'native_deny', 'source_expired', 'overrun'])
def test_actual_hkg_drain_precedes_shared_decision_clock(guard):
  from openpilot.selfdrive.selfdrived import selfdrived as sd_module
  from openpilot.starpilot.aol.intent_companion import MAX_DRAIN
  from openpilot.starpilot.aol.tests.test_runtime import IpcAxisContractTests

  case = IpcAxisContractTests(methodName='runTest')
  a = 10_000_000_000
  before, after = a + 25_000_000, a + 28_000_000
  original = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=a)
  original.aolIntentWire = encode_intent(IntentState('authority-card', 1, a, a,
    a + 200_000_000, True, False, False, True, True))
  b = after + 1 if guard == 'future' else a + 26_000_000
  latest_value = IntentState('authority-card', 2, b, b, b + 200_000_000,
                            guard != 'latest_deny', guard == 'latest_pause', False, True, True)
  latest = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=b)
  latest.aolIntentWire = encode_intent(latest_value)
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, card, feedback = case._transport_callers()
      with intent_receive(sd, return_value=None):
        axis, _, command = step(0, intent_message=original)
      assert axis.lateralActive and command.latActive
      assert not feedback(a, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      calls = []
      def receive(_sock):
        calls.append(1)
        # The actual SD decision clock changes while its queued read executes.
        sd_module.time.monotonic_ns.return_value = a + 30_000_001 if guard == 'source_expired' else after
        return latest.as_reader() if len(calls) == 1 or guard == 'overrun' else None
      kwargs = {'native_valid': False} if guard == 'native_invalid' else {'allowed': False} if guard == 'native_deny' else {}
      with intent_receive(sd, side_effect=receive):
        axis, state, command = step(1, state_stamp=a, intent_message=original,
                                    offset_ns=before - 10_010_000_000, **kwargs)
      assert len(calls) == (MAX_DRAIN if guard == 'overrun' else 2)
      if guard == 'healthy':
        assert axis.sourceCarStateMonoTime == a
        assert sd.aol_last_intent.observedMonoTime == a
        assert sd.aol_last_intent.validUntilMonoTime == a + 200_000_000
        assert axis.nativeAcknowledged and axis.lateralActive and command.latActive
        assert not sd.aol_authority_lost
        assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
        assert state.alertText1 != 'TAKE CONTROL IMMEDIATELY'
        assert not feedback(after, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
        assert card.aol_card_intent.allowed_latch
      elif guard == 'latest_deny':
        # Ordinary enabled control remains valid; the persistent AOL latch veto is folded.
        assert sd.aol_last_intent.allowedLatch is False
        assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
      else:
        assert not axis.lateralActive and not command.latActive
        if guard == 'source_expired':
          assert axis.sourceCarStateMonoTime == 0
          assert str(axis.faultReason) == 'transportPause'
          assert not sd.enabled and not sd.active and not axis.longitudinalActive and not command.longActive
          assert not sd.aol_authority_lost
          publication_ns = int(sd.pm.messages['aolAxisState'].logMonoTime)
          assert publication_ns == a + 30_000_001
          assert not feedback(publication_ns, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
          assert card.aol_card_intent.allowed_latch
        elif guard in ('future', 'native_invalid', 'native_deny', 'overrun'):
          assert str(axis.faultReason) == 'critical'
          assert log.OnroadEvent.EventName.controlsMismatch in sd.events.names
          assert feedback(after, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
          assert not card.aol_card_intent.allowed_latch




@pytest.mark.parametrize('guard', [
  'none', 'unknown', 'mutated', 'invalid', 'future', 'cache_expired', 'pair_expired', 'latest_invalid', 'future_observed',
])
def test_raw_observed_projection_restricts_without_renewing_authority(guard):
  from types import SimpleNamespace
  from openpilot.starpilot.aol.intent_companion import IntentCompanion

  old_ns = 10_000_000_000
  source_ns = old_ns + (201_000_000 if guard == 'cache_expired' else 50_000_000)
  now_ns = source_ns + (31_000_000 if guard == 'pair_expired' else 1_000_000)

  def message(stamp, sequence, *, paused=False, valid=True):
    event = messaging.new_message('aolIntentWire', 0, valid=valid, logMonoTime=stamp)
    event.aolIntentWire = encode_intent(IntentState('raw-card', sequence, stamp, stamp,
      stamp + 200_000_000, True, paused, False, True, True))
    return event

  old = message(old_ns, 1, paused=True)
  if guard == 'future_observed':
    old.aolIntentWire = encode_intent(IntentState('raw-card', 1, old_ns, now_ns + 1,
      now_ns + 200_000_000, True, True, False, True, True))
  companion = IntentCompanion(object())
  class ProjectionSource(SimpleNamespace):
    def __getitem__(self, name):
      return self.payload

  sm = ProjectionSource(seen={'aolIntentWire': False}, valid={'aolIntentWire': True},
    alive={'aolIntentWire': True}, logMonoTime={'aolIntentWire': old_ns})
  sm.payload = old.aolIntentWire
  with patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none',
             side_effect=[None] if guard == 'unknown' else [old, None]):
    assert companion.current(sm, source_ns=0, now_ns=old_ns + 1_000_000) is None
  assert companion.verified_sm_projection is None
  sm.seen['aolIntentWire'] = True
  if guard == 'mutated':
    sm.payload = message(old_ns, 1).aolIntentWire
  elif guard == 'invalid':
    sm.valid['aolIntentWire'] = False
  elif guard == 'future':
    future = message(now_ns + 1, 4)
    sm.logMonoTime['aolIntentWire'], sm.payload = now_ns + 1, future.aolIntentWire
  source = message(source_ns, 2)
  latest = message(now_ns, 3, valid=guard != 'latest_invalid')
  with patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none', side_effect=[source, latest, None]):
    result = companion.current(sm, source_ns=source_ns, now_ns=now_ns)
  if guard == 'none':
    assert result is not None and result.allowedLatch and result.pauseLateral
    assert result.carStateLogMonoTime == source_ns
    assert result.observedMonoTime == source_ns
    assert result.validUntilMonoTime == source_ns + 200_000_000
    assert companion.integrity_epoch == 0
    assert companion.raw_projections[old_ns][0].pauseLateral
    assert old_ns not in companion.samples
  else:
    assert result is None


@pytest.mark.parametrize('fault', ['native_invalid', 'native_deny', 'critical_event'])
def test_actual_hkg_raw_known_unaccepted_sm_projection_preserves_full_axes_then_denies_fault(fault):
  from openpilot.starpilot.aol.runtime import current_axis
  from openpilot.starpilot.aol.tests.test_runtime import IpcAxisContractTests

  case = IpcAxisContractTests(methodName='runTest')
  c = 10_030_000_000
  a, b, now = c + 7_299_280, c + 35_184_464, c + 37_092_338

  def message(stamp, sequence):
    event = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=stamp)
    event.aolIntentWire = encode_intent(IntentState('authority-card', sequence, stamp, stamp,
      stamp + 200_000_000, True, False, False, True, True))
    return event

  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, controls, step, card, feedback = case._ioniq_availability_callers(full_op=True)
      prior = c - 10_000_000
      axis, _, command = step(2)
      case.assertEqual(card.CP.to_dict(), sd.CP.to_dict())
      from openpilot.starpilot.aol.wire import decode_safety
      native = decode_safety(sd.sm['aolSafetyWire'])
      assert native is not None
      case.assertTrue(native.pandaInventory)
      case.assertTrue(axis.lateralActive and axis.longitudinalActive and command.latActive and command.longActive)
      feedback(prior, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      # Keep the established output continuous while its unchanged source is fresh.
      with patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=c + 10_000_000):
        sd.publish_axis_proof(sd.CS_prev)
      feedback(c + 10_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      old, source, latest = message(c, 4), message(a, 5), message(b, 6)
      with intent_receive(sd, side_effect=[old.as_reader(), None]):
        case.assertTrue(sd.aol_intent_companion.drain())
      # C was observed on the original socket, but never admitted as an SM triple.
      case.assertNotEqual(sd.aol_intent_companion.verified_sm_projection[0], c)
      epoch = sd.aol_intent_companion.integrity_epoch
      with intent_receive(sd, side_effect=[source.as_reader(), latest.as_reader(), None]):
        axis, state, command = step(3, state_stamp=a, intent_message=old, offset_ns=now - 10_030_000_000)
      case.assertTrue(axis.nativeAcknowledged and axis.lateralActive and axis.longitudinalActive)
      case.assertTrue(command.latActive and command.longActive and sd.enabled)
      case.assertEqual(axis.sourceCarStateMonoTime, a)
      case.assertEqual(sd.aol_last_intent.carStateLogMonoTime, a)
      case.assertEqual(sd.aol_intent_companion.integrity_epoch, epoch)
      case.assertNotIn(c, sd.aol_intent_companion.samples)
      case.assertNotIn(log.OnroadEvent.EventName.controlsMismatch, sd.events.names)
      case.assertNotEqual(state.alertText1, 'TAKE CONTROL IMMEDIATELY')
      case.assertTrue(feedback(now, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']))
      case.assertTrue(card.aol_card_intent.allowed_latch)
      expired = int(sd.pm.messages['aolAxisState'].aolAxisState.validUntilMonoTime) + 1
      case.assertIsNone(current_axis(controls.sm, now_ns=expired))
      with patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=expired):
        expired_command, _ = controls.state_control()
      case.assertFalse(expired_command.latActive or expired_command.longActive)
      kwargs = ({'native_valid': False} if fault == 'native_invalid' else
                {'allowed': False} if fault == 'native_deny' else
                {'critical_event': log.OnroadEvent.EventName.controlsMismatch})
      denied_at = expired + 1
      fresh = message(denied_at, 7)
      with intent_receive(sd, side_effect=[fresh.as_reader(), None]):
        denied, _, denied_command = step(4, state_stamp=denied_at, intent_message=fresh,
          offset_ns=denied_at - 10_040_000_000, **kwargs)
      case.assertEqual(str(denied.faultReason), 'critical')
      case.assertFalse(denied.lateralActive or denied.longitudinalActive or
                       denied_command.latActive or denied_command.longActive)
      case.assertFalse(feedback(denied_at, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']))
      case.assertFalse(card.aol_card_intent.allowed_latch)


def test_reduced_owner_subscribes_control_before_receiving_actual_command():
  from openpilot.starpilot.aol.tests.test_runtime import IpcAxisContractTests

  case = IpcAxisContractTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, controls, step, _, _ = case._transport_callers()
      assert 'carControl' in sd.sm.seen
      assert not sd.sm.seen['carControl'] and not sd.sm.valid['carControl']
      assert sd.sm.logMonoTime['carControl'] == 0
      # A subscribed-but-unseen packet cannot establish a held pedal override.
      proof = ('authority-session', 1, 1, 30_000_001, 'authority-card', 0, True, True, True, True)
      assert sd.held_axis_override_wait(sd.CS_prev, proof, 2) == (False, False)
      _, _, command = step(0)
      published = controls.pm.messages['carControl']
      assert not sd.sm.seen['carControl']
      step(1)
      assert sd.sm.seen['carControl'] and sd.sm.valid['carControl']
      assert sd.sm.logMonoTime['carControl'] == published.logMonoTime
      assert sd.sm['carControl'].to_dict() == published.carControl.to_dict()
      assert (sd.sm['carControl'].enabled, sd.sm['carControl'].latActive, sd.sm['carControl'].longActive) == (
        command.enabled, command.latActive, command.longActive)
