"""PCM role source availability and joined delivery boundaries."""

from contextlib import ExitStack
from unittest import mock
import pytest
from openpilot.cereal import log, messaging
from openpilot.selfdrive.car import card as card_module
from openpilot.starpilot.aol.tests import stock_lateral_test_helpers as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE
from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings
from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import callers


def receive_pair(sd, controls, card, now, *, axis=None, event=None):
  frames = []
  for name in ('pandaStates', 'aolSafetyWire', 'deviceState', 'carControl'):
    command = controls.pm.messages['carControl'] if name == 'carControl' else None
    message = messaging.new_message(
      name,
      len(sd.sm[name]) if name in ('pandaStates', 'aolSafetyWire') else None,
      valid=True if command is not None else sd.sm.valid[name],
      logMonoTime=int(command.logMonoTime) if command is not None else int(sd.sm.logMonoTime[name]),
    )
    setattr(message, name, getattr(command, name) if command is not None else sd.sm[name])
    frames.append(messaging.log_from_bytes(message.to_bytes()))
  card.sm.update_msgs(now / 1e9, frames + [m for m in (axis, event) if m is not None])
  physical = fixture.car_state()
  physical.cruiseState.available = True
  physical.cruiseState.enabled = False
  with (
    mock.patch.object(card_module.messaging, 'drain_sock_raw', return_value=[b'fixture']),
    mock.patch.object(card_module, 'can_capnp_to_list', return_value=[]),
    mock.patch.object(card_module.time, 'monotonic_ns', return_value=now),
    mock.patch.object(card_module, 'REPLAY', False),
    mock.patch.object(card.sm, 'update'),
    mock.patch.object(card.CI, 'update', return_value=physical),
  ):
    actual, _ = card.state_update()
  assert actual is physical
  return card.aol_card_intent.allowed_latch


@pytest.mark.parametrize('order', ['proof_first', 'event_first', 'together'])
def test_pcm_lat_only_host_gap_joins_actual_card(order):
  with ExitStack() as cleanup:
    sd, controls, drive, card, receive = callers(cleanup, 'toyota', True)
    old, _, _ = drive(2, state_stamp=BASE, **settings('lateral_only', BASE, 3))
    assert old.lateralActive and not old.longitudinalActive and receive(BASE)
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, state, command = drive(5, timeout=True, state_stamp=BASE, offset_ns=5_399_000, **settings('lateral_only', BASE, 3))
    assert not state.enabled and not state.active and not command.latActive and not command.longActive
    assert str(axis.faultReason) == 'availabilityPause' and axis.sourceCarStateMonoTime == 0
    assert axis.desiredLateral and axis.nativeAcknowledged and not axis.desiredLongitudinal
    assert not axis.lateralActive and not axis.longitudinalActive and not sd.aol_authority_lost
    proof, event, now = sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents'], BASE + 35_399_000
    assert any(e.name == log.OnroadEvent.EventName.pcmDisable and e.userDisable for e in event.onroadEvents)
    assert any(e.name == log.OnroadEvent.EventName.selfdrivedLagging and e.softDisable for e in event.onroadEvents)
    if order == 'proof_first':
      assert receive_pair(sd, controls, card, now, axis=proof)
      assert receive_pair(sd, controls, card, now + 1_000_000, event=event)
    elif order == 'event_first':
      assert receive_pair(sd, controls, card, now, event=event)
      assert receive_pair(sd, controls, card, now + 1_000_000, axis=proof)
    else:
      assert receive_pair(sd, controls, card, now, axis=proof, event=event)
    assert card.aol_transport_feedback.retention_verified and not card.aol_transport_feedback.failed
    assert not sd.events.contains('enable')


def test_nominal_pcm_remembers_normally_admitted_newer_lat_input_without_renewing_old_command():
  with ExitStack() as cleanup:
    sd, controls, drive, card, receive = callers(cleanup, 'toyota', True)
    old, _, _ = drive(2, state_stamp=BASE, **settings('lateral_only', BASE, 3))
    original = sd.aol_ordinary_source_anchor[0]
    assert old.lateralActive and not old.longitudinalActive
    fresh_stamp = BASE + 10_000_000
    actual_metadata = sd.observe_ordinary_source_metadata
    metadata_result = []

    def record_metadata(*args, **kwargs):
      actual_metadata(*args, **kwargs)
      metadata_result.append(sd.aol_ordinary_source_anchor)

    with mock.patch.object(sd, 'observe_ordinary_source_metadata', side_effect=record_metadata):
      fresh, state, command = drive(3, state_stamp=fresh_stamp, **settings('lateral_only', fresh_stamp, 4))
    assert fresh.lateralActive and command.latActive and not state.enabled and not command.longActive
    assert sd.aol_ordinary_source_anchor[2].carStateLogMonoTime == fresh_stamp
    assert metadata_result and metadata_result[-1][0] == original
    assert metadata_result[-1][2].carStateLogMonoTime == fresh_stamp
    # A newly admitted ACTIVE publication legitimately creates its OWN proof;
    # the old tuple was not restamped or extended by the metadata recorder.
    published = sd.aol_ordinary_source_anchor[0]
    assert published[1] == fresh_stamp and published[3] == fresh.validUntilMonoTime
    assert original[1] == BASE and original[3] == old.validUntilMonoTime
    assert receive(fresh_stamp)
    assert any(e.name == log.OnroadEvent.EventName.pcmDisable and e.userDisable for e in sd.events.to_msg())
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=fresh.validUntilMonoTime + 1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
    paused, state, command = drive(6, timeout=True, state_stamp=fresh_stamp, offset_ns=5_399_000, **settings('lateral_only', fresh_stamp, 4))
    assert str(paused.faultReason) == 'availabilityPause' and paused.sourceCarStateMonoTime == 0
    assert not command.latActive and not command.longActive and not state.enabled and not sd.aol_authority_lost
    assert receive(BASE + 45_399_000)
    assert sd.aol_ordinary_source_anchor[0] == published


@pytest.mark.parametrize(
  'fault',
  [
    'main_off',
    'stock_enabled',
    'cancel',
    'brake',
    'gas',
    'regen',
    'mixed_user',
    'mixed_hard',
    'steer_soft',
    'sticky_dm',
    'native_denied',
    'epoch_changed',
    'prior_user_history',
  ],
)
def test_pcm_role_never_waives_other_owners_or_historical_user_fault(fault):
  from opendbc.car.structs import car

  with ExitStack() as cleanup:
    sd, controls, drive, _, _ = callers(cleanup, 'toyota', True)
    old, _, _ = drive(2, state_stamp=BASE, **settings('lateral_only', BASE, 3))
    physical = fixture.car_state()
    if fault in ('brake', 'gas', 'regen'):
      setattr(physical, {'brake': 'brakePressed', 'gas': 'gasPressed', 'regen': 'regenBraking'}[fault], True)
    elif fault == 'cancel':
      physical.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
    original_events = sd.update_events

    def events(cs):
      result = original_events(cs)
      if fault == 'stock_enabled':
        # Adversarial inconsistent event/physical role; an enabled stock
        # source cannot qualify a nominal stock-OFF USER exception.
        sd.events.add(log.OnroadEvent.EventName.pcmDisable)
      if fault in ('mixed_user', 'mixed_hard', 'steer_soft'):
        sd.events.add(
          getattr(log.OnroadEvent.EventName, {'mixed_user': 'buttonCancel', 'mixed_hard': 'controlsMismatch', 'steer_soft': 'steerTempUnavailable'}[fault])
        )
      elif fault == 'sticky_dm':
        sd.aol_dm_lateral_inhibit = True
      elif fault == 'epoch_changed':
        sd.aol_intent_companion.integrity_epoch += 1
      elif fault == 'prior_user_history':
        # Adversarial closed history, not a fabricated healthy-role witness.
        names = (log.OnroadEvent.EventName.pcmDisable, log.OnroadEvent.EventName.selfdrivedLagging)
        sd.events_prev = list(names)
        sd.aol_published_fault_reason = sd.aol_fault_reason = 'critical'
        sd.aol_fault_event_ns = BASE + 1
        sd.aol_published_fault_proof = (sd.aol_session_id, 'critical', BASE + 1, names, False, False, False, False, False)
      return result

    options = settings('lateral_only', BASE, 3)
    if fault == 'native_denied':
      options['allowed'] = False
    physical_faults = ('main_off', 'stock_enabled', 'cancel', 'brake', 'gas', 'regen')
    with mock.patch.object(sd, 'update_events', side_effect=events), mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      if fault in physical_faults:
        # Deliver real original carState bytes before the missing tick. The
        # generic fixture normalizes MAIN/gas before serializing, so amend the
        # received envelope itself; no unseen timeout input is invented.
        from openpilot.selfdrive.selfdrived import selfdrived as sd_module

        receiver = sd_module.messaging.recv_one

        def delivered(sock):
          message = receiver.return_value
          if message is None:
            return None
          packet = message.as_builder()
          if fault == 'main_off':
            packet.carState.cruiseState.available = False
          elif fault == 'stock_enabled':
            packet.carState.cruiseState.enabled = True
          elif fault == 'gas':
            packet.carState.gasPressed = True
          return packet.as_reader()

        fault_stamp = BASE + 10_000_000
        with mock.patch.object(receiver, 'side_effect', side_effect=delivered):
          drive(3, observed_state=physical, state_stamp=fault_stamp, **settings('lateral_only', fault_stamp, 4))
        actual = sd.CS_prev
        if fault == 'main_off':
          assert not actual.cruiseState.available
        elif fault == 'stock_enabled':
          assert actual.cruiseState.enabled
        elif fault == 'gas':
          assert actual.gasPressed
        elif fault == 'brake':
          assert actual.brakePressed
        elif fault == 'regen':
          assert actual.regenBraking
        else:
          assert any(e.type == car.CarState.ButtonEvent.Type.cancel and e.pressed for e in actual.buttonEvents)
        options = settings('lateral_only', fault_stamp, 4)
        axis, state, command = drive(6, timeout=True, state_stamp=fault_stamp, offset_ns=5_399_000, **options)
      else:
        axis, state, command = drive(5, timeout=True, state_stamp=BASE, offset_ns=5_399_000, **options)
    assert not command.latActive and not command.longActive
    assert not axis.lateralActive and not axis.longitudinalActive
    assert str(axis.faultReason) != 'availabilityPause' and not sd.aol_ordinary_source_pause
    assert old.validUntilMonoTime < BASE + 35_399_000
    assert not command.longActive


@pytest.mark.parametrize('kind', ['speed_user', 'cruise_user', 'mixed_button', 'pcm_soft', 'pcm_immediate', 'user_without_pcm'])
def test_other_user_flags_never_advance_normally_admitted_metadata(kind):
  from openpilot.selfdrive.selfdrived.events import ET

  with ExitStack() as cleanup:
    sd, _, drive, _, _ = callers(cleanup, 'toyota', True)
    drive(2, state_stamp=BASE, **settings('lateral_only', BASE, 3))
    original_anchor = sd.aol_ordinary_source_anchor
    actual_metadata, actual_events = sd.observe_ordinary_source_metadata, sd.update_events
    observations = []

    def record_metadata(*args, **kwargs):
      actual_metadata(*args, **kwargs)
      observations.append(sd.aol_ordinary_source_anchor)

    rules = dict(sd.events.event_rules)
    user_alert = rules[log.OnroadEvent.EventName.pcmDisable][ET.USER_DISABLE]
    name = {'speed_user': 'speedTooLow', 'cruise_user': 'cruiseDisabled', 'mixed_button': 'buttonCancel', 'user_without_pcm': 'speedTooLow'}.get(kind)
    if name:
      rules[getattr(log.OnroadEvent.EventName, name)] = {ET.USER_DISABLE: user_alert}
    else:
      rules[log.OnroadEvent.EventName.pcmDisable] = {
        ET.USER_DISABLE: user_alert,
        ET.SOFT_DISABLE if kind == 'pcm_soft' else ET.IMMEDIATE_DISABLE: rules[log.OnroadEvent.EventName.commIssue][ET.SOFT_DISABLE],
      }

    def events(cs):
      result = actual_events(cs)
      if name:
        sd.events.add(getattr(log.OnroadEvent.EventName, name))
      if kind == 'user_without_pcm':
        sd.events.events = [e for e in sd.events.names if e != log.OnroadEvent.EventName.pcmDisable]
      return result

    stamp = BASE + 10_000_000
    with (
      mock.patch.object(sd.events, 'event_rules', rules),
      mock.patch.object(sd, 'update_events', side_effect=events),
      mock.patch.object(sd, 'observe_ordinary_source_metadata', side_effect=record_metadata),
    ):
      _, state, command = drive(3, state_stamp=stamp, **settings('lateral_only', stamp, 4))
    assert observations and observations[-1] is original_anchor
    assert observations[-1][2].carStateLogMonoTime == BASE
    assert not state.enabled and not command.longActive


@pytest.mark.parametrize(
  'fault', ['hard_event', 'other_user', 'native_withdrawn', 'serial_changed', 'epoch_changed', 'producer_changed', 'missing_proof', 'late_proof']
)
def test_pcm_pending_join_does_not_renew_deadlines_or_waive_current_owner(fault):
  from dataclasses import replace
  from openpilot.starpilot.aol.wire import decode_safety, encode_safety

  with ExitStack() as cleanup:
    sd, controls, drive, card, receive = callers(cleanup, 'toyota', True)
    old, _, _ = drive(2, state_stamp=BASE, **settings('lateral_only', BASE, 3))
    assert old.lateralActive and not old.longitudinalActive and receive(BASE)
    original = (
      card.aol_transport_feedback.lateral_source_ns,
      card.aol_transport_feedback.lateral_baseline_ns,
      card.aol_transport_feedback.lateral_native_ns,
      card.aol_transport_feedback.healthy_native_ns,
      card.aol_transport_feedback.healthy_feedback_ns,
    )
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=old.validUntilMonoTime + 1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, state, command = drive(5, timeout=True, state_stamp=BASE, offset_ns=5_399_000, **settings('lateral_only', BASE, 3))
      assert not state.enabled and not command.latActive and not command.longActive
      now = BASE + 35_399_000
      proof, event = sd.pm.messages['aolAxisState'], sd.pm.messages['onroadEvents']
      assert receive_pair(sd, controls, card, now, event=event)
      feedback = card.aol_transport_feedback
      assert feedback.retention_pending and not feedback.retention_verified and not feedback.failed
      assert feedback.retention_started_ns == now and feedback.retention_event_ns == event.logMonoTime
      assert (
        feedback.lateral_source_ns,
        feedback.lateral_baseline_ns,
        feedback.lateral_native_ns,
        feedback.healthy_native_ns,
        feedback.healthy_feedback_ns,
      ) == original
      if fault in ('hard_event', 'other_user'):
        bad = messaging.new_message('onroadEvents', 2, valid=True, logMonoTime=event.logMonoTime)
        bad.onroadEvents[0].name = 'pcmDisable'
        bad.onroadEvents[0].userDisable = True
        bad.onroadEvents[1].name = 'controlsMismatch' if fault == 'hard_event' else 'buttonCancel'
        if fault == 'hard_event':
          bad.onroadEvents[1].immediateDisable = True
        else:
          bad.onroadEvents[1].userDisable = True
        receive_pair(sd, controls, card, now + 1_000_000, event=bad.as_reader())
      elif fault in ('native_withdrawn', 'serial_changed'):
        native = decode_safety(sd.sm['aolSafetyWire'])
        if fault == 'native_withdrawn':
          native = replace(native, lateralAllowed=False)
        else:
          inventory = tuple(replace(slot, hardwareSerial='other-panda') for slot in native.pandaInventory)
          native = replace(native, pandaSerial='other-panda', pandaInventory=inventory)
        packet = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=native.observedMonoTime)
        packet.aolSafetyWire = encode_safety(native)
        sd.sm.update_msgs(now / 1e9, [packet.as_reader()])
        receive_pair(sd, controls, card, now + 1_000_000, axis=proof)
      elif fault in ('epoch_changed', 'producer_changed'):
        bad = proof.as_builder()
        if fault == 'epoch_changed':
          bad.aolAxisState.intentIntegrityEpoch += 1
        else:
          bad.aolAxisState.intentProducerSessionId = 'other-producer'
        receive_pair(sd, controls, card, now + 1_000_000, axis=bad.as_reader())
      else:
        # Duplicate event/old-proof receipts do not restart the pending clock.
        for delta in (10_000_000, 20_000_000):
          assert receive_pair(sd, controls, card, now + delta, event=event)
          assert feedback.retention_started_ns == now and not feedback.failed
          assert (
            feedback.lateral_source_ns,
            feedback.lateral_baseline_ns,
            feedback.lateral_native_ns,
            feedback.healthy_native_ns,
            feedback.healthy_feedback_ns,
          ) == original
        late = now + 30_000_001
        if fault == 'missing_proof':
          receive_pair(sd, controls, card, late, event=event)
        else:
          # Actual SD publishes a NEW inactive proof with its OWN live30ms lease;
          # receiving it cannot extend the earlier pending event's fixed bound.
          off, _, command = drive(8, timeout=True, state_stamp=BASE, offset_ns=5_399_001, **settings('lateral_only', BASE, 3))
          assert off.observedMonoTime == late and off.validUntilMonoTime > late
          assert off.faultEventMonoTime == event.logMonoTime
          assert not command.latActive and not command.longActive
          receive_pair(sd, controls, card, late, axis=sd.pm.messages['aolAxisState'])
      assert feedback.failed and not feedback.retention_verified
      with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=now + 30_000_001):
        off, _ = controls.state_control()
      assert not off.latActive and not off.longActive and not sd.events.contains('enable')
      assert old.validUntilMonoTime == BASE + 30_000_000


@pytest.mark.parametrize('user_name', ['buttonCancel', 'cruiseDisabled'])
def test_pcm_proof_first_pending_rejects_other_user_even_with_comm_only(user_name):
  with ExitStack() as cleanup:
    sd, controls, drive, card, receive = callers(cleanup, 'toyota', True)
    drive(2, state_stamp=BASE, **settings('lateral_only', BASE, 3))
    assert receive(BASE)
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, _, command = drive(5, timeout=True, state_stamp=BASE, offset_ns=5_399_000, **settings('lateral_only', BASE, 3))
    now = BASE + 35_399_000
    assert str(axis.faultReason) == 'availabilityPause' and not command.latActive and not command.longActive
    assert receive_pair(sd, controls, card, now, axis=sd.pm.messages['aolAxisState'])
    feedback = card.aol_transport_feedback
    assert feedback.retention_pending and not feedback.retention_verified and not feedback.failed
    # An adversarial current event vector must not use generic comm-only
    # eligibility to hide a different USER during this nominal PCM join.
    bad = messaging.new_message('onroadEvents', 3, valid=True, logMonoTime=axis.faultEventMonoTime)
    bad.onroadEvents[0].name = 'pcmDisable'
    bad.onroadEvents[0].userDisable = True
    bad.onroadEvents[1].name = 'commIssue'
    bad.onroadEvents[1].softDisable = True
    bad.onroadEvents[2].name = user_name
    bad.onroadEvents[2].userDisable = True
    receive_pair(sd, controls, card, now + 1_000_000, event=bad.as_reader())
    assert feedback.failed and not feedback.retention_verified
    assert not command.latActive and not command.longActive
