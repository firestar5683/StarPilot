from openpilot.starpilot.longitudinal.extension import LongitudinalContext
from openpilot.starpilot.longitudinal.tests.extension_helpers import extension_state
import os
import unittest
from unittest.mock import patch

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR
from opendbc.car.gm.bolt_mode import policy_for
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.lib.longcontrol import LongControl


def params(identity, pedal=False, alpha=False):
  fingerprint = gen_empty_fingerprint()
  fingerprint[2][0x320] = 8
  fingerprint[2][0x180] = 4
  if pedal:
    fingerprint[0][0x201] = 6
  return CarInterface.get_params(identity, fingerprint, [], alpha, False, False)


def state():
  cs = structs.CarState.new_message()
  cs.vEgo = 28.0
  cs.canValid = True
  cs.gearShifter = structs.CarState.GearShifter.drive
  cs.cruiseState.available = cs.cruiseState.enabled = True
  return cs


class TestBoltModeTransition(unittest.TestCase):
  def test_actual_longcontrol_transition_stale_hold_and_reset(self):
    for identity, pedal, alpha in ((CAR.CHEVROLET_BOLT_CC_2018_2021, False, False),
                                   (CAR.CHEVROLET_BOLT_CC_2018_2021, True, False),
                                   (CAR.CHEVROLET_BOLT_EUV, False, True),
                                   (CAR.CHEVROLET_BOLT_ACC_2022_2023, False, True)):
      cp = params(identity, pedal=pedal, alpha=alpha)
      controller = LongControl(cp)
      self.assertIsNotNone(extension_state(controller, 'bolt_mode'))
      cs = state()
      initial = controller.update(True, cs, -0.5, False, (-3, 2), context=LongitudinalContext(experimental_mode=None))
      self.assertEqual(extension_state(controller, 'bolt_mode').current_mode, 'acc')
      self.assertFalse(extension_state(controller, 'bolt_mode').transitioning)
      self.assertEqual(initial, float(controller.pid.control))
      controller.reset()
      controller.last_output_accel = 0.0
      first = controller.update(True, cs, -0.5, False, (-3, 2), context=LongitudinalContext(experimental_mode=True))
      raw = float(controller.pid.control)
      factor = 1 - .99 * (1 - min(1, abs(raw / -4) ** .4))
      self.assertAlmostEqual(first, raw * factor)
      controller.update(True, cs, -0.5, False, (-3, 2), context=LongitudinalContext(experimental_mode=None))
      self.assertEqual(extension_state(controller, 'bolt_mode').current_mode, 'blended')
      self.assertAlmostEqual(extension_state(controller, 'bolt_mode').timer, .02)
      controller.reset()
      self.assertAlmostEqual(extension_state(controller, 'bolt_mode').timer, .02)
      controller.update(True, cs, -0.5, True, (-3, 2), context=LongitudinalContext(experimental_mode=False))
      self.assertEqual(extension_state(controller, 'bolt_mode').current_mode, 'blended')
      self.assertAlmostEqual(extension_state(controller, 'bolt_mode').timer, .02)
      controller.update(False, cs, -0.5, False, (-3, 2), context=LongitudinalContext(experimental_mode=False))
      self.assertEqual(extension_state(controller, 'bolt_mode').current_mode, 'blended')
      self.assertAlmostEqual(extension_state(controller, 'bolt_mode').timer, .02)
      controller.update(True, cs, 0.5, False, (-3, 2), context=LongitudinalContext(experimental_mode=False))
      self.assertTrue(extension_state(controller, 'bolt_mode').leaving_experimental)
      self.assertEqual(controller.pid.i, 0.0)
      self.assertAlmostEqual(controller.last_output_accel, float(controller.pid.control) * .01)

  def test_only_exact_admitted_bolt_profiles_receive_mode_policy(self):
    for identity in (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021,
                     CAR.CHEVROLET_BOLT_CC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL):
      cp = params(identity, pedal=True)
      self.assertIsNotNone(policy_for(cp))
      cp.safetyConfigs[0].safetyParam |= 0x8000
      self.assertIsNone(policy_for(cp))
    cp = params(CAR.CHEVROLET_BOLT_EUV, alpha=False)
    self.assertIsNone(policy_for(cp))
    cs = state()
    first, second = LongControl(cp), LongControl(cp)
    self.assertEqual(first.update(True, cs, -.5, False, (-3, 2), context=LongitudinalContext(experimental_mode=True)),
                     second.update(True, cs, -.5, False, (-3, 2), context=LongitudinalContext(experimental_mode=False)))

  def test_actual_controls_transports_only_healthy_mode_state(self):
    from openpilot.cereal import messaging
    from openpilot.selfdrive.controls.controlsd import Controls

    with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
      cp = params(CAR.CHEVROLET_BOLT_CC_2018_2021)
      Params().put('CarParams', cp.to_bytes(), block=True)
      controls = Controls()
      controls.sm.simulation = False
      def publish(now, mode, valid=True):
        drive = messaging.new_message('selfdriveState', valid=valid)
        drive.selfdriveState.enabled = drive.selfdriveState.active = True
        drive.selfdriveState.experimentalMode = mode
        vehicle = messaging.new_message('carState', valid=True)
        vehicle.carState = state()
        plan = messaging.new_message('longitudinalPlan', valid=True)
        plan.longitudinalPlan.aTarget = -.5
        controls.sm.update_msgs(now, [messaging.log_from_bytes(msg.to_bytes()) for msg in (drive, vehicle, plan)])
      # Real receive cadence establishes the existing SubMaster frequency guard.
      publish(1.00, False)
      publish(1.01, False)
      self.assertTrue(controls.sm.all_checks(['selfdriveState']))
      command, _ = controls.state_control()
      self.assertTrue(command.longActive)
      self.assertEqual(extension_state(controls.LoC, 'bolt_mode').current_mode, 'acc')
      publish(1.02, True)
      controls.state_control()
      self.assertEqual(extension_state(controls.LoC, 'bolt_mode').current_mode, 'blended')
      publish(1.03, False, valid=False)
      self.assertFalse(controls.sm.all_checks(['selfdriveState']))
      controls.state_control()
      self.assertEqual(extension_state(controls.LoC, 'bolt_mode').current_mode, 'blended')
      controls.sm.update_msgs(1.20, [])
      self.assertFalse(controls.sm.all_checks(['selfdriveState']))
      controls.state_control()
      self.assertEqual(extension_state(controls.LoC, 'bolt_mode').current_mode, 'blended')
      for tick in range(110):
        publish(1.21 + tick * .01, False)
      self.assertTrue(controls.sm.all_checks(['selfdriveState']))
      controls.state_control()
      self.assertEqual(extension_state(controls.LoC, 'bolt_mode').current_mode, 'acc')
