"""FRP reverse-tunnel configuration and lifecycle management."""

from __future__ import annotations

import os
import secrets
import subprocess
import time

from pathlib import Path

from openpilot.system.vehicle_telemetry.core import _atomic_write_bytes, _atomic_write_json, vehicle_telemetry_dir


FRPC_CONFIG_FILENAME = "frpc.generated.toml"
FRPC_TOKEN_FILENAME = "frpc_token"
FRPC_SLUG_FILENAME = "frpc_subdomain"
FRPC_STATUS_FILENAME = "frpc_status.json"


def _toml_string(value):
  text = str(value)
  escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
  return f'"{escaped}"'


def _read_owner_only_text(path):
  try:
    file_stat = Path(path).stat()
    if file_stat.st_uid != os.geteuid() or file_stat.st_mode & 0o077:
      return ""
    return Path(path).read_text(encoding="utf-8").strip()
  except Exception:
    return ""


def ensure_frp_subdomain(data_dir=None, requested="auto"):
  if requested != "auto":
    return requested
  path = Path(data_dir or vehicle_telemetry_dir()) / FRPC_SLUG_FILENAME
  existing = _read_owner_only_text(path)
  if existing.startswith("vt-") and 8 <= len(existing) <= 63:
    return existing
  generated = f"vt-{secrets.token_hex(8)}"
  _atomic_write_bytes(path, (generated + "\n").encode("utf-8"))
  return generated


def build_frpc_config(tunnel, fetch, subdomain, token_path):
  lines = [
    f"serverAddr = {_toml_string(tunnel['serverAddress'])}",
    f"serverPort = {int(tunnel['serverPort'])}",
    f"user = {_toml_string('vehicle-telemetry-' + subdomain)}",
    "transport.tls.enable = true",
    'auth.method = "token"',
    'auth.tokenSource.type = "file"',
    f"auth.tokenSource.file.path = {_toml_string(str(token_path))}",
  ]
  if tunnel.get("trustedCaFile"):
    lines.append(f"transport.tls.trustedCaFile = {_toml_string(tunnel['trustedCaFile'])}")
  if tunnel.get("serverName"):
    lines.append(f"transport.tls.serverName = {_toml_string(tunnel['serverName'])}")
  lines += [
    "",
    "[[proxies]]",
    f"name = {_toml_string('vehicle-telemetry-' + subdomain)}",
    'type = "http"',
    'localIP = "127.0.0.1"',
    f"localPort = {int(fetch['port'])}",
    f"subdomain = {_toml_string(subdomain)}",
    "",
  ]
  return "\n".join(lines)


def frp_public_url(tunnel, subdomain):
  return f"https://{subdomain}.{tunnel['subdomainHost']}/api/vehicle/telemetry"


class FRPTunnelController:
  def __init__(self, data_dir=None, popen=None, monotonic=None):
    self.data_dir = Path(data_dir or vehicle_telemetry_dir())
    self.popen = popen or subprocess.Popen
    self.monotonic = monotonic or time.monotonic
    self.process = None
    self.signature = None
    self.next_start_mono = 0.0
    self.backoff_seconds = 1.0
    self.config_path = self.data_dir / FRPC_CONFIG_FILENAME
    self.token_path = self.data_dir / FRPC_TOKEN_FILENAME
    self.status_path = self.data_dir / FRPC_STATUS_FILENAME
    self.public_url = ""
    self._last_status_signature = None

  def _write_status(self, state, error="", return_code=None):
    signature = (state, str(error)[:240], return_code, self.public_url)
    if signature == self._last_status_signature:
      return
    _atomic_write_json(
      self.status_path,
      {
        "schemaVersion": 1,
        "updatedAt": time.time(),  # noqa: TID251
        "state": state,
        "publicURL": self.public_url,
        "error": str(error)[:240],
        "returnCode": return_code,
      },
    )
    self._last_status_signature = signature

  def _configuration_signature(self, tunnel, fetch, subdomain):
    return (
      tunnel["binaryPath"],
      tunnel["serverAddress"],
      tunnel["serverPort"],
      tunnel["token"],
      tunnel["subdomainHost"],
      tunnel["trustedCaFile"],
      tunnel["serverName"],
      fetch["port"],
      subdomain,
    )

  def _valid(self, tunnel, fetch):
    return bool(
      fetch["enabled"]
      and tunnel["serverAddress"]
      and tunnel["subdomainHost"]
      and tunnel["token"]
      and tunnel["binaryPath"]
      and tunnel["trustedCaFile"]
      and tunnel["serverName"]
    )

  def reconcile(self, enabled, tunnel, fetch):
    if not enabled:
      self.stop(state="disabled")
      return
    if not self._valid(tunnel, fetch):
      self.stop(state="invalid-config", error="FRP mode requires fetch auth, gateway, domain, binary, token, trusted CA, and TLS server name.")
      return

    subdomain = ensure_frp_subdomain(self.data_dir, tunnel["subdomain"])
    signature = self._configuration_signature(tunnel, fetch, subdomain)
    if signature != self.signature:
      self.stop(state="reconfiguring")
      self.signature = signature
      self.public_url = frp_public_url(tunnel, subdomain)
      _atomic_write_bytes(self.token_path, (tunnel["token"] + "\n").encode("utf-8"))
      config = build_frpc_config(tunnel, fetch, subdomain, self.token_path)
      _atomic_write_bytes(self.config_path, config.encode("utf-8"))
      self.next_start_mono = 0.0
      self.backoff_seconds = 1.0

    if self.process is not None:
      return_code = self.process.poll()
      if return_code is None:
        return
      self.process = None
      self._write_status("stopped", return_code=return_code)
      self.next_start_mono = self.monotonic() + self.backoff_seconds
      self.backoff_seconds = min(60.0, self.backoff_seconds * 2.0)

    if self.monotonic() < self.next_start_mono:
      return
    binary_path = Path(tunnel["binaryPath"])
    if not binary_path.is_file() or not os.access(binary_path, os.X_OK):
      self.next_start_mono = self.monotonic() + 30.0
      self._write_status("missing-binary", error=f"frpc is not executable: {binary_path}")
      return
    try:
      self.process = self.popen(
        [str(binary_path), "-c", str(self.config_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        close_fds=True,
      )
      try:
        os.setpriority(os.PRIO_PROCESS, self.process.pid, 19)
      except (AttributeError, OSError):
        pass
      self.backoff_seconds = 1.0
      self._write_status("running")
    except Exception as error:
      self.next_start_mono = self.monotonic() + self.backoff_seconds
      self.backoff_seconds = min(60.0, self.backoff_seconds * 2.0)
      self._write_status("start-failed", error=error)

  def stop(self, state="stopped", error=""):
    process = self.process
    self.process = None
    if process is not None and process.poll() is None:
      process.terminate()
      try:
        process.wait(timeout=3.0)
      except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=1.0)
    self._write_status(state, error=error)
