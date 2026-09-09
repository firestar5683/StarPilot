"""Combined Flask setup with in-memory Params and temporary statistics only."""
from copy import deepcopy

import pytest
from test_personality_profiles_api import _client, the_galaxy
from openpilot.starpilot.common.longitudinal_personality_profiles import (
  PERSONALITY_PROFILES_PARAM, default_personality_profiles, profile_document,
)
from openpilot.starpilot.system.the_galaxy import model_stats_api


@pytest.mark.parametrize("target", ["chill", "experimental", "conditional_experimental", "conditional_chill"])
def test_combined_routes_keep_mode_profiles_and_statistics_independent(monkeypatch, tmp_path, target):
  register = model_stats_api.register_model_stats_api
  stats_path = tmp_path / "statistics.sqlite"
  monkeypatch.setattr(model_stats_api, "register_model_stats_api", lambda app: register(app, stats_path))
  monkeypatch.setattr(the_galaxy, "_get_longitudinal_mode_capable", lambda: True)
  document = profile_document(default_personality_profiles(False), enabled=True)
  client, params = _client(monkeypatch, {
    PERSONALITY_PROFILES_PARAM: document, "CustomPersonalities": True,
    "SafeMode": False, "ExperimentalModeConfirmed": True,
    "ExperimentalMode": False, "ConditionalExperimental": False, "ConditionalChill": False,
  })
  monkeypatch.setattr(params, "get_param_path", lambda: str(tmp_path / "params"), raising=False)
  # This exercises setup(app), not just separately extracted handler bodies.
  before_document = deepcopy(params.values[PERSONALITY_PROFILES_PARAM])
  before = client.get("/api/longitudinal_mode").get_json()
  assert client.get("/api/personality_profiles").status_code == 200
  assert client.get("/api/models/stats").status_code == 200
  assert not params.writes and not stats_path.exists()
  response = client.put("/api/longitudinal_mode", json={"mode": target, "expected": before["values"]})
  assert response.status_code == 200, response.get_json()
  assert client.get("/api/longitudinal_mode").get_json()["mode"] == target
  assert params.values[PERSONALITY_PROFILES_PARAM] == before_document
  mode_values = {key: params.values[key] for key in before["values"]}
  response = client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "acceleration", "preset": "custom", "curve": [],
  })
  assert response.status_code == 200, response.get_json()
  assert {key: params.values[key] for key in mode_values} == mode_values
  params.values["IsOnroad"] = True
  params.values["IsOffroad"] = False
  assert client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "acceleration", "preset": "standard", "curve": [],
  }).status_code == 200
  assert {key: params.values[key] for key in mode_values} == mode_values
  params.values["SafeMode"] = True
  writes = len(params.writes)
  assert client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "acceleration", "preset": "standard", "curve": [],
  }).status_code == 403
  assert len(params.writes) == writes
  assert client.get("/api/models/stats").status_code == 200
  assert client.post("/api/models/stats").status_code == 405
  assert not stats_path.exists()
