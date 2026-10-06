import unittest

from opendbc.car.gm.tests.test_ascm_intercept import params
from opendbc.car.gm.values import CAR, ORDINARY_CC_CAR, is_ordinary_cc_profile, CruiseButtons, GMFlags
from opendbc.car.gm.ordinary_cc import button_request, ButtonCadence, policy_for
from opendbc.car.gm.feature_capabilities import longitudinal_supported
from opendbc.car.gm.lateral import lane_centering_supported
from opendbc.car.gm.aol import qualified_gm
from openpilot.starpilot.lateral.controller_selection import policy_for as lateral_policy_for


def qualified_frames(packer, counter):
  from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
  from opendbc.car.gm.gmcan import create_buttons
  frames = [frame for frame in pt_frames(packer, counter=counter) if frame[0] not in (0x1E1, 0x34A)]
  frames.append(create_buttons(packer, 0, counter, CruiseButtons.UNPRESS))
  frames.append(packer.make_can_msg('EBCMWheelSpdRear', 0, {'RLWheelSpd': 60, 'RRWheelSpd': 60, 'RLWheelDir': 1, 'RRWheelDir': 1}))
  return frames


def malibu_f1_params(*, release=False):
  from opendbc.car import gen_empty_fingerprint
  from opendbc.car.gm.interface import CarInterface
  from opendbc.car.gm.values import MALIBU_CC_F1_SOURCES
  fingerprint = gen_empty_fingerprint()
  fingerprint[0].update(MALIBU_CC_F1_SOURCES)
  return CarInterface.get_params(CAR.CHEVROLET_MALIBU_CC, fingerprint, [], False, release, False)

class TestOrdinaryCc(unittest.TestCase):
  def test_alternate_malibu_factory_and_parser_brake_sources(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.startup_preferences import prepare_disable_longitudinal
    from opendbc.car.gm.values import DBC, is_malibu_cc_f1_profile
    for release in (False, True):
      for disabled in (False, True):
        cp = malibu_f1_params(release=release)
        prepare_disable_longitudinal(cp, disabled)
        self.assertTrue(is_malibu_cc_f1_profile(cp))
        self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xC162 if disabled else 0xC161)
        self.assertEqual(cp.pcmCruise, disabled)
        self.assertEqual(cp.openpilotLongitudinalControl, not disabled)
        ci = CarInterface(cp)
        packer = CANPacker(DBC[CAR.CHEVROLET_MALIBU_CC][Bus.pt])
        for tick in range(80):
          raw, f1, c9 = ((20, 0, 0), (21, 0, 0), (0, 1, 0), (0, 0, 1), (0, 1, 1), (0, 0, 1), (0, 0, 0))[tick % 7]
          frames = [frame for frame in qualified_frames(packer, tick % 4) if frame[0] not in (0xBE, 0xF1, 0xC9)]
          frames += [packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': raw, 'BrakePressed': f1}),
                     packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': 1, 'BrakePressed': c9})]
          out = ci.update([(1_000_000_000 + tick * 10_000_000, frames)])
          self.assertEqual(out.brakePressed, bool(raw >= 21 or f1 or c9))
          self.assertFalse(out.cruiseState.nonAdaptive)
        self.assertTrue(out.canValid)
        self.assertNotIn('ECMAcceleratorPos', ci.can_parsers[Bus.pt].vl)

  def test_alternate_malibu_missing_source_is_final_no_output(self):
    from opendbc.car import gen_empty_fingerprint, structs
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.values import MALIBU_CC_F1_SOURCES, is_malibu_cc_f1_profile
    for address in MALIBU_CC_F1_SOURCES:
      fingerprint = gen_empty_fingerprint()
      fingerprint[0].update(MALIBU_CC_F1_SOURCES)
      fingerprint[0].pop(address)
      cp = CarInterface.get_params(CAR.CHEVROLET_MALIBU_CC, fingerprint, [], False, False, False)
      self.assertTrue(cp.dashcamOnly)
      self.assertFalse(cp.openpilotLongitudinalControl)
      self.assertFalse(is_malibu_cc_f1_profile(cp))
      self.assertEqual(cp.safetyConfigs[0].safetyModel, structs.CarParams.SafetyModel.noOutput)

  def test_actual_final_configuration_and_shared_owners(self):
    self.assertEqual(len(ORDINARY_CC_CAR), 8)
    for identity in ORDINARY_CC_CAR:
      for release in (False, True):
        for alpha in (False, True):
          cp = params(identity, alpha=alpha, release=release)
          self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xC160)
          self.assertTrue(cp.openpilotLongitudinalControl)
          self.assertFalse(cp.pcmCruise)
          self.assertFalse(cp.alphaLongitudinalAvailable)
          self.assertFalse(cp.dashcamOnly)
          self.assertTrue(is_ordinary_cc_profile(cp))
          self.assertTrue(longitudinal_supported(cp))
          self.assertTrue(lane_centering_supported(cp))
          self.assertTrue(qualified_gm(cp))
          self.assertEqual(lateral_policy_for(cp), 'ordinary_cc')
          self.assertEqual(policy_for(cp).stopping_decel_rate, 11.18)
          self.assertEqual(policy_for(cp).kp[1], (0, 20, 20) if identity == CAR.CHEVROLET_MALIBU_CC else (0, 5, 2))
          if identity in (CAR.CADILLAC_CT6_CC, CAR.CADILLAC_XT5_CC, CAR.CHEVROLET_SUBURBAN_CC, CAR.GMC_YUKON_CC):
            self.assertEqual(identity.config.specs.tireStiffnessFactor, 1.0)

  def test_bsm_metadata_preserves_exact_control_profile_and_other_flags_deny(self):
    for identity in ORDINARY_CC_CAR:
      cp = params(identity)
      word = cp.safetyConfigs[0].safetyParam
      cp.flags |= int(GMFlags.HAS_BSM)
      self.assertTrue(is_ordinary_cc_profile(cp), identity)
      self.assertTrue(longitudinal_supported(cp), identity)
      self.assertTrue(lane_centering_supported(cp), identity)
      self.assertEqual(cp.safetyConfigs[0].safetyParam, word)
      for flag in (GMFlags.PEDAL_LONG, GMFlags.NO_CAMERA, 1 << 30):
        rejected = cp.as_reader().as_builder()
        rejected.flags |= int(flag)
        self.assertFalse(is_ordinary_cc_profile(rejected), (identity, flag))

  def test_bsm_metadata_preserves_actual_interface_controller_can(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus, structs
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.values import DBC
    for identity in ORDINARY_CC_CAR:
      plain = params(identity)
      bsm = plain.as_reader().as_builder()
      bsm.flags |= int(GMFlags.HAS_BSM)
      interfaces = (CarInterface(plain), CarInterface(bsm))
      for ci in interfaces:
        ci.update([])
      packer = CANPacker(DBC[identity][Bus.pt])
      control = structs.CarControl(enabled=True, latActive=True, longActive=True)
      control.actuators.torque = .1
      control.actuators.accel = .5
      control.hudControl.setSpeed = 35
      for tick in range(40):
        now = 1_000_000_000 + tick * 10_000_000
        frames = qualified_frames(packer, tick % 4)
        with_bsm = [*frames, packer.make_can_msg('BCMBlindSpotMonitor', 0, {})]
        states = [ci.update([(now, inputs)]) for ci, inputs in zip(interfaces, (frames, with_bsm), strict=True)]
        self.assertEqual(states[0].canValid, states[1].canValid, identity)
        outputs = [ci.apply(control.as_reader(), now) for ci in interfaces]
        self.assertEqual(outputs[0][0].to_dict(), outputs[1][0].to_dict(), identity)
        self.assertEqual(outputs[0][1], outputs[1][1], (identity, tick))
      self.assertTrue(states[0].canValid, identity)
      self.assertTrue(states[1].canValid, identity)

  def test_button_request_and_observed_counter_burst(self):
    self.assertEqual(button_request(20, 19, .4, 10.72896, True)[0], CruiseButtons.RES_ACCEL)
    self.assertEqual(button_request(20, 22, -.4, 10.72896, True)[0], CruiseButtons.DECEL_SET)
    cadence = ButtonCadence(True)
    self.assertFalse(cadence.ready(30, 0, CruiseButtons.RES_ACCEL, .2))
    self.assertTrue(cadence.ready(31, 0, CruiseButtons.RES_ACCEL, .2))
    self.assertFalse(cadence.ready(32, 0, CruiseButtons.RES_ACCEL, .2))
    self.assertFalse(cadence.ready(33, 1, CruiseButtons.RES_ACCEL, .2))
    self.assertTrue(cadence.ready(34, 1, CruiseButtons.RES_ACCEL, .2))

  def test_actual_packed_state_and_missing_source_steering_backstop(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus, structs
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.values import DBC
    for identity in ORDINARY_CC_CAR:
      cp = params(identity)
      ci = CarInterface(cp)
      packer = CANPacker(DBC[identity][Bus.pt])
      control = structs.CarControl(enabled=True, latActive=True, longActive=True)
      control.actuators.torque = .1
      control.actuators.accel = .5
      control.hudControl.setSpeed = 35
      for tick in range(30):
        now = 1_000_000_000 + tick * 10_000_000
        out = ci.update([(now, qualified_frames(packer, tick % 4))])
        ci.apply(control.as_reader(), now)
      self.assertTrue(out.canValid)
      self.assertFalse(out.cruiseState.nonAdaptive)
      self.assertTrue(out.cruiseState.enabled)
      self.assertTrue(ci.CS.volt_cc_physical.current(now))
      for tick in range(30, 50):
        now = 1_000_000_000 + tick * 10_000_000
        frames = [frame for frame in qualified_frames(packer, tick % 4) if frame[0] != 0xC9]
        ci.update([(now, frames)])
        actuators, _ = ci.apply(control.as_reader(), now)
      self.assertFalse(ci.CS.volt_cc_physical.sources_current(now))
      self.assertEqual(actuators.torqueOutputCan, 0)

  def test_saved_disabled_owner_preserves_lateral_without_long_takeover(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus, structs
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.startup_preferences import prepare_disable_longitudinal
    from opendbc.car.gm.values import DBC
    for identity in ORDINARY_CC_CAR:
      cp = params(identity)
      prepare_disable_longitudinal(cp, True)
      self.assertFalse(cp.openpilotLongitudinalControl)
      self.assertFalse(cp.pcmCruise)
      self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xC160)
      ci = CarInterface(cp)
      packer = CANPacker(DBC[identity][Bus.pt])
      control = structs.CarControl(enabled=True, latActive=True, longActive=True)
      control.actuators.accel = 2
      control.actuators.torque = .1
      control.hudControl.setSpeed = 35
      for tick in range(60):
        now = 1_000_000_000 + tick * 10_000_000
        ci.update([(now, qualified_frames(packer, tick % 4))])
        if tick == 59:
          control.enabled = False
        _, frames = ci.apply(control.as_reader(), now)
        self.assertEqual({frame[0] for frame in frames} - {0x180}, set())

  def test_actual_longcontrol_stopping_release_and_source_unknown(self):
    from opendbc.car.structs import CarState, CarControl
    from opendbc.car.gm.cc_longitudinal import VoltCcEvidence
    from openpilot.selfdrive.controls.lib.longcontrol import LongControl
    from openpilot.starpilot.longitudinal.extension import LongitudinalContext
    for identity in (CAR.CADILLAC_CT6_CC, CAR.CHEVROLET_MALIBU_CC):
      cp = params(identity).as_reader()
      cs = CarState.new_message(vEgo=0., canValid=True, canTimeout=False)
      cs.cruiseState.standstill = True
      controller = LongControl(cp)
      states = CarControl.Actuators.LongControlState
      output = controller.update(True, cs.as_reader(), -.5, True, (-4., 2.))
      self.assertEqual(controller.long_control_state, states.stopping)
      self.assertAlmostEqual(output, -.1118, places=6)
      for _ in range(40):
        controller.update(True, cs.as_reader(), .2, False, (-4., 2.))
        self.assertEqual(controller.long_control_state, states.stopping)
      for tick in range(35):
        evidence = VoltCcEvidence(1, 1_000_000_000 + tick * 10_000_000, False)
        context = LongitudinalContext(vehicle_stop_evidence=evidence)
        controller.update(True, cs.as_reader(), .2, False, (-4., 2.), context=context)
        self.assertEqual(controller.long_control_state, states.pid if tick == 34 else states.stopping)

  def test_held_gas_set_uses_fresh_33hz_neutral_credit_once(self):
    from opendbc.can import CANPacker
    from opendbc.car import Bus, structs
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.values import DBC
    for identity in (CAR.CADILLAC_CT6_CC, CAR.CADILLAC_XT4_CC):
      cp = params(identity)
      ci = CarInterface(cp)
      packer = CANPacker(DBC[identity][Bus.pt])
      control = structs.CarControl(enabled=True, latActive=True, longActive=False)
      control.hudControl.setSpeed = 35
      emitted = []
      for tick in range(55):
        now = 1_000_000_000 + tick * 10_000_000
        frames = [frame for frame in qualified_frames(packer, (tick // 3) % 4)
                  if frame[0] not in (0x3D1, 0x1C4) and (tick % 3 == 0 or frame[0] != 0x1E1)]
        frames += [packer.make_can_msg('ECMCruiseControl', 0, {'CruiseActive': 1, 'CruiseSetSpeed': 50}),
                   packer.make_can_msg('AcceleratorPedal2', 0, {'AcceleratorPedal2': 30})]
        ci.update([(now, frames)])
        _, commands = ci.apply(control.as_reader(), now)
        emitted += [(tick, frame) for frame in commands if frame[0] == 0x1E1]
      self.assertEqual([tick for tick, _ in emitted], [0, 52])

  def test_default_lateral_and_explicit_standard_remain_separate(self):
    from opendbc.car.gm.interface import CarInterface
    from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque, KP_INTERP, INTERP_SPEEDS
    from openpilot.starpilot.lateral.controller_selection import ControllerMode
    for identity in ORDINARY_CC_CAR:
      cp = params(identity).as_reader()
      ci = CarInterface(cp)
      owner = LatControlTorque(cp, ci, .01)
      self.assertEqual(owner.controller_policy, 'ordinary_cc')
      self.assertEqual(owner.pid._k_p, ([0], [.6]))
      self.assertEqual(owner.pid._k_i, ([0], [.35]))
      standard = LatControlTorque(cp, ci, .01, controller_mode=ControllerMode.STANDARD)
      self.assertIsNone(standard.starpilot_extension)
      self.assertEqual(standard.pid._k_p, [INTERP_SPEEDS, KP_INTERP])

  def test_actual_card_finalizes_registered_saved_choice_and_metric(self):
    import os
    from unittest.mock import patch
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.car.card import Car
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.radar_interface import RadarInterface
    for identity in (CAR.CADILLAC_CT6_CC, CAR.CADILLAC_XT4_CC):
      with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        saved = Params()
        saved.put_bool('OpenpilotEnabledToggle', True, block=True)
        saved.put_bool('DisableOpenpilotLongitudinal', True, block=True)
        saved.put_bool('IsMetric', True, block=True)
        cp = params(identity)
        ci = CarInterface(cp)
        card = Car(CI=ci, RI=RadarInterface(cp))
        self.assertFalse(card.CP.openpilotLongitudinalControl)
        self.assertFalse(card.CP.pcmCruise)
        self.assertEqual(card.CP.safetyConfigs[0].safetyParam, 0xC160)
        self.assertTrue(card.volt_cc_selected)
        self.assertTrue(card.is_metric)
        from opendbc.can import CANPacker
        from opendbc.car import Bus, structs
        from opendbc.car.gm.values import DBC
        packer = CANPacker(DBC[identity][Bus.pt])
        ci.update([(1_000_000_000, qualified_frames(packer, 0))])
        # Exercise metric transport before initialization; the separately qualified
        # envelope-clock tests own source admission, not this units regression.
        card.volt_cc_boot_offset_ns = 0
        card.volt_cc_drive_id = 1
        card.volt_cc_source_floor_ns = 0
        with patch.object(card, 'volt_cc_control_current', return_value=True):
          card.controls_update(structs.CarState(canValid=False), structs.CarControl())
        self.assertTrue(ci.CC.volt_cc_metric)
