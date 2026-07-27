from openpilot.system.vehicle_telemetry.gateway import (
  CloudflareDNSUpdater,
  build_frps_config,
  normalize_gateway_config,
)


def test_gateway_requires_zone_apex_for_free_wildcard_tls():
  raw = {
    "frp": {"subdomainHost": "telemetry.example.com", "token": "t" * 32},
    "dns": {"zoneName": "example.com", "zoneId": "zone", "apiToken": "a" * 24},
  }
  try:
    normalize_gateway_config(raw)
  except ValueError as error:
    assert "subdomainHost" in str(error)
  else:
    raise AssertionError("nested subdomain host should not be accepted for free wildcard TLS mode")


def test_gateway_requires_frp_server_certificate_paths():
  raw = {
    "frp": {"subdomainHost": "example.com", "token": "t" * 32},
    "dns": {"zoneName": "example.com", "zoneId": "zone", "apiToken": "a" * 24},
  }
  try:
    normalize_gateway_config(raw)
  except ValueError as error:
    assert "certificate" in str(error)
  else:
    raise AssertionError("an unauthenticated FRP server certificate must not be accepted")


def test_frps_config_forces_tls_and_loads_token_from_owner_file():
  config = build_frps_config(
    {
      "bindPort": 7000,
      "vhostHTTPPort": 80,
      "subdomainHost": "example.com",
      "certFile": "/etc/frp/server.crt",
      "keyFile": "/etc/frp/server.key",
    },
    "/var/lib/vehicle-telemetry/frps_token",
  )
  assert "transport.tls.force = true" in config
  assert 'auth.tokenSource.file.path = "/var/lib/vehicle-telemetry/frps_token"' in config
  assert 'transport.tls.certFile = "/etc/frp/server.crt"' in config


class FakeResponse:
  def __init__(self, payload):
    self.payload = payload
    self.closed = False

  def json(self):
    return self.payload

  def close(self):
    self.closed = True


class FakeHeaders(dict):
  def update(self, value):
    super().update(value)


class FakeSession:
  def __init__(self):
    self.trust_env = True
    self.headers = FakeHeaders()
    self.calls = []
    self.records = {}

  def get(self, url, **kwargs):
    self.calls.append(("GET", url, kwargs))
    name = kwargs["params"]["name"]
    result = [{"id": self.records[name]}] if name in self.records else []
    return FakeResponse({"success": True, "result": result})

  def post(self, url, **kwargs):
    self.calls.append(("POST", url, kwargs))
    name = kwargs["json"]["name"]
    self.records[name] = f"id-{len(self.records)}"
    return FakeResponse({"success": True, "result": {"id": self.records[name]}})

  def put(self, url, **kwargs):
    self.calls.append(("PUT", url, kwargs))
    return FakeResponse({"success": True, "result": {"id": url.rsplit("/", 1)[-1]}})


def test_cloudflare_updater_keeps_control_dns_only_and_proxies_wildcard():
  session = FakeSession()
  updater = CloudflareDNSUpdater("zone", "a" * 24, session=session)
  updater.update_gateway_records("example.com", "203.0.113.10")
  posts = [call for call in session.calls if call[0] == "POST"]
  assert posts[0][2]["json"]["name"] == "example.com"
  assert posts[0][2]["json"]["proxied"] is False
  assert posts[1][2]["json"]["name"] == "*.example.com"
  assert posts[1][2]["json"]["proxied"] is True
  assert session.trust_env is False
  assert "Authorization" not in session.headers
  assert all(call[2]["headers"]["Authorization"] == f"Bearer {'a' * 24}" for call in session.calls)
