import json
from types import SimpleNamespace

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


def test_ios_pairing_advertises_compact_telemetry_endpoint():
  payload = the_galaxy._build_ios_galaxy_pairing_payload(
    "testGalaxySlug01",
    "a" * 64,
    "http://192.168.0.75:8082",
  )

  assert payload["telemetryPath"] == "/api/galaxy/telemetry"
  assert payload["vehicleTelemetryUrl"] == "https://galaxy.firestar.link/api/galaxy/telemetry"


def test_galaxy_lan_address_filter_rejects_cellular_and_accepts_wifi():
  assert not the_galaxy._is_galaxy_lan_ipv4_address("30.9.31.4")
  assert not the_galaxy._is_galaxy_lan_ipv4_address("25.73.76.228")
  assert the_galaxy._is_galaxy_lan_ipv4_address("192.168.0.75")
  assert the_galaxy._is_galaxy_lan_ipv4_address("10.0.0.2")


def test_ios_pairing_rejects_public_request_host_as_local_base_url(monkeypatch):
  monkeypatch.setattr(the_galaxy, "request", SimpleNamespace(
    host="30.9.31.4:8082",
    host_url="http://30.9.31.4:8082/",
  ))

  assert the_galaxy._request_local_base_url() == ""


def test_ios_pairing_uses_private_request_host_as_local_base_url(monkeypatch):
  monkeypatch.setattr(the_galaxy, "request", SimpleNamespace(
    host="192.168.0.75:8082",
    host_url="http://192.168.0.75:8082/",
  ))

  assert the_galaxy._request_local_base_url() == "http://192.168.0.75:8082"


def test_compact_vehicle_telemetry_payload_keeps_only_maps_fields():
  payload = the_galaxy._compact_vehicle_telemetry_payload({
    "available": True,
    "status": "ok",
    "updatedAt": 1234.5,
    "source": "StarPilot Galaxy E-GMP CAN",
    "vehicleName": "Kia EV9",
    "stateOfChargePercent": 82.0,
    "distanceToEmptyKilometers": 401.0,
    "isCharging": False,
    "isPluggedIn": None,
    "rawValues": {"large": "diagnostic payload"},
    "canTopFrames": [{"address": "0x2b5"}],
    "location": {"latitude": 41.0, "longitude": -87.0},
  })

  assert payload == {
    "available": True,
    "status": "ok",
    "updatedAt": 1234.5,
    "source": "StarPilot Galaxy E-GMP CAN",
    "vehicleName": "Kia EV9",
    "stateOfChargePercent": 82.0,
    "distanceToEmptyKilometers": 401.0,
    "isCharging": False,
  }


def test_vehicle_telemetry_updated_at_does_not_regress_during_boot_clock_sync(monkeypatch):
  gnss_time = 1_783_624_171.0
  cached_time = gnss_time + 2_463.0
  monkeypatch.setattr(the_galaxy.time, "time", lambda: 1_751_465_133.0)
  monkeypatch.setattr(the_galaxy, "_vehicle_telemetry_best_cache_load", lambda: {"updatedAt": cached_time})

  assert the_galaxy._vehicle_telemetry_updated_at({"updatedAtSec": gnss_time}) == cached_time


def test_ev9_passive_decoder_distinguishes_charge_states():
  def decode(charge_status, energy_status, redundant_energy_status):
    frames = [
      {"src": 1, "address": 0x30A, "data": bytes.fromhex(charge_status)},
      {"src": 1, "address": 0x320, "data": bytes.fromhex(energy_status)},
      {"src": 1, "address": 0x2FA, "data": bytes.fromhex(redundant_energy_status)},
    ]
    return the_galaxy._decode_egmp_passive_display_frames(frames)[0]

  charging = decode(
    "4dc1150854011015006578000f00a00f0000000049820018000038402101003a",
    "98921544000001baac0d88190001000f00000000000000000d003e004c040000",
    "447b7404c31ecdcdf1ff1c1e000080ba00000000001414137c01720140280000",
  )
  charge_complete = decode(
    "2c1a9508440000108068b6230f01a00f00000000477d0002000038402101003a",
    "3e499544000000c8ac0d88190001000f0000000000000000000000004c040000",
    "5cb801008f1dcece00001d1e00007ac80000000000140f0fffff720140280000",
  )
  unplugged = decode(
    "c9174f000400000000000c002c00a00f0000000043000001000038402000000e",
    "7f5a4f44000000c3ac0d88190001000f000000000000000000000000ef560000",
    "a24e5104d81dcccd09001a1b000084c3000000000014100f0000720140280000",
  )

  assert (charging["isPluggedIn"], charging["isCharging"]) == (True, True)
  assert (charge_complete["isPluggedIn"], charge_complete["isCharging"]) == (True, False)
  assert (unplugged["isPluggedIn"], unplugged["isCharging"]) == (False, False)


def test_galaxy_telemetry_route_reads_cache_without_sampling(monkeypatch):
  monkeypatch.setattr(the_galaxy, "_start_vehicle_telemetry_background_sampler", lambda: None)
  client, _ = _params_client(monkeypatch, {"IsOnroad": False}, "tici")
  monkeypatch.setattr(the_galaxy, "_vehicle_telemetry_best_cache_load", lambda: {
    "updatedAt": 1234.5,
    "stateOfChargePercent": 82.0,
    "rawValues": {"large": "diagnostic payload"},
  })
  monkeypatch.setattr(the_galaxy, "_build_vehicle_telemetry_payload", lambda **_: (_ for _ in ()).throw(AssertionError("sampled CAN")))

  response = client.get("/api/galaxy/telemetry")

  assert response.status_code == 200
  assert response.headers["Cache-Control"] == "no-store"
  assert response.get_json() == {
    "available": True,
    "stateOfChargePercent": 82.0,
    "updatedAt": 1234.5,
  }


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
