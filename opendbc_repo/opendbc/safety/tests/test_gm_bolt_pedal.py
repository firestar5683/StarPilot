import unittest
from types import SimpleNamespace

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.gmcan import create_bolt_regen_gear, create_bolt_regen_paddle, create_pedal_command, create_steering_control, pedal_crc
from opendbc.car.gm.tests.test_bolt_pedal import params
from opendbc.car.gm.values import CAR, DBC, GMSafetyFlags, PEDAL_BOLT_CAR
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests.libsafety.libsafety_py import ffi, new_CANPacket


class TestGmBoltPedalSafety(unittest.TestCase):
  def setUp(self):
    self.packer = CANPacker(DBC[CAR.CHEVROLET_BOLT_CC_2017]["pt"])
    self.safety = libsafety_py.libsafety
    self.init_mode(GMSafetyFlags.NO_ACC | GMSafetyFlags.BOLT_2017)

  def init_mode(self, variant, pedal=True):
    param = int(GMSafetyFlags.HW_CAM | GMSafetyFlags.EV | variant)
    if pedal:
      param |= int(GMSafetyFlags.PEDAL_LONG | GMSafetyFlags.PADDLE_SCHED)
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, param), 0)
    self.safety.init_tests()
    self.safety.reset_recorded_can()

  @staticmethod
  def packet(msg):
    return libsafety_py.make_CANPacket(msg[0], msg[2], msg[1])

  def sensor(self, counter, state=0, gas=0., pair_error=False, bad_crc=False):
    msg = self.packer.make_can_msg("GAS_SENSOR", 0, {
      "INTERCEPTOR_GAS": gas, "INTERCEPTOR_GAS2": gas,
      "STATE": state, "COUNTER_PEDAL": counter,
    })
    data = bytearray(msg[1])
    if pair_error:
      data[2] += 8
    data[5] = pedal_crc(data) ^ int(bad_crc)
    return self.packet((msg[0], bytes(data), 0))

  def stock(self, name, values):
    return self.packet(self.packer.make_can_msg(name, 0, values))

  def low_gear(self):
    return self.stock("ECMPRDNL2", {"PRNDL2": 6, "ManualMode": 0})

  def recorded(self):
    result = []
    for index in range(self.safety.get_recorded_can_count()):
      packet = new_CANPacket()
      self.assertTrue(self.safety.get_recorded_can(index, packet))
      result.append((packet.addr, packet.bus, bytes(packet.data[0:7 if packet.addr == 0xBD else 8])))
    return result

  def test_paired_sensor_fault_checksum_counter_and_timeout(self):
    self.safety.safety_rx_hook(self.low_gear())
    self.safety.set_controls_allowed(True)
    self.assertTrue(self.safety.safety_rx_hook(self.sensor(1)))
    self.assertTrue(self.safety.safety_tx_hook(self.packet(create_pedal_command(self.packer, .2, 1))))
    self.assertFalse(self.safety.safety_tx_hook(self.packet(create_pedal_command(self.packer, .2, 1))))

    for counter, bad in enumerate((self.sensor(2, state=1), self.sensor(3, pair_error=True),
                                   self.sensor(4, bad_crc=True), self.sensor(4)), start=2):
      self.safety.set_controls_allowed(True)
      self.safety.safety_rx_hook(bad)
      self.assertFalse(self.safety.safety_tx_hook(self.packet(create_pedal_command(self.packer, .2, counter))))
      self.assertTrue(self.safety.safety_tx_hook(self.packet(create_pedal_command(self.packer, 0., counter))))

    self.safety.safety_rx_hook(self.sensor(5))
    self.safety.set_controls_allowed(True)
    self.safety.set_timer(100001)
    self.assertFalse(self.safety.safety_tx_hook(self.packet(create_pedal_command(self.packer, .2, 6))))
    self.assertTrue(self.safety.safety_tx_hook(self.packet(create_pedal_command(self.packer, 0., 6))))

  def test_sensor_physical_curve_and_driver_override(self):
    self.safety.safety_rx_hook(self.low_gear())
    for counter, gas in enumerate((0., 4., 10., 23., 24., 30., 128., 255.), start=1):
      with self.subTest(gas=gas):
        self.assertTrue(self.safety.safety_rx_hook(self.sensor(counter, gas=gas)))
        self.assertEqual(self.safety.get_gas_pressed_prev(), gas > 23.)
        self.safety.set_controls_allowed(True)
        self.assertEqual(self.safety.safety_tx_hook(self.packet(create_pedal_command(self.packer, .2, counter))),
                         gas <= 23.)

  def test_paddle_waits_for_stock_phase_and_expires_without_feed(self):
    self.safety.safety_rx_hook(self.low_gear())
    self.safety.safety_rx_hook(self.sensor(1))
    self.safety.set_controls_allowed(True)
    paddle = create_bolt_regen_paddle(self.packer, True)
    gear = create_bolt_regen_gear(self.packer, True, False)
    self.assertFalse(self.safety.safety_tx_hook(self.packet(paddle)))
    self.assertFalse(self.safety.safety_tx_hook(self.packet(gear)))
    self.assertEqual(self.recorded(), [])

    stock_paddle = self.stock("EBCMRegenPaddle", {"RegenPaddle": 0})
    stock_gear = self.stock("ECMPRDNL2", {"PRNDL2": 6})
    self.safety.safety_rx_hook(stock_paddle)
    self.safety.safety_rx_hook(stock_gear)
    self.assertEqual([(addr, bus) for addr, bus, _ in self.recorded()], [(0xBD, 0), (0x1F5, 0)])
    self.assertEqual(self.recorded()[0][2], paddle[1])
    self.assertEqual(self.recorded()[1][2], gear[1])

    self.safety.reset_recorded_can()
    self.safety.set_timer(150000)
    self.safety.safety_rx_hook(stock_paddle)
    self.safety.safety_rx_hook(stock_gear)
    self.assertEqual(self.recorded(), [])
    self.safety.safety_rx_hook(self.sensor(2))
    self.safety.set_controls_allowed(True)
    self.safety.safety_rx_hook(self.low_gear())
    self.assertFalse(self.safety.safety_tx_hook(self.packet(paddle)))
    self.assertFalse(self.safety.safety_tx_hook(self.packet(gear)))
    self.safety.safety_rx_hook(stock_paddle)
    self.safety.safety_rx_hook(stock_gear)
    self.assertEqual([(addr, bus) for addr, bus, _ in self.recorded()], [(0xBD, 0), (0x1F5, 0)])

  def test_fault_and_driver_source_changes_consume_pending_spoofs(self):
    self.safety.safety_rx_hook(self.sensor(1))
    self.safety.safety_rx_hook(self.low_gear())
    self.safety.set_controls_allowed(True)
    applied_gear = self.packet(create_bolt_regen_gear(self.packer, True, False))
    applied_paddle = self.packet(create_bolt_regen_paddle(self.packer, True))
    stock_paddle = self.stock("EBCMRegenPaddle", {"RegenPaddle": 0})
    self.assertFalse(self.safety.safety_tx_hook(applied_gear))
    self.assertFalse(self.safety.safety_tx_hook(applied_paddle))
    # A real brake edge clears the pending active request; regaining controls alone cannot replay it.
    self.safety.safety_rx_hook(self.packet((0xC9, b"\x00" * 5 + b"\x01\x00\x00", 0)))
    self.safety.safety_rx_hook(self.packet((0xC9, b"\x00" * 8, 0)))
    self.safety.set_controls_allowed(True)
    self.safety.safety_rx_hook(self.low_gear())
    self.safety.safety_rx_hook(stock_paddle)
    self.assertEqual(self.recorded(), [])
    self.assertFalse(self.safety.safety_tx_hook(applied_gear))
    self.assertFalse(self.safety.safety_tx_hook(applied_paddle))
    self.safety.safety_rx_hook(self.low_gear())
    self.safety.safety_rx_hook(stock_paddle)
    self.assertEqual([addr for addr, _, _ in self.recorded()], [0x1F5, 0xBD])

    for prndl, manual in ((1, 0), (2, 0), (4, 0), (6, 1)):
      with self.subTest(prndl=prndl, manual=manual):
        self.safety.reset_recorded_can()
        self.safety.safety_rx_hook(self.low_gear())
        self.safety.set_controls_allowed(True)
        self.assertFalse(self.safety.safety_tx_hook(applied_gear))
        self.safety.safety_rx_hook(self.stock("ECMPRDNL2", {"PRNDL2": prndl, "ManualMode": manual}))
        self.assertEqual(self.recorded(), [])
        self.assertFalse(self.safety.safety_tx_hook(self.packet(create_pedal_command(self.packer, .2, prndl))))
        self.safety.safety_rx_hook(self.low_gear())
        self.assertEqual(self.recorded(), [])

    self.safety.reset_recorded_can()
    self.safety.safety_rx_hook(self.low_gear())
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(applied_paddle))
    self.safety.safety_rx_hook(self.stock("EBCMRegenPaddle", {"RegenPaddle": 2}))
    self.assertEqual(self.recorded(), [])
    self.safety.safety_rx_hook(stock_paddle)
    self.assertEqual(self.recorded(), [])
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(applied_paddle))
    self.safety.safety_rx_hook(stock_paddle)
    self.assertEqual([addr for addr, _, _ in self.recorded()], [0xBD])

  def test_owned_tx_only_and_stock_acc_sibling(self):
    self.safety.safety_rx_hook(self.sensor(1))
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(self.stock("ASCMGasRegenCmd", {"GasRegenCmd": 0})))
    self.assertFalse(self.safety.safety_tx_hook(self.packet(self.packer.make_can_msg("ASCMSteeringButton", 2, {"ACCButtons": 6}))))

    self.init_mode(GMSafetyFlags.BOLT_ACC_PEDAL)
    self.safety.safety_rx_hook(self.sensor(1))
    self.safety.safety_rx_hook(self.stock("AcceleratorPedal2", {"CruiseState": 1}))
    self.assertTrue(self.safety.safety_tx_hook(self.packet(self.packer.make_can_msg("ASCMSteeringButton", 2, {"ACCButtons": 6}))))
    self.assertFalse(self.safety.safety_tx_hook(self.packet(self.packer.make_can_msg("ASCMSteeringButton", 2, {"ACCButtons": 2}))))
    self.assertFalse(self.safety.safety_tx_hook(self.stock("ASCMGasRegenCmd", {"GasRegenCmd": 0})))

    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, int(GMSafetyFlags.HW_CAM | GMSafetyFlags.EV)), 0)
    self.safety.init_tests()
    self.assertFalse(self.safety.safety_tx_hook(self.packet(create_pedal_command(self.packer, .2, 1))))

  def test_acc_pedal_friction_requires_exclusive_fresh_owner(self):
    chassis = CANPacker("gm_global_a_chassis")

    def brake(value, counter, mode=None, bus=0):
      mode = (1 if value == 0 else 0xA) if mode is None else mode
      raw = (0x1000 - value) & 0xFFF
      checksum = (0x10000 - (mode << 12) - raw - counter) & 0xFFFF
      return self.packet(chassis.make_can_msg("EBCMFrictionBrakeCmd", bus, {
        "FrictionBrakeCmd": -value, "FrictionBrakeMode": mode,
        "RollingCounter": counter, "FrictionBrakeChecksum": checksum,
      }))

    self.init_mode(GMSafetyFlags.BOLT_ACC_PEDAL | GMSafetyFlags.BOLT_GEN2)
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(brake(100, 0)))
    self.assertFalse(self.safety.safety_tx_hook(brake(0, 0)))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x315), 0)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x2CB), 0)

    self.safety.safety_rx_hook(self.low_gear())
    self.safety.safety_rx_hook(self.sensor(1))
    self.safety.safety_rx_hook(self.stock("AcceleratorPedal2", {"CruiseState": 0}))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x315), -1)
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(brake(100, 0)))
    self.assertTrue(self.safety.safety_tx_hook(brake(0, 0)))
    self.safety.safety_rx_hook(self.stock("ECMEngineStatus", {"CruiseMainOn": 1}))
    self.assertTrue(self.safety.safety_tx_hook(brake(100, 1)))
    self.assertFalse(self.safety.safety_tx_hook(brake(100, 1)))
    self.assertFalse(self.safety.safety_tx_hook(brake(401, 2)))
    self.assertTrue(self.safety.safety_tx_hook(brake(0, 2, mode=9)))
    self.assertFalse(self.safety.safety_tx_hook(brake(100, 3, mode=1)))
    self.assertFalse(self.safety.safety_tx_hook(brake(100, 3, bus=2)))
    invalid = bytearray(chassis.make_can_msg("EBCMFrictionBrakeCmd", 0, {
      "FrictionBrakeCmd": -100, "FrictionBrakeMode": 0xA,
      "RollingCounter": 3, "FrictionBrakeChecksum": (0x10000 - (0xA << 12) - (0x1000 - 100) - 3) & 0xFFFF,
    })[1])
    invalid[3] ^= 1
    self.assertFalse(self.safety.safety_tx_hook(self.packet((0x315, bytes(invalid), 0))))

    self.safety.safety_rx_hook(self.stock("AcceleratorPedal2", {"CruiseState": 1}))
    self.assertFalse(self.safety.safety_tx_hook(brake(100, 3)))
    self.assertFalse(self.safety.safety_tx_hook(brake(0, 3, mode=9)))
    self.assertFalse(self.safety.safety_tx_hook(brake(0, 3)))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x315), 0)
    self.safety.safety_rx_hook(self.stock("AcceleratorPedal2", {"CruiseState": 0}))
    self.safety.safety_rx_hook(self.stock("ECMEngineStatus", {"CruiseMainOn": 0, "BrakePressed": 1}))
    self.assertFalse(self.safety.safety_tx_hook(brake(100, 3)))
    self.assertTrue(self.safety.safety_tx_hook(brake(0, 3)))
    self.safety.set_timer(300001)
    self.assertFalse(self.safety.safety_tx_hook(brake(100, 0)))
    self.assertFalse(self.safety.safety_tx_hook(brake(0, 0)))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x315), 0)

    self.init_mode(GMSafetyFlags.NO_ACC | GMSafetyFlags.BOLT_GEN2)
    self.assertFalse(self.safety.safety_tx_hook(brake(0, 0)))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x315), 0)

  def test_2017_steering_limit_is_conditional(self):
    steer = self.packet(create_steering_control(self.packer, 0, 400, 0, True))
    for variant, pedal, allowed in ((GMSafetyFlags.NO_ACC | GMSafetyFlags.BOLT_2017, True, True),
                                    (GMSafetyFlags.NO_ACC | GMSafetyFlags.BOLT_2017, False, True),
                                    (GMSafetyFlags.NO_ACC, True, False)):
      with self.subTest(variant=variant, pedal=pedal):
        self.init_mode(variant, pedal=pedal)
        self.safety.set_controls_allowed(True)
        self.safety.set_torque_driver(0, 0)
        self.safety.set_desired_torque_last(400)
        self.safety.set_rt_torque_last(400)
        self.assertEqual(self.safety.safety_tx_hook(steer), allowed)

  def test_stock_acc_ownership_requires_fresh_confirmed_disengagement(self):
    self.init_mode(GMSafetyFlags.BOLT_ACC_PEDAL | GMSafetyFlags.BOLT_GEN2)
    self.safety.safety_rx_hook(self.low_gear())

    def active(counter):
      return self.packet(create_pedal_command(self.packer, .2, counter))

    def disabled(counter):
      return self.packet(create_pedal_command(self.packer, 0., counter))
    self.safety.safety_rx_hook(self.sensor(1))
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(active(1)))  # startup status unknown
    self.assertTrue(self.safety.safety_tx_hook(disabled(1)))

    self.safety.safety_rx_hook(self.stock("AcceleratorPedal2", {"CruiseState": 0}))
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(active(2)))  # main state unknown
    self.safety.safety_rx_hook(self.stock("ECMEngineStatus", {"CruiseMainOn": 1}))
    self.assertTrue(self.safety.safety_tx_hook(active(2)))
    self.safety.safety_rx_hook(self.stock("AcceleratorPedal2", {"CruiseState": 1}))
    self.assertFalse(self.safety.safety_tx_hook(active(3)))
    self.assertFalse(self.safety.safety_tx_hook(self.packet(create_bolt_regen_paddle(self.packer, True))))
    self.assertFalse(self.safety.safety_tx_hook(self.packet(create_bolt_regen_gear(self.packer, True, True))))
    self.assertTrue(self.safety.safety_tx_hook(disabled(3)))
    self.assertTrue(self.safety.safety_tx_hook(self.packet(self.packer.make_can_msg("ASCMSteeringButton", 2, {"ACCButtons": 6}))))

    self.safety.safety_rx_hook(self.stock("AcceleratorPedal2", {"CruiseState": 0}))
    self.safety.safety_rx_hook(self.sensor(2))
    self.safety.set_controls_allowed(True)
    self.assertTrue(self.safety.safety_tx_hook(active(4)))
    self.safety.safety_rx_hook(self.stock("ECMEngineStatus", {"CruiseMainOn": 0}))
    self.assertFalse(self.safety.get_controls_allowed())
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(active(5)))
    self.assertTrue(self.safety.safety_tx_hook(disabled(5)))
    self.safety.safety_rx_hook(self.stock("ECMEngineStatus", {"CruiseMainOn": 1}))
    self.safety.set_timer(300001)
    self.safety.safety_rx_hook(self.sensor(3))
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(active(6)))
    self.assertTrue(self.safety.safety_tx_hook(disabled(6)))

  def test_scheduler_rejects_all_noncanonical_payloads(self):
    for variant in (GMSafetyFlags.NO_ACC | GMSafetyFlags.BOLT_2017,
                    GMSafetyFlags.NO_ACC | GMSafetyFlags.BOLT_GEN2):
      with self.subTest(variant=variant):
        self.init_mode(variant)
        self.safety.safety_rx_hook(self.low_gear())
        self.safety.safety_rx_hook(self.sensor(1))
        self.safety.set_controls_allowed(True)
        paddle = create_bolt_regen_paddle(self.packer, True)
        gear = create_bolt_regen_gear(self.packer, True, bool(variant & GMSafetyFlags.BOLT_GEN2))
        bad = bytearray(paddle[1])
        bad[1] = 1
        self.assertFalse(self.safety.safety_tx_hook(self.packet((paddle[0], bytes(bad), paddle[2]))))
        bad = bytearray(paddle[1])
        bad[0] = 0x30
        self.assertFalse(self.safety.safety_tx_hook(self.packet((paddle[0], bytes(bad), paddle[2]))))
        for index, replacement in ((0, 0x0D), (3, 0x0F), (5, 3), (6, 2)):
          bad = bytearray(gear[1])
          bad[index] = replacement
          self.assertFalse(self.safety.safety_tx_hook(self.packet((gear[0], bytes(bad), gear[2]))))
        wrong_generation = create_bolt_regen_gear(self.packer, True, not bool(variant & GMSafetyFlags.BOLT_GEN2))
        self.assertFalse(self.safety.safety_tx_hook(self.packet(wrong_generation)))
        self.assertEqual(self.recorded(), [])

  def test_real_parser_controller_and_native_safety_four_variants(self):
    for candidate in PEDAL_BOLT_CAR:
      with self.subTest(candidate=candidate):
        cp = params(candidate, True, True)
        self.assertTrue(cp.openpilotLongitudinalControl)
        self.assertEqual(cp.safetyConfigs[0].safetyModel, CarParams.SafetyModel.gm)
        self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm,
                                                      cp.safetyConfigs[0].safetyParam), 0)
        self.safety.init_tests()
        self.safety.reset_recorded_can()
        self.safety.set_timer(950000)
        packer = CANPacker(DBC[candidate][Bus.pt])
        car_state = CarState(cp)
        parsers = car_state.get_can_parsers(cp)
        car_state.update(parsers)
        sensor = packer.make_can_msg("GAS_SENSOR", 0, {"INTERCEPTOR_GAS": 0,
                                                      "INTERCEPTOR_GAS2": 0,
                                                      "COUNTER_PEDAL": 1, "STATE": 0})
        sensor_data = bytearray(sensor[1])
        sensor_data[5] = pedal_crc(sensor_data)
        source = [(sensor[0], bytes(sensor_data), sensor[2]),
                  packer.make_can_msg("ECMPRDNL2", 0, {"PRNDL2": 6, "ManualMode": 0})]
        if candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
          source.append(packer.make_can_msg("AcceleratorPedal2", 0, {"CruiseState": 0}))
          source.append(packer.make_can_msg("ECMEngineStatus", 0, {"CruiseMainOn": 1}))
        parsers[Bus.pt].update([(950_000_000, source)])
        out = car_state.update(parsers)
        self.assertTrue(car_state.pedal_sensor_healthy)
        self.assertTrue(self.safety.safety_rx_hook(self.packet(source[0])))
        self.assertTrue(self.safety.safety_rx_hook(self.packet(source[1])))
        if len(source) > 2:
          self.assertTrue(self.safety.safety_rx_hook(self.packet(source[2])))
          self.assertTrue(self.safety.safety_rx_hook(self.packet(source[3])))
          self.assertFalse(out.cruiseState.enabled)
          self.assertEqual(car_state.stock_acc_status_ts_nanos, 950_000_000)
        self.safety.set_controls_allowed(True)
        self.assertEqual(out.gearShifter, structs.CarState.GearShifter.low)

        controller = CarController(DBC[candidate], cp)
        controller.frame = 4
        controller.last_steer_frame = 4
        control = structs.CarControl()
        control.enabled = True
        control.longActive = True
        control.actuators.accel = 1.
        out.vEgo = 12.
        cs = SimpleNamespace(out=out.as_reader(), pedal_sensor_healthy=car_state.pedal_sensor_healthy,
                             pedal_sensor_ts_nanos=car_state.pedal_sensor_ts_nanos,
                             stock_acc_status_ts_nanos=car_state.stock_acc_status_ts_nanos,
                             cam_lka_steering_cmd_counter=0, loopback_lka_steering_cmd_updated=False,
                             loopback_lka_steering_cmd_ts_nanos=1_000_000_000, pt_lka_steering_cmd_counter=0,
                             buttons_counter=0)
        _, commands = controller.update(control.as_reader(), cs, 1_000_000_000)
        acc_pedal = candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL
        self.assertEqual([msg[0] for msg in commands], [0x200, 0x1F5, 0xBD] + ([0x315] if acc_pedal else []))
        self.safety.set_timer(1_000_000)
        self.assertTrue(self.safety.safety_tx_hook(self.packet(commands[0])))
        self.assertFalse(self.safety.safety_tx_hook(self.packet(commands[1])))
        self.assertFalse(self.safety.safety_tx_hook(self.packet(commands[2])))
        if acc_pedal:
          self.assertTrue(self.safety.safety_tx_hook(self.packet(commands[3])))
        self.assertEqual(self.recorded(), [])
        self.safety.safety_rx_hook(self.packet(packer.make_can_msg("ECMPRDNL2", 0, {"PRNDL2": 6})))
        self.safety.safety_rx_hook(self.packet(packer.make_can_msg("EBCMRegenPaddle", 0, {"RegenPaddle": 0})))
        self.assertEqual([item[0] for item in self.recorded()], [0x1F5, 0xBD])

        controller.frame = 8
        self.safety.reset_recorded_can()
        _, released = controller.update(control.as_reader(), cs, 1_200_000_000)
        released = [msg for msg in released if msg[0] in (0x200, 0x1F5, 0xBD)]
        self.assertEqual([msg[0] for msg in released], [0x200, 0x1F5, 0xBD])
        self.assertEqual(released[0][1][0:4], b"\x00" * 4)
        self.assertEqual(released[1][1], b"\x0c\x0c\x00\x06\x00\x00\x01\x00")
        self.assertEqual(released[2][1], b"\x00" * 7)
        self.safety.set_timer(1_200_000)
        self.assertTrue(self.safety.safety_tx_hook(self.packet(released[0])))
        self.assertFalse(self.safety.safety_tx_hook(self.packet(released[1])))
        self.assertFalse(self.safety.safety_tx_hook(self.packet(released[2])))
        self.safety.safety_rx_hook(self.packet(packer.make_can_msg("ECMPRDNL2", 0, {"PRNDL2": 6})))
        self.safety.safety_rx_hook(self.packet(packer.make_can_msg("EBCMRegenPaddle", 0, {"RegenPaddle": 0})))
        self.assertEqual(self.recorded(), [(0x1F5, 0, released[1][1]), (0xBD, 0, released[2][1])])
