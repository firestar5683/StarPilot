import pytest

from openpilot.common.constants import CV
from openpilot.starpilot.controls.lib.starpilot_vcruise import StarPilotVCruise, get_active_slc_control_target
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


def make_vcruise(*, red_light=False, raw_model_stopped=False, forcing_stop=False, nav_state=None):
  planner = SimpleNamespace(
    params=FakeParams(),
    params_memory=FakeParams({"NavInstructionState": nav_state or {}}),
    lead_one=SimpleNamespace(status=False, dRel=float("inf"), vLead=0.0),
    starpilot_cem=SimpleNamespace(stop_light_detected=red_light),
    tracking_lead=False,
    driving_in_curve=False,
    model_length=60.0,
    raw_model_stopped=raw_model_stopped,
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
    "carState": SimpleNamespace(standstill=standstill, gasPressed=False, vCruiseCluster=0.0, vEgoCluster=0.0),
    "carParams": SimpleNamespace(minSteerSpeed=min_steer_speed),
    "starpilotCarState": SimpleNamespace(accelPressed=False, dashboardStopSign=0, dashboardSpeedLimit=0),
  }


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
