import unittest
from math import isclose

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, structs
from opendbc.car.subaru import subarucan
from opendbc.car.subaru.carcontroller import CarController
from opendbc.car.subaru.carstate import CarState
from opendbc.car.subaru.interface import CarInterface
from opendbc.car.subaru.values import CAR, DBC, SubaruSafetyFlags
from opendbc.safety.tests import test_subaru_gen2_angle_pair as pair


CAR_ID = CAR.SUBARU_ASCENT_2023


def setup_controller(car=CAR_ID):
  cp = CarInterface.get_params(car, {0: {}, 1: {}, 2: {}}, [], False, False, False)
  _, frames = pair.TestSubaruGen2AnglePair.sources(car)
  state = CarState(cp)
  parsers = state.get_can_parsers(cp)
  state.update(parsers)
  for parser in parsers.values():
    parser.update([(1_000_000_000, frames)])
  state.out = state.update(parsers)
  command = structs.CarControl()
  command.enabled = command.latActive = True
  command.actuators.steeringAngleDeg = -1.45
  return cp, CarController(DBC[car], cp), command, state


def step(controller, command, state):
  _, sends = controller.update(command.as_reader(), state, 1_000_000_000 + controller.frame * 10_000_000)
  if controller.frame % 2 == 0:
    _, sends = controller.update(command.as_reader(), state, 1_000_000_000 + controller.frame * 10_000_000)
  steer = next(frame for frame in sends if frame[0] == 0x124)
  parser = CANParser(DBC[controller.CP.carFingerprint][Bus.pt], [('ES_LKAS_ANGLE', 0)], steer[2])
  parser.update([(1, [steer])])
  return steer, parser.vl['ES_LKAS_ANGLE']


class TestSubaruAscentController(unittest.TestCase):
  def test_ascent_admission_and_outback_unchanged(self):
    cp, _, _, state = setup_controller()
    assert not cp.dashcamOnly
    assert not cp.openpilotLongitudinalControl
    assert not cp.alphaLongitudinalAvailable
    assert cp.steerControlType == structs.CarParams.SteerControlType.angle
    assert cp.safetyConfigs[0].safetyParam == (SubaruSafetyFlags.GEN2 | SubaruSafetyFlags.LKAS_ANGLE |
                                             SubaruSafetyFlags.FIXED_ANGLE_LIMITS | SubaruSafetyFlags.ANGLE_MAIN_BUS)
    assert state.out.cruiseState.enabled
    assert state.out.cruiseState.available
    outback = CarInterface.get_non_essential_params(CAR.SUBARU_OUTBACK_2023)
    assert outback.dashcamOnly
    assert outback.safetyConfigs[0].safetyParam == SubaruSafetyFlags.GEN2
    _, controller, command, state = setup_controller(CAR.SUBARU_OUTBACK_2023)
    command.latActive = False
    _, sends = controller.update(command.as_reader(), state, 1_000_000_000)
    assert not any(frame[0] == 0x124 for frame in sends)
    torque = next(frame for frame in sends if frame[0] == 0x122)
    assert torque == subarucan.create_steering_control(CANPacker(DBC[CAR.SUBARU_OUTBACK_2023][Bus.pt]), 0, False)

  def test_first_entry_and_reentry_use_original_transmitted_history(self):
    _, controller, command, state = setup_controller()
    state.out.vEgoRaw = 30.3
    state.out.steeringAngleDeg = 0.78
    state.out.steeringRateDeg = -1.5
    controller.angle_handoff_active = True
    steer, decoded = step(controller, command, state)
    assert steer[2] == 0
    assert decoded['LKAS_Request'] == 0
    assert decoded['LKAS_Output'] == 0.78
    state.out.steeringAngleDeg = 0.74
    state.out.steeringRateDeg = -1.99
    _, decoded = step(controller, command, state)
    assert decoded['LKAS_Request'] == 1
    assert isclose(decoded['LKAS_Output'], 0.53, abs_tol=0.01)

    _, initial, command, state = setup_controller()
    state.out.vEgoRaw = 30.3
    state.out.steeringAngleDeg = 20.0
    state.out.steeringRateDeg = 0.0
    _, decoded = step(initial, command, state)
    assert decoded['LKAS_Request'] == 0
    assert decoded['LKAS_Output'] == 20.0
    _, decoded = step(initial, command, state)
    assert decoded['LKAS_Request'] == 1
    assert 19.7 < decoded['LKAS_Output'] < 20.0

  def test_driver_override_hysteresis_and_settled_handoff(self):
    _, controller, command, state = setup_controller()
    state.out.vEgoRaw = 30.3
    state.out.steeringAngleDeg = -25.06
    state.out.steeringTorque = -250
    state.out.steeringRateDeg = 35
    for _ in range(2):
      _, decoded = step(controller, command, state)
    assert decoded['LKAS_Request'] == 0
    state.out.steeringTorque = -150
    state.out.steeringRateDeg = 0
    _, decoded = step(controller, command, state)
    assert decoded['LKAS_Request'] == 0
    state.out.steeringTorque = -149
    state.out.steeringAngleDeg = -17.91
    _, decoded = step(controller, command, state)
    assert decoded['LKAS_Request'] == 0
    assert decoded['LKAS_Output'] == -17.91
    _, decoded = step(controller, command, state)
    assert decoded['LKAS_Request'] == 1
    assert -17.91 < decoded['LKAS_Output'] < -17.6

  def test_ascent_inactive_follows_measurement_and_requires_stock_permission(self):
    for revocation in ('brake', 'standstill', 'park', 'reverse', 'cruise', 'main', 'disabled', 'lateral'):
      with self.subTest(revocation=revocation):
        _, controller, command, state = setup_controller()
        state.out.steeringAngleDeg = 12.5
        if revocation == 'brake':
          state.out.brakePressed = True
        elif revocation == 'standstill':
          state.out.standstill = True
        elif revocation in ('park', 'reverse'):
          state.out.gearShifter = getattr(structs.CarState.GearShifter, revocation)
        elif revocation == 'cruise':
          state.out.cruiseState.enabled = False
        elif revocation == 'main':
          state.out.cruiseState.available = False
        elif revocation == 'disabled':
          command.enabled = False
        else:
          command.latActive = False
        _, decoded = step(controller, command, state)
        assert decoded['LKAS_Request'] == 0
        assert decoded['LKAS_Output'] == 12.5

  def test_inactive_ascent_preserves_fixed_angle_bound(self):
    for measured in (-600.0, 600.0):
      with self.subTest(measured=measured):
        _, controller, command, state = setup_controller()
        state.out.steeringAngleDeg = measured
        command.latActive = False
        _, decoded = step(controller, command, state)
        assert decoded['LKAS_Request'] == 0
        assert decoded['LKAS_Output'] == (545.0 if measured > 0 else -545.0)
