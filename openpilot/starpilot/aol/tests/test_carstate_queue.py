from contextlib import ExitStack
from unittest import mock

import pytest

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.structs import car
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.wire import IntentState, encode_intent


def message(stamp, state=None, *, valid=True):
  sample = messaging.new_message('carState', valid=valid, logMonoTime=stamp)
  value = fixture.car_state() if state is None else state
  value.cruiseState.available = True
  sample.carState = value
  return sample.as_reader()


def queued_step(sd, step, samples, *, tick=5, offset_ns=4_292_276, intent=True):
  selected_ns = samples[-1].logMonoTime
  wire = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=selected_ns)
  wire.aolIntentWire = encode_intent(IntentState('authority-card', 50, selected_ns, selected_ns,
    selected_ns + 200_000_000, True, False, False, True, True))
  backlog = iter(samples[1:])
  original_receive = messaging.recv_one_or_none

  def receive(sock):
    return next(backlog, None) if sock is sd.car_state_sock else original_receive(sock)

  with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one', return_value=samples[0]), \
       mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive):
    return step(tick, offset_ns=offset_ns, state_stamp=samples[0].logMonoTime,
                intent_message=wire if intent else None)


def test_route3c_oldest_35ms_advances_to_exact_fresh_pair_and_actual_controls():
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, _, receive = case._ioniq_availability_callers()
      a, b, now = 10_019_000_000, 10_051_448_441, 10_054_292_276
      axis, _, command = queued_step(sd, step, [message(a), message(10_030_000_000), message(b)])
      assert now - a == 35_292_276 and now - b == 2_843_835
      assert axis.sourceCarStateMonoTime == b and sd.aol_last_intent.carStateLogMonoTime == b
      assert axis.lateralActive and axis.longitudinalActive and command.latActive and command.longActive
      assert not sd.aol_authority_lost and log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
      assert receive(now, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])


@pytest.mark.parametrize('pulse', ['cancel', 'brake', 'gas', 'permanent_eps', 'invalid_can', 'invalid_envelope', 'temporary_eps'])
def test_queue_preserves_pulses_and_latest_reader_without_reengaging(pulse):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, card, receive = case._ioniq_availability_callers()
      first = fixture.car_state()
      first.cruiseState.available = True
      if pulse == 'cancel':
        first.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
      elif pulse == 'brake':
        first.brakePressed = True
      elif pulse == 'gas':
        first.gasPressed = True
        sd.disengage_on_accelerator = True
      elif pulse == 'permanent_eps':
        first.steerFaultPermanent = True
      elif pulse == 'invalid_can':
        first.canValid = False
      elif pulse == 'temporary_eps':
        first.steerFaultTemporary = first.standstill = True
      final = fixture.car_state()
      final.cruiseState.available = True
      final.buttonEnable = True
      axis, _, command = queued_step(sd, step, [message(10_019_000_000, first, valid=pulse != 'invalid_envelope'),
                                                message(10_051_448_441, final)])
      assert axis.sourceCarStateMonoTime == 10_051_448_441
      assert not sd.CS_prev.steerFaultTemporary and not sd.CS_prev.steerFaultPermanent
      assert not sd.CS_prev.brakePressed and not sd.CS_prev.gasPressed and sd.CS_prev.canValid
      if pulse not in ('brake', 'gas'):
        assert not axis.lateralActive and not command.latActive
      if pulse == 'temporary_eps':
        assert log.OnroadEvent.EventName.steerTempUnavailableSilent in sd.events.names
        assert not sd.aol_authority_lost and sd.aol_last_intent.allowedLatch
        assert receive(10_054_292_276, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
        assert card.aol_card_intent.allowed_latch
      else:
        assert not axis.longitudinalActive and not command.longActive
        if pulse in ('cancel', 'brake', 'gas'):
          assert not sd.enabled
        assert not sd.events.contains(fixture.ET.ENABLE)


@pytest.mark.parametrize('failure', ['reordered', 'full_bound', 'missing_latest_pair'])
def test_queue_reorder_bound_and_pair_loss_still_withdraw(failure):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, _, _ = case._ioniq_availability_callers()
      stamps = ([10_020_000_000, 10_019_000_000] if failure == 'reordered' else
                [10_019_000_000 + i * 1_000_000 for i in range(32)] if failure == 'full_bound' else
                [10_019_000_000, 10_051_448_441])
      axis, _, command = queued_step(sd, step, [message(stamp) for stamp in stamps], intent=failure != 'missing_latest_pair')
      assert not axis.lateralActive and not axis.longitudinalActive and not command.latActive and not command.longActive
      assert str(axis.faultReason) == 'critical' and sd.aol_authority_lost
      if failure != 'missing_latest_pair':
        assert axis.sourceCarStateMonoTime == 0 and not sd.conditional_car_state_valid
