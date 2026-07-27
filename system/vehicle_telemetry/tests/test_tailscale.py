import hashlib
import io
import json
import tarfile

from pathlib import Path
from types import SimpleNamespace

from openpilot.system.vehicle_telemetry import core
from openpilot.system.vehicle_telemetry import tailscale
from openpilot.system.vehicle_telemetry.core import load_vehicle_telemetry_status
from openpilot.system.vehicle_telemetry.tailscale import (
  TAILSCALE_PACKAGE_BASE_URL,
  TAILSCALE_STATUS_FILENAME,
  TailscaleFunnelController,
  _status_error,
  begin_tailscale_login,
  enable_personal_tailscale_relay,
  ensure_tailscale_hostname,
  install_tailscale,
  latest_tailscale_version,
)


class FakeResponse:
  def __init__(self, payload):
    self.payload = payload
    self.headers = {"Content-Length": str(len(payload))}
    self.closed = False

  def raise_for_status(self):
    return None

  def iter_content(self, chunk_size):
    for offset in range(0, len(self.payload), max(1, chunk_size)):
      yield self.payload[offset : offset + chunk_size]

  def close(self):
    self.closed = True


class FakeSession:
  def __init__(self, responses):
    self.responses = responses
    self.calls = []

  def get(self, url, **kwargs):
    self.calls.append((url, kwargs))
    return self.responses[url]


def _tailscale_archive(version="1.98.9", architecture="arm64"):
  output = io.BytesIO()
  directory = f"tailscale_{version}_{architecture}"
  with tarfile.open(fileobj=output, mode="w:gz") as archive:
    for name, content in (("tailscale", b"client"), ("tailscaled", b"daemon")):
      info = tarfile.TarInfo(f"{directory}/{name}")
      info.size = len(content)
      archive.addfile(info, io.BytesIO(content))
    escaped = tarfile.TarInfo("../../must-not-extract")
    escaped.size = 4
    archive.addfile(escaped, io.BytesIO(b"nope"))
  return output.getvalue()


def test_latest_version_and_installer_verify_checksum_and_extract_only_binaries(tmp_path):
  archive = _tailscale_archive()
  filename = "tailscale_1.98.9_arm64.tgz"
  archive_url = f"{TAILSCALE_PACKAGE_BASE_URL}/{filename}"
  responses = {
    f"{TAILSCALE_PACKAGE_BASE_URL}/": FakeResponse(b"tailscale_1.90.1_arm64.tgz tailscale_1.98.9_arm64.tgz"),
    f"{archive_url}.sha256": FakeResponse((hashlib.sha256(archive).hexdigest() + f"  {filename}\n").encode()),
    archive_url: FakeResponse(archive),
  }

  assert latest_tailscale_version("tailscale_1.2.3_arm64.tgz tailscale_1.12.0_arm64.tgz", "arm64") == "1.12.0"
  installed = install_tailscale(tmp_path / "tailscale", session=FakeSession(responses), architecture="arm64")

  assert installed["version"] == "1.98.9"
  assert Path(installed["binaryPath"]).read_bytes() == b"client"
  assert Path(installed["daemonBinaryPath"]).read_bytes() == b"daemon"
  assert Path(installed["binaryPath"]).stat().st_mode & 0o077 == 0
  assert not (tmp_path / "must-not-extract").exists()
  assert not (tmp_path / filename).exists()


def test_generated_tailscale_hostname_is_private_and_stable(tmp_path):
  first = ensure_tailscale_hostname(tmp_path)
  second = ensure_tailscale_hostname(tmp_path)
  assert first == second
  assert first.startswith("vt-")
  assert len(first) == 19
  assert (tmp_path / "tailscale_hostname").stat().st_mode & 0o077 == 0


def test_login_returns_only_tailscale_owner_url():
  config = {
    "binaryPath": "/data/tailscale/tailscale",
    "socketPath": "/data/tailscale/tailscaled.sock",
  }

  commands = []

  def run(args, **kwargs):
    commands.append(args)
    return SimpleNamespace(returncode=1, stdout="To authenticate, visit https://login.tailscale.com/a/test", stderr="")

  assert begin_tailscale_login(config, "vt-test", run=run) == "https://login.tailscale.com/a/test"
  assert "--ssh=false" in commands[0]
  assert "--accept-dns=false" in commands[0]
  assert "login.tailscale.com" not in _status_error("Approve at https://login.tailscale.com/admin/funnel?node=secret")


def test_enable_relay_generates_one_token_and_loopback_config(tmp_path):
  base = tmp_path / "tailscale"

  def installer(_base):
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

  config_path = tmp_path / "config.json"
  config, generated = enable_personal_tailscale_relay(
    config_path=config_path,
    data_dir=tmp_path,
    installer=installer,
    base_dir=base,
  )
  assert config["mode"] == "tailscale"
  assert config["fetch"]["enabled"]
  assert config["fetch"]["bindAddress"] == "127.0.0.1"
  assert len(generated) >= 32

  _, second_generated = enable_personal_tailscale_relay(config_path=config_path, data_dir=tmp_path, installer=installer, base_dir=base)
  assert second_generated == ""


def test_enable_relay_preserves_config_updates_made_during_install(tmp_path):
  base = tmp_path / "tailscale"
  config_path = tmp_path / "config.json"
  core.save_vehicle_telemetry_config({"push": {"token": "p" * 32}}, config_path)

  def installer(_base):
    base.mkdir()
    for name in ("tailscale", "tailscaled"):
      path = base / name
      path.write_text(name)
      path.chmod(0o700)

    def pair_client(current):
      current["fetch"]["clients"].append({"name": "RangeBridge", "token": "c" * 32, "createdAt": 1000.0})
      current["tailscale"]["hostname"] = "owner-selected"
      return current

    core.update_vehicle_telemetry_config(pair_client, config_path)
    return {
      "binaryPath": str(base / "tailscale"),
      "daemonBinaryPath": str(base / "tailscaled"),
      "socketPath": str(base / "tailscaled.sock"),
      "stateDirectory": str(base / "state"),
    }

  config, generated = enable_personal_tailscale_relay(
    config_path=config_path,
    data_dir=tmp_path,
    installer=installer,
    base_dir=base,
  )

  assert generated == ""
  assert config["mode"] == "tailscale"
  assert config["fetch"]["enabled"]
  assert config["fetch"]["clients"][0]["name"] == "RangeBridge"
  assert config["fetch"]["token"] == ""
  assert config["push"]["token"] == "p" * 32
  assert config["tailscale"]["hostname"] == "owner-selected"


def test_disable_relay_preserves_config_updates_made_during_funnel_shutdown(tmp_path, monkeypatch, capsys):
  core.configure_vehicle_telemetry_runtime(data_dir_provider=lambda: tmp_path)
  config_path = tmp_path / core.VEHICLE_TELEMETRY_CONFIG_FILENAME
  core.save_vehicle_telemetry_config(
    {
      "mode": "tailscale",
      "fetch": {"enabled": True, "token": "f" * 32},
      "push": {"token": "p" * 32},
    },
    config_path,
  )

  def update_config_while_funnel_stops(_controller, _enabled, _tailscale, _fetch):
    def pair_client(current):
      current["fetch"]["clients"].append({"name": "RangeBridge", "token": "c" * 32, "createdAt": 1000.0})
      current["push"]["token"] = "n" * 32
      return current

    core.update_vehicle_telemetry_config(pair_client, config_path)

  monkeypatch.setattr(tailscale.TailscaleFunnelController, "reconcile", update_config_while_funnel_stops)
  assert tailscale.main(["disable"]) == 0
  assert '"mode":"off"' in capsys.readouterr().out

  config = core.load_vehicle_telemetry_config(config_path)
  assert config["mode"] == "off"
  assert not config["fetch"]["enabled"]
  assert config["fetch"]["clients"][0]["name"] == "RangeBridge"
  assert config["push"]["token"] == "n" * 32


def test_controller_does_not_duplicate_existing_tailscale_daemon(tmp_path):
  binary = tmp_path / "tailscale"
  daemon = tmp_path / "tailscaled"
  socket_path = tmp_path / "tailscaled.sock"
  for path in (binary, daemon):
    path.write_text(path.name)
    path.chmod(0o700)
  socket_path.touch()
  config = {
    "binaryPath": str(binary),
    "daemonBinaryPath": str(daemon),
    "socketPath": str(socket_path),
    "stateDirectory": str(tmp_path / "state"),
    "hostname": "auto",
    "httpsPort": 443,
  }

  def run(args, **kwargs):
    return SimpleNamespace(returncode=1, stdout="", stderr="not ready")

  def popen(*args, **kwargs):
    raise AssertionError("must not start a duplicate daemon")

  controller = TailscaleFunnelController(tmp_path, run=run, popen=popen, monotonic=lambda: 100.0)
  controller.reconcile(True, config, {"enabled": True, "port": 7766})
  status = load_vehicle_telemetry_status(tmp_path / TAILSCALE_STATUS_FILENAME)
  assert status["state"] == "daemon-not-ready"


def test_controller_creates_persistent_funnel_and_removes_only_managed_port(tmp_path):
  binary = tmp_path / "tailscale"
  daemon = tmp_path / "tailscaled"
  binary.write_text("client")
  daemon.write_text("daemon")
  binary.chmod(0o700)
  daemon.chmod(0o700)
  config = {
    "binaryPath": str(binary),
    "daemonBinaryPath": str(daemon),
    "socketPath": str(tmp_path / "tailscaled.sock"),
    "stateDirectory": str(tmp_path / "state"),
    "hostname": "auto",
    "httpsPort": 443,
  }
  calls = []

  def run(args, **kwargs):
    calls.append(args)
    if "status" in args:
      return SimpleNamespace(
        returncode=0,
        stdout=json.dumps({"BackendState": "Running", "Self": {"DNSName": "vt-test.example.ts.net."}}),
        stderr="",
      )
    return SimpleNamespace(returncode=0, stdout="", stderr="")

  controller = TailscaleFunnelController(tmp_path, run=run, monotonic=lambda: 100.0)
  controller.reconcile(True, config, {"enabled": True, "port": 7766})
  status = load_vehicle_telemetry_status(tmp_path / TAILSCALE_STATUS_FILENAME)
  assert status["state"] == "running"
  assert status["publicURL"] == "https://vt-test.example.ts.net/api/vehicle/telemetry"
  assert any(call[-5:] == ["funnel", "--bg", "--yes", "--https=443", "http://127.0.0.1:7766"] for call in calls)

  controller.reconcile(False, config, {"enabled": True, "port": 7766})
  assert any(call[-3:] == ["funnel", "--https=443", "off"] for call in calls)
  assert not controller.marker_path.exists()
