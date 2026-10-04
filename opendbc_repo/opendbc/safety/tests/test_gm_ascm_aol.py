"""Ordinary non-EV ASCM main-source and independent-axis contracts."""

import unittest

from opendbc.car import structs
from opendbc.car.gm import gmcan
from opendbc.safety.tests import test_gm_aol as aol_fixture
from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames


class TestGmAscmAol(unittest.TestCase):
  setUp = aol_fixture.TestGmAol.setUp
  tearDown = aol_fixture.TestGmAol.tearDown
  packet = staticmethod(aol_fixture.TestGmAol.packet)
  reset = aol_fixture.TestGmAol.reset
  request = aol_fixture.TestGmAol.request
  WORDS = (0x201, 0x601, 0xA01, 0xE01, 0x203, 0x603, 0xA03, 0xE03)

  def feed(self, *, main=True, active=False, gas=False, brake=False, missing=None):
    # No regen packet exists or is required for these non-EV profiles.
    frames = pt_frames(self.packer, main=main, cruise=active, gas=gas, brake=brake,
                       acc_cruise=2 if active else 0)
    for frame in frames:
      if frame[0] != missing:
        self.safety.safety_rx_hook(self.packet(frame))
    self.safety.safety_tick()

  def test_all_ordinary_words_main_source_and_axis_ownership(self):
    for word in self.WORDS:
      for alternative in (0, 32):
        self.safety.init_tests()
        self.safety.set_alternative_experience(alternative)
        status = self.safety.set_safety_hooks(structs.CarParams.SafetyModel.gm, word)
        self.assertEqual(status, 0)
        if self.release and word & 2:
          # RELEASE does not admit an AOL alpha policy; legacy mode selection stays unchanged.
          self.safety.set_timer(1_000_000)
          self.safety.set_aol_test_heartbeat(True)
          self.feed()
          self.assertEqual(self.request(3), 0)
          continue
        self.safety.set_timer(1_000_000)
        self.safety.set_aol_test_heartbeat(True)
        self.feed()
        self.assertFalse(self.safety.get_controls_allowed())
        self.assertEqual(self.request(1), 1 if alternative == 32 else 0)
        self.assertEqual(self.request(3), 1 if alternative == 32 else 0)
        positive_gas = gmcan.create_gas_regen_command(self.packer, 0, 10, 0, True, False)
        self.assertFalse(self.safety.safety_tx_hook(self.packet(positive_gas)))
        if alternative == 32:
          self.safety.set_controls_allowed(True)
          self.assertEqual(self.request(1), 1)
          self.assertFalse(self.safety.safety_tx_hook(self.packet(positive_gas)))
          self.safety.set_controls_allowed(False)
        steer = gmcan.create_steering_control(self.packer, 0, 1, 0, True)
        self.assertEqual(bool(self.safety.safety_tx_hook(self.packet(steer))), alternative == 32)
        if alternative == 32:
          self.feed(main=False)
          self.assertEqual(self.request(1), 0)
          self.feed()
          self.assertEqual(self.request(1), 1)
          self.safety.set_timer(1_300_001)
          self.assertEqual(self.request(1), 0)

  def test_real_main_source_is_required_without_ev_regen(self):
    for word in self.WORDS:
      if self.release and word & 2:
        continue
      self.reset(word)
      self.feed(missing=0xC9)
      self.assertEqual(self.request(1), 0)
      main = self.packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': 1})
      self.safety.safety_rx_hook(self.packet((main[0], main[1], 2)))
      self.assertEqual(self.request(1), 0)
      self.safety.safety_rx_hook(self.packet((main[0], main[1][:-1], 0)))
      self.assertEqual(self.request(1), 0)
      self.feed()
      self.assertEqual(self.request(1), 1)
