from __future__ import annotations
from dataclasses import replace
import json
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
  ToggleTile,
  draw_list_group_shell,
  draw_section_header,
  draw_selection_list_row,
  draw_settings_panel_header,
  draw_soft_card,
  draw_tab_bar,
  AetherSliderDialog,
  _mix_colors,
  _with_alpha,
  _snap_rect,
  _draw_rounded_fill,
  _draw_rounded_stroke,
  _point_hits,
  _draw_text_fit_common,
)
from openpilot.starpilot.common.connect_server import prepare_konik_server_switch

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
  "StarPilotStats",
  "GithubSshKeys",
  "GithubUsername",
  "MapBoxRequests",
  "ModelDrivesAndScores",
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


SECTION_GAP = AETHER_LIST_METRICS.section_gap
SECTION_HEADER_HEIGHT = AETHER_LIST_METRICS.section_header_height
SECTION_HEADER_GAP = AETHER_LIST_METRICS.section_header_gap
ROW_HEIGHT = AETHER_LIST_METRICS.row_height
FADE_HEIGHT = AETHER_LIST_METRICS.fade_height
PANEL_STYLE = DEFAULT_PANEL_STYLE

SYSTEM_PANEL_METRICS = replace(
  AETHER_LIST_METRICS,
  outer_margin_y=14,
  panel_padding_bottom=14,
)


class SystemSettingsManagerView(PanelManagerView):
  HEADER_SUBTITLE_HEIGHT = 24
  HEADER_SUMMARY_GAP = 6
  HEADER_CARD_HEIGHT = 140
  TAB_HEIGHT = 68
  TAB_GAP = 10
  TAB_BOTTOM_GAP = 18
  ACTION_PILL_WIDTH = 132
  DANGER_PILL_WIDTH = 112
  METRICS = SYSTEM_PANEL_METRICS

  def __init__(self, controller: StarPilotSystemLayout):
    super().__init__()
    self._controller = controller
    self._adjustor_rows: dict[str, AetherAdjustorRow] = {}
    self._display_slider_keys = ["ScreenBrightness", "ScreenBrightnessOnroad", "ScreenTimeout", "ScreenTimeoutOnroad"]
    self._power_slider_keys = ["DeviceShutdown", "LowVoltageShutdown"]

    shutdown_labels = {0: tr("5 mins")}
    for i in range(1, 4):
      shutdown_labels[i] = f"{i * 15} mins"
    for i in range(4, 34):
      shutdown_labels[i] = f"{i - 3} " + (tr("hour") if i == 4 else tr("hours"))
    brightness_labels = {101: tr("Auto"), 0: tr("Off")}

    self._slider_specs: dict[str, dict[str, Any]] = {
      "ScreenBrightness": {
        "title": tr("Offroad Brightness"),
        "subtitle": tr("Primary screen brightness while parked."),
        "unit": "%",
        "labels": brightness_labels,
        "min": 0,
        "max": 101,
        "step": 1,
        "live": True,
        "presets": [0, 25, 50, 75, 101],
        "get": lambda: float(self._controller._params.get_int("ScreenBrightness")),
        "set": lambda v: self._controller._set_brightness("ScreenBrightness", v),
      },
      "ScreenBrightnessOnroad": {
        "title": tr("Onroad Brightness"),
        "subtitle": tr("Screen brightness while driving."),
        "unit": "%",
        "labels": brightness_labels,
        "min": 0,
        "max": 101,
        "step": 1,
        "live": True,
        "presets": [0, 35, 60, 80, 101],
        "get": lambda: float(self._controller._params.get_int("ScreenBrightnessOnroad")),
        "set": lambda v: self._controller._set_brightness("ScreenBrightnessOnroad", int(v)),
      },
      "ScreenTimeout": {
        "title": tr("Offroad Screen Timeout"),
        "subtitle": tr("How long the display stays awake while parked."),
        "unit": "s",
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
        "title": tr("Onroad Screen Timeout"),
        "subtitle": tr("How long the display stays on while driving."),
        "unit": "s",
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
        "subtitle": tr("How long the device waits before powering down."),
        "unit": "",
        "labels": shutdown_labels,
        "min": 0,
        "max": 33,
        "step": 1,
        "live": False,
        "presets": [0, 1, 4, 8],
        "get": lambda: float(self._controller._params.get_int("DeviceShutdown")),
        "set": lambda v: self._controller._params.put_int("DeviceShutdown", int(v)),
      },
      "LowVoltageShutdown": {
        "title": tr("Low Voltage Shutdown"),
        "subtitle": tr("Voltage threshold that protects the car battery."),
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
      adjustor = self._child(
        AetherAdjustorRow(
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
        )
      )
      adjustor.set_touch_valid_callback(lambda: self._scroll_panel.is_touch_valid())
      self._adjustor_rows[key] = adjustor

    self._toggle_defs = [
      {
        "id": "StandbyMode",
        "title": tr("Standby Mode"),
        "subtitle": tr("Keep the device ready for faster wake-ups."),
        "get": lambda: self._controller._params.get_bool("StandbyMode"),
        "set": lambda v: self._controller._params.put_bool("StandbyMode", v),
      },
      {
        "id": "UseKonikServer",
        "title": tr("Use Konik Server"),
        "subtitle": tr("Switch remote services to the Konik endpoint."),
        "get": self._controller._get_konik_state,
        "set": self._controller._on_konik_toggle,
      },
      {
        "id": "DebugMode",
        "title": tr("Debug Mode"),
        "subtitle": tr("Expose additional debugging and developer toggles."),
        "get": lambda: self._controller._params.get_bool("DebugMode"),
        "set": lambda v: self._controller._params.put_bool("DebugMode", v),
      },
      {
        "id": "ShowFPS",
        "title": tr("Show FPS"),
        "subtitle": tr("Display screen refresh rate and system performance metrics onroad."),
        "get": lambda: self._controller._params.get_bool("ShowFPS"),
        "set": lambda v: self._controller._params.put_bool("ShowFPS", v),
      },
      {
        "id": "NoUploads",
        "title": tr("Disable Uploads"),
        "subtitle": tr("Stop all cloud uploads from this device."),
        "get": lambda: self._controller._params.get_bool("NoUploads"),
        "set": lambda v: self._controller._params.put_bool("NoUploads", v),
      },
      {
        "id": "DisableOnroadUploads",
        "title": tr("Disable Onroad Uploads"),
        "subtitle": tr("Block uploads while the car is onroad."),
        "get": lambda: self._controller._params.get_bool("DisableOnroadUploads"),
        "set": lambda v: self._controller._params.put_bool("DisableOnroadUploads", v),
        "is_enabled": lambda: not self._controller._params.get_bool("NoUploads"),
        "disabled_label": tr("Turn off Disable Uploads first"),
      },
      {
        "id": "NoLogging",
        "title": tr("Disable Logging"),
        "subtitle": tr("Stop writing standard log data to storage."),
        "get": lambda: self._controller._params.get_bool("NoLogging"),
        "set": lambda v: self._controller._params.put_bool("NoLogging", v),
      },
      {
        "id": "HigherBitrate",
        "title": tr("High Bitrate Recording"),
        "subtitle": tr("Capture higher-quality onroad footage."),
        "get": lambda: self._controller._params.get_bool("HigherBitrate"),
        "set": self._controller._on_higher_bitrate_toggle,
        "is_enabled": lambda: not self._controller._params.get_bool("DisableOnroadUploads") and not self._controller._params.get_bool("NoUploads"),
        "disabled_label": tr("Uploads must stay enabled"),
      },
    ]

    self._basics_tile_grid_h = 0.0

    self._connectivity_tile_grid = TileGrid(columns=2, padding=12)
    for toggle_def in self._toggle_defs:
      tile = ToggleTile(
        title=toggle_def["title"],
        get_state=toggle_def["get"],
        set_state=toggle_def["set"],
        bg_color=PANEL_STYLE.accent,
        desc=toggle_def["subtitle"],
        is_enabled=toggle_def.get("is_enabled"),
        disabled_label=toggle_def.get("disabled_label", ""),
      )
      self._connectivity_tile_grid.add_tile(tile)
    self._connectivity_tile_grid.set_touch_valid_callback(lambda: self._scroll_panel.is_touch_valid())
    self._child(self._connectivity_tile_grid)
    self._page_grid = self._connectivity_tile_grid
    self._set_toggle_pages([self._toggle_defs[i:i+6] for i in range(0, len(self._toggle_defs), 6)])

    self._drive_mode_control = self._child(
      AetherSegmentedControl(
        [tr("Auto"), tr("Onroad"), tr("Offroad")],
        self._get_drive_mode_index,
        self._on_drive_mode_change,
        statuses=[tr("Default"), tr("Force on"), tr("Force off")],
        style=PANEL_STYLE,
      )
    )

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
    hovered = _point_hits(gui_app.last_mouse_event.pos, rect, parent_rect, pad_x=6, pad_y=pad_y)
    return hovered, self._pressed_target == target_id

  def _target_at(self, mouse_pos) -> str | None:
    for target_id, rect in self._interactive_rects.items():
      if target_id.startswith("static:"):
        if _point_hits(mouse_pos, rect, None, pad_x=6, pad_y=0):
          return target_id
    for target_id, rect in self._interactive_rects.items():
      if not target_id.startswith("static:"):
        if _point_hits(mouse_pos, rect, self._scroll_rect, pad_x=6, pad_y=0):
          return target_id
    return None

  def _activate_target(self, target_id: str | None):
    if not target_id:
      return
    if target_id == "static:first_aid":
      gui_app.push_widget(AetherBackupsCareDialog(self._controller))

  def _on_frame_created(self, frame) -> None:
    self._drive_mode_control.set_parent_rect(frame.header)

  def _draw_header(self, rect: rl.Rectangle):
    draw_settings_panel_header(rect, tr("System Settings"),
                                tr("Manage display, backups, connectivity, and device maintenance from one touch-first panel."),
                                max_title_width=0.60, max_subtitle_width=0.62)

    # First Aid Button in top right
    btn_w, btn_h = 68.0, 68.0
    btn_x = rect.x + rect.width - btn_w
    btn_y = rect.y + 4.0
    btn_rect = rl.Rectangle(btn_x, btn_y, btn_w, btn_h)

    hovered, pressed = self._interactive_state("static:first_aid", btn_rect)

    if pressed:
      fill = rl.Color(255, 255, 255, 30)
      border = PANEL_STYLE.accent
    elif hovered:
      fill = rl.Color(255, 255, 255, 18)
      border = PANEL_STYLE.accent
    else:
      fill = rl.Color(255, 255, 255, 8)
      border = rl.Color(255, 255, 255, 20)

    draw_soft_card(btn_rect, fill, border)

    s = 48.0 / 60.0
    icon_x = btn_x + (btn_w - 60.0 * s) / 2.0
    icon_y = btn_y + (btn_h - 60.0 * s) / 2.0
    icon_color = PANEL_STYLE.accent if (hovered or pressed) else AetherListColors.HEADER
    draw_custom_icon("first_aid", icon_x, icon_y, s, icon_color)

    content_width = rect.width - AETHER_LIST_METRICS.content_right_gutter
    summary_y = rect.y + 92

    control_rect = rl.Rectangle(rect.x, summary_y, content_width, 108)
    self._drive_mode_control.render(control_rect)

  def _measure_content_height(self, width: float) -> float:
    display_h = self._section_block_height(self._slider_section_height(self._display_slider_keys, width))
    power_h = self._section_block_height(self._slider_section_height(self._power_slider_keys, width))

    if self._uses_two_columns(width):
      column_w = self._column_width(width)
      col_w = (column_w - 24 - 12) / 2
      grid_h = 2 * col_w + 12
      container_h = grid_h + 24
      right_h = self._section_block_height(container_h)
      left_h = display_h + SECTION_GAP + power_h
      min_h = self._scroll_rect.height if self._scroll_rect else 0.0
      return max(min_h, left_h, right_h)
    else:
      tiles_content_h = self._connectivity_tile_grid.measure_height(width - 24)
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
      display_container_h = self._slider_section_height(self._display_slider_keys, column_w)
      power_container_h = self._slider_section_height(self._power_slider_keys, column_w)
      header_overhead = (SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP) * 2

      viewport_h = self._scroll_rect.height if self._scroll_rect else 0.0
      needed_gap = viewport_h - (display_container_h + power_container_h + header_overhead)
      section_gap = max(AETHER_LIST_METRICS.section_gap, needed_gap)

      display_bottom = self._draw_slider_section(y, x, column_w, tr("Display"), self._display_slider_keys)
      power_y = display_bottom + section_gap
      self._draw_slider_section(power_y, x, column_w, tr("Power"), self._power_slider_keys)

      container_top = y + SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
      col_w = (column_w - 24 - 12) / 2
      grid_h = 2 * col_w + 12
      container_height = grid_h + 24
      self._draw_connectivity_tiles_column(container_top, x + column_w + self.COLUMN_GAP, column_w, container_height)
      return
    y = self._draw_slider_section(y, x, width, tr("Display"), self._display_slider_keys)
    y += SECTION_GAP
    y = self._draw_slider_section(y, x, width, tr("Power"), self._power_slider_keys)
    y += SECTION_GAP
    self._draw_connectivity_tiles_section(y, x, width)

  def _draw_connectivity_tiles_column(self, y: float, x: float, width: float, height: float):
    draw_list_group_shell(rl.Rectangle(x, y, width, height), style=PANEL_STYLE)
    self._render_page_grid(self._connectivity_tile_grid, rl.Rectangle(x + 12, y + 12, width - 24, height - 24))

  def _draw_connectivity_tiles_section(self, y: float, x: float, width: float):
    tiles_content_h = self._connectivity_tile_grid.measure_height(width - 24)

    draw_list_group_shell(rl.Rectangle(x, y, width, tiles_content_h + 24), style=PANEL_STYLE)
    self._render_page_grid(self._connectivity_tile_grid, rl.Rectangle(x + 12, y + 12, width - 24, tiles_content_h))

  def _draw_slider_section(self, y: float, x: float, width: float, title: str, keys: list[str]) -> float:
    draw_section_header(rl.Rectangle(x, y, width, SECTION_HEADER_HEIGHT), title, style=PANEL_STYLE)
    y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
    group_rect = rl.Rectangle(x, y, width, self._slider_section_height(keys, width))
    draw_list_group_shell(group_rect, style=PANEL_STYLE)
    current_y = group_rect.y
    for index, key in enumerate(keys):
      current_y = self._draw_slider_row(rl.Rectangle(group_rect.x, current_y, group_rect.width, 0), key, is_last=index == len(keys) - 1)
    return y + group_rect.height

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
      {"id": "toggle_snapshots", "text": tr("Toggle Snapshots"), "danger": False},
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

    dialog_w = 960
    dialog_h = 660
    dx = rect.x + (rect.width - dialog_w) / 2
    dy = rect.y + (rect.height - dialog_h) / 2

    MARGIN = 40
    COL_GAP = 24
    content_w = dialog_w - MARGIN * 2
    btn_pad = 12.0
    col_w = (content_w - btn_pad * 2 - COL_GAP) / 2

    d_rect = _snap_rect(rl.Rectangle(dx, dy, dialog_w, dialog_h))
    _draw_rounded_fill(d_rect, rl.Color(10, 12, 16, 255), radius_px=24)
    _draw_rounded_stroke(d_rect, rl.Color(255, 255, 255, 16), radius_px=24)
    rl.draw_rectangle_rec(rl.Rectangle(d_rect.x, d_rect.y, d_rect.width, 4), self._color)

    title_text = tr("Maintenance")
    title_size = 32
    ts = measure_text_cached(self._font_title, title_text, title_size)
    rl.draw_text_ex(self._font_title, title_text, rl.Vector2(round(dx + (dialog_w - ts.x) / 2), round(dy + (84 - title_size) / 2)), title_size, 0, rl.WHITE)

    status_rect = _snap_rect(rl.Rectangle(dx + MARGIN, dy + 84, content_w, 90))
    draw_list_group_shell(status_rect, style=PANEL_STYLE)

    gui_label(rl.Rectangle(status_rect.x + 16, status_rect.y + 8, status_rect.width - 32, 18),
              tr("System Status"), 14, AetherListColors.MUTED, FontWeight.SEMI_BOLD)

    metric_rows = [
      (tr("Storage"), self._controller.storage_summary()),
      (tr("System Backups"), self._controller.backup_count_text()),
      (tr("Toggle Snapshots"), self._controller.toggle_backup_count_text()),
    ]
    metric_label_w = 160.0
    for i, (label, value) in enumerate(metric_rows):
      row_y = status_rect.y + 32 + i * 16
      gui_label(rl.Rectangle(status_rect.x + 16, row_y, metric_label_w, 16),
                label, 14, AetherListColors.MUTED, FontWeight.MEDIUM)
      gui_label(rl.Rectangle(status_rect.x + 16 + metric_label_w, row_y, status_rect.width - 32 - metric_label_w, 16),
                value, 14, AetherListColors.HEADER, FontWeight.MEDIUM)

    mouse_pos = gui_app.last_mouse_event.pos

    btn_fill = rl.Color(22, 24, 32, 255)
    btn_border = rl.Color(255, 255, 255, 40)
    btn_fill_hover = rl.Color(30, 32, 42, 255)
    btn_fill_pressed = _mix_colors(self._color, rl.Color(0, 0, 0, 255), 0.15)
    btn_radius = 14.0

    btn_group_y = dy + 192
    btn_group_h = 4 * 68 + 3 * 14 + btn_pad * 2
    btn_group_rect = _snap_rect(rl.Rectangle(dx + MARGIN, btn_group_y, content_w, btn_group_h))
    draw_list_group_shell(btn_group_rect, style=PANEL_STYLE)

    self._button_rects.clear()
    for i, btn in enumerate(self._buttons):
      btn_id = btn["id"]
      row = i % 4
      col = i // 4
      bx = btn_group_rect.x + btn_pad + col * (col_w + COL_GAP)
      by = btn_group_rect.y + btn_pad + row * (68 + 14)
      btn_rect = _snap_rect(rl.Rectangle(bx, by, col_w, 68))
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

      _draw_rounded_fill(btn_rect, fill, radius_px=btn_radius)
      _draw_rounded_stroke(btn_rect, border, thickness=2, radius_px=btn_radius)

      font_size = 20
      _draw_text_fit_common(
        self._font_btn,
        btn["text"],
        rl.Vector2(btn_rect.x + 12, btn_rect.y + (btn_rect.height - font_size) / 2),
        btn_rect.width - 24,
        font_size,
        align_center=True,
        color=text_color,
      )

    cx = dx + (dialog_w - 320) / 2
    cy = d_rect.y + d_rect.height - 36 - 72
    self._close_rect = _snap_rect(rl.Rectangle(cx, cy, 320, 72))

    close_hovered = rl.check_collision_point_rec(mouse_pos, self._close_rect)
    close_pressed = self._pressed_btn_id == "close"

    if close_pressed:
      close_fill = _mix_colors(self._color, rl.Color(0, 0, 0, 255), 0.2)
      close_border = self._color
    elif close_hovered:
      close_fill = self._color
      close_border = self._color
    else:
      close_fill = rl.Color(255, 255, 255, 14)
      close_border = rl.Color(255, 255, 255, 28)

    draw_soft_card(self._close_rect, close_fill, close_border)

    close_text = tr("Close")
    close_size = 22
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
    return tr("{} full • {} toggle").format(system_count, toggle_count)

  def open_backup_manager(self, backup_kind: str):
    if backup_kind == "system":
      options = [tr("Create Backup"), tr("Restore Backup"), tr("Delete Backup")]
      title = tr("System Backups")
    else:
      options = [tr("Save Toggle Snapshot"), tr("Restore Toggle Snapshot"), tr("Delete Toggle Snapshot")]
      title = tr("Toggle Snapshots")

    def on_select(res):
      if res != DialogResult.CONFIRM or not dialog.selection:
        return
      selection = dialog.selection
      if selection == options[0]:
        if backup_kind == "system":
          self._on_create_backup()
        else:
          self._on_create_toggle_backup()
      elif selection == options[1]:
        if backup_kind == "system":
          self._on_restore_backup()
        else:
          self._on_restore_toggle_backup()
      elif selection == options[2]:
        if backup_kind == "system":
          self._on_delete_backup()
        else:
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
    self._params.put_int(key, int(val))
    if key == "ScreenBrightnessOnroad" and not ui_state.started:
      return
    if key in ("ScreenBrightnessOnroad", "ScreenBrightness") and hasattr(HARDWARE, 'set_brightness'):
      HARDWARE.set_brightness(int(val))

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
          report = json.dumps({"DiscordUser": username, "Issue": dialog.selection})
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
