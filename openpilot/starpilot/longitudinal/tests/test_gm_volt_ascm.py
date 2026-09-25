"""Final Volt ASCM configuration selects the established acceleration law and wire path."""
from openpilot.starpilot.longitudinal.extension import LongitudinalContext
from openpilot.starpilot.longitudinal.tests.extension_helpers import extension_state
import os
import unittest
from unittest.mock import patch

from opendbc.car import structs
from opendbc.car.gm.tests.test_ascm_intercept import params
from opendbc.car.gm.tests.test_volt_grade import command
from opendbc.car.gm.values import CAR
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.starpilot.longitudinal.tests.test_gm_volt_long_policy import controls_fixture, observed_lead


class TestVoltAscmLongitudinal(unittest.TestCase):
  def test_actual_pid_output_reaches_original_controller_frames(self):
    # Initial I, requested/measured acceleration, lead state, expected output and wire.
    cases = ((1., -.2, .3, None, .04, '4142c2e000bd3d1f', '1000efff01'),
             (-1., 0., 0., False, -.995, '4142abe000bd541f', 'afff500001'),
             (-1., 0., 0., None, -1., '4142abe000bd541f', 'afff500001'),
             (-1., 0., 0., True, -1., '4142abe000bd541f', 'afff500001'))
    for brake_c9 in (False, True):
      for radar in (False, True):
        cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, accelerator=not brake_c9, radar=radar)
        for integral, target, measured, lead, expected, gas_hex, brake_hex in cases:
          owner = LongControl(cp)
          self.assertIsNotNone(extension_state(owner, 'vehicle_policy'))
          self.assertIsNone(extension_state(owner, 'gm_start'))
          owner.pid.i = integral
          state = structs.CarState(vEgo=12., aEgo=measured, canValid=True)
          output = owner.update(True, state.as_reader(), target, False, (-4., 2.), context=LongitudinalContext(has_lead=lead))
          self.assertAlmostEqual(output, expected)
          _, frames = command(cp, accel=float(output), speed=12., orientation=[])
          self.assertEqual([(address, payload.hex(), bus) for address, payload, bus in frames if address in (0x2cb, 0x315)],
                           [(0x2cb, gas_hex, 0), (0x315, brake_hex, 0)])
          owner.update(False, state.as_reader(), target, False, (-4., 2.), context=LongitudinalContext(has_lead=lead))
          self.assertEqual(owner.pid.i, 0.)
          self.assertEqual(owner.long_control_state, structs.CarControl.Actuators.LongControlState.off)
    stock = LongControl(params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=False))
    self.assertIsNone(extension_state(stock, 'vehicle_policy'))

  def test_fresh_lead_transport_is_required_for_integral_release(self):
    for radar in (False, True):
      controls, now, offset = controls_fixture()
      controls.CP = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, radar=radar)
      controls.longitudinal_inputs.CP = controls.CP
      controls.LoC = LongControl(controls.CP)
      with patch.dict(os.environ, {'REPLAY': '0'}), \
           patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now + offset)):
        for lead in (False, True):
          controls.sm['radarState'].leadTwo.present = lead
          self.assertIs(observed_lead(controls), lead)
          controls.LoC.pid.i = -1.
          cc, _ = controls.state_control()
          self.assertAlmostEqual(cc.actuators.accel, -1. if lead else -.995, places=6)
        for source in ('radarState', 'carState', 'longitudinalPlan'):
          controls.sm.valid[source] = False
          self.assertIsNone(observed_lead(controls))
          controls.LoC.pid.i = -1.
          cc, _ = controls.state_control()
          self.assertAlmostEqual(cc.actuators.accel, -1., places=6)
          controls.sm.valid[source] = True
