from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


def _source(relative_path: str) -> str:
  return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_galaxy_telemetry_ui_uses_one_time_pairing_without_session_secrets():
  navigation = _source("starpilot/system/the_galaxy/assets/components/navigation/navigation_keys.js")

  assert 'externalPairing: "/api/external-app/pairing"' in navigation
  assert 'telemetryConfig: "/api/vehicle/telemetry/config"' in navigation
  assert "Create Pairing QR" in navigation
  assert "One-time connection package" in navigation
  assert 'credentials: "same-origin"' in navigation
  assert "galaxySessionToken" not in navigation
  assert "sessionToken" not in navigation
  assert "galaxyIOSPairingCode" not in navigation
  assert "X-Galaxy-LAN-Setup" not in navigation


def test_tailscale_controls_use_owner_setup_cookie_flow():
  tailscale = _source("starpilot/system/the_galaxy/assets/components/tailscale/tailscale.js")

  assert 'requestJSON("/api/tailscale/installed")' in tailscale
  assert 'requestJSON("/api/tailscale/setup", { method: "POST" })' in tailscale
  assert 'requestJSON("/api/tailscale/login", { method: "POST" })' in tailscale
  assert 'credentials: "same-origin"' in tailscale
  assert "X-Galaxy-LAN-Setup" not in tailscale


def test_all_device_settings_launch_temporary_telemetry_setup():
  c3 = _source("selfdrive/ui/layouts/settings/device.py")
  c4 = _source("selfdrive/ui/mici/layouts/settings/galaxy.py")
  c4_settings = _source("selfdrive/ui/mici/layouts/settings/settings.py")
  qt = _source("selfdrive/ui/qt/offroad/settings.cc")

  assert "launch_vehicle_telemetry_setup" in c3
  assert "enabled=ui_state.is_offroad" in c3
  assert "launch_vehicle_telemetry_setup" in c4
  assert "telemetry_setup_btn.set_enabled(lambda: ui_state.is_offroad())" in c4_settings
  assert '"openpilot.system.vehicle_telemetry.setup", "launch"' in qt
  assert 'galaxy_dir + "/telemetry_setup_session.json"' in qt
