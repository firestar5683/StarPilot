from types import SimpleNamespace

import numpy as np
import pytest

from cereal import log
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from opendbc.car.gm.values import CAR as GM_CAR, GMFlags

import openpilot.selfdrive.controls.lib.longitudinal_planner as planner_module
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import (
  T_IDXS,
  LongitudinalMpc,
  should_trigger_planner_fcw,
)
from openpilot.selfdrive.controls.lib.longitudinal_planner import (
  MIN_PLAN_HORIZON,
  LongitudinalPlanner,
  PlanState,
  get_vehicle_min_accel,
)
from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import get_longitudinal_planner_tune
from openpilot.selfdrive.modeld.constants import ModelConstants


def make_lead(*, status=False, d_rel=200.0, v_lead=0.0, a_lead=0.0,
              radar=False, model_prob=1.0):
  lead = log.RadarState.LeadData.new_message()
  lead.status = status
  lead.dRel = d_rel
  lead.vLead = v_lead
  lead.vLeadK = v_lead
  lead.vRel = 0.0
  lead.aLeadK = a_lead
  lead.aLeadTau = 1.5
  lead.modelProb = model_prob
  lead.radar = radar
  return lead


def make_model(v_ego, desired_accel=0.0):
  model = log.ModelDataV2.new_message()
  times = np.asarray(ModelConstants.T_IDXS)
  model.position.x = (v_ego * times).tolist()
  model.position.y = [0.0] * len(times)
  model.position.z = [0.0] * len(times)
  model.position.t = times.tolist()
  model.velocity.x = [v_ego] * len(times)
  model.velocity.y = [0.0] * len(times)
  model.velocity.z = [0.0] * len(times)
  model.velocity.t = times.tolist()
  model.acceleration.x = [0.0] * len(times)
  model.acceleration.y = [0.0] * len(times)
  model.acceleration.z = [0.0] * len(times)
  model.acceleration.t = times.tolist()
  model.meta.disengagePredictions.gasPressProbs = [1.0] * 6
  model.action.desiredAcceleration = desired_accel
  model.action.shouldStop = False
  return model


def set_model_departure(model, accel=0.5):
  times = np.asarray(ModelConstants.T_IDXS)
  model.position.x = (2.0 * times + 0.5 * accel * times ** 2).tolist()
  model.velocity.x = (2.0 + accel * times).tolist()
  model.acceleration.x = [accel] * len(times)
  model.action.desiredAcceleration = accel
  model.action.shouldStop = False


def set_model_stop(model, distance=5.0):
  count = len(ModelConstants.T_IDXS)
  model.position.x = np.linspace(0.0, distance, count).tolist()
  model.velocity.x = np.linspace(10.0, 0.0, count).tolist()
  model.action.desiredAcceleration = -1.0


def make_sm(v_ego=20.0, *, v_cruise=None, model_accel=0.0, lead_one=None, lead_two=None):
  v_cruise = v_ego + 5.0 if v_cruise is None else v_cruise
  return {
    "carControl": SimpleNamespace(orientationNED=[0.0, 0.0, 0.0]),
    "carState": SimpleNamespace(
      vEgo=v_ego,
      vEgoCluster=v_ego,
      aEgo=0.0,
      vCruise=100.0,
      standstill=v_ego == 0.0,
      steeringAngleDeg=0.0,
      brakePressed=False,
      leftBlinker=False,
      rightBlinker=False,
    ),
    "controlsState": SimpleNamespace(longControlState=LongCtrlState.pid, forceDecel=False),
    "liveParameters": SimpleNamespace(angleOffsetDeg=0.0),
    "modelV2": make_model(v_ego, model_accel),
    "radarState": SimpleNamespace(
      leadOne=lead_one or make_lead(),
      leadTwo=lead_two or make_lead(),
    ),
    "selfdriveState": SimpleNamespace(
      enabled=True,
      personality=log.LongitudinalPersonality.standard,
    ),
    "starpilotPlan": SimpleNamespace(
      vCruise=v_cruise,
      minAcceleration=-3.5,
      maxAcceleration=2.0,
      accelerationJerk=200.0,
      dangerJerk=100.0,
      speedJerk=5.0,
      dangerFactor=0.75,
      tFollow=1.45,
      disableThrottle=False,
      forcingStop=False,
      redLight=False,
      stopSignConfirmed=False,
      forcingStopLength=2.0,
      increasedStoppedDistance=0.0,
      roadCurvature=0.0,
    ),
  }


def make_toggles(*, model_first=False, delay=0.2):
  return SimpleNamespace(
    longitudinal_model_preference=model_first,
    longitudinalActuatorDelay=delay,
    vEgoStopping=0.05,
    stopAccel=-0.5,
  )


def use_fixed_mpc(planner, accel):
  def update(*_args, **_kwargs):
    v_ego = planner.mpc.x0[1]
    planner.mpc.a_solution = np.full(len(T_IDXS), accel)
    planner.mpc.v_solution = np.maximum(v_ego + accel * T_IDXS, 0.0)
    planner.mpc.j_solution = np.zeros(len(T_IDXS) - 1)
    planner.mpc.source = "cruise"
    planner.mpc.crash_cnt = 0

  planner.mpc.update = update


def test_set_speed_first_and_model_first_are_continuous_preferences():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  sm = make_sm(v_ego=20.0, v_cruise=20.0, model_accel=-0.4)

  set_speed = LongitudinalPlanner(CP, init_v=20.0)
  use_fixed_mpc(set_speed, 0.5)
  set_speed.update(sm, make_toggles(model_first=False))

  model_first = LongitudinalPlanner(CP, init_v=20.0)
  use_fixed_mpc(model_first, 0.5)
  model_first.update(sm, make_toggles(model_first=True))

  assert set_speed.model_authority == 0.0
  assert set_speed.output_a_target > 0.0
  assert model_first.model_authority >= 0.75
  assert model_first.output_a_target < 0.0


def test_model_stop_intent_brakes_without_binary_mode_switch():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=10.0)
  use_fixed_mpc(planner, 0.4)
  sm = make_sm(v_ego=10.0, model_accel=-1.0)
  set_model_stop(sm["modelV2"])

  planner.update(sm, make_toggles())

  assert planner.model_authority == 1.0
  assert planner.state == PlanState.stopping
  assert planner.output_a_target < 0.0
  assert planner.plan_source == "e2e"


def test_force_stop_is_a_hard_stop():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  use_fixed_mpc(planner, 0.5)
  sm = make_sm(v_ego=0.0, model_accel=0.5)
  set_model_departure(sm["modelV2"])
  sm["starpilotPlan"].forcingStop = True

  planner.update(sm, make_toggles())

  assert planner.state == PlanState.stopped
  assert planner.output_should_stop
  assert planner.output_a_target <= 0.0


def test_second_lead_slot_can_immediately_cap_acceleration():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=15.0)
  use_fixed_mpc(planner, 0.8)
  sm = make_sm(
    v_ego=15.0,
    model_accel=0.8,
    lead_one=make_lead(status=True, d_rel=150.0, v_lead=15.0, radar=True),
    lead_two=make_lead(status=True, d_rel=20.0, v_lead=0.0, radar=False),
  )

  planner.update(sm, make_toggles())

  assert planner.output_a_target < 0.0


def test_stopped_lead_holds_until_motion_and_gap_are_both_safe():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  use_fixed_mpc(planner, 0.5)
  lead = make_lead(status=True, d_rel=5.9, v_lead=1.0)
  sm = make_sm(v_ego=0.0, model_accel=0.5, lead_one=lead)
  set_model_departure(sm["modelV2"])
  planner.state = PlanState.stopped

  planner.update(sm, make_toggles())
  assert planner.state == PlanState.stopped
  assert planner.output_should_stop
  assert planner.output_a_target <= 0.0

  lead.dRel = 6.0
  planner.update(sm, make_toggles())
  assert planner.state == PlanState.departing
  assert planner.output_a_target >= planner.tune.launch_accel


def test_departing_lead_that_brakes_aborts_launch_immediately():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  use_fixed_mpc(planner, 0.5)
  lead = make_lead(status=True, d_rel=7.0, v_lead=1.0)
  sm = make_sm(v_ego=0.0, model_accel=0.5, lead_one=lead)
  set_model_departure(sm["modelV2"])
  planner.state = PlanState.stopped
  planner.update(sm, make_toggles())
  assert planner.state == PlanState.departing

  sm["carState"].vEgo = 0.4
  sm["carState"].vEgoCluster = 0.4
  sm["carState"].standstill = False
  lead.vLead = 0.1
  lead.aLeadK = -1.0
  planner.update(sm, make_toggles())

  assert planner.state == PlanState.stopping
  assert planner.output_a_target <= -0.5


def test_output_smoothing_is_asymmetric_and_urgent_braking_bypasses_it():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP)
  planner.output_a_target = 0.0

  assert planner._smooth_output(1.0, urgent=False) == pytest.approx(
    planner.tune.accel_slew_rate * planner.dt
  )
  assert planner._smooth_output(-2.0, urgent=True) == -2.0


def test_low_actuator_delay_uses_stable_evaluation_horizon(monkeypatch):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=20.0)
  use_fixed_mpc(planner, 0.0)
  captured = {}

  def capture_plan(_speeds, _accels, action_t, _v_ego_stopping):
    captured["action_t"] = action_t
    return 0.0, False

  monkeypatch.setattr(planner_module, "get_accel_from_plan", capture_plan)
  planner.update(make_sm(v_ego=20.0), make_toggles(delay=0.05))

  assert captured["action_t"] == pytest.approx(MIN_PLAN_HORIZON)


def test_mpc_tracks_both_lead_slots_independently_without_fusion():
  mpc = LongitudinalMpc()
  mpc.set_cur_state(20.0, 0.0)
  mpc.run = lambda: None
  lead_one = make_lead(status=True, d_rel=100.0, v_lead=20.0)
  lead_two = make_lead(status=True, d_rel=25.0, v_lead=5.0)
  radar_state = SimpleNamespace(leadOne=lead_one, leadTwo=lead_two)

  mpc.update(radar_state, 30.0)

  assert mpc.source == "lead1"
  assert mpc._lead_filter_state[0][0] == pytest.approx(20.0)
  assert mpc._lead_filter_state[1][0] == pytest.approx(5.0)

  lead_one.vLead = 10.0
  mpc.process_lead(lead_one, 0)
  assert mpc._lead_filter_state[1][0] == pytest.approx(5.0)


def test_fcw_considers_each_credible_closing_lead():
  safe = make_lead(status=True, d_rel=100.0, v_lead=20.0, model_prob=1.0)
  dangerous = make_lead(status=True, d_rel=20.0, v_lead=0.0, model_prob=1.0)

  assert not should_trigger_planner_fcw(safe, 20.0)
  assert should_trigger_planner_fcw(dangerous, 20.0)


def test_vehicle_tuning_is_declarative_and_honda_exception_is_conservative():
  civic = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  hrv = CarInterface.get_non_essential_params(CAR.HONDA_HRV_3G)

  assert get_longitudinal_planner_tune(hrv).lead_filter_tau > get_longitudinal_planner_tune(civic).lead_filter_tau
  assert get_longitudinal_planner_tune(hrv).accel_slew_rate < get_longitudinal_planner_tune(civic).accel_slew_rate


def test_gm_pedal_min_accel_keeps_physical_vehicle_floor():
  CP = SimpleNamespace(
    carName=None,
    brand="gm",
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=GM_CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  )

  assert get_vehicle_min_accel(CP, 32.4) == pytest.approx(-2.95)
