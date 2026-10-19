#!/usr/bin/env python3
"""Always On Lateral on SecOC TSS2 Toyotas (2021+ Sienna, safety param 2121 = EPS scale 73 | SECOC).

They have no 0x3BC GEAR_PACKET: the gear is read from 0x127 GEAR_PACKET_HYBRID (P 0, R 1, N 2, D 3, B 4; checksummed,
~60 Hz). Everything else is the TSS2 rule: main switch, doors, EPS state, and for longitudinal also cruise and belt.
"""
import unittest

from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py

WORD = 2121
P, R, N, D, B = 0, 1, 2, 3, 4


REAL_1D3 = bytes.fromhex("00a81d39f80000d2")
REAL_620 = bytes.fromhex("000000008000001a")
REAL_262 = bytes.fromhex("0008000208ffff7c")


def checksum(address, data):
  data = bytearray(data)
  data[-1] = ((address & 255) + (address >> 8) + len(data) + sum(data[:-1])) & 255
  return bytes(data)


class TestToyotaSecocAol(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety

  def tearDown(self):
    self.safety.set_alternative_experience(0)
    self.safety.set_safety_hooks(CarParams.SafetyModel.noOutput, 0)

  def init(self, word=WORD, ae=32):
    self.omit_addresses = set()
    self.safety.init_tests()
    self.safety.set_alternative_experience(ae)
    self.safety.set_safety_hooks(CarParams.SafetyModel.toyota, word)
    self.safety.set_timer(1_000_000)
    self.safety.set_aol_test_heartbeat(True)

  def rx(self, address, data, crc=False, bus=0):
    if address in getattr(self, "omit_addresses", ()):
      return
    data = checksum(address, data) if crc else bytes(data)
    self.assertTrue(self.safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data)))

  def gear(self, g, crc=True):
    self.rx(0x127, bytes(5) + bytes([g << 4]) + bytes(2), crc)

  def physical(self, *, gear=D, cruise=False, belt=True, main=True, door=False, eps=1, brake=False, gas=False, real=False, request=True):
    self.rx(0xAA, bytes([0x1A, 0x6F] * 4))
    self.rx(0x260, bytes(8), True)
    self.rx(0x176, bytes([32 if cruise else 0]) + bytes(7), True)
    self.rx(0x116, bytes([0, 10 if gas else 0]) + bytes(6))
    self.rx(0x101, bytes([8 if brake else 0]) + bytes(7))
    if real:
      self.rx(0x1D3, REAL_1D3)
      self.rx(0x620, REAL_620)
      self.rx(0x262, REAL_262)
    else:
      self.rx(0x1D3, bytes([0, 128 if main else 0]) + bytes(6), True)
      self.rx(0x620, bytes(5) + bytes([4 if door else 0, 0, 0 if belt else 64]))
      self.rx(0x262, bytes(3) + bytes([eps << 1]) + bytes(4), True)
    if gear is not None:
      self.gear(gear)
    if request:
      self.safety.aol_set_host_request(3)

  def test_drive_and_b_grant_lateral(self):
    for g in (D, B):
      self.init()
      self.physical(gear=g)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
      self.physical(gear=g, cruise=True)
      self.assertEqual(self.safety.aol_get_permission_mask(), 3)

  def test_park_reverse_neutral_deny(self):
    for g in (P, R, N, 5, 15):
      self.init()
      self.physical(gear=D)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
      self.physical(gear=g)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0, g)

  def test_real_sienna_frames(self):
    self.init()
    self.physical(real=True, gear=D)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.physical(real=True, gear=P)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_gear_packet_is_not_the_source_on_secoc(self):
    self.init()
    self.physical(gear=None)
    self.rx(0x3BC, bytes(8))
    self.safety.aol_set_host_request(3)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_hybrid_gear_is_not_the_source_without_secoc(self):
    self.safety.init_tests()
    self.safety.set_alternative_experience(32)
    self.safety.set_safety_hooks(CarParams.SafetyModel.toyota, 73)
    self.safety.set_timer(1_000_000)
    self.safety.set_aol_test_heartbeat(True)
    self.rx(0xAA, bytes([0x1A, 0x6F] * 4))
    self.rx(0x260, bytes(8), True)
    self.rx(0x1D2, bytes([16]) + bytes(7), True)
    self.rx(0x226, bytes(8))
    self.rx(0x1D3, bytes([0, 128]) + bytes(6), True)
    self.rx(0x620, bytes(8))
    self.rx(0x262, bytes(3) + bytes([2]) + bytes(4), True)
    self.gear(D)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.rx(0x3BC, bytes(8))
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)

  def test_gear_checksum_and_length_faults(self):
    self.init()
    self.physical()
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.gear(D, crc=False)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.physical()
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.safety.safety_rx_hook(libsafety_py.make_CANPacket(0x127, 0, bytes(7)))
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.physical()
    self.safety.safety_rx_hook(libsafety_py.make_CANPacket(0x127, 1, bytes(7)))
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)

  def test_gear_expiry(self):
    for delta, fresh in ((200000, True), (200001, False)):
      self.init()
      self.physical()
      self.safety.set_timer(1_000_000 + delta)
      self.safety.set_aol_test_heartbeat(True)
      self.physical(gear=None)
      self.assertEqual(self.safety.aol_get_permission_mask(), int(fresh), delta)

  def test_other_conditions_still_apply(self):
    for changes in ({"main": False}, {"door": True}, {"eps": 9}, {"eps": 17}, {"eps": 3}):
      self.init()
      self.physical()
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
      self.physical(**changes)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0, changes)
    for changes in ({"belt": False}, {"brake": True}, {"gas": True}):
      self.init()
      self.physical(cruise=True)
      self.assertEqual(self.safety.aol_get_permission_mask(), 3)
      self.physical(cruise=True, **changes)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1, changes)

  def steer(self, torque, req=True):
    data = bytes([1 if req else 0]) + (torque & 0xFFFF).to_bytes(2, "big") + bytes(5)
    return bool(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x2E4, 0, data)))

  def test_torque_steering_follows_the_gear(self):
    self.init()
    self.physical(gear=D)
    self.assertTrue(self.steer(0, req=False))
    self.assertTrue(self.steer(10))
    self.physical(gear=P)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.assertFalse(self.steer(10))
    self.assertTrue(self.steer(0, req=False))

  def test_lta_stays_blocked(self):
    self.init()
    self.physical(gear=D, cruise=True)
    self.assertEqual(self.safety.aol_get_permission_mask(), 3)
    self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x131, 0, bytes([8]) + bytes(7))))

  def test_exact_admission(self):
    for word, ae in ((WORD, 0), (WORD, 160), (WORD, 288), (WORD, 33), (WORD | 512, 32), (2120, 32), (2122, 32)):
      self.init(word, ae)
      self.physical()
      self.assertEqual(self.safety.aol_get_request_mask(), 0, (word, ae))

  def test_each_optional_physical_source_deadline(self):
    for address, deadline in ((0x1D3, 303031), (0x127, 200000), (0x620, 3333334), (0x262, 400000)):
      for delta, allowed in ((deadline, True), (deadline + 1, False)):
        with self.subTest(address=address, delta=delta):
          self.init()
          self.physical()
          self.omit_addresses = {address}
          self.safety.set_timer(1_000_000 + delta)
          self.physical()
          self.assertEqual(self.safety.aol_get_permission_mask(), int(allowed))

  def test_wrong_bus_and_nonselected_gear_cannot_refresh_gear(self):
    self.init()
    self.physical()
    self.safety.set_timer(1_200_001)
    self.omit_addresses = {0x127}
    self.physical()
    self.rx(0x3BC, bytes(8))
    self.rx(0x127, bytes(5) + bytes([D << 4]) + bytes(2), crc=True, bus=2)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_main_fault_each_door_and_every_rejected_eps_state(self):
    for door_bit in (2, 3, 4, 5):
      self.init()
      self.physical()
      self.rx(0x620, bytes(5) + bytes([1 << door_bit]) + bytes(2))
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    for eps in (0, 3, 9, 11, 17, 21, 25):
      self.init()
      self.physical(eps=eps)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.init()
    self.physical()
    self.rx(0x1D3, bytes([0, 128, 0, 0, 0, 128, 0, 0]), crc=True)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_host_heartbeat_request_and_required_rx_health_are_independent(self):
    self.init()
    self.physical(cruise=True)
    self.assertEqual(self.safety.aol_get_permission_mask(), 3)
    self.safety.set_aol_test_heartbeat(False)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.safety.set_aol_test_heartbeat(True)
    self.safety.aol_set_host_request(0)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.physical(cruise=True)
    self.safety.set_relay_malfunction(True)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.safety.set_relay_malfunction(False)
    self.init()
    self.physical(cruise=True)
    self.safety.safety_rx_hook(libsafety_py.make_CANPacket(0x260, 0, bytes(8)))
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_host_request_lease_expires_with_all_physical_inputs_fresh(self):
    for elapsed, allowed in ((300000, True), (300001, False)):
      self.init()
      self.physical(cruise=True)
      self.safety.set_timer(1_000_000 + elapsed)
      self.physical(cruise=True, request=False)
      self.assertEqual(self.safety.aol_get_permission_mask(), 3 if allowed else 0)

  def test_optional_source_corruption_revokes_until_fresh_recovery(self):
    for address in (0x1D3, 0x127, 0x620, 0x262):
      self.init()
      self.physical(cruise=True)
      self.assertEqual(self.safety.aol_get_permission_mask(), 3)
      self.safety.safety_rx_hook(libsafety_py.make_CANPacket(address, 0, bytes(7)))
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
      self.physical(cruise=True)
      self.assertEqual(self.safety.aol_get_permission_mask(), 3)
      if address != 0x620:
        self.safety.safety_rx_hook(libsafety_py.make_CANPacket(address, 0, bytes(8)))
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_native_torque_and_accel_limits_are_not_bypassed(self):
    for torque, allowed in ((15, True), (16, False), (1501, False), (-1501, False)):
      self.init()
      self.physical(cruise=False)
      self.assertEqual(self.steer(torque), allowed)
    for accel, allowed in ((-3501, False), (-3500, True), (2000, True), (2001, False)):
      self.init()
      self.physical(cruise=True)
      packet = libsafety_py.make_CANPacket(0x183, 0, (accel & 0xffff).to_bytes(2, 'big') + bytes(6))
      self.assertEqual(bool(self.safety.safety_tx_hook(packet)), allowed)
    self.init()
    self.physical(cruise=False)
    self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x183, 0, bytes([0, 1]) + bytes(6))))
    self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x343, 0, bytes([0, 1]) + bytes(6))))


if __name__ == "__main__":
  unittest.main()
