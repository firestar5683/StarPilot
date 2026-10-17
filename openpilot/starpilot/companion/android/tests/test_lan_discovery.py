"""Real Zeroconf validation of the phone bridge's LAN advertiser, as discovered by Android."""
import importlib.util
from pathlib import Path
import socket
import sys
from unittest.mock import Mock, patch

import pytest

ANDROID = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ANDROID.parents[1] / 'galaxy_bluetooth/vendor'))
from zeroconf import ServiceInfo, NonUniqueNameException
from zeroconf._utils.name import service_type_name

spec = importlib.util.spec_from_file_location('lan_discovery', ANDROID.parents[1] / 'galaxy_bluetooth/bridge/lan_discovery.py')
assert spec is not None and spec.loader is not None
lan_discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lan_discovery)


def test_real_zeroconf_accepts_the_service_advertised_to_android():
  publishers = []
  interfaces = []

  def factory(addresses):
    publisher = Mock()
    # Registration performs strict type validation, unlike the old mock-only tests.
    publisher.register_service.side_effect = lambda info, **_: service_type_name(info.name)
    publishers.append(publisher)
    interfaces.append(addresses)
    return publisher

  advertisement = lan_discovery.Advertisement(factory, ServiceInfo)
  with patch.object(socket, 'gethostname', return_value='comma-test'):
    advertisement.update(['172.31.254.1', '192.168.1.25'])
  assert interfaces == [['172.31.254.1'], ['192.168.1.25']]
  for publisher, addresses in zip(publishers, interfaces, strict=True):
    info = publisher.register_service.call_args.args[0]
    assert info.type == lan_discovery.SERVICE
    assert info.parsed_addresses() == addresses
    assert info.port == 8082
    assert info.properties == {b'protocol': b'galaxy-lan-1'}
  assert publishers[0].register_service.call_args.args[0].server != publishers[1].register_service.call_args.args[0].server
  android = ANDROID / 'app/src/main/java/link/firestar/companion/LanDiscovery.kt'
  assert f'const val SERVICE = "{lan_discovery.SERVICE.removesuffix("local.")}"' in android.read_text()
  advertisement.update(['172.31.254.1', '192.168.1.25'])
  assert len(publishers) == 2
  advertisement.update([])
  advertisement.close()
  for publisher in publishers:
    publisher.close.assert_called_once()


def test_partial_registration_failure_closes_all_publishers_and_can_retry():
  first, failed, retried = Mock(), Mock(), Mock()
  failed.register_service.side_effect = OSError('interface went away')
  advertisement = lan_discovery.Advertisement(Mock(side_effect=[first, failed, retried]), ServiceInfo)
  with pytest.raises(OSError):
    advertisement.update(['172.31.254.1', '192.168.1.25'])
  first.close.assert_called_once()
  failed.close.assert_called_once()
  assert advertisement.addresses == []
  advertisement.update(['192.168.1.26'])
  assert advertisement.addresses == ['192.168.1.26']
  advertisement.close()
  retried.close.assert_called_once()


def test_long_device_hostname_stays_within_dns_label_limits():
  publisher = Mock()
  advertisement = lan_discovery.Advertisement(Mock(return_value=publisher), ServiceInfo)
  with patch.object(socket, 'gethostname', return_value='comma-' + 'x' * 100):
    advertisement.update(['192.168.100.200'])
  info = publisher.register_service.call_args.args[0]
  assert len(info.server.removesuffix('.local.')) <= 63
  assert service_type_name(info.name) == lan_discovery.SERVICE
  advertisement.close()


def test_loop_retries_zeroconf_exceptions_without_crashing():
  discovery = lan_discovery
  failed, good = Mock(), Mock()
  failed.register_service.side_effect = NonUniqueNameException()
  # A cleanup error must not prevent cleanup of other publishers or retrying.
  failed.close.side_effect = RuntimeError('already stopped')
  advertisement = lan_discovery.Advertisement(Mock(side_effect=[failed, good]), ServiceInfo)
  stopped = Mock(is_set=Mock(side_effect=[False, False, True]))
  with patch.object(discovery, 'Advertisement', return_value=advertisement), \
       patch.object(discovery, 'local_addresses', return_value=['192.168.1.25']), \
       patch.object(discovery, 'galaxy_listening', return_value=True), \
       patch.object(discovery.threading, 'Event', return_value=stopped), \
       patch.object(discovery.signal, 'signal'):
    discovery.main()
  assert stopped.wait.call_count == 2
  good.register_service.assert_called_once()
  good.close.assert_called_once()
