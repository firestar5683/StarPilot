"""Bounded event-first stock lag join retains no output authority."""

from dataclasses import replace
from unittest import mock
import pytest
from openpilot.cereal import messaging
from openpilot.starpilot.aol.wire import decode_safety, encode_safety
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE
from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings
from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import stock_family
from openpilot.starpilot.aol.tests.test_stock_lateral_pcm import receive_pair


@pytest.mark.parametrize('fault', ['hard', 'other_user', 'producer', 'epoch', 'late', 'missing', 'duplicates', 'native_denied', 'inventory'])
def test_matched_critical_event_first_cannot_extend_or_replace_owner(fault):
  with stock_family('toyota') as (sd, controls, drive, card, receive):
    old, _, _ = drive(2, state_stamp=BASE, **settings('lateral_only', BASE, 3))
    assert old.lateralActive and receive(BASE)
    feedback = card.aol_transport_feedback
    first, now = BASE + 10_000_000, BASE + 45_399_000
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      lag, _, _ = drive(3, state_stamp=first, **settings('lateral_only', first, 4))
      assert str(lag.faultReason) == 'critical' and receive(first) and not feedback.failed
      original = (
        feedback.lateral_source_ns,
        feedback.lateral_baseline_ns,
        feedback.lateral_native_ns,
        feedback.healthy_native_ns,
        feedback.healthy_feedback_ns,
      )
      paused, _, command = drive(6, timeout=True, state_stamp=first, offset_ns=5_399_000, **settings('lateral_only', first, 4))
      assert str(paused.faultReason) == 'availabilityPause' and paused.sourceCarStateMonoTime == 0
      proof, event = sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents']
      assert receive_pair(sd, controls, card, now, event=event)
      assert not feedback.failed and feedback.retention_pending and not feedback.retention_verified
      assert feedback.retention_started_ns == now and feedback.retention_event_ns == event.logMonoTime
      assert (
        feedback.lateral_source_ns,
        feedback.lateral_baseline_ns,
        feedback.lateral_native_ns,
        feedback.healthy_native_ns,
        feedback.healthy_feedback_ns,
      ) == original
      if fault in ('hard', 'other_user'):
        bad = messaging.new_message('onroadEvents', 3, valid=True, logMonoTime=event.logMonoTime)
        bad.onroadEvents[0].name = 'pcmDisable'
        bad.onroadEvents[0].userDisable = True
        bad.onroadEvents[1].name = 'commIssue'
        bad.onroadEvents[1].softDisable = True
        bad.onroadEvents[2].name = 'controlsMismatch' if fault == 'hard' else 'buttonCancel'
        bad.onroadEvents[2].immediateDisable = fault == 'hard'
        bad.onroadEvents[2].userDisable = fault == 'other_user'
        receive_pair(sd, controls, card, now + 1_000_000, event=bad.as_reader())
      elif fault in ('producer', 'epoch'):
        bad = proof.as_builder()
        if fault == 'producer':
          bad.aolAxisState.intentProducerSessionId = 'other-producer'
        else:
          bad.aolAxisState.intentIntegrityEpoch += 1
        receive_pair(sd, controls, card, now + 1_000_000, axis=bad.as_reader())
      elif fault in ('native_denied', 'inventory'):
        native = decode_safety(sd.sm['aolSafetyWire'])
        if fault == 'native_denied':
          native = replace(native, lateralAllowed=False)
        else:
          inventory = tuple(replace(slot, hardwareSerial='other-panda') for slot in native.pandaInventory)
          native = replace(native, pandaSerial='other-panda', pandaInventory=inventory)
        packet = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=native.observedMonoTime)
        packet.aolSafetyWire = encode_safety(native)
        sd.sm.update_msgs(now / 1e9, [packet.as_reader()])
        receive_pair(sd, controls, card, now + 1_000_000, axis=proof)
      else:
        if fault == 'duplicates':
          for delta in (10_000_000, 20_000_000):
            assert receive_pair(sd, controls, card, now + delta, event=event)
            assert not feedback.failed and feedback.retention_started_ns == now
            assert (
              feedback.lateral_source_ns,
              feedback.lateral_baseline_ns,
              feedback.lateral_native_ns,
              feedback.healthy_native_ns,
              feedback.healthy_feedback_ns,
            ) == original
        late = now + 30_000_001
        if fault == 'late':
          new, _, command = drive(9, timeout=True, state_stamp=first, offset_ns=5_399_001, **settings('lateral_only', first, 4))
          assert new.observedMonoTime == late and new.validUntilMonoTime > late
          assert new.faultEventMonoTime == event.logMonoTime and not command.latActive and not command.longActive
          receive_pair(sd, controls, card, late, axis=sd.pm.messages['aolAxisState'])
        else:
          receive_pair(sd, controls, card, late, event=event)
      assert feedback.failed and not feedback.retention_verified
      assert (
        feedback.lateral_source_ns,
        feedback.lateral_baseline_ns,
        feedback.lateral_native_ns,
        feedback.healthy_native_ns,
        feedback.healthy_feedback_ns,
      ) == original
      assert old.validUntilMonoTime == BASE + 30_000_000 and not sd.events.contains('enable')
      with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=now + 30_000_001):
        expired, _ = controls.state_control()
      assert not expired.latActive and not expired.longActive
