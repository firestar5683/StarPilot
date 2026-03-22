from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum

import pyray as rl

from openpilot.common.params import Params
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.widgets import Widget


class StarPilotPanelType(IntEnum):
  MAIN = 0
  SOUNDS = 1
  DRIVING_MODEL = 2
  LONGITUDINAL = 3
  LATERAL = 4
  MAPS = 5
  NAVIGATION = 6
  DATA = 7
  DEVICE = 8
  UTILITIES = 9
  VISUALS = 10
  THEMES = 11
  VEHICLE = 12
  WHEEL = 13


@dataclass
class StarPilotPanelInfo:
  name: str
  instance: Widget


from openpilot.selfdrive.ui.layouts.settings.starpilot.metro import TileGrid, HubTile, ToggleTile, ValueTile


class StarPilotPanel(Widget):
  def __init__(self):
    super().__init__()
    self._params = Params()
    self._params_memory = Params(memory=True)
    self._navigate_callback: Callable | None = None
    self._back_callback: Callable | None = None
    self._current_sub_panel = ""
    self._sub_panels: dict[str, Widget] = {}
    self._scroller = None
    self._tile_grid = None
    self.CATEGORIES = []

  def set_navigate_callback(self, callback: Callable):
    self._navigate_callback = callback

  def set_back_callback(self, callback: Callable):
    self._back_callback = callback

  def _rebuild_grid(self):
    if not self.CATEGORIES:
      return

    if self._tile_grid is None:
      self._tile_grid = TileGrid(columns=None, padding=20)

    self._tile_grid.clear()

    for cat in self.CATEGORIES:
      visible_fn = cat.get("visible")
      if visible_fn is not None and not visible_fn():
        continue

      tile_type = cat.get("type", "hub")
      if tile_type == "hub":
        on_click = cat.get("on_click")
        if on_click is None:
          on_click = lambda c=cat: self._navigate_to(c["panel"])

        tile = HubTile(
          title=tr(cat["title"]),
          desc=tr(cat.get("desc", "")),
          icon_path=cat.get("icon"),
          on_click=on_click,
          starpilot_icon=cat.get("starpilot_icon", True),
          bg_color=cat.get("color"),
        )
      elif tile_type == "toggle":
        tile = ToggleTile(title=tr(cat["title"]), get_state=cat["get_state"], set_state=cat["set_state"], icon_path=cat.get("icon"), bg_color=cat.get("color"))
      elif tile_type == "value":
        tile = ValueTile(title=tr(cat["title"]), get_value=cat["get_value"], on_click=cat["on_click"], icon_path=cat.get("icon"), bg_color=cat.get("color"))
      else:
        continue

      self._tile_grid.add_tile(tile)

  def _navigate_to(self, sub_panel: str):
    self._current_sub_panel = sub_panel
    if self._navigate_callback:
      self._navigate_callback(sub_panel)

  def _go_back(self):
    self._current_sub_panel = ""
    if self._back_callback:
      self._back_callback()

  def _render(self, rect: rl.Rectangle):
    if self._current_sub_panel and self._current_sub_panel in self._sub_panels:
      self._sub_panels[self._current_sub_panel].render(rect)
    elif self.CATEGORIES and self._tile_grid:
      self._tile_grid.render(rect)
    elif self._scroller:
      self._scroller.render(rect)

  def show_event(self):
    super().show_event()
    self._rebuild_grid()
    if self._current_sub_panel and self._current_sub_panel in self._sub_panels:
      self._sub_panels[self._current_sub_panel].show_event()
    elif self._scroller:
      self._scroller.show_event()
