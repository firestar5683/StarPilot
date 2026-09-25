"""Exact Kona LDA uses the already-qualified classic physical token owner."""
import unittest
from opendbc.car.structs import CarParams
from opendbc.safety.tests import test_hyundai_forte_aol as fixture


class TestHyundaiKonaLdaAol(unittest.TestCase):
  setUp = fixture.TestHyundaiForteAol.setUp
  tearDown = fixture.TestHyundaiForteAol.tearDown
  rx = fixture.TestHyundaiForteAol.rx
  feed = fixture.TestHyundaiForteAol.feed
  request = fixture.TestHyundaiForteAol.request

  def reset(self, word=0x1c40, experience=32, mode=CarParams.SafetyModel.hyundai):
    return fixture.TestHyundaiForteAol.reset(self, word, experience, mode)

  test_combined_sources_do_not_double_toggle_and_neutral_retains_token = fixture.TestHyundaiForteAol.test_combined_sources_do_not_double_toggle_and_neutral_retains_token
  test_unclaimed_token_and_missing_required_sources_expire = fixture.TestHyundaiForteAol.test_unclaimed_token_and_missing_required_sources_expire
  test_new_or_expired_held_source_requires_its_own_neutral = fixture.TestHyundaiForteAol.test_new_or_expired_held_source_requires_its_own_neutral

  def test_exact_kona_lda_namespace_and_no_independent_longitudinal(self):
    for source in ('BCM_PO_11','CLU13'):
      self.reset()
      for _ in range(6): self.feed(main=False, source=source)
      self.feed(main=False,source=source,pressed=True)
      self.assertFalse(self.safety.get_controls_allowed())
      self.assertEqual(self.request(1),1)
      self.assertEqual(self.request(3),1)
      self.assertEqual(self.request(2),0)
    for word in (0x1840,0x1c43,0x1c42,0x1c44,0x9c40,0x3c40):
      self.reset(word)
      for _ in range(6): self.feed(main=True)
      self.assertEqual(self.request(1),0)
    for experience in (0,1,33):
      self.reset(experience=experience)
      for _ in range(6): self.feed(main=True)
      self.assertEqual(self.request(1),0)
