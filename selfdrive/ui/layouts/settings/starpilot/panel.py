from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum

import pyray as rl

from openpilot.common.params import Params, UnknownKeyName
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import TileGrid, HubTile, ToggleTile, ValueTile, SliderTile, SPACING, AetherSliderDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.sectioned_panel import SectionedTileLayout, TileSection


class StarPilotPanelType(IntEnum):
    MAIN = 0
    SOUNDS = 1
    DRIVING_MODEL = 2
    LONGITUDINAL = 3
    LATERAL = 4
    MAPS = 5
    DEVICE = 6
    UTILITIES = 7
    VISUALS = 8
    THEMES = 9
    VEHICLE = 10
    WHEEL = 11
    SYSTEM = 12


@dataclass
class StarPilotPanelInfo:
    name: str
    instance: Widget


class StarPilotParamsProxy:
    def __init__(self, params: Params, params_memory: Params):
        self._params = params
        self._params_memory = params_memory

    def _mark_updated(self):
        self._params_memory.put_bool("StarPilotTogglesUpdated", True)

    def put(self, key, value):
        try:
            result = self._params.put(key, value)
        except UnknownKeyName:
            return None
        self._mark_updated()
        return result

    def put_bool(self, key, value):
        try:
            result = self._params.put_bool(key, value)
        except UnknownKeyName:
            return None
        self._mark_updated()
        return result

    def put_int(self, key, value):
        try:
            result = self._params.put_int(key, value)
        except UnknownKeyName:
            return None
        self._mark_updated()
        return result

    def put_float(self, key, value):
        try:
            result = self._params.put_float(key, value)
        except UnknownKeyName:
            return None
        self._mark_updated()
        return result

    def remove(self, key):
        try:
            result = self._params.remove(key)
        except UnknownKeyName:
            return None
        self._mark_updated()
        return result

    def __getattr__(self, name):
        return getattr(self._params, name)


class StarPilotPanel(Widget):
    def __init__(self):
        super().__init__()
        self._params_memory = Params(memory=True)
        self._params = StarPilotParamsProxy(Params(), self._params_memory)
        self._navigate_callback: Callable | None = None
        self._back_callback: Callable | None = None
        self._current_sub_panel = ""
        self._sub_panels: dict[str, Widget] = {}
        self._scroller = None
        self._tile_grid = None
        self._sectioned_grid = None
        self.CATEGORIES = []
        self.SECTIONS = []

    def set_navigate_callback(self, callback: Callable):
        self._navigate_callback = callback

    def set_back_callback(self, callback: Callable):
        self._back_callback = callback

    def set_current_sub_panel(self, sub_panel: str):
        self._current_sub_panel = sub_panel

    def _is_category_visible(self, cat: dict) -> bool:
        visible_fn = cat.get("visible")
        return visible_fn is None or visible_fn()

    def _build_tile(self, cat: dict) -> Widget | None:
        tile_type = cat.get("type", "hub")
        if tile_type == "hub":
            on_click = cat.get("on_click")
            if on_click is None:
                on_click = lambda c=cat: self._navigate_to(c["panel"])

            return HubTile(
                title=tr(cat["title"]),
                desc=tr(cat.get("desc", "")),
                icon_key=cat.get("icon"),
                on_click=on_click,
                bg_color=cat.get("color"),
                get_status=cat.get("get_status"),
            )

        if tile_type == "toggle":
            raw_set_state = cat["set_state"]

            def on_toggle(state: bool, setter=raw_set_state):
                setter(state)
                self._rebuild_grid()

            return ToggleTile(title=tr(cat["title"]), get_state=cat["get_state"], set_state=on_toggle, bg_color=cat.get("color"), desc=tr(cat.get("desc", "")), is_enabled=cat.get("is_enabled"), disabled_label=cat.get("disabled_label", ""))

        if tile_type == "value":
            return ValueTile(title=tr(cat["title"]), get_value=cat["get_value"], on_click=cat["on_click"], bg_color=cat.get("color"), is_enabled=cat.get("is_enabled"), desc=tr(cat.get("desc", "")))

        if tile_type == "slider":
            return SliderTile(
                title=tr(cat["title"]),
                get_value=cat["get_value"],
                set_value=cat["set_value"],
                min_val=cat["min_val"],
                max_val=cat["max_val"],
                step=cat["step"],
                unit=cat.get("unit", ""),
                labels=cat.get("labels", {}),
                bg_color=cat.get("color"),
                is_enabled=cat.get("is_enabled"),
                desc=tr(cat.get("desc", "")),
                on_test=cat.get("on_test"),
            )

        return None

    def _build_tile_grid(self, categories: list[dict], columns: int | None = None, padding: int | None = None, uniform_width: bool = False) -> TileGrid:
        grid = TileGrid(columns=columns, padding=padding, uniform_width=uniform_width)
        for cat in categories:
            if not self._is_category_visible(cat):
                continue
            tile = self._build_tile(cat)
            if tile is not None:
                grid.add_tile(tile)
        return grid

    def _rebuild_grid(self):
        if self.SECTIONS:
            if self._sectioned_grid is None:
                self._sectioned_grid = SectionedTileLayout()

            sections: list[TileSection] = []
            for section in self.SECTIONS:
                visible_fn = section.get("visible")
                if visible_fn is not None and not visible_fn():
                    continue

                grid = self._build_tile_grid(
                    section.get("categories", []),
                    columns=section.get("columns", 2),
                    padding=section.get("padding", SPACING.tile_gap),
                    uniform_width=section.get("uniform_width", True),
                )
                if grid.tiles:
                    sections.append(TileSection(tr(section["title"]), grid))

            self._sectioned_grid.set_sections(sections)
            return

        if not self.CATEGORIES:
            return

        if self._tile_grid is None:
            self._tile_grid = TileGrid(columns=None, padding=SPACING.tile_gap)

        self._tile_grid.clear()

        for cat in self.CATEGORIES:
            if not self._is_category_visible(cat):
                continue
            tile = self._build_tile(cat)
            if tile is not None:
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
        elif self.SECTIONS and self._sectioned_grid:
            self._sectioned_grid.render(rect)
        elif self.CATEGORIES and self._tile_grid:
            self._tile_grid.render(rect)
        elif self._scroller:
            self._scroller.render(rect)

    def show_event(self):
        super().show_event()
        self._rebuild_grid()
        if self._current_sub_panel and self._current_sub_panel in self._sub_panels:
            self._sub_panels[self._current_sub_panel].show_event()
        elif self.SECTIONS and self._sectioned_grid:
            self._sectioned_grid.show_event()
        elif self._scroller:
            self._scroller.show_event()

    def hide_event(self):
        super().hide_event()
        if self._current_sub_panel and self._current_sub_panel in self._sub_panels:
            self._sub_panels[self._current_sub_panel].hide_event()
        elif self.SECTIONS and self._sectioned_grid:
            self._sectioned_grid.hide_event()
        elif self._scroller:
            self._scroller.hide_event()


def create_tile_panel(categories: list[dict], sub_panels: dict[str, Widget] | None = None) -> StarPilotPanel:
    panel = StarPilotPanel()
    panel.CATEGORIES = categories
    panel._sub_panels = sub_panels or {}
    panel._tile_grid = TileGrid(columns=2, padding=SPACING.tile_gap, uniform_width=True)

    for name, child in panel._sub_panels.items():
        if hasattr(child, 'set_navigate_callback'):
            child.set_navigate_callback(panel._navigate_to)
        if hasattr(child, 'set_back_callback'):
            child.set_back_callback(panel._go_back)

    panel._rebuild_grid()
    return panel


# ═══════════════════════════════════════════════════════════════
# _SettingsPage — shared base for AetherSettingsView-backed panels
# ═══════════════════════════════════════════════════════════════

class _SettingsPage(StarPilotPanel):
  """Base for settings pages backed by an AetherSettingsView-like manager.

  Provides default ``_render`` / ``show_event`` / ``hide_event`` that
  delegate to ``_manager_view`` with automatic sub-panel routing, plus
  shared slider and selector dialog helpers.
  """

  SLIDER_COLOR = "#597497"

  def __init__(self):
    super().__init__()
    self._manager_view: Widget | None = None

  def _wire_sub_panels(self):
    """Wire navigation callbacks on all child sub-panels."""
    for child in self._sub_panels.values():
      if hasattr(child, "set_navigate_callback"):
        child.set_navigate_callback(self._navigate_to)
      if hasattr(child, "set_back_callback"):
        child.set_back_callback(self._go_back)

  def _render(self, rect):
    if self._current_sub_panel and self._current_sub_panel in self._sub_panels:
      self._sub_panels[self._current_sub_panel].render(rect)
    elif self._manager_view is not None:
      self._manager_view.render(rect)
    else:
      super()._render(rect)

  def show_event(self):
    super().show_event()
    if self._current_sub_panel and self._current_sub_panel in self._sub_panels:
      self._sub_panels[self._current_sub_panel].show_event()
    elif self._manager_view is not None:
      self._manager_view.show_event()

  def hide_event(self):
    super().hide_event()
    if self._current_sub_panel and self._current_sub_panel in self._sub_panels:
      self._sub_panels[self._current_sub_panel].hide_event()
    elif self._manager_view is not None:
      self._manager_view.hide_event()

  # ── shared dialog helpers ──

  def _show_slider(self, key, min_v, max_v, step=1, unit="",
                   value_type="int", current_value=None, title=None, color=None):
    """Unified slider dialog (int/float).
    
    title: if provided, used as dialog title; otherwise uses tr(key).
    """
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        if value_type == "float":
          self._params.put_float(key, float(val))
        else:
          self._params.put_int(key, int(val))
    if current_value is None:
      current_value = self._params.get_float(key) if value_type == "float" else self._params.get_int(key)
    dialog_title = tr(title) if title else tr(key)
    gui_app.push_widget(AetherSliderDialog(dialog_title, min_v, max_v, step, current_value, on_close,
                                           unit=unit, color=self.SLIDER_COLOR if color is None else color))

  def _show_string_select(self, key, options, default="None"):
    """String-based multi-option selector (puts string via params.put)."""
    current = self._params.get(key, encoding="utf-8") or default

    def on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        self._params.put(key, dialog.selection)

    dialog = MultiOptionDialog(tr(key), options, current, callback=on_select)
    gui_app.push_widget(dialog)

  def _show_labeled_select(self, title, key, options, current_value):
    """Integer-based multi-option selector with label/value pairs (puts int)."""
    option_labels = [tr(label) for _, label in options]
    label_to_value = {tr(label): value for value, label in options}
    default = next((tr(label) for value, label in options if value == current_value), option_labels[0])

    def on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        self._params.put_int(key, label_to_value[dialog.selection])

    dialog = MultiOptionDialog(tr(title), option_labels, default, callback=on_select)
    gui_app.push_widget(dialog)
