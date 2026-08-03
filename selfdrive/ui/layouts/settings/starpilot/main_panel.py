from __future__ import annotations
from collections.abc import Callable
import pyray as rl

from openpilot.common.params import Params
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.lib.application import MousePos, gui_app, FontWeight

from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanelType, StarPilotPanelInfo, FrameCachedParams
from openpilot.selfdrive.ui.layouts.settings.starpilot.sounds import StarPilotSoundsLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.driving_model import StarPilotDrivingModelLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.longitudinal import StarPilotLongitudinalLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.lateral import StarPilotLateralLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.maps import StarPilotMapsLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.system_settings import StarPilotSystemLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.appearance import StarPilotAppearanceLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.vehicle import StarPilotVehicleSettingsLayout

from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import TileGrid, HubTile, SPACING, BreadcrumbController, AETHER_LIST_METRICS, AetherListColors, draw_rounded_fill, draw_rounded_stroke

class StarPilotLayout(Widget):
  CATEGORIES = [
    {
      "title": "Sounds & Alerts",
      "icon": "sound",
      "panel": "SOUNDS",
    },
    {
      "title": "Driving Controls",
      "icon": "steering",
      "buttons": [("Driving Model", "DRIVING_MODEL", "aicar"), ("Gas / Brake", "LONGITUDINAL", "road"), ("Steering", "LATERAL", "steering")],
    },
    {
      "title": "Map Data",
      "icon": "navigate",
      "panel": "MAPS",
    },
    {
      "title": "System",
      "icon": "system",
      "panel": "SYSTEM",
    },
    {
      "title": "Appearance",
      "icon": "display",
      "panel": "VISUALS",
    },
    {
      "title": "Vehicle Settings",
      "icon": "vehicle",
      "panel": "VEHICLE",
    },
  ]

  def __init__(self):
    super().__init__()
    self._params = FrameCachedParams()

    self._current_panel = StarPilotPanelType.MAIN
    self._current_category_idx: int | None = None
    self._depth_callback: Callable | None = None
    self._settings_layout = None

    StarPilotLayout.active_instance = self

    self._panel_stack: list[tuple[StarPilotPanelType, str]] = []  
    self._sub_panel_callbacks: dict[str, Callable] = {}  

    self._panels = {
      StarPilotPanelType.MAIN: StarPilotPanelInfo("", None),
      StarPilotPanelType.SOUNDS: StarPilotPanelInfo(tr_noop("Sounds"), StarPilotSoundsLayout()),
      StarPilotPanelType.SYSTEM: StarPilotPanelInfo(tr_noop("System Settings"), StarPilotSystemLayout()),
      StarPilotPanelType.DRIVING_MODEL: StarPilotPanelInfo(tr_noop("Driving Model"), StarPilotDrivingModelLayout()),
      StarPilotPanelType.LONGITUDINAL: StarPilotPanelInfo(tr_noop("Gas / Brake"), StarPilotLongitudinalLayout()),
      StarPilotPanelType.LATERAL: StarPilotPanelInfo(tr_noop("Steering"), StarPilotLateralLayout()),
      StarPilotPanelType.MAPS: StarPilotPanelInfo(tr_noop("Map Data"), StarPilotMapsLayout()),
      StarPilotPanelType.VISUALS: StarPilotPanelInfo(tr_noop("Appearance"), StarPilotAppearanceLayout()),
      StarPilotPanelType.VEHICLE: StarPilotPanelInfo(tr_noop("Vehicle Settings"), StarPilotVehicleSettingsLayout()),
    }

    self._setup_sub_panels(
      StarPilotPanelType.LONGITUDINAL,
      StarPilotPanelType.SOUNDS,
      StarPilotPanelType.SYSTEM,
      StarPilotPanelType.LATERAL,
      StarPilotPanelType.MAPS,
      StarPilotPanelType.VISUALS,
      StarPilotPanelType.VEHICLE,
    )

    self._breadcrumbs = BreadcrumbController()
    self._main_grid = TileGrid(columns=None, padding=SPACING.tile_gap)
    self._rebuild_grid()

  def set_depth_callback(self, callback: Callable):
    self._depth_callback = callback

  def set_settings_layout(self, settings_layout):
    self._settings_layout = settings_layout

  def navigate_back(self):
    if self._panel_stack:
      self._panel_stack.pop()
      self._commit_navigation()
    elif self._current_panel != StarPilotPanelType.MAIN:
      if self._current_category_idx is not None:
        cat_info = self.CATEGORIES[self._current_category_idx]
        if "buttons" in cat_info:
          self._set_current_panel(StarPilotPanelType.MAIN)
        else:
          self._current_category_idx = None
          self._set_current_panel(StarPilotPanelType.MAIN)
      else:
        self._set_current_panel(StarPilotPanelType.MAIN)
    elif self._current_category_idx is not None:
      self._current_category_idx = None
      self._set_current_panel(StarPilotPanelType.MAIN)

  def _update_depth(self):
    depth = 0
    if self._current_panel != StarPilotPanelType.MAIN:
      if self._current_category_idx is not None:
        cat_info = self.CATEGORIES[self._current_category_idx]
        depth = 2 if "buttons" in cat_info else 1
      else:
        depth = 1
      # Deep nesting check
      if self._panel_stack:
        depth += len(self._panel_stack)
    elif self._current_category_idx is not None:
      depth = 1
    
    if self._depth_callback:
      self._depth_callback(depth)

  def _commit_navigation(self):
    self._update_sub_panel_visibility()
    self._update_depth()

  def _push_sub_panel(self, sub_panel_name: str):
    if sub_panel_name:
      self._panel_stack.append((self._current_panel, sub_panel_name))
    else:
      while self._panel_stack and self._panel_stack[-1][0] == self._current_panel:
        self._panel_stack.pop()
    self._commit_navigation()

  def _update_sub_panel_visibility(self):
    panel = self._panels[self._current_panel].instance
    current_sub = self._get_current_sub_panel()
    if panel and hasattr(panel, 'set_current_sub_panel'):
      panel.set_current_sub_panel(current_sub)

  def _get_current_sub_panel(self) -> str:
    if self._panel_stack and self._panel_stack[-1][0] == self._current_panel:
      return self._panel_stack[-1][1]
    return ""

  def _setup_sub_panels(self, *panel_types: StarPilotPanelType):
    for panel_type in panel_types:
      panel = self._panels[panel_type].instance
      if panel and hasattr(panel, 'set_navigate_callback'):
        panel.set_navigate_callback(self._push_sub_panel)

  def _rebuild_grid(self):
    state = (self._current_category_idx,)
    if getattr(self, "_last_grid_state", None) == state:
      return
    self._last_grid_state = state
    self._main_grid.clear()
    
    panel_type_map = {
      "SOUNDS": StarPilotPanelType.SOUNDS,
      "SYSTEM": StarPilotPanelType.SYSTEM,
      "DRIVING_MODEL": StarPilotPanelType.DRIVING_MODEL,
      "LONGITUDINAL": StarPilotPanelType.LONGITUDINAL,
      "LATERAL": StarPilotPanelType.LATERAL,
      "MAPS": StarPilotPanelType.MAPS,
      "VISUALS": StarPilotPanelType.VISUALS,
      "VEHICLE": StarPilotPanelType.VEHICLE,
    }

    if self._current_category_idx is None:
      # Main Categories Grid
      for i, cat in enumerate(self.CATEGORIES):
        def on_click(idx=i):
          cat_info = self.CATEGORIES[idx]
          self._current_category_idx = idx
          panel_key = cat_info.get("panel")
          if panel_key is not None:
            self._set_current_panel(panel_type_map[panel_key])
          else:
            self._rebuild_grid()
            if self._depth_callback:
              self._depth_callback(1)

        tile = HubTile(
          title=tr(cat["title"]),
          desc=tr(cat.get("desc", "")),
          icon_key=cat["icon"],
          on_click=on_click,
          bg_color=cat.get("color")
        )
        self._main_grid.add_tile(tile)
    else:
      # Sub-buttons Grid for selected Category
      cat = self.CATEGORIES[self._current_category_idx]
      visible_buttons = cat["buttons"]
      
      for button_info in visible_buttons:
        if len(button_info) == 3:
          label, panel_key, btn_icon = button_info
        else:
          label, panel_key = button_info
          btn_icon = cat["icon"]
          
        p_type = panel_type_map[panel_key]
        def on_btn_click(p=p_type):
          self._set_current_panel(p)

        tile = HubTile(
          title=tr(label),
          desc="",
          icon_key=btn_icon,
          on_click=on_btn_click,
          bg_color=cat.get("color")
        )
        self._main_grid.add_tile(tile)

  def _set_current_panel(self, panel_type: StarPilotPanelType):
    if panel_type != self._current_panel:

      if self._current_panel != StarPilotPanelType.MAIN:
        old = self._panels[self._current_panel].instance
        old.hide_event()
        if hasattr(old, 'set_current_sub_panel'):
          old.set_current_sub_panel("")
      self._current_panel = panel_type
      self._panel_stack.clear()
      if panel_type != StarPilotPanelType.MAIN:
        self._panels[panel_type].instance.show_event()
      else:
        self._rebuild_grid()
    elif panel_type == StarPilotPanelType.MAIN:
      self._rebuild_grid()
      self._panel_stack.clear()

    self._commit_navigation()

  def _render(self, rect: rl.Rectangle):
    TOP_BAR_HEIGHT = 72
    BOTTOM_BAR_HEIGHT = 10
    content_rect = rl.Rectangle(rect.x, rect.y + TOP_BAR_HEIGHT, rect.width, rect.height - TOP_BAR_HEIGHT - BOTTOM_BAR_HEIGHT)

    # Standardize width to perfectly match subpanel shells
    shell_w = min(rect.width - AETHER_LIST_METRICS.outer_margin_x * 2, AETHER_LIST_METRICS.max_content_width)
    shell_x = rect.x + (rect.width - shell_w) / 2

    # 0. Draw top bar with HubTile-style purple glow
    glass_rect = rl.Rectangle(shell_x, rect.y + 2, shell_w, TOP_BAR_HEIGHT - 4)

    GLOW = AetherListColors.PRIMARY
    BAR_FILL = rl.Color(12, 10, 18, 255)

    # 0a. Purple glow rings — 4 concentric, fading outward (HubTile parity)
    for i in range(4, 0, -1):
      off = i * 2.5
      gr = rl.Rectangle(glass_rect.x - off, glass_rect.y - off, glass_rect.width + off * 2, glass_rect.height + off * 2)
      a = int(25 * (1.0 - i / 5))
      draw_rounded_fill(gr, rl.Color(GLOW.r, GLOW.g, GLOW.b, max(0, min(255, a))), radius_px=34)

    # 0b. Dark fill — strict parity with HubTile _HUD_BG_ON
    draw_rounded_fill(glass_rect, BAR_FILL, radius_px=34)

    # 0c. Full bright purple border — strict parity
    draw_rounded_stroke(glass_rect, GLOW, radius_px=34)

    # 1. Draw breadcrumbs in top bar
    crumb_rect = rl.Rectangle(glass_rect.x, glass_rect.y, glass_rect.width, glass_rect.height)
    self._breadcrumbs.draw(crumb_rect)

    # 4. Render active content panel
    if self._current_panel == StarPilotPanelType.MAIN:
      grid_rect = rl.Rectangle(shell_x, content_rect.y + AETHER_LIST_METRICS.outer_margin_y, shell_w, content_rect.height - AETHER_LIST_METRICS.outer_margin_y * 2)
      self._main_grid.render(grid_rect)
    else:
      panel = self._panels[self._current_panel]
      if panel.instance:
        panel.instance.render(content_rect)

  def _handle_mouse_press(self, mouse_pos: MousePos):
    self._breadcrumbs.init_interaction(mouse_pos)

  def _handle_mouse_release(self, mouse_pos: MousePos):
    action = self._breadcrumbs.finish_interaction(mouse_pos)
    if action:
      self._breadcrumbs.handle_click(action)

  def _handle_mouse_event(self, mouse_event):
    pass


  def show_event(self):
    super().show_event()
    if self._current_panel != StarPilotPanelType.MAIN:
      self._panels[self._current_panel].instance.show_event()

  def hide_event(self):
    super().hide_event()
    if self._current_panel != StarPilotPanelType.MAIN:
      self._panels[self._current_panel].instance.hide_event()
