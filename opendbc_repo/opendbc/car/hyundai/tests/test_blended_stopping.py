import unittest
from unittest.mock import patch

from opendbc.car.structs import car
from opendbc.car.hyundai.blended_longitudinal import alpha_eligible, candidate_from_stock
from opendbc.car.hyundai.tests.test_palisade_2023 import params
from opendbc.car.hyundai.values import HyundaiFlags
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.starpilot.longitudinal.extension import LongitudinalContext

State = car.CarControl.Actuators.LongControlState


class TestBlendedStopping(unittest.TestCase):
  def setUp(self):
    self.scope = patch('opendbc.car.hyundai.blended_longitudinal.BLENDED_ALPHA_STARTUP_ENABLED', True)
    self.scope.start()
    self.addCleanup(self.scope.stop)
    self.cp = candidate_from_stock(params(), alpha_requested=True, native_qualified=True)
    self.cs = car.CarState()
    self.cs.canValid = True
    self.cs.cruiseState.standstill = True

  def control(self):
    return LongControl(self.cp)

  def update(self, control, target, *, stop=False, active=True, lead=False):
    return control.update(active, self.cs, target, stop, (-3.5, 2.0),
                          context=LongitudinalContext(has_lead=lead))

  def test_actual_loop_original_ramp_and_unclamped_floor(self):
    control = self.control()
    self.assertAlmostEqual(control.stopping_decel_rate, .35)
    self.assertFalse(control.extension.starting)
    control.last_output_accel = .2
    self.assertAlmostEqual(self.update(control, -1, stop=True), -.0035)
    for frame in range(1, 20):
      self.assertAlmostEqual(self.update(control, -1, stop=True), -.0035 * (frame + 1))
    control.last_output_accel = -.849
    self.assertAlmostEqual(self.update(control, -1, stop=True), -.8525)
    self.assertAlmostEqual(self.update(control, -1, stop=True), -.8525)

  def test_actual_loop_release_35_frames_and_reset_boundary(self):
    control = self.control()
    self.update(control, -.5, stop=True)
    for _ in range(34):
      self.update(control, .2)
      self.assertEqual(control.long_control_state, State.stopping)
    self.update(control, .2)
    self.assertEqual(control.long_control_state, State.pid)
    self.update(control, -.5, stop=True)
    for _ in range(20):
      self.update(control, .2)
    self.update(control, .15)
    self.assertEqual(control.extension.stopping_policy.release_counter, 0)
    for _ in range(34):
      self.update(control, .2)
      self.assertEqual(control.long_control_state, State.stopping)
    self.cs.brakePressed = True
    self.update(control, .8, lead=True)
    self.assertEqual(control.extension.stopping_policy.release_counter, 0)
    self.cs.brakePressed = False
    self.update(control, .2, active=False)
    self.assertEqual(control.long_control_state, State.off)
    self.assertEqual(control.extension.stopping_policy.release_counter, 0)

  def test_actual_loop_original_immediate_release_thresholds(self):
    for speed, target, lead, standstill, expected in [
        (.5, .15, False, True, State.stopping),
        (.5001, 0, False, True, State.pid),
        (0, .1501, True, True, State.pid),
        (0, .15, True, True, State.stopping),
        (0, .45, False, False, State.pid),
        (0, .45, False, True, State.stopping)]:
      with self.subTest(speed=speed, target=target, lead=lead, standstill=standstill):
        control = self.control()
        self.cs.vEgo = speed
        self.cs.cruiseState.standstill = standstill
        control.long_control_state = State.stopping
        self.update(control, target, lead=lead)
        self.assertEqual(control.long_control_state, expected)
        self.assertNotEqual(control.long_control_state, State.starting)

  def test_exact_policy_gate_stock_and_fca_topology(self):
    with patch('opendbc.car.hyundai.blended_longitudinal.BLENDED_ALPHA_STARTUP_ENABLED', False):
      self.assertIsNone(self.control().extension)
    self.assertIsNone(LongControl(params()).extension)
    hdai = params()
    hdai.flags |= HyundaiFlags.USE_FCA.value
    self.assertFalse(alpha_eligible(hdai))
    self.assertIsNone(candidate_from_stock(hdai, alpha_requested=True, native_qualified=True))
    hdaii = params('hdaii')
    hdaii.flags |= HyundaiFlags.USE_FCA.value
    self.assertTrue(alpha_eligible(hdaii))
    candidate = candidate_from_stock(hdaii, alpha_requested=True, native_qualified=True)
    self.assertEqual(candidate.safetyConfigs[0].safetyParam, 0x2014)
    self.assertAlmostEqual(LongControl(candidate).stopping_decel_rate, .35)
