from collections import deque
from contextlib import ExitStack
from unittest import mock

import pytest

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.structs import car
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_carstate_queue import message
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE, intent


@pytest.mark.parametrize('timeout', [False, True])
@pytest.mark.parametrize('full_op', [False, True])
@pytest.mark.parametrize('pulse', ['healthy', 'cancel_then_enable', 'brake_then_clear', 'permanent_eps', 'invalid_then_valid'])
def test_input_arriving_during_car_event_work_is_reconciled_once(full_op, pulse, timeout):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, _, _ = case._ioniq_availability_callers(full_op=full_op)
      first, _, command = step(2, offset_ns=3_720_071, state_stamp=BASE, intent_message=intent(BASE, 3), gas=not full_op)
      assert first.lateralActive and command.latActive and first.longitudinalActive == full_op
      deadline = BASE + 33_720_071
      sample_age = 30_100_000 if timeout else 27_000_000
      now = [BASE + sample_age]
      sd.car_state_poller = mock.Mock()
      sd.car_state_poller.poll.return_value = []
      fresh = BASE + 28_254_175
      queue, wires = deque(), deque()
      original_receive = messaging.recv_one_or_none
      original_car_update = sd._update_car_event_sample
      injected = False

      def receive(sock):
        if sock is sd.car_state_sock:
          return queue.popleft() if queue else None
        if sock is sd.aol_intent_companion.sock:
          return wires.popleft() if wires else None
        return original_receive(sock)

      def car_update(sample, previous):
        nonlocal injected
        result = original_car_update(sample, previous)
        if not injected:
          injected = True
          late = fixture.car_state()
          late.cruiseState.available = True
          late.gasPressed = not full_op
          late.vEgo = 25.
          if pulse == 'cancel_then_enable':
            late.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
          elif pulse == 'brake_then_clear':
            late.brakePressed = True
          elif pulse == 'permanent_eps':
            late.steerFaultPermanent = True
          queue.append(message(fresh, late, valid=pulse != 'invalid_then_valid'))
          wires.append(intent(fresh, 4, latched=pulse != 'cancel_then_enable').as_reader())
          if pulse in ('cancel_then_enable', 'brake_then_clear', 'invalid_then_valid'):
            cleared = fixture.car_state()
            cleared.cruiseState.available = True
            cleared.gasPressed = not full_op
            cleared.vEgo = 26.
            cleared.buttonEnable = pulse == 'cancel_then_enable'
            queue.append(message(fresh + 100_000, cleared))
            wires.append(intent(fresh + 100_000, 5).as_reader())
          now[0] = BASE + 30_253_011
        return result

      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: now[0]), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch.object(sd, '_update_car_event_sample', side_effect=car_update) as car_events, \
           mock.patch.object(sd.state_machine, 'update', wraps=sd.state_machine.update) as transition, \
           mock.patch.object(sd.excessive_actuation_check, 'update', wraps=sd.excessive_actuation_check.update) as excessive:
        axis, _, command = step(4, timeout=timeout, offset_ns=sample_age - 20_000_000, state_stamp=BASE,
                                intent_message=intent(BASE, 3), gas=not full_op)
      assert now[0] < deadline and not queue
      assert transition.call_count == 1
      assert excessive.call_count == (1 if sd.calibrated_pose is not None else 0)
      assert car_events.call_count == (3 if pulse.endswith(('enable', 'clear', 'valid')) else 2)
      if pulse == 'healthy':
        assert axis.sourceCarStateMonoTime == fresh and sd.aol_last_intent.carStateLogMonoTime == fresh
        assert axis.lateralActive and command.latActive
        assert axis.longitudinalActive == full_op and command.longActive == full_op
        assert sd.enabled == full_op and not sd.aol_authority_lost
      else:
        assert not axis.longitudinalActive and not command.longActive and not sd.enabled
        if pulse != 'brake_then_clear':
          assert not axis.lateralActive and not command.latActive
        if pulse == 'cancel_then_enable':
          assert log.OnroadEvent.EventName.buttonCancel in sd.events.names
          assert not sd.events.contains(fixture.ET.ENABLE)
        if pulse == 'brake_then_clear':
          assert log.OnroadEvent.EventName.pedalPressed in sd.events.names
        if pulse == 'invalid_then_valid':
          assert axis.sourceCarStateMonoTime == 0 and not sd.conditional_car_state_valid


def changed_intent(stamp, sequence, **changes):
  from dataclasses import replace
  from openpilot.starpilot.aol.wire import decode_intent, encode_intent
  wire = intent(stamp, sequence)
  decoded = decode_intent(wire.aolIntentWire)
  assert decoded is not None
  wire.aolIntentWire = encode_intent(replace(decoded, **changes))
  return wire


@pytest.mark.parametrize('restriction', ['pauseLongitudinal', 'pauseLateral', 'allowedLatch', 'lateralArmed',
                                         'settingsQualified', 'missing', 'producer', 'session', 'conflict', 'future', 'intermediate'])
def test_reconciliation_preserves_every_exact_intent_restriction(restriction):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      full_op = restriction not in ('allowedLatch', 'lateralArmed')
      sd, _, step, _, _ = case._ioniq_availability_callers(full_op=full_op)
      step(2, offset_ns=3_720_071, state_stamp=BASE, intent_message=intent(BASE, 3))
      a, b, c = BASE + 20_000_000, BASE + 25_000_000, BASE + 26_000_000
      changes = ({restriction: restriction.startswith('pause')} if restriction in
                 ('pauseLongitudinal', 'pauseLateral', 'allowedLatch', 'lateralArmed', 'settingsQualified') else {})
      if restriction == 'lateralArmed':
        changes['allowedLatch'] = False
      if restriction == 'future':
        changes['observedMonoTime'] = BASE + 40_000_000
      original_intent = changed_intent(a, 4, **changes)
      fresh_intent = changed_intent(b, 5, **({'producerSessionId': 'replacement-card'} if restriction == 'producer' else {}))
      if restriction == 'intermediate':
        fresh_intent = changed_intent(b, 5, pauseLongitudinal=True)
      latest = intent(c, 6) if restriction == 'intermediate' else fresh_intent
      wires = deque([] if restriction == 'missing' else [original_intent.as_reader()])
      if restriction == 'conflict':
        wires.append(changed_intent(a, 4, pauseLongitudinal=True).as_reader())
      wires.append(fresh_intent.as_reader())
      if restriction == 'intermediate':
        wires.append(latest.as_reader())
      queue = deque()
      now = [BASE + 27_000_000]
      original_receive, original_car_update, original_health = messaging.recv_one_or_none, sd._update_car_event_sample, sd.update_process_health
      injected = False

      def health():
        result = original_health()
        sd.sm.update_msgs(now[0] / 1e9, [latest.as_reader()])
        return result

      def receive(sock):
        if sock is sd.car_state_sock:
          return queue.popleft() if queue else None
        if sock is sd.aol_intent_companion.sock:
          return wires.popleft() if wires else None
        return original_receive(sock)

      def car_update(sample, previous):
        nonlocal injected
        result = original_car_update(sample, previous)
        if not injected:
          injected = True
          if restriction == 'session':
            sd.aol_session_id = 'replacement-selfdrived'
          for stamp in ((b, c) if restriction == 'intermediate' else (b,)):
            late = fixture.car_state()
            late.cruiseState.available = True
            queue.append(message(stamp, late))
          now[0] = BASE + 29_000_000
        return result

      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: now[0]), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch.object(sd, '_update_car_event_sample', side_effect=car_update), \
           mock.patch.object(sd, 'update_process_health', side_effect=health):
        axis, _, command = step(4, offset_ns=7_000_000, state_stamp=a, intent_message=original_intent)
      assert not queue
      if restriction in ('pauseLongitudinal', 'intermediate'):
        assert sd.aol_last_intent is not None and sd.aol_last_intent.pauseLongitudinal
        assert axis.lateralActive and command.latActive and not axis.longitudinalActive and not command.longActive
      elif restriction == 'pauseLateral':
        assert sd.aol_last_intent is not None and sd.aol_last_intent.pauseLateral
        assert not axis.lateralActive and not command.latActive and axis.longitudinalActive and command.longActive
      elif restriction in ('allowedLatch', 'lateralArmed'):
        assert sd.aol_last_intent is not None and not getattr(sd.aol_last_intent, restriction)
        assert not axis.lateralActive and not command.latActive
      else:
        assert sd.aol_last_intent is None
        assert not axis.lateralActive and not axis.longitudinalActive and not command.latActive and not command.longActive


@pytest.mark.parametrize('companion_case', ['healthy', 'unavailable', 'missing', 'invalid'])
def test_gm_companion_ordering_is_unchanged_by_ioniq_reconciliation(companion_case, monkeypatch):
  from opendbc.car.gm.tests.test_bolt_volt_configurations import ordinary_params
  from opendbc.car.gm.values import CAR
  from openpilot.starpilot.car.gm.steering_companion import SteeringCompanion
  monkeypatch.setenv('SIMULATION', '0')
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      cp = ordinary_params(CAR.CHEVROLET_VOLT_ASCM, alpha=True, sascm=True, radar=True)
      sd, _, step = case._authority_callers(True, cp=cp, genuine_events=True)
      sd.steering_companion = SteeringCompanion()
      assert step(2, state_stamp=BASE, intent_message=intent(BASE, 3))[2].longActive
      a, b = BASE + 20_000_000, BASE + 25_000_000
      now = [BASE + 27_000_000]
      queue, wires = deque(), deque([intent(a, 4).as_reader()])
      original_receive, original_car_update, original_health = messaging.recv_one_or_none, sd._update_car_event_sample, sd.update_process_health

      def health():
        result = original_health()
        for stamp in (a, b):
          companion = messaging.new_message('starpilotCarState', valid=True, logMonoTime=stamp)
          companion.starpilotCarState.sourceCarStateMonoTime = stamp
          companion.starpilotCarState.lateralAuthorityUnavailable = stamp == a and companion_case == 'unavailable'
          if stamp == a and companion_case != 'missing':
            sd.steering_companion._observe(stamp, companion_case != 'invalid', companion.starpilotCarState)
          if stamp == b:
            sd.sm.update_msgs(now[0] / 1e9, [companion.as_reader()])
        return result

      def receive(sock):
        if sock is sd.car_state_sock:
          return queue.popleft() if queue else None
        if sock is sd.aol_intent_companion.sock:
          return wires.popleft() if wires else None
        return original_receive(sock)

      def car_update(sample, previous):
        result = original_car_update(sample, previous)
        late = fixture.car_state()
        late.cruiseState.available = True
        queue.append(message(b, late))
        wires.append(intent(b, 5).as_reader())
        now[0] = BASE + 29_000_000
        return result

      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: now[0]), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch.object(sd, '_update_car_event_sample', side_effect=car_update), \
           mock.patch.object(sd, 'update_process_health', side_effect=health):
        axis, _, command = step(4, offset_ns=7_000_000, state_stamp=a, intent_message=intent(a, 4))
      assert len(queue) == 1 and axis.sourceCarStateMonoTime == a
      assert command.latActive == (companion_case == 'healthy')
      assert command.longActive == (companion_case == 'healthy')
      assert (log.OnroadEvent.EventName.controlsMismatch in sd.events.names) == (companion_case != 'healthy')
