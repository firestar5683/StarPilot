"""Metering uses actual hardware owner with synthetic modem/settings boundaries."""
from unittest.mock import Mock, patch

import pytest

from openpilot.common.esim.base import Profile, WEBBING_ICCID_PREFIX
from openpilot.common.hardware.comma.hardware import HardwareComma, NetworkType


@pytest.mark.parametrize('network', [NetworkType.cell2G, NetworkType.cell3G, NetworkType.cell4G, NetworkType.cell5G])
def test_prime_cellular_remains_metered_even_when_user_setting_is_false(network):
  hardware = HardwareComma.__new__(HardwareComma)
  hardware.get_modem_state = Mock(return_value={'iccid': WEBBING_ICCID_PREFIX + '123456789'})
  with patch('openpilot.common.params.Params') as params:
    assert hardware.get_network_metered(network) is True
  params.assert_not_called()


@pytest.mark.parametrize('modem', [{}, {'iccid': ''}, {'iccid': 'other-sim'}])
@pytest.mark.parametrize('metered', [False, True])
def test_other_cellular_retains_saved_metered_setting(modem, metered):
  hardware = HardwareComma.__new__(HardwareComma)
  hardware.get_modem_state = Mock(return_value=modem)
  with patch('openpilot.common.params.Params') as params:
    params.return_value.get_bool.return_value = metered
    assert hardware.get_network_metered(NetworkType.cell4G) is metered
  params.return_value.get_bool.assert_called_once_with('GsmMetered')


def test_wifi_never_borrows_cellular_prime_override():
  hardware = HardwareComma.__new__(HardwareComma)
  hardware.get_modem_state = Mock(side_effect=AssertionError('Wi-Fi must not inspect SIM'))
  with patch('openpilot.common.hardware.comma.hardware.wpa_supplicant_cmd', return_value={}), \
       patch('openpilot.common.hardware.base.HardwareBase.get_network_metered', return_value=False):
    assert hardware.get_network_metered(NetworkType.wifi) is False
  hardware.get_modem_state.assert_not_called()


@pytest.mark.parametrize('provider,iccid,expected', [
  ('Webbing', WEBBING_ICCID_PREFIX + '1234', True),
  ('Other', WEBBING_ICCID_PREFIX + '1234', False),
  ('Webbing', 'other-sim', False),
])
def test_comma_profile_still_requires_provider_and_shared_prefix(provider, iccid, expected):
  assert Profile(iccid, '', True, provider).is_comma is expected
