import json

import numpy as np
import pytest

from openpilot.starpilot.common.accel_profile import A_CRUISE_MAX_BP_CUSTOM, ACCELERATION_PROFILES, interpolate_accel_profile
from openpilot.starpilot.common.longitudinal_personality_profiles import (
  FOLLOWING_SPEEDS_MPH,
  PERSONALITY_ADVANCED_PARAM_KEYS,
  PERSONALITY_FOLLOW_PARAM_KEYS,
  PERSONALITY_PARKED_PARAM_KEYS,
  PERSONALITY_PROFILE_ENABLE_PARAM_KEYS,
  PERSONALITY_PROFILES_PARAM,
  PROFILE_SCHEMA_VERSION,
  default_personality_profiles,
  initial_custom_curve,
  migrate_profile_document,
  profile_document,
  strict_profile_document,
)
from test_navigation_params import _params_client, the_galaxy


def _client(monkeypatch, values=None, *, ev_tuning=False, truck_tuning=False):
  device_values = dict(values or {})
  device_values.setdefault("IsOnroad", False)
  device_values.setdefault("IsOffroad", not device_values["IsOnroad"])
  client, params = _params_client(monkeypatch, device_values, "tici")
  personality_keys = set(PERSONALITY_PARKED_PARAM_KEYS)
  personality_bool_keys = set(PERSONALITY_PROFILE_ENABLE_PARAM_KEYS) | {"CustomPersonalities"}
  base_types = {"AlphaLongitudinalEnabled": bool, "ForceOffroad": bool, "FordLateralMode": int}
  monkeypatch.setattr(
    the_galaxy, "_get_param_type_info",
    lambda: (
      set(base_types) | personality_keys,
      base_types | dict.fromkeys(personality_bool_keys, bool)
      | dict.fromkeys(personality_keys - personality_bool_keys, float),
    ),
  )
  monkeypatch.setattr(the_galaxy, "_get_detected_ev_tuning", lambda: ev_tuning)
  monkeypatch.setattr(the_galaxy, "_get_detected_truck_tuning", lambda: truck_tuning, raising=False)
  monkeypatch.setattr(the_galaxy, "_safe_params_get_live_raw", lambda key, default=None, block=False: params.values.get(key, default))
  return client, params


def _slot_client(monkeypatch, tmp_path, settings, values=None):
  client, params = _client(monkeypatch, values)
  types = {key: the_galaxy.ParamKeyType.BOOL if key == "CustomPersonalities" else the_galaxy.ParamKeyType.FLOAT
           for key in settings}
  monkeypatch.setattr(params, "get_type", lambda key: types[key], raising=False)
  monkeypatch.setattr(the_galaxy, "_params_raw", params)
  monkeypatch.setattr(the_galaxy, "TOGGLE_BACKUPS", tmp_path)
  monkeypatch.setattr(the_galaxy, "_get_toggle_backup_keys", lambda: set(settings))
  monkeypatch.setattr(the_galaxy, "update_starpilot_toggles", lambda: None)
  (tmp_path / ".params-profile-a.json").write_text(json.dumps({
    "format": the_galaxy.param_profiles.PROFILE_FORMAT, "version": 1, "slot": "a",
    "settings": {key: {"type": int(types[key]), "value": value} for key, value in settings.items()},
  }))
  return client, params


@pytest.mark.parametrize("state", [{"IsOnroad": True}, {"IsOffroad": False}, {"IsOffroad": None}])
def test_slot_load_requires_confirmed_offroad(monkeypatch, tmp_path, state):
  client, params = _slot_client(monkeypatch, tmp_path, {"UnrelatedSetting": 2.0}, state)
  assert client.post("/api/toggles/profiles/a/load").status_code == 403
  assert params.writes == []


def test_slot_load_rechecks_offroad_after_acquiring_shared_lock(monkeypatch, tmp_path):
  client, params = _slot_client(monkeypatch, tmp_path, {"UnrelatedSetting": 2.0})

  class StateChangingLock:
    def __enter__(self):
      params.values["IsOffroad"] = False

    def __exit__(self, *args):
      pass

  monkeypatch.setattr(the_galaxy, "_PERSONALITY_PROFILES_WRITE_LOCK", StateChangingLock())
  assert client.post("/api/toggles/profiles/a/load").status_code == 403
  assert params.writes == []


def test_slot_load_preserves_native_types_renames_and_skips(monkeypatch, tmp_path):
  from datetime import datetime

  client, params = _slot_client(monkeypatch, tmp_path, {"BytesSetting": 0, "TimeSetting": 0, "ChangedSetting": 0})
  types = {"BytesSetting": the_galaxy.ParamKeyType.BYTES, "TimeSetting": the_galaxy.ParamKeyType.TIME,
           "ChangedSetting": the_galaxy.ParamKeyType.BOOL}
  monkeypatch.setattr(params, "get_type", lambda key: types[key])
  monkeypatch.setattr(the_galaxy, "LEGACY_STARPILOT_PARAM_RENAMES", {"OldBytesSetting": "BytesSetting"})
  path = tmp_path / ".params-profile-a.json"
  payload = json.loads(path.read_text())
  payload["settings"] = {
    "OldBytesSetting": {"type": int(types["BytesSetting"]), "value": "AP8="},
    "TimeSetting": {"type": int(types["TimeSetting"]), "value": "2026-01-01T00:00:00+00:00"},
    "ChangedSetting": {"type": int(the_galaxy.ParamKeyType.FLOAT), "value": 2.0},
    "UnavailableSetting": {"type": int(the_galaxy.ParamKeyType.FLOAT), "value": 3.0},
  }
  path.write_text(json.dumps(payload))
  response = client.post("/api/toggles/profiles/a/load")
  assert response.status_code == 200
  assert response.get_json()["restoredCount"] == 2
  assert response.get_json()["skippedCount"] == 2
  assert params.values["BytesSetting"] == b"\x00\xff"
  assert params.values["TimeSetting"] == datetime.fromisoformat("2026-01-01T00:00:00+00:00")
  assert {key for key, _ in params.writes} == {"BytesSetting", "TimeSetting"}


@pytest.mark.parametrize("key,value", [
  ("CustomPersonalities", "true"),
  (sorted(PERSONALITY_ADVANCED_PARAM_KEYS)[0], 200.1),
  (sorted(PERSONALITY_FOLLOW_PARAM_KEYS)[0], 99),
])
def test_slot_load_validates_personality_before_any_writes(monkeypatch, tmp_path, key, value):
  client, params = _slot_client(monkeypatch, tmp_path, {"UnrelatedSetting": 2.0, key: value})
  assert client.post("/api/toggles/profiles/a/load").status_code == 400
  assert params.writes == []


@pytest.mark.parametrize("enabled", [False, True])
def test_slot_load_rejects_incompatible_document_before_any_writes(monkeypatch, tmp_path, enabled):
  client, params = _slot_client(monkeypatch, tmp_path, {"UnrelatedSetting": 2.0, "CustomPersonalities": enabled}, {
    PERSONALITY_PROFILES_PARAM: {"schemaVersion": 99},
  })
  assert client.post("/api/toggles/profiles/a/load").status_code == 409
  assert params.writes == []


@pytest.mark.parametrize("enabled", [False, True])
def test_slot_load_syncs_master_preserves_historical_curves_under_shared_lock(monkeypatch, tmp_path, enabled):
  profiles = default_personality_profiles(False)
  profiles["aggressive"]["acceleration"] = {"preset": "custom", "curve": [6.0] * 10}
  client, params = _slot_client(monkeypatch, tmp_path, {"UnrelatedSetting": 2.0, "CustomPersonalities": enabled}, {
    PERSONALITY_PROFILES_PARAM: profile_document(profiles, enabled=not enabled),
  })
  original_put = params.put
  original_put_bool = params.put_bool

  def locked_put(key, value):
    assert the_galaxy._PERSONALITY_PROFILES_WRITE_LOCK.locked()
    original_put(key, value)

  def locked_put_bool(key, value):
    assert the_galaxy._PERSONALITY_PROFILES_WRITE_LOCK.locked()
    original_put_bool(key, value)

  monkeypatch.setattr(params, "put", locked_put)
  monkeypatch.setattr(params, "put_bool", locked_put_bool)
  response = client.post("/api/toggles/profiles/a/load")
  assert response.status_code == 200
  assert response.get_json()["restoredCount"] == 2
  assert response.get_json()["slot"] == "a"
  assert params.values["CustomPersonalities"] is enabled
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert document is not None
  assert document["enabled"] is enabled
  assert document["profiles"] == profiles
  assert params.values["UnrelatedSetting"] == 2.0


@pytest.mark.parametrize("value", [3.51, 4.0, 5.0, 6.0])
def test_saved_v2_high_curve_read_migrate_edit_and_master_round_trip(monkeypatch, value):
  profiles = default_personality_profiles(False)
  profiles["aggressive"]["acceleration"] = {"preset": "custom", "curve": [value] * 10}
  raw = json.dumps(profile_document(profiles, enabled=True))
  client, params = _client(monkeypatch, {PERSONALITY_PROFILES_PARAM: raw, "CustomPersonalities": True})

  response = client.get("/api/personality_profiles")
  assert response.status_code == 200
  assert response.get_json()["profiles"] == profiles
  assert response.get_json()["bounds"]["acceleration"] == [0.0, 3.5]
  assert response.get_json()["migration_required"] is False
  assert client.post("/api/personality_profiles/migrate").status_code == 200
  assert params.values[PERSONALITY_PROFILES_PARAM] == raw
  assert params.writes == []

  assert client.put("/api/personality_profiles", json={
    "profile": "relaxed", "category": "braking", "preset": "eco", "curve": [],
  }).status_code == 200
  stored = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert stored is not None
  assert stored["profiles"]["aggressive"] == profiles["aggressive"]
  curve = [3.0] + [value] * 9
  response = client.put("/api/personality_profiles", json={
    "profile": "aggressive", "category": "acceleration", "preset": "custom", "curve": curve,
  })
  assert response.status_code == 200
  assert response.get_json()["profiles"]["aggressive"]["acceleration"]["curve"] == curve
  for enabled in (False, True):
    assert client.put("/api/params", json={"key": "CustomPersonalities", "value": enabled}).status_code == 200
    stored = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
    assert stored is not None
    assert stored["enabled"] is enabled
    assert stored["profiles"]["aggressive"]["acceleration"]["curve"] == curve
  before = json.dumps(params.values, sort_keys=True)
  writes = list(params.writes)
  assert client.put("/api/personality_profiles", json={
    "profile": "aggressive", "category": "acceleration", "preset": "custom", "curve": [value] * 10,
  }).status_code == 400
  assert json.dumps(params.values, sort_keys=True) == before
  assert params.writes == writes


@pytest.mark.parametrize("state", [{"IsOnroad": True}, {"IsOnroad": False, "IsOffroad": False}])
def test_saved_v2_high_curve_never_bypasses_parked_write_guard(monkeypatch, state):
  profiles = default_personality_profiles(False)
  profiles["aggressive"]["acceleration"] = {"preset": "custom", "curve": [6.0] * 10}
  raw = json.dumps(profile_document(profiles, enabled=True))
  client, params = _client(monkeypatch, {PERSONALITY_PROFILES_PARAM: raw, **state})
  assert client.get("/api/personality_profiles").status_code == 200
  assert client.put("/api/personality_profiles", json={
    "profile": "aggressive", "category": "acceleration", "preset": "custom", "curve": [3.0] + [6.0] * 9,
  }).status_code == 403
  assert client.post("/api/personality_profiles/migrate").status_code == 403
  assert client.put("/api/params", json={"key": "CustomPersonalities", "value": False}).status_code == 403
  assert params.values[PERSONALITY_PROFILES_PARAM] == raw
  assert params.writes == []


def test_get_returns_disabled_standard_defaults_and_explicit_graph_metadata(monkeypatch):
  client, _ = _client(monkeypatch)
  response = client.get("/api/personality_profiles")
  assert response.status_code == 200
  body = response.get_json()
  assert body["schema_version"] == PROFILE_SCHEMA_VERSION
  assert body["configured"] is False
  assert body["profiles"] == default_personality_profiles(False)
  assert set(body["options"]) == {"acceleration", "braking", "following"}
  assert set(body["speed_breakpoints_mph"]) == {"acceleration", "braking", "following"}
  for speeds in body["speed_breakpoints_mph"].values():
    assert speeds == list(FOLLOWING_SPEEDS_MPH)
  assert body["reference_curves"]["aggressive"]["following"] == [1.25] * 10
  assert body["reference_curves"]["standard"]["following"] == [1.45] * 10


def test_legacy_master_without_document_remains_enabled_when_first_profile_is_saved(monkeypatch):
  client, params = _client(monkeypatch, {"IsOnroad": False, "CustomPersonalities": True})

  readback = client.get("/api/personality_profiles").get_json()
  response = client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "acceleration", "preset": "eco", "curve": [],
  })

  assert readback["enabled"] is True
  assert response.status_code == 200
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert document is not None and document["enabled"] is True


def test_first_save_persists_one_atomic_versioned_document_with_other_categories_standard(monkeypatch):
  client, params = _client(monkeypatch)
  response = client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "braking", "preset": "sport", "curve": [2.0] * 10,
  })
  assert response.status_code == 200
  stored = params.values[PERSONALITY_PROFILES_PARAM]
  document = strict_profile_document(stored)
  assert document is not None and document["enabled"] is False
  assert document["profiles"]["standard"]["braking"]["preset"] == "sport"
  for profile_id, profile in document["profiles"].items():
    for category, config in profile.items():
      if (profile_id, category) != ("standard", "braking"):
        assert config == {
          "preset": "medium" if category == "following" else "standard", "curve": [],
        }
  assert len([write for write in params.writes if write[0] == PERSONALITY_PROFILES_PARAM]) == 1


def test_profile_read_modify_write_endpoint_is_serialized():
  source = (the_galaxy.Path(the_galaxy.__file__)).read_text(encoding="utf-8")
  endpoint = source.split('@app.route("/api/personality_profiles"', 1)[1].split('@app.route(', 1)[0]
  serializer = source.split("def _serialize_personality_profile_writes", 1)[1].split("\n\ndef ", 1)[0]
  assert "@_serialize_personality_profile_writes" in endpoint
  assert 'request.method not in ("PUT", "POST")' in serializer


def test_selecting_custom_is_seeded_server_side_from_current_ev_preset_with_ev_over_truck(monkeypatch):
  profiles = default_personality_profiles(False)
  profiles["aggressive"]["acceleration"] = {"preset": "sport", "curve": []}
  stored = profile_document(profiles, enabled=True)
  client, params = _client(monkeypatch, {
    "IsOnroad": False, "TruckTuning": True, PERSONALITY_PROFILES_PARAM: stored,
  }, ev_tuning=True)

  response = client.put("/api/personality_profiles", json={
    "profile": "aggressive", "category": "acceleration", "preset": "custom", "curve": [0.0] * 10,
  })

  assert response.status_code == 200
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert document["profiles"]["aggressive"]["acceleration"] == {
    "preset": "custom",
    "curve": initial_custom_curve(
      "acceleration", {"preset": "sport", "curve": []}, ev_tuning=True, truck_tuning=False,
    ),
  }


def test_selecting_custom_uses_the_automatically_detected_truck_curve(monkeypatch):
  profiles = default_personality_profiles(False)
  profiles["aggressive"]["acceleration"] = {"preset": "sport", "curve": []}
  client, params = _client(monkeypatch, {
    "IsOnroad": False,
    PERSONALITY_PROFILES_PARAM: profile_document(profiles, enabled=True),
  }, truck_tuning=True)
  assert the_galaxy._get_detected_truck_tuning() is True
  original_initializer = the_galaxy.initial_custom_curve
  observed = {}

  def capture_initializer(category, current_config, ev_tuning, truck_tuning, *, legacy_curve=None):
    curve = original_initializer(category, current_config, ev_tuning, truck_tuning, legacy_curve=legacy_curve)
    observed.update(ev_tuning=ev_tuning, truck_tuning=truck_tuning, curve=curve)
    return curve

  monkeypatch.setattr(the_galaxy, "initial_custom_curve", capture_initializer)
  response = client.put("/api/personality_profiles", json={
    "profile": "aggressive", "category": "acceleration", "preset": "custom", "curve": [],
  })

  assert response.status_code == 200
  assert observed["ev_tuning"] is False
  assert observed["truck_tuning"] is True
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert document is not None
  assert document["profiles"]["aggressive"]["acceleration"]["curve"] == observed["curve"]


def test_custom_braking_is_seeded_from_selected_deceleration_preset(monkeypatch):
  profiles = default_personality_profiles(False)
  profiles["relaxed"]["braking"] = {"preset": "eco", "curve": []}
  client, params = _client(monkeypatch, {
    "IsOnroad": False, PERSONALITY_PROFILES_PARAM: profile_document(profiles, enabled=True),
  })
  response = client.put("/api/personality_profiles", json={
    "profile": "relaxed", "category": "braking", "preset": "custom", "curve": [2.0] * 10,
  })
  assert response.status_code == 200
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert document["profiles"]["relaxed"]["braking"] == {"preset": "custom", "curve": [0.5] * 10}


def test_dom_default_custom_acceleration_seeds_from_effective_legacy_custom_curve(monkeypatch):
  profiles = default_personality_profiles(False)
  profiles["traffic"]["acceleration"] = {"preset": "dom_default", "curve": []}
  values = {
    "IsOnroad": False,
    "CustomAccelProfile": True,
    "CustomAccelProfileInitialized": True,
    PERSONALITY_PROFILES_PARAM: profile_document(profiles, enabled=False),
    **{
      f"CustomAccelProfile{mph}MPH": value
      for mph, value in zip((0, 11, 22, 34, 45, 56, 89), (1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5), strict=True)
    },
  }
  client, params = _client(monkeypatch, values)
  response = client.put("/api/personality_profiles", json={
    "profile": "traffic", "category": "acceleration", "preset": "custom", "curve": [3.5] * 10,
  })
  assert response.status_code == 200
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  expected = [
    round(interpolate_accel_profile(speed * 0.44704, [1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5], A_CRUISE_MAX_BP_CUSTOM), 4)
    for speed in FOLLOWING_SPEEDS_MPH
  ]
  assert document["profiles"]["traffic"]["acceleration"]["curve"] == expected


def test_existing_custom_category_persists_subsequent_graph_edits_exactly(monkeypatch):
  profiles = default_personality_profiles(False)
  profiles["standard"]["acceleration"] = {"preset": "custom", "curve": [1.0] * 10}
  client, params = _client(monkeypatch, {
    "IsOnroad": False, PERSONALITY_PROFILES_PARAM: profile_document(profiles, enabled=True),
  })
  edited = [round(1.0 + 0.1 * index, 4) for index in range(10)]
  response = client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "acceleration", "preset": "custom", "curve": edited,
  })
  assert response.status_code == 200
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert document["profiles"]["standard"]["acceleration"]["curve"] == edited


def test_dom_default_custom_seed_resamples_valid_dynamic_curve_and_malformed_dynamic_falls_back(monkeypatch):
  profiles = default_personality_profiles(False)
  profiles["standard"]["acceleration"] = {"preset": "dom_default", "curve": []}
  dynamic = {
    "IsOnroad": False,
    "CustomAccelProfile": True,
    PERSONALITY_PROFILES_PARAM: profile_document(profiles, enabled=False),
    "CustomAccelProfileBreakpointsInitialized": True,
    "CustomAccelProfilePointCount": 3,
    "CustomAccelProfileBreakpoint1MPH": 0,
    "CustomAccelProfileBreakpoint2MPH": 40,
    "CustomAccelProfileBreakpoint3MPH": 90,
    "CustomAccelProfilePoint1Accel": 1.0,
    "CustomAccelProfilePoint2Accel": 2.0,
    "CustomAccelProfilePoint3Accel": 3.0,
  }
  client, params = _client(monkeypatch, dynamic)
  response = client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "acceleration", "preset": "custom", "curve": [0.0] * 10,
  })
  assert response.status_code == 200
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  dynamic_axis_ms = np.array([0.0, 40.0, 90.0]) * 0.44704
  expected = [
    round(interpolate_accel_profile(speed * 0.44704, [1.0, 2.0, 3.0], dynamic_axis_ms), 4)
    for speed in FOLLOWING_SPEEDS_MPH
  ]
  assert document["profiles"]["standard"]["acceleration"]["curve"] == expected

  malformed_client, malformed_params = _client(monkeypatch, {
    **dynamic, "CustomAccelProfilePointCount": 3.5, "AccelerationProfile": ACCELERATION_PROFILES["ECO"],
  })
  response = malformed_client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "acceleration", "preset": "custom", "curve": [3.5] * 10,
  })
  assert response.status_code == 200
  document = strict_profile_document(malformed_params.values[PERSONALITY_PROFILES_PARAM])
  assert document["profiles"]["standard"]["acceleration"]["curve"] == initial_custom_curve(
    "acceleration", {"preset": "eco", "curve": []}, False, False,
  )


def test_following_custom_seeds_from_legacy_profile_and_then_persists_edits(monkeypatch):
  profiles = default_personality_profiles(False)
  profiles["standard"]["following"] = {"preset": "dom_default", "curve": []}
  client, params = _client(monkeypatch, {
    "IsOnroad": False,
    "CustomPersonalities": True,
    PERSONALITY_PROFILES_PARAM: profile_document(profiles, enabled=True),
    "StandardFollow": 1.4,
    "StandardFollowHigh": 1.1,
  })
  response = client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "following", "preset": "custom", "curve": [3.0] * 10,
  })
  assert response.status_code == 200
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  expected = [round(float(value), 4) for value in np.interp(FOLLOWING_SPEEDS_MPH, [45.0, 70.0], [1.4, 1.1])]
  assert document["profiles"]["standard"]["following"] == {"preset": "custom", "curve": expected}

  edited = [0.75 + index * 0.1 for index in range(10)]
  response = client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "following", "preset": "custom", "curve": edited,
  })
  assert response.status_code == 200
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert document["profiles"]["standard"]["following"]["curve"] == [round(value, 4) for value in edited]


def test_fresh_following_custom_seeds_from_selected_medium_even_when_legacy_custom_is_off(monkeypatch):
  client, params = _client(monkeypatch, {
    "IsOnroad": False,
    "CustomPersonalities": False,
    "RelaxedFollow": 1.1,
    "RelaxedFollowHigh": 0.9,
  })
  response = client.put("/api/personality_profiles", json={
    "profile": "relaxed", "category": "following", "preset": "custom", "curve": [],
  })
  assert response.status_code == 200
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert document["profiles"]["relaxed"]["following"]["curve"] == [1.45] * len(FOLLOWING_SPEEDS_MPH)


def test_traffic_following_seed_matches_legacy_runtime_speed_units(monkeypatch):
  profiles = default_personality_profiles(False)
  profiles["traffic"]["following"] = {"preset": "dom_default", "curve": []}
  client, params = _client(monkeypatch, {
    "IsOnroad": False,
    PERSONALITY_PROFILES_PARAM: profile_document(profiles, enabled=False),
    "TrafficFollow": 0.8,
    "RelaxedFollow": 1.6,
  })
  response = client.put("/api/personality_profiles", json={
    "profile": "traffic", "category": "following", "preset": "custom", "curve": [],
  })

  assert response.status_code == 200
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  expected = [
    round(float(value), 4)
    for value in np.interp(np.array(FOLLOWING_SPEEDS_MPH) * 0.44704, [0.0, 25.0], [0.8, 1.6])
  ]
  assert document["profiles"]["traffic"]["following"]["curve"] == expected


def test_invalid_payload_never_writes(monkeypatch):
  client, params = _client(monkeypatch)
  for payload in (
    {"profile": "standard", "category": "braking", "preset": "custom", "curve": [True] * 10},
    {"profile": "standard", "category": "following", "preset": "custom", "curve": [0.74] * 10},
  ):
    response = client.put("/api/personality_profiles", json=payload)
    assert response.status_code == 400
  assert PERSONALITY_PROFILES_PARAM not in params.values


def test_api_exposes_and_enforces_requested_acceleration_and_braking_bounds(monkeypatch):
  client, params = _client(monkeypatch, {"IsOnroad": False})
  bounds = client.get("/api/personality_profiles").get_json()["bounds"]
  assert bounds["acceleration"] == [0.0, 3.5]
  assert bounds["braking"] == [0.5, 2.0]

  accepted = client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "braking", "preset": "custom", "curve": [2.0] * 10,
  })
  assert accepted.status_code == 200
  stored = params.values[PERSONALITY_PROFILES_PARAM]

  rejected = client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "acceleration", "preset": "custom", "curve": [3.51] * 10,
  })
  assert rejected.status_code == 400
  assert params.values[PERSONALITY_PROFILES_PARAM] == stored


@pytest.mark.parametrize("device_state", [
  {"IsOnroad": True, "IsOffroad": False},
  {"IsOnroad": False, "IsOffroad": False},
])
def test_dedicated_and_generic_profile_mutations_require_confirmed_offroad(monkeypatch, device_state):
  original = profile_document(default_personality_profiles(False), enabled=False)
  client, params = _client(monkeypatch, {**device_state, PERSONALITY_PROFILES_PARAM: original})
  before = json.loads(json.dumps(params.values))

  dedicated = client.put("/api/personality_profiles", json={
    "profile": "traffic", "category": "acceleration", "preset": "eco", "curve": [1.0] * 7,
  })
  generic = client.put("/api/params", json={"key": PERSONALITY_PROFILES_PARAM, "value": {"enabled": True}})
  legacy_parent = client.put("/api/params", json={"key": "CustomPersonalities", "value": True})

  assert dedicated.status_code == 403
  assert generic.status_code == 403
  assert legacy_parent.status_code == 403
  assert "parked" in legacy_parent.get_json()["error"].lower()
  assert params.values == before


def test_generic_profile_mutation_is_also_rejected_while_parked(monkeypatch):
  client, params = _client(monkeypatch, {"IsOnroad": False})
  response = client.put("/api/params", json={"key": PERSONALITY_PROFILES_PARAM, "value": {"enabled": True}})
  assert response.status_code == 403
  assert PERSONALITY_PROFILES_PARAM not in params.values


def test_dedicated_enable_mutation_is_rejected(monkeypatch):
  client, params = _client(monkeypatch, {"IsOnroad": False})
  response = client.put("/api/personality_profiles", json={"enabled": True})
  assert response.status_code == 400
  assert PERSONALITY_PROFILES_PARAM not in params.values


def test_enabling_master_without_document_creates_standard_medium_defaults(monkeypatch):
  client, params = _client(monkeypatch, {"IsOnroad": False})

  response = client.put("/api/params", json={"key": "CustomPersonalities", "value": True})

  assert response.status_code == 200
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert document is not None
  assert document["enabled"] is True
  assert document["profiles"] == default_personality_profiles(False)


def test_master_toggle_synchronises_the_profile_document_enable_bit(monkeypatch):
  original = profile_document(default_personality_profiles(False), enabled=False)
  client, params = _client(monkeypatch, {
    "IsOnroad": False, "CustomPersonalities": False, PERSONALITY_PROFILES_PARAM: original,
  })

  response = client.put("/api/params", json={"key": "CustomPersonalities", "value": True})

  assert response.status_code == 200
  assert params.get_bool("CustomPersonalities") is True
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert document is not None and document["enabled"] is True


@pytest.mark.parametrize(("enabled", "expected_order"), [
  (True, [PERSONALITY_PROFILES_PARAM, "CustomPersonalities"]),
  (False, ["CustomPersonalities", PERSONALITY_PROFILES_PARAM]),
])
def test_master_toggle_writes_in_fail_closed_order(monkeypatch, enabled, expected_order):
  original = profile_document(default_personality_profiles(False), enabled=not enabled)
  client, params = _client(monkeypatch, {
    "IsOnroad": False, "CustomPersonalities": not enabled, PERSONALITY_PROFILES_PARAM: original,
  })

  response = client.put("/api/params", json={"key": "CustomPersonalities", "value": enabled})

  assert response.status_code == 200
  assert [key for key, _ in params.writes] == expected_order


def test_profile_document_write_failure_never_enables_master(monkeypatch):
  original = profile_document(default_personality_profiles(False), enabled=False)
  client, params = _client(monkeypatch, {
    "IsOnroad": False, "CustomPersonalities": False, PERSONALITY_PROFILES_PARAM: original,
  })
  original_put = params.put

  def fail_profile_document_write(key, value):
    if key == PERSONALITY_PROFILES_PARAM:
      raise OSError("injected profile document write failure")
    original_put(key, value)

  monkeypatch.setattr(params, "put", fail_profile_document_write)

  response = client.put("/api/params", json={"key": "CustomPersonalities", "value": True})

  assert response.status_code == 500
  assert params.get_bool("CustomPersonalities") is False
  assert params.values[PERSONALITY_PROFILES_PARAM] == original


def test_unverified_profile_document_write_never_enables_master(monkeypatch):
  client, params = _client(monkeypatch, {"IsOnroad": False, "CustomPersonalities": False})
  monkeypatch.setattr(the_galaxy, "_safe_params_get_live_raw", lambda key, default=None, block=False: None)

  response = client.put("/api/params", json={"key": "CustomPersonalities", "value": True})

  assert response.status_code == 500
  assert params.get_bool("CustomPersonalities") is False
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert document is not None and document["enabled"] is True


def test_master_write_failure_leaves_master_false_after_verified_document_write(monkeypatch):
  original = profile_document(default_personality_profiles(False), enabled=False)
  client, params = _client(monkeypatch, {
    "IsOnroad": False, "CustomPersonalities": False, PERSONALITY_PROFILES_PARAM: original,
  })
  original_put_bool = params.put_bool

  def fail_master_write(key, value):
    if key == "CustomPersonalities":
      raise OSError("injected master write failure")
    original_put_bool(key, value)

  monkeypatch.setattr(params, "put_bool", fail_master_write)

  response = client.put("/api/params", json={"key": "CustomPersonalities", "value": True})

  assert response.status_code == 500
  assert params.get_bool("CustomPersonalities") is False
  document = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert document is not None and document["enabled"] is True


def test_every_state_affecting_personality_write_is_rejected_onroad(monkeypatch):
  client, params = _client(monkeypatch, {"IsOnroad": True})
  before = json.loads(json.dumps(params.values))

  for key in PERSONALITY_PARKED_PARAM_KEYS:
    value = False if key in PERSONALITY_PROFILE_ENABLE_PARAM_KEYS or key == "CustomPersonalities" else 50
    response = client.put("/api/params", json={"key": key, "value": value})
    assert response.status_code == 403, key
  assert params.values == before


def test_every_state_affecting_personality_write_is_rejected_until_offroad_is_confirmed(monkeypatch):
  client, params = _client(monkeypatch, {"IsOnroad": False, "IsOffroad": False})
  before = json.loads(json.dumps(params.values))

  for key in PERSONALITY_PARKED_PARAM_KEYS:
    value = False if key in PERSONALITY_PROFILE_ENABLE_PARAM_KEYS or key == "CustomPersonalities" else 50
    response = client.put("/api/params", json={"key": key, "value": value})
    assert response.status_code == 403, key
  assert params.values == before


@pytest.mark.parametrize("device_state", [
  {"IsOnroad": True, "IsOffroad": False},
  {"IsOnroad": False, "IsOffroad": False},
])
def test_reset_defaults_requires_confirmed_offroad_without_side_effects(monkeypatch, device_state):
  personality_key = "StandardJerkAcceleration"
  client, params = _client(monkeypatch, {**device_state, personality_key: 99.0})
  monkeypatch.setattr(params, "all_keys", lambda: [personality_key], raising=False)
  monkeypatch.setattr(params, "get_default_value", lambda key: 50.0, raising=False)
  monkeypatch.setattr(the_galaxy, "_params_raw", params)
  toggle_updates = []
  reboots = []
  monkeypatch.setattr(the_galaxy, "update_starpilot_toggles", lambda: toggle_updates.append(True))
  monkeypatch.setattr(the_galaxy.HARDWARE, "reboot", lambda: reboots.append(True))
  before = json.loads(json.dumps(params.values))

  response = client.post("/api/toggles/reset_default")

  assert response.status_code == 403
  assert params.values == before
  assert params.writes == []
  assert toggle_updates == []
  assert reboots == []


@pytest.mark.parametrize("device_state", [
  {"IsOnroad": True, "IsOffroad": False},
  {"IsOnroad": False, "IsOffroad": False},
])
def test_troubleshoot_reset_skips_every_parked_personality_key_without_confirmed_offroad(monkeypatch, device_state):
  boolean_keys = set(PERSONALITY_PROFILE_ENABLE_PARAM_KEYS) | {"CustomPersonalities"}
  original_values = {
    key: True if key in boolean_keys else 99.0
    for key in PERSONALITY_PARKED_PARAM_KEYS
  }
  client, params = _client(monkeypatch, {**device_state, **original_values})
  monkeypatch.setattr(the_galaxy, "_get_default_param_values", lambda: {
    key: False if key in boolean_keys else 50.0
    for key in PERSONALITY_PARKED_PARAM_KEYS
  })
  before = json.loads(json.dumps(params.values))

  response = client.post("/api/troubleshoot/reset", json={"sectionId": "personality_settings"})

  assert response.status_code == 200
  body = response.get_json()
  skipped_by_key = {item["key"]: item["reason"] for item in body["skippedKeys"]}
  assert set(skipped_by_key) == set(PERSONALITY_PARKED_PARAM_KEYS)
  for key in set(PERSONALITY_ADVANCED_PARAM_KEYS) | set(PERSONALITY_FOLLOW_PARAM_KEYS):
    assert skipped_by_key[key] == "blocked until required off-road state is confirmed"
  assert body["updatedKeys"] == []
  assert body["updatedCount"] == 0
  assert body["skippedCount"] == len(PERSONALITY_PARKED_PARAM_KEYS)
  assert params.values == before
  assert params.writes == []


@pytest.mark.parametrize("key", sorted(PERSONALITY_ADVANCED_PARAM_KEYS))
def test_advanced_personality_values_require_numbers_in_supported_range(monkeypatch, key):
  client, params = _client(monkeypatch, {"IsOnroad": False})
  for invalid in (True, "50", 24.9, 200.1):
    assert client.put("/api/params", json={"key": key, "value": invalid}).status_code == 400
  assert key not in params.values

  assert client.put("/api/params", json={"key": key, "value": 50}).status_code == 200
  assert float(params.values[key]) == 50.0


def test_legacy_follow_values_require_numbers_in_supported_range(monkeypatch):
  client, params = _client(monkeypatch, {"IsOnroad": False})
  key = "AggressiveFollow"
  for invalid in (True, "1.25", 0.49, 3.01):
    assert client.put("/api/params", json={"key": key, "value": invalid}).status_code == 400
  assert key not in params.values

  assert client.put("/api/params", json={"key": key, "value": 1.25}).status_code == 200
  assert float(params.values[key]) == 1.25


@pytest.mark.parametrize("key", sorted(PERSONALITY_PROFILE_ENABLE_PARAM_KEYS))
@pytest.mark.parametrize("invalid_value", ["true", 1, 1.0, [True], {"enabled": True}, None])
def test_profile_enable_params_require_json_booleans(monkeypatch, key, invalid_value):
  client, params = _client(monkeypatch, {"IsOnroad": False})

  response = client.put("/api/params", json={"key": key, "value": invalid_value})

  assert response.status_code == 400
  assert "boolean" in response.get_json()["error"].lower()
  assert key not in params.values


def test_master_toggle_rejects_malformed_profile_document_without_mutation(monkeypatch):
  malformed = {"schemaVersion": 99}
  client, params = _client(monkeypatch, {
    "IsOnroad": False, "CustomPersonalities": False, PERSONALITY_PROFILES_PARAM: malformed,
  })

  response = client.put("/api/params", json={"key": "CustomPersonalities", "value": True})

  assert response.status_code == 409
  assert params.get_bool("CustomPersonalities") is False
  assert params.values[PERSONALITY_PROFILES_PARAM] == malformed


def _known_v1_document():
  legacy = profile_document(default_personality_profiles(False), enabled=True)
  legacy["schemaVersion"] = 1
  legacy["axes"] = {
    "acceleration": {
      "speed": {"unit": "mph", "values": [0.0, 11.184681, 22.369363, 33.554044, 44.738726, 55.923407, 89.477452]},
      "value": {"unit": "m/s^2", "meaning": "maximum_requested_acceleration"},
    },
    "braking": {
      "speed": {"unit": "mph", "values": [0.0, 11.184681, 22.369363, 33.554044, 44.738726, 55.923407, 89.477452]},
      "value": {"unit": "m/s^2", "meaning": "cruise_slc_deceleration_magnitude"},
    },
    "following": {"speed": {"unit": "mph", "values": list(range(0, 91, 10))}, "value": {"unit": "s", "meaning": "base_time_headway"}},
  }
  legacy["profiles"]["standard"]["acceleration"] = {"preset": "custom", "curve": [1.0] * 7}
  return legacy


def test_known_v1_document_is_migrated_for_readback(monkeypatch):
  legacy = _known_v1_document()
  client, _ = _client(monkeypatch, {"IsOnroad": False, PERSONALITY_PROFILES_PARAM: legacy})

  body = client.get("/api/personality_profiles").get_json()

  assert body["configured"] is True
  assert body["migration_required"] is True
  assert body["schema_version"] == 2
  assert len(body["profiles"]["standard"]["acceleration"]["curve"]) == 10
  assert body["profiles"]["standard"]["acceleration"]["legacyCurve"] == [1.0] * 7


def test_known_v1_document_can_be_installed_by_explicit_offroad_migration(monkeypatch):
  legacy = _known_v1_document()
  client, params = _client(monkeypatch, {
    "IsOnroad": False,
    "IsOffroad": True,
    "CustomPersonalities": True,
    PERSONALITY_PROFILES_PARAM: legacy,
  })

  response = client.post("/api/personality_profiles/migrate")

  assert response.status_code == 200
  stored = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert stored is not None
  assert stored["enabled"] is True
  assert stored["profiles"]["standard"]["acceleration"]["legacyCurve"] == [1.0] * 7
  assert len([write for write in params.writes if write[0] == PERSONALITY_PROFILES_PARAM]) == 1


def test_verified_v2_migration_remains_editable_and_preserves_other_legacy_curves(monkeypatch):
  migrated = migrate_profile_document(_known_v1_document())
  assert migrated is not None
  client, params = _client(monkeypatch, {"IsOnroad": False, PERSONALITY_PROFILES_PARAM: migrated})

  readback = client.get("/api/personality_profiles")
  assert readback.status_code == 200
  assert readback.get_json()["migration_required"] is False

  response = client.put("/api/personality_profiles", json={
    "profile": "aggressive", "category": "braking", "preset": "sport", "curve": [],
  })
  assert response.status_code == 200
  stored = strict_profile_document(params.values[PERSONALITY_PROFILES_PARAM])
  assert stored is not None
  assert stored["profiles"]["standard"]["acceleration"]["legacyCurve"] == [1.0] * 7
  assert stored["profiles"]["aggressive"]["braking"] == {"preset": "sport", "curve": []}


def test_known_v1_document_cannot_be_overwritten_before_a_verified_migration(monkeypatch):
  legacy = _known_v1_document()
  client, params = _client(monkeypatch, {"IsOnroad": False, PERSONALITY_PROFILES_PARAM: legacy})

  profile_response = client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "acceleration", "preset": "eco", "curve": [],
  })
  master_response = client.put("/api/params", json={"key": "CustomPersonalities", "value": False})

  assert profile_response.status_code == 409
  assert master_response.status_code == 409
  assert params.values[PERSONALITY_PROFILES_PARAM] == legacy


def test_malformed_document_is_not_overwritten_by_profile_edit(monkeypatch):
  malformed = {"schemaVersion": 99}
  client, params = _client(monkeypatch, {"IsOnroad": False, PERSONALITY_PROFILES_PARAM: malformed})

  response = client.put("/api/personality_profiles", json={
    "profile": "standard", "category": "acceleration", "preset": "eco", "curve": [],
  })

  assert response.status_code == 409
  assert params.values[PERSONALITY_PROFILES_PARAM] == malformed


def test_malformed_stored_document_readback_fails_closed(monkeypatch):
  client, _ = _client(monkeypatch, {"IsOnroad": False, PERSONALITY_PROFILES_PARAM: {"schemaVersion": 99}})
  response = client.get("/api/personality_profiles")
  assert response.status_code == 409
  assert "malformed" in response.get_json()["error"].lower()
