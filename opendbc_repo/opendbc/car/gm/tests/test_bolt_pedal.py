import unittest
from types import SimpleNamespace

from opendbc.can import CANPacker, CANParser

from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.gmcan import pedal_crc
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import (CAR, DBC, GMFlags, GMSafetyFlags, NO_ACC_BOLT_CAR, PEDAL_BOLT_CAR, BOLT_PEDAL_WORDS,
                                  CarControllerParams, is_bolt_present_no_acc_pedal_profile)


def params(candidate, setting=False, pedal=False, alpha_long=False, missing_key=False, camera=False, removed=False):
  fingerprint = gen_empty_fingerprint()
  if not removed:
    fingerprint[2][0x320] = 8
  else:
    fingerprint[0].update({0x184: 8, 0x34A: 5, 0x348: 5, 0xC9: 8, 0x1C4: 8, 0x1E1: 7,
                           0x1F5: 8, 0xBD: 7, 0x232: 8, 0x3D1: 8, 0xBE: 6})
  if camera:
    fingerprint[2][0x180] = 4
  if pedal:
    fingerprint[0][0x201] = 6
  return CarInterface.get_params(candidate, fingerprint, [], alpha_long, False, False)


class TestBoltPedalIdentity(unittest.TestCase):
  def test_removed_pedal_factory_has_one_physical_parser_owner(self):
    from opendbc.car.gm.values import (BOLT_PEDAL_REMOVED_CARS, BOLT_PEDAL_REMOVED_STOCK_WORDS,
                                      is_bolt_pedal_profile, is_bolt_pedal_removed_profile)
    for index, candidate in enumerate(BOLT_PEDAL_REMOVED_CARS):
      with self.subTest(candidate=candidate):
        cp = params(candidate, pedal=True, removed=True)
        self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xE700 + index)
        self.assertTrue(is_bolt_pedal_removed_profile(cp))
        self.assertTrue(cp.openpilotLongitudinalControl)
        self.assertFalse(cp.pcmCruise)
        for stock in (False, True):
          selected = cp.as_reader().as_builder()
          if stock:
            selected.safetyConfigs[0].safetyParam = BOLT_PEDAL_REMOVED_STOCK_WORDS[candidate]
            selected.openpilotLongitudinalControl = False
            selected.pcmCruise = True
          self.assertTrue(is_bolt_pedal_removed_profile(selected, stock_only=stock))
          state = CarState(selected)
          parsers = state.get_can_parsers(selected)
          for parser in parsers.values():
            parser.update([(1_000_000_000, [])])
          state.update(parsers)
          self.assertFalse(parsers[Bus.cam].message_states)
          self.assertNotIn(0x180, parsers[Bus.pt].message_states)
          self.assertIn(0x180, parsers[Bus.loopback].message_states)
          self.assertEqual(0x201 in parsers[Bus.pt].message_states, not stock)
        missing = params(candidate, pedal=False, removed=True)
        self.assertFalse(is_bolt_pedal_removed_profile(missing))
        present = params(candidate, pedal=True)
        self.assertTrue(is_bolt_pedal_profile(present))
        self.assertFalse(is_bolt_pedal_removed_profile(present))

  def test_removed_acc_admission_keeps_both_physical_cruise_sources(self):
    cp = params(CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, pedal=True, removed=True)
    cs = CarState(cp)
    parsers = cs.get_can_parsers(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    controller = CarController(DBC[cp.carFingerprint], cp)
    control = structs.CarControl(longActive=True)
    for tick, (acc, cruise) in enumerate(((1, 0), (0, 1), (0, 0)), 1):
      now = 1_000_000_000 + tick * 20_000_000
      frames = [packer.make_can_msg("AcceleratorPedal2", 0, {"CruiseState": acc}),
                packer.make_can_msg("ECMCruiseControl", 0, {"CruiseActive": cruise})]
      parsers[Bus.pt].update([(now, frames)])
      cs.out = cs.update(parsers)
      self.assertEqual(cs.bolt_pedal_removed_acc_active, bool(acc))
      self.assertEqual(cs.out.cruiseState.enabled, bool(cruise))
      self.assertEqual(controller.bolt_pedal_admission(control, cs, now)[1], not (acc or cruise))

  def test_reduced_stock_cancel_credit_requires_new_slot_after_driver_override(self):
    from opendbc.car.gm.conventional_pedal import CancelCredit
    packer = CANPacker(DBC[CAR.CHEVROLET_BOLT_CC_2017][Bus.pt])
    neutral = packer.make_can_msg("ASCMSteeringButton", 0, {
      "ACCAlwaysOne": 1, "ACCButtons": 1, "RollingCounter": 0, "SteeringButtonChecksum": 0xFF})
    overrides = ((0xBD, bytes((0x20, 0, 0, 0, 0, 0, 0))),
                 (0xC9, bytes((0, 0, 0, 32, 0, 1, 0, 0))),
                 (0x1C4, bytes((0, 0, 0, 0, 0, 1, 0, 0))),
                 (0x1F5, bytes((0, 0, 0, 3, 0, 0, 0, 0))))
    for address, raw in overrides:
      for scoped in (False, True):
        with self.subTest(address=address, scoped=scoped):
          credit = CancelCredit()
          credit.observe([(1_000_000_000, [neutral])], clear_on_driver_override=scoped)
          self.assertGreater(credit.credit_ns, 0)
          released = (bytes((0, 0, 0, 32, 0, 0, 0, 0)) if address == 0xC9 else
                      bytes((0, 0, 0, 4, 0, 0, 0, 0)) if address == 0x1F5 else bytes(len(raw)))
          credit.observe([(1_010_000_000, [(address, raw, 0)]),
                          (1_020_000_000, [(address, released, 0)])],
                         clear_on_driver_override=scoped)
          self.assertEqual(credit.credit_ns, 0 if scoped else 1_000_000_000)
          next_neutral = packer.make_can_msg("ASCMSteeringButton", 0, {
            "ACCAlwaysOne": 1, "ACCButtons": 1, "RollingCounter": 1, "SteeringButtonChecksum": 0x5EE})
          credit.observe([(1_030_000_000, [next_neutral])], clear_on_driver_override=scoped)
          self.assertEqual(credit.credit_ns, 1_030_000_000)

  def test_no_acc_fixed_stop_preserves_calc_memory_and_emits_neutral(self):
    for candidate in NO_ACC_BOLT_CAR:
      with self.subTest(candidate=candidate):
        cp = params(candidate, pedal=True)
        controller = CarController(DBC[candidate], cp)
        controller.frame = controller.last_steer_frame = 4
        controller.pedal_steady, controller.pedal_active_last = .2, True
        controller.regen_press_count, controller.regen_release_count = 2, 3
        controller.regen_min_on_frames, controller.regen_min_off_frames = 4, 5
        controller.regen_paddle_pressed = True
        names = ("pedal_steady", "pedal_active_last", "regen_press_count", "regen_release_count",
                 "regen_min_on_frames", "regen_min_off_frames", "regen_paddle_pressed")
        memory = tuple(getattr(controller, name) for name in names)
        out = structs.CarState(vEgo=0., aEgo=0., standstill=True)
        out.gearShifter = structs.CarState.GearShifter.low
        out.cruiseState.available = out.cruiseState.standstill = True
        cs = SimpleNamespace(out=out, pedal_sensor_healthy=True, pedal_sensor_ts_nanos=1_000_000_000,
                             bolt_pedal_standstill_ts_nanos=1_000_000_000,
                             bolt_pedal_main_ts_nanos=1_000_000_000, bolt_pedal_gear_ts_nanos=1_000_000_000,
                             cam_lka_steering_cmd_counter=0, loopback_lka_steering_cmd_updated=False,
                             loopback_lka_steering_cmd_ts_nanos=1_000_000_000, pt_lka_steering_cmd_counter=0,
                             buttons_counter=0)
        control = structs.CarControl(enabled=True, longActive=True)
        control.actuators.accel = -.03
        control.actuators.longControlState = structs.CarControl.Actuators.LongControlState.stopping
        _, commands = controller.update(control.as_reader(), cs, 1_000_000_000)
        self.assertEqual(tuple(getattr(controller, name) for name in names), memory)
        self.assertEqual(controller.apply_gas, 0.)
        for frame in commands:
          if frame[0] == 0x200:
            self.assertFalse(frame[1][4] & 0x80)
          elif frame[0] == 0xBD:
            self.assertEqual(frame[1][0] & 0xF0, 0)
          elif frame[0] == 0x1F5:
            self.assertEqual(frame[1][3] & 15, 6)
            self.assertEqual(frame[1][5] & 2, 0)

  def test_no_acc_standstill_is_fresh_and_does_not_block_interceptor_release(self):
    from openpilot.selfdrive.controls.lib.longcontrol import LongControl
    from openpilot.starpilot.longitudinal.extension import LongitudinalContext
    states = structs.CarControl.Actuators.LongControlState
    for candidate in NO_ACC_BOLT_CAR:
      with self.subTest(candidate=candidate):
        cp = params(candidate, pedal=True)
        cs = CarState(cp)
        parsers = cs.get_can_parsers(cp)
        parser = parsers[Bus.pt]
        packer = CANPacker(DBC[candidate][Bus.pt])
        packets = []
        for message in parser.message_states.values():
          values = ({"CruiseState": 4} if message.name == "AcceleratorPedal2" else
                    {"CruiseMainOn": 1} if message.name == "ECMEngineStatus" else
                    {"PRNDL2": 6, "ManualMode": 0} if message.name == "ECMPRDNL2" else {})
          if message.name == "GAS_SENSOR":
            packets.append(TestBoltPedalMessages.sensor(packer, 0., 1))
          else:
            packets.append(packer.make_can_msg(message.name, 0, values))
        parser.update([(1_000_000_000, packets)])
        out = cs.update(parsers)
        self.assertTrue(parser.can_valid)
        self.assertTrue(out.cruiseState.standstill)
        out.canValid = parser.can_valid
        out.canTimeout = parser.bus_timeout
        long = LongControl(cp)
        long.long_control_state = states.stopping
        long.update(True, out, .5, False, (-4., 2.), context=LongitudinalContext())
        self.assertEqual(long.long_control_state, states.pid)
        long.update(True, out, .5, True, (-4., 2.), context=LongitudinalContext())
        self.assertEqual(long.long_control_state, states.stopping)
        out.brakePressed = True
        long.update(True, out, .5, False, (-4., 2.), context=LongitudinalContext())
        self.assertEqual(long.long_control_state, states.stopping)
        parser.update([(1_300_000_001, [packer.make_can_msg("ECMEngineStatus", 0, {})])])
        self.assertFalse(cs.update(parsers).cruiseState.standstill)

  def test_no_acc_fixed_launch_requires_current_original_stop_state(self):
    for candidate in NO_ACC_BOLT_CAR:
      cp = params(candidate, pedal=True)
      for unavailable in (None, "missing", "future", "stale", "stale_main", "stale_gear", "moving", "main", "gas", "brake",
                          "regen", "stopping", "untuned", "tuned"):
        with self.subTest(candidate=candidate, unavailable=unavailable):
          controller = CarController(DBC[candidate], cp)
          controller.frame = controller.last_steer_frame = 104
          controller.gm_acc_tune_input = SimpleNamespace(update=lambda now, case=unavailable: case == "tuned")
          control = structs.CarControl(enabled=True, longActive=True)
          control.actuators.accel = -.12 if unavailable in ("untuned", "tuned") else .5
          control.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
          if unavailable == "stopping":
            control.actuators.longControlState = structs.CarControl.Actuators.LongControlState.stopping
          out = structs.CarState(vEgo=2., aEgo=0., standstill=unavailable != "moving")
          out.gearShifter = structs.CarState.GearShifter.low
          out.cruiseState.available = unavailable != "main"
          out.cruiseState.standstill = True
          out.gasPressed, out.brakePressed, out.regenBraking = (unavailable == "gas", unavailable == "brake", unavailable == "regen")
          stamp = 699_999_999 if unavailable == "stale" else 1_000_000_001 if unavailable == "future" else 1_000_000_000
          cs = SimpleNamespace(out=out, pedal_sensor_healthy=True, pedal_sensor_ts_nanos=1_000_000_000,
                               bolt_pedal_standstill_ts_nanos=stamp,
                               bolt_pedal_main_ts_nanos=699_999_999 if unavailable == "stale_main" else 1_000_000_000,
                               bolt_pedal_gear_ts_nanos=899_999_999 if unavailable == "stale_gear" else 1_000_000_000,
                               cam_lka_steering_cmd_counter=0, loopback_lka_steering_cmd_updated=False,
                               loopback_lka_steering_cmd_ts_nanos=1_000_000_000, pt_lka_steering_cmd_counter=0, buttons_counter=0)
          if unavailable == "missing":
            del cs.bolt_pedal_standstill_ts_nanos
          _, messages = controller.update(control.as_reader(), cs, 1_000_000_000)
          self.assertEqual([message[0] for message in messages if message[0] == 0x200], [0x200])
          if unavailable in (None, "untuned"):
            self.assertAlmostEqual(controller.apply_gas, 18. / 255.)
          else:
            self.assertNotAlmostEqual(controller.apply_gas, 18. / 255.)

  def test_pedal_requires_exact_hardware_not_saved_opt_in(self):
    for candidate in PEDAL_BOLT_CAR:
      for setting in (False, True):
        for observed in (False, True):
          for missing in (False, True):
            with self.subTest(candidate=candidate, setting=setting, observed=observed, missing=missing):
              cp = params(candidate, setting, observed, alpha_long=True, missing_key=missing)
              self.assertEqual(bool(cp.flags & GMFlags.PEDAL_LONG), observed)
              self.assertEqual(bool(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.PEDAL_LONG), observed)
              self.assertFalse(cp.pcmCruise)

  def test_ordinary_cruise_ownership_is_never_stock_acc(self):
    for candidate in NO_ACC_BOLT_CAR:
      for enabled in (False, True):
        with self.subTest(candidate=candidate, enabled=enabled):
          cp = params(candidate, enabled, True)
          self.assertFalse(cp.pcmCruise)
          self.assertTrue(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.NO_ACC)
          self.assertFalse(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.BOLT_ACC_PEDAL)

  def test_detected_stock_acc_bolt_selects_existing_pedal_owner(self):
    for identity in (CAR.CHEVROLET_BOLT_EUV, CAR.CHEVROLET_BOLT_ACC_2022_2023):
      cp = params(identity, False, True)
      self.assertEqual(cp.carFingerprint, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)
      self.assertTrue(cp.flags & GMFlags.PEDAL_LONG)
      self.assertTrue(cp.openpilotLongitudinalControl)
      self.assertFalse(cp.pcmCruise)

  def test_2022_pedal_variants_do_not_claim_automatic_fingerprint_identity(self):
    from opendbc.car.gm.fingerprints import FINGERPRINTS, FW_VERSIONS
    self.assertNotIn(CAR.CHEVROLET_BOLT_CC_2022_2023, FINGERPRINTS)
    self.assertNotIn(CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, FINGERPRINTS)
    self.assertFalse(FW_VERSIONS)


class TestBoltPedalMessages(unittest.TestCase):
  @staticmethod
  def sensor(packer, gas, counter, state=0, other_track=None, bad_crc=False):
    msg = packer.make_can_msg("GAS_SENSOR", 0, {
      "INTERCEPTOR_GAS": gas,
      "INTERCEPTOR_GAS2": gas if other_track is None else other_track,
      "STATE": state, "COUNTER_PEDAL": counter,
    })
    data = bytearray(msg[1])
    data[5] = pedal_crc(data) ^ int(bad_crc)
    return msg[0], bytes(data), msg[2]

  def test_physical_route_channels_are_independent_adc_observations(self):
    cp = params(CAR.CHEVROLET_BOLT_CC_2018_2021, True, True)
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    route_frames = ("053502ba0164", "04e30286048f", "046c024108e3", "0279012a06f6")
    for index, payload in enumerate(route_frames):
      with self.subTest(payload=payload):
        raw = bytes.fromhex(payload)
        self.assertEqual(pedal_crc(raw), raw[5])
        parsers[Bus.pt].update([(1_000_000_000 + index * 20_000_000, [(0x201, raw, 0)])])
        out = state.update(parsers)
        self.assertTrue(state.pedal_sensor_healthy)
        sensor = parsers[Bus.pt].vl["GAS_SENSOR"]
        encoded = packer.make_can_msg("GAS_SENSOR", 0, sensor)[1]
        self.assertEqual(encoded, raw)
        first, second = int.from_bytes(raw[:2], "big"), int.from_bytes(raw[2:4], "big")
        self.assertEqual(out.gasPressed, first + second > 1190)
    self.assertLess(sensor["INTERCEPTOR_GAS2"], 0.)
    gear = packer.make_can_msg("ECMPRDNL2", 0, {"PRNDL2": 6, "ManualMode": 0})
    parsers[Bus.pt].update([(1_080_000_000, [gear])])
    state.out = state.update(parsers).as_reader()
    command = structs.CarControl(longActive=True)
    controller = CarController(DBC[cp.carFingerprint], cp)
    sensor_time = state.pedal_sensor_ts_nanos
    self.assertTrue(controller.bolt_pedal_admission(command, state, sensor_time + 100_000_000)[0])
    self.assertFalse(controller.bolt_pedal_admission(command, state, sensor_time + 100_000_001)[0])
    self.assertFalse(controller.bolt_pedal_admission(command, state, sensor_time - 1)[0])

    last = bytes.fromhex(route_frames[-1])
    parsers[Bus.pt].update([(1_100_000_000, [(0x201, last, 0)])])
    state.update(parsers)
    self.assertFalse(state.pedal_sensor_healthy)
    for index, (first, second, status, corrupt_crc) in enumerate(
        ((633, 298, 1, False), (633, 298, 0, True), (4096, 298, 0, False), (633, 4096, 0, False))):
      raw = bytearray(first.to_bytes(2, "big") + second.to_bytes(2, "big") + bytes([(status << 4) | (index + 7), 0]))
      raw[5] = pedal_crc(raw) ^ int(corrupt_crc)
      parsers[Bus.pt].update([(1_120_000_000 + index * 20_000_000, [(0x201, bytes(raw), 0)])])
      state.update(parsers)
      self.assertFalse(state.pedal_sensor_healthy)

  def test_real_parser_sensor_curve_and_fault_recovery(self):
    for candidate in PEDAL_BOLT_CAR:
      with self.subTest(candidate=candidate):
        cp = params(candidate, True, True)
        state = CarState(cp)
        parsers = state.get_can_parsers(cp)
        state.update(parsers)
        packer = CANPacker(DBC[candidate][Bus.pt])
        for counter, gas in enumerate((0., 4., 10., 23., 24., 30., 128., 255.), start=1):
          parsers[Bus.pt].update([(1_000_000_000 + counter * 20_000_000,
                                   [self.sensor(packer, gas, counter)])])
          out = state.update(parsers)
          self.assertTrue(state.pedal_sensor_healthy, gas)
          self.assertEqual(out.gasPressed, gas > 23., gas)

        for counter, kwargs in ((9, {"state": 1}), (10, {"other_track": 1000.}), (11, {"bad_crc": True})):
          parsers[Bus.pt].update([(1_000_000_000 + counter * 20_000_000,
                                   [self.sensor(packer, 30., counter, **kwargs)])])
          state.update(parsers)
          self.assertFalse(state.pedal_sensor_healthy)
        parsers[Bus.pt].update([(1_240_000_000, [self.sensor(packer, 30., 12)])])
        state.update(parsers)
        self.assertTrue(state.pedal_sensor_healthy)
        parsers[Bus.pt].update([(1_260_000_000, [self.sensor(packer, 30., 12)])])
        state.update(parsers)
        self.assertFalse(state.pedal_sensor_healthy)

  def test_controller_pedal_rate_release_and_stock_handoff(self):
    for candidate in PEDAL_BOLT_CAR:
      with self.subTest(candidate=candidate):
        cp = params(candidate, True, True)
        controller = CarController(DBC[candidate], cp)
        controller.frame = 4
        controller.last_steer_frame = 4
        control = structs.CarControl()
        control.enabled = True
        control.longActive = True
        control.actuators.accel = 1.
        state = structs.CarState()
        state.vEgo = 12.
        state.aEgo = 0.
        state.gearShifter = structs.CarState.GearShifter.low
        state.cruiseState.available = True
        cs = SimpleNamespace(out=state.as_reader(), pedal_sensor_healthy=True,
                             pedal_sensor_ts_nanos=950_000_000, stock_acc_status_ts_nanos=950_000_000,
                             bolt_pedal_gear_ts_nanos=950_000_000, bolt_pedal_main_ts_nanos=950_000_000,
                             cam_lka_steering_cmd_counter=0, loopback_lka_steering_cmd_updated=False,
                             loopback_lka_steering_cmd_ts_nanos=1_000_000_000, pt_lka_steering_cmd_counter=0,
                             buttons_counter=0)
        _, messages = controller.update(control.as_reader(), cs, 1_000_000_000)
        expected = ([0x3D1] if candidate in NO_ACC_BOLT_CAR else []) + [0x200, 0x1F5, 0xBD]
        if candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
          expected.append(0x315)
        self.assertEqual([m[0] for m in messages], expected)
        self.assertGreater(controller.pedal_steady, 0.)
        first_fraction = controller.pedal_steady

        controller.frame = 8
        control.actuators.accel = 2.
        _, messages = controller.update(control.as_reader(), cs, 1_000_000_000)
        self.assertEqual([m[0] for m in messages], expected)
        self.assertGreater(controller.pedal_steady, first_fraction)
        self.assertLess(controller.pedal_steady - first_fraction, 0.06)

        controller.frame = 12
        cs.pedal_sensor_healthy = False
        _, messages = controller.update(control.as_reader(), cs, 1_000_000_000)
        self.assertEqual([m[0] for m in messages], expected)
        payloads = {message[0]: message[1] for message in messages}
        self.assertEqual(payloads[0x200][0:4], b"\x00" * 4)
        self.assertEqual(payloads[0x1F5], b"\x0c\x0c\x00\x06\x00\x00\x01\x00")
        self.assertEqual(payloads[0xBD], b"\x00" * 7)
        self.assertEqual(controller.pedal_steady, 0.)

        if candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
          controller.frame = 16
          cs.pedal_sensor_healthy = True
          state.cruiseState.enabled = True
          cs.out = state.as_reader()
          _, messages = controller.update(control.as_reader(), cs, 1_000_000_000)
          self.assertEqual(messages[0][1][0:4], b"\x00" * 4)
          self.assertIn((0x1E1, 2), [(m[0], m[2]) for m in messages])

  def test_driver_gear_and_paddle_ownership(self):
    for candidate in PEDAL_BOLT_CAR:
      with self.subTest(candidate=candidate):
        cp = params(candidate, True, True)
        controller = CarController(DBC[candidate], cp)
        control = structs.CarControl()
        control.enabled = True
        control.longActive = True
        control.actuators.accel = 1.
        state = structs.CarState()
        state.vEgo = 12.
        state.cruiseState.available = True
        cs = SimpleNamespace(pedal_sensor_healthy=True, pedal_sensor_ts_nanos=950_000_000,
                             stock_acc_status_ts_nanos=950_000_000,
                             bolt_pedal_gear_ts_nanos=950_000_000, bolt_pedal_main_ts_nanos=950_000_000, cam_lka_steering_cmd_counter=0,
                             loopback_lka_steering_cmd_updated=False, loopback_lka_steering_cmd_ts_nanos=1_000_000_000,
                             pt_lka_steering_cmd_counter=0, buttons_counter=0)
        for gear, driver_paddle in ((structs.CarState.GearShifter.park, False),
                                    (structs.CarState.GearShifter.reverse, False),
                                    (structs.CarState.GearShifter.drive, False),
                                    (structs.CarState.GearShifter.manumatic, False),
                                    (structs.CarState.GearShifter.low, True)):
          controller.frame = 4
          state.gearShifter = gear
          state.regenBraking = driver_paddle
          cs.out = state.as_reader()
          _, commands = controller.update(control.as_reader(), cs, 1_000_000_000)
          owned = [msg for msg in commands if msg[0] in (0x200, 0x1F5, 0xBD)]
          self.assertEqual([msg[0] for msg in owned], [0x200])
          if candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL and gear == structs.CarState.GearShifter.drive:
            self.assertGreater(controller.pedal_steady, 0.)
          else:
            self.assertEqual(owned[0][1][0:4], b"\x00" * 4)
        controller.frame = 4
        state.gearShifter = structs.CarState.GearShifter.low
        state.regenBraking = False
        cs.out = state.as_reader()
        _, commands = controller.update(control.as_reader(), cs, 1_000_000_000)
        self.assertEqual([msg[0] for msg in commands if msg[0] in (0x200, 0x1F5, 0xBD)], [0x200, 0x1F5, 0xBD])


class TestBoltPedalStartupParser(unittest.TestCase):
  PT_MESSAGES = {
    'PSCMStatus': 10, 'ESPStatus': 10, 'EBCMWheelSpdFront': 20, 'EBCMWheelSpdRear': 20,
    'EBCMFrictionBrakeStatus': 20, 'PSCMSteeringAngle': 100, 'ECMAcceleratorPos': 80,
    'ECMPRDNL2': 40, 'AcceleratorPedal2': 33, 'ECMEngineStatus': 100, 'BCMTurnSignals': 1,
    'BCMDoorBeltStatus': 10, 'BCMGeneralPlatformStatus': 10, 'ASCMSteeringButton': 33,
    'EBCMRegenPaddle': 40, 'ECMCruiseControl': 10, 'GAS_SENSOR': 50,
  }

  def present_tick(self, ci, native, now, sensor_counter, *, button=None, gear=4, manual=0, main=True,
                   stock=True, driver=0., sensor_state=0, fault=1, loopback=(), omit=(), wrong_bus=None,
                   bad_length=None, healthy=True, acc_cruise=0, camera_stock=False):
    packer = CANPacker(DBC[ci.CP.carFingerprint][Bus.pt])
    values = {
      'PSCMStatus': {'LKADriverAppldTrq': driver, 'LKATorqueDelivered': 0, 'LKATorqueDeliveredStatus': fault},
      'PSCMSteeringAngle': {'SteeringWheelAngle': 0},
      'ECMCruiseControl': {'CruiseActive': int(stock)},
      'AcceleratorPedal2': {'CruiseState': acc_cruise},
      'ECMEngineStatus': {'CruiseMainOn': int(main)},
      'ECMPRDNL2': {'PRNDL2': gear, 'ManualMode': manual}, 'BCMDoorBeltStatus': {'LeftSeatBelt': 1},
      'EBCMWheelSpdFront': {'FLWheelSpd': 72, 'FRWheelSpd': 72},
      'EBCMWheelSpdRear': {'RLWheelSpd': 72, 'RRWheelSpd': 72, 'RLWheelDir': 1, 'RRWheelDir': 1},
    }
    frames = [packer.make_can_msg(name, 1 if name == wrong_bus else 0, values.get(name, {})) for name in self.PT_MESSAGES
              if name not in ('ASCMSteeringButton', 'GAS_SENSOR', *omit)]
    if 'GAS_SENSOR' not in omit:
      frames.append(TestBoltPedalMessages.sensor(packer, 0, sensor_counter % 16, state=sensor_state))
    frames += [packer.make_can_msg('ASCMLKASteeringCmd', 2, {}), packer.make_can_msg('AEBCmd', 2, {})]
    if camera_stock:
      frames.append(packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCruiseState': 2}))
    if bad_length is not None:
      frames = [(address, raw[:-1] if address == bad_length else raw, bus) for address, raw, bus in frames]
    if button is not None:
      frames.append((0x1E1, button, 0))
    native.set_timer(now // 1000)
    from opendbc.safety.tests.libsafety import libsafety_py
    for address, raw, bus in frames:
      self.assertTrue(native.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, raw)), hex(address))
    native.safety_tick()
    state = ci.update([(now, frames + list(loopback))])
    if healthy:
      self.assertTrue(state.canValid)
      self.assertFalse(state.canTimeout)
    self.assertAlmostEqual(state.steeringTorque, driver, places=2)
    self.assertEqual(state.steeringPressed, abs(driver) > 1)
    return state

  def test_present_no_acc_gap_recovers_without_replenishing_duplicate_credit(self):
    from opendbc.car.gm.bolt_cc import button_bytes
    from opendbc.safety.tests.libsafety import libsafety_py
    for identity in NO_ACC_BOLT_CAR:
      for kind in ('neutral', 'nonneutral', 'skipped', 'duplicate'):
        with self.subTest(identity=identity, interrupted=kind):
          cp = params(identity, pedal=True, camera=True)
          native = libsafety_py.libsafety
          self.assertEqual(native.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam), 0)
          native.init_tests()
          ci, _ = self.stream(cp, native=native)
          ci.CC.frame = 100
          first_counter = (ci.CS.conventional_cancel_credit.counter + 1) % 4
          interrupted_counter = (first_counter + {'neutral': 1, 'nonneutral': 1, 'skipped': 3, 'duplicate': 0}[kind]) % 4
          interrupted = button_bytes(2 if kind == 'nonneutral' else 1, interrupted_counter)
          self.assertEqual(ci.CS.conventional_cancel_credit.neutral_interval_ns, 100_000_000)
          command = structs.CarControl()  # Withdrawing stock cruise still works with both axes disabled.
          for tick in range(22):
            now = 3_500_000_000 + tick * 10_000_000
            duplicate = kind == 'duplicate'
            button = {0: button_bytes(1, first_counter), 15: interrupted,
                      18: button_bytes(1, (interrupted[4] + 1) % 4),
                      19: button_bytes(1, (interrupted[4] + 1) % 4)}.get(tick)
            if duplicate and tick == 21:
              button = button_bytes(1, (interrupted[4] + 2) % 4)
            self.present_tick(ci, native, now, 13 + tick, button=button)
            _, messages = ci.apply(command.as_reader(), now)
            cancel = [message for message in messages if message[0] == 0x1E1]
            expected = tick in (0, 21 if duplicate else 18)
            self.assertEqual(bool(cancel), expected, (identity, tick, interrupted.hex()))
            for address, raw, bus in cancel:
              self.assertTrue(native.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, raw)))
              self.assertFalse(native.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, raw)))
            if tick in (15, 19) or tick == 21 and not duplicate:
              counter = ci.CS.conventional_cancel_credit.counter
              self.assertFalse(native.safety_tx_hook(libsafety_py.make_CANPacket(0x1E1, 0, button_bytes(6, (counter + 1) % 4))))
            self.assertFalse(any(message[0] in (0x315, 0x370) for message in messages))

  def test_present_no_acc_raw_withdrawal_and_new_slot_rearm(self):
    from opendbc.car.gm.bolt_cc import button_bytes
    from opendbc.safety.tests.libsafety import libsafety_py
    cases = ('main', 'stock', 'sensor_fault', 'manual', 'wrong_bus_gear', 'short_gear', 'stale_sensor')
    for identity in NO_ACC_BOLT_CAR:
      for failure in cases:
        with self.subTest(identity=identity, failure=failure):
          cp = params(identity, pedal=True, camera=True)
          native = libsafety_py.libsafety
          self.assertEqual(native.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam), 0)
          native.init_tests()
          ci, _ = self.stream(cp, native=native)
          ci.CC.frame = 100
          first_counter = (ci.CS.conventional_cancel_credit.counter + 1) % 4
          gear_stamp = ci.CS.bolt_pedal_gear_ts_nanos
          command = structs.CarControl()
          for tick in range(20):
            now = 3_500_000_000 + tick * 10_000_000
            withdrawn = 1 <= tick <= 13
            options = {}
            if withdrawn:
              options = {'main': failure != 'main', 'stock': failure != 'stock',
                         'sensor_state': int(failure == 'sensor_fault'), 'manual': int(failure == 'manual'),
                         'wrong_bus': 'ECMPRDNL2' if failure == 'wrong_bus_gear' else None,
                         'bad_length': 0x1F5 if failure == 'short_gear' else None,
                         'omit': ('GAS_SENSOR',) if failure == 'stale_sensor' else (), 'healthy': False}
            # A consumed slot cannot revive across withdrawal. The first late slot
            # re-establishes observation; only the next sequential slot grants credit.
            button = {0: button_bytes(1, first_counter), 14: button_bytes(1, (first_counter + 1) % 4),
                      17: button_bytes(1, (first_counter + 2) % 4)}.get(tick)
            state = self.present_tick(ci, native, now, 13 + tick, button=button, **options)
            if tick == 0:
              gear_stamp = ci.CS.bolt_pedal_gear_ts_nanos
            if withdrawn and failure == 'wrong_bus_gear':
              self.assertEqual(ci.CS.bolt_pedal_gear_ts_nanos, gear_stamp, (identity, failure, tick))
            if withdrawn and failure == 'short_gear':
              self.assertEqual(ci.CS.bolt_pedal_gear_ts_nanos, 0, (identity, failure, tick))
            if withdrawn and failure == 'sensor_fault':
              self.assertFalse(ci.CS.pedal_sensor_healthy)
            if withdrawn and failure == 'manual':
              self.assertEqual(state.gearShifter, structs.CarState.GearShifter.manumatic)
            _, messages = ci.apply(command.as_reader(), now)
            cancel = [message for message in messages if message[0] == 0x1E1]
            self.assertEqual(bool(cancel), tick in (0, 17), (identity, failure, tick))
            for address, raw, bus in cancel:
              self.assertTrue(native.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, raw)), (identity, failure, tick))
              self.assertFalse(native.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, raw)))

  def test_present_no_acc_same_batch_valid_gear_retains_only_qualified_clock(self):
    from opendbc.car.gm.bolt_cc import button_bytes
    from opendbc.safety.tests.libsafety import libsafety_py
    for identity in NO_ACC_BOLT_CAR:
      for invalid_first in (False, True):
        with self.subTest(identity=identity, invalid_first=invalid_first):
          cp = params(identity, pedal=True, camera=True)
          safety = libsafety_py.libsafety
          self.assertEqual(safety.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam), 0)
          safety.init_tests()
          ci, _ = self.stream(cp, native=safety)
          ci.CC.frame = 100
          counter = (ci.CS.conventional_cancel_credit.counter + 1) % 4
          now = 3_500_000_000
          self.present_tick(ci, safety, now, 13, button=button_bytes(1, counter))
          gear = CANPacker(DBC[identity][Bus.pt]).make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 4})
          first = (gear[0], gear[1][:-1], gear[2]) if invalid_first else gear
          ci.update([(now, [first, gear])])
          self.assertEqual(ci.CS.bolt_pedal_gear_ts_nanos, 0 if invalid_first else now)
          _, messages = ci.apply(structs.CarControl().as_reader(), now)
          cancel = [message for message in messages if message[0] == 0x1E1]
          self.assertEqual(bool(cancel), not invalid_first)
          for address, raw, bus in cancel:
            self.assertTrue(safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, raw)))
          if not invalid_first:
            # Fresh other inputs and a new neutral lease cannot revive expired gear.
            for sensor_counter, tick in enumerate((11, 13), start=14):
              self.present_tick(ci, safety, now + tick * 10_000_000, sensor_counter, omit=('ECMPRDNL2',),
                                button=button_bytes(1, (counter + (1 if tick == 11 else 2)) % 4))
            ci.update([(now, [gear])])
            self.assertEqual(ci.CS.bolt_pedal_gear_ts_nanos, now)
            self.assertGreater(ci.CS.conventional_cancel_credit.credit_ns, now)
            self.assertTrue(ci.CS.pedal_sensor_healthy)
            _, messages = ci.apply(structs.CarControl().as_reader(), now + 130_000_000)
            self.assertFalse(any(message[0] == 0x1E1 for message in messages))
          ci.update([(now - 1, [gear]), (now, [gear])])
          self.assertEqual(ci.CS.bolt_pedal_gear_ts_nanos, 0)

  def test_present_no_acc_short_gear_cannot_restore_cancel_authority(self):
    from opendbc.car.gm.bolt_cc import button_bytes
    from opendbc.safety.tests.libsafety import libsafety_py
    for identity in NO_ACC_BOLT_CAR:
      for initial in ('expired', 'park', 'manual'):
        for restored_gear in (4, 6):
          with self.subTest(identity=identity, initial=initial, restored_gear=restored_gear):
            cp = params(identity, pedal=True, camera=True)
            native = libsafety_py.libsafety
            self.assertEqual(native.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam), 0)
            native.init_tests()
            ci, _ = self.stream(cp, native=native)
            ci.CC.frame = 100
            command = structs.CarControl()
            first = (ci.CS.conventional_cancel_credit.counter + 1) % 4
            last_tick = 13 if initial == 'expired' else 0
            for tick in range(last_tick + 1):
              now = 3_500_000_000 + tick * 10_000_000
              self.present_tick(ci, native, now, 13 + tick, gear=0 if initial == 'park' else 4,
                                manual=int(initial == 'manual'), button=button_bytes(1, (first + tick) % 4),
                                omit=('ECMPRDNL2',) if tick else (), healthy=tick < 10)
            counter = ci.CS.conventional_cancel_credit.counter
            self.assertFalse(native.safety_tx_hook(libsafety_py.make_CANPacket(0x1E1, 0, button_bytes(6, (counter + 1) % 4))))
            _, messages = ci.apply(command.as_reader(), now)
            self.assertFalse(any(message[0] == 0x1E1 for message in messages))
            for offset, short in ((1, True), (2, False)):
              stamp = now + offset * 1_000_000
              self.present_tick(ci, native, stamp, 14 + last_tick + offset - 1, gear=restored_gear,
                                button=button_bytes(1, (counter + offset) % 4), bad_length=0x1F5 if short else None)
              self.assertEqual(ci.CS.bolt_pedal_gear_ts_nanos, 0 if short else stamp)
              _, messages = ci.apply(command.as_reader(), stamp)
              cancel = [message for message in messages if message[0] == 0x1E1]
              self.assertEqual(bool(cancel), not short, (identity, initial, restored_gear, short))
              candidate = libsafety_py.make_CANPacket(0x1E1, 0, button_bytes(6, (counter + offset + 1) % 4))
              self.assertEqual(bool(native.safety_tx_hook(candidate)), not short)
              if cancel:
                self.assertFalse(native.safety_tx_hook(candidate))

  def test_present_no_acc_signed_steering_sender_and_generation_limits(self):
    from opendbc.car.gm.bolt_cc import button_bytes
    from opendbc.safety.tests.libsafety import libsafety_py
    for identity in NO_ACC_BOLT_CAR:
      for sign in (-1, 1):
        with self.subTest(identity=identity, sign=sign):
          cp = params(identity, pedal=True, camera=True)
          native = libsafety_py.libsafety
          self.assertEqual(native.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam), 0)
          native.init_tests()
          ci, _ = self.stream(cp, native=native)
          self.assertTrue(is_bolt_present_no_acc_pedal_profile(cp))
          limit = 450 if identity == CAR.CHEVROLET_BOLT_CC_2017 else 300
          self.assertEqual(CarControllerParams(cp).STEER_MAX, limit)
          decoder = CANParser(DBC[identity][Bus.pt], [('ASCMLKASteeringCmd', 100)], 0)
          command = structs.CarControl(enabled=True, latActive=True)
          command.actuators.torque = float(sign)
          loopback = []
          torques = []
          for tick in range(150):
            now = 3_500_000_000 + tick * 10_000_000
            state = self.present_tick(ci, native, now, 13 + tick,
                                      button=button_bytes(2 if tick == 0 else 1, (3 + tick) % 4), loopback=loopback)
            self.assertEqual(state.steeringTorque, 0)
            self.assertGreater(state.vEgo, 19)
            self.assertTrue(native.get_controls_allowed())
            _, messages = ci.apply(command.as_reader(), now)
            steering = [message for message in messages if message[0] == 0x180]
            loopback = [(address, raw, 128) for address, raw, _ in steering]
            decoder.update([(now, steering)])
            for address, raw, bus in steering:
              torque = decoder.vl['ASCMLKASteeringCmd']['LKASteeringCmd']
              self.assertNotEqual(torque, 0, (identity, sign, tick))
              self.assertGreater(torque * sign, 0)
              self.assertLessEqual(abs(torque), limit)
              self.assertTrue(native.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, raw)), (identity, sign, tick, torque))
              torques.append(torque)
          self.assertEqual(torques[-1], sign * limit)
          # Physical opposing driver torque clips the actual sender; axis withdrawal then emits neutral.
          for tick in range(150, 162):
            now = 3_500_000_000 + tick * 10_000_000
            self.present_tick(ci, native, now, 13 + tick, driver=-sign * 10., loopback=loopback)
            _, messages = ci.apply(command.as_reader(), now)
            steering = [message for message in messages if message[0] == 0x180]
            loopback = [(address, raw, 128) for address, raw, _ in steering]
            decoder.update([(now, steering)])
            for address, raw, bus in steering:
              self.assertLess(abs(decoder.vl['ASCMLKASteeringCmd']['LKASteeringCmd']), limit)
              self.assertTrue(native.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, raw)))
          for tick in range(162, 183):
            now = 3_500_000_000 + tick * 10_000_000
            state = self.present_tick(ci, native, now, 13 + tick, main=False, fault=3, loopback=loopback)
            self.assertTrue(state.steerFaultPermanent)
            self.assertFalse(state.cruiseState.available)
            command.enabled = command.latActive = command.longActive = False
            _, messages = ci.apply(command.as_reader(), now)
            steering = [message for message in messages if message[0] == 0x180]
            loopback = [(address, raw, 128) for address, raw, _ in steering]
            decoder.update([(now, steering)])
            for address, raw, bus in steering:
              self.assertEqual(decoder.vl['ASCMLKASteeringCmd']['LKASteeringCmd'], 0)
              self.assertTrue(native.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, raw)))

  def stream(self, cp, missing=None, *, blindspot=False, pedal_present=True, camera_present=True, native=None):
    ci = CarInterface(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    pt_messages = dict(self.PT_MESSAGES)
    if blindspot:
      pt_messages['BCMBlindSpotMonitor'] = 10
    if not pedal_present:
      pt_messages.pop('GAS_SENSOR')
    camera = ['ASCMLKASteeringCmd', 'AEBCmd'] if camera_present else []
    if cp.carFingerprint == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
      camera.append('ASCMActiveCruiseControlStatus')
    sensor_counter = 0
    for index in range(250):
      frames = []
      for bus, names in ((0, pt_messages), (2, camera), (128, ['ASCMLKASteeringCmd'])):
        for name in names:
          if (bus, name) == missing:
            continue
          rate = pt_messages[name] if bus == 0 else 25 if name == 'ASCMActiveCruiseControlStatus' else 10
          if index and index * rate // 100 == (index - 1) * rate // 100:
            continue
          if name == 'ASCMSteeringButton':
            from opendbc.car.gm.bolt_cc import button_bytes
            frame = (0x1E1, button_bytes(1, (index * rate // 100) % 4), bus)
          elif name == 'GAS_SENSOR':
            frame = TestBoltPedalMessages.sensor(packer, 0, sensor_counter % 16)
            sensor_counter += 1
          else:
            values = {'PSCMStatus': {'LKADriverAppldTrq': 0, 'LKATorqueDelivered': 0},
                      'PSCMSteeringAngle': {'SteeringWheelAngle': 0},
                      'ECMCruiseControl': {'CruiseSetSpeed': 60, 'CruiseActive': 1},
                      'ASCMActiveCruiseControlStatus': {'ACCSpeedSetpoint': 60, 'ACCCmdActive': 1},
                      'ECMPRDNL2': {'PRNDL2': 4}, 'BCMDoorBeltStatus': {'LeftSeatBelt': 1},
                      'ECMEngineStatus': {'CruiseMainOn': 1}}.get(name, {})
            frame = packer.make_can_msg(name, bus, values)
          frames.append(frame)
      stamp = 1_000_000_000 + index * 10_000_000
      if native is not None:
        from opendbc.safety.tests.libsafety import libsafety_py
        native.set_timer(stamp // 1000)
        for address, data, bus in frames:
          if bus != 128:
            native.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data))
        native.safety_tick()
      result = ci.update([(stamp, frames)])
    return ci, result

  def test_present_no_acc_stock_cancel_uses_real_activity_without_logical_engagement(self):
    from opendbc.car.gm.bolt_cc import button_bytes
    from opendbc.safety.tests.libsafety import libsafety_py
    for identity in NO_ACC_BOLT_CAR:
      with self.subTest(identity=identity):
        cp = params(identity, True, True, camera=True)
        self.assertEqual(cp.safetyConfigs[0].safetyParam, BOLT_PEDAL_WORDS[identity])
        now = 3_490_000_000
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        contexts = [(acceleration, long_active, True) for acceleration in (-1., 0., 1.) for long_active in (False, True)]
        contexts.append((0., False, False))
        for acceleration, long_active, enabled in contexts:
          with self.subTest(acceleration=acceleration, long_active=long_active, enabled=enabled):
            native = libsafety_py.libsafety
            self.assertEqual(native.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam), 0)
            native.init_tests()
            ci, state = self.stream(cp, native=native)
            self.assertTrue(state.canValid)
            self.assertFalse(state.cruiseState.enabled)
            self.assertTrue(ci.CS.bolt_pedal_stock_active)
            native.safety_rx_hook(libsafety_py.make_CANPacket(0x1E1, 0, button_bytes(1, 3)))
            ci.update([(now, [(0x1E1, button_bytes(1, 3), 0)])])
            controller = CarController(DBC[cp.carFingerprint], cp)
            controller.frame = 100
            command = structs.CarControl(enabled=enabled, longActive=long_active)
            command.actuators.accel = acceleration
            _, frames = controller.update(command.as_reader(), ci.CS, now)
            self.assertEqual([frame for frame in frames if frame[0] == 0x1E1],
                             [(0x1E1, button_bytes(6, 0), 0)])
            self.assertTrue(native.safety_tx_hook(libsafety_py.make_CANPacket(0x1E1, 0, button_bytes(6, 0))))
            self.assertFalse(native.safety_tx_hook(libsafety_py.make_CANPacket(0x1E1, 0, button_bytes(6, 0))))
            controller.frame = 101
            _, frames = controller.update(command.as_reader(), ci.CS, now + 10_000_000)
            self.assertFalse(any(frame[0] == 0x1E1 for frame in frames))
            self.assertFalse(any(frame[0] == 0x370 for frame in frames))

            for sample, (delay, stock_active, counter, frame_number, expected) in enumerate((
              (10_000_000, False, 0, 101, False),
              (20_000_000, True, 1, 102, False),
              (50_000_000, True, 2, 105, True),
            )):
              stamp = now + delay
              incoming = [
                packer.make_can_msg("ECMCruiseControl", 0, {"CruiseActive": int(stock_active)}),
                packer.make_can_msg("ECMEngineStatus", 0, {"CruiseMainOn": 1}),
                packer.make_can_msg("ECMPRDNL2", 0, {"PRNDL2": 4}),
                TestBoltPedalMessages.sensor(packer, 0, (13 + sample) % 16),
                (0x1E1, button_bytes(1, counter), 0),
              ]
              native.set_timer(stamp // 1000)
              for address, data, bus in incoming:
                native.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data))
              ci.update([(stamp, incoming)])
              self.assertEqual(ci.CS.bolt_pedal_stock_active, stock_active)
              self.assertFalse(ci.CS.out.cruiseState.enabled)
              controller.frame = frame_number
              _, frames = controller.update(command.as_reader(), ci.CS, stamp)
              cancel = [frame for frame in frames if frame[0] == 0x1E1]
              self.assertEqual(cancel, [(0x1E1, button_bytes(6, 3), 0)] if expected else [])
              if cancel:
                self.assertTrue(native.safety_tx_hook(libsafety_py.make_CANPacket(0x1E1, 0, cancel[0][1])))
            native.set_timer((now + 400_000_000) // 1000)
            self.assertFalse(native.safety_tx_hook(libsafety_py.make_CANPacket(0x1E1, 0, button_bytes(6, 3))))
        for failure in ("main", "stock", "sensor", "can", "credit"):
          with self.subTest(failure=failure):
            ci, _ = self.stream(cp)
            ci.update([(now, [(0x1E1, button_bytes(1, 3), 0)])])
            if failure == "main":
              ci.CS.bolt_pedal_main_ts_nanos = now - 300_000_001
            elif failure == "stock":
              ci.CS.bolt_pedal_stock_ts_nanos = now - 300_000_001
            elif failure == "sensor":
              ci.CS.pedal_sensor_healthy = False
            elif failure == "credit":
              ci.CS.conventional_cancel_credit.credit_ns = now - 100_000_001
            else:
              out = ci.CS.out.as_reader().as_builder()
              out.canValid = False
              ci.CS.out = out.as_reader()
            controller = CarController(DBC[cp.carFingerprint], cp)
            controller.frame = 100
            _, frames = controller.update(command.as_reader(), ci.CS, now)
            self.assertFalse(any(frame[0] == 0x1E1 for frame in frames))

  def test_identification_to_no_acc_pedal_parser(self):
    from opendbc.car.fingerprints import all_legacy_fingerprint_cars, eliminate_incompatible_cars
    from opendbc.car.gm.fingerprints import FINGERPRINTS
    candidate = CAR.CHEVROLET_BOLT_CC_2018_2021
    candidates = all_legacy_fingerprint_cars()
    for address, length in FINGERPRINTS[candidate][0].items():
      candidates = eliminate_incompatible_cars(SimpleNamespace(address=address, dat=bytes(length)), candidates)
    self.assertEqual(candidates, [candidate])
    cp = params(candidates[0], True, True, camera=True)
    ci, state = self.stream(cp)
    self.assertTrue(state.canValid)
    self.assertTrue(ci.CS.pedal_sensor_healthy)
    self.assertEqual(state.gearShifter, structs.CarState.GearShifter.drive)
    self.assertFalse(state.seatbeltUnlatched)
    self.assertFalse(state.doorOpen)
    self.assertAlmostEqual(state.cruiseState.speed, 60 / 3.6, places=5)
    self.assertNotIn('ASCMActiveCruiseControlStatus', ci.can_parsers[Bus.cam].vl)
    by_name = {message.name: message.frequency for message in ci.can_parsers[Bus.pt].message_states.values()}
    optional = {'ASCMLKASteeringCmd', 'TCICOnStarGPSPosition'}
    self.assertEqual({name: rate for name, rate in by_name.items() if name not in optional}, self.PT_MESSAGES)
    gps = next(message for message in ci.can_parsers[Bus.pt].message_states.values() if message.name == 'TCICOnStarGPSPosition')
    self.assertTrue(gps.ignore_alive)
    steering_counter = next(message for message in ci.can_parsers[Bus.pt].message_states.values()
                            if message.name == 'ASCMLKASteeringCmd')
    self.assertTrue(steering_counter.ignore_alive)

  def test_active_and_saved_disabled_pedal_profiles(self):
    from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
    for candidate in (CAR.CHEVROLET_BOLT_CC_2018_2021, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL):
      for alpha in (False, True):
        for disabled in (False, True):
          with self.subTest(candidate=candidate, alpha=alpha, disabled=disabled):
            cp = params(candidate, True, True, alpha_long=alpha, camera=True)
            if disabled:
              VehicleStartupPreferences(disable_bolt_long=True).prepare(cp, fingerprints={2: {0x180: 4}})
            ci, state = self.stream(cp)
            self.assertTrue(state.canValid)
            self.assertTrue(ci.CS.pedal_sensor_healthy)
            self.assertEqual(state.gearShifter, structs.CarState.GearShifter.drive)
            self.assertEqual('ASCMActiveCruiseControlStatus' in ci.can_parsers[Bus.cam].vl,
                             candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)

  def test_missing_required_sources_stay_invalid(self):
    for candidate in (CAR.CHEVROLET_BOLT_CC_2018_2021, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL):
      missing_sources = [(0, 'GAS_SENSOR'), (0, 'ECMPRDNL2'), (2, 'ASCMLKASteeringCmd')]
      if candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL:
        missing_sources.append((2, 'ASCMActiveCruiseControlStatus'))
      for missing in missing_sources:
        with self.subTest(candidate=candidate, missing=missing):
          cp = params(candidate, True, True, camera=True)
          ci, state = self.stream(cp, missing)
          self.assertFalse(state.canValid)
          if missing == (0, 'GAS_SENSOR'):
            self.assertFalse(ci.CS.pedal_sensor_healthy)


class TestBoltPaddleModes(unittest.TestCase):
  def test_hidden_mode_binds_only_to_actual_active_pedal_owners(self):
    import os
    from unittest.mock import patch
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.starpilot.aol.tests.test_gm import TestGmAol

    for candidate in PEDAL_BOLT_CAR:
      for observed, disabled in ((False, False), (True, True)):
        with self.subTest(candidate=candidate, observed=observed, disabled=disabled), OpenpilotPrefix(), \
             patch.dict(os.environ, {'SIMULATION': '1'}):
          settings = Params()
          settings.put('LongitudinalManeuverPaddleMode', 'force', block=True)
          settings.put_bool('DisableOpenpilotLongitudinal', disabled, block=True)
          card = TestGmAol.card(params(candidate, pedal=observed, camera=True), settings)
          self.assertIsNone(card.CI.CC.maneuver_paddle_input)
          self.assertEqual(card.CI.CC.maneuver_paddle_mode, 'auto')

  def test_saved_modes_cross_actual_card_parser_and_native_scheduler(self):
    import os
    from unittest.mock import patch
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.starpilot.aol.tests.test_gm import TestGmAol
    from opendbc.car.gm.bolt_cc import button_bytes
    from opendbc.safety.tests.libsafety import libsafety_py
    from opendbc.safety.tests.test_gm_bolt_pedal import TestGmBoltPedalSafety

    for candidate in PEDAL_BOLT_CAR:
      with self.subTest(candidate=candidate), OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        settings = Params()
        card = TestGmAol.card(params(candidate, pedal=True, camera=True), settings)
        ci, cp = card.CI, card.CP
        self.assertIsNotNone(ci.CC.maneuver_paddle_input)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        safety = libsafety_py.libsafety
        self.assertEqual(safety.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam), 0)
        safety.init_tests()
        recorder = TestGmBoltPedalSafety()
        recorder.safety = safety
        control = structs.CarControl()
        control.actuators.accel = -.5
        counter = 0
        observed = set()
        last_feeds = {}
        mode = 'auto'
        for tick in range(875):
          now = 1_000_000_000 + tick * 10_000_000
          safety.set_timer(now // 1000)
          if tick in (251, 326, 426, 526):
            mode = {251: 'force', 326: 'off', 426: 'auto', 526: 'force'}[tick]
            settings.put('LongitudinalManeuverPaddleMode', mode, block=True)
          live = {675: ('OpenpilotEnabledToggle', False), 700: ('OpenpilotEnabledToggle', True),
                  725: ('SafeMode', True), 750: ('SafeMode', False),
                  775: ('DisableOpenpilotLongitudinal', True), 800: ('DisableOpenpilotLongitudinal', False),
                  825: ('LongitudinalManeuverPaddleMode', 'garbage'),
                  850: ('LongitudinalManeuverPaddleMode', ' FoRcE ')}
          if tick in live:
            settings.put(*live[tick], block=True)
          fallback = any(start <= tick < start + 25 for start in (675, 725, 775, 825))
          control.actuators.accel = .35 if fallback else -.5
          control.enabled = tick >= 250
          control.longActive = tick >= 250
          withdrawals = {576: 'gas', 586: 'brake', 596: 'regen', 606: 'gear', 616: 'main', 626: 'sensor', 636: 'stock'}
          override = next((value for start, value in withdrawals.items() if start <= tick < start + 4), None)
          if override in ('brake', 'regen'):
            control.enabled = control.longActive = False
          values = {
            'ECMEngineStatus': {'CruiseMainOn': int(override != 'main'), 'BrakePressed': int(override == 'brake')},
            'ECMPRDNL2': {'PRNDL2': 3 if override == 'gear' else 6},
            'AcceleratorPedal2': {'AcceleratorPedal2': 30 if override == 'gas' else 0,
                                 'CruiseState': int(override == 'stock')},
            'ECMAcceleratorPos': {'BrakePedalPos': 12 if override == 'brake' else 0},
            'EBCMRegenPaddle': {'RegenPaddle': int(override == 'regen')},
            'EBCMWheelSpdRear': {'RLWheelSpd': 43.2, 'RRWheelSpd': 43.2},
            'EBCMWheelSpdFront': {'FLWheelSpd': 43.2, 'FRWheelSpd': 43.2},
            'BCMDoorBeltStatus': {'LeftSeatBelt': 1},
            'ASCMActiveCruiseControlStatus': {'ACCCmdActive': int(override == 'stock')},
          }
          frames = [packer.make_can_msg(name, 0, values.get(name, {}))
                    for name in TestBoltPedalStartupParser.PT_MESSAGES if name not in ('GAS_SENSOR', 'ASCMSteeringButton')]
          if tick % 2 == 0:
            frames.append(TestBoltPedalMessages.sensor(packer, 30 if override == 'gas' else 0, counter % 16, state=int(override == 'sensor')))
            counter += 1
          # Every withdrawal is followed by physical SET press/release before positive commands resume.
          buttons = 3 if tick in (248, *(start + 4 for start in withdrawals)) else 1
          if buttons == 3:
            control.enabled = control.longActive = False
          frames.append((0x1E1, button_bytes(buttons, tick % 4), 0))
          frames.extend(packer.make_can_msg(name, 2, values.get(name, {})) for name in
                        ('ASCMLKASteeringCmd', 'AEBCmd', 'ASCMActiveCruiseControlStatus'))
          frames.append(packer.make_can_msg('ASCMLKASteeringCmd', 128, {}))
          safety.reset_recorded_can()
          for frame in sorted(frames, key=lambda frame: frame[0] in (0x1F5, 0xBD)):
            if frame[2] != 128:
              safety.safety_rx_hook(recorder.packet(frame))
          all_recorded = recorder.recorded()
          statuses = [packet for packet in all_recorded if packet[0] == 0x3D1]
          recorded = [packet for packet in all_recorded if packet[0] != 0x3D1]
          for address, bus, payload in statuses:
            self.assertIn(candidate, NO_ACC_BOLT_CAR)
            self.assertEqual(bus, 0)
            self.assertEqual(payload, last_feeds[address])
            self.assertEqual((payload[0], payload[1], *payload[4:]), (1, 0, 0, 0, 0, 0))
            self.assertEqual(payload[2] & 0xF0, 0)
          if tick in (277, 353):
            expected_pressed = tick == 277
            self.assertEqual({address for address, _, _ in recorded}, {0xBD, 0x1F5})
            for address, _, payload in recorded:
              if address == 0xBD:
                self.assertEqual(payload[0], 0x20 if expected_pressed else 0)
              else:
                self.assertEqual((payload[3], payload[5]),
                                 ((5 if candidate in (CAR.CHEVROLET_BOLT_CC_2022_2023,
                                                      CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL) else 7), 2)
                                 if expected_pressed else (6, 0))
          if override is not None and (override not in ('main', 'stock') or candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL):
            self.assertFalse(any(payload[0] == 0x20 if address == 0xBD else payload[5] == 2
                                 for address, _, payload in recorded))
          for address, bus, payload in recorded:
            self.assertEqual(bus, 0)
            self.assertEqual(payload, last_feeds[address])
          state = ci.update([(now, frames)])
          if tick >= 250:
            self.assertTrue(state.canValid)
          _, messages = ci.apply(control.as_reader(), now)
          expected_mode = ('auto' if tick < 275 else 'force' if tick < 350 else 'off' if tick < 450 else
                           'auto' if tick < 550 or fallback else 'force')
          self.assertEqual(ci.CC.maneuver_paddle_mode, expected_mode)
          if tick >= 250:
            observed.add(expected_mode)
          if fallback and tick % 4 == 0:
            self.assertGreater(ci.CC.pedal_steady, 0.)  # Selection falls back to auto; physical authority is unchanged.
          for message in messages:
            allowed = safety.safety_tx_hook(recorder.packet(message))
            if message[0] in (0xBD, 0x1F5, 0x3D1):
              self.assertFalse(allowed)  # Host feed is consumed; only the internal scheduler may transmit.
              last_feeds[message[0]] = message[1]
              if tick in (276, 352) and message[0] == 0xBD:
                self.assertEqual(message[1][0], 0x20 if tick == 276 else 0)
            else:
              self.assertTrue(allowed, (candidate, tick, hex(message[0])))
          if override is not None and tick % 4 == 0 and (override not in ('main', 'stock') or
                                                      candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL):
            self.assertFalse(ci.CC.regen_paddle_pressed, (tick, override))
            self.assertEqual(ci.CC.pedal_steady, 0., (tick, override))
        self.assertEqual(observed, {'auto', 'off', 'force'})


class TestCruiseStatus(unittest.TestCase):
  def test_exact_helper_payload(self):
    from opendbc.car.gm import gmcan
    packer = CANPacker("gm_global_a_powertrain_generated")
    for speed, raw in ((0., 0), (80., 1280), (10000., 4095), (-1., 0), (float("nan"), 0)):
      frame = gmcan.create_ecm_cruise_control_command(packer, 0, True, speed)
      self.assertEqual(frame, (0x3D1, bytes((1, 0, raw >> 8, raw & 255, 0, 0, 0, 0)), 0))
    self.assertEqual(gmcan.create_ecm_cruise_control_command(packer, 0, False, 80.)[1],
                     bytes((1, 0, 0, 0, 0, 0, 0, 0)))

  def test_actual_parser_controller_status_cadence_and_owner_scope(self):
    from opendbc.car.gm.bolt_cc import button_bytes
    from opendbc.safety.tests.libsafety import libsafety_py
    from opendbc.safety.tests.test_gm_bolt_pedal import TestGmBoltPedalSafety
    helper = TestBoltPedalStartupParser()
    native = libsafety_py.libsafety
    recorder = TestGmBoltPedalSafety()
    recorder.safety = native
    for identity in PEDAL_BOLT_CAR:
      for removed in (False, True):
        with self.subTest(identity=identity, removed=removed):
          cp = params(identity, pedal=True, camera=not removed, removed=removed)
          self.assertEqual(native.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw,
                                                  cp.safetyConfigs[0].safetyParam), 0)
          native.init_tests()
          ci, _ = helper.stream(cp, native=native, camera_present=not removed)
          control = structs.CarControl()
          control.hudControl.setSpeed = 80. / 3.6
          captured = []
          packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
          for tick in range(16):
            now = 3_500_000_000 + tick * 10_000_000
            helper.present_tick(ci, native, now, tick, button=button_bytes(1, tick % 4), gear=6)
            ci.CC.frame = 104 + tick
            _, messages = ci.apply(control.as_reader(), now)
            statuses = [message for message in messages if message[0] == 0x3D1]
            expected = identity in NO_ACC_BOLT_CAR and tick % 4 == 0
            self.assertEqual(bool(statuses), expected)
            if expected:
              self.assertEqual(statuses, [(0x3D1, bytes((1, 0, 5, 0, 0, 0, 0, 0)), 0)])
              self.assertFalse(native.safety_tx_hook(recorder.packet(statuses[0])))
              native.reset_recorded_can()
              native.set_timer(now // 1000 + 1)
              self.assertEqual(native.safety_fwd_hook(0, 0x3D1), -1)
              raw = packer.make_can_msg('ECMCruiseControl', 0, {'CruiseActive': 1})
              self.assertTrue(native.safety_rx_hook(recorder.packet(raw)))
              self.assertEqual(recorder.recorded(), [(0x3D1, 0, statuses[0][1])])
              captured.extend(recorder.recorded())
          self.assertEqual(len(captured), 4 if identity in NO_ACC_BOLT_CAR else 0)
