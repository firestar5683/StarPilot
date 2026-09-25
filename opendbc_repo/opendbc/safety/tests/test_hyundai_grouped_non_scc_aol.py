"""Grouped physical main/gas/LDA owners, retaining native common health."""
import unittest
from opendbc.safety.tests import test_hyundai_kona_lda_aol as kona


class TestHyundaiGroupedNonSccAol(unittest.TestCase):
  setUp = kona.TestHyundaiKonaLdaAol.setUp
  tearDown = kona.TestHyundaiKonaLdaAol.tearDown
  reset = kona.TestHyundaiKonaLdaAol.reset
  rx = kona.TestHyundaiKonaLdaAol.rx
  request = kona.TestHyundaiKonaLdaAol.request
  def grouped_feed(self, word, main=False, source=None, pressed=False, engagement_source=True):
    self.safety.set_timer(self.now)
    count = self.counter
    self.counter += 1
    if word & 1:
      self.rx('E_EMS11', {'Accel_Pedal_Pos': 0})
      if engagement_source:
        self.rx('EMS12', {'ACC_ACT': 0})
      self.rx('LABEL11', {'CC_React': int(main)})
    elif word & 2:
      self.rx('E_EMS11', {'CR_Vcu_AccPedDep_Pos': 0})
      self.rx('E_CRUISE_CONTROL', {'CRUISE_LAMP_M': int(main), 'CRUISE_LAMP_S': 0})
    else:
      self.rx('EMS16', {'CRUISE_LAMP_M': int(main), 'CRUISE_LAMP_S': 0,
                        'AliveCounter': count % 4}, integrity=True)
    self.rx('WHL_SPD11', {'WHL_SPD_AliveCounter_LSB': count % 4,
                        'WHL_SPD_AliveCounter_MSB': (count // 4) % 4}, integrity=True)
    self.rx('TCS13', {'AliveCounterTCS': count % 8}, integrity=True)
    self.rx('MDPS12', {})
    self.rx('CLU11', {'CF_Clu_AliveCnt1': count % 16})
    if source:
      signal = 'LDA_BTN' if source == 'BCM_PO_11' else 'CF_Clu_LdwsLkasSW'
      self.rx(source, {signal: int(pressed)})
    self.now += 10_000

  def test_grouped_main_source_identity_and_no_longitudinal(self):
    for word in (0x1400,0x1440,0x1402,0x1441):
      self.reset(word)
      for _ in range(6): self.grouped_feed(word)
      self.assertEqual(self.request(1),0)
      for _ in range(6): self.grouped_feed(word,main=True)
      self.assertEqual(self.request(1),1)
      self.assertFalse(self.safety.get_controls_allowed())
      self.assertEqual(self.request(2),0)
      self.grouped_feed(word)
      self.assertEqual(self.request(1),0)

  def test_grouped_lda_alternatives_and_missing_main_denial(self):
    for word in (0x1c00,0x1c40,0x1c02,0x1c41):
      for source in ('BCM_PO_11','CLU13'):
        self.reset(word)
        for _ in range(6): self.grouped_feed(word,source=source)
        self.grouped_feed(word,source=source,pressed=True)
        self.assertEqual(self.request(1),1)
        self.assertEqual(self.request(2),0)
        self.now += 300_001
        self.safety.set_timer(self.now)
        self.assertEqual(self.request(1),0)

  def test_ev_main_and_engagement_are_distinct_required_sources(self):
    self.reset(0x1441)
    for _ in range(6): self.grouped_feed(0x1441)
    self.rx('EMS12', {'ACC_ACT':1})
    self.assertEqual(self.request(1),0)
    self.rx('LABEL11', {'CC_React':1})
    self.assertEqual(self.request(1),1)
    # MAIN evidence alone must not survive required engagement-source expiry.
    for _ in range(120):
      self.grouped_feed(0x1441, main=True, engagement_source=False)
    self.assertEqual(self.request(1),0)
