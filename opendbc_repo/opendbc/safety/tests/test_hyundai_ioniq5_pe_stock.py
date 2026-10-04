"""Ordinary Ioniq 5 PE readiness and committed camera replacement ownership."""
import unittest

from opendbc.can import CANPacker
from opendbc.car.structs import CarParams
from opendbc.car.hyundai.hyundaicanfd import hkg_can_fd_checksum
from opendbc.safety.tests.libsafety import libsafety_py


class HyundaiOrdinaryAngleOwnershipChecks:
  DEFAULT_PARAM = None
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPacker('hyundai_canfd_generated')
    self.now = 1_000_000
    self.reset()

  def reset(self, word=None):
    word = self.DEFAULT_PARAM if word is None else word
    self.safety.init_tests()
    self.safety.set_alternative_experience(0)
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, word), 0)
    self.safety.set_timer(self.now)
    self.safety.set_aol_test_heartbeat(True)

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def feed(self, *, cruise=True, gear=5, speed=36.0, brake=False, fault=0, measured=0.0, buttons=True):
    self.safety.set_timer(self.now)
    entries = [('ACCELERATOR', {'GEAR': gear}),
               ('TCS', {'DriverBraking': int(brake)}),
               ('WHEEL_SPEEDS', dict.fromkeys(('WHL_SpdFLVal', 'WHL_SpdFRVal', 'WHL_SpdRLVal', 'WHL_SpdRRVal'), speed)),
               ('MDPS', {'MDPS_ADAS_AciFltSig_Lv2': fault, 'MDPS_PaStrAnglVal': measured}),
               ('CRUISE_BUTTONS', {'CRUISE_BUTTONS': 2}),
               ('SCC_CONTROL', {'ACCMode': 0}), ('SCC_CONTROL', {'ACCMode': int(cruise)})]
    for name, values in entries:
      if name == "CRUISE_BUTTONS" and not buttons:
        continue
      self.assertTrue(self.safety.safety_rx_hook(self.packet(self.packer.make_can_msg(name, 1, values))), name)
    self.now += 10_000

  def frame(self, counter=0, *, address=0x110, active=True, bad_crc=False, angle=0.0):
    name = 'LKAS_ALT' if address == 0x110 else 'CAM_0x362'
    _, packed, _ = self.packer.make_can_msg(name, 0, {'COUNTER': counter})
    data = bytearray(packed)
    if address == 0x110:
      data[9] = (2 if active else 1) << 4
      raw_angle = int(round(angle * 10)) & 0x3FFF
      data[10] = (raw_angle & 0x3F) << 2
      data[11] = raw_angle >> 6
      data[5], data[6] = 0, 8  # zero torque request, no torque enable
    data[:2] = hkg_can_fd_checksum(address, None, data).to_bytes(2, 'little')
    if bad_crc:
      data[0] ^= 1
    return libsafety_py.make_CANPacket(address, 0, data)

  def ready(self):
    for _ in range(6):
      self.feed()
    self.assertAlmostEqual(self.safety.get_vehicle_speed_min(), 10.0)
    self.assertTrue(self.safety.get_controls_allowed())
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)

  def test_ready_does_not_own_until_first_accepted_replacement(self):
    self.ready()
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x362), 0)
    self.assertFalse(self.safety.safety_tx_hook(self.frame(address=0x362)))
    self.assertTrue(self.safety.safety_tx_hook(self.frame()))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), -1)
    self.assertTrue(self.safety.safety_tx_hook(self.frame(address=0x362)))
    self.safety.aol_set_host_request(0)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    self.assertFalse(self.safety.safety_tx_hook(self.frame(1)))

  def test_crc_counter_and_final_relay_denials_cannot_acquire(self):
    self.ready()
    self.assertFalse(self.safety.safety_tx_hook(self.frame(bad_crc=True)))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    self.assertFalse(self.safety.safety_tx_hook(self.frame(active=False)))
    self.safety.set_relay_malfunction(True)
    self.assertFalse(self.safety.safety_tx_hook(self.frame()))
    self.safety.set_relay_malfunction(False)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    self.assertTrue(self.safety.safety_tx_hook(self.frame(254)))
    self.assertFalse(self.safety.safety_tx_hook(self.frame(254)))
    self.assertFalse(self.safety.safety_tx_hook(self.frame(253)))
    self.assertTrue(self.safety.safety_tx_hook(self.frame(0)))

  def test_missing_replacement_expires_with_fresh_requests_and_sources(self):
    self.ready()
    self.assertTrue(self.safety.safety_tx_hook(self.frame()))
    for tick in range(31):
      self.feed()
      self.safety.aol_set_host_request(1)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
      self.assertFalse(self.safety.safety_tx_hook(self.frame(1, bad_crc=True)))
      # Suppression traffic is accepted while ownership is current, but cannot
      # sustain it when replacement steering stops arriving.
      self.assertEqual(self.safety.safety_tx_hook(self.frame(address=0x362)), tick < 30)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x362), 0)
    self.assertFalse(self.safety.safety_tx_hook(self.frame(address=0x362)))
    self.assertTrue(self.safety.safety_tx_hook(self.frame(2)))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), -1)

  def test_gear_standstill_fault_heartbeat_and_profile_release(self):
    for changed in ({'gear': 0}, {'speed': 0.0}, {'fault': 1}, {'brake': True}):
      self.reset()
      self.ready()
      self.assertTrue(self.safety.safety_tx_hook(self.frame()))
      self.feed(**changed)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
      self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    self.reset()
    self.ready()
    self.assertTrue(self.safety.safety_tx_hook(self.frame()))
    self.safety.set_aol_test_heartbeat(False)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    for bit in (2, 4, 8, 32, 256, 512, 2048, 8192, 32768):
      self.reset(self.DEFAULT_PARAM | bit)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_counter_restart_and_nonzero_measured_angle_reacquisition(self):
    self.ready()
    self.assertTrue(self.safety.safety_tx_hook(self.frame(100)))
    # Continuous ownership accepts skipped forward counters but not reverse.
    self.assertTrue(self.safety.safety_tx_hook(self.frame(103)))
    self.assertFalse(self.safety.safety_tx_hook(self.frame(102)))
    self.safety.aol_set_host_request(0)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    self.feed(measured=3.0)
    self.safety.aol_set_host_request(0)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    # A restarted controller may start at zero in a new acquisition. The
    # shared limiter now starts from actual EPS angle, not the old OP request.
    self.assertTrue(self.safety.safety_tx_hook(self.frame(0, angle=3.0)))
    self.assertFalse(self.safety.safety_tx_hook(self.frame(1, angle=90.0)))
    self.safety.aol_set_host_request(0)
    self.feed(measured=3.0)
    self.safety.aol_set_host_request(0)
    self.safety.aol_set_host_request(1)
    self.assertFalse(self.safety.safety_tx_hook(self.frame(0, angle=360.0)))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    self.assertTrue(self.safety.safety_tx_hook(self.frame(0, angle=3.0)))

  def test_expired_owner_reacquires_from_110_without_forward_query(self):
    self.ready()
    self.assertTrue(self.safety.safety_tx_hook(self.frame(100)))
    # Keep readiness alive while withholding steering and forwarding callbacks.
    # 110 itself must expire the old counter before a restarted sender acquires.
    for _ in range(31):
      self.feed()
      self.safety.aol_set_host_request(1)
    self.assertTrue(self.safety.safety_tx_hook(self.frame(0)))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), -1)

  def test_core_wrong_bus_length_and_unlisted_tx_never_acquire(self):
    self.ready()
    good = self.frame()
    payload = bytes(good[0].data[0:32])
    for address, bus, data in ((0x110, 1, payload), (0x110, 0, payload[:24]), (0x111, 0, payload)):
      rejected = libsafety_py.make_CANPacket(address, bus, data)
      self.assertFalse(self.safety.safety_tx_hook(rejected))
      self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    self.assertTrue(self.safety.safety_tx_hook(good))

  def test_angle_and_shared_stock_namespaces_are_exact_and_invalid_experience_denied(self):
    # Shared torque-stock words and Ioniq6 ordinary/LONG selectors have separate owners.
    supported = {
      0x0800, 0x0801, 0x0802, 0x0808, 0x0809, 0x080A,
      0x0810, 0x0811, 0x0812, 0x0820, 0x0821, 0x0822,
      0x0828, 0x0829, 0x082A, 0x0890, 0x0891, 0x0892,
      0x0C08, 0x0C09, 0x0C0A, 0x0C28, 0x0C29, 0x0C2A,
      0x2820, 0x2822, 0x2828, 0x282A, 0x2830, 0x2832,
      0x28B0, 0x28B2, 0x2C28, 0x2C2A,
      0x8815, 0x8895, 0x5491, 0x5C91,
    }
    for word in range(0x10000):
      if word in supported:
        continue
      self.reset(word)
      self.safety.aol_set_host_request(3)
      self.assertEqual(self.safety.aol_get_request_mask(), 0, hex(word))
    self.reset()
    self.safety.aol_set_host_request(3)
    self.assertEqual(self.safety.aol_get_request_mask(), 1)
    self.safety.init_tests()
    self.safety.set_alternative_experience(1)
    self.safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, self.DEFAULT_PARAM)
    self.safety.set_timer(self.now)
    self.safety.set_aol_test_heartbeat(True)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_request_mask(), 0)

  def test_required_source_expiry_releases_camera_owner(self):
    self.ready()
    self.assertTrue(self.safety.safety_tx_hook(self.frame()))
    self.now += 1_000_000
    self.safety.set_timer(self.now)
    self.safety.aol_set_host_request(1)
    self.safety.safety_tick()
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    self.assertFalse(self.safety.safety_tx_hook(self.frame(1)))

  def test_first_acquisition_uses_measured_angle_without_prior_release(self):
    # No forwarding query or zero host request seeds the inactive baseline.
    for _ in range(6):
      self.feed(measured=3.0)
    self.assertAlmostEqual(self.safety.get_vehicle_speed_min(), 10.0)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.assertFalse(self.safety.safety_tx_hook(self.frame(angle=90.0)))
    self.assertTrue(self.safety.safety_tx_hook(self.frame(angle=3.0)))
    self.assertFalse(self.safety.safety_tx_hook(self.frame(1, angle=90.0)))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), -1)

  def test_missing_or_stale_required_buttons_cannot_claim_readiness(self):
    for _ in range(6):
      self.feed(buttons=False)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    self.assertFalse(self.safety.safety_tx_hook(self.frame()))
    self.reset()
    self.ready()
    self.assertTrue(self.safety.safety_tx_hook(self.frame()))
    # 250 ms exceeds this required 50-Hz source's 200-ms freshness bound,
    # while accepted-110's 300-ms lease and every other RX source remain fresh.
    for _ in range(25):
      self.feed(buttons=False)
      self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x110), 0)
    self.assertFalse(self.safety.safety_tx_hook(self.frame(1)))


class TestIoniq5PeStockOwnership(HyundaiOrdinaryAngleOwnershipChecks, unittest.TestCase):
  DEFAULT_PARAM = 0x5491
