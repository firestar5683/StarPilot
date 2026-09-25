"""EV9's distinct profile runs the shared stock ownership contract."""
import unittest

from opendbc.safety.tests.test_hyundai_ioniq5_pe_stock import HyundaiOrdinaryAngleOwnershipChecks


class TestEv9StockOwnership(HyundaiOrdinaryAngleOwnershipChecks, unittest.TestCase):
  DEFAULT_PARAM = 0x5C91

  def test_ev9_geometry_has_its_own_40kph_rate_boundary(self):
    # At 40 km/h the measured EV9 geometry permits eleven CAN angle units/frame;
    # the PE bank permits only ten. This catches an accidental bank10 alias.
    for _ in range(6):
      self.feed(speed=40.0)
    self.assertAlmostEqual(self.safety.get_vehicle_speed_min(), 40.0 / 3.6, places=3)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.assertTrue(self.safety.safety_tx_hook(self.frame(angle=1.1)))
    self.assertFalse(self.safety.safety_tx_hook(self.frame(1, angle=2.3)))

    # Fresh PE acquisition at the same physical speed must reject the EV9
    # boundary, while accepting its own. Geometry identity is not interchangeable.
    self.reset(0x5491)
    for _ in range(6):
      self.feed(speed=40.0)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.assertFalse(self.safety.safety_tx_hook(self.frame(angle=1.1)))
    self.assertTrue(self.safety.safety_tx_hook(self.frame(angle=1.0)))
