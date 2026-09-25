import unittest
import math

from opendbc.can import CANDefine, CANPacker, CANParser
from opendbc.car import Bus, structs
from opendbc.car.honda.carcontroller import CarController
from opendbc.car.honda.carstate import CarState
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, DBC, HondaFlags
from opendbc.safety.tests.common import MAX_WRONG_COUNTERS
from opendbc.safety.tests.libsafety import libsafety_py


CARS = (CAR.HONDA_CRV_SA, CAR.HONDA_CLARITY, CAR.HONDA_ACCORD_9G,
        CAR.ACURA_MDX_3G, CAR.ACURA_MDX_3G_MMR, CAR.ACURA_TLX_1G)


class TestHondaNidecSix(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety

  @staticmethod
  def packet(msg):
    return libsafety_py.make_CANPacket(msg[0], msg[2], msg[1])

  def mode(self, cp):
    cfg = cp.safetyConfigs[0]
    self.assertEqual(self.safety.set_safety_hooks(cfg.safetyModel.raw, cfg.safetyParam), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  def sources(self, car, *, cvt=False, hybrid=False, brake_pressed=False, door_open=False):
    fp = {0: {0x191 if cvt else 0x1A3: 8}, 1: {}, 2: {}}
    if hybrid:
      fp[0][0x184] = 8
    cp = CarInterface.get_params(car, fp, [], False, False, False)
    packer = CANPacker(DBC[car][Bus.pt])
    gearbox = "GEARBOX_CVT" if cvt else "GEARBOX_AUTO"
    gear_map = CANDefine(DBC[car][Bus.pt]).dv[gearbox]["GEAR_SHIFTER"]
    drive = next(raw for raw, gear in gear_map.items() if gear == "D")
    clarity = car == CAR.HONDA_CLARITY
    scm = {} if clarity else {"MAIN_ON": 1}
    if not cp.flags & HondaFlags.HAS_ALL_DOOR_STATES:
      scm["DRIVERS_DOOR_OPEN"] = int(door_open)
    pt = [
      packer.make_can_msg("SCM_BUTTONS", 0, scm),
      packer.make_can_msg("ENGINE_DATA", 0, {"XMISSION_SPEED": 50}),
      packer.make_can_msg("POWERTRAIN_DATA", 0, {"ACC_STATUS": 1, "BRAKE_PRESSED": int(brake_pressed)}),
      packer.make_can_msg("CAR_SPEED", 0, {"CAR_SPEED": 50}),
      packer.make_can_msg("WHEEL_SPEEDS", 0, {f"WHEEL_SPEED_{wheel}": 50 for wheel in ("FL", "FR", "RL", "RR")}),
      packer.make_can_msg("STEER_STATUS", 0, {}),
      packer.make_can_msg("SEATBELT_STATUS", 0, {"SEATBELT_DRIVER_LATCHED": 1}),
      packer.make_can_msg(gearbox, 0, {"GEAR_SHIFTER": drive}),
    ]
    if clarity:
      pt.append(packer.make_can_msg("SCM_FEEDBACK", 0, {"MAIN_ON": 1}))
    if cp.flags & HondaFlags.HAS_ALL_DOOR_STATES:
      pt.append(packer.make_can_msg("DOORS_STATUS", 0, {"DOOR_OPEN_FL": int(door_open)}))
    cam = [packer.make_can_msg(name, 2, {}) for name in ("BRAKE_COMMAND", "ACC_HUD", "LKAS_HUD")]
    return cp, packer, pt, cam

  def parsed_controller(self, car, cp, pt, cam, *, lat_active=True, long_active=True,
                        brake_pressed=False, door_open=False):
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    state.update(parsers)  # Register the signals consumed by CarState before feeding the CANParser.
    parsers[Bus.pt].update([(1_000_000_000, pt)])
    parsers[Bus.cam].update([(1_000_000_000, cam)])
    state.out = state.update(parsers).as_reader()
    self.assertGreater(state.out.vEgo, 10)
    self.assertTrue(state.out.cruiseState.enabled)
    self.assertTrue(state.out.cruiseState.available)
    self.assertEqual(state.out.gearShifter, structs.CarState.GearShifter.drive)
    self.assertEqual(state.out.brakePressed, brake_pressed)
    self.assertEqual(state.out.doorOpen, door_open)
    control = structs.CarControl()
    control.enabled = True
    control.latActive = lat_active
    control.longActive = long_active
    control.actuators.torque = 0.03
    controller = CarController(DBC[car], cp)
    _, commands = controller.update(control.as_reader(), state, 1_100_000_000)
    return commands

  def test_cvt_hybrid_and_parsed_driver_state(self):
    for car in (CAR.HONDA_CLARITY, CAR.HONDA_ACCORD_9G, CAR.ACURA_MDX_3G):
      with self.subTest(car=car):
        cp, _, pt, cam = self.sources(car, cvt=True, hybrid=True, brake_pressed=True, door_open=True)
        self.assertEqual(cp.transmissionType, structs.CarParams.TransmissionType.cvt)
        self.assertTrue(cp.flags & HondaFlags.HYBRID)
        commands = self.parsed_controller(car, cp, pt, cam, lat_active=False, long_active=False,
                                          brake_pressed=True, door_open=True)
        steer = next(msg for msg in commands if msg[0] in (0xE4, 0x194))
        parser = CANParser(DBC[car][Bus.pt], [("STEERING_CONTROL", math.nan)], 0)
        parser.update([(1_100_000_000, [steer])])
        self.assertEqual(parser.vl["STEERING_CONTROL"]["STEER_TORQUE"], 0)

  def arm(self, car, cp, pt, cam):
    self.mode(cp)
    required = [pt[0], pt[1], pt[2], cam[0]]
    if car == CAR.HONDA_CLARITY:
      required.append(next(frame for frame in pt if frame[0] == 0x326))
    for frame in required:
      self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)), hex(frame[0]))
    self.safety.safety_tick()
    self.assertTrue(self.safety.safety_config_valid())
    self.assertTrue(self.safety.get_controls_allowed())
    return required

  def test_packed_parser_controller_native_all_six(self):
    for car in CARS:
      with self.subTest(car=car):
        cp, packer, pt, cam = self.sources(car)
        commands = self.parsed_controller(car, cp, pt, cam)
        self.arm(car, cp, pt, cam)
        steer_addr = 0x194 if car == CAR.HONDA_CRV_SA else 0xE4
        self.assertEqual({msg[0] for msg in commands}, {steer_addr, 0x1FA, 0x30C, 0x33D})
        steering = next(msg for msg in commands if msg[0] == steer_addr)
        steering_parser = CANParser(DBC[car][Bus.pt], [("STEERING_CONTROL", math.nan)], 0)
        steering_parser.update([(1_100_000_000, [steering])])
        self.assertNotEqual(steering_parser.vl["STEERING_CONTROL"]["STEER_TORQUE"], 0)
        self.assertEqual(steering_parser.vl["STEERING_CONTROL"]["STEER_TORQUE_REQUEST"], 1)
        for frame in commands:
          self.assertTrue(self.safety.safety_tx_hook(self.packet(frame)), hex(frame[0]))
          self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1], 1))))
          self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1][:-1], frame[2]))))
        inactive = self.parsed_controller(car, cp, pt, cam, lat_active=False, long_active=False)
        steering_parser.update([(1_110_000_000, [next(msg for msg in inactive if msg[0] == steer_addr)])])
        self.assertEqual(steering_parser.vl["STEERING_CONTROL"]["STEER_TORQUE"], 0)
        self.assertEqual(steering_parser.vl["STEERING_CONTROL"]["STEER_TORQUE_REQUEST"], 0)
        for frame in inactive:
          self.assertTrue(self.safety.safety_tx_hook(self.packet(frame)), hex(frame[0]))
        self.assertFalse(self.safety.safety_tx_hook(self.packet(packer.make_can_msg("BRAKE_COMMAND", 0, {"AEB_REQ_1": 1}))))
        self.assertEqual(self.safety.safety_fwd_hook(2, steer_addr), -1)
        self.assertEqual(self.safety.safety_fwd_hook(2, 0x1FA), -1)
        self.assertEqual(self.safety.safety_fwd_hook(0, steer_addr), 2)
        self.assertEqual(self.safety.safety_fwd_hook(0, 0x1FA), 2)

  def test_required_receive_health_and_stock_aeb_forwarding(self):
    for car in CARS:
      with self.subTest(car=car):
        cp, packer, pt, cam = self.sources(car)
        required = self.arm(car, cp, pt, cam)
        for missing in required:
          self.mode(cp)
          for frame in required:
            if frame is not missing:
              self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))
          self.safety.safety_tick()
          self.assertFalse(self.safety.safety_config_valid(), hex(missing[0]))
          self.assertTrue(self.safety.safety_rx_hook(self.packet((missing[0], missing[1], 1))))
          self.safety.safety_tick()
          self.assertFalse(self.safety.safety_config_valid(), hex(missing[0]))
          for malformed in ((missing[0], missing[1][:-1], missing[2]),
                            (missing[0], missing[1][:-1] + bytes([missing[1][-1] ^ 1]), missing[2])):
            self.mode(cp)
            for frame in required:
              if frame is not missing:
                self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))
            self.safety.safety_rx_hook(self.packet(malformed))
            self.safety.safety_tick()
            self.assertFalse(self.safety.safety_config_valid(), hex(missing[0]))
        self.arm(car, cp, pt, cam)
        for _ in range(MAX_WRONG_COUNTERS + 2):
          self.safety.safety_rx_hook(self.packet(pt[0]))
        self.safety.safety_tick()
        self.assertFalse(self.safety.safety_config_valid())
        self.arm(car, cp, pt, cam)
        brake_pressed = packer.make_can_msg("POWERTRAIN_DATA", 0, {"ACC_STATUS": 1, "BRAKE_PRESSED": 1})
        self.assertTrue(self.safety.safety_rx_hook(self.packet(brake_pressed)))
        self.assertFalse(self.safety.get_controls_allowed())
        self.arm(car, cp, pt, cam)
        aeb = packer.make_can_msg("BRAKE_COMMAND", 2, {"AEB_REQ_1": 1, "COMPUTER_BRAKE": 20})
        self.assertTrue(self.safety.safety_rx_hook(self.packet(aeb)))
        self.assertTrue(self.safety.get_honda_fwd_brake())
        self.assertEqual(self.safety.safety_fwd_hook(2, 0x1FA), 0)
        brake = next(msg for msg in self.parsed_controller(car, cp, pt, cam) if msg[0] == 0x1FA)
        self.assertFalse(self.safety.safety_tx_hook(self.packet(brake)))
        self.assertTrue(self.safety.safety_rx_hook(self.packet(packer.make_can_msg("BRAKE_COMMAND", 2, {}))))
        self.assertFalse(self.safety.get_honda_fwd_brake())
