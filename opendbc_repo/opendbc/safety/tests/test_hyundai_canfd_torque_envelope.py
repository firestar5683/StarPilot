import unittest
from types import SimpleNamespace

from opendbc.can import CANPacker
from opendbc.car import structs
from opendbc.car.hyundai.hyundaicanfd import create_steering_messages
from opendbc.car.hyundai.values import CAR, HyundaiFlags, CarControllerParams
from opendbc.car.lateral import apply_driver_steer_torque_limits
from opendbc.safety.tests.libsafety import libsafety_py


class TestHyundaiCanfdTorqueEnvelope(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.release = self.safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    self.packer = CANPacker('hyundai_canfd_generated')

  def tearDown(self):
    self.safety.init_tests()
    self.safety.set_alternative_experience(0)
    self.safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)

  def mode(self, word):
    self.safety.set_alternative_experience(0)
    self.assertEqual(self.safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundaiCanfd, word), 0)
    self.safety.init_tests()
    self.safety.set_timer(0)
    self.word = word

  def tx(self, frame):
    return bool(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])))

  def frames(self, torque):
    flags = HyundaiFlags.CANFD | (HyundaiFlags.CANFD_LKA_STEER_MSG if self.word & 16 else 0)
    if self.word & 128:
      flags |= HyundaiFlags.CANFD_LKA_STEER_MSG_ALT
    cp = SimpleNamespace(carFingerprint=CAR.HYUNDAI_TUCSON_4TH_GEN, flags=int(flags),
                         openpilotLongitudinalControl=bool(self.word & 4) and not self.release)
    return create_steering_messages(self.packer, cp, SimpleNamespace(ECAN=1 if self.word & 16 else 0, ACAN=0), True, True, torque)

  def previous(self, torque, driver=0):
    self.safety.set_desired_torque_last(torque)
    self.safety.set_rt_torque_last(torque)
    for counter in range(6):
      frame = self.packer.make_can_msg('MDPS', 1 if self.word & 16 else 0,
                                      {'COUNTER': counter, 'MDPS_StrTqSnsrVal': driver, 'MDPS_OutTqVal': 0})
      self.assertTrue(self.safety.safety_rx_hook(libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])))
    self.safety.set_controls_allowed(True)

  def test_host_unwind_speed_transition_and_driver_override(self):
    for word in (0x11, 0x91, 9):
      for vehicle in (CAR.KIA_EV6, CAR.KIA_CARNIVAL_HEV_4TH_GEN):
        for sign in (-1, 1):
          for speed, expected in ((14.999, 401 if vehicle == CAR.KIA_EV6 else 406), (15., 406)):
            with self.subTest(word=hex(word), vehicle=vehicle, sign=sign, speed=speed):
              self.mode(word)
              self.previous(sign * 409, -sign * 500)
              cp = SimpleNamespace(flags=int(HyundaiFlags.CANFD), carFingerprint=vehicle)
              output = apply_driver_steer_torque_limits(0, sign * 409, -sign * 500, CarControllerParams(cp, speed))
              self.assertEqual(output, sign * expected)
              self.assertTrue(self.tx(self.frames(output)[0]))
              if speed < 15 and vehicle == CAR.KIA_EV6:
                self.safety.set_timer(10_000)
                next_output = apply_driver_steer_torque_limits(0, output, -sign * 500, CarControllerParams(cp, 15.))
                self.assertEqual(next_output, sign * 398)
                self.assertTrue(self.tx(self.frames(next_output)[0]))
              self.previous(sign * 409, -sign * 500)
              self.assertFalse(self.tx(self.frames(sign * 407)[0]))
              self.previous(sign)
              crossing = apply_driver_steer_torque_limits(-sign * 409, sign, 0, CarControllerParams(cp, speed))
              self.assertEqual(crossing, sign * (1 - (8 if speed < 15 and vehicle == CAR.KIA_EV6 else 3)))
              self.assertTrue(self.tx(self.frames(crossing)[0]))

  def test_real_clock_ramp_and_absolute_cap(self):
    for word in (0x11, 0x91, 9):
      for sign in (-1, 1):
        with self.subTest(word=hex(word), sign=sign):
          self.mode(word)
          self.previous(0)
          self.assertFalse(self.tx(self.frames(sign * 409)[0]))
          self.previous(0)
          for tick in range(42):
            self.safety.set_timer(tick * 10_000)
            self.assertTrue(self.tx(self.frames(sign * min(tick * 10, 409))[0]))
          self.previous(sign * 409)
          self.assertFalse(self.tx(self.frames(sign * 410)[0]))
          self.previous(0)
          self.assertFalse(self.tx(self.frames(sign * 11)[0]))
          for clock in (250_000, 250_001):
            self.mode(word)
            self.previous(sign * 375)
            self.safety.set_rt_torque_last(0)
            self.safety.set_timer(clock)
            self.assertTrue(self.tx(self.frames(sign * 375)[0]))
            self.assertEqual(self.tx(self.frames(sign * 376)[0]), clock > 250_000)

  def test_all_hda2_long_secondary_frames_require_single_limited_primary(self):
    for word in (0x14, 0x15, 0x16, 0x34, 0x35, 0x36, 0x94, 0x95, 0x96, 0xB4, 0xB5, 0xB6):
      for sign in (-1, 1):
        for fault in ('unpaired', 'different', 'expired', 'replacement', 'checksum', 'body'):
          with self.subTest(word=hex(word), sign=sign, fault=fault):
            self.mode(word)
            self.previous(sign * 409)
            frames = self.frames(sign * 409)
            if self.release:
              self.assertEqual(len(frames), 1)
              self.assertTrue(self.tx(frames[0]))
              lfa = self.packer.make_can_msg('LFA', 1, {'StrTqReqVal': sign * 409, 'ActToiSta': 1})
              self.assertFalse(self.tx(lfa))
              continue
            source, mirror = frames
            self.assertFalse(self.tx(mirror))
            self.previous(sign * 409)
            self.assertTrue(self.tx(source))
            if fault == 'unpaired':
              self.assertTrue(self.tx(mirror))
            elif fault == 'different':
              self.assertFalse(self.tx(self.frames(sign * 384)[1]))
            elif fault == 'expired':
              self.safety.set_timer(10_001)
              self.assertFalse(self.tx(mirror))
            elif fault == 'replacement':
              self.assertFalse(self.tx(self.frames(sign * 410)[0]))
            elif fault == 'body':
              name = 'LKAS_ALT' if word & 128 else 'LKAS'
              forged = self.packer.make_can_msg(name, 0, {'LKA_OptUsmSta': 2, 'LKA_SysIndReq': 2,
                'StrTqReqVal': sign * 409, 'ActToiSta': 1, 'Damping_Gain': 99})
              self.assertFalse(self.tx(forged))
            else:
              data = bytearray(mirror[1])
              data[0] ^= 1
              self.assertFalse(self.tx((mirror[0], bytes(data), mirror[2])))
            self.assertFalse(self.tx(mirror))
