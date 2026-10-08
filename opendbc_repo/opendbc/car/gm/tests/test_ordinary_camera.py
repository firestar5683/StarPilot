import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import DBC, ORDINARY_CAMERA_CAR, ORDINARY_CAMERA_ALPHA_CAR, is_ordinary_camera_profile


def params(identity, *, alpha=False, release=False, camera=True, be=True):
  fp = gen_empty_fingerprint()
  fp[0].update({0xF1: 6, 0xC9: 8, 0x1C4: 8, 0x184: 8, 0x34A: 5})
  if be:
    fp[0][0xBE] = 6
  if not camera:
    fp[0][0x1E1] = 7
  if camera:
    fp[2].update({0x320: 6, 0x180: 4, 0x370: 6})
  return CarInterface.get_params(identity, fp, [], alpha, release, False)


def feed(ci, packer, now, *, cruise=True, gas=False, brake=False, fcw=0, counter=0, camera=True, speed=None):
  from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
  frames = pt_frames(packer, gas=gas, counter=counter, acc_cruise=2 if cruise else 0)
  frames = [frame for frame in frames if frame[0] != 0xC9]
  frames.append(packer.make_can_msg("EBCMBrakePedalPosition", 0, {"BrakePedalPosition": 40 if brake else 0}))
  frames.append(packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': 1, 'BrakePressed': int(brake)}))
  frames += [packer.make_can_msg('ASCMLKASteeringCmd', 2, {'RollingCounter': counter}),
             packer.make_can_msg('AEBCmd', 2, {}),
             packer.make_can_msg('ASCMActiveCruiseControlStatus', 2,
                                 {'ACCCruiseState': 2, 'ACCSpeedSetpoint': 80, 'FCWAlert': fcw})]
  if not camera:
    frames = [frame for frame in frames if frame[2] != 2]
  if speed is not None:
    frames = [frame for frame in frames if frame[0] not in (0x348, 0x34A)]
    frames += [packer.make_can_msg('EBCMWheelSpdFront', 0, {'FLWheelSpd': speed, 'FRWheelSpd': speed}),
               packer.make_can_msg('EBCMWheelSpdRear', 0, {'RLWheelSpd': speed, 'RRWheelSpd': speed})]
  return ci.update([(now, frames)]), frames


class TestOrdinaryCamera(unittest.TestCase):
  def test_final_modes_do_not_require_removed_camera_after_lazy_reads(self):
    from opendbc.car.gm.startup_preferences import prepare_disable_longitudinal
    for identity in ORDINARY_CAMERA_CAR:
      for alpha in (False, True):
        for release in (False, True):
          for camera in (False, True):
            for disable_long in (False, True):
              with self.subTest(identity=identity, alpha=alpha, release=release,
                                camera=camera, disable_long=disable_long):
                cp = params(identity, alpha=alpha, release=release, camera=camera)
                before = (cp.openpilotLongitudinalControl, cp.pcmCruise, cp.safetyConfigs[0].safetyParam)
                prepare_disable_longitudinal(cp, disable_long)
                expected = ((False, True, 0xC171 if camera else 0xC172)
                            if disable_long and before[0] else before)
                self.assertEqual((cp.openpilotLongitudinalControl, cp.pcmCruise,
                                  cp.safetyConfigs[0].safetyParam), expected)
                self.assertTrue(is_ordinary_camera_profile(cp, longitudinal=expected[0]))
                ci = CarInterface(cp)
                packer = CANPacker(DBC[identity][Bus.pt])
                for tick in range(40):
                  out, frames = feed(ci, packer, 1_000_000_000 + tick * 10_000_000,
                                     camera=camera, counter=tick % 4)
                self.assertTrue(out.canValid)
                self.assertFalse(out.canTimeout)
                if not camera:
                  self.assertFalse(any(frame[2] == 2 for frame in frames))
                steering_address = packer.make_can_msg('PSCMSteeringAngle', 0, {})[0]
                self.assertTrue(any(frame[0] == steering_address and frame[2] == 0 for frame in frames))
                for tick in range(40, 140):
                  now = 1_000_000_000 + tick * 10_000_000
                  retained = [frame for frame in frames if not (frame[0] == steering_address and frame[2] == 0)]
                  out = ci.update([(now, retained)])
                self.assertFalse(out.canValid)
                for tick in range(140, 180):
                  out, _ = feed(ci, packer, 1_000_000_000 + tick * 10_000_000,
                                camera=camera, counter=tick % 4)
                self.assertTrue(out.canValid)

  def test_final_cp_and_default_policy_modes(self):
    from opendbc.car.gm.camera import policy_for
    from opendbc.car.gm.feature_capabilities import longitudinal_supported, display_supported
    from opendbc.car.gm.lateral import lane_centering_supported
    from opendbc.car.gm.aol import qualified_gm
    from openpilot.starpilot.lateral.controller_selection import policy_for as lateral_policy_for
    self.assertEqual(len(ORDINARY_CAMERA_CAR), 6)
    for identity in ORDINARY_CAMERA_CAR:
      for release in (False, True):
        for alpha in (False, True):
          cp = params(identity, alpha=alpha, release=release)
          long = alpha and not release and identity in ORDINARY_CAMERA_ALPHA_CAR
          self.assertEqual(cp.openpilotLongitudinalControl, long)
          self.assertEqual(cp.pcmCruise, not long)
          self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xC170 if long else 0xC171)
          self.assertFalse(cp.dashcamOnly)
          self.assertTrue(is_ordinary_camera_profile(cp, longitudinal=long))
          self.assertEqual(policy_for(cp) is not None, long)
          self.assertEqual(longitudinal_supported(cp), long)
          self.assertTrue(display_supported(cp))
          self.assertTrue(lane_centering_supported(cp))
          self.assertTrue(qualified_gm(cp))
          self.assertEqual(lateral_policy_for(cp), 'ordinary_camera')
          absent = params(identity, alpha=alpha, release=release, camera=False)
          self.assertFalse(absent.dashcamOnly)
          self.assertTrue(is_ordinary_camera_profile(absent, longitudinal=long))
          self.assertEqual(absent.safetyConfigs[0].safetyParam, 0xC173 if long else 0xC172)

  def test_actual_required_sources_and_alt_status_ownership(self):
    for identity in ORDINARY_CAMERA_CAR:
      cp = params(identity)
      ci = CarInterface(cp)
      packer = CANPacker(DBC[identity][Bus.pt])
      for tick in range(30):
        out, _ = feed(ci, packer, 1_000_000_000 + tick * 10_000_000, fcw=2, counter=tick % 4)
      self.assertTrue(out.canValid)
      self.assertTrue(out.cruiseState.enabled)
      self.assertFalse(out.cruiseState.nonAdaptive)
      self.assertAlmostEqual(out.cruiseState.speed, 80 / 3.6, places=5)
      self.assertEqual(ci.CS.stock_fcw_alert, 2)

  def test_packed_commands_gas_lateral_and_stock_cancel_route(self):
    for identity in ORDINARY_CAMERA_CAR:
      for alpha in (False, True):
        cp = params(identity, alpha=alpha)
        ci = CarInterface(cp)
        packer = CANPacker(DBC[identity][Bus.pt])
        emitted_cancel = False
        for tick in range(30):
          now = 1_000_000_000 + tick * 40_000_000
          out, _ = feed(ci, packer, now, gas=tick >= 12, counter=tick % 4)
          self.assertTrue(out.canValid)
          cc = structs.CarControl(enabled=True, latActive=True, longActive=cp.openpilotLongitudinalControl and tick < 12)
          cc.actuators.torque = .1
          cc.actuators.accel = 1.
          cc.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
          cc.cruiseControl.cancel = not cp.openpilotLongitudinalControl
          ci.CC.frame = tick * 4
          _, messages = ci.apply(cc.as_reader(), now)
          self.assertFalse(any(message[0] in (0x200, 0xBD, 0x1F5, 0x3D1, 0xA1, 0x306, 0x308, 0x310) for message in messages))
          if cp.openpilotLongitudinalControl:
            self.assertEqual([message[0] for message in messages if message[0] in (0x2CD, 0x2CB, 0x315, 0x370)],
                             [0x2CD, 0x2CB, 0x315, 0x370])
            self.assertTrue(all(message[2] == 0 for message in messages if message[0] in (0x2CD, 0x2CB, 0x315, 0x370)))
            if tick >= 12:
              self.assertEqual((ci.CC.apply_gas, ci.CC.apply_brake), (-500., 0))
          else:
            self.assertFalse(any(message[0] in (0x2CD, 0x2CB, 0x315, 0x370) for message in messages))
            for message in messages:
              if message[0] == 0x1E1:
                emitted_cancel = True
                self.assertEqual(message[2], 2)
          if tick >= 12:
            self.assertNotEqual(ci.CC.apply_torque_last, 0)
        if not cp.openpilotLongitudinalControl:
          self.assertTrue(emitted_cancel)

  def test_expired_camera_and_main_sources_zero_actual_steering(self):
    for alpha in (False, True):
      identity = next(iter(ORDINARY_CAMERA_ALPHA_CAR))
      for omitted in ('camera', 'main'):
        cp = params(identity, alpha=alpha)
        ci = CarInterface(cp)
        packer = CANPacker(DBC[identity][Bus.pt])
        for tick in range(30):
          now = 1_000_000_000 + tick * 10_000_000
          out, messages = feed(ci, packer, now, counter=tick % 4)
        self.assertTrue(out.canValid)
        cc = structs.CarControl(enabled=True, latActive=True)
        cc.actuators.torque = .1
        ci.CC.frame = 120
        ci.apply(cc.as_reader(), now)
        self.assertNotEqual(ci.CC.apply_torque_last, 0)
        retained = [message for message in messages if message[2] == 0] if omitted == 'camera' else [
          message for message in messages if message[0] != 0xC9]
        for tick in range(1, 80):
          stamp = now + tick * 20_000_000
          ci.update([(stamp, retained)])
        ci.CC.frame += 10
        _, emitted = ci.apply(cc.as_reader(), stamp)
        self.assertEqual(ci.CC.apply_torque_last, 0)
        self.assertTrue(any(message[0] == 0x180 for message in emitted))

  def test_f1_analog_source_with_and_without_be_keeps_c9_brake_owner(self):
    from opendbc.car.gm.values import GMFlags
    for identity in ORDINARY_CAMERA_CAR:
      for be in (False, True):
        for alpha in (False, True):
          cp = params(identity, alpha=alpha, be=be)
          self.assertEqual(bool(cp.flags & GMFlags.NO_ACCELERATOR_POS_MSG), not be)
          ci = CarInterface(cp)
          packer = CANPacker(DBC[identity][Bus.pt])
          for tick in range(30):
            now = 1_000_000_000 + tick * 10_000_000
            _, messages = feed(ci, packer, now, counter=tick % 4)
            messages = [message for message in messages if message[0] not in (0xC9, 0xF1) and (be or message[0] != 0xBE)]
            messages += [packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': 80}),
                         packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': 1, 'BrakePressed': 0})]
            out = ci.update([(now + 1, messages)])
          self.assertTrue(out.canValid)
          self.assertFalse(out.brakePressed)
          messages = [message for message in messages if message[0] not in (0xC9, 0xF1)]
          messages += [packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': 0}),
                       packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': 1, 'BrakePressed': 1})]
          out = ci.update([(now + 10_000_000, messages)])
          self.assertTrue(out.brakePressed)

  def test_actual_card_preserves_final_camera_owner(self):
    import os
    from unittest.mock import patch
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.car.card import Car
    from opendbc.car.gm.radar_interface import RadarInterface
    for identity in ORDINARY_CAMERA_CAR:
      with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        saved = Params()
        saved.put_bool('OpenpilotEnabledToggle', True, block=True)
        saved.put_bool('AlwaysOnLateral', True, block=True)
        cp = params(identity, alpha=True, be=False)
        card = Car(CI=CarInterface(cp), RI=RadarInterface(cp))
        long = identity in ORDINARY_CAMERA_ALPHA_CAR
        self.assertEqual(card.CP.openpilotLongitudinalControl, long)
        self.assertEqual(card.CP.pcmCruise, not long)
        self.assertEqual(card.CP.safetyConfigs[0].safetyParam, 0xC170 if long else 0xC171)
        self.assertTrue(is_ordinary_camera_profile(card.CP, longitudinal=long))

  def test_declared_f1_source_recipe_matches_selected_analog_owner(self):
    from unittest.mock import patch
    from opendbc.car.gm import carstate
    real_parser = carstate.CANParser
    for be in (False, True):
      recipes = {}

      def make_parser(dbc, messages, bus, recipes=recipes):
        recipes[bus] = list(messages)
        return real_parser(dbc, messages, bus)
      cp = params(next(iter(ORDINARY_CAMERA_ALPHA_CAR)), alpha=True, be=be)
      with patch.object(carstate, 'CANParser', side_effect=make_parser):
        CarInterface(cp)
      self.assertEqual([frequency for name, frequency in recipes[0] if name == 'EBCMBrakePedalPosition'],
                       [10 if be else 100])
      self.assertEqual(any(name == 'ECMAcceleratorPos' for name, _ in recipes[0]), be)


class TestTruckTuning(unittest.TestCase):
  def test_exact_final_owner_and_pedal_stock_release_denials(self):
    from opendbc.car.gm.values import CAR
    from opendbc.car.gm.truck_longitudinal import truck_tuning_supported
    from opendbc.car.gm.tests.test_silverado_cc_pedal import params as pedal_params
    for camera, word in ((True, 0xC170), (False, 0xC173)):
      cp = params(CAR.CHEVROLET_SILVERADO, alpha=True, camera=camera)
      self.assertEqual(cp.safetyConfigs[0].safetyParam, word)
      self.assertTrue(truck_tuning_supported(cp))
      self.assertIsNotNone(CarInterface(cp).CC.truck_tuning)
    for cp in (params(CAR.CHEVROLET_SILVERADO), params(CAR.CHEVROLET_SILVERADO, alpha=True, release=True),
               params(CAR.CHEVROLET_EQUINOX, alpha=True), pedal_params(), pedal_params(disabled=True)):
      self.assertFalse(truck_tuning_supported(cp))
      self.assertIsNone(CarInterface(cp).CC.truck_tuning)

  def test_original_pitch_positive_follow_and_immediate_brake_boundaries(self):
    from opendbc.car.gm.truck_longitudinal import (shape_truck_positive_accel, smooth_truck_follow_accel,
                                                 shape_truck_pitch_accel, shape_truck_friction_brake)
    self.assertAlmostEqual(shape_truck_pitch_accel(-.3, 30., True), -.0825)
    self.assertAlmostEqual(shape_truck_pitch_accel(.3, 30., True), .0825)
    self.assertEqual(shape_truck_pitch_accel(-.3, 30., False), -.3)
    self.assertLess(shape_truck_positive_accel(.12, 26., True), .12)
    self.assertGreater(shape_truck_positive_accel(.28, 26., True, True, 6.),
                       shape_truck_positive_accel(.28, 26., True))
    for accel, speed, enabled in ((-.3, 26., True), (1., 26., True), (.12, 6., True), (.12, 26., False)):
      self.assertEqual(shape_truck_positive_accel(accel, speed, enabled), accel)
    self.assertAlmostEqual(smooth_truck_follow_accel(.3, 0., 26., True, True, False), .06)
    self.assertEqual(smooth_truck_follow_accel(-.85, .3, 26., True, True, False), -.85)
    self.assertEqual(shape_truck_friction_brake(39, -.3, False, False), (0, False))
    self.assertEqual(shape_truck_friction_brake(40, -.3, False, False), (40, True))
    self.assertEqual(shape_truck_friction_brake(9, -.3, False, True), (9, True))
    self.assertEqual(shape_truck_friction_brake(8, -.3, False, True), (0, False))
    self.assertEqual(shape_truck_friction_brake(5, -.85, False, False), (5, True))
    self.assertEqual(shape_truck_friction_brake(5, -.2, True, False), (5, True))

  def test_absent_and_off_keep_default_demands_and_braking(self):
    from opendbc.car.gm.values import CAR
    from opendbc.car.gm.ordinary import demands
    from opendbc.car.gm.truck_longitudinal import TruckTuning
    cp = params(CAR.CHEVROLET_SILVERADO, alpha=True)
    off = TruckTuning()
    for speed in (0., 12., 26., 35.):
      for accel in (-4., -.85, -.3, .12, .35, 1.):
        for orientation in (None, (0., -.03, 0.), (0., .03, 0.)):
          arguments = dict(min_gas=-540, max_gas=2698, inactive_gas=-500, brake_threshold=0.)
          baseline = demands(accel, speed, orientation, cp, **arguments)
          self.assertEqual(demands(accel, speed, orientation, cp, truck_tuning=off,
                                   lead_visible=True, set_speed_error=6., **arguments), baseline)
    enabled = TruckTuning()
    enabled.enabled = True
    arguments = dict(min_gas=-540, max_gas=2698, inactive_gas=-500, brake_threshold=0.)
    baseline = demands(.12, 26., None, cp, **arguments)
    selected = demands(.12, 26., None, cp, truck_tuning=enabled, **arguments)
    self.assertLess(selected[0], baseline[0])
    self.assertEqual(selected[1], 0)
    baseline = demands(-1., 26., None, cp, **arguments)
    self.assertEqual(demands(-1., 26., None, cp, truck_tuning=enabled, **arguments), baseline)

  def test_saved_owner_default_off_live_off_and_invalid_choice(self):
    from unittest.mock import patch
    from openpilot.starpilot.car.gm.tune_preferences import TruckTuningPreference
    from openpilot.starpilot.controller_extensions import configure_controller
    from opendbc.car.gm.values import CAR
    cp = params(CAR.CHEVROLET_SILVERADO, alpha=True)
    ci = CarInterface(cp)
    saved = {'OpenpilotEnabledToggle': b'1'}

    def read(_, key, limit):
      return saved.get(key), True
    with patch('openpilot.starpilot.car.gm.tune_preferences.read_saved', side_effect=read):
      configure_controller(ci, object())
      self.assertIsInstance(ci.CC.truck_tuning_input, TruckTuningPreference)
      before = cp.to_bytes()
      cp.clear_write_flag()
      owner = ci.CC.truck_tuning_input
      self.assertFalse(owner.update(1_000_000_000))
      saved['TruckTuning'] = b'1'
      self.assertTrue(owner.update(1_500_000_000))
      saved['TruckTuning'] = b'0'
      self.assertFalse(owner.update(2_000_000_000))
      saved['TruckTuning'] = b'1\n'
      self.assertFalse(owner.update(2_500_000_000))
      saved['TruckTuning'] = b'1'
      saved['SafeMode'] = b'1'
      self.assertFalse(owner.update(3_000_000_000))
      saved['SafeMode'] = b'0'
      saved['DisableOpenpilotLongitudinal'] = b'1'
      self.assertFalse(owner.update(3_500_000_000))
      self.assertFalse(owner.update(3_000_000_000))
      self.assertEqual(cp.to_bytes(), before)

  def test_actual_ci_selected_shaping_retains_packed_owner_and_long_withdrawal(self):
    from unittest.mock import patch
    from openpilot.starpilot.controller_extensions import configure_controller
    from opendbc.car.gm.values import CAR
    outputs = []
    for selected in (False, True):
      ci = CarInterface(params(CAR.CHEVROLET_SILVERADO, alpha=True))
      packer = CANPacker(DBC[CAR.CHEVROLET_SILVERADO][Bus.pt])

      def read(_, key, limit, selected=selected):
        return ({'OpenpilotEnabledToggle': b'1', 'TruckTuning': b'1' if selected else b'0'}.get(key), True)
      with patch('openpilot.starpilot.car.gm.tune_preferences.read_saved', side_effect=read):
        configure_controller(ci, object())
        for tick in range(60):
          now = 1_000_000_000 + tick * 10_000_000
          out, _ = feed(ci, packer, now, counter=tick % 4, speed=93.6)
        self.assertTrue(out.canValid)
        self.assertGreater(out.vEgo, 25.)
        cc = structs.CarControl(enabled=True, longActive=True)
        cc.actuators.accel = .12
        cc.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
        ci.CC.frame = 240
        _, messages = ci.apply(cc.as_reader(), now + 2)
        self.assertEqual([m[0] for m in messages if m[0] in (0x2CB, 0x315)], [0x2CB, 0x315])
        self.assertTrue(all(m[2] == 0 for m in messages if m[0] in (0x2CB, 0x315)))
        outputs.append((ci.CC.apply_gas, ci.CC.apply_brake))
        cc.longActive = False
        ci.CC.frame = 244
        ci.apply(cc.as_reader(), now + 40_000_000)
        self.assertEqual((ci.CC.apply_gas, ci.CC.apply_brake), (-500, 0))
        self.assertEqual(ci.CC.truck_tuning.follow_accel, 0.)
        cc.longActive = True
        cc.actuators.accel = -1.
        ci.CC.frame = 248
        ci.apply(cc.as_reader(), now + 80_000_000)
        self.assertGreater(ci.CC.apply_brake, 0)
    self.assertLess(outputs[1][0], outputs[0][0])
    self.assertEqual(outputs[0][1], outputs[1][1])
