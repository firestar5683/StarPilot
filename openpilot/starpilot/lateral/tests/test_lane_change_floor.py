from dataclasses import replace
from types import SimpleNamespace
import unittest

from openpilot.cereal import log
from openpilot.selfdrive.controls.lib.desire_helper import DesireHelper, LANE_CHANGE_SPEED_MIN
from openpilot.starpilot.lateral.lane_change_preferences import LaneChangePolicy, MINIMUM_SPEED_MPS, SavedLaneChange, effective
from openpilot.starpilot.lateral.lane_change_smoothing import LaneChangeSmoother


def state(speed, signal=True, torque=False):
  return SimpleNamespace(vEgo=speed, leftBlinker=signal, rightBlinker=False,
                         steeringPressed=torque, steeringTorque=1. if torque else 0., leftBlindspot=False, rightBlindspot=False)


class TestLaneChangeFloor(unittest.TestCase):
  def test_default_and_saved_zero_have_five_mph_floor(self):
    self.assertAlmostEqual(LaneChangePolicy().minimum_speed_mps, 5 * .44704)
    saved = SavedLaneChange(b'legacy', LaneChangePolicy(minimum_speed_mps=0.))
    self.assertEqual(effective(saved).minimum_speed_mps, MINIMUM_SPEED_MPS)
    self.assertEqual(saved.policy.minimum_speed_mps, 0.)
    above = replace(saved, policy=LaneChangePolicy(minimum_speed_mps=10.))
    self.assertEqual(effective(above).minimum_speed_mps, 10.)

  def test_manual_and_auto_cannot_start_below_floor(self):
    for auto in (False, True):
      for speed in (0., MINIMUM_SPEED_MPS - 1e-6, MINIMUM_SPEED_MPS):
        with self.subTest(auto=auto, speed=speed):
          helper = DesireHelper(LaneChangePolicy(minimum_speed_mps=0., auto_lane_change=auto, auto_delay_s=0.))
          helper.update(state(speed, False), True, 1., engaged=True, auto_evidence=True)
          helper.update(state(speed), True, 1., engaged=True, auto_evidence=True)
          helper.update(state(speed, torque=True), True, 1., engaged=True, auto_evidence=True)
          expected = log.LaneChangeState.off if speed < MINIMUM_SPEED_MPS else log.LaneChangeState.laneChangeStarting
          self.assertEqual(helper.lane_change_state, expected)

  def test_speed_drop_and_changed_policy_cancel_active_maneuver(self):
    helper = DesireHelper(LaneChangePolicy(minimum_speed_mps=0.))
    helper.update(state(10., False), True, 1.)
    helper.update(state(10.), True, 1.)
    helper.update(state(10., torque=True), True, 1.)
    self.assertEqual(helper.lane_change_state, log.LaneChangeState.laneChangeStarting)
    helper.policy = replace(helper.policy, minimum_speed_mps=15.)
    helper.update(state(10., torque=True), True, 1.)
    self.assertEqual(helper.lane_change_state, log.LaneChangeState.off)
    helper.policy = replace(helper.policy, minimum_speed_mps=0.)
    helper.update(state(MINIMUM_SPEED_MPS - 1e-6, torque=True), True, 1.)
    self.assertEqual(helper.lane_change_state, log.LaneChangeState.off)
    helper.update(state(10., torque=True), True, 1.)
    self.assertEqual(helper.lane_change_state, log.LaneChangeState.off)

  def test_turn_assist_intersection_exemption_remains_independent(self):
    self.assertAlmostEqual(LANE_CHANGE_SPEED_MIN, 20 * .44704)
    smoother = LaneChangeSmoother()
    self.assertEqual(smoother.factor(active=True, lane_change_state=log.LaneChangeState.laneChangeStarting,
      speed=MINIMUM_SPEED_MPS / 2, minimum_speed=MINIMUM_SPEED_MPS, duration=6., previous=0., desired=.01, turn_assist=True), 1.)
