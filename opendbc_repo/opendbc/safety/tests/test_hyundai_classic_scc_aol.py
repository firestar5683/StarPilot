"""Classic SCC physical ownership remains separate from stock longitudinal control."""

import unittest
from opendbc.car.structs import CarParams
from opendbc.safety.tests import test_hyundai_grouped_non_scc_aol as grouped
from opendbc.safety.tests import test_hyundai_kona_lda_aol as fixture


class TestHyundaiClassicSccAol(unittest.TestCase):
  setUp = fixture.TestHyundaiKonaLdaAol.setUp
  tearDown = fixture.TestHyundaiKonaLdaAol.tearDown
  reset = fixture.TestHyundaiKonaLdaAol.reset
  rx = fixture.TestHyundaiKonaLdaAol.rx
  request = fixture.TestHyundaiKonaLdaAol.request

  def feed(self, word, main=False, source=None, pressed=False, scc11=True, main_bus=None):
    self.safety.set_timer(self.now)
    count = self.counter
    self.counter += 1
    if word & 3:
      self.rx("E_EMS11", {"Accel_Pedal_Pos": 0, "CR_Vcu_AccPedDep_Pos": 0})
    else:
      self.rx("EMS16", {"AliveCounter": count % 4}, integrity=True)
    self.rx("WHL_SPD11", {"WHL_SPD_AliveCounter_LSB": count % 4, "WHL_SPD_AliveCounter_MSB": (count // 4) % 4}, integrity=True)
    self.rx("TCS13", {"AliveCounterTCS": count % 8}, integrity=True)
    self.rx("MDPS12", {"CR_Mdps_StrColTq": 0})
    self.rx("CLU11", {"CF_Clu_AliveCnt1": count % 16})
    bus = 2 if word & 8 else 0
    self.rx("SCC12", {"ACCMode": 0, "CR_VSM_Alive": count % 16}, bus=bus, integrity=True)
    if scc11:
      self.rx("SCC11", {"MainMode_ACC": int(main)}, bus=bus if main_bus is None else main_bus)
    if source:
      signal = "LDA_BTN" if source == "BCM_PO_11" else "CF_Clu_LdwsLkasSW"
      self.rx(source, {signal: int(pressed)})
    self.now += 10_000

  def test_main_namespace_gas_limits_bus_and_no_longitudinal(self):
    for mode in (CarParams.SafetyModel.hyundai, CarParams.SafetyModel.hyundaiLegacy):
      for gas in (0, 1, 2):
        for limits in (0, 64, 512):
          for bus in (0, 8) if mode == CarParams.SafetyModel.hyundai else (0,):
            word = 0x400 | gas | limits | bus
            self.reset(word, mode=mode)
            for _ in range(6):
              self.feed(word)
            self.assertEqual(self.request(1), 0)
            for _ in range(6):
              self.feed(word, main=True)
            self.assertEqual(self.request(1), 1)
            self.assertFalse(self.safety.get_controls_allowed())
            self.assertEqual(self.request(2), 0)
            self.assertFalse(
              self.safety.safety_tx_hook(self.packer.make_can_msg_safety("SCC12", 2 if bus else 0, {"ACCMode": 1, "aReqRaw": 1, "aReqValue": 1}))
            )
            self.feed(word)
            self.assertEqual(self.request(1), 0)

  def test_lda_sources_and_required_main_expiry(self):
    for mode in (CarParams.SafetyModel.hyundai, CarParams.SafetyModel.hyundaiLegacy):
      for word in (0xC00, 0xC41, 0xE02):
        for source in ("BCM_PO_11", "CLU13"):
          self.reset(word, mode=mode)
          for _ in range(6):
            self.feed(word, source=source)
          self.feed(word, source=source, pressed=True)
          self.assertEqual(self.request(1), 1)
          for _ in range(120):
            self.feed(word, source=source, scc11=False)
            self.request(1)
          self.assertEqual(self.request(1), 0)

  def test_wrong_bus_unknown_namespace_and_legacy_camera_rejected(self):
    self.reset(0x408)
    for _ in range(6):
      self.feed(0x408, main=True, main_bus=0)
    self.assertEqual(self.request(1), 0)
    for word in (0x403, 0x640, 0x404, 0x1408, 0x2400, 0x8400):
      self.reset(word)
      for _ in range(6):
        self.feed(word, main=True)
      self.assertEqual(self.request(1), 0)
    self.reset(0x408, mode=CarParams.SafetyModel.hyundaiLegacy)
    for _ in range(6):
      self.feed(0x408, main=True)
    self.assertEqual(self.request(1), 0)
    for experience in (0, 1, 33):
      self.reset(0x400, experience=experience)
      for _ in range(6):
        self.feed(0x400, main=True)
      self.assertEqual(self.request(1), 0)

  def test_swl_only_and_held_lda_do_not_authorize_independent_request(self):
    self.reset(0xC02)
    for _ in range(6):
      self.feed(0xC02, main=True, source="CLU13")
    self.rx("CLU13", {"CF_Clu_SWL_Stat": 4})
    self.assertEqual(self.request(1), 0)
    self.assertFalse(self.safety.get_controls_allowed())
    self.reset(0xC02)
    for _ in range(6):
      self.feed(0xC02, main=True, source="BCM_PO_11", pressed=True)
    self.assertEqual(self.request(1), 0)
    self.assertEqual(self.request(0), 0)
    self.feed(0xC02, main=True, source="BCM_PO_11")
    self.feed(0xC02, main=True, source="BCM_PO_11", pressed=True)
    self.assertEqual(self.request(1), 1)

  def test_no_lda_traffic_preserves_ordinary_stock_steering_with_aol_off(self):
    for mode in (CarParams.SafetyModel.hyundai, CarParams.SafetyModel.hyundaiLegacy):
      self.reset(0xC00, mode=mode)
      for _ in range(120):
        self.feed(0xC00, main=True)
      self.assertEqual(self.request(1), 0)
      self.rx("CLU11", {"CF_Clu_CruiseSwState": 2, "CF_Clu_AliveCnt1": self.counter % 16})
      self.rx("SCC12", {"ACCMode": 1, "CR_VSM_Alive": self.counter % 16}, integrity=True)
      self.counter += 1
      self.assertTrue(self.safety.get_controls_allowed())
      self.assertEqual(self.request(0), 0)
      active = self.packer.make_can_msg_safety("LKAS11", 0, {"CR_Lkas_StrToqReq": 1, "CF_Lkas_ActToi": 1})
      self.assertFalse(self.safety.safety_tx_hook(active))
      # Ordinary enabled steering requests the lateral axis even with AOL preference off.
      self.assertEqual(self.request(1), 1)
      self.assertTrue(self.safety.safety_tx_hook(active))

  def test_actual_stock_engagement_seeds_lateral_then_heartbeat_revokes(self):
    for mode in (CarParams.SafetyModel.hyundai, CarParams.SafetyModel.hyundaiLegacy):
      self.reset(0xC00, mode=mode)
      for _ in range(6):
        self.feed(0xC00, main=True)
      self.assertEqual(self.request(1), 0)
      self.rx("CLU11", {"CF_Clu_CruiseSwState": 2, "CF_Clu_AliveCnt1": self.counter % 16})
      self.rx("SCC12", {"ACCMode": 1, "CR_VSM_Alive": self.counter % 16}, integrity=True)
      self.counter += 1
      self.assertTrue(self.safety.get_controls_allowed())
      self.assertEqual(self.request(1), 1)
      self.rx("SCC12", {"ACCMode": 0, "CR_VSM_Alive": self.counter % 16}, integrity=True)
      self.counter += 1
      self.assertFalse(self.safety.get_controls_allowed())
      self.assertEqual(self.request(1), 1)
      self.assertEqual(self.request(2), 0)
      self.safety.set_aol_test_heartbeat(False)
      self.assertEqual(self.request(1), 0)

  def test_non_scc_owner_survives_mode_transition(self):
    self.reset(0x400)
    for _ in range(6):
      self.feed(0x400, main=True)
    self.assertEqual(self.request(1), 1)
    self.reset(0x1400)
    for _ in range(6):
      grouped.TestHyundaiGroupedNonSccAol.grouped_feed(self, 0x1400, main=True)
    self.assertEqual(self.request(1), 1)
