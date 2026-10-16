"""Advertise Galaxy on local Ethernet/Wi-Fi independently of Bluetooth."""
import ipaddress
import json
import logging
import re
import signal
import socket
import subprocess
import threading

SERVICE = '_sp-galaxy._tcp.local.'
PORT = 8082
LOG = logging.getLogger('galaxy-lan-discovery')


def private_addresses(interfaces):
  addresses = set()
  for interface in interfaces:
    name = interface.get('ifname', '')
    # Never advertise cellular, VPN, loopback, or virtual bridge addresses.
    # galaxy0 is the Galaxy hotspot; iPhones only find comma there via mDNS.
    if not re.match(r'^(wlan|wl|eth|en|galaxy0$)', name) or interface.get('operstate') != 'UP':
      continue
    for item in interface.get('addr_info', []):
      if item.get('family') != 'inet' or item.get('scope') != 'global':
        continue
      try:
        address = ipaddress.IPv4Address(item.get('local', ''))
      except ipaddress.AddressValueError:
        continue
      if any(address in network for network in PRIVATE_NETWORKS):
        addresses.add(str(address))
  return sorted(addresses)


PRIVATE_NETWORKS = tuple(ipaddress.IPv4Network(value) for value in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))


def local_addresses():
  result = subprocess.run(['ip', '-j', '-4', 'addr', 'show'], check=True, capture_output=True, text=True, timeout=3)
  return private_addresses(json.loads(result.stdout))


def galaxy_listening():
  try:
    with socket.create_connection(('127.0.0.1', PORT), timeout=0.3):
      return True
  except OSError:
    return False


class Advertisement:
  """Publish only the reachable address on each interface, including for older Android clients."""

  def __init__(self, factory=None, info_factory=None):
    if factory is None or info_factory is None:
      from zeroconf import Zeroconf, ServiceInfo, IPVersion
      def factory(addresses):
        return Zeroconf(interfaces=addresses, ip_version=IPVersion.V4Only)
      info_factory = ServiceInfo
    self.factory, self.info_factory = factory, info_factory
    self.publishers = []
    self.addresses = []

  def update(self, addresses):
    if addresses == self.addresses:
      return
    self.close()
    hostname = re.sub(r'[^A-Za-z0-9-]', '-', socket.gethostname()).strip('-')[:46] or 'comma'
    try:
      for address in addresses:
        publisher = self.factory([address])
        self.publishers.append(publisher)
        # Do not hand home-LAN clients the hotspot address (or vice versa).
        # Distinct hostnames also prevent cached A records crossing interfaces.
        name = f'{hostname}-{address.replace(".", "-")}'
        info = self.info_factory(SERVICE, f'{name}.{SERVICE}', port=PORT,
                                 addresses=[socket.inet_aton(address)],
                                 properties={'protocol': 'galaxy-lan-1'}, server=f'{name}.local.')
        publisher.register_service(info, allow_name_change=True)
    except Exception as error:
      self.close()
      # main() retries OSError, but Zeroconf's own exceptions do not inherit from it.
      raise OSError(f'LAN registration failed: {type(error).__name__}') from error
    self.addresses = list(addresses)
    if addresses:
      LOG.info('Galaxy Wi-Fi discovery available on %s local interface(s)', len(addresses))

  def close(self):
    publishers, self.publishers = self.publishers, []
    self.addresses = []
    for publisher in publishers:
      try:
        # Zeroconf sends goodbye records and stops its own background threads.
        publisher.close()
      except Exception:
        LOG.exception('LAN publisher cleanup failed')


def main():
  logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
  stopped = threading.Event()
  for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, lambda *_: stopped.set())
  advertisement = Advertisement()
  last_error = None
  try:
    while not stopped.is_set():
      try:
        advertisement.update(local_addresses() if galaxy_listening() else [])
        last_error = None
      except (OSError, ValueError, subprocess.SubprocessError) as error:
        advertisement.close()
        if type(error).__name__ != last_error:
          LOG.warning('Wi-Fi discovery unavailable: %s', type(error).__name__)
        last_error = type(error).__name__
      stopped.wait(30)
  finally:
    advertisement.close()


if __name__ == '__main__':
  main()
