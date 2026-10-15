"""Branch adapter for the preserved upstream LAN advertiser."""
import logging
import re
import socket

from openpilot.starpilot.companion.bluetooth import upstream_module

# DNS-SD service names allow at most 15 bytes, excluding the underscore.
# Upstream's "starpilot-galaxy" is 16 bytes and fails Zeroconf registration.
SERVICE = '_sp-galaxy._tcp.local.'


class Advertisement:
  """Publish only the reachable address on each interface, including on older Android."""

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
        info = self.info_factory(SERVICE, f'{name}.{SERVICE}', port=8082,
                                 addresses=[socket.inet_aton(address)],
                                 properties={'protocol': 'galaxy-lan-1'}, server=f'{name}.local.')
        publisher.register_service(info, allow_name_change=True)
    except Exception as error:
      self.close()
      # The preserved loop retries OSError, but Zeroconf's own exceptions do
      # not inherit from it. Keep registration failures inside that retry loop.
      raise OSError(f'LAN registration failed: {type(error).__name__}') from error
    self.addresses = list(addresses)

  def close(self):
    publishers, self.publishers = self.publishers, []
    self.addresses = []
    for publisher in publishers:
      try:
        publisher.close()
      except Exception:
        logging.exception('LAN publisher cleanup failed')


def discovery_module():
  discovery = upstream_module('lan_discovery')
  discovery.SERVICE = SERVICE
  discovery.Advertisement = Advertisement
  return discovery


def main():
  discovery_module().main()


if __name__ == '__main__':
  main()
