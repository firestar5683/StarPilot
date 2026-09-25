"""Classic Forte axis authority, physical source fusion, and reset boundaries."""
import unittest

from opendbc.car.structs import CarParams
from opendbc.safety.tests.common import CANPackerSafety
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests.test_hyundai import checksum


class TestHyundaiForteAol(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPackerSafety('hyundai_can_generated')
    self.counter = 0
    self.now = 1_000_000

  def tearDown(self):
    self.safety.set_alternative_experience(0)

  def reset(self, word=0x1c00, experience=32, mode=CarParams.SafetyModel.hyundai):
    self.safety.init_tests()
    self.safety.set_alternative_experience(experience)
    self.assertEqual(self.safety.set_safety_hooks(mode, word), 0)
    self.safety.set_timer(self.now)
    self.safety.set_aol_test_heartbeat(True)

  def rx(self, name, values, *, integrity=False, bus=0):
    return self.safety.safety_rx_hook(self.packer.make_can_msg_safety(
      name, bus, values, fix_checksum=checksum if integrity else None))

  def feed(self, *, main=False, cruise=False, source='BCM_PO_11', pressed=False):
    self.safety.set_timer(self.now)
    count = self.counter
    self.counter += 1
    self.rx('EMS16', {'CRUISE_LAMP_M': int(main), 'CRUISE_LAMP_S': int(cruise),
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

  def request(self, mask):
    self.safety.aol_set_host_request(mask)
    return self.safety.aol_get_permission_mask()

  def test_main_before_cruise_and_exact_mode_word_experience(self):
    for word, source in ((0x1400, None), (0x1c00, 'BCM_PO_11'), (0x1c00, 'CLU13')):
      self.reset(word)
      for _ in range(3):
        self.feed(main=True, source=source)
      self.assertEqual(self.request(1), 1)
      self.assertFalse(self.safety.get_controls_allowed())
      self.assertEqual(self.request(2), 0)
      self.feed(main=False, source=source)
      self.assertEqual(self.request(1), 0)
    for word, experience in ((0x1000, 32), (0x1800, 32), (0x1400, 0), (0x1400, 33),
                             (0x1401, 32), (0x1403, 32), (0x1404, 32), (0x1410, 32), (0x3400, 32)):
      self.reset(word, experience)
      self.feed(main=True)
      self.assertEqual(self.request(1), 0)
    self.reset(0x1400, 32, CarParams.SafetyModel.hyundaiCanfd)
    self.assertEqual(self.request(1), 0)

  def test_combined_sources_do_not_double_toggle_and_neutral_retains_token(self):
    self.reset()
    for _ in range(3):
      self.feed()
    self.request(0)
    self.feed(pressed=True)
    self.assertEqual(self.request(1), 1)
    # Another source's zero cannot erase the held combined physical state.
    self.rx('CLU13', {'CF_Clu_LdwsLkasSW': 0})
    self.assertEqual(self.request(1), 1)
    self.feed(pressed=False)
    self.assertEqual(self.request(0), 0)
    self.assertEqual(self.request(1), 1)

  def test_safety_reset_held_input_expiry_and_new_gesture(self):
    self.reset()
    for _ in range(3):
      self.feed()
    self.request(0)
    self.feed(pressed=True)
    self.assertEqual(self.request(1), 1)
    self.reset()
    for _ in range(3):
      self.feed(pressed=True)
    self.assertEqual(self.request(1), 0)
    self.request(0)
    self.feed(pressed=False)
    self.feed(pressed=True)
    self.assertEqual(self.request(1), 1)
    self.safety.set_aol_test_heartbeat(False)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.safety.set_aol_test_heartbeat(True)
    for _ in range(3):
      self.feed(pressed=True)
    self.assertEqual(self.request(1), 0)

  def test_unclaimed_token_and_missing_required_sources_expire(self):
    self.reset()
    for _ in range(3):
      self.feed()
    self.request(0)
    self.feed(pressed=True)
    # Required RX stays current; only the unclaimed gesture expires.
    for _ in range(40):
      self.feed(pressed=True)
      self.request(0)
    self.assertEqual(self.request(1), 0)
    self.request(0)
    self.feed(pressed=False)
    self.feed(pressed=True)
    self.assertEqual(self.request(1), 1)
    # No permission read or host refresh during this interval: the fresh late
    # request itself must reject the expired claimed authorization.
    for _ in range(40):
      self.feed(pressed=True)
    self.assertEqual(self.request(1), 0)
    for _ in range(3):
      self.feed(main=True)
    self.assertEqual(self.request(1), 1)
    self.safety.set_timer(self.now + 300_001)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_lateral_permission_keeps_neutral_and_existing_torque_guards(self):
    self.reset(0x1400)
    for _ in range(3):
      self.feed(main=True, source=None)
    def steer(torque, request):
      return self.packer.make_can_msg_safety('LKAS11', 0, {
        'CR_Lkas_StrToqReq': torque, 'CF_Lkas_ActToi': request})
    self.assertEqual(self.request(0), 0)
    self.assertTrue(self.safety.safety_tx_hook(steer(0, 0)))
    self.assertFalse(self.safety.safety_tx_hook(steer(1, 1)))
    self.assertEqual(self.request(1), 1)
    self.assertTrue(self.safety.safety_tx_hook(steer(1, 1)))
    self.assertFalse(self.safety.safety_tx_hook(steer(400, 1)))
    self.assertFalse(self.safety.safety_tx_hook(steer(1, 0)))

  def test_new_or_expired_held_source_requires_its_own_neutral(self):
    # CLU alone supplies physical authorization; BCM is not a second required
    # source. A wrong-length alternative cannot supply a gesture.
    self.reset()
    for _ in range(3):
      self.feed(source='CLU13')
    self.request(0)
    malformed = libsafety_py.make_CANPacket(0x391, 0, b'\x10' + b'\x00' * 6)
    self.safety.safety_rx_hook(malformed)
    self.assertEqual(self.request(1), 0)
    self.request(0)
    self.feed(source='CLU13', pressed=True)
    self.assertEqual(self.request(1), 1)
    # Reverse the selected required alternative: BCM remains observable after
    # CLU selects the mandatory health entry, without becoming required itself.
    self.reset()
    for _ in range(3):
      self.feed(source='CLU13')
    self.request(0)
    self.rx('BCM_PO_11', {'LDA_BTN': 1})
    self.assertEqual(self.request(1), 0)
    self.request(0)
    self.rx('BCM_PO_11', {'LDA_BTN': 0})
    self.rx('BCM_PO_11', {'LDA_BTN': 1})
    self.assertEqual(self.request(1), 1)
    self.reset()
    for _ in range(3):
      self.feed()
    self.request(0)
    self.rx('CLU13', {'CF_Clu_LdwsLkasSW': 1})
    self.assertEqual(self.request(1), 0)
    self.request(0)
    self.rx('CLU13', {'CF_Clu_LdwsLkasSW': 0})
    self.rx('CLU13', {'CF_Clu_LdwsLkasSW': 1})
    self.assertEqual(self.request(1), 1)
    self.request(0)
    # Keep required sources current while CLU drops its release and expires.
    for _ in range(40):
      self.feed(source='BCM_PO_11', pressed=False)
      self.request(0)
    self.rx('CLU13', {'CF_Clu_LdwsLkasSW': 1})
    self.assertEqual(self.request(1), 1)  # Previously claimed current-epoch token remains.
    self.reset()
    for _ in range(3):
      self.feed()
    self.request(0)
    self.rx('CLU13', {'CF_Clu_LdwsLkasSW': 0})
    for _ in range(40):
      self.feed()
      self.request(0)
    self.rx('CLU13', {'CF_Clu_LdwsLkasSW': 1})
    self.assertEqual(self.request(1), 0)
    self.request(0)
    self.rx('CLU13', {'CF_Clu_LdwsLkasSW': 0})
    self.rx('CLU13', {'CF_Clu_LdwsLkasSW': 1})
    self.assertEqual(self.request(1), 1)

  def test_transmitted_authority_packets_never_authorize(self):
    self.reset()
    for _ in range(3):
      self.feed()
    self.request(0)
    for name, values in (('EMS16', {'CRUISE_LAMP_M': 1}),
                         ('BCM_PO_11', {'LDA_BTN': 1}),
                         ('CLU13', {'CF_Clu_LdwsLkasSW': 1})):
      self.assertFalse(self.safety.safety_tx_hook(self.packer.make_can_msg_safety(name, 0, values)))
      self.assertEqual(self.request(1), 0)
      self.request(0)

  def test_wrong_bus_integrity_counter_driver_and_relay_guards(self):
    self.reset()
    for _ in range(3):
      self.feed()
    self.request(0)
    self.rx('EMS16', {'CRUISE_LAMP_M': 1, 'AliveCounter': self.counter % 4}, integrity=True, bus=1)
    self.rx('BCM_PO_11', {'LDA_BTN': 1}, bus=1)
    self.assertEqual(self.request(1), 0)
    for _ in range(3):
      self.feed(main=True)
    self.assertEqual(self.request(1), 1)
    self.assertFalse(self.rx('EMS16', {'CRUISE_LAMP_M': 1, 'AliveCounter': self.counter % 4,
                                    'Checksum': 15}, integrity=False))
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.reset(0x1400)
    for _ in range(3):
      self.feed(main=True, source=None)
    repeated = (self.counter - 1) % 4
    for _ in range(6):
      self.rx('EMS16', {'CRUISE_LAMP_M': 1, 'AliveCounter': repeated}, integrity=True)
    self.assertEqual(self.request(1), 0)
    self.reset(0x1400)
    for _ in range(3):
      self.feed(main=True, source=None)
    self.assertEqual(self.request(1), 1)
    steer = self.packer.make_can_msg_safety('LKAS11', 0, {'CR_Lkas_StrToqReq': 1, 'CF_Lkas_ActToi': 1})
    self.safety.set_torque_driver(-1000, -1000)
    self.assertFalse(self.safety.safety_tx_hook(steer))
    self.safety.set_relay_malfunction(True)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.assertFalse(self.safety.safety_tx_hook(steer))
