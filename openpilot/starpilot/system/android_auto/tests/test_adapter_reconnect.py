from unittest.mock import Mock
import pytest

from openpilot.starpilot.system.android_auto.bluez_phone import BluezPhone, DEVICE_IFACE, HFP_HF_UUID
from openpilot.starpilot.system.android_auto.sdp import AA_WIRELESS_UUID

ADDRESS = '50:5A:65:8B:8B:82'
PATH = '/org/bluez/hci0/dev_50_5A_65_8B_8B_82'
PNP = '00001200-0000-1000-8000-00805f9b34fb'


def phone(*, uuids, paired=True, connected=False, registered=True, call_error=None):
  instance = BluezPhone.__new__(BluezPhone)
  props = {'Address': ADDRESS, 'Alias': 'AndroidAuto-8b83', 'UUIDs': uuids,
           'Paired': paired, 'Connected': connected, 'Trusted': True}
  instance.managed_objects = Mock(side_effect=lambda: {PATH: {DEVICE_IFACE: props}})
  instance._profile_registered = registered
  events, calls = [], []
  instance.log = Mock(side_effect=lambda event, **details: events.append((event, details)))
  def call(*args, **kwargs):
    calls.append((args, kwargs))
    if call_error:
      raise call_error
  instance._call = Mock(side_effect=call)
  return instance, props, calls, events


def test_bonded_custom_adapter_bypasses_generic_profile_connect():
  instance, props, calls, events = phone(uuids=[PNP, str(AA_WIRELESS_UUID)], call_error=TimeoutError())
  assert instance.device(ADDRESS)['android_auto']
  instance.connect_device(ADDRESS)
  assert calls == []
  assert events == [('device_connect_raw_android_auto', {'address': ADDRESS})]
  assert props['Paired'] and props['Trusted'] and not props['Connected']


def test_connected_peer_keeps_existing_fast_path():
  instance, _props, calls, events = phone(uuids=[str(AA_WIRELESS_UUID)], connected=True)
  instance.connect_device(ADDRESS)
  assert calls == [] and events == []


@pytest.mark.parametrize('uuids,paired', [([PNP], True), ([str(AA_WIRELESS_UUID)], False),
                                        (['00000000-0000-0000-0000-000000000000'], True)])
def test_no_raw_bypass_without_exact_wireless_uuid_and_bond(uuids, paired):
  instance, _props, calls, events = phone(uuids=uuids, paired=paired)
  instance.connect_device(ADDRESS)
  assert [args[2] for args, _kwargs in calls] == ['Connect']
  assert events == []


@pytest.mark.parametrize('uuids', [[HFP_HF_UUID], [HFP_HF_UUID, str(AA_WIRELESS_UUID)]])
def test_hfp_car_and_hfp_adapter_keep_specific_profile_path(uuids):
  instance, _props, calls, _events = phone(uuids=uuids)
  instance.connect_device(ADDRESS, timeout=7)
  assert calls == [((PATH, DEVICE_IFACE, 'ConnectProfile', 's', (HFP_HF_UUID,)), {'timeout': 7})]


def test_unregistered_hfp_gateway_preserves_generic_behavior():
  instance, _props, calls, _events = phone(uuids=[HFP_HF_UUID, str(AA_WIRELESS_UUID)], registered=False)
  instance.connect_device(ADDRESS)
  assert [args[2] for args, _kwargs in calls] == ['Connect']


def test_hfp_failure_keeps_existing_fallback_behavior():
  instance, _props, calls, events = phone(uuids=[HFP_HF_UUID], call_error=RuntimeError('failed'))
  instance.connect_device(ADDRESS)
  assert [args[2] for args, _kwargs in calls] == ['ConnectProfile', 'Connect']
  assert len(events) == 2


def test_non_adapter_timeout_is_not_swallowed():
  instance, _props, calls, _events = phone(uuids=[PNP], call_error=TimeoutError('pending'))
  with pytest.raises(TimeoutError, match='pending'):
    instance.connect_device(ADDRESS)
  assert [args[2] for args, _kwargs in calls] == ['Connect']


def test_unknown_address_is_still_rejected():
  instance, _props, calls, _events = phone(uuids=[str(AA_WIRELESS_UUID)])
  with pytest.raises(RuntimeError, match='not known'):
    instance.connect_device('00:00:00:00:00:00')
  assert calls == []
