"""Volt 2019 SDGM stock and observed SASCM longitudinal ownership."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.longitudinal import volt_policy_for
from opendbc.car.gm.tests.test_bolt_cc import setup, native
from opendbc.car.gm.tests.test_volt_camera_control import feed_camera
from opendbc.car.gm.values import CAR, DBC, is_volt_sdgm_profile, requires_camera_state_sources
from opendbc.safety.tests.libsafety import libsafety_py


def sdgm_params(alpha=True, release=False, sascm=True, brake_c9=False, radar=False):
  fingerprint = gen_empty_fingerprint()
  if sascm:
    fingerprint[0][0x2FF] = 8
  if not brake_c9:
    fingerprint[0][0xBE] = 6
  if radar:
    fingerprint[1][0x460] = 8
  return CarInterface.get_params(CAR.CHEVROLET_VOLT_2019, fingerprint, [], alpha, release, False)


class TestVoltSdgmControl(unittest.TestCase):
  def test_actual_startup_matrix_and_source_ownership(self):
    for alpha in (False, True):
      for release in (False, True):
        for sascm in (False, True):
          for c9 in (False, True):
            for radar in (False, True):
              cp = sdgm_params(alpha, release, sascm, c9, radar)
              enabled = alpha and sascm and not release
              self.assertEqual(cp.openpilotLongitudinalControl, enabled)
              self.assertEqual(cp.pcmCruise, not enabled)
              self.assertEqual(cp.alphaLongitudinalAvailable, sascm and not release)
              self.assertEqual(cp.safetyConfigs[0].safetyParam, (0x5007 if enabled else 0x1005) | (0x400 if c9 else 0))
              if enabled:
                from opendbc.car.gm.auto_hold import config_for
                from opendbc.car.gm.values import apply_gm_auto_hold, is_gm_auto_hold
                from opendbc.car.gm.aol import qualified_gm
                from opendbc.car.gm.lateral import lane_centering_supported
                marked = cp.as_reader().as_builder()
                apply_gm_auto_hold(marked, True)
                self.assertTrue(is_gm_auto_hold(marked))
                self.assertEqual(config_for(marked).minimum_brake, 100)
                self.assertEqual(config_for(marked).continued_stop_speed, .25)
                self.assertEqual(config_for(cp).minimum_brake, 80)
                self.assertEqual(marked.lateralTuning.to_dict(), cp.lateralTuning.to_dict())
                self.assertEqual(lane_centering_supported(marked), lane_centering_supported(cp))
                self.assertEqual(qualified_gm(marked), qualified_gm(cp))
              self.assertTrue(is_volt_sdgm_profile(cp, longitudinal=enabled))
              self.assertTrue(requires_camera_state_sources(cp))
              self.assertEqual(cp.radarUnavailable, not radar)
              self.assertEqual(cp.minEnableSpeed, -1.)
              self.assertAlmostEqual(cp.minSteerSpeed, 7 * .44704, delta=1e-6)
              self.assertEqual(list(cp.longitudinalTuning.kiV), [.5, .5])
              self.assertEqual(cp.stopAccel, -.25)
              self.assertEqual(volt_policy_for(cp) is not None, enabled)

  def test_actual_parser_controller_and_native_routes(self):
    safety = libsafety_py.libsafety
    release = safety.set_safety_hooks(int(structs.CarParams.SafetyModel.allOutput), 0) != 0
    for alpha in (False, True):
      for c9 in (False, True):
        cp = sdgm_params(alpha=alpha, release=release, brake_c9=c9, radar=True)
        ci = CarInterface(cp)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        setup(cp)
        for tick in range(16):
          now = 1_000_000_000 + tick * 40_000_000
          out, sources = feed_camera(ci, packer, now, counter=tick % 4, gas=tick >= 8, low=tick % 2 == 0)
          self.assertTrue(out.canValid)
          for source in sources:
            native("rx", source, now // 1000)
          if cp.openpilotLongitudinalControl:
            native("rx", packer.make_can_msg("ASCMSteeringButton", 0, {"ACCButtons": 2}), now // 1000)
          safety.safety_tick()
          self.assertTrue(safety.safety_config_valid())
          cc = structs.CarControl(enabled=True, latActive=True, longActive=cp.openpilotLongitudinalControl and tick < 8)
          cc.actuators.accel = -2. if tick % 2 else 1.
          cc.actuators.torque = .01
          cc.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
          ci.CC.frame = tick * 4
          _, messages = ci.apply(cc.as_reader(), now)
          self.assertFalse(any(message[0] in (0x2CD, 0x200, 0xBD, 0x1F5, 0x3D1, 0xA1, 0x306, 0x308, 0x310) for message in messages))
          if cp.openpilotLongitudinalControl:
            self.assertEqual({message[0] for message in messages if message[0] in (0x2CB, 0x315, 0x370)}, {0x2CB, 0x315, 0x370})
            self.assertTrue(all(message[2] == 2 for message in messages if message[0] == 0x315))
            self.assertTrue(all(message[2] == 0 for message in messages if message[0] in (0x2CB, 0x370)))
            if tick >= 8:
              self.assertEqual((ci.CC.apply_gas, ci.CC.apply_brake), (-500, 0))
          else:
            self.assertFalse(any(message[0] in (0x2CB, 0x315, 0x370) for message in messages))
          for message in messages:
            self.assertTrue(native("tx", message, now // 1000), hex(message[0]))
        self.assertNotEqual(ci.CC.apply_torque_last, 0)

  def test_stale_camera_suppresses_steering_without_reconfiguring(self):
    cp = sdgm_params()
    ci = CarInterface(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    now = 1_000_000_000
    _, messages = feed_camera(ci, packer, now)
    cc = structs.CarControl(enabled=True, latActive=True)
    cc.actuators.torque = .1
    ci.CC.frame = 3
    ci.apply(cc.as_reader(), now)
    self.assertNotEqual(ci.CC.apply_torque_last, 0)
    for tick in range(1, 50):
      stamp = now + tick * 40_000_000
      ci.update([(stamp, [message for message in messages if message[2] == 0])])
    self.assertFalse(ci.CS.out.canValid)
    ci.CC.frame += 10
    ci.apply(cc.as_reader(), stamp)
    self.assertEqual(ci.CC.apply_torque_last, 0)
    self.assertEqual(cp.safetyConfigs[0].safetyParam, 0x5007)

  def test_selected_brake_source_and_c9_without_accelerator_position(self):
    for c9 in (False, True):
      for selected_pressed in (False, True):
        cp = sdgm_params(brake_c9=c9)
        ci = CarInterface(cp)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        template_ci = CarInterface(cp)
        for tick in range(40):
          now = 1_000_000_000 + tick * 40_000_000
          _, template = feed_camera(template_ci, packer, now, counter=tick % 4)
          messages = [message for message in template if message[0] not in (0xBE, 0xC9)]
          messages.append(packer.make_can_msg("ECMEngineStatus", 0,
            {"CruiseMainOn": 1, "BrakePressed": selected_pressed if c9 else not selected_pressed}))
          if not c9:
            messages.append(packer.make_can_msg("ECMAcceleratorPos", 0, {"BrakePedalPos": 12 if selected_pressed else 0}))
          out = ci.update([(now + 1, messages)])
          self.assertTrue(out.canValid)
          self.assertEqual(out.brakePressed, selected_pressed)
          self.assertEqual(bool(cp.safetyConfigs[0].safetyParam & 0x400), c9)


class TestVoltSdgmAcceptedEnvelope(unittest.TestCase):
  def test_factory_selector_and_legacy_aliases_do_not_borrow_default_cap(self):
    from opendbc.car.gm.values import CarControllerParams, is_volt_sdgm_accepted_envelope
    from opendbc.car.gm.tests.test_volt_transitions import volt_sdgm_pedal_params
    from opendbc.car.gm.tests.test_volt_grade import params
    for c9 in (False, True):
      cp = sdgm_params(brake_c9=c9)
      self.assertTrue(is_volt_sdgm_accepted_envelope(cp))
      self.assertEqual(CarControllerParams(cp).MAX_GAS, 2041)
      for word in ((0x5487, 0xD108, 0xD118) if c9 else (0x5087, 0xD107, 0xD117)):
        marked = cp.as_reader().as_builder()
        marked.safetyConfigs[0].safetyParam = word
        self.assertFalse(is_volt_sdgm_accepted_envelope(marked))
        self.assertEqual(CarControllerParams(marked).MAX_GAS, 2698)
      for field, value in (('brand', 'hyundai'), ('carFingerprint', CAR.HOLDEN_ASTRA),
                           ('passive', True), ('dashcamOnly', True), ('notCar', True),
                           ('openpilotLongitudinalControl', False), ('pcmCruise', True)):
        wrong = cp.as_reader().as_builder()
        setattr(wrong, field, value)
        self.assertFalse(is_volt_sdgm_accepted_envelope(wrong), field)
      self.assertFalse(is_volt_sdgm_accepted_envelope(volt_sdgm_pedal_params(be=not c9)))
    self.assertFalse(is_volt_sdgm_accepted_envelope(sdgm_params(alpha=False)))
    self.assertFalse(is_volt_sdgm_accepted_envelope(params(CAR.CHEVROLET_VOLT_ASCM, alpha=True, sascm=True)))

  def test_factory_bound_denies_malformed_physical_inputs(self):
    from opendbc.car.gm.values import volt_sdgm_accepted_accel_max
    cp = sdgm_params()
    for speed in (-1., float('nan'), float('inf'), -float('inf'), 1e308):
      self.assertEqual(volt_sdgm_accepted_accel_max(cp, speed), 0.)
    for field in ('mass', 'wheelbase'):
      for value in (0., -1., float('nan'), float('inf')):
        invalid = cp.as_reader().as_builder()
        setattr(invalid, field, value)
        self.assertEqual(volt_sdgm_accepted_accel_max(invalid, 10.), 0.)

  def test_current_controller_preserves_lower_wire_and_clamps_upper_for_all_counters(self):
    from opendbc.car.gm.carcontroller import volt_demands
    for c9 in (False, True):
      cp = sdgm_params(brake_c9=c9)
      for speed in (0., 5., 10., 25., 40.):
        for pitch in (-.08, 0., .08):
          for accel in (-3., -.5, 0., .3, .8, 1.4, 2.):
            original_gas, original_brake = volt_demands(
              accel, speed, [0., pitch, 0.], .25, cp.mass, cp.wheelbase,
              -4., 2., 400, min_gas=-540, max_gas=2698, inactive_gas=-500)
            for counter in range(4):
              ci = CarInterface(cp)
              packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
              feed_camera(ci, packer, 1_000_000_000, speed=speed)
              control = structs.CarControl(enabled=True, longActive=True)
              control.actuators.accel = accel
              control.orientationNED = [0., pitch, 0.]
              ci.CC.frame = counter * 4
              _, frames = ci.apply(control.as_reader(), 1_000_000_000)
              controller = ci.CC
              gas_frame = next(frame for frame in frames if frame[0] == 0x2CB)
              brake_frame = next(frame for frame in frames if frame[0] == 0x315)
              data = gas_frame[1]
              gas = (((data[1] & 7) << 16) | (data[2] << 8) | data[3]) / 8 - 22534
              brake = (4096 - (((brake_frame[1][0] & 15) << 8) | brake_frame[1][1])) & 4095
              self.assertEqual(gas, min(original_gas, 2041))
              self.assertEqual(brake, original_brake)
              self.assertEqual((gas_frame[2], brake_frame[2], data[0] >> 6), (0, 2, counter))
              # Accepted original raw values naturally carry the legacy marker.
              self.assertEqual(data[2] & 0x80, 0x80)
              # Transcribed Dom bytes for its actually admitted raw command.
              raw = int(min(original_gas, 2041)) + 6150
              expected = bytearray(8)
              expected[0] = (counter << 6) | 1
              expected[1] = 0x42 | ((raw >> 13) & 1)
              expected[2] = ((raw << 3) >> 8) & 255 | 0x80
              expected[3] = (raw << 3) & 255
              expected[5] = 255 - expected[1]
              expected[6] = 255 - expected[2]
              expected[7] = (256 - expected[3] - counter) & 255
              self.assertEqual(data, bytes(expected))
              self.assertLessEqual(controller.apply_gas, 2041)

  def test_actual_longcontrol_driver_release_reaches_25hz_native_envelope_and_neutral(self):
    from openpilot.selfdrive.controls.lib.longcontrol import LongControl
    safety = libsafety_py.libsafety
    release = safety.set_safety_hooks(int(structs.CarParams.SafetyModel.allOutput), 0) != 0
    for c9 in (False, True):
      cp = sdgm_params(brake_c9=c9, release=release)
      ci = CarInterface(cp)
      owner = LongControl(cp)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      setup(cp)
      gas_count = brake_count = 0
      previous_counter = None
      for tick in range(320):
        now = 1_000_000_000 + tick * 40_000_000
        driver = tick < 40
        active = cp.openpilotLongitudinalControl and 40 <= tick < 280
        state, sources = feed_camera(ci, packer, now, counter=tick % 4, speed=10., gas=driver)
        for frame in sources:
          native('rx', frame, now // 1000)
        if active:
          native('rx', packer.make_can_msg('ASCMSteeringButton', 0, {'ACCButtons': 2}), now // 1000)
        safety.safety_tick()
        self.assertTrue(state.canValid)
        self.assertTrue(safety.safety_config_valid())
        limits = CarInterface.get_pid_accel_limits(cp, state.vEgo, 40. / 3.6)
        for _ in range(4):
          accel = owner.update(active, state, 1.11575 if tick < 220 else -.72, False, limits)
        control = structs.CarControl(enabled=active, longActive=active, latActive=active)
        control.actuators.accel = float(accel)
        control.actuators.torque = 0.
        control.actuators.longControlState = owner.long_control_state
        ci.CC.frame = tick * 4
        _, frames = ci.apply(control.as_reader(), now)
        for frame in frames:
          self.assertTrue(native('tx', frame, now // 1000), hex(frame[0]))
          if frame[0] == 0x2CB:
            gas_count += 1
            data = frame[1]
            gas = (((data[1] & 7) << 16) | (data[2] << 8) | data[3]) / 8 - 22534
            self.assertLessEqual(gas, 2041)
            self.assertGreaterEqual(gas, -540)
            counter = data[0] >> 6
            if previous_counter is not None:
              self.assertEqual(counter, (previous_counter + 1) % 4)
            previous_counter = counter
            if not active:
              self.assertEqual(gas, -500)
              self.assertEqual(data[0] & 1, 0)
          elif frame[0] == 0x315:
            brake_count += 1
        if not active:
          self.assertEqual(owner.pid.i, 0.)
      self.assertEqual((gas_count, brake_count), (0, 0) if release else (320, 320))
