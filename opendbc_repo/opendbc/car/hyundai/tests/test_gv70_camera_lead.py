"""Actual isolated parser tests using synthetic packed camera CAN evidence."""
import unittest
from unittest.mock import patch

from opendbc.can.packer import CANPacker
from opendbc.car import Bus, CanData, gen_empty_fingerprint, structs
from opendbc.car.hyundai.gv70_camera_lead import GV70CameraLead
from opendbc.car.hyundai.hyundaicanfd import CanBus, hkg_can_fd_checksum
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags


def params(lka=True):
  fingerprint = gen_empty_fingerprint()
  if lka:
    fingerprint[2][0x50] = 16
  fingerprint[1 if lka else 0][0x1cf] = 8
  firmware = [structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.adas)] if lka else []
  cp = CarInterface.get_params(CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN, fingerprint, firmware, True, False, False)
  assert bool(cp.flags & HyundaiFlags.CANFD_LKA_STEER_MSG) == lka
  return cp


def packet(packer, bus, counter, distance=12., relative=-2.):
  address, raw, src = packer.make_can_msg('FR_CMR_03_50ms', bus, {
    'FR_CMR_AlvCnt3Val': counter, 'Longitudinal_Distance': distance, 'Relative_Velocity': relative})
  data = bytearray(raw)
  data[:2] = hkg_can_fd_checksum(address, None, data).to_bytes(2, 'little')
  return CanData(address, bytes(data), src)



class TestGV70CameraLead(unittest.TestCase):
  def setUp(self):
    boot_clock = patch("opendbc.car.hyundai.canfd_camera_lead.time.CLOCK_BOOTTIME", 7, create=True)
    boot_clock.start()
    self.addCleanup(boot_clock.stop)
    self.clock = patch("opendbc.car.hyundai.canfd_camera_lead.time.clock_gettime_ns", return_value=10_000_000_000)
    self.clock_mock = self.clock.start()
    self.addCleanup(self.clock.stop)

  def test_scoped_raw_integrity_units_and_topology(self):
    for lka in (True, False):
      cp = params(lka)
      owner = GV70CameraLead(cp)
      buses = CanBus(cp)
      self.assertEqual(owner.bus, buses.ECAN if lka else buses.CAM)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      for counter in (1, 2):
        owner.update([(counter*50_000_000, [packet(packer, owner.bus, counter)])])
      observation = owner.current(100_000_000)
      self.assertIsNotNone(observation)
      self.assertTrue(observation.visible)
      self.assertEqual(observation.distance_m, 12.)
      self.assertEqual(observation.relative_speed_mps, -2.)
      decoded = owner.parser.vl['FR_CMR_03_50ms']
      self.assertNotIn('CHECKSUM', decoded)
      self.assertNotIn('COUNTER', decoded)
      self.assertEqual(decoded['FR_CMR_AlvCnt3Val'], 2)
      self.assertEqual(owner.parser.message_states[0x1b5].counter_fail, 0)

  def test_bad_crc_counter_wrong_bus_length_do_not_renew_and_expire(self):
    cp = params()
    owner = GV70CameraLead(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    owner.update([(50_000_000, [packet(packer, owner.bus, 1)])])
    good = owner.current(50_000_000)
    self.assertIsNotNone(good)
    wrong_crc = bytearray(packet(packer, owner.bus, 2).dat)
    wrong_crc[27] ^= 1
    owner.update([(100_000_000, [(0x1b5, bytes(wrong_crc), owner.bus)])])
    self.assertEqual(owner.current(100_000_000), good)
    # Repeated raw counters cannot renew the optional observation.
    for tick in range(3, 9):
      owner.update([(tick*50_000_000, [packet(packer, owner.bus, 1)])])
    self.assertEqual(owner.observation, good)
    self.assertIsNone(owner.current(400_000_000))
    for bus, data in ((owner.bus+1, packet(packer, owner.bus, 3).dat),
                      (owner.bus, bytes(31)), (owner.bus, bytes(33))):
      owner.update([(450_000_000, [(0x1b5, data, bus)])])
    self.assertEqual(owner.observation, good)
    owner.update([(500_000_000, [packet(packer, owner.bus, 2)])])
    self.assertEqual(owner.current(500_000_000).producer_boot_ns, 500_000_000)
    owner.update([(550_000_000, [packet(packer, owner.bus, 4)])])
    self.assertEqual(owner.observation.producer_boot_ns, 500_000_000)
    owner.update([(600_000_000, [packet(packer, owner.bus, 5)])])
    self.assertEqual(owner.current(600_000_000).producer_boot_ns, 600_000_000)

  def test_clock_floor_visibility_and_descriptor_scope(self):
    cp = params()
    owner = GV70CameraLead(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    owner.update([(100_000_000, [packet(packer, owner.bus, 1, .1)])])
    self.assertFalse(owner.current(100_000_000).visible)
    self.assertIsNone(owner.current(99_999_999))
    self.assertIsNone(owner.current(100_000_000, 100_000_000))
    self.assertIsNotNone(owner.current(400_000_000))
    self.assertIsNone(owner.current(400_000_001))
    previous_counter = owner.last_counter
    owner.update([(99_999_999, [packet(packer, owner.bus, 2, .15)])])
    self.assertEqual(owner.last_counter, previous_counter)
    owner.update([(10_000_000_001, [packet(packer, owner.bus, 2, .15)])])
    self.assertEqual(owner.last_counter, previous_counter)
    self.assertIsNone(owner.current(10_000_000_001))
    self.assertEqual(owner.observation.producer_boot_ns, 100_000_000)
    with patch("opendbc.car.hyundai.canfd_camera_lead.time.CLOCK_BOOTTIME", None):
      owner.update([(200_000_000, [packet(packer, owner.bus, 2, .15)])])
    with patch("opendbc.car.hyundai.canfd_camera_lead.time.clock_gettime_ns", side_effect=OSError):
      owner.update([(200_000_000, [packet(packer, owner.bus, 2, .15)])])
    self.assertEqual(owner.observation.producer_boot_ns, 100_000_000)
    self.assertEqual(owner.last_packet_ns, 100_000_000)
    cp.openpilotLongitudinalControl = False
    with self.assertRaises(ValueError):
      GV70CameraLead(cp)
    cp.openpilotLongitudinalControl = True
    cp.carFingerprint = CAR.KIA_EV6
    with self.assertRaises(ValueError):
      GV70CameraLead(cp)

  def test_isolated_counter_failure_does_not_join_controls_health(self):
    cp = params()
    ci = CarInterface(cp)
    owner = GV70CameraLead(cp)
    self.assertNotIn(owner.parser, ci.can_parsers.values())
    self.assertTrue(all(0x1b5 not in parser.addresses for parser in ci.can_parsers.values()))
    before = [(parser.can_valid, parser.bus_timeout, parser.can_invalid_cnt) for parser in ci.can_parsers.values()]
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    for tick in range(8):
      owner.update([((tick+1)*50_000_000, [packet(packer, owner.bus, 1)])])
    self.assertEqual(owner.observation.producer_boot_ns, 50_000_000)
    after = [(parser.can_valid, parser.bus_timeout, parser.can_invalid_cnt) for parser in ci.can_parsers.values()]
    self.assertEqual([x[:2] for x in before], [x[:2] for x in after])
