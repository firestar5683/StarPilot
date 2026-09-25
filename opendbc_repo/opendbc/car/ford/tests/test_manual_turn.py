import unittest
from types import SimpleNamespace

from opendbc.can import CANParser
from opendbc.car import Bus, structs
from opendbc.car.ford import fordcan
from opendbc.car.ford.carcontroller import CarController
from opendbc.car.ford.carstate import CarState
from opendbc.car.ford.manual_turn import HumanTurnDetector, ManualTurnLatch
from opendbc.car.ford.tests.test_three_ports import params as _params
from opendbc.car.ford.values import CAR, DBC


def turn_state(direction=1):
  return SimpleNamespace(out=SimpleNamespace(steeringPressed=True, steeringAngleDeg=-direction * 12.,
                                             steeringTorque=-direction, rightBlinker=direction == 1,
                                             leftBlinker=direction == -1, yawRate=0., vEgoRaw=20.))


def params(candidate):
  cp = _params(candidate)
  if candidate == CAR.FORD_MUSTANG_MACH_E_MK1:
    cp.safetyConfigs[0].safetyParam = 3 if cp.openpilotLongitudinalControl else 2
  return cp


class TestManualTurn(unittest.TestCase):
  def test_detector_preturned_and_new_turn_hold(self):
    for preturned, frames in ((True, 60), (False, 30)):
      detector = HumanTurnDetector()
      if not preturned:
        self.assertFalse(detector.update(True, True, 0.))
      for _ in range(frames - 1):
        self.assertFalse(detector.update(True, True, 46.))
      self.assertTrue(detector.update(True, True, 46.))
      self.assertFalse(detector.update(True, False, 46.))
      self.assertFalse(detector.update(False, True, 46.))

  def test_signed_directional_recovery_and_resets(self):
    command = SimpleNamespace(latActive=True)
    for direction in (-1, 1):
      for desired, current, release in ((.006, .003, False), (.005, .003, True), (0., .003, True), (-.006, .003, True)):
        with self.subTest(direction=direction, desired=desired):
          latch = ManualTurnLatch()
          state = turn_state(direction)
          self.assertTrue(latch.update(command, state, direction * desired, True, False))
          state.out.steeringPressed = False
          state.out.steeringAngleDeg = 0.
          state.out.rightBlinker = state.out.leftBlinker = False
          state.out.yawRate = -direction * current * 20.
          for _ in range(4):
            self.assertTrue(latch.update(command, state, direction * desired, True, False))
          self.assertEqual(latch.update(command, state, direction * desired, True, False), not release)
          self.assertFalse(latch.update(command, state, direction * desired, False, False))
          self.assertEqual(latch.manual_turn_direction, 0.)
          state = turn_state(direction)
          self.assertFalse(latch.update(command, state, .006, True, True))
          self.assertTrue(latch.update(command, state, .006, True, False))
          command.latActive = False
          self.assertFalse(latch.update(command, state, .006, True, False))
          command.latActive = True

  def test_no_signal_direction_and_recovery_interruptions(self):
    latch = ManualTurnLatch()
    command = SimpleNamespace(latActive=True)
    state = turn_state(-1)
    state.out.leftBlinker = False
    state.out.steeringAngleDeg = 46.
    for _ in range(60):
      latched = latch.update(command, state, -.006, True, False)
    self.assertTrue(latched)
    self.assertEqual(latch.manual_turn_direction, -1.)
    for attribute, value in (('steeringPressed', True), ('rightBlinker', True), ('steeringAngleDeg', 13.)):
      state.out.steeringPressed = False
      state.out.rightBlinker = False
      state.out.steeringAngleDeg = 0.
      latch.update(command, state, -.006, True, False)
      setattr(state.out, attribute, value)
      self.assertTrue(latch.update(command, state, -.006, True, False))
      self.assertEqual(latch.manual_turn_recovery_timer, 0.)

  def test_missing_model_blocks_entry_but_preserves_recovery(self):
    command = SimpleNamespace(latActive=True)
    state = turn_state()
    latch = ManualTurnLatch()
    self.assertFalse(latch.update(command, state, .006, True, False, False))
    self.assertTrue(latch.update(command, state, .006, True, False, True))
    state.out.steeringPressed = False
    state.out.rightBlinker = False
    state.out.steeringAngleDeg = 0.
    for _ in range(4):
      self.assertTrue(latch.update(command, state, 0., True, False, False))
    self.assertFalse(latch.update(command, state, 0., True, False, False))

  def test_controller_real_can_yield_counter_and_recovery(self):
    candidate = CAR.FORD_MUSTANG_MACH_E_MK1
    cp = params(candidate)
    state = CarState(cp)
    state.update(state.get_can_parsers(cp))
    out = structs.CarState()
    out.vEgoRaw = 20.
    out.steeringPressed = True
    out.steeringAngleDeg = -12.
    out.steeringTorque = -1.
    out.rightBlinker = True
    state.out = out.as_reader()
    command = structs.CarControl()
    command.latActive = True
    command.actuators.curvature = .006
    controller = CarController(DBC[candidate], cp)
    controller.manual_turn_inputs = SimpleNamespace(update=lambda: (True, False, True))
    parser = CANParser(DBC[candidate][Bus.pt], [('LateralMotionControl2', 20)], controller.CAN.main)
    for index in range(10):
      controller.frame = index * 5
      if index == 1:
        out.steeringPressed = False
        out.steeringAngleDeg = 0.
        out.rightBlinker = False
      if index == 7:
        command.actuators.curvature = -.001
      state.out = out.as_reader()
      _, messages = controller.update(command.as_reader(), state, (index + 1) * 50_000_000)
      wire = next(message for message in messages if message[0] == 0x3D6)
      expected = fordcan.create_lat_ctl2_msg(controller.packer, controller.CAN, int(index >= 7), 0., 0.,
                                            -controller.apply_curvature_last, 0., index)
      self.assertEqual(wire, expected)
      parser.update([((index + 1) * 50_000_000, messages)])
      values = parser.vl['LateralMotionControl2']
      self.assertEqual(values['LatCtlPath_No_Cnt'], index)
      self.assertEqual(values['LatCtl_D2_Rq'], int(index >= 7))
      if index < 7:
        self.assertAlmostEqual(values['LatCtlCurv_No_Actl'], 0., places=5)
        self.assertEqual(controller.apply_curvature_last, 0.)
      self.assertTrue(parser.can_valid)

  def test_other_platform_and_lka_do_not_create_inputs(self):
    for candidate in (CAR.FORD_BRONCO_SPORT_MK1, CAR.FORD_TRANSIT_MK5):
      cp = params(candidate)
      controller = CarController(DBC[candidate], cp)
      self.assertIsNone(controller.manual_turn)
      state = CarState(cp)
      state.update(state.get_can_parsers(cp))
      state.out = structs.CarState().as_reader()
      controller.update(structs.CarControl().as_reader(), state, 0)
