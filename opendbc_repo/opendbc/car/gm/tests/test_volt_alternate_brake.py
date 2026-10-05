"""Gateway Volt brake source and friction routing remain one configuration."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.longitudinal import volt_policy_for
from opendbc.car.gm.profiles import profiles_supported
from opendbc.car.gm.tests.test_bolt_volt_configurations import controller_messages, ordinary_params
from opendbc.car.gm.values import CAR, DBC, GMSafetyFlags, is_volt_gateway_alternate_brake


class TestVoltAlternateBrake(unittest.TestCase):
  def test_auto_hold_actual_gateway_parser_controller_native(self):
    from itertools import product
    for accelerator, alternative in product((True, False), (0, 32)):
      cp = ordinary_params(CAR.CHEVROLET_VOLT, radar=True, accelerator=accelerator)
      self._auto_hold_join(cp, accelerator=accelerator, alternative=alternative,
                           expected_word=0x4084 if accelerator else 0xC084)

  def test_auto_hold_actual_ascm_camera_parser_controller_native(self):
    from itertools import product
    from opendbc.car.gm.tests.test_ascm_intercept import params as ascm_params
    from opendbc.car.gm.tests.test_volt_camera_control import camera_params
    from opendbc.car import structs
    from opendbc.safety.tests.libsafety import libsafety_py
    from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
    release = libsafety_py.libsafety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    cases = [(ascm_params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, accelerator=accelerator,
                          radar=radar, release=release), accelerator, False)
             for accelerator, radar in product((True, False), (False, True))]
    cases += [(camera_params(radar=radar, release=release), True, True) for radar in (False, True)]
    for cp, accelerator, camera in cases:
      for alternative in (0, 32):
        candidate = cp.as_reader().as_builder()
        expected_word = int(cp.safetyConfigs[0].safetyParam) | 0x80
        if release:
          VehicleStartupPreferences(gm_auto_hold=True).prepare(candidate)
          self.assertFalse(candidate.openpilotLongitudinalControl)
          self.assertEqual(candidate.safetyConfigs[0].safetyParam, cp.safetyConfigs[0].safetyParam)
          self._hold_release_factory(candidate, camera=camera, alternative=alternative)
        else:
          self._auto_hold_join(candidate, accelerator=accelerator, alternative=alternative,
                               expected_word=expected_word, camera=camera)

  def test_auto_hold_actual_sdgm_parser_controller_native(self):
    from itertools import product
    from opendbc.car import structs
    from opendbc.car.gm.tests.test_volt_sdgm_control import sdgm_params
    from opendbc.safety.tests.libsafety import libsafety_py
    from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
    release = libsafety_py.libsafety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    for brake_c9, alternative in product((False, True), (0, 32)):
      cp = sdgm_params(brake_c9=brake_c9, radar=True, release=release)
      base_word = int(cp.safetyConfigs[0].safetyParam)
      if release:
        VehicleStartupPreferences(gm_auto_hold=True).prepare(cp)
        self.assertFalse(cp.openpilotLongitudinalControl)
        self.assertEqual(cp.safetyConfigs[0].safetyParam, base_word)
        self._hold_release_factory(cp, camera=True, alternative=alternative)
      else:
        self._auto_hold_join(cp, accelerator=not brake_c9, alternative=alternative,
                             expected_word=0x5487 if brake_c9 else 0x5087)
        denied = cp.as_reader().as_builder()  # Withdraw the actual already-prepared hold selector.
        preferences = VehicleStartupPreferences(gm_auto_hold=True, disable_bolt_long=True)
        preferences.prepare(denied)
        preferences.finalize(denied)
        self.assertEqual(denied.safetyConfigs[0].safetyParam, 0x1405 if brake_c9 else 0x1005)
        self.assertFalse(denied.openpilotLongitudinalControl)
        self.assertTrue(denied.pcmCruise)
        self._hold_release_factory(denied, camera=True, alternative=alternative)

  def _hold_release_factory(self, cp, *, camera, alternative):
    from types import SimpleNamespace
    from opendbc.car import structs
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm import gmcan
    from opendbc.car.gm.tests.test_bolt_cc import feed, setup, native
    from opendbc.safety.tests.libsafety import libsafety_py
    from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
    with self.subTest(identity=cp.carFingerprint, word=cp.safetyConfigs[0].safetyParam, alternative=alternative):
      cp.alternativeExperience = alternative
      ci = CarInterface(cp)
      VehicleStartupPreferences(gm_auto_hold=True).configure_controller(ci)
      self.assertFalse(ci.CC.gm_auto_hold)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      setup(cp)
      libsafety_py.libsafety.set_alternative_experience(alternative)
      libsafety_py.libsafety.set_safety_hooks(int(structs.CarParams.SafetyModel.gm), cp.safetyConfigs[0].safetyParam)
      for tick in range(40):
        now = 1_000_000_000 + tick * 10_000_000
        _, rx = feed(SimpleNamespace(update=lambda _: None), packer, now, speed=0., camera=True)
        rx.append(packer.make_can_msg("ASCMActiveCruiseControlStatus", 2, {"ACCCruiseState": 3}))
        ci.update([(now - 1_000_000, rx)])
        self.assertTrue(ci.update([(now, rx)]).canValid)
        for message in rx:
          native("rx", message, now // 1000)
        libsafety_py.libsafety.safety_tick()
        if alternative:
          libsafety_py.libsafety.set_aol_test_heartbeat(True)
          libsafety_py.libsafety.aol_set_host_request(1)
        _, commands = ci.apply(structs.CarControl(enabled=True, longActive=True).as_reader(), now)
        self.assertFalse(any(message[0] in (0x315, 0x2CB) for message in commands))
        for message in commands:
          self.assertTrue(native("tx", message, now // 1000), message)
      brake_packer = CANPacker(DBC[cp.carFingerprint][Bus.chassis])
      positive = gmcan.create_friction_brake_command(brake_packer, 2 if cp.carFingerprint == CAR.CHEVROLET_VOLT_2019 else 0,
                                                    100 if cp.carFingerprint == CAR.CHEVROLET_VOLT_2019 else 80,
                                                    1, False, True, False, cp, auto_hold=True)
      self.assertFalse(native("tx", positive, now // 1000))
      libsafety_py.libsafety.set_alternative_experience(0)

  def _auto_hold_join(self, cp, *, accelerator, alternative, expected_word, camera=False):
    from tempfile import TemporaryDirectory
    from types import SimpleNamespace
    from opendbc.car import structs
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.tests.test_bolt_cc import feed, setup, native
    from opendbc.safety.tests.libsafety import libsafety_py
    from openpilot.common.params import Params
    from openpilot.starpilot.controller_extensions import configure_controller
    from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences

    with self.subTest(identity=cp.carFingerprint, word=expected_word, alternative=alternative), TemporaryDirectory() as directory:
      params = Params(directory)
      params.put_bool("OpenpilotEnabledToggle", True, block=True)
      params.put_bool("GMAutoHold", True, block=True)
      preferences = VehicleStartupPreferences.read(params, enabled=True)
      cp.alternativeExperience = alternative
      preferences.prepare(cp)
      preferences.finalize(cp)
      self.assertEqual(cp.safetyConfigs[0].safetyParam, expected_word)
      from opendbc.car.gm.aol import qualified_gm
      from opendbc.car.gm.lateral import lane_centering_supported
      self.assertTrue(qualified_gm(cp))
      self.assertTrue(lane_centering_supported(cp))
      ci = CarInterface(cp)
      preferences.configure_controller(ci)
      configure_controller(ci, params)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      setup(cp)
      libsafety_py.libsafety.set_alternative_experience(alternative)
      self.assertEqual(libsafety_py.libsafety.set_safety_hooks(int(structs.CarParams.SafetyModel.gm), cp.safetyConfigs[0].safetyParam), 0)
      from openpilot.selfdrive.car.car_events import CarEvents, EventName
      events = CarEvents(cp)
      sdgm = cp.carFingerprint == CAR.CHEVROLET_VOLT_2019
      seen_retained = seen_normal_credit_withdrawn = False
      seen_hold = seen_near_stop = seen_normal = seen_feedback = False
      last_sent_hold = False
      for tick in range(1570 if camera else 1000):
        now = 1_000_000_000 + tick * 10_000_000
        moving = (tick < 309 and not 290 <= tick < 300) or 320 <= tick < 340 or 540 <= tick < 870 or 1000 <= tick < 1350
        regen = 360 <= tick < 370
        unavailable = 490 <= tick < 500
        gas = 470 <= tick < 480
        unknown_gear = 480 <= tick < 490
        stale_brake_status = 920 <= tick < 960
        main_off = 910 <= tick < 915
        camera_missing = camera and 1400 <= tick < 1550
        if tick == 500:
          params.put_bool("GMAutoHold", False, block=True)
        if tick == 540:
          params.put_bool("GMAutoHold", True, block=True)
        normal_long = 881 <= tick < 900
        raw_wheel = 28 if sdgm and tick == 348 else 29 if sdgm and tick == 352 else (
          20 if sdgm and (349 <= tick < 352 or 353 <= tick < 360 or 900 <= tick < 910) else None)
        speed = raw_wheel * .0311 / 3.6 if raw_wheel is not None else 2. if moving else 0.
        _, rx = feed(SimpleNamespace(update=lambda _: None), packer, now, speed=speed,
                     brake=not moving and not 880 <= tick < 900, gas=gas, regen=regen,
                     camera=cp.networkLocation == structs.CarParams.NetworkLocation.fwdCamera and not camera_missing)
        rx = [message for message in rx if message[0] not in (0xBE, 0xF1, 0x1C4, 0x232, 0x1E1, 0x1F5, 0xC9)]
        brake_name, brake_signal = (("ECMAcceleratorPos", "BrakePedalPos") if accelerator else
                                    ("EBCMBrakePedalPosition", "BrakePedalPosition"))
        rx += [packer.make_can_msg(brake_name, 0, {brake_signal: 20 if not moving and not 880 <= tick < 900 else 0}),
               packer.make_can_msg("AcceleratorPedal2", 0, {"CruiseState": 2 if moving or 880 <= tick < (920 if sdgm else 910) else 4,
                                                                        "AcceleratorPedal2": 30 if gas else 0}),
               packer.make_can_msg("EBCMFrictionBrakeStatus", 0, {"FrictionBrakeUnavailable": int(unavailable)}),
               packer.make_can_msg("ASCMSteeringButton", 0, {"ACCButtons": 3 if tick == 880 else 6 if tick == 900 else 1, "RollingCounter": tick % 4})]
        nonselected_c9 = cp.carFingerprint in (CAR.CHEVROLET_VOLT_ASCM, CAR.CHEVROLET_VOLT_2019) and accelerator
        rx.append(packer.make_can_msg("ECMEngineStatus", 0, {"CruiseMainOn": int(not main_off),
                                                                   "BrakePressed": int(not moving and not 880 <= tick < 900 and
                                                                                       not nonselected_c9)}))
        rx.append(packer.make_can_msg("ECMPRDNL2", 0, {"PRNDL2": 8 if unknown_gear else 4,
                                                      "ManualMode": int(unknown_gear)}))
        if not accelerator and cp.carFingerprint in (CAR.CHEVROLET_VOLT_ASCM, CAR.CHEVROLET_VOLT_2019):
          rx = [message for message in rx if message[0] != 0xF1]
          rx.append(packer.make_can_msg("ECMAcceleratorPos", 0, {"BrakePedalPos": 200}))
        if camera:
          rx = [message for message in rx if message[0] != 0xBE]
          rx.append(packer.make_can_msg("ECMAcceleratorPos", 0, {"BrakePedalPos": 20 if not moving else 0}))
        if cp.networkLocation == structs.CarParams.NetworkLocation.fwdCamera and not camera_missing:
          rx.append(packer.make_can_msg("ASCMActiveCruiseControlStatus", 2, {"ACCCruiseState": 3, "ACCSpeedSetpoint": 60}))
        if stale_brake_status:
          rx = [message for message in rx if message[0] != 0x232]
        ci.update([(now - 1_000_000, rx)])
        out = ci.update([(now, rx)])
        self.assertEqual(out.brakePressed, not moving and not 880 <= tick < 900)
        if raw_wheel is not None:
          self.assertAlmostEqual(out.wheelSpeeds.rl, speed, places=6)
          self.assertAlmostEqual(out.wheelSpeeds.rr, speed, places=6)
          self.assertGreater(out.wheelSpeeds.rl, 0.)
        if not stale_brake_status and not camera_missing:
          self.assertTrue(out.canValid, tick)
          self.assertFalse(out.canTimeout)
        if camera and 1510 <= tick < 1550:
          self.assertFalse(out.canValid)
        if unavailable:
          self.assertTrue(out.accFaulted)
        physical_withdrawal = (moving or regen or unavailable or gas or unknown_gear or main_off or
                               950 <= tick < 960 or camera and 1510 <= tick < 1550)
        if physical_withdrawal or not out.standstill:
          self.assertFalse(out.brakeHoldActive)
        elif (last_sent_hold and not normal_long and not 500 <= tick < 540 and out.canValid and
              out.standstill and ci.CS.gm_auto_hold_forward):
          self.assertTrue(out.brakeHoldActive, (tick, ci.CS.gm_auto_hold_engaged, out.cruiseState.available, ci.CS.gm_auto_hold_sources))
          seen_feedback = True
        common = events.create_common_events(out, out)
        self.assertEqual(EventName.brakeHold in common.names, out.brakeHoldActive)
        for message in rx:
          native("rx", message, now // 1000)
        libsafety_py.libsafety.safety_tick()
        if alternative:
          libsafety_py.libsafety.set_aol_test_heartbeat(True)
          libsafety_py.libsafety.aol_set_host_request(3 if normal_long else 1)
        self.assertEqual(bool(libsafety_py.libsafety.get_controls_allowed()), normal_long)
        cc = structs.CarControl(enabled=normal_long, longActive=normal_long)
        _, commands = ci.apply(cc.as_reader(), now)
        for message in commands:
          self.assertTrue(native("tx", message, now // 1000), (tick, message))
        brakes = [message for message in commands if message[0] == 0x315]
        self.assertLessEqual(len(brakes), 1)
        if not brakes:
          continue
        mode = brakes[0][1][0] >> 4
        hold = mode in (0xA, 0xB, 0xD) and not normal_long
        last_sent_hold = hold
        if normal_long:
          seen_normal = True
          self.assertTrue(any(message[0] == 0x2CB for message in commands))
          self.assertFalse(ci.CC.gm_auto_hold_state.engaged)
        if 900 <= tick < 910 and not sdgm or sdgm and 915 <= tick < 920:
          self.assertEqual(mode, 0xB)
          seen_near_stop = True
        if sdgm and tick == 348:
          self.assertTrue(hold, (tick, out.vEgo, out.wheelSpeeds.rl, ci.CS.gm_auto_hold_engaged))
          self.assertFalse(out.brakeHoldActive)
          seen_retained = True
        if sdgm and 352 <= tick < 360:
          self.assertFalse(hold)
        if sdgm and 900 <= tick < 910:
          self.assertFalse(hold)
          seen_normal_credit_withdrawn = True
        if hold:
          self.assertEqual(brakes[0][2], 2 if sdgm else
                           0 if cp.networkLocation == structs.CarParams.NetworkLocation.fwdCamera or
                           is_volt_gateway_alternate_brake(cp) else 2)
          if cp.carFingerprint in (CAR.CHEVROLET_VOLT_ASCM, CAR.CHEVROLET_VOLT_2019) and not accelerator:
            raw_brake = ((brakes[0][1][0] & 15) << 8) | brakes[0][1][1]
            self.assertEqual((0x1000 - raw_brake) & 0xFFF, 100 if sdgm else 80)
          seen_hold = True
          self.assertFalse(any(message[0] == 0x2CB for message in commands))
          self.assertGreaterEqual(tick, 340)
          self.assertFalse(regen or unavailable or gas or unknown_gear or main_off)
          self.assertFalse(370 <= tick < 470)
        if (moving or regen or unavailable or gas or unknown_gear or main_off or 370 <= tick < 470 or
            525 <= tick < 540 or 950 <= tick < 960 or camera and 1510 <= tick < 1550):
          self.assertFalse(hold)
        if 290 <= tick < 300 or 309 <= tick < 320:
          self.assertFalse(hold)
      self.assertTrue(seen_hold and seen_near_stop and seen_normal and seen_feedback)
      if sdgm:
        self.assertTrue(seen_retained and seen_normal_credit_withdrawn)
      libsafety_py.libsafety.set_alternative_experience(0)
      self.assertFalse(ci.CC.gm_auto_hold_state.engaged)

  def test_final_configuration_selection_both_alpha_modes(self):
    for alpha in (False, True):
      for accelerator in (False, True):
        cp = ordinary_params(CAR.CHEVROLET_VOLT, alpha=alpha, radar=True, accelerator=accelerator)
        expected = GMSafetyFlags.EV | GMSafetyFlags.VOLT_GATEWAY_LONG
        if not accelerator:
          expected |= GMSafetyFlags.VOLT_GATEWAY_ALT_BRAKE
        self.assertEqual(cp.safetyConfigs[0].safetyParam, expected)
        self.assertEqual(is_volt_gateway_alternate_brake(cp), not accelerator)
        self.assertTrue(cp.openpilotLongitudinalControl and not cp.pcmCruise and not cp.dashcamOnly)
        self.assertTrue(profiles_supported(cp))
        self.assertIsNotNone(volt_policy_for(cp))
      missing_radar = ordinary_params(CAR.CHEVROLET_VOLT, alpha=alpha, accelerator=False)
      self.assertFalse(is_volt_gateway_alternate_brake(missing_radar))
      self.assertTrue(missing_radar.dashcamOnly)
      for candidate in (CAR.CHEVROLET_VOLT_ASCM, CAR.CHEVROLET_VOLT_CAMERA, CAR.CHEVROLET_VOLT_2019,
                        CAR.CHEVROLET_BOLT_ACC_2022_2023, CAR.GMC_ACADIA):
        cp = ordinary_params(candidate, alpha=alpha, radar=True, accelerator=False)
        self.assertFalse(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.VOLT_GATEWAY_ALT_BRAKE)
        self.assertFalse(is_volt_gateway_alternate_brake(cp))

  def test_unknown_host_flags_and_mixed_native_selectors_are_not_admitted(self):
    for accelerator in (False, True):
      for flags in (1, 2, 3, 1 << 31):
        cp = ordinary_params(CAR.CHEVROLET_VOLT, radar=True, accelerator=accelerator)
        cp.flags = flags
        self.assertFalse(is_volt_gateway_alternate_brake(cp))
        self.assertFalse(profiles_supported(cp))
        self.assertIsNone(volt_policy_for(cp))
        controller = CarController(DBC[cp.carFingerprint], cp)
        self.assertFalse(controller.volt_gateway_long)
        self.assertEqual(controller.params.MAX_GAS, 1018)
      for extra in (GMSafetyFlags.HW_CAM, GMSafetyFlags.PEDAL_LONG, GMSafetyFlags.NO_ACC, GMSafetyFlags.ASCM_INTERCEPT):
        cp = ordinary_params(CAR.CHEVROLET_VOLT, radar=True, accelerator=accelerator)
        cp.safetyConfigs[0].safetyParam |= int(extra)
        self.assertFalse(is_volt_gateway_alternate_brake(cp))
        self.assertFalse(profiles_supported(cp))
        self.assertIsNone(volt_policy_for(cp))

  def test_brake_input_threshold_and_wrong_source_isolation(self):
    for alpha in (False, True):
      cp = ordinary_params(CAR.CHEVROLET_VOLT, alpha=alpha, radar=True, accelerator=False)
      state = CarState(cp)
      parsers = state.get_can_parsers(cp)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      state.update(parsers)  # Subscribe all ordinary state fields.
      self.assertNotIn(0xbe, parsers[Bus.pt].addresses)
      self.assertEqual(parsers[Bus.pt].message_states[0xf1].frequency, 100)
      for index, raw in enumerate((0, 5, 6, 7, 208, 255, 0)):
        frames = [packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': raw}),
                  packer.make_can_msg('ECMEngineStatus', 0, {'BrakePressed': raw < 6}),
                  packer.make_can_msg('ECMAcceleratorPos', 0, {'BrakePedalPos': 255 if raw < 6 else 0}),
                  packer.make_can_msg('EBCMBrakePedalPosition', 2, {'BrakePedalPosition': 255 if raw < 6 else 0})]
        parsers[Bus.pt].update([(1_000_000_000 + index * 10_000_000, frames)])
        out = state.update(parsers)
        self.assertEqual(out.brakePressed, raw >= 6)

  def test_ebcm_brake_input_missing_and_stale_is_invalid(self):
    cp = ordinary_params(CAR.CHEVROLET_VOLT, radar=True, accelerator=False)
    parser = CarState.get_can_parsers(cp)[Bus.pt]
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    wrong = packer.make_can_msg('ECMAcceleratorPos', 0, {'BrakePedalPos': 0})
    frame = packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': 0})
    for tick in range(5):
      parser.update([(1_000_000_000 + tick * 10_000_000, [wrong])])
      valid = parser.can_valid
    self.assertFalse(valid)
    parser.update([(1_100_000_000, [frame])])
    self.assertTrue(parser.can_valid)
    for tick in range(5):
      parser.update([(1_500_000_000 + tick * 10_000_000, [wrong])])
      valid = parser.can_valid
    self.assertFalse(valid)

  def test_controller_bytes_and_stop_release_only_change_brake_bus(self):
    for alpha in (False, True):
      normal = ordinary_params(CAR.CHEVROLET_VOLT, alpha=alpha, radar=True)
      alternate = ordinary_params(CAR.CHEVROLET_VOLT, alpha=alpha, radar=True, accelerator=False)
      # Independent wire literals cover moving regen and near-stop fixed braking.
      for cp, bus in ((normal, 2), (alternate, 0)):
        _, messages = controller_messages(cp, 4, accel=-.5, speed=2.)
        self.assertEqual([m for m in messages if m[0] == 0x315], [(0x315, bytes.fromhex('afed501201'), bus)])
        self.assertEqual([m for m in messages if m[0] == 0x2cb], [(0x2cb, bytes.fromhex('4142abe000bd541f'), 0)])
        controller = None
        for frame in range(4, 28):
          resume = frame >= 12
          active = frame < 20
          controller, messages = controller_messages(cp, frame, controller, accel=1., speed=0.,
                                                     stopping=True, resume=resume, standstill=True, long_active=active)
          brakes = [m for m in messages if m[0] == 0x315]
          if frame % 4:
            self.assertEqual(brakes, [])
          else:
            count = (frame // 4) % 4
            hold = not resume and active
            expected = bytes.fromhex(('df6a209600', 'df6a209501', 'df6a209402', 'df6a209303')[count]) if hold else \
                       bytes.fromhex(('1000f00000', '1000efff01', '1000effe02', '1000effd03')[count])
            self.assertEqual(brakes, [(0x315, expected, bus)])
            self.assertFalse(any(m[0] in (0x200, 0x1e1) for m in messages))


if __name__ == '__main__':
  unittest.main()
