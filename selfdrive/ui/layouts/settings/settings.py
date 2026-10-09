import pyray as rl
from dataclasses import dataclass
from enum import IntEnum
from collections.abc import Callable
from openpilot.selfdrive.ui.layouts.settings.developer import DeveloperLayout
from openpilot.selfdrive.ui.layouts.settings.device import DeviceLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.main_panel import StarPilotLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import draw_text_fit_common
from openpilot.selfdrive.ui.layouts.settings.software import SoftwareLayout
from openpilot.selfdrive.ui.layouts.settings.toggles import TogglesLayout
from openpilot.system.ui.lib.application import gui_app, FontWeight, MousePos
from openpilot.system.ui.lib.bluetooth_manager import BluetoothManager
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.lib.wifi_manager import WifiManager
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.widgets.bluetooth import BluetoothManagerUI
from openpilot.system.ui.widgets.network import NetworkUI

# Constants
COLLAPSED_WIDTH = 0
EXPANDED_WIDTH = 500
SWIPE_THRESHOLD = 80
CLOSE_BTN_SIZE = 200
CLOSE_ICON_SIZE = 70
NAV_BTN_HEIGHT = 110
PANEL_MARGIN = 10
COLLAPSED_TAB_WIDTH = 64

# Colors
SIDEBAR_COLOR = rl.BLACK
ACCENT_LINE_COLOR = rl.Color(139, 92, 246, 55)
PANEL_COLOR = rl.BLACK
CLOSE_BTN_COLOR = rl.Color(41, 41, 41, 255)
CLOSE_BTN_PRESSED = rl.Color(59, 59, 59, 255)
TEXT_NORMAL = rl.Color(128, 128, 128, 255)
TEXT_SELECTED = rl.WHITE
DARK_CORE_COLOR = rl.Color(12, 10, 18, 190)


class PanelType(IntEnum):
  STARPILOT = 0
  DEVICE = 1
  NETWORK = 2
  BLUETOOTH = 3
  TOGGLES = 4
  SOFTWARE = 5
  DEVELOPER = 6


@dataclass
class PanelInfo:
  name: str
  instance: Widget
  button_rect: rl.Rectangle = rl.Rectangle(0, 0, 0, 0)


class SettingsLayout(Widget):
  def __init__(self):
    super().__init__()
    self._current_panel = PanelType.STARPILOT

    # Panel depth tracking for hierarchical back navigation
    # 0 = top level (settings main), 1+ = nested custom panels
    self._panel_depth = 0

    # Collapse / swipe state (always start expanded)
    self._sidebar_expanded = True
    self._swipe_start = None
    self._collapse_btn_rect = rl.Rectangle(0, 0, 0, 0)
    self._back_btn_rect = rl.Rectangle(0, 0, 0, 0)

    # Panel configuration
    wifi_manager = WifiManager()
    wifi_manager.set_active(False)
    bluetooth_manager = BluetoothManager()
    bluetooth_manager.set_active(False)

    self._panels = {
      PanelType.STARPILOT: PanelInfo(tr_noop("StarPilot"), StarPilotLayout()),
      PanelType.DEVICE: PanelInfo(tr_noop("Device"), DeviceLayout()),
      PanelType.NETWORK: PanelInfo(tr_noop("Network"), NetworkUI(wifi_manager)),
      PanelType.BLUETOOTH: PanelInfo(tr_noop("Bluetooth"), BluetoothManagerUI(bluetooth_manager)),
      PanelType.TOGGLES: PanelInfo(tr_noop("Toggles"), TogglesLayout()),
      PanelType.SOFTWARE: PanelInfo(tr_noop("Software"), SoftwareLayout()),
      PanelType.DEVELOPER: PanelInfo(tr_noop("Developer"), DeveloperLayout()),
    }

    # Connect the custom-panel depth callback for hierarchical back navigation
    self._panels[PanelType.STARPILOT].instance.set_depth_callback(self.set_panel_depth)
    self._panels[PanelType.STARPILOT].instance.set_settings_layout(self)

    self._font_medium = gui_app.font(FontWeight.MEDIUM)
    self._close_icon = gui_app.texture("icons/backspace.png", CLOSE_ICON_SIZE, CLOSE_ICON_SIZE)

    # Callbacks
    self._close_callback: Callable | None = None

  @property
  def _sidebar_width(self) -> int:
    return EXPANDED_WIDTH if self._sidebar_expanded else COLLAPSED_WIDTH

  def set_callbacks(self, on_close: Callable):
    self._close_callback = on_close

  def set_panel_depth(self, depth: int):
    self._panel_depth = depth

  def refresh_developer_visibility(self):
    pass

  def get_panel_depth(self) -> int:
    return self._panel_depth

  def _handle_back_navigation(self):
    if self._panel_depth > 0:
      self._panel_depth -= 1
      if hasattr(self._panels[PanelType.STARPILOT].instance, 'navigate_back'):
        self._panels[PanelType.STARPILOT].instance.navigate_back()
    else:
      if self._close_callback:
        self._close_callback()

  def _render(self, rect: rl.Rectangle):
    w = self._sidebar_width
    sidebar_rect = rl.Rectangle(rect.x, rect.y, w, rect.height)
    panel_rect = rl.Rectangle(rect.x + w, rect.y, rect.width - w, rect.height)

    original_events = list(gui_app.mouse_events)
    if not self._sidebar_expanded:
      tab_zone = rl.Rectangle(rect.x, rect.y + 581 - 70, COLLAPSED_TAB_WIDTH, 140)
      gui_app.mouse_events[:] = [e for e in original_events if not rl.check_collision_point_rec(e.pos, tab_zone)]

    self._draw_current_panel(panel_rect)

    gui_app.mouse_events[:] = original_events
    self._draw_sidebar(sidebar_rect)

  def _draw_chevron(self, cx: float, cy: float, right: bool, color: rl.Color, size: int = 14, bloom: bool = False):
    half = size / 2
    if right:
      p1 = rl.Vector2(cx - half, cy - size)
      p2 = rl.Vector2(cx + half, cy)
      p3 = rl.Vector2(cx - half, cy + size)
    else:
      p1 = rl.Vector2(cx + half, cy - size)
      p2 = rl.Vector2(cx - half, cy)
      p3 = rl.Vector2(cx + half, cy + size)
    if bloom:
      bloom_col = rl.Color(color.r, color.g, color.b, 35)
      rl.draw_line_ex(p1, p2, 7.0, bloom_col)
      rl.draw_line_ex(p2, p3, 7.0, bloom_col)
    rl.draw_line_ex(p1, p2, 2.8, color)
    rl.draw_line_ex(p2, p3, 2.8, color)

  def _draw_sidebar(self, rect: rl.Rectangle):
    rl.draw_rectangle_rec(rect, SIDEBAR_COLOR)

    # 2px purple accent line — persistent in both collapsed and expanded states
    line_rect = rl.Rectangle(rect.x, rect.y, 2, rect.height)
    rl.draw_rectangle_rec(line_rect, ACCENT_LINE_COLOR)

    # Unified Protruding Edge Tab (Expand/Collapse toggle)
    tab_cy = int(rect.y + 581)
    tab_h = 140
    visible_w = 40 if self._sidebar_expanded else COLLAPSED_TAB_WIDTH
    tab_w = visible_w + 30
    tab_x = rect.x - 30
    tab_y = tab_cy - (tab_h / 2)
    tab_rect = rl.Rectangle(tab_x, tab_y, tab_w, tab_h)

    # Hit zone is the visible portion on screen
    self._collapse_btn_rect = rl.Rectangle(rect.x, tab_y, visible_w, tab_h)

    # Interaction state
    is_pressed = False
    mouse_pos = gui_app.last_mouse_event.pos
    if gui_app.last_mouse_event.left_down:
      if self._sidebar_expanded:
        is_pressed = rl.check_collision_point_rec(mouse_pos, self._collapse_btn_rect)
      else:
        is_pressed = self._swipe_start is not None

    # Tab Colors and Styling
    accent = rl.Color(139, 92, 246, 255)
    tab_bg = rl.Color(139, 92, 246, 120 if is_pressed else 60)
    tab_border = rl.Color(accent.r, accent.g, accent.b, 255 if is_pressed else 160)

    # Faint outer glow behind the tab
    glow_rect = rl.Rectangle(tab_x - 10, tab_y - 10, tab_w + 20, tab_h + 20)
    rl.draw_rectangle_rounded(glow_rect, 0.5, 30, rl.Color(accent.r, accent.g, accent.b, 30))

    # Solid core and crisp border
    rl.draw_rectangle_rounded(tab_rect, 0.5, 30, tab_bg)
    rl.draw_rectangle_rounded_lines_ex(tab_rect, 0.5, 30, 2.0, tab_border)

    # Chevron properly centered on the *visible* portion of the tab
    chevron_x = rect.x + visible_w / 2
    self._draw_chevron(chevron_x, tab_cy, not self._sidebar_expanded, rl.Color(255, 255, 255, 255), size=24, bloom=True)

    if self._sidebar_expanded:
      # ── EXPANDED ──

      # Back/Close button - hierarchical navigation
      back_btn_rect = rl.Rectangle(rect.x + (rect.width - CLOSE_BTN_SIZE) / 2, rect.y + 60, CLOSE_BTN_SIZE, CLOSE_BTN_SIZE)
      pressed = gui_app.last_mouse_event.left_down and rl.check_collision_point_rec(gui_app.last_mouse_event.pos, back_btn_rect)
      close_color = CLOSE_BTN_PRESSED if pressed else CLOSE_BTN_COLOR
      rl.draw_rectangle_rounded(back_btn_rect, 1.0, 20, close_color)

      icon_color = rl.Color(255, 255, 255, 255) if not pressed else rl.Color(220, 220, 220, 255)
      icon_dest = rl.Rectangle(
        back_btn_rect.x + (back_btn_rect.width - self._close_icon.width) / 2,
        back_btn_rect.y + (back_btn_rect.height - self._close_icon.height) / 2,
        self._close_icon.width,
        self._close_icon.height,
      )
      rl.draw_texture_pro(
        self._close_icon,
        rl.Rectangle(0, 0, self._close_icon.width, self._close_icon.height),
        icon_dest,
        rl.Vector2(0, 0),
        0,
        icon_color,
      )

      # Store back button rect for click detection
      self._back_btn_rect = back_btn_rect

      # Navigation buttons
      y = rect.y + 300
      for panel_type, panel_info in self._panels.items():
        button_rect = rl.Rectangle(rect.x + 50, y, rect.width - 150, NAV_BTN_HEIGHT)

        # Button styling
        is_selected = panel_type == self._current_panel
        text_color = TEXT_SELECTED if is_selected else TEXT_NORMAL
        # Draw button text (right-aligned)
        panel_name = tr(panel_info.name)
        text_size = measure_text_cached(self._font_medium, panel_name, 65)
        text_pos = rl.Vector2(button_rect.x, button_rect.y + (button_rect.height - text_size.y) / 2)
        draw_text_fit_common(self._font_medium, panel_name, text_pos, button_rect.width, 65, align_right=True, color=text_color)

        # Store button rect for click detection
        panel_info.button_rect = button_rect

        y += NAV_BTN_HEIGHT

  def _draw_current_panel(self, rect: rl.Rectangle):
    rl.draw_rectangle_rounded(rl.Rectangle(rect.x + 10, rect.y + 10, rect.width - 20, rect.height - 20), 0.04, 30, PANEL_COLOR)
    content_rect = rl.Rectangle(rect.x + PANEL_MARGIN, rect.y + 10, rect.width - (PANEL_MARGIN * 2), rect.height - 20)
    panel = self._panels[self._current_panel]
    if panel.instance:
      panel.instance.render(content_rect)

  def _handle_mouse_press(self, mouse_pos: MousePos) -> None:
    if not self._sidebar_expanded:
      # Only record swipe/tap start when touch is within the 10px left margin OR directly on the protruding tab
      gesture_zone = rl.Rectangle(self._rect.x, self._rect.y, 10, self._rect.height)
      tab_zone = rl.Rectangle(self._rect.x, self._rect.y + 581 - 70, COLLAPSED_TAB_WIDTH, 140)
      if rl.check_collision_point_rec(mouse_pos, gesture_zone) or rl.check_collision_point_rec(mouse_pos, tab_zone):
        self._swipe_start = mouse_pos
      else:
        self._swipe_start = None

  def _handle_mouse_release(self, mouse_pos: MousePos) -> None:
    start = self._swipe_start
    self._swipe_start = None

    # ── Collapsed: tap or swipe from left edge ──
    if not self._sidebar_expanded and start is not None:
      dx = mouse_pos.x - start.x
      dy = abs(mouse_pos.y - start.y)
      if dx > SWIPE_THRESHOLD:
        if self._panel_depth > 0:
          self._handle_back_navigation()
        else:
          self._sidebar_expanded = True
        return
      elif dy < 20:
        self._sidebar_expanded = True
        return

    # ── Expanded: collapse button ──
    if self._sidebar_expanded and rl.check_collision_point_rec(mouse_pos, self._collapse_btn_rect):
      self._sidebar_expanded = False
      return

    # ── Expanded: back button ──
    if self._sidebar_expanded and rl.check_collision_point_rec(mouse_pos, self._back_btn_rect):
      self._handle_back_navigation()
      return

    # ── Expanded: nav items ──
    if self._sidebar_expanded:
      for panel_type, panel_info in self._panels.items():
        if rl.check_collision_point_rec(mouse_pos, panel_info.button_rect):
          self.set_current_panel(panel_type)
          return

  def set_current_panel(self, panel_type: PanelType):
    if panel_type != self._current_panel:
      self._panels[self._current_panel].instance.hide_event()
      self._current_panel = panel_type
      self._panels[self._current_panel].instance.show_event()

  def show_event(self):
    super().show_event()
    self._panels[self._current_panel].instance.show_event()

  def hide_event(self):
    super().hide_event()
    self._panels[self._current_panel].instance.hide_event()
