import ast
import sys
from enum import IntEnum
from pathlib import Path
from types import CodeType, FunctionType, ModuleType, SimpleNamespace

import pytest

from openpilot.starpilot.common.longitudinal_personality_profiles import default_personality_profiles, profile_document


def _module(name, **attributes):
  module = ModuleType(name)
  for key, value in attributes.items():
    setattr(module, key, value)
  return module


def _faithful_get_t_follow(
  aggressive_follow=1.25, standard_follow=1.45, relaxed_follow=1.75,
  custom_personalities=False, personality=1,
):
  configured = (aggressive_follow, standard_follow, relaxed_follow)
  defaults = (1.25, 1.45, 1.75)
  return (configured if custom_personalities else defaults)[int(personality)]


class LaneChangeState(IntEnum):
  off = 0
  preLaneChange = 1
  laneChangeStarting = 2
  laneChangeFinishing = 3


class LaneChangeDirection(IntEnum):
  none = 0
  left = 1
  right = 2


sys.modules["cereal"] = _module(
  "cereal",
  log=SimpleNamespace(LaneChangeState=LaneChangeState, LaneChangeDirection=LaneChangeDirection),
)
sys.modules["openpilot.common.constants"] = _module(
  "openpilot.common.constants", CV=SimpleNamespace(MPH_TO_MS=0.44704),
)
sys.modules["openpilot.common.realtime"] = _module("openpilot.common.realtime", DT_MDL=0.05)
sys.modules["openpilot.selfdrive.controls.lib.lead_behavior"] = _module(
  "openpilot.selfdrive.controls.lib.lead_behavior", should_disable_far_lead_throttle=lambda *_args: False,
)
sys.modules["openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc"] = _module(
  "openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc",
  COMFORT_BRAKE=2.5,
  LEAD_DANGER_FACTOR=0.8,
  desired_follow_distance=lambda v_ego, _v_lead, t_follow: v_ego * t_follow,
  get_jerk_factor=lambda *_args: (1.0, 1.0, 1.0),
  get_T_FOLLOW=_faithful_get_t_follow,
)
sys.modules["openpilot.starpilot.common.starpilot_variables"] = _module(
  "openpilot.starpilot.common.starpilot_variables", CITY_SPEED_LIMIT=11.176, MAX_T_FOLLOW=3.0,
)

import openpilot.starpilot.controls.lib.starpilot_following as following_module

StarPilotFollowing = following_module.StarPilotFollowing


class Personality(IntEnum):
  aggressive = 0
  standard = 1
  relaxed = 2


def _real_get_jerk_factor():
  source_path = Path(__file__).resolve().parents[3] / "selfdrive/controls/lib/longitudinal_mpc_lib/long_mpc.py"
  tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
  function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "get_jerk_factor")
  module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
  module_code = compile(module, str(source_path), "exec")
  function_code = next(code for code in module_code.co_consts if isinstance(code, CodeType) and code.co_name == function.name)
  np_stub = SimpleNamespace(interp=lambda value, breakpoints, values: values[0] if value <= breakpoints[0] else values[-1])
  return FunctionType(function_code, {"log": SimpleNamespace(LongitudinalPersonality=Personality), "np": np_stub})


def _planner(*, weather_id=0, weather_increase=0.0):
  lead = SimpleNamespace(status=False, dRel=1000.0, vLead=0.0, aLeadK=0.0)
  return SimpleNamespace(
    lead_one=lead,
    starpilot_weather=SimpleNamespace(weather_id=weather_id, increase_following_distance=weather_increase),
    tracking_lead=False,
  )


def _sm(*, traffic=False, personality=Personality.standard):
  return {
    "carState": SimpleNamespace(aEgo=0.0, standstill=False, leftBlindspot=False, rightBlindspot=False),
    "selfdriveState": SimpleNamespace(personality=personality),
    "starpilotCarState": SimpleNamespace(trafficModeEnabled=traffic),
  }


def _toggles(document):
  return SimpleNamespace(
    aggressive_follow=1.25,
    aggressive_jerk_acceleration=1.0,
    aggressive_jerk_danger=1.0,
    aggressive_jerk_deceleration=1.0,
    aggressive_jerk_speed=1.0,
    aggressive_jerk_speed_decrease=1.0,
    conditional_slower_lead=False,
    custom_personalities=True,
    lane_change_close_gap=False,
    lane_change_close_gap_seconds=0.75,
    longitudinal_personality_profiles=document,
    minimum_lane_change_speed=0.0,
    personality_ev_tuning=False,
    relaxed_follow=1.6,
    relaxed_jerk_acceleration=1.0,
    relaxed_jerk_danger=1.0,
    relaxed_jerk_deceleration=1.0,
    relaxed_jerk_speed=1.0,
    relaxed_jerk_speed_decrease=1.0,
    standard_follow=1.45,
    standard_jerk_acceleration=1.0,
    standard_jerk_danger=1.0,
    standard_jerk_deceleration=1.0,
    standard_jerk_speed=1.0,
    standard_jerk_speed_decrease=1.0,
    traffic_mode_follow=[0.75, 1.0],
    traffic_mode_jerk_acceleration=[1.0, 1.0],
    traffic_mode_jerk_danger=[1.0, 1.0],
    traffic_mode_jerk_deceleration=[1.0, 1.0],
    traffic_mode_jerk_speed=[1.0, 1.0],
    traffic_mode_jerk_speed_decrease=[1.0, 1.0],
  )


def _document(*, enabled=True):
  return profile_document(default_personality_profiles(False), enabled=enabled)


def test_explicit_following_curve_selects_active_personality_and_linear_speed_point():
  document = _document()
  document["profiles"]["standard"]["following"] = {
    "preset": "custom",
    "curve": [0.75 + 0.1 * index for index in range(10)],
  }
  controller = StarPilotFollowing(_planner())

  controller.update(True, 5.0 * 0.44704, _sm(), _toggles(document))

  assert controller.t_follow == pytest.approx(0.80)
  assert controller.base_acceleration_jerk == 1.0


@pytest.mark.parametrize(
  ("profile", "personality", "traffic_mode", "following"),
  [
    ("aggressive", Personality.aggressive, False, 0.90),
    ("standard", Personality.standard, False, 1.20),
    ("relaxed", Personality.relaxed, False, 1.50),
    ("traffic", Personality.aggressive, True, 1.80),
  ],
)
def test_each_explicit_profile_following_override_reaches_runtime(profile, personality, traffic_mode, following):
  document = _document()
  document["profiles"][profile]["following"] = {"preset": "custom", "curve": [following] * 10}
  controller = StarPilotFollowing(_planner())

  controller.update(True, 10.0, _sm(traffic=traffic_mode, personality=personality), _toggles(document))

  assert controller.t_follow == pytest.approx(following)


def test_master_toggle_disables_following_document_override():
  document = _document()
  document["profiles"]["standard"]["following"] = {"preset": "custom", "curve": [0.9] * 10}
  toggles = _toggles(document)
  toggles.custom_personalities = False

  controller = StarPilotFollowing(_planner())
  controller.update(True, 10.0, _sm(), toggles)

  assert controller.t_follow == pytest.approx(1.45)


@pytest.mark.parametrize(
  ("profile", "personality", "traffic_mode", "legacy_follow"),
  [
    ("traffic", Personality.aggressive, True, 0.75),
    ("aggressive", Personality.aggressive, False, 1.25),
    ("standard", Personality.standard, False, 1.45),
    ("relaxed", Personality.relaxed, False, 1.6),
  ],
)
def test_disabled_active_profile_keeps_legacy_following_path(profile, personality, traffic_mode, legacy_follow):
  document = _document()
  document["profiles"][profile]["following"] = {"preset": "custom", "curve": [0.9] * 10}
  toggles = _toggles(document)
  setattr(toggles, f"{profile}_personality_profile", False)
  controller = StarPilotFollowing(_planner())

  controller.update(True, 0.0, _sm(traffic=traffic_mode, personality=personality), toggles)

  assert controller.t_follow == pytest.approx(legacy_follow)


def test_traffic_profile_wins_over_cereal_personality_without_changing_jerk():
  document = _document()
  document["profiles"]["traffic"]["following"] = {"preset": "far", "curve": []}
  controller = StarPilotFollowing(_planner())

  controller.update(True, 0.0, _sm(traffic=True, personality=Personality.aggressive), _toggles(document))

  assert controller.t_follow == pytest.approx(1.75)
  assert controller.base_acceleration_jerk == 1.0


@pytest.mark.parametrize("document", [None, {}, _document(enabled=False)])
def test_absent_malformed_or_disabled_document_keeps_legacy_standard_follow(document):
  controller = StarPilotFollowing(_planner())

  controller.update(True, 0.0, _sm(), _toggles(document))

  assert controller.t_follow == pytest.approx(1.45)


def test_dom_default_category_keeps_legacy_traffic_follow():
  document = _document()
  document["profiles"]["traffic"]["following"] = {"preset": "dom_default", "curve": []}
  controller = StarPilotFollowing(_planner())

  controller.update(True, 0.0, _sm(traffic=True), _toggles(document))

  assert controller.t_follow == pytest.approx(0.75)


def test_existing_weather_modifier_runs_after_profile_and_retains_maximum_bound():
  document = _document()
  document["profiles"]["relaxed"]["following"] = {"preset": "custom", "curve": [2.9] * 10}
  controller = StarPilotFollowing(_planner(weather_id=1, weather_increase=0.5))

  controller.update(True, 10.0, _sm(personality=Personality.relaxed), _toggles(document))

  assert controller.t_follow == pytest.approx(3.0)


@pytest.mark.parametrize(
  ("personality", "prefix"),
  [
    (Personality.aggressive, "aggressive"),
    (Personality.standard, "standard"),
    (Personality.relaxed, "relaxed"),
  ],
)
@pytest.mark.parametrize(
  ("a_ego", "expected_suffix"),
  [(1.0, "acceleration"), (-1.0, "deceleration")],
)
def test_every_nontraffic_advanced_jerk_value_reaches_runtime(monkeypatch, personality, prefix, a_ego, expected_suffix):
  toggles = _toggles(_document())
  values = {
    "acceleration": 0.31,
    "deceleration": 0.47,
    "danger": 0.63,
    "speed": 0.79,
    "speed_decrease": 0.95,
  }
  for suffix, value in values.items():
    setattr(toggles, f"{prefix}_jerk_{suffix}", value)

  monkeypatch.setattr(following_module, "get_jerk_factor", _real_get_jerk_factor())
  sm = _sm(personality=personality)
  sm["carState"].aEgo = a_ego
  controller = StarPilotFollowing(_planner())
  controller.update(True, 10.0, sm, toggles)

  assert controller.base_acceleration_jerk == pytest.approx(values[expected_suffix])
  assert controller.base_danger_jerk == pytest.approx(values["danger"])
  assert controller.base_speed_jerk == pytest.approx(values["speed" if a_ego >= 0 else "speed_decrease"])


@pytest.mark.parametrize(
  ("a_ego", "expected_suffix"),
  [(1.0, "acceleration"), (-1.0, "deceleration")],
)
def test_every_traffic_advanced_jerk_value_reaches_low_speed_runtime(monkeypatch, a_ego, expected_suffix):
  toggles = _toggles(_document())
  values = {
    "acceleration": 0.31,
    "deceleration": 0.47,
    "danger": 0.63,
    "speed": 0.79,
    "speed_decrease": 0.95,
  }
  for suffix, value in values.items():
    setattr(toggles, f"traffic_mode_jerk_{suffix}", [value, 1.75])

  monkeypatch.setattr(following_module, "get_jerk_factor", _real_get_jerk_factor())
  sm = _sm(traffic=True, personality=Personality.standard)
  sm["carState"].aEgo = a_ego
  controller = StarPilotFollowing(_planner())
  controller.update(True, 0.0, sm, toggles)

  assert controller.base_acceleration_jerk == pytest.approx(values[expected_suffix])
  assert controller.base_danger_jerk == pytest.approx(values["danger"])
  assert controller.base_speed_jerk == pytest.approx(values["speed" if a_ego >= 0 else "speed_decrease"])


def test_every_advanced_param_maps_to_runtime_attribute_with_hundredth_conversion():
  source_path = Path(__file__).resolve().parents[2] / "common/starpilot_variables.py"
  tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
  expected = {
    f"{profile}Jerk{suffix}": f"{attribute_prefix}_jerk_{attribute_suffix}"
    for profile, attribute_prefix in (
      ("Aggressive", "aggressive"),
      ("Standard", "standard"),
      ("Relaxed", "relaxed"),
      ("Traffic", "traffic_mode"),
    )
    for suffix, attribute_suffix in (
      ("Acceleration", "acceleration"),
      ("Deceleration", "deceleration"),
      ("Danger", "danger"),
      ("Speed", "speed"),
      ("SpeedDecrease", "speed_decrease"),
    )
  }
  discovered = {}
  for assignment in (node for node in ast.walk(tree) if isinstance(node, ast.Assign)):
    if len(assignment.targets) != 1 or not isinstance(assignment.targets[0], ast.Attribute):
      continue
    target = assignment.targets[0].attr
    for call in (node for node in ast.walk(assignment.value) if isinstance(node, ast.Call)):
      if not call.args or not isinstance(call.args[0], ast.Constant) or call.args[0].value not in expected:
        continue
      discovered[call.args[0].value] = (
        target,
        {keyword.arg: ast.literal_eval(keyword.value) for keyword in call.keywords if keyword.arg in {"conversion", "min", "max"}},
      )

  assert set(discovered) == set(expected)
  for key, expected_attribute in expected.items():
    attribute, keywords = discovered[key]
    assert attribute == expected_attribute
    assert keywords["conversion"] == 0.01
    assert keywords["min"] == 0.25
    assert keywords["max"] == 2.0
