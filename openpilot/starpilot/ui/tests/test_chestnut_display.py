from types import SimpleNamespace
from unittest.mock import Mock, patch

import pyray as rl
import pytest

from openpilot.selfdrive.ui.mici.onroad.augmented_road_view import AugmentedRoadView
from openpilot.selfdrive.ui.ui_state import UIState


@pytest.mark.parametrize('raw, expected', [(True, True), (False, False), (b'1', True), (b'0', False),
                                          ('1', True), ('0', False), (None, None), (b'invalid', None)])
def test_native_chestnut_status_accepts_typed_params(raw, expected):
  params = Mock()
  params.get.return_value = raw
  params.get_bool.return_value = False
  state = SimpleNamespace(params=params, started=True, chestnut_compiled=True, usb_connected=False)
  with patch('openpilot.selfdrive.ui.ui_state.get_cache', return_value=None), \
       patch('openpilot.selfdrive.ui.ui_state.read_int', return_value=0):
    UIState.update_params(state)
  assert state.chestnut_active is expected


def test_custom_model_source_layer_uses_native_status_animation():
  view = SimpleNamespace(_hud_renderer=Mock())
  rect = rl.Rectangle(0, 0, 476, 240)
  AugmentedRoadView.render_model_source_layer(view, rect)
  view._hud_renderer._update_state.assert_called_once_with()
  view._hud_renderer._draw_model_source.assert_called_once_with(rect)
