import unittest
from unittest.mock import patch

from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import A_CHANGE_COST, LongitudinalMpc
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.plannerd import update_curve_frame
from openpilot.starpilot.curve_speed.host import CurveHost
from openpilot.starpilot.longitudinal.follow_jerk import FollowJerk
from openpilot.starpilot.longitudinal.force_stop import StopPlan
from openpilot.starpilot.longitudinal.profile_runtime import ProfileTuning
from openpilot.starpilot.longitudinal.tests.test_lead_approach_planner import Frame, DRIVE_NS


def params(car=CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN):
  cp = CarInterface.get_non_essential_params(car)
  cp.openpilotLongitudinalControl = True
  cp.pcmCruise = False
  return cp


class FollowJerkTests(unittest.TestCase):
  def frame(self, index):
    sm = Frame(index).with_drive()
    sm['modelV2'].position.x = [float(index * 5) for index in range(33)]
    sm['modelV2'].position.y = [0.] * 33
    sm['modelV2'].timestampEof = sm.logMonoTime['modelV2'] + 20_000_000_000
    return sm

  def test_actual_detector_tracking_stop_precedence_and_epoch_reset(self):
    owner = FollowJerk(params())
    scales = []
    for index in range(20):
      sm = self.frame(index)
      owner.clock_pair = lambda sm=sm: (sm.now_ns, sm.now_ns + 20_000_000_000)
      scales.append(owner.sample(sm, params(), sm.now_ns, 1.8, StopPlan(), active=True, drive_id=DRIVE_NS))
    self.assertEqual(scales[0], 1.)
    self.assertEqual(scales[-1], 1.75)
    for index, stop in enumerate((StopPlan(forcing=True), StopPlan(approach_distance_m=.1)), 20):
      sm = self.frame(index)
      owner.clock_pair = lambda sm=sm: (sm.now_ns, sm.now_ns + 20_000_000_000)
      self.assertEqual(owner.sample(sm, params(), sm.now_ns, 1.8, stop, active=True, drive_id=DRIVE_NS), 1.)
    sm = self.frame(22)
    owner.clock_pair = lambda sm=sm: (sm.now_ns, sm.now_ns + 20_000_000_000)
    sm.valid['radarState'] = False
    self.assertEqual(owner.sample(sm, params(), sm.now_ns, 1.8, StopPlan(), active=True, drive_id=DRIVE_NS), 1.)
    self.assertFalse(owner.detector.tracked)
    sm = self.frame(23)
    owner.clock_pair = lambda sm=sm: (sm.now_ns, sm.now_ns + 40_000_000_000)
    self.assertEqual(owner.sample(sm, params(), sm.now_ns, 1.8, StopPlan(), active=True, drive_id=DRIVE_NS), 1.)

    for index, defect in enumerate(('inactive', 'stale', 'future', 'drive'), 24):
      sm = self.frame(index)
      owner.clock_pair = lambda sm=sm: (sm.now_ns, sm.now_ns + 40_000_000_000)
      if defect == 'stale':
        sm.logMonoTime['radarState'] = sm.now_ns - 250_000_001
      if defect == 'future':
        sm.logMonoTime['modelV2'] = sm.now_ns + 1
      self.assertEqual(owner.sample(sm, params(), sm.now_ns, 1.8, StopPlan(), active=defect != 'inactive',
                                    drive_id=DRIVE_NS + 1 if defect == 'drive' else DRIVE_NS), 1.)
      self.assertFalse(owner.detector.tracked)

  def test_sibling_noop_never_samples_clock_or_detector(self):
    owner = FollowJerk(params(CAR.KIA_EV6), clock_pair=lambda: self.fail('sibling clock sampled'))
    with patch.object(owner.detector, 'step', side_effect=AssertionError('sibling tracker sampled')):
      self.assertEqual(owner.sample(None, None, 0, None, None, active=True, drive_id=1), 1.)

  def test_actual_planner_join_uses_selected_headway_before_weights_without_curve(self):
    planner = LongitudinalPlanner(params(), init_v=21.535)
    recorded = []
    original = planner.mpc.set_weights
    def weights(*args, **kwargs):
      recorded.append(kwargs['acceleration_change_scale'])
      return original(*args, **kwargs)
    with patch.object(planner.mpc, 'set_weights', side_effect=weights):
      for index in range(20):
        sm = self.frame(index)
        planner.follow_jerk.clock_pair = lambda sm=sm: (sm.now_ns, sm.now_ns + 20_000_000_000)
        update_curve_frame(planner, sm, planner.CP, sm.now_ns, host=None, drive_id=DRIVE_NS)
    self.assertEqual(recorded[-1], 1.75)
    self.assertTrue(planner.follow_jerk.detector.tracked)
    sm = self.frame(20)
    planner.follow_jerk.clock_pair = lambda: (sm.now_ns, sm.now_ns + 20_000_000_000)
    with patch.object(planner.mpc, 'set_weights', side_effect=weights):
      planner.update(sm, now_ns=sm.now_ns, drive_id=DRIVE_NS,
                     force_stop_provider=lambda _: StopPlan(model_ns=sm.logMonoTime['modelV2'], forcing=True))
    self.assertTrue(planner.force_stop_plan.forcing)
    self.assertEqual(recorded[-1], 1.)
    sm = self.frame(21)
    planner.follow_jerk.clock_pair = lambda: (sm.now_ns, sm.now_ns + 20_000_000_000)
    headways = []
    with patch.object(planner.mpc, 'set_weights', side_effect=weights), \
         patch.object(planner.follow_jerk.detector, 'step', wraps=planner.follow_jerk.detector.step) as detected:
      planner.update(sm, now_ns=sm.now_ns, drive_id=DRIVE_NS,
                     profile_tuning=ProfileTuning('standard', 1.8, 1., 1., 1., 1., 1.),
                     force_stop_provider=lambda headway: (headways.append(headway) or StopPlan(model_ns=1, forcing=True)))
    self.assertFalse(planner.force_stop_plan.forcing)
    self.assertEqual(recorded[-1], 1.75)
    self.assertEqual(headways, [planner.last_profile.follow_seconds])
    self.assertEqual(detected.call_args.kwargs['t_follow_s'], headways[0])
    self.assertEqual(planner.mpc.solution_status, 0)
    sm = self.frame(22)
    planner.follow_jerk.clock_pair = lambda: (sm.now_ns, sm.now_ns + 20_000_000_000)
    with patch.object(planner.mpc, 'set_weights', side_effect=weights):
      update_curve_frame(planner, sm, planner.CP, sm.now_ns, host=CurveHost(enabled=False, replay=True), drive_id=DRIVE_NS)
    self.assertEqual(recorded[-1], 1.75)

  def test_actual_mpc_base_validation_then_scale_and_default_cost_equivalence(self):
    mpc = LongitudinalMpc()
    calls = []
    with patch.object(mpc, 'set_cost_weights', side_effect=lambda costs, limits: calls.append((costs, limits))):
      mpc.set_weights(acceleration_jerk=2., speed_jerk=1.3, danger_jerk=1.2)
      baseline = calls[-1]
      mpc.set_weights(acceleration_jerk=2., speed_jerk=1.3, danger_jerk=1.2, acceleration_change_scale=1.)
      self.assertEqual(calls[-1], baseline)
      mpc.set_weights(acceleration_jerk=2., speed_jerk=1.3, danger_jerk=1.2, acceleration_change_scale=1.75)
      self.assertEqual(calls[-1][0][4], 3.5 * A_CHANGE_COST)
      self.assertEqual(calls[-1][0][:4], baseline[0][:4])
      self.assertEqual(calls[-1][0][5], baseline[0][5])
      self.assertEqual(calls[-1][1], baseline[1])
      mpc.set_weights(False, acceleration_jerk=2., acceleration_change_scale=1.75)
      self.assertEqual(calls[-1][0][4], 0.)
