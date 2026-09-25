"""Main-only Kona and unchanged Forte shared independent authority boundaries."""
import unittest
from opendbc.car.structs import CarParams
from opendbc.safety.tests import test_hyundai_forte_aol as fixture


class TestHyundaiKonaAol(unittest.TestCase):
  setUp = fixture.TestHyundaiForteAol.setUp
  tearDown = fixture.TestHyundaiForteAol.tearDown
  reset = fixture.TestHyundaiForteAol.reset
  rx = fixture.TestHyundaiForteAol.rx
  feed = fixture.TestHyundaiForteAol.feed
  request = fixture.TestHyundaiForteAol.request

  def test_exact_main_kona_and_unchanged_forte_profiles(self):
    for word, source in ((0x1440, None), (0x1400, None), (0x1c00, 'BCM_PO_11')):
      self.reset(word)
      for _ in range(6):
        self.feed(main=True, source=source)
      self.assertFalse(self.safety.get_controls_allowed())
      self.assertEqual(self.request(1), 1)
      self.assertEqual(self.request(2), 0)
      self.feed(main=False, source=source)
      self.assertEqual(self.request(1), 0)

  def test_kona_namespace_experience_and_mode_denials(self):
    for word in (0x1040, 0x1840, 0x1c43, 0x1c42, 0x1c44, 0x1443, 0x1442, 0x1444, 0x9440, 0x3440):
      self.reset(word)
      for _ in range(6):
        self.feed(main=True, source=None)
      self.assertEqual(self.request(1), 0, hex(word))
    for experience in (0, 1, 33):
      self.reset(0x1440, experience=experience)
      for _ in range(6):
        self.feed(main=True, source=None)
      self.assertEqual(self.request(1), 0)
    self.reset(0x1440, mode=CarParams.SafetyModel.hyundaiCanfd)
    self.assertEqual(self.request(1), 0)

  def test_kona_no_lda_authorization_and_no_longitudinal_permission(self):
    self.reset(0x1440)
    for source in ('BCM_PO_11', 'CLU13'):
      for pressed in (False, True, False):
        self.feed(main=False, source=source, pressed=pressed)
        self.assertEqual(self.request(1), 0)
    for _ in range(6):
      self.feed(main=True, source=None)
    self.assertEqual(self.request(1), 1)
    self.assertEqual(self.request(3), 1)
    self.assertEqual(self.request(2), 0)

  def test_kona_lease_and_heartbeat_loss_require_fresh_physical_main(self):
    self.reset(0x1440)
    for _ in range(6):
      self.feed(main=True, source=None)
    self.assertEqual(self.request(1), 1)
    self.safety.set_aol_test_heartbeat(False)
    self.assertEqual(self.request(1), 0)
    self.safety.set_aol_test_heartbeat(True)
    self.assertEqual(self.request(1), 0)
    self.feed(main=True, source=None)
    self.assertEqual(self.request(1), 1)
    self.now += 300_001
    self.safety.set_timer(self.now)
    self.assertEqual(self.request(1), 0)
    self.assertEqual(self.request(1), 0)
    for _ in range(6):
      self.feed(main=True, source=None)
    self.assertEqual(self.request(1), 1)
