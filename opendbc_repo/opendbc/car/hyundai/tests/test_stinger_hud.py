import itertools
import unittest

from opendbc.can import CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC


def controller(car, alpha):
  cp = CarInterface.get_params(car, gen_empty_fingerprint(), [], alpha, False, False)
  cc = CarController(DBC[cp.carFingerprint], cp)
  cs = CarState(cp)
  cs.out = structs.CarState.new_message(vEgo=15., vEgoRaw=15.)
  cs.out.gearShifter = structs.CarState.GearShifter.drive
  parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [('LKAS11', 0), ('CLU11', 0)], 0)
  cs.lkas11, cs.clu11 = parser.vl['LKAS11'], parser.vl['CLU11']
  return cc, cs, parser


class TestStingerHud(unittest.TestCase):
  def test_lkas_cluster_status_matches_active_lateral(self):
    for car, alpha, enabled, lateral in itertools.product(
        (CAR.KIA_STINGER_2022, CAR.KIA_STINGER, CAR.HYUNDAI_SONATA), (False, True), (False, True), (False, True)):
      with self.subTest(car=car, alpha=alpha, enabled=enabled, lateral=lateral):
        cc, cs, parser = controller(car, alpha)
        command = structs.CarControl.new_message(enabled=enabled, latActive=lateral)
        command.hudControl.leftLaneVisible = command.hudControl.rightLaneVisible = True
        command.hudControl.setSpeed = 25.
        command.actuators.torque = .3
        for tick in range(2):
          _, frames = cc.update(command.as_reader(), cs, (tick + 1) * 10_000_000)
          parser.update([((tick + 1) * 10_000_000, frames)])
        hud_active = enabled or (car == CAR.KIA_STINGER_2022 and lateral)
        values = parser.vl['LKAS11']
        self.assertEqual(values['CF_Lkas_LdwsSysState'], 3 if hud_active else 4)
        if car != CAR.KIA_STINGER:
          self.assertEqual(values['CF_Lkas_FcwOpt_USM'], 2 if hud_active else 1)
        self.assertEqual(values['CF_Lkas_ActToi'], int(lateral))
        self.assertEqual(values['CF_Lkas_ToiFlt'], 0)
        self.assertEqual(values['CF_Lkas_MsgCount'], 1)
        if not lateral:
          self.assertEqual(values['CR_Lkas_StrToqReq'], 0)

  def test_lateral_hud_keeps_lane_warnings_and_driver_alerts(self):
    for left, right, alert in itertools.product((False, True), (False, True),
                                              (structs.CarControl.HUDControl.VisualAlert.none,
                                               structs.CarControl.HUDControl.VisualAlert.steerRequired)):
      cc, cs, parser = controller(CAR.KIA_STINGER_2022, False)
      command = structs.CarControl.new_message(enabled=False, latActive=True)
      command.hudControl.leftLaneVisible, command.hudControl.rightLaneVisible = left, right
      command.hudControl.leftLaneDepart, command.hudControl.rightLaneDepart = True, True
      command.hudControl.visualAlert = alert
      _, frames = cc.update(command.as_reader(), cs, 10_000_000)
      parser.update([(10_000_000, frames)])
      values = parser.vl['LKAS11']
      warning = alert == structs.CarControl.HUDControl.VisualAlert.steerRequired
      self.assertEqual(values['CF_Lkas_LdwsSysState'], 3 if (left and right) or warning else 5 if left else 6 if right else 1)
      self.assertEqual(values['CF_Lkas_SysWarning'], 4 if warning else 0)
      self.assertEqual(values['CF_Lkas_LdwsLHWarning'], 2)
      self.assertEqual(values['CF_Lkas_LdwsRHWarning'], 2)
      self.assertEqual(values['CF_Lkas_LdwsActivemode'], int(left) + 2 * int(right))


if __name__ == '__main__':
  unittest.main()
