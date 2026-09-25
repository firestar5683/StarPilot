import unittest
from types import SimpleNamespace

from opendbc.can import CANParser
from opendbc.car import Bus, structs
from opendbc.car.ford.curvature_preview import blend_curvature
from opendbc.car.ford.carcontroller import CarController
from opendbc.car.ford.carstate import CarState
from opendbc.car.ford.tests.test_three_ports import params
from opendbc.car.ford.values import CAR, DBC


class TestCurvaturePreview(unittest.TestCase):
  def test_original_default_signed_preview_and_conservative_overshoot(self):
    for sign in (-1, 1):
      self.assertAlmostEqual(blend_curvature(sign * .001, sign * .002, 0.), sign * .0014)
      self.assertAlmostEqual(blend_curvature(sign * .001, sign * .002, sign * .003), sign * .0012)
      self.assertEqual(blend_curvature(sign * .001, -sign * .002, 0.), sign * .001)
      self.assertEqual(blend_curvature(0., sign * .002, 0.), 0.)
    for bad in (float('nan'), float('inf'), -float('inf')):
      self.assertEqual(blend_curvature(.001, bad, 0.), .001)

  def test_actual_controller_blends_before_unchanged_envelope_and_yields(self):
    cp = params(CAR.FORD_MUSTANG_MACH_E_MK1)
    cp.safetyConfigs[0].safetyParam = 3 if cp.openpilotLongitudinalControl else 2
    controller = CarController(DBC[cp.carFingerprint], cp)
    state = CarState(cp)
    state.update(state.get_can_parsers(cp))
    out = structs.CarState()
    out.vEgoRaw = 20.
    state.out = out.as_reader()
    command = structs.CarControl()
    command.latActive = True
    command.actuators.curvature = .001
    preview = SimpleNamespace(update=lambda: (True, False, True), preview_curvature=lambda speed: .002)
    controller.manual_turn_inputs = preview
    controller.apply_curvature_last = .0014
    from opendbc.car.ford.values import CarControllerParams
    expected = CarControllerParams.CURVATURE_LIMITS.apply_limits(.0014, .0014, 20., 0., True, CarControllerParams.STEER_STEP)
    actual, frames = controller.update(command.as_reader(), state, 0)
    self.assertAlmostEqual(actual.curvature, expected)
    parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [('LateralMotionControl2', 20)], controller.CAN.main)
    parser.update([(50_000_000, frames)])
    self.assertAlmostEqual(parser.vl['LateralMotionControl2']['LatCtlCurv_No_Actl'], -.0014, places=5)
    self.assertEqual(parser.vl['LateralMotionControl2']['LatCtl_D2_Rq'], 1)
    controller.frame = 5
    out.steeringPressed = True
    out.steeringAngleDeg = -12.
    out.steeringTorque = -1.
    out.rightBlinker = True
    state.out = out.as_reader()
    actual, _ = controller.update(command.as_reader(), state, 50_000_000)
    self.assertEqual(actual.curvature, 0.)

  def test_neighbor_controller_does_not_query_preview(self):
    cp = params(CAR.FORD_F_150_MK14)
    controller = CarController(DBC[cp.carFingerprint], cp)
    state = CarState(cp)
    state.update(state.get_can_parsers(cp))
    state.out = structs.CarState(vEgoRaw=20.).as_reader()
    command = structs.CarControl(latActive=True)
    command.actuators.curvature = .001

    def unexpected(speed):
      raise AssertionError('neighbor queried Mach-E preview')
    controller.manual_turn_inputs = SimpleNamespace(preview_curvature=unexpected)
    controller.update(command.as_reader(), state, 0)
