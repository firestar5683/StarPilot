"""Default control remains native when no vehicle extension is selected."""
from types import SimpleNamespace
import unittest

from opendbc.car import structs
from openpilot.selfdrive.controls.lib.longcontrol import LongControl, LongCtrlState
from openpilot.starpilot.longitudinal.extension import LongitudinalContext


class TestDefaultLongitudinalControl(unittest.TestCase):
  def test_no_extension_pid_stop_clip_and_reset_contract(self):
    cp = structs.CarParams()
    cp.stopAccel = -0.25
    cp.longitudinalTuning.kiBP = [0.0]
    cp.longitudinalTuning.kiV = [0.1]
    controller = LongControl(cp)
    self.assertIsNone(controller.extension)
    state = SimpleNamespace(vEgo=12.0, aEgo=0.25, brakePressed=False, cruiseState=SimpleNamespace(standstill=False))
    # Unselected optional evidence cannot change the shared controller.
    context = LongitudinalContext(has_lead=True, experimental_mode=True, start_evidence=object())
    for tick in range(20):
      output = controller.update(True, state, 1.0, False, (-4.0, 2.0), context=context)
      self.assertAlmostEqual(output, 1.0 + (tick + 1) * 0.00075)
      self.assertEqual(controller.long_control_state, LongCtrlState.pid)
    self.assertEqual(controller.update(True, state, 5.0, False, (-4.0, 2.0)), 2.0)
    self.assertEqual(controller.update(True, state, -5.0, False, (-4.0, 2.0)), -4.0)
    controller.update(True, state, -1.0, True, (-4.0, 2.0))
    self.assertEqual(controller.long_control_state, LongCtrlState.stopping)
    previous = controller.last_output_accel
    controller.reset(reset_start=False)
    self.assertEqual(controller.long_control_state, LongCtrlState.stopping)
    self.assertEqual(controller.last_output_accel, previous)
    self.assertEqual(controller.pid.i, 0.0)
    controller.reset()
    self.assertEqual(controller.long_control_state, LongCtrlState.stopping)
    self.assertEqual(controller.update(False, state, 1.0, False, (-4.0, 2.0)), 0.0)
    self.assertEqual(controller.long_control_state, LongCtrlState.off)
    self.assertAlmostEqual(controller.update(True, state, 1.0, False, (-4.0, 2.0)), 1.00075)
