from contextlib import ExitStack
from unittest import mock

import pytest

from openpilot.cereal import log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import intent


@pytest.mark.parametrize('fault', ['alert_three', 'lockout'])
def test_source_zero_withdrawal_respects_dm_inhibit_after_current_dm_clears(fault):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=True)
    for tick in range(2, 5):
      axis, _, command = drive(tick)
      assert axis.lateralActive and axis.longitudinalActive
      assert command.latActive and command.longActive
      assert receive(10_000_000_000 + tick * 10_000_000,
        axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    actual_update = sd.sm.update_msgs
    current_fault = [True]
    delivered = []

    def update(timestamp, messages):
      selected = []
      for message in messages:
        if message.which() == 'driverMonitoringState':
          delivered.append(int(message.logMonoTime))
          if current_fault[0]:
            message = message.as_builder()
            message.driverMonitoringState.activePolicy = 'vision'
            if fault == 'alert_three':
              message.driverMonitoringState.alertLevel = 'three'
            else:
              message.driverMonitoringState.lockout = True
            message = message.as_reader()
        selected.append(message)
      return actual_update(timestamp, selected)

    with mock.patch.object(sd.sm, 'update_msgs', side_effect=update):
      axis, _, command = drive(5)
      assert delivered == [10_050_000_000]
      assert sd.sm.logMonoTime['driverMonitoringState'] == 10_050_000_000
      assert sd.aol_dm_lateral_inhibit
      assert not axis.lateralActive and not command.latActive
      if fault == 'alert_three':
        assert sd.sm['driverMonitoringState'].alertLevel == log.DriverMonitoringState.AlertLevel.three
      else:
        assert sd.sm['driverMonitoringState'].lockout
      current_fault[0] = False
      for tick in range(6, 11):
        axis, _, command = drive(tick)
        assert sd.aol_dm_lateral_inhibit
        assert not axis.lateralActive and not command.latActive
      assert delivered == [10_050_000_000, 10_100_000_000]
      assert sd.sm['driverMonitoringState'].alertLevel == log.DriverMonitoringState.AlertLevel.none
      assert not sd.sm['driverMonitoringState'].lockout
      accepted_source = 10_100_000_000
      accepted = sd.aol_ordinary_source_anchor[2]
      assert accepted.carStateLogMonoTime == accepted_source
      assert accepted.allowedLatch and accepted.lateralArmed and card.aol_card_intent.allowed_latch
      axis, _, command = drive(14, timeout=True, state_stamp=accepted_source,
        intent_message=intent(accepted_source, 11))
      assert sd.aol_ordinary_source_pause
      assert sd.aol_dm_lateral_inhibit
      assert axis.sourceCarStateMonoTime == 0 and not sd.conditional_car_state_valid
      assert not axis.lateralActive and not axis.longitudinalActive
      assert not command.latActive and not command.longActive
      assert not axis.desiredLateral and not axis.nativeAcknowledged
