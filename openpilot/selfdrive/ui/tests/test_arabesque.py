"""Exercise real layout routing and Widget input with native service owners isolated."""

import ast
from dataclasses import replace
from enum import IntEnum
import gc
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock
import weakref

import pyray as rl
import pytest

from openpilot.selfdrive.ui.layouts.arabesque import ArabesqueLayout
from openpilot.selfdrive.ui.layouts.arabesque import desktop
from openpilot.selfdrive.ui.layouts.arabesque.theme import DEFAULT_THEME
from openpilot.selfdrive.ui.layouts.arabesque.tools import terminal
from openpilot.system.ui.lib.application import gui_app, FontWeight, MouseEvent, MousePos
from openpilot.system.ui.widgets import Widget

ROOT = Path(__file__).resolve().parents[2]


def layout_classes(path, names, namespace):
  # UI owners import device-native IPC; keep these tests usable on a desktop too.
  tree = ast.parse(path.read_text())
  tree.body = ast.parse('from __future__ import annotations').body + [
    node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in names
  ]
  exec(compile(ast.fix_missing_locations(tree), str(path), 'exec'), namespace)
  return NS(**namespace)


@pytest.fixture
def shell(monkeypatch):
  import openpilot.system.ui.widgets as widgets
  monkeypatch.setattr(widgets, 'device', NS(awake=True))
  monkeypatch.setattr(gui_app, '_mouse_events', [])
  monkeypatch.setattr(gui_app, '_show_touches', False)
  monkeypatch.setattr(desktop, 'gui_label', Mock())
  monkeypatch.setattr(terminal, 'gui_label', Mock())
  monkeypatch.setattr(terminal.Terminal, 'show_event', lambda self: None)
  for name in ('draw_rectangle_rec', 'draw_rectangle_rounded', 'draw_rectangle_rounded_lines_ex', 'draw_line_ex', 'draw_ring',
               'draw_circle_v', 'draw_triangle', 'draw_ellipse', 'begin_scissor_mode', 'end_scissor_mode'):
    monkeypatch.setattr(rl, name, lambda *a: None)
  return ArabesqueLayout(Mock())


def event(x, y, *, pressed=False, released=False, slot=0):
  return MouseEvent(MousePos(x, y), slot, pressed, released, pressed, 1.0)


def frame(view, *events):
  gui_app._mouse_events = list(events)
  view.render()


def tap(view, rect):
  x, y = rect.x + rect.width / 2, rect.y + rect.height / 2
  frame(view, event(x, y, pressed=True))
  frame(view, event(x, y, released=True))


def test_menu_dismissal_tool_title_and_desktop_return(shell):
  shell.set_rect(rl.Rectangle(0, 0, 2160, 1080))
  tap(shell, shell._menu_button)
  assert shell._menu_open
  tap(shell, shell._dock)
  assert not shell._menu_open
  assert shell._active_tool is None
  tap(shell, shell._dock)
  assert isinstance(shell._active_tool, terminal.Terminal)
  assert not gui_app.mouse_events
  frame(shell)
  assert desktop.gui_label.call_args_list[-1].args[1] == '< Desktop'
  assert desktop.gui_label.call_args_list[-2].args[1] == 'Terminal'
  assert any(call.args[1] == 'Opening local shell…' for call in terminal.gui_label.call_args_list)
  tap(shell, shell._back_button)
  assert shell._active_tool is None
  frame(shell)
  assert desktop.gui_label.call_args_list[-2].args[1] == 'Arabesque'
  shell._on_exit.assert_not_called()
  tap(shell, shell._menu_button)
  tap(shell, shell._exit_button)
  shell._on_exit.assert_called_once()


def test_drag_stray_release_second_finger_and_hidden_press_do_not_activate(shell):
  shell.set_rect(rl.Rectangle(0, 0, 2160, 1080))
  tap(shell, shell._menu_button)
  frame(shell, event(900, 400, pressed=True), event(100, 170, released=True))
  assert not shell._menu_open
  frame(shell, event(60, 50, pressed=True, slot=1), event(60, 50, released=True, slot=1))
  assert not shell._menu_open
  frame(shell, event(60, 50, released=True))
  assert not shell._menu_open
  tap(shell, shell._menu_button)
  frame(shell, event(100, 170, pressed=True))
  shell.hide_event()
  frame(shell, event(100, 170, released=True))
  shell._on_exit.assert_not_called()


@pytest.mark.parametrize('bounds', [(0, 0, 2160, 1080), (0, 0, 1920, 1080), (45, 30, 1280, 720), (0, 0, 2560, 1080)])
def test_layout_anchors_and_touch_targets(shell, bounds):
  shell.set_rect(rl.Rectangle(*bounds))
  rect, dock = shell.rect, shell._dock
  assert dock.x + dock.width / 2 == pytest.approx(rect.x + rect.width / 2)
  assert dock.y + dock.height < rect.y + rect.height
  assert dock.width >= 44 and dock.height >= 44
  assert shell._dock_icon.x == pytest.approx(dock.x + dock.width / 2)
  frame(shell)
  caption = desktop.gui_label.call_args.args[0]
  assert caption.x + caption.width / 2 == pytest.approx(shell._dock_icon.x)
  assert caption.y >= shell._dock_icon.y + 64 * shell._scale
  assert caption.y + caption.height < shell._dock_shelf.y
  assert caption.width < dock.width
  back_left, front_left, front_right, back_right = shell._dock_top
  assert back_left.x > front_left.x and back_right.x < front_right.x
  assert back_left.y < shell._dock_icon.y + 64 * shell._scale < front_left.y
  assert front_left.y == pytest.approx(shell._dock_shelf.y)
  assert front_right.y == pytest.approx(shell._dock_shelf.y)
  assert shell._dock_shelf.y + shell._dock_shelf.height < dock.y + dock.height
  assert shell._bar.width == rect.width
  assert shell._exit_button.y > shell._bar.y + shell._bar.height
  assert min(shell._menu_button.width, shell._menu_button.height) >= 44
  assert min(shell._back_button.width, shell._back_button.height) >= 44
  assert shell._tool_rect.y == shell._bar.y + shell._bar.height
  assert shell._tool_rect.x == rect.x
  assert shell._tool_rect.width == rect.width
  assert shell._tool_rect.y + shell._tool_rect.height == pytest.approx(rect.y + rect.height)
  tap(shell, shell._menu_button)
  assert shell._menu_open
  tap(shell, shell._dock)
  tap(shell, shell._dock)
  frame(shell)
  assert shell._active_tool.rect == shell._tool_rect
  label = desktop.gui_label.call_args
  assert label.args[0] is shell._back_button
  assert label.args[1] == '< Desktop'
  assert label.kwargs['alignment'] == desktop.TextAlignment.CENTER


def test_tool_theme_override_does_not_change_desktop_or_defaults(shell, monkeypatch):
  draw = Mock()
  monkeypatch.setattr(rl, 'draw_rectangle_rec', draw)
  custom = replace(DEFAULT_THEME, background=rl.Color(25, 31, 37, 255), text=rl.Color(240, 230, 220, 255), font_weight=FontWeight.BOLD)
  assert terminal.Terminal()._theme is DEFAULT_THEME
  shell.set_rect(rl.Rectangle(0, 0, 2160, 1080))
  shell._open_tool('Terminal', terminal.Terminal(theme=custom))
  frame(shell)
  assert draw.call_args_list[1].args[1] is custom.background
  assert any(call.args[3] is custom.text and call.args[4] is FontWeight.BOLD for call in terminal.gui_label.call_args_list)
  assert desktop.gui_label.call_args_list[0].args[3] is DEFAULT_THEME.text
  assert DEFAULT_THEME.background.r == 12


@pytest.fixture
def probe():
  class Probe(Widget):
    def __init__(self):
      super().__init__()
      self.show_event = Mock()
      self.hide_event = Mock()
      self._handle_mouse_press = Mock()
      self._handle_mouse_release = Mock()
      self._update_state = Mock()
      self.render_calls = Mock()

    def _render(self, rect, /):
      self.render_calls(rect)
  return Probe()


def test_dock_is_hidden_for_tools_and_returns_on_desktop(shell, probe, monkeypatch):
  triangles = Mock()
  monkeypatch.setattr(rl, 'draw_triangle', triangles)
  shell.set_rect(rl.Rectangle(0, 0, 2160, 1080))
  frame(shell)
  assert any(call.args[0] is shell._dock_top[0] for call in triangles.call_args_list)

  shell._open_tool('Probe', probe)
  triangles.reset_mock()
  frame(shell)
  assert not any(call.args[0] is shell._dock_top[0] for call in triangles.call_args_list)
  assert probe.rect == shell._tool_rect

  # The bottom edge now belongs to the tool, including the former dock area.
  x, y = shell.rect.x + shell.rect.width / 2, shell.rect.y + shell.rect.height - 1
  frame(shell, event(x, y, pressed=True))
  frame(shell, event(x, y, released=True))
  probe._handle_mouse_press.assert_called_once()
  probe._handle_mouse_release.assert_called_once()

  tap(shell, shell._back_button)
  triangles.reset_mock()
  frame(shell)
  assert shell._active_tool is None
  assert any(call.args[0] is shell._dock_top[0] for call in triangles.call_args_list)


def test_tool_input_is_gated_for_menu_chrome_and_disabled_desktop(shell, probe):
  shell.set_rect(rl.Rectangle(0, 0, 2160, 1080))
  shell._open_tool('Probe', probe)
  tap(shell, shell._tool_rect)
  probe._handle_mouse_press.assert_called_once()
  probe._handle_mouse_release.assert_called_once()
  probe._handle_mouse_press.reset_mock()
  probe._handle_mouse_release.reset_mock()

  # A whole queued gesture after the menu tap must not reach content in the same frame.
  frame(shell, event(60, 50, pressed=True), event(60, 50, released=True),
        event(1000, 500, pressed=True), event(1000, 500, released=True))
  assert not probe.enabled
  probe._handle_mouse_press.assert_not_called()
  probe._handle_mouse_release.assert_not_called()
  tap(shell, shell._menu_button)
  assert shell._menu_open
  tap(shell, shell._tool_rect)
  assert not shell._menu_open
  probe._handle_mouse_press.assert_not_called()
  probe._handle_mouse_release.assert_not_called()
  shell.set_enabled(False)
  tap(shell, shell._tool_rect)
  assert not probe.enabled
  probe._handle_mouse_press.assert_not_called()
  shell.set_enabled(True)
  tap(shell, shell._tool_rect)
  probe._handle_mouse_press.assert_called_once()
  probe._handle_mouse_release.assert_called_once()


def test_tool_lifecycle_runs_once_and_closed_tool_is_not_rendered(shell, probe, monkeypatch):
  shell.set_rect(rl.Rectangle(0, 0, 2160, 1080))
  create = Mock(return_value=probe)
  monkeypatch.setattr(desktop, 'Terminal', create)
  frame(shell)
  create.assert_not_called()
  tap(shell, shell._dock)
  probe.show_event.assert_called_once()
  tap(shell, shell._dock)
  create.assert_called_once()
  probe._handle_mouse_press.assert_called_once()
  probe._handle_mouse_release.assert_called_once()
  probe._handle_mouse_press.reset_mock()
  probe._handle_mouse_release.reset_mock()
  x, y = shell._back_button.x + 40, shell._back_button.y + 40
  frame(shell, event(x, y, pressed=True))
  frame(shell, event(x, y, released=True), event(1000, 500, pressed=True), event(1000, 500, released=True))
  assert not gui_app.mouse_events
  probe._handle_mouse_press.assert_not_called()
  probe._handle_mouse_release.assert_not_called()
  probe.hide_event.assert_called_once()
  probe.render_calls.reset_mock()
  probe._update_state.reset_mock()
  shell.hide_event()
  for _ in range(3):
    frame(shell)
  probe.hide_event.assert_called_once()
  probe.render_calls.assert_not_called()
  probe._update_state.assert_not_called()


def test_closed_tool_instances_are_released(shell):
  shell.set_rect(rl.Rectangle(0, 0, 2160, 1080))
  instances = []
  for _ in range(100):
    tap(shell, shell._dock)
    instances.append(weakref.ref(shell._active_tool))
    tap(shell, shell._back_button)
  gc.collect()
  assert all(instance() is None for instance in instances)


@pytest.fixture
def main(shell, monkeypatch):
  ui = NS(started=False, is_body=False, add_on_body_changed_callbacks=Mock())
  ui.is_offroad = lambda: not ui.started
  sidebar = Mock(is_visible=False)
  sidebar.set_visible.side_effect = lambda visible: setattr(sidebar, 'is_visible', visible)
  settings = Mock()
  namespace = {'rl': rl, 'IntEnum': IntEnum, 'Widget': Widget, 'gui_app': gui_app, 'ui_state': ui,
               'ArabesqueLayout': ArabesqueLayout, 'Sidebar': lambda: sidebar,
               'SIDEBAR_WIDTH': 300, 'HomeLayout': Mock, 'BodyLayout': Mock, 'SettingsLayout': Mock(return_value=settings),
               'AugmentedRoadView': Mock, 'messaging': NS(PubMaster=Mock()),
               'device': NS(add_interactive_timeout_callback=Mock()), 'OnboardingWindow': lambda: NS(completed=True),
               'PanelType': NS(TOGGLES=2, FIREHOSE=4)}
  native = layout_classes(ROOT / 'ui/layouts/main.py', {'MainState', 'MainLayout'}, namespace)
  monkeypatch.setattr(gui_app, 'push_widget', lambda widget: None)
  layout = native.MainLayout()
  layout.set_rect(rl.Rectangle(0, 0, 2160, 1080))
  layout._set_current_layout(native.MainState.SETTINGS)
  return NS(layout=layout, state=native.MainState, ui=ui, settings=settings, native=native)


def test_entry_wiring_and_offroad_gate(main):
  m = main
  callbacks = m.native.SettingsLayout.call_args.kwargs
  assert callbacks['on_open_arabesque'] == m.layout._open_arabesque
  m.ui.started = True
  callbacks['on_open_arabesque']()
  assert m.layout._current_mode == m.state.SETTINGS
  m.ui.started = False
  callbacks['on_open_arabesque']()
  assert m.layout._current_mode == m.state.ARABESQUE
  frame(m.layout)
  m.settings.render.assert_not_called()


def test_handoff_discards_queued_touches_and_restores_settings(main, probe):
  m = main
  gui_app._mouse_events = [event(60, 50, pressed=True), event(60, 50, released=True)]
  m.layout._open_arabesque()
  assert not gui_app.mouse_events
  view = m.layout._layouts[m.state.ARABESQUE]
  frame(m.layout)
  view._open_tool('Probe', probe)
  tap(m.layout, view._menu_button)
  frame(m.layout, event(100, 170, pressed=True))
  frame(m.layout, event(100, 170, released=True), event(1000, 500, pressed=True), event(1000, 500, released=True))
  assert m.layout._current_mode == m.state.SETTINGS
  assert not gui_app.mouse_events
  m.settings.render.assert_not_called()
  assert not view._menu_open
  assert view._active_tool is None
  probe.hide_event.assert_called_once()
  frame(m.layout)
  m.settings.render.assert_called_once()


def test_onroad_transition_draws_normal_alert_owner_immediately(main, probe):
  m = main
  m.layout._open_arabesque()
  view = m.layout._layouts[m.state.ARABESQUE]
  frame(m.layout)
  view._open_tool('Probe', probe)
  tap(m.layout, view._menu_button)
  m.ui.started = True
  frame(m.layout, event(100, 170, pressed=True))
  assert m.layout._current_mode == m.state.ONROAD
  assert not view._menu_open
  assert view._active_tool is None
  probe.hide_event.assert_called_once()
  assert not gui_app.mouse_events
  m.layout._layouts[m.state.ONROAD].render.assert_called_once()
  m.ui.started = False
  frame(m.layout)
  assert m.layout._current_mode == m.state.HOME


def test_shutdown_closes_active_tool_once(main, probe):
  main.layout._open_arabesque()
  view = main.layout._layouts[main.state.ARABESQUE]
  frame(main.layout)
  view._open_tool('Probe', probe)
  main.layout.close()
  main.layout.close()
  assert view._active_tool is None
  probe.hide_event.assert_called_once()


def test_repeated_entry_exit_reuses_view_and_never_runs_it_closed(main):
  m = main
  view = m.layout._layouts[m.state.ARABESQUE]
  for _ in range(100):
    m.layout._open_arabesque()
    frame(m.layout)
    tap(m.layout, view._menu_button)
    tap(m.layout, view._exit_button)
    assert m.layout._current_mode == m.state.SETTINGS
    assert m.layout._layouts[m.state.ARABESQUE] is view
  view._render = Mock()
  frame(m.layout)
  view._render.assert_not_called()


def test_star_large_routes_shell_and_uses_confirmed_offroad(main, probe):
  namespace = vars(main.native).copy()
  namespace['Destination'] = NS(NETWORK='network')
  namespace['ShellMode'] = NS(HOME='home', SETTINGS='settings', ONROAD='onroad')
  star = layout_classes(ROOT.parent / 'starpilot/ui/runtime_app.py', {'StarMainLayout'}, namespace)
  main.layout.__class__ = star.StarMainLayout
  layout = main.layout
  layout.star, layout.page = Mock(), Mock()
  layout.star.selected = 'developer'
  layout._large_destination = None
  layout._network_bridge = Mock()
  layout.star.adapter.confirmed_offroad.return_value = False
  layout._open_arabesque()
  assert layout._current_mode == main.state.SETTINGS
  layout.star.adapter.confirmed_offroad.return_value = True
  layout._open_arabesque()
  frame(layout)
  view = layout._layouts[main.state.ARABESQUE]
  view._open_tool('Probe', probe)
  layout.page.render.assert_not_called()
  layout.star.adapter.confirmed_offroad.return_value = False
  frame(layout)
  assert layout._current_mode == main.state.HOME
  layout.page.render.assert_called_once()
  probe.hide_event.assert_called_once()
  assert view._active_tool is None
  layout.star.adapter.confirmed_offroad.return_value = True
  layout._set_current_layout(main.state.SETTINGS)
  layout._open_arabesque()
  view._open_tool('Probe', probe)
  layout._native_onroad = layout._layouts[main.state.ONROAD]
  layout.close()
  assert probe.hide_event.call_count == 2
  assert view._active_tool is None
  layout.star.close.assert_called_once()
  layout._native_onroad.close.assert_called_once()
