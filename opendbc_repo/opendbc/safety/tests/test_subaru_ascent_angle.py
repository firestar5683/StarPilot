import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.subaru import subarucan
from opendbc.car.subaru.values import CAR, DBC, SubaruSafetyFlags
from opendbc.car.subaru.tests.test_ascent_angle import setup_controller, step
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests import test_subaru_gen2_angle_pair as pair


class TestSubaruAscentAngle(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.cp, self.controller, self.command, self.state = setup_controller()
    self.packer = CANPacker(DBC[CAR.SUBARU_ASCENT_2023][Bus.pt])

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def arm(self, **changes):
    cfg = self.cp.safetyConfigs[0]
    self.assertEqual(self.safety.set_safety_hooks(cfg.safetyModel.raw, cfg.safetyParam), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)
    speed = changes.pop('speed', 30.3 * 3.6)
    _, frames = pair.TestSubaruGen2AnglePair.sources(CAR.SUBARU_ASCENT_2023, speed=speed, **changes)
    for frame in frames:
      if frame[0] in {0x40, 0x119, 0x11A, 0x13A, 0x13C, 0x222, 0x321}:
        self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))
    for counter in range(1, 6):
      wheel = self.packer.make_can_msg("Wheel_Speeds", 1, {"FL": speed, "FR": speed, "RL": speed, "RR": speed, "COUNTER": counter})
      self.assertTrue(self.safety.safety_rx_hook(self.packet(wheel)))
    self.safety.safety_tick()
    self.assertTrue(self.safety.safety_config_valid())

  def angle(self, value, active=True, bus=0):
    return self.packet(subarucan.create_steering_control_angle(self.packer, value, active, bus))

  def test_host_inactive_entry_and_reentry_match_native_history(self):
    self.arm()
    self.state.out.vEgoRaw = 30.3
    self.state.out.steeringAngleDeg = 0.78
    self.state.out.steeringRateDeg = -1.5
    self.controller.ascent_handoff_active = True
    self.safety.set_angle_meas(78, 78)
    steer, decoded = step(self.controller, self.command, self.state)
    self.assertFalse(decoded['LKAS_Request'])
    self.assertTrue(self.safety.safety_tx_hook(self.packet(steer)))
    self.state.out.steeringAngleDeg = 0.74
    self.state.out.steeringRateDeg = -1.99
    self.safety.set_angle_meas(74, 74)
    steer, decoded = step(self.controller, self.command, self.state)
    self.assertAlmostEqual(decoded['LKAS_Output'], 0.53, delta=0.01)
    self.assertTrue(self.safety.safety_tx_hook(self.packet(steer)))
    self.assertFalse(self.safety.safety_tx_hook(self.angle(-1.45)))

  def test_first_nonzero_angle_primes_native_history_before_request(self):
    self.arm()
    self.state.out.vEgoRaw = 30.3
    self.state.out.steeringAngleDeg = 20.0
    self.state.out.steeringRateDeg = 0.0
    self.safety.set_angle_meas(2000, 2000)
    steer, decoded = step(self.controller, self.command, self.state)
    self.assertFalse(decoded['LKAS_Request'])
    self.assertTrue(self.safety.safety_tx_hook(self.packet(steer)))
    steer, decoded = step(self.controller, self.command, self.state)
    self.assertTrue(decoded['LKAS_Request'])
    self.assertTrue(self.safety.safety_tx_hook(self.packet(steer)))

  def test_buses_angle_bounds_permission_and_rate_limits(self):
    for bad in (self.angle(0, bus=1), self.angle(0, bus=2), self.angle(546)):
      self.arm()
      self.assertFalse(self.safety.safety_tx_hook(bad))
    self.arm()
    self.safety.set_desired_angle_last(0)
    self.assertTrue(self.safety.safety_tx_hook(self.angle(0.25)))
    self.assertFalse(self.safety.safety_tx_hook(self.angle(1.0)))
    for changes in ({'main': False}, {'cruise': False}, {'brake': True}):
      self.arm(**changes)
      self.assertFalse(self.safety.safety_tx_hook(self.angle(0)))
      self.assertTrue(self.safety.safety_tx_hook(self.angle(0, active=False)))
    for flag in (SubaruSafetyFlags.LONG, 0x100, 0x40):
      cfg = self.cp.safetyConfigs[0]
      self.safety.set_safety_hooks(cfg.safetyModel.raw, cfg.safetyParam | flag)
      self.safety.init_tests()
      self.safety.set_controls_allowed(True)
      self.assertFalse(self.safety.safety_tx_hook(self.angle(0)))

  def test_forwarding_and_exact_parameter_discriminator(self):
    self.arm()
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x124), -1)
    self.assertEqual(self.safety.safety_fwd_hook(0, 0x124), 2)
    self.assertEqual(self.safety.safety_fwd_hook(1, 0x124), -1)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x221), 0)
    self.assertFalse(self.safety.safety_tx_hook(self.packet(self.packer.make_can_msg('ES_LKAS', 0, {}))))
    self.assertFalse(self.safety.safety_tx_hook(self.packet(self.packer.make_can_msg('ES_Brake', 1, {}))))
    self.safety.set_desired_angle_last(54500)
    self.assertFalse(self.safety.safety_tx_hook(self.angle(546)))
    self.arm()
    self.safety.set_desired_angle_last(-54500)
    self.assertFalse(self.safety.safety_tx_hook(self.angle(-546)))
    for invalid in (0x20, 0x21, 0x30, 0x31, 0xA0, 0xB0, 0xB3, 0x1B1):
      self.safety.set_safety_hooks(structs.CarParams.SafetyModel.subaru, invalid)
      self.safety.init_tests()
      self.safety.set_controls_allowed(True)
      for bus in (0, 1, 2):
        self.assertFalse(self.safety.safety_tx_hook(self.angle(0, bus=bus)), hex(invalid))
    self.arm()
    self.safety.set_relay_malfunction(True)
    self.assertEqual(self.safety.safety_fwd_hook(0, 0x124), -1)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x221), -1)

  def test_required_can_loss_and_relay_revoke(self):
    self.arm()
    self.assertTrue(self.safety.safety_tx_hook(self.angle(0)))
    self.safety.set_timer(10_000_000)
    self.safety.safety_tick()
    self.assertFalse(self.safety.safety_config_valid())
    self.assertFalse(self.safety.safety_tx_hook(self.angle(0)))
    self.arm()
    self.safety.set_relay_malfunction(True)
    self.assertFalse(self.safety.safety_tx_hook(self.angle(0)))

  def test_received_stock_angle_detects_relay(self):
    for bus in (1, 2):
      self.arm()
      self.safety.safety_rx_hook(self.angle(0, active=False, bus=bus))
      self.assertFalse(self.safety.get_relay_malfunction())
    self.arm()
    self.safety.safety_rx_hook(self.angle(0, active=False))
    self.assertTrue(self.safety.get_relay_malfunction())
    self.assertFalse(self.safety.safety_tx_hook(self.angle(0)))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x221), -1)

  def test_inactive_measured_beyond_fixed_bound_is_safely_clamped(self):
    for measured in (-600.0, 600.0):
      with self.subTest(measured=measured):
        self.arm()
        _, self.controller, self.command, self.state = setup_controller()
        self.command.latActive = False
        self.state.out.steeringAngleDeg = measured
        self.safety.set_angle_meas(int(measured * 100), int(measured * 100))
        steer, decoded = step(self.controller, self.command, self.state)
        self.assertEqual(abs(decoded['LKAS_Output']), 545.0)
        self.assertTrue(self.safety.safety_tx_hook(self.packet(steer)))

  def test_driver_override_handoff_frames_match_native(self):
    self.arm()
    self.state.out.vEgoRaw = 30.3
    for torque, rate, measured, active in ((0, 0, 0, False), (0, 0, 0, True),
                                         (250, 35, 0, True), (250, 35, 0, False),
                                         (150, 0, 0, False), (149, 3, 0, False),
                                         (149, 0, 0, False), (149, 0, 0, True), (0, 0, 0, True)):
      self.state.out.steeringTorque = torque
      self.state.out.steeringRateDeg = rate
      self.state.out.steeringAngleDeg = measured
      self.safety.set_angle_meas(int(measured * 100), int(measured * 100))
      steer, decoded = step(self.controller, self.command, self.state)
      self.assertEqual(bool(decoded['LKAS_Request']), active, (torque, rate))
      self.assertTrue(self.safety.safety_tx_hook(self.packet(steer)))
