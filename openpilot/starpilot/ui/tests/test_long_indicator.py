from types import SimpleNamespace as NS
from typing import cast
from unittest.mock import Mock, patch

import pyray as rl
import pytest

from openpilot.cereal import log
from openpilot.selfdrive.ui.mici.onroad import long_indicator as indicator


@pytest.fixture
def display(monkeypatch):
  class Messages(dict):
    recv_frame = {'selfdriveState': 12}
    alive = {'longitudinalPlan': True, 'carControl': True}
  sm = Messages(selfdriveState=NS(enabled=True, active=True, personality=NS(raw=1), alertSize=log.SelfdriveState.AlertSize.none),
                longitudinalPlan=NS(hasLead=True, longitudinalPlanSource=log.LongitudinalPlan.LongitudinalPlanSource.e2e),
                carControl=NS(longActive=True), onroadEvents=[])
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


@pytest.mark.parametrize('source', tuple(log.LongitudinalPlan.LongitudinalPlanSource.schema.enumerants))
def test_indicator_tracks_lead_policy_and_yields_to_alerts(display, source):
  widget, state = display
  state.sm['longitudinalPlan'].longitudinalPlanSource = source
  rect = rl.Rectangle(0, 0, 476, 240)
  for _ in range(60):
    widget._render(rect)
  lead_draws = widget._draw_centered.call_args_list[-8:-6]
  assert lead_draws[1].args[0].endswith('car_green.png')
  assert lead_draws[1].args[3] > .95
  for has_lead, alive in ((False, True), (True, False)):
    state.sm['longitudinalPlan'].hasLead = has_lead
    state.sm.alive['longitudinalPlan'] = alive
    for _ in range(60):
      widget._render(rect)
    lead_draws = widget._draw_centered.call_args_list[-8:-6]
    assert lead_draws[0].args[3] == pytest.approx(.35, abs=.001)
    assert lead_draws[1].args[3] < .001
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
  assert draws[0].args[3] == pytest.approx(1., abs=.001)
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
  assert draws[0].args[3] == pytest.approx(1., abs=.001)
  assert draws[1].args[3] == 0.0
  assert draws[2].args[3] > .89
  assert draws[4].args[3] > .89


@pytest.mark.parametrize('ordered', [False, True])
@pytest.mark.parametrize('moved', [False, True])
def test_lane_change_notice_keeps_compact_rail_without_covering_urgent_alerts(display, monkeypatch, ordered, moved):
  from dataclasses import replace

  from openpilot.cereal import messaging
  from openpilot.starpilot.ui import onroad
  from openpilot.starpilot.ui.onroad_compact_widgets import MiciSidebarWidgets
  from openpilot.starpilot.ui.onroad_customization import default_document, DEFAULT_WIDGET_ORDER
  from openpilot.starpilot.ui.onroad_state import OnroadState, SpeedLimitObservation
  from openpilot.starpilot.ui.presentation import BitmapFonts, Profile
  from openpilot.starpilot.ui.runtime_app import StarShellSession
  from openpilot.starpilot.ui.runtime_snapshot import current_alert
  from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW, ui_fake

  widget, _ = display
  monkeypatch.setattr(widget, 'render', widget._render)
  session = StarShellSession.__new__(StarShellSession)
  session.camera_owner = NS(_long_indicator=widget)
  fonts = cast(BitmapFonts, NS(profile=Profile.COMPACT, draw=Mock(), measure=Mock(return_value=NS(width=100, height=30))))
  rail = MiciSidebarWidgets(fonts)
  rail.personality_renderer = session._render_personality
  rail._conditional = Mock()  # Unrelated CEM icon; confidence and native bars remain real.
  view = onroad.OnroadView.__new__(onroad.OnroadView)
  view.fonts, view.compact_sidebar = fonts, rail
  for name in ('navigation', 'compact_hud', 'torque_bar', 'alert'):
    setattr(view, name, Mock())
  for name in ('camera_layer', 'background_layer', 'projection_viewport', 'extra_overlays', '_fade'):
    setattr(view, name, None)
  document = default_document()
  if moved:
    document['layouts']['compact']['model_confidence'].update(x=200, y=20)
    document['layouts']['compact']['following_distance'].update(x=260, y=20)
  if ordered:
    document['widgetOrder'] = {'compact': list(DEFAULT_WIDGET_ORDER['compact'])}
  base = OnroadState(True, False, 15, 80, SpeedLimitObservation(), customization=document,
                    lateral_active=True, longitudinal_active=True, personality=1,
                    stock_confidence_source_fresh=True, stock_confidence_source_stamp_ns=NOW,
                    stock_confidence_drive_frame=1, model_confidence=.9)
  ui = ui_fake()
  cases = [('preLaneChangeLeft/warning', 'mid', 'normal', 'none', True),
           ('preLaneChangeRight/warning', 'mid', 'normal', 'none', True),
           ('preLaneChangeLeft/warning', 'small', 'normal', 'none', True),
           ('laneChange/warning', 'small', 'normal', 'none', True),
           ('laneChangeBlocked/warning', 'small', 'userPrompt', 'none', False),
           ('preLaneChangeLeft/warning', 'mid', 'critical', 'none', False),
           ('preLaneChangeLeft/warning', 'full', 'normal', 'none', False),
           ('preLaneChangeLeft/warning', 'mid', 'normal', 'steerRequired', False)]
  with patch.object(onroad.clip, 'begin_scissor_mode'), patch.object(onroad.clip, 'end_scissor_mode'), \
       patch.object(rl, 'draw_rectangle'), patch.object(rl, 'draw_rectangle_rounded'), \
       patch.object(rl, 'draw_rectangle_rounded_lines_ex'), patch.object(rl, 'draw_texture_ex'), \
       patch.object(rl, 'draw_rectangle_gradient_v') as confidence, patch.object(rl, 'draw_ring'), \
       patch.object(onroad, 'render_compact_half_borders'), patch.object(view, '_prepare_compact_fade'), \
       patch.object(view, '_slc_actions'):
    for alert_type, size, status, visual, routine in cases:
      event = messaging.new_message('selfdriveState', valid=True, logMonoTime=NOW)
      event.selfdriveState.enabled = True
      event.selfdriveState.alertType, event.selfdriveState.alertSize = alert_type, size
      event.selfdriveState.alertStatus, event.selfdriveState.alertHudVisual = status, visual
      wire = messaging.log_from_bytes(event.to_bytes())
      ui.sm.put('selfdriveState', wire.selfdriveState)
      alert = current_alert(ui.sm, NOW, after_frame=ui.started_frame)
      state = replace(base, alert=alert)
      confidence.reset_mock()
      widget._draw_centered.reset_mock()
      for _ in range(60):
        view.render(state)
      assert view.alert.render.call_args.args[1] == alert
      if routine:
        assert widget._draw_centered.call_args_list[-7].args[3] > .99
        color = confidence.call_args.args[-2]
        assert (color.r, color.g, color.b) == (0, 255, 204)
      elif moved:
        widget._draw_centered.assert_not_called()
        confidence.assert_not_called()
      else:
        assert all(call.args[3] < .001 for call in widget._draw_centered.call_args_list[-8:])
        color = confidence.call_args.args[-2]
        assert (color.r, color.g, color.b) == (50, 50, 50)
