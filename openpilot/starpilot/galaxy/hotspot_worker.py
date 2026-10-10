"""Privileged, pipe-leased hotspot worker. Never reconfigures the station link.

The unprivileged manager child sends validated settings/heartbeats on stdin.
EOF, ten seconds without a heartbeat, or SIGTERM tears down only our AP.
"""
from __future__ import annotations

import fcntl
import ipaddress
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import time

from openpilot.starpilot.galaxy.hotspot import ADDRESS, INTERFACE, NETWORK, HotspotSettings, validate_config
from openpilot.starpilot.galaxy.hotspot_netlink import WirelessInterfaces

ALIAS = 'starpilot-galaxy-hotspot'
RUNTIME = Path('/run/starpilot-galaxy-hotspot')
STANDALONE_CHANNEL = ('g', 6)


def radio_channel(status):
  fields = dict(line.split('=', 1) for line in status.splitlines() if '=' in line)
  # A disconnected station remains available for AA/Wi-Fi association. Do not
  # depend on an Internet connection to offer local access. Association itself
  # gets priority: pause the AP while the station is negotiating its channel.
  if fields.get('wpa_state') in ('DISCONNECTED', 'INACTIVE', 'SCANNING'):
    return STANDALONE_CHANNEL
  if fields.get('wpa_state') != 'COMPLETED':
    return None
  frequency = int(fields.get('freq', '0'))
  if 2412 <= frequency <= 2472 and (frequency - 2407) % 5 == 0:
    return 'g', (frequency - 2407) // 5
  if 5180 <= frequency <= 5825 and frequency % 5 == 0:
    return 'a', (frequency - 5000) // 5
  return None


def overlapping_routes(rows):
  subnet = ipaddress.ip_network(NETWORK)
  for row in rows:
    destination = row.get('dst', 'default')
    if destination == 'default' or row.get('dev') == INTERFACE:
      continue
    if subnet.overlaps(ipaddress.ip_network(destination, strict=False)):
      return True
  return False


def hostapd_config(config, channel):
  validate_config(config)
  band, number = channel
  if band not in ('a', 'g') or type(number) is not int or not 1 <= number <= 165:
    raise ValueError('Invalid channel')
  return (f'interface={INTERFACE}\ndriver=nl80211\nssid={config["ssid"]}\nhw_mode={band}\nchannel={number}\n' +
          f'wmm_enabled=1\nauth_algs=1\nwpa=2\nwpa_passphrase={config["password"]}\n' +
          'wpa_key_mgmt=WPA-PSK\nrsn_pairwise=CCMP\nmax_num_sta=4\n')


class HotspotBackend:
  def __init__(self, root=RUNTIME, run=subprocess.run, interfaces=WirelessInterfaces, popen=subprocess.Popen):
    self.root, self.run, self.interfaces, self.popen = root, run, interfaces, popen
    self.children = []
    self.owned = False
    self.firewall = shutil.which('iptables-legacy') or shutil.which('iptables')

  def command(self, args, check=True):
    return self.run(args, check=check, text=True, capture_output=True, timeout=5)

  def channel(self):
    return radio_channel(self.command(['/usr/sbin/wpa_cli', '-i', 'wlan0', 'status']).stdout)

  def alive(self):
    return self.owned and len(self.children) == 2 and all(child.poll() is None for child in self.children)

  def ready(self):
    reply = self.command(['/usr/sbin/hostapd_cli', '-p', str(self.root / 'control'), '-i', INTERFACE, 'status'], check=False)
    return reply.returncode == 0 and 'state=ENABLED' in reply.stdout.splitlines()

  def _wireless(self, method):
    client = self.interfaces()
    try:
      getattr(client, method)(INTERFACE)
    finally:
      client.close()

  def stale_owned(self):
    try:
      return Path(f'/sys/class/net/{INTERFACE}/ifalias').read_text().strip() == ALIAS
    except FileNotFoundError:
      return False

  def stop(self):
    for child in self.children:
      if child.poll() is None:
        child.terminate()
    for child in self.children:
      try:
        child.wait(timeout=2)
      except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=2)
    self.children.clear()
    owned = self.owned or self.stale_owned()
    if owned:
      self._wireless('delete')
      self.owned = False
    if self.firewall:
      # The comment distinguishes our rules even if the kernel already removed
      # the AP after a worker crash. Never flush the shared forwarding chain.
      for direction in ('-i', '-o'):
        self.command(self.firewall_rule('-D', direction), check=False)

  def firewall_rule(self, operation, direction):
    return [self.firewall, '-w', '2', operation, 'FORWARD', direction, INTERFACE,
            '-m', 'comment', '--comment', ALIAS, '-j', 'DROP']

  def start(self, config, channel):
    if not self.firewall:
      raise RuntimeError('Firewall helper unavailable')
    if overlapping_routes(json.loads(self.command(['ip', '-j', '-4', 'route', 'show', 'table', 'all']).stdout)):
      raise RuntimeError('Hotspot subnet conflicts with an existing network')
    self._wireless('create')
    self.owned = True
    try:
      self.command(['ip', 'link', 'set', 'dev', INTERFACE, 'alias', ALIAS])
      self.command(['nmcli', 'device', 'set', INTERFACE, 'managed', 'no'])
      self.command(['sysctl', '-w', f'net.ipv6.conf.{INTERFACE}.disable_ipv6=1'])
      # Local access only, even if the phone supplies its own default route.
      for direction in ('-i', '-o'):
        self.command(self.firewall_rule('-I', direction))
      self.command(['ip', 'address', 'add', f'{ADDRESS}/24', 'dev', INTERFACE])
      self.command(['ip', 'link', 'set', 'dev', INTERFACE, 'up'])
      ap = self.root / 'hostapd.conf'
      ap.write_text(hostapd_config(config, channel) + f'ctrl_interface={self.root / "control"}\n')
      ap.chmod(0o600)
      dhcp = self.root / 'dnsmasq.conf'
      dhcp.write_text(f'interface={INTERFACE}\nbind-interfaces\nport=0\nno-resolv\nno-hosts\n' +
                      'dhcp-range=172.31.254.10,172.31.254.30,255.255.255.0,10m\n' +
                      'dhcp-option=3\ndhcp-option=6\nleasefile-ro\n')
      for command in (['/usr/sbin/hostapd', str(ap)],
                      ['/usr/sbin/dnsmasq', '--keep-in-foreground', '--conf-file=' + str(dhcp)]):
        self.children.append(self.popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL, close_fds=True))
    except BaseException:
      self.stop()
      raise


class HotspotController:
  def __init__(self, backend, clock=time.monotonic):
    self.backend, self.clock = backend, clock
    self.applied, self.retry_at, self.ready_deadline = None, 0.0, 0.0

  def tick(self, config):
    if not config['enabled']:
      self.backend.stop()
      self.applied = None
      return {'active': False, 'state': 'disabled', 'reason': ''}
    try:
      channel = self.backend.channel()
      if channel is None:
        self.backend.stop()
        self.applied = None
        return {'active': False, 'state': 'waiting', 'reason': 'Waiting for Wi-Fi radio readiness or a supported connection channel.'}
      desired = (dict(config), channel)
      if desired != self.applied or not self.backend.alive():
        self.backend.stop()
        self.applied = None
        if self.clock() < self.retry_at:
          return {'active': False, 'state': 'error', 'reason': 'Hotspot unavailable; retrying shortly.'}
        self.retry_at = self.clock() + 15
        self.backend.start(config, channel)
        self.applied = desired
        self.ready_deadline = self.clock() + 15
        return {'active': False, 'state': 'starting', 'reason': 'Starting the local Wi-Fi network.', 'channel': channel[1]}
      if not self.backend.ready():
        if self.clock() >= self.ready_deadline:
          raise RuntimeError('Hotspot did not become ready')
        return {'active': False, 'state': 'starting', 'reason': 'Waiting for the Wi-Fi access point.', 'channel': channel[1]}
      return {'active': True, 'state': 'active', 'reason': '', 'channel': channel[1]}
    except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError):
      self.backend.stop()
      self.applied = None
      self.retry_at = self.clock() + 15
      return {'active': False, 'state': 'error', 'reason': 'Hotspot could not start on this channel. Projection Wi-Fi was not reconfigured.'}


def main():
  if os.geteuid() != 0:
    raise RuntimeError('Hotspot worker requires network administration privileges')
  os.umask(0o077)
  RUNTIME.mkdir(mode=0o700, exist_ok=True)
  if RUNTIME.is_symlink() or RUNTIME.stat().st_uid != 0:
    raise RuntimeError('Unsafe hotspot runtime directory')
  fd = os.open(RUNTIME / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
  fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
  backend = HotspotBackend()
  controller = HotspotController(backend)
  stopped = False
  def stop(*_):
    nonlocal stopped
    stopped = True
  signal.signal(signal.SIGTERM, stop)
  signal.signal(signal.SIGINT, stop)
  config, buffer, last = None, b'', time.monotonic()
  try:
    backend.stop()  # clean an interface explicitly marked as ours after a crash
    while not stopped and time.monotonic() - last < 10:
      if select.select([sys.stdin], [], [], 2)[0]:
        data = os.read(sys.stdin.fileno(), 4097)
        if not data:
          break
        buffer += data
        if len(buffer) > 4096:
          raise ValueError('Oversized settings input')
        while b'\n' in buffer:
          line, buffer = buffer.split(b'\n', 1)
          config = validate_config(json.loads(line))
          last = time.monotonic()
      if config is not None:
        print(json.dumps({**controller.tick(config), 'revision': HotspotSettings.revision(config)}), flush=True)
  finally:
    backend.stop()
    os.close(fd)


if __name__ == '__main__':
  main()
