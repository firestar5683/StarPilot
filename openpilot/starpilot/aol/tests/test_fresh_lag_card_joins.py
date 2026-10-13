"""Actual Card joins and bounded refusal probes for final ordinary fresh lag."""
from unittest import mock
import pytest
from openpilot.cereal import log, messaging
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE
from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings
from openpilot.starpilot.aol.tests.test_fresh_lag_continuity import callers


@pytest.mark.parametrize('order', ['proof_first', 'event_first', 'together'])
@pytest.mark.parametrize('after_source_pause', [False, True])
def test_current_standard_lag_active_proof_is_joined_by_actual_card(order, after_source_pause):
  with callers('combined') as ((sd, controls, drive, card, receive), _):
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      if after_source_pause:
        paused, state, command = drive(5, timeout=True, state_stamp=BASE, offset_ns=5_399_000,
                                       **settings('combined', BASE, 3))
        assert paused.sourceCarStateMonoTime == 0 and not command.latActive and not command.longActive
        assert state.enabled and state.state == log.SelfdriveState.OpenpilotState.softDisabling
        assert receive(BASE + 35_399_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
        tick, stamp, sequence = 6, BASE + 40_000_000, 4
      else:
        tick, stamp, sequence = 3, BASE + 10_000_000, 4
      axis, state, command = drive(tick, state_stamp=stamp, **settings('combined', stamp, sequence))
      assert state.enabled and state.active and str(axis.faultReason) == 'none'
      assert axis.desiredLateral and axis.desiredLongitudinal and axis.lateralActive and axis.longitudinalActive
      assert command.latActive and command.longActive
      proof, event = sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents']
      assert axis.faultEventMonoTime == event.logMonoTime and axis.validUntilMonoTime == stamp + 30_000_000
      assert any(e.name == log.OnroadEvent.EventName.selfdrivedLagging and e.softDisable for e in event.onroadEvents)
      if order == 'proof_first':
        assert receive(stamp, axis=proof)
        assert receive(stamp + 1_000_000, event=event)
      elif order == 'event_first':
        assert receive(stamp, event=event)
        assert receive(stamp + 1_000_000, axis=proof)
      else:
        assert receive(stamp, axis=proof, event=event)
      assert card.aol_card_intent.allowed_latch and not card.aol_transport_feedback.failed
      assert not sd.events.contains('enable')
      with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=axis.validUntilMonoTime + 1):
        expired, _ = controls.state_control()
      assert not expired.latActive and not expired.longActive


@pytest.mark.parametrize('fault', ['wrong_hard_event', 'expired_proof'])
def test_new_standard_active_proof_does_not_waive_missing_or_hard_consumer_evidence(fault):
  with callers('combined') as ((sd, _, drive, card, receive), _):
    stamp = BASE + 10_000_000
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, _, command = drive(3, state_stamp=stamp, **settings('combined', stamp, 4))
    assert str(axis.faultReason) == 'none' and axis.lateralActive and axis.longitudinalActive
    assert command.latActive and command.longActive
    proof, event = sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents']
    if fault == 'expired_proof':
      assert not receive(axis.validUntilMonoTime + 1, axis=proof, event=event)
    else:
      hard = messaging.new_message('onroadEvents', 1, valid=True, logMonoTime=event.logMonoTime)
      hard.onroadEvents[0].name = 'controlsMismatch'
      hard.onroadEvents[0].immediateDisable = True
      assert not receive(stamp, axis=proof, event=hard.as_reader())
    assert not card.aol_card_intent.allowed_latch


@pytest.mark.parametrize('event_name', ['wrongCarMode', 'belowEngageSpeed', 'pedalPressed'])
def test_other_no_entry_or_user_event_is_never_filtered_with_lag(event_name):
  with callers('combined') as ((sd, _, drive, _, _), _):
    original = sd.update_events
    def events(cs):
      result = original(cs)
      sd.events.add(getattr(log.OnroadEvent.EventName, event_name))
      return result
    stamp = BASE + 10_000_000
    with mock.patch.object(sd, 'update_events', side_effect=events), \
         mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, _, command = drive(3, state_stamp=stamp, **settings('combined', stamp, 4))
    assert getattr(log.OnroadEvent.EventName, event_name) in sd.events.names
    assert not axis.lateralActive and not axis.longitudinalActive and not command.latActive and not command.longActive


def test_pre_enabled_lag_cannot_use_existing_old_anchor_for_first_actuation():
  with callers('combined') as ((sd, _, drive, _, _), _):
    # Boundary probe: old publication exists, but the actual state owner is
    # preEnabled. Its production transition cannot justify this exception.
    stamp = BASE + 10_000_000
    pending = settings('combined', stamp, 4)
    pending.update(native_request_long=False, long_allowed=False)
    lat_only, _, _ = drive(3, state_stamp=stamp, **pending)
    assert lat_only.lateralActive and not lat_only.longitudinalActive
    assert sd.aol_ordinary_source_anchor[0][8] and not sd.aol_ordinary_source_anchor[0][9]
    sd.state_machine.state = log.SelfdriveState.OpenpilotState.preEnabled
    sd.enabled, sd.active = True, False
    stamp += 10_000_000
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, _, command = drive(4, state_stamp=stamp, **settings('combined', stamp, 5))
    assert not axis.lateralActive and not axis.longitudinalActive and not command.latActive and not command.longActive
    assert str(axis.faultReason) == 'critical'


def test_accepted_proof_without_new_event_retains_only_bounded_intent_memory():
  with callers('combined') as ((sd, controls, drive, card, receive), _):
    stamp = BASE + 10_000_000
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, _, _ = drive(3, state_stamp=stamp, **settings('combined', stamp, 4))
    assert receive(stamp, axis=sd.pm.messages['aolAxisState'])
    feedback = card.aol_transport_feedback
    original = (feedback.lateral_source_ns, feedback.lateral_baseline_ns, feedback.lateral_native_ns)
    for now in (axis.validUntilMonoTime + 1, axis.validUntilMonoTime + 20_000_000):
      with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=now):
        expired, _ = controls.state_control()
      assert not expired.latActive and not expired.longActive
      assert receive(now)
      assert (feedback.lateral_source_ns, feedback.lateral_baseline_ns, feedback.lateral_native_ns) == original
      assert feedback.signature[4] == axis.validUntilMonoTime
    # Duplicate receipt/inspection cannot renew the ORIGINAL source/native bound.
    assert not receive(stamp + 200_000_001)
    assert not card.aol_card_intent.allowed_latch


@pytest.mark.parametrize('fault', ['hard_event', 'mixed_user', 'native_long_withdrawn', 'late_join'])
def test_pending_combined_recovery_requires_exact_event_grants_and_fixed_join(fault):
  from dataclasses import replace
  from openpilot.starpilot.aol.wire import decode_safety, encode_safety
  with callers('combined') as ((sd, _, drive, card, receive), _):
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      paused, _, _ = drive(5, timeout=True, state_stamp=BASE, offset_ns=5_399_000,
                            **settings('combined', BASE, 3))
      assert paused.sourceCarStateMonoTime == 0
      assert receive(BASE + 35_399_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      stamp = BASE + 40_000_000
      axis, _, _ = drive(6, state_stamp=stamp, **settings('combined', stamp, 4))
      assert axis.lateralActive and axis.longitudinalActive and str(axis.faultReason) == 'none'
      event = sd.pm.messages['onroadEvents']
      assert receive(stamp, event=event)
      started = card.aol_transport_feedback.retention_started_ns
      assert started == stamp and card.aol_transport_feedback.retention_verified
      if fault in ('hard_event', 'mixed_user'):
        bad = messaging.new_message('onroadEvents', 2 if fault == 'mixed_user' else 1,
                                    valid=True, logMonoTime=event.logMonoTime)
        if fault == 'mixed_user':
          bad.onroadEvents[0].name = 'selfdrivedLagging'
          bad.onroadEvents[0].softDisable = True
          bad.onroadEvents[1].name = 'pedalPressed'
          bad.onroadEvents[1].userDisable = True
        else:
          bad.onroadEvents[0].name = 'controlsMismatch'
          bad.onroadEvents[0].immediateDisable = True
        assert not receive(stamp + 1_000_000, axis=sd.pm.messages['aolAxisState'], event=bad.as_reader())
      elif fault == 'native_long_withdrawn':
        native = decode_safety(sd.sm['aolSafetyWire'])
        denied = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=stamp)
        denied.aolSafetyWire = encode_safety(replace(native, requestedLongitudinal=False, longitudinalAllowed=False))
        sd.sm.update_msgs(stamp / 1e9, [denied.as_reader()])
        assert not receive(stamp + 1_000_000, axis=sd.pm.messages['aolAxisState'])
      else:
        # Fresh forward proof remains within its OWN lease; old join still ends
        # at its original 30ms deadline and cannot be restarted by that proof.
        next_stamp = stamp + 20_000_000
        fresh, _, _ = drive(8, state_stamp=next_stamp, **settings('combined', next_stamp, 5))
        assert fresh.lateralActive and fresh.longitudinalActive
        assert fresh.faultEventMonoTime == event.logMonoTime
        assert fresh.validUntilMonoTime > started + 30_000_001
        assert not receive(started + 30_000_001, axis=sd.pm.messages['aolAxisState'])
      assert not card.aol_card_intent.allowed_latch
