from openpilot.starpilot.longitudinal.tests.extension_helpers import extension_state
from types import SimpleNamespace
import unittest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR
from opendbc.car.gm.bolt_cc import BoltCcLongitudinalPolicy
from opendbc.car.gm.longitudinal import GMPedalLongitudinalPolicy
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.longcontrol import LongControl


def params(identity, pedal=False):
  fingerprint = gen_empty_fingerprint()
  fingerprint[2][0x320] = 8
  fingerprint[2][0x180] = 4
  if pedal:
    fingerprint[0][0x201] = 6
  return CarInterface.get_params(identity, fingerprint, [], False, False, False)


class TestBoltCcIntegrator(unittest.TestCase):
  def test_actual_longcontrol_reduces_stale_positive_integrator_during_deceleration(self):
    for identity in (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021, CAR.CHEVROLET_BOLT_CC_2022_2023):
      controller = LongControl(params(identity))
      self.assertIsInstance(extension_state(controller, 'vehicle_policy'), BoltCcLongitudinalPolicy)
      controller.pid.i = 0.8
      state = structs.CarState.new_message()
      state.vEgo, state.aEgo = 28.0, 0.2
      output = controller.update(True, state, -0.2, False, (-3.0, 2.0))
      expected_i = 0.8 * 0.46 + controller.pid.k_i * DT_CTRL * -0.4
      self.assertAlmostEqual(controller.pid.i, expected_i)
      self.assertAlmostEqual(output, 2.0 * -0.4 + expected_i - 0.2)
      controller.reset()
      self.assertEqual(controller.pid.i, 0.0)

  def test_actual_longcontrol_caps_positive_command_on_negative_target(self):
    controller = LongControl(params(CAR.CHEVROLET_BOLT_CC_2018_2021))
    controller.pid.i = 2.0
    state = structs.CarState.new_message()
    state.vEgo, state.aEgo = 28.0, 0.16
    output = controller.update(True, state, -0.2, False, (-3.0, 2.0))
    self.assertAlmostEqual(output, 0.04)

  def test_active_pedal_retains_its_existing_policy_and_creep_exclusion(self):
    controller = LongControl(params(CAR.CHEVROLET_BOLT_CC_2018_2021, pedal=True))
    self.assertIsInstance(extension_state(controller, 'vehicle_policy'), GMPedalLongitudinalPolicy)
    policy = BoltCcLongitudinalPolicy()
    pid = SimpleNamespace(i=0.8)
    policy.prepare_pid(pid, -0.2, -0.4, 0.35, 0, (-3, 2))
    self.assertEqual(pid.i, 0.8)
    self.assertEqual(policy.shape_output(0.3, -0.2, -0.4, 0.35), 0.3)
    controller.pid.i = 0.8
    extension_state(controller, 'vehicle_policy').prepare_pid(controller.pid, -0.2, -0.4, 28.0, 0, (-3, 2))
    self.assertAlmostEqual(controller.pid.i, 0.368)
