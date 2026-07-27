#!/usr/bin/env python3
"""Temporary, token-gated LAN setup UI for the EV Vehicle Telemetry core."""

from __future__ import annotations

import argparse
import fcntl
import hmac
import ipaddress
import json
import os
import re
import secrets
import socket
import struct
import subprocess
import sys
import threading
import time

from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from openpilot.system.vehicle_telemetry.core import (
  VEHICLE_TELEMETRY_CONFIG_FILENAME,
  _atomic_write_json,
  load_vehicle_telemetry_config,
  load_vehicle_telemetry_status,
  public_vehicle_telemetry_config,
  update_vehicle_telemetry_config,
  vehicle_telemetry_dir,
)
from openpilot.system.vehicle_telemetry.http_server import VehicleTelemetryRequestHandler, _TelemetryHTTPServer
from openpilot.system.vehicle_telemetry.tailscale import (
  TAILSCALE_DEFAULT_BASE,
  TAILSCALE_STATUS_FILENAME,
  TailscaleFunnelController,
  begin_tailscale_login,
  enable_personal_tailscale_relay,
  ensure_tailscale_hostname,
)


TELEMETRY_SETUP_PORT = 7767
TELEMETRY_SETUP_DURATION_SECONDS = 10 * 60
TELEMETRY_SETUP_MIN_DURATION_SECONDS = 2 * 60
TELEMETRY_SETUP_MAX_DURATION_SECONDS = 15 * 60
TELEMETRY_SETUP_MAX_BODY_BYTES = 16 * 1024
TELEMETRY_SETUP_STATUS_FILENAME = "telemetry_setup_session.json"
TELEMETRY_SETUP_LOCK_FILENAME = "telemetry_setup.lock"
TELEMETRY_SETUP_TOKEN_HEADER = "X-Telemetry-Setup"
TELEMETRY_SETUP_COOKIE_NAME = "openpilot_ev_telemetry_setup"

_PRIVATE_V4_NETWORKS = tuple(ipaddress.ip_network(network) for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16"))
_INTERFACE_PRIORITY = ("wlan", "wifi", "eth", "en", "usb", "bridge", "ap")
_CELLULAR_INTERFACE_PREFIXES = ("rmnet", "wwan", "ccmni", "pdp", "cell")


def telemetry_setup_status_path(data_dir=None):
  return Path(data_dir or vehicle_telemetry_dir()) / TELEMETRY_SETUP_STATUS_FILENAME


def _owner_status(path):
  return load_vehicle_telemetry_status(path)


def _pid_is_running(pid):
  try:
    os.kill(int(pid), 0)
    return True
  except (OSError, TypeError, ValueError):
    return False


def active_telemetry_setup_token(data_dir=None, *, wall_time=None):
  """Return the live owner setup capability from its owner-only session file."""
  status = _owner_status(telemetry_setup_status_path(data_dir))
  now = time.time() if wall_time is None else float(wall_time)  # noqa: TID251
  if status.get("state") not in ("starting", "running") or float(status.get("expiresAt") or 0.0) <= now:
    return ""
  if not _pid_is_running(status.get("pid")):
    return ""
  token = parse_qs(urlsplit(str(status.get("url") or "")).query).get("setup", [""])[0]
  return token if re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token) else ""


def telemetry_setup_token_is_authorized(supplied, data_dir=None, *, wall_time=None):
  active = active_telemetry_setup_token(data_dir, wall_time=wall_time)
  return bool(active) and hmac.compare_digest(str(supplied or ""), active)


def _interface_ipv4_addresses():
  addresses = []
  try:
    interfaces = socket.if_nameindex()
  except OSError:
    return addresses
  with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
    for _, name in interfaces:
      try:
        request = struct.pack("256s", name[:15].encode("ascii", errors="ignore"))
        response = fcntl.ioctl(probe.fileno(), 0x8915, request)  # Linux SIOCGIFADDR
        addresses.append((name, socket.inet_ntoa(response[20:24])))
      except OSError:
        continue
  return addresses


def choose_lan_ipv4(addresses=None):
  """Choose Wi-Fi first and never bind the setup UI to a cellular interface."""
  candidates = []
  for interface, raw_address in addresses if addresses is not None else _interface_ipv4_addresses():
    interface = str(interface or "").lower()
    if interface.startswith(_CELLULAR_INTERFACE_PREFIXES):
      continue
    try:
      address = ipaddress.ip_address(str(raw_address or ""))
    except ValueError:
      continue
    if address.version != 4 or not any(address in network for network in _PRIVATE_V4_NETWORKS):
      continue
    priority = next((index for index, prefix in enumerate(_INTERFACE_PRIORITY) if interface.startswith(prefix)), None)
    if priority is None:
      continue
    candidates.append((priority, interface, str(address)))
  return min(candidates)[2] if candidates else ""


def _device_is_onroad():
  try:
    from openpilot.common.params import Params
    return Params().get_bool("IsOnroad")
  except Exception:
    return False


class SetupSessionState:
  def __init__(
    self,
    data_dir,
    token,
    expires_at,
    *,
    installer=None,
    tailscale_base=TAILSCALE_DEFAULT_BASE,
    wall_time=None,
  ):
    self.data_dir = Path(data_dir)
    self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
      self.data_dir.chmod(0o700)
    except OSError:
      pass
    self.config_path = self.data_dir / VEHICLE_TELEMETRY_CONFIG_FILENAME
    self.token = str(token)
    self.expires_at = float(expires_at)
    self.installer = installer
    self.tailscale_base = Path(tailscale_base)
    self.wall_time = wall_time or time.time  # noqa: TID251
    self.lan_address = ""
    self.job_state = "idle"
    self.job_message = "Choose how this comma should share telemetry."
    self.job_error = ""
    self.generated_fetch_token = ""
    self._job = None
    self._lock = threading.Lock()

  def expired(self):
    return self.wall_time() >= self.expires_at

  def _disable_managed_funnel(self, config):
    try:
      TailscaleFunnelController(self.data_dir).reconcile(False, config["tailscale"], config["fetch"])
    except Exception:
      pass

  def _configure_mode(self, mode):
    if mode == "tailscale":
      config, generated = enable_personal_tailscale_relay(
        config_path=self.config_path,
        data_dir=self.data_dir,
        installer=self.installer,
        base_dir=self.tailscale_base,
      )
      message = "Personal relay enabled. Continue with owner login when requested."
    else:
      # Funnel reconciliation may invoke external processes, so keep it outside
      # the config lock and apply only the final field mutation atomically.
      self._disable_managed_funnel(load_vehicle_telemetry_config(self.config_path))
      generated = ""

      def configure_mode(current):
        nonlocal generated
        if mode == "local":
          current["mode"] = "local"
          current["fetch"]["enabled"] = True
          current["fetch"]["bindAddress"] = "0.0.0.0"
          if len(str(current["fetch"].get("token") or "")) < 32 and not current["fetch"].get("clients"):
            generated = secrets.token_urlsafe(32)
            current["fetch"]["token"] = generated
        else:
          current["mode"] = "off"
          current["fetch"]["enabled"] = False
          current["push"]["enabled"] = False
        return current

      update_vehicle_telemetry_config(configure_mode, self.config_path)
      message = (
        "Authenticated telemetry is available on this local network."
        if mode == "local"
        else "Network telemetry is off. Local caching remains available."
      )

    with self._lock:
      if generated:
        self.generated_fetch_token = generated
      self.job_state = "succeeded"
      self.job_message = message
      self.job_error = ""

  def _run_mode(self, mode):
    try:
      self._configure_mode(mode)
    except Exception as error:
      with self._lock:
        self.job_state = "failed"
        self.job_message = "Setup did not complete."
        self.job_error = str(error)[:240]

  def _configure_backend(self, update):
    # Stop the old managed Funnel without holding the config lock. The daemon
    # will retry cleanup if another transport change races this operation.
    self._disable_managed_funnel(load_vehicle_telemetry_config(self.config_path))
    supplied_endpoint = str(update.get("url") or "").strip()
    supplied_token = str(update.get("token") or "").strip()

    def configure_backend(current):
      push = current["push"]
      endpoint = supplied_endpoint or str(push.get("url") or "").strip()
      parsed = urlsplit(endpoint)
      if (
        len(endpoint) > 2048
        or parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
      ):
        raise ValueError("Enter a valid HTTPS backend URL without credentials or a fragment.")

      backend_token = supplied_token or str(push.get("token") or "").strip()
      if len(backend_token) < 32:
        raise ValueError("Enter a backend bearer token with at least 32 characters.")

      current["mode"] = "send"
      current["fetch"]["enabled"] = False
      push.update({
        "enabled": True,
        "url": endpoint,
        "token": backend_token,
        "vehicleId": str(update.get("vehicleId") or "").strip(),
        "vehicleName": str(update.get("vehicleName") or "").strip(),
      })
      return current

    saved = update_vehicle_telemetry_config(configure_backend, self.config_path)
    if not saved["push"]["enabled"]:
      raise ValueError("The custom backend configuration was not accepted.")
    with self._lock:
      self.job_state = "succeeded"
      self.job_message = "Custom backend sending is enabled."
      self.job_error = ""

  def _run_backend(self, update):
    try:
      self._configure_backend(update)
    except Exception as error:
      with self._lock:
        self.job_state = "failed"
        self.job_message = "Custom backend setup did not complete."
        self.job_error = str(error)[:240]

  def _rotate_fetch_token(self):
    try:
      generated = secrets.token_urlsafe(32)

      def rotate_fetch_token(current):
        current["fetch"]["token"] = generated
        if current["mode"] != "off":
          current["fetch"]["enabled"] = True
        return current

      update_vehicle_telemetry_config(rotate_fetch_token, self.config_path)
      with self._lock:
        self.generated_fetch_token = generated
        self.job_state = "succeeded"
        self.job_message = "A new owner fetch token was generated. Copy it now."
        self.job_error = ""
    except Exception as error:
      with self._lock:
        self.job_state = "failed"
        self.job_message = "Token rotation did not complete."
        self.job_error = str(error)[:240]

  def start_mode(self, mode):
    mode = str(mode or "").strip().lower()
    if mode not in ("off", "local", "tailscale") or self.expired():
      return False
    with self._lock:
      if self._job is not None and self._job.is_alive():
        return False
      self.job_state = "running"
      self.job_message = "Downloading and verifying Tailscale..." if mode == "tailscale" else "Saving configuration..."
      self.job_error = ""
      self._job = threading.Thread(target=self._run_mode, args=(mode,), name="telemetry-setup-job", daemon=True)
      self._job.start()
    return True

  def start_token_rotation(self):
    if self.expired():
      return False
    with self._lock:
      if self._job is not None and self._job.is_alive():
        return False
      self.job_state = "running"
      self.job_message = "Generating a new owner fetch token..."
      self.job_error = ""
      self._job = threading.Thread(target=self._rotate_fetch_token, name="telemetry-setup-token", daemon=True)
      self._job.start()
    return True

  def start_backend(self, update):
    if self.expired() or not isinstance(update, dict):
      return False
    bounded = {
      "url": str(update.get("url") or "")[:2048],
      "token": str(update.get("token") or "")[:512],
      "vehicleId": str(update.get("vehicleId") or "")[:128],
      "vehicleName": str(update.get("vehicleName") or "")[:120],
    }
    with self._lock:
      if self._job is not None and self._job.is_alive():
        return False
      self.job_state = "running"
      self.job_message = "Saving custom backend settings..."
      self.job_error = ""
      self._job = threading.Thread(target=self._run_backend, args=(bounded,), name="telemetry-setup-backend", daemon=True)
      self._job.start()
    return True

  def wait_for_job(self, timeout=None):
    with self._lock:
      job = self._job
    if job is not None:
      job.join(timeout=timeout)

  def job_running(self):
    with self._lock:
      return self._job is not None and self._job.is_alive()

  def owner_login(self):
    config = load_vehicle_telemetry_config(self.config_path)
    if config["mode"] != "tailscale" or not config["fetch"]["enabled"]:
      raise RuntimeError("Enable the personal relay first.")
    hostname = ensure_tailscale_hostname(self.data_dir, config["tailscale"].get("hostname", "auto"))
    return begin_tailscale_login(config["tailscale"], hostname)

  def status_payload(self):
    config = load_vehicle_telemetry_config(self.config_path)
    tunnel = _owner_status(self.data_dir / TAILSCALE_STATUS_FILENAME) if config["mode"] == "tailscale" else {}
    with self._lock:
      payload = {
        "config": public_vehicle_telemetry_config(config),
        "expiresAt": self.expires_at,
        "remainingSeconds": max(0, int(self.expires_at - self.wall_time())),
        "jobState": self.job_state,
        "message": self.job_message,
        "error": self.job_error,
        "generatedFetchToken": self.generated_fetch_token,
        "tunnel": tunnel,
      }
    if config["mode"] == "local" and self.lan_address:
      payload["localURL"] = f"http://{self.lan_address}:{config['fetch']['port']}/api/vehicle/telemetry"
    return payload


def render_setup_page(duration_seconds, nonce="telemetry-setup"):
  duration_json = json.dumps(int(duration_seconds))
  template = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer"><title>EV Vehicle Telemetry Setup</title>
<style>
:root { --bg:#f8f7f3; --surface:#fff; --line:#deded8; --text:#1d1d22; --muted:#66666d; --accent:#0966e8;
  --accent-soft:#eef5ff; --good:#2f7d32; --good-soft:#f1f8ee; --bad:#b3261e; --bad-soft:#fff1ef; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--text);
  font:16px/1.42 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; -webkit-font-smoothing:antialiased; }
main { width:min(100%,520px); margin:0 auto; padding:28px 20px 32px; }
.product-name { margin:0 0 7px; color:var(--text); font-size:13px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
.eyebrow { margin:0 0 22px; color:var(--good); font-size:14px; font-weight:700; letter-spacing:.01em; }
h1 { max-width:430px; margin:0 0 26px; font-size:clamp(34px,9vw,46px); line-height:1.04; letter-spacing:-.035em; }
h2 { margin:0 0 6px; font-size:20px; line-height:1.2; }
p, small { color:var(--muted); }
fieldset { min-width:0; margin:0; padding:0; border:0; }
legend { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); }
.option { display:grid; grid-template-columns:28px minmax(0,1fr) auto; gap:12px; align-items:start; margin:0 -4px;
  padding:14px 12px; border-top:1px solid var(--line); cursor:pointer; }
.option:last-of-type { border-bottom:1px solid var(--line); }
.option.selected { margin:0 -8px; padding:14px 16px; background:var(--surface); border:1px solid var(--line);
  border-radius:15px; box-shadow:0 5px 18px rgba(34,34,28,.05); }
.option.selected + .option { border-top-color:transparent; }
.option input { width:22px; height:22px; margin:2px 0 0; accent-color:var(--accent); cursor:pointer; }
.option-title { display:block; color:var(--text); font-size:18px; font-weight:750; letter-spacing:-.01em; }
.option-copy { display:block; margin-top:2px; color:var(--muted); font-size:14px; }
.best { align-self:center; padding:5px 9px; border:1px solid #a9c89d; border-radius:9px; background:var(--good-soft);
  color:var(--good); font-size:12px; font-weight:700; white-space:nowrap; }
.connection-path { margin:24px 0 0; padding:18px; border:1px solid var(--line); border-radius:14px; background:var(--surface); }
.path { margin:0 0 8px; color:var(--text); font-size:14px; font-weight:750; letter-spacing:.01em; }
.connection-path p { margin:0; }
button { width:100%; min-height:54px; border:0; border-radius:12px; padding:14px 16px; background:var(--accent);
  color:white; font-family:inherit; font-size:17px; font-weight:700; line-height:1.2; cursor:pointer; }
button:hover { filter:brightness(.96); }
button:focus-visible, a:focus-visible, input:focus-visible { outline:3px solid rgba(9,102,232,.28); outline-offset:3px; }
button:disabled { opacity:.5; cursor:wait; filter:none; }
.primary { margin-top:22px; }
button.secondary { background:#eef0f2; color:var(--text); }
button.text-button { min-height:44px; margin-top:8px; background:transparent; color:var(--accent); font-size:15px; }
.backend-fields { margin-top:18px; }
.backend-fields label { display:block; margin-top:13px; color:var(--text); font-size:14px; font-weight:700; }
.backend-fields input { width:100%; min-height:48px; margin-top:6px; padding:11px 12px; border:1px solid var(--line);
  border-radius:10px; background:var(--bg); color:var(--text); font:15px/1.2 inherit; }
.backend-fields small { display:block; margin-top:8px; }
.panel { margin-top:18px; padding:17px; border:1px solid var(--line); border-radius:14px; background:var(--surface); }
.status { white-space:pre-wrap; color:var(--muted); overflow-wrap:anywhere; }
.status.good { color:var(--good); }
.status.bad { color:var(--bad); }
.panel.good-panel { border-color:#b7d3ad; background:var(--good-soft); }
.panel.bad-panel { border-color:#efb6b1; background:var(--bad-soft); }
.panel button { margin-top:12px; }
.secret { margin:8px 0; font-family:ui-monospace,SFMono-Regular,Consolas,monospace; font-size:12px; word-break:break-all; }
.details { margin-top:20px; border-top:1px solid var(--line); }
.details summary { padding:16px 2px; color:var(--muted); font-weight:700; cursor:pointer; }
.details .panel { margin-top:0; }
.rangebridge { margin-top:24px; padding-top:22px; border-top:1px solid var(--line); text-align:center; }
.rangebridge a { color:var(--accent); font-weight:750; text-decoration:none; }
.rangebridge a:hover { text-decoration:underline; }
.footnote { margin:13px 0 0; color:#85858a; font-size:12px; }
.completion { padding-top:70px; text-align:center; }
.hidden { display:none; }
@media(max-width:380px) { main { padding-inline:16px; } .best { display:none; } .option { grid-template-columns:28px 1fr; } }
@media(prefers-reduced-motion:reduce) { * { scroll-behavior:auto !important; } }
</style></head><body><main>
<header><p class="product-name">EV Vehicle Telemetry</p><p id="connection-status" class="eyebrow">comma found · Wi-Fi · setup starting</p>
<h1>How should this comma connect?</h1></header>
<form id="mode-form">
<fieldset><legend>EV Vehicle Telemetry connection mode</legend>
<label class="option selected" data-option="tailscale"><input type="radio" name="mode" value="tailscale" checked>
<span><span class="option-title">Tailscale</span><span class="option-copy">Reach it securely from anywhere</span></span>
<span class="best">Best choice</span></label>
<label class="option" data-option="send"><input type="radio" name="mode" value="send">
<span><span class="option-title">Custom backend</span><span class="option-copy">Send small HTTPS updates to your server</span></span></label>
<label class="option" data-option="local"><input type="radio" name="mode" value="local">
<span><span class="option-title">This Wi-Fi only</span><span class="option-copy">Keep access on this network</span></span></label>
<label class="option" data-option="off"><input type="radio" name="mode" value="off">
<span><span class="option-title">No network</span><span class="option-copy">Save telemetry on the comma</span></span></label>
</fieldset>
<section class="connection-path" aria-live="polite"><p id="path" class="path">comma · private relay · RangeBridge</p>
<p id="mode-detail">Uses your own free Tailscale account. No shared server.</p></section>
<section id="backend-fields" class="panel backend-fields hidden">
<h2>Custom backend</h2>
<label>HTTPS endpoint<input id="backend-url" type="url" inputmode="url" autocomplete="url" placeholder="https://telemetry.example/v1/ingest"></label>
<label>Bearer token<input id="backend-token" type="password" autocomplete="new-password" placeholder="At least 32 characters"></label>
<small>The token is sent only in the Authorization header. Leave it blank to keep an existing token.</small>
<label>Vehicle ID <small>(optional)</small><input id="backend-vehicle-id" type="text" autocomplete="off" maxlength="128" placeholder="my-ev"></label>
<label>Vehicle name <small>(optional)</small><input id="backend-vehicle-name" type="text" autocomplete="off" maxlength="120" placeholder="My EV"></label>
</section>
<button id="apply-mode" class="primary" type="submit">Set up Tailscale</button>
<button id="finish" class="text-button" type="button">I’ll configure this later</button>
</form>
<section id="setup-status" class="panel hidden" aria-live="polite"><h2>Setup status</h2><div id="status" class="status">Ready.</div>
<div id="owner-wrap" class="hidden"><button id="owner" type="button">Owner login</button></div></section>
<section id="connection" class="panel hidden"><h2>Connection details</h2><p id="endpoint"></p>
<div id="token-wrap" class="hidden"><p>Fetch token — copy this now:</p><p id="fetch-token" class="secret"></p>
<button id="copy" class="secondary" type="button">Copy token</button></div></section>
<footer class="rangebridge"><a href="https://github.com/LowkeyNEXT/RangeBridge" target="_blank" rel="noreferrer">RangeBridge on GitHub</a>
<p class="footnote">Telemetry runs while driving · no CAN writes · low CPU</p></footer>
<details class="details"><summary>Advanced access</summary><section class="panel">
<p>Rotate the owner fetch token if it may have been shared. Existing clients using the old token will stop working.</p>
<button id="rotate" class="secondary" type="button">Generate new owner fetch token</button>
<button id="refresh" class="text-button" type="button">Refresh status</button>
<button id="galaxy" class="text-button" type="button">Open StarPilot Galaxy controls</button></section></details>
</main><script nonce="__NONCE__">
const lifetime = __DURATION__;
let latest = {};
let selectionInitialized = false;
let backendInitialized = false;
history.replaceState(null, "", location.pathname);
const statusEl = document.getElementById("status");
const setupStatusEl = document.getElementById("setup-status");
const modeCopy = {
  tailscale: {
    action: "Set up Tailscale",
    path: "comma · private relay · RangeBridge",
    detail: "Uses your own free Tailscale account. No shared server.",
  },
  local: {
    action: "Enable Wi-Fi access",
    path: "comma · this Wi-Fi · your apps",
    detail: "The authenticated API is reachable only from this local network.",
  },
  send: {
    action: "Enable custom backend",
    path: "comma · outbound HTTPS · your backend",
    detail: "Sends compact authenticated snapshots without exposing an inbound API.",
  },
  off: {
    action: "Turn network access off",
    path: "comma · local telemetry cache",
    detail: "Telemetry stays on this comma without a network endpoint.",
  },
};

async function api(path, options = {}) {
  options.credentials = "same-origin";
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function safeOwner(url) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" && parsed.hostname === "login.tailscale.com" ? parsed.href : "";
  } catch (error) {
    return "";
  }
}

function formatTime(seconds) {
  const safeSeconds = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(safeSeconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(Math.floor(safeSeconds % 60)).padStart(2, "0")}`;
}

function selectedMode() {
  return document.querySelector('input[name="mode"]:checked')?.value || "tailscale";
}

function selectMode(mode) {
  const input = document.querySelector(`input[name="mode"][value="${mode}"]`);
  if (input) input.checked = true;
  document.querySelectorAll("[data-option]").forEach(option => option.classList.toggle("selected", option.dataset.option === mode));
  document.getElementById("apply-mode").textContent = modeCopy[mode].action;
  document.getElementById("path").textContent = modeCopy[mode].path;
  document.getElementById("mode-detail").textContent = modeCopy[mode].detail;
  document.getElementById("backend-fields").classList.toggle("hidden", mode !== "send");
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const field = document.createElement("textarea");
  field.value = text;
  field.setAttribute("readonly", "");
  field.style.position = "fixed";
  field.style.left = "-9999px";
  document.body.appendChild(field);
  field.select();
  try {
    if (!document.execCommand("copy")) throw new Error("Copy failed");
  } finally {
    field.remove();
  }
}

function render(data) {
  latest = data;
  const tunnel = data.tunnel || {};
  if (!selectionInitialized) {
    const currentMode = data.config?.mode;
    selectMode(currentMode && currentMode !== "off" && modeCopy[currentMode] ? currentMode : "tailscale");
    selectionInitialized = true;
  }
  if (!backendInitialized) {
    document.getElementById("backend-url").value = data.config?.push?.url || "";
    document.getElementById("backend-vehicle-id").value = data.config?.push?.vehicleId || "";
    document.getElementById("backend-vehicle-name").value = data.config?.push?.vehicleName || "";
    if (data.config?.push?.hasToken) document.getElementById("backend-token").placeholder = "Leave blank to keep stored token";
    backendInitialized = true;
  }
  const lines = [data.message || "Ready.", `Mode: ${data.config?.mode || "off"}`, `Relay: ${tunnel.state || "disabled"}`,
    `Custom sender: ${data.config?.push?.enabled ? "enabled" : "disabled"}`];
  if (data.error) lines.push(`Error: ${data.error}`);
  if (tunnel.error) lines.push(`Relay detail: ${tunnel.error}`);
  statusEl.textContent = lines.join("\\n");
  const failed = data.jobState === "failed";
  const succeeded = data.jobState === "succeeded" || tunnel.state === "running";
  const hideStatus = data.jobState === "idle" && !data.error && !tunnel.error && !tunnel.ownerURL && tunnel.state !== "running";
  setupStatusEl.className = "panel" + (hideStatus ? " hidden" : failed ? " bad-panel" : succeeded ? " good-panel" : "");
  statusEl.className = "status" + (failed ? " bad" : succeeded ? " good" : "");
  document.getElementById("owner-wrap").classList.toggle("hidden", !(data.config?.mode === "tailscale" && tunnel.state !== "running"));
  document.getElementById("owner").textContent = tunnel.state === "needs-funnel-approval" ? "Approve Funnel" : "Owner login";
  const endpoint = tunnel.publicURL || data.localURL || "";
  document.getElementById("connection").classList.toggle("hidden", !endpoint && !data.generatedFetchToken);
  document.getElementById("endpoint").textContent = endpoint ? `Endpoint: ${endpoint}` : "";
  document.getElementById("token-wrap").classList.toggle("hidden", !data.generatedFetchToken);
  document.getElementById("fetch-token").textContent = data.generatedFetchToken || "";
  document.getElementById("connection-status").textContent = `comma found · Wi-Fi · setup closes in ${formatTime(data.remainingSeconds)}`;
  document.getElementById("apply-mode").disabled = data.jobState === "running";
  document.querySelectorAll('input[name="mode"]').forEach(input => input.disabled = data.jobState === "running");
  document.querySelectorAll("#backend-fields input").forEach(input => input.disabled = data.jobState === "running");
}

async function refresh() {
  try {
    render(await api("/api/status"));
  } catch (error) {
    statusEl.textContent = error.message;
    statusEl.className = "status bad";
  }
}

document.querySelectorAll('input[name="mode"]').forEach(input => input.addEventListener("change", () => selectMode(input.value)));
document.getElementById("mode-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    const mode = selectedMode();
    const backend = mode === "send";
    await api(backend ? "/api/backend" : "/api/mode", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(backend ? {
        url: document.getElementById("backend-url").value.trim(),
        token: document.getElementById("backend-token").value,
        vehicleId: document.getElementById("backend-vehicle-id").value.trim(),
        vehicleName: document.getElementById("backend-vehicle-name").value.trim(),
      } : {mode}),
    });
    setupStatusEl.classList.remove("hidden");
    await refresh();
  } catch (error) {
    setupStatusEl.classList.remove("hidden");
    statusEl.textContent = error.message;
    statusEl.className = "status bad";
  }
});

document.getElementById("owner").addEventListener("click", async () => {
  try {
    let target = safeOwner(latest.tunnel?.ownerURL || "");
    if (!target) target = safeOwner((await api("/api/tailscale/login", {method: "POST"})).ownerURL || "");
    if (!target) throw new Error("Tailscale did not return a valid owner URL.");
    location.assign(target);
  } catch (error) {
    statusEl.textContent = error.message;
    statusEl.className = "status bad";
  }
});

document.getElementById("copy").addEventListener("click", () => {
  copyText(document.getElementById("fetch-token").textContent);
});
document.getElementById("refresh").addEventListener("click", refresh);
document.getElementById("galaxy").addEventListener("click", () => {
  const host = location.hostname.includes(":") ? `[${location.hostname}]` : location.hostname;
  location.href = `http://${host}:8082/manage_navigation_keys`;
});
document.getElementById("rotate").addEventListener("click", async () => {
  try {
    await api("/api/token/rotate", {method: "POST"});
    await refresh();
  } catch (error) {
    statusEl.textContent = error.message;
    statusEl.className = "status bad";
  }
});
document.getElementById("finish").addEventListener("click", async () => {
  try { await api("/api/finish", {method: "POST"}); } catch (error) {}
  document.body.innerHTML = [
    "<main class='completion'><p class='eyebrow'>Setup closed</p><h1>EV Vehicle Telemetry is ready.</h1>",
    "<p>You can close this page. The API or custom sender can continue running while you drive.</p></main>",
  ].join("");
});
refresh();
setInterval(refresh, 2000);
setTimeout(refresh, Math.min(lifetime, 5) * 1000);
</script></body></html>"""
  return template.replace("__DURATION__", duration_json).replace("__NONCE__", nonce)


class _SetupHTTPServer(_TelemetryHTTPServer):
  def __init__(self, server_address, state):
    self.state = state
    super().__init__(
      server_address,
      TelemetrySetupRequestHandler,
      max_concurrent_requests=2,
      request_timeout_seconds=3.0,
      requests_per_second=4.0,
      request_burst=12,
      failed_auths_per_second=0.2,
      failed_auth_burst=5,
    )


class TelemetrySetupRequestHandler(VehicleTelemetryRequestHandler):
  server_version = "openpilot-telemetry-setup/1"

  def _write_setup_json(self, status, payload, *, retry_after=None):
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(encoded)))
    self.send_header("Cache-Control", "no-store")
    self.send_header("Connection", "close")
    self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    self.send_header("Referrer-Policy", "no-referrer")
    self.send_header("X-Content-Type-Options", "nosniff")
    if retry_after is not None:
      self.send_header("Retry-After", str(max(1, int(retry_after))))
    self.end_headers()
    try:
      self.wfile.write(encoded)
    except (BrokenPipeError, ConnectionResetError, TimeoutError):
      pass
    self.close_connection = True

  def _authorized(self, *, allow_query=False):
    supplied = self.headers.get(TELEMETRY_SETUP_TOKEN_HEADER, "")
    if not supplied:
      try:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get(TELEMETRY_SETUP_COOKIE_NAME)
        supplied = morsel.value if morsel is not None else ""
      except Exception:
        supplied = ""
    if allow_query and not supplied:
      supplied = parse_qs(urlsplit(self.path).query).get("setup", [""])[0]
    if hmac.compare_digest(str(supplied), self.server.state.token):
      return True
    if not self.server.failed_auth_limiter.consume():
      self._write_setup_json(429, {"error": "Too many requests."}, retry_after=5)
    else:
      self._write_setup_json(404, {"error": "Not found."})
    return False

  def _available(self):
    if not self.server.state.expired():
      return True
    self._write_setup_json(410, {"error": "This setup session has expired."})
    return False

  def _read_json(self):
    try:
      length = int(self.headers.get("Content-Length", "0"))
    except ValueError:
      self._write_setup_json(400, {"error": "Invalid content length."})
      return None
    if length < 0 or length > TELEMETRY_SETUP_MAX_BODY_BYTES:
      self._write_setup_json(413, {"error": "Request body is too large."})
      return None
    if not self.headers.get("Content-Type", "").lower().startswith("application/json"):
      self._write_setup_json(415, {"error": "JSON is required."})
      return None
    try:
      payload = json.loads(self.rfile.read(length))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
      self._write_setup_json(400, {"error": "Invalid JSON."})
      return None
    if not isinstance(payload, dict):
      self._write_setup_json(400, {"error": "A JSON object is required."})
      return None
    return payload

  def do_GET(self):
    if not self.server.request_limiter.consume():
      self._write_setup_json(429, {"error": "Too many requests."}, retry_after=1)
      return
    path = urlsplit(self.path).path
    if path == "/":
      if not self._authorized(allow_query=True) or not self._available():
        return
      nonce = secrets.token_urlsafe(12)
      remaining_seconds = max(0, int(self.server.state.expires_at - self.server.state.wall_time()))
      encoded = render_setup_page(remaining_seconds, nonce).encode("utf-8")
      self.send_response(200)
      self.send_header("Content-Type", "text/html; charset=utf-8")
      self.send_header("Content-Length", str(len(encoded)))
      self.send_header("Cache-Control", "no-store")
      self.send_header("Connection", "close")
      policy = "".join((
        "default-src 'none'; style-src 'unsafe-inline'; ",
        f"script-src 'nonce-{nonce}'; connect-src 'self'; form-action 'none'; ",
        "frame-ancestors 'none'; base-uri 'none'",
      ))
      self.send_header("Content-Security-Policy", policy)
      self.send_header("Referrer-Policy", "no-referrer")
      self.send_header("X-Content-Type-Options", "nosniff")
      self.send_header("X-Frame-Options", "DENY")
      self.send_header(
        "Set-Cookie",
        f"{TELEMETRY_SETUP_COOKIE_NAME}={self.server.state.token}; Path=/; Max-Age={remaining_seconds}; HttpOnly; SameSite=Strict",
      )
      self.end_headers()
      self.wfile.write(encoded)
      self.close_connection = True
      return
    if path == "/api/status" and self._authorized() and self._available():
      self._write_setup_json(200, self.server.state.status_payload())
      return
    self._write_setup_json(404, {"error": "Not found."})

  def do_POST(self):
    if not self.server.request_limiter.consume():
      self._write_setup_json(429, {"error": "Too many requests."}, retry_after=1)
      return
    if not self._authorized() or not self._available():
      return
    path = urlsplit(self.path).path
    if path == "/api/mode":
      payload = self._read_json()
      if payload is None:
        return
      mode = str(payload.get("mode") or "").strip().lower()
      if mode not in ("off", "local", "tailscale"):
        self._write_setup_json(400, {"error": "Unsupported setup mode."})
      elif self.server.state.start_mode(mode):
        self._write_setup_json(202, {"message": "Setup started."})
      else:
        self._write_setup_json(409, {"error": "Another setup action is already running."})
      return
    if path == "/api/backend":
      payload = self._read_json()
      if payload is None:
        return
      if self.server.state.start_backend(payload):
        self._write_setup_json(202, {"message": "Custom backend setup started."})
      else:
        self._write_setup_json(409, {"error": "Another setup action is already running."})
      return
    if path == "/api/tailscale/login":
      try:
        self._write_setup_json(200, {"ownerURL": self.server.state.owner_login()})
      except Exception as error:
        self._write_setup_json(409, {"error": str(error)[:240]})
      return
    if path == "/api/token/rotate":
      if self.server.state.start_token_rotation():
        self._write_setup_json(202, {"message": "Token rotation started."})
      else:
        self._write_setup_json(409, {"error": "Another setup action is already running."})
      return
    if path == "/api/finish":
      if self.server.state.job_running():
        self._write_setup_json(409, {"error": "Wait for the current setup action to finish."})
        return
      self._write_setup_json(200, {"message": "Setup is closing."})
      threading.Thread(target=self.server.shutdown, name="telemetry-setup-stop", daemon=True).start()
      return
    self._write_setup_json(404, {"error": "Not found."})


class TelemetrySetupService:
  def __init__(self, state):
    self.state = state
    self._server = None
    self._thread = None
    self.port = None

  def start(self, bind_address, port=TELEMETRY_SETUP_PORT):
    if self._server is not None:
      return
    self._server = _SetupHTTPServer((str(bind_address), int(port)), self.state)
    self.port = self._server.server_address[1]
    self.state.lan_address = str(bind_address)
    self._thread = threading.Thread(target=self._server.serve_forever, name="telemetry-setup-http", daemon=True)
    self._thread.start()

  def stop(self):
    server, thread = self._server, self._thread
    self._server = None
    self._thread = None
    self.port = None
    if server is not None:
      server.shutdown()
      server.server_close()
    if thread is not None and thread is not threading.current_thread():
      thread.join(timeout=2.0)


def launch_vehicle_telemetry_setup(
  data_dir=None,
  *,
  addresses=None,
  port=TELEMETRY_SETUP_PORT,
  duration_seconds=TELEMETRY_SETUP_DURATION_SECONDS,
  popen=None,
  python_executable=None,
  startup_timeout=2.0,
):
  if _device_is_onroad():
    raise RuntimeError("EV Vehicle Telemetry setup is available only while parked.")
  address = choose_lan_ipv4(addresses)
  if not address:
    raise RuntimeError("Connect the comma to Wi-Fi before starting telemetry setup.")
  port = max(1024, min(65535, int(port)))
  duration_seconds = max(TELEMETRY_SETUP_MIN_DURATION_SECONDS, min(TELEMETRY_SETUP_MAX_DURATION_SECONDS, int(duration_seconds)))
  data_dir = Path(data_dir or vehicle_telemetry_dir())
  status_path = telemetry_setup_status_path(data_dir)
  now = time.time()  # noqa: TID251
  existing = _owner_status(status_path)
  parsed_existing = urlsplit(str(existing.get("url") or ""))
  if existing.get("expiresAt", 0) > now + 10 and _pid_is_running(existing.get("pid")) and parsed_existing.hostname == address:
    return existing | {"token": parse_qs(parsed_existing.query).get("setup", [""])[0]}

  token = secrets.token_urlsafe(32)
  expires_at = now + duration_seconds
  url = f"http://{address}:{port}/?setup={token}"
  command = [
    python_executable or sys.executable,
    "-m",
    "openpilot.system.vehicle_telemetry.setup",
    "serve",
    "--data-dir",
    str(data_dir),
    "--host",
    address,
    "--port",
    str(port),
    "--expires-at",
    str(expires_at),
  ]
  process = (popen or subprocess.Popen)(
    command,
    stdin=subprocess.PIPE,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    close_fds=True,
    start_new_session=True,
  )
  if process.stdin is None:
    raise RuntimeError("Could not securely start the telemetry setup session.")
  process.stdin.write((token + "\n").encode("ascii"))
  process.stdin.close()
  status = {
    "schemaVersion": 1,
    "state": "starting",
    "pid": process.pid,
    "url": url,
    "expiresAt": expires_at,
  }
  current = _owner_status(status_path)
  if current.get("pid") != process.pid:
    _atomic_write_json(status_path, status)
  deadline = time.monotonic() + max(0.0, float(startup_timeout))
  while time.monotonic() < deadline:
    current = _owner_status(status_path)
    if current.get("pid") == process.pid and current.get("state") == "running":
      return current | {"token": token}
    if current.get("pid") == process.pid and current.get("state") == "error":
      raise RuntimeError(str(current.get("error") or "Telemetry setup could not start."))
    time.sleep(0.05)
  return status | {"token": token}


def serve_vehicle_telemetry_setup(data_dir, host, port, expires_at, token):
  if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", str(token or "")):
    raise RuntimeError("Invalid setup token.")
  if _device_is_onroad():
    raise RuntimeError("EV Vehicle Telemetry setup is available only while parked.")
  data_dir = Path(data_dir)
  data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
  lock_path = data_dir / TELEMETRY_SETUP_LOCK_FILENAME
  descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
  lock_file = os.fdopen(descriptor, "r+")
  try:
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
  except BlockingIOError as error:
    lock_file.close()
    raise RuntimeError("A telemetry setup session is already running.") from error

  try:
    try:
      os.setpriority(os.PRIO_PROCESS, 0, 19)
    except (AttributeError, OSError):
      pass
    state = SetupSessionState(data_dir, token, expires_at)
    service = TelemetrySetupService(state)
    service.start(host, port)
    status_path = telemetry_setup_status_path(data_dir)
    _atomic_write_json(status_path, {
      "schemaVersion": 1,
      "state": "running",
      "pid": os.getpid(),
      "url": f"http://{host}:{service.port}/?setup={token}",
      "expiresAt": expires_at,
    })

    stop = threading.Event()

    def lifecycle():
      while not stop.wait(2.0):
        if state.expired() or _device_is_onroad():
          service.stop()
          return

    watcher = threading.Thread(target=lifecycle, name="telemetry-setup-lifecycle", daemon=True)
    watcher.start()
    try:
      if service._thread is not None:
        service._thread.join()
    finally:
      stop.set()
      service.stop()
      watcher.join(timeout=1.0)
      current = _owner_status(status_path)
      if current.get("pid") == os.getpid():
        status_path.unlink(missing_ok=True)
  finally:
    lock_file.close()


def main(argv=None):
  parser = argparse.ArgumentParser(description="Launch the temporary EV Vehicle Telemetry LAN setup page.")
  subparsers = parser.add_subparsers(dest="action", required=False)
  launch_parser = subparsers.add_parser("launch")
  launch_parser.add_argument("--data-dir")
  launch_parser.add_argument("--port", type=int, default=TELEMETRY_SETUP_PORT)
  launch_parser.add_argument("--duration", type=int, default=TELEMETRY_SETUP_DURATION_SECONDS)
  serve_parser = subparsers.add_parser("serve", help=argparse.SUPPRESS)
  serve_parser.add_argument("--data-dir", required=True)
  serve_parser.add_argument("--host", required=True)
  serve_parser.add_argument("--port", type=int, required=True)
  serve_parser.add_argument("--expires-at", type=float, required=True)
  arguments = parser.parse_args(argv)
  action = arguments.action or "launch"
  try:
    if action == "serve":
      token = sys.stdin.readline(256).strip()
      serve_vehicle_telemetry_setup(arguments.data_dir, arguments.host, arguments.port, arguments.expires_at, token)
      return 0
    session = launch_vehicle_telemetry_setup(arguments.data_dir, port=arguments.port, duration_seconds=arguments.duration)
    parsed_url = urlsplit(str(session.get("url") or ""))
    print(json.dumps({
      "expiresAt": session["expiresAt"],
      "host": parsed_url.hostname or "",
      "pid": session["pid"],
      "port": parsed_url.port,
      "state": "running",
    }, separators=(",", ":"), sort_keys=True))
    return 0
  except Exception as error:
    if action == "serve":
      status_path = telemetry_setup_status_path(arguments.data_dir)
      status = _owner_status(status_path)
      status.update({
        "schemaVersion": 1,
        "state": "error",
        "pid": os.getpid(),
        "expiresAt": arguments.expires_at,
        "error": str(error)[:240],
      })
      _atomic_write_json(status_path, status)
    print(json.dumps({"error": str(error)[:240]}, separators=(",", ":")))
    return 1


if __name__ == "__main__":
  raise SystemExit(main())
