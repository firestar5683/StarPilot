from opendbc.car.hyundai.hyundaicanfd import hkg_can_fd_checksum
from opendbc.safety.tests import test_hyundai_angle_hybrids_three as angle_profiles
import unittest

from opendbc.can import CANPacker
from opendbc.car import structs
from opendbc.safety.tests.libsafety import libsafety_py


WORDS = (0x4010, 0x4811, 0x5010, 0x5811, 0x6010, 0x6810, 0x7010, 0x4408, 0x4C08, 0x7809, 0x5491, 0x5C91)


class TestHyundaiStockAngleAol(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPacker('hyundai_canfd_generated')

  def mode(self, word):
    self.safety.set_alternative_experience(32)
    self.assertEqual(self.safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd, word), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  def rx(self, name, bus, values):
    self.assertFalse(set(values) - set(self.packer.dbc.name_to_msg[name].sigs), name)
    frame = self.packer.make_can_msg(name, bus, values)
    self.assertTrue(self.safety.safety_rx_hook(libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])), name)

  def sources(self, word, *, gear=5, brake=False, gas=False, fault=0, omit=None, gear_bus=None):
    pt = 1 if word & 16 else 0
    fuel = 'ACCELERATOR' if word & 1 else 'ACCELERATOR_ALT' if word & 2 else 'ACCELERATOR_BRAKE_ALT'
    button = 'CRUISE_BUTTONS_ALT' if word & 32 else 'CRUISE_BUTTONS'
    fuel_values = {'ACCELERATOR_PEDAL': 4 if gas else 0} if word & 3 else {'ACCELERATOR_PEDAL_PRESSED': int(gas)}
    if word & 1:
      fuel_values['GEAR'] = gear
    for count in range(1, 7):
      entries = [
        (fuel, pt, fuel_values),
        ('TCS', pt, {'DriverBraking': int(brake)}),
        ('WHEEL_SPEEDS', pt, dict.fromkeys(('WHL_SpdFLVal', 'WHL_SpdFRVal', 'WHL_SpdRLVal', 'WHL_SpdRRVal'), 36)),
        ('MDPS', pt, {'MDPS_LkaFailSta': fault}),
        (button, pt, {}),
        ('SCC_CONTROL', 2 if word & 8 else pt, {}),
      ]
      if not word & 1:
        entries.append(('GEAR_ALT_2', pt if gear_bus is None else gear_bus, {'GEAR': gear}))
      for name, bus, values in entries:
        if name != omit:
          self.rx(name, bus, dict(values, COUNTER=count % (16 if name == 'CRUISE_BUTTONS' else 256)))

  def gesture(self, word):
    pt = 1 if word & 16 else 0
    button = 'CRUISE_BUTTONS_ALT' if word & 32 else 'CRUISE_BUTTONS'
    self.rx(button, pt, {'COUNTER': 7, 'LDA_BTN': 1})
    self.rx(button, pt, {'COUNTER': 8, 'LDA_BTN': 0})
    self.safety.set_aol_test_heartbeat(True)
    self.safety.aol_set_host_request(3)

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def command(self, word, counter, *, active=True, bad_crc=False):
    if word & 0x200 and not word & 0x10:
      return self.packet(self.packer.make_can_msg('LFA_ALT', 0, {'COUNTER': counter,
        'ADAS_ActvACISta': 0, 'ADAS_ActvACILvl2Sta': 2 if active else 1, 'ADAS_StrAnglReqVal': 0,
        'ADAS_ACIAnglTqRedcGainVal': 0, 'FCA_ESA_ActvSta': 0, 'FCA_ESA_TqBstGainVal': 0}))
    name = 'LKAS_ALT' if word & 0x80 else 'LKAS' if word & 0x10 else 'LFA'
    address, raw, bus = self.packer.make_can_msg(name, 0, {'COUNTER': counter})
    data = bytearray(raw)
    data[9] = (2 if active else 1) << 4
    data[5], data[6] = 0, 8
    data[10], data[11] = 0, 0
    data[:2] = hkg_can_fd_checksum(address, None, data).to_bytes(2, 'little')
    if bad_crc:
      data[0] ^= 1
    return self.packet((address, bytes(data), bus))

  def test_real_angle_profiles_commit_only_valid_fresh_commands(self):
    for topology, adas in (('lka', False), ('lka_alt', False), ('lfa', False), ('lfa_alt', True)):
      cp = angle_profiles.params(angle_profiles.CARS[0], topology, hybrid=True, adas=adas)
      word = cp.safetyConfigs[-1].safetyParam
      self.mode(word)
      self.sources(word)
      self.gesture(word)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
      active = self.command(word, 1)
      address = active[0].addr
      self.assertTrue(self.safety.safety_tx_hook(active))
      self.assertTrue(self.safety.safety_test_selected_fwd(2, address))
      self.assertFalse(self.safety.safety_tx_hook(self.command(word, 1)))
      self.assertFalse(self.safety.safety_test_selected_fwd(2, address))
      self.assertTrue(self.safety.safety_tx_hook(self.command(word, 2)))
      corrupt = self.command(word, 3)
      corrupt[0].data[0] ^= 1
      self.assertFalse(self.safety.safety_tx_hook(corrupt))
      self.assertFalse(self.safety.safety_test_selected_fwd(2, address))
      self.assertTrue(self.safety.safety_tx_hook(self.command(word, 3)))
      self.assertTrue(self.safety.safety_tx_hook(self.command(word, 4, active=False)))
      self.assertFalse(self.safety.safety_test_selected_fwd(2, address))
      self.assertTrue(self.safety.safety_tx_hook(self.command(word, 5)))
      self.safety.set_timer(1_300_001)
      self.assertFalse(self.safety.safety_test_selected_fwd(2, address))
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
      self.assertFalse(self.safety.safety_tx_hook(self.command(word, 6)))

  def test_non_angle_profile_rejects_cb_at_public_and_selected_hooks(self):
    self.safety.set_alternative_experience(0)
    self.assertEqual(self.safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd, 0), 0)
    packet = self.packet(self.packer.make_can_msg('LFA_ALT', 0, {}))
    self.assertFalse(self.safety.safety_tx_hook(packet))
    self.assertFalse(self.safety.safety_test_selected_tx(packet))

  def test_independent_angle_invalid_capacity_returns_empty_config(self):
    self.assertTrue(self.safety.safety_test_hyundai_angle_invalid_capacity(0))
    self.assertTrue(self.safety.safety_test_hyundai_angle_invalid_capacity(65))

  def test_exact_stock_words_require_physical_token_and_fresh_drive(self):
    for word in WORDS:
      with self.subTest(word=hex(word)):
        self.mode(word)
        self.sources(word)
        self.safety.set_aol_test_heartbeat(True)
        self.safety.aol_set_host_request(3)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)
        self.gesture(word)
        self.assertEqual(self.safety.aol_get_permission_mask(), 1)
        self.safety.set_timer(2_000_000)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_non_ev_missing_wrong_bus_and_reverse_gear_denied(self):
    for word in (0x4010, 0x4408, 0x4C08):
      for kwargs in ({'omit': 'GEAR_ALT_2'}, {'gear_bus': 2}, {'gear': 7}):
        with self.subTest(word=hex(word), kwargs=kwargs):
          self.mode(word)
          self.sources(word, **kwargs)
          self.gesture(word)
          self.assertEqual(self.safety.aol_get_permission_mask(), 0)
