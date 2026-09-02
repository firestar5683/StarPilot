import time
import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest

from cereal import log
from openpilot.common.constants import CV
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from opendbc.car.gm.values import CAR as GM_CAR, GMFlags
from opendbc.car.ford.interface import CarInterface as FordCarInterface
from opendbc.car.ford.values import CAR as FORD_CAR
from opendbc.car.toyota.interface import CarInterface as ToyotaCarInterface
from opendbc.car.toyota.values import CAR as TOYOTA_CAR
import openpilot.selfdrive.controls.lib.longitudinal_planner as longitudinal_planner_module
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.drive_helpers import CONTROL_N
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner, get_coast_accel, get_vehicle_min_accel, should_publish_planner_fcw
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import (
  LongitudinalMpc,
  build_model_lead_trajectory,
  soften_far_radar_lead_accel,
  should_trigger_planner_fcw,
)
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import T_IDXS as T_IDXS_MPC
from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import (
  allow_radar_standstill_gap_settle,
  get_far_follow_output_slew_rates,
  get_follow_prebrake_min_headway,
  get_honda_accord_lead_departure_tune,
  get_honda_accord_stop_go_accel_cap,
  get_honda_crv_5g_stopped_lead_obstacle_bias,
  get_honda_crv_5g_low_speed_stopped_lead_cap,
  allow_honda_crv_5g_vision_gap_settle,
  is_honda_crv_5g_early_radar_follow_lead,
  get_honda_crv_5g_early_radar_follow_cap,
  get_standstill_gap_settle_max_extra_gap,
  get_standstill_stopped_lead_guard_distance_margin,
  get_standstill_stopped_lead_guard_max_lead_speed,
  get_stop_sign_low_speed_hold,
  is_ford_f150_lightning_stopped_radar_follow_lead,
  get_tracked_lead_catchup_bias_cap,
  get_tracked_lead_catchup_bias_gain,
  get_tracked_lead_catchup_cruise_error_full,
  get_tracked_lead_catchup_fade_margins,
  get_tracked_lead_catchup_headway_margins,
  get_tracked_lead_catchup_speed_range,
  get_toyota_prius_stopped_lead_obstacle_bias,
  get_toyota_rav4_tss2_lead_departure_tune,
  get_toyota_rav4_tss2_lead_creep_tune,
  get_toyota_rav4_tss2_early_lead_cap,
  get_toyota_sienna_post_departure_restop_cap,
  is_toyota_rav4_tss2_radar_follow_lead,
  is_gm_silverado_early_follow_lead,
  is_toyota_rav4_tss2_post_departure_tune,
)
from openpilot.selfdrive.modeld.constants import ModelConstants, Plan
from openpilot.selfdrive.modeld import modeld


class _SmoothParams:
  def __init__(self, value, developer=True, safe=False):
    self.value = value
    self.developer = developer
    self.safe = safe

  def get_bool(self, key):
    return self.developer if key == "DeveloperUI" else self.safe

  def get_float(self, key, **kwargs):
    return self.value


def test_model_smoothing_is_developer_gated_and_quantized():
  assert modeld._model_smooth_seconds(_SmoothParams(0.126), "LatSmoothSeconds", 0.1) == pytest.approx(0.125)
  assert modeld._model_smooth_seconds(_SmoothParams(0.126, developer=False), "LatSmoothSeconds", 0.1) == pytest.approx(0.1)
  assert modeld._model_smooth_seconds(_SmoothParams(0.126, safe=True), "LatSmoothSeconds", 0.1) == pytest.approx(0.1)


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


def test_mpc_duplicate_lead_filters_do_not_cross_contaminate_tracks():
  mpc = LongitudinalMpc()
  mpc.set_cur_state(20.0, 0.0)
  mpc.current_filter_time = 0.5
  lead_one = make_lead(status=True, d_rel=35.0, v_lead=12.0, model_prob=1.0)
  lead_two = make_lead(status=True, d_rel=35.0, v_lead=28.0, model_prob=1.0)

  mpc.process_lead(lead_one, lead_index=0, smooth_duplicate_vision=True)
  mpc.process_lead(lead_two, lead_index=1, smooth_duplicate_vision=True)

  assert mpc.duplicate_lead_v_filters[0].x == pytest.approx(12.0)
  assert mpc.duplicate_lead_v_filters[1].x == pytest.approx(28.0)

  lead_one.vLead = 14.0
  mpc.process_lead(lead_one, lead_index=0, smooth_duplicate_vision=True)
  assert 12.0 < mpc.duplicate_lead_v_filters[0].x < 14.0
  assert mpc.duplicate_lead_v_filters[1].x == pytest.approx(28.0)


def test_prius_stopped_lead_obstacle_bias_is_small_and_vehicle_specific():
  prius = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_PRIUS)
  other = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  stopped_lead = make_lead(status=True, d_rel=18.0, v_lead=0.2, model_prob=0.99)

  bias = get_toyota_prius_stopped_lead_obstacle_bias(prius, stopped_lead, v_ego=8.0)
  assert 0.0 < bias < 1.5
  assert get_toyota_prius_stopped_lead_obstacle_bias(other, stopped_lead, v_ego=8.0) == pytest.approx(0.0)
  assert get_toyota_prius_stopped_lead_obstacle_bias(
    prius, make_lead(status=True, d_rel=18.0, v_lead=4.0), v_ego=8.0,
  ) == pytest.approx(0.0)


def test_prius_stopped_lead_obstacle_bias_does_not_apply_at_standstill_or_to_departures():
  prius = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_PRIUS)
  stopped_lead = make_lead(status=True, d_rel=4.0, v_lead=0.0, model_prob=0.99)
  departing_lead = make_lead(status=True, d_rel=18.0, v_lead=2.0, model_prob=0.99)

  assert get_toyota_prius_stopped_lead_obstacle_bias(prius, stopped_lead, v_ego=0.0) == pytest.approx(0.0)
  assert get_toyota_prius_stopped_lead_obstacle_bias(prius, departing_lead, v_ego=8.0) == pytest.approx(0.0)


def test_honda_crv_5g_stopped_lead_tune_is_vehicle_specific():
  crv = CarInterface.get_non_essential_params(CAR.HONDA_CRV_5G)
  civic = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  stopped_lead = make_lead(status=True, d_rel=18.0, v_lead=0.2, model_prob=0.99)

  bias = get_honda_crv_5g_stopped_lead_obstacle_bias(crv, stopped_lead, v_ego=8.0)
  assert 0.0 < bias < 1.0
  assert get_honda_crv_5g_stopped_lead_obstacle_bias(civic, stopped_lead, v_ego=8.0) == pytest.approx(0.0)
  assert get_honda_crv_5g_low_speed_stopped_lead_cap(
    crv, make_lead(status=True, d_rel=10.0, v_lead=0.1, model_prob=0.99), v_ego=1.6, accel_min=-0.5,
  ) == pytest.approx(-0.272)
  assert get_honda_crv_5g_low_speed_stopped_lead_cap(
    civic, make_lead(status=True, d_rel=10.0, v_lead=0.1, model_prob=0.99), v_ego=1.6, accel_min=-0.5,
  ) is None
  assert allow_honda_crv_5g_vision_gap_settle(crv)
  assert not allow_honda_crv_5g_vision_gap_settle(civic)
  assert get_standstill_gap_settle_max_extra_gap(crv) > get_standstill_gap_settle_max_extra_gap(civic)


def test_honda_crv_5g_early_radar_follow_admits_high_closing_centered_lead():
  crv = CarInterface.get_non_essential_params(CAR.HONDA_CRV_5G)
  lead = make_lead(
    status=True, d_rel=77.0, v_lead=2.8, radar=True, model_prob=0.87, y_rel=0.56,
  )

  assert is_honda_crv_5g_early_radar_follow_lead(crv, lead, v_ego=16.2)
  assert get_honda_crv_5g_early_radar_follow_cap(
    crv, lead, v_ego=16.2, accel_min=-3.5,
  ) == pytest.approx(-0.39, abs=0.01)


@pytest.mark.parametrize("kwargs", [
  {"radar": False},
  {"model_prob": 0.79},
  {"y_rel": 1.01},
  {"v_lead": 8.1},
  {"d_rel": 90.0},
])
def test_honda_crv_5g_early_radar_follow_rejects_unreliable_or_nonurgent_lead(kwargs):
  crv = CarInterface.get_non_essential_params(CAR.HONDA_CRV_5G)
  lead_kwargs = {
    "d_rel": 77.0, "v_lead": 2.8, "radar": True, "model_prob": 0.87, "y_rel": 0.56,
  }
  lead_kwargs.update(kwargs)
  lead = make_lead(status=True, **lead_kwargs)

  assert not is_honda_crv_5g_early_radar_follow_lead(crv, lead, v_ego=16.2)


def test_honda_crv_5g_early_radar_follow_is_vehicle_specific():
  civic = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  lead = make_lead(status=True, d_rel=77.0, v_lead=2.8, radar=True, model_prob=0.87, y_rel=0.56)

  assert not is_honda_crv_5g_early_radar_follow_lead(civic, lead, v_ego=16.2)


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_honda_crv_5g_vision_lead_gap_settle_is_bounded(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CRV_5G)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm = make_sm(
    0.0,
    desired_accel=-0.12,
    min_accel=-0.5,
    experimental_mode=True,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=11.0, v_lead=0.0, a_lead=0.0, model_prob=0.99),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = True

  frames = int(round(longitudinal_planner_module.RADAR_STANDSTILL_GAP_SETTLE_CONFIRM_TIME / planner.dt)) + 2
  for _ in range(frames):
    planner.update(sm, make_toggles(model_version))

  assert planner.radar_standstill_gap_settle_active
  assert not planner.output_should_stop
  assert planner.output_a_target == pytest.approx(longitudinal_planner_module.RADAR_STANDSTILL_GAP_SETTLE_ACCEL)


def test_mpc_duplicate_vision_filter_smooths_distance_jumps_per_track():
  mpc = LongitudinalMpc()
  mpc.set_cur_state(27.0, 0.0)
  mpc.current_filter_time = 1.2
  lead_one = make_lead(status=True, d_rel=52.0, v_lead=25.0, model_prob=1.0)
  lead_two = make_lead(status=True, d_rel=70.0, v_lead=25.0, model_prob=1.0)

  first_one = mpc.process_lead(lead_one, lead_index=0, smooth_duplicate_vision=True)
  first_two = mpc.process_lead(lead_two, lead_index=1, smooth_duplicate_vision=True)
  assert first_one[0, 0] == pytest.approx(52.0)
  assert first_two[0, 0] == pytest.approx(70.0)

  lead_one.dRel = 60.0
  filtered_one = mpc.process_lead(lead_one, lead_index=0, smooth_duplicate_vision=True)

  assert 52.0 < filtered_one[0, 0] < 54.0
  assert mpc.duplicate_lead_x_filters[1].x == pytest.approx(70.0)


def test_mpc_duplicate_vision_distance_filter_bypasses_urgent_path():
  mpc = LongitudinalMpc()
  mpc.set_cur_state(27.0, 0.0)
  mpc.current_filter_time = 1.2
  lead = make_lead(status=True, d_rel=60.0, v_lead=25.0, model_prob=1.0)

  mpc.process_lead(lead, lead_index=0, smooth_duplicate_vision=True)
  lead.dRel = 35.0
  raw = mpc.process_lead(lead, lead_index=0, smooth_duplicate_vision=False)

  assert raw[0, 0] == pytest.approx(35.0)
  assert not mpc.duplicate_lead_x_filters[0].initialized


def test_mpc_duplicate_vision_distance_filter_never_delays_closer_lead():
  mpc = LongitudinalMpc()
  mpc.set_cur_state(27.0, 0.0)
  mpc.current_filter_time = 1.2
  lead = make_lead(status=True, d_rel=60.0, v_lead=25.0, model_prob=1.0)

  mpc.process_lead(lead, lead_index=0, smooth_duplicate_vision=True)
  lead.dRel = 42.0
  closer = mpc.process_lead(lead, lead_index=0, smooth_duplicate_vision=True)

  assert closer[0, 0] == pytest.approx(42.0)


def test_mpc_duplicate_vision_filter_damps_low_speed_velocity_noise():
  mpc = LongitudinalMpc()
  mpc.set_cur_state(18.0, 0.0)
  mpc.current_filter_time = 0.0
  lead = make_lead(status=True, d_rel=38.0, v_lead=17.0, model_prob=1.0)

  mpc.process_lead(lead, lead_index=0, smooth_duplicate_vision=True)
  lead.vLead = 20.0
  mpc.process_lead(lead, lead_index=0, smooth_duplicate_vision=True)

  assert 17.0 < mpc.duplicate_lead_v_filters[0].x < 20.0


def test_mpc_distinct_vision_lead_uses_unchanged_baseline_filter():
  mpc = LongitudinalMpc()
  baseline_mpc = LongitudinalMpc()
  mpc.set_cur_state(18.0, 0.0)
  baseline_mpc.set_cur_state(18.0, 0.0)
  mpc.current_filter_time = 0.0
  baseline_mpc.current_filter_time = 0.0
  lead = make_lead(status=True, d_rel=38.0, v_lead=17.0, model_prob=1.0)

  mpc.process_lead(lead, lead_index=0, smooth_duplicate_vision=False)
  baseline_mpc.process_lead(lead)
  lead.vLead = 20.0
  mpc.process_lead(lead, lead_index=0, smooth_duplicate_vision=False)
  baseline_mpc.process_lead(lead)

  assert mpc.lead_v_filter.x == pytest.approx(baseline_mpc.lead_v_filter.x)


def test_mpc_panic_bypass_immediately_removes_duplicate_vision_filter():
  mpc = LongitudinalMpc()
  mpc.set_cur_state(18.0, 0.0)
  mpc.current_filter_time = 0.0
  lead = make_lead(status=True, d_rel=25.0, v_lead=17.0, model_prob=1.0)

  mpc.process_lead(lead, lead_index=0, smooth_duplicate_vision=True)
  mpc.set_weights(v_ego=18.0, panic_bypass=True)
  lead.vLead = 10.0
  mpc.process_lead(lead, lead_index=0, smooth_duplicate_vision=False)

  assert mpc.filter_time_factor == 0.0
  assert mpc.lead_v_filter.x == pytest.approx(10.0)


def test_hrv_far_follow_output_slew_damps_only_continuous_safe_follow():
  v_ego = 24.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_HRV_3G)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  planner.lead_one = make_lead(status=True, d_rel=58.0, v_lead=20.0, model_prob=0.99)
  planner.lead_two = make_lead(status=False)

  initial = planner.get_vehicle_far_follow_slew_target(
    v_ego, prev_target=0.0, target=-0.6, output_should_stop=False, panic_bypass=False,
  )

  assert initial == pytest.approx(-0.6)

  smoothed = planner.get_vehicle_far_follow_slew_target(
    v_ego, prev_target=initial, target=0.4, output_should_stop=False, panic_bypass=False,
  )
  assert smoothed == pytest.approx(-0.5)


def test_crv_far_follow_output_slew_damps_nonurgent_lead_transition():
  v_ego = 24.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CRV_5G)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  planner.lead_one = make_lead(status=True, d_rel=58.0, v_lead=20.0, model_prob=0.99)
  planner.lead_two = make_lead(status=False)

  brake_rate, release_rate = get_far_follow_output_slew_rates(CP)
  assert brake_rate == pytest.approx(1.5)
  assert release_rate == pytest.approx(1.0)

  initial = planner.get_vehicle_far_follow_slew_target(
    v_ego, prev_target=0.0, target=-0.6, output_should_stop=False, panic_bypass=False,
  )
  smoothed = planner.get_vehicle_far_follow_slew_target(
    v_ego, prev_target=initial, target=0.4, output_should_stop=False, panic_bypass=False,
  )

  assert initial == pytest.approx(-0.6)
  assert smoothed == pytest.approx(initial + release_rate * planner.dt)


def test_accord_far_follow_output_slew_damps_nonurgent_radar_transition():
  v_ego = 24.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_ACCORD)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  planner.lead_one = make_lead(status=True, d_rel=58.0, v_lead=20.0, radar=True, model_prob=0.99)
  planner.lead_two = make_lead(status=False)

  brake_rate, release_rate = get_far_follow_output_slew_rates(CP)
  assert brake_rate == pytest.approx(2.0)
  assert release_rate == pytest.approx(1.5)

  initial = planner.get_vehicle_far_follow_slew_target(
    v_ego, prev_target=0.0, target=-0.6, output_should_stop=False, panic_bypass=False,
  )
  smoothed = planner.get_vehicle_far_follow_slew_target(
    v_ego, prev_target=initial, target=0.4, output_should_stop=False, panic_bypass=False,
  )

  assert initial == pytest.approx(-0.6)
  assert smoothed == pytest.approx(initial + release_rate * planner.dt)


@pytest.mark.parametrize("output_should_stop,panic_bypass", [(True, False), (False, True)])
def test_accord_far_follow_output_slew_bypasses_urgent_scenes(output_should_stop, panic_bypass):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_ACCORD)
  planner = LongitudinalPlanner(CP, init_v=24.0)
  planner.lead_one = make_lead(status=True, d_rel=58.0, v_lead=20.0, radar=True, model_prob=0.99)
  planner.lead_two = make_lead(status=False)
  planner.far_follow_output_slew_active = True

  target = planner.get_vehicle_far_follow_slew_target(
    24.0, prev_target=0.4, target=-1.0,
    output_should_stop=output_should_stop, panic_bypass=panic_bypass,
  )

  assert target == pytest.approx(-1.0)
  assert not planner.far_follow_output_slew_active


@pytest.mark.parametrize("d_rel,v_lead,output_should_stop,panic_bypass", [
  (20.0, 20.0, False, False),
  (35.0, 18.0, False, False),
  (58.0, 20.0, True, False),
  (58.0, 20.0, False, True),
])
def test_hrv_far_follow_output_slew_bypasses_urgent_scenes(d_rel, v_lead, output_should_stop, panic_bypass):
  v_ego = 24.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_HRV_3G)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  planner.lead_one = make_lead(status=True, d_rel=58.0, v_lead=20.0, model_prob=0.99)
  planner.lead_two = make_lead(status=False)
  planner.far_follow_output_slew_active = True
  planner.lead_one.dRel = d_rel
  planner.lead_one.vLead = v_lead

  target = planner.get_vehicle_far_follow_slew_target(
    v_ego, prev_target=0.4, target=-1.0,
    output_should_stop=output_should_stop, panic_bypass=panic_bypass,
  )

  assert target == pytest.approx(-1.0)
  assert not planner.far_follow_output_slew_active


def test_non_hrv_has_no_vehicle_far_follow_output_slew():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=24.0)
  planner.lead_one = make_lead(status=True, d_rel=58.0, v_lead=20.0, model_prob=0.99)
  planner.lead_two = make_lead(status=False)

  target = planner.get_vehicle_far_follow_slew_target(
    24.0, prev_target=0.4, target=-1.0, output_should_stop=False, panic_bypass=False,
  )

  assert target == pytest.approx(-1.0)


def test_rav4_far_follow_output_slew_damps_vision_lead_chatter():
  v_ego = 24.0
  CP = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2_2023)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  planner.lead_one = make_lead(status=True, d_rel=58.0, v_lead=20.0, model_prob=0.99)
  planner.lead_two = make_lead(status=False)

  brake_rate, release_rate = get_far_follow_output_slew_rates(CP)
  assert brake_rate > 0.0
  assert release_rate > 0.0

  initial = planner.get_vehicle_far_follow_slew_target(
    v_ego, prev_target=0.0, target=-0.6, output_should_stop=False, panic_bypass=False,
  )
  smoothed = planner.get_vehicle_far_follow_slew_target(
    v_ego, prev_target=initial, target=0.4, output_should_stop=False, panic_bypass=False,
  )

  assert initial == pytest.approx(-0.6)
  assert smoothed == pytest.approx(initial + release_rate * planner.dt)


def test_depart_release_hold_rejects_nearby_stopped_lead_conflict():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP)
  planner.lead_one = make_lead(status=True, d_rel=4.0, v_lead=0.8, a_lead=0.2, model_prob=1.0)
  planner.lead_two = make_lead(status=True, d_rel=5.5, v_lead=0.0, model_prob=1.0)

  assert planner.get_safe_depart_release_hold_lead(0.0) is None


def test_depart_release_hold_survives_stale_stop_then_cancels_for_braking_lead():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP)
  lead_one = make_lead(status=True, d_rel=4.0, v_lead=0.8, a_lead=0.2, model_prob=1.0)
  lead_two = make_lead(status=False)
  sm = make_sm(
    0.0,
    desired_accel=0.4,
    min_accel=-1.0,
    experimental_mode=True,
    tracking_lead=True,
    lead_one=lead_one,
    lead_two=lead_two,
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = True
  sm["modelV2"].position.x = [0.0] * len(ModelConstants.T_IDXS)
  sm["modelV2"].velocity.x = [0.0] * len(ModelConstants.T_IDXS)
  sm["modelV2"].acceleration.x = [0.0] * len(ModelConstants.T_IDXS)
  planner.lead_depart_release_candidate_elapsed = longitudinal_planner_module.LEAD_DEPART_RELEASE_HOLD_CONFIRM_TIME
  planner.lead_depart_release_hold_remaining = 1.0

  planner.update(sm, make_toggles())

  assert not planner.output_should_stop
  assert planner.output_a_target >= longitudinal_planner_module.STANDSTILL_LEAD_CREEP_RELEASE_MIN_ACCEL

  lead_one.vLead = 0.1
  lead_one.aLeadK = -0.5
  planner.update(sm, make_toggles())
  assert planner.lead_depart_release_hold_remaining == 0.0
  assert planner.output_should_stop


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


def make_model_lead(*, prob: float = 0.99, x=None, v=None):
  model = log.ModelDataV2.new_message()
  model.init('leadsV3', 3)
  lead = model.leadsV3[0]
  lead.prob = float(prob)
  lead.x = list(x if x is not None else [0.0, 20.0, 38.0, 54.0, 68.0, 80.0])
  lead.v = list(v if v is not None else [18.0, 18.0, 17.0, 16.0, 15.0, 14.0])
  return model, lead


def test_model_lead_trajectory_is_default_for_stable_lead():
  lead = make_lead(status=True, d_rel=42.0, v_lead=18.0, model_prob=0.99)
  _, model_lead = make_model_lead()

  mpc = LongitudinalMpc()
  mpc.set_cur_state(20.0, 0.0)

  actual = mpc.process_lead(lead, model_lead=model_lead)
  expected = build_model_lead_trajectory(model_lead, lead, 20.0)
  np.testing.assert_allclose(actual, expected)


def test_model_lead_trajectory_uses_raw_current_anchor_and_future_deltas():
  lead = make_lead(status=True, d_rel=42.0, v_lead=18.0, model_prob=0.99)
  _, model_lead = make_model_lead()

  trajectory = build_model_lead_trajectory(model_lead, lead, 20.0)

  assert trajectory is not None
  assert trajectory[0, 0] == pytest.approx(42.0)
  assert trajectory[0, 1] == pytest.approx(18.0)
  assert np.all(np.diff(trajectory[:, 0]) >= -1e-9)
  assert trajectory[-1, 0] > trajectory[0, 0]
  assert trajectory[-1, 1] < trajectory[0, 1]


@pytest.mark.parametrize("prob", [0.0, 0.5])
def test_model_lead_trajectory_falls_back_for_low_confidence(prob):
  lead = make_lead(status=True, d_rel=42.0, v_lead=18.0, model_prob=prob)
  _, model_lead = make_model_lead(prob=prob)
  assert build_model_lead_trajectory(model_lead, lead, 20.0) is None


def test_model_lead_trajectory_falls_back_without_raw_lead_or_valid_shape():
  _, model_lead = make_model_lead()
  no_raw_lead = make_lead(status=False, d_rel=42.0, v_lead=18.0)
  assert build_model_lead_trajectory(model_lead, no_raw_lead, 20.0) is None

  raw_lead = make_lead(status=True, d_rel=42.0, v_lead=18.0)
  _, short_model_lead = make_model_lead(x=[0.0], v=[18.0])
  assert build_model_lead_trajectory(short_model_lead, raw_lead, 20.0) is None


@pytest.mark.parametrize("d_rel,v_lead,a_lead", [
  (42.0, 18.0, -0.6),
  (8.0, 0.0, 0.0),
])
def test_model_lead_trajectory_falls_back_for_urgent_raw_lead(d_rel, v_lead, a_lead):
  raw_lead = make_lead(status=True, d_rel=d_rel, v_lead=v_lead, a_lead=a_lead, model_prob=0.99)
  _, model_lead = make_model_lead()

  assert build_model_lead_trajectory(model_lead, raw_lead, 20.0) is None


def set_model_launch_trajectory(model, *, wait_time: float = 0.6, accel: float = 1.0):
  times = np.asarray(ModelConstants.T_IDXS, dtype=float)
  moving_time = np.maximum(times - wait_time, 0.0)
  model.position.x = (0.5 * accel * moving_time ** 2).tolist()
  model.velocity.x = (accel * moving_time).tolist()
  model.acceleration.x = np.where(times >= wait_time, accel, 0.0).tolist()


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
      approachStopLength=0.0,
    ),
  }


def make_toggles(model_version: str = "v11", radar_takeoffs: bool = False):
  return SimpleNamespace(
    taco_tune=False,
    classic_model=False,
    tinygrad_model=True,
    model_version=model_version,
    vEgoStopping=0.5,
    radar_takeoffs=radar_takeoffs,
    conditional_limit=0.0,
    conditional_limit_lead=0.0,
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


def test_gm_pedal_vehicle_min_accel_uses_brand_when_car_name_is_missing():
  CP = SimpleNamespace(
    carName=None,
    brand="gm",
    enableGasInterceptorDEPRECATED=True,
    flags=GMFlags.PEDAL_LONG.value,
    carFingerprint=GM_CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
  )

  assert get_vehicle_min_accel(CP, 32.4) == pytest.approx(-2.95)


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


def test_gm_silverado_admits_credible_far_vision_lead_for_acc_follow():
  CP = SimpleNamespace(brand="gm", carFingerprint=GM_CAR.CHEVROLET_SILVERADO)
  lead = make_lead(status=True, d_rel=80.0, v_lead=30.0, model_prob=0.90, y_rel=0.2)

  assert is_gm_silverado_early_follow_lead(CP, lead, 30.0)


@pytest.mark.parametrize("fingerprint", [GM_CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, CAR.HONDA_CIVIC])
def test_gm_silverado_early_follow_does_not_apply_to_other_vehicles(fingerprint):
  brand = "gm" if fingerprint == GM_CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL else "honda"
  CP = SimpleNamespace(brand=brand, carFingerprint=fingerprint)
  lead = make_lead(status=True, d_rel=80.0, v_lead=30.0, model_prob=0.99)

  assert not is_gm_silverado_early_follow_lead(CP, lead, 30.0)


@pytest.mark.parametrize("kwargs", [
  {"radar": True},
  {"model_prob": 0.80},
  {"y_rel": 1.3},
  {"d_rel": 131.0},
])
def test_gm_silverado_early_follow_requires_a_credible_centered_vision_lead(kwargs):
  CP = SimpleNamespace(brand="gm", carFingerprint=GM_CAR.CHEVROLET_SILVERADO)
  lead_kwargs = {"d_rel": 80.0, "v_lead": 30.0, "model_prob": 0.90}
  lead_kwargs.update(kwargs)
  lead = make_lead(status=True, **lead_kwargs)

  assert not is_gm_silverado_early_follow_lead(CP, lead, 30.0)


def test_prebrake_floor_is_vehicle_specific():
  silverado = SimpleNamespace(brand="gm", carFingerprint=GM_CAR.CHEVROLET_SILVERADO)
  lightning = SimpleNamespace(brand="ford", carFingerprint="FORD_F_150_LIGHTNING_MK1")
  honda = SimpleNamespace(brand="honda", carFingerprint=CAR.HONDA_CIVIC)

  assert get_follow_prebrake_min_headway(silverado, 1.0) == pytest.approx(1.25)
  assert get_follow_prebrake_min_headway(lightning, 0.75) == pytest.approx(0.75)
  assert get_follow_prebrake_min_headway(honda, 1.0) == pytest.approx(1.25)


def test_lightning_stopped_lead_guard_tune_is_vehicle_specific():
  lightning = FordCarInterface.get_non_essential_params(FORD_CAR.FORD_F_150_LIGHTNING_MK1)
  civic = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)

  assert get_standstill_stopped_lead_guard_distance_margin(lightning) == pytest.approx(5.0)
  assert get_standstill_stopped_lead_guard_distance_margin(civic) == pytest.approx(3.0)
  assert get_standstill_stopped_lead_guard_max_lead_speed(lightning, 0.45) == pytest.approx(0.60)
  assert get_standstill_stopped_lead_guard_max_lead_speed(civic, 0.45) == pytest.approx(0.45)
  assert get_standstill_gap_settle_max_extra_gap(lightning) == pytest.approx(3.0)
  assert get_tracked_lead_catchup_headway_margins(lightning) == pytest.approx((0.10, 0.25))
  assert get_tracked_lead_catchup_bias_gain(lightning) == pytest.approx(1.0)
  assert get_tracked_lead_catchup_headway_margins(civic) is None
  assert get_tracked_lead_catchup_bias_gain(civic) is None


def test_lightning_stopped_radar_lead_handoff_is_narrow_and_vehicle_specific():
  lightning = FordCarInterface.get_non_essential_params(FORD_CAR.FORD_F_150_LIGHTNING_MK1)
  civic = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  lead = make_lead(status=True, d_rel=17.2, v_lead=0.2, radar=True, model_prob=1.0, y_rel=0.1)

  assert is_ford_f150_lightning_stopped_radar_follow_lead(lightning, lead, v_ego=2.6)
  assert is_ford_f150_lightning_stopped_radar_follow_lead(lightning, lead, v_ego=0.0)
  assert not is_ford_f150_lightning_stopped_radar_follow_lead(lightning, make_lead(
    status=True, d_rel=18.1, v_lead=0.2, radar=True, model_prob=1.0, y_rel=0.1,
  ), v_ego=2.6)
  assert not is_ford_f150_lightning_stopped_radar_follow_lead(lightning, make_lead(
    status=True, d_rel=17.2, v_lead=2.1, radar=True, model_prob=1.0, y_rel=0.1,
  ), v_ego=2.6)
  assert not is_ford_f150_lightning_stopped_radar_follow_lead(civic, lead, v_ego=2.6)


def test_crv_tracked_lead_catchup_tune_is_vehicle_specific():
  crv = CarInterface.get_non_essential_params(CAR.HONDA_CRV_5G)
  civic = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)

  assert get_tracked_lead_catchup_headway_margins(crv) == pytest.approx((0.10, 0.35))
  assert get_tracked_lead_catchup_bias_gain(crv) == pytest.approx(1.25)
  assert get_tracked_lead_catchup_bias_cap(crv) == pytest.approx(65.0)
  assert get_tracked_lead_catchup_speed_range(crv) == pytest.approx((10.0, 18.0))
  assert get_tracked_lead_catchup_fade_margins(crv) == pytest.approx((0.75, 6.5))
  assert get_tracked_lead_catchup_cruise_error_full(crv) == pytest.approx(0.75)
  assert get_tracked_lead_catchup_bias_cap(civic) is None
  assert get_tracked_lead_catchup_speed_range(civic) is None


def test_lightning_far_follow_output_slew_damps_nonurgent_lead_braking():
  v_ego = 24.0
  CP = FordCarInterface.get_non_essential_params(FORD_CAR.FORD_F_150_LIGHTNING_MK1)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  planner.lead_one = make_lead(status=True, d_rel=58.0, v_lead=20.0, model_prob=0.99)
  planner.lead_two = make_lead(status=False)

  brake_rate, release_rate = get_far_follow_output_slew_rates(CP)
  assert brake_rate == pytest.approx(2.5)
  assert release_rate == pytest.approx(1.75)

  initial = planner.get_vehicle_far_follow_slew_target(
    v_ego, prev_target=0.0, target=-0.6, output_should_stop=False, panic_bypass=False,
  )
  smoothed = planner.get_vehicle_far_follow_slew_target(
    v_ego, prev_target=initial, target=-2.0, output_should_stop=False, panic_bypass=False,
  )

  assert initial == pytest.approx(-0.6)
  assert smoothed == pytest.approx(initial - brake_rate * planner.dt)


def test_silverado_vision_follow_hold_survives_nonurgent_far_lead_crossover():
  v_ego = 32.0
  t_follow = 1.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=70.0, v_lead=31.2, a_lead=-0.02, radar=False, model_prob=1.0, y_rel=0.1)
  lead_two = make_lead(status=False)

  assert planner.mpc.get_vision_follow_cruise_hold(
    "lead0", lead_one, lead_two, 101.0, 200.0, 100.0, v_ego, t_follow, True,
  ) is None
  assert planner.mpc.get_vision_follow_cruise_hold(
    "lead0", lead_one, lead_two, 101.0, 200.0, 100.0, v_ego, t_follow, True,
    early_follow=True,
  ) == "lead0"


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_acc_mode_uses_far_near_stopped_radar_lead_before_tracking(model_version):
  v_ego = 24.6

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=0.0,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=116.0, v_lead=0.0, a_lead=-0.2, radar=True, model_prob=0.85),
  )
  sm["starpilotPlan"].vCruise = v_ego + 6.0

  planner.update(sm, make_toggles(model_version))

  assert planner.raw_close_lead_needs_control(sm["radarState"].leadOne, v_ego)
  assert planner.output_a_target < -0.1


def test_cruise_accel_cap_does_not_manufacture_braking_after_set_speed_drop_with_lead():
  v_ego = 20.115
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(
    status=True,
    d_rel=68.95,
    v_lead=18.74,
    a_lead=-0.32,
    radar=True,
    model_prob=0.991,
    y_rel=-0.15,
  )
  lead_two = make_lead(
    status=True,
    d_rel=68.95,
    v_lead=18.74,
    a_lead=-0.32,
    radar=True,
    model_prob=0.993,
    y_rel=-0.15,
  )
  sm = make_sm(
    v_ego,
    desired_accel=-0.05,
    min_accel=-1.0,
    experimental_mode=True,
    tracking_lead=True,
    lead_one=lead_one,
    lead_two=lead_two,
  )
  sm["starpilotPlan"].vCruise = 15.646
  sm["starpilotPlan"].tFollow = 1.0

  planner.update(sm, make_toggles())

  assert planner.output_a_target > -1.0
  assert planner.output_a_target <= 0.0


def test_cruise_accel_cap_preserves_close_lead_braking_after_set_speed_drop():
  v_ego = 20.115
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=-0.05,
    min_accel=-1.0,
    experimental_mode=True,
    tracking_lead=True,
    lead_one=make_lead(
      status=True,
      d_rel=20.0,
      v_lead=0.0,
      a_lead=-1.0,
      radar=True,
      model_prob=0.99,
    ),
  )
  sm["starpilotPlan"].vCruise = 15.646
  sm["starpilotPlan"].tFollow = 1.0

  planner.update(sm, make_toggles())

  assert planner.output_a_target <= -3.0


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


def test_vision_untracked_slow_lead_cap_starts_earlier_for_high_confidence_rav4_approach():
  v_ego = 21.4

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  route_like_lead = make_lead(status=True, d_rel=68.3, v_lead=18.3, radar=False, model_prob=0.95)

  route_cap = planner.get_vision_untracked_slow_lead_cap(route_like_lead, v_ego, -1.0)

  assert route_cap is not None
  assert -0.6 < route_cap < -0.2


def test_vision_untracked_slow_lead_cap_catches_near_rav4_lead_before_tracking():
  v_ego = 21.3

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  route_like_lead = make_lead(status=True, d_rel=41.1, v_lead=19.2, radar=False, model_prob=0.90)

  route_cap = planner.get_vision_untracked_slow_lead_cap(route_like_lead, v_ego, -1.0)

  assert route_cap is not None
  assert -0.35 < route_cap <= -0.1


def test_vision_untracked_slow_lead_relaxed_entry_requires_centered_lead():
  v_ego = 21.4

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  off_path_lead = make_lead(status=True, d_rel=68.3, v_lead=18.3, radar=False, model_prob=0.99, y_rel=1.5)

  assert planner.get_vision_untracked_slow_lead_cap(off_path_lead, v_ego, -1.0) is None


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


def test_hrv_untracked_slow_lead_cap_prepares_more_for_high_speed_stop():
  v_ego = 21.8
  lead = make_lead(status=True, d_rel=86.5, v_lead=8.3, a_lead=0.0, radar=False, model_prob=0.93, y_rel=-0.14)

  civic_planner = LongitudinalPlanner(CarInterface.get_non_essential_params(CAR.HONDA_CIVIC), init_v=v_ego)
  hrv_planner = LongitudinalPlanner(CarInterface.get_non_essential_params(CAR.HONDA_HRV_3G), init_v=v_ego)
  civic_cap = civic_planner.get_vision_untracked_slow_lead_cap(lead, v_ego, -3.5)
  hrv_cap = hrv_planner.get_vision_untracked_slow_lead_cap(lead, v_ego, -3.5)

  assert civic_cap is not None
  assert hrv_cap is not None
  assert hrv_cap < civic_cap - 0.15
  assert -1.2 < hrv_cap < -0.8


def test_vision_untracked_slow_lead_cap_keeps_low_confidence_floor_for_less_threatening_lead():
  v_ego = 20.35

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  less_threatening_lead = make_lead(status=True, d_rel=115.4, v_lead=9.5, a_lead=0.0, radar=False, model_prob=0.75)

  assert planner.get_vision_untracked_slow_lead_cap(less_threatening_lead, v_ego, -1.0) is None


def test_vision_untracked_approach_lift_eases_throttle_without_braking():
  v_ego = 30.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=110.0, v_lead=27.0, radar=False, model_prob=0.98)

  aggressive_cap = planner.get_vision_untracked_approach_lift_cap(lead, v_ego, 1.2)
  standard_cap = planner.get_vision_untracked_approach_lift_cap(lead, v_ego, 1.4)

  assert aggressive_cap is not None
  assert standard_cap is not None
  assert 0.0 <= standard_cap <= aggressive_cap < 0.22


@pytest.mark.parametrize("lead", [
  make_lead(status=True, d_rel=110.0, v_lead=27.0, radar=True, model_prob=0.98),
  make_lead(status=True, d_rel=110.0, v_lead=27.0, radar=False, model_prob=0.90),
  make_lead(status=True, d_rel=110.0, v_lead=27.0, radar=False, model_prob=0.98, y_rel=1.5),
  make_lead(status=True, d_rel=110.0, v_lead=30.0, radar=False, model_prob=0.98),
])
def test_vision_untracked_approach_lift_ignores_unqualified_leads(lead):
  v_ego = 30.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)

  assert planner.get_vision_untracked_approach_lift_cap(lead, v_ego, 1.4) is None


def test_vision_untracked_approach_lift_is_rate_limited_and_held():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=25.0, init_a=0.5)
  now = 0.0

  cap = None
  for _ in range(6):
    now += planner.dt
    cap = planner.update_vision_untracked_approach_lift_cap(0.0, 0.5, 0.5, now, True)

  assert cap is not None
  assert 0.45 < cap < 0.5

  held_cap = planner.update_vision_untracked_approach_lift_cap(None, 0.5, 0.5, now + planner.dt, True)
  assert held_cap is not None
  assert held_cap < cap


def test_vision_untracked_approach_lift_releases_after_hold_or_tracking():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=25.0, init_a=0.5)
  now = 0.0

  for _ in range(6):
    now += planner.dt
    planner.update_vision_untracked_approach_lift_cap(0.0, 0.5, 0.5, now, True)

  previous_cap = planner.untracked_vision_approach_lift_cap
  now += planner.dt
  releasing_cap = planner.update_vision_untracked_approach_lift_cap(None, 0.5, 0.5, now, False)

  assert releasing_cap is not None
  assert releasing_cap > previous_cap


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
@pytest.mark.parametrize("v_ego,v_lead,d_rel", [
  (4.5, 3.7, 12.0),
  (6.0, 5.2, 12.0),
  (7.5, 6.7, 12.0),
])
def test_acc_mode_low_speed_vision_takeoff_never_relaxes_closing_lead(model_version, v_ego, v_lead, d_rel):
  """The takeoff change must not turn a closing vision lead into acceleration."""
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(
    v_ego,
    desired_accel=1.4,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(
      status=True, d_rel=d_rel, v_lead=v_lead, a_lead=0.0,
      radar=False, model_prob=0.99, y_rel=0.0,
    ),
  )
  sm["starpilotPlan"].vCruise = v_ego + 10.0

  for _ in range(3):
    planner.update(sm, make_toggles(model_version))

  assert planner.mode == "acc"
  assert planner.output_a_target <= 0.0
  assert not planner.output_should_stop


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


def test_model_launch_accel_skips_hesitant_start_of_trajectory():
  model_v = np.maximum(T_IDXS_MPC - 0.6, 0.0)
  model_a = np.where(T_IDXS_MPC >= 0.6, 1.0, 0.0)

  launch_accel = LongitudinalPlanner.get_model_launch_accel(model_v, model_a, action_t=0.2, v_ego=0.0)

  assert launch_accel is not None
  assert launch_accel >= 0.8


def test_green_light_model_launch_boosts_no_lead_experimental_takeoff():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm = make_sm(0.0, desired_accel=0.0, min_accel=-0.5, experimental_mode=True)
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  set_model_launch_trajectory(sm["modelV2"])

  planner.update(sm, make_toggles())

  assert not planner.output_should_stop
  assert planner.output_a_target >= 0.8


def test_green_light_model_launch_survives_cem_switch_back_to_chill():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm_red = make_sm(0.0, desired_accel=0.0, min_accel=-0.5, experimental_mode=True)
  sm_red["carState"].standstill = True
  sm_red["controlsState"].longControlState = LongCtrlState.stopping
  sm_red["modelV2"].action.shouldStop = True
  sm_red["starpilotPlan"].redLight = True
  planner.update(sm_red, make_toggles())

  sm_green = make_sm(0.0, desired_accel=0.0, min_accel=-0.5, experimental_mode=False)
  sm_green["carState"].standstill = True
  sm_green["controlsState"].longControlState = LongCtrlState.stopping
  set_model_launch_trajectory(sm_green["modelV2"])
  planner.update(sm_green, make_toggles())

  assert planner.model_launch_stop_seen
  assert not planner.output_should_stop
  assert planner.output_a_target >= 0.8


@pytest.mark.parametrize(("veto", "brake_pressed"), [("redLight", False), ("forcingStop", False), (None, True)])
def test_green_light_model_launch_respects_stop_and_driver_vetoes(veto, brake_pressed):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm = make_sm(0.0, desired_accel=0.0, min_accel=-0.5, experimental_mode=True)
  sm["carState"].standstill = True
  sm["carState"].brakePressed = brake_pressed
  sm["controlsState"].longControlState = LongCtrlState.stopping
  if veto is not None:
    setattr(sm["starpilotPlan"], veto, True)
  set_model_launch_trajectory(sm["modelV2"])

  planner.update(sm, make_toggles())

  assert planner.output_a_target < 0.3


def test_model_launch_does_not_override_stationary_lead_guard():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm = make_sm(
    0.0,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=True,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=4.0, v_lead=0.0, a_lead=0.0, radar=True, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  set_model_launch_trajectory(sm["modelV2"])

  planner.update(sm, make_toggles())

  assert planner.output_should_stop
  assert planner.output_a_target <= 0.0


def test_model_launch_boosts_only_after_lead_departure_is_confirmed():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm = make_sm(
    0.0,
    desired_accel=0.1,
    min_accel=-0.5,
    experimental_mode=True,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=7.0, v_lead=1.5, a_lead=0.8, radar=True, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  set_model_launch_trajectory(sm["modelV2"])

  planner.update(sm, make_toggles())

  assert not planner.output_should_stop
  assert planner.output_a_target >= 0.8


def test_model_launch_is_cancelled_when_departing_lead_stops_again():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm_depart = make_sm(
    0.0,
    desired_accel=0.1,
    min_accel=-0.5,
    experimental_mode=True,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=7.0, v_lead=1.5, a_lead=0.8, radar=True, model_prob=1.0),
  )
  sm_depart["carState"].standstill = True
  sm_depart["controlsState"].longControlState = LongCtrlState.stopping
  set_model_launch_trajectory(sm_depart["modelV2"])
  planner.update(sm_depart, make_toggles())

  sm_stop = make_sm(
    0.2,
    desired_accel=0.1,
    min_accel=-0.5,
    experimental_mode=True,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=3.8, v_lead=0.0, a_lead=-0.6, radar=True, model_prob=1.0),
  )
  sm_stop["controlsState"].longControlState = LongCtrlState.pid
  set_model_launch_trajectory(sm_stop["modelV2"])

  planner.update(sm_stop, make_toggles())

  assert planner.output_should_stop
  assert planner.output_a_target <= 0.0


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
def test_manual_resume_override_accepts_accelerator_pedal(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm = make_sm(0.0, desired_accel=0.0, min_accel=-0.5)
  sm["carState"].standstill = True
  sm["carState"].gasPressed = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = True
  sm["starpilotPlan"].forcingStop = True

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
def test_standstill_accelerating_lead_keeps_small_nudge_while_stop_holds(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=5.55, v_lead=0.02, a_lead=0.40, radar=False, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False

  planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop
  assert longitudinal_planner_module.STANDSTILL_LEAD_NUDGE_ACCEL <= planner.output_a_target < 0.1


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_near_standstill_accelerating_lead_keeps_nudge_during_creep_frame(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.03)

  sm = make_sm(
    0.03,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=5.60, v_lead=0.06, a_lead=0.40, radar=False, model_prob=1.0),
  )
  sm["carState"].standstill = False
  sm["controlsState"].longControlState = LongCtrlState.pid
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False

  planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop
  assert longitudinal_planner_module.STANDSTILL_LEAD_NUDGE_ACCEL <= planner.output_a_target < 0.1


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_tiny_opening_lead_without_accel_does_not_get_nudge_floor(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=5.55, v_lead=0.02, a_lead=0.0, radar=False, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False

  planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop
  assert planner.output_a_target <= 0.0


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_slow_creep_depart_releases_after_short_confirm(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=7.2, v_lead=0.33, a_lead=0.28, radar=True, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False

  frames = int(round(longitudinal_planner_module.STANDSTILL_LEAD_CREEP_RELEASE_CONFIRM_TIME / planner.dt))
  for _ in range(max(frames, 1)):
    planner.update(sm, make_toggles(model_version))

  assert not planner.output_should_stop
  assert planner.output_a_target >= longitudinal_planner_module.STANDSTILL_LEAD_CREEP_RELEASE_MIN_ACCEL


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_slow_creep_depart_releases_near_stop_gap_with_modest_accel(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=5.7, v_lead=1.0, a_lead=0.09, radar=True, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False

  frames = int(round(longitudinal_planner_module.STANDSTILL_LEAD_CREEP_RELEASE_CONFIRM_TIME / planner.dt))
  for _ in range(max(frames, 1)):
    planner.update(sm, make_toggles(model_version))

  assert not planner.output_should_stop
  assert planner.output_a_target >= longitudinal_planner_module.STANDSTILL_LEAD_CREEP_RELEASE_MIN_ACCEL


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_slow_creep_depart_does_not_release_on_gap_without_motion_signal(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=7.2, v_lead=0.20, a_lead=0.05, radar=True, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False

  frames = int(round(longitudinal_planner_module.STANDSTILL_LEAD_CREEP_RELEASE_CONFIRM_TIME / planner.dt)) + 2
  for _ in range(max(frames, 1)):
    planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_stationary_radar_lead_settles_excess_stop_gap_after_confirmation(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm = make_sm(
    0.0,
    desired_accel=-0.12,
    min_accel=-0.5,
    experimental_mode=True,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=6.4, v_lead=0.0, a_lead=0.0, radar=True, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = True

  frames = int(round(longitudinal_planner_module.RADAR_STANDSTILL_GAP_SETTLE_CONFIRM_TIME / planner.dt))
  for _ in range(max(frames - 1, 1)):
    planner.update(sm, make_toggles(model_version))
    assert planner.output_should_stop

  planner.update(sm, make_toggles(model_version))

  assert not planner.output_should_stop
  assert planner.output_a_target == pytest.approx(longitudinal_planner_module.RADAR_STANDSTILL_GAP_SETTLE_ACCEL)


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_stationary_radar_gap_settle_reholds_at_target_gap(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm = make_sm(
    0.0,
    desired_accel=-0.12,
    min_accel=-0.5,
    experimental_mode=True,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=6.4, v_lead=0.0, a_lead=0.0, radar=True, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = True

  frames = int(round(longitudinal_planner_module.RADAR_STANDSTILL_GAP_SETTLE_CONFIRM_TIME / planner.dt))
  for _ in range(frames):
    planner.update(sm, make_toggles(model_version))
  assert planner.radar_standstill_gap_settle_active

  sm["carState"].vEgo = 0.15
  sm["carState"].standstill = False
  sm["radarState"].leadOne.dRel = 5.6
  planner.update(sm, make_toggles(model_version))

  assert not planner.radar_standstill_gap_settle_active
  assert planner.output_should_stop
  assert planner.output_a_target <= 0.0


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_stationary_gap_settle_never_uses_vision_only_lead(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm = make_sm(
    0.0,
    desired_accel=-0.12,
    min_accel=-0.5,
    experimental_mode=True,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=6.4, v_lead=0.0, a_lead=0.0, radar=False, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = True

  frames = int(round(longitudinal_planner_module.RADAR_STANDSTILL_GAP_SETTLE_CONFIRM_TIME / planner.dt)) + 2
  for _ in range(frames):
    planner.update(sm, make_toggles(model_version))

  assert not planner.radar_standstill_gap_settle_active
  assert planner.output_should_stop


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_rav4_tss2_does_not_release_a_stopped_lead_for_gap_settle(model_version):
  CP = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  sm = make_sm(
    0.0,
    desired_accel=-0.12,
    min_accel=-0.5,
    experimental_mode=True,
    tracking_lead=False,
    lead_one=make_lead(status=True, d_rel=6.4, v_lead=0.0, a_lead=0.0, radar=True, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["modelV2"].action.shouldStop = True

  frames = int(round(longitudinal_planner_module.RADAR_STANDSTILL_GAP_SETTLE_CONFIRM_TIME / planner.dt)) + 2
  for _ in range(max(frames, 1)):
    planner.update(sm, make_toggles(model_version))

  assert not allow_radar_standstill_gap_settle(CP)
  assert not planner.radar_standstill_gap_settle_active
  assert planner.output_should_stop


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


def test_lightning_stopped_lead_guard_holds_ambiguous_creep_then_releases():
  CP = FordCarInterface.get_non_essential_params(FORD_CAR.FORD_F_150_LIGHTNING_MK1)
  planner = LongitudinalPlanner(CP, init_v=0.17)
  sm = make_sm(
    0.17,
    desired_accel=0.17,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=9.5, v_lead=0.46, a_lead=0.02, radar=True, model_prob=1.0),
  )
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False

  planner.update(sm, make_toggles("v15"))

  assert planner.output_should_stop
  assert planner.output_a_target <= 0.0

  sm["carState"].vEgo = 0.0
  sm["carState"].vEgoCluster = 0.0
  sm["carState"].standstill = True
  sm["radarState"].leadOne.dRel = 9.9
  sm["radarState"].leadOne.vLead = 0.71
  sm["radarState"].leadOne.vLeadK = 0.71
  sm["radarState"].leadOne.aLeadK = 0.22
  planner.update(sm, make_toggles("v15"))

  assert not planner.output_should_stop


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
def test_standstill_stopped_lead_guard_holds_marginal_creep_release(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)

  sm = make_sm(
    0.0,
    desired_accel=0.8,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=4.2, v_lead=0.38, a_lead=0.31, radar=True, model_prob=1.0),
  )
  sm["carState"].standstill = True
  sm["controlsState"].longControlState = LongCtrlState.stopping
  sm["starpilotPlan"].vCruise = 10.0
  sm["modelV2"].action.shouldStop = False

  planner.update(sm, make_toggles(model_version))

  assert planner.output_should_stop
  assert planner.output_a_target <= 0.0


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


def test_toyota_sienna_post_departure_restop_blocks_lead_that_stops_again():
  CP = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  now_t = time.monotonic()
  lead = make_lead(status=True, d_rel=5.0, v_lead=0.10, a_lead=0.0, model_prob=0.99)

  cap = get_toyota_sienna_post_departure_restop_cap(
    CP, lead, v_ego=1.2, accel_min=-1.0, stop_distance=4.0,
    now_t=now_t, departure_latch_until=now_t + 5.0,
  )

  assert cap is not None
  assert cap < -0.18


def test_toyota_sienna_post_departure_restop_allows_confirmed_departure():
  CP = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  now_t = time.monotonic()
  lead = make_lead(status=True, d_rel=6.5, v_lead=1.0, a_lead=0.45, model_prob=0.99)

  cap = get_toyota_sienna_post_departure_restop_cap(
    CP, lead, v_ego=0.6, accel_min=-1.0, stop_distance=4.0,
    now_t=now_t, departure_latch_until=now_t + 5.0,
  )

  assert cap is None


def test_toyota_sienna_post_departure_restop_reasserts_should_stop_in_planner():
  CP = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_SIENNA_4TH_GEN)
  planner = LongitudinalPlanner(CP, init_v=1.2)
  sm = make_sm(
    1.2,
    desired_accel=1.0,
    min_accel=-1.0,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=5.0, v_lead=0.10, a_lead=0.0, model_prob=0.99),
  )
  planner.post_departure_follow_settle_until = time.monotonic() + 5.0

  planner.update(sm, make_toggles())

  assert planner.output_should_stop
  assert planner.output_a_target < 0.0


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


def test_route_251682_rav4_confirmed_depart_adds_bounded_accel_assist():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  lead = make_lead(
    status=True,
    d_rel=7.7,
    v_lead=2.0,
    a_lead=1.79,
    radar=False,
    model_prob=1.0,
  )

  floor = planner.get_lead_depart_accel_floor(lead, v_ego=0.0, model_desired_accel=0.44)

  assert 0.52 <= floor <= 0.54
  assert floor <= longitudinal_planner_module.LEAD_DEPART_ACCEL_HOLD_MAX_ACCEL


def test_honda_accord_lead_departure_assist_is_stronger_but_vehicle_scoped():
  accord = CarInterface.get_non_essential_params(CAR.HONDA_ACCORD)
  civic = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(accord, init_v=0.0)
  lead = make_lead(
    status=True,
    d_rel=7.7,
    v_lead=2.0,
    a_lead=1.79,
    radar=False,
    model_prob=1.0,
  )

  accord_floor = planner.get_lead_depart_accel_floor(lead, v_ego=0.0, model_desired_accel=0.44)
  civic_floor = LongitudinalPlanner(civic, init_v=0.0).get_lead_depart_accel_floor(
    lead, v_ego=0.0, model_desired_accel=0.44,
  )

  assert get_honda_accord_lead_departure_tune(accord) is not None
  assert get_honda_accord_lead_departure_tune(civic) is None
  assert accord_floor > civic_floor
  assert accord_floor <= get_honda_accord_lead_departure_tune(accord)[0]


def test_honda_accord_stop_go_departure_cap_is_vehicle_and_scene_scoped():
  accord = CarInterface.get_non_essential_params(CAR.HONDA_ACCORD)
  civic = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  lead = make_lead(
    status=True,
    d_rel=7.7,
    v_lead=1.5,
    a_lead=0.6,
    radar=False,
    model_prob=1.0,
  )

  cap = get_honda_accord_stop_go_accel_cap(accord, lead, v_ego=0.0)
  assert cap is not None
  assert cap < 1.0
  assert get_honda_accord_stop_go_accel_cap(civic, lead, v_ego=0.0) is None
  assert get_honda_accord_stop_go_accel_cap(
    accord, make_lead(status=True, d_rel=7.7, v_lead=0.0, model_prob=1.0), v_ego=0.0,
  ) is None
  assert get_honda_accord_stop_go_accel_cap(
    accord, make_lead(status=True, d_rel=30.0, v_lead=1.5, model_prob=1.0), v_ego=0.0,
  ) is None

  planner = LongitudinalPlanner(accord, init_v=0.0)
  assert planner.get_honda_accord_stop_go_accel_target(
    lead, v_ego=0.0, previous_target=-0.2, target=1.5, blocked=False,
  ) == pytest.approx(0.0)
  assert planner.get_honda_accord_stop_go_accel_target(
    lead, v_ego=0.0, previous_target=0.0, target=1.5, blocked=True,
  ) == pytest.approx(1.5)
  assert planner.get_honda_accord_stop_go_accel_target(
    lead, v_ego=0.0, previous_target=0.9, target=-1.5, blocked=False,
  ) == pytest.approx(-1.5)


def test_rav4_tss2_lead_departure_assist_is_vehicle_scoped():
  rav4 = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2_2023)
  civic = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  lead = make_lead(
    status=True,
    d_rel=7.7,
    v_lead=2.0,
    a_lead=1.79,
    radar=False,
    model_prob=1.0,
  )

  rav4_floor = LongitudinalPlanner(rav4, init_v=0.0).get_lead_depart_accel_floor(
    lead, v_ego=0.0, model_desired_accel=0.44,
  )
  civic_floor = LongitudinalPlanner(civic, init_v=0.0).get_lead_depart_accel_floor(
    lead, v_ego=0.0, model_desired_accel=0.44,
  )

  assert get_toyota_rav4_tss2_lead_departure_tune(rav4) is not None
  assert get_toyota_rav4_tss2_lead_departure_tune(civic) is None
  assert rav4_floor > civic_floor
  assert rav4_floor == pytest.approx(0.64)


@pytest.mark.parametrize("model_version", ["v11", "v12", "v13", "v14", "v15"])
def test_standstill_depart_accel_hold_reuses_floor_through_softening_lead_delta(model_version):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  toggles = make_toggles(model_version)

  sm_release = make_sm(
    0.0,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=4.1, v_lead=1.05, a_lead=1.2, radar=False, model_prob=1.0),
  )
  sm_release["carState"].standstill = True
  sm_release["controlsState"].longControlState = LongCtrlState.stopping
  sm_release["starpilotPlan"].vCruise = 10.0
  sm_release["modelV2"].action.shouldStop = False

  for _ in range(6):
    planner.update(sm_release, toggles)
    assert planner.output_should_stop

  planner.update(sm_release, toggles)
  assert not planner.output_should_stop
  assert planner.output_a_target >= longitudinal_planner_module.LEAD_DEPART_ACCEL_HOLD_MIN_ACCEL

  sm_hold = make_sm(
    0.5,
    desired_accel=0.0,
    min_accel=-0.5,
    experimental_mode=False,
    tracking_lead=True,
    lead_one=make_lead(status=True, d_rel=5.8, v_lead=1.25, a_lead=0.08, radar=False, model_prob=1.0),
  )
  sm_hold["carState"].standstill = False
  sm_hold["controlsState"].longControlState = LongCtrlState.pid
  sm_hold["starpilotPlan"].vCruise = 10.0
  sm_hold["modelV2"].action.shouldStop = False

  planner.update(sm_hold, toggles)

  assert not planner.output_should_stop
  assert planner.output_a_target >= longitudinal_planner_module.LEAD_DEPART_ACCEL_HOLD_MIN_ACCEL


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

  assert action.desiredCurvature == pytest.approx(modeld.smooth_value(0.12, prev_action.desiredCurvature, modeld.LAT_SMOOTH_SECONDS))
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

  assert action.desiredCurvature == pytest.approx(modeld.smooth_value(0.48, prev_action.desiredCurvature, modeld.LAT_SMOOTH_SECONDS))
  assert action.desiredAcceleration < -0.2
  assert not action.shouldStop


def test_modeld_action_uses_current_action_head_scaling_for_v16(monkeypatch):
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
    is_v15=False,
    starpilot_toggles=toggles,
    is_v16=True,
  )

  assert action.desiredCurvature == pytest.approx(modeld.smooth_value(0.48, prev_action.desiredCurvature, modeld.LAT_SMOOTH_SECONDS))
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


def test_publish_has_lead_includes_second_mpc_lead():
  class FakePM:
    def __init__(self):
      self.sent = {}

    def send(self, name, msg):
      self.sent[name] = msg

  class FakeSM(dict):
    def all_checks(self, service_list=None):
      return True

    logMonoTime = {"modelV2": int(1e9)}

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=5.0)
  planner.output_a_target = 0.0
  planner.output_should_stop = False
  planner.v_desired_trajectory = np.zeros(CONTROL_N)
  planner.a_desired_trajectory = np.zeros(CONTROL_N)
  planner.j_desired_trajectory = np.zeros(CONTROL_N)
  planner.fcw = False
  planner.mpc.source = "lead1"
  planner.mpc.solve_time = 0.0

  sm = FakeSM(make_sm(5.0, desired_accel=0.0, min_accel=-1.0, experimental_mode=False))
  sm["radarState"].leadOne = make_lead(status=False)
  sm["radarState"].leadTwo = make_lead(status=True, d_rel=8.0, v_lead=4.0, radar=True)
  pm = FakePM()

  planner.publish(sm, pm)

  assert pm.sent["longitudinalPlan"].longitudinalPlan.hasLead


def test_rav4_tss2_variants_use_the_car_specific_post_departure_tune():
  rav4_2019_cp = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2)
  rav4_2023_cp = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2_2023)
  other_cp = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2_2022)

  assert is_toyota_rav4_tss2_post_departure_tune(rav4_2019_cp)
  assert is_toyota_rav4_tss2_post_departure_tune(rav4_2023_cp)
  assert not is_toyota_rav4_tss2_post_departure_tune(other_cp)


def test_rav4_tss2_lead_creep_tune_is_vehicle_specific():
  rav4 = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2_2023)
  other = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2_2022)

  assert get_toyota_rav4_tss2_lead_creep_tune(rav4) == pytest.approx((0.15, -0.05))
  assert get_toyota_rav4_tss2_lead_creep_tune(other) is None


def test_rav4_tss2_standstill_lead_creep_does_not_wait_for_lead_acceleration():
  rav4 = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2_2023)
  civic = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  rav4_planner = LongitudinalPlanner(rav4, init_v=0.0)
  civic_planner = LongitudinalPlanner(civic, init_v=0.0)
  lead = make_lead(status=True, d_rel=6.4, v_lead=0.2, a_lead=0.0, model_prob=1.0)
  gap = longitudinal_planner_module.STOP_DISTANCE - 0.5

  assert rav4_planner.is_slow_creep_lead_depart(lead, 0.0, gap)
  assert not civic_planner.is_slow_creep_lead_depart(lead, 0.0, gap)


def test_rav4_tss2_early_lead_cap_starts_a_mild_response():
  CP = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2_2023)
  lead = make_lead(status=True, d_rel=100.0, v_lead=13.0, a_lead=-1.1, model_prob=0.9)

  cap = get_toyota_rav4_tss2_early_lead_cap(CP, lead, 21.0, -3.5)

  assert cap is not None
  assert -0.5 <= cap < 0.0


def test_rav4_tss2_early_lead_cap_does_not_change_other_paths():
  rav4 = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2_2023)
  other = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2_2022)
  lead = make_lead(status=True, d_rel=100.0, v_lead=13.0, a_lead=-1.1, model_prob=0.9)
  radar_lead = make_lead(status=True, d_rel=100.0, v_lead=13.0, a_lead=-1.1, radar=True, model_prob=1.0)

  assert get_toyota_rav4_tss2_early_lead_cap(other, lead, 21.0, -3.5) is None
  assert get_toyota_rav4_tss2_early_lead_cap(rav4, radar_lead, 21.0, -3.5) is None


def test_rav4_tss2_radar_follow_admits_closing_lead_before_model_tracking():
  rav4 = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2)
  lead = make_lead(status=True, d_rel=74.0, v_lead=1.0, radar=True)

  assert is_toyota_rav4_tss2_radar_follow_lead(rav4, lead, 9.7)


def test_rav4_tss2_radar_follow_admission_is_vehicle_and_safety_scoped():
  rav4 = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2)
  other = ToyotaCarInterface.get_non_essential_params(TOYOTA_CAR.TOYOTA_RAV4_TSS2_2022)
  lead = make_lead(status=True, d_rel=74.0, v_lead=1.0, radar=True)
  far_lead = make_lead(status=True, d_rel=110.0, v_lead=1.0, radar=True)
  vision_lead = make_lead(status=True, d_rel=74.0, v_lead=1.0, radar=False, model_prob=1.0)

  assert not is_toyota_rav4_tss2_radar_follow_lead(other, lead, 9.7)
  assert not is_toyota_rav4_tss2_radar_follow_lead(rav4, far_lead, 9.7)
  assert not is_toyota_rav4_tss2_radar_follow_lead(rav4, vision_lead, 9.7)


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


def test_carnival_confirmed_stop_sign_stays_latched_at_low_speed():
  class FakePM:
    def __init__(self):
      self.sent = {}

    def send(self, name, msg):
      self.sent[name] = msg

  class FakeSM(dict):
    def all_checks(self, service_list=None):
      return True

    logMonoTime = {"modelV2": int(1e9)}

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  CP.carFingerprint = "KIA_CARNIVAL_2025"
  planner = LongitudinalPlanner(CP, init_v=0.4)
  planner.output_a_target = -0.2
  planner.output_should_stop = False
  planner.v_desired_trajectory = np.zeros(CONTROL_N)
  planner.a_desired_trajectory = np.zeros(CONTROL_N)
  planner.j_desired_trajectory = np.zeros(CONTROL_N)
  planner.fcw = False
  planner.mpc.source = "cruise"
  planner.mpc.solve_time = 0.0

  sm = FakeSM(make_sm(0.4, desired_accel=0.0, min_accel=-1.0, experimental_mode=False))
  sm["starpilotPlan"].stopSignConfirmed = True
  pm = FakePM()

  assert get_stop_sign_low_speed_hold(CP) == pytest.approx(0.75)
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
  for _ in range(4):
    planner.update(sm, toggles)
    assert planner.model_allow_throttle
    assert planner.allow_throttle
  planner.update(sm, toggles)
  assert not planner.model_allow_throttle
  assert not planner.allow_throttle

  sm["modelV2"] = make_model(v_ego, desired_accel=0.0, gas_press_prob=0.43)
  planner.update(sm, toggles)
  assert not planner.model_allow_throttle
  assert not planner.allow_throttle

  sm["modelV2"] = make_model(v_ego, desired_accel=0.0, gas_press_prob=0.46)
  for _ in range(4):
    planner.update(sm, toggles)
    assert not planner.model_allow_throttle
    assert not planner.allow_throttle
  planner.update(sm, toggles)
  assert planner.model_allow_throttle
  assert planner.allow_throttle


def test_allow_throttle_confirmation_filters_route_length_model_pulses():
  v_ego = 25.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(v_ego, desired_accel=0.0, min_accel=-1.0, experimental_mode=False, gas_press_prob=0.6)
  toggles = make_toggles()

  planner.update(sm, toggles)

  # Representative gasPressProb runs from route b85c25a4c6f99d83/0000000c:
  # repeated 0.05-0.20 second threshold crossings must not change the coast cap.
  for probability, frames in ((0.30, 2), (0.50, 1), (0.32, 3), (0.48, 4), (0.29, 4)):
    sm["modelV2"] = make_model(v_ego, desired_accel=0.0, gas_press_prob=probability)
    for _ in range(frames):
      planner.update(sm, toggles)
      assert planner.model_allow_throttle
      assert planner.allow_throttle

  # A sustained model request still applies the physical coast cap.
  sm["modelV2"] = make_model(v_ego, desired_accel=0.0, gas_press_prob=0.2)
  for _ in range(5):
    planner.update(sm, toggles)
  assert not planner.model_allow_throttle
  assert not planner.allow_throttle


def test_no_throttle_cap_stays_at_coast_limit_until_throttle_returns():
  v_ego = 8.5

  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  sm = make_sm(v_ego, desired_accel=0.0, min_accel=-3.0, experimental_mode=False, gas_press_prob=0.0)
  sm["carControl"].orientationNED = [0.0, 0.1, 0.0]
  toggles = make_toggles()

  for _ in range(5):
    planner.update(sm, toggles)

  accel_coast = max(get_vehicle_min_accel(CP, v_ego), get_coast_accel(sm["carControl"].orientationNED[1]))

  assert not planner.allow_throttle
  assert planner.output_a_target == pytest.approx(accel_coast, abs=1e-3)


def test_experimental_release_state_arms_only_on_falling_edge():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP)

  planner.update_experimental_release_accel_state(True, 10.0, v_ego=23.96)
  assert planner.experimental_release_accel_until == 0.0

  planner.update_experimental_release_accel_state(False, 10.1, v_ego=23.96)
  assert planner.experimental_release_accel_until == pytest.approx(
    10.1 + longitudinal_planner_module.EXPERIMENTAL_RELEASE_ACCEL_HOLD_TIME
  )

  planner.update_experimental_release_accel_state(True, 10.2)
  assert planner.experimental_release_accel_until == 0.0


def test_experimental_release_state_holds_longer_at_low_speed():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP)

  planner.update_experimental_release_accel_state(True, 10.0, v_ego=6.75)
  planner.update_experimental_release_accel_state(False, 10.1, v_ego=6.75)

  assert planner.experimental_release_accel_until == pytest.approx(
    10.1 + longitudinal_planner_module.EXPERIMENTAL_RELEASE_ACCEL_LOW_SPEED_HOLD_TIME
  )


def test_experimental_release_accel_transition_damps_low_speed_slow_lead_handoff():
  v_ego = 6.75
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=11.0, v_lead=6.8, a_lead=0.0, radar=False, model_prob=0.99)

  target = planner.get_experimental_release_accel_target(
    lead,
    v_ego,
    1.13,
    prev_output_a_target=-0.25,
    output_a_target=-0.03,
    release_active=True,
  )

  assert target == pytest.approx(-0.19)


def test_experimental_release_accel_transition_damps_moving_lead_handoff():
  v_ego = 23.96
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=55.15, v_lead=23.73, a_lead=0.40, radar=True, model_prob=0.997)

  target = planner.get_experimental_release_accel_target(
    lead,
    v_ego,
    1.13,
    prev_output_a_target=0.03,
    output_a_target=0.44,
    release_active=True,
  )

  assert target == pytest.approx(0.09)


def test_experimental_release_accel_transition_damps_open_road_cespeed_exit():
  v_ego = 23.96
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)

  target = planner.get_experimental_release_accel_target(
    None,
    v_ego,
    1.13,
    prev_output_a_target=0.03,
    output_a_target=0.44,
    release_active=True,
  )

  assert target == pytest.approx(0.09)


def test_experimental_speed_handoff_weight_ramps_into_cespeed():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP)
  toggles = make_toggles()
  limit = 35.0 * CV.MPH_TO_MS
  band = longitudinal_planner_module.EXPERIMENTAL_SPEED_HANDOFF_BAND
  toggles.conditional_limit = limit

  assert planner.get_experimental_speed_handoff_weight(limit - band - 1.0, True, False, toggles, False) == 0.0
  assert planner.get_experimental_speed_handoff_weight(limit, True, False, toggles, False) == pytest.approx(1.0)
  assert planner.get_experimental_speed_handoff_weight(limit - 0.5 * band, True, False, toggles, False) == pytest.approx(0.5)
  assert planner.get_experimental_speed_handoff_weight(limit, True, False, toggles, True) == 0.0
  assert planner.get_experimental_speed_handoff_weight(limit, False, False, toggles, False) == 0.0


def test_experimental_speed_handoff_uses_lead_limit_when_following():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP)
  toggles = make_toggles()
  toggles.conditional_limit = 55.0 * CV.MPH_TO_MS
  toggles.conditional_limit_lead = 20.0 * CV.MPH_TO_MS

  assert planner.get_experimental_speed_handoff_weight(20.0 * CV.MPH_TO_MS, True, True, toggles, False) == pytest.approx(1.0)
  assert planner.get_experimental_speed_handoff_weight(20.0 * CV.MPH_TO_MS, True, False, toggles, False) == 0.0


def test_experimental_speed_handoff_keeps_stronger_e2e_brake():
  kept = LongitudinalPlanner.apply_experimental_speed_handoff(-0.50, 0.20, -0.50, 1.0)
  blended = LongitudinalPlanner.apply_experimental_speed_handoff(0.02, 0.40, 0.02, 0.5)

  assert kept == pytest.approx(-0.50)
  assert blended == pytest.approx(0.21)


def test_experimental_speed_handoff_following_lead_matches_cem_window():
  # Distant radar-active lead is not CEM following_lead.
  assert LongitudinalPlanner.is_cem_following_lead(True, 40.0, 1.5, 20.0)
  assert not LongitudinalPlanner.is_cem_following_lead(True, 80.0, 1.5, 20.0)
  assert not LongitudinalPlanner.is_cem_following_lead(False, 10.0, 1.5, 20.0)


def test_experimental_release_accel_transition_does_not_mask_stopped_lead():
  v_ego = 23.96
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=35.0, v_lead=0.0, a_lead=-1.0, radar=True, model_prob=0.997)

  target = planner.get_experimental_release_accel_target(
    lead,
    v_ego,
    1.13,
    prev_output_a_target=-0.4,
    output_a_target=0.4,
    release_active=True,
  )

  assert target is None


def test_planner_arms_experimental_release_accel_only_on_mode_exit():
  v_ego = 23.96
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=55.15, v_lead=23.73, a_lead=0.40, radar=True, model_prob=0.997)
  sm = make_sm(
    v_ego,
    desired_accel=0.0,
    min_accel=-1.0,
    experimental_mode=True,
    tracking_lead=True,
    lead_one=lead,
  )

  release_states = []
  original = planner.get_experimental_release_accel_target

  def record_release_state(self, *args, **kwargs):
    release_states.append(bool(args[-1]))
    return original(*args, **kwargs)

  planner.get_experimental_release_accel_target = types.MethodType(record_release_state, planner)
  planner.update(sm, make_toggles())
  sm["selfdriveState"].experimentalMode = False
  planner.update(sm, make_toggles())

  assert release_states == [False, True]


def test_inside_gap_closing_lead_cap_blocks_route_accel_burst():
  v_ego = 17.1
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=26.3, v_lead=16.5, a_lead=0.0, radar=True, model_prob=1.0)

  cap = planner.get_inside_gap_closing_lead_accel_cap(lead, v_ego, -1.0, 1.25)

  assert cap is not None
  assert cap == pytest.approx(0.0)


def test_inside_gap_closing_lead_cap_strengthens_with_route_closure():
  v_ego = 19.8
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=23.3, v_lead=17.3, a_lead=0.0, radar=True, model_prob=1.0)

  cap = planner.get_inside_gap_closing_lead_accel_cap(lead, v_ego, -1.0, 1.25)

  assert cap is not None
  assert -0.7 <= cap <= -0.5


@pytest.mark.parametrize("lead", [
  make_lead(status=True, d_rel=36.0, v_lead=16.5, radar=True, model_prob=1.0),
  make_lead(status=True, d_rel=26.3, v_lead=17.8, radar=True, model_prob=1.0),
  make_lead(status=True, d_rel=26.3, v_lead=16.5, radar=False, model_prob=0.8),
  make_lead(status=True, d_rel=26.3, v_lead=16.5, radar=True, model_prob=1.0, y_rel=2.0),
])
def test_inside_gap_closing_lead_cap_ignores_normal_or_ambiguous_follow(lead):
  v_ego = 17.1
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)

  assert planner.get_inside_gap_closing_lead_accel_cap(lead, v_ego, -1.0, 1.25) is None


def test_inside_gap_closing_lead_cap_does_not_touch_standstill_departure():
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=0.0)
  lead = make_lead(status=True, d_rel=5.0, v_lead=1.0, a_lead=0.5, radar=True, model_prob=1.0)

  assert planner.get_inside_gap_closing_lead_accel_cap(lead, 0.0, -1.0, 1.25) is None


def test_rolling_departure_settle_latch_stays_active_through_headway_hysteresis():
  v_ego = 10.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  departing_lead = make_lead(
    status=True, d_rel=13.4, v_lead=10.3,
    a_lead=0.3, radar=True, model_prob=1.0, y_rel=0.0,
  )
  settling_lead = make_lead(
    status=True, d_rel=13.2, v_lead=10.2,
    a_lead=0.1, radar=True, model_prob=1.0, y_rel=0.0,
  )

  assert planner.post_departure_follow_settle_active(departing_lead, v_ego, 1.25)
  assert planner.post_departure_follow_settle_active(settling_lead, v_ego, 1.25)


def test_rolling_departure_settle_latch_supports_confident_vision_lead():
  v_ego = 10.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(
    status=True, d_rel=13.4, v_lead=10.3,
    a_lead=0.3, radar=False, model_prob=0.95, y_rel=0.0,
  )

  assert planner.post_departure_follow_settle_active(lead, v_ego, 1.25)


def test_rolling_departure_settle_latch_clears_for_stopped_lead():
  v_ego = 10.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  departing_lead = make_lead(
    status=True, d_rel=13.4, v_lead=10.3,
    a_lead=0.3, radar=True, model_prob=1.0, y_rel=0.0,
  )
  stopped_lead = make_lead(
    status=True, d_rel=12.0, v_lead=0.0,
    a_lead=0.0, radar=True, model_prob=1.0, y_rel=0.0,
  )

  assert planner.post_departure_follow_settle_active(departing_lead, v_ego, 1.25)
  assert not planner.post_departure_follow_settle_active(stopped_lead, v_ego, 1.25)
  assert planner.post_departure_follow_settle_until == 0.0


@pytest.mark.parametrize("v_ego,d_rel,v_lead,a_lead", [
  (10.0, 14.0, 10.5, -0.2),
  (10.0, 12.5, 11.0, 0.5),
  (20.0, 29.0, 20.5, 0.5),
])
def test_rolling_departure_settle_latch_does_not_arm_without_safe_departure(v_ego, d_rel, v_lead, a_lead):
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(
    status=True, d_rel=d_rel, v_lead=v_lead,
    a_lead=a_lead, radar=True, model_prob=1.0, y_rel=0.0,
  )

  assert not planner.post_departure_follow_settle_active(lead, v_ego, 1.25)
  assert planner.post_departure_follow_settle_until == 0.0


def test_near_duplicate_lead_source_hysteresis_prefers_previous_source():
  v_ego = 27.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=46.2, v_lead=25.5, a_lead=-0.05, radar=False, model_prob=0.99)
  lead_two = make_lead(status=True, d_rel=46.8, v_lead=25.55, a_lead=-0.03, radar=False, model_prob=0.99)

  lead_0_bias, lead_1_bias = planner.mpc.get_near_duplicate_lead_source_hysteresis("lead0", lead_one, lead_two, v_ego)

  assert lead_0_bias == 0.0
  assert lead_1_bias > 0.0


def test_near_duplicate_vision_source_hysteresis_applies_at_tesla_city_speed():
  v_ego = 11.5
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=22.0, v_lead=10.8, a_lead=-0.04, radar=False, model_prob=1.0)
  lead_two = make_lead(status=True, d_rel=22.1, v_lead=10.82, a_lead=-0.03, radar=False, model_prob=1.0)

  lead_0_bias, lead_1_bias = planner.mpc.get_near_duplicate_lead_source_hysteresis("lead0", lead_one, lead_two, v_ego)

  assert lead_0_bias == 0.0
  assert lead_1_bias > 0.0


def test_near_duplicate_vision_source_hysteresis_holds_through_low_speed_stop_approach():
  v_ego = 5.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=9.8, v_lead=3.0, a_lead=-0.02, radar=False, model_prob=1.0)
  lead_two = make_lead(status=True, d_rel=9.9, v_lead=3.02, a_lead=-0.01, radar=False, model_prob=1.0)

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


def test_stable_follow_cruise_hysteresis_applies_to_radarless_lead_below_highway_speed():
  v_ego = 10.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=18.0, v_lead=9.9, a_lead=-0.02, radar=False, model_prob=1.0)

  hysteresis = planner.mpc.get_stable_follow_cruise_hysteresis(lead, v_ego, 1.45)

  assert hysteresis > 0.0


def test_stable_follow_cruise_hysteresis_holds_pullaway_lead_longer_near_target_gap():
  v_ego = 15.0
  t_follow = 1.45
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_matched = make_lead(status=True, d_rel=22.0, v_lead=15.0, a_lead=0.02, radar=True, model_prob=1.0)
  lead_pullaway = make_lead(status=True, d_rel=22.0, v_lead=16.4, a_lead=0.02, radar=True, model_prob=1.0)

  matched_hysteresis = planner.mpc.get_stable_follow_cruise_hysteresis(lead_matched, v_ego, t_follow)
  pullaway_hysteresis = planner.mpc.get_stable_follow_cruise_hysteresis(lead_pullaway, v_ego, t_follow)

  assert pullaway_hysteresis > matched_hysteresis


def test_stable_follow_cruise_hysteresis_skips_fast_closing_radar_lead():
  v_ego = 27.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead = make_lead(status=True, d_rel=40.5, v_lead=21.5, a_lead=-0.02, radar=True, model_prob=1.0)

  hysteresis = planner.mpc.get_stable_follow_cruise_hysteresis(lead, v_ego, 1.45)

  assert hysteresis == 0.0


def test_vision_follow_cruise_hold_keeps_high_confidence_matched_lead_through_small_crossover():
  v_ego = 22.5
  t_follow = 1.20
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=32.0, v_lead=22.0, a_lead=-0.02, radar=False, model_prob=0.99)
  lead_two = make_lead(status=False)

  sticky = planner.mpc.get_vision_follow_cruise_hold(
    "lead0",
    lead_one,
    lead_two,
    101.0,
    200.0,
    100.0,
    v_ego,
    t_follow,
    True,
  )

  assert sticky == "lead0"


@pytest.mark.parametrize("tracking_lead, radar, model_prob, cruise_obstacle", [
  (False, False, 0.99, 100.0),
  (True, True, 1.0, 100.0),
  (True, False, 0.80, 100.0),
  (True, False, 0.99, 98.0),
])
def test_vision_follow_cruise_hold_skips_nonmatching_or_clear_cruise_cases(
  tracking_lead, radar, model_prob, cruise_obstacle,
):
  v_ego = 22.5
  t_follow = 1.20
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=32.0, v_lead=22.0, a_lead=-0.02, radar=radar, model_prob=model_prob)
  lead_two = make_lead(status=False)

  sticky = planner.mpc.get_vision_follow_cruise_hold(
    "lead0",
    lead_one,
    lead_two,
    101.0,
    200.0,
    cruise_obstacle,
    v_ego,
    t_follow,
    tracking_lead,
  )

  assert sticky is None


@pytest.mark.parametrize("prev_source, lead_accel", [
  ("cruise", -0.02),
  ("lead0", -0.60),
])
def test_vision_follow_cruise_hold_never_delays_restrictive_transition(prev_source, lead_accel):
  v_ego = 22.5
  t_follow = 1.20
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=32.0, v_lead=22.0, a_lead=lead_accel, radar=False, model_prob=0.99)
  lead_two = make_lead(status=False)

  sticky = planner.mpc.get_vision_follow_cruise_hold(
    prev_source,
    lead_one,
    lead_two,
    101.0,
    200.0,
    100.0,
    v_ego,
    t_follow,
    True,
  )

  assert sticky is None


def test_near_duplicate_lead_source_hysteresis_prefers_previous_source_for_identical_radar_track():
  v_ego = 27.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=34.6, v_lead=24.2, a_lead=-0.04, radar=True, model_prob=1.0)
  lead_two = make_lead(status=True, d_rel=34.7, v_lead=24.2, a_lead=-0.04, radar=True, model_prob=1.0)
  lead_one.vRel = -0.8
  lead_two.vRel = -0.78
  lead_one.radarTrackId = 123
  lead_two.radarTrackId = 123

  lead_0_bias, lead_1_bias = planner.mpc.get_near_duplicate_lead_source_hysteresis("lead0", lead_one, lead_two, v_ego)

  assert lead_0_bias == 0.0
  assert lead_1_bias > 0.0


def test_near_duplicate_leads_detect_identical_radar_track_below_45_mph():
  v_ego = 14.31
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=25.7, v_lead=14.61, a_lead=0.0, radar=True, model_prob=1.0)
  lead_two = make_lead(status=True, d_rel=25.7, v_lead=14.61, a_lead=0.0, radar=True, model_prob=1.0)
  lead_one.vRel = lead_one.vLead - v_ego
  lead_two.vRel = lead_two.vLead - v_ego
  lead_one.radarTrackId = 2493
  lead_two.radarTrackId = 2493

  assert planner.mpc.leads_are_near_duplicates(lead_one, lead_two, v_ego)


def test_identical_radar_duplicate_source_hold_keeps_previous_label():
  v_ego = 21.6
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=33.5, v_lead=20.7, a_lead=-0.03, radar=True, model_prob=1.0)
  lead_two = make_lead(status=True, d_rel=33.5, v_lead=20.7, a_lead=-0.03, radar=True, model_prob=1.0)
  lead_one.radarTrackId = 2493
  lead_two.radarTrackId = 2493

  sticky = planner.mpc.get_identical_radar_duplicate_source_hold("lead1", lead_one, lead_two, 33.52, 33.50)

  assert sticky == "lead1"


def test_identical_radar_duplicate_cruise_hold_keeps_previous_lead_through_route_like_crossover():
  v_ego = 22.57
  t_follow = 1.20
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=32.3, v_lead=23.74, a_lead=0.67, radar=True, model_prob=1.0)
  lead_two = make_lead(status=True, d_rel=32.3, v_lead=23.74, a_lead=0.67, radar=True, model_prob=1.0)
  lead_one.radarTrackId = 2493
  lead_two.radarTrackId = 2493

  sticky = planner.mpc.get_identical_radar_duplicate_cruise_hold(
    "lead0",
    lead_one,
    lead_two,
    144.92,
    144.91,
    135.10,
    v_ego,
    t_follow,
  )

  assert sticky == "lead0"


def test_identical_radar_duplicate_cruise_hold_skips_clear_pullaway():
  v_ego = 22.57
  t_follow = 1.20
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=48.0, v_lead=25.5, a_lead=0.45, radar=True, model_prob=1.0)
  lead_two = make_lead(status=True, d_rel=48.0, v_lead=25.5, a_lead=0.45, radar=True, model_prob=1.0)
  lead_one.radarTrackId = 2493
  lead_two.radarTrackId = 2493

  sticky = planner.mpc.get_identical_radar_duplicate_cruise_hold(
    "lead0",
    lead_one,
    lead_two,
    180.0,
    180.0,
    150.0,
    v_ego,
    t_follow,
  )

  assert sticky is None


def test_identical_radar_duplicate_cruise_bias_penalizes_near_target_follow():
  v_ego = 23.8
  t_follow = 1.15
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=35.8, v_lead=23.2, a_lead=0.02, radar=True, model_prob=1.0)
  lead_two = make_lead(status=True, d_rel=35.8, v_lead=23.2, a_lead=0.02, radar=True, model_prob=1.0)
  lead_one.radarTrackId = 2493
  lead_two.radarTrackId = 2493

  bias = planner.mpc.get_identical_radar_duplicate_cruise_bias(lead_one, lead_two, v_ego, t_follow)

  assert bias > 0.0


def test_identical_radar_duplicate_cruise_bias_skips_far_pullaway_follow():
  v_ego = 23.8
  t_follow = 1.15
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=52.0, v_lead=25.5, a_lead=0.08, radar=True, model_prob=1.0)
  lead_two = make_lead(status=True, d_rel=52.0, v_lead=25.5, a_lead=0.08, radar=True, model_prob=1.0)
  lead_one.radarTrackId = 2493
  lead_two.radarTrackId = 2493

  bias = planner.mpc.get_identical_radar_duplicate_cruise_bias(lead_one, lead_two, v_ego, t_follow)

  assert bias == 0.0


def test_near_duplicate_lead_source_hysteresis_skips_distinct_leads():
  v_ego = 27.0
  CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = LongitudinalPlanner(CP, init_v=v_ego)
  lead_one = make_lead(status=True, d_rel=41.0, v_lead=23.8, a_lead=0.0, radar=False, model_prob=0.99)
  lead_two = make_lead(status=True, d_rel=48.0, v_lead=25.4, a_lead=0.0, radar=False, model_prob=0.99)

  lead_0_bias, lead_1_bias = planner.mpc.get_near_duplicate_lead_source_hysteresis("lead0", lead_one, lead_two, v_ego)

  assert lead_0_bias == 0.0
  assert lead_1_bias == 0.0
