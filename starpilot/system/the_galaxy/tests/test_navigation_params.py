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
  "KiaEv9ClusterBsmReconstructionEnabled",
  "KiaEv9ClusterHeadwayEnabled",
  "KiaEv9ClusterObjectsEnabled",
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


def test_galaxy_lan_address_filter_rejects_cellular_and_accepts_wifi():
  assert not the_galaxy._is_galaxy_lan_ipv4_address("30.9.31.4")
  assert not the_galaxy._is_galaxy_lan_ipv4_address("25.73.76.228")
  assert the_galaxy._is_galaxy_lan_ipv4_address("192.168.0.75")
  assert the_galaxy._is_galaxy_lan_ipv4_address("10.0.0.2")


def test_galaxy_telemetry_routes_separate_lan_and_remote_auth(monkeypatch, tmp_path):
  monkeypatch.setenv("SP_GALAXY_DIR", str(tmp_path))
  slug = "testGalaxySlug01"
  session_secret = "a" * 64
  (tmp_path / "glxyslug").write_text(slug)
  (tmp_path / "glxysession").write_text(session_secret)
  config = {
    "mode": "galaxy",
    "fetch": {"enabled": True},
    "push": {"vehicleId": "ev9-test"},
  }
  cache_loads = []

  class FakeVehicleTelemetryCache:
    def load(self):
      cache_loads.append(True)
      return {"updatedAt": 1234.5, "stateOfChargePercent": 82.0}

  monkeypatch.setattr(the_galaxy, "load_vehicle_telemetry_config", lambda: config)
  monkeypatch.setattr(the_galaxy, "is_fetch_authorized", lambda _config, auth: auth == "Bearer test-token")
  monkeypatch.setattr(the_galaxy, "VehicleTelemetryCache", FakeVehicleTelemetryCache)
  monkeypatch.setattr(
    the_galaxy,
    "telemetry_response",
    lambda payload, vehicle_id="": {**payload, "vehicleId": vehicle_id} if payload is not None else None,
  )
  client, _ = _params_client(monkeypatch, {"IsOnroad": False}, "tici")
  cache_loads.clear()

  for alias in ("/api/galaxy/telemetry", "/api/vehicle/telemetry"):
    prior_loads = len(cache_loads)
    unauthorized = client.get(alias)
    assert unauthorized.status_code == 401
    assert unauthorized.headers["WWW-Authenticate"] == 'Bearer realm="vehicle-telemetry"'
    assert len(cache_loads) == prior_loads

    authorized = client.get(alias, headers={"Authorization": "Bearer test-token"})
    assert authorized.status_code == 200
    assert authorized.headers["Cache-Control"] == "no-store"
    assert authorized.get_json() == {
      "stateOfChargePercent": 82.0,
      "updatedAt": 1234.5,
      "vehicleId": "ev9-test",
    }
    assert len(cache_loads) == prior_loads + 1

  remote = {"REMOTE_ADDR": "203.0.113.5", "HTTP_HOST": "galaxy.firestar.link"}
  assert client.get(
    "/api/galaxy/telemetry",
    headers={"Authorization": "Bearer test-token"},
    environ_overrides=remote,
  ).status_code == 404
  assert client.get(
    "/wrong-slug/api/vehicle/telemetry",
    headers={"Authorization": "Bearer test-token"},
    environ_overrides=remote,
  ).status_code == 404

  for remote_alias in (f"/{slug}/api/galaxy/telemetry", f"/{slug}/api/vehicle/telemetry"):
    bearer_only = client.get(
      remote_alias,
      headers={"Authorization": "Bearer test-token"},
      environ_overrides=remote,
    )
    assert bearer_only.status_code == 401

  client.set_cookie(
    the_galaxy.GALAXY_COOKIE_NAME,
    the_galaxy._build_galaxy_session_value(slug, session_secret),
    domain="galaxy.firestar.link",
  )
  for remote_alias in (f"/{slug}/api/galaxy/telemetry", f"/{slug}/api/vehicle/telemetry"):
    cookie_only = client.get(remote_alias, environ_overrides=remote)
    assert cookie_only.status_code == 401
    authorized = client.get(
      remote_alias,
      headers={"Authorization": "Bearer test-token"},
      environ_overrides=remote,
    )
    assert authorized.status_code == 200

  assert cache_loads == [True, True, True, True]


def test_unauthenticated_galaxy_session_does_not_read_or_return_vehicle_telemetry(monkeypatch):
  def unexpected_telemetry_access(*_args, **_kwargs):
    raise AssertionError("Unauthenticated Galaxy session accessed vehicle telemetry")

  monkeypatch.setattr(the_galaxy, "load_vehicle_telemetry_config", unexpected_telemetry_access)
  monkeypatch.setattr(the_galaxy, "VehicleTelemetryCache", unexpected_telemetry_access)
  client, _ = _params_client(monkeypatch, {"IsOnroad": False}, "tici")

  response = client.get("/api/galaxy/session")
  assert response.status_code == 200
  assert "vehicleTelemetry" not in response.get_json()


def test_unauthenticated_galaxy_metadata_never_returns_reusable_credentials(monkeypatch, tmp_path):
  monkeypatch.setenv("SP_GALAXY_DIR", str(tmp_path))
  slug = "testGalaxySlug01"
  secret = "a" * 64
  (tmp_path / "glxyauth").write_text("b" * 64)
  (tmp_path / "glxyslug").write_text(slug)
  (tmp_path / "glxysession").write_text(secret)
  client, _ = _params_client(monkeypatch, {"IsOnroad": False}, "tici")

  forbidden = {
    "appKey",
    "galaxyNavConnectUrl",
    "iosConnectUrl",
    "iosPairingCode",
    "iosShortConnectUrl",
    "iosShortPairingCode",
    "pairingPayload",
    "sessionToken",
    "token",
  }
  for route in ("/api/galaxy/status", "/api/galaxy/session"):
    response = client.get(route)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["paired"] is True
    assert not forbidden.intersection(payload)
    assert secret not in response.get_data(as_text=True)
    assert payload["externalAppPairingPath"] == "/api/external-app/pairing"

  for route in ("/api/galaxy/ios-pairing/123456", "/api/galaxy/ios-pairing-qr"):
    response = client.get(route)
    assert response.status_code == 410
    assert response.get_json()["externalAppPairingPath"] == "/api/external-app/pairing"


def test_legacy_galaxy_pair_mutations_require_owner_setup_session(monkeypatch, tmp_path):
  monkeypatch.setenv("SP_GALAXY_DIR", str(tmp_path))
  client, _ = _params_client(monkeypatch, {"IsOnroad": False}, "tici")

  denied_pair = client.post("/api/galaxy/pair", json={"password": "secret-password"})
  assert denied_pair.status_code == 403
  assert not (tmp_path / "glxyauth").exists()

  (tmp_path / "glxyauth").write_text("b" * 64)
  (tmp_path / "glxysession").write_text("a" * 64)
  (tmp_path / "glxyslug").write_text("testGalaxySlug01")
  denied_unpair = client.post("/api/galaxy/unpair")
  assert denied_unpair.status_code == 403
  assert (tmp_path / "glxysession").exists()

  monkeypatch.setattr(the_galaxy, "_request_is_lan_setup", lambda: True)
  allowed_unpair = client.post("/api/galaxy/unpair")
  assert allowed_unpair.status_code == 200
  assert not (tmp_path / "glxysession").exists()
  allowed_pair = client.post("/api/galaxy/pair", json={"password": "secret-password"})
  assert allowed_pair.status_code == 200
  assert allowed_pair.get_json()["externalAppPairingPath"] == "/api/external-app/pairing"
  assert "sessionToken" not in allowed_pair.get_json()
  assert (tmp_path / "glxysession").is_file()


def test_vehicle_telemetry_config_route_uses_atomic_update(monkeypatch, tmp_path):
  monkeypatch.setenv("SP_GALAXY_DIR", str(tmp_path))
  client, _ = _params_client(monkeypatch, {"IsOnroad": False}, "tici")
  monkeypatch.setattr(the_galaxy, "_request_is_lan_setup", lambda: True)
  real_update = the_galaxy.update_vehicle_telemetry_config
  updates = []

  def recording_update(mutator):
    updates.append(True)
    return real_update(mutator)

  monkeypatch.setattr(the_galaxy, "update_vehicle_telemetry_config", recording_update)
  response = client.post("/api/vehicle/telemetry/config", json={
    "mode": "local",
    "fetch": {"enabled": True, "port": 17766},
    "rotateFetchToken": True,
  })

  assert response.status_code == 200
  assert updates == [True]
  config = the_galaxy.load_vehicle_telemetry_config()
  assert config["mode"] == "local"
  assert config["fetch"]["enabled"] is True
  assert config["fetch"]["port"] == 17766
  assert len(config["fetch"]["token"]) >= 32


def _poison_direct_vehicle_hardware(monkeypatch):
  def unexpected_hardware_access(*_args, **_kwargs):
    raise AssertionError("Galaxy opened direct vehicle hardware while access was blocked")

  monkeypatch.setattr(the_galaxy, "CANParser", unexpected_hardware_access)
  monkeypatch.setattr(the_galaxy.messaging, "sub_sock", unexpected_hardware_access)
  monkeypatch.setattr(the_galaxy, "Panda", unexpected_hardware_access)


def _assert_direct_vehicle_hardware_routes_blocked(client):
  for route in ("/api/doors/lock", "/api/doors/unlock"):
    response = client.post(route)
    assert response.status_code == 409
    assert "onroad or EV9 preinit" in response.get_json()["error"]


def test_ev9_preinit_blocks_galaxy_hardware_routes_before_opening_can(monkeypatch):
  client, _ = _params_client(
    monkeypatch,
    {"EV9LongPreinitPanda": True, "IsOnroad": False},
    "tici",
  )
  _poison_direct_vehicle_hardware(monkeypatch)
  _assert_direct_vehicle_hardware_routes_blocked(client)


def test_onroad_blocks_galaxy_hardware_routes_before_opening_can(monkeypatch):
  client, _ = _params_client(
    monkeypatch,
    {"EV9LongPreinitPanda": False, "IsOnroad": True},
    "tici",
  )
  _poison_direct_vehicle_hardware(monkeypatch)
  _assert_direct_vehicle_hardware_routes_blocked(client)


def test_vehicle_gate_transition_stops_before_any_door_hardware(monkeypatch):
  client, _ = _params_client(
    monkeypatch,
    {"EV9LongPreinitPanda": False, "IsOnroad": False},
    "tici",
  )
  checks = iter((False, True, False, True))
  monkeypatch.setattr(the_galaxy, "_direct_vehicle_hardware_access_blocked", lambda: next(checks))
  _poison_direct_vehicle_hardware(monkeypatch)

  for route in ("/api/doors/lock", "/api/doors/unlock"):
    response = client.post(route)
    assert response.status_code == 409
    assert "onroad or EV9 preinit" in response.get_json()["error"]


def test_door_command_has_bounded_retries_and_preserves_success(monkeypatch):
  client, _ = _params_client(
    monkeypatch,
    {"EV9LongPreinitPanda": False, "IsOnroad": False},
    "tici",
  )
  sends = []

  class FakePanda:
    SAFETY_TOYOTA = 73

    def __init__(self, **_kwargs):
      pass

    def __enter__(self):
      return self

    def __exit__(self, *_args):
      return None

    def set_safety_mode(self, mode):
      assert mode == self.SAFETY_TOYOTA

    def can_send(self, address, command, bus):
      sends.append((address, command, bus))

  monkeypatch.setattr(the_galaxy, "_direct_vehicle_hardware_access_blocked", lambda: False)
  monkeypatch.setattr(the_galaxy, "CANParser", lambda *_args, **_kwargs: object())
  monkeypatch.setattr(the_galaxy.messaging, "sub_sock", lambda *_args, **_kwargs: object())
  monkeypatch.setattr(the_galaxy, "Panda", FakePanda)
  monkeypatch.setattr(the_galaxy.time, "monotonic", lambda: 0.0)
  monkeypatch.setattr(the_galaxy.time, "sleep", lambda _seconds: None)
  monkeypatch.setattr(the_galaxy, "get_lock_status", lambda *_args: 1)

  timed_out = client.post("/api/doors/lock")
  assert timed_out.status_code == 504
  assert len(sends) == the_galaxy.DOOR_COMMAND_MAX_ATTEMPTS

  sends.clear()
  unlocked = client.post("/api/doors/unlock")
  assert unlocked.status_code == 200
  assert len(sends) == 1


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
