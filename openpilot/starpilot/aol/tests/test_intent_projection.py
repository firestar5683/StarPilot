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


@pytest.mark.parametrize('guard', ['healthy', 'latest_deny', 'latest_pause', 'future',
                                 'native_invalid', 'native_deny', 'source_expired', 'overrun'])
def test_actual_hkg_drain_precedes_shared_decision_clock(guard):
  from unittest.mock import patch
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
      with patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none', return_value=None):
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
      with patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none', side_effect=receive):
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
        if guard in ('future', 'native_invalid', 'native_deny', 'source_expired', 'overrun'):
          assert str(axis.faultReason) == 'critical'
          assert log.OnroadEvent.EventName.controlsMismatch in sd.events.names
          assert feedback(after, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
          assert not card.aol_card_intent.allowed_latch


def test_authority_loss_diagnostic_is_bounded_and_logged_by_params_worker():
  from types import SimpleNamespace
  from openpilot.common.params import Params
  from unittest.mock import Mock, patch
  from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD

  with OpenpilotPrefix():
    sd = SelfdriveD.__new__(SelfdriveD)
    sd.sm = messaging.SubMaster(['aolSafetyWire'])
    sd.sm.logMonoTime['aolSafetyWire'] = 100
    sd.aol_car_state_log_ns = 90
    arguments = {'companion': None, 'drained': False, 'native': None, 'source_current': False,
                 'lost_active': True, 'lost_companion': True, 'lost_permission': False, 'upgraded': False}
    for now in (6_000_000_000, 6_000_000_001, 12_000_000_000, 18_000_000_000):
      sd.record_aol_authority_loss(now_ns=now, **arguments)
    assert len(sd.aol_authority_reports) == 2
    assert [row['decision_ns'] for row in sd.aol_authority_reports] == [12_000_000_000, 18_000_000_000]
    sd.aol_replay = False
    sd.params = Params()
    sd.refresh_saved_driving_mode = Mock()
    evt = SimpleNamespace(is_set=Mock(side_effect=[False, True]))
    with (patch('openpilot.selfdrive.selfdrived.selfdrived.cloudlog.event') as report,
          patch('openpilot.selfdrive.selfdrived.selfdrived.time.sleep')):
      sd.params_thread(evt)
    report.assert_called_once_with('selfdrived.authority_lost', decision_ns=12_000_000_000, source_ns=90,
      intent_snapshot={}, intent_rejection='no_companion', drain_ok=False, drain_count=0,
      source_current=False, source_expired=False, native_present=False, native_message_ns=100,
      native_requested_lateral=False, native_allowed_lateral=False, lost_active=True,
      lost_companion=True, lost_permission=False, pause_upgraded=False)
    assert len(sd.aol_authority_reports) == 1
