from unittest.mock import Mock, patch

import pyray as rl
import pytest
from types import SimpleNamespace

from openpilot.selfdrive.ui.mici.onroad.augmented_road_view import AugmentedRoadView
from openpilot.selfdrive.ui.ui_state import ChestnutState, UIState


@pytest.mark.parametrize('raw, expected', [(True, True), (False, False), (b'1', True), (b'0', False),
                                          ('1', True), ('0', False), (None, None), (b'invalid', None)])
def test_native_chestnut_status_accepts_typed_params(raw, expected):
  params = Mock()
  params.get.return_value = raw
  params.get_bool.return_value = False
  state = Mock(spec=UIState, params=params, started=True, chestnut_compiled=True, usb_connected=False)
  with patch('openpilot.selfdrive.ui.ui_state.get_cache', return_value=None), \
       patch('openpilot.selfdrive.ui.ui_state.cable_connected', return_value=False):
    UIState.update_params(state)
  assert state.chestnut_active is expected


def test_custom_model_source_layer_uses_native_status_animation():
  view = Mock(spec=AugmentedRoadView, _hud_renderer=Mock())
  rect = rl.Rectangle(0, 0, 476, 240)
  AugmentedRoadView.render_model_source_layer(view, rect)
  view._hud_renderer._update_state.assert_called_once_with()
  view._hud_renderer._draw_model_source.assert_called_once_with(rect)


@pytest.mark.parametrize('compiled', [False, True])
@pytest.mark.parametrize('prior', [ChestnutState.UNCOMPILED, ChestnutState.FAILED, ChestnutState.LOADING])
def test_catalog_gpu_output_does_not_require_retired_bundled_artifact(compiled, prior):
  sm = Mock()
  sm.__getitem__ = Mock(side_effect=lambda service: SimpleNamespace(chestnutPresent=True) if service == 'deviceState' else SimpleNamespace(big=True))
  sm.recv_frame = {'modelV2': 12}
  sm.logMonoTime = {'modelV2': 1_000_000_000}
  sm.valid = {'modelV2': True}
  sm.alive = {'modelV2': True}
  state = Mock(spec=UIState, sm=sm, started=True, started_frame=10, chestnut_present=True, chestnut_compiled=compiled,
                          chestnut_loading=False, chestnut_active=True, chestnut_state=prior)
  with patch('openpilot.selfdrive.ui.ui_state.time.monotonic_ns', return_value=1_100_000_000):
    UIState._update_chestnut_state(state)
  assert state.chestnut_state == ChestnutState.ACTIVE


@pytest.mark.parametrize('big, valid, alive, age, active', [(False, True, True, 100_000_000, False),
                                                         (True, False, True, 100_000_000, True),
                                                         (True, True, False, 100_000_000, True),
                                                         (True, True, True, 300_000_000, True),
                                                         (True, True, True, 100_000_000, False)])
def test_catalog_gpu_fallback_or_stale_output_stays_failed(big, valid, alive, age, active):
  sm = Mock()
  sm.__getitem__ = Mock(side_effect=lambda service: SimpleNamespace(chestnutPresent=True) if service == 'deviceState' else SimpleNamespace(big=big))
  sm.recv_frame = {'modelV2': 12}
  sm.logMonoTime = {'modelV2': 1_000_000_000}
  sm.valid = {'modelV2': valid}
  sm.alive = {'modelV2': alive}
  state = Mock(spec=UIState, sm=sm, started=True, started_frame=10, chestnut_present=True, chestnut_compiled=False,
                          chestnut_loading=False, chestnut_active=active, chestnut_state=ChestnutState.ACTIVE)
  with patch('openpilot.selfdrive.ui.ui_state.time.monotonic_ns', return_value=1_000_000_000 + age):
    UIState._update_chestnut_state(state)
  assert state.chestnut_state == ChestnutState.FAILED
