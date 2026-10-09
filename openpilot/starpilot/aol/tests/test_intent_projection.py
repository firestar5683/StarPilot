"""Real HKG callers with a controlled older SubMaster intent projection."""
from contextlib import ExitStack

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
