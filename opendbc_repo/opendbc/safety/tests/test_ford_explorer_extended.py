"""Exact Explorer classic extension intersects original and modern limits."""
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
import unittest
from opendbc.safety.tests import test_ford as ford
from opendbc.safety.tests import test_ford_stock_switch as stock


class TestFordExplorerExtended(unittest.TestCase):

  def setUp(self):
    libsafety_py.libsafety.set_alternative_experience(0)
    self.fixture = ford.TestFordLongitudinalSafety()
    self.fixture.SAFETY_PARAM = 32
    self.fixture.setUp()

  def tearDown(self):
    self.safety.set_alternative_experience(0)
    self.safety.set_safety_hooks(CarParams.SafetyModel.noOutput, 0)

  def __getattr__(self, name):
    fixture = self.__dict__.get('fixture')
    if fixture is None:
      raise AttributeError(name)
    return getattr(fixture, name)

  def select(self, word=32, ae=0):
    self.safety.set_alternative_experience(ae)
    self.safety.set_safety_hooks(CarParams.SafetyModel.ford, word)
    self.safety.set_timer(0)

  def announce(self, active=True, forbidden=False):
    msg = self._lkas_command_msg(0)
    msg[0].data[4] = (2 if active else 0) | int(forbidden)
    return self._tx(msg)

  def prepare(self, speed=5.0):
    self._reset_curvature_measurement(0.0, speed)
    self._set_prev_desired_angle(0.0)
    self.safety.set_controls_allowed(True)

  def test_namespace_and_classic_long_both_variants(self):
    for word in (32, 33):
      self.select(word)
      self.assertTrue(self.announce())
      self.prepare()
      self.assertTrue(self._tx(self._lat_ctl_msg(True, 0, 0, 0, 0.0002)))
      self.assertEqual(word == 33, self._tx(self._acc_command_msg(self.INACTIVE_GAS, self.INACTIVE_ACCEL, False)))
    for word in (32, 33):
      self.select(word, 32)
      self.assertTrue(self.announce())
      self.assertTrue(self._tx(self._lat_ctl_msg(False, 0, 0, 0, 0)))
    for word, ae in ((34, 0), (36, 0), (40, 0), (48, 0), (96, 0), (32, 1), (33, 1)):
      self.select(word, ae)
      self.assertFalse(self.announce())
      self.assertFalse(self._tx(self._lat_ctl_msg(False, 0, 0, 0, 0)))

  def test_accepted_announcement_and_inactive_fields(self):
    self.prepare()
    self.assertFalse(self._tx(self._lat_ctl_msg(True, 0, 0, 0, 0.0002)))
    self.assertFalse(self.announce(forbidden=True))
    self.prepare()
    self.assertFalse(self._tx(self._lat_ctl_msg(True, 0, 0, 0, 0.0002)))
    self.assertTrue(self.announce())
    for rate in (-0.001024, 0.00102375):
      self.prepare()
      self.assertTrue(self._tx(self._lat_ctl_msg(True, 0, 0, 0, rate)))
    for offset, angle, curvature, rate in ((0.01, 0, 0, 0), (0, 0.01, 0, 0), (0, 0, 0, 0.0002), (0, 0, 0.001, 0)):
      self.prepare()
      self.assertFalse(self._tx(self._lat_ctl_msg(False, offset, angle, curvature, rate)))
    self.assertTrue(self._tx(self._lat_ctl_msg(False, 0, 0, 0, 0)))
    self.assertTrue(self.announce(active=False))
    self.prepare()
    self.assertFalse(self._tx(self._lat_ctl_msg(True, 0, 0, 0, 0)))

  def test_modern_jerk_and_original_lookup_intersect(self):
    self.assertTrue(self.announce())
    for speed, accepted_can, rejected_can in ((15.0, 40, 70), (26.0, 8, 12)):
      self.prepare(speed)
      self.assertTrue(self._tx(self._lat_ctl_msg(True, 0, 0, accepted_can / self.DEG_TO_CAN, 0)))
      self.prepare(speed)
      self.assertFalse(self._tx(self._lat_ctl_msg(True, 0, 0, rejected_can / self.DEG_TO_CAN, 0)))
      self.assertEqual(self.safety.get_desired_curvature_last(), 0)
      # A follow-up from zero must pass without resetting previous desire.
      # Retaining the rejected positive command would make this reversal fail.
      self.assertTrue(self._tx(self._lat_ctl_msg(True, 0, 0, -accepted_can / self.DEG_TO_CAN, 0)))

  def cruise(self, state):
    return stock.TestFordStockSwitch.cruise(self, state)

  def physical_switch(self, pressed, bus=0):
    return stock.TestFordStockSwitch.physical_switch(self, pressed, bus)

  def test_stock_resume_does_not_grant_steering(self):
    for word in (32, 33):
      self.select(word)
      stock.TestFordStockSwitch.healthy(self, word)
      self.assertFalse(self.safety.get_controls_allowed())
      self.assertEqual(word == 32, self._tx(self._acc_button_msg(ford.Buttons.RESUME, 0)))
      self.assertFalse(self.safety.get_controls_allowed())
      self.assertTrue(self._rx(self.physical_switch(False)))
      self.assertFalse(self._tx(self._acc_button_msg(ford.Buttons.RESUME, 0)))
