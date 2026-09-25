"""Publication-time stock role provenance and current owner refusal probes."""

from contextlib import ExitStack


from dataclasses import replace


from unittest import mock


import pytest


from openpilot.cereal import log, messaging


from openpilot.starpilot.aol.wire import decode_safety, encode_safety


from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE


from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings


from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import stock_family
from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import callers
from openpilot.starpilot.aol.tests.test_stock_lateral_pcm import receive_pair


def fresh_fault(sd, drive):
  first = BASE + 10_000_000
  axis, state, command = drive(3, state_stamp=first, **settings('lateral_only', first, 4))
  assert str(axis.faultReason) == 'critical' and axis.sourceCarStateMonoTime == first
  assert not state.enabled and not command.latActive and not command.longActive
  published = sd.aol_published_fault_proof
  record = sd.aol_published_stock_lateral_proof
  assert len(published) == 9 and record is not None and record[0] == published
  assert record[1] == log.OnroadEvent.EventName.pcmDisable
  return axis, published, record


@pytest.mark.parametrize(
  'fault',
  [
    'missing_record',
    'wrong_user',
    'wrong_occurrence',
    'prior_other_user',
    'prior_hard',
    'publisher_session',
    'current_native_denied',
    'current_serial',
    'current_epoch',
    'current_sticky_dm',
  ],
)
def test_current_health_cannot_replace_exact_completed_prior_stock_role(fault):
  with stock_family('toyota') as (sd, controls, drive, _, _):
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      _, published, record = fresh_fault(sd, drive)
      if fault == 'missing_record':
        sd.aol_published_stock_lateral_proof = None
      elif fault == 'wrong_user':
        sd.aol_published_stock_lateral_proof = (published, log.OnroadEvent.EventName.cruiseDisabled)
      elif fault == 'wrong_occurrence':
        wrong = list(published)
        wrong[2] += 1
        sd.aol_published_stock_lateral_proof = (tuple(wrong), record[1])
      elif fault in ('prior_other_user', 'prior_hard'):
        wrong = list(published)
        wrong[3] += (log.OnroadEvent.EventName.buttonCancel if fault == 'prior_other_user' else log.OnroadEvent.EventName.controlsMismatch,)
        sd.aol_published_fault_proof = tuple(wrong)
        sd.events_prev = list(wrong[3])
      elif fault == 'publisher_session':
        wrong = list(published)
        wrong[0] = 'other-publisher'
        sd.aol_published_fault_proof = tuple(wrong)
      original = sd.update_events

      def events(cs):
        result = original(cs)
        if fault == 'current_serial':
          native = decode_safety(sd.sm['aolSafetyWire'])
          inventory = tuple(replace(slot, hardwareSerial=f'other-{i}') for i, slot in enumerate(native.pandaInventory))
          native = replace(native, pandaSerial=inventory[-1].hardwareSerial, pandaInventory=inventory)
          message = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=native.observedMonoTime)
          message.aolSafetyWire = encode_safety(native)
          sd.sm.update_msgs(native.observedMonoTime / 1e9, [message.as_reader()])
        elif fault == 'current_epoch':
          sd.aol_intent_companion.integrity_epoch += 1
        elif fault == 'current_sticky_dm':
          sd.aol_dm_lateral_inhibit = True
        return result

      opts = settings('lateral_only', BASE + 10_000_000, 4)
      if fault == 'current_native_denied':
        opts['allowed'] = False
      with mock.patch.object(sd, 'update_events', side_effect=events):
        axis, state, command = drive(6, timeout=True, state_stamp=BASE + 10_000_000, offset_ns=5_399_000, **opts)
      assert not axis.lateralActive and not axis.longitudinalActive and not command.latActive and not command.longActive
      assert str(axis.faultReason) != 'availabilityPause' and not sd.aol_ordinary_source_pause
      assert not state.enabled and not command.longActive and not sd.events.contains('enable')


@pytest.mark.parametrize(
  'fault', ['cancel', 'main_off', 'native_denied', 'serial_changed', 'epoch_changed', 'dm_lockout', 'other_user', 'hard_event', 'publication_cutoff']
)
def test_stock_role_is_not_captured_for_unqualified_actual_publication(fault):
  with stock_family('toyota') as (sd, controls, drive, _, _):
    original = sd.update_events

    def events(cs):
      result = original(cs)
      if fault == 'serial_changed':
        native = decode_safety(sd.sm['aolSafetyWire'])
        inventory = tuple(replace(slot, hardwareSerial=f'other-{i}') for i, slot in enumerate(native.pandaInventory))
        native = replace(native, pandaSerial=inventory[-1].hardwareSerial, pandaInventory=inventory)
        packet = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=native.observedMonoTime)
        packet.aolSafetyWire = encode_safety(native)
        sd.sm.update_msgs(native.observedMonoTime / 1e9, [packet.as_reader()])
      elif fault == 'epoch_changed':
        sd.aol_intent_companion.integrity_epoch += 1
      elif fault == 'dm_lockout':
        packet = messaging.new_message('driverMonitoringState', valid=True, logMonoTime=BASE + 10_000_000)
        packet.driverMonitoringState.lockout = True
        sd.sm.update_msgs((BASE + 10_000_000) / 1e9, [packet.as_reader()])
      elif fault in ('other_user', 'hard_event'):
        sd.events.add(log.OnroadEvent.EventName.buttonCancel if fault == 'other_user' else log.OnroadEvent.EventName.controlsMismatch)
      return result

    first = BASE + 10_000_000
    opts = settings('lateral_only', first, 4)
    if fault == 'native_denied':
      opts['allowed'] = False
    with ExitStack() as cleanup:
      cleanup.enter_context(mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02))
      cleanup.enter_context(mock.patch.object(sd, 'update_events', side_effect=events))
      if fault in ('cancel', 'main_off'):
        from opendbc.car.structs import car
        from openpilot.selfdrive.selfdrived import selfdrived as sd_module

        receiver = sd_module.messaging.recv_one

        def delivered(sock):
          packet = receiver.return_value.as_builder()
          if fault == 'cancel':
            packet.carState.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
          else:
            packet.carState.cruiseState.available = False
          return packet.as_reader()

        cleanup.enter_context(mock.patch.object(receiver, 'side_effect', side_effect=delivered))
      elif fault == 'publication_cutoff':
        from openpilot.selfdrive.selfdrived import selfdrived as sd_module

        actual = sd.publish_axis_proof
        publishing = [False]

        def publish(*args, **kwargs):
          publishing[0] = True
          return actual(*args, **kwargs)

        cleanup.enter_context(mock.patch.object(sd, 'publish_axis_proof', side_effect=publish))
        cleanup.enter_context(mock.patch.object(sd_module.time, 'monotonic_ns', side_effect=lambda: first + 30_000_001 if publishing[0] else first))
      axis, _, command = drive(3, state_stamp=first, **opts)
    assert sd.aol_published_stock_lateral_proof is None
    assert not axis.lateralActive and not axis.longitudinalActive and not command.latActive and not command.longActive
    assert not command.longActive


@pytest.mark.parametrize('origin', ['ordinary_combined', 'ordinary_long_pending'])
def test_stock_temp_lag_cannot_claim_a_lat_only_origin_from_long_request(origin):
  with ExitStack() as cleanup:
    sd, controls, drive, card, receive = callers(cleanup, 'toyota', False)
    opts = settings('combined', BASE, 3)
    if origin == 'ordinary_long_pending':
      opts.update(native_request_long=False, long_allowed=False)
    old, _, command = drive(2, state_stamp=BASE, **opts)
    assert old.lateralActive and old.desiredLongitudinal
    assert old.longitudinalActive == (origin == 'ordinary_combined')
    assert receive(BASE)
    assert not card.aol_transport_feedback.lateral_only_baseline
    from openpilot.selfdrive.selfdrived import selfdrived as sd_module

    receiver = sd_module.messaging.recv_one

    def delivered(sock):
      packet = receiver.return_value.as_builder()
      packet.carState.cruiseState.enabled = False
      return packet.as_reader()

    first = BASE + 10_000_000
    with mock.patch.object(receiver, 'side_effect', side_effect=delivered), mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      off, state, command = drive(3, state_stamp=first, **dict(settings('combined', first, 4), native_request_long=False, long_allowed=False))
    assert str(off.faultReason) == 'critical' and not state.enabled
    assert sd.aol_published_stock_lateral_proof is None
    receive_pair(sd, controls, card, first, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    assert card.aol_transport_feedback.failed and not card.aol_transport_feedback.lateral_only_baseline
    assert not command.latActive and not command.longActive
