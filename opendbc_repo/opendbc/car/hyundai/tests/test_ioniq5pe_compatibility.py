"""The legacy PE helper keeps its identity boundary after shared extraction."""
import unittest

from opendbc.car import structs
from opendbc.car.hyundai import ccnc_ev_stock, ioniq5pe
from opendbc.car.hyundai.tests.test_ioniq5pe_stock import params
from opendbc.car.hyundai.values import CAR


class TestIoniq5PECompatibility(unittest.TestCase):
  def test_pe_api_rejects_ev9_while_shared_owner_accepts_both(self):
    state = structs.CarState(canValid=True, gearShifter=structs.CarState.GearShifter.drive)
    state.cruiseState.enabled = True
    control = structs.CarControl(enabled=True, latActive=True)
    for identity in (CAR.HYUNDAI_IONIQ_5_PE, CAR.KIA_EV9):
      cp = params(candidate=identity)
      expected = identity == CAR.HYUNDAI_IONIQ_5_PE
      self.assertTrue(ccnc_ev_stock.qualified(cp))
      self.assertTrue(ccnc_ev_stock.request_allowed(cp, state))
      self.assertTrue(ccnc_ev_stock.replacement_requested(cp, control, state))
      self.assertEqual(ioniq5pe.qualified(cp), expected)
      self.assertEqual(ioniq5pe.request_allowed(cp, state), expected)
      self.assertEqual(ioniq5pe.replacement_requested(cp, control, state), expected)
