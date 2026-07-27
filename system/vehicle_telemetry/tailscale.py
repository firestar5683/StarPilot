"""Per-owner Tailscale installation and public Funnel lifecycle.

The telemetry daemon owns a dedicated userspace ``tailscaled`` instance and
exposes only the bounded loopback HTTP service. Tailscale account authorization
and the first Funnel policy approval remain explicit owner actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import subprocess
import tarfile
import time

from pathlib import Path
from urllib.parse import urlsplit

import requests

from openpilot.system.vehicle_telemetry.core import (
  _atomic_write_bytes,
  _atomic_write_json,
  load_vehicle_telemetry_config,
  load_vehicle_telemetry_status,
  public_vehicle_telemetry_config,
  update_vehicle_telemetry_config,
  vehicle_telemetry_dir,
)


TAILSCALE_PACKAGE_BASE_URL = "https://pkgs.tailscale.com/stable"
TAILSCALE_DEFAULT_BASE = "/data/tailscale"
TAILSCALE_STATUS_FILENAME = "tailscale_status.json"
TAILSCALE_HOSTNAME_FILENAME = "tailscale_hostname"
TAILSCALE_MANAGED_FUNNEL_FILENAME = "tailscale_funnel_managed"
TAILSCALE_VERSION_FILENAME = "version"
TAILSCALE_MAX_INDEX_BYTES = 2 * 1024 * 1024
TAILSCALE_MAX_ARCHIVE_BYTES = 96 * 1024 * 1024
TAILSCALE_MAX_BINARY_BYTES = 64 * 1024 * 1024
TAILSCALE_RECONCILE_SECONDS = 5.0
TAILSCALE_FAILURE_RETRY_SECONDS = 30.0
TAILSCALE_RUNNING_RECONCILE_SECONDS = 60.0


def tailscale_architecture(machine=None):
  value = str(machine or platform.machine()).strip().lower()
  architectures = {
    "aarch64": "arm64",
    "arm64": "arm64",
    "x86_64": "amd64",
    "amd64": "amd64",
  }
  if value not in architectures:
    raise RuntimeError(f"Tailscale does not publish a supported static binary for architecture: {value}")
  return architectures[value]


def _response_content(response, maximum_bytes):
  response.raise_for_status()
  if getattr(response, "status_code", 200) != 200:
    raise RuntimeError("Tailscale download returned an unexpected response.")
  content_length = response.headers.get("Content-Length")
  if content_length:
    try:
      if int(content_length) > maximum_bytes:
        raise RuntimeError("Tailscale download exceeds the permitted size.")
    except ValueError as error:
      raise RuntimeError("Tailscale download returned an invalid size.") from error
  payload = bytearray()
  for chunk in response.iter_content(chunk_size=64 * 1024):
    if not chunk:
      continue
    payload.extend(chunk)
    if len(payload) > maximum_bytes:
      raise RuntimeError("Tailscale download exceeds the permitted size.")
  return bytes(payload)


def latest_tailscale_version(index_text, architecture):
  pattern = rf"tailscale_(\d+\.\d+\.\d+)_{re.escape(architecture)}\.tgz"
  versions = set(re.findall(pattern, str(index_text or "")))
  if not versions:
    raise RuntimeError(f"No Tailscale {architecture} static package was listed.")
  return max(versions, key=lambda value: tuple(int(part) for part in value.split(".")))


def _download_to_path(response, destination, maximum_bytes):
  response.raise_for_status()
  if getattr(response, "status_code", 200) != 200:
    raise RuntimeError("Tailscale archive returned an unexpected response.")
  content_length = response.headers.get("Content-Length")
  if content_length:
    try:
      if int(content_length) > maximum_bytes:
        raise RuntimeError("Tailscale archive exceeds the permitted size.")
    except ValueError as error:
      raise RuntimeError("Tailscale archive returned an invalid size.") from error
  destination = Path(destination)
  destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
  temp_path = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
  digest = hashlib.sha256()
  total = 0
  descriptor = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
  try:
    with os.fdopen(descriptor, "wb") as output:
      for chunk in response.iter_content(chunk_size=256 * 1024):
        if not chunk:
          continue
        total += len(chunk)
        if total > maximum_bytes:
          raise RuntimeError("Tailscale archive exceeds the permitted size.")
        digest.update(chunk)
        output.write(chunk)
      output.flush()
      os.fsync(output.fileno())
    os.replace(temp_path, destination)
  finally:
    temp_path.unlink(missing_ok=True)
  return digest.hexdigest()


def _extract_binary(archive, member_name, destination):
  try:
    member = archive.getmember(member_name)
  except KeyError as error:
    raise RuntimeError(f"Tailscale archive is missing {member_name}.") from error
  if not member.isfile() or member.size <= 0 or member.size > TAILSCALE_MAX_BINARY_BYTES:
    raise RuntimeError(f"Tailscale archive contains an invalid {member_name}.")
  source = archive.extractfile(member)
  if source is None:
    raise RuntimeError(f"Tailscale archive could not read {member_name}.")

  destination = Path(destination)
  temp_path = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
  descriptor = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o700)
  written = 0
  try:
    with source, os.fdopen(descriptor, "wb") as output:
      while chunk := source.read(256 * 1024):
        written += len(chunk)
        if written > member.size:
          raise RuntimeError(f"Tailscale archive expanded beyond the declared size for {member_name}.")
        output.write(chunk)
      if written != member.size:
        raise RuntimeError(f"Tailscale archive truncated {member_name}.")
      output.flush()
      os.fsync(output.fileno())
    os.chmod(temp_path, 0o700)
    os.replace(temp_path, destination)
  finally:
    temp_path.unlink(missing_ok=True)


def install_tailscale(base_dir=TAILSCALE_DEFAULT_BASE, *, session=None, architecture=None):
  """Install the latest checksum-verified static client without modifying `/`."""
  base_dir = Path(base_dir)
  base_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
  os.chmod(base_dir, 0o700)
  client = session or requests.Session()
  if session is None:
    client.trust_env = False
  architecture = tailscale_architecture(architecture)

  index_response = client.get(f"{TAILSCALE_PACKAGE_BASE_URL}/", timeout=(5.0, 20.0), allow_redirects=False, stream=True)
  try:
    index = _response_content(index_response, TAILSCALE_MAX_INDEX_BYTES).decode("utf-8", errors="replace")
  finally:
    index_response.close()
  version = latest_tailscale_version(index, architecture)
  filename = f"tailscale_{version}_{architecture}.tgz"
  archive_url = f"{TAILSCALE_PACKAGE_BASE_URL}/{filename}"

  checksum_response = client.get(f"{archive_url}.sha256", timeout=(5.0, 20.0), allow_redirects=False, stream=True)
  try:
    checksum_text = _response_content(checksum_response, 4096).decode("ascii", errors="strict")
  finally:
    checksum_response.close()
  expected = checksum_text.strip().split()[0].lower() if checksum_text.strip() else ""
  if not re.fullmatch(r"[0-9a-f]{64}", expected):
    raise RuntimeError("Tailscale published an invalid SHA-256 checksum.")

  archive_path = base_dir / filename
  archive_response = client.get(archive_url, timeout=(5.0, 180.0), allow_redirects=False, stream=True)
  try:
    actual = _download_to_path(archive_response, archive_path, TAILSCALE_MAX_ARCHIVE_BYTES)
  finally:
    archive_response.close()
  try:
    if not secrets.compare_digest(actual, expected):
      raise RuntimeError("Tailscale archive checksum mismatch.")
    directory = f"tailscale_{version}_{architecture}"
    with tarfile.open(archive_path, mode="r:gz") as archive:
      _extract_binary(archive, f"{directory}/tailscale", base_dir / "tailscale")
      _extract_binary(archive, f"{directory}/tailscaled", base_dir / "tailscaled")
    _atomic_write_bytes(base_dir / TAILSCALE_VERSION_FILENAME, (version + "\n").encode("ascii"))
  finally:
    archive_path.unlink(missing_ok=True)
  return {
    "version": version,
    "binaryPath": str(base_dir / "tailscale"),
    "daemonBinaryPath": str(base_dir / "tailscaled"),
    "socketPath": str(base_dir / "tailscaled.sock"),
    "stateDirectory": str(base_dir / "state"),
  }


def tailscale_is_installed(config):
  return all(Path(config[key]).is_file() and os.access(config[key], os.X_OK) for key in ("binaryPath", "daemonBinaryPath"))


def enable_personal_tailscale_relay(*, config_path=None, data_dir=None, installer=None, base_dir=TAILSCALE_DEFAULT_BASE):
  """Install outside the config lock, then atomically enable the loopback API."""
  snapshot = load_vehicle_telemetry_config(config_path)
  snapshot_tailscale = snapshot["tailscale"]
  installed_paths = {
    key: snapshot_tailscale[key]
    for key in ("binaryPath", "daemonBinaryPath", "socketPath", "stateDirectory")
  }
  if not tailscale_is_installed(snapshot_tailscale):
    installed_paths.update((installer or install_tailscale)(base_dir))

  # This may create an owner-only hostname file, but never runs while the
  # configuration lock is held. A concurrently selected custom hostname wins.
  automatic_hostname = ensure_tailscale_hostname(data_dir, "auto")
  token_candidate = secrets.token_urlsafe(32)
  generated_fetch_token = ""

  def enable_relay(current):
    nonlocal generated_fetch_token
    tailscale = current["tailscale"]
    if not tailscale_is_installed(tailscale):
      tailscale.update(installed_paths)
    if tailscale.get("hostname", "auto") == "auto":
      tailscale["hostname"] = automatic_hostname
    current["mode"] = "tailscale"
    current["fetch"]["enabled"] = True
    current["fetch"]["bindAddress"] = "127.0.0.1"
    if len(str(current["fetch"].get("token") or "")) < 32 and not current["fetch"].get("clients"):
      generated_fetch_token = token_candidate
      current["fetch"]["token"] = token_candidate
    return current

  config = update_vehicle_telemetry_config(enable_relay, config_path)
  return config, generated_fetch_token


def ensure_tailscale_hostname(data_dir=None, requested="auto"):
  if requested != "auto":
    return requested
  path = Path(data_dir or vehicle_telemetry_dir()) / TAILSCALE_HOSTNAME_FILENAME
  try:
    file_stat = path.stat()
    existing = path.read_text(encoding="utf-8").strip() if file_stat.st_uid == os.geteuid() and not file_stat.st_mode & 0o077 else ""
  except OSError:
    existing = ""
  if re.fullmatch(r"vt-[a-z0-9]{16}", existing):
    return existing
  hostname = f"vt-{secrets.token_hex(8)}"
  _atomic_write_bytes(path, (hostname + "\n").encode("ascii"))
  return hostname


def _tailscale_command(config, *arguments):
  return [config["binaryPath"], "--socket", config["socketPath"], *arguments]


def _login_url(output):
  match = re.search(r"https://login\.tailscale\.com/[^\s]+", str(output or ""))
  if not match:
    return ""
  candidate = match.group(0).rstrip(".,;)")
  parsed = urlsplit(candidate)
  return candidate if parsed.scheme == "https" and parsed.hostname == "login.tailscale.com" else ""


def _status_error(output):
  return re.sub(r"https://[^\s]+", "[owner URL redacted]", str(output or ""))[:240]


def tailscale_status(config, *, run=None, timeout=3.0):
  runner = run or subprocess.run
  result = runner(
    _tailscale_command(config, "status", "--json"),
    stdin=subprocess.DEVNULL,
    capture_output=True,
    text=True,
    timeout=timeout,
    check=False,
  )
  if result.returncode != 0:
    return None, (result.stderr or result.stdout or "Tailscale is not ready.").strip()[:240]
  try:
    status = json.loads(result.stdout)
  except (TypeError, ValueError, json.JSONDecodeError):
    return None, "Tailscale returned invalid status JSON."
  return (status, "") if isinstance(status, dict) else (None, "Tailscale returned invalid status JSON.")


def begin_tailscale_login(config, hostname, *, run=None, timeout=8.0):
  runner = run or subprocess.run
  command = _tailscale_command(
    config,
    "up",
    f"--hostname={hostname}",
    "--accept-dns=false",
    "--accept-routes=false",
    "--ssh=false",
  )
  try:
    result = runner(
      command,
      stdin=subprocess.DEVNULL,
      capture_output=True,
      text=True,
      timeout=timeout,
      check=False,
    )
    output = (result.stdout or "") + "\n" + (result.stderr or "")
  except subprocess.TimeoutExpired as error:
    stdout = error.stdout.decode(errors="replace") if isinstance(error.stdout, bytes) else str(error.stdout or "")
    stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else str(error.stderr or "")
    output = stdout + "\n" + stderr
  url = _login_url(output)
  if not url:
    status, _ = tailscale_status(config, run=runner)
    url = _login_url(status.get("AuthURL")) if isinstance(status, dict) else ""
  if not url:
    raise RuntimeError("Tailscale did not return an owner login URL.")
  return url


class TailscaleFunnelController:
  def __init__(self, data_dir=None, *, popen=None, run=None, monotonic=None):
    self.data_dir = Path(data_dir or vehicle_telemetry_dir())
    self.popen = popen or subprocess.Popen
    self.run = run or subprocess.run
    self.monotonic = monotonic or time.monotonic
    self.status_path = self.data_dir / TAILSCALE_STATUS_FILENAME
    self.marker_path = self.data_dir / TAILSCALE_MANAGED_FUNNEL_FILENAME
    self.process = None
    self.signature = None
    self.next_reconcile = 0.0
    self._last_status_signature = None

  def _write_status(self, state, *, public_url="", owner_url="", error=""):
    safe_error = _status_error(error)
    signature = (state, public_url, owner_url, safe_error)
    if signature == self._last_status_signature:
      return
    _atomic_write_json(self.status_path, {
      "schemaVersion": 1,
      "provider": "tailscale",
      "updatedAt": time.time(),  # noqa: TID251
      "state": state,
      "publicURL": public_url,
      "ownerURL": owner_url,
      "error": safe_error,
    })
    self._last_status_signature = signature

  def _start_daemon(self, config):
    daemon = Path(config["daemonBinaryPath"])
    if not daemon.is_file() or not os.access(daemon, os.X_OK):
      self._write_status("missing-binary", error=f"tailscaled is not executable: {daemon}")
      return False
    state_directory = Path(config["stateDirectory"])
    state_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(state_directory, 0o700)
    Path(config["socketPath"]).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    self.process = self.popen(
      [
        str(daemon),
        "--tun=userspace-networking",
        f"--state={state_directory / 'tailscaled.state'}",
        f"--socket={config['socketPath']}",
        f"--statedir={state_directory}",
      ],
      stdin=subprocess.DEVNULL,
      stdout=subprocess.DEVNULL,
      stderr=subprocess.STDOUT,
      close_fds=True,
    )
    try:
      os.setpriority(os.PRIO_PROCESS, self.process.pid, 19)
    except (AttributeError, OSError):
      pass
    self._write_status("starting")
    return True

  def _disable_managed_funnel(self, config):
    if not self.marker_path.is_file():
      return
    try:
      self.run(
        _tailscale_command(config, "funnel", "--https=443", "off"),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5.0,
        check=False,
      )
    except (OSError, subprocess.TimeoutExpired):
      return
    self.marker_path.unlink(missing_ok=True)

  def reconcile(self, enabled, config, fetch):
    if not enabled:
      self._disable_managed_funnel(config)
      self._stop_process()
      self.signature = None
      self._write_status("disabled")
      return
    binary = Path(config["binaryPath"])
    if not binary.is_file() or not os.access(binary, os.X_OK):
      self._write_status("missing-binary", error=f"tailscale is not executable: {binary}")
      return
    if self.process is not None and self.process.poll() is not None:
      self.process = None

    now = self.monotonic()
    if now < self.next_reconcile:
      return
    self.next_reconcile = now + TAILSCALE_RECONCILE_SECONDS
    status, error = tailscale_status(config, run=self.run)
    if status is None:
      if self.process is None:
        # Never launch a duplicate daemon when another fork or system service
        # already owns this socket. That service can recover independently.
        if Path(config["socketPath"]).exists():
          self._write_status("daemon-not-ready", error=error)
          return
        try:
          self._start_daemon(config)
        except OSError as start_error:
          self._write_status("start-failed", error=start_error)
      else:
        self._write_status("starting", error=error)
      return

    backend_state = str(status.get("BackendState") or "").strip()
    owner_url = _login_url(status.get("AuthURL"))
    if backend_state != "Running":
      self._write_status("needs-login" if backend_state == "NeedsLogin" else "not-ready", owner_url=owner_url, error=backend_state)
      return

    self_info = status.get("Self") if isinstance(status.get("Self"), dict) else {}
    dns_name = str(self_info.get("DNSName") or "").strip().rstrip(".")
    if not dns_name:
      self._write_status("not-ready", error="Tailscale has not assigned a DNS name.")
      return
    public_url = f"https://{dns_name}/api/vehicle/telemetry"
    target = f"http://127.0.0.1:{int(fetch['port'])}"
    signature = (target, int(config["httpsPort"]), dns_name)
    if signature != self.signature or not self.marker_path.is_file():
      try:
        result = self.run(
          _tailscale_command(config, "funnel", "--bg", "--yes", f"--https={int(config['httpsPort'])}", target),
          stdin=subprocess.DEVNULL,
          capture_output=True,
          text=True,
          timeout=15.0,
          check=False,
        )
        output = (result.stdout or "") + "\n" + (result.stderr or "")
      except subprocess.TimeoutExpired as command_error:
        stdout = command_error.stdout.decode(errors="replace") if isinstance(command_error.stdout, bytes) else str(command_error.stdout or "")
        stderr = command_error.stderr.decode(errors="replace") if isinstance(command_error.stderr, bytes) else str(command_error.stderr or "")
        output = stdout + "\n" + stderr
        result = None
      approval_url = _login_url(output)
      if result is None or result.returncode != 0:
        self.next_reconcile = max(self.next_reconcile, now + TAILSCALE_FAILURE_RETRY_SECONDS)
        self._write_status("needs-funnel-approval" if approval_url else "funnel-failed", owner_url=approval_url, error=output.strip())
        return
      _atomic_write_bytes(self.marker_path, (json.dumps({"target": target, "httpsPort": config["httpsPort"]}) + "\n").encode("utf-8"))
      self.signature = signature
    self.next_reconcile = max(self.next_reconcile, now + TAILSCALE_RUNNING_RECONCILE_SECONDS)
    self._write_status("running", public_url=public_url)

  def _stop_process(self):
    process = self.process
    self.process = None
    if process is None or process.poll() is not None:
      return
    process.terminate()
    try:
      process.wait(timeout=3.0)
    except subprocess.TimeoutExpired:
      process.kill()
      process.wait(timeout=1.0)

  def stop(self):
    self._stop_process()
    self._write_status("stopped")


def main(argv=None):
  parser = argparse.ArgumentParser(description="Configure the per-owner Tailscale telemetry relay.")
  parser.add_argument("action", choices=("enable", "login", "status", "disable"))
  arguments = parser.parse_args(argv)
  try:
    if arguments.action == "enable":
      config, generated_token = enable_personal_tailscale_relay()
      result = {"config": public_vehicle_telemetry_config(config)}
      if generated_token:
        result["generatedFetchToken"] = generated_token
    elif arguments.action == "login":
      config = load_vehicle_telemetry_config()
      hostname = ensure_tailscale_hostname(requested=config["tailscale"].get("hostname", "auto"))
      result = {"ownerURL": begin_tailscale_login(config["tailscale"], hostname)}
    elif arguments.action == "disable":
      config = load_vehicle_telemetry_config()
      TailscaleFunnelController().reconcile(False, config["tailscale"], config["fetch"])

      def disable_relay(current):
        current["mode"] = "off"
        current["fetch"]["enabled"] = False
        return current

      result = {"config": public_vehicle_telemetry_config(update_vehicle_telemetry_config(disable_relay))}
    else:
      config = load_vehicle_telemetry_config()
      result = {
        "config": public_vehicle_telemetry_config(config),
        "tunnel": load_vehicle_telemetry_status(vehicle_telemetry_dir() / TAILSCALE_STATUS_FILENAME),
      }
  except Exception as error:
    print(json.dumps({"error": str(error)[:240]}, separators=(",", ":")))
    return 1
  print(json.dumps(result, separators=(",", ":"), sort_keys=True))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
