"""Real HKG callers with a controlled older SubMaster intent projection."""
from contextlib import ExitStack

import pytest

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.runtime import current_intent
from openpilot.starpilot.aol.wire import IntentState, encode_intent


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
  from unittest.mock import patch
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
      with patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none', side_effect=[old.as_reader(), source.as_reader(), None]):
        axis, _, command = step(0, state_stamp=c, intent_message=old, offset_ns=before - 10_000_000_000)
      case.assertTrue(axis.lateralActive and axis.longitudinalActive and command.latActive and command.longActive)
      feedback(before, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      epoch = sd.aol_intent_companion.integrity_epoch
      selected = {'C': old, 'A': source, 'B': latest}[projection]
      with patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none', side_effect=[latest.as_reader(), None]):
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
      with patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none', return_value=None):
        repeated, _, repeated_command = step(2, state_stamp=a, intent_message=selected, offset_ns=now + 1 - 10_020_000_000)
      case.assertTrue(repeated.lateralActive and repeated.longitudinalActive and repeated_command.latActive and repeated_command.longActive)
      case.assertFalse(sd.aol_authority_lost)
      case.assertEqual(sd.aol_intent_companion.integrity_epoch, epoch)
      kwargs = ({'native_valid': False} if hard_guard == 'native_invalid' else
                {'allowed': False} if hard_guard == 'native_deny' else
                {'critical_event': log.OnroadEvent.EventName.controlsMismatch} if hard_guard == 'critical_event' else {})
      failed_at = a + 30_000_001 if hard_guard == 'source_expired' else now + 2
      with patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none', return_value=None):
        axis, _, command = step(3, state_stamp=a, intent_message=selected, offset_ns=failed_at - 10_030_000_000, **kwargs)
      case.assertEqual(str(axis.faultReason), 'critical')
      case.assertFalse(axis.lateralActive or axis.longitudinalActive or command.latActive or command.longActive)
      # The global event disables current output, but a healthy source/native
      # does not create the separate sticky companion/native authority loss.
      case.assertEqual(sd.aol_authority_lost, hard_guard != 'critical_event')
      case.assertTrue(feedback(failed_at, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']))
      case.assertFalse(card.aol_card_intent.allowed_latch)
