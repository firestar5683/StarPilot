import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest

from cereal import log
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
import openpilot.selfdrive.controls.lib.longitudinal_planner as longitudinal_planner_module
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.drive_helpers import CONTROL_N
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner, get_coast_accel, get_vehicle_min_accel, should_publish_planner_fcw
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import soften_far_radar_lead_accel, should_trigger_planner_fcw
from openpilot.selfdrive.modeld.constants import ModelConstants, Plan


def make_lead(*, status: bool, d_rel: float = 200.0, v_lead: float = 0.0, a_lead: float = 0.0,
              radar: bool = False, model_prob: float = 0.0, y_rel: float = 0.0):
  lead = log.RadarState.LeadData.new_message()
  lead.status = status
  lead.dRel = d_rel
  lead.vLead = v_lead
  lead.vLeadK = v_lead
  lead.aLeadK = a_lead
  lead.vRel = 0.0
  lead.aRel = 0.0
  lead.yRel = y_rel
  lead.modelProb = model_prob
  lead.radar = radar
  return lead


def make_model(v_ego: float, desired_accel: float, gas_press_prob: float = 1.0, brake_press_prob: float = 0.0):
  model = log.ModelDataV2.new_message()
  model.init('leadsV3', 3)
  t_idxs = ModelConstants.T_IDXS

  model.position.x = [float(v_ego * t) for t in t_idxs]
  model.position.y = [0.0] * len(t_idxs)
  model.position.z = [0.0] * len(t_idxs)
  model.position.t = [float(t) for t in t_idxs]

  model.velocity.x = [float(v_ego)] * len(t_idxs)
  model.velocity.y = [0.0] * len(t_idxs)
  model.velocity.z = [0.0] * len(t_idxs)
  model.velocity.t = [float(t) for t in t_idxs]

  model.acceleration.x = [0.0] * len(t_idxs)
  model.acceleration.y = [0.0] * len(t_idxs)
  model.acceleration.z = [0.0] * len(t_idxs)
  model.acceleration.t = [float(t) for t in t_idxs]

  model.meta.disengagePredictions.gasPressProbs = [float(gas_press_prob)] * 6
  model.meta.disengagePredictions.brakePressProbs = [float(brake_press_prob)] * 6
  model.action.desiredAcceleration = desired_accel
  model.action.shouldStop = False
  return model


def set_model_lead(model, idx: int, *, prob: float, x0: float, y0: float, v0: float, a0: float = 0.0):
  lead = model.leadsV3[idx]
  lead.prob = float(prob)
  lead.x = [float(x0)]
  lead.y = [float(y0)]
  lead.v = [float(v0)]
  lead.a = [float(a0)]


def make_sm(v_ego: float, desired_accel: float, min_accel: float, *, experimental_mode: bool = True,
            tracking_lead: bool = False, lead_one=None, lead_two=None,
            gas_press_prob: float = 1.0, brake_press_prob: float = 0.0, disable_throttle: bool = False):
  return {
    "carControl": SimpleNamespace(orientationNED=[0.0, 0.0, 0.0]),
    "carState": SimpleNamespace(
      vEgo=v_ego,
      vEgoCluster=v_ego,
      aEgo=0.0,
      vCruise=100.0,
      standstill=False,
      steeringAngleDeg=0.0,
    ),
    "controlsState": SimpleNamespace(
      longControlState=LongCtrlState.pid,
      forceDecel=False,
    ),
    "liveParameters": SimpleNamespace(angleOffsetDeg=0.0),
    "modelV2": make_model(v_ego, desired_accel, gas_press_prob=gas_press_prob, brake_press_prob=brake_press_prob),
    "radarState": SimpleNamespace(
      leadOne=lead_one if lead_one is not None else make_lead(status=False),
      leadTwo=lead_two if lead_two is not None else make_lead(status=False),
    ),
    "selfdriveState": SimpleNamespace(enabled=True, experimentalMode=experimental_mode, personality=0),
    "starpilotCarState": SimpleNamespace(accelPressed=False),
    "starpilotPlan": SimpleNamespace(
      vCruise=v_ego + 5.0,
      minAcceleration=min_accel,
      maxAcceleration=2.0,
      disableThrottle=disable_throttle,
      trackingLead=tracking_lead,
      accelerationJerk=5.0,
      dangerJerk=5.0,
      speedJerk=5.0,
      dangerFactor=1.0,
      tFollow=1.45,
      forcingStop=False,
      redLight=False,
      forcingStopLength=2,
    ),
  }


def make_toggles(model_version: str = "v11", radar_takeoffs: bool = False, prioritize_smooth_following: bool = False):
  return SimpleNamespace(
    taco_tune=False,
    classic_model=False,
    tinygrad_model=True,
    model_version=model_version,
    stop_distance=6.0,
    vEgoStopping=0.5,
    radar_takeoffs=radar_takeoffs,
    prioritize_smooth_following=prioritize_smooth_following,
  )


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_experimental_mlsim_uses_vehicle_min_accel_floor(model_version):
  v_ego = 18.0
  desired_accel = -1.0
  comfort_min_accel = -0.5

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(v_ego, desired_accel, comfort_min_accel)

  vehicle_min_accel = get_vehicle_min_accel(CP, v_ego)
  assert vehicle_min_accel < comfort_min_accel

  planner.update(sm, make_toggles(model_version))

  assert planner.mode == "blended"
  assert planner.mlsim
  assert planner.output_a_target == pytest.approx(desired_accel, abs=1e-3)
  assert planner.output_a_target < comfort_min_accel


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_uses_close_raw_lead_when_tracking_lead_is_debounced(model_version):
  v_ego = 5.0

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=-0.6,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=24.0, v_lead=0.3),
  )
  sm["starpilotPlan"].vCruise = v_ego + 12.0

  planner.update(sm, make_toggles(model_version))

  assert planner.mode == "acc"
  assert planner.raw_close_lead_needs_control(sm["radarState"].leadOne, v_ego)
  assert planner.output_a_target == pytest.approx(
    planner.get_close_lead_brake_cap(sm["radarState"].leadOne, v_ego, sm["starpilotPlan"].minAcceleration)
  )


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_matches_no_lead_baseline_for_far_vision_only_lead_without_tracking(model_version):
  v_ego = 29.0

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner_no_lead = LongitudinalPlanner(CP, init_v=v_ego)
  planner_far_vision = LongitudinalPlanner(CP, init_v=v_ego)
  sm_no_lead = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
  )
  sm_far_vision = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=82.0, v_lead=25.0, radar=False, model_prob=0.9),
  )
  sm_no_lead["starpilotPlan"].vCruise = v_ego + 2.0
  sm_far_vision["starpilotPlan"].vCruise = v_ego + 2.0

  no_lead_outputs = []
  far_vision_outputs = []
  for _ in range(8):
    planner_no_lead.update(sm_no_lead, make_toggles(model_version))
    planner_far_vision.update(sm_far_vision, make_toggles(model_version))
    no_lead_outputs.append(planner_no_lead.output_a_target)
    far_vision_outputs.append(planner_far_vision.output_a_target)

  assert planner_far_vision.mode == "acc"
  assert not planner_far_vision.raw_close_lead_needs_control(sm_far_vision["radarState"].leadOne, v_ego)
  np.testing.assert_allclose(far_vision_outputs, no_lead_outputs, atol=1e-6)


def test_soften_far_radar_lead_accel_reduces_gentle_far_brake():
  softened = soften_far_radar_lead_accel(114.8, 28.88, -0.75, 29.26, 1.45, radar=True)
  assert softened > -0.35
  assert softened < 0.0


def test_soften_far_radar_lead_accel_keeps_close_closing_brake():
  baseline = -0.76
  softened = soften_far_radar_lead_accel(68.0, 26.38, baseline, 29.38, 1.45, radar=True)
  assert softened == pytest.approx(baseline)


def test_planner_fcw_suppresses_low_speed_opening_or_low_ttc_false_positives():
  assert not should_trigger_planner_fcw(
    make_lead(status=True, d_rel=7.156, v_lead=0.798, a_lead=0.021, radar=False, model_prob=0.99),
    0.402,
  )
  assert not should_trigger_planner_fcw(
    make_lead(status=True, d_rel=9.311, v_lead=0.911, a_lead=-0.263, radar=False, model_prob=0.99),
    1.252,
  )


def test_planner_fcw_keeps_real_low_speed_closing_alerts():
  assert should_trigger_planner_fcw(
    make_lead(status=True, d_rel=1.8, v_lead=0.0, a_lead=0.0, radar=False, model_prob=0.99),
    1.6,
  )


def test_publish_planner_fcw_suppresses_crawl_speed_false_positive():
  car_state = SimpleNamespace(vEgo=0.29, standstill=False)
  radar_state = SimpleNamespace(
    leadOne=make_lead(status=True, d_rel=7.55, v_lead=0.033, a_lead=0.0, radar=False, model_prob=0.99),
  )
  assert not should_publish_planner_fcw(3, car_state, radar_state)


def test_publish_planner_fcw_keeps_real_current_close_closing_alert():
  car_state = SimpleNamespace(vEgo=1.6, standstill=False)
  radar_state = SimpleNamespace(
    leadOne=make_lead(status=True, d_rel=1.8, v_lead=0.0, a_lead=0.0, radar=False, model_prob=0.99),
  )
  assert should_publish_planner_fcw(3, car_state, radar_state)


def test_vision_lead_approach_cap_brakes_before_hard_cap():
  v_ego = 21.535
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=38.9, v_lead=18.04, a_lead=-0.026, radar=False, model_prob=0.984)

  hard_cap = planner.get_close_lead_brake_cap(lead, v_ego, -1.0)
  approach_cap = planner.get_vision_lead_approach_cap(lead, v_ego, -1.0, 1.45)

  assert hard_cap == pytest.approx(-0.212, abs=1e-2)
  assert approach_cap is not None
  assert approach_cap < hard_cap
  assert approach_cap > -1.2


def test_vision_lead_approach_cap_brakes_harder_when_inside_tight_gap():
  v_ego = 26.18
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=39.72, v_lead=22.46, a_lead=-0.15, radar=False, model_prob=0.97)

  approach_cap = planner.get_vision_lead_approach_cap(lead, v_ego, -1.0, 1.49)

  assert approach_cap is not None
  assert approach_cap < -0.5


def test_vision_lead_approach_cap_brakes_harder_for_braking_tracked_lead_inside_tight_gap():
  v_ego = 19.50
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=19.7, v_lead=16.25, a_lead=-0.83, radar=False, model_prob=0.98)

  hard_cap = planner.get_close_lead_brake_cap(lead, v_ego, -3.0)
  approach_cap = planner.get_vision_lead_approach_cap(lead, v_ego, -3.0, 1.45)

  assert hard_cap == pytest.approx(-1.01, abs=0.03)
  assert approach_cap is not None
  assert approach_cap < -1.35
  assert approach_cap < hard_cap


def test_vision_lead_approach_cap_ignores_opening_lead_with_large_gap():
  v_ego = 19.37
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=66.168, v_lead=20.751, a_lead=0.261, radar=False, model_prob=0.975)

  assert planner.get_vision_lead_approach_cap(lead, v_ego, -1.0, 1.45) is None


def test_vision_untracked_slow_lead_cap_triggers_only_for_meaningful_closing_case():
  route_v_ego = 23.23
  far_v_ego = 29.0

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=route_v_ego)
  route_like_lead = make_lead(status=True, d_rel=66.7, v_lead=18.49, a_lead=0.0, radar=False, model_prob=0.92)
  far_mild_lead = make_lead(status=True, d_rel=82.0, v_lead=25.0, a_lead=0.0, radar=False, model_prob=0.9)

  route_cap = planner.get_vision_untracked_slow_lead_cap(route_like_lead, route_v_ego, -1.0)
  far_cap = planner.get_vision_untracked_slow_lead_cap(far_mild_lead, far_v_ego, -1.0)

  assert route_cap is not None
  assert route_cap < -0.1
  assert far_cap is None


def test_vision_untracked_slow_lead_cap_reaches_high_confidence_far_slower_lead_before_raw_close_lead():
  v_ego = 21.48

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  route_like_lead = make_lead(status=True, d_rel=93.0, v_lead=12.84, a_lead=0.0, radar=False, model_prob=0.935)

  route_cap = planner.get_vision_untracked_slow_lead_cap(route_like_lead, v_ego, -1.0)

  assert route_cap is not None
  assert route_cap < -0.5
  assert not planner.raw_close_lead_needs_control(route_like_lead, v_ego)


def test_vision_untracked_slow_lead_cap_relaxes_confidence_for_near_stopped_high_closure_lead():
  v_ego = 20.35

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  route_like_lead = make_lead(status=True, d_rel=115.4, v_lead=3.76, a_lead=0.0, radar=False, model_prob=0.70)

  route_cap = planner.get_vision_untracked_slow_lead_cap(route_like_lead, v_ego, -1.0)

  assert route_cap is not None
  assert route_cap < -0.55


def test_vision_untracked_slow_lead_cap_keeps_low_confidence_floor_for_less_threatening_lead():
  v_ego = 20.35

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  less_threatening_lead = make_lead(status=True, d_rel=115.4, v_lead=9.5, a_lead=0.0, radar=False, model_prob=0.75)

  assert planner.get_vision_untracked_slow_lead_cap(less_threatening_lead, v_ego, -1.0) is None


def test_vision_slow_stopped_lead_cap_brakes_earlier_for_confident_stop():
  v_ego = 13.207
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=49.131, v_lead=1.837, a_lead=-0.312, radar=False, model_prob=0.942)

  slow_stop_cap = planner.get_vision_slow_stopped_lead_cap(lead, v_ego, -1.0, 1.75)

  assert slow_stop_cap is not None
  assert slow_stop_cap < -0.9
  assert slow_stop_cap > -1.25


def test_vision_slow_stopped_lead_cap_ignores_far_high_speed_stop_candidate():
  v_ego = 33.5
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=183.0, v_lead=0.0, a_lead=0.0, radar=False, model_prob=0.995)

  assert planner.get_vision_slow_stopped_lead_cap(lead, v_ego, -1.0, 1.45) is None


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_dynamic_t_follow_increases_modestly_for_closing_lead(model_version):
  v_ego = 21.535

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-3.0,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=38.9, v_lead=18.04, a_lead=-0.026, radar=False, model_prob=0.984),
  )
  sm["starpilotPlan"].vCruise = v_ego + 8.0

  for _ in range(8):
    planner.update(sm, make_toggles(model_version))

  assert planner.effective_t_follow is not None
  assert planner.effective_t_follow > sm["starpilotPlan"].tFollow + 0.15
  assert planner.effective_t_follow < sm["starpilotPlan"].tFollow + 0.45


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_dynamic_t_follow_stays_near_base_for_far_highway_lead(model_version):
  v_ego = 29.26

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=114.8, v_lead=28.88, a_lead=-0.75, radar=True, model_prob=0.9),
  )
  sm["starpilotPlan"].vCruise = v_ego + 3.0

  for _ in range(12):
    planner.update(sm, make_toggles(model_version))

  assert planner.effective_t_follow == pytest.approx(sm["starpilotPlan"].tFollow, abs=0.02)


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_dynamic_t_follow_releases_toward_base_after_lead_opens(model_version):
  v_ego = 21.535

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-3.0,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=38.9, v_lead=18.04, a_lead=-0.026, radar=False, model_prob=0.984),
  )

  for _ in range(8):
    planner.update(sm, make_toggles(model_version))

  boosted_t_follow = planner.effective_t_follow
  sm["radarState"].leadOne = make_lead(status=True, d_rel=66.168, v_lead=20.751, a_lead=0.261, radar=False, model_prob=0.975)
  for _ in range(12):
    planner.update(sm, make_toggles(model_version))

  assert boosted_t_follow is not None
  assert planner.effective_t_follow < boosted_t_follow
  assert planner.effective_t_follow == pytest.approx(sm["starpilotPlan"].tFollow, abs=0.02)


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_vision_lead_approach_cap_smooths_before_close_brake(model_version):
  approach_v_ego = 21.535
  close_v_ego = 21.435

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner_approach = LongitudinalPlanner(CP, init_v=approach_v_ego)
  planner_close = LongitudinalPlanner(CP, init_v=close_v_ego)

  sm_approach = make_sm(
    approach_v_ego,
    desired_accel=0.2,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=38.9, v_lead=18.04, a_lead=-0.026, radar=False, model_prob=0.984),
  )
  sm_close = make_sm(
    close_v_ego,
    desired_accel=0.2,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=27.18, v_lead=15.76, a_lead=-0.824, radar=False, model_prob=0.988),
  )
  sm_approach["starpilotPlan"].vCruise = approach_v_ego + 8.0
  sm_close["starpilotPlan"].vCruise = close_v_ego + 8.0

  approach_outputs = []
  for _ in range(6):
    planner_approach.update(sm_approach, make_toggles(model_version))
    approach_outputs.append(planner_approach.output_a_target)

  planner_close.update(sm_close, make_toggles(model_version))

  assert planner_approach.mode == "acc"
  assert planner_close.mode == "acc"
  assert min(approach_outputs[:2]) > -0.55
  assert approach_outputs[-1] < -1.3
  assert planner_close.output_a_target < approach_outputs[0] - 0.8


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_tracked_vision_far_mild_closure_does_not_bypass_persistence(model_version):
  v_ego = 37.45
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=42.8, v_lead=35.31, a_lead=0.18, radar=False, model_prob=0.98)

  approach_cap = planner.get_vision_lead_approach_cap(lead, v_ego, -1.0, 1.45)

  assert approach_cap is not None
  assert approach_cap > -1.0
  assert not planner.tracked_vision_lead_approach_needs_immediate_brake(lead, v_ego, approach_cap)


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_tracked_vision_close_or_braking_lead_bypasses_persistence(model_version):
  v_ego = 19.50

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=19.7, v_lead=16.25, a_lead=-0.83, radar=False, model_prob=0.98),
  )
  sm["starpilotPlan"].vCruise = v_ego + 6.0

  planner.update(sm, make_toggles(model_version))

  assert planner.output_a_target < -1.3


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_pretracking_vision_slow_lead_blocks_positive_catchup(model_version):
  v_ego = 23.23

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner_no_lead = LongitudinalPlanner(CP, init_v=v_ego)
  planner_with_lead = LongitudinalPlanner(CP, init_v=v_ego)
  sm_no_lead = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=False,
  )
  sm_with_lead = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=66.7, v_lead=18.49, a_lead=0.0, radar=False, model_prob=0.92),
  )
  sm_no_lead["starpilotPlan"].vCruise = v_ego + 6.0
  sm_with_lead["starpilotPlan"].vCruise = v_ego + 6.0

  for _ in range(6):
    planner_no_lead.update(sm_no_lead, make_toggles(model_version))
    planner_with_lead.update(sm_with_lead, make_toggles(model_version))

  assert planner_with_lead.mode == "acc"
  assert not planner_with_lead.raw_close_lead_needs_control(sm_with_lead["radarState"].leadOne, v_ego)
  assert planner_with_lead.output_a_target <= planner_no_lead.output_a_target - 0.04
  assert planner_with_lead.output_a_target < -0.2


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_keeps_close_slow_radar_lead_active_when_tracking_flaps(model_version):
  v_ego = 0.96

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner_no_lead = LongitudinalPlanner(CP, init_v=v_ego)
  planner_with_lead = LongitudinalPlanner(CP, init_v=v_ego)
  sm_no_lead = make_sm(
    v_ego,
    desired_accel=0.45,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=False,
  )
  sm_with_lead = make_sm(
    v_ego,
    desired_accel=0.45,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=8.15, v_lead=0.09, a_lead=-0.36, radar=True, model_prob=1.0, y_rel=0.1),
  )
  sm_no_lead["starpilotPlan"].vCruise = v_ego + 8.0
  sm_with_lead["starpilotPlan"].vCruise = v_ego + 8.0

  planner_no_lead.update(sm_no_lead, make_toggles(model_version))
  planner_with_lead.update(sm_with_lead, make_toggles(model_version))

  assert planner_with_lead.raw_close_lead_needs_control(sm_with_lead["radarState"].leadOne, v_ego)
  assert planner_with_lead.output_a_target < planner_no_lead.output_a_target - 0.15
  assert planner_with_lead.output_a_target <= 0.22


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_low_speed_weak_departure_accel_cap_softens_voacc_follow_pulse(model_version):
  v_ego = 2.8

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.45,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=16.6, v_lead=2.85, a_lead=0.05, radar=False, model_prob=0.99, y_rel=0.0),
  )
  sm["starpilotPlan"].vCruise = v_ego + 10.0

  planner.update(sm, make_toggles(model_version))

  assert planner.output_a_target <= 0.22


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_pretracking_vision_far_slower_lead_starts_braking_before_tracking(model_version):
  v_ego = 21.48

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner_no_lead = LongitudinalPlanner(CP, init_v=v_ego)
  planner_with_lead = LongitudinalPlanner(CP, init_v=v_ego)
  sm_no_lead = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
  )
  sm_with_lead = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=93.0, v_lead=12.84, a_lead=0.0, radar=False, model_prob=0.935),
  )
  sm_no_lead["starpilotPlan"].vCruise = v_ego + 6.0
  sm_with_lead["starpilotPlan"].vCruise = v_ego + 6.0

  no_lead_outputs = []
  lead_outputs = []
  for _ in range(8):
    planner_no_lead.update(sm_no_lead, make_toggles(model_version))
    planner_with_lead.update(sm_with_lead, make_toggles(model_version))
    no_lead_outputs.append(planner_no_lead.output_a_target)
    lead_outputs.append(planner_with_lead.output_a_target)

  assert planner_with_lead.mode == "acc"
  assert not planner_with_lead.raw_close_lead_needs_control(sm_with_lead["radarState"].leadOne, v_ego)
  assert all(lead_output <= no_lead_output + 1e-6
             for lead_output, no_lead_output in zip(lead_outputs[5:], no_lead_outputs[5:]))
  assert min(lead_outputs[5:]) < min(no_lead_outputs[5:]) - 0.08
  assert lead_outputs[-1] < no_lead_outputs[-1] - 0.15


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_pretracking_vision_far_slower_lead_can_still_brake_immediately(model_version):
  v_ego = 21.48

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=93.0, v_lead=12.84, a_lead=0.0, radar=False, model_prob=0.935),
  )
  sm["starpilotPlan"].vCruise = v_ego + 6.0

  planner.update(sm, make_toggles(model_version))

  assert planner.mode == "acc"
  assert planner.output_a_target < -0.45


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_pretracking_closer_braking_vision_lead_bypasses_far_lead_persistence(model_version):
  v_ego = 17.46

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=41.9, v_lead=14.86, a_lead=-0.03, radar=False, model_prob=1.0),
  )
  sm["starpilotPlan"].vCruise = v_ego + 6.0

  planner.update(sm, make_toggles(model_version))

  assert planner.mode == "acc"
  assert planner.output_a_target < -0.35


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_pretracking_flappy_far_lead_requires_persistence(model_version):
  v_ego = 26.09

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner_no_lead = LongitudinalPlanner(CP, init_v=v_ego)
  planner_flappy = LongitudinalPlanner(CP, init_v=v_ego)
  sm_no_lead = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
  )
  sm_flappy = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=74.75, v_lead=26.63, a_lead=0.01, radar=False, model_prob=0.989),
  )
  sm_no_lead["starpilotPlan"].vCruise = v_ego + 6.0
  sm_flappy["starpilotPlan"].vCruise = v_ego + 6.0

  flappy_sequence = [
    (74.75, 26.63, 0.01, 0.989),
    (68.17, 20.81, 0.094, 0.971),
    (69.73, 24.12, 0.057, 0.981),
    (62.15, 21.38, 0.064, 0.983),
    (66.29, 23.19, 0.069, 0.985),
    (70.58, 27.51, 0.036, 0.988),
  ]

  no_lead_outputs = []
  flappy_outputs = []
  for d_rel, v_lead, a_lead, model_prob in flappy_sequence:
    planner_no_lead.update(sm_no_lead, make_toggles(model_version))
    sm_flappy["radarState"].leadOne = make_lead(
      status=True, d_rel=d_rel, v_lead=v_lead, a_lead=a_lead, radar=False, model_prob=model_prob,
    )
    planner_flappy.update(sm_flappy, make_toggles(model_version))
    no_lead_outputs.append(planner_no_lead.output_a_target)
    flappy_outputs.append(planner_flappy.output_a_target)

  assert planner_flappy.mode == "acc"
  assert min(flappy_outputs) > min(no_lead_outputs) - 0.12


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_pretracking_near_stopped_vision_lead_does_not_relax_when_confidence_is_midrange(model_version):
  v_ego = 20.35

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner_no_lead = LongitudinalPlanner(CP, init_v=v_ego)
  planner_with_lead = LongitudinalPlanner(CP, init_v=v_ego)
  sm_no_lead = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
  )
  sm_with_lead = make_sm(
    v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=115.4, v_lead=3.76, a_lead=0.0, radar=False, model_prob=0.70),
  )
  sm_no_lead["starpilotPlan"].vCruise = v_ego + 6.0
  sm_with_lead["starpilotPlan"].vCruise = v_ego + 6.0

  for _ in range(8):
    planner_no_lead.update(sm_no_lead, make_toggles(model_version))
    planner_with_lead.update(sm_with_lead, make_toggles(model_version))

  assert planner_with_lead.mode == "acc"
  assert planner_with_lead.output_a_target < planner_no_lead.output_a_target - 0.12
  assert planner_with_lead.output_a_target < -0.45


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_tracked_pace_matched_lead_caps_positive_catchup(model_version):
  v_ego = 28.7

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner_no_lead = LongitudinalPlanner(CP, init_v=v_ego)
  planner_with_lead = LongitudinalPlanner(CP, init_v=v_ego)
  sm_no_lead = make_sm(
    v_ego,
    desired_accel=0.5,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
  )
  sm_with_lead = make_sm(
    v_ego,
    desired_accel=0.5,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=22.0, v_lead=29.4, a_lead=0.0, radar=False, model_prob=0.995),
  )
  sm_no_lead["starpilotPlan"].vCruise = v_ego + 4.0
  sm_with_lead["starpilotPlan"].vCruise = v_ego + 4.0

  for _ in range(8):
    planner_no_lead.update(sm_no_lead, make_toggles(model_version))
    planner_with_lead.update(sm_with_lead, make_toggles(model_version))

  assert planner_with_lead.mode == "acc"
  assert planner_with_lead.output_a_target <= planner_no_lead.output_a_target - 0.15
  assert planner_with_lead.output_a_target < 0.08


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_low_speed_vision_stop_buffer_sets_should_stop_before_tiny_gap(model_version):
  v_ego = 3.8

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.1,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=5.75, v_lead=0.58, a_lead=-0.1, radar=False, model_prob=0.99),
  )
  sm["starpilotPlan"].vCruise = v_ego + 4.0

  planner.update(sm, make_toggles(model_version))

  assert planner.mode == "acc"
  assert planner.output_should_stop
  assert planner.output_a_target < -1.0


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_low_speed_vision_stop_buffer_brakes_harder_for_close_slow_vision_lead(model_version):
  v_ego = 6.2

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.1,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=9.35, v_lead=2.8, a_lead=-0.2, radar=False, model_prob=0.99),
  )
  sm["starpilotPlan"].vCruise = v_ego + 4.0

  planner.update(sm, make_toggles(model_version))

  assert planner.mode == "acc"
  assert planner.output_should_stop
  assert planner.output_a_target <= -2.7


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_low_speed_vision_stop_buffer_stays_latched_when_closure_softens_near_stop(model_version, monkeypatch):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.55)
  lead = make_lead(status=True, d_rel=2.1, v_lead=0.05, a_lead=-0.02, radar=False, model_prob=0.99)

  monotonic_values = iter([10.0, 10.1])
  monkeypatch.setattr(longitudinal_planner_module.time, "monotonic", lambda: next(monotonic_values))

  cap_armed, active_armed = planner.get_vision_low_speed_stop_buffer_cap(lead, 0.55, -2.0)
  cap_held, active_held = planner.get_vision_low_speed_stop_buffer_cap(lead, 0.34, -2.0)

  assert active_armed
  assert cap_armed is not None
  assert active_held
  assert cap_held is not None
  assert cap_held <= -1.25


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_close_moving_vision_lead_keeps_negative_output_while_should_stop(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.242)
  toggles = make_toggles(model_version)

  stop_sequence = [
    (0.242, 2.062, 0.284, -0.081),
    (0.221, 1.963, 0.338, -0.076),
    (0.194, 2.100, 0.451, -0.076),
    (0.180, 2.001, 0.447, -0.066),
    (0.166, 1.964, 0.451, -0.066),
    (0.151, 2.075, 0.451, -0.060),
  ]

  outputs = []
  for v_ego, d_rel, v_lead, desired_accel in stop_sequence:
    sm = make_sm(
      v_ego,
      desired_accel=desired_accel,
      min_accel=-0.5,
      experimental_mode=False,
      tracking_lead=True,
      lead_one=make_lead(status=True, d_rel=d_rel, v_lead=v_lead, a_lead=0.0, radar=False, model_prob=1.0),
    )
    sm["controlsState"].longControlState = LongCtrlState.stopping
    sm["starpilotPlan"].vCruise = 10.0

    planner.update(sm, toggles)
    outputs.append(planner.output_a_target)

  assert all(output <= -0.02 for output in outputs[2:])


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_close_near_standstill_vision_lead_keeps_meaningful_brake_floor(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.017)

  sm = make_sm(
    0.017,
    desired_accel=-0.06,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=2.83, v_lead=0.09, a_lead=0.10, radar=False, model_prob=0.9999),
  )
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = True

  planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop
  assert planner.output_a_target <= -0.20


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_close_near_standstill_moving_lead_keeps_brake_floor_while_should_stop(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.034)

  sm = make_sm(
    0.034,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=3.93, v_lead=1.61, a_lead=2.18, radar=False, model_prob=1.0),
  )
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = True

  planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop
  assert planner.output_a_target <= -0.20


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_close_opening_vision_lead_does_not_drop_to_zero_after_stop_release(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=1.49)
  toggles = make_toggles(model_version)

  sm_stop = make_sm(
    1.488,
    desired_accel=-1.64,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=3.433, v_lead=1.469, a_lead=0.58, radar=False, model_prob=0.9996),
  )
  sm_stop["controlsState"].longControlState = LongCtrlState.stopping
  sm_stop["starpilotPlan"].vCruise = 10.0
  sm_stop["modelV2"].action.shouldStop = True
  planner.update(sm_stop, toggles)

  sm_release = make_sm(
    1.420,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=3.568, v_lead=1.679, a_lead=0.66, radar=False, model_prob=0.9994),
  )
  sm_release["controlsState"].longControlState = LongCtrlState.pid
  sm_release["starpilotPlan"].vCruise = 10.0
  sm_release["modelV2"].action.shouldStop = False
  planner.update(sm_release, toggles)

  assert planner.output_a_target <= -0.18


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_close_near_standstill_departing_lead_keeps_small_brake_after_stop_release(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.034)
  toggles = make_toggles(model_version)

  sm_stop = make_sm(
    0.034,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=3.93, v_lead=1.61, a_lead=2.18, radar=False, model_prob=1.0),
  )
  sm_stop["controlsState"].longControlState = LongCtrlState.stopping
  sm_stop["starpilotPlan"].vCruise = 10.0
  sm_stop["modelV2"].action.shouldStop = True
  planner.update(sm_stop, toggles)

  sm_release = make_sm(
    0.449,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=4.02, v_lead=2.45, a_lead=2.26, radar=False, model_prob=1.0),
  )
  sm_release["controlsState"].longControlState = LongCtrlState.pid
  sm_release["starpilotPlan"].vCruise = 10.0
  sm_release["modelV2"].action.shouldStop = False
  planner.update(sm_release, toggles)

  assert planner.output_a_target <= -0.18


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_tracked_vision_model_brake_floor_prevents_positive_output_on_slower_lead(model_version):
  v_ego = 19.1

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=-1.18,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=36.5, v_lead=17.2, a_lead=-0.53, radar=False, model_prob=0.993),
  )

  for _ in range(8):
    planner.update(sm, make_toggles(model_version))

  assert planner.mode == "acc"
  assert planner.output_a_target <= -0.35


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_tracked_vision_model_brake_cap_relaxes_mild_model_brake_slam_window(model_version):
  v_ego = 20.56

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=48.0, v_lead=19.07, a_lead=-0.30, radar=False, model_prob=0.999)

  cap = planner.get_tracked_vision_model_brake_cap(lead, v_ego, 1.45, -0.35)

  assert cap is not None
  assert cap > -1.2


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_tracked_vision_model_brake_cap_does_not_relax_strong_model_brake(model_version):
  v_ego = 20.56

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=38.1, v_lead=19.07, a_lead=-0.30, radar=False, model_prob=0.999)

  cap = planner.get_tracked_vision_model_brake_cap(lead, v_ego, 1.45, -1.2)

  assert cap is None


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_manual_resume_override_clears_no_lead_model_stop_at_standstill(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm = make_sm(0.0, desired_accel=0.0, min_accel=-0.5)
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = True
  sm["starpilotPlan"].forcingStop = True
  sm["starpilotCarState"] = SimpleNamespace(accelPressed=True)

  planner.update(sm, make_toggles(model_version))

  assert not planner.output_should_stop
  assert planner.output_a_target >= 0.2


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_manual_resume_override_does_not_clear_stopped_lead_stop(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm = make_sm(
    0.0,
    desired_accel=0.0,
    min_accel=-0.5,
    lead_one=make_lead(status=True, d_rel=4.0, v_lead=0.0, radar=False, model_prob=0.99),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = True
  sm["starpilotPlan"].forcingStop = True
  sm["starpilotCarState"] = SimpleNamespace(accelPressed=True)

  planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_moving_lead_does_not_force_resume_while_should_stop(model_version):
  v_ego = 0.0

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=7.1, v_lead=2.3, a_lead=1.8, radar=True, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0

  planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop
  assert planner.output_a_target < 0.1


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_moving_lead_applies_resume_floor_once_stop_clears(model_version):
  v_ego = 0.0

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.1,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=15.0, v_lead=2.2, a_lead=0.4, radar=False, model_prob=0.99),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = False
  sm["starpilotPlan"].vCruise = 10.0

  for _ in range(12):
    planner.update(sm, make_toggles(model_version))

  assert not planner.output_should_stop
  assert planner.output_a_target >= 0.2


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_stopped_lead_guard_blocks_false_release_at_longer_gap(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.03,
    desired_accel=1.85,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=8.15, v_lead=0.04, a_lead=0.0, radar=False, model_prob=0.99),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.pid
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False

  planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop
  assert planner.output_a_target <= 0.0


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_stopped_lead_guard_does_not_block_radar_depart_at_longer_gap(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.45,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=8.2, v_lead=0.72, a_lead=0.32, radar=True, model_prob=0.999, y_rel=0.1),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False

  planner.update(sm, make_toggles(model_version))

  assert not planner.output_should_stop
  assert planner.output_a_target >= longitudinal_planner_module.STANDSTILL_LEAD_DEPART_MIN_ACCEL


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_stopped_lead_guard_blocks_false_release_during_creep_frame(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.2)

  sm = make_sm(
    0.2,
    desired_accel=1.15,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=7.9, v_lead=0.03, a_lead=0.0, radar=False, model_prob=0.99),
  )
  sm["carState"].standstill = False
  sm["controlsState"].longControlState = LongCtrlState.pid
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False

  planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop
  assert planner.output_a_target <= 0.0


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_confident_departing_lead_clears_stop_without_waiting_for_model_accel(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=3.95, v_lead=0.62, a_lead=1.05, radar=False, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = True
  sm["starpilotPlan"].vCruise = 10.0

  for _ in range(6):
    planner.update(sm, make_toggles(model_version))
    assert planner.output_should_stop

  planner.update(sm, make_toggles(model_version))

  assert not planner.output_should_stop
  assert planner.output_a_target >= 0.2


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_confident_departing_lead_gets_depart_floor_with_zero_model_accel(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=4.10, v_lead=1.05, a_lead=1.20, radar=False, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = False
  sm["starpilotPlan"].vCruise = 10.0

  for _ in range(6):
    planner.update(sm, make_toggles(model_version))
    assert planner.output_should_stop

  planner.update(sm, make_toggles(model_version))

  assert not planner.output_should_stop
  assert planner.output_a_target >= 0.25


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_confident_departing_lead_does_not_release_on_first_creep_frame(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.38,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=4.12, v_lead=0.32, a_lead=1.12, radar=False, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = False
  sm["starpilotPlan"].vCruise = 10.0

  planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop
  assert planner.output_a_target <= 0.2


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_moving_lead_holds_depart_accel_floor_after_stop_release(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  toggles = make_toggles(model_version)

  sequence = [
    (0.0, True, 15.0, 2.2, 0.10),
    (0.0, True, 15.2, 2.4, 0.12),
    (0.0, True, 15.5, 2.6, 0.15),
    (0.10, False, 15.8, 2.8, 0.20),
    (0.25, False, 16.2, 3.0, 0.25),
    (0.45, False, 16.8, 3.2, 0.30),
  ]

  outputs = []
  for v_ego, standstill, d_rel, v_lead, desired_accel in sequence:
    sm = make_sm(
      v_ego,
      desired_accel=desired_accel,
      min_accel=-0.5,
      experimental_mode=False,
      tracking_lead=True,
      lead_one=make_lead(status=True, d_rel=d_rel, v_lead=v_lead, a_lead=0.0, radar=False, model_prob=0.99),
    )
    sm["carState"].standstill = standstill
    sm["controlsState"].longControlState = LongCtrlState.starting if standstill else LongCtrlState.pid
    sm["starpilotPlan"].vCruise = 10.0
    sm["modelV2"].action.shouldStop = False

    planner.update(sm, toggles)
    outputs.append(planner.output_a_target)

  assert outputs[2] >= 0.25
  assert outputs[3] >= 0.25
  assert outputs[4] >= 0.25


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_moving_lead_depart_accel_hold_cancels_if_lead_brakes(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  toggles = make_toggles(model_version)

  sm_release = make_sm(
    0.0,
    desired_accel=0.45,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=4.8, v_lead=1.0, a_lead=0.0, radar=False, model_prob=0.99),
  )
  sm_release["carState"].standstill = True
  sm_release["controlsState"].longControlState = LongCtrlState.starting
  sm_release["starpilotPlan"].vCruise = 10.0
  sm_release["modelV2"].action.shouldStop = False
  planner.update(sm_release, toggles)

  sm_brake = make_sm(
    0.18,
    desired_accel=0.18,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=3.9, v_lead=0.1, a_lead=-0.4, radar=False, model_prob=0.99),
  )
  sm_brake["controlsState"].longControlState = LongCtrlState.pid
  sm_brake["starpilotPlan"].vCruise = 10.0
  sm_brake["modelV2"].action.shouldStop = True

  planner.update(sm_brake, toggles)

  assert planner.output_should_stop
  assert planner.output_a_target < 0.1


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_radar_depart_kept_when_radar_lead_is_centered(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.45,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=11.2, v_lead=0.63, a_lead=0.36, radar=True, model_prob=0.998, y_rel=0.2),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False
  set_model_lead(sm["modelV2"], 0, prob=0.999, x0=12.2, y0=0.03, v0=0.4)

  planner.update(sm, make_toggles(model_version))

  assert planner.output_a_target >= longitudinal_planner_module.STANDSTILL_LEAD_DEPART_MIN_ACCEL


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_radar_depart_blocks_offcenter_radar_conflict(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.45,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=11.2, v_lead=0.63, a_lead=0.36, radar=True, model_prob=0.998, y_rel=2.3),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False
  set_model_lead(sm["modelV2"], 0, prob=0.999, x0=12.2, y0=0.03, v0=0.4)

  planner.update(sm, make_toggles(model_version))

  assert planner.output_a_target < longitudinal_planner_module.STANDSTILL_LEAD_DEPART_MIN_ACCEL


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_low_speed_radar_depart_hold_blocks_offcenter_radar_conflict(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=1.25)

  sm = make_sm(
    1.25,
    desired_accel=0.20,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=9.95, v_lead=0.43, a_lead=0.44, radar=True, model_prob=0.999, y_rel=2.2),
  )
  sm["carState"].standstill = False
  sm["controlsState"].longControlState = LongCtrlState.pid
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False
  set_model_lead(sm["modelV2"], 0, prob=0.999, x0=11.4, y0=0.0, v0=0.2)

  planner.update(sm, make_toggles(model_version))

  assert planner.output_a_target < longitudinal_planner_module.STANDSTILL_LEAD_DEPART_MIN_ACCEL


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_radar_takeoffs_toggle_bypasses_offcenter_veto(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.45,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=11.2, v_lead=0.63, a_lead=0.36, radar=True, model_prob=0.998, y_rel=2.3),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False
  set_model_lead(sm["modelV2"], 0, prob=0.999, x0=12.2, y0=0.03, v0=0.4)

  planner.update(sm, make_toggles(model_version, radar_takeoffs=True))

  assert planner.output_a_target >= longitudinal_planner_module.STANDSTILL_LEAD_DEPART_MIN_ACCEL


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_low_speed_radar_takeoffs_toggle_bypasses_offcenter_veto(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=1.25)

  sm = make_sm(
    1.25,
    desired_accel=0.20,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=9.95, v_lead=0.43, a_lead=0.44, radar=True, model_prob=0.999, y_rel=2.2),
  )
  sm["carState"].standstill = False
  sm["controlsState"].longControlState = LongCtrlState.pid
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False
  set_model_lead(sm["modelV2"], 0, prob=0.999, x0=11.4, y0=0.0, v0=0.2)

  planner.update(sm, make_toggles(model_version, radar_takeoffs=True))

  assert planner.output_a_target >= 0.0


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_damps_far_radar_mild_lead_brake_more_than_close_brake(model_version):
  far_v_ego = 29.26
  far_v_cruise = 32.22
  close_v_ego = 29.38
  close_v_cruise = 32.22

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner_far = LongitudinalPlanner(CP, init_v=far_v_ego)
  planner_close = LongitudinalPlanner(CP, init_v=close_v_ego)

  sm_far = make_sm(
    far_v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=114.8, v_lead=28.88, a_lead=-0.75, radar=True, model_prob=0.9),
  )
  sm_close = make_sm(
    close_v_ego,
    desired_accel=0.2,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=68.0, v_lead=26.38, a_lead=-0.76, radar=True, model_prob=0.9),
  )
  sm_far["starpilotPlan"].vCruise = far_v_cruise
  sm_close["starpilotPlan"].vCruise = close_v_cruise

  for _ in range(80):
    planner_far.update(sm_far, make_toggles(model_version))
    planner_close.update(sm_close, make_toggles(model_version))

  assert planner_far.mode == "acc"
  assert planner_close.mode == "acc"
  assert planner_far.output_a_target > -0.4
  assert planner_close.output_a_target < planner_far.output_a_target - 0.1


def test_modeld_action_passes_tomb_raider_longitudinal_params(monkeypatch):
  monkeypatch.setenv("DEBUG", "0")
  fake_commonmodel = types.ModuleType("openpilot.selfdrive.modeld.models.commonmodel_pyx")
  fake_commonmodel.DrivingModelFrame = object
  fake_commonmodel.CLContext = object
  monkeypatch.setitem(sys.modules, fake_commonmodel.__name__, fake_commonmodel)

  from openpilot.selfdrive.modeld import modeld

  captured = {}

  def fake_get_accel_from_plan(speeds, accels, t_idxs, *, action_t, vEgoStopping):
    captured["speeds"] = speeds
    captured["accels"] = accels
    captured["t_idxs"] = t_idxs
    captured["action_t"] = action_t
    captured["vEgoStopping"] = vEgoStopping
    return 0.4, True

  monkeypatch.setattr(modeld, "get_accel_from_plan_tomb_raider", fake_get_accel_from_plan)

  plan = np.zeros((1, ModelConstants.IDX_N, ModelConstants.PLAN_WIDTH), dtype=np.float32)
  plan[0, :, Plan.VELOCITY] = 3.0
  plan[0, :, Plan.ACCELERATION] = -0.1
  prev_action = log.ModelDataV2.Action.new_message()
  toggles = SimpleNamespace(vEgoStopping=0.42)

  action = modeld.get_action_from_model(
    {"plan": plan},
    prev_action,
    lat_action_t=0.2,
    long_action_t=0.73,
    v_ego=5.0,
    mlsim=True,
    is_v9=True,
    is_v14=False,
    is_v15=False,
    starpilot_toggles=toggles,
  )

  assert captured["action_t"] == pytest.approx(0.73)
  assert captured["vEgoStopping"] == pytest.approx(0.42)
  assert list(captured["t_idxs"]) == ModelConstants.T_IDXS
  np.testing.assert_allclose(captured["speeds"], 3.0)
  np.testing.assert_allclose(captured["accels"], -0.1)
  assert action.shouldStop


def test_modeld_action_uses_direct_action_head_for_v14(monkeypatch):
  monkeypatch.setenv("DEBUG", "0")
  fake_commonmodel = types.ModuleType("openpilot.selfdrive.modeld.models.commonmodel_pyx")
  fake_commonmodel.DrivingModelFrame = object
  fake_commonmodel.CLContext = object
  monkeypatch.setitem(sys.modules, fake_commonmodel.__name__, fake_commonmodel)

  from openpilot.selfdrive.modeld import modeld

  prev_action = log.ModelDataV2.Action.new_message()
  prev_action.desiredCurvature = 0.05
  prev_action.desiredAcceleration = -0.2
  toggles = SimpleNamespace(vEgoStopping=0.42)

  action = modeld.get_action_from_model(
    {"action": np.array([[12.0, -0.8]], dtype=np.float32)},
    prev_action,
    lat_action_t=0.2,
    long_action_t=0.73,
    v_ego=5.0,
    mlsim=True,
    is_v9=False,
    is_v14=True,
    is_v15=False,
    starpilot_toggles=toggles,
  )

  assert action.desiredCurvature == pytest.approx(0.12)
  assert action.desiredAcceleration < -0.2
  assert not action.shouldStop


def test_modeld_action_uses_current_action_head_scaling_for_v15(monkeypatch):
  monkeypatch.setenv("DEBUG", "0")
  fake_commonmodel = types.ModuleType("openpilot.selfdrive.modeld.models.commonmodel_pyx")
  fake_commonmodel.DrivingModelFrame = object
  fake_commonmodel.CLContext = object
  monkeypatch.setitem(sys.modules, fake_commonmodel.__name__, fake_commonmodel)

  from openpilot.selfdrive.modeld import modeld

  prev_action = log.ModelDataV2.Action.new_message()
  prev_action.desiredCurvature = 0.05
  prev_action.desiredAcceleration = -0.2
  toggles = SimpleNamespace(vEgoStopping=0.42)

  action = modeld.get_action_from_model(
    {"action": np.array([[12.0, -0.8]], dtype=np.float32)},
    prev_action,
    lat_action_t=0.2,
    long_action_t=0.73,
    v_ego=5.0,
    mlsim=True,
    is_v9=False,
    is_v14=False,
    is_v15=True,
    starpilot_toggles=toggles,
  )

  assert action.desiredCurvature == pytest.approx(0.48)
  assert action.desiredAcceleration < -0.2
  assert not action.shouldStop


def test_publish_force_stop_handoff_sets_should_stop_when_vcruise_zero():
  class FakePM:
    def __init__(self):
      self.sent = {}

    def send(self, name, msg):
      self.sent[name] = msg

  class FakeSM(dict):
    def all_checks(self, service_list=None):
      return True

    logMonoTime = {"modelV2": int(1e9)}

  v_ego = 5.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  planner.output_a_target = -0.5
  planner.output_should_stop = False
  planner.v_desired_trajectory = np.zeros(CONTROL_N)
  planner.a_desired_trajectory = np.zeros(CONTROL_N)
  planner.j_desired_trajectory = np.zeros(CONTROL_N)
  planner.fcw = False
  planner.mpc.source = "cruise"
  planner.mpc.solve_time = 0.0
  pm = FakePM()

  sm = FakeSM(make_sm(v_ego, desired_accel=0.0, min_accel=-1.0, experimental_mode=False))
  sm["starpilotPlan"].forcingStop = True
  sm["starpilotPlan"].forcingStopLength = 5.0
  sm["starpilotPlan"].vCruise = 0.0

  planner.publish(sm, pm)

  assert pm.sent["longitudinalPlan"].longitudinalPlan.shouldStop


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_force_stop_handoff_sets_output_should_stop_before_zero_vcruise(model_version):
  v_ego = 1.25
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(v_ego, desired_accel=-0.35, min_accel=-1.0, experimental_mode=False)
  sm["starpilotPlan"].forcingStop = True
  sm["starpilotPlan"].forcingStopLength = 6.5
  sm["starpilotPlan"].vCruise = 0.4
  sm["modelV2"].action.shouldStop = False

  planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop


def test_publish_force_stop_handoff_sets_should_stop_when_vcruise_low():
  class FakePM:
    def __init__(self):
      self.sent = {}

    def send(self, name, msg):
      self.sent[name] = msg

  class FakeSM(dict):
    def all_checks(self, service_list=None):
      return True

    logMonoTime = {"modelV2": int(1e9)}

  v_ego = 1.25
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  planner.output_a_target = -0.35
  planner.output_should_stop = False
  planner.v_desired_trajectory = np.zeros(CONTROL_N)
  planner.a_desired_trajectory = np.zeros(CONTROL_N)
  planner.j_desired_trajectory = np.zeros(CONTROL_N)
  planner.fcw = False
  planner.mpc.source = "cruise"
  planner.mpc.solve_time = 0.0
  pm = FakePM()

  sm = FakeSM(make_sm(v_ego, desired_accel=0.0, min_accel=-1.0, experimental_mode=False))
  sm["starpilotPlan"].forcingStop = True
  sm["starpilotPlan"].forcingStopLength = 6.5
  sm["starpilotPlan"].vCruise = 0.4

  planner.publish(sm, pm)

  assert pm.sent["longitudinalPlan"].longitudinalPlan.shouldStop


def test_allow_throttle_hysteresis_filters_gas_prob_chatter():
  v_ego = 10.0

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(v_ego, desired_accel=0.0, min_accel=-1.0, experimental_mode=False, gas_press_prob=0.5)
  toggles = make_toggles()

  planner.update(sm, toggles)
  assert planner.model_allow_throttle
  assert planner.allow_throttle

  sm["modelV2"] = make_model(v_ego, desired_accel=0.0, gas_press_prob=0.37)
  planner.update(sm, toggles)
  assert planner.model_allow_throttle
  assert planner.allow_throttle

  sm["modelV2"] = make_model(v_ego, desired_accel=0.0, gas_press_prob=0.34)
  planner.update(sm, toggles)
  assert not planner.model_allow_throttle
  assert not planner.allow_throttle

  sm["modelV2"] = make_model(v_ego, desired_accel=0.0, gas_press_prob=0.43)
  planner.update(sm, toggles)
  assert not planner.model_allow_throttle
  assert not planner.allow_throttle

  sm["modelV2"] = make_model(v_ego, desired_accel=0.0, gas_press_prob=0.46)
  planner.update(sm, toggles)
  assert planner.model_allow_throttle
  assert planner.allow_throttle


def test_no_throttle_cap_stays_at_coast_limit_until_throttle_returns():
  v_ego = 8.5

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(v_ego, desired_accel=0.0, min_accel=-3.0, experimental_mode=False, gas_press_prob=0.0)
  sm["carControl"].orientationNED = [0.0, 0.1, 0.0]
  toggles = make_toggles()

  planner.update(sm, toggles)

  accel_coast = max(get_vehicle_min_accel(CP, v_ego), get_coast_accel(sm["carControl"].orientationNED[1]))

  assert not planner.allow_throttle
  assert planner.output_a_target == pytest.approx(accel_coast, abs=1e-3)


def test_low_speed_follow_catchup_accel_cap_limits_close_vision_catchup():
  v_ego = 7.8
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=18.4, v_lead=8.2, radar=False, model_prob=0.98)

  cap = planner.get_lead_catchup_accel_cap(lead, v_ego, 1.45)

  assert cap is not None
  assert 0.15 <= cap <= 0.45


def test_low_speed_follow_catchup_uses_raw_vehicle_speed_when_cluster_runs_high():
  v_ego = 7.8
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.6,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=16.0, v_lead=8.4, radar=False, model_prob=0.99),
  )
  sm["carState"].vEgoCluster = 9.2
  sm["starpilotPlan"].vCruise = v_ego + 4.0

  for _ in range(6):
    planner.update(sm, make_toggles())

  assert planner.output_a_target <= 0.20


def test_low_speed_follow_transition_brake_cap_softens_first_sign_flip():
  v_ego = 7.7
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=18.6, v_lead=7.6, radar=False, model_prob=0.98)

  cap = planner.get_low_speed_follow_transition_brake_cap(lead, v_ego, 1.45, 0.59, -0.24)

  assert cap is not None
  assert -0.14 <= cap <= -0.08


def test_low_speed_follow_transition_brake_cap_stays_off_when_gap_is_tight():
  v_ego = 7.7
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=13.0, v_lead=7.6, radar=False, model_prob=0.98)

  cap = planner.get_low_speed_follow_transition_brake_cap(lead, v_ego, 1.45, 0.59, -0.24)

  assert cap is None


def test_far_near_speed_follow_keeps_uncertainty_smoothing_active():
  v_ego = 30.0

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.0,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=78.0, v_lead=29.2, radar=False, model_prob=0.96),
  )
  sm["modelV2"] = make_model(v_ego, desired_accel=0.0, gas_press_prob=1.0, brake_press_prob=0.52)
  toggles = make_toggles()

  for _ in range(12):
    planner.update(sm, toggles)

  assert planner.mpc.filter_time_factor > 0.75


def test_near_speed_follow_keeps_some_smoothing_under_high_uncertainty():
  v_ego = 31.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=53.0, v_lead=29.8, radar=False, model_prob=0.96)
  sm = make_sm(
    v_ego,
    desired_accel=0.0,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=lead,
    brake_press_prob=0.85,
  )

  for _ in range(16):
    planner.update(sm, make_toggles())

  assert planner.mpc.filter_time_factor >= 0.24


def test_near_speed_follow_soft_brake_cap_limits_matched_follow_pulse():
  v_ego = 31.4
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=44.0, v_lead=30.1, radar=False, model_prob=0.96)
  sm = make_sm(
    v_ego,
    desired_accel=0.0,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=lead,
    brake_press_prob=0.85,
  )

  for _ in range(16):
    planner.update(sm, make_toggles())

  assert planner.mpc.filter_time_factor >= 0.24
  assert planner.output_a_target >= -0.33


def test_near_speed_follow_soft_brake_cap_covers_slightly_opening_lead():
  v_ego = 29.58
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=44.44, v_lead=30.65, radar=False, model_prob=0.98)

  cap = planner.get_matched_follow_brake_cap(lead, v_ego, 1.45)

  assert cap is not None
  assert cap >= -0.14
  assert cap <= -0.06


def test_near_speed_follow_soft_brake_cap_extends_to_spacious_modest_closing():
  v_ego = 23.69
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=49.48, v_lead=21.64, a_lead=-0.014, radar=False, model_prob=0.998)

  cap = planner.get_matched_follow_brake_cap(lead, v_ego, 1.45)

  assert cap is not None
  assert cap >= -0.33
  assert cap <= -0.22


def test_near_speed_follow_soft_brake_cap_uses_raw_vehicle_speed_when_cluster_runs_high():
  v_ego = 23.0073
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=47.52, v_lead=21.68, a_lead=-0.0646, radar=False, model_prob=0.998),
  )
  sm["carState"].vEgoCluster = 23.6931
  sm["starpilotPlan"].maxAcceleration = 0.61

  for _ in range(6):
    planner.update(sm, make_toggles())

  assert not planner.lead_is_matched_follow_window(sm["radarState"].leadOne, sm["carState"].vEgoCluster, 1.45)
  assert planner.output_a_target > -0.35
  assert planner.output_a_target < -0.22


def test_near_speed_follow_soft_brake_cap_rejects_close_gap_even_with_modest_closing():
  v_ego = 37.19
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=34.70, v_lead=35.88, radar=False, model_prob=0.99)

  cap = planner.get_matched_follow_brake_cap(lead, v_ego, 1.0)

  assert cap is None


def test_follow_control_lead_prefers_active_lead1_for_matched_follow():
  v_ego = 23.3
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  planner.lead_one = make_lead(status=True, d_rel=80.0, v_lead=20.0, radar=False, model_prob=0.6)
  planner.lead_two = make_lead(status=True, d_rel=49.9, v_lead=21.9, radar=False, model_prob=0.98)
  planner.mpc.source = "lead1"

  follow_lead = planner.get_follow_control_lead(True, v_ego, 1.45)

  assert follow_lead is planner.lead_two


def test_follow_control_lead_disables_optional_matched_follow_override():
  v_ego = 23.3
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  planner.lead_one = make_lead(status=True, d_rel=80.0, v_lead=20.0, radar=False, model_prob=0.6)
  planner.lead_two = make_lead(status=True, d_rel=49.9, v_lead=21.9, radar=False, model_prob=0.98)
  planner.mpc.source = "lead1"

  follow_lead = planner.get_follow_control_lead(True, v_ego, 1.45, allow_optional_far_lead_logic=False)

  assert follow_lead is planner.lead_one


def test_follow_control_lead_keeps_matched_follow_lead_without_tracking_latch():
  v_ego = 27.5
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  planner.lead_one = make_lead(status=True, d_rel=61.99, v_lead=27.63, radar=False, model_prob=0.99)

  follow_lead = planner.get_follow_control_lead(False, v_ego, 1.45)

  assert follow_lead is planner.lead_one


def test_follow_control_lead_requires_real_lead_control_when_optional_logic_disabled():
  v_ego = 27.5
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  planner.lead_one = make_lead(status=True, d_rel=61.99, v_lead=27.63, radar=False, model_prob=0.99)

  follow_lead = planner.get_follow_control_lead(False, v_ego, 1.45, allow_optional_far_lead_logic=False)

  assert follow_lead is None


def test_far_lead_soft_brake_cap_limits_high_confidence_distant_vision_lead():
  v_ego = 32.37
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=82.07, v_lead=30.63, a_lead=-0.01, radar=False, model_prob=0.99)

  cap = planner.get_far_lead_brake_cap(lead, v_ego, 1.70)

  assert cap is not None
  assert cap > -0.2
  assert cap < -0.05


def test_matched_follow_transition_target_damps_large_comfort_sign_flip():
  v_ego = 20.3
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=45.6, v_lead=19.19, a_lead=0.0, radar=False, model_prob=0.99)

  smoothed = planner.get_matched_follow_transition_target(
    lead,
    v_ego,
    1.45,
    prev_output_a_target=0.12,
    output_a_target=-0.40,
    current_source="cruise",
    tracking_lead_active=True,
  )

  assert smoothed is not None
  assert smoothed > -0.05
  assert smoothed < 0.12


def test_matched_follow_transition_target_skips_urgent_closure():
  v_ego = 31.5
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=35.0, v_lead=28.0, a_lead=0.0, radar=False, model_prob=0.99)

  smoothed = planner.get_matched_follow_transition_target(
    lead,
    v_ego,
    1.45,
    prev_output_a_target=0.10,
    output_a_target=-0.60,
    current_source="cruise",
    tracking_lead_active=True,
  )

  assert smoothed is None


def test_matched_follow_transition_target_damps_low_speed_tracking_cruise_throttle_jitter():
  v_ego = 14.5
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=31.1, v_lead=14.5, a_lead=0.0, radar=False, model_prob=0.999)

  smoothed = planner.get_matched_follow_transition_target(
    lead,
    v_ego,
    1.45,
    prev_output_a_target=0.08,
    output_a_target=0.46,
    current_source="cruise",
    tracking_lead_active=True,
  )

  assert smoothed is not None
  assert smoothed == pytest.approx(0.14, abs=1e-6)


def test_matched_follow_transition_target_skips_low_speed_without_tracking():
  v_ego = 14.5
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=31.1, v_lead=14.5, a_lead=0.0, radar=False, model_prob=0.999)

  smoothed = planner.get_matched_follow_transition_target(
    lead,
    v_ego,
    1.45,
    prev_output_a_target=0.08,
    output_a_target=0.46,
    current_source="cruise",
    tracking_lead_active=False,
  )

  assert smoothed is None


def test_matched_follow_transition_target_skips_low_speed_real_braking():
  v_ego = 14.5
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=29.0, v_lead=13.6, a_lead=0.0, radar=False, model_prob=0.999)

  smoothed = planner.get_matched_follow_transition_target(
    lead,
    v_ego,
    1.45,
    prev_output_a_target=0.08,
    output_a_target=-0.30,
    current_source="cruise",
    tracking_lead_active=True,
  )

  assert smoothed is None


def test_cruise_tracking_lead_accel_cap_limits_mid_speed_follow_nibble():
  v_ego = 16.2
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=33.4, v_lead=16.0, a_lead=0.0, radar=False, model_prob=0.99, y_rel=0.12)

  cap = planner.get_cruise_tracking_lead_accel_cap(
    lead,
    v_ego,
    1.45,
    current_source="cruise",
    tracking_lead_active=True,
  )

  assert cap is not None
  assert 0.05 <= cap <= 0.10


def test_cruise_tracking_lead_accel_cap_blocks_unresolved_raw_close_lead_burst():
  v_ego = 17.6
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=41.9, v_lead=14.2, a_lead=0.0, radar=True, model_prob=0.99, y_rel=-0.97)

  cap = planner.get_cruise_tracking_lead_accel_cap(
    lead,
    v_ego,
    1.45,
    current_source="cruise",
    tracking_lead_active=False,
  )

  assert cap is not None
  assert 0.0 <= cap <= 0.05


def test_cruise_tracking_lead_accel_cap_skips_when_lead_clearly_pulls_away():
  v_ego = 14.5
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=35.0, v_lead=16.0, a_lead=0.0, radar=False, model_prob=0.99, y_rel=0.1)

  cap = planner.get_cruise_tracking_lead_accel_cap(
    lead,
    v_ego,
    1.45,
    current_source="cruise",
    tracking_lead_active=True,
  )

  assert cap is None


def test_cruise_tracking_lead_accel_transition_target_damps_mid_speed_reacquisition_burst():
  v_ego = 16.2
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=20.0, v_lead=17.4, a_lead=0.0, radar=False, model_prob=0.99, y_rel=0.18)

  smoothed = planner.get_cruise_tracking_lead_accel_transition_target(
    lead,
    v_ego,
    1.45,
    prev_output_a_target=0.10,
    output_a_target=1.10,
    current_source="cruise",
  )

  assert smoothed is not None
  assert smoothed == pytest.approx(0.23, abs=1e-2)


def test_cruise_tracking_lead_accel_transition_target_skips_clear_pullaway():
  v_ego = 16.2
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=34.0, v_lead=19.2, a_lead=0.0, radar=False, model_prob=0.99, y_rel=0.12)

  smoothed = planner.get_cruise_tracking_lead_accel_transition_target(
    lead,
    v_ego,
    1.45,
    prev_output_a_target=0.10,
    output_a_target=1.10,
    current_source="cruise",
  )

  assert smoothed is None


def test_mild_follow_zero_cross_guard_coasts_on_cruise_sign_flip():
  v_ego = 19.8
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=42.0, v_lead=19.0, a_lead=-0.15, radar=False, model_prob=0.99, y_rel=0.10)

  guarded = planner.get_mild_follow_zero_cross_guard_target(
    lead,
    v_ego,
    1.45,
    prev_output_a_target=0.18,
    output_a_target=-0.12,
    current_source="cruise",
    tracking_lead_active=True,
  )

  assert guarded == pytest.approx(0.0, abs=1e-6)


def test_mild_follow_zero_cross_guard_coasts_on_near_duplicate_sign_flip():
  v_ego = 24.5
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=51.0, v_lead=21.7, a_lead=-0.25, radar=False, model_prob=0.99, y_rel=0.08)

  guarded = planner.get_mild_follow_zero_cross_guard_target(
    lead,
    v_ego,
    1.45,
    prev_output_a_target=0.33,
    output_a_target=-0.13,
    current_source="lead1",
    tracking_lead_active=True,
  )

  assert guarded == pytest.approx(0.0, abs=1e-6)


def test_mild_follow_zero_cross_guard_skips_urgent_close_follow():
  v_ego = 17.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=16.0, v_lead=12.0, a_lead=-0.45, radar=False, model_prob=0.99, y_rel=0.05)

  guarded = planner.get_mild_follow_zero_cross_guard_target(
    lead,
    v_ego,
    1.45,
    prev_output_a_target=0.22,
    output_a_target=-0.28,
    current_source="cruise",
    tracking_lead_active=True,
  )

  assert guarded is None


def test_prioritize_smooth_following_skips_post_097_follow_nudges():
  v_ego = 16.2
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  lead = make_lead(status=True, d_rel=33.4, v_lead=16.0, a_lead=0.0, radar=False, model_prob=0.99, y_rel=0.12)

  def run_once(prioritize_smooth_following: bool) -> list[str]:
    planner = LongitudinalPlanner(CP, init_v=v_ego)
    sm = make_sm(
      v_ego,
      desired_accel=0.8,
      min_accel=-0.5,
      experimental_mode=False,
      tracking_lead=True,
      lead_one=lead,
    )
    sm["starpilotPlan"].vCruise = v_ego + 8.0

    calls = []

    def record(name, return_value=None):
      def _inner(self, *args, **kwargs):
        calls.append(name)
        return return_value
      return types.MethodType(_inner, planner)

    planner.get_follow_control_lead = record("get_follow_control_lead", lead)
    planner.get_lead_catchup_accel_cap = record("get_lead_catchup_accel_cap", None)
    planner.get_tracked_vision_model_brake_floor = record("get_tracked_vision_model_brake_floor", None)
    planner.get_low_speed_follow_transition_brake_cap = record("get_low_speed_follow_transition_brake_cap", None)
    planner.get_tracked_vision_model_brake_cap = record("get_tracked_vision_model_brake_cap", None)
    planner.get_cruise_tracking_lead_accel_cap = record("get_cruise_tracking_lead_accel_cap", None)
    planner.get_cruise_tracking_lead_accel_transition_target = record("get_cruise_tracking_lead_accel_transition_target", None)

    planner.update(sm, make_toggles(prioritize_smooth_following=prioritize_smooth_following))
    return calls

  calls_default = run_once(False)
  calls_smooth = run_once(True)

  expected_calls = {
    "get_lead_catchup_accel_cap",
    "get_follow_control_lead",
    "get_tracked_vision_model_brake_floor",
    "get_low_speed_follow_transition_brake_cap",
    "get_tracked_vision_model_brake_cap",
    "get_cruise_tracking_lead_accel_cap",
    "get_cruise_tracking_lead_accel_transition_target",
  }

  assert expected_calls.issubset(set(calls_default))
  assert not expected_calls.intersection(set(calls_smooth))


def test_near_duplicate_lead_source_hysteresis_prefers_previous_source():
  v_ego = 27.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=46.2, v_lead=25.5, a_lead=-0.05, radar=False, model_prob=0.99)
  lead_two = make_lead(status=True, d_rel=46.8, v_lead=25.55, a_lead=-0.03, radar=False, model_prob=0.99)

  lead_0_bias, lead_1_bias = planner.mpc.get_near_duplicate_lead_source_hysteresis("lead0", lead_one, lead_two, v_ego)

  assert lead_0_bias == 0.0
  assert lead_1_bias > 0.0


def test_stable_follow_cruise_hysteresis_applies_for_radar_lead():
  v_ego = 27.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=40.5, v_lead=26.3, a_lead=-0.02, radar=True, model_prob=1.0)

  hysteresis = planner.mpc.get_stable_follow_cruise_hysteresis(lead, v_ego, 1.45)

  assert hysteresis > 0.0


def test_stable_follow_cruise_hysteresis_skips_fast_closing_radar_lead():
  v_ego = 27.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=40.5, v_lead=21.5, a_lead=-0.02, radar=True, model_prob=1.0)

  hysteresis = planner.mpc.get_stable_follow_cruise_hysteresis(lead, v_ego, 1.45)

  assert hysteresis == 0.0


def test_near_duplicate_lead_source_hysteresis_skips_distinct_leads():
  v_ego = 27.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=41.0, v_lead=23.8, a_lead=0.0, radar=False, model_prob=0.99)
  lead_two = make_lead(status=True, d_rel=48.0, v_lead=25.4, a_lead=0.0, radar=False, model_prob=0.99)

  lead_0_bias, lead_1_bias = planner.mpc.get_near_duplicate_lead_source_hysteresis("lead0", lead_one, lead_two, v_ego)

  assert lead_0_bias == 0.0
  assert lead_1_bias == 0.0


def test_near_duplicate_lead_transition_target_damps_same_source_sign_flip():
  v_ego = 25.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=44.6, v_lead=24.05, a_lead=-0.03, radar=False, model_prob=0.99)
  lead_two = make_lead(status=True, d_rel=45.1, v_lead=24.0, a_lead=-0.04, radar=False, model_prob=0.99)
  lead_one.vRel = -0.95
  lead_two.vRel = -1.00
  planner.lead_one = lead_one
  planner.lead_two = lead_two

  smoothed = planner.get_near_duplicate_lead_transition_target(
    lead_two,
    v_ego,
    1.45,
    prev_output_a_target=-1.10,
    output_a_target=0.13,
    current_source="lead1",
    tracking_lead_active=True,
  )

  assert smoothed is not None
  assert smoothed == pytest.approx(-0.92, abs=1e-6)


def test_near_duplicate_lead_transition_target_damps_tracking_cruise_sign_flip():
  v_ego = 25.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=44.6, v_lead=24.05, a_lead=-0.03, radar=False, model_prob=0.99)
  lead_two = make_lead(status=True, d_rel=45.1, v_lead=24.0, a_lead=-0.04, radar=False, model_prob=0.99)
  lead_one.vRel = -0.95
  lead_two.vRel = -1.00
  planner.lead_one = lead_one
  planner.lead_two = lead_two

  smoothed = planner.get_near_duplicate_lead_transition_target(
    lead_two,
    v_ego,
    1.45,
    prev_output_a_target=-1.10,
    output_a_target=0.13,
    current_source="cruise",
    tracking_lead_active=True,
  )

  assert smoothed is not None
  assert smoothed == pytest.approx(-0.92, abs=1e-6)


def test_near_duplicate_lead_transition_target_skips_plain_cruise_without_tracking():
  v_ego = 25.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=44.6, v_lead=24.05, a_lead=-0.03, radar=False, model_prob=0.99)
  lead_two = make_lead(status=True, d_rel=45.1, v_lead=24.0, a_lead=-0.04, radar=False, model_prob=0.99)
  lead_one.vRel = -0.95
  lead_two.vRel = -1.00
  planner.lead_one = lead_one
  planner.lead_two = lead_two

  smoothed = planner.get_near_duplicate_lead_transition_target(
    lead_two,
    v_ego,
    1.45,
    prev_output_a_target=-1.10,
    output_a_target=0.13,
    current_source="cruise",
    tracking_lead_active=False,
  )

  assert smoothed is None
