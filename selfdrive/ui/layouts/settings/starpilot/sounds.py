from __future__ import annotations
from dataclasses import replace
import subprocess
from pathlib import Path

import pyray as rl

from openpilot.common.basedir import BASEDIR
from openpilot.starpilot.common.starpilot_variables import ACTIVE_THEME_PATH
from openpilot.system.ui.lib.application import gui_app, FontWeight, MouseEvent, MousePos
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import Widget, DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.widgets.label import gui_label
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AETHER_LIST_METRICS,
  COMPACT_PANEL_METRICS,
  AdjustorTogglesPanelView,
  AetherAdjustorRow,
  AetherListColors,
  PanelManagerView,
  SPACING,
  TileGrid,
  TOGGLE_MIN_HEIGHT,
  TOGGLE_ROW_HEIGHT,
  DEFAULT_PANEL_STYLE,
  point_hits,
  draw_list_group_shell,
  draw_settings_panel_header,
  AetherSliderDialog,
  SECTION_GAP,
  GROUP_HEADER_HEIGHT,
  GROUP_HEADER_GAP,
  GROUP_HEADER_LINE_GAP,
  GROUP_HEADER_TOTAL_HEIGHT,
  GROUP_TOP_INSET,
  draw_group_header,
)

PANEL_STYLE = DEFAULT_PANEL_STYLE
SOUNDS_PANEL_METRICS = replace(
  COMPACT_PANEL_METRICS,
  header_height=0,
)



class SoundsManagerView(AdjustorTogglesPanelView):
  METRICS = SOUNDS_PANEL_METRICS

  def __init__(self, controller: StarPilotSoundsLayout):
    super().__init__()
    self._controller = controller
    self._reset_rect = rl.Rectangle(0, 0, 0, 0)

    self._tile_grid_h = 0.0

    self._init_adjustors()
    self._init_toggles()

  def _init_toggles(self):
    if self.PANEL_STYLE.toggle_row_mode:
      self._toggle_grid = TileGrid(columns=1, padding=SPACING.md, min_tile_height=TOGGLE_MIN_HEIGHT)
    else:
      self._toggle_grid = TileGrid(columns=2, padding=12, min_tile_height=130.0)
    self.register_page_grid(self._toggle_grid)

    toggle_defs = []
    for key in self._controller.CUSTOM_ALERTS_KEYS:
      info = self._controller.ALERT_INFO[key]
      toggle_defs.append({
        "title": tr(info["title"]),
        "subtitle": tr(info.get("subtitle", "")),
        "get_state": lambda k=key: self._controller._params.get_bool(k),
        "set_state": lambda state, k=key: self._controller._params.put_bool(k, state),
        "is_enabled": info.get("is_enabled"),
        "disabled_label": tr(info.get("disabled_label", "")) if info.get("disabled_label") else "",
      })

    page_size = self._compute_page_size(TOGGLE_ROW_HEIGHT)
    self._set_toggle_pages([toggle_defs[i:i+page_size] for i in range(0, len(toggle_defs), page_size)])

  def _init_adjustors(self):
    for key in self._controller.VOLUME_KEYS:
      info = self._controller.VOLUME_INFO[key]

      adjustor = AetherAdjustorRow(
        tr(info["title"]),
        tr(info["subtitle"]),
        float(info["min"]), 101.0, 1.0,
        get_value=lambda k=key: float(self._controller._params.get_int(k, return_default=True, default=101)),
        on_change=lambda _v: None,
        on_commit=None,
        unit="%",
        labels={0.0: tr("Muted"), 101.0: tr("Auto")},
        presets=[p for p in [0, 25, 50, 75, 101] if p >= info["min"]],
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
        min_val=float(min_v),
        max_val=101.0,
        step=1.0,
        current_val=current_val,
        on_close=on_close,
        presets=[float(p) for p in [0, 25, 50, 75, 101] if p >= min_v],
        unit="%",
        labels={0.0: tr("Muted"), 101.0: tr("Auto")},
        color=PANEL_STYLE.accent,
        on_change=on_change,
      )
    )

  def _target_at(self, mouse_pos: MousePos) -> str | None:
    if point_hits(mouse_pos, self._reset_rect, None, pad_x=6, pad_y=0):
      return "action:restore_defaults"
    return None

  def _activate_target(self, target: str):
    if target == "action:restore_defaults":
      def on_result(result: DialogResult):
        if result == DialogResult.CONFIRM:
          self._controller._restore_defaults()

      gui_app.push_widget(ConfirmDialog(
        tr("Reset all sound volumes, cooldown, and custom alerts to their defaults?"),
        tr("Reset All"),
        callback=on_result,
      ))

  def _measure_content_height(self, content_width: float) -> float:
    col_width = (content_width - SECTION_GAP) / 2

    for key in self._controller.VOLUME_KEYS:
      self._adjustor_rows[key].custom_row_height = None
    self._adjustor_rows[self._controller.COOLDOWN_KEY].custom_row_height = None

    vol_overhead = GROUP_TOP_INSET + 28  # top pad + "Reset All" label

    available_h = max(72.0, (self._scroll_rect.height if self._scroll_rect else 0.0) - 6.0)
    rows_available = max(72.0 * (len(self._controller.VOLUME_KEYS) + 1), available_h - vol_overhead)
    ROW_HEIGHT = rows_available / (len(self._controller.VOLUME_KEYS) + 1)
    for key in self._controller.VOLUME_KEYS:
      self._adjustor_rows[key].custom_row_height = ROW_HEIGHT
    self._adjustor_rows[self._controller.COOLDOWN_KEY].custom_row_height = ROW_HEIGHT

    left_content_h = (len(self._controller.VOLUME_KEYS) + 1) * ROW_HEIGHT + vol_overhead
    tiles_needed_h = self.measure_page_grid_height(self._toggle_grid, col_width - 24) + 24 + GROUP_TOP_INSET + GROUP_HEADER_TOTAL_HEIGHT
    max_content_h = max(left_content_h, tiles_needed_h)

    self._left_container_h = max_content_h
    self._tiles_container_h = max_content_h

    return self._compute_two_column_height(max_content_h)

  def _draw_header(self, rect: rl.Rectangle):
    pass

  def _draw_scroll_content(self, rect: rl.Rectangle, content_width: float):
    y = rect.y + self._scroll_offset
    col_width = (content_width - SECTION_GAP) / 2

    self._draw_volume_column(y, rect.x, col_width)
    self._draw_utility_column(y, rect.x + col_width + SECTION_GAP, col_width)

  def _draw_volume_column(self, y: float, x: float, width: float):
    all_keys = self._controller.VOLUME_KEYS + [self._controller.COOLDOWN_KEY]

    draw_list_group_shell(
      rl.Rectangle(x, y, width, self._left_container_h),
      style=PANEL_STYLE
    )

    current_y = y + GROUP_TOP_INSET

    label_rect = rl.Rectangle(x + 24, current_y - 4, width - 48, 28)
    gui_label(label_rect, tr("Reset All"), 28, AetherListColors.SUBTEXT, FontWeight.MEDIUM,
              alignment=rl.GuiTextAlignment.TEXT_ALIGN_RIGHT)
    reset_width = min(240.0, label_rect.width)
    self._reset_rect = rl.Rectangle(label_rect.x + label_rect.width - reset_width,
                                    current_y - GROUP_TOP_INSET, reset_width, GROUP_TOP_INSET + label_rect.height)
    self._interactive_rects["action:restore_defaults"] = self._reset_rect
    current_y += 28
    for index, key in enumerate(all_keys):
      adjustor = self._adjustor_rows[key]
      row_h = adjustor.measure_height(width)
      row_rect = rl.Rectangle(x, current_y, width, row_h)
      adjustor.set_is_last(index == len(all_keys) - 1)
      adjustor.set_parent_rect(self._scroll_rect)
      adjustor.render(row_rect)
      current_y += row_h

  def _draw_utility_column(self, y: float, x: float, width: float):
    draw_list_group_shell(rl.Rectangle(x, y, width, self._tiles_container_h), style=PANEL_STYLE)
    header_y = draw_group_header(x + 24, y + GROUP_TOP_INSET, width - 48, tr("Alerts"))
    avail_h = self._tiles_container_h - (header_y - y)
    self._render_page_grid(self._toggle_grid, rl.Rectangle(x + 12, header_y, width - 24, max(0.0, avail_h - 12)))


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
    "LoudBlindspotAlertWhenDisengaged",
    "SpeedLimitChangedAlert",
  ]

  COOLDOWN_INFO = {
    "title": tr_noop("Switchback Cooldown"),
    "subtitle": "",
    "min": 0,
    "max": 30,
  }
  VOLUME_INFO = {
    "WarningImmediateVolume": {"title": tr_noop("Immediate Warning"), "subtitle": "", "min": 25},
    "WarningSoftVolume": {"title": tr_noop("Soft Warning"), "subtitle": "", "min": 25},
    "RefuseVolume": {"title": tr_noop("Engagement Refused"), "subtitle": "", "min": 0},
    "PromptDistractedVolume": {"title": tr_noop("Distracted Driver"), "subtitle": "", "min": 0},
    "EngageVolume": {"title": tr_noop("Engagement Chime"), "subtitle": "", "min": 0},
    "DisengageVolume": {"title": tr_noop("Disengagement Alert"), "subtitle": "", "min": 0},
    "PromptVolume": {"title": tr_noop("General Prompt"), "subtitle": "", "min": 0},
    "BelowSteerSpeedVolume": {"title": tr_noop("Low Speed Alert"), "subtitle": "", "min": 0},
  }

  _sound_player_process = None

  def __init__(self):
    super().__init__()
    self._init_sound_player()

    self.ALERT_INFO = {
      "GreenLightAlert": {
        "title": tr_noop("Green Light"),
        "subtitle": "",
      },
      "LeadDepartingAlert": {
        "title": tr_noop("Lead Departure"),
        "subtitle": "",
      },
      "LoudBlindspotAlert": {
        "title": tr_noop("Loud Blindspot"),
        "subtitle": "",
        "is_enabled": lambda: starpilot_state.car_state.hasBSM,
        "disabled_label": tr_noop("Needs BSM")
      },
      "LoudBlindspotAlertWhenDisengaged": {
        "title": tr_noop("Loud While Paused"),
        "subtitle": "",
        "is_enabled": lambda: starpilot_state.car_state.hasBSM,
        "disabled_label": tr_noop("Needs BSM")
      },
      "SpeedLimitChangedAlert": {
        "title": tr_noop("Speed Limit"),
        "subtitle": "",
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
    except (BrokenPipeError, OSError): pass
