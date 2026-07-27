#!/usr/bin/env python3
"""One-time pairing exchange for external Galaxy applications.

The QR payload contains only a short-lived code and an exchange URL. Reusable
credentials are returned after the code is consumed and are stored only in the
external application's secure storage.
"""

from __future__ import annotations

import base64
import fcntl
import hashlib
import hmac
import json
import os
import secrets
import threading
import time

from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from openpilot.starpilot.system.vehicle_telemetry import update_vehicle_telemetry_config


PAIRING_SCHEMA_VERSION = 1
PAIRING_PREFIX = "starpilot-external-v1:"
PAIRING_TTL_SECONDS = 10 * 60
PAIRING_FILENAME = "external_app_pairing.json"
PAIRING_LOCK_FILENAME = ".external_app_pairing.lock"
PAIRING_CLAIM_FILENAME = ".external_app_pairing.claim.json"
MAX_PAIRING_ATTEMPTS = 5
_PAIRING_PROCESS_LOCK = threading.Lock()


def pairing_path(galaxy_dir: Path) -> Path:
  return Path(galaxy_dir) / PAIRING_FILENAME


@contextmanager
def _exclusive_pairing_lock(galaxy_dir: Path):
  """Serialize pairing and config mutation in this and other Galaxy processes."""
  directory = Path(galaxy_dir)
  with _PAIRING_PROCESS_LOCK:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(directory / PAIRING_LOCK_FILENAME, flags, 0o600)
    try:
      os.fchmod(descriptor, 0o600)
      fcntl.flock(descriptor, fcntl.LOCK_EX)
      yield
    finally:
      fcntl.flock(descriptor, fcntl.LOCK_UN)
      os.close(descriptor)


def _atomic_owner_write(path: Path, payload: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
  path.parent.chmod(0o700)
  temp_path = path.with_name(f".{path.name}.tmp")
  temp_path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True), encoding="utf-8")
  temp_path.chmod(0o600)
  temp_path.replace(path)


def _read_owner_json(path: Path) -> dict | None:
  try:
    stat = path.stat()
    if stat.st_uid != os.geteuid() or stat.st_mode & 0o077:
      return None
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else None
  except Exception:
    return None


def _normalized_local_base_url(value: str) -> str:
  parsed = urlsplit(str(value or "").strip())
  if parsed.scheme not in ("http", "https") or not parsed.hostname:
    return ""
  return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def create_pairing(galaxy_dir: Path, base_url: str, now: float | None = None) -> dict:
  local_base_url = _normalized_local_base_url(base_url)
  if not local_base_url:
    raise ValueError("A valid Galaxy base URL is required")

  created_at = time.time() if now is None else float(now)  # noqa: TID251 - pairing payload uses Unix time
  expires_at = created_at + PAIRING_TTL_SECONDS
  code = f"{secrets.randbelow(1_000_000):06d}"
  exchange_url = f"{local_base_url}/api/external-app/pair"
  payload = {
    "schemaVersion": PAIRING_SCHEMA_VERSION,
    "type": "starpilot-galaxy",
    "exchangeURL": exchange_url,
    "code": code,
    "expiresAt": expires_at,
    "attempts": 0,
  }
  encoded = base64.urlsafe_b64encode(
    json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
  ).decode("ascii").rstrip("=")
  qr_data = f"{PAIRING_PREFIX}{encoded}"
  with _exclusive_pairing_lock(galaxy_dir):
    _atomic_owner_write(pairing_path(galaxy_dir), {
      "schemaVersion": PAIRING_SCHEMA_VERSION,
      "codeHash": hashlib.sha256(code.encode("utf-8")).hexdigest(),
      "createdAt": created_at,
      "expiresAt": expires_at,
      "localBaseURL": local_base_url,
      "attempts": 0,
    })
  return {
    "schemaVersion": PAIRING_SCHEMA_VERSION,
    "qrData": qr_data,
    "pairingCode": code,
    "exchangeURL": exchange_url,
    "expiresAt": expires_at,
  }


def complete_pairing(
  galaxy_dir: Path,
  code: str,
  client_name: str,
  requested_capabilities: list[str] | None = None,
  legacy_connection: dict | None = None,
  telemetry_base_urls: list[str] | None = None,
  telemetry_path: str = "/api/vehicle/telemetry",
  now: float | None = None,
) -> tuple[dict | None, str | None]:
  path = pairing_path(galaxy_dir)
  claim_path = Path(galaxy_dir) / PAIRING_CLAIM_FILENAME
  current_time = time.time() if now is None else float(now)  # noqa: TID251 - persisted expiry uses Unix time

  with _exclusive_pairing_lock(galaxy_dir):
    # Atomic rename makes one request the sole owner even if a second Galaxy
    # process is briefly present during an update or restart.
    try:
      path.replace(claim_path)
    except FileNotFoundError:
      return None, "No external-app pairing is waiting"

    record = _read_owner_json(claim_path)
    if not record:
      claim_path.unlink(missing_ok=True)
      return None, "No external-app pairing is waiting"
    if current_time > float(record.get("expiresAt") or 0.0):
      claim_path.unlink(missing_ok=True)
      return None, "The external-app pairing code expired"

    supplied_hash = hashlib.sha256(str(code or "").strip().encode("utf-8")).hexdigest()
    if not hmac.compare_digest(supplied_hash, str(record.get("codeHash") or "")):
      attempts = int(record.get("attempts") or 0) + 1
      if attempts >= MAX_PAIRING_ATTEMPTS:
        claim_path.unlink(missing_ok=True)
      else:
        record["attempts"] = attempts
        _atomic_owner_write(claim_path, record)
        claim_path.replace(path)
      return None, "The external-app pairing code is invalid"

    candidate_base_urls = telemetry_base_urls or [str(record.get("localBaseURL") or "")]
    base_urls = []
    for candidate in candidate_base_urls:
      normalized = _normalized_local_base_url(candidate)
      if normalized and normalized not in base_urls:
        base_urls.append(normalized)
    if not base_urls:
      claim_path.replace(path)
      return None, "No valid EV Vehicle Telemetry endpoint is configured"

    name = str(client_name or "External app").strip()[:80] or "External app"
    bearer_token = secrets.token_urlsafe(32)

    def add_paired_client(config):
      if config["mode"] == "off":
        config["mode"] = "galaxy"
      clients = [client for client in config["fetch"].get("clients", []) if client.get("name") != name]
      clients.append({"name": name, "token": bearer_token, "createdAt": current_time})
      config["fetch"]["enabled"] = True
      config["fetch"]["clients"] = clients[-8:]
      return config

    try:
      update_vehicle_telemetry_config(add_paired_client)
    except Exception:
      # The token has not been returned. Restore the claim so the owner can
      # retry after a transient storage failure.
      claim_path.replace(path)
      raise

    # Consume only after the credential is durably present in the config.
    claim_path.unlink(missing_ok=True)
    response = {
      "schemaVersion": PAIRING_SCHEMA_VERSION,
      "type": "starpilot-galaxy-connection",
      "displayName": "StarPilot Galaxy",
      "capabilities": {
        "vehicleTelemetry": {
          "baseURLs": base_urls,
          "path": telemetry_path if str(telemetry_path).startswith("/") else "/api/vehicle/telemetry",
          "authorization": "bearer",
          "bearerToken": bearer_token,
        },
      },
    }
    requested = set(requested_capabilities or ["vehicleTelemetry"])
    if "galaxySession" in requested and isinstance(legacy_connection, dict) and legacy_connection.get("sessionToken"):
      response["capabilities"]["galaxySession"] = {
        key: value for key, value in legacy_connection.items() if value
      }
    return response, None
