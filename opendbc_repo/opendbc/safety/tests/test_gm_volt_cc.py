"""Exact development-only manual Volt CC native admission and arbitration."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm import gmcan
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
from opendbc.car.gm.values import CAR, DBC
from opendbc.safety.tests.libsafety import libsafety_py


class TestGmVoltCc(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.release = self.safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    fp = gen_empty_fingerprint()
    fp[0].update({0xbe: 6, 0x3d1: 8, 0xc9: 8, 0x1e1: 7, 0x1f5: 8, 0x34a: 5, 0x1c4: 8, 0xbd: 7})
    self.cp = CarInterface.get_params(CAR.CHEVROLET_VOLT_CC, fp, [], False, False, False)
    self.packer = CANPacker(DBC[self.cp.carFingerprint][Bus.pt])

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def reset(self):
    self.assertEqual(self.safety.set_safety_hooks(structs.CarParams.SafetyModel.gm, 20), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  def frames(self, counter=0, speed=20., gas=False, brake=False):
    frames = pt_frames(self.packer, counter=counter, gas=gas, brake=brake)
    replacements = [self.packer.make_can_msg('EBCMWheelSpdRear', 0,
                    {'RLWheelSpd': speed * 3.6, 'RRWheelSpd': speed * 3.6, 'RLWheelDir': 1, 'RRWheelDir': 1}),
                    gmcan.create_buttons(self.packer, 0, counter, 1),
                    self.packer.make_can_msg('EBCMRegenPaddle', 0, {})]
    addresses = {frame[0] for frame in replacements}
    return [frame for frame in frames if frame[0] not in addresses] + replacements

  def feed(self, **kwargs):
    for frame in self.frames(**kwargs):
      self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))
    self.safety.safety_tick_current_safety_config()

  def tx(self, counter=1, button=2):
    return self.safety.safety_tx_hook(self.packet(gmcan.create_buttons(self.packer, 0, counter, button)))

  def test_release_denial_and_literal_counter_credit(self):
    self.reset()
    self.feed()
    self.safety.set_controls_allowed(True)
    self.assertEqual(self.tx(), not self.release)
    self.assertFalse(self.tx())
    if self.release:
      return
    for tick, counter in ((1_100_000, 1), (1_200_000, 2), (1_300_000, 3)):
      self.safety.set_timer(tick)
      self.feed(counter=counter)
    self.assertFalse(self.tx(counter=1))
    good = gmcan.create_buttons(self.packer, 0, 0, 2)
    for index in range(7):
      bad = bytearray(good[1])
      bad[index] ^= 1
      self.assertFalse(self.safety.safety_tx_hook(self.packet((good[0], bytes(bad), 0))))
    self.assertFalse(self.safety.safety_tx_hook(self.packet((good[0], good[1], 2))))
    self.assertTrue(self.tx(counter=0))

  def test_duplicate_counter_does_not_renew_consumed_credit(self):
    self.reset()
    self.feed(counter=3)
    self.assertEqual(self.safety.get_controls_allowed(), not self.release)
    self.assertEqual(self.tx(counter=0), not self.release)
    for elapsed in range(10_000, 290_000, 10_000):
      self.safety.set_timer(1_000_000 + elapsed)
      self.feed(counter=3)
      self.assertFalse(self.tx(counter=0))
    self.safety.set_timer(1_290_000)
    self.feed(counter=0)
    self.assertEqual(self.tx(counter=1), not self.release)
    self.safety.set_timer(1_300_000)
    self.feed(counter=2)
    self.assertFalse(self.tx(counter=3, button=6))
    self.safety.set_timer(1_410_000)
    self.feed(counter=3)
    self.assertFalse(self.tx(counter=0, button=6))
    self.safety.set_timer(1_420_000)
    self.feed(counter=0)
    self.assertEqual(self.tx(counter=1, button=6), not self.release)

  def test_cancel_is_independently_paced_after_direction_and_override(self):
    for button in (2, 3):
      for elapsed in range(0, 40_001, 1_000):
        for override in ('none', 'gas', 'brake'):
          self.reset()
          self.feed()
          self.safety.set_controls_allowed(True)
          self.assertEqual(self.tx(button=button), not self.release)
          self.safety.set_timer(1_000_000 + elapsed)
          self.feed(counter=1, gas=override == 'gas', brake=override == 'brake')
          self.safety.set_controls_allowed(False)
          self.assertEqual(self.tx(counter=2, button=6), not self.release)
          self.assertFalse(self.tx(counter=2, button=6))

  def test_actual_controller_direction_to_disable_native_acceptance(self):
    for accel in (-2., 2.):
      for offset_frames in range(1, 5):
        for override in ('none', 'gas', 'brake'):
          self.reset()
          ci = CarInterface(self.cp)
          initial = self.frames()
          for frame in initial:
            self.safety.safety_rx_hook(self.packet(frame))
          self.safety.safety_tick_current_safety_config()
          self.safety.set_controls_allowed(True)
          ci.update([(998_000_000, initial)])
          ci.CC.frame = 100
          command = structs.CarControl.new_message(enabled=True, longActive=True)
          command.actuators.accel = accel
          command.hudControl.leadVisible = True
          _, frames = ci.apply(command.as_reader(), 1_000_000_000)
          buttons = [frame for frame in frames if frame[0] == 0x1e1]
          self.assertEqual(len(buttons), 1)
          self.assertEqual(self.safety.safety_tx_hook(self.packet(buttons[0])), not self.release)
          elapsed = offset_frames * 10_000
          self.safety.set_timer(1_000_000 + elapsed)
          fresh = self.frames(counter=1, gas=override == 'gas', brake=override == 'brake')
          for frame in fresh:
            self.safety.safety_rx_hook(self.packet(frame))
          ci.update([(1_000_000_000 + elapsed * 1000 - 1_000_000, fresh)])
          ci.CC.frame += offset_frames - 1
          command.enabled = False
          command.longActive = False
          self.safety.set_controls_allowed(False)
          _, frames = ci.apply(command.as_reader(), 1_000_000_000 + elapsed * 1000)
          buttons = [frame for frame in frames if frame[0] == 0x1e1]
          self.assertEqual(len(buttons), 1)
          self.assertEqual((buttons[0][1][5] >> 4) & 7, 6)
          self.assertEqual(self.safety.safety_tx_hook(self.packet(buttons[0])), not self.release)

  def test_low_speed_and_gas_are_not_lateral_propulsion_gates(self):
    for speed, gas in ((4., False), (20., True)):
      self.reset()
      self.feed(speed=speed)
      self.assertEqual(self.safety.get_controls_allowed(), not self.release)
      if gas:
        self.safety.set_timer(1_010_000)
        self.feed(counter=1, speed=speed, gas=True)
        # Authority was acquired by stock main/active RX, then retained on the gas edge.
        self.assertEqual(self.safety.get_controls_allowed(), not self.release)
      steer = gmcan.create_steering_control(self.packer, 0, 1, 0, True)
      self.assertEqual(self.safety.safety_tx_hook(self.packet(steer)), not self.release)
      self.assertFalse(self.tx(counter=2 if gas else 1))

  def test_individual_source_staleness_and_forbidden_authority(self):
    required = {0x3d1, 0x1e1, 0xc9, 0xbe, 0x1f5, 0x1c4, 0xbd, 0x34a}
    for missing in required:
      self.reset()
      self.feed()
      self.safety.set_timer(1_310_000)
      for frame in self.frames(counter=1):
        if frame[0] != missing:
          self.safety.safety_rx_hook(self.packet(frame))
      self.safety.set_controls_allowed(True)
      self.assertFalse(self.tx(counter=2))
      self.assertFalse(self.tx(counter=2, button=6))
    self.reset()
    self.feed()
    self.safety.set_controls_allowed(True)
    for addr, size in ((0x200, 6), (0x2cb, 8), (0x315, 5), (0x3d1, 8)):
      self.assertFalse(self.safety.safety_tx_hook(self.packet((addr, bytes(size), 0))))


if __name__ == '__main__':
  unittest.main()
