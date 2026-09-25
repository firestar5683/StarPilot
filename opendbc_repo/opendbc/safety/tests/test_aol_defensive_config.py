"""Generic AOL health/default-denial checks before vehicle adapters exist."""
import unittest
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py


class TestAolDefensiveRxConfiguration(unittest.TestCase):
  def test_nooutput_has_no_axis_request_or_permission(self):
    safety = libsafety_py.libsafety
    self.assertEqual(safety.set_safety_hooks(CarParams.SafetyModel.noOutput, 0), 0)
    safety.aol_set_host_request(3)
    self.assertEqual(safety.aol_get_request_mask(), 0)
    self.assertEqual(safety.aol_get_permission_mask(), 0)

  def test_empty_null_low_frequency_and_stale_configs_deny_health(self):
    safety = libsafety_py.libsafety
    safety.set_timer(1_000_000)
    self.assertTrue(safety.safety_test_rx_health_fixture(4, False))
    for variant in (0, 1, 2, 3):
      with self.subTest(variant=variant):
        self.assertFalse(safety.safety_test_rx_health_fixture(variant, False))
