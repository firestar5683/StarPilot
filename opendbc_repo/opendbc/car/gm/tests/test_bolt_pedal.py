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
