"""Paginated native controls retain callbacks, fresh state, and network authority."""

import ast
from collections.abc import Callable
from enum import Enum
from pathlib import Path
import sys
from types import SimpleNamespace as NS, ModuleType
import unittest
from unittest.mock import Mock, patch

import pyray as rl

from openpilot.starpilot.ui.feature_settings_state import FEATURE_ROW_TOP, FEATURE_ROW_HEIGHT, FeatureInput, FeatureUiAction
from openpilot.starpilot.ui.starpilot_settings_adapter_large import StarPilotSettingsAdapterLarge
from openpilot.starpilot.ui.network_panel import NetworkPanelBridge
from openpilot.starpilot.ui.tests.test_feature_settings_visuals import fake_fonts
from openpilot.system.ui.lib.application import gui_app, MouseEvent, MousePos
from openpilot.system.ui.lib.wifi_manager import Network, SecurityType
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.list_view import ButtonAction, DualButtonAction, ItemAction, MultipleButtonAction, ToggleAction
from openpilot.system.ui.widgets.button import Button, ButtonStyle
from openpilot.system.ui.widgets.network import NetworkUI, PanelType, UIState, WifiManagerUI


def item(title, action=None):
  return NS(title=title, action_item=action, enabled=True, is_visible=True, callback=Mock(), description="Details",
            description_opened_callback=None)


def button_action():
  action = Mock(spec=ButtonAction)
  action.text, action.value, action.enabled = "OPEN", "Status", True
  return action


class NativeSettingsPageTests(unittest.TestCase):
  def panel(self, items):
    owner = NS(_scroller=NS(_items=items), show_event=Mock(), hide_event=Mock(), _update_state=Mock())
    pane = StarPilotSettingsAdapterLarge(owner, fake_fonts(), "Device", Mock())
    pane.show_event()
    return pane

  def click(self, pane, x=1930, index=0):
    pos = MousePos(x + pane.origin[0], FEATURE_ROW_TOP + (index + .5) * FEATURE_ROW_HEIGHT + pane.origin[1])
    pane._handle_mouse_press(pos)
    pane._handle_mouse_release(pos)

  def test_every_row_reachable_and_page_clamps_when_visibility_changes(self):
    items = [item(str(index), button_action()) for index in range(12)]
    pane = self.panel(items)
    reached = []
    for page in range(3):
      state = pane.snapshot()
      reached.extend(row.label for row in state.rows[state.scroll:state.scroll + 5])
      pane._emit(FeatureUiAction("scroll"))
    self.assertEqual(reached, [str(index) for index in range(12)])
    self.assertEqual(pane.scroll, 10)
    for row in items[5:]:
      row.is_visible = False
    self.assertEqual(pane.snapshot().scroll, 0)
    pane.show_event()
    self.assertEqual(pane.scroll, 0)
    self.assertFalse(hasattr(pane, "scroll_panel"))

  def test_buttons_cancel_on_disabled_hidden_changed_page_and_drag(self):
    row = item("Update", button_action())
    pane = self.panel([row, *[item(str(index), button_action()) for index in range(6)]])
    pos = MousePos(1930, FEATURE_ROW_TOP + FEATURE_ROW_HEIGHT / 2)
    for change in (lambda: setattr(row.action_item, "enabled", False), lambda: setattr(row, "is_visible", False),
                   lambda: setattr(pane, "scroll", 5)):
      pane._handle_mouse_press(pos)
      change()
      pane._handle_mouse_release(pos)
      row.callback.assert_not_called()
      row.action_item.enabled, row.is_visible, pane.scroll = True, True, 0
    pane._handle_mouse_press(pos)
    pane._handle_mouse_event(NS(pos=MousePos(1930, FEATURE_ROW_TOP + FEATURE_ROW_HEIGHT / 2 + 40)))
    pane._handle_mouse_release(pos)
    row.callback.assert_not_called()
    self.click(pane)
    row.callback.assert_called_once_with()

  def test_footer_and_actions_use_the_rendered_origin_in_both_sidebar_modes(self):
    rows = [item(str(index), button_action()) for index in range(7)]
    pane = self.panel(rows)
    for width, left in ((1560, 550), (2060, 50)):
      with patch.object(Widget, "render"):
        pane.render(rl.Rectangle(left + 40, 55, width, 1030))
      pos = MousePos(1720 + pane.origin[0], 1015 + pane.origin[1])
      pane._handle_mouse_press(pos)
      pane._handle_mouse_release(pos)
      self.assertEqual(pane.scroll, 5)
      self.click(pane)
      pos = MousePos(900 + pane.origin[0], 1015 + pane.origin[1])
      pane._handle_mouse_press(pos)
      pane._handle_mouse_release(pos)
      self.assertEqual(pane.scroll, 0)
    self.assertEqual(rows[5].callback.call_count, 2)

  def test_widget_dispatch_keeps_pagination_and_buttons_clickable_without_scrolling(self):
    rows = [item(str(index), button_action()) for index in range(7)]
    pane = self.panel(rows)
    bounds = rl.Rectangle(550, 25, 1560, 1030)
    with (patch.object(pane, '_render'), patch.object(gui_app, '_show_touches', False),
          patch('openpilot.system.ui.widgets.device', NS(awake=True)),
          patch.object(rl, 'get_mouse_wheel_move', return_value=-10) as wheel):
      for x, y in ((1720, 1015), (1930, FEATURE_ROW_TOP + FEATURE_ROW_HEIGHT / 2), (900, 1015)):
        for pressed, released in ((True, False), (False, True)):
          event = MouseEvent(MousePos(x, y), 0, pressed, released, pressed, 1)
          with patch.object(gui_app, '_mouse_events', [event]):
            pane.render(bounds)
      rows[5].callback.assert_called_once_with()
      self.assertEqual(pane.scroll, 0)
      wheel.assert_not_called()

  def test_toggle_calls_its_native_callback_once_and_respects_displayed_value(self):
    action = ToggleAction(callback=Mock())
    row = item("Automatic updates", action)
    row.callback = None
    pane = self.panel([row])
    pane._handle_mouse_press(MousePos(2000, FEATURE_ROW_TOP + FEATURE_ROW_HEIGHT / 2))
    action.set_state(True)
    pane._handle_mouse_release(MousePos(2000, FEATURE_ROW_TOP + FEATURE_ROW_HEIGHT / 2))
    action.toggle._callback.assert_not_called()
    self.click(pane, 2000)
    action.toggle._callback.assert_called_once_with(False)

  def test_power_buttons_remain_distinct_and_hidden_shutdown_is_not_exposed(self):
    with patch('openpilot.system.ui.lib.application.gui_app.font', return_value=rl.Font()):
      action = DualButtonAction("Reboot", "Power Off", left_callback=Mock(), right_callback=Mock())
    pane = self.panel([item("", action)])
    self.click(pane, 1500)
    self.click(pane)
    action.left_button._click_callback.assert_called_once_with()
    action.right_button._click_callback.assert_called_once_with()
    action.right_button.set_visible(False)
    self.assertEqual(pane.snapshot().rows[0].actions, (("Reboot", True),))

  def test_choices_reuse_feature_controls_and_cancel_when_stale_disabled_or_inactive(self):
    with patch('openpilot.system.ui.lib.application.gui_app.font', return_value=rl.Font()):
      action = MultipleButtonAction(["Default", "Metered", "Unmetered"], 255, callback=Mock())
    pane = self.panel([item("Metered", action)])
    self.assertEqual(pane.snapshot().rows[0].choices, tuple(action.buttons))
    pos = MousePos(2000, FEATURE_ROW_TOP + FEATURE_ROW_HEIGHT / 2)
    pane._handle_mouse_press(pos)
    action.selected_button = 1
    pane._handle_mouse_release(pos)
    action.callback.assert_not_called()
    self.click(pane, 2000)
    action.callback.assert_called_once_with(2)
    self.click(pane, 1800)
    self.assertEqual(action.callback.call_args.args, (1,))
    action.callback.reset_mock()
    action.set_enabled(False)
    self.click(pane, 2000)
    action.set_enabled(True)
    pane.hide_event()
    self.click(pane, 2000)
    action.callback.assert_not_called()

  def test_developer_ssh_preserves_native_fetcher_loading_and_add_remove_actions(self):
    # Execute the actual SSH control with its Params/network dependencies isolated.
    source = Path('openpilot/selfdrive/ui/widgets/ssh_key.py')
    nodes = [node for node in ast.parse(source.read_text()).body
             if isinstance(node, ast.ClassDef) and node.name in ('SshKeyActionState', 'SshKeyAction')]
    params = NS(get=lambda _: '', remove=Mock())
    module = ModuleType('openpilot.selfdrive.ui.widgets.ssh_key')
    module.__dict__.update(Enum=Enum, ItemAction=ItemAction, Params=lambda: params, SshKeyFetcher=lambda _: Mock(),
                           Keyboard=lambda **_: Mock(), gui_app=gui_app, Button=Button, ButtonStyle=ButtonStyle,
                           FontWeight=NS(NORMAL=0), Callable=Callable, DialogResult=DialogResult, rl=rl, MousePos=MousePos, tr=lambda value: value,
                           tr_noop=lambda value: value, BUTTON_BORDER_RADIUS=50, BUTTON_FONT_SIZE=35)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), module.__dict__)
    with patch.dict(sys.modules, {module.__name__: module}), patch.object(gui_app, 'font', return_value=rl.Font()):
      action = module.SshKeyAction()
      pane = self.panel([item('SSH Keys', action)])
      pane.title = 'Developer'
      self.assertEqual(pane.snapshot().rows[0].actions, (('ADD', True),))
      with patch.object(gui_app, 'push_widget') as pushed:
        self.click(pane)
        pushed.assert_called_once_with(action._keyboard)
      action._state = module.SshKeyActionState.LOADING
      self.assertEqual(pane.snapshot().rows[0].actions, (('LOADING', False),))
      self.click(pane)
      action._fetcher.clear.assert_not_called()
      pane._update_state()
      action._fetcher.update.assert_called_once()
      action._state, action._username = module.SshKeyActionState.REMOVE, 'my-user'
      self.assertEqual(pane.snapshot().rows[0].value, 'my-user')
      self.click(pane)
      action._fetcher.clear.assert_called_once()

  def test_toggles_keep_native_fresh_state_request_guards(self):
    action = ToggleAction(callback=Mock())
    row = item('Enable openpilot', action)
    with patch.object(gui_app, 'font', return_value=rl.Font()):
      personality = MultipleButtonAction(['Aggressive', 'Standard', 'Relaxed'], 255, selected_index=1, callback=Mock())
    pane = self.panel([row, item('Driving Personality', personality)])
    pane.title = 'Toggles'
    pane.panel._toggles = {'OpenpilotEnabledToggle': row}
    pane.panel.request_toggle, pane.panel.request_personality = Mock(return_value=False), Mock(return_value=False)
    self.click(pane, 2000)
    pane.panel.request_toggle.assert_called_once_with('OpenpilotEnabledToggle', True)
    action.toggle._callback.assert_not_called()
    self.assertFalse(action.get_state())
    self.click(pane, 2000, index=1)
    pane.panel.request_personality.assert_called_once_with(2)
    personality.callback.assert_not_called()
    self.assertEqual(personality.selected_button, 1)

  def test_toggles_saved_state_matches_display_after_changes_and_confirmations(self):
    # Run the real controller methods with only device services isolated.
    source = Path('openpilot/selfdrive/ui/layouts/settings/toggles.py')
    layout = next(node for node in ast.parse(source.read_text()).body if isinstance(node, ast.ClassDef) and node.name == 'TogglesLayout')
    methods = {'_update_toggles', '_update_state', '_toggle_callback', '_handle_experimental_mode_toggle',
               'request_toggle', 'request_personality', '_set_longitudinal_personality'}
    layout.bases = []
    layout.body = [node for node in layout.body if isinstance(node, ast.FunctionDef) and node.name in methods]
    ui = NS(CP=None, engaged=False, update_params=Mock(), sm=NS(updated={'selfdriveState': False}))
    app = NS(push_widget=Mock())
    namespace = dict(tr=lambda text: text, ui_state=ui, gui_app=app, DialogResult=DialogResult,
                     ConfirmDialog=lambda *args, **kwargs: NS(callback=kwargs['callback']))
    exec(compile(ast.Module(body=[layout], type_ignores=[]), str(source), 'exec'), namespace)
    owner = namespace['TogglesLayout']()
    saved = {'IsLdwEnabled': False, 'LongitudinalPersonality': 1}
    owner._params = NS(get_bool=lambda key: bool(saved.get(key, False)), get=lambda key, **_: saved.get(key),
                       put_bool=lambda key, value, **_: saved.__setitem__(key, value),
                       put=lambda key, value, **_: saved.__setitem__(key, value))
    toggle = item('Lane Departure Warnings', ToggleAction())
    experimental = item('Experimental Mode', ToggleAction())
    experimental.set_description = Mock()
    with patch.object(gui_app, 'font', return_value=rl.Font()):
      personality = item('Driving Personality', MultipleButtonAction(['Aggressive', 'Standard', 'Relaxed'], 255, selected_index=1))
    owner._toggles = {'IsLdwEnabled': toggle, 'ExperimentalMode': experimental}
    owner._toggle_defs = {key: ('', '', '', False) for key in owner._toggles}
    owner._locked_toggles = set()
    owner._slc_offsets = NS(_raw=lambda key: b'0')
    owner._update_experimental_mode_icon = Mock()
    owner._long_personality_setting = personality
    owner._scroller = NS(_items=[toggle, personality, experimental])
    pane = self.panel(owner._scroller._items)
    pane.panel, pane.title = owner, 'Toggles'
    for desired in (True, False):
      self.click(pane, 2000)
      pane._update_state()
      self.assertEqual(saved['IsLdwEnabled'], desired)
      self.assertEqual(pane.snapshot().rows[0].value, 'On' if desired else 'Off')
    for expected in (2, 0, 1):
      self.click(pane, 2000, index=1)
      pane._update_state()
      self.assertEqual(saved['LongitudinalPersonality'], expected)
      self.assertEqual(pane.snapshot().rows[1].value, personality.action_item.buttons[expected])
    owner._toggle_defs['IsLdwEnabled'] = ('', '', '', True)
    ui.engaged = True
    self.click(pane, 2000)
    self.assertFalse(saved['IsLdwEnabled'])
    self.assertEqual(pane.snapshot().rows[0].value, 'Off')
    for result in (DialogResult.CANCEL, DialogResult.CONFIRM):
      self.click(pane, 2000, index=2)
      self.assertFalse(saved.get('ExperimentalMode', False))
      app.push_widget.call_args.args[0].callback(result)
      pane._update_state()
      self.assertEqual(pane.snapshot().rows[2].value, 'On' if result == DialogResult.CONFIRM else 'Off')
    self.click(pane, 2000, index=2)
    self.assertFalse(saved['ExperimentalMode'])
    self.assertEqual(pane.snapshot().rows[2].value, 'Off')

  def network_panel(self):
    manager = NS(is_connection_saved=lambda ssid: ssid == "Saved", connected_ssid="Saved",
                 wifi_state=NS(ssid="Saved"), set_active=Mock(), process_callbacks=Mock(), activate_connection=Mock(),
                 connect_to_network=Mock(), forget_connection=Mock())
    wifi = WifiManagerUI.__new__(WifiManagerUI)
    Widget.__init__(wifi)
    wifi._wifi_manager, wifi._action_guard = manager, None
    wifi.state, wifi._state_network = UIState.IDLE, None
    wifi._networks = [Network("Saved", 90, SecurityType.OPEN, False), Network("Open", 50, SecurityType.OPEN, False),
                      Network("Locked", 40, SecurityType.WPA, False)]
    owner = NetworkUI.__new__(NetworkUI)
    Widget.__init__(owner)
    owner._wifi_panel, owner._advanced_panel = wifi, Mock()
    owner._advanced_panel._scroller = NS(_items=[])
    owner._current_panel, owner._action_guard = PanelType.WIFI, None
    owner._children = [wifi]
    pane = StarPilotSettingsAdapterLarge(owner, fake_fonts(), "Network", Mock())
    allowed = [True]
    bridge = NetworkPanelBridge(owner, lambda: allowed[0])
    bridge.presentation = pane
    self.assertTrue(bridge.enter())
    return pane, bridge, wifi, manager, allowed

  def test_network_scan_connect_password_forget_and_authority_use_existing_owner(self):
    pane, bridge, wifi, manager, allowed = self.network_panel()
    manager.set_active.assert_called_once_with(True)
    self.assertIsNone(FeatureInput.target(1500, FEATURE_ROW_TOP + FEATURE_ROW_HEIGHT * 1.5, pane.snapshot()))  # connected network: Connect disabled
    self.click(pane, index=1)
    self.assertEqual(wifi.state, UIState.SHOW_FORGET_CONFIRM)
    wifi.state, wifi._state_network = UIState.IDLE, None
    self.click(pane, index=2)
    manager.connect_to_network.assert_called_once_with('Open', '')
    wifi.state, wifi._state_network = UIState.IDLE, None
    self.click(pane, index=3)
    self.assertEqual(wifi.state, UIState.NEEDS_AUTH)
    allowed[0] = False
    wifi.forget_network(wifi._networks[0])
    manager.forget_connection.assert_not_called()
    bridge.leave()
    manager.set_active.assert_called_with(False)
    self.assertFalse(pane.active)

  def test_network_tabs_reset_pages_and_back_returns_to_wifi(self):
    pane, bridge, wifi, manager, allowed = self.network_panel()
    self.click(pane)
    self.assertEqual(pane.panel._current_panel, PanelType.ADVANCED)
    pane.scroll = 5
    pane._emit(FeatureUiAction("back"))
    self.assertEqual(pane.panel._current_panel, PanelType.WIFI)
    self.assertEqual(pane.scroll, 0)
    pane.on_back.assert_not_called()
    pane._emit(FeatureUiAction("back"))
    pane.on_back.assert_called_once_with()
    bridge.leave()


if __name__ == '__main__':
  unittest.main()
