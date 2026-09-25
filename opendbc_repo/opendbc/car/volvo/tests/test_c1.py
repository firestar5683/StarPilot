import unittest
import pytest
from opendbc.can import CANPacker, CANParser
from opendbc.car import structs
from opendbc.car.volvo.values import CAR, DBC
from opendbc.car.volvo.interface import CarInterface
from opendbc.car.volvo.carstate import CarState
from opendbc.car.volvo.carcontroller import CarController


def params(alpha=False, release=False):
  cp = CarInterface.get_non_essential_params(CAR.VOLVO_V40)
  return CarInterface._get_params(cp, CAR.VOLVO_V40, {0: {}, 1: {}, 2: {}}, [], alpha, release, False)


def feed(parsers, time=1000000000, torque=10):
  packer = CANPacker('volvo_v40_2017_pt')
  messages = [
    packer.make_can_msg('VehicleSpeed1', 0, {'VehicleSpeed': 72}),
    packer.make_can_msg('CCButtons', 0, {'ACCResumeBtn': 1}),
    packer.make_can_msg('PSCM1', 0, {'SteeringAngleServo': 12.5, 'LKATorque': torque}),
    packer.make_can_msg('PedalandBrake', 0, {'AccPedal': 5.1, 'BrakePedalActive': 1}),
    packer.make_can_msg('TCM0', 0, {'GearShifter': 3}),
    packer.make_can_msg('ACC', 0, {'SpeedTargetACC': 100}),
    packer.make_can_msg('MiscCarInfo', 0, {'TurnSignal': 1}),
    packer.make_can_msg('FSM0', 2, {'ACCStatusOnOff': 1, 'ACCStatusActive': 1}),
    packer.make_can_msg('FSM1', 2, {}),
  ]
  for parser in parsers.values():
    parser.update([(time, messages)])


class TestVolvoC1Host(unittest.TestCase):
  def test_c1_params_preserve_stock_long(self):
    for alpha in [False, True]:
      for release in [False, True]:
        with self.subTest(alpha=alpha, release=release):
          cp = params(alpha, release)
          assert (cp.safetyConfigs[0].safetyModel, cp.safetyConfigs[0].safetyParam) == (structs.CarParams.SafetyModel.volvo, 2)
          assert not cp.openpilotLongitudinalControl and (not cp.alphaLongitudinalAvailable)
          assert cp.pcmCruise and cp.radarUnavailable
          assert cp.steerControlType == structs.CarParams.SteerControlType.angle
          assert cp.minSteerSpeed == pytest.approx(1 / 3.6)
          assert cp.steerActuatorDelay == pytest.approx(0.2)

  def test_c1_required_can_and_state_contract(self):
    cp = params()
    cs = CarState(cp)
    parsers = cs.get_can_parsers(cp)
    feed(parsers)
    assert all(parser.can_valid for parser in parsers.values())
    ret = cs.update(parsers)
    assert ret.vEgoRaw == pytest.approx(20)
    assert ret.steeringAngleDeg == pytest.approx(12.5, abs=0.03)
    assert ret.steeringTorque == 10
    assert ret.gasPressed and ret.brakePressed
    assert ret.gearShifter == structs.CarState.GearShifter.drive
    assert ret.cruiseState.available and ret.cruiseState.enabled
    assert ret.cruiseState.speed == pytest.approx(100 / 3.6)
    assert ret.leftBlinker and (not ret.rightBlinker)
    assert len(ret.buttonEvents) == 1 and ret.buttonEvents[0].pressed
    assert not ret.steeringPressed and (not ret.doorOpen) and (not ret.seatbeltUnlatched)
    assert not ret.steerFaultTemporary and (not ret.steerFaultPermanent)
    for index in range(6):
      for parser in parsers.values():
        parser.update([(3000000000 + index * 10000000, [])])
        _ = parser.can_valid
    assert not all(parser.can_valid for parser in parsers.values())

  def test_c1_recovery_and_cancel_cadence_are_distinct(self):
    cp = params()
    cs = CarState(cp)
    parsers = cs.get_can_parsers(cp)
    feed(parsers, torque=0)
    cs.out = cs.update(parsers)
    controller = CarController(DBC[CAR.VOLVO_V40], cp)
    cc = structs.CarControl.new_message()
    cc.latActive = True
    cc.cruiseControl.cancel = True
    cc.actuators.steeringAngleDeg = 12.5
    decoder = CANParser('volvo_v40_2017_pt', [('FSM1', 0), ('CCButtons', 0)], 0)
    types = []
    cancel_frames = []
    for frame in range(124):
      _, messages = controller.update(cc.as_reader(), cs, frame * 10000000)
      if frame % 2 == 0:
        assert {msg[0] for msg in messages if msg[0] != 16} == {208, 293}
        decoder.update([(1000000000 + frame * 10000000, messages)])
        types.append((frame, decoder.vl['FSM1']['LKASteerDirection']))
      else:
        assert not any(msg[0] in (208, 293) for msg in messages)
      if any(msg[0] == 16 for msg in messages):
        cancel_frames.append(frame)
    assert cancel_frames == list(range(0, 124, 10))
    assert all((direction == 3 for frame, direction in types if frame < 22))
    assert all((direction == 0 for frame, direction in types if 22 <= frame < 122))
    assert types[-1] == (122, 3)
    assert not cp.openpilotLongitudinalControl

  def test_c1_complete_fingerprint_identifies_unique_vehicle(self):
    for capture in range(3):
      with self.subTest(capture=capture):
        from types import SimpleNamespace
        from opendbc.car.fingerprints import all_legacy_fingerprint_cars, eliminate_incompatible_cars
        from opendbc.car.volvo.fingerprints import FINGERPRINTS

        candidates = all_legacy_fingerprint_cars()
        for address, size in FINGERPRINTS[CAR.VOLVO_V40][capture].items():
          candidates = eliminate_incompatible_cars(SimpleNamespace(address=address, dat=bytes(size)), candidates)
        assert candidates == [CAR.VOLVO_V40]
        assert not eliminate_incompatible_cars(SimpleNamespace(address=293, dat=bytes(7)), [CAR.VOLVO_V40])

  def test_host_output_matches_native_sign_relay_and_limits(self):
    for active in [False, True]:
      with self.subTest(active=active):
        from opendbc.safety.tests import test_volvo_c1 as native

        cp = params()
        cs = CarState(cp)
        parsers = cs.get_can_parsers(cp)
        feed(parsers, torque=10)
        cs.out = cs.update(parsers)
        controller = CarController(DBC[CAR.VOLVO_V40], cp)
        cc = structs.CarControl.new_message()
        cc.latActive = active
        cc.cruiseControl.cancel = True
        cc.actuators.steeringAngleDeg = 15
        native.reset()
        native.lib.set_angle_meas(284, 284)
        native.lib.set_desired_angle_last(284)
        for _ in range(6):
          native.rx('VehicleSpeed1', 0, {'VehicleSpeed': 72})
        native.lib.set_controls_allowed(True)
        for frame in range(100):
          cc.latActive = active and frame >= 2
          _, messages = controller.update(cc.as_reader(), cs, frame * 10000000)
          for message in messages:
            assert native.lib.safety_tx_hook(native.packet(message)), (active, frame, message)
