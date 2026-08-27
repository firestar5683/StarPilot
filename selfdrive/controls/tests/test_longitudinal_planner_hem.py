#!/usr/bin/env python3
import numpy as np
import pytest
from types import SimpleNamespace

from cereal import log
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner, get_vehicle_min_accel
from openpilot.selfdrive.modeld.constants import ModelConstants

TRAJ_LEN = len(ModelConstants.T_IDXS)


def make_lead(*, status, d_rel=200.0, v_lead=0.0, a_lead=0.0, radar=False, model_prob=0.0):
  lead = log.RadarState.LeadData.new_message()
  lead.status = status
  lead.dRel = d_rel
  lead.vLead = v_lead
  lead.vLeadK = v_lead
  lead.aLeadK = a_lead
  lead.vRel = 0.0
  lead.aRel = 0.0
  lead.yRel = 0.0
  lead.modelProb = model_prob
  lead.radar = radar
  return lead


def make_model(v_ego, desired_accel, *, velocity_traj=None, should_stop=False):
  model = log.ModelDataV2.new_message()
  model.init('leadsV3', 3)
  t_idxs = ModelConstants.T_IDXS
  n = len(t_idxs)

  model.position.x = [float(v_ego * t) for t in t_idxs]
  model.position.y = [0.0] * n
  model.position.z = [0.0] * n
  model.position.t = [float(t) for t in t_idxs]

  if velocity_traj is None:
    model.velocity.x = [float(v_ego)] * n
  else:
    model.velocity.x = [float(x) for x in velocity_traj]
  model.velocity.y = [0.0] * n
  model.velocity.z = [0.0] * n
  model.velocity.t = [float(t) for t in t_idxs]

  model.acceleration.x = [0.0] * n
  model.acceleration.y = [0.0] * n
  model.acceleration.z = [0.0] * n
  model.acceleration.t = [float(t) for t in t_idxs]

  model.action.desiredAcceleration = desired_accel
  model.action.shouldStop = should_stop
  return model


def make_sm(v_ego, desired_accel, min_accel, *, experimental_mode=True, tracking_lead=False,
            lead_one=None, velocity_traj=None, should_stop=False):
  if lead_one is None:
    lead_one = make_lead(status=False)
  return {
    "carControl": SimpleNamespace(orientationNED=[0.0, 0.0, 0.0]),
    "carState": SimpleNamespace(
      vEgo=v_ego, vEgoCluster=v_ego, aEgo=0.0, vCruise=100.0, standstill=False,
      steeringAngleDeg=0.0,
    ),
    "controlsState": SimpleNamespace(longControlState=0, forceDecel=False),
    "liveParameters": SimpleNamespace(angleOffsetDeg=0.0),
    "modelV2": make_model(v_ego, desired_accel, velocity_traj=velocity_traj, should_stop=should_stop),
    "radarState": SimpleNamespace(leadOne=lead_one, leadTwo=make_lead(status=False)),
    "selfdriveState": SimpleNamespace(enabled=True, experimentalMode=experimental_mode, personality=0),
    "starpilotCarState": SimpleNamespace(accelPressed=False),
    "starpilotPlan": SimpleNamespace(
      vCruise=v_ego + 5.0,
      minAcceleration=min_accel,
      maxAcceleration=2.0,
      disableThrottle=False,
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


def make_toggles(*, hybrid=False, exp_bias=0.0, sens=1.0):
  return SimpleNamespace(
    taco_tune=False,
    classic_model=False,
    tinygrad_model=True,
    model_version="v11",
    vEgoStopping=0.5,
    radar_takeoffs=False,
    hybrid_experimental_mode=hybrid,
    hybrid_exp_bias=exp_bias,
    hybrid_vision_brake_sensitivity=sens,
  )


def assert_outputs_equal(p1, p2, label=""):
  assert p1.output_a_target == pytest.approx(p2.output_a_target, abs=1e-9), f"{label} aTarget mismatch"
  assert p1.output_should_stop == p2.output_should_stop, f"{label} shouldStop mismatch"
  np.testing.assert_allclose(p1.v_desired_trajectory, p2.v_desired_trajectory, atol=1e-9)
  np.testing.assert_allclose(p1.a_desired_trajectory, p2.a_desired_trajectory, atol=1e-9)


# 1. Toggle equivalence (regression safety)
def _run_equivalence_scenarios(experimental_mode):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)

  scenarios = [
    dict(v_ego=20.0, desired_accel=0.4, min_accel=-2.0, tracking_lead=False,
         lead_one=None, velocity_traj=None, should_stop=False, label="chill-cruise"),
    dict(v_ego=20.0, desired_accel=-0.6, min_accel=-2.0, tracking_lead=True,
         lead_one=make_lead(status=True, d_rel=30.0, v_lead=18.0, radar=True, model_prob=1.0),
         velocity_traj=None, should_stop=False, label="slow-lead"),
    dict(v_ego=25.0, desired_accel=-1.2, min_accel=-3.0, tracking_lead=True,
         lead_one=make_lead(status=True, d_rel=12.0, v_lead=3.0, radar=True, model_prob=1.0),
         velocity_traj=list(np.linspace(25.0, 2.0, TRAJ_LEN)), should_stop=True, label="stop-approach"),
  ]

  for scen in scenarios:
    label = scen.pop("label")
    hybrid_planner = LongitudinalPlanner(CP, init_v=scen["v_ego"])
    stock_planner = LongitudinalPlanner(CP, init_v=scen["v_ego"])
    sm = make_sm(experimental_mode=experimental_mode, **scen)
    hybrid_planner.update(sm, make_toggles(hybrid=True) if False else make_toggles(hybrid=False))
    stock_planner.update(sm, make_toggles())
    assert_outputs_equal(hybrid_planner, stock_planner, label=f"chill/{label}" if not experimental_mode else f"exp/{label}")


def test_hem_off_matches_stock_chill_mode():
  _run_equivalence_scenarios(experimental_mode=False)


def test_hem_off_matches_stock_experimental_mode():
  _run_equivalence_scenarios(experimental_mode=True)


# 2. Stop sign / red light approach
def test_stop_sign_approach_commands_pure_model_braking():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=20.0)
  toggles = make_toggles(hybrid=True)
  sm = make_sm(20.0, -2.5, -4.0, experimental_mode=False,
               velocity_traj=list(np.linspace(20.0, 0.0, TRAJ_LEN)), should_stop=True)
  # Enough frames for the jerk slew limiter to ramp to full vision braking.
  for _ in range(20):
    planner.update(sm, toggles)
  assert planner.output_a_target <= -2.0, "Exp stop braking must not be diluted by cruise throttle"
  assert planner.output_a_target < 0.0, "Cruise throttle must be locked out during a vision stop"


def test_stop_line_handshake_asserts_should_stop():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.3)
  toggles = make_toggles(hybrid=True)
  sm = make_sm(0.3, -1.0, -4.0, experimental_mode=False,
               velocity_traj=[0.0] * TRAJ_LEN, should_stop=True)
  for _ in range(6):
    planner.update(sm, toggles)
  assert planner.output_should_stop, "Standstill at a predicted stop must assert shouldStop"
  assert planner.output_a_target <= -0.4, "Standstill brake must be held at the stop line"


# 3. Slower-lead approach (radar + vision blend within safety)
def test_slower_lead_approach_blends_vision_prebrake_within_safety():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=20.0)
  toggles = make_toggles(hybrid=True)
  lead = make_lead(status=True, d_rel=25.0, v_lead=0.4, radar=True, model_prob=1.0)
  sm = make_sm(20.0, -1.5, -4.0, experimental_mode=False, tracking_lead=True, lead_one=lead,
               velocity_traj=list(np.linspace(20.0, 5.0, TRAJ_LEN)), should_stop=False)
  for _ in range(15):
    planner.update(sm, toggles)
  # Vision pre-braking must be engaged while closing on a slower lead.
  assert planner.output_a_target <= -1.0, "Vision pre-brake should be blended in on a slow lead"
  # ...but it must never exceed the physical / commanded deceleration floors.
  assert planner.output_a_target >= get_vehicle_min_accel(CP, 20.0)
  assert planner.output_a_target >= -4.0


# 4. Green light / lead departure (instant unlatch)
def test_green_light_departure_instantly_clears_should_stop():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.3)
  toggles = make_toggles(hybrid=True)

  sm_stop = make_sm(0.3, -1.0, -4.0, experimental_mode=False,
                    velocity_traj=[0.0] * TRAJ_LEN, should_stop=True)
  for _ in range(6):
    planner.update(sm_stop, toggles)
  assert planner.output_should_stop
  assert planner.output_a_target <= -0.4

  # Green light / lead pulls away: horizon ramps up and Exp accelerates. Run a
  # few frames so the jerk slew ramps the commanded accel up from the brake hold.
  sm_go = make_sm(0.3, 1.5, -4.0, experimental_mode=False,
                  velocity_traj=list(np.linspace(0.0, 8.0, TRAJ_LEN)), should_stop=False)
  sm_go["starpilotPlan"].vCruise = 15.0
  for _ in range(6):
    planner.update(sm_go, toggles)

  assert not planner.output_should_stop, "Departure must instantly clear the stop latch"
  assert planner.output_a_target > 0.0, "Departure must deliver positive cruise acceleration"


def test_lead_departure_clears_stop_without_sticky_latch():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.3)
  toggles = make_toggles(hybrid=True)

  sm_stop = make_sm(0.3, -1.0, -4.0, experimental_mode=False, tracking_lead=True,
                    lead_one=make_lead(status=True, d_rel=3.0, v_lead=0.1, radar=True, model_prob=1.0),
                    velocity_traj=[0.0] * TRAJ_LEN, should_stop=True)
  for _ in range(6):
    planner.update(sm_stop, toggles)
  assert planner.output_should_stop

  # Lead accelerates away from standstill and opens up a safe gap.
  sm_go = make_sm(0.3, 1.0, -4.0, experimental_mode=False, tracking_lead=True,
                  lead_one=make_lead(status=True, d_rel=25.0, v_lead=10.0, radar=True, model_prob=1.0),
                  velocity_traj=list(np.linspace(0.0, 7.0, TRAJ_LEN)), should_stop=False)
  sm_go["starpilotPlan"].vCruise = 15.0
  for _ in range(6):
    planner.update(sm_go, toggles)

  # HEM's own vision latch releases instantly (no sticky vision authority).
  assert planner.hybrid_controller.w_vision == 0.0
  assert not planner.output_should_stop, "Lead departure must clear shouldStop without lag"
  assert planner.output_a_target > 0.0


# 5. Safety clamping preservation
def test_radar_cut_in_preserves_chill_floor_within_physical_limits():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=20.0)
  toggles = make_toggles(hybrid=True)
  lead = make_lead(status=True, d_rel=6.0, v_lead=10.0, radar=True, model_prob=1.0)
  sm = make_sm(20.0, 0.0, -3.5, experimental_mode=False, tracking_lead=True, lead_one=lead,
               velocity_traj=[20.0] * TRAJ_LEN, should_stop=False)
  for _ in range(15):
    planner.update(sm, toggles)
  assert planner.output_a_target <= -1.0, "Radar cut-in must brake hard at the planner output"
  assert planner.output_a_target >= -3.5, "Output must never exceed the commanded accel_min floor"
  assert planner.output_a_target >= get_vehicle_min_accel(CP, 20.0), "Physical decel limit respected"


def test_hem_output_clamped_to_physical_limits_under_corrupt_exp():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  lo = get_vehicle_min_accel(CP, 20.0)
  for a_exp in (float("nan"), -100.0, 100.0):
    planner = LongitudinalPlanner(CP, init_v=20.0)
    sm = make_sm(20.0, a_exp, -3.5, experimental_mode=False,
                 velocity_traj=[20.0] * TRAJ_LEN, should_stop=False)
    for _ in range(3):
      planner.update(sm, make_toggles(hybrid=True))
    assert np.isfinite(planner.output_a_target), f"corrupt a_exp={a_exp} must not propagate"
    assert lo - 1e-6 <= planner.output_a_target <= 2.0 + 1e-6


def test_output_stays_within_physical_limits_across_scenarios():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  scenarios = [
    dict(v_ego=20.0, desired_accel=-2.5, min_accel=-4.0, tracking_lead=False,
         lead_one=None, velocity_traj=list(np.linspace(20.0, 0.0, TRAJ_LEN)), should_stop=True),
    dict(v_ego=20.0, desired_accel=0.5, min_accel=-3.0, tracking_lead=True,
         lead_one=make_lead(status=True, d_rel=40.0, v_lead=22.0, radar=True, model_prob=1.0),
         velocity_traj=None, should_stop=False),
  ]
  for scen in scenarios:
    planner = LongitudinalPlanner(CP, init_v=scen["v_ego"])
    sm = make_sm(experimental_mode=False, **scen)
    for _ in range(6):
      planner.update(sm, make_toggles(hybrid=True))
    assert planner.output_a_target >= get_vehicle_min_accel(CP, scen["v_ego"])
    assert planner.output_a_target <= 2.0
