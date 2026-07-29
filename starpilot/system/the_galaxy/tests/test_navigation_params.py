import json

import pytest

from openpilot.common.params import ParamKeyType

from test_dashboard_stats import MODULE_DIR, _install_server_import_stubs


def _load_server_module():
  import importlib.util

  _install_server_import_stubs()
  spec = importlib.util.spec_from_file_location("navigation_params_server", MODULE_DIR / "the_galaxy.py")
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


the_galaxy = _load_server_module()


class FakeParamsBackend:
  def __init__(self, key_types=None, default_values=None, values=None):
    self.key_types = key_types or {}
    self.default_values = default_values or {}
    self.values = values or {}
    self.writes = []

  def get_key_type(self, key):
    return self.key_types[key]

  def get_default_value(self, key):
    return self.default_values.get(key)

  def put(self, key, value):
    self.writes.append((key, value))
    self.values[key] = value

  def put_bool(self, key, value):
    self.writes.append((key, bool(value)))
    self.values[key] = bool(value)

  def get(self, key, block=False):
    return self.values.get(key)


class WritableFakeParams:
  def __init__(self, values=None):
    self.values = dict(values or {})
    self.writes = []
    self.removals = []

  def get(self, key, encoding=None, default=None, block=False):
    del encoding, block
    return self.values.get(key, default)

  def get_bool(self, key):
    value = self.values.get(key, False)
    if isinstance(value, bool):
      return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")

  def put(self, key, value):
    self.writes.append((key, value))
    self.values[key] = value

  def put_bool(self, key, value):
    self.writes.append((key, bool(value)))
    self.values[key] = bool(value)

  def get_int(self, key, default=0):
    return int(self.values.get(key, default))

  def put_int(self, key, value):
    self.writes.append((key, int(value)))
    self.values[key] = int(value)

  def remove(self, key):
    self.removals.append(key)
    self.values.pop(key, None)

def _params_client(monkeypatch, values, device_type):
  fake_params = WritableFakeParams(values)
  monkeypatch.setattr(the_galaxy, "params", fake_params)
  monkeypatch.setattr(
    the_galaxy,
    "_get_param_type_info",
    lambda: ({"UseOldUI", "TryRaylibUI"}, {"UseOldUI": bool, "TryRaylibUI": bool}),
  )
  monkeypatch.setattr(the_galaxy.HARDWARE, "get_device_type", lambda: device_type)
  monkeypatch.setattr(the_galaxy.Paths, "comma_home", lambda: "/tmp/dashboard-test-home", raising=False)

  assert the_galaxy._import_galaxy_web_symbols()
  app = the_galaxy.Flask(f"params_test_{device_type}")
  the_galaxy.setup(app)
  return app.test_client(), fake_params


EV9_SCOPED_PARAM_KEYS = {
  "EV9LongPreinitPanda",
}


@pytest.mark.parametrize("fingerprint", ["", "KIA_EV6", "HYUNDAI_IONIQ_5"])
@pytest.mark.parametrize("key", sorted(EV9_SCOPED_PARAM_KEYS))
def test_ev9_scoped_param_writes_require_exact_fingerprint(monkeypatch, fingerprint, key):
  client, fake_params = _params_client(monkeypatch, {}, "tici")
  monkeypatch.setattr(
    the_galaxy,
    "_get_param_type_info",
    lambda: (EV9_SCOPED_PARAM_KEYS, dict.fromkeys(EV9_SCOPED_PARAM_KEYS, bool)),
  )
  monkeypatch.setattr(the_galaxy, "_persistent_car_fingerprint", lambda: fingerprint, raising=False)

  response = client.put("/api/params", json={"key": key, "value": True})

  assert response.status_code == 403
  assert not fake_params.get_bool(key)


def test_ev9_controls_are_visible_only_for_exact_fingerprint(monkeypatch):
  client, _ = _params_client(monkeypatch, {}, "tici")
  monkeypatch.setattr(
    the_galaxy,
    "_get_param_type_info",
    lambda: (EV9_SCOPED_PARAM_KEYS, dict.fromkeys(EV9_SCOPED_PARAM_KEYS, bool)),
  )
  monkeypatch.setattr(the_galaxy, "_get_default_param_values", lambda: dict.fromkeys(EV9_SCOPED_PARAM_KEYS, False))

  monkeypatch.setattr(the_galaxy, "_persistent_car_fingerprint", lambda: "KIA_EV9")
  ev9_controls = {control["key"]: control for control in client.get("/api/galaxy/session").get_json()["controls"]}
  assert EV9_SCOPED_PARAM_KEYS <= set(ev9_controls)
  assert ev9_controls["EV9LongPreinitPanda"]["confirmation"]["field"] == the_galaxy.PANDA_FIRMWARE_CONFIRMATION_FIELD

  monkeypatch.setattr(the_galaxy, "_persistent_car_fingerprint", lambda: "KIA_EV6")
  ev6_keys = {control["key"] for control in client.get("/api/galaxy/session").get_json()["controls"]}
  assert EV9_SCOPED_PARAM_KEYS.isdisjoint(ev6_keys)


def test_ev9_preinit_write_requires_panda_firmware_confirmation(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {}, "tici")
  monkeypatch.setattr(
    the_galaxy,
    "_get_param_type_info",
    lambda: (EV9_SCOPED_PARAM_KEYS, dict.fromkeys(EV9_SCOPED_PARAM_KEYS, bool)),
  )
  monkeypatch.setattr(the_galaxy, "_persistent_car_fingerprint", lambda: "KIA_EV9")

  response = client.put("/api/params", json={"key": "EV9LongPreinitPanda", "value": True})

  assert response.status_code == 409
  assert response.get_json()["confirmationRequired"] is True
  assert not fake_params.get_bool("EV9LongPreinitPanda")


def test_params_compat_accepts_json_strings_for_json_keys():
  backend = FakeParamsBackend(
    key_types={"FavoriteDestinations": ParamKeyType.JSON},
    default_values={"FavoriteDestinations": []},
  )
  compat = the_galaxy.ParamsCompat(backend)

  compat.put("FavoriteDestinations", json.dumps([{"name": "Home"}]))

  assert backend.writes == [("FavoriteDestinations", [{"name": "Home"}])]


def test_params_compat_syncs_lead_indicator_inverse_key():
  backend = FakeParamsBackend()
  compat = the_galaxy.ParamsCompat(backend)

  compat.put_bool("LeadIndicator", True)

  assert backend.writes == [("LeadIndicator", True), ("HideLeadMarker", False)]


def test_params_compat_syncs_hide_lead_marker_inverse_key():
  backend = FakeParamsBackend()
  compat = the_galaxy.ParamsCompat(backend)

  compat.put_bool("HideLeadMarker", True)

  assert backend.writes == [("HideLeadMarker", True), ("LeadIndicator", False)]


def test_navigation_last_position_uses_recent_persisted_fix(monkeypatch):
  recent_payload = json.dumps({
    "latitude": 41.0,
    "longitude": -87.0,
    "hasFix": True,
    "updatedAtSec": 10_000.0,
  })
  memory_backend = FakeParamsBackend(values={"LastGPSPosition": ""})
  persisted_backend = FakeParamsBackend(values={"LastGPSPosition": recent_payload})

  monkeypatch.setattr(the_galaxy, "params_memory", the_galaxy.ParamsCompat(memory_backend))
  monkeypatch.setattr(the_galaxy, "params", the_galaxy.ParamsCompat(persisted_backend))
  monkeypatch.setattr(the_galaxy.time, "time", lambda: 10_300.0)
  monkeypatch.setattr(the_galaxy, "system_time_valid", lambda: True)

  position = the_galaxy._get_navigation_last_position()

  assert position["latitude"] == 41.0
  assert position["longitude"] == -87.0


def test_navigation_last_position_rejects_stale_persisted_fix(monkeypatch):
  stale_payload = json.dumps({
    "latitude": 41.0,
    "longitude": -87.0,
    "hasFix": True,
    "updatedAtSec": 10_000.0,
  })
  memory_backend = FakeParamsBackend(values={"LastGPSPosition": ""})
  persisted_backend = FakeParamsBackend(values={"LastGPSPosition": stale_payload})

  monkeypatch.setattr(the_galaxy, "params_memory", the_galaxy.ParamsCompat(memory_backend))
  monkeypatch.setattr(the_galaxy, "params", the_galaxy.ParamsCompat(persisted_backend))
  monkeypatch.setattr(the_galaxy.time, "time", lambda: 10_000.0 + the_galaxy.NAVIGATION_PERSISTED_LOCATION_MAX_AGE_SECONDS + 1.0)
  monkeypatch.setattr(the_galaxy, "system_time_valid", lambda: True)

  assert the_galaxy._get_navigation_last_position() is None


def test_save_longitudinal_maneuver_status_writes_json_param_as_dict(monkeypatch):
  fake_params = WritableFakeParams()
  monkeypatch.setattr(the_galaxy, "params", fake_params)

  saved = the_galaxy._save_longitudinal_maneuver_status({
    "state": "armed",
    "history": ["", "Started"],
  })

  assert fake_params.writes == [("LongitudinalManeuverStatus", saved)]
  assert isinstance(fake_params.writes[0][1], dict)
  assert saved["history"] == ["Started"]


def test_save_lateral_maneuver_status_writes_json_param_as_dict(monkeypatch):
  fake_params = WritableFakeParams()
  monkeypatch.setattr(the_galaxy, "params", fake_params)

  saved = the_galaxy._save_lateral_maneuver_status({
    "state": "armed",
    "history": ["", "Started"],
  })

  assert fake_params.writes == [("LateralManeuverStatus", saved)]
  assert isinstance(fake_params.writes[0][1], dict)
  assert saved["history"] == ["Started"]


def test_galaxy_session_value_matches_cookie_format():
  assert the_galaxy._build_galaxy_session_value(
    "testGalaxySlug01",
    "a" * 64,
  ) == f"testGalaxySlug01%3A{'a' * 64}"


def test_configured_favorite_slot_values_only_reads_selected_keys(monkeypatch):
  fake_params = WritableFakeParams({
    "NavDesiresAllowed": False,
    "RedneckCruise": True,
    "UnusedToggle": True,
  })
  monkeypatch.setattr(the_galaxy, "params", fake_params)

  values = the_galaxy._configured_favorite_slot_values([
    {"enabled": True, "key": "NavDesiresAllowed"},
    {"enabled": False, "key": "RedneckCruise"},
    {"enabled": False, "key": None},
  ])

  assert values == {"NavDesiresAllowed": False, "RedneckCruise": True}


def test_favorite_values_endpoint_returns_current_selected_value(monkeypatch):
  client, _ = _params_client(monkeypatch, {"UseOldUI": False}, "tici")
  monkeypatch.setattr(the_galaxy, "_get_favorite_slot_options", lambda: [{"key": "UseOldUI"}])
  monkeypatch.setattr(
    the_galaxy,
    "normalize_favorite_slots",
    lambda *args, **kwargs: [{"enabled": True, "key": "UseOldUI"}],
  )

  response = client.get("/api/favorites/values")

  assert response.status_code == 200
  assert response.get_json() == {"values": {"UseOldUI": False}}


def test_favorite_slot_options_include_virtual_cruise_actions(monkeypatch):
  monkeypatch.setattr(the_galaxy, "_favorite_slot_options", None)
  monkeypatch.setattr(the_galaxy, "_get_param_type_info", lambda: (set(), {}))

  options = the_galaxy._get_favorite_slot_options()
  option_keys = {option["key"] for option in options}

  assert "__starpilot_favorite_action__:distance_decrease" in option_keys
  assert "__starpilot_favorite_action__:distance_increase" in option_keys


def test_favorite_action_endpoint_increments_virtual_button_counter(monkeypatch):
  client, _ = _params_client(monkeypatch, {}, "tici")
  fake_memory = WritableFakeParams()
  monkeypatch.setattr(the_galaxy, "params_memory", fake_memory)

  response = client.post("/api/favorites/action", json={"key": "__starpilot_favorite_action__:distance_increase"})

  assert response.status_code == 200
  assert fake_memory.get_int("FavoriteVirtualAccelCruiseCounter") == 1


def test_use_old_ui_is_noop_on_c4_mici(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {"UseOldUI": False, "IsOnroad": False}, "mici")

  response = client.put("/api/params", json={"key": "UseOldUI", "value": True})
  payload = response.get_json()

  assert response.status_code == 200
  assert payload["updated"] == {"UseOldUI": False, "TryRaylibUI": False}
  assert fake_params.values["UseOldUI"] is False
  assert fake_params.writes == []


def test_use_old_ui_writes_on_big_device_offroad(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {"UseOldUI": False, "TryRaylibUI": True, "IsOnroad": False}, "tici")

  response = client.put("/api/params", json={"key": "UseOldUI", "value": True})
  payload = response.get_json()

  assert response.status_code == 200
  assert payload["updated"] == {"UseOldUI": True, "TryRaylibUI": False}
  assert fake_params.values["UseOldUI"] is True
  assert fake_params.values["TryRaylibUI"] is False
  assert fake_params.writes == [("UseOldUI", True), ("TryRaylibUI", False)]


def test_use_old_ui_rejects_big_device_onroad_change(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {"UseOldUI": False, "TryRaylibUI": True, "IsOnroad": True}, "tici")

  response = client.put("/api/params", json={"key": "UseOldUI", "value": True})

  assert response.status_code == 403
  assert response.get_json()["error"] == "Cannot change Use Old UI while driving."
  assert fake_params.values["UseOldUI"] is False
  assert fake_params.values["TryRaylibUI"] is True
  assert fake_params.writes == []


def test_legacy_try_raylib_ui_payload_updates_use_old_ui(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {"UseOldUI": True, "TryRaylibUI": False, "IsOnroad": False}, "tici")

  response = client.put("/api/params", json={"key": "TryRaylibUI", "value": True})
  payload = response.get_json()

  assert response.status_code == 200
  assert payload["updated"] == {"UseOldUI": False, "TryRaylibUI": True}
  assert fake_params.values["UseOldUI"] is False
  assert fake_params.values["TryRaylibUI"] is True
  assert fake_params.writes == [("UseOldUI", False), ("TryRaylibUI", True)]


def test_curve_speed_controller_reset_clears_learned_data_offroad(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {
    "IsOnroad": False,
    "CalibratedLateralAcceleration": 2.73,
    "CalibrationProgress": 48.0,
    "CurvatureData": {"0.01": {"average": 2.73, "count": 12}},
  }, "tici")

  response = client.post("/api/curve_speed_controller/reset")

  assert response.status_code == 200
  assert response.get_json()["updated"] == {
    "CalibratedLateralAcceleration": 2.0,
    "CalibrationProgress": 0.0,
  }
  assert fake_params.values["CalibratedLateralAcceleration"] == 2.0
  assert "CalibrationProgress" not in fake_params.values
  assert "CurvatureData" not in fake_params.values
  assert fake_params.removals == ["CalibrationProgress", "CurvatureData"]


def test_curve_speed_controller_reset_rejected_onroad(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {
    "IsOnroad": True,
    "CalibratedLateralAcceleration": 2.73,
    "CalibrationProgress": 48.0,
    "CurvatureData": {"0.01": {"average": 2.73, "count": 12}},
  }, "tici")

  response = client.post("/api/curve_speed_controller/reset")

  assert response.status_code == 403
  assert response.get_json()["error"] == "Curve Speed Controller data can only be reset while parked."
  assert fake_params.writes == []
  assert fake_params.removals == []
