import unittest
from types import SimpleNamespace

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.starpilot.longitudinal.vehicle_policy import stopping_decel_rate


class TestG90StopRate(unittest.TestCase):
  def test_actual_controller_stop_ramp_and_default_scope(self):
    state = structs.CarState()
    for candidate in (CAR.GENESIS_G90, CAR.GENESIS_G80):
      for alpha in (False, True):
        cp = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], alpha, False, False)
        controller = LongControl(cp)
        rate = 0.55 if candidate == CAR.GENESIS_G90 and cp.openpilotLongitudinalControl else 1.0
        for frame in range(60):
          output = controller.update(True, state.as_reader(), -2., True, (-3.5, 2.))
          self.assertAlmostEqual(output, -rate * (frame + 1) * 0.01)
        self.assertEqual(controller.update(False, state.as_reader(), -2., True, (-3.5, 2.)), 0)

  def test_other_vehicle_policy_retains_its_rate(self):
    cp = CarInterface.get_params(CAR.GENESIS_G80, gen_empty_fingerprint(), [], True, False, False)
    self.assertEqual(stopping_decel_rate(cp, SimpleNamespace(stopping_decel_rate=0.8)), 0.8)
