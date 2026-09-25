import unittest

from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py


class TestAolDefensiveRxConfiguration(unittest.TestCase):
  def test_vehicle_policy_is_removed_on_mode_change(self):
    safety = libsafety_py.libsafety
    # allOutput is registered only in DEBUG; detect the loaded build without
    # inferring expected authority from the vehicle policy being tested.
    debug_build = safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) == 0
    expected_request = 3 if debug_build else 0
    for mode, param in ((CarParams.SafetyModel.hondaBosch, 0x22),
                        (CarParams.SafetyModel.hyundaiCanfd, 0x8815)):
      with self.subTest(mode=mode):
        self.assertEqual(safety.set_safety_hooks(mode, param), 0)
        safety.set_aol_test_heartbeat(True)
        safety.aol_set_host_request(3)
        self.assertEqual(safety.aol_get_request_mask(), expected_request)
        if not debug_build:
          self.assertEqual(safety.aol_get_permission_mask(), 0)
        self.assertEqual(safety.set_safety_hooks(CarParams.SafetyModel.noOutput, 0), 0)
        safety.aol_set_host_request(3)
        self.assertEqual(safety.aol_get_request_mask(), 0)
        self.assertEqual(safety.aol_get_permission_mask(), 0)
        # Re-enter the previous profile without a new request: no latent
        # axis request survives the intervening noOutput mode.
        self.assertEqual(safety.set_safety_hooks(mode, param), 0)
        self.assertEqual(safety.aol_get_request_mask(), 0)
        self.assertEqual(safety.aol_get_permission_mask(), 0)

  def test_empty_null_low_frequency_and_stale_configs_deny_health(self):
    # These malformed configurations cannot arise from a production safety
    # hook. The native fixture restores the active configuration after each
    # check; they exercise defense-in-depth guards without relaxing a mode.
    safety = libsafety_py.libsafety
    safety.set_timer(1_000_000)
    for canfd in (False, True):
      with self.subTest(canfd=canfd, variant="valid"):
        self.assertTrue(safety.safety_test_rx_health_fixture(4, canfd))
      for variant in (0, 1, 2, 3):
        with self.subTest(canfd=canfd, variant=variant):
          self.assertFalse(safety.safety_test_rx_health_fixture(variant, canfd))


if __name__ == "__main__":
  unittest.main()
