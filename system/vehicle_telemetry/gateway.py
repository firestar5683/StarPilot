#!/usr/bin/env python3
"""Provision and run the optional public FRP + Cloudflare DNS gateway.

This module runs on an Internet-reachable Linux host, not on the vehicle. It
keeps Cloudflare credentials at the gateway, updates the apex and wildcard DNS
records, and generates an frps configuration compatible with the vehicle's
``frp`` telemetry mode.
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import subprocess
import time

from pathlib import Path

import requests

from openpilot.system.vehicle_telemetry.core import _atomic_write_bytes, _read_owner_only_json
from openpilot.system.vehicle_telemetry.tunnel import _toml_string


CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"
DEFAULT_ADDRESS_SOURCE_URL = "https://api.ipify.org?format=json"


def _valid_absolute_path(value, default=""):
  path = str(value or default).strip()[:1024]
  return path if path.startswith("/") else default


def normalize_gateway_config(raw):
  if not isinstance(raw, dict):
    raise ValueError("Gateway configuration must be a JSON object.")
  frp = raw.get("frp") if isinstance(raw.get("frp"), dict) else {}
  dns = raw.get("dns") if isinstance(raw.get("dns"), dict) else {}
  zone_name = str(dns.get("zoneName") or "").strip().lower().rstrip(".")
  subdomain_host = str(frp.get("subdomainHost") or "").strip().lower().rstrip(".")
  if not zone_name or subdomain_host != zone_name:
    raise ValueError("Free Cloudflare TLS mode requires frp.subdomainHost to equal dns.zoneName.")

  token = str(frp.get("token") or "").strip()
  api_token = str(dns.get("apiToken") or "").strip()
  zone_id = str(dns.get("zoneId") or "").strip()
  if len(token) < 32 or len(api_token) < 20 or not zone_id:
    raise ValueError("Gateway FRP token, Cloudflare API token, and zone ID are required.")
  cert_file = _valid_absolute_path(frp.get("certFile"))
  key_file = _valid_absolute_path(frp.get("keyFile"))
  if not cert_file or not key_file:
    raise ValueError("Gateway FRP TLS certificate and key paths are required.")

  return {
    "frp": {
      "binaryPath": _valid_absolute_path(frp.get("binaryPath"), "/usr/local/bin/frps"),
      "bindPort": max(1, min(65535, int(frp.get("bindPort") or 7000))),
      "vhostHTTPPort": max(1, min(65535, int(frp.get("vhostHTTPPort") or 80))),
      "subdomainHost": subdomain_host,
      "token": token,
      "certFile": cert_file,
      "keyFile": key_file,
    },
    "dns": {
      "zoneId": zone_id,
      "zoneName": zone_name,
      "apiToken": api_token,
      "address": str(dns.get("address") or "auto").strip(),
      "addressSourceURL": str(dns.get("addressSourceURL") or DEFAULT_ADDRESS_SOURCE_URL).strip(),
      "refreshSeconds": max(60, min(86400, int(dns.get("refreshSeconds") or 300))),
    },
  }


def discover_public_ipv4(session, url=DEFAULT_ADDRESS_SOURCE_URL):
  response = session.get(url, timeout=(3.0, 5.0), allow_redirects=False)
  try:
    response.raise_for_status()
    payload = response.json()
    value = payload.get("ip") if isinstance(payload, dict) else ""
    return str(ipaddress.IPv4Address(value))
  finally:
    response.close()


class CloudflareDNSUpdater:
  def __init__(self, zone_id, api_token, session=None):
    self.zone_id = zone_id
    self.authorization_headers = {
      "Authorization": f"Bearer {api_token}",
      "Content-Type": "application/json",
    }
    self.session = session or requests.Session()
    self.session.trust_env = False

  def _result(self, response):
    try:
      payload = response.json()
    finally:
      response.close()
    if not isinstance(payload, dict) or not payload.get("success"):
      errors = payload.get("errors") if isinstance(payload, dict) else None
      raise RuntimeError(f"Cloudflare DNS request failed: {errors or 'invalid response'}")
    return payload.get("result")

  def upsert_a_record(self, name, address, *, proxied):
    base_url = f"{CLOUDFLARE_API_BASE}/zones/{self.zone_id}/dns_records"
    response = self.session.get(
      base_url,
      headers=self.authorization_headers,
      params={"type": "A", "name": name},
      timeout=(3.0, 8.0),
      allow_redirects=False,
    )
    records = self._result(response) or []
    body = {
      "type": "A",
      "name": name,
      "content": str(ipaddress.IPv4Address(address)),
      "ttl": 1,
      "proxied": bool(proxied),
      "comment": "Managed by the openpilot EV Vehicle Telemetry gateway",
    }
    if records:
      record_id = str(records[0].get("id") or "")
      if not record_id:
        raise RuntimeError(f"Cloudflare returned an invalid DNS record for {name}.")
      response = self.session.put(
        f"{base_url}/{record_id}",
        headers=self.authorization_headers,
        json=body,
        timeout=(3.0, 8.0),
        allow_redirects=False,
      )
    else:
      response = self.session.post(
        base_url,
        headers=self.authorization_headers,
        json=body,
        timeout=(3.0, 8.0),
        allow_redirects=False,
      )
    return self._result(response)

  def update_gateway_records(self, zone_name, address):
    # The apex is DNS-only so frpc can reach bindPort directly. The wildcard is
    # proxied so Cloudflare terminates public HTTPS before forwarding HTTP to
    # frps's vhostHTTPPort.
    return {
      "gateway": self.upsert_a_record(zone_name, address, proxied=False),
      "wildcard": self.upsert_a_record(f"*.{zone_name}", address, proxied=True),
    }


def build_frps_config(frp, token_path):
  lines = [
    f"bindPort = {frp['bindPort']}",
    f"vhostHTTPPort = {frp['vhostHTTPPort']}",
    f"subdomainHost = {_toml_string(frp['subdomainHost'])}",
    "transport.tls.force = true",
    'auth.method = "token"',
    'auth.tokenSource.type = "file"',
    f"auth.tokenSource.file.path = {_toml_string(str(token_path))}",
  ]
  if frp.get("certFile") and frp.get("keyFile"):
    lines += [
      f"transport.tls.certFile = {_toml_string(frp['certFile'])}",
      f"transport.tls.keyFile = {_toml_string(frp['keyFile'])}",
    ]
  lines.append("")
  return "\n".join(lines)


def provision_gateway(config, output_dir, session=None):
  output_dir = Path(output_dir)
  output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
  os.chmod(output_dir, 0o700)
  token_path = output_dir / "frps_token"
  config_path = output_dir / "frps.generated.toml"
  _atomic_write_bytes(token_path, (config["frp"]["token"] + "\n").encode("utf-8"))
  _atomic_write_bytes(config_path, build_frps_config(config["frp"], token_path).encode("utf-8"))

  dns = config["dns"]
  updater = CloudflareDNSUpdater(dns["zoneId"], dns["apiToken"], session=session)
  address = dns["address"]
  if address == "auto":
    address_session = requests.Session()
    address_session.trust_env = False
    try:
      address = discover_public_ipv4(address_session, dns["addressSourceURL"])
    finally:
      address_session.close()
  else:
    address = str(ipaddress.IPv4Address(address))
  updater.update_gateway_records(dns["zoneName"], address)
  return config_path, address


def run_gateway(config, output_dir):
  process = None
  while True:
    try:
      config_path, address = provision_gateway(config, output_dir)
      print(f"Gateway DNS points {config['dns']['zoneName']} and *.{config['dns']['zoneName']} to {address}")
      if process is None or process.poll() is not None:
        binary = Path(config["frp"]["binaryPath"])
        if not binary.is_file() or not os.access(binary, os.X_OK):
          raise FileNotFoundError(f"frps is not executable: {binary}")
        process = subprocess.Popen([str(binary), "-c", str(config_path)], close_fds=True)
      time.sleep(config["dns"]["refreshSeconds"])
    except KeyboardInterrupt:
      break
    except Exception as error:
      print(f"Gateway provisioning failed: {error}")
      time.sleep(30.0)
  if process is not None and process.poll() is None:
    process.terminate()
    process.wait(timeout=5.0)


def main():
  parser = argparse.ArgumentParser(description="Provision the EV Vehicle Telemetry FRP gateway and Cloudflare DNS.")
  parser.add_argument("config", type=Path, help="Owner-only gateway JSON configuration")
  parser.add_argument("--output-dir", type=Path, default=Path("./vehicle-telemetry-gateway"))
  parser.add_argument("--once", action="store_true", help="Generate config and update DNS without starting frps")
  args = parser.parse_args()

  raw = _read_owner_only_json(args.config)
  if raw is None:
    raise SystemExit("Gateway config must exist, be valid JSON, and have mode 0600.")
  config = normalize_gateway_config(raw)
  if args.once:
    config_path, address = provision_gateway(config, args.output_dir)
    print(f"Generated {config_path}; DNS now points to {address}")
  else:
    run_gateway(config, args.output_dir)


if __name__ == "__main__":
  main()
