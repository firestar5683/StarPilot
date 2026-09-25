from unittest.mock import Mock, mock_open, patch

import pytest

from openpilot.common.hardware.comma.hardware import HardwareComma


@pytest.mark.parametrize('device', ['tici', 'tizi'])
def test_panda_owns_comma_three_infrared(device):
  hardware = HardwareComma.__new__(HardwareComma)
  hardware.get_device_type = Mock(return_value=device)
  with patch('builtins.open') as opened:
    hardware.set_ir_power(100)
  opened.assert_not_called()


def test_comma_four_retains_soc_infrared():
  hardware = HardwareComma.__new__(HardwareComma)
  hardware.get_device_type = Mock(return_value='mici')
  with patch('builtins.open', mock_open()) as opened:
    hardware.set_ir_power(50)
  assert [call.args[0] for call in opened.call_args_list] == [
    '/sys/class/leds/led:switch_2/brightness',
    '/sys/class/leds/led:torch_2/brightness',
    '/sys/class/leds/led:switch_2/brightness',
  ]
  assert [call.args[0] for call in opened().write.call_args_list] == ['0\n', '150\n', '150\n']
