import unittest
from unittest.mock import patch

from opendbc.can import CANParser
from opendbc.car import Bus, structs
from opendbc.car.hyundai.hyundaicanfd import hkg_can_fd_checksum
from opendbc.car.hyundai.values import CAR, DBC
from opendbc.car.vehicle_model import calc_slip_factor
from opendbc.safety.tests.libsafety import libsafety_py


class TestKiaEv62025Angle(unittest.TestCase):
  def setUp(self):
    from opendbc.safety.tests.test_hyundai_mrr35_angle_four import TestHyundaiMRR35AngleFour
    self.helper = TestHyundaiMRR35AngleFour()

  def test_packed_sources_controller_and_correct_native_geometry(self):
    for topology in ('lfa', 'lfa_alt'):
      for speed in (2.0, 10.0, 25.0, 35.0):
        cp, _, safety, _, controller, frames, _ = self.helper.joined(CAR.KIA_EV6_2025, topology, speed=speed * 3.6)
        self.assertAlmostEqual(calc_slip_factor(controller.angle_vm), -0.0008898049378, places=11)
        self.assertAlmostEqual(controller.angle_vm.sR, 14.26, places=5)
        self.assertAlmostEqual(controller.angle_vm.l, 2.9, places=6)
        self.assertEqual(cp.safetyConfigs[-1].safetyParam, 0x7809 if topology == 'lfa' else 0x7829)
        self.assertEqual({frame[0] for frame in frames}, {0x12A})
        for frame in frames:
          self.assertTrue(safety.safety_tx_hook(self.helper.packet(frame)))
          self.assertEqual(int.from_bytes(frame[1][:2], 'little'), hkg_can_fd_checksum(frame[0], None, bytearray(frame[1])))
        self.assertEqual(safety.safety_fwd_hook(0, 0x1A0), 2)
        self.assertEqual(safety.safety_fwd_hook(2, 0x1A0), 0)
        self.assertEqual(safety.safety_fwd_hook(2, 0x12A), -1)
        self.assertEqual(safety.safety_fwd_hook(0, 0x12A), 2)

  def test_neutral_fault_timeout_and_relay(self):
    for topology in ('lfa', 'lfa_alt'):
      cp, state, safety, control, controller, _, _ = self.helper.joined(CAR.KIA_EV6_2025, topology)
      control.enabled = control.latActive = False
      _, frames = controller.update(control.as_reader(), state, 1_010_000_000)
      parser = CANParser(DBC[CAR.KIA_EV6_2025][Bus.pt], [('LFA', 0)], 0)
      steering = next(frame for frame in frames if frame[0] == 0x12A)
      parser.update((1_010_000_000, [steering]))
      self.assertEqual((steering[1][9] >> 4) & 3, 1)
      self.assertTrue(safety.safety_tx_hook(self.helper.packet(steering)))
      # A cleared controls permission cannot transmit an active angle request.
      cp, _, safety, _, _, active_frames, _ = self.helper.joined(CAR.KIA_EV6_2025, topology)
      safety.set_controls_allowed(False)
      self.assertFalse(safety.safety_tx_hook(self.helper.packet(active_frames[0])))
      cp, _, safety, _, _, active_frames, _ = self.helper.joined(CAR.KIA_EV6_2025, topology)
      safety.set_timer(2_100_000)
      safety.safety_tick_current_safety_config()
      self.assertFalse(safety.safety_config_valid())
      self.assertFalse(safety.safety_tx_hook(self.helper.packet(active_frames[0])))
      safety.set_relay_malfunction(True)
      self.assertFalse(safety.safety_tx_hook(self.helper.packet(steering)))

  def test_driver_pedals_and_temporary_eps_fault_send_neutral(self):
    for topology in ('lfa', 'lfa_alt'):
      for field in ('gasPressed', 'brakePressed', 'steerFaultTemporary'):
        _, state, safety, control, controller, _, _ = self.helper.joined(CAR.KIA_EV6_2025, topology)
        setattr(state.out, field, True)
        _, sends = controller.update(control.as_reader(), state, 1_010_000_000)
        self.assertEqual({frame[0] for frame in sends}, {0x12A})
        for frame in sends:
          self.assertEqual((frame[1][9] >> 4) & 3, 1)
          self.assertTrue(safety.safety_tx_hook(self.helper.packet(frame)))

  def test_ev6_rate_limits_and_required_source_health(self):
    from opendbc.safety.tests import test_hyundai_mrr35_angle_four as suite
    with patch.object(suite, 'ANGLE_CARS', (CAR.KIA_EV6_2025,)), patch.object(suite, 'TOPOLOGIES', ('lfa', 'lfa_alt')):
      self.helper.test_host_native_speed_envelopes_and_rate()
      self.helper.test_native_required_source_bus_crc_counter_and_staleness()

  def test_profile_bits_cannot_enable_other_topologies_or_authorities(self):
    safety = libsafety_py.libsafety
    for topology in ('lfa', 'lfa_alt'):
      cp, _, _, _, _, frames, _ = self.helper.joined(CAR.KIA_EV6_2025, topology)
      raw = cp.safetyConfigs[-1].safetyParam
      for forbidden in (2, 4, 16, 64, 128, 256, 512, 1024, 32768):
        self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd, raw | forbidden), 0)
        safety.init_tests()
        self.assertFalse(safety.safety_tx_hook(self.helper.packet(frames[0])), hex(raw | forbidden))


if __name__ == '__main__':
  unittest.main()
