"""Actual Card receipt refusal and completed-publication clock boundaries."""

from dataclasses import replace


from unittest import mock


import pytest


from openpilot.cereal import messaging


from openpilot.starpilot.aol.wire import decode_safety, encode_safety


from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE


from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings


from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import stock_family
from openpilot.starpilot.aol.tests.test_stock_lateral_pcm import receive_pair


@pytest.mark.parametrize(
  'fault', ['unmatched', 'non_lag', 'hard', 'unlatched', 'native_denied', 'inventory', 'producer', 'epoch', 'source_clock', 'ack', 'desired_long']
)
def test_stock_gap_cannot_infer_unaccepted_or_changed_prior_critical(fault):
  with stock_family('toyota') as (sd, controls, drive, card, receive):
    old, _, _ = drive(2, state_stamp=BASE, **settings('lateral_only', BASE, 3))
    assert old.lateralActive and receive(BASE)
    feedback = card.aol_transport_feedback
    origin = (feedback.lateral_source_ns, feedback.lateral_baseline_ns, feedback.lateral_native_ns)
    first, now = BASE + 10_000_000, BASE + 45_399_000
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      lag, _, _ = drive(3, state_stamp=first, **settings('lateral_only', first, 4))
      proof, event = sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents']
      assert str(lag.faultReason) == 'critical' and not lag.nativeAcknowledged
      if fault == 'unmatched':
        receive_pair(sd, controls, card, first, axis=proof)
        assert feedback.pending_event == lag.faultEventMonoTime and feedback.awaiting
      elif fault in ('non_lag', 'hard'):
        bad = messaging.new_message('onroadEvents', 2, valid=True, logMonoTime=event.logMonoTime)
        bad.onroadEvents[0].name = 'pcmDisable'
        bad.onroadEvents[0].userDisable = True
        bad.onroadEvents[1].name = 'commIssue' if fault == 'non_lag' else 'controlsMismatch'
        bad.onroadEvents[1].softDisable = fault == 'non_lag'
        bad.onroadEvents[1].immediateDisable = fault == 'hard'
        receive_pair(sd, controls, card, first, axis=proof, event=bad.as_reader())
        assert feedback.failed and not feedback.lateral_only_baseline
      elif fault == 'unlatched':
        # Actual transport owner sees this receipt while its intent owner is off.
        card.sm.update_msgs(first / 1e9, [proof, event])
        assert feedback.observe(card.sm, card.CP, sd.CS_prev, first, latched=False, intent_producer_session=feedback.availability_producer)
        assert feedback.failed and not feedback.lateral_only_baseline
        assert feedback.signature[5] == 'none'
      else:
        assert receive(first) and not feedback.failed and not feedback.pending_event
        assert feedback.signature[5] == 'critical' and feedback.lateral_only_baseline
      axis, _, command = drive(6, timeout=True, state_stamp=first, offset_ns=5_399_000, **settings('lateral_only', first, 4))
      assert str(axis.faultReason) == 'availabilityPause' and axis.sourceCarStateMonoTime == 0
      gap = sd.pm.messages['aolAxisState']
      if fault in ('producer', 'epoch'):
        bad = gap.as_builder()
        if fault == 'producer':
          bad.aolAxisState.intentProducerSessionId = 'other-producer'
        else:
          bad.aolAxisState.intentIntegrityEpoch += 1
        gap = bad.as_reader()
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
      elif fault in ('source_clock', 'ack', 'desired_long'):
        altered = list(feedback.signature)
        if fault == 'source_clock':
          altered[8] = now - 200_000_001
        elif fault == 'ack':
          altered[13] = True
        else:
          altered[12] = True
        feedback.signature = tuple(altered)
      receive_pair(sd, controls, card, now, axis=gap, event=sd.pm.messages['onroadEvents'])
      assert feedback.failed and not feedback.retention_verified
      assert not command.latActive and not command.longActive and not sd.events.contains('enable')
      assert (feedback.lateral_source_ns, feedback.lateral_baseline_ns, feedback.lateral_native_ns) == origin
      with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=old.validUntilMonoTime + 1):
        expired, _ = controls.state_control()
      assert not expired.latActive and not expired.longActive


def test_completed_stock_role_is_not_captured_when_actual_send_crosses_source_deadline():
  with stock_family('toyota') as (sd, _, drive, _, _):
    first = BASE + 10_000_000
    actual_send = sd.pm.send
    sent = [False]

    def send(name, message):
      result = actual_send(name, message)
      if name == 'aolAxisState':
        sent[0] = True
      return result

    from openpilot.selfdrive.selfdrived import selfdrived as sd_module

    with (
      mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02),
      mock.patch.object(sd.pm, 'send', side_effect=send),
      mock.patch.object(sd_module.time, 'monotonic_ns', side_effect=lambda: first + 30_000_001 if sent[0] else first),
    ):
      axis, _, command = drive(3, state_stamp=first, **settings('lateral_only', first, 4))
    assert sent[0] and str(axis.faultReason) == 'critical'
    assert sd.aol_published_fault_proof is not None and not any(sd.aol_published_fault_proof[4:])
    assert sd.aol_published_stock_lateral_proof is None
    assert not command.latActive and not command.longActive
