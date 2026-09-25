from openpilot.starpilot.longitudinal.tests.extension_helpers import extension_state
import os
import unittest
from unittest.mock import patch

from opendbc.car.gm.tests.test_bolt_factory_acc import factory_params
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls


class TestBoltFactoryAccPolicy(unittest.TestCase):
  def test_actual_controls_constructor_selects_factory_owner(self):
    for alpha in (False, True):
      with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        cp = factory_params(alpha=alpha)
        Params().put('CarParams', cp.to_bytes(), block=True)
        controls = Controls()
        self.assertEqual(controls.longitudinal_inputs.gm_euv_enabled, alpha)
        self.assertEqual(extension_state(controls.LoC, 'bolt_mode') is not None, alpha)
        self.assertEqual(extension_state(controls.LoC, 'vehicle_policy') is not None, alpha)
        if alpha:
          self.assertIn('radarState', controls.sm.services)
          self.assertIn('deviceState', controls.sm.services)
