"""Unknown vehicles have no implicit AOL capability or native receipt."""

import unittest
from types import SimpleNamespace

from openpilot.starpilot.aol.vehicle import AolVehiclePolicy, native_matches_cp, native_profile_supported, policy_for


class GenericVehiclePolicyTests(unittest.TestCase):
  def test_unknown_and_malformed_cp_fail_closed(self):
    denied = AolVehiclePolicy()
    for cp in (None, SimpleNamespace(), SimpleNamespace(brand='ford'),
               SimpleNamespace(brand='honda'), SimpleNamespace(brand='hyundai')):
      with self.subTest(cp=cp):
        self.assertEqual(policy_for(cp), denied)
        self.assertFalse(native_matches_cp(cp, 0, 0))

  def test_no_unregistered_native_profile(self):
    self.assertFalse(native_profile_supported(0, 0))
    self.assertFalse(native_profile_supported(999, 0x8815))
