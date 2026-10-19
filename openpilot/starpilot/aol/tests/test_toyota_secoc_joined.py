"""Fresh factory CAN -> native permission -> SD/Controls -> Card send path.

CAN and transport are synthetic; all production owners and source envelopes run.
No old parsed CarState is restamped and no actuator command bypasses Card.
"""
from contextlib import ExitStack
from unittest import mock

from opendbc.car import structs
from opendbc.car.secoc import add_mac
from opendbc.safety.tests.libsafety import libsafety_py
from openpilot.cereal import messaging
from openpilot.starpilot.aol.tests.test_ioniq_availability import IoniqAvailabilityTests
from openpilot.starpilot.aol.tests.test_toyota_secoc import TEST_KEY, actual_card, parsed_state
from openpilot.starpilot.aol.wire import decode_safety


class CapturePublisher:
  def __init__(self):
    self.messages = {}

  def send(self, service, message):
    raw = message if isinstance(message, bytes) else message.to_bytes()
    self.messages[service] = messaging.log_from_bytes(raw)


def test_fresh_secoc_source_permission_sd_controls_card_sendcan_join():
  case = IoniqAvailabilityTests(methodName='runTest')
  with actual_card(simulation=False) as (selected, _), ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    sd, controls, step = case._authority_callers(
      False, cp=selected.CP.as_reader().as_builder(), genuine_events=True)
    assert not selected.sm.simulation and not sd.sm.simulation and not controls.sm.simulation
    capture = CapturePublisher()
    cleanup.enter_context(mock.patch.object(selected, 'pm', capture))
    cleanup.enter_context(mock.patch('openpilot.selfdrive.car.card.REPLAY', False))
    transition = cleanup.enter_context(mock.patch.object(sd.state_machine, 'update', wraps=sd.state_machine.update))
    apply = cleanup.enter_context(mock.patch.object(selected.CI, 'apply', wraps=selected.CI.apply))
    original_update_msgs = controls.sm.update_msgs
    def model_target(timestamp, messages):


      selected_messages = []
      for message in messages:
        if message.which() == 'modelV2':
          target = message.as_builder()
          target.modelV2.action.desiredCurvature = 0.002
          selected_messages.append(target.as_reader())
        else:
          selected_messages.append(message)
      return original_update_msgs(timestamp, selected_messages)
    cleanup.enter_context(mock.patch.object(controls.sm, 'update_msgs', side_effect=model_target))
    safety = libsafety_py.libsafety
    safety.init_tests()
    safety.set_alternative_experience(32)
    safety.set_safety_hooks(structs.CarParams.SafetyModel.toyota, 2121)
    def reset_native():
      safety.set_alternative_experience(0)
      safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)
    cleanup.callback(reset_native)
    base = 10_000_000_000
    warm, _ = parsed_state(selected.CI, now_ns=base - 80_000_000)
    assert warm.canValid and not warm.canTimeout
    original_message = messaging.new_message
    driving_torques = []
    for tick, gear in enumerate((3,) * 12 + (0,)):
      now = base + tick * 10_000_000
      def clocked_message(*args, _stamp=now, **kwargs):
        message = original_message(*args, **kwargs)
        if 'logMonoTime' not in kwargs:
          message.logMonoTime = _stamp
        return message


      with mock.patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=now), \
           mock.patch('openpilot.selfdrive.car.card.messaging.new_message', side_effect=clocked_message):
        physical, frames = parsed_state(selected.CI, gear=gear, now_ns=now, ticks=1)
        assert physical.canValid and not physical.canTimeout
        safety.set_timer(now // 1000)
        safety.set_aol_test_heartbeat(True)
        for address, payload, bus in frames:
          assert safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, payload))
        safety.aol_set_host_request(1)
        request = safety.aol_get_request_mask()
        permission = safety.aol_get_permission_mask()
        assert request == 1 and permission == (1 if gear == 3 else 0)
        selected.aol_card_intent.update(physical.as_reader(), now_ns=now)
        selected.state_publish(physical, None)
        car_source = capture.messages['carState']
        intent_source = capture.messages['aolIntentWire']
        assert car_source.valid and car_source.logMonoTime == now
        assert intent_source.logMonoTime == now
        before = transition.call_count
        axis, _, command = step(
          tick, car_state_message=car_source.as_builder(), intent_message=intent_source.as_builder(),
          allowed=bool(permission & 1), long_allowed=False,
          native_request_lat=bool(request & 1), native_request_long=False,
          panda_controls_allowed=False)
        assert transition.call_count == before + 1
        assert axis.sourceCarStateMonoTime == car_source.logMonoTime == now
        assert axis.observedMonoTime == now and axis.validUntilMonoTime == now + 30_000_000
        assert axis.intentProducerSessionId == selected.slc_producer_session
        assert command.latActive == (gear == 3) and not command.longActive
        native = decode_safety(sd.sm['aolSafetyWire'])
        assert native is not None and native.observedMonoTime == now
        assert native.safetyParam == 2121 and native.axisSessionId == axis.sessionId
        assert native.requestedLateral == bool(request & 1)
        assert native.lateralAllowed == bool(permission & 1)
        assert len(native.pandaInventory) == 1
        assert native.pandaInventory[0].safetyParam == 2121
        assert native.pandaInventory[0].alternativeExperience == 32
        control_source = controls.pm.messages['carControl']
        assert control_source.logMonoTime == now


        selected.sm.update_msgs(now / 1e9, [control_source, sd.pm.messages['aolAxisState'],
          sd.pm.messages['onroadEvents'], sd.pm.messages['selfdriveState']])
        counter = selected.CI.CC.secoc_lka_message_counter
        calls = apply.call_count
        selected.controls_update(physical, control_source.carControl)
        assert apply.call_count == calls + 1
        assert selected.ci_initialized
        sent = capture.messages['sendcan']
        assert sent.valid and abs(int(sent.logMonoTime) - now) <= 1
        frame = next(packet for packet in sent.sendcan if packet.address == 0x2E4)
        steer = (frame.address, bytes(frame.dat), frame.src)
        assert len(steer[1]) == 8
        assert bool(steer[1][0] & 1) == command.latActive
        assert steer == add_mac(bytes.fromhex(TEST_KEY), 1, 1, counter, (steer[0], steer[1][:4], steer[2]))
        assert safety.safety_tx_hook(libsafety_py.make_CANPacket(steer[0], steer[2], steer[1]))
        torque = int.from_bytes(steer[1][1:3], 'big', signed=True)
        if gear == 3:
          driving_torques.append(torque)
          assert abs(torque) <= min(1500, 15 * (tick + 1))
        else:
          assert not axis.lateralActive and torque == 0
    assert any(torque != 0 for torque in driving_torques), 'Fresh joined Controls must produce actual steering torque'
