import io
import json
import subprocess
import time

import requests

from openpilot.system.vehicle_telemetry import core
from openpilot.system.vehicle_telemetry.setup import (
  TELEMETRY_SETUP_STATUS_FILENAME,
  SetupSessionState,
  TelemetrySetupService,
  active_telemetry_setup_token,
  choose_lan_ipv4,
  launch_vehicle_telemetry_setup,
  main,
  render_setup_page,
)


def test_setup_selects_only_private_wifi_or_ethernet_addresses():
  addresses = [
    ("rmnet_data0", "10.20.30.40"),
    ("wlan0", "8.8.8.8"),
    ("eth0", "192.168.10.20"),
    ("wlan0", "192.168.1.50"),
  ]
  assert choose_lan_ipv4(addresses) == "192.168.1.50"
  assert choose_lan_ipv4([("rmnet_data0", "10.20.30.40")]) == ""


def test_setup_page_is_self_contained_and_does_not_load_third_party_assets():
  page = render_setup_page(600)
  assert "EV Vehicle Telemetry" in page
  assert "How should this comma connect?" in page
  assert "Best choice" in page
  assert "Custom backend" in page
  assert "/api/backend" in page
  assert "RangeBridge on GitHub" in page
  assert "Telemetry runs while driving · no CAN writes · low CPU" in page
  assert "offroad only" not in page.lower()
  assert "setup-secret" not in page
  assert "X-Telemetry-Setup" not in page
  assert "Open StarPilot Galaxy controls" in page
  assert "<script src=" not in page
  assert "<link" not in page
  assert "<img" not in page
  script = page.split("<script nonce=", 1)[1].split(">", 1)[1].split("</script>", 1)[0]
  syntax = subprocess.run(["node", "--check", "-"], input=script, capture_output=True, text=True, check=False)
  assert syntax.returncode == 0, syntax.stderr


def test_setup_state_applies_local_mode_and_generates_fetch_token(tmp_path):
  state = SetupSessionState(tmp_path, "s" * 43, 1600.0, wall_time=lambda: 1000.0)
  assert state.start_mode("local")
  state.wait_for_job(timeout=2.0)

  payload = state.status_payload()
  config = core.load_vehicle_telemetry_config(tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME)
  assert payload["jobState"] == "succeeded"
  assert payload["generatedFetchToken"] == config["fetch"]["token"]
  assert config["mode"] == "local"
  assert config["fetch"]["enabled"]
  assert config["fetch"]["bindAddress"] == "0.0.0.0"

  first_token = config["fetch"]["token"]
  assert state.start_token_rotation()
  state.wait_for_job(timeout=2.0)
  rotated = core.load_vehicle_telemetry_config(tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME)["fetch"]["token"]
  assert rotated != first_token
  assert state.status_payload()["generatedFetchToken"] == rotated


def test_setup_local_mode_preserves_pairing_added_during_funnel_shutdown(tmp_path):
  config_path = tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME
  core.save_vehicle_telemetry_config({"push": {"token": "p" * 32}}, config_path)
  state = SetupSessionState(tmp_path, "s" * 43, 1600.0, wall_time=lambda: 1000.0)

  def pair_client_while_funnel_stops(_snapshot):
    def add_client(current):
      current["fetch"]["clients"].append({"name": "RangeBridge", "token": "c" * 32, "createdAt": 1000.0})
      return current

    core.update_vehicle_telemetry_config(add_client, config_path)

  state._disable_managed_funnel = pair_client_while_funnel_stops
  assert state.start_mode("local")
  state.wait_for_job(timeout=2.0)

  config = core.load_vehicle_telemetry_config(config_path)
  assert state.status_payload()["jobState"] == "succeeded"
  assert state.status_payload()["generatedFetchToken"] == ""
  assert config["fetch"]["clients"][0]["name"] == "RangeBridge"
  assert config["fetch"]["token"] == ""
  assert config["push"]["token"] == "p" * 32


def test_setup_state_runs_tailscale_install_once_in_background(tmp_path):
  calls = []
  base = tmp_path / "tailscale"

  def installer(_base):
    calls.append(_base)
    base.mkdir()
    for name in ("tailscale", "tailscaled"):
      path = base / name
      path.write_text(name)
      path.chmod(0o700)
    return {
      "binaryPath": str(base / "tailscale"),
      "daemonBinaryPath": str(base / "tailscaled"),
      "socketPath": str(base / "tailscaled.sock"),
      "stateDirectory": str(base / "state"),
    }

  state = SetupSessionState(tmp_path, "s" * 43, 1600.0, installer=installer, tailscale_base=base, wall_time=lambda: 1000.0)
  assert state.start_mode("tailscale")
  assert not state.start_mode("local")
  state.wait_for_job(timeout=2.0)
  assert state.status_payload()["jobState"] == "succeeded"
  assert core.load_vehicle_telemetry_config(tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME)["mode"] == "tailscale"
  assert calls == [base]


def test_setup_state_configures_send_only_custom_backend_and_preserves_token(tmp_path):
  state = SetupSessionState(tmp_path, "s" * 43, 1600.0, wall_time=lambda: 1000.0)
  assert state.start_backend({
    "url": "https://telemetry.example/v1/ingest",
    "token": "b" * 32,
    "vehicleId": "my-ev",
    "vehicleName": "My EV",
  })
  state.wait_for_job(timeout=2.0)

  config = core.load_vehicle_telemetry_config(tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME)
  assert config["mode"] == "send"
  assert not config["fetch"]["enabled"]
  assert config["push"]["enabled"]
  assert config["push"]["url"] == "https://telemetry.example/v1/ingest"
  assert config["push"]["token"] == "b" * 32
  assert state.status_payload()["config"]["push"]["hasToken"]
  assert "token" not in state.status_payload()["config"]["push"]

  assert state.start_backend({"url": "https://new.example/ingest", "token": "", "vehicleId": "my-ev"})
  state.wait_for_job(timeout=2.0)
  updated = core.load_vehicle_telemetry_config(tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME)
  assert updated["push"]["url"] == "https://new.example/ingest"
  assert updated["push"]["token"] == "b" * 32

  assert state.start_mode("off")
  state.wait_for_job(timeout=2.0)
  disabled = core.load_vehicle_telemetry_config(tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME)
  assert disabled["mode"] == "off"
  assert not disabled["push"]["enabled"]


def test_setup_backend_uses_latest_secret_and_preserves_concurrent_pairing(tmp_path):
  config_path = tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME
  core.save_vehicle_telemetry_config(
    {
      "mode": "tailscale",
      "fetch": {"enabled": True, "token": "f" * 32},
      "push": {
        "url": "https://old.example/ingest",
        "token": "o" * 32,
      },
    },
    config_path,
  )
  state = SetupSessionState(tmp_path, "s" * 43, 1600.0, wall_time=lambda: 1000.0)

  def update_secrets_while_funnel_stops(_snapshot):
    def update_secrets(current):
      current["push"]["token"] = "n" * 32
      current["fetch"]["clients"].append({"name": "RangeBridge", "token": "c" * 32, "createdAt": 1000.0})
      return current

    core.update_vehicle_telemetry_config(update_secrets, config_path)

  state._disable_managed_funnel = update_secrets_while_funnel_stops
  assert state.start_backend({"url": "https://new.example/ingest", "token": "", "vehicleId": "my-ev"})
  state.wait_for_job(timeout=2.0)

  config = core.load_vehicle_telemetry_config(config_path)
  assert state.status_payload()["jobState"] == "succeeded"
  assert config["push"]["token"] == "n" * 32
  assert config["push"]["url"] == "https://new.example/ingest"
  assert config["fetch"]["clients"][0]["name"] == "RangeBridge"


def test_setup_state_rejects_insecure_custom_backend(tmp_path):
  state = SetupSessionState(tmp_path, "s" * 43, 1600.0, wall_time=lambda: 1000.0)
  assert state.start_backend({"url": "http://telemetry.example/ingest", "token": "b" * 32})
  state.wait_for_job(timeout=2.0)
  assert state.status_payload()["jobState"] == "failed"
  assert core.load_vehicle_telemetry_config(tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME)["mode"] == "off"


def test_launcher_keeps_setup_token_out_of_process_arguments(tmp_path):
  class FakeStdin(io.BytesIO):
    def close(self):
      self.captured = self.getvalue()
      super().close()

  class FakeProcess:
    pid = 4321

    def __init__(self):
      self.stdin = FakeStdin()

  process = FakeProcess()
  calls = []

  def popen(args, **kwargs):
    calls.append((args, kwargs))
    return process

  session = launch_vehicle_telemetry_setup(
    tmp_path,
    addresses=[("wlan0", "192.168.1.50")],
    duration_seconds=600,
    popen=popen,
    python_executable="python-test",
    startup_timeout=0,
  )
  args, kwargs = calls[0]
  assert args[:4] == ["python-test", "-m", "openpilot.system.vehicle_telemetry.setup", "serve"]
  assert session["url"].startswith("http://192.168.1.50:7767/?setup=")
  assert session["token"] not in " ".join(args)
  assert process.stdin.captured.decode().strip() == session["token"]
  assert kwargs["start_new_session"] is True
  status = json.loads((tmp_path / TELEMETRY_SETUP_STATUS_FILENAME).read_text())
  assert status["pid"] == 4321
  assert (tmp_path / TELEMETRY_SETUP_STATUS_FILENAME).stat().st_mode & 0o077 == 0


def test_live_setup_token_requires_owner_only_unexpired_running_session(tmp_path):
  token = "s" * 43
  path = tmp_path / TELEMETRY_SETUP_STATUS_FILENAME
  path.write_text(json.dumps({
    "state": "running",
    "pid": 123,
    "url": f"http://192.168.1.50:7767/?setup={token}",
    "expiresAt": 1600.0,
  }))
  path.chmod(0o600)

  from openpilot.system.vehicle_telemetry import setup
  original = setup._pid_is_running
  setup._pid_is_running = lambda pid: pid == 123
  try:
    assert active_telemetry_setup_token(tmp_path, wall_time=1000.0) == token
    assert active_telemetry_setup_token(tmp_path, wall_time=1601.0) == ""
    path.chmod(0o644)
    assert active_telemetry_setup_token(tmp_path, wall_time=1000.0) == ""
  finally:
    setup._pid_is_running = original


def test_launch_cli_never_prints_setup_capability(monkeypatch, capsys):
  secret = "s" * 43
  monkeypatch.setattr(
    "openpilot.system.vehicle_telemetry.setup.launch_vehicle_telemetry_setup",
    lambda *args, **kwargs: {
      "url": f"http://192.168.1.50:7767/?setup={secret}",
      "expiresAt": time.time() + 600,  # noqa: TID251
      "pid": 4321,
    },
  )
  assert main(["launch"]) == 0
  output = capsys.readouterr().out
  assert secret not in output
  assert "?setup=" not in output
  assert json.loads(output)["host"] == "192.168.1.50"


def test_setup_http_requires_session_token_and_bounds_request_body(tmp_path):
  token = "s" * 43
  state = SetupSessionState(tmp_path, token, 1600.0, wall_time=lambda: 1000.0)
  service = TelemetrySetupService(state)
  try:
    service.start("127.0.0.1", 0)
    port = service.port
    base = f"http://127.0.0.1:{port}"

    assert requests.get(base + "/", timeout=2.0).status_code == 404
    page = requests.get(base + f"/?setup={token}", timeout=2.0)
    assert page.status_code == 200
    assert page.headers["Cache-Control"] == "no-store"
    assert "default-src 'none'" in page.headers["Content-Security-Policy"]
    assert "HttpOnly" in page.headers["Set-Cookie"]
    assert "SameSite=Strict" in page.headers["Set-Cookie"]
    assert token not in page.text

    headers = {"X-Telemetry-Setup": token, "Content-Type": "application/json"}
    started = requests.post(base + "/api/mode", headers=headers, json={"mode": "local"}, timeout=2.0)
    assert started.status_code == 202
    state.wait_for_job(timeout=2.0)
    status = requests.get(base + "/api/status", headers={"X-Telemetry-Setup": token}, timeout=2.0)
    assert status.status_code == 200
    assert status.json()["config"]["mode"] == "local"
    assert "token" not in status.json()["config"]["fetch"]

    backend = requests.post(base + "/api/backend", headers=headers, json={
      "url": "https://telemetry.example/v1/ingest",
      "token": "b" * 32,
      "vehicleId": "my-ev",
    }, timeout=2.0)
    assert backend.status_code == 202
    state.wait_for_job(timeout=2.0)
    status = requests.get(base + "/api/status", headers={"X-Telemetry-Setup": token}, timeout=2.0)
    assert status.json()["config"]["mode"] == "send"
    assert status.json()["config"]["push"]["enabled"]

    oversized = requests.post(
      base + "/api/mode",
      headers=headers,
      data=b"x" * 17000,
      timeout=2.0,
    )
    assert oversized.status_code == 413
  finally:
    service.stop()
