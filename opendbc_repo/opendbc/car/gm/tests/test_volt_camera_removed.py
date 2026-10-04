"""Manual Volt PT-state camera fallback, with explicit cancellation ownership."""
import unittest
from types import SimpleNamespace

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_bolt_cc import feed, setup, native
from opendbc.car.gm.values import CAR, DBC, GMFlags, is_volt_camera_removed
from opendbc.safety.tests.libsafety import libsafety_py


def removed_params(alpha=True, release=False, alternate=False, sascm=False):
  fingerprint = gen_empty_fingerprint()
  fingerprint[0] = {0x184: 8, 0x34A: 5, 0x1C4: 8, 0xC9: 8, 0x1E1: 7, 0xF1 if alternate else 0xBE: 6}
  if sascm:
    fingerprint[0][0x2FF] = 8
  return CarInterface.get_params(CAR.CHEVROLET_VOLT_CAMERA, fingerprint, [], alpha, release, False)


def feed_removed(ci, packer, now, *, counter=0, gas=False, brake=False, low=False, active=True, speed=20.):
  _, messages = feed(SimpleNamespace(update=lambda messages: None), packer, now, counter=counter, gas=gas, brake=brake, speed=speed)
  messages = [m for m in messages if m[2] == 0 and m[0] not in (0x1C4, 0x1F5, 0xBE)]
  messages += [packer.make_can_msg("AcceleratorPedal2", 0, {"CruiseState": 2 if active else 0,
                                                          "AcceleratorPedal2": 30 if gas else 0}),
               packer.make_can_msg("ECMPRDNL2", 0, {"PRNDL2": 6 if low else 4})]
  alternate = bool(ci.CP.flags & GMFlags.VOLT_CAMERA_NO_ACCEL_POS)
  messages.append(packer.make_can_msg("EBCMBrakePedalPosition" if alternate else "ECMAcceleratorPos", 0,
                                     {"BrakePedalPosition": 104} if alternate else {"BrakePedalPos": 4}))
  ci.update([(now, messages)])
  return ci.update([(now + 1, messages)]), messages


class TestVoltCameraRemoved(unittest.TestCase):
  def test_startup_matrix_and_malformed_sources(self):
    for alpha in (False, True):
      for release in (False, True):
        for alternate in (False, True):
          for sascm in (False, True):
            cp = removed_params(alpha, release, alternate, sascm)
            enabled = alpha and not release
            self.assertTrue(is_volt_camera_removed(cp))
            self.assertFalse(cp.dashcamOnly)
            self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xC151 if enabled else 0xC150)
            self.assertEqual(cp.openpilotLongitudinalControl, enabled)
            self.assertEqual(cp.pcmCruise, not enabled)
            from opendbc.car.gm.lateral import lane_centering_supported
            from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
            from openpilot.starpilot.lateral.torque_extension import selected_policy
            from openpilot.starpilot.lateral.volt_policy import VoltTorquePolicy
            self.assertTrue(lane_centering_supported(cp))
            controller = LatControlTorque(cp.as_reader(), CarInterface(cp), .01)
            self.assertIsInstance(selected_policy(controller), VoltTorquePolicy)
    for address in (0x184, 0x34A, 0x1C4, 0xC9, 0x1E1, 0xBE):
      fingerprint = gen_empty_fingerprint()
      fingerprint[0] = {0x184: 8, 0x34A: 5, 0x1C4: 8, 0xC9: 8, 0x1E1: 7, 0xBE: 6}
      fingerprint[0][address] -= 1
      cp = CarInterface.get_params(CAR.CHEVROLET_VOLT_CAMERA, fingerprint, [], True, False, False)
      self.assertTrue(cp.dashcamOnly)
      self.assertFalse(is_volt_camera_removed(cp))

  def test_actual_pt_parser_and_source_selected_brake(self):
    for alternate in (False, True):
      cp = removed_params(alternate=alternate)
      ci = CarInterface(cp)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      for tick in range(20):
        now = 1_000_000_000 + tick * 40_000_000
        out, _ = feed_removed(ci, packer, now, counter=tick % 4, gas=True, low=True, brake=tick >= 10)
        self.assertTrue(out.canValid)
        self.assertEqual(out.brakePressed, tick >= 10)
        raw = (ci.can_parsers[Bus.pt].vl["EBCMBrakePedalPosition"]["BrakePedalPosition"] if alternate else
               ci.can_parsers[Bus.pt].vl["ECMAcceleratorPos"]["BrakePedalPos"])
        self.assertEqual(raw / 208. if alternate else raw, .5 if alternate else 4.)
        self.assertTrue(out.gasPressed)
        self.assertTrue(out.cruiseState.enabled)
        self.assertFalse(out.stockAeb or out.stockFcw or out.cruiseState.nonAdaptive)
        self.assertEqual(out.gearShifter, structs.CarState.GearShifter.low)

  def test_actual_commands_and_pt_cancel_slot(self):
    release = libsafety_py.libsafety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    for alpha in (False, True):
      cp = removed_params(alpha=alpha, release=release)
      ci = CarInterface(cp)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      setup(cp)
      cancelled = 0
      for tick in range(32):
        now = 1_000_000_000 + tick * 40_000_000
        out, sources = feed_removed(ci, packer, now, counter=tick % 4, gas=tick >= 16, low=True)
        self.assertTrue(out.canValid)
        for source in sources:
          native("rx", source, now // 1000)
        if cp.openpilotLongitudinalControl:
          native("rx", packer.make_can_msg("ASCMSteeringButton", 0, {"ACCButtons": 2}), now // 1000)
        cc = structs.CarControl(enabled=True, latActive=True, longActive=cp.openpilotLongitudinalControl and tick < 16)
        cc.actuators.torque = .01
        cc.actuators.accel = -2. if tick % 2 else 1.
        cc.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
        cc.cruiseControl.cancel = not cp.openpilotLongitudinalControl
        ci.CC.frame = tick * 4
        _, commands = ci.apply(cc.as_reader(), now + 1)
        self.assertFalse(any(m[0] in (0x2CD, 0x3D1, 0x200, 0xBD, 0x1F5, 0xA1, 0x306, 0x308, 0x310) for m in commands))
        if cp.openpilotLongitudinalControl:
          self.assertTrue(all(native("tx", m, now // 1000) for m in commands))
          self.assertTrue(any(m[0] == 0x370 for m in commands))
          if ci.CC.frame - 1 == 100:
            self.assertEqual([m[0] for m in commands if m[0] in (0x409, 0x40A)], [0x409, 0x40A])
        else:
          self.assertFalse(any(m[0] in (0x315, 0x2CB, 0x370, 0x409, 0x40A) for m in commands))
          for message in commands:
            if message[0] == 0x1E1:
              cancelled += 1
              self.assertEqual(message[2], 0)
              self.assertTrue(native("tx", message, now // 1000))
              self.assertFalse(native("tx", message, now // 1000))
      if not cp.openpilotLongitudinalControl:
        self.assertGreater(cancelled, 0)

  def test_pt_source_expiry_future_clock_and_no_camera_subscription(self):
    cp = removed_params()
    ci = CarInterface(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    now = 1_000_000_000
    out, sources = feed_removed(ci, packer, now)
    self.assertTrue(out.canValid)
    cc = structs.CarControl(enabled=True, latActive=True, longActive=False)
    cc.actuators.torque = .1
    for step, clock in enumerate((now - 1, now + 400_000_000)):
      ci.CC.frame = 104 + step * 4
      _, commands = ci.apply(cc.as_reader(), clock)
      steer = next(m for m in commands if m[0] == 0x180)
      self.assertEqual(int.from_bytes(steer[1][:2], 'big') & 0x7FF, 0)
    later = now + 1_000_000_000
    without_c9 = [m for m in sources if m[0] != 0xC9]
    out = ci.update([(later, without_c9)])
    self.assertTrue(out.canValid)  # The parser retains its five-update debounce.
    ci.CC.frame = 112
    _, commands = ci.apply(cc.as_reader(), later)
    steer = next(m for m in commands if m[0] == 0x180)
    self.assertEqual(int.from_bytes(steer[1][:2], 'big') & 0x7FF, 0)
    for frame in range(1, 5):
      out = ci.update([(later + frame * 10_000_000, without_c9)])
    self.assertFalse(out.canValid)
    ci.CC.frame = 116
    _, commands = ci.apply(cc.as_reader(), later + 40_000_000)
    steer = next(m for m in commands if m[0] == 0x180)
    self.assertEqual(int.from_bytes(steer[1][:2], 'big') & 0x7FF, 0)
    self.assertFalse(ci.can_parsers[Bus.cam].vl)
