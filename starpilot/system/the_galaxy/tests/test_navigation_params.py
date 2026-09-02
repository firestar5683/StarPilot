import json
import sys
from dataclasses import asdict

from openpilot.common.params import ParamKeyType

from test_dashboard_stats import MODULE_DIR, _install_server_import_stubs


def _load_server_module():
  import importlib.util

  favorite_slots_name = "openpilot.starpilot.common.favorite_slots"
  previous_favorite_slots = sys.modules.get(favorite_slots_name)
  _install_server_import_stubs()
  try:
    spec = importlib.util.spec_from_file_location("navigation_params_server", MODULE_DIR / "the_galaxy.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
  finally:
    if previous_favorite_slots is None:
      sys.modules.pop(favorite_slots_name, None)
    else:
      sys.modules[favorite_slots_name] = previous_favorite_slots


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
    lambda: (
      {"AlphaLongitudinalEnabled", "ForceOffroad", "FordLateralMode"},
      {
        "AlphaLongitudinalEnabled": bool,
        "ForceOffroad": bool,
        "FordLateralMode": int,
      },
    ),
  )
  monkeypatch.setattr(the_galaxy.HARDWARE, "get_device_type", lambda: device_type)
  monkeypatch.setattr(the_galaxy.Paths, "comma_home", lambda: "/tmp/dashboard-test-home", raising=False)

  assert the_galaxy._import_galaxy_web_symbols()
  app = the_galaxy.Flask(f"params_test_{device_type}")
  the_galaxy.setup(app)
  return app.test_client(), fake_params


class FakeBluetoothClient:
  calls = []

  def __init__(self, timeout=0):
    self.timeout = timeout

  def status(self):
    from openpilot.starpilot.system.bluetooth.protocol import BluetoothStatus
    return BluetoothStatus(available=True, enabled=True, powered=True, offroad=True)

  @staticmethod
  def serialize_status(status):
    return asdict(status)

  def set_power(self, enabled):
    self.calls.append(("set_power", {"enabled": enabled}))

  def call(self, command, **payload):
    self.calls.append((command, payload))
    if command == "test_audio":
      return {"audio_test_delay_ms": 3000}
    if command == "elm_open":
      return {"adapter": "Fake ELM327"}
    if command == "elm_command":
      return {"response": "OK"}
    if command == "elm_read_dtcs":
      return {"codes": ["P0133"], "raw": "43 01 33"}
    return {}


def test_bluetooth_status_api(monkeypatch):
  client, _ = _params_client(monkeypatch, {"IsOffroad": True}, "mici")
  monkeypatch.setattr(the_galaxy, "BluetoothClient", FakeBluetoothClient)

  response = client.get("/api/bluetooth/status")

  assert response.status_code == 200
  assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
  assert response.get_json() == {
    "available": True,
    "devices": [],
    "discovering": False,
    "enabled": True,
    "error": "",
    "offroad": True,
    "pairing_address": "",
    "powered": True,
    "prompt": None,
    "selected_audio": "",
  }


def test_bluetooth_api_enforces_offroad(monkeypatch):
  FakeBluetoothClient.calls = []
  client, _ = _params_client(monkeypatch, {"IsOffroad": False}, "mici")
  monkeypatch.setattr(the_galaxy, "BluetoothClient", FakeBluetoothClient)

  response = client.post("/api/bluetooth/pair", json={"address": "00:11:22:33:44:55"})

  assert response.status_code == 409
  assert FakeBluetoothClient.calls == []

  response = client.post("/api/bluetooth/test_audio", json={"address": "00:11:22:33:44:55"})
  assert response.status_code == 409
  assert FakeBluetoothClient.calls == []


def test_bluetooth_api_allows_connection_recovery_onroad(monkeypatch):
  FakeBluetoothClient.calls = []
  client, _ = _params_client(monkeypatch, {"IsOffroad": False}, "mici")
  monkeypatch.setattr(the_galaxy, "BluetoothClient", FakeBluetoothClient)

  response = client.post("/api/bluetooth/connect", json={"address": "00:11:22:33:44:55"})

  assert response.status_code == 200
  assert FakeBluetoothClient.calls == [("connect", {"address": "00:11:22:33:44:55"})]


def test_bluetooth_api_dispatches_operations(monkeypatch):
  FakeBluetoothClient.calls = []
  client, _ = _params_client(monkeypatch, {"IsOffroad": True}, "mici")
  monkeypatch.setattr(the_galaxy, "BluetoothClient", FakeBluetoothClient)

  assert client.post("/api/bluetooth/power", json={"enabled": True}).status_code == 200
  assert client.post("/api/bluetooth/select_audio", json={"address": "00:11:22:33:44:55"}).status_code == 200
  assert client.post("/api/bluetooth/select_audio", json={"address": ""}).status_code == 200
  audio_response = client.post("/api/bluetooth/test_audio", json={"address": "00:11:22:33:44:55"})
  assert audio_response.status_code == 200
  assert audio_response.get_json()["audio_test_delay_ms"] == 3000

  assert FakeBluetoothClient.calls == [
    ("set_power", {"enabled": True}),
    ("select_audio", {"address": "00:11:22:33:44:55"}),
    ("select_audio", {"address": ""}),
    ("test_audio", {"address": "00:11:22:33:44:55"}),
  ]


def test_bluetooth_api_dispatches_elm_payload_and_allows_close_onroad(monkeypatch):
  FakeBluetoothClient.calls = []
  client, fake_params = _params_client(monkeypatch, {"IsOffroad": True}, "mici")
  monkeypatch.setattr(the_galaxy, "BluetoothClient", FakeBluetoothClient)
  address = "00:11:22:33:44:55"

  assert client.post("/api/bluetooth/elm_open", json={"address": address}).get_json()["adapter"] == "Fake ELM327"
  assert client.post("/api/bluetooth/elm_command", json={"address": address, "value": "ATI"}).get_json()["response"] == "OK"
  assert client.post("/api/bluetooth/elm_read_dtcs", json={"address": address}).get_json()["codes"] == ["P0133"]
  fake_params.values["IsOffroad"] = False
  assert client.post("/api/bluetooth/elm_close", json={"address": address}).status_code == 200

  assert FakeBluetoothClient.calls == [
    ("elm_open", {"address": address}),
    ("elm_command", {"address": address, "value": "ATI"}),
    ("elm_read_dtcs", {"address": address}),
    ("elm_close", {"address": address}),
  ]


def test_wheel_controls_status_includes_favorite_slots(monkeypatch):
  client, _ = _params_client(monkeypatch, {"IsOffroad": True, "FavoriteSlots": []}, "mici")
  monkeypatch.setattr(the_galaxy, "wheel_control_status", lambda *_args: {"available": True, "mappings": [], "devices": []})
  monkeypatch.setattr(the_galaxy, "_get_available_favorite_slot_options", lambda: [{"key": "ForceOffroad", "label": "Force Offroad"}])
  monkeypatch.setattr(the_galaxy, "normalize_favorite_slots", lambda *_args, **_kwargs: [
    {"enabled": True, "key": "ForceOffroad", "label": ""},
    {"enabled": False, "key": None, "label": ""},
    {"enabled": False, "key": None, "label": ""},
  ])

  response = client.get("/api/wheel-controls/status")

  assert response.status_code == 200
  assert response.get_json()["slots"][0]["label"] == "Force Offroad"
  assert len(response.get_json()["slots"]) == 3
  assert len(response.get_json()["controller_slots"]) == 10
  option_keys = {option["key"] for option in response.get_json()["controller_options"]}
  assert option_keys == {
    "ForceOffroad",
    "__starpilot_controller_action__:set_speed",
    "__starpilot_controller_action__:selfie",
    "__starpilot_controller_action__:bookmark",
    "__starpilot_controller_action__:pulse_and_glide",
    "__starpilot_controller_action__:force_coast",
    "__starpilot_controller_action__:toggle_aol",
    "__starpilot_controller_action__:engage_openpilot",
    "__starpilot_controller_action__:disengage_openpilot",
  }
  assert response.get_json()["speed_unit"] == "mph"


def test_wheel_controls_configures_a_controller_only_action(monkeypatch):
  client, _ = _params_client(monkeypatch, {"IsOffroad": True}, "mici")
  calls = []
  monkeypatch.setattr(the_galaxy, "_get_available_favorite_slot_options", lambda: [{"key": "ForceOffroad", "label": "Force Offroad"}])
  monkeypatch.setattr(the_galaxy, "set_controller_action_slot", lambda *args, **kwargs: calls.append((args, kwargs)))

  response = client.post("/api/wheel-controls/action", json={"slot": 9, "key": "ForceOffroad"})

  assert response.status_code == 200
  expected_keys = {
    "ForceOffroad",
    "__starpilot_controller_action__:set_speed",
    "__starpilot_controller_action__:selfie",
    "__starpilot_controller_action__:bookmark",
    "__starpilot_controller_action__:pulse_and_glide",
    "__starpilot_controller_action__:force_coast",
    "__starpilot_controller_action__:toggle_aol",
    "__starpilot_controller_action__:engage_openpilot",
    "__starpilot_controller_action__:disengage_openpilot",
  }
  assert calls == [((9, "ForceOffroad", "Force Offroad", the_galaxy.params), {"value": None, "eligible_keys": expected_keys})]


def test_wheel_controls_configures_set_speed_in_current_units(monkeypatch):
  client, _ = _params_client(monkeypatch, {"IsOffroad": True, "IsMetric": False}, "mici")
  calls = []
  monkeypatch.setattr(the_galaxy, "_get_available_favorite_slot_options", list)
  monkeypatch.setattr(the_galaxy, "set_controller_action_slot", lambda *args, **kwargs: calls.append((args, kwargs)))

  response = client.post("/api/wheel-controls/action", json={
    "slot": 0,
    "key": "__starpilot_controller_action__:set_speed",
    "value": 60,
  })

  assert response.status_code == 200
  assert calls[0][0][:4] == (0, "__starpilot_controller_action__:set_speed", "Set Speed To", the_galaxy.params)
  assert calls[0][1]["value"] == 60

  response = client.post("/api/wheel-controls/action", json={
    "slot": 0,
    "key": "__starpilot_controller_action__:set_speed",
    "value": 100,
  })
  assert response.status_code == 400


def test_controller_selfie_is_saved_to_sentry_history(monkeypatch, tmp_path):
  client, fake_params = _params_client(monkeypatch, {"IsOffroad": False}, "mici")
  recorded = []
  monkeypatch.setattr(the_galaxy, "_get_live_driver_jpeg", lambda: b"jpeg-data")
  monkeypatch.setattr(the_galaxy, "_sentry_event_roots", lambda: (tmp_path,))
  monkeypatch.setattr(the_galaxy, "_record_sentry_event", lambda event: recorded.append(event))

  response = client.post("/api/sentry/selfie")

  assert response.status_code == 201
  event = recorded[0]
  assert event["kind"] == "selfie"
  assert event["message"] == "Comma Selfie"
  assert (tmp_path / event["eventId"] / "driver.jpg").read_bytes() == b"jpeg-data"
  assert the_galaxy._normalize_sentry_event(event)["kind"] == "selfie"
  assert fake_params.get("SentryModeLastEvent") is not None


def test_wheel_controls_learning_targets_controller_only_action(monkeypatch):
  client, _ = _params_client(monkeypatch, {"IsOffroad": True}, "mici")
  calls = []
  monkeypatch.setattr(the_galaxy, "start_wheel_control_learning", lambda *args: calls.append(args))
  monkeypatch.setattr(the_galaxy, "_get_available_favorite_slot_options", lambda: [{"key": "ForceOffroad", "label": "Force Offroad"}])
  monkeypatch.setattr(the_galaxy, "load_controller_action_slots", lambda *_args, **_kwargs: [
    {"enabled": True, "key": "ForceOffroad", "label": "Force Offroad"},
    *[{"enabled": False, "key": None, "label": ""} for _ in range(9)],
  ])

  response = client.post("/api/wheel-controls/learn", json={"slot": 3})

  assert response.status_code == 200
  assert calls == [(3, the_galaxy.params_memory, the_galaxy.params)]


def test_wheel_controls_learning_requires_offroad(monkeypatch):
  client, _ = _params_client(monkeypatch, {"IsOffroad": False}, "mici")
  calls = []
  monkeypatch.setattr(the_galaxy, "start_wheel_control_learning", lambda *args: calls.append(args))

  response = client.post("/api/wheel-controls/learn", json={"slot": 0})

  assert response.status_code == 409
  assert calls == []


def test_wheel_controls_learning_targets_configured_favorite(monkeypatch):
  client, _ = _params_client(monkeypatch, {"IsOffroad": True, "FavoriteSlots": []}, "mici")
  calls = []
  monkeypatch.setattr(the_galaxy, "start_wheel_control_learning", lambda *args: calls.append(args))
  monkeypatch.setattr(the_galaxy, "_get_available_favorite_slot_options", lambda: [{"key": "ForceOffroad", "label": "Force Offroad"}])
  monkeypatch.setattr(the_galaxy, "normalize_favorite_slots", lambda *_args, **_kwargs: [
    {"enabled": True, "key": "ForceOffroad", "label": "Force Offroad"},
    {"enabled": False, "key": None, "label": ""},
    {"enabled": False, "key": None, "label": ""},
  ])

  response = client.post("/api/wheel-controls/learn", json={"slot": 0})

  assert response.status_code == 200
  assert calls == [(0, the_galaxy.params_memory, the_galaxy.params)]


def test_wheel_controls_test_mode_has_explicit_start_and_stop(monkeypatch):
  client, _ = _params_client(monkeypatch, {"IsOffroad": True}, "mici")
  calls = []
  monkeypatch.setattr(the_galaxy, "start_wheel_control_testing", lambda *args: calls.append(("start", args)))
  monkeypatch.setattr(the_galaxy, "stop_wheel_control_testing", lambda *args: calls.append(("stop", args)))

  assert client.post("/api/wheel-controls/test").status_code == 200
  assert client.post("/api/wheel-controls/test-stop").status_code == 200
  assert calls == [
    ("start", (the_galaxy.params_memory, the_galaxy.params)),
    ("stop", (the_galaxy.params_memory,)),
  ]


def test_wheel_controls_joystick_selection_is_explicit_and_offroad(monkeypatch):
  client, _ = _params_client(monkeypatch, {"IsOffroad": True}, "mici")
  calls = []
  monkeypatch.setattr(the_galaxy, "wheel_control_status", lambda *_args: {"devices": [
    {"device_id": "bt-pad", "joystick_capable": True},
  ]})
  monkeypatch.setattr(the_galaxy, "set_joystick_device", lambda *args: calls.append(args))

  response = client.post("/api/wheel-controls/joystick", json={"device_id": "bt-pad", "enabled": True})

  assert response.status_code == 200
  assert calls == [("bt-pad", True, the_galaxy.params)]


def test_wheel_controls_rejects_button_only_joystick_source(monkeypatch):
  client, _ = _params_client(monkeypatch, {"IsOffroad": True}, "mici")
  monkeypatch.setattr(the_galaxy, "wheel_control_status", lambda *_args: {"devices": [
    {"device_id": "media-remote", "joystick_capable": False},
  ]})

  response = client.post("/api/wheel-controls/joystick", json={"device_id": "media-remote", "enabled": True})

  assert response.status_code == 400


def test_wheel_controls_joystick_selection_requires_offroad(monkeypatch):
  client, _ = _params_client(monkeypatch, {"IsOffroad": False}, "mici")
  calls = []
  monkeypatch.setattr(the_galaxy, "set_joystick_device", lambda *args: calls.append(args))

  response = client.post("/api/wheel-controls/joystick", json={"device_id": "bt-pad", "enabled": True})

  assert response.status_code == 409
  assert calls == []


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
  client, _ = _params_client(monkeypatch, {"ForceOffroad": False}, "tici")
  monkeypatch.setattr(the_galaxy, "_get_favorite_slot_options", lambda: [{"key": "ForceOffroad"}])
  monkeypatch.setattr(
    the_galaxy,
    "normalize_favorite_slots",
    lambda *args, **kwargs: [{"enabled": True, "key": "ForceOffroad"}],
  )

  response = client.get("/api/favorites/values")

  assert response.status_code == 200
  assert response.get_json() == {"values": {"ForceOffroad": False}}


def test_device_settings_layout_asset_is_served_from_common_catalog(monkeypatch):
  client, _ = _params_client(monkeypatch, {}, "tici")

  with client.get("/assets/components/tools/device_settings_layout.json") as response:
    assert response.status_code == 200
    assert response.get_json() == the_galaxy.load_settings_catalog()


def test_params_all_exposes_curve_calibration_readouts(monkeypatch):
  client, _ = _params_client(monkeypatch, {
    "CalibratedLateralAcceleration": 2.73,
    "CalibrationProgress": 48.0,
  }, "tici")
  monkeypatch.setattr(
    the_galaxy,
    "_params_live_raw",
    WritableFakeParams({
      "CalibratedLateralAcceleration": 2.73,
      "CalibrationProgress": 48.0,
    }),
  )

  response = client.get("/api/params/all")

  assert response.status_code == 200
  assert response.get_json()["CalibratedLateralAcceleration"] == 2.73
  assert response.get_json()["CalibrationProgress"] == 48.0


def test_ford_lateral_mode_is_editable_through_galaxy(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {
    "CarMake": "Ford",
    "FordLateralMode": 1,
  }, "mici")

  response = client.put("/api/params", json={"key": "FordLateralMode", "value": 2, "label": "Angle"})

  assert response.status_code == 200
  assert fake_params.values["FordLateralMode"] == "2"
  assert ("FordLateralMode", "2") in fake_params.writes


def test_custom_accel_breakpoint_update_validates_the_complete_curve(monkeypatch):
  point_count_key = the_galaxy.CUSTOM_ACCEL_PROFILE_POINT_COUNT_KEY
  breakpoint_keys = the_galaxy.CUSTOM_ACCEL_PROFILE_BREAKPOINT_PARAM_KEYS
  value_keys = the_galaxy.CUSTOM_ACCEL_PROFILE_POINT_VALUE_PARAM_KEYS
  values = {
    the_galaxy.CUSTOM_ACCEL_PROFILE_BREAKPOINTS_INITIALIZED_KEY: True,
    point_count_key: 3,
    **dict(zip(breakpoint_keys, [0.0, 20.0, 40.0] + [50.0] * 9, strict=True)),
    **dict.fromkeys(value_keys, 1.0),
  }
  client, fake_params = _params_client(monkeypatch, values, "tici")
  monkeypatch.setattr(the_galaxy, "_get_param_type_info", lambda: ({breakpoint_keys[1]}, {breakpoint_keys[1]: float}))
  monkeypatch.setattr(the_galaxy, "_get_custom_accel_profile_breakpoints_initialized", lambda: True)
  monkeypatch.setattr(the_galaxy, "_get_default_param_values", dict)

  valid_response = client.put("/api/params", json={"key": breakpoint_keys[1], "value": 25.0})
  assert valid_response.status_code == 200
  assert fake_params.values[breakpoint_keys[1]] == "25.0"

  invalid_response = client.put("/api/params", json={"key": breakpoint_keys[1], "value": 45.0})
  assert invalid_response.status_code == 400
  assert "strictly increasing" in invalid_response.get_json()["error"]
  assert fake_params.values[breakpoint_keys[1]] == "25.0"


def test_uninitialized_custom_accel_curve_returns_zero_mph_breakpoint(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {}, "tici")
  monkeypatch.setattr(the_galaxy, "_params_live_raw", fake_params)

  response = client.get(f"/api/params?key={the_galaxy.CUSTOM_ACCEL_PROFILE_BREAKPOINT_PARAM_KEYS[0]}")

  assert response.status_code == 200
  assert response.get_data(as_text=True) == "0.0"


def test_first_breakpoint_edit_seeds_existing_legacy_accel_values(monkeypatch):
  legacy_keys = [f"CustomAccelProfile{speed}MPH" for speed in (0, 11, 22, 34, 45, 56, 89)]
  breakpoint_keys = the_galaxy.CUSTOM_ACCEL_PROFILE_BREAKPOINT_PARAM_KEYS
  value_keys = the_galaxy.CUSTOM_ACCEL_PROFILE_POINT_VALUE_PARAM_KEYS
  legacy_values = [3.2, 2.7, 2.1, 1.6, 1.1, 0.75, 0.5]
  defaults = {
    the_galaxy.CUSTOM_ACCEL_PROFILE_POINT_COUNT_KEY: 7,
    **dict(zip(breakpoint_keys, the_galaxy.CUSTOM_ACCEL_PROFILE_DEFAULT_BREAKPOINTS_MPH, strict=True)),
    **dict.fromkeys(value_keys, 0.35),
  }
  values = dict(zip(legacy_keys, legacy_values, strict=True))
  client, fake_params = _params_client(monkeypatch, values, "tici")
  monkeypatch.setattr(the_galaxy, "_params_live_raw", fake_params)
  monkeypatch.setattr(the_galaxy, "CUSTOM_ACCEL_PROFILE_PARAM_KEYS", legacy_keys)
  monkeypatch.setattr(the_galaxy, "_get_param_type_info", lambda: ({breakpoint_keys[1]}, {breakpoint_keys[1]: float}))
  monkeypatch.setattr(the_galaxy, "_get_custom_accel_profile_initialized", lambda: True)
  monkeypatch.setattr(the_galaxy, "_get_custom_accel_profile_breakpoints_initialized", lambda: False)
  monkeypatch.setattr(the_galaxy, "_get_default_param_values", lambda: defaults)

  response = client.put("/api/params", json={"key": breakpoint_keys[1], "value": 18.0})

  assert response.status_code == 200
  assert [float(fake_params.values[key]) for key in value_keys[:7]] == legacy_values
  assert fake_params.values[breakpoint_keys[1]] == "18.0"
  assert fake_params.values[the_galaxy.CUSTOM_ACCEL_PROFILE_BREAKPOINTS_INITIALIZED_KEY] is True


def test_favorite_slot_options_include_virtual_cruise_actions(monkeypatch):
  monkeypatch.setattr(the_galaxy, "_favorite_slot_options", None)
  monkeypatch.setattr(the_galaxy, "_get_param_type_info", lambda: (set(), {}))

  options = the_galaxy._get_favorite_slot_options()
  option_keys = {option["key"] for option in options}

  assert "__starpilot_favorite_action__:distance_decrease" in option_keys
  assert "__starpilot_favorite_action__:distance_increase" in option_keys


def test_rivian_angle_favorite_requires_detected_extreme_harness(monkeypatch):
  options = [
    {"key": "RivianAngleControl", "requiresCapability": "HasRivianAngleHarness"},
    {"key": "NonGatedFavorite", "requiresCapability": ""},
  ]
  monkeypatch.setattr(the_galaxy, "_get_favorite_slot_options", lambda: options)

  monkeypatch.setattr(the_galaxy, "_get_has_rivian_angle_harness", lambda: False)
  assert [option["key"] for option in the_galaxy._get_available_favorite_slot_options()] == ["NonGatedFavorite"]

  monkeypatch.setattr(the_galaxy, "_get_has_rivian_angle_harness", lambda: True)
  assert [option["key"] for option in the_galaxy._get_available_favorite_slot_options()] == [
    "RivianAngleControl",
    "NonGatedFavorite",
  ]


def test_favorite_action_endpoint_increments_virtual_button_counter(monkeypatch):
  client, _ = _params_client(monkeypatch, {}, "tici")
  fake_memory = WritableFakeParams()
  monkeypatch.setattr(the_galaxy, "params_memory", fake_memory)

  response = client.post("/api/favorites/action", json={"key": "__starpilot_favorite_action__:distance_increase"})

  assert response.status_code == 200
  assert fake_memory.get_int("FavoriteVirtualAccelCruiseCounter") == 1


def test_alpha_longitudinal_toggle_writes_and_requests_offroad_cycle(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {
    "AlphaLongitudinalEnabled": False,
    "IsOnroad": False,
  }, "tici")
  monkeypatch.setattr(the_galaxy, "_get_alpha_longitudinal_available", lambda: True)

  response = client.put("/api/params", json={"key": "AlphaLongitudinalEnabled", "value": True})

  assert response.status_code == 200
  assert fake_params.values["AlphaLongitudinalEnabled"] is True
  assert fake_params.values["OnroadCycleRequested"] is True
  assert fake_params.writes == [
    ("AlphaLongitudinalEnabled", True),
    ("OnroadCycleRequested", True),
  ]


def test_alpha_longitudinal_toggle_rejects_onroad(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {
    "AlphaLongitudinalEnabled": False,
    "IsOnroad": True,
  }, "tici")
  monkeypatch.setattr(the_galaxy, "_get_alpha_longitudinal_available", lambda: True)

  response = client.put("/api/params", json={"key": "AlphaLongitudinalEnabled", "value": True})

  assert response.status_code == 403
  assert response.get_json()["error"] == "Cannot change Alpha Longitudinal while driving."
  assert fake_params.writes == []


def test_alpha_longitudinal_toggle_rejects_unsupported_vehicle(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {
    "AlphaLongitudinalEnabled": False,
    "IsOnroad": False,
  }, "tici")
  monkeypatch.setattr(the_galaxy, "_get_alpha_longitudinal_available", lambda: False)

  response = client.put("/api/params", json={"key": "AlphaLongitudinalEnabled", "value": True})

  assert response.status_code == 403
  assert response.get_json()["error"] == "Alpha Longitudinal is not available for the detected vehicle."
  assert fake_params.writes == []


def test_force_offroad_toggle_requires_live_park(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {
    "ForceOffroad": False,
    "ForceOnroad": False,
    "IsOnroad": True,
  }, "tici")
  monkeypatch.setattr(the_galaxy, "_get_vehicle_parked", lambda: True)

  response = client.put("/api/params", json={"key": "ForceOffroad", "value": True})

  assert response.status_code == 200
  assert response.get_json()["updated"] == {"ForceOffroad": True, "ForceOnroad": False}
  assert fake_params.values["ForceOffroad"] is True
  assert fake_params.values["ForceOnroad"] is False


def test_force_offroad_toggle_rejects_when_not_parked(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {
    "ForceOffroad": False,
    "IsOnroad": True,
  }, "tici")
  monkeypatch.setattr(the_galaxy, "_get_vehicle_parked", lambda: False)

  response = client.put("/api/params", json={"key": "ForceOffroad", "value": True})

  assert response.status_code == 403
  assert response.get_json()["error"] == "Force Offroad is only available while the vehicle is in Park."
  assert fake_params.writes == []


def test_curve_speed_controller_reset_clears_learned_data_offroad(monkeypatch):
  client, fake_params = _params_client(monkeypatch, {
    "IsOnroad": False,
    "CalibratedLateralAcceleration": 2.73,
    "CalibrationProgress": 48.0,
    "CurvatureData": {"0.01": {"average": 2.73, "count": 12}},
  }, "tici")
  fake_memory = WritableFakeParams({
    "CalibratedLateralAcceleration": 2.73,
    "CalibrationProgress": 48.0,
    "CurvatureData": {"0.01": {"average": 2.73, "count": 12}},
  })
  monkeypatch.setattr(the_galaxy, "params_memory", fake_memory)

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
  assert fake_memory.values == {
    "CalibratedLateralAcceleration": 2.0,
    "CalibrationProgress": 0.0,
  }
  assert fake_memory.removals == ["CurvatureData"]


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
