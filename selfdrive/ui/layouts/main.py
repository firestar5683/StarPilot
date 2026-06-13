import pyray as rl
from enum import IntEnum
import cereal.messaging as messaging
from openpilot.system.hardware import PC
from openpilot.system.ui.lib.application import gui_app
from openpilot.selfdrive.ui.layouts.sidebar import Sidebar, SIDEBAR_WIDTH
from openpilot.selfdrive.ui.onroad.starpilot.developer_sidebar import DeveloperSidebar
from openpilot.selfdrive.ui.layouts.home import HomeLayout
from openpilot.selfdrive.ui.layouts.settings.settings import SettingsLayout, PanelType
from openpilot.selfdrive.ui.onroad.starpilot.starpilot_onroad_view import StarPilotOnroadView
from openpilot.selfdrive.ui.ui_state import device, ui_state
from openpilot.system.ui.widgets import Widget
from openpilot.selfdrive.ui.layouts.onboarding import OnboardingWindow


class MainState(IntEnum):
  HOME = 0
  SETTINGS = 1
  ONROAD = 2


class MainLayout(Widget):
  def __init__(self):
    super().__init__()

    self._pm = messaging.PubMaster(['bookmarkButton'])

    self._sidebar = Sidebar()
    self._dev_sidebar = DeveloperSidebar()
    self._current_mode = MainState.HOME
    self._prev_onroad = False

    self._layouts = {MainState.HOME: HomeLayout(), MainState.SETTINGS: SettingsLayout(), MainState.ONROAD: StarPilotOnroadView()}

    self._sidebar_rect = rl.Rectangle(0, 0, 0, 0)
    self._dev_sidebar_rect = rl.Rectangle(0, 0, 0, 0)
    self._content_rect = rl.Rectangle(0, 0, 0, 0)

    self._setup_callbacks()

    gui_app.push_widget(self)

    self._onboarding_window = None
    if not PC:
      self._onboarding_window = OnboardingWindow()
      if not self._onboarding_window.completed:
        gui_app.push_widget(self._onboarding_window)

  def _render(self, _):
    self._handle_onroad_transition()
    self._render_main_content()

  def _setup_callbacks(self):
    self._sidebar.set_callbacks(on_settings=self._on_settings_clicked,
                                on_flag=self._on_bookmark_clicked,
                                open_settings=lambda: self.open_settings(PanelType.TOGGLES))
    self._layouts[MainState.HOME].set_settings_callback(lambda: self.open_settings(PanelType.TOGGLES))
    self._layouts[MainState.SETTINGS].set_callbacks(on_close=self._set_mode_for_state)
    self._layouts[MainState.ONROAD].set_click_callback(self._on_onroad_clicked)
    device.add_interactive_timeout_callback(self._set_mode_for_state)

  def _update_layout_rects(self):
    left_w = SIDEBAR_WIDTH if self._sidebar.is_visible else 0
    right_w = SIDEBAR_WIDTH if (self._current_mode == MainState.ONROAD and self._dev_sidebar.visible) else 0

    self._sidebar_rect = rl.Rectangle(self._rect.x, self._rect.y, SIDEBAR_WIDTH, self._rect.height)
    self._dev_sidebar_rect = rl.Rectangle(
      self._rect.x + self._rect.width - SIDEBAR_WIDTH, self._rect.y,
      SIDEBAR_WIDTH, self._rect.height
    )

    self._content_rect = rl.Rectangle(
      self._rect.x + left_w, self._rect.y,
      self._rect.width - left_w - right_w, self._rect.height
    )

  def _handle_onroad_transition(self):
    if ui_state.started != self._prev_onroad:
      self._prev_onroad = ui_state.started
      self._set_mode_for_state()

  def _set_mode_for_state(self):
    if ui_state.started:
      if self._current_mode != MainState.ONROAD:
        self._sidebar.set_visible(False)
      self._set_current_layout(MainState.ONROAD)
    else:
      self._set_current_layout(MainState.HOME)
      self._sidebar.set_visible(True)

  def _set_current_layout(self, layout: MainState):
    if layout != self._current_mode:
      self._layouts[self._current_mode].hide_event()
      self._current_mode = layout
      self._layouts[self._current_mode].show_event()

  def open_settings(self, panel_type: PanelType):
    self._layouts[MainState.SETTINGS].set_current_panel(panel_type)
    self._set_current_layout(MainState.SETTINGS)
    self._sidebar.set_visible(False)

  def _on_settings_clicked(self):
    self.open_settings(PanelType.STARPILOT)

  def _on_bookmark_clicked(self):
    user_bookmark = messaging.new_message('bookmarkButton')
    user_bookmark.valid = True
    self._pm.send('bookmarkButton', user_bookmark)

  def _on_onroad_clicked(self):
    self._sidebar.set_visible(not self._sidebar.is_visible)

  def _render_main_content(self):
    if self._current_mode == MainState.ONROAD:
      self._dev_sidebar.update()

    self._update_layout_rects()

    if self._sidebar.is_visible:
      self._sidebar.render(self._sidebar_rect)

    has_dev = self._current_mode == MainState.ONROAD and self._dev_sidebar.visible
    content_rect = self._content_rect if (self._sidebar.is_visible or has_dev) else self._rect
    self._layouts[self._current_mode].render(content_rect)

    if has_dev:
      self._dev_sidebar.render(self._dev_sidebar_rect)
