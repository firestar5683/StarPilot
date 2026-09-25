import math
import unittest

from opendbc.can import CANDefine, CANPacker, CANParser
from opendbc.car import Bus, structs
from opendbc.car.honda.carcontroller import CarController
from opendbc.car.honda.carstate import CarState
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, DBC, HondaFlags
from opendbc.car.common.conversions import Conversions as CV
from opendbc.safety.tests.libsafety import libsafety_py


CARS = (CAR.HONDA_FIT_4G, CAR.ACURA_INTEGRA, CAR.ACURA_ADX)


class TestHondaBoschRadarlessThree(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.debug = self.safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) == 0

  @staticmethod
  def packet(msg):
    return libsafety_py.make_CANPacket(msg[0], msg[2], msg[1])

  def sources(self, car, *, alpha=False, release=False, alt_brake=False, brake=False):
    fp = {0: {0x1BE: 3} if alt_brake else {}, 1: {}, 2: {}}
    cp = CarInterface.get_params(car, fp, [], alpha, release, False)
    packer = CANPacker(DBC[car][Bus.pt])
    drive = next(raw for raw, gear in CANDefine(DBC[car][Bus.pt]).dv['GEARBOX_AUTO']['GEAR_SHIFTER'].items() if gear == 'D')
    pt = [
      packer.make_can_msg('SCM_BUTTONS', 0, {'CRUISE_BUTTONS': 0, 'COUNTER': 0}),
      packer.make_can_msg('SCM_FEEDBACK', 0, {'MAIN_ON': 1}),
      packer.make_can_msg('ENGINE_DATA', 0, {'XMISSION_SPEED': 50}),
      packer.make_can_msg('POWERTRAIN_DATA', 0, {'ACC_STATUS': 1, 'BRAKE_PRESSED': int(brake)}),
      packer.make_can_msg('CAR_SPEED', 0, {'CAR_SPEED': 50}),
      packer.make_can_msg('WHEEL_SPEEDS', 0, {f'WHEEL_SPEED_{w}': 50 for w in ('FL', 'FR', 'RL', 'RR')}),
      packer.make_can_msg('SEATBELT_STATUS', 0, {'SEATBELT_DRIVER_LATCHED': 1}),
      packer.make_can_msg('STEER_STATUS', 0, {}),
      packer.make_can_msg('GEARBOX_AUTO', 0, {'GEAR_SHIFTER': drive}),
    ]
    if alt_brake:
      pt.append(packer.make_can_msg('BRAKE_MODULE', 0, {'BRAKE_PRESSED': int(brake)}))
    cam = [packer.make_can_msg(name, 2, {}) for name in ('ACC_HUD', 'LKAS_HUD')]
    return cp, packer, pt, cam

  def controller(self, car, cp, pt, cam, *, active=True, brake=False):
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    state.update(parsers)
    parsers[Bus.pt].update([(1_000_000_000, pt)])
    parsers[Bus.cam].update([(1_000_000_000, cam)])
    state.out = state.update(parsers).as_reader()
    self.assertGreater(state.out.vEgo, 10)
    self.assertTrue(state.out.cruiseState.available)
    self.assertTrue(state.out.cruiseState.enabled)
    self.assertEqual(state.out.gearShifter, structs.CarState.GearShifter.drive)
    self.assertEqual(state.out.brakePressed, brake)
    cc = structs.CarControl()
    cc.enabled = True
    cc.latActive = active
    cc.longActive = active and cp.openpilotLongitudinalControl and not brake
    cc.actuators.torque = 0.03 if active else 0
    cc.actuators.accel = 0.3 if active else 0
    cc.cruiseControl.cancel = not cp.openpilotLongitudinalControl
    _, commands = CarController(DBC[car], cp).update(cc.as_reader(), state, 1_100_000_000)
    steer = next(msg for msg in commands if msg[0] == 0xE4)
    parser = CANParser(DBC[car][Bus.pt], [('STEERING_CONTROL', math.nan)], 0)
    parser.update([(1_100_000_000, [steer])])
    self.assertEqual(parser.vl['STEERING_CONTROL']['STEER_TORQUE'] != 0, active)
    return commands

  def mode(self, cp):
    cfg = cp.safetyConfigs[0]
    self.assertEqual(self.safety.set_safety_hooks(cfg.safetyModel.raw, cfg.safetyParam), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  def arm(self, cp, packer, pt, *, alpha=False, alt_brake=False):
    self.mode(cp)
    required = pt[:4] + ([pt[-1]] if alt_brake else [])
    if alpha:
      required = [pt[1], packer.make_can_msg('SCM_BUTTONS', 0, {'CRUISE_BUTTONS': 3, 'COUNTER': 0}),
                  packer.make_can_msg('SCM_BUTTONS', 0, {'CRUISE_BUTTONS': 0, 'COUNTER': 1}), pt[2], pt[3]] + \
                 ([pt[-1]] if alt_brake else [])
    for frame in required:
      self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)), hex(frame[0]))
    self.safety.safety_tick()
    self.assertTrue(self.safety.safety_config_valid())
    self.assertTrue(self.safety.get_controls_allowed())
    return required

  def test_real_stock_and_debug_long_frames(self):
    for car in CARS:
      for alt_brake in ((False, True) if car == CAR.ACURA_ADX else (False,)):
        for alpha in (False, True):
          with self.subTest(car=car, alt_brake=alt_brake, alpha=alpha):
            cp, packer, pt, cam = self.sources(car, alpha=alpha, alt_brake=alt_brake)
            self.assertEqual(cp.openpilotLongitudinalControl, alpha)
            self.assertTrue(cp.flags & HondaFlags.BOSCH_RADARLESS)
            commands = self.controller(car, cp, pt, cam)
            self.arm(cp, packer, pt, alpha=alpha and self.debug, alt_brake=alt_brake)
            self.assertEqual({m[0] for m in commands}, {0xE4, 0x1C8, 0x30C, 0x33D} if alpha else {0xE4, 0x296, 0x33D})
            for frame in commands:
              self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)),
                               self.debug or not alpha or frame[0] not in (0x1C8, 0x30C), hex(frame[0]))
              self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1], 1))))
              self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1][:-1], frame[2]))))
            inactive = self.controller(car, cp, pt, cam, active=False)
            for frame in inactive:
              self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)),
                               self.debug or not alpha or frame[0] not in (0x1C8, 0x30C), hex(frame[0]))
            if alpha:
              self.assertEqual(self.safety.safety_tx_hook(self.packet(packer.make_can_msg('SCM_BUTTONS', 2, {'CRUISE_BUTTONS': 2}))),
                               not self.debug)
            else:
              self.assertFalse(self.safety.safety_tx_hook(self.packet(packer.make_can_msg('ACC_CONTROL', 0, {}))))

  def test_brake_health_and_release(self):
    for car in CARS:
      for alt_brake in ((False, True) if car == CAR.ACURA_ADX else (False,)):
        for alpha in (False, True):
          with self.subTest(car=car, alt_brake=alt_brake, alpha=alpha):
            cp, packer, pt, cam = self.sources(car, alpha=alpha, alt_brake=alt_brake)
            required = self.arm(cp, packer, pt, alpha=alpha and self.debug, alt_brake=alt_brake)
            for missing in (required[0], required[-2], required[-1]) if alpha and self.debug else required:
              self.mode(cp)
              for frame in required:
                if frame is not missing:
                  self.safety.safety_rx_hook(self.packet(frame))
              self.safety.safety_tick()
              self.assertFalse(self.safety.safety_config_valid(), hex(missing[0]))
            # Both variants require a healthy button source; alpha uses two button edges to arm.
            self.mode(cp)
            for frame in required:
              if frame[0] != 0x296:
                self.safety.safety_rx_hook(self.packet(frame))
            self.safety.safety_tick()
            self.assertFalse(self.safety.safety_config_valid())
            for replacement in ((required[-1][0], required[-1][1], 1),
                                (required[-1][0], required[-1][1][:-1], required[-1][2]),
                                (required[-1][0], required[-1][1][:-1] + bytes([required[-1][1][-1] ^ 1]), required[-1][2])):
              self.mode(cp)
              for frame in required[:-1]:
                self.safety.safety_rx_hook(self.packet(frame))
              self.safety.safety_rx_hook(self.packet(replacement))
              self.safety.safety_tick()
              self.assertFalse(self.safety.safety_config_valid())
            self.arm(cp, packer, pt, alpha=alpha and self.debug, alt_brake=alt_brake)
            positive = self.controller(car, cp, pt, cam)
            brake_name = 'BRAKE_MODULE' if alt_brake else 'POWERTRAIN_DATA'
            brake_frame = packer.make_can_msg(brake_name, 0, {'BRAKE_PRESSED': 1, 'ACC_STATUS': 1} if not alt_brake else {'BRAKE_PRESSED': 1})
            self.assertTrue(self.safety.safety_rx_hook(self.packet(brake_frame)))
            self.assertFalse(self.safety.get_controls_allowed())
            self.assertFalse(self.safety.safety_tx_hook(self.packet(next(frame for frame in positive if frame[0] == 0xE4))))
            if alpha:
              self.assertFalse(self.safety.safety_tx_hook(self.packet(next(frame for frame in positive if frame[0] == 0x1C8))))
            braked = list(pt)
            braked[-1 if alt_brake else 3] = brake_frame
            neutral = self.controller(car, cp, braked, cam, active=False, brake=True)
            if alpha:
              accel_parser = CANParser(DBC[car][Bus.pt], [('ACC_CONTROL', math.nan)], 0)
              accel_parser.update([(1_110_000_000, [next(frame for frame in neutral if frame[0] == 0x1C8)])])
              self.assertEqual(accel_parser.vl['ACC_CONTROL']['ACCEL_COMMAND'], 0)
            for frame in neutral:
              self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)),
                               self.debug or not alpha or frame[0] not in (0x1C8, 0x30C), hex(frame[0]))
            release, _, _, _ = self.sources(car, alpha=True, release=True, alt_brake=alt_brake)
            self.assertFalse(release.openpilotLongitudinalControl)
            self.assertFalse(release.alphaLongitudinalAvailable)
            self.assertEqual(release.safetyConfigs[0].safetyParam & 2, 0)
            self.arm(cp, packer, pt, alpha=alpha and self.debug, alt_brake=alt_brake)
            self.safety.set_timer(3_000_000)
            self.safety.safety_tick()
            self.assertFalse(self.safety.safety_config_valid())

  def test_fit_threshold_and_integra_speed_source(self):
    fit_stock, _, _, _ = self.sources(CAR.HONDA_FIT_4G)
    fit_alpha, _, _, _ = self.sources(CAR.HONDA_FIT_4G, alpha=True)
    self.assertAlmostEqual(fit_stock.minSteerSpeed, 23 * CV.KPH_TO_MS, places=6)
    self.assertAlmostEqual(fit_stock.minEnableSpeed, 30 * CV.KPH_TO_MS, places=6)
    self.assertFalse(fit_stock.autoResumeSng)
    self.assertEqual(fit_alpha.minEnableSpeed, -1)
    self.assertTrue(fit_alpha.autoResumeSng)
    for car in CARS:
      cp, _, _, _ = self.sources(car)
      self.assertEqual(cp.transmissionType, structs.CarParams.TransmissionType.automatic)
    cp, packer, pt, cam = self.sources(CAR.ACURA_INTEGRA)
    pt[2] = packer.make_can_msg('ENGINE_DATA', 0, {'XMISSION_SPEED': 0})
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    state.update(parsers)
    parsers[Bus.pt].update([(1_000_000_000, pt)])
    parsers[Bus.cam].update([(1_000_000_000, cam)])
    out = state.update(parsers)
    self.assertFalse(out.standstill)
    self.assertGreater(out.vEgoRaw, 0)

  def test_raw_long_release_denied(self):
    # This case is run unchanged against both DEBUG and RELEASE native libraries.
    for car in CARS:
      cp, packer, pt, cam = self.sources(car, alpha=True)
      frames = self.controller(car, cp, pt, cam)
      self.arm(cp, packer, pt, alpha=self.debug)
      accepted = all(self.safety.safety_tx_hook(self.packet(frame)) for frame in frames)
      self.assertEqual(accepted, self.debug)
