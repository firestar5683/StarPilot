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
        ('WHEEL_SPEEDS', pt, {k: 36 for k in ('WHL_SpdFLVal', 'WHL_SpdFRVal', 'WHL_SpdRLVal', 'WHL_SpdRRVal')}),
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
