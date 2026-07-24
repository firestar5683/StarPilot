import datetime

import pytest

from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL
from openpilot.starpilot.controls.lib.curve_speed_controller import CSC_MAX_DECEL_RATE, CurveSpeedController
from openpilot.starpilot.controls.lib.starpilot_vcruise import (
  FORCE_STOP_TURN_VETO_STOP_SEEN_HOLD_TIME,
  StarPilotVCruise,
  get_active_slc_control_target,
  get_slc_lead_drop_relaxed_target,
)
from types import SimpleNamespace


class FakeParams:
  def __init__(self, values=None):
    self.values = dict(values or {})

  def get(self, *args, **kwargs):
    key = args[0] if args else None
    return self.values.get(key)

  def get_float(self, *args, **kwargs):
    return 0.0

  def put_nonblocking(self, *args, **kwargs):
    pass


def make_vcruise(*, red_light=False, raw_model_stopped=False, forcing_stop=False, nav_state=None, road_curvature=0.0):
  planner = SimpleNamespace(
    params=FakeParams(),
    params_memory=FakeParams({"NavInstructionState": nav_state or {}}),
    lead_one=SimpleNamespace(status=False, dRel=float("inf"), vLead=0.0),
    longitudinal_intent=SimpleNamespace(stop_detected=red_light),
    tracking_lead=False,
    driving_in_curve=False,
    model_length=60.0,
    raw_model_stopped=raw_model_stopped,
    road_curvature=road_curvature,
    road_curvature_detected=False,
  )
  vcruise = StarPilotVCruise(planner)
  vcruise.forcing_stop = forcing_stop
  vcruise.force_stop_timer = 1.0 if forcing_stop else 0.0
  vcruise.tracked_model_length = 0.0 if forcing_stop else planner.model_length
  return planner, vcruise


def make_sm(*, standstill=True, min_steer_speed=0.0):
  return {
    "carControl": SimpleNamespace(longActive=True),
    "carState": SimpleNamespace(
      standstill=standstill,
      gasPressed=False,
      vCruiseCluster=0.0,
      vEgoCluster=0.0,
      leftBlinker=False,
      rightBlinker=False,
      steeringAngleDeg=0.0,
    ),
    "carParams": SimpleNamespace(minSteerSpeed=min_steer_speed),
    "starpilotCarState": SimpleNamespace(accelPressed=False, dashboardStopSign=0, dashboardSpeedLimit=0),
  }


def update_vcruise(vcruise, sm, toggles, *, now, v_ego=0.0, controls_enabled=True):
  return vcruise.update(
    controls_enabled=controls_enabled,
    now=now,
    time_validated=True,
    v_cruise=20.0,
    v_ego=v_ego,
    sm=sm,
    starpilot_toggles=toggles,
  )


def make_toggles():
  return SimpleNamespace(
    force_stops=True,
    force_standstill=False,
    curve_speed_controller=False,
    nav_longitudinal_allowed=False,
    speed_limit_controller=False,
    show_speed_limits=False,
    force_stop_distance_offset=0,
  )


def test_active_slc_control_target_does_not_require_set_speed_limit():
  target = get_active_slc_control_target(
    speed_limit_controller=True,
    set_speed_limit=False,
    slc_target=45.0 * CV.MPH_TO_MS,
    slc_offset=3.0 * CV.MPH_TO_MS,
    overridden_speed=0.0,
    v_ego_diff=0.4,
  )

  assert target == pytest.approx((48.0 * CV.MPH_TO_MS) - 0.4)


def test_curve_speed_controller_holds_target_through_brief_detector_dropout():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  def set_curve_target(_v_ego):
    vcruise.csc.target_set = True
    vcruise.csc.target = 14.0

  vcruise.csc.update_target = set_curve_target
  planner.road_curvature_detected = True
  result = update_vcruise(vcruise, sm, toggles, now=10.0, v_ego=20.0)
  assert result == pytest.approx(14.0)
  assert vcruise.csc_controlling_speed

  planner.road_curvature_detected = False
  result = update_vcruise(vcruise, sm, toggles, now=10.25, v_ego=20.0)
  assert result == pytest.approx(14.0)
  assert vcruise.csc_controlling_speed

  result = update_vcruise(vcruise, sm, toggles, now=10.8, v_ego=20.0)
  assert result == pytest.approx(20.0)
  assert not vcruise.csc_controlling_speed


def test_curve_speed_controller_releases_immediately_when_disabled():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  def set_curve_target(_v_ego):
    vcruise.csc.target_set = True
    vcruise.csc.target = 14.0

  vcruise.csc.update_target = set_curve_target
  planner.road_curvature_detected = True
  update_vcruise(vcruise, sm, toggles, now=20.0, v_ego=20.0)
  assert vcruise.csc_controlling_speed

  planner.road_curvature_detected = False
  toggles.curve_speed_controller = False
  result = update_vcruise(vcruise, sm, toggles, now=20.1, v_ego=20.0)
  assert result == pytest.approx(20.0)
  assert not vcruise.csc_controlling_speed


def test_curve_speed_controller_ramps_toward_curve_speed_at_bounded_rate():
  planner = SimpleNamespace(
    params=FakeParams(),
    road_curvature=0.004,
    time_to_curve=2.0,
    starpilot_weather=SimpleNamespace(weather_id=0, reduce_lateral_acceleration=0.0),
  )
  controller = CurveSpeedController(SimpleNamespace(starpilot_planner=planner))
  controller.lateral_acceleration = 2.0
  controller.target_set = True
  controller.target = 30.0

  controller.update_target(30.0)

  assert controller.target == pytest.approx(30.0 - CSC_MAX_DECEL_RATE * DT_MDL)
  assert controller.target > (controller.lateral_acceleration / planner.road_curvature) ** 0.5


def test_curve_speed_controller_does_not_slow_for_curve_speed_above_ego():
  planner = SimpleNamespace(
    params=FakeParams(),
    road_curvature=0.001,
    time_to_curve=2.0,
    starpilot_weather=SimpleNamespace(weather_id=0, reduce_lateral_acceleration=0.0),
  )
  controller = CurveSpeedController(SimpleNamespace(starpilot_planner=planner))
  controller.lateral_acceleration = 2.0
  controller.target_set = True
  controller.target = 28.0

  controller.update_target(30.0)

  assert controller.target == pytest.approx(30.0)


def test_active_slc_control_target_applies_offset_and_cluster_diff():
  target = get_active_slc_control_target(
    speed_limit_controller=True,
    set_speed_limit=True,
    slc_target=45.0 * CV.MPH_TO_MS,
    slc_offset=3.0 * CV.MPH_TO_MS,
    overridden_speed=0.0,
    v_ego_diff=0.4,
  )

  assert target == pytest.approx((48.0 * CV.MPH_TO_MS) - 0.4)


def test_slc_lead_drop_relaxed_target_softens_map_stepdown_for_harmless_lead():
  raw_target = 55.0 * CV.MPH_TO_MS
  previous_target = 65.0 * CV.MPH_TO_MS
  v_ego = 65.0 * CV.MPH_TO_MS
  lead = SimpleNamespace(status=True, dRel=46.0, vLead=71.0 * CV.MPH_TO_MS, aLeadK=0.08)

  relaxed = get_slc_lead_drop_relaxed_target(
    raw_target,
    previous_target,
    v_ego,
    tracking_lead=True,
    lead=lead,
    override_active=False,
    source="Map Data",
  )

  assert raw_target < relaxed < previous_target


def test_slc_lead_drop_relaxed_target_bails_out_for_override():
  raw_target = 55.0 * CV.MPH_TO_MS
  previous_target = 65.0 * CV.MPH_TO_MS
  v_ego = 65.0 * CV.MPH_TO_MS
  lead = SimpleNamespace(status=True, dRel=46.0, vLead=71.0 * CV.MPH_TO_MS, aLeadK=0.08)

  relaxed = get_slc_lead_drop_relaxed_target(
    raw_target,
    previous_target,
    v_ego,
    tracking_lead=True,
    lead=lead,
    override_active=True,
    source="Map Data",
  )

  assert relaxed == pytest.approx(raw_target)


def test_slc_lead_drop_relaxed_target_bails_out_for_threatening_lead():
  raw_target = 55.0 * CV.MPH_TO_MS
  previous_target = 65.0 * CV.MPH_TO_MS
  v_ego = 65.0 * CV.MPH_TO_MS
  lead = SimpleNamespace(status=True, dRel=20.0, vLead=52.0 * CV.MPH_TO_MS, aLeadK=-0.5)

  relaxed = get_slc_lead_drop_relaxed_target(
    raw_target,
    previous_target,
    v_ego,
    tracking_lead=True,
    lead=lead,
    override_active=False,
    source="Map Data",
  )

  assert relaxed == pytest.approx(raw_target)


def test_slc_lead_drop_relaxed_target_softens_for_far_slower_lead_if_new_limit_is_still_below_lead_speed():
  raw_target = 45.0 * CV.MPH_TO_MS
  previous_target = 56.0 * CV.MPH_TO_MS
  v_ego = 56.0 * CV.MPH_TO_MS
  lead = SimpleNamespace(status=True, dRel=113.0, vLead=50.0 * CV.MPH_TO_MS, aLeadK=-0.15)

  relaxed = get_slc_lead_drop_relaxed_target(
    raw_target,
    previous_target,
    v_ego,
    tracking_lead=True,
    lead=lead,
    override_active=False,
    source="Map Data",
  )

  assert raw_target < relaxed < previous_target


def test_slc_lead_drop_relaxed_target_still_bails_if_lead_is_slower_than_new_limit():
  raw_target = 45.0 * CV.MPH_TO_MS
  previous_target = 56.0 * CV.MPH_TO_MS
  v_ego = 56.0 * CV.MPH_TO_MS
  lead = SimpleNamespace(status=True, dRel=113.0, vLead=39.0 * CV.MPH_TO_MS, aLeadK=-0.05)

  relaxed = get_slc_lead_drop_relaxed_target(
    raw_target,
    previous_target,
    v_ego,
    tracking_lead=True,
    lead=lead,
    override_active=False,
    source="Map Data",
  )

  assert relaxed == pytest.approx(raw_target)


def test_slc_lead_drop_relaxed_target_bails_out_without_tracking_lead():
  raw_target = 55.0 * CV.MPH_TO_MS
  previous_target = 65.0 * CV.MPH_TO_MS
  v_ego = 65.0 * CV.MPH_TO_MS
  lead = SimpleNamespace(status=True, dRel=46.0, vLead=71.0 * CV.MPH_TO_MS, aLeadK=0.08)

  relaxed = get_slc_lead_drop_relaxed_target(
    raw_target,
    previous_target,
    v_ego,
    tracking_lead=False,
    lead=lead,
    override_active=False,
    source="Map Data",
  )

  assert relaxed == pytest.approx(raw_target)


def test_force_stop_clears_at_standstill_once_scene_opens():
  planner, vcruise = make_vcruise(red_light=False, raw_model_stopped=False, forcing_stop=True)

  result = vcruise.update(
    controls_enabled=True,
    now=0.0,
    time_validated=True,
    v_cruise=20.0,
    v_ego=0.0,
    sm=make_sm(standstill=True),
    starpilot_toggles=make_toggles(),
  )

  assert result == pytest.approx(20.0)
  assert vcruise.force_stop_timer == 0.0
  assert not vcruise.forcing_stop
  assert vcruise.tracked_model_length == pytest.approx(planner.model_length)


def test_force_stop_stays_committed_while_model_still_sees_stop():
  planner, vcruise = make_vcruise(red_light=False, raw_model_stopped=True, forcing_stop=True)

  result = vcruise.update(
    controls_enabled=True,
    now=0.0,
    time_validated=True,
    v_cruise=20.0,
    v_ego=0.0,
    sm=make_sm(standstill=True),
    starpilot_toggles=make_toggles(),
  )

  assert result == pytest.approx(0.0)
  assert vcruise.force_stop_timer >= 0.5
  assert vcruise.forcing_stop


def test_force_stop_stays_committed_while_moving_even_if_scene_opens():
  planner, vcruise = make_vcruise(red_light=False, raw_model_stopped=False, forcing_stop=True)

  result = vcruise.update(
    controls_enabled=True,
    now=0.0,
    time_validated=True,
    v_cruise=20.0,
    v_ego=1.5,
    sm=make_sm(standstill=False),
    starpilot_toggles=make_toggles(),
  )

  assert result == pytest.approx(0.0)
  assert vcruise.force_stop_timer >= 0.5
  assert vcruise.forcing_stop


def test_force_stop_turn_scene_veto_blocks_new_activation():
  _, vcruise = make_vcruise(red_light=False, raw_model_stopped=False, forcing_stop=False)
  sm = make_sm(standstill=False)
  sm["carState"].leftBlinker = True
  sm["carState"].steeringAngleDeg = 30.0

  result = update_vcruise(vcruise, sm, make_toggles(), now=0.0, v_ego=7.0)

  assert result == pytest.approx(20.0)
  assert vcruise.force_stop_timer == pytest.approx(0.0)
  assert not vcruise.forcing_stop


def test_force_stop_curve_veto_blocks_new_activation():
  _, vcruise = make_vcruise(red_light=False, raw_model_stopped=False, forcing_stop=False, road_curvature=0.005)
  sm = make_sm(standstill=False)
  toggles = make_toggles()

  for frame in range(12):
    result = update_vcruise(vcruise, sm, toggles, now=frame * 0.05, v_ego=7.0)

  assert result == pytest.approx(20.0)
  assert vcruise.force_stop_timer == pytest.approx(0.0)
  assert not vcruise.forcing_stop


def test_force_stop_turn_scene_veto_yields_to_stop_then_turn():
  _, vcruise = make_vcruise(red_light=True, raw_model_stopped=True, forcing_stop=False)
  sm = make_sm(standstill=False)
  sm["carState"].leftBlinker = True
  sm["carState"].steeringAngleDeg = 30.0
  toggles = make_toggles()

  for frame in range(12):
    result = update_vcruise(vcruise, sm, toggles, now=frame * 0.05, v_ego=7.0)

  assert 0.0 < result < 20.0
  assert vcruise.force_stop_timer >= 0.5
  assert vcruise.forcing_stop


def test_force_stop_curve_veto_yields_to_stop_then_turn():
  _, vcruise = make_vcruise(red_light=True, raw_model_stopped=True, forcing_stop=False, road_curvature=0.05)
  sm = make_sm(standstill=False)
  sm["carState"].rightBlinker = True
  sm["carState"].steeringAngleDeg = -40.0
  toggles = make_toggles()

  for frame in range(12):
    result = update_vcruise(vcruise, sm, toggles, now=frame * 0.05, v_ego=7.0)

  assert 0.0 < result < 20.0
  assert vcruise.force_stop_timer >= 0.5
  assert vcruise.forcing_stop


def test_stop_then_turn_override_releases_after_stop_seen_window_expires():
  _, vcruise = make_vcruise(red_light=False, raw_model_stopped=False, forcing_stop=False)
  planner = vcruise.starpilot_planner
  sm = make_sm(standstill=False)
  sm["carState"].leftBlinker = True
  sm["carState"].steeringAngleDeg = 30.0
  toggles = make_toggles()

  planner.longitudinal_intent.stop_detected = True
  update_vcruise(vcruise, sm, toggles, now=0.0, v_ego=7.0)
  planner.longitudinal_intent.stop_detected = False

  now = FORCE_STOP_TURN_VETO_STOP_SEEN_HOLD_TIME + 0.5
  for frame in range(12):
    result = update_vcruise(vcruise, sm, toggles, now=now + frame * 0.05, v_ego=7.0)

  assert result == pytest.approx(20.0)
  assert not vcruise.forcing_stop


def test_force_stop_still_activates_for_straight_red_light_approach():
  _, vcruise = make_vcruise(red_light=True, raw_model_stopped=False, forcing_stop=False, road_curvature=0.001)
  sm = make_sm(standstill=False)
  toggles = make_toggles()

  for frame in range(12):
    result = update_vcruise(vcruise, sm, toggles, now=frame * 0.05, v_ego=7.0)

  assert 0.0 < result < 20.0
  assert vcruise.force_stop_timer >= 0.5
  assert vcruise.forcing_stop


def test_force_stop_turn_scene_does_not_abandon_moving_commitment():
  _, vcruise = make_vcruise(red_light=False, raw_model_stopped=False, forcing_stop=True)
  sm = make_sm(standstill=False)
  sm["carState"].rightBlinker = True
  sm["carState"].steeringAngleDeg = -30.0

  result = update_vcruise(vcruise, sm, make_toggles(), now=0.0, v_ego=8.0)

  assert result == pytest.approx(0.0)
  assert vcruise.force_stop_timer >= 0.5
  assert vcruise.forcing_stop


def test_engage_while_already_stopped_in_red_light_scene_seeds_force_stop_hold():
  _, vcruise = make_vcruise(red_light=True, raw_model_stopped=False, forcing_stop=False)

  result = vcruise.update(
    controls_enabled=True,
    now=0.0,
    time_validated=True,
    v_cruise=20.0,
    v_ego=0.0,
    sm=make_sm(standstill=True),
    starpilot_toggles=make_toggles(),
  )

  assert result == pytest.approx(0.0)
  assert vcruise.standstill_force_stop_hold
  assert vcruise.force_stop_timer >= 0.5
  assert vcruise.forcing_stop
  assert vcruise.tracked_model_length == pytest.approx(0.0)


def test_engage_from_aol_while_stopped_at_red_light_seeds_force_stop_hold():
  _, vcruise = make_vcruise(red_light=True, raw_model_stopped=True, forcing_stop=False)
  sm = make_sm(standstill=True)
  toggles = make_toggles()

  assert update_vcruise(vcruise, sm, toggles, now=0.0, controls_enabled=False) == pytest.approx(20.0)
  assert not vcruise.standstill_force_stop_hold

  assert update_vcruise(vcruise, sm, toggles, now=0.05, controls_enabled=True) == pytest.approx(0.0)
  assert vcruise.standstill_force_stop_hold
  assert vcruise.standstill_force_stop_reason == "light"
  assert vcruise.forcing_stop


def test_standstill_seeded_force_stop_hold_requires_clear_window_before_release():
  planner, vcruise = make_vcruise(red_light=True, raw_model_stopped=False, forcing_stop=False)
  sm = make_sm(standstill=True)
  toggles = make_toggles()

  first = vcruise.update(
    controls_enabled=True,
    now=0.0,
    time_validated=True,
    v_cruise=20.0,
    v_ego=0.0,
    sm=sm,
    starpilot_toggles=toggles,
  )
  assert first == pytest.approx(0.0)
  assert vcruise.standstill_force_stop_hold

  planner.longitudinal_intent.stop_detected = False
  second = vcruise.update(
    controls_enabled=True,
    now=0.4,
    time_validated=True,
    v_cruise=20.0,
    v_ego=0.0,
    sm=sm,
    starpilot_toggles=toggles,
  )
  assert second == pytest.approx(0.0)
  assert vcruise.standstill_force_stop_hold
  assert vcruise.forcing_stop

  released = vcruise.update(
    controls_enabled=True,
    now=1.2,
    time_validated=True,
    v_cruise=20.0,
    v_ego=0.0,
    sm=sm,
    starpilot_toggles=toggles,
  )
  assert released == pytest.approx(20.0)
  assert not vcruise.standstill_force_stop_hold
  assert not vcruise.forcing_stop


def test_standstill_seeded_force_stop_hold_accepts_datetime_now_without_crashing():
  planner, vcruise = make_vcruise(red_light=True, raw_model_stopped=False, forcing_stop=False)
  sm = make_sm(standstill=True)
  toggles = make_toggles()
  base = datetime.datetime(2026, 6, 18, tzinfo=datetime.UTC)

  first = vcruise.update(
    controls_enabled=True,
    now=base,
    time_validated=True,
    v_cruise=20.0,
    v_ego=0.0,
    sm=sm,
    starpilot_toggles=toggles,
  )
  assert first == pytest.approx(0.0)
  assert vcruise.standstill_force_stop_hold

  planner.longitudinal_intent.stop_detected = False
  second = vcruise.update(
    controls_enabled=True,
    now=base + datetime.timedelta(seconds=0.4),
    time_validated=True,
    v_cruise=20.0,
    v_ego=0.0,
    sm=sm,
    starpilot_toggles=toggles,
  )
  assert second == pytest.approx(0.0)
  assert vcruise.standstill_force_stop_hold

  released = vcruise.update(
    controls_enabled=True,
    now=base + datetime.timedelta(seconds=1.2),
    time_validated=True,
    v_cruise=20.0,
    v_ego=0.0,
    sm=sm,
    starpilot_toggles=toggles,
  )
  assert released == pytest.approx(20.0)
  assert not vcruise.standstill_force_stop_hold
  assert not vcruise.forcing_stop


def test_standstill_light_hold_expires_and_does_not_rearm_from_stopped_model():
  planner, vcruise = make_vcruise(red_light=True, raw_model_stopped=True, forcing_stop=False)
  sm = make_sm(standstill=True)
  toggles = make_toggles()

  assert update_vcruise(vcruise, sm, toggles, now=0.0) == pytest.approx(0.0)
  assert vcruise.standstill_force_stop_reason == "light"

  assert update_vcruise(vcruise, sm, toggles, now=4.9) == pytest.approx(0.0)
  assert vcruise.forcing_stop

  assert update_vcruise(vcruise, sm, toggles, now=5.1) == pytest.approx(20.0)
  assert not vcruise.forcing_stop
  assert not vcruise.standstill_force_stop_hold

  # The red-light model remains stopped, but Force Stop must stay released so
  # Experimental Mode can own the red-to-green departure.
  assert update_vcruise(vcruise, sm, toggles, now=5.2) == pytest.approx(20.0)
  assert not vcruise.forcing_stop


def test_approach_light_force_stop_expires_without_rearming_at_standstill():
  _, vcruise = make_vcruise(red_light=True, raw_model_stopped=True, forcing_stop=True)
  toggles = make_toggles()

  update_vcruise(vcruise, make_sm(standstill=False), toggles, now=0.0, v_ego=1.0)
  sm = make_sm(standstill=True)
  for frame in range(60):
    result = update_vcruise(vcruise, sm, toggles, now=(frame + 1) * 0.05)

  assert result == pytest.approx(20.0)
  assert not vcruise.forcing_stop
  assert not vcruise.standstill_force_stop_hold

  assert update_vcruise(vcruise, sm, toggles, now=3.1) == pytest.approx(20.0)
  assert not vcruise.forcing_stop


def test_stop_sign_hold_persists_until_resume():
  _, vcruise = make_vcruise(red_light=True, raw_model_stopped=True, forcing_stop=False)
  sm = make_sm(standstill=True)
  sm["starpilotCarState"].dashboardStopSign = 1
  toggles = make_toggles()

  assert update_vcruise(vcruise, sm, toggles, now=0.0) == pytest.approx(0.0)
  assert vcruise.standstill_force_stop_reason == "sign"

  sm["starpilotCarState"].dashboardStopSign = 0
  assert update_vcruise(vcruise, sm, toggles, now=8.0) == pytest.approx(0.0)
  assert vcruise.forcing_stop

  sm["starpilotCarState"].accelPressed = True
  assert update_vcruise(vcruise, sm, toggles, now=8.1) == pytest.approx(20.0)
  assert not vcruise.forcing_stop
  assert not vcruise.stop_sign_confirmed


def test_nav_turn_speed_control_default_off():
  _, vcruise = make_vcruise(nav_state={
    "valid": True,
    "maneuverType": "turn",
    "maneuverModifier": "right",
    "maneuverDistance": 30.0,
    "nextManeuverType": "",
    "nextManeuverModifier": "",
    "nextManeuverDistance": 0.0,
  })

  result = vcruise.update(
    controls_enabled=True,
    now=0.0,
    time_validated=True,
    v_cruise=20.0,
    v_ego=20.0,
    sm=make_sm(standstill=False),
    starpilot_toggles=make_toggles(),
  )

  assert result == pytest.approx(20.0)
  assert vcruise.nav_turn_target == pytest.approx(0.0)


def test_nav_turn_speed_control_slows_for_imminent_turn():
  _, vcruise = make_vcruise(nav_state={
    "valid": True,
    "maneuverType": "turn",
    "maneuverModifier": "right",
    "maneuverDistance": 30.0,
    "nextManeuverType": "",
    "nextManeuverModifier": "",
    "nextManeuverDistance": 0.0,
  })

  toggles = make_toggles()
  toggles.nav_longitudinal_allowed = True
  result = vcruise.update(
    controls_enabled=True,
    now=0.0,
    time_validated=True,
    v_cruise=20.0,
    v_ego=20.0,
    sm=make_sm(standstill=False),
    starpilot_toggles=toggles,
  )

  assert result < 20.0
  assert result == pytest.approx(vcruise.nav_turn_target)
  assert result > 0.0


def test_nav_turn_speed_control_ignores_distant_turn():
  _, vcruise = make_vcruise(nav_state={
    "valid": True,
    "maneuverType": "turn",
    "maneuverModifier": "right",
    "maneuverDistance": 400.0,
    "nextManeuverType": "",
    "nextManeuverModifier": "",
    "nextManeuverDistance": 0.0,
  })

  toggles = make_toggles()
  toggles.nav_longitudinal_allowed = True
  result = vcruise.update(
    controls_enabled=True,
    now=0.0,
    time_validated=True,
    v_cruise=20.0,
    v_ego=20.0,
    sm=make_sm(standstill=False),
    starpilot_toggles=toggles,
  )

  assert result == pytest.approx(20.0)
  assert vcruise.nav_turn_target == pytest.approx(0.0)


def test_nav_turn_speed_control_ignores_off_ramp():
  _, vcruise = make_vcruise(nav_state={
    "valid": True,
    "maneuverType": "off ramp",
    "maneuverModifier": "slightRight",
    "maneuverDistance": 40.0,
    "nextManeuverType": "",
    "nextManeuverModifier": "",
    "nextManeuverDistance": 0.0,
  })

  toggles = make_toggles()
  toggles.nav_longitudinal_allowed = True
  result = vcruise.update(
    controls_enabled=True,
    now=0.0,
    time_validated=True,
    v_cruise=30.0,
    v_ego=30.0,
    sm=make_sm(standstill=False),
    starpilot_toggles=toggles,
  )

  assert result == pytest.approx(30.0)
  assert vcruise.nav_turn_target == pytest.approx(0.0)


def test_nav_turn_speed_control_respects_car_min_steer_speed():
  _, vcruise = make_vcruise(nav_state={
    "valid": True,
    "maneuverType": "turn",
    "maneuverModifier": "uturn",
    "maneuverDistance": 8.0,
    "nextManeuverType": "",
    "nextManeuverModifier": "",
    "nextManeuverDistance": 0.0,
  })

  toggles = make_toggles()
  toggles.nav_longitudinal_allowed = True
  result = vcruise.update(
    controls_enabled=True,
    now=0.0,
    time_validated=True,
    v_cruise=20.0,
    v_ego=20.0,
    sm=make_sm(standstill=False, min_steer_speed=7.0 * CV.MPH_TO_MS),
    starpilot_toggles=toggles,
  )

  assert result == pytest.approx(vcruise.nav_turn_target)
  assert vcruise.nav_turn_target >= 7.0 * CV.MPH_TO_MS


def test_nav_turn_speed_control_does_not_floor_steer_to_zero_cars():
  _, vcruise = make_vcruise(nav_state={
    "valid": True,
    "maneuverType": "turn",
    "maneuverModifier": "uturn",
    "maneuverDistance": 8.0,
    "nextManeuverType": "",
    "nextManeuverModifier": "",
    "nextManeuverDistance": 0.0,
  })

  toggles = make_toggles()
  toggles.nav_longitudinal_allowed = True
  result = vcruise.update(
    controls_enabled=True,
    now=0.0,
    time_validated=True,
    v_cruise=20.0,
    v_ego=20.0,
    sm=make_sm(standstill=False, min_steer_speed=0.0),
    starpilot_toggles=toggles,
  )

  assert result == pytest.approx(vcruise.nav_turn_target)
  assert vcruise.nav_turn_target == pytest.approx(5.0 * CV.MPH_TO_MS)
