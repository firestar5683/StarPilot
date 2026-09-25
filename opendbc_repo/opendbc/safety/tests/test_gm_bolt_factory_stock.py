import unittest

from opendbc.can import CANParser, CANPacker
from opendbc.car import Bus, structs
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.values import CAR, DBC
from opendbc.safety.tests import test_gm_camera_stock_four as stock_fixtures


class TestGmBoltFactoryStock(unittest.TestCase):
  setUp = stock_fixtures.TestGmCameraStockFour.setUp
  packet = staticmethod(stock_fixtures.TestGmCameraStockFour.packet)

  @staticmethod
  def params(car, **kwargs):
    # Exercise the retained OEM longitudinal owner explicitly.
    kwargs['alpha'] = False
    return stock_fixtures.TestGmCameraStockFour.params(car, **kwargs)

  frames = staticmethod(stock_fixtures.TestGmCameraStockFour.frames)
  mode = stock_fixtures.TestGmCameraStockFour.mode
  joined = stock_fixtures.TestGmCameraStockFour.joined

  def test_joined_stock_steering_cancel_pscm_and_long_denial(self):
    for car in (CAR.CHEVROLET_BOLT_ACC_2022_2023,):
      with self.subTest(car=car):
        cp, packer, parsers, state, pt, cam, commands = self.joined(car)
        self.assertEqual({msg[0] for msg in commands}, {0x180, 0x1E1, 0x184})
        steer = next(msg for msg in commands if msg[0] == 0x180)
        cancel = next(msg for msg in commands if msg[0] == 0x1E1)
        pscm = next(msg for msg in commands if msg[0] == 0x184)
        self.assertNotEqual(((steer[1][0] & 7) << 8) | steer[1][1], 0)
        self.assertEqual(cancel[2], 2)
        self.assertEqual(pscm[2], 2)
        cancel_parser = CANParser(DBC[car][Bus.pt], [('ASCMSteeringButton', 10)], 2)
        cancel_parser.update([(1_050_000_000, [cancel])])
        self.assertEqual(cancel_parser.vl['ASCMSteeringButton']['ACCButtons'], 6)
        self.assertEqual(cancel_parser.vl['ASCMSteeringButton']['RollingCounter'], state.buttons_counter)
        self.assertEqual(cancel_parser.vl['ASCMSteeringButton']['ACCAlwaysOne'], 1)
        self.assertEqual(cancel_parser.vl['ASCMSteeringButton']['DistanceButton'], 0)
        self.assertTrue(self.safety.get_controls_allowed())
        for msg in commands:
          self.assertTrue(self.safety.safety_tx_hook(self.packet(msg)), hex(msg[0]))
        self.assertFalse(self.safety.safety_tx_hook(self.packet((cancel[0], cancel[1], 0))))
        self.assertFalse(self.safety.safety_tx_hook(self.packet((steer[0], steer[1][:-1], 0))))
        for addr, bus, length in ((0x315, 0, 5), (0x2CB, 0, 8), (0x370, 0, 6), (0x200, 0, 6), (0x409, 0, 7)):
          self.assertFalse(self.safety.safety_tx_hook(self.packet((addr, bytes(length), bus))), hex(addr))
        self.assertAlmostEqual(state.out.cruiseState.speed,
                               64 / 3.6 if car == CAR.CHEVROLET_SUBURBAN_CAMERA else 88 / 3.6, places=5)
        self.assertFalse(state.out.cruiseState.nonAdaptive)
        self.assertFalse(state.out.regenBraking)

  def test_host_neutral_on_inactive_brake_and_gas(self):
    for car in (CAR.CHEVROLET_BOLT_ACC_2022_2023,):
      for scenario in ({'lat': False}, {'brake': True}, {'gas': True}, {'main': False}, {'cruise': False}):
        with self.subTest(car=car, scenario=scenario):
          _, _, _, state, _, _, commands = self.joined(car, **scenario)
          steer = next(msg for msg in commands if msg[0] == 0x180)
          if scenario in ({'brake': True}, {'cruise': False}):
            self.assertFalse(self.safety.get_controls_allowed())
          self.assertEqual(((steer[1][0] & 7) << 8) | steer[1][1], 0)
          self.assertTrue(self.safety.safety_tx_hook(self.packet(steer)))

  def test_missing_camera_or_pt_source_and_stale_status(self):
    for car in (CAR.CHEVROLET_BOLT_ACC_2022_2023,):
      with self.subTest(car=car):
        cp = self.params(car)
        packer = CANPacker(DBC[car][Bus.pt])
        pt, cam = self.frames(packer, car)
        for missing_bus, missing_addr in ((Bus.cam, 0x180), (Bus.cam, 0x320), (Bus.cam, 0x370),
                                          (Bus.pt, 0xC9), (Bus.pt, 0x1C4), (Bus.pt, 0xBE)):
          with self.subTest(missing_bus=missing_bus, missing_addr=hex(missing_addr)):
            state = CarState(cp)
            parsers = state.get_can_parsers(cp)
            parsers[Bus.pt].update([(1_000_000_000, [m for m in pt if m[0] != missing_addr or missing_bus != Bus.pt])])
            parsers[Bus.cam].update([(1_000_000_000, [m for m in cam if m[0] != missing_addr or missing_bus != Bus.cam])])
            self.assertFalse(parsers[missing_bus].can_valid)
            state.out = state.update(parsers).as_reader()
            self.assertFalse(state.camera_stock_sources_valid)
            controller = CarController(DBC[car], cp)
            controller.frame = 20
            control = structs.CarControl()
            control.enabled = True
            control.latActive = True
            control.actuators.torque = 0.03
            _, commands = controller.update(control.as_reader(), state, 1_050_000_000)
            steer = next(m for m in commands if m[0] == 0x180)
            self.assertEqual(((steer[1][0] & 7) << 8) | steer[1][1], 0)

        _, _, _, state, _, _, commands = self.joined(car, now=1_400_000_001)
        steer = next(m for m in commands if m[0] == 0x180)
        self.assertEqual(((steer[1][0] & 7) << 8) | steer[1][1], 0)
        self.safety.set_timer(2_100_000)
        self.safety.safety_tick()
        self.assertFalse(self.safety.safety_config_valid())
