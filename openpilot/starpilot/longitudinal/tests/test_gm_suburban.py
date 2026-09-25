"""Suburban stopping ramp through the production longitudinal controller."""

import unittest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR
from openpilot.selfdrive.controls.lib.longcontrol import LongControl


def params(candidate=CAR.CHEVROLET_SUBURBAN):
  fingerprint = gen_empty_fingerprint()
  fingerprint[1][0x460] = 8
  return CarInterface.get_params(candidate, fingerprint, [], False, False, False)


class TestSuburbanStop(unittest.TestCase):
  def test_actual_stopping_ramp_and_profile_isolation(self):
    cp = params()
    state = structs.CarState(vEgo=0.1)
    owner = LongControl(cp)
    self.assertEqual(owner.stopping_decel_rate, 0.8)
    for tick in range(1, 51):
      accel = owner.update(True, state, 0.0, True, (-4.0, 2.0))
      self.assertAlmostEqual(accel, -0.008 * tick)
    self.assertEqual(owner.long_control_state, structs.CarControl.Actuators.LongControlState.stopping)
    self.assertEqual(owner.update(False, state, 0.0, True, (-4.0, 2.0)), 0.0)
    self.assertEqual(LongControl(params(CAR.CHEVROLET_SUBURBAN_ASCM)).stopping_decel_rate, 1.0)
    for field, value in (("openpilotLongitudinalControl", False), ("pcmCruise", True),
                         ("networkLocation", structs.CarParams.NetworkLocation.fwdCamera)):
      rejected = params()
      setattr(rejected, field, value)
      self.assertEqual(LongControl(rejected).stopping_decel_rate, 1.0)
    rejected = params()
    rejected.safetyConfigs[0].safetyParam = 1
    self.assertEqual(LongControl(rejected).stopping_decel_rate, 1.0)
