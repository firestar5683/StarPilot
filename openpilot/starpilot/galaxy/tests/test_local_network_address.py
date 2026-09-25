import json
from types import SimpleNamespace

from openpilot.starpilot.galaxy.local_access import LocalAccess


def test_network_changes_expire_and_virtual_addresses_never_appear():
  def iface(name, ip, **extra):
    return dict(ifname=name, flags=['UP'], addr_info=[dict(family='inet', scope='global', local=ip)], **extra)
  now = [0.0]
  inventory = [iface('wlan0', '192.168.3.110'), iface('tun0', '10.0.0.1'),
               iface('customVPN', '10.1.0.1', linkinfo={'info_kind': 'wireguard'}),
               iface('ppp0', '10.208.34.39'), iface('p2p-wlan0', '192.168.49.1'), iface('eth0', '10.2.3.4', operstate='DOWN')]
  def run(*args, **kwargs):
    return SimpleNamespace(stdout=json.dumps(inventory).encode())
  reader = LocalAccess(run=run, clock=lambda: now[0])
  assert [r['interface'] for r in reader.snapshot()['addresses']] == ['wlan0']
  inventory.clear()
  now[0] = 5.1
  assert reader.snapshot()['addresses'] == []
  inventory.append(iface('wlan0', '192.168.1.50'))
  now[0] = 10.2
  assert reader.snapshot()['addresses'][0]['url'] == 'http://192.168.1.50:8082/'
