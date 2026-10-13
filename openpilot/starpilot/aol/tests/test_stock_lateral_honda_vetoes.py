"""Stock Honda source gaps retain every physical and configuration veto."""

from unittest import mock
import pytest
from opendbc.car.structs import car
from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import honda_family_case as family_case


@pytest.mark.parametrize(
  'veto', ['wrong_make', 'unmarked', 'wrong_config', 'dm_lockout', 'physical_cancel', 'brake', 'main_off', 'speed_too_low', 'mixed_immediate']
)
def test_honda_host_gap_retains_every_non_nominal_veto(veto):
  with OpenpilotPrefix():
    case = family_case('honda', False)
    try:
      sd, controls, step, card, receive = case.family_callers(False)
      baseline, _, command = step(2)
      assert baseline.lateralActive and command.latActive
      accepted = messaging.new_message('aolIntentWire', 0, valid=sd.sm.valid['aolIntentWire'], logMonoTime=sd.sm.logMonoTime['aolIntentWire'])
      accepted.aolIntentWire = sd.sm['aolIntentWire']
      assert accepted.logMonoTime == baseline.sourceCarStateMonoTime
      original_events = sd.update_events

      def events(state):
        result = original_events(state)
        sd.events.add(log.OnroadEvent.EventName.selfdrivedLagging)
        if veto == 'dm_lockout':
          frame = messaging.new_message('driverMonitoringState', valid=True, logMonoTime=10_055_000_000)
          frame.driverMonitoringState = sd.sm['driverMonitoringState']
          frame.driverMonitoringState.lockout = True
          sd.sm.update_msgs(10.055, [frame.as_reader()])
        elif veto == 'speed_too_low':
          sd.events.add(log.OnroadEvent.EventName.speedTooLow)
        elif veto == 'mixed_immediate':
          sd.events.add(log.OnroadEvent.EventName.controlsMismatch)
        return result

      if veto in ('wrong_make', 'unmarked', 'wrong_config'):
        cp = sd.CP.as_builder()
        if veto == 'wrong_make':
          cp.brand = 'hyundai'
        elif veto == 'unmarked':
          cp.alternativeExperience = 0
        else:
          cp.safetyConfigs[0].safetyParam ^= 1
        sd.CP = cp.as_reader()
      elif veto in ('physical_cancel', 'brake', 'main_off'):
        # Deliver a NEW actual serialized CarState envelope through the fixture's
        # receive boundary. Never mutate a previously accepted immutable reader.
        from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import car_state

        physical = car_state()
        if veto == 'physical_cancel':
          physical.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
        elif veto == 'brake':
          physical.brakePressed = True
        else:
          physical.cruiseState.available = False
        # The generic step forces available=True on its supplied state. Change
        # only its CAN-receive serialization hook for this main-off envelope.
        saved_receive = messaging.recv_one

        def receive_main_off(sock):
          frame = saved_receive(sock)
          if sock is sd.car_state_sock and frame is not None:
            copied = frame.as_builder()
            copied.carState.cruiseState.available = False
            return messaging.log_from_bytes(copied.to_bytes())
          return frame

        with (
          mock.patch.object(messaging, 'recv_one', side_effect=receive_main_off)
          if veto == 'main_off'
          else mock.patch.object(messaging, 'recv_one', wraps=saved_receive)
        ):
          denied, _, fault_command = step(3, observed_state=physical)
        witnessed = sd.CS_prev
        if veto == 'physical_cancel':
          assert any(e.type == car.CarState.ButtonEvent.Type.cancel and e.pressed for e in witnessed.buttonEvents)
        elif veto == 'brake':
          assert witnessed.brakePressed
        else:
          assert not witnessed.cruiseState.available
        # Freeze the exact fault-source intent received during this real step.
        accepted = messaging.new_message('aolIntentWire', 0, valid=sd.sm.valid['aolIntentWire'], logMonoTime=sd.sm.logMonoTime['aolIntentWire'])
        accepted.aolIntentWire = sd.sm['aolIntentWire']
      with mock.patch.object(sd, 'update_events', side_effect=events):
        off, _, command = step(6 if veto in ('physical_cancel', 'brake', 'main_off') else 5, timeout=True, offset_ns=5_000_000, intent_message=accepted)
      assert not off.lateralActive and not off.longitudinalActive
      assert not command.latActive and not command.longActive
      assert str(off.faultReason) != 'availabilityPause', (veto, off.to_dict())
    finally:
      case.doCleanups()
