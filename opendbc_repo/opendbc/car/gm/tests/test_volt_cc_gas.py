"""Actual Volt CC gas override is a SET-only physical speed-capture request."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_bolt_cc import feed, setup, native
from opendbc.car.gm.values import CAR, DBC
from opendbc.safety.tests.libsafety import libsafety_py


def fixture():
  fingerprint = gen_empty_fingerprint()
  fingerprint[0].update({0xBE: 6, 0x3D1: 8, 0xC9: 8, 0x1E1: 7, 0x1F5: 8, 0x34A: 5, 0x1C4: 8, 0xBD: 7})
  cp = CarInterface.get_params(CAR.CHEVROLET_VOLT_CC, fingerprint, [], False, False, False)
  return cp, CarInterface(cp), CANPacker(DBC[cp.carFingerprint][Bus.pt])


class TestVoltCcGas(unittest.TestCase):
  def prepare(self, gas=True, stock=15., active=True, brake=False, regen=False, gear=4, manual=False):
    cp, ci, packer = fixture()
    setup(cp)
    for tick in range(40):
      now = 1_000_000_000 + tick * 10_000_000
      out, sources = feed(ci, packer, now, counter=tick % 4, gas=gas, stock=stock, active=active, brake=brake, regen=regen)
      selected_gear = packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': gear, 'ManualMode': manual})
      sources = [source for source in sources if source[0] != selected_gear[0]] + [selected_gear]
      out = ci.update([(now + 1, sources)])
      if brake:
        selected = packer.make_can_msg('ECMAcceleratorPos', 0, {'BrakePedalPos': 12})
        sources = [source for source in sources if source[0] != selected[0]] + [selected]
        out = ci.update([(now + 1, sources)])
      for source in sources:
        native('rx', source, now // 1000)
    self.assertTrue(out.canValid)
    return cp, ci, packer, now

  @staticmethod
  def command(enabled=True, long_active=False, hud=25.):
    cc = structs.CarControl(enabled=enabled, latActive=True, longActive=long_active)
    cc.hudControl.setSpeed = hud
    cc.actuators.torque = .01
    return cc

  def test_actual_parser_controller_to_native_set_and_credit(self):
    safety = libsafety_py.libsafety
    release = safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    _, ci, _, now = self.prepare()
    ci.CC.frame = 156
    _, messages = ci.apply(self.command().as_reader(), now + 1)
    buttons = [message for message in messages if message[0] == 0x1E1]
    self.assertEqual(len(buttons), 1)
    self.assertEqual((buttons[0][1][5] >> 4) & 7, 3)
    self.assertEqual(safety.get_controls_allowed(), not release)
    self.assertEqual(native('tx', buttons[0], now // 1000), not release)
    ci.CC.frame = 208
    _, repeated = ci.apply(self.command().as_reader(), now + 2)
    self.assertFalse(any(message[0] == 0x1E1 for message in repeated))
    self.assertEqual(safety.get_controls_allowed(), not release)

  def test_original_reached_caller_conditions_and_current_health(self):
    for change in ('frame', 'enabled', 'long_active', 'hud_equal', 'stock_above', 'inactive', 'brake', 'regen', 'invalid', 'timeout', 'credit', 'disabled'):
      with self.subTest(change=change):
        _, ci, _, now = self.prepare(stock=21. if change == 'stock_above' else 15., active=change != 'inactive',
                                    brake=change == 'brake', regen=change == 'regen')
        cc = self.command(enabled=change != 'enabled', long_active=change == 'long_active')
        if change == 'hud_equal':
          cc.hudControl.setSpeed = ci.CS.out.vEgo
        if change == 'invalid':
          ci.CS.out.canValid = False
        if change == 'timeout':
          ci.CS.out.canTimeout = True
        if change == 'credit':
          ci.CC.volt_cc_consumed_source_ns = ci.CS.volt_cc_physical.button_credit_ns
        if change == 'disabled':
          ci.CC.CP.openpilotLongitudinalControl = False
        ci.CC.frame = 157 if change == 'frame' else 156
        _, messages = ci.apply(cc.as_reader(), now + 1)
        self.assertFalse(any(message[0] == 0x1E1 for message in messages), change)

  def test_packed_drive_low_and_disallowed_gears(self):
    safety = libsafety_py.libsafety
    release = safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    for gear in (4, 6):
      _, ci, packer, now = self.prepare(gear=gear)
      self.assertIn(ci.CS.out.gearShifter, (structs.CarState.GearShifter.drive, structs.CarState.GearShifter.low))
      ci.CC.frame = 156
      _, messages = ci.apply(self.command().as_reader(), now + 2)
      buttons = [message for message in messages if message[0] == 0x1E1]
      self.assertEqual(len(buttons), 1)
      self.assertEqual(native('tx', buttons[0], now // 1000), not release)
      self.assertNotEqual(ci.CC.apply_torque_last, 0)
      stamp = now + 10_000_000
      changed = packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 6 if gear == 4 else 4})
      ci.update([(stamp, [changed])])
      native('rx', changed, stamp // 1000)
      ci.CC.frame = 208
      _, reused = ci.apply(self.command().as_reader(), stamp + 1)
      self.assertFalse(any(message[0] == 0x1E1 for message in reused))
      self.assertEqual(safety.get_controls_allowed(), not release)
    for gear, manual in ((0, False), (1, False), (2, False), (4, True), (6, True)):
      _, ci, _, now = self.prepare(gear=gear, manual=manual)
      ci.CC.frame = 156
      _, messages = ci.apply(self.command().as_reader(), now + 2)
      self.assertFalse(any(message[0] == 0x1E1 for message in messages))
      self.assertEqual(ci.CC.apply_torque_last, 0)
