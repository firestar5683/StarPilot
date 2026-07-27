import json
import socket
import time

from types import SimpleNamespace

import requests
import pytest

from openpilot.common.params import Params
from openpilot.system.vehicle_telemetry import core
from openpilot.system.vehicle_telemetry import daemon
from openpilot.system.vehicle_telemetry.http_server import TimedLoader, TokenBucket, VehicleTelemetryHTTPService


@pytest.fixture(autouse=True)
def reset_runtime_adapter_state():
  core.reset_vehicle_telemetry_runtime()
  yield
  core.reset_vehicle_telemetry_runtime()


def test_snapshot_uses_generic_fields_and_feature_detects_optional_values():
  snapshot = core.build_vehicle_telemetry_snapshot(
    SimpleNamespace(
      fuelGauge=0.775,
      distanceToEmpty=408000.0,
      charging=True,
      chargingPortConnected=True,
      chargingTimeRemaining=18000.0,
      vEgo=12.3456,
      standstill=False,
    ),
    timestamp=1234.5,
    vehicle_fingerprint="KIA EV9",
  )

  assert snapshot == {
    "schemaVersion": 1,
    "source": "openpilot carState",
    "updatedAt": 1234.5,
    "vehicleFingerprint": "KIA EV9",
    "stateOfChargePercent": 77.5,
    "distanceToEmptyKilometers": 408.0,
    "isCharging": True,
    "isPluggedIn": True,
    "minutesToFull": 300,
    "speedMetersPerSecond": 12.346,
    "standstill": False,
  }
  fuel_only = core.build_vehicle_telemetry_snapshot(SimpleNamespace(fuelGauge=0.5), timestamp=1.0)
  assert fuel_only["stateOfChargePercent"] == 50.0
  assert "distanceToEmptyKilometers" not in fuel_only


def test_default_zero_car_state_is_not_valid_telemetry():
  assert core.build_vehicle_telemetry_snapshot(SimpleNamespace(fuelGauge=0.0, distanceToEmpty=0.0)) is None


def test_snapshot_honors_optional_per_field_validity():
  snapshot = core.build_vehicle_telemetry_snapshot(
    SimpleNamespace(
      fuelGauge=0.0,
      distanceToEmpty=408000.0,
      charging=False,
      chargingPortConnected=False,
      vehicleTelemetrySocValid=False,
      vehicleTelemetryDteValid=True,
      vehicleTelemetryChargingValid=False,
      vehicleTelemetryChargePortValid=True,
    ),
    timestamp=1234.5,
  )

  assert snapshot is not None
  assert "stateOfChargePercent" not in snapshot
  assert snapshot["distanceToEmptyKilometers"] == 408.0
  assert "isCharging" not in snapshot
  assert snapshot["isPluggedIn"] is False


def test_stock_daemon_defaults_to_car_state():
  assert daemon.DEFAULT_CAR_STATE_SERVICE == "carState"


def test_clock_validation_and_cached_timestamp(monkeypatch):
  state = SimpleNamespace(fuelGauge=0.5)
  monkeypatch.setattr(daemon, "system_time_valid", lambda: False)
  assert daemon.build_clock_valid_vehicle_telemetry_snapshot(state, timestamp=1000.0) is None

  monkeypatch.setattr(daemon, "system_time_valid", lambda: True)
  assert daemon.build_clock_valid_vehicle_telemetry_snapshot(state, timestamp=2000.0)["updatedAt"] == 2000.0
  assert daemon.cached_snapshot_timestamp_is_plausible({"updatedAt": 999.0}, now=1000.0)
  assert not daemon.cached_snapshot_timestamp_is_plausible({"updatedAt": 1001.0}, now=1000.0)


def test_cached_snapshot_rejects_future_timestamp_and_invalid_energy_schema(tmp_path, monkeypatch):
  cache_path = tmp_path / core.VEHICLE_TELEMETRY_CACHE_FILENAME
  monkeypatch.setattr(core.time, "time", lambda: 1000.0)

  invalid_snapshots = (
    {"schemaVersion": 1, "updatedAt": 1000.1, "stateOfChargePercent": 80.0},
    {"schemaVersion": 2, "updatedAt": 999.0, "stateOfChargePercent": 80.0},
    {"schemaVersion": 1, "updatedAt": 999.0, "stateOfChargePercent": "80"},
    {"schemaVersion": 1, "updatedAt": 999.0, "stateOfChargePercent": 101.0},
    {"schemaVersion": 1, "updatedAt": 999.0, "distanceToEmptyKilometers": 900.0},
    {"schemaVersion": 1, "updatedAt": 999.0, "stateOfChargePercent": 0.0},
    {"schemaVersion": 1, "updatedAt": 999.0, "stateOfChargePercent": 80.0, "isCharging": 1},
    {"schemaVersion": 1, "updatedAt": 999.0, "stateOfChargePercent": 80.0, "minutesToFull": 1.5},
  )
  for snapshot in invalid_snapshots:
    cache_path.write_text(json.dumps(snapshot), encoding="utf-8")
    cache_path.chmod(0o600)
    assert core.VehicleTelemetryCache(cache_path).load() is None
    assert core.telemetry_response(snapshot, now=1000.0) is None


def test_cache_defers_only_future_timestamp_check_until_wall_clock_sync(tmp_path, monkeypatch):
  cache_path = tmp_path / core.VEHICLE_TELEMETRY_CACHE_FILENAME
  cache_path.write_text(json.dumps({
    "schemaVersion": 1,
    "updatedAt": 1_750_000_000.0,
    "stateOfChargePercent": 80.0,
    "isCharging": False,
  }), encoding="utf-8")
  cache_path.chmod(0o600)

  # Before clock sync, the otherwise valid persisted Unix timestamp is future.
  monkeypatch.setattr(core.time, "time", lambda: 1_000.0)
  cache = core.VehicleTelemetryCache(cache_path)
  assert cache.latest is None
  pending = cache.load_before_clock_sync()
  assert pending == {
    "schemaVersion": 1,
    "updatedAt": 1_750_000_000.0,
    "stateOfChargePercent": 80.0,
    "isCharging": False,
  }

  # Once time is trustworthy, normal validation accepts the retained record.
  assert core.validated_vehicle_telemetry_snapshot(pending, now=1_750_000_001.0) == pending

  # The deferred path still enforces every non-time schema constraint.
  cache_path.write_text(json.dumps({
    "schemaVersion": 1,
    "updatedAt": 1_750_000_000.0,
    "stateOfChargePercent": "80",
  }), encoding="utf-8")
  assert core.VehicleTelemetryCache(cache_path).load_before_clock_sync() is None


def test_future_timestamp_remains_rejected_for_storage_and_serving_after_sync(tmp_path, monkeypatch):
  monkeypatch.setattr(core.time, "time", lambda: 2_000.0)
  future = {"schemaVersion": 1, "updatedAt": 2_001.0, "stateOfChargePercent": 80.0}
  cache = core.VehicleTelemetryCache(tmp_path / core.VEHICLE_TELEMETRY_CACHE_FILENAME)

  assert not cache.store(future, monotonic_now=1.0)
  assert not cache.path.exists()
  assert core.telemetry_response(future, now=2_000.0) is None


def test_cached_snapshot_is_schema_bounded_before_serving():
  response = core.telemetry_response(
    {
      "schemaVersion": 1,
      "source": "StarPilot carState",
      "updatedAt": 999.0,
      "stateOfChargePercent": 80,
      "distanceToEmptyKilometers": 408,
      "isCharging": False,
      "isPluggedIn": False,
      "speedMetersPerSecond": 0,
      "standstill": True,
      "untrustedExtraField": "must not escape the cache boundary",
    },
    now=1000.0,
  )

  assert response is not None
  assert response["stateOfChargePercent"] == 80.0
  assert response["distanceToEmptyKilometers"] == 408.0
  assert response["ageSeconds"] == 1.0
  assert "untrustedExtraField" not in response


def test_config_modes_are_owner_only_and_secrets_are_redacted(tmp_path):
  path = tmp_path / "config.json"
  saved = core.save_vehicle_telemetry_config(
    {
      "mode": "frp",
      "fetch": {"enabled": True, "token": "f" * 32, "port": 17766},
      "push": {
        "enabled": True,
        "url": "https://telemetry.example/ingest",
        "token": "p" * 32,
        "vehicleId": "test-vehicle",
      },
      "tunnel": {
        "binaryPath": "/opt/frpc",
        "serverAddress": "gateway.example",
        "token": "t" * 32,
        "subdomainHost": "telemetry.example",
        "subdomain": "auto",
      },
    },
    path,
  )
  assert saved["mode"] == "frp"
  assert saved["fetch"]["enabled"] and saved["push"]["enabled"]
  assert path.stat().st_mode & 0o077 == 0

  public = core.public_vehicle_telemetry_config(saved)
  assert public["fetch"]["hasToken"] and public["push"]["hasToken"] and public["tunnel"]["hasToken"]
  assert "token" not in public["fetch"]
  assert "token" not in public["push"]
  assert "token" not in public["tunnel"]

  path.chmod(0o640)
  assert core.load_vehicle_telemetry_config(path)["mode"] == "off"


def test_fetch_requires_long_bearer_token_and_constant_time_comparison(tmp_path):
  token_config = core.save_vehicle_telemetry_config(
    {
      "mode": "local",
      "fetch": {"enabled": True, "token": "s" * 32},
    },
    tmp_path / "config.json",
  )
  assert core.is_fetch_authorized(token_config, f"Bearer {'s' * 32}")
  assert not core.is_fetch_authorized(token_config, f"Bearer {'x' * 32}")
  assert not core.is_fetch_authorized({"fetch": {"enabled": True, "token": "short"}}, "Bearer short")


def test_send_mode_disables_inbound_fetch_but_keeps_custom_publisher(tmp_path):
  config = core.save_vehicle_telemetry_config(
    {
      "mode": "send",
      "fetch": {"enabled": True, "token": "f" * 32},
      "push": {
        "enabled": True,
        "url": "https://telemetry.example/v1/ingest",
        "token": "p" * 32,
      },
    },
    tmp_path / "config.json",
  )
  assert config["mode"] == "send"
  assert not config["fetch"]["enabled"]
  assert config["push"]["enabled"]


def test_standalone_http_api_enforces_bearer_and_reports_cached_data(tmp_path):
  token = "a" * 32
  config_path = tmp_path / "config.json"
  cache_path = tmp_path / core.VEHICLE_TELEMETRY_CACHE_FILENAME
  core.save_vehicle_telemetry_config(
    {
      "mode": "local",
      "fetch": {"enabled": True, "token": token, "bindAddress": "127.0.0.1", "port": 17766},
    },
    config_path,
  )
  core.VehicleTelemetryCache(cache_path).store(
    {
      "schemaVersion": 1,
      "source": "openpilot carState",
      "updatedAt": 1000.0,
      "stateOfChargePercent": 80.0,
    }
  )
  tunnel_status_path = tmp_path / "tunnel.json"
  tunnel_status_path.write_text(json.dumps({"state": "needs-login", "ownerURL": "https://login.tailscale.com/a/secret"}))
  tunnel_status_path.chmod(0o600)

  previous_provider = core._data_dir_provider
  core.configure_vehicle_telemetry_runtime(data_dir_provider=lambda: tmp_path)
  service = VehicleTelemetryHTTPService(config_path=config_path, tunnel_status_path=tunnel_status_path)
  try:
    service.start("127.0.0.1", 0)
    port = service._server.server_address[1]
    url = f"http://127.0.0.1:{port}/api/vehicle/telemetry"
    unauthorized = requests.get(url, timeout=2.0)
    assert unauthorized.status_code == 401
    response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=2.0)
    assert response.status_code == 200
    assert response.json()["stateOfChargePercent"] == 80.0
    assert response.headers["Cache-Control"] == "no-store"
    status = requests.get(f"http://127.0.0.1:{port}/api/vehicle/telemetry/status", headers={"Authorization": f"Bearer {token}"}, timeout=2.0)
    assert "ownerURL" not in status.json()["tunnel"]
  finally:
    service.stop()
    core._data_dir_provider = previous_provider


def test_http_token_bucket_and_read_cache_have_fixed_work(monkeypatch):
  clock = [100.0]
  limiter = TokenBucket(1.0, 2, monotonic=lambda: clock[0])
  assert limiter.consume()
  assert limiter.consume()
  assert not limiter.consume()
  clock[0] += 1.0
  assert limiter.consume()

  loads = []
  loader = TimedLoader(lambda: loads.append(clock[0]) or {"loadedAt": clock[0]}, cache_seconds=1.0, monotonic=lambda: clock[0])
  assert loader.get() == loader.get()
  assert loads == [101.0]
  clock[0] += 1.0
  assert loader.get()["loadedAt"] == 102.0
  assert loads == [101.0, 102.0]


def test_config_loader_bounds_idle_disk_reads():
  clock = [100.0]
  loads = []
  loader = core.VehicleTelemetryConfigLoader(
    reload_seconds=5.0,
    monotonic=lambda: clock[0],
    loader=lambda: loads.append(clock[0]) or core.default_vehicle_telemetry_config(),
  )
  assert loader.get() is loader.get()
  assert loads == [100.0]
  clock[0] += 5.0
  loader.get()
  assert loads == [100.0, 105.0]


def test_http_service_rejects_overload_without_starting_another_handler(tmp_path):
  service = VehicleTelemetryHTTPService(
    config_path=tmp_path / "config.json",
    server_options={"max_concurrent_requests": 1},
  )
  try:
    service.start("127.0.0.1", 0)
    assert service._server.request_slots.acquire(blocking=False)
    port = service._server.server_address[1]
    response = requests.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
    assert response.status_code == 503
    assert response.json() == {"error": "Service unavailable."}
  finally:
    if service._server is not None:
      service._server.request_slots.release()
    service.stop()


def test_http_service_bounds_all_requests_and_failed_auth(tmp_path):
  token = "a" * 32
  config_path = tmp_path / "config.json"
  core.save_vehicle_telemetry_config(
    {"mode": "local", "fetch": {"enabled": True, "token": token}},
    config_path,
  )
  service = VehicleTelemetryHTTPService(
    config_path=config_path,
    server_options={
      "requests_per_second": 0,
      "request_burst": 3,
      "failed_auths_per_second": 0,
      "failed_auth_burst": 1,
    },
  )
  try:
    service.start("127.0.0.1", 0)
    port = service._server.server_address[1]
    url = f"http://127.0.0.1:{port}/api/vehicle/telemetry"
    first = requests.get(url, headers={"Authorization": "Bearer wrong"}, timeout=2.0)
    second = requests.get(url, headers={"Authorization": "Bearer still-wrong"}, timeout=2.0)
    limited = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=2.0)
    exhausted = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=2.0)
    assert first.status_code == 401
    assert second.status_code == 429
    assert limited.status_code == 503  # Authorized, but no telemetry has been cached.
    assert exhausted.status_code == 429
  finally:
    service.stop()


def test_authenticated_fetch_api_remains_available_onroad(tmp_path):
  core.configure_vehicle_telemetry_runtime(data_dir_provider=lambda: tmp_path)
  Params().put_bool("IsOnroad", True)
  token = "a" * 32
  config_path = tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME
  core.save_vehicle_telemetry_config(
    {"mode": "local", "fetch": {"enabled": True, "token": token}},
    config_path,
  )
  core.VehicleTelemetryCache().store({
    "schemaVersion": 1,
    "updatedAt": time.time(),  # noqa: TID251
    "stateOfChargePercent": 72.5,
  })

  service = VehicleTelemetryHTTPService(config_path=config_path)
  try:
    service.start("127.0.0.1", 0)
    port = service._server.server_address[1]
    response = requests.get(
      f"http://127.0.0.1:{port}/api/vehicle/telemetry",
      headers={"Authorization": f"Bearer {token}"},
      timeout=2.0,
    )
    assert Params().get_bool("IsOnroad")
    assert response.status_code == 200
    assert response.json()["stateOfChargePercent"] == 72.5
  finally:
    service.stop()


def test_http_service_rejects_headers_before_they_exceed_fixed_buffer(tmp_path):
  service = VehicleTelemetryHTTPService(config_path=tmp_path / "config.json")
  try:
    service.start("127.0.0.1", 0)
    port = service._server.server_address[1]
    with socket.create_connection(("127.0.0.1", port), timeout=2.0) as connection:
      connection.sendall(b"GET /health HTTP/1.1\r\nX-Fill: " + b"a" * 9000 + b"\r\n\r\n")
      response = connection.recv(4096)
    assert response.startswith(b"HTTP/1.0 431 ")
  finally:
    service.stop()


def test_cache_heartbeat_and_legacy_range_alias(tmp_path):
  cache_path = tmp_path / "latest.json"
  cache = core.VehicleTelemetryCache(cache_path, heartbeat_seconds=60)
  snapshot = {"schemaVersion": 1, "updatedAt": 1000.0, "stateOfChargePercent": 80.0}
  assert cache.store(snapshot, monotonic_now=100.0)
  assert not cache.store(snapshot, monotonic_now=120.0)
  assert cache.store(snapshot, monotonic_now=161.0)

  cache_path.write_text(
    json.dumps(
      {
        "schemaVersion": 1,
        "source": "StarPilot carState",
        "updatedAt": 1000.0,
        "estimatedRangeKilometers": 408.0,
        "distanceToEmptyKilometers": 408.0,
      }
    )
  )
  cache_path.chmod(0o600)
  loaded = core.VehicleTelemetryCache(cache_path).load()
  assert loaded["distanceToEmptyKilometers"] == 408.0
  assert "estimatedRangeKilometers" not in loaded


def test_default_cache_heartbeat_keeps_unchanged_fresh_samples_live(tmp_path, monkeypatch):
  cache_path = tmp_path / "latest.json"
  monkeypatch.setattr(core.time, "time", lambda: 2_000.0)
  cache = core.VehicleTelemetryCache(cache_path)
  assert cache.heartbeat_seconds == core.VEHICLE_TELEMETRY_HEARTBEAT_SECONDS
  assert cache.heartbeat_seconds < core.VEHICLE_TELEMETRY_LIVE_SECONDS

  first = {"schemaVersion": 1, "updatedAt": 1_990.0, "stateOfChargePercent": 80.0}
  unchanged_fresh = {**first, "updatedAt": 2_000.0}
  assert cache.store(first, monotonic_now=100.0)
  assert not cache.store(unchanged_fresh, monotonic_now=109.9)
  assert cache.store(unchanged_fresh, monotonic_now=110.0)
  assert core.telemetry_response(cache.load(), now=2_009.9)["isLive"]


def test_first_fresh_sample_refreshes_loaded_cache_immediately(tmp_path, monkeypatch):
  cache_path = tmp_path / "latest.json"
  cache_path.write_text(json.dumps({
    "schemaVersion": 1,
    "updatedAt": 1_000.0,
    "stateOfChargePercent": 80.0,
  }), encoding="utf-8")
  cache_path.chmod(0o600)
  monkeypatch.setattr(core.time, "time", lambda: 2_000.0)
  cache = core.VehicleTelemetryCache(cache_path)

  assert cache.store({
    "schemaVersion": 1,
    "updatedAt": 2_000.0,
    "stateOfChargePercent": 80.0,
  }, monotonic_now=1.0)
  assert cache.load()["updatedAt"] == 2_000.0


class FakeResponse:
  status_code = 202

  def __init__(self):
    self.closed = False

  def close(self):
    self.closed = True


class FakeSession:
  def __init__(self):
    self.trust_env = True
    self.request = None
    self.response = FakeResponse()

  def post(self, *args, **kwargs):
    self.request = (args, kwargs)
    return self.response


def test_publisher_disables_redirects_and_keeps_token_in_header_only(tmp_path):
  session = FakeSession()
  publisher = core.VehicleTelemetryPublisher(status_path=tmp_path / "status.json", session=session)
  push = core.default_vehicle_telemetry_config()["push"] | {
    "enabled": True,
    "url": "https://telemetry.example/ingest",
    "token": "t" * 32,
    "vehicleId": "vehicle",
  }
  success, status = publisher._post(push, {"updatedAt": 1234.5, "stateOfChargePercent": 80.0})
  assert success and status == 202
  assert session.trust_env is False
  assert session.request[1]["allow_redirects"] is False
  assert session.request[1]["stream"] is True
  assert session.request[1]["headers"]["Authorization"] == f"Bearer {'t' * 32}"
  assert "token" not in session.request[1]["json"]
  assert session.response.closed


def test_live_cache_write_skips_fsync(tmp_path, monkeypatch):
  fsync_calls = []
  monkeypatch.setattr(core.os, "fsync", lambda descriptor: fsync_calls.append(descriptor))
  core.VehicleTelemetryCache(tmp_path / "latest.json").store(
    {
      "schemaVersion": 1,
      "updatedAt": 1000.0,
      "stateOfChargePercent": 80.0,
    }
  )
  assert fsync_calls == []
  core.save_vehicle_telemetry_config({}, tmp_path / "config.json")
  assert len(fsync_calls) == 1


def test_config_rejects_relative_executable_and_unsafe_hostname(tmp_path):
  config = core.save_vehicle_telemetry_config(
    {
      "mode": "tailscale",
      "tunnel": {
        "binaryPath": "./frpc;bad",
        "serverAddress": "gateway.example;bad",
        "subdomain": "bad/value",
      },
      "tailscale": {
        "binaryPath": "./tailscale",
        "daemonBinaryPath": "/data/tailscale/tailscaled",
        "hostname": "bad/value",
        "httpsPort": 8443,
      },
    },
    tmp_path / "config.json",
  )
  assert config["mode"] == "tailscale"
  assert config["tunnel"]["binaryPath"] == "/data/vehicle_telemetry/bin/frpc"
  assert config["tunnel"]["serverAddress"] == ""
  assert config["tunnel"]["subdomain"] == "auto"
  assert config["tailscale"]["binaryPath"] == "/data/tailscale/tailscale"
  assert config["tailscale"]["hostname"] == "auto"
  assert config["tailscale"]["httpsPort"] == 443
  public = core.public_vehicle_telemetry_config(config)
  assert public["tailscale"]["socketPath"] == "/data/tailscale/tailscaled.sock"
