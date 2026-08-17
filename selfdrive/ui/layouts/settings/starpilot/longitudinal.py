from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Callable

import pyray as rl

from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.system.ui.lib.application import FontWeight, MouseEvent, MousePos, gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.widgets.keyboard import Keyboard
from openpilot.system.ui.widgets.label import gui_label
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog

from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage

from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AETHER_LIST_METRICS,
  AetherListColors,
  COMPACT_PANEL_METRICS,
  AdjustorTogglesPanelView,
  AetherAdjustorRow,
  AetherSegmentedControl,
  AetherSliderDialog,
  DEFAULT_PANEL_STYLE,
  PanelManagerView,
  ParentToggle,
  SettingRow,
  SettingSection,
  AetherSettingsView,
  CardHubManagerView,
  TileGrid,
  HubTile,
  TOGGLE_MIN_HEIGHT,
  TOGGLE_ROW_HEIGHT,
  RowToggleTile,
  ToggleTile,
  SPACING,
  draw_section_header,
  draw_list_group_shell,
  SECTION_GAP,
  SECTION_HEADER_HEIGHT,
  SECTION_HEADER_GAP,
  hex_to_color,
)

from openpilot.starpilot.common.accel_profile import (
  ACCELERATION_PROFILES,
  DECELERATION_PROFILES,
  normalize_acceleration_profile,
  normalize_deceleration_profile,
)
from openpilot.starpilot.common.experimental_state import sync_persist_experimental_state, sync_persist_chill_state
from openpilot.common.constants import CV


PANEL_STYLE = DEFAULT_PANEL_STYLE

ACCELERATION_PROFILE_OPTIONS = [
  (ACCELERATION_PROFILES["STANDARD"], "Standard"),
  (ACCELERATION_PROFILES["ECO"], "Eco"),
  (ACCELERATION_PROFILES["SPORT"], "Sport"),
  (ACCELERATION_PROFILES["SPORT_PLUS"], "Sport+"),
]

DECELERATION_PROFILE_OPTIONS = [
  (DECELERATION_PROFILES["STANDARD"], "Standard"),
  (DECELERATION_PROFILES["ECO"], "Eco"),
  (DECELERATION_PROFILES["SPORT"], "Sport"),
]

SLC_FALLBACK_OPTIONS = [
  (0, "Set Speed"),
  (1, "Experimental Mode"),
  (2, "Previous Limit"),
]

SLC_OVERRIDE_OPTIONS = [
  (0, "None"),
  (1, "Set With Gas Pedal"),
  (2, "Max Set Speed"),
]


# ═══════════════════════════════════════════════════════════════
# AdaptiveSpeedView — nested panel with two adaptive speed tiles
# ═══════════════════════════════════════════════════════════════

class AdaptiveSpeedView(CardHubManagerView):
  def __init__(self, controller):
    super().__init__(controller, [], columns=2,
                     header_title=tr_noop("Adaptive Speed Controls"))

  def _build_cards(self):
    return [
      {
        "title": tr("Conditional Drive Mode"),
        "desc": tr("Configure automated switching between Experimental and Chill Modes based on set conditions."),
        "icon": "steering",
        "on_click": lambda: self._controller._navigate_to("ce"),
      },
      {
        "title": tr("Curve Speed Controller"),
        "desc": tr("Configure speed control on curves and reset collected calibration data."),
        "icon": "navigate",
        "on_click": lambda: self._controller._navigate_to("csc"),
      },
    ]


# ═══════════════════════════════════════════════════════════════
# LongitudinalManagerView — 7-card category hub
# ═══════════════════════════════════════════════════════════════

class LongitudinalManagerView(CardHubManagerView):
  def __init__(self, controller, sections, **kwargs):
    super().__init__(controller, sections, **kwargs)

  def _build_cards(self):
    return [
      {
        "title": tr("Longitudinal Tuning"),
        "desc": tr("Configure acceleration profiles, lane changes, and route speed control."),
        "icon": "steering",
        "on_click": lambda: self._controller._navigate_to("tune"),
      },
      {
        "title": tr("Advanced Actuators"),
        "desc": tr("Adjust actuator delay, EV/Truck tuning, and launch/stop speeds/rates."),
        "icon": "vehicle",
        "on_click": lambda: self._controller._navigate_to("advanced"),
      },
      {
        "title": tr("Speed Limit Controller"),
        "desc": tr("Manage auto speed matching, confirmation, offsets, and source priority."),
        "icon": "navigate",
        "on_click": lambda: self._controller._navigate_to("slc"),
      },
      {
        "title": tr("Vision Speed Limits"),
        "desc": tr("Detect and display speed-limit signs without enabling Speed Limit Controller."),
        "icon": "road",
        "on_click": lambda: self._controller._navigate_to("vision_speed_limits"),
      },
      {
        "title": tr("Adaptive Speed Controls"),
        "desc": tr("Configure Curve Speed Controller and Conditional Experimental Mode triggers."),
        "icon": "display",
        "on_click": lambda: self._controller._navigate_to("adaptive_speed"),
      },
      {
        "title": tr("Driving Personalities"),
        "desc": tr("Customize follow distance and jerk/response metrics for each personality profile."),
        "icon": "system",
        "on_click": lambda: self._controller._navigate_to("personality"),
      },
      {
        "title": tr("Quality of Life"),
        "desc": tr("Configure cruise intervals, standstill behaviors, gear mapping, and weather presets."),
        "icon": "sound",
        "on_click": lambda: self._controller._navigate_to("daily"),
      },
    ]


class ConditionalDriveModeView(AdjustorTogglesPanelView):
  METRICS = COMPACT_PANEL_METRICS
  TAB_HEIGHT = 98
  TAB_BOTTOM_GAP = 26

  def __init__(self, controller: StarPilotLongitudinalLayout):
    super().__init__()
    self._header_title = tr("Conditional Drive Mode")
    self._controller = controller

    self._init_segmented_control()
    self._init_adjustors()
    self._init_toggles()

  def _init_segmented_control(self):
    self._drive_mode_control = self._child(
      AetherSegmentedControl(
        [tr("OFF"), tr("Experimental"), tr("Chill")],
        self._get_drive_mode_index,
        self._on_drive_mode_change,
        style=PANEL_STYLE,
        suppress_background=True,
      )
    )

  def _get_drive_mode_index(self):
    if self._controller._params.get_bool("ConditionalExperimental"):
      return 1
    elif self._controller._params.get_bool("ConditionalChill"):
      return 2
    return 0

  def _on_drive_mode_change(self, idx):
    if idx == 0:
      self._controller._params.put_bool("ConditionalExperimental", False)
      self._controller._params.put_bool("ConditionalChill", False)
    elif idx == 1:
      self._controller._params.put_bool("ConditionalExperimental", True)
      self._controller._params.put_bool("ConditionalChill", False)
    elif idx == 2:
      self._controller._params.put_bool("ConditionalExperimental", False)
      self._controller._params.put_bool("ConditionalChill", True)
    self._update_pagination()

  def _init_toggles(self):
    if PANEL_STYLE.toggle_row_mode:
      self._toggle_grid = TileGrid(columns=1, padding=12, min_tile_height=TOGGLE_MIN_HEIGHT)
    else:
      self._toggle_grid = TileGrid(columns=2, padding=12, min_tile_height=130.0)
    self._child(self._toggle_grid)
    self.register_page_grid(self._toggle_grid)

    cem_defs = [
      {"title": tr("Curves"), "subtitle": tr("Switch to Experimental Mode on open-road curves."), "get_state": lambda: self._controller._params.get_bool("CECurves"), "set_state": lambda v: self._controller._params.put_bool("CECurves", v)},
      {"title": tr("Curves w/ Lead"), "subtitle": tr("Switch on curves even when following a lead."), "get_state": lambda: self._controller._params.get_bool("CECurvesLead"), "set_state": lambda v: self._controller._params.put_bool("CECurvesLead", v), "is_enabled": lambda: self._controller._params.get_bool("CECurves"), "disabled_label": tr("Turn on Curves first")},
      {"title": tr("Stop Lights/Signs"), "subtitle": tr("Switch when openpilot detects a stop."), "get_state": lambda: self._controller._params.get_bool("CEStopLights"), "set_state": lambda v: self._controller._params.put_bool("CEStopLights", v)},
      {"title": tr("Lead Ahead"), "subtitle": tr("Switch when a slower/stopped vehicle is ahead."), "get_state": lambda: self._controller._params.get_bool("CELead"), "set_state": lambda v: self._controller._params.put_bool("CELead", v)},
      {"title": tr("Slower Lead"), "subtitle": tr("Switch specifically for slower leads."), "get_state": lambda: self._controller._params.get_bool("CESlowerLead"), "set_state": lambda v: self._controller._params.put_bool("CESlowerLead", v), "is_enabled": lambda: self._controller._params.get_bool("CELead"), "disabled_label": tr("Turn on Lead first")},
      {"title": tr("Stopped Lead"), "subtitle": tr("Switch specifically for stopped leads."), "get_state": lambda: self._controller._params.get_bool("CEStoppedLead"), "set_state": lambda v: self._controller._params.put_bool("CEStoppedLead", v), "is_enabled": lambda: self._controller._params.get_bool("CELead"), "disabled_label": tr("Turn on Lead first")},
      {"title": tr("Signal Lane Detect"), "subtitle": tr("Don't trigger on turn signal if lines are clear."), "get_state": lambda: self._controller._params.get_bool("CESignalLaneDetection"), "set_state": lambda v: self._controller._params.put_bool("CESignalLaneDetection", v), "is_enabled": lambda: self._controller._params.get_int("CESignalSpeed") > 0, "disabled_label": tr("Needs Turn Signal speed > 0")},
      {"title": tr("Status Widget"), "subtitle": tr("Show condition trigger on the drive screen."), "get_state": lambda: self._controller._params.get_bool("ShowCEMStatus"), "set_state": lambda v: self._controller._params.put_bool("ShowCEMStatus", v)},
      {"title": tr("Persist Exp State"), "subtitle": tr("Keep manual Experimental override through reboots."), "get_state": lambda: self._controller._params.get_bool("PersistExperimentalState"), "set_state": self._controller._set_persist_experimental_state},
    ]

    ccm_defs = [
      {"title": tr("Stable Lead Ahead"), "subtitle": tr("Switch to Chill Mode when following a steady lead."), "get_state": lambda: self._controller._params.get_bool("CCMLead"), "set_state": lambda v: self._controller._params.put_bool("CCMLead", v)},
      {"title": tr("Launch Assist"), "subtitle": tr("Temporarily switch to Chill from a stop."), "get_state": lambda: self._controller._params.get_bool("CCMLaunchAssist"), "set_state": lambda v: self._controller._params.put_bool("CCMLaunchAssist", v)},
      {"title": tr("Status Widget"), "subtitle": tr("Show condition trigger on the drive screen."), "get_state": lambda: self._controller._params.get_bool("ShowCCMStatus"), "set_state": lambda v: self._controller._params.put_bool("ShowCCMStatus", v)},
      {"title": tr("Persist Chill State"), "subtitle": tr("Keep manual Chill override through reboots."), "get_state": lambda: self._controller._params.get_bool("PersistChillState"), "set_state": self._controller._set_persist_chill_state},
    ]

    self._cem_toggle_defs = cem_defs
    self._ccm_toggle_defs = ccm_defs

    self._update_pagination()

  def _update_pagination(self):
    mode = self._get_drive_mode_index()
    page_size = self._compute_page_size(TOGGLE_ROW_HEIGHT)
    if mode == 1:
      pages = [self._cem_toggle_defs[i:i+page_size] for i in range(0, len(self._cem_toggle_defs), page_size)]
      self._set_toggle_pages(pages)
    elif mode == 2:
      pages = [self._ccm_toggle_defs[i:i+page_size] for i in range(0, len(self._ccm_toggle_defs), page_size)]
      self._set_toggle_pages(pages)
    else:
      self._set_toggle_pages([])

  def _make_toggle_tile(self, info: dict) -> ToggleTile:
    cls = RowToggleTile if PANEL_STYLE.toggle_row_mode else ToggleTile
    kwargs = {
      "title": info["title"],
      "desc": info.get("subtitle", ""),
      "get_state": info["get_state"],
      "set_state": info["set_state"],
      "bg_color": PANEL_STYLE.accent
    }
    if "is_enabled" in info:
      kwargs["is_enabled"] = info["is_enabled"]
    if "disabled_label" in info:
      kwargs["disabled_label"] = info["disabled_label"]
      
    return cls(**kwargs)

  def _init_adjustors(self):
    speed_unit = self._controller._speed_unit()
    is_metric = self._controller._is_metric()
    max_speed = 150.0 if is_metric else 100.0

    specs = {
      "CESpeed": {"title": tr("Below Speed"), "subtitle": "", "min": 0, "max": max_speed, "step": 1.0, "unit": speed_unit, "presets": [0, 20, 35, 55, 75], "labels": {}, "get": lambda: float(self._controller._params.get_int("CESpeed"))},
      "CESpeedLead": {"title": tr("Speed w/ Lead"), "subtitle": "", "min": 0, "max": max_speed, "step": 1.0, "unit": speed_unit, "presets": [0, 20, 35, 55, 75], "labels": {}, "get": lambda: float(self._controller._params.get_int("CESpeedLead"))},
      "CESignalSpeed": {"title": tr("Turn Signal Below"), "subtitle": "", "min": 0, "max": max_speed, "step": 1.0, "unit": speed_unit, "presets": [0, 20, 35, 55, 75], "labels": {0.0: tr("Off")}, "get": lambda: float(self._controller._params.get_int("CESignalSpeed"))},
      "CEModelStopTime": {"title": tr("Predicted Stop In"), "subtitle": "", "min": 0, "max": 10.0, "step": 0.1, "unit": "s", "presets": [0, 3, 5, 7.7, 10], "labels": {0.0: tr("Off")}, "get": lambda: float(self._controller._params.get_float("CEModelStopTime"))},
      "CCMSpeed": {"title": tr("Above Speed"), "subtitle": "", "min": 0, "max": max_speed, "step": 1.0, "unit": speed_unit, "presets": [0, 35, 55, 65, 80], "labels": {}, "get": lambda: float(self._controller._params.get_int("CCMSpeed"))},
      "CCMSpeedLead": {"title": tr("Speed w/ Lead"), "subtitle": "", "min": 0, "max": max_speed, "step": 1.0, "unit": speed_unit, "presets": [0, 35, 55, 65, 80], "labels": {}, "get": lambda: float(self._controller._params.get_int("CCMSpeedLead"))},
      "CCMSetSpeedMargin": {"title": tr("Set Speed Margin"), "subtitle": "", "min": 0, "max": 30.0 if is_metric else 15.0, "step": 1.0, "unit": speed_unit, "presets": [0, 5, 10, 15], "labels": {}, "get": lambda: float(self._controller._params.get_int("CCMSetSpeedMargin"))},
    }

    self._cem_keys = ["CESpeed", "CESpeedLead", "CESignalSpeed", "CEModelStopTime"]
    self._ccm_keys = ["CCMSpeed", "CCMSpeedLead", "CCMSetSpeedMargin"]

    for key, spec in specs.items():
      adjustor = self._child(AetherAdjustorRow(
        spec["title"], spec["subtitle"], spec["min"], spec["max"], spec["step"],
        get_value=spec["get"],
        on_change=lambda _v: None,
        on_commit=None,
        unit=spec["unit"],
        labels=spec["labels"],
        presets=spec["presets"],
        is_active=lambda: False,
        set_active=lambda active, k=key: self._show_slider(k) if active else None,
        style=PANEL_STYLE, color=PANEL_STYLE.accent
      ))
      adjustor.set_touch_valid_callback(lambda: self._scroll_panel.is_touch_valid())
      self._adjustor_rows[key] = adjustor

  def _show_slider(self, key: str):
    is_metric = self._controller._is_metric()
    speed_unit = self._controller._speed_unit()
    max_speed = 150.0 if is_metric else 100.0

    specs = {
      "CESpeed": {"title": tr("Below Speed"), "min": 0, "max": max_speed, "unit": speed_unit, "labels": {}, "presets": [0, 20, 35, 55, 75]},
      "CESpeedLead": {"title": tr("Speed w/ Lead"), "min": 0, "max": max_speed, "unit": speed_unit, "labels": {}, "presets": [0, 20, 35, 55, 75]},
      "CESignalSpeed": {"title": tr("Turn Signal Below"), "min": 0, "max": max_speed, "unit": speed_unit, "labels": {0.0: tr("Off")}, "presets": [0, 20, 35, 55, 75]},
      "CEModelStopTime": {"title": tr("Predicted Stop In"), "min": 0, "max": 10.0, "unit": "s", "labels": {0.0: tr("Off")}, "presets": [0, 3, 5, 7.7, 10]},
      "CCMSpeed": {"title": tr("Above Speed"), "min": 0, "max": max_speed, "unit": speed_unit, "labels": {}, "presets": [0, 35, 55, 65, 80]},
      "CCMSpeedLead": {"title": tr("Speed w/ Lead"), "min": 0, "max": max_speed, "unit": speed_unit, "labels": {}, "presets": [0, 35, 55, 65, 80]},
      "CCMSetSpeedMargin": {"title": tr("Set Speed Margin"), "min": 0, "max": 30.0 if is_metric else 15.0, "unit": speed_unit, "labels": {}, "presets": [0, 5, 10, 15]},
      "PulseGlideSpeedDelta": {"title": tr("Pulse and Glide Delta"), "min": 0.5, "max": 30.0 if is_metric else 15.0, "unit": speed_unit, "labels": {}, "presets": [1, 3, 5, 10]},
    }
    
    spec = specs[key]
    is_float = key in ("CEModelStopTime", "PulseGlideSpeedDelta")
    original_val = float(self._controller._params.get_float(key) if is_float else self._controller._params.get_int(key))

    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        if is_float:
          self._controller._params.put_float(key, float(val))
        else:
          self._controller._params.put_int(key, int(val))

    gui_app.push_widget(AetherSliderDialog(
      title=spec["title"],
      min_val=float(spec["min"]), max_val=float(spec["max"]), step=0.1 if key == "CEModelStopTime" else (0.5 if key == "PulseGlideSpeedDelta" else 1.0),
      current_val=original_val,
      on_close=on_close, presets=[float(p) for p in spec["presets"]],
      unit=spec["unit"], labels=spec["labels"], color=PANEL_STYLE.accent
    ))

  def _draw_header(self, rect: rl.Rectangle):
    pass

  def _measure_content_height(self, content_width: float) -> float:
    mode = self._get_drive_mode_index()
    if mode == 0:
      return self.TAB_HEIGHT + self.TAB_BOTTOM_GAP
    
    keys = self._cem_keys if mode == 1 else self._ccm_keys
    grid = self._toggle_grid
    
    col_width = (content_width - SECTION_GAP) / 2 if self._uses_two_columns(content_width) else content_width

    for key in keys:
      self._adjustor_rows[key].custom_row_height = None

    default_adjustor_h = float(AETHER_LIST_METRICS.adjustor_row_height)
    left_h = len(keys) * default_adjustor_h + 16.0
    
    num_tiles = 4 if self._has_pagination else len(grid.tiles)
    if PANEL_STYLE.toggle_row_mode:
      rows = num_tiles
      tile_h = TOGGLE_ROW_HEIGHT
    else:
      rows = (num_tiles + 1) // 2 if self._uses_two_columns(content_width) else num_tiles
      tile_h = grid.min_tile_height
    
    pagination_space = 32.0 if self._has_pagination else 0.0
    tiles_h = rows * tile_h + (rows - 1) * grid.gap + grid.gap * 2 + pagination_space

    right_h = tiles_h

    banner_overhead = 52.0
    if self._uses_two_columns(content_width):
      max_natural_h = max(left_h, right_h)
      section_overhead = banner_overhead + SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
      
      if self._scroll_rect:
        available_h = self._scroll_rect.height - section_overhead - self.TAB_HEIGHT - self.TAB_BOTTOM_GAP - 6.0
      else:
        available_h = max_natural_h
        
      max_container_h = available_h
      
      left_row_h = max(95.0, (max_container_h - 16.0) / max(1, len(keys)))
      for key in keys:
        self._adjustor_rows[key].custom_row_height = left_row_h
        
      self._left_container_h = max_container_h
      self._tiles_container_h = max_container_h
      
      return self._compute_two_column_height(section_overhead + max_container_h) + self.TAB_HEIGHT + self.TAB_BOTTOM_GAP
    else:
      self._left_container_h = left_h
      self._tiles_container_h = right_h
      total = banner_overhead + left_h + SECTION_GAP + right_h + SECTION_HEADER_HEIGHT * 2 + SECTION_HEADER_GAP * 2
      return total + self.TAB_HEIGHT + self.TAB_BOTTOM_GAP

  def _draw_scroll_content(self, rect: rl.Rectangle, content_width: float):
    y = rect.y + self._scroll_offset
    
    header_w = content_width
    bar_rect = rl.Rectangle(rect.x, y, header_w, self.TAB_HEIGHT)
    draw_list_group_shell(bar_rect, style=PANEL_STYLE)
    self._drive_mode_control.render(bar_rect)
    
    y += self.TAB_HEIGHT + self.TAB_BOTTOM_GAP
    mode = self._get_drive_mode_index()
    if mode == 0:
      return

    banner_text = tr("Switch to Experimental Mode") if mode == 1 else tr("Switch to Chill Mode")
    banner_rect = rl.Rectangle(rect.x, y, content_width, 40)
    gui_label(banner_rect, banner_text, 40, AetherListColors.HEADER, FontWeight.BOLD, alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
    y += 40 + 12

    keys = self._cem_keys if mode == 1 else self._ccm_keys
    grid = self._toggle_grid
    
    col_width = (content_width - SECTION_GAP) / 2 if self._uses_two_columns(content_width) else content_width

    draw_section_header(rl.Rectangle(rect.x, y, col_width, SECTION_HEADER_HEIGHT), tr("When"), style=PANEL_STYLE, title_size=38, align_center=True)
    if self._uses_two_columns(content_width):
      draw_section_header(rl.Rectangle(rect.x + col_width + SECTION_GAP, y, col_width, SECTION_HEADER_HEIGHT), tr("For"), style=PANEL_STYLE, title_size=38, align_center=True)
    
    y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
    
    self._draw_adjustors(y, rect.x, col_width, keys)

    tg_columns = 1 if PANEL_STYLE.toggle_row_mode else 2
    if self._uses_two_columns(content_width):
      self._draw_two_column_tile_grid(
        grid, rect.x + col_width + SECTION_GAP, y, col_width,
        self._tiles_container_h, title=None, style=PANEL_STYLE,
        columns=tg_columns)
    else:
      y += self._left_container_h + SECTION_GAP
      draw_section_header(rl.Rectangle(rect.x, y, col_width, SECTION_HEADER_HEIGHT), tr("For"), style=PANEL_STYLE, title_size=38, align_center=True)
      y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
      self._draw_two_column_tile_grid(
        grid, rect.x, y, col_width,
        self._tiles_container_h, title=None, style=PANEL_STYLE,
        columns=tg_columns)

  def _draw_adjustors(self, y: float, x: float, width: float, keys: list[str]):
    draw_list_group_shell(rl.Rectangle(x, y, width, self._left_container_h), style=PANEL_STYLE)
    current_y = y + 4
    for index, key in enumerate(keys):
      adjustor = self._adjustor_rows[key]
      row_h = adjustor.measure_height(width)
      row_rect = rl.Rectangle(x, current_y, width, row_h)
      adjustor.set_is_last(index == len(keys) - 1)
      adjustor.set_parent_rect(self._scroll_rect)
      adjustor.render(row_rect)
      current_y += row_h

  def _get_active_elements(self):
    mode = self._get_drive_mode_index()
    elems = [self._drive_mode_control]
    if mode == 1:
      elems += [self._adjustor_rows[k] for k in self._cem_keys]
    elif mode == 2:
      elems += [self._adjustor_rows[k] for k in self._ccm_keys]
    elems.append(self._toggle_grid)
    return elems


# ═══════════════════════════════════════════════════════════════
# StarPilotLongitudinalLayout — controller
# ═══════════════════════════════════════════════════════════════

class StarPilotLongitudinalLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._keyboard = Keyboard(min_text_size=1)
    # Track metric↔imperial transitions so we can rescale speed- and
    # distance-typed params to the new unit when it flips.
    self._last_is_metric: bool | None = None
    self._build_view()
    self._last_is_metric = self._is_metric()

  def _longitudinal_enabled(self) -> bool:
    return self._params.get_bool("LongitudinalTune")

  def _advanced_enabled(self) -> bool:
    return self._params.get_bool("AdvancedLongitudinalTune")

  def _show_stop_tuning_values(self) -> bool:
    return self._advanced_enabled()

  def _make_parent(self, key: str, label: str, subtitle: str = "") -> ParentToggle:
    return ParentToggle(
      label=label,
      subtitle=subtitle,
      get_state=lambda k=key: self._params.get_bool(k),
      set_state=lambda s, k=key: self._params.put_bool(k, s),
    )

  def _build_view(self):
    ol = lambda: starpilot_state.car_state.hasOpenpilotLongitudinal
    ce_on = lambda: self._params.get_bool("ConditionalExperimental")
    cc_on = lambda: self._params.get_bool("ConditionalChill")
    ce_lead = lambda: ce_on() and self._params.get_bool("CELead")
    csc_on = lambda: self._params.get_bool("CurveSpeedController")
    confirmation_on = lambda: self._params.get_bool("SLCConfirmation")
    
    # ── 1. Longitudinal Tuning Rows ──
    self._tune_rows = [
      SettingRow("AccelProfile", "value", tr_noop("Acceleration Profile"),
                 subtitle=tr_noop("Choose how quickly openpilot speeds up."),
                 get_value=self._get_acceleration_profile_label,
                 on_click=self._show_acceleration_profile_selector,
                 visible=self._longitudinal_enabled),
      SettingRow("DecelProfile", "value", tr_noop("Deceleration Profile"),
                 subtitle=tr_noop("Choose how firmly openpilot slows the car down."),
                 get_value=self._get_deceleration_profile_label,
                 on_click=self._show_deceleration_profile_selector,
                 visible=self._longitudinal_enabled),
      SettingRow("HumanLaneChanges", "toggle", tr_noop("Human-Like Lane Changes"),
                 subtitle=tr_noop("Radar-informed behavior during lane changes."),
                 get_state=lambda: self._params.get_bool("HumanLaneChanges"),
                 set_state=lambda s: self._params.put_bool("HumanLaneChanges", s),
                 visible=lambda: self._longitudinal_enabled() and starpilot_state.car_state.hasRadar),
      SettingRow("LeadDetection", "value", tr_noop("Lead Detection Sensitivity"),
                 subtitle=tr_noop("Control how aggressively openpilot detects and reacts to vehicles ahead."),
                 get_value=lambda: f"{self._params.get_int('LeadDetectionThreshold')}%",
                 on_click=lambda: self._show_slider("LeadDetectionThreshold", 25, 50, unit="%"),
                 visible=self._longitudinal_enabled),
      SettingRow("NavLongitudinalAllowed", "toggle", tr_noop("Use Route Speed Control"),
                 subtitle=tr_noop("Allow an active navigation route to reduce cruise speed for upcoming turns, ramps, and roundabouts."),
                 get_state=lambda: self._params.get_bool("NavLongitudinalAllowed"),
                 set_state=lambda s: self._params.put_bool("NavLongitudinalAllowed", s),
                 visible=self._longitudinal_enabled),
    ]

    # ── 2. Advanced Actuators Rows ──
    adv = self._advanced_enabled
    self._advanced_rows = [
      SettingRow("EVTuning", "toggle", tr_noop("EV Tuning"),
                 subtitle=tr_noop("Acceleration tuning for EV and direct-drive vehicles."),
                 get_state=lambda: self._params.get_bool("EVTuning"),
                 set_state=self._set_ev_tuning,
                 visible=adv,
                 enabled=lambda: not self._params.get_bool("TruckTuning"),
                 disabled_label=tr_noop("Truck Active")),
      SettingRow("TruckTuning", "toggle", tr_noop("Truck Tuning"),
                 subtitle=tr_noop("Stronger launch and acceleration for heavier vehicles."),
                 get_state=lambda: self._params.get_bool("TruckTuning"),
                 set_state=self._set_truck_tuning,
                 visible=adv,
                 enabled=lambda: not self._params.get_bool("EVTuning"),
                 disabled_label=tr_noop("EV Active")),
      SettingRow("TrailerLoad", "value", tr_noop("Trailer Load"),
                 subtitle=tr_noop("Loaded trailer weight for tow-aware gas, brake, and conservative lateral assist."),
                 get_value=lambda: f"{self._params.get_int('TrailerLoad')} lb",
                 on_click=lambda: self._show_slider("TrailerLoad", 0, 15000, step=500, unit=" lb"),
                 visible=adv),
      SettingRow("ActuatorDelay", "value", tr_noop("Actuator Delay"),
                 subtitle=tr_noop("Time between command and the vehicle's response."),
                 get_value=lambda: f"{self._params.get_float('LongitudinalActuatorDelay'):.2f}s",
                 on_click=lambda: self._show_slider("LongitudinalActuatorDelay", 0.0, 1.0, step=0.01, unit="s", value_type="float"),
                 visible=adv),
      SettingRow("MaxAccel", "value", tr_noop("Maximum Acceleration"),
                 subtitle=tr_noop("Strongest acceleration openpilot is allowed to command."),
                 get_value=lambda: f"{self._params.get_float('MaxDesiredAcceleration'):.1f}m/s" if self._params.get_float("MaxDesiredAcceleration") is not None else "N/A",
                 on_click=lambda: self._show_slider("MaxDesiredAcceleration", 0.1, 4.0, step=0.1, unit="m/s", value_type="float"),
                 visible=adv),
      SettingRow("StartAccel", "value", tr_noop("Start Acceleration"),
                 subtitle=tr_noop("Extra acceleration when moving away from a stop."),
                 get_value=lambda: f"{self._params.get_float('StartAccel'):.2f}m/s",
                 on_click=lambda: self._show_slider("StartAccel", 0.0, 4.0, step=0.01, unit="m/s", value_type="float"),
                 visible=adv),
      SettingRow("StopAccel", "value", tr_noop("Stop Acceleration"),
                 subtitle=tr_noop("Brake force to hold the vehicle at a complete stop."),
                 get_value=lambda: f"{self._params.get_float('StopAccel'):.2f}m/s",
                 on_click=lambda: self._show_slider("StopAccel", -4.0, 0.0, step=0.01, unit="m/s", value_type="float"),
                 visible=adv),
      SettingRow("StoppingRate", "value", tr_noop("Stopping Rate"),
                 subtitle=tr_noop("How quickly braking ramps up to bring the car to a stop."),
                 get_value=lambda: f"{self._params.get_float('StoppingDecelRate'):.3f}m/s",
                 on_click=lambda: self._show_slider("StoppingDecelRate", 0.001, 1.0, step=0.001, unit="m/s", value_type="float"),
                 visible=self._show_stop_tuning_values),
      SettingRow("StartSpeed", "value", tr_noop("Start Speed"),
                 subtitle=tr_noop("Speed where openpilot exits the stopped state."),
                 get_value=lambda: f"{self._params.get_float('VEgoStarting'):.2f}m/s",
                 on_click=lambda: self._show_slider("VEgoStarting", 0.01, 1.0, step=0.01, unit="m/s", value_type="float"),
                 visible=self._show_stop_tuning_values),
      SettingRow("StopSpeed", "value", tr_noop("Stop Speed"),
                 subtitle=tr_noop("Speed where openpilot considers the vehicle fully stopped."),
                 get_value=lambda: f"{self._params.get_float('VEgoStopping'):.2f}m/s",
                 on_click=lambda: self._show_slider("VEgoStopping", 0.01, 1.0, step=0.01, unit="m/s", value_type="float"),
                 visible=self._show_stop_tuning_values),
    ]

    # ── 3. Speed Limit Controller (SLC) Rows ──
    self._slc_rows = [
      SettingRow("SLCFallback", "value", tr_noop("Fallback Speed"),
                 subtitle="",
                 get_value=lambda: self._profile_label_for_value(self._params.get_int("SLCFallback"), SLC_FALLBACK_OPTIONS),
                 on_click=lambda: self._show_labeled_select("Fallback Speed", "SLCFallback", SLC_FALLBACK_OPTIONS,
                                                            self._params.get_int("SLCFallback"))),
      SettingRow("SLCOverride", "value", tr_noop("Override Speed"),
                 subtitle="",
                 get_value=lambda: self._profile_label_for_value(self._params.get_int("SLCOverride"), SLC_OVERRIDE_OPTIONS),
                 on_click=lambda: self._show_labeled_select("Override Speed", "SLCOverride", SLC_OVERRIDE_OPTIONS,
                                                            self._params.get_int("SLCOverride"))),
      SettingRow("SLCPriority", "value", tr_noop("Source Priority"),
                 subtitle="",
                 get_value=self._get_priority_value,
                 on_click=self._on_priority_clicked),
      SettingRow("SetSpeedLimit", "toggle", tr_noop("Auto Match Speed Limits"),
                 subtitle="",
                 get_state=lambda: self._params.get_bool("SetSpeedLimit"),
                 set_state=lambda s: self._params.put_bool("SetSpeedLimit", s)),
      SettingRow("SLCConfirmation", "toggle", tr_noop("Confirm New Limits"),
                 subtitle="",
                 get_state=lambda: self._params.get_bool("SLCConfirmation"),
                 set_state=lambda s: self._params.put_bool("SLCConfirmation", s)),
      SettingRow("SLCConfirmationLower", "toggle", tr_noop("Confirm Lower"),
                 subtitle="",
                 get_state=lambda: self._params.get_bool("SLCConfirmationLower"),
                 set_state=lambda s: self._params.put_bool("SLCConfirmationLower", s),
                 visible=confirmation_on),
      SettingRow("SLCConfirmationHigher", "toggle", tr_noop("Confirm Higher"),
                 subtitle="",
                 get_state=lambda: self._params.get_bool("SLCConfirmationHigher"),
                 set_state=lambda s: self._params.put_bool("SLCConfirmationHigher", s),
                 visible=confirmation_on),
      SettingRow("SLCLookHigher", "value", tr_noop("Higher Lookahead"),
                 subtitle="",
                 get_value=lambda: f"{self._params.get_int('SLCLookaheadHigher')}s",
                 on_click=lambda: self._show_slider("SLCLookaheadHigher", 0, 30, unit="s")),
      SettingRow("SLCLookLower", "value", tr_noop("Lower Lookahead"),
                 subtitle="",
                 get_value=lambda: f"{self._params.get_int('SLCLookaheadLower')}s",
                 on_click=lambda: self._show_slider("SLCLookaheadLower", 0, 30, unit="s")),
      SettingRow("SLCMapboxFiller", "toggle", tr_noop("Mapbox Fallback"),
                 subtitle="",
                 get_state=lambda: self._params.get_bool("SLCMapboxFiller"),
                 set_state=lambda s: self._params.put_bool("SLCMapboxFiller", s),
                 visible=self._mapbox_available),
      SettingRow("ShowSLCOffset", "toggle", tr_noop("Show SLC Offset"),
                 subtitle="",
                 get_state=lambda: self._params.get_bool("ShowSLCOffset"),
                 set_state=lambda s: self._params.put_bool("ShowSLCOffset", s)),
      SettingRow("SpeedLimitSources", "toggle", tr_noop("Show Sources"),
                 subtitle="",
                 get_state=lambda: self._params.get_bool("SpeedLimitSources"),
                 set_state=lambda s: self._params.put_bool("SpeedLimitSources", s)),
      SettingRow("SLCAbbreviatedSources", "toggle", tr_noop("Abbreviated Sources"),
                 subtitle=tr_noop("Render speed-limit sources as compact text labels (e.g. Dash-45)."),
                 get_state=lambda: self._params.get_bool("SLCAbbreviatedSources"),
                 set_state=lambda s: self._params.put_bool("SLCAbbreviatedSources", s),
                 visible=self._sources_visible),
      SettingRow("SLCActiveSourcesOnly", "toggle", tr_noop("Active Sources Only"),
                 subtitle=tr_noop("Hide source rows that have no current speed limit reading."),
                 get_state=lambda: self._params.get_bool("SLCActiveSourcesOnly"),
                 set_state=lambda s: self._params.put_bool("SLCActiveSourcesOnly", s),
                 visible=self._sources_visible),
      SettingRow("ConfigureOffsets", "value", tr_noop("SLC Offsets"),
                 subtitle=tr_noop("Per-limit speed adjustments for the Speed Limit Controller."),
                 get_value=lambda: tr_noop("Configure"),
                 on_click=self._show_slc_offsets_category),
    ]

    # ── 4. Vision Speed Limits Rows ──
    self._vision_speed_limit_rows = [
      SettingRow("VisionSpeedLimit", "toggle", tr_noop("Vision Detection"),
                 subtitle=tr_noop("Use the road camera to detect and display speed-limit signs, with optional use by Speed Limit Controller."),
                 get_state=lambda: self._params.get_bool("VisionSpeedLimitDetection"),
                 set_state=lambda s: self._params.put_bool("VisionSpeedLimitDetection", s)),
    ]

    # Initialize SLC Offsets rows
    self._slc_offset_rows = []
    for i in range(1, 8):
      key = f"Offset{i}"
      self._slc_offset_rows.append(SettingRow(
        f"Offset{i}", "value", tr_noop(f"Offset {i}"),
        subtitle="",
        get_value=lambda k=key: f"{self._params.get_int(k)}{self._speed_unit()}",
        on_click=lambda k=key: self._show_slider(k, *self._speed_range(), unit=self._speed_unit()),
      ))

    # ── 5. Adaptive Speed Controls Rows (CES + CSC + CCM) ──
    self._curve_speed_controller_rows = [
      SettingRow("CurveSpeedMargin", "value", tr_noop("Curve Speed Margin"),
                 subtitle=tr_noop("How much of your learned cornering comfort to use. Lower slows more for curves; 100% matches how you take them yourself."),
                 get_value=lambda: f"{self._params.get_int('CurveSpeedMargin')}%",
                 on_click=lambda: self._show_slider("CurveSpeedMargin", 70, 100, step=5, unit="%"),
                 visible=csc_on),
      SettingRow("CalibratedLatAccel", "value", tr_noop("Calibrated Lateral Accel"),
                 subtitle=tr_noop("The learned lateral acceleration from collected driving data. Higher values allow faster cornering."),
                 get_value=lambda: f"{self._params.get_float('CalibratedLateralAcceleration'):.2f} m/s",
                 on_click=None,
                 visible=csc_on),
      SettingRow("CalibrationProgress", "value", tr_noop("Calibration Progress"),
                 subtitle=tr_noop("How much curve data has been collected. Normal for the value to stay low."),
                 get_value=lambda: f"{self._params.get_float('CalibrationProgress'):.2f}%",
                 on_click=None,
                 visible=csc_on),
      SettingRow("ResetCurve", "action", tr_noop("Reset Curve Data"),
                 subtitle=tr_noop("Reset collected user data for Curve Speed Controller."),
                 action_text=tr_noop("Reset"),
                 action_danger=True,
                 on_click=self._reset_curve_data,
                 visible=csc_on),
    ]

    # ── 6. Driving Personalities Rows ──
    self._personality_rows = [
      SettingRow("Traffic", "value", tr_noop("Traffic"),
                 subtitle=tr_noop("Configure follow distance, smoothness, and response for traffic conditions."),
                 get_value=lambda: tr_noop("Configure"),
                 on_click=lambda: self._show_personality_profile_category("Traffic")),
      SettingRow("Aggressive", "value", tr_noop("Aggressive"),
                 subtitle=tr_noop("Configure follow distance, smoothness, and response for aggressive driving."),
                 get_value=lambda: tr_noop("Configure"),
                 on_click=lambda: self._show_personality_profile_category("Aggressive")),
      SettingRow("Standard", "value", tr_noop("Standard"),
                 subtitle=tr_noop("Configure follow distance, smoothness, and response for everyday driving."),
                 get_value=lambda: tr_noop("Configure"),
                 on_click=lambda: self._show_personality_profile_category("Standard")),
      SettingRow("Relaxed", "value", tr_noop("Relaxed"),
                 subtitle=tr_noop("Configure follow distance, smoothness, and response for relaxed driving."),
                 get_value=lambda: tr_noop("Configure"),
                 on_click=lambda: self._show_personality_profile_category("Relaxed")),
    ]

    # ── 7. Daily QOL & Weather Rows ──
    self._daily_rows = [
      SettingRow("CustomCruise", "value", tr_noop("Cruise Interval"),
                 subtitle="",
                 get_value=lambda: f"{max(1, self._params.get_int('CustomCruise'))}{self._speed_unit()}",
                 on_click=lambda: self._show_slider("CustomCruise", 1, 150 if self._is_metric() else 99,
                                                    unit=self._speed_unit(),
                                                    current_value=max(1, self._params.get_int("CustomCruise"))),
                 visible=lambda: self._params.get_bool("QOLLongitudinal")),
      SettingRow("CustomCruiseLong", "value", tr_noop("Cruise Long"),
                 subtitle="",
                 get_value=lambda: f"{max(1, self._params.get_int('CustomCruiseLong'))}{self._speed_unit()}",
                 on_click=lambda: self._show_slider("CustomCruiseLong", 1, 150 if self._is_metric() else 99,
                                                    unit=self._speed_unit(),
                                                    current_value=max(1, self._params.get_int("CustomCruiseLong"))),
                 visible=lambda: self._params.get_bool("QOLLongitudinal")),
      SettingRow("ForceStops", "toggle", tr_noop("Force Stops"),
                 subtitle="",
                 get_state=lambda: self._params.get_bool("ForceStops"),
                 set_state=lambda s: self._params.put_bool("ForceStops", s),
                 visible=lambda: self._params.get_bool("QOLLongitudinal")),
      SettingRow("ForceStopDist", "value", tr_noop("Force Stop Offset"),
                 subtitle="",
                 get_value=lambda: f"{self._params.get_int('ForceStopDistanceOffset'):+d} ft",
                 on_click=lambda: self._show_slider("ForceStopDistanceOffset", -20, 20, unit=" ft"),
                 visible=lambda: self._params.get_bool("QOLLongitudinal") and self._params.get_bool("ForceStops")),
      SettingRow("RadarTakeoffs", "toggle", tr_noop("Radar for Takeoffs"),
                 subtitle=tr_noop("Turns on/off using radar data to track leads at standstill, making following/takeoffs more responsive once leads move."),
                 get_state=lambda: self._params.get_bool("RadarTakeoffs"),
                 set_state=lambda s: self._params.put_bool("RadarTakeoffs", s),
                 visible=lambda: self._params.get_bool("QOLLongitudinal") and starpilot_state.car_state.hasRadar),
      SettingRow("ForceStandstill", "toggle", tr_noop("Force Standstill"),
                 subtitle="",
                 get_state=lambda: self._params.get_bool("ForceStandstill"),
                 set_state=lambda s: self._params.put_bool("ForceStandstill", s),
                 visible=lambda: self._params.get_bool("QOLLongitudinal")),
      SettingRow("IncStoppedDist", "value", tr_noop("Stopped Distance"),
                 subtitle="",
                 get_value=lambda: f"{self._params.get_int('IncreasedStoppedDistance')}{self._distance_unit()}",
                 on_click=lambda: self._show_slider("IncreasedStoppedDistance", *self._distance_range(),
                                                    unit=self._distance_unit()),
                 visible=lambda: self._params.get_bool("QOLLongitudinal")),
      SettingRow("SetSpeedOffset", "value", tr_noop("Set Speed Offset"),
                 subtitle="",
                 get_value=lambda: f"+{self._params.get_int('SetSpeedOffset')}{self._speed_unit()}",
                 on_click=lambda: self._show_slider("SetSpeedOffset", 0, 150 if self._is_metric() else 99,
                                                    unit=self._speed_unit()),
                 visible=lambda: self._params.get_bool("QOLLongitudinal")),
      SettingRow("PulseGlideSpeedDelta", "value", tr_noop("Pulse and Glide Delta"),
                 subtitle=tr_noop("Developer-only: coast this far below the current cruise target before accelerating back up."),
                 get_value=lambda: f"{self._params.get_float('PulseGlideSpeedDelta'):.1f}{self._speed_unit()}",
                 on_click=lambda: self._show_slider("PulseGlideSpeedDelta"),
                 visible=lambda: self._params.get_bool("QOLLongitudinal") and self._developer_feature_access()),
      SettingRow("MapGears", "toggle", tr_noop("Map Gears"),
                 subtitle="",
                 get_state=lambda: self._params.get_bool("MapGears"),
                 set_state=lambda s: self._params.put_bool("MapGears", s),
                 visible=lambda: self._params.get_bool("QOLLongitudinal")),
      SettingRow("MapAccel", "toggle", tr_noop("Map Acceleration"),
                 subtitle="",
                 get_state=lambda: self._params.get_bool("MapAcceleration"),
                 set_state=lambda s: self._params.put_bool("MapAcceleration", s),
                 visible=lambda: self._params.get_bool("QOLLongitudinal") and self._params.get_bool("MapGears")),
      SettingRow("MapDecel", "toggle", tr_noop("Map Deceleration"),
                 subtitle="",
                 get_state=lambda: self._params.get_bool("MapDeceleration"),
                 set_state=lambda s: self._params.put_bool("MapDeceleration", s),
                 visible=lambda: self._params.get_bool("QOLLongitudinal") and self._params.get_bool("MapGears")),
      SettingRow("WeatherPresets", "toggle", tr_noop("Weather Condition Offsets"),
                 subtitle=tr_noop("Automatically adjust driving behavior based on real-time weather."),
                 get_state=lambda: self._params.get_bool("WeatherPresets"),
                 set_state=lambda s: self._params.put_bool("WeatherPresets", s),
                 visible=lambda: self._params.get_bool("QOLLongitudinal")),
      SettingRow("LowVisibility", "value", tr_noop("Low Visibility"),
                 subtitle=tr_noop("Adjust parameters for fog, mist, and poor visibility conditions."),
                 get_value=lambda: tr_noop("Configure"),
                 on_click=lambda: self._show_weather_offsets_category("LowVisibility", tr_noop("Low Visibility")),
                 visible=lambda: self._params.get_bool("QOLLongitudinal") and self._params.get_bool("WeatherPresets")),
      SettingRow("Rain", "value", tr_noop("Rain"),
                 subtitle=tr_noop("Adjust parameters for light to moderate rain."),
                 get_value=lambda: tr_noop("Configure"),
                 on_click=lambda: self._show_weather_offsets_category("Rain", tr_noop("Rain")),
                 visible=lambda: self._params.get_bool("QOLLongitudinal") and self._params.get_bool("WeatherPresets")),
      SettingRow("RainStorm", "value", tr_noop("Rainstorms"),
                 subtitle=tr_noop("Adjust parameters for heavy rain and storms."),
                 get_value=lambda: tr_noop("Configure"),
                 on_click=lambda: self._show_weather_offsets_category("RainStorm", tr_noop("Rainstorms")),
                 visible=lambda: self._params.get_bool("QOLLongitudinal") and self._params.get_bool("WeatherPresets")),
      SettingRow("Snow", "value", tr_noop("Snow"),
                 subtitle=tr_noop("Adjust parameters for snowy and icy conditions."),
                 get_value=lambda: tr_noop("Configure"),
                 on_click=lambda: self._show_weather_offsets_category("Snow", tr_noop("Snow")),
                 visible=lambda: self._params.get_bool("QOLLongitudinal") and self._params.get_bool("WeatherPresets")),
      SettingRow("WeatherKey", "action", tr_noop("Set Weather Key"),
                 subtitle=tr_noop("Enter or remove your weather data API key."),
                 action_text=tr_noop("Set Key"),
                 on_click=self._set_weather_key,
                 visible=lambda: self._params.get_bool("QOLLongitudinal")),
    ]

    self._manager_view = LongitudinalManagerView(
      self, [],
      header_title=tr_noop("Gas/Brake"),
      header_subtitle=tr_noop("Fine-tune acceleration, braking, and driving behavior."),
      panel_style=PANEL_STYLE,
    )

    pt_tune = self._make_parent("LongitudinalTune", "Longitudinal Tuning",
      "Acceleration and braking control changes to fine-tune how openpilot drives.")
    pt_advanced = self._make_parent("AdvancedLongitudinalTune", "Advanced Longitudinal Tuning",
      "Advanced acceleration and braking changes for refining launch, stopping, and actuator response.")
    pt_personality = self._make_parent("CustomPersonalities", "Driving Personalities")
    pt_daily = self._make_parent("QOLLongitudinal", "Quality of Life")
    pt_slc = self._make_parent("SpeedLimitController", "Speed Limit Controller",
      "Limit the car's maximum speed to the current speed limit.")
    pt_vision_speed_limits = self._make_parent("VisionSpeedLimitDetection", "Vision Speed Limits",
      "Detect and display speed-limit signs without enabling the Speed Limit Controller.")
    pt_csc = self._make_parent("CurveSpeedController", "Curve Speed Controller",
      "Configure speed control on curves and reset collected calibration data.")

    self._sub_panels["ce"] = ConditionalDriveModeView(self)


    self._sub_panels["csc"] = AetherSettingsView(
      self,
      [SettingSection(tr("Curve Speed Controller"), self._curve_speed_controller_rows)],
      header_title=tr("Curve Speed Controller"),
      header_subtitle=tr("Configure speed control on curves and reset collected calibration data."),
      parent_toggle=pt_csc,
      panel_style=PANEL_STYLE,
    )

    self._sub_panels["adaptive_speed"] = AdaptiveSpeedView(self)

    # Register subpanels for Level 2 slide transitions
    self._sub_panels["tune"] = AetherSettingsView(
      self,
      [SettingSection(title="", rows=self._tune_rows)],
      header_title=tr_noop("Longitudinal Tuning"),
      header_subtitle=tr_noop("Configure acceleration profiles, lane changes, and route speed control."),
      parent_toggle=pt_tune,
      panel_style=PANEL_STYLE,
    )
    self._sub_panels["advanced"] = AetherSettingsView(
      self,
      [SettingSection(title="", rows=self._advanced_rows)],
      header_title=tr_noop("Advanced Actuators"),
      header_subtitle=tr_noop("Adjust actuator delay, EV/Truck tuning, and launch/stop speeds/rates."),
      parent_toggle=pt_advanced,
      panel_style=PANEL_STYLE,
    )
    self._sub_panels["slc"] = AetherSettingsView(
      self,
      [SettingSection(title="", rows=self._slc_rows)],
      header_title=tr_noop("Speed Limit Controller"),
      header_subtitle=tr_noop("Manage auto speed matching, confirmation, offsets, and source priority."),
      parent_toggle=pt_slc,
      panel_style=PANEL_STYLE,
    )
    self._sub_panels["vision_speed_limits"] = AetherSettingsView(
      self,
      [SettingSection(title="", rows=self._vision_speed_limit_rows)],
      header_title=tr_noop("Vision Speed Limits"),
      header_subtitle=tr_noop("Detect and display speed-limit signs without enabling the Speed Limit Controller."),
      parent_toggle=pt_vision_speed_limits,
      panel_style=PANEL_STYLE,
    )
    self._sub_panels["personality"] = AetherSettingsView(
      self,
      [SettingSection(title="", rows=self._personality_rows)],
      header_title=tr_noop("Driving Personalities"),
      header_subtitle=tr_noop("Customize follow distance and jerk/response metrics for each personality profile."),
      parent_toggle=pt_personality,
      panel_style=PANEL_STYLE,
    )
    self._sub_panels["daily"] = AetherSettingsView(
      self,
      [SettingSection(title="", rows=self._daily_rows)],
      header_title=tr_noop("Daily QOL & Weather"),
      header_subtitle=tr_noop("Configure cruise intervals, standstill behaviors, gear mapping, and weather presets."),
      parent_toggle=pt_daily,
      panel_style=PANEL_STYLE,
    )
    self._wire_sub_panels()

  def _get_priority_value(self) -> str:
    primary = self._params.get("SLCPriority1", encoding="utf-8") or "Map Data"
    secondary = self._params.get("SLCPriority2", encoding="utf-8") or "None"
    if primary in ("Highest", "Lowest") or secondary in ("", "None", primary):
      return primary
    return f"{primary}, {secondary}"

  def _on_priority_clicked(self):
    primary_options = ["Dashboard", "Map Data", "Vision", "Highest", "Lowest"]
    if not starpilot_state.car_state.hasDashSpeedLimits:
      primary_options.remove("Dashboard")

    current_primary = self._params.get("SLCPriority1", encoding="utf-8") or "Map Data"
    if current_primary not in primary_options:
      current_primary = primary_options[0]

    current_secondary = self._params.get("SLCPriority2", encoding="utf-8") or "None"

    def on_secondary_select(primary, dialog, res):
      if res == DialogResult.CONFIRM and dialog.selection:
        self._params.put("SLCPriority1", primary)
        self._params.put("SLCPriority2", dialog.selection)

    def show_secondary_dialog(primary):
      secondary_options = ["None"] + [option for option in ("Dashboard", "Map Data", "Vision") if option != primary]
      if not starpilot_state.car_state.hasDashSpeedLimits and "Dashboard" in secondary_options:
        secondary_options.remove("Dashboard")
      selected_secondary = current_secondary if current_secondary in secondary_options else "None"
      secondary_dialog = MultiOptionDialog(tr("SLC Secondary Priority"), secondary_options, selected_secondary,
                                           callback=lambda res: on_secondary_select(primary, secondary_dialog, res))
      gui_app.push_widget(secondary_dialog)

    def on_primary_select(res):
      if res != DialogResult.CONFIRM or not primary_dialog.selection:
        return
      if primary_dialog.selection in ("Highest", "Lowest"):
        self._params.put("SLCPriority1", primary_dialog.selection)
        self._params.put("SLCPriority2", "None")
        return
      show_secondary_dialog(primary_dialog.selection)

    primary_dialog = MultiOptionDialog(tr("SLC Primary Priority"), primary_options, current_primary, callback=on_primary_select)
    gui_app.push_widget(primary_dialog)

  def _get_acceleration_profile_label(self) -> str:
    value = normalize_acceleration_profile(self._params.get("AccelerationProfile", encoding="utf-8"))
    return self._profile_label_for_value(value, ACCELERATION_PROFILE_OPTIONS)

  def _get_deceleration_profile_label(self) -> str:
    value = normalize_deceleration_profile(self._params.get("DecelerationProfile", encoding="utf-8"))
    return self._profile_label_for_value(value, DECELERATION_PROFILE_OPTIONS)

  def _show_acceleration_profile_selector(self):
    self._show_labeled_select("Acceleration Profile", "AccelerationProfile", ACCELERATION_PROFILE_OPTIONS,
                              normalize_acceleration_profile(self._params.get("AccelerationProfile", encoding="utf-8")))

  def _show_deceleration_profile_selector(self):
    self._show_labeled_select("Deceleration Profile", "DecelerationProfile", DECELERATION_PROFILE_OPTIONS,
                              normalize_deceleration_profile(self._params.get("DecelerationProfile", encoding="utf-8")))

  def _profile_label_for_value(self, value, options) -> str:
    for option_value, option_label in options:
      if option_value == value:
        return tr(option_label)
    return tr(options[0][1])

  def _set_ev_tuning(self, state: bool):
    self._params.put_bool("EVTuning", state)
    if state:
      self._params.put_bool("TruckTuning", False)

  def _set_truck_tuning(self, state: bool):
    self._params.put_bool("TruckTuning", state)
    if state:
      self._params.put_bool("EVTuning", False)

  def _set_persist_experimental_state(self, state: bool):
    sync_persist_experimental_state(self._params, self._params_memory, state)

  def _set_persist_chill_state(self, state: bool):
    sync_persist_chill_state(self._params, self._params_memory, state)

  def _get_conditional_mode_label(self) -> str:
    if self._params.get_bool("ConditionalExperimental"):
      return tr("Conditional Experimental")
    elif self._params.get_bool("ConditionalChill"):
      return tr("Conditional Chill")
    else:
      return tr("OFF")

  def _show_conditional_mode_selector(self):
    options = ["OFF", "Conditional Experimental", "Conditional Chill"]
    current = self._get_conditional_mode_label()

    def on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        if dialog.selection == "OFF":
          self._params.put_bool("ConditionalExperimental", False)
          self._params.put_bool("ConditionalChill", False)
        elif dialog.selection == "Conditional Experimental":
          self._params.put_bool("ConditionalExperimental", True)
          self._params.put_bool("ConditionalChill", False)
        elif dialog.selection == "Conditional Chill":
          self._params.put_bool("ConditionalExperimental", False)
          self._params.put_bool("ConditionalChill", True)

    dialog = MultiOptionDialog(tr("Conditional Drive Mode"), options, current, callback=on_select)
    gui_app.push_widget(dialog)

  def _reset_curve_data(self):
    def on_close(res):
      if res == DialogResult.CONFIRM:
        self._params.put_float("CalibratedLateralAcceleration", 2.00)
        self._params.remove("CalibrationProgress")
        self._params.remove("CurvatureData")

    gui_app.push_widget(ConfirmDialog(tr_noop("Reset Curve Data?"), tr_noop("Confirm"), callback=on_close))

  def _reset_profile(self, profile: str):
    def on_close(res):
      if res == DialogResult.CONFIRM:
        for key in ["Follow", "FollowHigh", "JerkAcceleration", "JerkDeceleration", "JerkDanger", "JerkSpeedDecrease", "JerkSpeed"]:
          self._params.remove(profile + key)

    gui_app.push_widget(ConfirmDialog(tr_noop("Reset to Defaults?"), tr_noop("Confirm"), callback=on_close))

  def _is_metric(self) -> bool:
    return self._params.get_bool("IsMetric")

  # Speed-typed int params stored in the current unit (mph or km/h); rescaled
  # when IsMetric flips so the numeric value stays correct in the new unit.
  _SPEED_RESCALE_KEYS = (
    "Offset1", "Offset2", "Offset3", "Offset4", "Offset5", "Offset6", "Offset7",
    "CustomCruise", "CustomCruiseLong", "SetSpeedOffset",
    "CESpeed", "CESpeedLead", "CESignalSpeed",
    "CCMSpeed", "CCMSpeedLead", "CCMSetSpeedMargin",
  )
  _SPEED_RESCALE_FLOAT_KEYS = ("PulseGlideSpeedDelta",)

  # Distance-typed int params stored in the current unit (ft or m); rescaled
  # when IsMetric flips so the numeric value stays correct in the new unit.
  _DISTANCE_RESCALE_KEYS = (
    "IncreasedStoppedDistance",
    "IncreasedStoppedDistanceLowVisibility",
    "IncreasedStoppedDistanceRain",
    "IncreasedStoppedDistanceRainStorm",
    "IncreasedStoppedDistanceSnow",
  )

  def _maybe_rescale_on_metric_change(self) -> None:
    """When IsMetric flips, recompute stored speed- and distance-typed int
    params so they read correctly in the new unit. The first call (no prior
    state) is a no-op so the user's saved values aren't rewritten on boot."""
    current = self._is_metric()

    # Update offset row titles dynamically to reflect correct unit-specific bounds (parity with C++).
    ranges_metric = ["0-29", "30-49", "50-59", "60-79", "80-99", "100-119", "120-140"]
    ranges_imperial = ["0-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-99"]
    unit = "km/h" if current else "mph"
    ranges = ranges_metric if current else ranges_imperial
    for i, row in enumerate(self._slc_offset_rows):
      row.title = f"Speed Offset ({ranges[i]} {unit})"

    last = self._last_is_metric
    self._last_is_metric = current
    if last is None or last == current:
      return
    speed_factor = CV.MPH_TO_KPH if current else CV.KPH_TO_MPH
    for key in self._SPEED_RESCALE_KEYS:
      self._params.put_int(key, int(round(self._params.get_int(key) * speed_factor)))
    for key in self._SPEED_RESCALE_FLOAT_KEYS:
      self._params.put_float(key, self._params.get_float(key) * speed_factor)
    distance_factor = CV.FOOT_TO_METER if current else CV.METER_TO_FOOT
    for key in self._DISTANCE_RESCALE_KEYS:
      self._params.put_int(key, int(round(self._params.get_int(key) * distance_factor)))

  def _mapbox_available(self) -> bool:
    """SLCMapboxFiller is only meaningful when a Mapbox key is configured."""
    return bool(self._params.get("MapboxSecretKey", encoding="utf-8"))

  def _sources_visible(self) -> bool:
    """Abbreviated/Active-Only sub-toggles only make sense when sources are shown."""
    return self._params.get_bool("SpeedLimitSources")

  def _developer_feature_access(self) -> bool:
    return (
      starpilot_state.car_state.hasOpenpilotLongitudinal and
      (self._params.get_bool("DeveloperUI") or self._params.get_bool("GalaxyDeveloperMode"))
    )

  def _speed_unit(self) -> str:
    self._maybe_rescale_on_metric_change()
    return " km/h" if self._is_metric() else " mph"

  def _speed_range(self) -> tuple[int, int]:
    self._maybe_rescale_on_metric_change()
    return (-150, 150) if self._is_metric() else (-99, 99)

  # IncreasedStoppedDistance* sliders use 0..3 m in metric and 0..10 ft in
  # imperial, reflecting the unit they're stored in.
  def _distance_unit(self) -> str:
    self._maybe_rescale_on_metric_change()
    return " m" if self._is_metric() else " ft"

  def _distance_range(self) -> tuple[int, int]:
    self._maybe_rescale_on_metric_change()
    return (0, 3) if self._is_metric() else (0, 10)

  def _show_slc_offsets_category(self):
    self._sub_panels["slc_offsets"] = AetherSettingsView(
      self,
      [SettingSection(title="", rows=self._slc_offset_rows)],
      header_title=tr_noop("SLC Offsets"),
      header_subtitle=tr_noop("Per-limit speed adjustments for the Speed Limit Controller."),
      panel_style=PANEL_STYLE,
    )
    self._wire_sub_panels()
    self._navigate_to("slc_offsets")

  def _show_personality_profile_category(self, profile: str):
    rows = self._build_personality_profile_rows(profile)
    panel_name = f"profile_{profile.lower()}"
    self._sub_panels[panel_name] = AetherSettingsView(
      self,
      [SettingSection(title="", rows=rows)],
      header_title=tr_noop(f"{profile} Profile"),
      header_subtitle=tr_noop("Customize follow distance and smoothness for this driving personality."),
      panel_style=PANEL_STYLE,
    )
    self._wire_sub_panels()
    self._navigate_to(panel_name)

  def _show_weather_offsets_category(self, suffix: str, title: str):
    rows = self._build_weather_offsets_rows(suffix)
    panel_name = f"weather_{suffix.lower()}"
    self._sub_panels[panel_name] = AetherSettingsView(
      self,
      [SettingSection(title="", rows=rows)],
      header_title=tr_noop(title),
      header_subtitle=tr_noop("Adjust driving parameters for this weather condition."),
      panel_style=PANEL_STYLE,
    )
    self._wire_sub_panels()
    self._navigate_to(panel_name)

  def _build_personality_profile_rows(self, profile: str) -> list[SettingRow]:
    follow_min = 0.5
    follow_max = 2.5 if profile == "Traffic" else 3.0
    p = profile
    rows = [
      SettingRow(f"{p}Follow", "value", tr_noop("Follow Distance"),
                 subtitle="",
                 get_value=lambda: f"{self._params.get_float(p + 'Follow'):.2f}s",
                 on_click=lambda: self._show_slider(p + "Follow", follow_min, follow_max, step=0.05, unit="s", value_type="float")),
    ]
    if profile != "Traffic":
      rows.append(
        SettingRow(f"{p}FollowHigh", "value", tr_noop("Follow High"),
                   subtitle="",
                   get_value=lambda: f"{self._params.get_float(p + 'FollowHigh'):.2f}s",
                   on_click=lambda: self._show_slider(p + "FollowHigh", 1.0, 3.0, step=0.05, unit="s", value_type="float"))
      )
    rows.extend([
      SettingRow(f"{p}JerkAccel", "value", tr_noop("Accel Smoothness"),
                 subtitle="",
                 get_value=lambda: f"{self._params.get_int(p + 'JerkAcceleration')}%",
                 on_click=lambda: self._show_slider(p + "JerkAcceleration", 25, 200, step=5, unit="%")),
      SettingRow(f"{p}JerkDecel", "value", tr_noop("Brake Smoothness"),
                 subtitle="",
                 get_value=lambda: f"{self._params.get_int(p + 'JerkDeceleration')}%",
                 on_click=lambda: self._show_slider(p + "JerkDeceleration", 25, 200, step=5, unit="%")),
      SettingRow(f"{p}JerkDanger", "value", tr_noop("Safety Gap Bias"),
                 subtitle="",
                 get_value=lambda: f"{self._params.get_int(p + 'JerkDanger')}%",
                 on_click=lambda: self._show_slider(p + "JerkDanger", 25, 200, step=5, unit="%")),
      SettingRow(f"{p}JerkSpeedDec", "value", tr_noop("Slowdown Response"),
                 subtitle="",
                 get_value=lambda: f"{self._params.get_int(p + 'JerkSpeedDecrease')}%",
                 on_click=lambda: self._show_slider(p + "JerkSpeedDecrease", 25, 200, step=5, unit="%")),
      SettingRow(f"{p}JerkSpeed", "value", tr_noop("Speed-Up Response"),
                 subtitle="",
                 get_value=lambda: f"{self._params.get_int(p + 'JerkSpeed')}%",
                 on_click=lambda: self._show_slider(p + "JerkSpeed", 25, 200, step=5, unit="%")),
      SettingRow(f"{p}Reset", "action", tr_noop("Reset to Defaults"),
                 subtitle="",
                 action_text=tr_noop("Reset"),
                 action_danger=True,
                 on_click=lambda: self._reset_profile(p)),
    ])
    return rows

  def _build_weather_offsets_rows(self, suffix: str) -> list[SettingRow]:
    s = suffix
    return [
      SettingRow(f"Follow{s}", "value", tr_noop("Following Distance"),
                 subtitle="",
                 get_value=lambda: f"+{self._params.get_int('IncreaseFollowing' + s)}s",
                 on_click=lambda: self._show_slider("IncreaseFollowing" + s, 0, 3, step=0.5, unit="s")),
      SettingRow(f"StoppedDist{s}", "value", tr_noop("Stopped Distance"),
                 subtitle="",
                 get_value=lambda: f"+{self._params.get_int('IncreasedStoppedDistance' + s)}{self._distance_unit()}",
                 on_click=lambda: self._show_slider("IncreasedStoppedDistance" + s, *self._distance_range(),
                                                    unit=self._distance_unit())),
      SettingRow(f"ReduceAccel{s}", "value", tr_noop("Reduce Accel"),
                 subtitle="",
                 get_value=lambda: f"{self._params.get_int('ReduceAcceleration' + s)}%",
                 on_click=lambda: self._show_slider("ReduceAcceleration" + s, 0, 99, unit="%")),
      SettingRow(f"ReduceLateral{s}", "value", tr_noop("Reduce Curve Speed"),
                 subtitle="",
                 get_value=lambda: f"{self._params.get_int('ReduceLateralAcceleration' + s)}%",
                 on_click=lambda: self._show_slider("ReduceLateralAcceleration" + s, 0, 99, unit="%")),
    ]

  def _set_weather_key(self):
    options = ["ADD", "REMOVE"]

    def on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        if dialog.selection == "ADD":

          def on_key(res, text):
            if res == DialogResult.CONFIRM:
              self._params.put("WeatherToken", text)

          self._keyboard.reset(min_text_size=1)
          self._keyboard.set_title(tr_noop("Weather API Key"), "")
          self._keyboard.set_text("")
          self._keyboard.set_callback(lambda result: on_key(result, self._keyboard.text))
          gui_app.push_widget(self._keyboard)
        elif dialog.selection == "REMOVE":

          def on_confirm(res):
            if res == DialogResult.CONFIRM:
              self._params.remove("WeatherToken")

          gui_app.push_widget(ConfirmDialog(tr_noop("Remove API Key?"), tr_noop("Confirm"), callback=on_confirm))

    dialog = MultiOptionDialog(tr_noop("Weather API Key"), options, "ADD", callback=on_select)
    gui_app.push_widget(dialog)
