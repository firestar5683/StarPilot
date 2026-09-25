import unittest

from opendbc.can import CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.ford.carcontroller import CarController, apply_creep_compensation
from opendbc.car.ford.carstate import CarState
from opendbc.car.ford.interface import CarInterface
from opendbc.car.ford.values import CAR, DBC


class TestCreepCompensation(unittest.TestCase):
  def test_mach_e_only_compensates_while_holding_a_stop(self):
    for standstill, stopping in ((False, False), (True, False), (False, True)):
      for accel in (-1., -.1, 0., .1, .2, 1.):
        for speed in (0., .5, 1., 2., 3., 10.):
          self.assertEqual(apply_creep_compensation(accel, speed, CAR.FORD_MUSTANG_MACH_E_MK1,
                                                   standstill=standstill, stopping=stopping), accel)
    for candidate in CAR:
      for standstill, stopping in ((False, False), (True, False), (False, True), (True, True)):
        if candidate == CAR.FORD_MUSTANG_MACH_E_MK1 and not (standstill and stopping):
          continue
        self.assertAlmostEqual(apply_creep_compensation(0., .5, candidate,
                                                       standstill=standstill, stopping=stopping), -.6)
        self.assertAlmostEqual(apply_creep_compensation(.1, 2., candidate,
                                                       standstill=standstill, stopping=stopping), -.05)
        self.assertAlmostEqual(apply_creep_compensation(.2, 3., candidate,
                                                       standstill=standstill, stopping=stopping), .2)

  def test_controller_brake_hold_release_and_inactive_commands(self):
    for candidate in (CAR.FORD_MUSTANG_MACH_E_MK1, CAR.FORD_F_150_MK14):
      fingerprint = gen_empty_fingerprint()
      fingerprint[0][0x5A] = 8
      fingerprint[2].update({0x3D6: 8, 0x186: 8})
      cp = CarInterface.get_params(candidate, fingerprint, [], True, False, False)
      self.assertTrue(cp.openpilotLongitudinalControl)
      state = CarState(cp)
      state.update(state.get_can_parsers(cp))
      controller = CarController(DBC[candidate], cp)
      controller.accel = -.6
      parser = CANParser(DBC[candidate][Bus.pt], [('ACCDATA', 50)], controller.CAN.main)
      command = structs.CarControl()
      command.longActive = True
      output = structs.CarState()
      for index, (standstill, stopping, active, target, expected, brake_request) in enumerate((
        (True, True, True, 0., -.6, True),
        (False, False, True, 0., 0. if candidate == CAR.FORD_MUSTANG_MACH_E_MK1 else -.6, True),
        (True, False, True, 0., 0. if candidate == CAR.FORD_MUSTANG_MACH_E_MK1 else -.6, True),
        (False, False, True, .4, .4, False),
        (True, True, False, 0., 0., False),
      )):
        controller.frame = 2 * index
        command.longActive = active
        command.actuators.accel = target
        command.actuators.longControlState = 'stopping' if stopping else 'pid'
        output.standstill = standstill
        output.vEgo = output.vEgoRaw = 0. if standstill else .5
        state.out = output.as_reader()
        applied, messages = controller.update(command.as_reader(), state, (index + 1) * 20_000_000)
        acc = [message for message in messages if message[0] == 0x186]
        self.assertEqual(len(acc), 1)
        self.assertEqual(acc[0][2], controller.CAN.main)
        parser.update([((index + 1) * 20_000_000, acc)])
        decoded = parser.vl['ACCDATA']
        self.assertAlmostEqual(decoded['AccBrkTot_A_Rq'], expected, delta=.0039)
        self.assertAlmostEqual(applied.accel, expected, places=5)
        self.assertEqual(decoded['Cmbb_B_Enbl'], int(active))
        self.assertEqual(decoded['AccStopStat_B_Rq'], int(stopping))
        self.assertEqual(decoded['AccBrkDecel_B_Rq'], int(brake_request))


if __name__ == '__main__':
  unittest.main()
