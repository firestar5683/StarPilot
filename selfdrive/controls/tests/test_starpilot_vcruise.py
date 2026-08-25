import datetime

import pytest

from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL
from openpilot.starpilot.common.starpilot_variables import PLANNER_TIME
from openpilot.starpilot.controls.lib.curve_speed_controller import CSC_GLOW_HOLD_TIME, CSC_GLOW_ON_DELTA
from openpilot.starpilot.controls.lib.starpilot_vcruise import (
  FORCE_STOP_CAP_SLACK_M,
  FORCE_STOP_TURN_VETO_STOP_SEEN_HOLD_TIME,
  STANDSTILL_FORCE_STOP_LIGHT_HOLD_TIME,
  StarPilotVCruise,
  get_active_slc_control_target,
  get_lead_veto_distance,
  get_slc_lead_drop_relaxed_target,
)
from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import (
  get_force_stop_distance_bias,
  get_force_stop_handoff_distance,
)
from types import SimpleNamespace


class FakeParams:
  def __init__(self, values=None):
    self.values = dict(values or {})
    self.writes = []

  def get(self, *args, **kwargs):
    key = args[0] if args else None
    return self.values.get(key)

  def get_float(self, *args, **kwargs):
    return 0.0

  def put_nonblocking(self, key, value):
    self.values[key] = value
    self.writes.append((key, value))


def make_vcruise(*, red_light=False, raw_model_stopped=False, forcing_stop=False, nav_state=None, road_curvature=0.0):
  planner = SimpleNamespace(
    params=FakeParams(),
    params_memory=FakeParams({"NavInstructionState": nav_state or {}}),
    lead_one=SimpleNamespace(status=False, dRel=float("inf"), vLead=0.0),
    starpilot_cem=SimpleNamespace(stop_light_detected=red_light),
    starpilot_following=SimpleNamespace(following_lead=False),
    tracking_lead=False,
    driving_in_curve=False,
    lateral_acceleration=0.0,
    model_length=60.0,
    raw_model_stopped=raw_model_stopped,
    road_curvature=road_curvature,
    road_curvature_detected=False,
  )
  vcruise = StarPilotVCruise(planner)
  vcruise.forcing_stop = forcing_stop
  vcruise.force_stop_timer = 1.0 if forcing_stop else 0.0
  vcruise.tracked_model_length = 0.0 if forcing_stop else planner.model_length
  # what the not-committed branch would have left behind on the frame before commit
  vcruise.force_stop_distance_cap = planner.model_length + FORCE_STOP_CAP_SLACK_M
  return planner, vcruise


def make_sm(*, standstill=True, min_steer_speed=0.0):
  return {
    "carControl": SimpleNamespace(longActive=True),
    "carState": SimpleNamespace(
      standstill=standstill,
      gasPressed=False,
      brakePressed=False,
      vCruiseCluster=0.0,
      vEgoCluster=0.0,
      leftBlinker=False,
      rightBlinker=False,
      steeringAngleDeg=0.0,
    ),
    "carParams": SimpleNamespace(minSteerSpeed=min_steer_speed),
    "starpilotCarState": SimpleNamespace(accelPressed=False, dashboardStopSign=0, dashboardSpeedLimit=0),
    "onroadEvents": [],
  }


def update_vcruise(vcruise, sm, toggles, *, now, v_ego=0.0, v_cruise=20.0, controls_enabled=True):
  return vcruise.update(
    controls_enabled=controls_enabled,
    now=now,
    time_validated=True,
    v_cruise=v_cruise,
    v_ego=v_ego,
    sm=sm,
    starpilot_toggles=toggles,
  )


def make_toggles():
  return SimpleNamespace(
    force_stops=True,
    force_standstill=False,
    curve_speed_controller=False,
    csc_no_lead=False,
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


def test_elantra_gets_lead_veto_margin_before_force_stop():
  assert get_lead_veto_distance(SimpleNamespace(carFingerprint="HYUNDAI_ELANTRA_2021")) == pytest.approx(90.0)
  assert get_lead_veto_distance(SimpleNamespace(carFingerprint="OTHER_CAR")) == pytest.approx(75.0)


def test_camry_tss2_uses_closer_force_stop_handoff():
  assert get_force_stop_handoff_distance("TOYOTA_CAMRY_TSS2") == pytest.approx(4.5)
  assert get_force_stop_handoff_distance("TOYOTA_RAV4_TSS2") == pytest.approx(6.0)


def test_camry_tss2_gets_forward_force_stop_bias_only():
  assert get_force_stop_distance_bias("TOYOTA_CAMRY_TSS2") == pytest.approx(6.0)
  assert get_force_stop_distance_bias("TOYOTA_RAV4_TSS2") == pytest.approx(0.0)


def test_curve_speed_controller_blinker_releases_the_cap_but_keeps_the_plan():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  calls = []

  def set_curve_target(_v_ego, _v_cruise):
    calls.append(_v_ego)
    vcruise.csc.target = 14.0

  vcruise.csc.update_target = set_curve_target
  result = update_vcruise(vcruise, sm, toggles, now=10.0, v_ego=20.0)
  assert result == pytest.approx(14.0)
  assert vcruise.csc_controlling_speed

  # the cap lifts so CSC can't fight the lane change, but the envelope keeps planning
  # so the curve doesn't have to be re-discovered from the set speed afterwards
  sm["carState"].leftBlinker = True
  result = update_vcruise(vcruise, sm, toggles, now=10.25, v_ego=20.0)
  assert result == pytest.approx(20.0)
  assert not vcruise.csc_controlling_speed
  assert len(calls) == 2  # still planning, so nothing has to be rediscovered

  # blinker off: the plan is already current, so the cap comes straight back
  sm["carState"].leftBlinker = False
  result = update_vcruise(vcruise, sm, toggles, now=10.5, v_ego=20.0)
  assert result == pytest.approx(14.0)
  assert vcruise.csc_controlling_speed


def test_curve_speed_controller_reseeds_after_a_real_dropout():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = 14.0

  vcruise.csc.update_target = set_curve_target
  update_vcruise(vcruise, sm, toggles, now=11.0, v_ego=20.0)
  assert vcruise.csc_controlling_speed

  # disengaging is a real dropout, not a momentary veto -- that still resets
  sm["carControl"].longActive = False
  update_vcruise(vcruise, sm, toggles, now=11.05, v_ego=20.0)
  assert not vcruise.csc_controlling_speed
  assert vcruise.csc.seed_pending


def test_curve_speed_controller_releases_immediately_when_disabled():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = 14.0

  vcruise.csc.update_target = set_curve_target
  update_vcruise(vcruise, sm, toggles, now=20.0, v_ego=20.0)
  assert vcruise.csc_controlling_speed

  toggles.curve_speed_controller = False
  result = update_vcruise(vcruise, sm, toggles, now=20.1, v_ego=20.0)
  assert result == pytest.approx(20.0)
  assert not vcruise.csc_controlling_speed


def test_curve_speed_controller_can_be_limited_to_driving_without_a_lead():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True
  toggles.csc_no_lead = True

  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = 14.0

  vcruise.csc.update_target = set_curve_target

  result = update_vcruise(vcruise, sm, toggles, now=30.0, v_ego=20.0)
  assert result == pytest.approx(14.0)
  assert vcruise.csc_controlling_speed

  planner.starpilot_following.following_lead = True
  result = update_vcruise(vcruise, sm, toggles, now=30.1, v_ego=20.0)
  assert result == pytest.approx(20.0)
  assert not vcruise.csc_controlling_speed


def test_curve_speed_controller_stays_enabled_with_a_lead_by_default():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True
  planner.starpilot_following.following_lead = True

  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = 14.0

  vcruise.csc.update_target = set_curve_target
  result = update_vcruise(vcruise, sm, toggles, now=40.0, v_ego=20.0)

  assert result == pytest.approx(14.0)
  assert vcruise.csc_controlling_speed


@pytest.mark.parametrize(
  ("long_active", "gas_pressed"),
  [(False, False), (True, True)],
)
def test_curve_speed_controller_learns_when_speed_is_manually_controlled(long_active, gas_pressed):
  planner, vcruise = make_vcruise(road_curvature=0.02)
  sm = make_sm(standstill=False)
  sm["carControl"].longActive = long_active
  sm["carState"].gasPressed = gas_pressed
  toggles = make_toggles()
  toggles.curve_speed_controller = True
  planner.driving_in_curve = True
  planner.road_curvature_detected = True
  planner.lateral_acceleration = 2.4
  vcruise.csc.training_timer = PLANNER_TIME

  update_vcruise(vcruise, sm, toggles, now=50.0, v_ego=20.0)

  assert vcruise.csc.enable_training
  assert vcruise.csc.curvature_data["0.02"]["count"] == 1
  assert not vcruise.csc_controlling_speed


def test_curve_speed_controller_persists_data_after_leaving_curve():
  planner, vcruise = make_vcruise(road_curvature=0.02)
  sm = make_sm(standstill=False)
  sm["carControl"].longActive = False
  planner.driving_in_curve = True
  planner.lateral_acceleration = 2.4
  vcruise.csc.training_timer = PLANNER_TIME

  vcruise.csc.log_data(20.0, sm)
  assert not any(key == "CurvatureData" for key, _ in planner.params.writes)

  planner.driving_in_curve = False
  vcruise.csc.log_data(20.0, sm)

  assert any(key == "CurvatureData" for key, _ in planner.params.writes)


def test_csc_res_press_cancels_for_episode_and_rearms():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  curve_target = {"v": 14.0}

  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = curve_target["v"]

  vcruise.csc.update_target = set_curve_target
  result = update_vcruise(vcruise, sm, toggles, now=60.0, v_ego=20.0)
  assert result == pytest.approx(14.0)
  assert vcruise.csc_controlling_speed

  sm["starpilotCarState"].accelPressed = True
  result = update_vcruise(vcruise, sm, toggles, now=60.05, v_ego=20.0)
  assert result == pytest.approx(20.0)
  assert not vcruise.csc_controlling_speed
  assert vcruise.csc_override

  # latches for the rest of the episode, not just while pressed
  sm["starpilotCarState"].accelPressed = False
  result = update_vcruise(vcruise, sm, toggles, now=60.1, v_ego=20.0)
  assert result == pytest.approx(20.0)
  assert vcruise.csc_override

  # curve ends -> re-arms
  curve_target["v"] = 20.0
  update_vcruise(vcruise, sm, toggles, now=60.15, v_ego=20.0)
  assert not vcruise.csc_override

  curve_target["v"] = 14.0
  result = update_vcruise(vcruise, sm, toggles, now=60.2, v_ego=20.0)
  assert result == pytest.approx(14.0)
  assert vcruise.csc_controlling_speed


def test_csc_res_press_does_not_latch_when_csc_was_not_active():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = 14.0

  vcruise.csc.update_target = set_curve_target
  # press before CSC ever limited: suspends it while held, but must not latch a cancel
  sm["starpilotCarState"].accelPressed = True
  result = update_vcruise(vcruise, sm, toggles, now=70.0, v_ego=20.0)
  assert result == pytest.approx(20.0)
  assert not vcruise.csc_override

  sm["starpilotCarState"].accelPressed = False
  result = update_vcruise(vcruise, sm, toggles, now=70.05, v_ego=20.0)
  assert result == pytest.approx(14.0)
  assert vcruise.csc_controlling_speed


def test_csc_res_press_defers_to_slc_confirmation():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = 14.0

  vcruise.csc.update_target = set_curve_target
  update_vcruise(vcruise, sm, toggles, now=80.0, v_ego=20.0)
  assert vcruise.csc_controlling_speed

  # confirming a speed limit must not also cancel the curve slowdown
  vcruise.slc.speed_limit_changed_timer = 1.0
  vcruise.slc.unconfirmed_speed_limit = 25.0
  sm["starpilotCarState"].accelPressed = True
  update_vcruise(vcruise, sm, toggles, now=80.05, v_ego=20.0)
  assert not vcruise.csc_override

  sm["starpilotCarState"].accelPressed = False
  result = update_vcruise(vcruise, sm, toggles, now=80.1, v_ego=20.0)
  assert result == pytest.approx(14.0)
  assert vcruise.csc_controlling_speed


def test_curve_speed_controller_glow_ignores_a_trivial_graze():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  # a long gentle bend where the envelope only shaves a little: the target hovers either
  # side of the threshold for the whole curve, so a low bar strobes the glow
  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = 20.0 - (CSC_GLOW_ON_DELTA / 2.0)

  vcruise.csc.update_target = set_curve_target
  result = update_vcruise(vcruise, sm, toggles, now=160.0, v_ego=20.0)

  assert result < 20.0                      # the cap is still applied
  assert not vcruise.csc_controlling_speed  # it just isn't worth announcing


def test_curve_speed_controller_glow_holds_through_a_brief_release():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  curve_target = {"v": 14.0}

  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = curve_target["v"]

  vcruise.csc.update_target = set_curve_target
  update_vcruise(vcruise, sm, toggles, now=130.0, v_ego=20.0)
  assert vcruise.csc_controlling_speed

  # one curve routinely lets go and re-engages; the glow must ride through it
  curve_target["v"] = 20.0
  now = 130.0
  for _ in range(int((CSC_GLOW_HOLD_TIME - 0.2) / DT_MDL)):
    now += DT_MDL
    update_vcruise(vcruise, sm, toggles, now=now, v_ego=20.0)
    assert vcruise.csc_controlling_speed

  curve_target["v"] = 14.0
  now += DT_MDL
  update_vcruise(vcruise, sm, toggles, now=now, v_ego=20.0)
  assert vcruise.csc_controlling_speed


def test_curve_speed_controller_glow_clears_once_the_release_sticks():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  curve_target = {"v": 14.0}

  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = curve_target["v"]

  vcruise.csc.update_target = set_curve_target
  update_vcruise(vcruise, sm, toggles, now=140.0, v_ego=20.0)
  assert vcruise.csc_controlling_speed

  curve_target["v"] = 20.0
  now = 140.0
  for _ in range(int(CSC_GLOW_HOLD_TIME / DT_MDL) + 1):
    now += DT_MDL
    update_vcruise(vcruise, sm, toggles, now=now, v_ego=20.0)
  assert not vcruise.csc_controlling_speed


def test_curve_speed_controller_keeps_the_cap_when_signalling_mid_curve():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = 14.0

  vcruise.csc.update_target = set_curve_target
  result = update_vcruise(vcruise, sm, toggles, now=150.0, v_ego=20.0)
  assert result == pytest.approx(14.0)

  # a lane change taken inside a curve must not hand the speed back
  planner.driving_in_curve = True
  sm["carState"].leftBlinker = True
  result = update_vcruise(vcruise, sm, toggles, now=150.05, v_ego=20.0)
  assert result == pytest.approx(14.0)
  assert vcruise.csc_controlling_speed

  # on a straight it still yields, so CSC can't fight the manoeuvre
  planner.driving_in_curve = False
  result = update_vcruise(vcruise, sm, toggles, now=150.1, v_ego=20.0)
  assert result == pytest.approx(20.0)
  assert not vcruise.csc_controlling_speed


def test_curve_speed_controller_glow_lights_when_the_car_arrives_at_the_cap_from_below():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  # accelerating out of a slow zone into a curve: the target is never under v_ego, but it
  # is still the only thing stopping the car from reaching the set speed
  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = 22.0

  vcruise.csc.update_target = set_curve_target

  update_vcruise(vcruise, sm, toggles, now=120.0, v_ego=15.0, v_cruise=32.0)
  assert not vcruise.csc_controlling_speed          # still climbing, CSC isn't holding it yet

  result = update_vcruise(vcruise, sm, toggles, now=120.05, v_ego=22.0, v_cruise=32.0)
  assert result == pytest.approx(22.0)
  assert vcruise.csc_controlling_speed              # arrived at the cap, and it binds


def test_curve_speed_controller_glow_stays_off_while_the_target_is_above_v_ego():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  # a highway sweeper trims the target well under the set speed but never under v_ego,
  # so the car keeps accelerating and the driver feels nothing
  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = 26.0

  vcruise.csc.update_target = set_curve_target
  result = update_vcruise(vcruise, sm, toggles, now=90.0, v_ego=20.0, v_cruise=30.0)

  assert result == pytest.approx(26.0)
  assert not vcruise.csc_controlling_speed


def test_curve_speed_controller_glow_holds_through_the_recovery_ramp():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  curve_target = {"v": 14.0}

  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = curve_target["v"]

  vcruise.csc.update_target = set_curve_target
  update_vcruise(vcruise, sm, toggles, now=100.0, v_ego=20.0)
  assert vcruise.csc_controlling_speed

  # past the apex the target climbs back above v_ego while the car is still cornering
  curve_target["v"] = 18.0
  update_vcruise(vcruise, sm, toggles, now=100.05, v_ego=15.0)
  assert vcruise.csc_controlling_speed

  # fully released, but the glow only clears once the release has stuck
  curve_target["v"] = 20.0
  now = 100.1
  update_vcruise(vcruise, sm, toggles, now=now, v_ego=17.0)
  assert vcruise.csc_controlling_speed

  for _ in range(int(CSC_GLOW_HOLD_TIME / DT_MDL) + 1):
    now += DT_MDL
    update_vcruise(vcruise, sm, toggles, now=now, v_ego=17.0)
  assert not vcruise.csc_controlling_speed


def test_curve_speed_controller_hysteresis_keeps_glow_off_for_marginal_targets():
  planner, vcruise = make_vcruise()
  sm = make_sm(standstill=False)
  toggles = make_toggles()
  toggles.curve_speed_controller = True

  def set_curve_target(_v_ego, _v_cruise):
    vcruise.csc.target = 19.7

  vcruise.csc.update_target = set_curve_target
  result = update_vcruise(vcruise, sm, toggles, now=50.0, v_ego=20.0)

  assert result == pytest.approx(19.7)
  assert not vcruise.csc_controlling_speed


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


def test_active_slc_control_target_allows_lower_redneck_override():
  target = get_active_slc_control_target(
    speed_limit_controller=True,
    set_speed_limit=False,
    slc_target=65.0 * CV.MPH_TO_MS,
    slc_offset=0.0,
    overridden_speed=35.0 * CV.MPH_TO_MS,
    v_ego_diff=0.4,
    allow_lower_override=True,
  )

  assert target == pytest.approx((35.0 * CV.MPH_TO_MS) - 0.4)


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


def test_force_stop_reanchors_when_model_reopens_path_without_stop_action():
  planner, vcruise = make_vcruise(red_light=False, raw_model_stopped=False, forcing_stop=True)
  planner.model_length = 90.0
  vcruise.tracked_model_length = 60.0
  vcruise.force_stop_distance_cap = 90.0 + FORCE_STOP_CAP_SLACK_M
  sm = make_sm(standstill=False)
  sm["modelV2"] = SimpleNamespace(action=SimpleNamespace(shouldStop=False))

  result = update_vcruise(vcruise, sm, make_toggles(), now=0.0, v_ego=1.5)

  assert vcruise.tracked_model_length == pytest.approx(90.0)
  assert result > 5.0


def test_force_stop_does_not_reanchor_inside_reanchor_floor():
  planner, vcruise = make_vcruise(red_light=False, raw_model_stopped=False, forcing_stop=True)
  planner.model_length = 90.0
  vcruise.tracked_model_length = 25.0
  sm = make_sm(standstill=False)
  sm["modelV2"] = SimpleNamespace(action=SimpleNamespace(shouldStop=False))

  update_vcruise(vcruise, sm, make_toggles(), now=0.0, v_ego=1.5)

  assert vcruise.tracked_model_length < 25.0


def test_force_stop_reanchor_bounded_by_distance_driven():
  # The line can't recede: a ballooning horizon may not push the stop past where it was at
  # commit minus the distance driven since.
  planner, vcruise = make_vcruise(red_light=False, raw_model_stopped=False, forcing_stop=True)
  planner.model_length = 200.0
  vcruise.tracked_model_length = 60.0
  vcruise.force_stop_distance_cap = 70.0
  sm = make_sm(standstill=False)
  sm["modelV2"] = SimpleNamespace(action=SimpleNamespace(shouldStop=False))

  update_vcruise(vcruise, sm, make_toggles(), now=0.0, v_ego=10.0)

  assert vcruise.tracked_model_length <= 70.0


def test_force_stop_does_not_reanchor_committed_model_stop():
  planner, vcruise = make_vcruise(red_light=False, raw_model_stopped=False, forcing_stop=True)
  planner.model_length = 40.0
  vcruise.tracked_model_length = 10.0
  sm = make_sm(standstill=False)
  sm["modelV2"] = SimpleNamespace(action=SimpleNamespace(shouldStop=True))

  update_vcruise(vcruise, sm, make_toggles(), now=0.0, v_ego=1.5)

  assert vcruise.tracked_model_length < 10.0


def test_force_stop_releases_after_cem_light_clears_while_moving():
  planner, vcruise = make_vcruise(red_light=True, raw_model_stopped=False, forcing_stop=True)
  sm = make_sm(standstill=False)
  toggles = make_toggles()

  update_vcruise(vcruise, sm, toggles, now=0.0, v_ego=3.0)
  assert vcruise.force_stop_from_light

  planner.starpilot_cem.stop_light_detected = False
  update_vcruise(vcruise, sm, toggles, now=0.25, v_ego=3.0)
  assert vcruise.forcing_stop

  result = update_vcruise(vcruise, sm, toggles, now=0.75, v_ego=3.0)
  assert result == pytest.approx(20.0)
  assert not vcruise.forcing_stop
  assert not vcruise.force_stop_from_light


def test_force_stop_light_release_ignores_coarse_stopped_model_horizon():
  planner, vcruise = make_vcruise(red_light=True, raw_model_stopped=True, forcing_stop=True)
  sm = make_sm(standstill=False)
  toggles = make_toggles()

  update_vcruise(vcruise, sm, toggles, now=0.0, v_ego=3.0)
  planner.starpilot_cem.stop_light_detected = False

  update_vcruise(vcruise, sm, toggles, now=0.25, v_ego=3.0)
  assert vcruise.forcing_stop

  result = update_vcruise(vcruise, sm, toggles, now=0.75, v_ego=3.0)
  assert result == pytest.approx(20.0)
  assert not vcruise.forcing_stop
  assert not vcruise.force_stop_from_light


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

  planner.starpilot_cem.stop_light_detected = True
  update_vcruise(vcruise, sm, toggles, now=0.0, v_ego=7.0)
  planner.starpilot_cem.stop_light_detected = False

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

  planner.starpilot_cem.stop_light_detected = False
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

  planner.starpilot_cem.stop_light_detected = False
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

  assert update_vcruise(vcruise, sm, toggles, now=STANDSTILL_FORCE_STOP_LIGHT_HOLD_TIME - 0.1) == pytest.approx(0.0)
  assert vcruise.forcing_stop

  assert update_vcruise(vcruise, sm, toggles, now=STANDSTILL_FORCE_STOP_LIGHT_HOLD_TIME + 0.1) == pytest.approx(20.0)
  assert not vcruise.forcing_stop
  assert not vcruise.standstill_force_stop_hold

  # The red-light model remains stopped, but Force Stop must stay released so
  # Experimental Mode can own the red-to-green departure.
  assert update_vcruise(vcruise, sm, toggles, now=STANDSTILL_FORCE_STOP_LIGHT_HOLD_TIME + 0.2) == pytest.approx(20.0)
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
  planner, vcruise = make_vcruise(red_light=True, raw_model_stopped=True, forcing_stop=False)
  planner.model_length = 20.0
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
