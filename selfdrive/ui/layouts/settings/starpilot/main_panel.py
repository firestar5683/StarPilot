from __future__ import annotations
from collections.abc import Callable
import pyray as rl

from openpilot.common.params import Params
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.lib.application import MousePos

from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanelType, StarPilotPanelInfo
from openpilot.selfdrive.ui.layouts.settings.starpilot.sounds import StarPilotSoundsLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.driving_model import StarPilotDrivingModelLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.longitudinal import StarPilotLongitudinalLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.lateral import StarPilotLateralLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.maps import StarPilotMapsLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.system_settings import StarPilotSystemLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.appearance import StarPilotAppearanceLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.vehicle import StarPilotVehicleSettingsLayout

from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import TileGrid, HubTile, RadioTileGroup, SPACING

class StarPilotLayout(Widget):
  CATEGORIES = [
    {
      "title": "Alerts & Sounds",
      "icon": "sound",
      "panel": "SOUNDS",
      "color": "#E63956",
    },
    {
      "title": "Driving Controls",
      "icon": "steering",
      "buttons": [("DRIVING MODEL", "DRIVING_MODEL"), ("GAS / BRAKE", "LONGITUDINAL"), ("STEERING", "LATERAL")],
      "color": "#3B82F6",
    },
    {
      "title": "Map Data",
      "icon": "navigate",
      "panel": "MAPS",
      "color": "#10B981",
    },
    {
      "title": "System",
      "icon": "system",
      "panel": "SYSTEM",
      "color": "#D946EF",
    },
    {
      "title": "Appearance",
      "icon": "display",
      "panel": "VISUALS",
      "color": "#8B5CF6",
    },
    {
      "title": "Vehicle Settings",
      "icon": "vehicle",
      "panel": "VEHICLE",
      "color": "#64748B",
    },
  ]

  def __init__(self):
    super().__init__()
    self._params = Params()

    self._current_panel = StarPilotPanelType.MAIN
    self._current_category_idx: int | None = None
    self._depth_callback: Callable | None = None
    self._settings_layout = None

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

    self._main_grid = TileGrid(columns=None, padding=SPACING.tile_gap)
    self._rebuild_grid()

  def set_depth_callback(self, callback: Callable):
    self._depth_callback = callback

  def set_settings_layout(self, settings_layout):
    self._settings_layout = settings_layout

  def navigate_back(self):
    if self._panel_stack:
      self._panel_stack.pop()
      self._update_sub_panel_visibility()
      self._update_depth()
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
      self._rebuild_grid()
      if self._depth_callback:
        self._depth_callback(0)

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

  def _push_sub_panel(self, sub_panel_name: str):
    if sub_panel_name:
      self._panel_stack.append((self._current_panel, sub_panel_name))
    else:
      while self._panel_stack and self._panel_stack[-1][0] == self._current_panel:
        self._panel_stack.pop()
    self._update_sub_panel_visibility()
    self._update_depth()

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
      
      for label, panel_key in visible_buttons:
        p_type = panel_type_map[panel_key]
        def on_btn_click(p=p_type):
          self._set_current_panel(p)

        tile = HubTile(
          title=tr(label),
          desc="",
          icon_key=cat["icon"],
          on_click=on_btn_click,
          bg_color=cat.get("color")
        )
        self._main_grid.add_tile(tile)

  def _set_current_panel(self, panel_type: StarPilotPanelType):
    if panel_type != self._current_panel:
      if self._current_panel != StarPilotPanelType.MAIN:
        self._panels[self._current_panel].instance.hide_event()
      self._current_panel = panel_type
      if panel_type != StarPilotPanelType.MAIN:
        self._panels[panel_type].instance.show_event()
      else:
        self._rebuild_grid()

    self._update_depth()

  def _render(self, rect: rl.Rectangle):
    if self._current_panel == StarPilotPanelType.MAIN:
      self._main_grid.render(rect)
    else:
      panel = self._panels[self._current_panel]
      if panel.instance:
        panel.instance.render(rect)

  def show_event(self):
    super().show_event()
    if self._current_panel != StarPilotPanelType.MAIN:
      self._panels[self._current_panel].instance.show_event()

  def hide_event(self):
    super().hide_event()
    if self._current_panel != StarPilotPanelType.MAIN:
      self._panels[self._current_panel].instance.hide_event()
