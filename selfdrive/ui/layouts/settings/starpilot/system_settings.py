from __future__ import annotations
from dataclasses import replace
import os
import re
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import pyray as rl

from openpilot.system.hardware import HARDWARE
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.system.ui.widgets.keyboard import Keyboard
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.system.ui.widgets.label import gui_label

from openpilot.selfdrive.ui.ui_state import device, ui_state
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage
from openpilot.selfdrive.ui.layouts.settings.starpilot.scribble import draw_custom_icon
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AETHER_LIST_METRICS,
  AetherAdjustorRow,
  AetherSegmentedControl,
  AetherListColors,
  DEFAULT_PANEL_STYLE,
  PanelManagerView,
  TileGrid,
  draw_list_group_shell,
  draw_selection_list_row,
  draw_settings_panel_header,
  draw_soft_card,
  GROUP_HEADER_GAP,
  GROUP_HEADER_LINE_GAP,
  GROUP_HEADER_HEIGHT,
  GROUP_HEADER_TOTAL_HEIGHT,
  GROUP_TOP_INSET,
  draw_group_header,
  AetherSliderDialog,
  mix_colors,
  snap_rect,
  draw_rounded_fill,
  draw_rounded_stroke,
  point_hits,
  draw_text_fit_common,
  wrap_text,
  SECTION_GAP,
  ROW_HEIGHT,
  SPACING,
  TOGGLE_MIN_HEIGHT,
  TOGGLE_ROW_HEIGHT,
)
from openpilot.starpilot.common import param_profiles
from openpilot.starpilot.common.screen_settings import (
  BRIGHTNESS_KEYS, SCREEN_WAKE_DESCRIPTIONS, SCREEN_WAKE_OPTIONS, brightness_preferences, write_screen_setting,
)
from openpilot.selfdrive.ui.layouts.settings.starpilot.screen_controls import (
  AetherBrightnessDialog, BrightnessAdjustorRow, WakeToggleRow, show_screen_save_error,
)
from openpilot.selfdrive.ui.lib.screen_settings import try_screen_setting
from openpilot.starpilot.common.connect_server import prepare_konik_server_switch
from openpilot.starpilot.common.starpilot_variables import EXCLUDED_KEYS as STARPILOT_EXCLUDED_KEYS, TOGGLE_BACKUPS, update_starpilot_toggles

LEGACY_STARPILOT_PARAM_RENAMES = {
  "FrogPilotApiToken": "StarPilotApiToken",
  "FrogPilotCarParams": "StarPilotCarParams",
  "FrogPilotCarParamsPersistent": "StarPilotCarParamsPersistent",
  "FrogPilotDongleId": "StarPilotDongleId",
  "FrogPilotStats": "StarPilotStats",
}

EXCLUDED_KEYS = {
  "AvailableModels",
  "AvailableModelNames",
  "AvailableModelArtifactFormats",
  "StarPilotStats",
  "GithubSshKeys",
  "GithubUsername",
  "MapBoxRequests",
  "ModelDrivesAndScores",
  "ModelManifestVersion",
  "OverpassRequests",
  "SpeedLimits",
  "SpeedLimitsFiltered",
  "UpdaterAvailableBranches",
}

REPORT_CATEGORIES = [
  tr_noop("Acceleration feels harsh or jerky"),
  tr_noop("An alert was unclear and I'm not sure what it meant"),
  tr_noop("Braking is too sudden or uncomfortable"),
  tr_noop("I'm not sure if this is normal or a bug:"),
  tr_noop("My steering wheel buttons aren't working"),
  tr_noop("openpilot disengages when I don't expect it"),
  tr_noop("openpilot feels sluggish or slow to respond"),
  tr_noop("Something else (please describe)"),
]



PANEL_STYLE = DEFAULT_PANEL_STYLE

SYSTEM_PANEL_METRICS = AETHER_LIST_METRICS


class SystemSettingsManagerView(PanelManagerView):
  HEADER_SUBTITLE_HEIGHT = 24
  HEADER_SUMMARY_GAP = 6
  HEADER_CARD_HEIGHT = 140
  TAB_HEIGHT = 98
  TAB_GAP = 14
  TAB_BOTTOM_GAP = 26
  ACTION_PILL_WIDTH = 132
  DANGER_PILL_WIDTH = 112
  _TOPBAR_HEIGHT = 120.0
  _TOPBAR_GAP = 0.0
  METRICS = SYSTEM_PANEL_METRICS

  @property
  def vertical_scrolling_disabled(self) -> bool:
    return True

  @property
  def _hit_rect(self) -> rl.Rectangle:
    base = super()._hit_rect
    return rl.Rectangle(base.x, base.y - 72, base.width, base.height + 72)

  def __init__(self, controller: StarPilotSystemLayout):
    super().__init__()
    self._controller = controller
    self._adjustor_rows: dict[str, AetherAdjustorRow] = {}
    self._display_slider_keys = ["ScreenBrightness", "ScreenBrightnessOnroad", "ScreenTimeout", "ScreenTimeoutOnroad"]
    self._power_slider_keys = ["DeviceShutdown", "LowVoltageShutdown"]

    shutdown_labels = {
      hours: f"{hours} " + (tr("hour") if hours == 1 else tr("hours"))
      for hours in range(1, 31)
    }
    brightness_labels = {0: tr("Off")}

    self._slider_specs: dict[str, dict[str, Any]] = {
      "ScreenBrightness": {
        "title": tr("Offroad Brightness"),
        "subtitle": "",
        "unit": "%",
        "labels": brightness_labels,
        "min": 0,
        "max": 100,
        "step": 1,
        "live": True,
        "presets": [0, 25, 50, 75, 100],
        "get": lambda: float(brightness_preferences(self._controller._params, "ScreenBrightness")["manual"]),
        "set": lambda v: self._controller._set_brightness("ScreenBrightness", v),
      },
      "ScreenBrightnessOnroad": {
        "title": tr("Onroad Brightness"),
        "subtitle": "",
        "unit": "%",
        "labels": brightness_labels,
        "min": 0,
        "max": 100,
        "step": 1,
        "live": True,
        "presets": [0, 25, 50, 75, 100],
        "get": lambda: float(brightness_preferences(self._controller._params, "ScreenBrightnessOnroad")["manual"]),
        "set": lambda v: self._controller._set_brightness("ScreenBrightnessOnroad", int(v)),
      },
      "ScreenTimeout": {
        "title": tr("Offroad Timeout"),
        "subtitle": tr("Screen sleeps while parked."),
        "unit": " seconds",
        "labels": {},
        "min": 5,
        "max": 60,
        "step": 5,
        "live": False,
        "presets": [5, 15, 30, 60],
        "get": lambda: float(self._controller._params.get_int("ScreenTimeout", return_default=True)),
        "set": lambda v: self._set_timeout("ScreenTimeout", v),
      },
      "ScreenTimeoutOnroad": {
        "title": tr("Onroad Timeout"),
        "subtitle": tr("Standby sleeps the screen after this many seconds."),
        "unit": " seconds",
        "labels": {},
        "min": 5,
        "max": 60,
        "step": 5,
        "live": False,
        "presets": [5, 15, 30, 60],
        "get": lambda: float(self._controller._params.get_int("ScreenTimeoutOnroad", return_default=True)),
        "set": lambda v: self._set_timeout("ScreenTimeoutOnroad", v),
      },
      "DeviceShutdown": {
        "title": tr("Shutdown Delay"),
        "subtitle": "",
        "unit": "",
        "labels": shutdown_labels,
        "min": 1,
        "max": 30,
        "step": 1,
        "live": False,
        "presets": [1, 3, 6, 12],
        "get": lambda: float(self._controller._params.get_int("DeviceShutdown")),
        "set": lambda v: self._controller._params.put_int("DeviceShutdown", int(v)),
      },
      "LowVoltageShutdown": {
        "title": tr("Low Voltage Shutdown"),
        "subtitle": "",
        "unit": "V",
        "labels": {},
        "min": 11.8,
        "max": 12.5,
        "step": 0.1,
        "live": False,
        "presets": [11.8, 12.0, 12.2, 12.5],
        "get": lambda: float(self._controller._params.get_float("LowVoltageShutdown")),
        "set": lambda v: self._controller._params.put_float("LowVoltageShutdown", float(v)),
      },
    }

    def make_set_active(k: str):
      return lambda active: self._show_system_slider(k) if active else None

    for key, spec in self._slider_specs.items():
      row_type = BrightnessAdjustorRow if key in BRIGHTNESS_KEYS else AetherAdjustorRow
      row_kwargs = {"params": self._controller._params, "brightness_key": key} if key in BRIGHTNESS_KEYS else {}
      adjustor = self._child(
        row_type(
          spec["title"],
          spec["subtitle"],
          spec["min"],
          spec["max"],
          spec["step"],
          spec["get"],
          on_change=lambda _v: None,
          on_commit=None,
          unit=spec["unit"],
          labels=spec["labels"],
          presets=spec.get("presets", []),
          is_active=lambda: False,
          set_active=make_set_active(key),
          style=PANEL_STYLE,
          color=PANEL_STYLE.accent,
          **row_kwargs,
        )
      )
      adjustor.set_touch_valid_callback(lambda: self._scroll_panel.is_touch_valid())
      self._adjustor_rows[key] = adjustor

    self._toggle_defs = [
      {
        "title": tr("Standby Mode"),
        "subtitle": tr("Only selected events wake the screen. Choose wake events below."),
        "get_state": lambda: self._controller._params.get_bool("StandbyMode"),
        "set_state": lambda v: self._controller._params.put_bool("StandbyMode", v),
      },
      {
        "title": tr("Use Konik Server"),
        "subtitle": "",
        "get_state": self._controller._get_konik_state,
        "set_state": self._controller._on_konik_toggle,
      },
      {
        "title": tr("Debug Mode"),
        "subtitle": "",
        "get_state": lambda: self._controller._params.get_bool("DebugMode"),
        "set_state": lambda v: self._controller._params.put_bool("DebugMode", v),
      },
      {
        "title": tr("Show FPS"),
        "subtitle": "",
        "get_state": lambda: self._controller._params.get_bool("FPSCounter"),
        "set_state": lambda v: self._controller._params.put_bool("FPSCounter", v),
      },
      {
        "title": tr("Disable Uploads"),
        "subtitle": "",
        "get_state": lambda: self._controller._params.get_bool("NoUploads"),
        "set_state": self._controller._on_no_uploads_toggle,
      },
      {
        "title": tr("Disable Onroad Uploads"),
        "subtitle": "",
        "get_state": lambda: self._controller._params.get_bool("DisableOnroadUploads"),
        "set_state": lambda v: self._controller._params.put_bool("DisableOnroadUploads", v),
        "is_enabled": lambda: not self._controller._params.get_bool("NoUploads"),
        "disabled_label": tr("Turn off Disable Uploads first"),
      },
      {
        "title": tr("Disable Logging"),
        "subtitle": "",
        "get_state": lambda: self._controller._params.get_bool("NoLogging"),
        "set_state": self._controller._on_no_logging_toggle,
      },
      {
        "title": tr("High Bitrate Recording"),
        "subtitle": "",
        "get_state": lambda: self._controller._params.get_bool("HigherBitrate"),
        "set_state": self._controller._on_higher_bitrate_toggle,
        "is_enabled": lambda: not self._controller._params.get_bool("DisableOnroadUploads") and not self._controller._params.get_bool("NoUploads"),
        "disabled_label": tr("Uploads must stay enabled"),
      },
    ]

    self._wake_toggle_defs = [
      {
        "title": tr("Wake: {}").format(tr(label)),
        "subtitle": tr(SCREEN_WAKE_DESCRIPTIONS[key]),
        "wake": True,
        "get_state": lambda k=key, d=default: self._controller._params.get_bool(k, default=d),
        "set_state": lambda value, k=key: self._save_wake_setting(k, value),
      }
      for key, label, default in SCREEN_WAKE_OPTIONS
    ]
    self._standby_visible = self._controller._params.get_bool("StandbyMode")
    self._basics_tile_grid_h = 0.0

    if self.PANEL_STYLE.toggle_row_mode:
      self._connectivity_tile_grid = TileGrid(columns=1, padding=SPACING.md, min_tile_height=TOGGLE_MIN_HEIGHT)
    else:
      self._connectivity_tile_grid = TileGrid(columns=2, padding=12, min_tile_height=130.0)
    for toggle_def in self._toggle_defs:
      tile = self._make_toggle_tile(toggle_def)
      self._connectivity_tile_grid.add_tile(tile)
    self.register_page_grid(self._connectivity_tile_grid)
    self._refresh_toggle_pages()

    self._drive_mode_control = self._child(
      AetherSegmentedControl(
        [tr("Auto"), tr("Onroad"), tr("Offroad")],
        self._get_drive_mode_index,
        self._on_drive_mode_change,
        style=PANEL_STYLE,
        suppress_background=True,
      )
    )

  def _save_wake_setting(self, key: str, value: bool):
    return try_screen_setting(lambda: write_screen_setting(self._controller._params, key, value), show_screen_save_error)

  def _make_toggle_tile(self, definition: dict):
    if definition.get("wake"):
      return WakeToggleRow(title=definition["title"], desc=definition["subtitle"],
                           get_state=definition["get_state"], set_state=definition["set_state"], bg_color=self.PANEL_STYLE.accent)
    return super()._make_toggle_tile(definition)

  def _display_keys(self) -> list[str]:
    standby = self._controller._params.get_bool("StandbyMode")
    return [key for key in self._display_slider_keys if key != "ScreenTimeoutOnroad" or standby]

  def _visible_toggle_defs(self) -> list[dict]:
    if self._controller._params.get_bool("StandbyMode"):
      return self._toggle_defs[:1] + self._wake_toggle_defs + self._toggle_defs[1:]
    return self._toggle_defs

  def _refresh_toggle_pages(self):
    definitions = self._visible_toggle_defs()
    page_size = self._compute_page_size(TOGGLE_ROW_HEIGHT)
    self._set_toggle_pages([definitions[i:i + page_size] for i in range(0, len(definitions), page_size)])

  def _tab_subtitle(self, tab_id: str) -> str:
    if tab_id == "basics":
      return tr("{} controls + {} toggles").format(
        len(self._display_slider_keys) + len(self._power_slider_keys),
        len(self._toggle_defs))
    return self._controller.backup_status_text()

  def _format_slider_value(self, key: str) -> str:
    adjustor = self._adjustor_rows.get(key)
    if adjustor is not None:
      return adjustor.formatted_value()
    spec = self._slider_specs[key]
    current_val = spec["get"]()
    if current_val in spec["labels"]:
      return str(spec["labels"][current_val])
    if spec["step"] < 1:
      return f"{current_val:.1f}{spec['unit']}"
    return f"{int(current_val)}{spec['unit']}"

  def _show_system_slider(self, key: str):
    if key in BRIGHTNESS_KEYS:
      gui_app.push_widget(AetherBrightnessDialog(self._controller._params, key, self._slider_specs[key]["title"]))
      return
    spec = self._slider_specs[key]
    original_val = spec["get"]()

    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        spec["set"](val)
      else:
        if spec.get("live"):
          spec["set"](original_val)

    def on_change(val):
      if spec.get("live"):
        spec["set"](val)

    gui_app.push_widget(
      AetherSliderDialog(
        title=spec["title"],
        min_val=float(spec["min"]),
        max_val=float(spec["max"]),
        step=float(spec["step"]),
        current_val=float(original_val),
        on_close=on_close,
        presets=[float(p) for p in spec.get("presets", [])],
        unit=spec["unit"],
        labels=spec["labels"],
        color=PANEL_STYLE.accent,
        on_change=on_change if spec.get("live") else None,
      )
    )

  def _set_timeout(self, key: str, value: float):
    self._controller._params.put_int(key, int(value))
    device.reset_interactive_timeout()

  def _get_drive_mode_index(self):
    state = self._controller._get_force_drive_state()
    if state == tr("Default"):
      return 0
    if state == tr("Onroad"):
      return 1
    if state == tr("Offroad"):
      return 2
    return 0

  def _on_drive_mode_change(self, idx):
    if idx == 0:
        self._controller.handle_action("DriveDefault")
    elif idx == 1:
        self._controller.handle_action("DriveOnroad")
    elif idx == 2:
        self._controller.handle_action("DriveOffroad")

  def _clear_ephemeral_state(self):
    self._pressed_target = None
    self._can_click = True
    for adjustor in self._adjustor_rows.values():
      adjustor.reset_interaction()

  def show_event(self):
    super().show_event()
    self._clear_ephemeral_state()
    self._scroll_offset = 0.0

  def hide_event(self):
    super().hide_event()
    self._clear_ephemeral_state()

  def _interactive_state(self, target_id: str, rect: rl.Rectangle, *, pad_y: float = 0) -> tuple[bool, bool]:
    self._interactive_rects[target_id] = rect
    parent_rect = None if target_id.startswith("static:") else self._scroll_rect
    hovered = point_hits(gui_app.last_mouse_event.pos, rect, parent_rect, pad_x=6, pad_y=pad_y)
    return hovered, self._pressed_target == target_id

  def _target_at(self, mouse_pos) -> str | None:
    for target_id, rect in self._interactive_rects.items():
      if target_id.startswith("static:"):
        if point_hits(mouse_pos, rect, None, pad_x=6, pad_y=0):
          return target_id
    for target_id, rect in self._interactive_rects.items():
      if not target_id.startswith("static:"):
        if point_hits(mouse_pos, rect, self._scroll_rect, pad_x=6, pad_y=0):
          return target_id
    return None

  def _activate_target(self, target_id: str | None):
    if not target_id:
      return
    if target_id == "static:first_aid":
      gui_app.push_widget(AetherBackupsCareDialog(self._controller))

  def _on_frame_created(self, frame) -> None:
    pass

  @property
  def bottombar_height(self) -> float:
    return 0.0

  def _draw_static_elements(self, scroll_rect: rl.Rectangle, content_width: float) -> None:
    pass

  def _draw_header(self, rect: rl.Rectangle):
    content_width = self._scroll_rect.width - AETHER_LIST_METRICS.content_right_gutter
    bar_rect = rl.Rectangle(rect.x, rect.y - 6.0, content_width, self._TOPBAR_HEIGHT)
    draw_list_group_shell(bar_rect, style=self.PANEL_STYLE)
    self._drive_mode_control.render(bar_rect)
    total_offset = self._TOPBAR_HEIGHT + self._TOPBAR_GAP
    self._scroll_rect.y += total_offset
    self._scroll_rect.height = max(0.0, self._scroll_rect.height - total_offset)

    self._draw_breadcrumb_first_aid()

  def _draw_breadcrumb_first_aid(self):
    top_bar_height = 72
    shell_w = min(self._rect.width - AETHER_LIST_METRICS.outer_margin_x * 2, AETHER_LIST_METRICS.max_content_width)
    shell_x = self._rect.x + (self._rect.width - shell_w) / 2

    btn_size = 48.0
    btn_x = shell_x + shell_w - 24 - btn_size
    btn_y = self._rect.y - top_bar_height + (top_bar_height - btn_size) / 2
    btn_rect = rl.Rectangle(btn_x, btn_y, btn_size, btn_size)

    hovered, pressed = self._interactive_state("static:first_aid", btn_rect, pad_y=6)

    if pressed:
      fill = rl.Color(139, 92, 246, 8)
      border = rl.Color(139, 92, 246, 28)
    elif hovered:
      fill = rl.Color(255, 255, 255, 4)
      border = rl.Color(255, 255, 255, 10)
    else:
      fill = rl.Color(255, 255, 255, 0)
      border = rl.Color(255, 255, 255, 0)

    draw_soft_card(btn_rect, fill, border)

    s = btn_size / 60.0
    icon_x = btn_rect.x + (btn_rect.width - 60.0 * s) / 2.0
    icon_y = btn_rect.y + (btn_rect.height - 60.0 * s) / 2.0
    if pressed:
      icon_color = rl.Color(139, 92, 246, 190)
    elif hovered:
      icon_color = rl.Color(160, 170, 185, 170)
    else:
      icon_color = rl.Color(160, 170, 185, 80)
    draw_custom_icon("first_aid", icon_x, icon_y, s, icon_color)

  def _measure_content_height(self, width: float) -> float:
    standby = self._controller._params.get_bool("StandbyMode")
    if standby != self._standby_visible:
      self._standby_visible = standby
      self._refresh_toggle_pages()
    display_h = self._slider_section_height(self._display_keys(), width) + GROUP_TOP_INSET + GROUP_HEADER_TOTAL_HEIGHT
    power_h = self._slider_section_height(self._power_slider_keys, width) + GROUP_TOP_INSET + GROUP_HEADER_TOTAL_HEIGHT

    if self._uses_two_columns(width):
      column_w = self._column_width(width)
      
      # Reset custom heights to calculate natural measurements first
      for key in self._display_keys() + self._power_slider_keys:
        self._adjustor_rows[key].custom_row_height = None

      display_container_h = self._slider_section_height(self._display_keys(), column_w)
      power_container_h = self._slider_section_height(self._power_slider_keys, column_w)

      left_overhead = GROUP_TOP_INSET + 2 * GROUP_HEADER_TOTAL_HEIGHT + SECTION_GAP
      left_natural_content_h = left_overhead + display_container_h + power_container_h
      
      tiles_content_h = self.measure_page_grid_height(self._connectivity_tile_grid, column_w - 24)
      right_natural_container_h = tiles_content_h + 24

      max_natural_h = max(left_natural_content_h, right_natural_container_h)

      if self._scroll_rect:
        available_container_h = self._scroll_rect.height - 12.0
      else:
        available_container_h = max_natural_h

      # Always stretch container to fill available height, preventing empty space at bottom
      max_container_h = available_container_h

      # Scale adjustors if needed
      if max_container_h < max_natural_h:
        scale_f = max_container_h / left_natural_content_h
        row_h = max(80.0, float(AETHER_LIST_METRICS.adjustor_row_height) * scale_f)
        for key in self._display_keys() + self._power_slider_keys:
          self._adjustor_rows[key].custom_row_height = row_h

      self._system_max_container_h = max_container_h

      return self._compute_two_column_height(max_container_h)
    else:
      # Ensure defaults are restored in single column mode
      for key in self._display_keys() + self._power_slider_keys:
        self._adjustor_rows[key].custom_row_height = None
      tiles_content_h = self.measure_page_grid_height(self._connectivity_tile_grid, width - 24)
      return self._stacked_section_height([display_h, power_h, tiles_content_h + 24])

  def _slider_section_height(self, keys: list[str], width: float) -> float:
    total = 0.0
    for key in keys:
      adjustor = self._adjustor_rows[key]
      total += adjustor.measure_height(width)
    return total

  def _draw_scroll_content(self, rect: rl.Rectangle, width: float):
    y = rect.y + self._scroll_offset
    self._draw_basics_tab(y, rect.x, width)

  def _draw_basics_tab(self, y: float, x: float, width: float):
    if self._uses_two_columns(width):
      column_w = self._column_width(width)
      adj_container_h = self._system_max_container_h

      draw_list_group_shell(rl.Rectangle(x, y, column_w, adj_container_h), style=PANEL_STYLE)

      current_y = y + GROUP_TOP_INSET
      current_y = draw_group_header(x + 24, current_y, column_w - 48, tr("Display"))
      for index, key in enumerate(self._display_keys()):
        current_y = self._draw_slider_row(rl.Rectangle(x, current_y, column_w, 0), key, is_last=index == len(self._display_keys()) - 1)
        
      current_y += SECTION_GAP
      
      current_y = draw_group_header(x + 24, current_y, column_w - 48, tr("Power"))
      for index, key in enumerate(self._power_slider_keys):
        current_y = self._draw_slider_row(rl.Rectangle(x, current_y, column_w, 0), key, is_last=index == len(self._power_slider_keys) - 1)

      tg_cols = 1 if self.PANEL_STYLE.toggle_row_mode else 2
      self._draw_two_column_tile_grid(
        self._connectivity_tile_grid, x + column_w + self.COLUMN_GAP, y, column_w,
        self._system_max_container_h, columns=tg_cols)
      return

    y = self._draw_slider_section(y, x, width, tr("Display"), self._display_keys())
    y += SECTION_GAP
    y = self._draw_slider_section(y, x, width, tr("Power"), self._power_slider_keys)
    y += SECTION_GAP
    self._draw_connectivity_tiles_section(y, x, width)

  def _draw_connectivity_tiles_section(self, y: float, x: float, width: float):
    tiles_content_h = self.measure_page_grid_height(self._connectivity_tile_grid, width - 24)

    draw_list_group_shell(rl.Rectangle(x, y, width, tiles_content_h + 24), style=PANEL_STYLE)
    self._render_page_grid(self._connectivity_tile_grid, rl.Rectangle(x + 12, y + 12, width - 24, tiles_content_h))

  def _draw_slider_section(self, y: float, x: float, width: float, title: str, keys: list[str]) -> float:
    group_h = self._slider_section_height(keys, width) + GROUP_TOP_INSET + GROUP_HEADER_TOTAL_HEIGHT
    group_rect = rl.Rectangle(x, y, width, group_h)
    draw_list_group_shell(group_rect, style=PANEL_STYLE)
    current_y = group_rect.y + GROUP_TOP_INSET
    current_y = draw_group_header(x + 24, current_y, width - 48, title)
    for index, key in enumerate(keys):
      current_y = self._draw_slider_row(rl.Rectangle(group_rect.x, current_y, group_rect.width, 0), key, is_last=index == len(keys) - 1)
    return y + group_h

  def _draw_slider_row(self, rect: rl.Rectangle, key: str, is_last: bool) -> float:
    adjustor = self._adjustor_rows[key]
    adjustor.set_is_last(is_last)
    row_h = adjustor.measure_height(rect.width)
    row_rect = rl.Rectangle(rect.x, rect.y, rect.width, row_h)
    adjustor.set_parent_rect(self._scroll_rect)
    adjustor.render(row_rect)
    return rect.y + row_h


class AetherBackupsCareDialog(Widget):
  def __init__(self, controller: StarPilotSystemLayout):
    super().__init__()
    self._controller = controller
    self._color = PANEL_STYLE.accent
    self._font_title = gui_app.font(FontWeight.BOLD)
    self._font_btn = gui_app.font(FontWeight.SEMI_BOLD)
    self._pressed_btn_id: str | None = None

    self._buttons = [
      {"id": "system_backups", "text": tr("System Backups"), "danger": False},
      {"id": "toggle_snapshots", "text": tr("Profiles & Snapshots"), "danger": False},
      {"id": "report_issue", "text": tr("Report Issue"), "danger": False},
      {"id": "flash_panda", "text": tr("Flash Panda"), "danger": False},
      {"id": "clear_data", "text": tr("Clear Driving Data"), "danger": True},
      {"id": "clear_logs", "text": tr("Clear Error Logs"), "danger": True},
      {"id": "reset_toggles", "text": tr("Reset Toggles"), "danger": True},
      {"id": "reset_stock", "text": tr("Reset To Stock"), "danger": True},
    ]

    self._button_rects: dict[str, rl.Rectangle] = {}
    self._close_rect = rl.Rectangle(0, 0, 0, 0)

  def _handle_mouse_press(self, mouse_pos):
    for btn in self._buttons:
      btn_id = btn["id"]
      rect = self._button_rects.get(btn_id)
      if rect and rl.check_collision_point_rec(mouse_pos, rect):
        self._pressed_btn_id = btn_id
        return
    if rl.check_collision_point_rec(mouse_pos, self._close_rect):
      self._pressed_btn_id = "close"

  def _handle_mouse_release(self, mouse_pos):
    if not self._pressed_btn_id:
      return

    released_btn = self._pressed_btn_id
    self._pressed_btn_id = None

    if released_btn == "close":
      if rl.check_collision_point_rec(mouse_pos, self._close_rect):
        gui_app.pop_widget()
      return

    for btn in self._buttons:
      btn_id = btn["id"]
      if btn_id == released_btn:
        rect = self._button_rects.get(btn_id)
        if rect and rl.check_collision_point_rec(mouse_pos, rect):
          self._trigger_action(btn_id)
        break

  def _trigger_action(self, btn_id: str):
    if btn_id == "system_backups":
      self._controller.open_backup_manager("system")
    elif btn_id == "toggle_snapshots":
      self._controller.open_backup_manager("toggle")
    elif btn_id == "report_issue":
      self._controller.handle_action("ReportIssue")
    elif btn_id == "flash_panda":
      self._controller.handle_action("FlashPanda")
    elif btn_id == "clear_data":
      self._controller.handle_action("Storage")
    elif btn_id == "clear_logs":
      self._controller.handle_action("ErrorLogs")
    elif btn_id == "reset_toggles":
      self._controller.handle_action("ResetDefaults")
    elif btn_id == "reset_stock":
      self._controller.handle_action("ResetStock")

  def _render(self, rect: rl.Rectangle):
    rl.draw_rectangle(0, 0, gui_app.width, gui_app.height, rl.Color(0, 0, 0, 160))

    dialog_w = min(2320, int(rect.width - 40))
    dialog_h = min(1015, int(rect.height - 40))
    dx = rect.x + (rect.width - dialog_w) / 2
    dy = rect.y + (rect.height - dialog_h) / 2

    d_rect = snap_rect(rl.Rectangle(dx, dy, dialog_w, dialog_h))
    draw_rounded_fill(d_rect, rl.Color(10, 12, 16, 255), radius_px=35)
    draw_rounded_stroke(d_rect, rl.Color(255, 255, 255, 16), radius_px=35)
    rl.draw_rectangle_rec(rl.Rectangle(d_rect.x, d_rect.y, d_rect.width, 3), self._color)

    title_text = tr("Maintenance")
    title_size = 64
    ts = measure_text_cached(self._font_title, title_text, title_size)
    rl.draw_text_ex(self._font_title, title_text, rl.Vector2(round(dx + (dialog_w - ts.x) / 2), round(dy + 87)), title_size, 0, rl.WHITE)

    MARGIN = 80
    content_w = dialog_w - MARGIN * 2

    status_rect = snap_rect(rl.Rectangle(dx + MARGIN, dy + 170, content_w, 80))
    draw_list_group_shell(status_rect, style=PANEL_STYLE)

    gui_label(rl.Rectangle(status_rect.x + 20, status_rect.y + 10, status_rect.width - 40, 24),
              tr("System Status"), 22, AetherListColors.MUTED, FontWeight.SEMI_BOLD)

    storage_text = tr("Storage: {}").format(self._controller.storage_summary())
    backup_text = tr("Backups: {}  •  Snapshots: {}").format(
      self._controller.backup_count_text(), self._controller.toggle_backup_count_text())
    gui_label(rl.Rectangle(status_rect.x + 20, status_rect.y + 40, status_rect.width - 40, 24),
              storage_text, 22, AetherListColors.HEADER, FontWeight.MEDIUM)
    gui_label(rl.Rectangle(status_rect.x + 300, status_rect.y + 40, status_rect.width - 320, 24),
              backup_text, 22, AetherListColors.HEADER, FontWeight.MEDIUM)

    mouse_pos = gui_app.last_mouse_event.pos

    btn_fill = rl.Color(22, 24, 32, 255)
    btn_border = rl.Color(255, 255, 255, 40)
    btn_fill_hover = rl.Color(30, 32, 42, 255)
    btn_fill_pressed = mix_colors(self._color, rl.Color(0, 0, 0, 255), 0.15)
    btn_radius = 18.0
    COL_GAP = 24
    ROW_GAP = 20
    btn_pad = 16.0
    BTN_HEIGHT = 120.0
    col_w = (content_w - btn_pad * 2 - COL_GAP) / 2

    btn_group_y = dy + 278
    btn_group_h = btn_pad * 2 + 4 * BTN_HEIGHT + 3 * ROW_GAP
    btn_group_rect = snap_rect(rl.Rectangle(dx + MARGIN, btn_group_y, content_w, btn_group_h))
    draw_list_group_shell(btn_group_rect, style=PANEL_STYLE)

    self._button_rects.clear()
    for i, btn in enumerate(self._buttons):
      btn_id = btn["id"]
      row = i % 4
      col = i // 4
      bx = btn_group_rect.x + btn_pad + col * (col_w + COL_GAP)
      by = btn_group_rect.y + btn_pad + row * (BTN_HEIGHT + ROW_GAP)
      btn_rect = snap_rect(rl.Rectangle(bx, by, col_w, BTN_HEIGHT))
      self._button_rects[btn_id] = btn_rect

      hovered = rl.check_collision_point_rec(mouse_pos, btn_rect)
      pressed = self._pressed_btn_id == btn_id

      if btn["danger"]:
        if pressed:
          fill = rl.Color(173, 78, 90, 120)
          border = PANEL_STYLE.danger_text
        elif hovered:
          fill = rl.Color(173, 78, 90, 80)
          border = PANEL_STYLE.danger_text
        else:
          fill = PANEL_STYLE.danger_fill
          border = PANEL_STYLE.danger_border
        text_color = PANEL_STYLE.danger_text
      else:
        if pressed:
          fill = btn_fill_pressed
          border = self._color
        elif hovered:
          fill = btn_fill_hover
          border = self._color
        else:
          fill = btn_fill
          border = btn_border
        text_color = AetherListColors.HEADER

      draw_rounded_fill(btn_rect, fill, radius_px=btn_radius)
      draw_rounded_stroke(btn_rect, border, thickness=2, radius_px=btn_radius)

      font_size = 36
      draw_text_fit_common(
        self._font_btn,
        btn["text"],
        rl.Vector2(btn_rect.x + 16, btn_rect.y + (btn_rect.height - font_size) / 2),
        btn_rect.width - 32,
        font_size,
        align_center=True,
        color=text_color,
      )

    close_w = 600.0
    close_h = 110.0
    cx = dx + (dialog_w - close_w) / 2
    cy = btn_group_rect.y + btn_group_rect.height + 40
    self._close_rect = snap_rect(rl.Rectangle(cx, cy, close_w, close_h))

    close_hovered = rl.check_collision_point_rec(mouse_pos, self._close_rect)
    close_pressed = self._pressed_btn_id == "close"

    if close_pressed:
      close_fill = mix_colors(self._color, rl.Color(0, 0, 0, 255), 0.2)
      close_border = self._color
    elif close_hovered:
      close_fill = self._color
      close_border = self._color
    else:
      close_fill = rl.Color(255, 255, 255, 14)
      close_border = rl.Color(255, 255, 255, 28)

    draw_rounded_fill(self._close_rect, close_fill, radius_px=28)
    draw_rounded_stroke(self._close_rect, close_border, thickness=2, radius_px=28)

    close_text = tr("Close")
    close_size = 38
    cts = measure_text_cached(self._font_btn, close_text, close_size)
    rl.draw_text_ex(
      self._font_btn,
      close_text,
      rl.Vector2(round(self._close_rect.x + (self._close_rect.width - cts.x) / 2), round(self._close_rect.y + (self._close_rect.height - cts.y) / 2)),
      close_size,
      0,
      rl.WHITE,
    )


class StarPilotSystemLayout(_SettingsPage):
  _BACKUP_NAME_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]+")

  def __init__(self):
    super().__init__()
    self._keyboard = Keyboard(min_text_size=0)
    self._storage_text = "0 MB"
    self._storage_updated_at = 0.0
    self._storage_refresh_pending = False
    self._storage_refresh_generation = 0
    self._pending_storage_text: tuple[int, str] | None = None
    self._manager_view = SystemSettingsManagerView(self)
    self._refresh_storage_cache(force=True)

  def show_event(self):
    self._refresh_storage_cache(force=True)
    super().show_event()

  def _render(self, rect: rl.Rectangle):
    if self._pending_storage_text is not None:
      generation, storage_text = self._pending_storage_text
      self._pending_storage_text = None
      if generation == self._storage_refresh_generation:
        self._storage_text = storage_text
        self._storage_updated_at = rl.get_time()
      self._storage_refresh_pending = False
    self._refresh_storage_cache()
    super()._render(rect)

  def _refresh_storage_cache(self, force: bool = False):
    now = rl.get_time()
    if self._storage_refresh_pending:
      return
    if not force and (now - self._storage_updated_at) < 5.0:
      return

    generation = self._storage_refresh_generation + 1
    self._storage_refresh_generation = generation

    def refresh_worker():
      result: str | None = None
      try:
        result = self._get_storage()
      finally:
        if result is None:
          self._storage_refresh_pending = False
        else:
          self._pending_storage_text = (generation, result)

    self._storage_refresh_pending = True
    self._storage_updated_at = now
    threading.Thread(target=refresh_worker, daemon=True).start()

  def storage_summary(self) -> str:
    return str(self._storage_text)

  def backup_count_text(self) -> str:
    count = len(self._get_backups("backups"))
    return tr("None") if count == 0 else tr("{} saved").format(count)

  def backup_count(self) -> int:
    return len(self._get_backups("backups"))

  def toggle_backup_count_text(self) -> str:
    count = len(self._get_backups("toggle_backups"))
    return tr("None") if count == 0 else tr("{} saved").format(count)

  def toggle_backup_count(self) -> int:
    return len(self._get_backups("toggle_backups"))

  def latest_backup_summary(self) -> str:
    backups = self._get_backups("backups")
    if not backups:
      return tr("No full-system backups saved yet.")
    return backups[-1]

  def latest_toggle_backup_summary(self) -> str:
    backups = self._get_backups("toggle_backups")
    if not backups:
      return tr("No toggle snapshots saved yet.")
    return backups[-1]

  def backup_status_text(self) -> str:
    system_count = len(self._get_backups("backups"))
    toggle_count = len(self._get_backups("toggle_backups"))
    return tr("{} full | {} toggle").format(system_count, toggle_count)

  def open_backup_manager(self, backup_kind: str):
    if backup_kind == "system":
      options = [tr("Create Backup"), tr("Restore Backup"), tr("Delete Backup")]
      title = tr("System Backups")
    else:
      options = [
        tr("Profile Slot A"),
        tr("Profile Slot B"),
        tr("Save Named Snapshot"),
        tr("Restore Named Snapshot"),
        tr("Delete Named Snapshot"),
      ]
      title = tr("Settings Profiles & Snapshots")

    def on_select(res):
      if res != DialogResult.CONFIRM or not dialog.selection:
        return
      selection = dialog.selection
      if backup_kind == "system":
        if selection == options[0]:
          self._on_create_backup()
        elif selection == options[1]:
          self._on_restore_backup()
        elif selection == options[2]:
          self._on_delete_backup()
      else:
        if selection == options[0]:
          self._open_param_profile("a")
        elif selection == options[1]:
          self._open_param_profile("b")
        elif selection == options[2]:
          self._on_create_toggle_backup()
        elif selection == options[3]:
          self._on_restore_toggle_backup()
        elif selection == options[4]:
          self._on_delete_toggle_backup()

    dialog = MultiOptionDialog(title, options, callback=on_select)
    gui_app.push_widget(dialog)

  def handle_action(self, action_id: str):
    if action_id == "ScreenManagement":
      self._params.put_bool("ScreenManagement", not self._params.get_bool("ScreenManagement"))
    elif action_id == "DeviceManagement":
      self._params.put_bool("DeviceManagement", not self._params.get_bool("DeviceManagement"))
    elif action_id == "Storage":
      self._on_delete_driving_data()
    elif action_id == "ErrorLogs":
      self._on_delete_error_logs()
    elif action_id == "CreateBackup":
      self._on_create_backup()
    elif action_id == "RestoreBackup":
      self._on_restore_backup()
    elif action_id == "DeleteBackup":
      self._on_delete_backup()
    elif action_id == "CreateToggleBackup":
      self._on_create_toggle_backup()
    elif action_id == "RestoreToggleBackup":
      self._on_restore_toggle_backup()
    elif action_id == "DeleteToggleBackup":
      self._on_delete_toggle_backup()
    elif action_id == "DriveDefault":
      self._params.put_bool("ForceOffroad", False)
      self._params.put_bool("ForceOnroad", False)
    elif action_id == "DriveOnroad":
      self._params.put_bool("ForceOnroad", True)
      self._params.put_bool("ForceOffroad", False)
    elif action_id == "DriveOffroad":
      self._params.put_bool("ForceOffroad", True)
      self._params.put_bool("ForceOnroad", False)
    elif action_id == "FlashPanda":
      self._on_flash_panda()
    elif action_id == "ReportIssue":
      self._on_report_issue()
    elif action_id == "ResetDefaults":
      self._on_reset_defaults()
    elif action_id == "ResetStock":
      self._on_reset_stock()

  def _set_brightness(self, key, val):
    return try_screen_setting(lambda: write_screen_setting(self._params, key, int(val)), show_screen_save_error)

  def _get_konik_state(self):
    if Path("/data/not_vetted").exists():
      return True
    return self._params.get_bool("UseKonikServer")

  def _on_konik_toggle(self, state):
    target = tr("Konik") if state else tr("Comma")

    def on_confirm(res):
      if res != DialogResult.CONFIRM:
        self._params.put_bool("UseKonikServer", not state)
        return
      prepare_konik_server_switch(state, self._params)
      try:
        cache_path = Path("/cache/use_konik")
        if state:
          cache_path.parent.mkdir(parents=True, exist_ok=True)
          cache_path.touch()
        else:
          if cache_path.exists():
            cache_path.unlink()
      except OSError:
        pass
      if ui_state.started:
        gui_app.push_widget(
          ConfirmDialog(
            tr("Reboot required. Reboot now?"), tr("Reboot"), tr("Cancel"),
            callback=lambda res: HARDWARE.reboot() if res == DialogResult.CONFIRM else None
          )
        )

    gui_app.push_widget(
      ConfirmDialog(
        tr("Switch Connect endpoint to {}?").format(target),
        tr("Switch"),
        tr("Cancel"),
        callback=on_confirm
      )
    )

  def _on_no_uploads_toggle(self, state):
    if state:
      gui_app.push_widget(ConfirmDialog(
        tr("This will prevent your drives from being uploaded to comma connect which may impact receiving support. Are you sure?"),
        tr("Disable"),
        callback=lambda res: self._params.put_bool("NoUploads", True) if res == DialogResult.CONFIRM else None,
      ))
    else:
      self._params.put_bool("NoUploads", False)

  def _on_no_logging_toggle(self, state):
    if state:
      gui_app.push_widget(ConfirmDialog(
        tr("This will prevent your drives from being logged. Are you sure?"),
        tr("Disable"),
        callback=lambda res: self._params.put_bool("NoLogging", True) if res == DialogResult.CONFIRM else None,
      ))
    else:
      self._params.put_bool("NoLogging", False)

  def _on_higher_bitrate_toggle(self, state):
    self._params.put_bool("HigherBitrate", state)
    try:
      cache_path = Path("/cache/use_HD")
      if state:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.touch()
      else:
        if cache_path.exists():
          cache_path.unlink()
    except OSError:
      pass
    if ui_state.started:
      gui_app.push_widget(
        ConfirmDialog(
          tr("Reboot required. Reboot now?"), tr("Reboot"), tr("Cancel"), callback=lambda res: HARDWARE.reboot() if res == DialogResult.CONFIRM else None
        )
      )

  def _get_storage(self):
    paths = ["/data/media/0/osm/offline", "/data/media/0/realdata", "/data/backups"]
    total = 0
    for p in paths:
      pp = Path(p)
      if pp.exists():
        total += sum(f.stat().st_size for f in pp.rglob('*') if f.is_file())
    mb = total / (1024 * 1024)
    if mb > 1024:
      return f"{(mb / 1024):.2f} GB"
    return f"{mb:.2f} MB"

  def _on_delete_driving_data(self):
    def _do_delete(res):
      if res == DialogResult.CONFIRM:
        def _task():
          drive_paths = ["/data/media/0/realdata/", "/data/media/0/realdata_HD/", "/data/media/0/realdata_konik/"]
          for path in drive_paths:
            p = Path(path)
            if p.exists():
              for entry in p.iterdir():
                if entry.is_dir():
                  shutil.rmtree(entry, ignore_errors=True)
        threading.Thread(target=_task, daemon=True).start()
        gui_app.push_widget(alert_dialog(tr("Driving data deletion started.")))
    gui_app.push_widget(ConfirmDialog(tr("Delete all driving data and footage?"), tr("Delete"), callback=_do_delete))

  def _on_delete_error_logs(self):
    def _do_delete(res):
      if res == DialogResult.CONFIRM:
        shutil.rmtree("/data/error_logs", ignore_errors=True)
        os.makedirs("/data/error_logs", exist_ok=True)
        gui_app.push_widget(alert_dialog(tr("Error logs deleted.")))
    gui_app.push_widget(ConfirmDialog(tr("Delete all error logs?"), tr("Delete"), callback=_do_delete))

  def _get_backups(self, folder: str = "backups") -> list[str]:
    b_dir = Path(f"/data/{folder}")
    if not b_dir.exists():
      return []
    if folder == "backups":
      entries = [f for f in b_dir.glob("*.tar.zst") if "in_progress" not in f.name]
    else:
      entries = [d for d in b_dir.iterdir() if d.is_dir() and "in_progress" not in d.name]
    entries.sort(key=lambda item: item.stat().st_mtime if item.exists() else 0.0, reverse=True)
    return [entry.name for entry in entries]

  def _sanitize_backup_name(self, raw_name: str, prefix: str) -> str:
    sanitized = self._BACKUP_NAME_SANITIZE_RE.sub("_", raw_name.strip())
    sanitized = sanitized.strip("._-")
    if not sanitized:
      sanitized = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return sanitized

  def _on_create_backup(self):
    def on_name(res, name):
      if res == DialogResult.CONFIRM:
        safe_name = self._sanitize_backup_name(name or "", "backup")
        backup_path = f"/data/backups/{safe_name}.tar.zst"
        if Path(backup_path).exists():
          gui_app.push_widget(alert_dialog(tr("A backup with this name already exists.")))
          return
        gui_app.push_widget(alert_dialog(tr("Backup creation started.")))
        def _task():
          os.makedirs("/data/backups", exist_ok=True)
          subprocess.run(["tar", "--use-compress-program=zstd", "-cf", backup_path, "/data/openpilot"])
        threading.Thread(target=_task, daemon=True).start()
    self._keyboard.reset(min_text_size=0)
    self._keyboard.set_title(tr("Name your backup"), "")
    self._keyboard.set_text("")
    self._keyboard.set_callback(lambda result: on_name(result, self._keyboard.text))
    gui_app.push_widget(self._keyboard)

  def _on_restore_backup(self):
    backups = self._get_backups("backups")
    if not backups:
      gui_app.push_widget(alert_dialog(tr("No backups found.")))
      return

    def _on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        gui_app.push_widget(alert_dialog(tr("Restoring... device will reboot.")))
        def _task():
          shutil.rmtree("/data/openpilot", ignore_errors=True)
          os.makedirs("/data/openpilot", exist_ok=True)
          subprocess.run(["tar", "--use-compress-program=zstd", "-xf", f"/data/backups/{dialog.selection}", "-C", "/"])
          os.system("reboot")
        threading.Thread(target=_task, daemon=True).start()

    dialog = MultiOptionDialog(tr("Select Backup"), backups, callback=_on_select)
    gui_app.push_widget(dialog)

  def _on_delete_backup(self):
    backups = self._get_backups("backups")
    if not backups:
      gui_app.push_widget(alert_dialog(tr("No backups found.")))
      return

    def _on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        backup_name = dialog.selection

        def _on_confirm(confirm_res):
          if confirm_res == DialogResult.CONFIRM:
            os.remove(f"/data/backups/{backup_name}")
            gui_app.push_widget(alert_dialog(tr("Backup deleted.")))

        gui_app.push_widget(ConfirmDialog(tr("Delete backup '{}'?").format(backup_name), tr("Delete"), callback=_on_confirm))

    dialog = MultiOptionDialog(tr("Delete Backup"), backups, callback=_on_select)
    gui_app.push_widget(dialog)

  def _on_create_toggle_backup(self):
    def on_name(res, name):
      if res == DialogResult.CONFIRM:
        safe_name = self._sanitize_backup_name(name or "", "toggle_backup")
        backup_path = Path(f"/data/toggle_backups/{safe_name}")
        if backup_path.exists():
          gui_app.push_widget(alert_dialog(tr("A toggle backup with this name already exists.")))
          return
        os.makedirs(backup_path, exist_ok=True)
        shutil.copytree("/data/params/d", str(backup_path), dirs_exist_ok=True)
        gui_app.push_widget(alert_dialog(tr("Toggle backup created.")))
    self._keyboard.reset(min_text_size=0)
    self._keyboard.set_title(tr("Name your toggle backup"), "")
    self._keyboard.set_text("")
    self._keyboard.set_callback(lambda result: on_name(result, self._keyboard.text))
    gui_app.push_widget(self._keyboard)

  def _open_param_profile(self, slot: str):
    status = param_profiles.profile_status(slot, profile_root=TOGGLE_BACKUPS)
    options = [tr("Save Current Settings")]
    if status["saved"] and not status.get("invalid"):
      options.append(tr("Load Saved Settings"))

    def _on_select(res):
      if res != DialogResult.CONFIRM or not dialog.selection:
        return
      if dialog.selection == options[0]:
        if ui_state.started:
          gui_app.push_widget(alert_dialog(tr("Settings profiles can only be saved while parked.")))
          return
        if status["saved"]:
          gui_app.push_widget(ConfirmDialog(
            tr("Overwrite {} with your current settings?").format(status["label"]),
            tr("Overwrite"),
            callback=lambda confirm_res: self._save_param_profile(slot) if confirm_res == DialogResult.CONFIRM else None,
          ))
        else:
          self._save_param_profile(slot)
      elif len(options) > 1 and dialog.selection == options[1]:
        if ui_state.started:
          gui_app.push_widget(alert_dialog(tr("Settings profiles can only be loaded while parked.")))
          return
        gui_app.push_widget(ConfirmDialog(
          tr("Load {} and overwrite your current settings?").format(status["label"]),
          tr("Load"),
          callback=lambda confirm_res: self._load_param_profile(slot) if confirm_res == DialogResult.CONFIRM else None,
        ))

    dialog = MultiOptionDialog(status["label"], options, callback=_on_select)
    gui_app.push_widget(dialog)

  def _save_param_profile(self, slot: str):
    try:
      status = param_profiles.save_profile(
        self._params,
        slot,
        allowed_keys=param_profiles.eligible_profile_keys(self._params, excluded_keys=STARPILOT_EXCLUDED_KEYS),
        profile_root=TOGGLE_BACKUPS,
      )
    except param_profiles.ParamProfileError as error:
      gui_app.push_widget(alert_dialog(str(error)))
      return
    gui_app.push_widget(alert_dialog(tr("Saved current settings to {}.").format(status["label"])))

  def _load_param_profile(self, slot: str):
    try:
      result = param_profiles.load_profile(
        self._params,
        slot,
        allowed_keys=param_profiles.eligible_profile_keys(self._params, excluded_keys=STARPILOT_EXCLUDED_KEYS),
        profile_root=TOGGLE_BACKUPS,
        legacy_renames=LEGACY_STARPILOT_PARAM_RENAMES,
      )
    except param_profiles.ParamProfileError as error:
      gui_app.push_widget(alert_dialog(str(error)))
      return
    update_starpilot_toggles()
    gui_app.push_widget(alert_dialog(
      tr("Loaded {} settings from {}.").format(result["restoredCount"], result["label"])
    ))

  def _on_restore_toggle_backup(self):
    backups = self._get_backups("toggle_backups")
    if not backups:
      gui_app.push_widget(alert_dialog(tr("No toggle backups found.")))
      return

    def _on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        def on_confirm(r2):
          if r2 == DialogResult.CONFIRM:
            src = Path(f"/data/toggle_backups/{dialog.selection}")
            params_dir = Path("/data/params/d")
            for old_key, new_key in LEGACY_STARPILOT_PARAM_RENAMES.items():
              if (src / old_key).exists():
                (params_dir / new_key).unlink(missing_ok=True)
            shutil.copytree(str(src), "/data/params/d", dirs_exist_ok=True)
            for old_key, new_key in LEGACY_STARPILOT_PARAM_RENAMES.items():
              old_path = params_dir / old_key
              new_path = params_dir / new_key
              if old_path.exists():
                old_path.replace(new_path)
            gui_app.push_widget(alert_dialog(tr("Toggles restored.")))
        gui_app.push_widget(ConfirmDialog(tr("This will overwrite your current toggles."), tr("Restore"), callback=on_confirm))

    dialog = MultiOptionDialog(tr("Select Toggle Backup"), backups, callback=_on_select)
    gui_app.push_widget(dialog)

  def _on_delete_toggle_backup(self):
    backups = self._get_backups("toggle_backups")
    if not backups:
      gui_app.push_widget(alert_dialog(tr("No toggle backups found.")))
      return

    def _on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        backup_name = dialog.selection

        def _on_confirm(confirm_res):
          if confirm_res == DialogResult.CONFIRM:
            shutil.rmtree(f"/data/toggle_backups/{backup_name}", ignore_errors=True)
            gui_app.push_widget(alert_dialog(tr("Toggle backup deleted.")))

        gui_app.push_widget(ConfirmDialog(tr("Delete toggle backup '{}'?").format(backup_name), tr("Delete"), callback=_on_confirm))

    dialog = MultiOptionDialog(tr("Delete Toggle Backup"), backups, callback=_on_select)
    gui_app.push_widget(dialog)

  def _get_force_drive_state(self):
    if self._params.get_bool("ForceOnroad"):
      return tr("Onroad")
    if self._params.get_bool("ForceOffroad"):
      return tr("Offroad")
    return tr("Default")

  def _on_flash_panda(self):
    def _do_flash(res):
      if res == DialogResult.CONFIRM:
        self._params_memory.put_bool("FlashPanda", True)
        gui_app.push_widget(alert_dialog(tr("Panda flashing started. Device will reboot when finished.")))
    gui_app.push_widget(ConfirmDialog(tr("Flash Panda firmware?"), tr("Flash"), callback=_do_flash))

  def _on_report_issue(self):
    def on_category(res):
      if res != DialogResult.CONFIRM or not dialog.selection:
        return
      discord_user = self._params.get("DiscordUsername", encoding='utf-8') or ""
      def on_discord(res2, username):
        if res2 == DialogResult.CONFIRM and username:
          self._params.put("DiscordUsername", username)
          report = {"DiscordUser": username, "Issue": dialog.selection}
          self._params_memory.put("IssueReported", report)
          gui_app.push_widget(alert_dialog(tr("Issue reported. Thank you!")))
      self._keyboard.reset(min_text_size=1)
      self._keyboard.set_title(tr("Discord Username"), "")
      self._keyboard.set_text(discord_user or "")
      self._keyboard.set_callback(lambda result: on_discord(result, self._keyboard.text))
      gui_app.push_widget(self._keyboard)
    dialog = MultiOptionDialog(tr("Select Issue"), REPORT_CATEGORIES, callback=on_category)
    gui_app.push_widget(dialog)

  def _on_reset_defaults(self):
    def _do_reset(res):
      if res == DialogResult.CONFIRM:
        all_keys = self._params.all_keys()
        for k in all_keys:
          if k in EXCLUDED_KEYS:
            continue
          default = self._params.get_default_value(k)
          if default is not None:
            self._params.put(k, default)
        gui_app.push_widget(alert_dialog(tr("Toggles reset to defaults.")))
    gui_app.push_widget(ConfirmDialog(tr("Reset all toggles to defaults?"), tr("Reset"), callback=_do_reset))

  def _on_reset_stock(self):
    def _do_reset(res):
      if res == DialogResult.CONFIRM:
        all_keys = self._params.all_keys()
        for k in all_keys:
          if k in EXCLUDED_KEYS:
            continue
          stock = self._params.get_stock_value(k)
          if stock is not None:
            self._params.put(k, stock)
        gui_app.push_widget(alert_dialog(tr("Toggles reset to stock openpilot.")))
    gui_app.push_widget(ConfirmDialog(tr("Reset all toggles to stock openpilot?"), tr("Reset"), callback=_do_reset))
