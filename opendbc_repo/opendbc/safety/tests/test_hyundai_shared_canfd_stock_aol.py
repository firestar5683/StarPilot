import unittest

from opendbc.can import CANPacker
from opendbc.car import structs
from opendbc.car.hyundai.canfd_stock_aol import STOCK_AOL_WORDS
from opendbc.safety.tests.libsafety import libsafety_py


class TestHyundaiSharedCanfdStockAol(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPacker('hyundai_canfd_generated')

  def mode(self, word):
    self.safety.set_alternative_experience(0)
    self.assertEqual(self.safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd, word), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def healthy(self, word, *, omit=None, wrong_bus=None):
    pt = 1 if word & 0x10 else 0
    fuel = {0: 'ACCELERATOR_BRAKE_ALT', 1: 'ACCELERATOR', 2: 'ACCELERATOR_ALT'}[word & 3]
    buttons = 'CRUISE_BUTTONS_ALT' if word & 0x20 else 'CRUISE_BUTTONS'
    for counter in range(1, 7):
      for name in (fuel, 'TCS', 'WHEEL_SPEEDS', 'MDPS', buttons):
        if name == omit:
          continue
        bus = 1 - pt if name == wrong_bus else pt
        values = {'COUNTER': counter % (16 if name == 'CRUISE_BUTTONS' else 256)}
        if name == 'MDPS':
          values['MDPS_StrTqSnsrVal'] = 0
        frame = self.packer.make_can_msg(name, bus, values)
        self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)), name)
      if not word & 4 and omit != 'SCC_CONTROL':
        frame = self.packer.make_can_msg('SCC_CONTROL', 2 if word & 8 else pt, {'COUNTER': counter})
        self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))

  def gesture(self, word):
    pt = 1 if word & 0x10 else 0
    name = 'CRUISE_BUTTONS_ALT' if word & 0x20 else 'CRUISE_BUTTONS'
    for count, pressed in ((7, 1), (8, 0)):
      frame = self.packer.make_can_msg(name, pt, {'COUNTER': count, 'LDA_BTN': pressed})
      self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))
    self.safety.set_aol_test_heartbeat(True)
    self.safety.aol_set_host_request(3)

  def test_selected_fuel_button_and_scc_sources_are_required(self):
    for word in (0x800 | fuel | topology for fuel in (0, 1, 2) for topology in (0, 8, 16, 32, 40, 144)):
      fuel = {0: 'ACCELERATOR_BRAKE_ALT', 1: 'ACCELERATOR', 2: 'ACCELERATOR_ALT'}[word & 3]
      buttons = 'CRUISE_BUTTONS_ALT' if word & 0x20 else 'CRUISE_BUTTONS'
      for omitted in (fuel, buttons, 'SCC_CONTROL'):
        self.mode(word)
        self.healthy(word, omit=omitted)
        if omitted != buttons:
          self.gesture(word)
        else:
          self.safety.set_aol_test_heartbeat(True)
          self.safety.aol_set_host_request(3)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)
      self.mode(word)
      self.healthy(word)
      self.gesture(word)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)

  def test_full_stock_word_inventory_and_unknown_marker_rejection(self):
    for word in STOCK_AOL_WORDS:
      with self.subTest(word=hex(word)):
        self.mode(word)
        self.healthy(word)
        self.gesture(word)
        self.assertEqual(self.safety.aol_get_permission_mask(), 1)
        pt = 1 if word & 0x10 else 0
        self.assertFalse(self.safety.safety_tx_hook(self.packet(self.packer.make_can_msg('SCC_CONTROL', pt, {}))))
    for word in (0x803, 0x804, 0x815, 0x895, 0x830, 0x880, 0xC00):
      self.mode(word)
      self.safety.set_aol_test_heartbeat(True)
      self.safety.aol_set_host_request(3)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_source_expiry_and_wrong_bus_withdraw_permission(self):
    for word in (0x800 | fuel | topology for fuel in (0, 1, 2) for topology in (0, 8, 16, 32, 40, 144)):
      self.mode(word)
      self.healthy(word)
      self.gesture(word)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
      self.safety.set_timer(2_000_000)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
      self.mode(word)
      self.healthy(word, wrong_bus='WHEEL_SPEEDS')
      self.gesture(word)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
