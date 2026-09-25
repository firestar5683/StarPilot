"""Experimental mixed longitudinal safety contract regressions."""
import unittest
from opendbc.car.structs import CarParams
from opendbc.safety.tests import common
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests.test_hyundai import checksum


class TestHyundaiBlendedAlpha(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = common.CANPackerSafety('hyundai_palisade_2023_generated')

  def select(self, hda2):
    self.bus = int(hda2)
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.hyundai,
                                               0x2014 if hda2 else 0x2004), 0)
    self.safety.init_tests()

  def primary(self, torque, request):
    data = bytearray(16)
    raw = torque + 1024
    data[5] = (raw & 0x7F) << 1
    data[6] = ((raw >> 7) & 0xF) | (int(request) << 4)
    return common.make_msg(0, 0x50, dat=bytes(data))

  def mirror(self, torque, request):
    data = bytearray(8)
    raw = torque + 1024
    data[2] = raw & 0xFF
    data[3] = ((raw >> 8) & 7) | (int(request) << 3)
    return common.make_msg(1, 0x340, dat=bytes(data))

  def test_secondary_torque_requires_accepted_one_use_primary(self):
    self.select(True)
    self.safety.set_controls_allowed(True)
    self.safety.set_torque_driver(0, 0)
    self.assertFalse(self.safety.safety_tx_hook(self.mirror(3, True)))
    self.assertTrue(self.safety.safety_tx_hook(self.primary(3, True)))
    self.assertTrue(self.safety.safety_tx_hook(self.mirror(3, True)))
    self.assertFalse(self.safety.safety_tx_hook(self.mirror(3, True)))
    self.assertFalse(self.safety.safety_tx_hook(self.primary(30, True)))
    self.assertFalse(self.safety.safety_tx_hook(self.mirror(30, True)))
    self.select(True)
    self.safety.set_controls_allowed(True)
    self.assertTrue(self.safety.safety_tx_hook(self.primary(3, True)))
    self.safety.set_timer(10001)
    self.assertFalse(self.safety.safety_tx_hook(self.mirror(3, True)))

  def test_acceleration_layout_limits_and_off_zero(self):
    for hda2 in (False, True):
      self.select(hda2)
      for allowed, accel, expected in ((False, 0, True), (False, .01, False),
                                       (True, -3.5, True), (True, 3.5, True),
                                       (True, -3.51, False), (True, 3.51, False)):
        self.safety.set_controls_allowed(allowed)
        for raw, value in ((accel, 0), (0, accel)):
          packet = self.packer.make_can_msg_safety('SCC11', self.bus,
                                                 {'aReqRaw': raw, 'aReqValue': value})
          self.assertEqual(self.safety.safety_tx_hook(packet), expected)

  def test_unresolved_payload_owners_and_non_tester_uds_stay_closed(self):
    for hda2 in (False, True):
      self.select(hda2)
      self.safety.set_controls_allowed(True)
      for address in (0x38D, 0x4F1):
        self.assertFalse(self.safety.safety_tx_hook(common.make_msg(self.bus, address)))
      self.assertEqual(self.safety.safety_tx_hook(common.make_msg(0, 0x51, 32)), hda2)
      modified = bytearray(32)
      modified[3] = 1
      self.assertFalse(self.safety.safety_tx_hook(common.make_msg(0, 0x51, dat=bytes(modified))))
      address = 0x730 if hda2 else 0x7D0
      self.assertTrue(self.safety.safety_tx_hook(common.make_msg(self.bus, address,
        dat=b'\x02\x3e\x80\x00\x00\x00\x00\x00')))
      self.assertFalse(self.safety.safety_tx_hook(common.make_msg(self.bus, address,
        dat=b'\x03\x28\x03\x01\x00\x00\x00\x00')))

  def test_hda2_fca_exact_original_source_pattern_and_request_guards(self):
    self.select(True)
    for counter in range(15):
      packet = self.packer.make_can_msg_safety('FCA11', 1,
        {'cr_vsm_deccmd': 255, 'cf_vsm_deccmdact': 0, 'COUNTER': counter, 'CHECKSUM': 0xA5})
      self.assertEqual(bytes(packet[0].data[0:8]), bytes([0xA5, counter << 4, 0, 0, 0xC0, 0x3F, 0x7F, 0]))
      self.assertTrue(self.safety.safety_tx_hook(packet))
      for index in range(2, 8):
        for bit in range(8):
          changed = bytearray([0xA5, counter << 4, 0, 0, 0xC0, 0x3F, 0x7F, 0])
          changed[index] ^= 1 << bit
          self.assertFalse(self.safety.safety_tx_hook(common.make_msg(1, 0x38D, dat=bytes(changed))))
      for bit in range(4):
        changed = bytearray([0xA5, (counter << 4) | (1 << bit), 0, 0, 0xC0, 0x3F, 0x7F, 0])
        self.assertFalse(self.safety.safety_tx_hook(common.make_msg(1, 0x38D, dat=bytes(changed))))
    valid = bytes([0xA5, 0, 0, 0, 0xC0, 0x3F, 0x7F, 0])
    for allowed in (False, True):
      self.safety.set_controls_allowed(allowed)
      self.assertTrue(self.safety.safety_tx_hook(common.make_msg(1, 0x38D, dat=valid)))
    for length in (0, 1, 4, 7, 12, 16):
      self.assertFalse(self.safety.safety_tx_hook(common.make_msg(1, 0x38D, dat=valid[:length].ljust(length, b'\x00'))))
    for bus in (0, 2, 3):
      self.assertFalse(self.safety.safety_tx_hook(common.make_msg(bus, 0x38D, dat=valid)))
    self.assertFalse(self.safety.safety_tx_hook(common.make_msg(1, 0x38D,
      dat=bytes([0xA5, 0xF0, 0, 0, 0xC0, 0x3F, 0x7F, 0]))))
    self.select(False)
    self.assertFalse(self.safety.safety_tx_hook(common.make_msg(0, 0x38D, dat=valid)))

  def test_fixed_radar_aux_source_bytes_and_mutations(self):
    for hda2 in (False, True):
      self.select(hda2)
      specs = [('RADAR_0x363', {'FCA_ESA': 1}),
               ('RADAR_0x398', {'BYTE4': 0x80, 'BYTE5': 0x5D if hda2 else 0x10})]
      if hda2:
        specs += [('RADAR_0x399', {'BYTE2': 2}), ('RADAR_0x39a', {'BYTE7': 0xFF}),
                  ('RADAR_0x39b', {}), ('RADAR_0x39c', {'BYTE5': 0xE0, 'BYTE6': 0x79}),
                  ('RADAR_0x43a', {'BYTE2': 7})]
      for name, fields in specs:
        for counter in range(16):
          packet = self.packer.make_can_msg_safety(name, self.bus,
            fields | {'COUNTER': counter, 'CHECKSUM': 0xA5})
          self.assertTrue(self.safety.safety_tx_hook(packet))
          for index in range(2, 8):
            for bit in range(8):
              modified = self.packer.make_can_msg_safety(name, self.bus,
                fields | {'COUNTER': counter, 'CHECKSUM': 0xA5})
              modified[0].data[index] ^= 1 << bit
              self.assertFalse(self.safety.safety_tx_hook(modified))

  def tcs(self, active, counter=0):
    values = {'ACC_REQ': int(active), 'AliveCounterTCS': counter}
    return self.packer.make_can_msg_safety('TCS13', self.bus, values, fix_checksum=checksum)

  def button(self, value, counter):
    return self.packer.make_can_msg_safety('CLU11', self.bus,
      {'CF_Clu_CruiseSwState': value, 'CF_Clu_AliveCnt1': counter})

  def test_cancel_enable_pair_and_active_stop_do_not_use_stale_stock_flag(self):
    for hda2 in (False, True):
      self.select(hda2)
      self.assertTrue(self.safety.safety_rx_hook(self.tcs(False)))
      self.safety.safety_rx_hook(self.button(4, 0))
      self.assertFalse(self.safety.get_controls_allowed())
      self.safety.safety_rx_hook(self.button(0, 1))
      self.assertTrue(self.safety.get_controls_allowed())
      self.safety.safety_rx_hook(self.button(4, 2))
      self.assertFalse(self.safety.get_controls_allowed())
      self.safety.safety_rx_hook(self.button(0, 3))
      self.assertFalse(self.safety.get_controls_allowed())
      self.select(hda2)
      self.safety.safety_rx_hook(self.tcs(True))
      self.safety.safety_rx_hook(self.button(4, 0))
      self.safety.safety_rx_hook(self.button(0, 1))
      self.assertFalse(self.safety.get_controls_allowed())

  def test_cancel_latch_cannot_survive_intervening_inhibits(self):
    for hda2 in (False, True):
      for inhibit in ('tcs', 'brake', 'gas', 'stale'):
        with self.subTest(hda2=hda2, inhibit=inhibit):
          self.select(hda2)
          self.assertTrue(self.safety.safety_rx_hook(self.tcs(False, 0)))
          self.assertTrue(self.safety.safety_rx_hook(self.button(4, 0)))
          if inhibit == 'tcs':
            self.assertTrue(self.safety.safety_rx_hook(self.tcs(True, 1)))
            self.assertTrue(self.safety.safety_rx_hook(self.tcs(False, 2)))
          elif inhibit == 'brake':
            for counter, pressed in ((1, True), (2, False)):
              packet = self.packer.make_can_msg_safety('TCS13', self.bus,
                {'DriverOverride': 2 if pressed else 0, 'AliveCounterTCS': counter}, fix_checksum=checksum)
              self.assertTrue(self.safety.safety_rx_hook(packet))
          elif inhibit == 'gas':
            for counter, pressed in ((0, True), (1, False)):
              packet = self.packer.make_can_msg_safety('EMS16', self.bus,
                {'CF_Ems_AclAct': int(pressed), 'AliveCounter': counter}, fix_checksum=checksum)
              self.assertTrue(self.safety.safety_rx_hook(packet))
          else:
            self.safety.set_timer(100001)
            self.assertTrue(self.safety.safety_rx_hook(self.tcs(False, 1)))
          self.assertTrue(self.safety.safety_rx_hook(self.button(4, 1)))
          self.assertTrue(self.safety.safety_rx_hook(self.button(0, 2)))
          self.assertFalse(self.safety.get_controls_allowed())
          # A new inactive pair may enable after the inhibit has cleared.
          self.assertTrue(self.safety.safety_rx_hook(self.button(4, 3)))
          self.assertTrue(self.safety.safety_rx_hook(self.button(0, 4)))
          self.assertTrue(self.safety.get_controls_allowed())
