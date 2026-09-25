from unittest.mock import patch
import unittest
from types import SimpleNamespace

from opendbc.can import CANPacker

from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.gmcan import pedal_crc
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR, DBC, GMFlags, GMSafetyFlags, NO_ACC_BOLT_CAR, PEDAL_BOLT_CAR, BOLT_CC_WORDS


class SavedPedalSetting:
  def __init__(self, enabled=False, missing=False):
    self.enabled = enabled
    self.missing = missing

  def get_bool(self, key):
    assert key == "GMPedalLongitudinal"
    if self.missing:
      from openpilot.common.params import UnknownKeyName
      raise UnknownKeyName(key)
    return self.enabled


def params(candidate, setting=False, pedal=False, alpha_long=False, missing_key=False, camera=False):
  fingerprint = gen_empty_fingerprint()
  if camera:
    fingerprint[2][0x180] = 4
  if pedal:
    fingerprint[0][0x201] = 6
  with patch("opendbc.car.gm.interface.Params", return_value=SavedPedalSetting(setting, missing_key)):
    return CarInterface.get_params(candidate, fingerprint, [], alpha_long, False, False)


class TestBoltPedalIdentity(unittest.TestCase):
  def test_pedal_requires_platform_observation_and_saved_opt_in(self):
    for candidate in PEDAL_BOLT_CAR:
      with self.subTest(candidate=candidate):
        for setting, observed, missing in ((False, True, False), (True, False, False), (False, True, True)):
          cp = params(candidate, setting, observed, alpha_long=True, missing_key=missing)
          self.assertTrue(cp.openpilotLongitudinalControl)
          self.assertFalse(cp.flags & GMFlags.PEDAL_LONG.value)
          self.assertFalse(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.PEDAL_LONG.value)

        cp = params(candidate, True, True)
        self.assertTrue(cp.openpilotLongitudinalControl)
        self.assertTrue(cp.flags & GMFlags.PEDAL_LONG.value)
        self.assertTrue(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.PEDAL_LONG.value)
        self.assertFalse(cp.pcmCruise)

  def test_ordinary_cruise_ownership_is_never_stock_acc(self):
    for candidate in NO_ACC_BOLT_CAR:
      for enabled in (False, True):
        with self.subTest(candidate=candidate, enabled=enabled):
          cp = params(candidate, enabled, True)
          self.assertFalse(cp.pcmCruise)
          if enabled:
            self.assertTrue(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.NO_ACC.value)
            self.assertFalse(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.BOLT_ACC_PEDAL.value)
          else:
            self.assertEqual(cp.safetyConfigs[0].safetyParam, BOLT_CC_WORDS[candidate][1])
            self.assertTrue(cp.flags & GMFlags.CC_LONG.value)

  def test_existing_bolt_stock_acc_is_unaffected_by_pedal_setting(self):
    without = params(CAR.CHEVROLET_BOLT_EUV, False, True)
    with_setting = params(CAR.CHEVROLET_BOLT_EUV, True, True)
    self.assertEqual(without.openpilotLongitudinalControl, with_setting.openpilotLongitudinalControl)
    self.assertEqual(without.pcmCruise, with_setting.pcmCruise)
    self.assertEqual(without.safetyConfigs[0].safetyParam, with_setting.safetyConfigs[0].safetyParam)
    self.assertFalse(with_setting.flags & GMFlags.PEDAL_LONG.value)

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
