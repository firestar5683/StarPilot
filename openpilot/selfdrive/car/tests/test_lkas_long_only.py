"""The physical LKAS gesture must stop lateral output during ordinary engagement."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from opendbc.can import CANParser
from opendbc.car import Bus
from opendbc.car.hyundai.tests.test_ioniq6_longitudinal import controller_fixture
from opendbc.car.hyundai.values import DBC
from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.car.structs import car
from openpilot.cereal import log, messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car.card import Car
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
from openpilot.starpilot.aol.wire import SafetyState, decode_intent, encode_safety
from openpilot.starpilot.audio.axis_alerts import AudibleAlert, AxisAlerts
from openpilot.starpilot.ui.onroad import axis_status_color
from openpilot.starpilot.ui.onroad_state import OnroadState, SpeedLimitObservation


@pytest.mark.parametrize('alt', [False, True])
@pytest.mark.parametrize('prearmed', [False, True])
def test_full_lkas_long_only_actual_owners_output_and_presentation(alt, prearmed):
  with OpenpilotPrefix(), patch.dict('os.environ', {'SIMULATION': '1'}):
    messaging.reset_context()
    cp, controller_cs, controller = controller_fixture(alt, aol=True)
    params = Params()
    params.put_bool('OpenpilotEnabledToggle', True, block=True)
    params.put_bool('AlwaysOnLateral', True, block=True)
    cs = car.CarState(canValid=True, gearShifter=car.CarState.GearShifter.drive, vEgo=20.)
    cs.cruiseState.available = True

    class Interface:
      CP, CC, CS = cp, controller, SimpleNamespace()

      def update(self, _can):
        return cs

    class Radar(RadarInterfaceBase):
      def update(self, _can):
        return None

    card = Car(Interface(), Radar(cp))
    sd, controls = SelfdriveD(), Controls()
    assert card.aol_card_intent.explicit_latch and sd.aol_replay and controls.aol_replay
    sd.initialized = True
    sd.state_machine.state = log.SelfdriveState.OpenpilotState.enabled
    audio = AxisAlerts()
    audio_sm = messaging.SubMaster(['aolIntentWire', 'selfdriveState'])
    now = 10_000_000_000
    captured = {}

    def send(service, message):
      captured[service] = messaging.log_from_bytes(message.to_bytes())

    card.pm, sd.pm = SimpleNamespace(send=send), SimpleNamespace(send=send)
    card.CC_prev = car.CarControl(enabled=True, latActive=True, longActive=True)
    card.aol_card_intent.allowed_latch = prearmed

    def tick(pressed, expected_lateral, *, native_lateral=True):
      nonlocal now
      now += 10_000_000
      cs.buttonEvents = [] if pressed is None else [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=pressed)]
      cc_message = messaging.new_message('carControl', valid=True)
      cc_message.logMonoTime = now
      cc_message.carControl = card.CC_prev
      card.sm.update_msgs(now / 1e9, [cc_message.as_reader()])
      with (patch('openpilot.selfdrive.car.card.messaging.drain_sock_raw', return_value=[b'can']),
            patch('openpilot.selfdrive.car.card.can_capnp_to_list', return_value=[]),
            patch.object(card.sm, 'update'), patch.object(card, 'observe_ioniq6_long_authority'),
            patch('openpilot.cereal.messaging.time.monotonic', return_value=now / 1e9),
            patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=now)):
        parsed, radar = card.state_update()
        card.state_publish(parsed, radar)
      intent = decode_intent(captured['aolIntentWire'].aolIntentWire)
      assert intent.pauseLateral is not expected_lateral
      assert not intent.pauseLongitudinal
      sd.aol_car_state_log_ns = now
      safety = messaging.new_message('aolSafetyWire', 0, valid=True)
      safety.logMonoTime = now
      safety.aolSafetyWire = encode_safety(SafetyState(
        1, True, now, now + 200_000_000, int(cp.safetyConfigs[0].safetyModel.raw), cp.safetyConfigs[0].safetyParam,
        native_lateral, True, native_lateral, True, 'panda', sd.aol_session_id))
      calibration = messaging.new_message('extrinsicsCalibration', valid=True)
      calibration.extrinsicsCalibration.calStatus = log.ExtrinsicsCalibration.Status.calibrated
      sd.sm.update_msgs(now / 1e9, [captured['aolIntentWire'], safety.as_reader(), calibration.as_reader()])
      with (patch.object(sd, 'data_sample', return_value=parsed),
            patch.object(sd, 'update_events', side_effect=lambda _: sd.events.clear()),
            patch.object(sd.sm, 'all_checks', return_value=True),
            patch('openpilot.cereal.messaging.time.monotonic', return_value=now / 1e9),
            patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=now)):
        sd.step()
      decision = sd.aol_axis_decision
      assert decision.desired_lateral == expected_lateral
      assert decision.desired_longitudinal and decision.longitudinal_active
      assert decision.lateral_active == (expected_lateral and native_lateral)
      controls.sm.update_msgs(now / 1e9, [captured['carState'], captured['selfdriveState'], captured['aolAxisState'], safety.as_reader()])
      with patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=now):
        command, _ = controls.state_control()
      assert command.enabled and command.longActive
      assert command.latActive == decision.lateral_active
      if not expected_lateral:
        assert command.actuators.torque == 0.
      _, frames = controller.update(command.as_reader(), controller_cs, now)
      parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [('LFA', 0)], 1)
      parser.update((now, [next(frame for frame in frames if frame[0] == 0x12A)]))
      assert parser.vl['LFA']['ActToiSta'] == int(command.latActive)
      if not expected_lateral:
        assert parser.vl['LFA']['StrTqReqVal'] == 0
      display = OnroadState(engaged=True, camera_available=False, speed_mps=20., cruise_kph=100.,
                            speed_limit=SpeedLimitObservation(), lateral_active=command.latActive, longitudinal_active=command.longActive)
      color = axis_status_color(display)
      assert (color.r, color.g, color.b) == ((22, 127, 64) if command.latActive else (255, 105, 180))
      audio_sm.update_msgs(now / 1e9, [captured['aolIntentWire'], captured['selfdriveState']])
      sound = audio.update(audio_sm, AudibleAlert.none, now)
      card.CC_prev = command
      controller.frame += controller.frame % 2  # LFA is transmitted at 50 Hz.
      return sound

    assert tick(None, True) == AudibleAlert.none  # Neutral baseline, fully engaged.
    assert tick(True, False) == AudibleAlert.disengage
    assert tick(True, False) == AudibleAlert.none  # A held press cannot rearm.
    assert tick(False, False, native_lateral=False) == AudibleAlert.none
    # Old long-only native acknowledgment cannot grant new lateral output.
    assert tick(True, True, native_lateral=False) == AudibleAlert.engage
    assert tick(False, True) == AudibleAlert.none
