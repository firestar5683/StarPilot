"""Root, pipe-leased phone uplink. All network changes are runtime-only.

hev-socks5-tunnel 2.18.0, static Linux ARM64 release.
SHA256: e44a6965cd718d98829f344e9f300a5664d12020557127b7469bee7c8f3098b0
Policy rules preserve every main-table connected route without modifying modem
or Android Auto profiles, including when a dead modem default route remains.
"""
from __future__ import annotations

import fcntl
import ipaddress
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import time

from openpilot.starpilot.galaxy.companion import STATUS_PATH, fresh, validate_lease
from openpilot.starpilot.galaxy.hotspot import atomic_json

INTERFACE = 'spuplink0'
RUNTIME = STATUS_PATH.parent
TABLE = '18082'
BINARY = Path(__file__).parent / 'bin/hev-socks5-tunnel_linux_arm64'
PROBE_INTERVAL = 15  # Re-probe other interfaces only this often unless the routes change.


def tunnel_config(lease):
  lease = validate_lease(lease)
  # JSON is valid YAML; credentials cannot introduce additional configuration.
  return json.dumps({'tunnel': {'name': INTERFACE, 'mtu': 1500, 'ipv4': '198.18.0.1'},
                     'socks5': {'address': lease['peer'], 'port': lease['port'], 'udp': 'udp',
                                'username': lease['user'], 'password': lease['pass']},
                     'mapdns': {'address': '198.18.0.2', 'port': 53, 'network': '198.19.0.0',
                                'netmask': '255.255.0.0', 'cache-size': 10000}})


def command(args, check=True):
  return subprocess.run(args, check=check, capture_output=True, text=True, timeout=3)


def other_internet(routes, probe=None):
  def tcp_probe(interface):
    # Numeric probes bypass mapped DNS and bind to the original interface.
    for address in ('1.1.1.1', '8.8.8.8'):
      try:
        with socket.socket() as sock:
          sock.settimeout(0.7)
          sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, interface.encode() + b'\0')
          sock.connect((address, 443))
        return True
      except OSError:
        pass
    return False
  probe = probe or tcp_probe
  devices = {r['dev'] for r in routes if r.get('dst', 'default') == 'default' and r.get('dev') not in (None, INTERFACE, 'galaxy0')}
  return any(probe(device) for device in sorted(devices))


class Backend:
  def __init__(self):
    self.child = None
    self.owned = False

  def status(self, active, reason=''):
    atomic_json(STATUS_PATH, {'active': active, 'updated': time.monotonic(),
                              'state': 'active' if active else 'error' if reason else 'waiting', 'reason': reason}, mode=0o644)

  def stop(self):
    # Keep the guard active until cleanup succeeds. The ownership marker lets a
    # replacement worker recover its own rules after SIGKILL or a tool timeout.
    failed = False

    def cleanup(args):
      nonlocal failed
      try:
        command(args, False)
      except (OSError, subprocess.SubprocessError):
        failed = True

    if self.owned:
      cleanup(['ip', 'rule', 'del', 'priority', '18001', 'table', TABLE])
      cleanup(['ip', 'rule', 'del', 'priority', '18000', 'lookup', 'main', 'suppress_prefixlength', '0'])
      cleanup(['resolvectl', 'revert', INTERFACE])
      cleanup(['ip', 'route', 'flush', 'table', TABLE])
      if self.child is not None:
        self.child.terminate()
        try:
          self.child.wait(timeout=3)
        except subprocess.TimeoutExpired:
          self.child.kill()
          self.child.wait(timeout=3)
      cleanup(['ip', 'link', 'delete', INTERFACE])
      cleanup(['resolvectl', 'flush-caches'])
      try:
        remaining = json.loads(command(['ip', '-j', 'rule']).stdout)
        failed |= any(rule.get('priority') in (18000, 18001) for rule in remaining)
      except (OSError, ValueError, subprocess.SubprocessError):
        failed = True
    self.child = None
    if failed:
      raise RuntimeError('Uplink cleanup incomplete; worker restart will retry')
    self.owned = False
    (RUNTIME / 'owned').unlink(missing_ok=True)
    self.status(False)

  def start(self, lease, routes):
    reserved = ipaddress.ip_network('198.18.0.0/15')
    if any(r.get('dst', 'default') != 'default' and r.get('dev') != INTERFACE and
           ipaddress.ip_network(r['dst'], strict=False).overlaps(reserved) for r in routes):
      raise RuntimeError('Mapped DNS subnet conflicts with an existing route')
    if Path('/sys/class/net/' + INTERFACE).exists():
      raise RuntimeError('Tunnel interface already exists')
    rules = json.loads(command(['ip', '-j', 'rule']).stdout)
    if any(r.get('priority') in (18000, 18001) for r in rules):
      raise RuntimeError('Policy routing priorities already in use')
    if json.loads(command(['ip', '-j', 'route', 'show', 'table', TABLE], False).stdout or '[]'):
      raise RuntimeError('Policy routing table already in use')
    config = RUNTIME / 'tunnel.json'
    atomic_json(config, json.loads(tunnel_config(lease)))
    (RUNTIME / 'owned').touch(mode=0o600)
    self.owned = True
    self.child = subprocess.Popen([str(BINARY), str(config)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + 3
    while not Path('/sys/class/net/' + INTERFACE).exists():
      if self.child.poll() is not None or time.monotonic() > deadline:
        raise RuntimeError('Tunnel failed to start')
      time.sleep(0.05)
    command(['nmcli', 'device', 'set', INTERFACE, 'managed', 'no'])
    command(['ip', 'link', 'set', INTERFACE, 'up'])
    command(['ip', 'route', 'add', '198.18.0.0/15', 'dev', INTERFACE])
    command(['ip', 'route', 'add', 'default', 'dev', INTERFACE, 'metric', '2000', 'table', TABLE])
    if 'updated' in lease and not fresh(lease, time.monotonic()):
      raise RuntimeError('Phone lease expired during tunnel startup')
    # Publish guard before enabling routing so upload loops cannot race activation.
    self.status(True)
    command(['ip', 'rule', 'add', 'priority', '18000', 'lookup', 'main', 'suppress_prefixlength', '0'])
    command(['ip', 'rule', 'add', 'priority', '18001', 'table', TABLE])
    command(['resolvectl', 'dns', INTERFACE, '198.18.0.2'])
    command(['resolvectl', 'domain', INTERFACE, '~.'])
    command(['resolvectl', 'default-route', INTERFACE, 'yes'])
    command(['resolvectl', 'flush-caches'])


def main():
  if os.geteuid() != 0:
    raise PermissionError('Companion worker requires root')
  RUNTIME.mkdir(mode=0o755, parents=True, exist_ok=True)
  with (RUNTIME / 'lock').open('w') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    backend = Backend()
    if (RUNTIME / 'owned').exists():
      backend.owned = True
      backend.stop()
    stop = False

    def stopped(*_):
      nonlocal stop
      stop = True

    signal.signal(signal.SIGTERM, stopped)
    signal.signal(signal.SIGINT, stopped)
    buffer, current, last_input = b'', None, time.monotonic()
    message = None
    reason = ''
    probed_routes, probed_at, has_other = None, 0., False
    try:
      while not stop:
        if not select.select([sys.stdin], [], [], 1)[0]:
          if time.monotonic() - last_input > 8 or (message and message.get('lease') and not fresh(message['lease'], time.monotonic())):
            break
          continue
        data = os.read(sys.stdin.fileno(), 8192)
        if not data:
          break
        buffer += data
        if len(buffer) > 16384:
          break
        if b'\n' not in buffer:
          if time.monotonic() - last_input > 8:
            break
          continue
        while b'\n' in buffer:
          raw, buffer = buffer.split(b'\n', 1)
          message = json.loads(raw)
          last_input = time.monotonic()
        if not fresh(message, time.monotonic()):
          break
        lease = message.get('lease')
        raw_routes = command(['ip', '-j', '-4', 'route', 'show', 'table', 'main']).stdout
        routes = json.loads(raw_routes)
        usable = lease and Path('/sys/class/net/galaxy0').exists() and fresh(lease, time.monotonic())
        if usable and (raw_routes != probed_routes or time.monotonic() - probed_at > PROBE_INTERVAL):
          # Probes to dead default routes can block for seconds; avoid repeating them every heartbeat.
          has_other = other_internet(routes)
          probed_routes, probed_at = raw_routes, time.monotonic()
        usable = usable and not has_other
        identity = tuple(validate_lease(lease)[key] for key in ('peer', 'port', 'user', 'pass')) if usable else None
        if identity != current or (backend.child and backend.child.poll() is not None):
          backend.stop()
          current = None
          if identity:
            backend.start(lease, routes)
            current = identity
        backend.status(current is not None)
        print(json.dumps({'active': current is not None}), flush=True)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
      reason = 'Phone internet setup failed. Check the installed tunnel binary and companion service.'
    finally:
      backend.stop()
      if reason:
        backend.status(False, reason)
      (RUNTIME / 'tunnel.json').unlink(missing_ok=True)


if __name__ == '__main__':
  main()
