"""Experimental mixed longitudinal safety contract regressions."""
import os
import unittest
from opendbc.safety.tests.test_hyundai import checksum
from opendbc.safety.tests import test_hyundai_blended_alpha as helpers


class TestHyundaiBlendedAlphaClosure(unittest.TestCase):
  select = helpers.TestHyundaiBlendedAlpha.select
  primary = helpers.TestHyundaiBlendedAlpha.primary
  mirror = helpers.TestHyundaiBlendedAlpha.mirror
  tcs = helpers.TestHyundaiBlendedAlpha.tcs
  button = helpers.TestHyundaiBlendedAlpha.button

  def setUp(self):
    helpers.TestHyundaiBlendedAlpha.setUp(self)
    if os.environ.get('ALPHA_NATIVE_RELEASE') == '1':
      self.skipTest('DEBUG behavior; RELEASE admission checked separately')

  def seed_torque(self, torque):
    self.safety.set_desired_torque_last(torque)
    self.safety.set_rt_torque_last(torque)
    self.safety.set_torque_driver(0, 0)

  def test_cancel_release_after_required_rx_loss_stays_disabled(self):
    for hda2 in (False, True):
      self.select(hda2)
      self.assertTrue(self.safety.safety_rx_hook(self.tcs(False, 0)))
      self.assertTrue(self.safety.safety_rx_hook(self.button(4, 0)))
      self.safety.set_timer(1000001)
      self.safety.safety_tick_current_safety_config()
      self.assertTrue(self.safety.safety_rx_hook(self.tcs(False, 1)))
      self.assertTrue(self.safety.safety_rx_hook(self.button(0, 1)))
      self.assertFalse(self.safety.get_controls_allowed())

  def test_cancel_press_with_pedal_already_pressed_never_arms(self):
    for hda2 in (False, True):
      for pedal in ('brake', 'gas'):
        self.select(hda2)
        if pedal == 'brake':
          packet = self.packer.make_can_msg_safety('TCS13', self.bus,
            {'DriverOverride': 2, 'AliveCounterTCS': 0}, fix_checksum=checksum)
        else:
          self.safety.safety_rx_hook(self.tcs(False, 0))
          packet = self.packer.make_can_msg_safety('EMS16', self.bus,
            {'CF_Ems_AclAct': 1, 'AliveCounter': 0}, fix_checksum=checksum)
        self.assertTrue(self.safety.safety_rx_hook(packet))
        self.assertTrue(self.safety.safety_rx_hook(self.button(4, 0)))
        if pedal == 'brake':
          self.assertTrue(self.safety.safety_rx_hook(self.tcs(False, 1)))
        else:
          packet = self.packer.make_can_msg_safety('EMS16', self.bus,
            {'CF_Ems_AclAct': 0, 'AliveCounter': 1}, fix_checksum=checksum)
          self.assertTrue(self.safety.safety_rx_hook(packet))
        self.assertTrue(self.safety.safety_rx_hook(self.button(0, 1)))
        self.assertFalse(self.safety.get_controls_allowed())

  def test_mirror_mismatch_consumes_only_that_primary_token(self):
    for torque, request in ((2, True), (3, False)):
      self.select(True)
      self.safety.set_controls_allowed(True)
      self.assertTrue(self.safety.safety_tx_hook(self.primary(3, True)))
      self.assertFalse(self.safety.safety_tx_hook(self.mirror(torque, request)))
      self.assertFalse(self.safety.safety_tx_hook(self.mirror(3, True)))
      self.assertTrue(self.safety.safety_tx_hook(self.primary(3, True)))
      self.assertTrue(self.safety.safety_tx_hook(self.mirror(3, True)))

  def test_mirror_does_not_double_request_history_or_change_cut_budget(self):
    for valid_count in (44, 88, 89):
      self.select(True)
      self.safety.set_timer(810000)
      self.safety.set_controls_allowed(True)
      self.seed_torque(30)
      for _ in range(valid_count):
        self.assertTrue(self.safety.safety_tx_hook(self.primary(30, True)))
        self.assertTrue(self.safety.safety_tx_hook(self.mirror(30, True)))
      for invalid in range(3):
        expected = valid_count >= 89 and invalid < 2
        self.assertEqual(self.safety.safety_tx_hook(self.primary(30, False)), expected)
        self.assertEqual(self.safety.safety_tx_hook(self.mirror(30, False)), expected)

  def test_mirror_does_not_relax_primary_driver_rate_or_controls(self):
    for torque, allowed, driver in ((4, True, 0), (3, False, 0), (3, True, -300)):
      self.select(True)
      self.safety.set_controls_allowed(allowed)
      self.safety.set_torque_driver(driver, driver)
      self.assertFalse(self.safety.safety_tx_hook(self.primary(torque, True)))
      self.assertFalse(self.safety.safety_tx_hook(self.mirror(torque, True)))

  def test_mirror_zero_off_and_exact_expiry_boundary(self):
    self.select(True)
    self.assertTrue(self.safety.safety_tx_hook(self.primary(0, False)))
    self.assertTrue(self.safety.safety_tx_hook(self.mirror(0, False)))
    for elapsed, allowed in ((10000, True), (10001, False)):
      self.select(True)
      self.safety.set_controls_allowed(True)
      self.assertTrue(self.safety.safety_tx_hook(self.primary(3, True)))
      self.safety.set_timer(elapsed)
      self.assertEqual(self.safety.safety_tx_hook(self.mirror(3, True)), allowed)

  def test_mirror_relay_and_profile_reinit_fail_closed(self):
    self.select(True)
    self.safety.set_controls_allowed(True)
    self.assertTrue(self.safety.safety_tx_hook(self.primary(3, True)))
    self.safety.set_relay_malfunction(True)
    self.assertFalse(self.safety.safety_tx_hook(self.mirror(3, True)))
    self.select(True)
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(self.mirror(3, True)))
