import sys
from types import ModuleType
from unittest.mock import Mock

import pytest

from openpilot.starpilot.system.android_auto.supervisor import _is_onroad


@pytest.mark.parametrize('raw,expected', [(None, False), (b'0', True), (b'1', False), (b'2', False), (b'', False), (b'garbage', False)])
def test_auto_connect_uses_exact_registered_offroad_state(tmp_path, monkeypatch, raw, expected):
  path = tmp_path / 'IsOffroad'
  if raw is not None:
    path.write_bytes(raw)
  params = Mock()
  def param_path(key):
    if key != 'IsOffroad':
      raise KeyError(key)
    return str(path)
  params.get_param_path.side_effect = param_path
  module = ModuleType('openpilot.common.params')
  module.Params = Mock(return_value=params)
  monkeypatch.setitem(sys.modules, module.__name__, module)
  assert _is_onroad() is expected
  params.get_param_path.assert_called_once_with('IsOffroad')
  params.get_bool.assert_not_called()


def test_unreadable_or_failed_params_cannot_trigger_auto_connect(tmp_path, monkeypatch):
  module = ModuleType('openpilot.common.params')
  module.Params = Mock(side_effect=RuntimeError('unavailable'))
  monkeypatch.setitem(sys.modules, module.__name__, module)
  assert _is_onroad() is False
  path = tmp_path / 'IsOffroad'
  path.mkdir()
  module.Params = Mock(return_value=Mock(get_param_path=lambda key: str(path)))
  assert _is_onroad() is False
