import importlib.util
from pathlib import Path
import socket
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lan_discovery', ROOT / 'bridge/lan_discovery.py')
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


def interface(name, address, state='UP'):
  return {'ifname': name, 'operstate': state, 'addr_info': [{'family': 'inet', 'scope': 'global', 'local': address}]}


class DiscoveryTests(unittest.TestCase):
  def test_only_up_private_wifi_and_ethernet_are_advertised(self):
    interfaces = [interface('wlan0', '192.168.10.85'), interface('eth0', '10.0.0.2'),
                  interface('wlan1', '192.168.10.85'), interface('wlan2', '172.16.0.4', 'DOWN'),
                  interface('wwan0', '10.0.0.3'), interface('tailscale0', '10.0.0.4'),
                  interface('lo', '127.0.0.1'), interface('eth1', '8.8.8.8'), interface('eth2', 'bad')]
    self.assertEqual(discovery.private_addresses(interfaces), ['10.0.0.2', '192.168.10.85'])

  def test_unchanged_network_does_not_republish_and_network_change_closes_old_service(self):
    publishers = []
    def factory(addresses):
      publisher = Mock()
      publishers.append(publisher)
      return publisher
    info_factory = Mock(return_value='service-record')
    advertisement = discovery.Advertisement(factory, info_factory)
    with patch.object(socket, 'gethostname', return_value='comma-19517593'):
      advertisement.update(['192.168.10.85'])
      advertisement.update(['192.168.10.85'])
      self.assertEqual(len(publishers), 1)
      properties = info_factory.call_args.kwargs['properties']
      self.assertEqual(properties, {'protocol': 'galaxy-lan-1'})
      # Neither pairing keys nor Galaxy session tokens appear in public TXT records.
      self.assertEqual(info_factory.call_args.kwargs['port'], 8082)
      advertisement.update(['192.168.10.86'])
      publishers[0].close.assert_called_once()
      self.assertEqual(len(publishers), 2)
      advertisement.update([])
      publishers[1].close.assert_called_once()
      self.assertEqual(advertisement.addresses, [])
      advertisement.close()
      publishers[1].close.assert_called_once()

  def test_registration_failure_closes_failed_publisher_and_can_retry(self):
    failed = Mock()
    failed.register_service.side_effect = OSError('no interface')
    good = Mock()
    factory = Mock(side_effect=[failed, good])
    advertisement = discovery.Advertisement(factory, Mock())
    with self.assertRaises(OSError):
      advertisement.update(['192.168.1.2'])
    failed.close.assert_called_once()
    self.assertEqual(advertisement.addresses, [])
    advertisement.update(['192.168.1.2'])
    good.register_service.assert_called_once()
    advertisement.close()


if __name__ == '__main__':
  unittest.main()
