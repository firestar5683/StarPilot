from opendbc.car.structs import CarParams
import unittest
from opendbc.safety.tests import test_hyundai_kona_lda_aol as fixture


class TestHyundaiClassicLongAol(unittest.TestCase):
  def setUp(self):
    fixture.TestHyundaiKonaLdaAol.setUp(self)
    self.release = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0

  tearDown = fixture.TestHyundaiKonaLdaAol.tearDown
  reset = fixture.TestHyundaiKonaLdaAol.reset
  rx = fixture.TestHyundaiKonaLdaAol.rx
  request = fixture.TestHyundaiKonaLdaAol.request

  def feed(self, word=0x404, button=0, main=False, available=True, tcs=True, clu=True, wrong_bus=None, corrupt_tcs=False):
    self.safety.set_timer(self.now)
    c = self.counter
    self.counter += 1
    if word & 3:
      self.rx('E_EMS11', {'Accel_Pedal_Pos': 0, 'CR_Vcu_AccPedDep_Pos': 0})
    else:
      self.rx('EMS16', {'AliveCounter': c % 4}, integrity=True)
    self.rx('WHL_SPD11', {'WHL_SPD_AliveCounter_LSB': c % 4, 'WHL_SPD_AliveCounter_MSB': (c // 4) % 4}, integrity=True)
    if tcs:
      self.rx('TCS13', {'AliveCounterTCS': c % 8, 'ACCEnable': 0 if available else 1}, integrity=not corrupt_tcs, bus=0 if wrong_bus is None else wrong_bus)
    self.rx('MDPS12', {'CR_Mdps_StrColTq': 0})
    if clu:
      self.rx('CLU11', {'CF_Clu_AliveCnt1': c % 16, 'CF_Clu_CruiseSwState': button, 'CF_Clu_CruiseSwMain': int(main)})
    self.now += 10000

  def test_marked_long_with_foreign_experience_has_no_rx_or_tx_admission(self):
    for experience in (0, 1, 33):
      self.safety.set_alternative_experience(experience)
      self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai, 0x404), 0)
      self.safety.init_tests()
      self.assertFalse(self.safety.safety_config_valid())
      self.assertFalse(self.safety.safety_tx_hook(self.packer.make_can_msg_safety('LKAS11', 0, {})))
      self.assertEqual(self.request(3), 0)

  def test_availability_and_held_main_cannot_authorize(self):
    self.reset(0x404)
    for _ in range(6):
      self.feed(main=True)
    self.assertEqual(self.request(3), 0)
    self.assertFalse(self.safety.get_controls_allowed())

  def test_physical_main_grants_lateral_only_without_stock_scc(self):
    self.reset(0x404)
    for _ in range(6):
      self.feed()
    self.feed(main=True)
    expected = 0 if self.release else 1
    self.assertEqual(self.request(3), expected)
    self.assertFalse(self.safety.get_controls_allowed())

  def test_set_resume_capture_and_cancel_keep_longitudinal_physical(self):
    if self.release:
      self.skipTest('Current classic OP-long is DEBUG-only')
    for button in (1, 2):
      self.reset(0xC04)
      for _ in range(6):
        self.feed(0xC04)
      self.feed(0xC04, button=button)
      self.feed(0xC04)
      self.assertTrue(self.safety.get_controls_allowed())
      self.assertEqual(self.request(3), 3)
      self.feed(0xC04, button=4)
      self.assertFalse(self.safety.get_controls_allowed())
      self.assertEqual(self.request(3), 1)
      self.safety.set_aol_test_heartbeat(False)
      self.assertEqual(self.request(3), 0)

  def test_tcs_fault_and_expiry_revoke_without_disabled_scc_requirement(self):
    if self.release:
      self.skipTest('Current classic OP-long is DEBUG-only')
    for cause in ('fault', 'expiry'):
      self.reset(0x404)
      for _ in range(6):
        self.feed()
      self.feed(main=True)
      self.assertEqual(self.request(1), 1)
      if cause == 'fault':
        self.feed(available=False)
      else:
        for _ in range(120):
          self.feed(tcs=False)
          self.request(1)
      self.assertEqual(self.request(3), 0)

  def test_release_marked_long_has_zero_tx_and_existing_unmarked_is_unchanged(self):
    if not self.release:
      self.skipTest('Explicit release marked-owner boundary')
    for word in (0x404, 0xC04, 0x405, 0xC05, 0x406, 0xC06, 0x444, 0xC44, 0x445, 0xC45, 0x446, 0xC46):
      self.reset(word)
      self.assertEqual(self.request(3), 0)
      for name, values in (('LKAS11', {'CR_Lkas_StrToqReq': 0, 'CF_Lkas_ActToi': 0}), ('SCC12', {'ACCMode': 0, 'aReqRaw': 0, 'aReqValue': 0})):
        self.assertFalse(self.safety.safety_tx_hook(self.packer.make_can_msg_safety(name, 0, values)))
    self.reset(4)
    self.assertTrue(self.safety.safety_tx_hook(self.packer.make_can_msg_safety('LKAS11', 0, {'CR_Lkas_StrToqReq': 0, 'CF_Lkas_ActToi': 0})))
    self.assertFalse(self.safety.safety_tx_hook(self.packer.make_can_msg_safety('SCC12', 0, {'ACCMode': 1, 'aReqRaw': 1, 'aReqValue': 1})))

  def test_required_clu_expiry_clears_prior_main_and_requires_fresh_gesture(self):
    if self.release:
      self.skipTest('Current classic OP-long is DEBUG-only')
    self.reset(0x404)
    for _ in range(6):
      self.feed()
    self.feed(main=True)
    self.assertEqual(self.request(1), 1)
    for _ in range(120):
      self.feed(clu=False)
      self.request(1)
    self.assertEqual(self.request(3), 0)
    for _ in range(6):
      self.feed(main=True)
    self.assertEqual(self.request(1), 0)
    self.assertEqual(self.request(0), 0)
    self.feed()
    self.feed(main=True)
    self.assertEqual(self.request(1), 1)

  def test_wrong_bus_tcs_does_not_renew_ready_health(self):
    if self.release:
      self.skipTest('Current classic OP-long is DEBUG-only')
    self.reset(0x404)
    for _ in range(6):
      self.feed()
    self.feed(main=True)
    self.assertEqual(self.request(1), 1)
    for _ in range(120):
      self.feed(wrong_bus=1)
      self.request(1)
    self.assertEqual(self.request(3), 0)
