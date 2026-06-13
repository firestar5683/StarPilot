from __future__ import annotations
from dataclasses import replace
import subprocess
from pathlib import Path

import pyray as rl

from openpilot.common.basedir import BASEDIR
from openpilot.starpilot.common.starpilot_variables import ACTIVE_THEME_PATH
from openpilot.system.ui.lib.application import gui_app, FontWeight, MouseEvent, MousePos
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.lib.scroll_panel2 import GuiScrollPanel2
from openpilot.system.ui.widgets import Widget, DialogResult
from openpilot.system.ui.widgets.label import gui_label
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AETHER_LIST_METRICS,
  COMPACT_PANEL_METRICS,
  AetherAdjustorRow,
  AetherListColors,
  AetherScrollbar,
  TileGrid,
  ToggleTile,
  panel_style_from_color,
  _point_hits,
  draw_action_pill,
  draw_list_group_shell,
  draw_list_scroll_fades,
  draw_section_header,
  draw_settings_panel_header,
  init_list_panel,
  AetherSliderDialog,
)

PANEL_STYLE = panel_style_from_color("#E63956")
SECTION_GAP = AETHER_LIST_METRICS.section_gap
SECTION_HEADER_HEIGHT = AETHER_LIST_METRICS.section_header_height
SECTION_HEADER_GAP = AETHER_LIST_METRICS.section_header_gap

GROUP_HEADER_HEIGHT = 20
GROUP_HEADER_GAP = 2
GROUP_HAIRLINE_COLOR = rl.Color(255, 255, 255, 10)
GROUP_HEADER_COLOR = rl.Color(255, 255, 255, 90)

SOUNDS_PANEL_METRICS = replace(
  COMPACT_PANEL_METRICS,
  outer_margin_y=14,
  panel_padding_top=16,
  panel_padding_bottom=14,
  header_height=88,
)


class SoundsManagerView(Widget):
  def __init__(self, controller: StarPilotSoundsLayout):
    super().__init__()
    self._controller = controller
    self._pressed_target: str | None = None
    self._adjustor_rows: dict[str, AetherAdjustorRow] = {}
    self._can_click = True
    self._reset_rect = rl.Rectangle(0, 0, 0, 0)

    self._scroll_panel = GuiScrollPanel2(horizontal=False)
    self._scrollbar = AetherScrollbar()
    self._content_height = 0.0
    self._scroll_offset = 0.0
    self._scroll_rect = rl.Rectangle(0, 0, 0, 0)
    self._tile_grid_h = 0.0

    self._init_adjustors()
    self._init_toggles()
    self._forward_touch_valid()

  def _forward_touch_valid(self):
    self._toggle_grid.set_touch_valid_callback(
      lambda: self._scroll_panel.is_touch_valid()
    )

  def _init_toggles(self):
    self._toggle_grid = TileGrid(columns=2, padding=12)
    for key in self._controller.CUSTOM_ALERTS_KEYS:
      info = self._controller.ALERT_INFO[key]
      tile = ToggleTile(
        title=tr(info["title"]),
        get_state=lambda k=key: self._controller._params.get_bool(k),
        set_state=lambda state, k=key: self._controller._params.put_bool(k, state),
        bg_color=PANEL_STYLE.accent,
        desc=tr(info.get("subtitle", "")),
        is_enabled=info.get("is_enabled"),
        disabled_label=tr(info.get("disabled_label", "")) if info.get("disabled_label") else "",
      )
      self._toggle_grid.add_tile(tile)
    self._child(self._toggle_grid)

  def _set_active_adjustor(self, key: str, active: bool):
    if active:
      if self._active_adjustor_key and self._active_adjustor_key != key:
        old = self._adjustor_rows.get(self._active_adjustor_key)
        if old:
          old.reset_interaction()
      self._active_adjustor_key = key
    elif self._active_adjustor_key == key:
      self._active_adjustor_key = None

  def _init_adjustors(self):
    for key in self._controller.VOLUME_KEYS:
      info = self._controller.VOLUME_INFO[key]

      adjustor = AetherAdjustorRow(
        tr(info["title"]),
        tr(info["subtitle"]),
        0.0, 101.0, 1.0,
        get_value=lambda k=key: float(self._controller._params.get_int(k, return_default=True, default=101)),
        on_change=lambda _v: None,
        on_commit=None,
        unit="%",
        labels={0.0: tr("Muted"), 101.0: tr("Auto")},
        presets=[0, 25, 50, 75, 101],
        is_active=lambda: False,
        set_active=lambda active, k=key: self._show_volume_slider(k) if active else None,
        style=PANEL_STYLE,
        color=PANEL_STYLE.accent,
      )
      self._adjustor_rows[key] = adjustor

    cd_key = self._controller.COOLDOWN_KEY
    cd_info = self._controller.COOLDOWN_INFO
    def on_cd_close(res, val):
      if res == DialogResult.CONFIRM:
        self._controller._params.put_int(cd_key, int(val))

    cd_adjustor = AetherAdjustorRow(
      tr(cd_info["title"]),
      tr(cd_info["subtitle"]),
      0.0, float(cd_info["max"]), 1.0,
      get_value=lambda: float(self._controller._params.get_int(cd_key, return_default=True, default=0)),
      on_change=lambda _v: None,
      on_commit=None,
      unit=" " + tr("min"),
      labels={0.0: tr("Off"), 1.0: tr("1 min")},
      presets=[0, 1, 5, 10, 20, 30],
      is_active=lambda: False,
      set_active=lambda active: gui_app.push_widget(
        AetherSliderDialog(
          title=tr(cd_info["title"]),
          min_val=0.0,
          max_val=float(cd_info["max"]),
          step=1.0,
          current_val=float(self._controller._params.get_int(cd_key, return_default=True, default=0)),
          on_close=on_cd_close,
          presets=[0.0, 1.0, 5.0, 10.0, 20.0, 30.0],
          unit=" " + tr("min"),
          labels={0.0: tr("Off"), 1.0: tr("1 min")},
          color=PANEL_STYLE.accent,
        )
      ) if active else None,
      style=PANEL_STYLE,
      color=PANEL_STYLE.accent,
    )
    self._adjustor_rows[cd_key] = cd_adjustor

  def _show_volume_slider(self, key: str):
    info = self._controller.VOLUME_INFO[key]
    min_v = info["min"]
    original_val = self._controller._params.get_int(key, return_default=True, default=101)

    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        new_v = int(val)
        if new_v != 101 and new_v < min_v:
          new_v = min_v
        self._controller._params.put_int(key, new_v)
      else:
        self._controller._params.put_int(key, original_val)

    def on_change(val):
      new_v = int(val)
      if new_v != 101 and new_v < min_v:
        new_v = min_v
      self._controller._params.put_int(key, new_v)
      self._controller._test_sound(key)

    current_val = float(original_val)
    dialog_title = tr(info["title"])
    gui_app.push_widget(
      AetherSliderDialog(
        title=dialog_title,
        min_val=0.0,
        max_val=101.0,
        step=1.0,
        current_val=current_val,
        on_close=on_close,
        presets=[0.0, 25.0, 50.0, 75.0, 101.0],
        unit="%",
        labels={0.0: tr("Muted"), 101.0: tr("Auto")},
        color=PANEL_STYLE.accent,
        on_change=on_change,
      )
    )

  def _handle_mouse_press(self, mouse_pos: MousePos):
    self._pressed_target = self._target_at(mouse_pos)
    self._can_click = True
    for adjustor in self._adjustor_rows.values():
      adjustor._handle_mouse_press(mouse_pos)
    self._toggle_grid._handle_mouse_press(mouse_pos)

  def _handle_mouse_release(self, mouse_pos: MousePos):
    for adjustor in self._adjustor_rows.values():
      adjustor._handle_mouse_release(mouse_pos)
    self._toggle_grid._handle_mouse_release(mouse_pos)

    target = self._target_at(mouse_pos) if self._scroll_panel.is_touch_valid() else None
    if self._pressed_target is not None and self._pressed_target == target and self._can_click:
      self._activate_target(target)
    self._pressed_target = None
    self._can_click = True

  def _handle_mouse_event(self, mouse_event: MouseEvent):
    if not self._scroll_panel.is_touch_valid():
      self._can_click = False
      return
    for adjustor in self._adjustor_rows.values():
      adjustor._handle_mouse_event(mouse_event)
    self._toggle_grid._handle_mouse_event(mouse_event)

  def _target_at(self, mouse_pos: MousePos) -> str | None:
    if _point_hits(mouse_pos, self._reset_rect, None, pad_x=6, pad_y=0):
      return "action:restore_defaults"
    return None

  def _activate_target(self, target: str):
    if target == "action:restore_defaults":
      self._controller._restore_defaults()

  def show_event(self):
    super().show_event()
    self._pressed_target = None
    self._can_click = True

  def hide_event(self):
    super().hide_event()
    self._pressed_target = None
    self._can_click = True

  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)

    frame, scroll_rect, content_width = init_list_panel(rect, PANEL_STYLE, metrics=SOUNDS_PANEL_METRICS)
    self._scroll_rect = scroll_rect

    self._draw_header(frame.header)

    self._content_height = self._measure_content_height(content_width)

    self._scroll_panel.set_enabled(self.is_visible)
    self._scroll_offset = self._scroll_panel.update(
      scroll_rect, max(self._content_height, scroll_rect.height)
    )

    rl.begin_scissor_mode(
      int(scroll_rect.x), int(scroll_rect.y),
      int(scroll_rect.width), int(scroll_rect.height)
    )
    self._draw_scroll_content(scroll_rect, content_width)
    rl.end_scissor_mode()

    if self._content_height > scroll_rect.height:
      self._scrollbar.render(scroll_rect, self._content_height, self._scroll_offset)
    draw_list_scroll_fades(scroll_rect, self._content_height, self._scroll_offset,
                           AetherListColors.PANEL_BG)

  def _measure_content_height(self, content_width: float) -> float:
    col_width = (content_width - SECTION_GAP) / 2
    left_h = 0.0
    for key in self._controller.VOLUME_KEYS:
      left_h += self._adjustor_rows[key].measure_height(col_width)
    left_h += GROUP_HEADER_HEIGHT + GROUP_HEADER_GAP
    left_h += GROUP_HEADER_HEIGHT + GROUP_HEADER_GAP
    left_h += GROUP_HEADER_HEIGHT + GROUP_HEADER_GAP
    left_column_total_h = left_h + 16

    cd_h = self._adjustor_rows[self._controller.COOLDOWN_KEY].measure_height(col_width)

    tile_rows = self._toggle_grid.get_row_count(len(self._toggle_grid.tiles), available_width=col_width)
    tile_gaps = self._toggle_grid.get_internal_gap_height(len(self._toggle_grid.tiles), available_width=col_width)
    tiles_content_h = tile_rows * 130 + tile_gaps

    self._tile_grid_h = max(tiles_content_h, left_column_total_h - cd_h - SECTION_GAP - (GROUP_HEADER_HEIGHT + GROUP_HEADER_GAP) - 16.0)

    right_column_total_h = cd_h + SECTION_GAP + (GROUP_HEADER_HEIGHT + GROUP_HEADER_GAP) + (self._tile_grid_h + 16.0)

    section_overhead = SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
    min_h = self._scroll_rect.height if self._scroll_rect else 0.0
    return max(min_h, section_overhead + max(left_column_total_h, right_column_total_h))

  def _draw_header(self, rect: rl.Rectangle):
    draw_settings_panel_header(rect, tr("Sounds & Alerts"), tr("Manage system volumes and custom alert toggles."), subtitle_size=24)

    btn_w = 120.0
    btn_h = 38.0
    btn_x = rect.x + rect.width - btn_w
    btn_y = rect.y + (rect.height - btn_h) / 2
    self._reset_rect = rl.Rectangle(btn_x, btn_y, btn_w, btn_h)

    hovered = _point_hits(gui_app.last_mouse_event.pos, self._reset_rect, None, pad_x=6, pad_y=0)
    pressed = self._pressed_target == "action:restore_defaults"
    draw_action_pill(
      self._reset_rect, tr("Reset All"),
      rl.Color(255, 255, 255, 8 if not pressed else 14),
      rl.Color(255, 255, 255, 18 if not pressed else 28),
      AetherListColors.SUBTEXT if not hovered else AetherListColors.HEADER,
    )

  def _draw_scroll_content(self, rect: rl.Rectangle, content_width: float):
    y = rect.y + self._scroll_offset
    col_width = (content_width - SECTION_GAP) / 2

    draw_section_header(
      rl.Rectangle(rect.x, y, col_width, SECTION_HEADER_HEIGHT),
      tr("Volume"), style=PANEL_STYLE
    )
    draw_section_header(
      rl.Rectangle(rect.x + col_width + SECTION_GAP, y, col_width, SECTION_HEADER_HEIGHT),
      tr("Alerts"), style=PANEL_STYLE
    )
    y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP

    self._draw_volume_column(y, rect.x, col_width)
    self._draw_utility_column(y, rect.x + col_width + SECTION_GAP, col_width)

  def _draw_group_header(self, x: float, y: float, width: float, label: str) -> float:
    gui_label(rl.Rectangle(x, y, width, GROUP_HEADER_HEIGHT), label, 14, GROUP_HEADER_COLOR, FontWeight.MEDIUM)
    y += GROUP_HEADER_HEIGHT
    rl.draw_line(int(x), int(y), int(x + width), int(y), GROUP_HAIRLINE_COLOR)
    return y + GROUP_HEADER_GAP

  def _draw_volume_column(self, y: float, x: float, width: float):
    safety_keys = ["WarningImmediateVolume", "WarningSoftVolume", "RefuseVolume", "PromptDistractedVolume"]
    system_keys = ["EngageVolume", "DisengageVolume"]
    info_keys = ["PromptVolume", "BelowSteerSpeedVolume"]

    groups = [
      (tr("SAFETY ALERTS"), safety_keys),
      (tr("SYSTEM STATE"), system_keys),
      (tr("INFORMATIONAL"), info_keys),
    ]

    total_h = sum(GROUP_HEADER_HEIGHT + GROUP_HEADER_GAP + sum(self._adjustor_rows[k].measure_height(width) for k in keys) for _, keys in groups)
    draw_list_group_shell(
      rl.Rectangle(x, y, width, total_h + 16),
      style=PANEL_STYLE
    )

    current_y = y + 8
    for label, keys in groups:
      current_y = self._draw_group_header(x + 24, current_y, width - 48, label)
      for key in keys:
        adjustor = self._adjustor_rows[key]
        row_h = adjustor.measure_height(width)
        row_rect = rl.Rectangle(x, current_y, width, row_h)
        adjustor.set_is_last(True)
        adjustor.set_parent_rect(self._scroll_rect)
        adjustor.render(row_rect)
        current_y += row_h

  def _draw_utility_column(self, y: float, x: float, width: float):
    current_y = y

    cd_key = self._controller.COOLDOWN_KEY
    adjustor = self._adjustor_rows[cd_key]
    row_h = adjustor.measure_height(width)

    draw_list_group_shell(rl.Rectangle(x, current_y, width, row_h), style=PANEL_STYLE)

    adjustor.set_is_last(True)
    adjustor.set_parent_rect(self._scroll_rect)
    adjustor.render(rl.Rectangle(x, current_y, width, row_h))
    current_y += row_h + SECTION_GAP

    current_y = self._draw_group_header(x + 24, current_y, width - 48, tr("CUSTOM ALERTS"))

    draw_list_group_shell(rl.Rectangle(x, current_y, width, self._tile_grid_h + 16), style=PANEL_STYLE)

    self._toggle_grid.set_parent_rect(self._scroll_rect)
    self._toggle_grid.render(rl.Rectangle(x + 12, current_y + 8, width - 24, self._tile_grid_h))


class StarPilotSoundsLayout(_SettingsPage):
  COOLDOWN_KEY = "SwitchbackModeCooldown"
  VOLUME_KEYS = [
    "WarningImmediateVolume",
    "WarningSoftVolume",
    "RefuseVolume",
    "PromptDistractedVolume",
    "EngageVolume",
    "DisengageVolume",
    "PromptVolume",
    "BelowSteerSpeedVolume",
  ]
  CUSTOM_ALERTS_KEYS = [
    "GreenLightAlert",
    "LeadDepartingAlert",
    "LoudBlindspotAlert",
    "SpeedLimitChangedAlert",
  ]

  COOLDOWN_INFO = {
    "title": tr_noop("Switchback Mode Cooldown"),
    "subtitle": tr_noop("Time before switchback re-engages"),
    "min": 0,
    "max": 30,
  }
  VOLUME_INFO = {
    "WarningImmediateVolume": {"title": tr_noop("Immediate Warning"), "subtitle": tr_noop("Critical safety intervention"), "min": 25},
    "WarningSoftVolume": {"title": tr_noop("Soft Warning"), "subtitle": tr_noop("Approaching system limits"), "min": 25},
    "RefuseVolume": {"title": tr_noop("Engagement Refused"), "subtitle": tr_noop("Action refused by system"), "min": 0},
    "PromptDistractedVolume": {"title": tr_noop("Distracted Driver"), "subtitle": tr_noop("Driver attention required"), "min": 0},
    "EngageVolume": {"title": tr_noop("Engagement Chime"), "subtitle": tr_noop("System engaged confirmation"), "min": 0},
    "DisengageVolume": {"title": tr_noop("Disengagement Alert"), "subtitle": tr_noop("Handoff to manual control"), "min": 0},
    "PromptVolume": {"title": tr_noop("General Prompt"), "subtitle": tr_noop("System guidance prompt"), "min": 0},
    "BelowSteerSpeedVolume": {"title": tr_noop("Low Speed Alert"), "subtitle": tr_noop("Minimum speed for steering"), "min": 0},
  }

  _sound_player_process = None

  def __init__(self):
    super().__init__()
    self._init_sound_player()

    self.ALERT_INFO = {
      "GreenLightAlert": {
        "title": tr_noop("Green Light"),
        "subtitle": tr_noop("When lead car moves at green light"),
      },
      "LeadDepartingAlert": {
        "title": tr_noop("Lead Departure"),
        "subtitle": tr_noop("When lead vehicle pulls away"),
      },
      "LoudBlindspotAlert": {
        "title": tr_noop("Loud Blindspot"),
        "subtitle": tr_noop("Blind spot collision warning"),
        "is_enabled": lambda: starpilot_state.car_state.hasBSM,
        "disabled_label": tr_noop("Needs BSM")
      },
      "SpeedLimitChangedAlert": {
        "title": tr_noop("Speed Limit"),
        "subtitle": tr_noop("When posted speed limit changes"),
        "is_enabled": lambda: self._params.get_bool("ShowSpeedLimits") or (
          starpilot_state.car_state.hasOpenpilotLongitudinal and self._params.get_bool("SpeedLimitController")
        ),
        "disabled_label": tr_noop("Needs Speed Limits")
      },
    }

    self._manager_view = SoundsManagerView(self)

  def _restore_defaults(self):
    for key in self.VOLUME_KEYS:
      self._params.put_int(key, 101)
    self._params.put_int(self.COOLDOWN_KEY, 0)
    for key in self.CUSTOM_ALERTS_KEYS:
      self._params.put_bool(key, False)

  @classmethod
  def _init_sound_player(cls):
    if cls._sound_player_process is not None and cls._sound_player_process.poll() is None: return
    program = """
import numpy as np
import sounddevice as sd
import sys
import wave
while True:
  try:
    line = sys.stdin.readline()
    if not line: break
    path, volume = line.strip().split('|')
    with wave.open(path, 'rb') as sound_file:
      audio = np.frombuffer(sound_file.readframes(sound_file.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
      sd.play(audio * float(volume), sound_file.getframerate())
    sd.wait()
  except Exception:
    sd._terminate()
    sd._initialize()
"""
    cls._sound_player_process = subprocess.Popen(["python3", "-u", "-c", program], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

  def _test_sound(self, key: str):
    base_name = key.replace("Volume", "")
    if ui_state.started:
      alert_name = "belowSteerSpeed" if base_name == "BelowSteerSpeed" else base_name[0].lower() + base_name[1:]
      self._params_memory.put("TestAlert", alert_name)
    else:
      self._play_sound_offroad(key)

  def _play_sound_offroad(self, key: str):
    base_name = key.replace("Volume", "")
    preview_base_name = "Prompt" if base_name == "BelowSteerSpeed" else base_name
    snake_case = "".join(["_" + c.lower() if c.isupper() else c for c in preview_base_name]).lstrip("_")
    stock_path = Path(BASEDIR) / "selfdrive" / "assets" / "sounds" / f"{snake_case}.wav"
    theme_path = ACTIVE_THEME_PATH / "sounds" / f"{snake_case}.wav"
    sound_path = theme_path if theme_path.exists() else stock_path
    if not sound_path.exists(): return
    volume = self._params.get_int(key, return_default=True, default=100) / 100.0
    if self._sound_player_process.poll() is not None:
      self._sound_player_process = None
      self._init_sound_player()
    try:
      self._sound_player_process.stdin.write(f"{sound_path}|{volume}\n".encode())
      self._sound_player_process.stdin.flush()
    except: pass
