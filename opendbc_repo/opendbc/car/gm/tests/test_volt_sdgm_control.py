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
                from opendbc.car.gm.values import apply_volt_auto_hold, is_volt_auto_hold
                from opendbc.car.gm.aol import qualified_gm
                from opendbc.car.gm.lateral import lane_centering_supported
                marked = cp.as_reader().as_builder()
                apply_volt_auto_hold(marked, True)
                self.assertTrue(is_volt_auto_hold(marked))
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
