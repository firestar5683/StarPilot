from copy import deepcopy

import pytest

from openpilot.starpilot.common import longitudinal_personality_profiles as lpp
from openpilot.starpilot.common.accel_profile import A_CRUISE_MAX_VALS_TRAFFIC_ALL, interpolate_accel_profile, get_accel_profile_curve_values
from test_personality_profiles_api import _client, the_galaxy


@pytest.mark.parametrize("personality", lpp.PERSONALITY_IDS)
@pytest.mark.parametrize("category,preset", [("acceleration", "eco"), ("braking", "sport"), ("following", "far")])
def test_retention_and_reset_are_atomic_per_category(monkeypatch, personality, category, preset):
  profiles = lpp.default_personality_profiles(False)
  saved = {"preset": "custom", "curve": [1.15] * 10}
  profiles[personality][category] = deepcopy(saved)
  client, params = _client(monkeypatch, {"CustomPersonalities": True, lpp.PERSONALITY_PROFILES_PARAM: lpp.profile_document(profiles, enabled=True)})
  endpoint = "/api/personality_profiles"
  for selected in (preset, "dom_default", "custom"):
    expected = client.get(endpoint).get_json()["profiles"][personality][category]
    response = client.put(endpoint, json={"profile": personality, "category": category, "preset": selected, "curve": [], "expected": expected})
    assert response.status_code == 200
    assert response.get_json()["profiles"][personality][category]["curve"] == saved["curve"]
  before = client.get(endpoint).get_json()
  response = client.put(endpoint, json={"profile": personality, "category": category, "preset": "custom", "curve": [], "reset": True, "expected": saved})
  assert response.status_code == 200
  result = response.get_json()
  expected_profiles = deepcopy(profiles)
  expected_profiles[personality][category] = {"preset": "custom", "curve": before["reference_curves"][personality][category]}
  assert result["profiles"] == expected_profiles
  assert lpp.strict_profile_document(params.values[lpp.PERSONALITY_PROFILES_PARAM])["profiles"] == expected_profiles
  for selected in (preset, "custom"):
    response = client.put(endpoint, json={"profile": personality, "category": category, "preset": selected, "curve": []})
    assert response.status_code == 200
  assert response.get_json()["profiles"] == expected_profiles


def test_reference_lines_use_dom_traffic_and_enabled_following_defaults(monkeypatch):
  client, _ = _client(monkeypatch, {"CustomPersonalities": True})
  curves = client.get("/api/personality_profiles").get_json()["reference_curves"]
  assert curves["traffic"]["acceleration"] == [round(interpolate_accel_profile(speed * 0.44704, A_CRUISE_MAX_VALS_TRAFFIC_ALL), 4) for speed in lpp.ACCELERATION_SPEEDS_MPH]
  assert curves["traffic"]["braking"] == [0.35] * 10
  assert curves["standard"]["braking"] == [0.5] * 10
  assert curves["standard"]["following"] == [1.45] * 5 + [1.4, 1.3, 1.2, 1.2, 1.2]
  assert curves["traffic"]["following"][0] == 0.75
  assert curves["traffic"]["following"][-1] == 1.6


@pytest.mark.parametrize("tuning", [False, True])
def test_reference_respects_global_tuning_switches_and_powertrain_overrides(monkeypatch, tuning):
  client, _ = _client(monkeypatch, {"CustomPersonalities": True, "LongitudinalTune": tuning, "AccelerationProfile": 2, "DecelerationProfile": 2, "EVTuning": False, "TruckTuning": True}, ev_tuning=True)
  curves = client.get("/api/personality_profiles").get_json()["reference_curves"]
  expected = get_accel_profile_curve_values(2 if tuning else 0, False, True)
  assert curves["standard"]["acceleration"] == [round(interpolate_accel_profile(speed * 0.44704, expected), 4) for speed in lpp.ACCELERATION_SPEEDS_MPH]
  assert curves["standard"]["braking"] == [2.0 if tuning else 0.5] * 10


@pytest.mark.parametrize("extra", [{"reset": "true"}, {"reset": 1}, {"reset": True, "preset": "eco"}, {"reset": True, "curve": [1.0] * 10}])
def test_malformed_reset_never_writes(monkeypatch, extra):
  client, params = _client(monkeypatch)
  response = client.put("/api/personality_profiles", json={"profile": "standard", "category": "acceleration", "preset": "custom", "curve": [], **extra})
  assert response.status_code == 400
  assert params.writes == []


def test_reset_obeys_offroad_and_stale_editor_guards(monkeypatch):
  client, params = _client(monkeypatch, {"IsOnroad": True})
  payload = {"profile": "standard", "category": "following", "preset": "custom", "curve": [], "reset": True}
  assert client.put("/api/personality_profiles", json=payload).status_code == 403
  assert params.writes == []
  params.values.update(IsOnroad=False, IsOffroad=True)
  payload["expected"] = {"preset": "custom", "curve": [1.0] * 10}
  assert client.put("/api/personality_profiles", json=payload).status_code == 409
  assert params.writes == []


@pytest.mark.parametrize("personality,category,values,expected", [
  ("traffic", "braking", {}, 0.35),
  ("standard", "acceleration", {"TruckTuning": True}, 6.0),
])
def test_first_custom_default_and_reset_keep_dom_points_outside_authoring_bounds(monkeypatch, personality, category, values, expected):
  client, params = _client(monkeypatch, {"CustomPersonalities": True, **values})
  endpoint = "/api/personality_profiles"
  payload = {"profile": personality, "category": category, "preset": "custom", "curve": []}
  response = client.put(endpoint, json=payload)
  assert response.status_code == 200
  config = response.get_json()["profiles"][personality][category]
  assert config["curve"][0] == expected
  original = deepcopy(config["curve"])
  # Editing one point retains the default-only values at the other points.
  edited = list(original)
  edited[-1] = 1.0
  response = client.put(endpoint, json={**payload, "curve": edited})
  assert response.status_code == 200
  assert response.get_json()["profiles"][personality][category]["curve"] == edited
  response = client.put(endpoint, json={**payload, "reset": True})
  assert response.status_code == 200
  assert response.get_json()["profiles"][personality][category]["curve"] == original
  invalid = list(original)
  invalid[0] = 0.4 if category == "braking" else 5.5
  before = deepcopy(params.values)
  assert client.put(endpoint, json={**payload, "curve": invalid}).status_code == 400
  assert params.values == before


def test_reset_retires_legacy_interpolation_even_if_display_points_match(monkeypatch):
  profiles = lpp.default_personality_profiles(False)
  profiles["standard"]["braking"] = {"preset": "custom", "curve": [0.5] * 10, "legacyCurve": [1.0] * 7}
  client, _ = _client(monkeypatch, {lpp.PERSONALITY_PROFILES_PARAM: lpp.profile_document(profiles, enabled=True)})
  result = client.put("/api/personality_profiles", json={"profile": "standard", "category": "braking", "preset": "custom", "curve": [], "reset": True})
  assert result.status_code == 200
  assert result.get_json()["profiles"]["standard"]["braking"] == {"preset": "custom", "curve": [0.5] * 10}


@pytest.mark.parametrize("enabled,low,high", [(True, 0.5, 1.1), (False, 0.75, 1.6)])
def test_traffic_following_defaults_honor_master_and_legacy_minimum(monkeypatch, enabled, low, high):
  client, _ = _client(monkeypatch, {"CustomPersonalities": enabled, "TrafficFollow": 0.5, "RelaxedFollow": 1.1})
  payload = {"profile": "traffic", "category": "following", "preset": "custom", "curve": [], "reset": True}
  result = client.put("/api/personality_profiles", json=payload)
  assert result.status_code == 200
  body = result.get_json()
  curve = body["profiles"]["traffic"]["following"]["curve"]
  assert curve == body["reference_curves"]["traffic"]["following"]
  assert (curve[0], curve[-1]) == (low, high)


def test_default_reference_uses_normal_gear_when_mapping_is_enabled(monkeypatch):
  client, _ = _client(monkeypatch, {"QOLLongitudinal": True, "MapGears": True, "MapAcceleration": True, "MapDeceleration": True, "LongitudinalTune": True, "AccelerationProfile": 2, "DecelerationProfile": 2})
  curves = client.get("/api/personality_profiles").get_json()["reference_curves"]
  expected = get_accel_profile_curve_values(0, False, False)
  assert curves["standard"]["acceleration"] == [round(interpolate_accel_profile(speed * 0.44704, expected), 4) for speed in lpp.ACCELERATION_SPEEDS_MPH]
  assert curves["standard"]["braking"] == [1.0] * 10
