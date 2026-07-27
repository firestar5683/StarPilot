from openpilot.system.vehicle_telemetry.tunnel import (
  FRPTunnelController,
  build_frpc_config,
  ensure_frp_subdomain,
  frp_public_url,
)


def test_auto_subdomain_is_private_stable_and_not_vehicle_identity(tmp_path):
  first = ensure_frp_subdomain(tmp_path, "auto")
  second = ensure_frp_subdomain(tmp_path, "auto")
  assert first == second
  assert first.startswith("vt-")
  assert (tmp_path / "frpc_subdomain").stat().st_mode & 0o077 == 0


def test_frpc_config_uses_token_file_tls_and_loopback():
  tunnel = {
    "serverAddress": "gateway.example",
    "serverPort": 7000,
    "trustedCaFile": "/data/ca.crt",
    "serverName": "gateway.example",
    "subdomainHost": "example.com",
  }
  config = build_frpc_config(tunnel, {"port": 7766}, "vt-test", "/data/frpc_token")
  assert 'serverAddr = "gateway.example"' in config
  assert 'auth.tokenSource.file.path = "/data/frpc_token"' in config
  assert 'transport.tls.trustedCaFile = "/data/ca.crt"' in config
  assert 'localIP = "127.0.0.1"' in config
  assert 'subdomain = "vt-test"' in config
  assert frp_public_url(tunnel, "vt-test") == "https://vt-test.example.com/api/vehicle/telemetry"


class FakeProcess:
  def __init__(self):
    self.return_code = None
    self.terminated = False

  def poll(self):
    return self.return_code

  def terminate(self):
    self.terminated = True
    self.return_code = 0

  def wait(self, timeout):
    return self.return_code

  def kill(self):
    self.return_code = -9


def test_controller_generates_config_and_starts_without_shell(tmp_path):
  binary = tmp_path / "frpc"
  binary.write_text("fake")
  binary.chmod(0o700)
  calls = []

  def fake_popen(args, **kwargs):
    calls.append((args, kwargs))
    return FakeProcess()

  controller = FRPTunnelController(tmp_path, popen=fake_popen, monotonic=lambda: 100.0)
  tunnel = {
    "binaryPath": str(binary),
    "serverAddress": "gateway.example",
    "serverPort": 7000,
    "token": "t" * 32,
    "subdomainHost": "example.com",
    "subdomain": "vt-test",
    "trustedCaFile": "/data/ca.crt",
    "serverName": "gateway.example",
  }
  controller.reconcile(True, tunnel, {"enabled": True, "port": 7766})
  assert calls[0][0] == [str(binary), "-c", str(tmp_path / "frpc.generated.toml")]
  assert calls[0][1]["close_fds"] is True
  assert (tmp_path / "frpc_token").read_text().strip() == "t" * 32
  assert (tmp_path / "frpc_token").stat().st_mode & 0o077 == 0
  assert controller.public_url == "https://vt-test.example.com/api/vehicle/telemetry"
  controller.stop()
  assert calls[0][0][0] == str(binary)


def test_controller_refuses_frp_without_server_identity_verification(tmp_path):
  controller = FRPTunnelController(tmp_path, popen=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not start")))
  controller.reconcile(True, {
    "binaryPath": "/data/frpc",
    "serverAddress": "gateway.example",
    "serverPort": 7000,
    "token": "t" * 32,
    "subdomainHost": "example.com",
    "subdomain": "vt-test",
    "trustedCaFile": "",
    "serverName": "",
  }, {"enabled": True, "port": 7766})
  assert controller.process is None
  assert "trusted CA" in (tmp_path / "frpc_status.json").read_text()
