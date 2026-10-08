from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import pyray as rl
import pytest

from openpilot.cereal import log
from openpilot.selfdrive.ui.mici.onroad import long_indicator as indicator


@pytest.fixture
def display(monkeypatch):
  class Messages(dict):
    recv_frame = {'selfdriveState': 12}
    alive = {'longitudinalPlan': True}
  sm = Messages(selfdriveState=NS(enabled=True, personality=NS(raw=1), alertSize=log.SelfdriveState.AlertSize.none),
                longitudinalPlan=NS(hasLead=True, longitudinalPlanSource=log.LongitudinalPlan.LongitudinalPlanSource.e2e),
                onroadEvents=[])
  state = NS(sm=sm, started_frame=10, has_longitudinal_control=True)
  monkeypatch.setattr(indicator, 'ui_state', state)
  monkeypatch.setattr(indicator.rl, 'get_time', lambda: 1.)
  with patch.object(indicator.gui_app, 'texture', side_effect=lambda path, *args, **kwargs: path):
    widget = indicator.LongIndicator()
  widget._draw_centered = Mock()
  widget.set_should_draw(True)
  return widget, state


@pytest.mark.parametrize('missing', ['longitudinal', 'engagement', 'drive'])
def test_no_longitudinal_indicator_from_unavailable_or_previous_drive(display, missing):
  widget, state = display
  if missing == 'longitudinal':
    state.has_longitudinal_control = False
  elif missing == 'engagement':
    state.sm['selfdriveState'].enabled = False
  else:
    state.started_frame = 13
  widget._render(rl.Rectangle(0, 0, 476, 240))
  widget._draw_centered.assert_not_called()


def test_indicator_tracks_lead_policy_and_yields_to_alerts(display):
  widget, state = display
  rect = rl.Rectangle(0, 0, 476, 240)
  for _ in range(60):
    widget._render(rect)
  lead_draws = widget._draw_centered.call_args_list[-8:-6]
  assert lead_draws[1].args[0].endswith('car_green.png')
  assert lead_draws[1].args[3] > .95
  state.sm['selfdriveState'].alertSize = log.SelfdriveState.AlertSize.full
  for _ in range(60):
    widget._render(rect)
  assert all(call.args[3] < .001 for call in widget._draw_centered.call_args_list[-8:])


def test_stock_indicator_fits_bottom_right_and_moved_personality_slot(display, monkeypatch):
  widget, _ = display
  widget._draw_centered = indicator.LongIndicator._draw_centered.__get__(widget)
  monkeypatch.setattr(widget, 'render', widget._render)
  widget._txt_lead_car = (NS(width=35, height=27), NS(width=50, height=42))
  widget._txt_distance = [(NS(width=w, height=h), NS(width=gw, height=gh))
                          for w, h, gw, gh in ((32, 7, 60, 35), (40, 9, 68, 37), (48, 11, 76, 39))]
  draw = Mock()
  monkeypatch.setattr(rl, 'draw_texture_ex', draw)
  for rect in (rl.Rectangle(476, 160, 60, 80), rl.Rectangle(476, 160, 60, 66), rl.Rectangle(300, 20, 60, 80)):
    draw.reset_mock()
    widget.render_sidebar(rect)
    assert draw.call_count == 8
    for call in draw.call_args_list:
      texture, pos, _, scale, _ = call.args
      assert rect.x <= pos.x and pos.x + texture.width * scale <= rect.x + rect.width
      assert rect.y <= pos.y and pos.y + texture.height * scale <= rect.y + rect.height
    assert not widget._sidebar


def test_stock_sidebar_preserves_traffic_accent_then_restores_personality(display, monkeypatch):
  widget, _ = display
  monkeypatch.setattr(widget, 'render', widget._render)
  rect = rl.Rectangle(476, 160, 60, 80)
  widget.render_sidebar(rect, traffic_mode=True)
  first_bar = widget._draw_centered.call_args_list[-6]
  assert first_bar.args[4] == (200, 32, 48)
  for _ in range(60):
    widget.render_sidebar(rect)
  bars = widget._draw_centered.call_args_list[-6::2]
  assert bars[1].args[3] > bars[2].args[3]
  assert all(call.args[4] == (255, 255, 255) for call in bars)


@pytest.mark.parametrize('missing', ['longitudinal', 'engagement', 'drive'])
def test_sidebar_keeps_selected_personality_without_claiming_active_control(display, monkeypatch, missing):
  widget, state = display
  if missing == 'longitudinal':
    state.has_longitudinal_control = False
  elif missing == 'engagement':
    state.sm['selfdriveState'].enabled = False
  else:
    state.started_frame = 13
  monkeypatch.setattr(widget, 'render', widget._render)
  for _ in range(60):
    widget.render_sidebar(rl.Rectangle(476, 160, 60, 80), personality=0)
  draws = widget._draw_centered.call_args_list[-8:]
  assert draws[0].args[3] == pytest.approx(.35, abs=.001)
  assert draws[1].args[3] < .001
  assert draws[2].args[3] > .89
  assert draws[4].args[3] == pytest.approx(.35, abs=.001)
  assert draws[6].args[3] == pytest.approx(.35, abs=.001)


def test_sidebar_disengagement_clears_active_lead_and_gas_override_immediately(display, monkeypatch):
  widget, state = display
  monkeypatch.setattr(widget, 'render', widget._render)
  monkeypatch.setattr(indicator.rl, 'get_time', lambda: 1.1)
  rect = rl.Rectangle(476, 160, 60, 80)
  for _ in range(60):
    widget.render_sidebar(rect, personality=1, longitudinal_active=True)
  assert widget._draw_centered.call_args_list[-7].args[3] > .95
  state.sm['onroadEvents'] = [NS(name=log.OnroadEvent.EventName.gasPressedOverride)]
  widget.render_sidebar(rect, personality=1, longitudinal_active=False)
  draws = widget._draw_centered.call_args_list[-8:]
  assert draws[0].args[3] == pytest.approx(.35, abs=.001)
  assert draws[1].args[3] == 0.0
  assert draws[2].args[3] > .89
  assert draws[4].args[3] > .89
