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


@pytest.mark.parametrize('indicator', [False, None])
def test_custom_model_source_layer_uses_native_status_animation(indicator):
  view = Mock(spec=AugmentedRoadView, _hud_renderer=Mock(), _long_indicator=Mock())
  rect = rl.Rectangle(0, 0, 476, 240)
  AugmentedRoadView.render_model_source_layer(view, rect, show_long_indicator=indicator)
  view._hud_renderer._update_state.assert_called_once_with()
  view._hud_renderer._draw_model_source.assert_called_once_with(rect)
  if indicator is None:
    view._long_indicator.set_should_draw.assert_not_called()
    view._long_indicator.render.assert_not_called()
  else:
    view._long_indicator.set_should_draw.assert_called_once_with(False)
    view._long_indicator.render.assert_called_once_with(rect)


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
                                                         (True, True, True, 300_000_000, True)])
def test_catalog_gpu_fallback_or_stale_output_stays_failed(big, valid, alive, age, active):
  sm = Mock()
  sm.__getitem__ = Mock(side_effect=lambda service: SimpleNamespace(chestnutPresent=True) if service == 'deviceState' else SimpleNamespace(big=big))
  sm.recv_frame = {'modelV2': 12}
  sm.logMonoTime = {'modelV2': 1_000_000_000}
  sm.valid = {'modelV2': valid}
  sm.alive = {'modelV2': alive}
  state = Mock(spec=UIState, sm=sm, started=True, started_frame=10, chestnut_present=True, chestnut_compiled=False,
                          chestnut_loading=False, chestnut_active=active, chestnut_output_seen=True, chestnut_state=ChestnutState.ACTIVE)
  with patch('openpilot.selfdrive.ui.ui_state.time.monotonic_ns', return_value=1_000_000_000 + age):
    UIState._update_chestnut_state(state)
  assert state.chestnut_state == ChestnutState.FAILED


@pytest.mark.parametrize('detected,installed,checking,expected', [
  (True, True, False, ChestnutState.READY),
  (True, False, True, ChestnutState.LOADING),
  (True, False, False, ChestnutState.UNCOMPILED),
  (False, True, False, ChestnutState.DISCONNECTED),
])
def test_offroad_status_uses_selected_download(detected, installed, checking, expected):
  sm = Mock()
  sm.__getitem__ = Mock(return_value=SimpleNamespace(chestnutPresent=detected))
  state = Mock(spec=UIState, sm=sm, started=False, chestnut_compiled=installed, chestnut_checking=checking)
  UIState._update_chestnut_state(state)
  assert state.chestnut_state == expected


def test_offroad_selection_rechecks_without_a_ui_restart():
  params = Mock()
  params.get.return_value = None
  params.get_bool.return_value = False
  artifacts = Mock()
  artifacts.selected_gpu_status.side_effect = [(False, True), (True, False), (False, False)]
  state = Mock(spec=UIState, params=params, started=False, _gpu_artifacts=artifacts, _gpu_artifacts_at=None,
               usb_connected=False)
  with patch('openpilot.selfdrive.ui.ui_state.get_cache', return_value=None), \
       patch('openpilot.selfdrive.ui.ui_state.cable_connected', return_value=False), \
       patch('openpilot.selfdrive.ui.ui_state.time.monotonic', side_effect=[1., 1.2, 2., 3., 4.]):
    UIState.update_params(state)
    assert state.chestnut_checking and not state.chestnut_compiled
    UIState.update_params(state)
    artifacts.selected_gpu_status.assert_called_once()
    UIState.update_params(state)
    assert state.chestnut_compiled and not state.chestnut_checking
    UIState.update_params(state)
    assert not state.chestnut_compiled and not state.chestnut_checking
    state.started = True
    UIState.update_params(state)
    assert artifacts.selected_gpu_status.call_count == 3


@pytest.mark.parametrize('state,small_engaged,texture', [
  (ChestnutState.LOADING, False, 'white'),
  (ChestnutState.ACTIVE, False, 'green'),
  (ChestnutState.FAILED, False, 'orange'),
  (ChestnutState.FAILED, True, 'crossed'),
  (ChestnutState.DISCONNECTED, True, 'crossed'),
  (ChestnutState.ACTIVE, True, 'green'),
])
def test_native_gpu_icons_render_for_loading_active_and_small_engagement(state, small_engaged, texture):
  from openpilot.selfdrive.ui.mici.onroad.hud_renderer import HudRenderer

  icons = {key: SimpleNamespace(name=key, width=60, height=44) for key in ('white', 'green', 'orange', 'crossed')}
  renderer = Mock(spec=HudRenderer, _small_model_engaged=small_engaged, _chestnut_icon=None,
                  _txt_chestnut=icons['white'], _txt_chestnut_green=icons['green'],
                  _txt_chestnut_orange=icons['orange'], _txt_chestnut_crossed=icons['crossed'],
                  _txt_wheel=SimpleNamespace(height=50))
  renderer._chestnut_alpha_filter = Mock()
  renderer._chestnut_alpha_filter.update.return_value = 1.
  ui = SimpleNamespace(sm=SimpleNamespace(recv_frame={'selfdriveState': 20}), started_frame=10, chestnut_state=state)
  with patch('openpilot.selfdrive.ui.mici.onroad.hud_renderer.ui_state', ui), \
       patch('openpilot.selfdrive.ui.mici.onroad.hud_renderer.rl.get_time', return_value=10.), \
       patch('openpilot.selfdrive.ui.mici.onroad.hud_renderer.rl.draw_texture_ex') as draw:
    HudRenderer._draw_model_source(renderer, rl.Rectangle(0, 0, 476, 240))
    assert draw.call_args.args[0] is icons[texture]


def test_startup_invalid_big_frame_remains_loading_until_first_valid_output():
  sm = Mock()
  sm.__getitem__ = Mock(side_effect=lambda service: SimpleNamespace(chestnutPresent=True) if service == 'deviceState' else SimpleNamespace(big=True))
  sm.recv_frame = {'modelV2': 12}
  sm.logMonoTime = {'modelV2': 1_000_000_000}
  sm.valid = {'modelV2': False}
  sm.alive = {'modelV2': True}
  state = Mock(spec=UIState, sm=sm, started=True, started_frame=10, chestnut_present=True, chestnut_compiled=True,
               chestnut_loading=False, chestnut_active=True, chestnut_output_seen=False, chestnut_state=ChestnutState.LOADING)
  with patch('openpilot.selfdrive.ui.ui_state.time.monotonic_ns', return_value=1_100_000_000):
    UIState._update_chestnut_state(state)
    assert state.chestnut_state == ChestnutState.LOADING
    assert not state.chestnut_output_seen
    sm.valid['modelV2'] = True
    state.chestnut_active = False
    UIState._update_chestnut_state(state)
    assert state.chestnut_state == ChestnutState.ACTIVE
    assert state.chestnut_output_seen
    sm.valid['modelV2'] = False
    UIState._update_chestnut_state(state)
    assert state.chestnut_state == ChestnutState.FAILED


def test_initial_valid_small_output_is_failed_despite_loaded_big_marker():
  sm = Mock()
  sm.__getitem__ = Mock(side_effect=lambda service: SimpleNamespace(chestnutPresent=True) if service == 'deviceState' else SimpleNamespace(big=False))
  sm.recv_frame = {'modelV2': 12}
  sm.logMonoTime = {'modelV2': 1_000_000_000}
  sm.valid = {'modelV2': True}
  sm.alive = {'modelV2': True}
  state = Mock(spec=UIState, sm=sm, started=True, started_frame=10, chestnut_present=True, chestnut_compiled=True,
               chestnut_loading=True, chestnut_active=True, chestnut_output_seen=False, chestnut_state=ChestnutState.LOADING)
  with patch('openpilot.selfdrive.ui.ui_state.time.monotonic_ns', return_value=1_100_000_000):
    UIState._update_chestnut_state(state)
  assert state.chestnut_state == ChestnutState.FAILED
