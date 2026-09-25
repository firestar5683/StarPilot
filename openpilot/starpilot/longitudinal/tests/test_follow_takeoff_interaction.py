"""Joined FollowJerk, selected acceleration and lead departure boundaries."""
from unittest.mock import patch

from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.plannerd import update_curve_frame
from openpilot.starpilot.curve_speed.host import CurveHost
from openpilot.starpilot.longitudinal.force_stop import StopPlan
from openpilot.starpilot.longitudinal.profile_runtime import SelectedProfileTuning
from openpilot.starpilot.longitudinal.tests.test_conditional_handoff import Frame, NOW, DRIVE


def test_curve_gateway_preserves_both_drive_owners_and_selected_takeoff_cap():
  cp = CarInterface.get_non_essential_params(CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN)
  cp.openpilotLongitudinalControl = True
  for curve in (None, CurveHost(enabled=False, replay=True)):
    planner = LongitudinalPlanner(cp)
    released = False
    # Establish tracking using the real owner, then preserve that lead at standstill.
    for warm in range(20):
      stamp = NOW - 1_000_000_000 + warm * 50_000_000
      seed = Frame()
      seed.logMonoTime = dict.fromkeys(seed, stamp-5_000_000)
      seed['modelV2'].position.x = [float(i*5) for i in range(33)]
      seed['modelV2'].position.y = [0.] * 33
      seed['modelV2'].timestampEof = stamp+2_000_000_000-5_000_000
      seed['carState'].vEgo, seed['carState'].standstill = 5., False
      lead = seed['radarState'].leadOne
      lead.present, lead.radar, lead.radarTrackId = True, True, 7
      lead.dRel, lead.vLead, lead.vLeadK, lead.vRel, lead.aLeadK = 7., 1., 1., -4., .3
      lead.yRel, lead.modelProb = 0., .99
      planner.follow_jerk.clock_pair = lambda stamp=stamp: (stamp, stamp+2_000_000_000)
      scale = planner.follow_jerk.sample(seed, cp, stamp, 1.45, StopPlan(), active=True, drive_id=DRIVE)
    assert scale == 1.75 and planner.follow_jerk.detector.tracked
    with (patch.object(planner.follow_jerk, 'sample', wraps=planner.follow_jerk.sample) as follow,
          patch.object(planner.mpc, 'set_weights', wraps=planner.mpc.set_weights) as weights):
      for tick in range(12):
        now = NOW + tick * 50_000_000
        sm = Frame()
        sm.logMonoTime = dict.fromkeys(sm, now - 5_000_000)
        sm.recv_time = dict.fromkeys(sm, (now - 5_000_000) / 1e9)
        sm['modelV2'].position.x = [float(i*5) for i in range(33)]
        sm['modelV2'].position.y = [0.] * 33
        sm['modelV2'].timestampEof = now+2_000_000_000-5_000_000
        planner.follow_jerk.clock_pair = lambda now=now: (now, now+2_000_000_000)
        sm['carState'].vEgo, sm['carState'].standstill = 0., True
        sm['selfdriveState'].experimentalMode = False
        sm['modelV2'].action.shouldStop = True
        lead = sm['radarState'].leadOne
        lead.present, lead.radar, lead.radarTrackId = True, True, 7
        lead.dRel, lead.vLead, lead.vLeadK, lead.vRel, lead.aLeadK = 7., 1., 1., 1., .3
        lead.yRel, lead.modelProb = 0., .99
        sm['radarState'].leadTwo.present = False
        def stop(_, source=sm):
          return StopPlan(model_ns=source.logMonoTime['modelV2'], takeoff_light_observed=True)
        update_curve_frame(planner, sm, cp, now, host=curve, drive_id=DRIVE,
                           selected_profiles=SelectedProfileTuning(acceleration_max=.2),
                           faster_lead_takeoff=True, force_stop_provider=stop)
        assert follow.call_args.kwargs['drive_id'] == DRIVE
        assert weights.call_args.kwargs['acceleration_change_scale'] == 1.75
        assert planner.output_a_target <= .2
        assert planner.last_profile is None
        released |= not planner.output_should_stop and planner.output_a_target == .2
    assert released


def test_takeoff_off_keeps_follow_cost_and_native_trajectory_exact():
  cp = CarInterface.get_non_essential_params(CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN)
  cp.openpilotLongitudinalControl = True
  implicit, explicit = LongitudinalPlanner(cp), LongitudinalPlanner(cp)
  assert implicit.follow_jerk.scale == explicit.follow_jerk.scale == 1.75
  for tick in range(5):
    now = NOW + tick * 50_000_000
    sm = Frame()
    sm.logMonoTime = dict.fromkeys(sm, now - 5_000_000)
    sm.recv_time = dict.fromkeys(sm, (now - 5_000_000) / 1e9)
    for planner in (implicit, explicit):
      planner.follow_jerk.clock_pair = lambda now=now: (now, now + 2_000_000_000)
    selected = SelectedProfileTuning(acceleration_max=.2)
    implicit.update(sm, now_ns=now, drive_id=DRIVE, selected_profiles=selected)
    explicit.update(sm, now_ns=now, drive_id=DRIVE, selected_profiles=selected,
                    faster_lead_takeoff=False, takeoff_drive_id=DRIVE)
    assert implicit.output_a_target <= .2 and explicit.output_a_target <= .2
    assert implicit.output_a_target == explicit.output_a_target
    assert implicit.output_should_stop == explicit.output_should_stop
    assert (implicit.a_desired_trajectory == explicit.a_desired_trajectory).all()
    assert (implicit.mpc.params == explicit.mpc.params).all()
