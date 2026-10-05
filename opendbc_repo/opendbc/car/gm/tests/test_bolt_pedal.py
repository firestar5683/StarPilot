import unittest
from types import SimpleNamespace

from opendbc.can import CANPacker

from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.gmcan import pedal_crc
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR, DBC, GMFlags, GMSafetyFlags, NO_ACC_BOLT_CAR, PEDAL_BOLT_CAR


def params(candidate, setting=False, pedal=False, alpha_long=False, missing_key=False, camera=False):
  fingerprint = gen_empty_fingerprint()
  if camera:
    fingerprint[2][0x180] = 4
  if pedal:
    fingerprint[0][0x201] = 6
  return CarInterface.get_params(candidate, fingerprint, [], alpha_long, False, False)


class TestBoltPedalIdentity(unittest.TestCase):
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

        for counter, kwargs in ((9, {"state": 1}), (10, {"other_track": 40.}), (11, {"bad_crc": True})):
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
                             cam_lka_steering_cmd_counter=0, loopback_lka_steering_cmd_updated=False,
                             loopback_lka_steering_cmd_ts_nanos=1_000_000_000, pt_lka_steering_cmd_counter=0,
                             buttons_counter=0)
        _, messages = controller.update(control.as_reader(), cs, 1_000_000_000)
        expected = [0x200, 0x1F5, 0xBD]
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
        self.assertEqual(messages[0][1][0:4], b"\x00" * 4)
        self.assertEqual(messages[1][1], b"\x0c\x0c\x00\x06\x00\x00\x01\x00")
        self.assertEqual(messages[2][1], b"\x00" * 7)
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
                             stock_acc_status_ts_nanos=950_000_000, cam_lka_steering_cmd_counter=0,
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

  def stream(self, cp, missing=None, *, blindspot=False, pedal_present=True, camera_present=True):
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
          if name == 'GAS_SENSOR':
            frame = TestBoltPedalMessages.sensor(packer, 0, sensor_counter % 16)
            sensor_counter += 1
          else:
            values = {'ECMCruiseControl': {'CruiseSetSpeed': 60, 'CruiseActive': 1},
                      'ASCMActiveCruiseControlStatus': {'ACCSpeedSetpoint': 60, 'ACCCmdActive': 1},
                      'ECMPRDNL2': {'PRNDL2': 4}, 'BCMDoorBeltStatus': {'LeftSeatBelt': 1},
                      'ECMEngineStatus': {'CruiseMainOn': 1}}.get(name, {})
            frame = packer.make_can_msg(name, bus, values)
          frames.append(frame)
      result = ci.update([(1_000_000_000 + index * 10_000_000, frames)])
    return ci, result

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
    self.assertEqual({name: rate for name, rate in by_name.items() if name != 'ASCMLKASteeringCmd'}, self.PT_MESSAGES)
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
          values = {
            'ECMEngineStatus': {'CruiseMainOn': int(override != 'main'), 'BrakePressed': int(override == 'brake')},
            'ECMPRDNL2': {'PRNDL2': 4 if override == 'gear' else 6},
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
          recorded = recorder.recorded()
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
            if message[0] in (0xBD, 0x1F5):
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
