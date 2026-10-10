import json
import stat
from unittest.mock import Mock

import pytest

from openpilot.starpilot.galaxy.hotspot import DEFAULT, HotspotSettings, atomic_json, hotspot_name, validate_config
from openpilot.starpilot.galaxy.hotspot_netlink import WirelessInterfaces, attribute, attributes
from openpilot.starpilot.galaxy.hotspot_worker import HotspotBackend, HotspotController, hostapd_config, overlapping_routes, radio_channel

CONFIG = {'enabled': True, 'ssid': 'TheGalaxy-6b86', 'password': '1234567890123456'}
DONGLE = 'b0c4a280b2f96b86'


@pytest.mark.parametrize('change', [{'enabled': 1}, {'ssid': 'bad\nssid'}, {'password': 'short'},
                                  {'password': 'has spaces in it'}, {'extra': True}, {'password': 'é' * 12}])
def test_strict_settings(change):
  with pytest.raises(ValueError):
    validate_config({**CONFIG, **change})


def test_settings_revision_permissions_and_credentials(tmp_path):
  settings = HotspotSettings(tmp_path, tmp_path / 'status', clock=lambda: 100, dongle_id=lambda: DONGLE)
  assert settings.read() == {**DEFAULT, 'ssid': 'TheGalaxy-6b86'}
  initial = settings.snapshot(True)
  payload = {'revision': initial['revision'], 'config': {**initial['config'], 'enabled': True}}
  with pytest.raises(PermissionError):
    settings.save(payload, lambda: False)
  assert not settings.path.exists()
  saved = settings.save(payload, lambda: True)
  assert len(saved['config']['password']) == 24
  assert stat.S_IMODE(settings.path.stat().st_mode) == 0o600
  with pytest.raises(FileExistsError):
    settings.save(payload, lambda: True)
  unchanged = settings.save({'revision': saved['revision'], 'config': {**saved['config'], 'password': ''}}, lambda: True)
  assert unchanged['config'] == saved['config']
  runtime = {'revision': saved['revision'], 'updated': 99, 'active': True, 'state': 'active', 'reason': '', 'channel': 149}
  atomic_json(settings.status_path, runtime)
  assert settings.snapshot(False)['active']
  assert not settings.snapshot(False)['editable']
  for updates in ({'updated': 80}, {'updated': 101}, {'revision': 'wrong'}):
    atomic_json(settings.status_path, {**runtime, **updates})
    assert settings.snapshot(True)['state'] == 'unavailable'


def test_settings_reject_symlink_and_oversize(tmp_path):
  settings = HotspotSettings(tmp_path, tmp_path / 'status', dongle_id=lambda: DONGLE)
  target = tmp_path / 'elsewhere'
  target.write_text(json.dumps(CONFIG))
  settings.path.symlink_to(target)
  with pytest.raises(OSError):
    settings.read()
  settings.path.unlink()
  settings.path.write_text(' ' * 4097)
  with pytest.raises(ValueError):
    settings.read()


def test_fixed_name_migration_password_and_restart(tmp_path):
  settings = HotspotSettings(tmp_path, dongle_id=lambda: DONGLE)
  atomic_json(settings.path, {**CONFIG, 'ssid': 'Old custom name'})
  assert settings.read() == CONFIG
  current = settings.snapshot(True)
  with pytest.raises(ValueError, match='fixed'):
    settings.save({'revision': current['revision'], 'config': {**CONFIG, 'ssid': 'Other name'}}, lambda: True)
  custom = {**CONFIG, 'password': 'my-new-password-123'}
  settings.save({'revision': current['revision'], 'config': custom}, lambda: True)
  restarted = HotspotSettings(tmp_path, dongle_id=lambda: DONGLE)
  assert restarted.read() == custom
  assert hotspot_name(DONGLE.upper()) == 'TheGalaxy-6b86'


@pytest.mark.parametrize('dongle', [None, '', 'UnregisteredDevice', '1234', 'x' * 16, b'0123456789abcdef'])
def test_unregistered_name_is_not_invented(dongle):
  with pytest.raises(ValueError, match='dongle ID'):
    hotspot_name(dongle)


@pytest.mark.parametrize('status,expected', [('wpa_state=COMPLETED\nfreq=5745', ('a', 149)),
  ('wpa_state=COMPLETED\nfreq=2412', ('g', 1)), ('wpa_state=DISCONNECTED\nfreq=5745', ('g', 6)),
  ('wpa_state=INACTIVE', ('g', 6)), ('wpa_state=SCANNING', ('g', 6)),
  ('wpa_state=ASSOCIATING', None), ('wpa_state=4WAY_HANDSHAKE\nfreq=5745', None),
  ('wpa_state=INTERFACE_DISABLED', None), ('FAIL', None),
  ('wpa_state=COMPLETED\nfreq=6000', None)])
def test_channel(status, expected):
  assert radio_channel(status) == expected


def test_automatic_standalone_connected_and_back():
  now = [100]
  backend = Mock()
  backend.alive.return_value = backend.ready.return_value = True
  controller = HotspotController(backend, clock=lambda: now[0])
  for status, expected in [('DISCONNECTED', ('g', 6)), ('COMPLETED\nfreq=5745', ('a', 149)), ('DISCONNECTED', ('g', 6))]:
    backend.channel.return_value = radio_channel('wpa_state=' + status)
    assert controller.tick(CONFIG)['state'] == 'starting'
    backend.start.assert_called_with(CONFIG, expected)
    assert controller.tick(CONFIG)['active']
    now[0] += 20
  assert backend.start.call_count == 3
  assert controller.tick({**CONFIG, 'enabled': False})['state'] == 'disabled'


def test_routes_and_config():
  assert not overlapping_routes([{'dst': 'default'}, {'dst': '192.168.180.0/24'}, {'dst': '172.31.254.0/24', 'dev': 'galaxy0'}])
  assert overlapping_routes([{'dst': '172.31.0.0/16', 'dev': 'wlan0'}])
  assert overlapping_routes([{'dst': '172.31.254.1', 'dev': 'eth0'}])
  config = hostapd_config(CONFIG, ('a', 149))
  assert 'interface=galaxy0\n' in config and 'channel=149\n' in config and 'wpa=2\n' in config
  assert 'country_code' not in config
  with pytest.raises(ValueError):
    hostapd_config({**CONFIG, 'ssid': 'Galaxy\ninterface=wlan0'}, ('a', 149))


def test_controller_lifecycle_and_channel_recovery():
  backend = Mock()
  backend.channel.return_value = ('a', 149)
  backend.alive.return_value = backend.ready.return_value = True
  now = [100]
  controller = HotspotController(backend, clock=lambda: now[0])
  assert controller.tick(CONFIG)['state'] == 'starting'
  assert controller.tick(CONFIG)['active']
  backend.start.assert_called_once_with(CONFIG, ('a', 149))
  backend.channel.return_value = ('g', 6)
  assert controller.tick(CONFIG)['state'] == 'error'  # rate limit restarts
  now[0] += 16
  assert controller.tick(CONFIG)['state'] == 'starting'
  backend.start.assert_called_with(CONFIG, ('g', 6))
  backend.channel.return_value = None
  assert controller.tick(CONFIG)['state'] == 'waiting'
  assert controller.applied is None
  assert controller.tick({**CONFIG, 'enabled': False})['state'] == 'disabled'
  backend.stop.assert_called()


def test_controller_readiness_and_failed_child():
  backend = Mock()
  backend.channel.return_value = ('a', 149)
  backend.alive.return_value = True
  backend.ready.return_value = False
  now = [0]
  controller = HotspotController(backend, clock=lambda: now[0])
  assert controller.tick(CONFIG)['state'] == 'starting'
  assert controller.tick(CONFIG)['state'] == 'starting'
  now[0] = 16
  assert controller.tick(CONFIG)['state'] == 'error'
  assert controller.applied is None
  now[0] = 32
  backend.start.side_effect = OSError('failed')
  assert controller.tick(CONFIG)['state'] == 'error'
  backend.stop.assert_called()


def test_backend_failure_rolls_back_only_owned_interface(tmp_path):
  run = Mock(return_value=Mock(stdout='[]'))
  interfaces = Mock()
  backend = HotspotBackend(tmp_path, run=run, interfaces=interfaces)
  backend.firewall = '/sbin/iptables-legacy'
  def command(args, **kwargs):
    if args[:3] == ['ip', 'address', 'add']:
      raise OSError('failed')
    return Mock(stdout='[]')
  run.side_effect = command
  with pytest.raises(OSError):
    backend.start(CONFIG, ('a', 149))
  interfaces.return_value.create.assert_called_once_with('galaxy0')
  interfaces.return_value.delete.assert_called_once_with('galaxy0')
  commands = [call.args[0] for call in run.call_args_list]
  assert ['nmcli', 'device', 'set', 'galaxy0', 'managed', 'no'] in commands
  assert all('wlan0' not in command and 'p2p0' not in command for command in commands)
  assert not backend.owned


def test_backend_conflict_does_not_create(tmp_path):
  interfaces = Mock()
  backend = HotspotBackend(tmp_path, run=Mock(return_value=Mock(stdout='[{"dst":"172.31.0.0/16"}]')), interfaces=interfaces)
  backend.firewall = '/sbin/iptables-legacy'
  with pytest.raises(RuntimeError):
    backend.start(CONFIG, ('a', 149))
  interfaces.assert_not_called()


def test_netlink_encoding_and_refusal():
  assert attributes(attribute(4, b'galaxy0\0')) == {4: b'galaxy0\0'}
  with pytest.raises(ValueError):
    attributes(b'\x03\x00\x01\x00')
  wireless = WirelessInterfaces.__new__(WirelessInterfaces)
  wireless.interfaces = Mock(return_value={'wlan0': {'type': 2, 'phy': 0, 'index': 1}, 'galaxy0': {'index': 7}})
  wireless.query = Mock()
  wireless.family = 22
  with pytest.raises(RuntimeError):
    wireless.create('galaxy0')
  wireless.query.assert_not_called()
  wireless.delete('galaxy0')
  wireless.query.assert_called_once_with(22, 8, attribute(3, b'\x07\0\0\0'), ack=True)
