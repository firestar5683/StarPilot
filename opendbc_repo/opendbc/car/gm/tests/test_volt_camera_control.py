"""Exact camera-present manual Volt owner; source conditioning is independent of SASCM."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.longitudinal import volt_policy_for
from opendbc.car.gm.radar_interface import RadarInterface
from opendbc.car.gm.tests.test_bolt_cc import feed, setup, native
from opendbc.car.gm.values import (CAR, DBC, CarControllerParams, is_volt_camera_longitudinal,
                                  requires_camera_state_sources, uses_camera_stock_controls)
from opendbc.safety.tests.libsafety import libsafety_py


def camera_params(alpha=True, release=False, camera_length=6, radar=False, sascm=False, pedal=False):
  fingerprint = gen_empty_fingerprint()
  if camera_length is not None:
    fingerprint[2][0x320] = camera_length
  if radar:
    fingerprint[1][0x460] = 8
  if sascm:
    fingerprint[0][0x2FF] = 8
  if pedal:
    fingerprint[0][0x201] = 6
  return CarInterface.get_params(CAR.CHEVROLET_VOLT_CAMERA, fingerprint, [], alpha, release, False)


def feed_camera(ci, packer, now, *, counter=0, speed=20., gas=False, brake=False, regen=False, low=False, active=True):
  _, messages = feed(ci, packer, now, counter=counter, speed=speed, gas=gas, brake=brake, regen=regen)
  messages = [message for message in messages if message[0] not in (0x1C4, 0x1F5)]
  messages += [packer.make_can_msg("AcceleratorPedal2", 0, {"CruiseState": 2 if active else 0, "AcceleratorPedal2": 30 if gas else 0}),
               packer.make_can_msg("ECMPRDNL2", 0, {"PRNDL2": 6 if low else 4}),
               packer.make_can_msg("ASCMActiveCruiseControlStatus", 2, {"ACCCruiseState": 3, "ACCSpeedSetpoint": 60})]
  ci.update([(now - 1_000_000, messages)])
  out = ci.update([(now, messages)])
  return out, messages


class TestVoltCameraControl(unittest.TestCase):
  def test_actual_startup_matrix_and_receive_only_radar(self):
    for alpha in (False, True):
      for release in (False, True):
        for radar in (False, True):
          for sascm in (False, True):
            for length in (None, 5, 6):
              cp = camera_params(alpha, release, length, radar, sascm, pedal=True)
              present = length == 6
              active = present and alpha and not release
              self.assertEqual(cp.dashcamOnly, not present)
              self.assertEqual(cp.openpilotLongitudinalControl, active)
              self.assertEqual(cp.pcmCruise, not active)
              self.assertEqual(cp.safetyConfigs[0].safetyParam, 0x4007 if active else 5)
              self.assertEqual(is_volt_camera_longitudinal(cp), active)
              self.assertEqual(uses_camera_stock_controls(cp), not active)
              self.assertTrue(requires_camera_state_sources(cp))
              self.assertEqual(cp.radarUnavailable, not radar if present else True)
              self.assertEqual(RadarInterface(cp).rcp is None, cp.radarUnavailable)
              if active:
                from opendbc.car.gm.values import apply_volt_auto_hold, is_volt_auto_hold
                from opendbc.car.gm.lateral import lane_centering_supported
                from opendbc.car.gm.aol import qualified_gm
                marked = cp.as_reader().as_builder()
                apply_volt_auto_hold(marked, True)
                self.assertTrue(is_volt_auto_hold(marked))
                self.assertEqual(lane_centering_supported(marked), lane_centering_supported(cp))
                self.assertEqual(qualified_gm(marked), qualified_gm(cp))
                self.assertEqual(marked.lateralTuning.to_dict(), cp.lateralTuning.to_dict())
                self.assertEqual(volt_policy_for(marked).stopping_decel_rate, volt_policy_for(cp).stopping_decel_rate)
                self.assertEqual(list(cp.longitudinalTuning.kiV), [.5, .5])
                self.assertEqual(cp.stopAccel, -.25)
                self.assertEqual(volt_policy_for(cp).stopping_decel_rate, 1.)
                parameters = CarControllerParams(cp)
                self.assertEqual((parameters.MAX_GAS, parameters.MAX_ACC_REGEN, parameters.INACTIVE_REGEN), (2698., -540., -500.))

  def test_packed_parser_controller_default_messages_and_gas_lateral_override(self):
    for alpha in (False, True):
      for radar in (False, True):
        cp = camera_params(alpha=alpha, radar=radar)
        ci = CarInterface(cp)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        for tick in range(24):
          now = 1_000_000_000 + tick * 40_000_000
          gas = tick >= 12
          out, _ = feed_camera(ci, packer, now, counter=tick % 4, gas=gas, low=tick % 2 == 0)
          self.assertTrue(out.canValid)
          self.assertEqual(out.gearShifter, structs.CarState.GearShifter.low if tick % 2 == 0 else structs.CarState.GearShifter.drive)
          cc = structs.CarControl(enabled=True, latActive=True, longActive=alpha and not gas)
          cc.actuators.torque = .1
          cc.actuators.accel = 1.
          cc.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
          ci.CC.frame = tick * 4
          _, messages = ci.apply(cc.as_reader(), now)
          self.assertFalse(any(message[0] in (0x200, 0xBD, 0x1F5, 0x3D1, 0xA1, 0x306, 0x308, 0x310) for message in messages))
          if alpha:
            self.assertEqual({message[0] for message in messages if message[0] in (0x2CB, 0x315, 0x2CD)}, {0x2CB, 0x315, 0x2CD})
            self.assertTrue(all(message[2] == 0 for message in messages if message[0] in (0x315, 0x2CB, 0x2CD)))
            if gas:
              self.assertNotEqual(ci.CC.apply_torque_last, 0)
              self.assertEqual((ci.CC.apply_gas, ci.CC.apply_brake), (-500., 0))
          else:
            if gas:
              self.assertNotEqual(ci.CC.apply_torque_last, 0)
            self.assertFalse(any(message[0] in (0x2CB, 0x315, 0x2CD) for message in messages))

  def test_required_camera_and_pt_sources_expire_without_changing_owner(self):
    cp = camera_params()
    ci = CarInterface(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    now = 1_000_000_000
    out, messages = feed_camera(ci, packer, now)
    self.assertTrue(out.canValid)
    cc = structs.CarControl(enabled=True, latActive=True, longActive=False)
    cc.actuators.torque = .1
    ci.CC.frame = 3  # First eligible steering slot; frame zero intentionally sends no command.
    ci.apply(cc.as_reader(), now)
    self.assertNotEqual(ci.CC.apply_torque_last, 0)
    only_pt = [message for message in messages if message[2] == 0]
    for tick in range(1, 50):
      stamp = now + tick * 40_000_000
      ci.update([(stamp, only_pt)])
    self.assertFalse(ci.CS.out.canValid)
    ci.CC.frame += 10
    ci.apply(cc.as_reader(), stamp)
    self.assertEqual(ci.CC.apply_torque_last, 0)
    self.assertEqual(cp.safetyConfigs[0].safetyParam, 0x4007)

  def test_actual_native_accepts_packed_commands_and_stock_ownership(self):
    safety = libsafety_py.libsafety
    release = safety.set_safety_hooks(int(structs.CarParams.SafetyModel.allOutput), 0) != 0
    for alpha in (False, True):
      cp = camera_params(alpha=alpha, release=release)
      ci = CarInterface(cp)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      setup(cp)
      for tick in range(12):
        now = 1_000_000_000 + tick * 40_000_000
        out, sources = feed_camera(ci, packer, now, counter=tick % 4)
        self.assertTrue(out.canValid)
        for source in sources:
          native("rx", source, now // 1000)
        if cp.openpilotLongitudinalControl:
          native("rx", packer.make_can_msg("ASCMSteeringButton", 0, {"ACCButtons": 2}), now // 1000)
        safety.safety_tick()
        self.assertTrue(safety.safety_config_valid())
        cc = structs.CarControl(enabled=True, latActive=True, longActive=cp.openpilotLongitudinalControl)
        cc.actuators.accel = -2. if tick % 2 else 1.
        cc.actuators.torque = .01
        cc.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
        ci.CC.frame = tick * 4
        _, messages = ci.apply(cc.as_reader(), now)
        for message in messages:
          self.assertTrue(native("tx", message, now // 1000), hex(message[0]))
