from dataclasses import replace
from types import SimpleNamespace as NS
from unittest.mock import patch
import pytest

from openpilot.starpilot.longitudinal.lead_takeoff import Frame, Lead, LeadTakeoff, project
from openpilot.starpilot.longitudinal.force_stop import StopPlan

NOW = 100_000_000_000
DRIVE = NOW - 10_000_000_000


def frame(tick=0, **changes):
  now = NOW + tick * 50_000_000
  lead = Lead(0, 7, True, .99, 4.5, .4, .25, 0.)
  return replace(Frame(now, now - 5_000_000, DRIVE, True, True, 0., 0., 0., 1., 1.45, (lead,)), **changes)


def test_confirmed_departure_releases_stopped_plan_in_normal_acc():
  policy = LeadTakeoff()
  for tick in range(7):
    assert policy.step(True, frame(tick), 0., True) == (0., True)
  assert policy.step(True, frame(7), 0., True) == (.35, False)


def test_creep_confirmation_and_profile_cap_remain_effective():
  policy = LeadTakeoff()
  lead = replace(frame().leads[0], distance=6., speed=.3, acceleration=.1)
  for tick in range(6):
    assert policy.step(True, frame(tick, leads=(lead,)), 0., True) == (0., True)
  assert policy.step(True, frame(6, leads=(lead,), acceleration_max=.15), 0., True) == (.15, False)
  policy.reset()
  for tick in range(7):
    result = policy.step(True, frame(tick, leads=(lead,), acceleration_max=.05), 0., True)
  assert result == (.05, True)


@pytest.mark.parametrize('changes', [dict(mpc_accel=-.001), dict(blocked=True), dict(eligible=False),
                                   dict(speed=2.01), dict(drive_id=0), dict(acceleration_max=0.),
                                   dict(model_ns=NOW-150_000_001)])
def test_native_braking_and_unavailable_or_stopping_context_never_release(changes):
  policy = LeadTakeoff()
  for tick in range(10):
    assert policy.step(True, frame(tick, **changes), -.2, True) == (-.2, True)


def test_track_replacement_stale_gap_and_toggle_off_clear_confirmation():
  policy = LeadTakeoff()
  for tick in range(7):
    policy.step(True, frame(tick), 0., True)
  changed = replace(frame(7).leads[0], track_id=8)
  assert policy.step(True, frame(7, leads=(changed,)), 0., True) == (0., True)
  assert policy.step(False, frame(8), 0., True) == (0., True)
  for tick in range(9, 15):
    assert policy.step(True, frame(tick), 0., True) == (0., True)
  assert policy.step(True, frame(20), 0., True) == (0., True)


def test_stopped_lead_conflict_and_acceleration_cap_cancel_departure():
  policy = LeadTakeoff()
  stopped = replace(frame().leads[0], slot=1, track_id=12, distance=5., speed=0., acceleration=0.)
  for tick in range(10):
    assert policy.step(True, frame(tick, leads=frame().leads+(stopped,)), 0., True) == (0., True)


def test_default_off_is_exact_numeric_and_state_path():
  policy = LeadTakeoff()
  for tick in range(20):
    target = float.fromhex('-0x1.23456789abcdep-4')
    result = policy.step(False, frame(tick), target, True)
    assert result[0] is target and result[1] is True
    assert vars(policy) == vars(LeadTakeoff())


@pytest.mark.parametrize('selected_cap', [None, .2])
def test_native_planner_stopped_release_and_off_trajectory_equivalence(selected_cap):
  from opendbc.car.hyundai.interface import CarInterface
  from opendbc.car.hyundai.values import CAR
  from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
  from openpilot.starpilot.longitudinal.profile_runtime import SelectedProfileTuning
  from openpilot.starpilot.longitudinal.tests.test_conditional_handoff import Frame as NativeFrame
  cp = CarInterface.get_non_essential_params(CAR.HYUNDAI_IONIQ_6)
  cp.openpilotLongitudinalControl = True
  native, off, enabled = (LongitudinalPlanner(cp) for _ in range(3))
  released = False
  for tick in range(12):
    now = NOW + tick * 50_000_000
    sm = NativeFrame()
    sm.logMonoTime = dict.fromkeys(sm, now-5_000_000)
    sm.recv_time = dict.fromkeys(sm, (now-5_000_000)/1e9)
    sm['carState'].vEgo = 0.
    sm['carState'].standstill = True
    sm['selfdriveState'].experimentalMode = False
    sm['modelV2'].action.shouldStop = True
    sm['modelV2'].action.desiredAcceleration = .2
    lead = sm['radarState'].leadOne
    lead.present, lead.radar, lead.radarTrackId = True, True, 7
    lead.dRel, lead.vLead, lead.vLeadK, lead.vRel, lead.aLeadK = 7., 1., 1., 1., .3
    lead.yRel, lead.modelProb = 0., .99
    sm['radarState'].leadTwo.present = False
    def stop(follow):
      return StopPlan(model_ns=sm.logMonoTime['modelV2'], takeoff_light_observed=True)
    native.update(sm, now_ns=now, force_stop_provider=stop)
    off.update(sm, now_ns=now, force_stop_provider=stop, faster_lead_takeoff=False, takeoff_drive_id=DRIVE)
    enabled.update(sm, now_ns=now, force_stop_provider=stop, faster_lead_takeoff=True, takeoff_drive_id=DRIVE,
                   selected_profiles=SelectedProfileTuning(acceleration_max=selected_cap) if selected_cap is not None else None)
    assert native.output_a_target == off.output_a_target
    assert native.output_should_stop == off.output_should_stop
    assert (native.a_desired_trajectory == off.a_desired_trajectory).all()
    assert enabled.last_profile is None
    if selected_cap is not None:
      assert enabled.output_a_target <= selected_cap
    if (native.output_should_stop and not enabled.output_should_stop and
        enabled.output_a_target > native.output_a_target and
        enabled.output_a_target >= (.35 if selected_cap is None else selected_cap)):
      released = True
  assert released  # Old partial port cannot release a stopped normal-ACC plan.


def test_force_stops_off_still_exposes_current_red_light_and_never_owns_control(tmp_path):
  from openpilot.common.params import Params
  from opendbc.car.honda.interface import CarInterface
  from opendbc.car.honda.values import CAR
  from openpilot.starpilot.longitudinal.force_stop_runtime import ForceStopRuntime
  from openpilot.starpilot.longitudinal.tests.test_force_stop_runtime import Frame as StopFrame, DRIVE as STOP_DRIVE
  params = Params(str(tmp_path))
  params.put_bool('ForceStops', False, block=True)
  cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  owner = ForceStopRuntime(params)
  for tick in range(40):
    sm = StopFrame(tick)
    plan = owner.sample(sm, cp, now_ns=sm.stamp+1_000_000, now_boot_ns=sm.stamp+2_001_000_000,
                        drive_id=STOP_DRIVE, follow_seconds=1.45, traffic_mode=False, takeoff_enabled=True)
  assert plan.takeoff_light_observed and plan.takeoff_light
  assert not plan.forcing and not plan.should_stop and plan.obstacle_m is None and plan.speed_ceiling_mps is None
  assert not owner.policy.forcing
  from pathlib import Path
  assert Path(params.get_param_path('ForceStops')).read_bytes() == b'0'
  owner = ForceStopRuntime(params)
  with patch.object(owner.light, 'step') as detect:
    for tick in range(2):
      sm = StopFrame(tick)
      assert owner.sample(sm, cp, now_ns=sm.stamp+1_000_000, now_boot_ns=sm.stamp+2_001_000_000,
                          drive_id=STOP_DRIVE, follow_seconds=1.45, traffic_mode=False) == StopPlan()
    detect.assert_not_called()


def test_projection_red_light_missing_observation_and_offcenter_conflict_veto():
  from openpilot.starpilot.longitudinal.tests.test_conditional_handoff import Frame as NativeFrame
  sm = NativeFrame()
  sm.recv_time = dict.fromkeys(sm, (NOW-5_000_000)/1e9)
  sm['carState'].vEgo, sm['carState'].standstill = 0., True
  cp = NS(openpilotLongitudinalControl=True, passive=False, dashcamOnly=False, notCar=False)
  args = dict(now_ns=NOW, drive_id=DRIVE, acceleration_max=1., mpc_accel=0., follow_seconds=1.45)
  for plan in (StopPlan(), StopPlan(model_ns=NOW-5_000_000, takeoff_light_observed=True, takeoff_light=True),
               StopPlan(model_ns=NOW-10_000_000, takeoff_light_observed=True)):
    observed = project(sm, cp, stop_plan=plan, **args)
    assert observed is None or observed.blocked


@pytest.mark.parametrize('raw', [None, b'0', b'1', b'2', b'true', b'1\n', b'1'*17])
def test_saved_takeoff_default_off_corruption_and_safe_mode_never_rewrite(tmp_path, raw):
  from openpilot.starpilot.longitudinal.lead_takeoff_preferences import TakeoffPreferences
  params = NS(get_param_path=lambda key: str(tmp_path/key))
  path = tmp_path/'FasterLeadTakeoff'
  if raw is not None:
    path.write_bytes(raw)
  host = TakeoffPreferences(params)
  assert host.sample(NOW) == (raw == b'1')
  assert (path.read_bytes() if path.exists() else None) == raw
  (tmp_path/'SafeMode').write_bytes(b'1')
  assert host.sample(NOW+1_000_000_000) is False
  assert (path.read_bytes() if path.exists() else None) == raw


def test_takeoff_light_carrier_rejects_corrupt_stop_preferences(tmp_path):
  from pathlib import Path
  from openpilot.common.params import Params
  from opendbc.car.honda.interface import CarInterface
  from opendbc.car.honda.values import CAR
  from openpilot.starpilot.longitudinal.force_stop_runtime import ForceStopRuntime
  from openpilot.starpilot.longitudinal.tests.test_force_stop_runtime import Frame as StopFrame, DRIVE as STOP_DRIVE
  params = Params(str(tmp_path))
  path = Path(params.get_param_path('ConditionalModeConfig'))
  path.write_bytes(b'{')
  cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  owner = ForceStopRuntime(params)
  for tick in range(40):
    sm = StopFrame(tick)
    assert owner.sample(sm, cp, now_ns=sm.stamp+1_000_000, now_boot_ns=sm.stamp+2_001_000_000,
                        drive_id=STOP_DRIVE, follow_seconds=1.45, traffic_mode=False, takeoff_enabled=True) == StopPlan()
  assert path.read_bytes() == b'{'
