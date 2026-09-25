"""Captured ADRV encoding keeps local validation and Panda routing separate."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, CanData, structs
from opendbc.car.hyundai.ev6_template import EV6Template
from opendbc.car.hyundai.gv70_template import GV70Template
from opendbc.car.hyundai.hyundaicanfd import CanBus, create_adrv_messages, hkg_can_fd_checksum
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags

CAPTURE = bytes.fromhex('88ed2e091700ffff5e0d0000012006ff021c2200000000000800000010000000')


def buses(pandas: int, *, lka: bool = True) -> CanBus:
  configs = [structs.CarParams.SafetyConfig(safetyModel=structs.CarParams.SafetyModel.noOutput) for _ in range(pandas - 1)]
  configs.append(structs.CarParams.SafetyConfig(safetyModel=structs.CarParams.SafetyModel.hyundaiCanfd))
  cp = structs.CarParams(safetyConfigs=configs, flags=int(HyundaiFlags.CANFD_LKA_STEER_MSG) if lka else 0)
  return CanBus(cp)


class TestCapturedADRVRouting(unittest.TestCase):
  def setUp(self):
    self.packer = CANPacker(DBC[CAR.KIA_EV6][Bus.pt])

  def test_ev6_and_gv70_use_local_encoding_and_logical_owner_bus(self):
    for pandas in (1, 2):
      can = buses(pandas)
      self.assertEqual((can.offset, can.ACAN, can.ECAN), (4 * (pandas - 1), 4 * (pandas - 1), 4 * (pandas - 1) + 1))
      for template in (EV6Template.capture(CAPTURE), GV70Template.capture(CAPTURE)):
        for frame in (0, 7, 255, 256):
          for drive in (False, True):
            for speed in (None, 12.345):
              with self.subTest(pandas=pandas, template=type(template).__name__, frame=frame, drive=drive, speed=speed):
                local = (template.frame(frame, drive, 0, speed=speed) if isinstance(template, GV70Template) else
                         template.frame(frame, drive, 0))
                sent = create_adrv_messages(self.packer, can, frame, template=template, drive_gear=drive, speed=speed)
                self.assertEqual(sent[0], CanData(local.address, local.dat, can.ACAN))
                self.assertEqual(int.from_bytes(sent[0].dat[:2], 'little'), hkg_can_fd_checksum(0x51, None, bytearray(sent[0].dat)))
                self.assertEqual(template.data, CAPTURE)
                self.assertTrue(all(packet[2] == can.ECAN for packet in sent[1:]))
                if pandas == 2:
                  self.assertNotEqual(sent[0].src, 0)

  def test_default_packer_sender_preserves_logical_bus_for_both_harnesses(self):
    expected_packer = CANPacker(DBC[CAR.KIA_EV6][Bus.pt])
    for pandas in (1, 2):
      for lka in (False, True):
        can = buses(pandas, lka=lka)
        expected = expected_packer.make_can_msg('ADRV_0x51', can.ACAN, {})
        self.assertEqual(create_adrv_messages(self.packer, can, 7)[0], expected)

  def test_wrong_local_bus_and_noninteger_routing_remain_rejected(self):
    for pandas in (1, 2):
      for template in (EV6Template.capture(CAPTURE), GV70Template.capture(CAPTURE)):
        with self.subTest(pandas=pandas, template=type(template).__name__, local_bus=1):
          with self.assertRaises(ValueError):
            create_adrv_messages(self.packer, buses(pandas, lka=False), 7, template=template, drive_gear=True)
        for field, value in (('_a', False), ('_a', 0.0), ('offset', False), ('offset', 0.0)):
          can = buses(pandas)
          setattr(can, field, value)
          with self.subTest(pandas=pandas, template=type(template).__name__, field=field, value=value):
            with self.assertRaises(ValueError):
              create_adrv_messages(self.packer, can, 7, template=template, drive_gear=True)

  def test_template_physical_bus_and_drive_guards_remain_closed(self):
    for pandas in (1, 2):
      for template in (EV6Template.capture(CAPTURE), GV70Template.capture(CAPTURE)):
        for drive in (0, 1):
          with self.assertRaises(ValueError):
            create_adrv_messages(self.packer, buses(pandas), 7, template=template, drive_gear=drive)
        for bus in (False, 1, 4):
          with self.assertRaises(ValueError):
            template.frame(7, True, bus)
