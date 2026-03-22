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
from openpilot.selfdrive.ui.layouts.settings.starpilot.navigation import StarPilotNavigationLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.data import StarPilotDataLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.device import StarPilotDeviceLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.utilities import StarPilotUtilitiesLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.visuals import StarPilotVisualsLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.themes import StarPilotThemesLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.vehicle import StarPilotVehicleSettingsLayout
from openpilot.selfdrive.ui.layouts.settings.starpilot.wheel import StarPilotWheelLayout

from openpilot.selfdrive.ui.layouts.settings.starpilot.metro import TileGrid, HubTile, RadioTileGroup

STARPILOT_ICONS_DIR = "toggle_icons"

class StarPilotLayout(Widget):
  CATEGORIES = [
    {
      "title": "Alerts and Sounds",
      "icon": "icon_sound.png",
      "desc": "Adjust alert volumes and enable custom notifications.",
      "buttons": [("MANAGE", "SOUNDS", 0)],
      "color": "#FF0097",
    },
    {
      "title": "Driving Controls",
      "icon": "icon_steering.png",
      "desc": "Fine-tune custom StarPilot acceleration, braking, and steering controls.",
      "buttons": [("DRIVING MODEL", "DRIVING_MODEL", 0), ("GAS / BRAKE", "LONGITUDINAL", 0), ("STEERING", "LATERAL", 0)],
      "color": "#1BA1E2",
    },
    {
      "title": "Navigation",
      "icon": "icon_navigate.png",
      "desc": "Download map data for the Speed Limit Controller.",
      "buttons": [("MAP DATA", "MAPS", 0), ("NAVIGATION", "NAVIGATION", 0)],
      "color": "#8CBF26",
    },
    {
      "title": "System Settings",
      "icon": "icon_system.png",
      "desc": "Manage backups, device settings, screen options, storage, and tools to keep StarPilot running smoothly.",
      "buttons": [("DATA", "DATA", 0), ("DEVICE CONTROLS", "DEVICE", 0), ("UTILITIES", "UTILITIES", 0)],
      "color": "#FA6800",
    },
    {
      "title": "Theme and Appearance",
      "icon": "icon_display.png",
      "desc": "Customize the look of the driving screen and interface, including themes!",
      "buttons": [("APPEARANCE", "VISUALS", 0), ("THEME", "THEMES", 0)],
      "color": "#A200FF",
    },
    {
      "title": "Vehicle Settings",
      "icon": "icon_vehicle.png",
      "desc": "Configure car-specific options and steering wheel button mappings.",
      "buttons": [("VEHICLE SETTINGS", "VEHICLE", 0), ("WHEEL CONTROLS", "WHEEL", 0)],
      "color": "#FFC40D",
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
      StarPilotPanelType.DRIVING_MODEL: StarPilotPanelInfo(tr_noop("Driving Model"), StarPilotDrivingModelLayout()),
      StarPilotPanelType.LONGITUDINAL: StarPilotPanelInfo(tr_noop("Gas / Brake"), StarPilotLongitudinalLayout()),
      StarPilotPanelType.LATERAL: StarPilotPanelInfo(tr_noop("Steering"), StarPilotLateralLayout()),
      StarPilotPanelType.MAPS: StarPilotPanelInfo(tr_noop("Map Data"), StarPilotMapsLayout()),
      StarPilotPanelType.NAVIGATION: StarPilotPanelInfo(tr_noop("Navigation"), StarPilotNavigationLayout()),
      StarPilotPanelType.DATA: StarPilotPanelInfo(tr_noop("Data Management"), StarPilotDataLayout()),
      StarPilotPanelType.DEVICE: StarPilotPanelInfo(tr_noop("Device Controls"), StarPilotDeviceLayout()),
      StarPilotPanelType.UTILITIES: StarPilotPanelInfo(tr_noop("Utilities"), StarPilotUtilitiesLayout()),
      StarPilotPanelType.VISUALS: StarPilotPanelInfo(tr_noop("Appearance"), StarPilotVisualsLayout()),
      StarPilotPanelType.THEMES: StarPilotPanelInfo(tr_noop("Themes"), StarPilotThemesLayout()),
      StarPilotPanelType.VEHICLE: StarPilotPanelInfo(tr_noop("Vehicle Settings"), StarPilotVehicleSettingsLayout()),
      StarPilotPanelType.WHEEL: StarPilotPanelInfo(tr_noop("Wheel Controls"), StarPilotWheelLayout()),
    }

    self._setup_longitudinal_sub_panels()
    self._setup_sounds_sub_panels()
    self._setup_lateral_sub_panels()
    self._setup_navigation_sub_panels()
    self._setup_maps_sub_panels()

    self._main_grid = TileGrid(columns=None, padding=20)
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
        vis_btns = cat_info["buttons"]
        if len(vis_btns) > 1:
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
        vis_btns = cat_info["buttons"]
        depth = 2 if len(vis_btns) > 1 else 1
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
    self._panel_stack.append((self._current_panel, sub_panel_name))
    self._update_sub_panel_visibility()
    self._update_depth()

  def _update_sub_panel_visibility(self):
    if self._current_panel == StarPilotPanelType.LONGITUDINAL:
      longitudinal = self._panels[StarPilotPanelType.LONGITUDINAL].instance
      if longitudinal:
        current_sub = self._get_current_sub_panel()
        if hasattr(longitudinal, 'set_current_sub_panel'):
          longitudinal.set_current_sub_panel(current_sub)
    elif self._current_panel == StarPilotPanelType.SOUNDS:
      sounds = self._panels[StarPilotPanelType.SOUNDS].instance
      if sounds:
        current_sub = self._get_current_sub_panel()
        if hasattr(sounds, '_navigate_to'):
          sounds._current_sub_panel = current_sub
    elif self._current_panel == StarPilotPanelType.NAVIGATION:
      nav = self._panels[StarPilotPanelType.NAVIGATION].instance
      if nav:
        current_sub = self._get_current_sub_panel()
        if hasattr(nav, '_navigate_to'):
          nav._current_sub_panel = current_sub
    elif self._current_panel == StarPilotPanelType.MAPS:
      maps = self._panels[StarPilotPanelType.MAPS].instance
      if maps:
        current_sub = self._get_current_sub_panel()
        if hasattr(maps, '_navigate_to'):
          maps._current_sub_panel = current_sub

  def _get_current_sub_panel(self) -> str:
    if self._panel_stack and self._panel_stack[-1][0] == self._current_panel:
      return self._panel_stack[-1][1]
    return ""

  def _setup_longitudinal_sub_panels(self):
    longitudinal = self._panels[StarPilotPanelType.LONGITUDINAL].instance
    if longitudinal and hasattr(longitudinal, 'set_navigate_callback'):
      longitudinal.set_navigate_callback(self._push_sub_panel)

  def _setup_sounds_sub_panels(self):
    sounds = self._panels[StarPilotPanelType.SOUNDS].instance
    if sounds and hasattr(sounds, 'set_navigate_callback'):
      sounds.set_navigate_callback(self._push_sub_panel)

  def _setup_lateral_sub_panels(self):
    lateral = self._panels[StarPilotPanelType.LATERAL].instance
    if lateral and hasattr(lateral, 'set_navigate_callback'):
      lateral.set_navigate_callback(self._push_sub_panel)

  def _setup_navigation_sub_panels(self):
    nav = self._panels[StarPilotPanelType.NAVIGATION].instance
    if nav and hasattr(nav, 'set_navigate_callback'):
      nav.set_navigate_callback(self._push_sub_panel)

  def _setup_maps_sub_panels(self):
    maps = self._panels[StarPilotPanelType.MAPS].instance
    if maps and hasattr(maps, 'set_navigate_callback'):
      maps.set_navigate_callback(self._push_sub_panel)

  def _rebuild_grid(self):
    self._main_grid.clear()
    
    panel_type_map = {
      "SOUNDS": StarPilotPanelType.SOUNDS,
      "DRIVING_MODEL": StarPilotPanelType.DRIVING_MODEL,
      "LONGITUDINAL": StarPilotPanelType.LONGITUDINAL,
      "LATERAL": StarPilotPanelType.LATERAL,
      "MAPS": StarPilotPanelType.MAPS,
      "NAVIGATION": StarPilotPanelType.NAVIGATION,
      "DATA": StarPilotPanelType.DATA,
      "DEVICE": StarPilotPanelType.DEVICE,
      "UTILITIES": StarPilotPanelType.UTILITIES,
      "VISUALS": StarPilotPanelType.VISUALS,
      "THEMES": StarPilotPanelType.THEMES,
      "VEHICLE": StarPilotPanelType.VEHICLE,
      "WHEEL": StarPilotPanelType.WHEEL,
    }

    if self._current_category_idx is None:
      # Main Categories Grid
      for i, cat in enumerate(self.CATEGORIES):
        visible_buttons = cat["buttons"]
        if not visible_buttons:
          continue
          
        def on_click(idx=i):
          cat_info = self.CATEGORIES[idx]
          vis_btns = cat_info["buttons"]
          if len(vis_btns) == 1:
            self._current_category_idx = idx
            self._set_current_panel(panel_type_map[vis_btns[0][1]])
          else:
            self._current_category_idx = idx
            self._rebuild_grid()
            if self._depth_callback:
              self._depth_callback(1)

        tile = HubTile(
          title=tr(cat["title"]),
          desc=tr(cat["desc"]),
          icon_path=f"{STARPILOT_ICONS_DIR}/{cat['icon']}",
          on_click=on_click,
          starpilot_icon=True,
          bg_color=cat.get("color")
        )
        self._main_grid.add_tile(tile)
    else:
      # Sub-buttons Grid for selected Category
      cat = self.CATEGORIES[self._current_category_idx]
      visible_buttons = cat["buttons"]
      
      for label, panel_key, _ in visible_buttons:
        p_type = panel_type_map[panel_key]
        def on_btn_click(p=p_type):
          self._set_current_panel(p)

        tile = HubTile(
          title=tr(label),
          desc="",
          icon_path=f"{STARPILOT_ICONS_DIR}/{cat['icon']}", # Reuse category icon for sub-tiles
          on_click=on_btn_click,
          starpilot_icon=True,
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
