from __future__ import annotations

import pyray as rl

from openpilot.system.hardware import HARDWARE
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog

from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AetherListMetrics,
  AetherListColors,
  AetherSliderDialog,
  DEFAULT_PANEL_STYLE,
  PanelManagerView,
  TileGrid,
  ToggleTile,
  draw_list_group_shell,
  draw_section_header,
  draw_selection_list_row,
  draw_settings_panel_header,
  _with_alpha,
)


def _confirm_reboot_toggle(params, key, state):
  params.put_bool(key, state)
  from openpilot.selfdrive.ui.ui_state import ui_state
  if ui_state.started:
    gui_app.push_widget(ConfirmDialog(
      tr("Reboot required. Reboot now?"), tr("Reboot"), tr("Cancel"),
      callback=lambda res: HARDWARE.reboot() if res == DialogResult.CONFIRM else None,
    ))


CUSTOM_METRICS = AetherListMetrics(
  max_content_width=1560,
  outer_margin_x=18,
  outer_margin_y=10,
  panel_padding_x=16,
  panel_padding_top=16,
  panel_padding_bottom=12,
  header_height=164,
  section_gap=12,
  section_header_height=28,
  section_header_gap=8,
  row_height=104,
  utility_row_height=88,
)

SECTION_GAP = CUSTOM_METRICS.section_gap
SECTION_HEADER_HEIGHT = CUSTOM_METRICS.section_header_height
SECTION_HEADER_GAP = CUSTOM_METRICS.section_header_gap
ROW_HEIGHT = CUSTOM_METRICS.row_height
PANEL_STYLE = DEFAULT_PANEL_STYLE

_LATERAL_TUNE_KEYS = ["TurnDesires", "NNFF", "NNFFLite", "ForceTorqueController"]
_ADVANCED_LATERAL_KEYS = ["ForceAutoTune", "ForceAutoTuneOff"]


def _ensure(params, key):
  if not params.get_bool(key):
    params.put_bool(key, True)


def _sync_parent(params, parent_key, child_keys):
  if any(params.get_bool(k) for k in child_keys):
    if not params.get_bool(parent_key):
      params.put_bool(parent_key, True)
  else:
    if params.get_bool(parent_key):
      params.put_bool(parent_key, False)


class SteeringManagerView(PanelManagerView):
  METRICS = CUSTOM_METRICS

  def __init__(self, controller: "StarPilotLateralLayout"):
    super().__init__()
    self._controller = controller
    self._shell_rect = rl.Rectangle(0, 0, 0, 0)

    self._toggle_grid = TileGrid(columns=2, padding=12, min_tile_width=100)
    self._toggle_grid.set_touch_valid_callback(lambda: self._scroll_panel.is_touch_valid())
    self._child(self._toggle_grid)

  def show_event(self):
    super().show_event()
    starpilot_state.update(force=True)
    self._rebuild_toggle_grid()

  def _on_frame_created(self, frame) -> None:
    self._shell_rect = frame.shell

  def _activate_target(self, target_id: str | None):
    if not target_id:
      return
    prefix, _, value = target_id.partition(":")
    if prefix == "select":
      self._controller._on_select(value)

  def _draw_header(self, rect: rl.Rectangle):
    draw_settings_panel_header(rect, tr("Steering"),
                                tr("Fine-tune lateral control, lane changes, and steering behavior."),
                                subtitle_size=22)

  def _build_toggle_defs(self) -> list[dict]:
    p = self._controller._params
    cs = starpilot_state.car_state
    toggles: list[dict] = []

    toggles.append({
      "key": "AdvancedLateralTune",
      "title": tr("Advanced Lateral Tuning"),
      "subtitle": tr("Fine-tune steering response and auto-tuning."),
      "get": lambda: p.get_bool("AdvancedLateralTune"),
      "set": lambda s: p.put_bool("AdvancedLateralTune", s),
    })

    toggles.append({
      "key": "AlwaysOnLateral",
      "title": tr("Always On Lateral"),
      "subtitle": tr("Steering stays active when ACC is off."),
      "get": lambda: p.get_bool("AlwaysOnLateral"),
      "set": lambda s: (_confirm_reboot_toggle(p, "AlwaysOnLateral", s)
                        if s else p.put_bool("AlwaysOnLateral", False)),
    })

    toggles.append({
      "key": "LaneChanges",
      "title": tr("Lane Changes"),
      "subtitle": tr("Allow openpilot to change lanes."),
      "get": lambda: p.get_bool("LaneChanges"),
      "set": lambda s: p.put_bool("LaneChanges", s),
    })

    toggles.append({
      "key": "PauseLateralOnSignal",
      "title": tr("Turn Signal Only"),
      "subtitle": tr("Only pause steering when turn signal is active."),
      "get": lambda: p.get_bool("PauseLateralOnSignal"),
      "set": lambda s: p.put_bool("PauseLateralOnSignal", s),
    })

    toggles.append({
      "key": "NudgelessLaneChange",
      "title": tr("Auto Lane Changes"),
      "subtitle": tr("Signal triggers automatic lane change."),
      "get": lambda: p.get_bool("NudgelessLaneChange"),
      "set": lambda s: p.put_bool("NudgelessLaneChange", s),
    })

    toggles.append({
      "key": "OneLaneChange",
      "title": tr("One Per Signal"),
      "subtitle": tr("One lane change per signal activation."),
      "get": lambda: p.get_bool("OneLaneChange"),
      "set": lambda s: p.put_bool("OneLaneChange", s),
    })

    toggles.append({
      "key": "TurnDesires",
      "title": tr("Force Turn Desires"),
      "subtitle": tr("Follow turn intent below min lane change speed."),
      "get": lambda: p.get_bool("TurnDesires"),
      "set": lambda s: (p.put_bool("TurnDesires", s),
                        _sync_parent(p, "LateralTune", _LATERAL_TUNE_KEYS)),
    })

    toggles.append({
      "key": "NavDesiresAllowed",
      "title": tr("Use Route Desires"),
      "subtitle": tr("Allow navigation to request lane keep and turns."),
      "get": lambda: p.get_bool("NavDesiresAllowed"),
      "set": lambda s: p.put_bool("NavDesiresAllowed", s),
    })

    toggles.append({
      "key": "NNFF",
      "title": tr("NNFF"),
      "subtitle": tr("Neural net feedforward steering controller."),
      "get": lambda: p.get_bool("NNFF"),
      "set": lambda s: (p.put_bool("NNFF", s),
                        s and p.put_bool("NNFFLite", False),
                        _sync_parent(p, "LateralTune", _LATERAL_TUNE_KEYS)),
      "enabled": cs.hasNNFFLog and not cs.isAngleCar,
      "disabled_label": tr("Not Available"),
    })

    toggles.append({
      "key": "NNFFLite",
      "title": tr("NNFF Lite"),
      "subtitle": tr("Lightweight NNFF when full model is off."),
      "get": lambda: p.get_bool("NNFFLite"),
      "set": lambda s: (p.put_bool("NNFFLite", s),
                        _sync_parent(p, "LateralTune", _LATERAL_TUNE_KEYS)),
      "enabled": not cs.isAngleCar,
      "disabled_label": tr("Not Available"),
    })

    toggles.append({
      "key": "ForceAutoTune",
      "title": tr("Force Auto-Tune On"),
      "subtitle": tr("Force-enable live auto-tuning for friction and lateral accel."),
      "get": lambda: p.get_bool("ForceAutoTune"),
      "set": lambda s: (p.put_bool("ForceAutoTune", s),
                        s and p.put_bool("ForceAutoTuneOff", False),
                        _sync_parent(p, "AdvancedLateralTune", _ADVANCED_LATERAL_KEYS)),
      "enabled": not cs.hasAutoTune and cs.isTorqueCar and not cs.isAngleCar,
      "disabled_label": tr("Not Available"),
    })

    toggles.append({
      "key": "ForceAutoTuneOff",
      "title": tr("Force Auto-Tune Off"),
      "subtitle": tr("Force-disable auto-tuning and use your set values."),
      "get": lambda: p.get_bool("ForceAutoTuneOff"),
      "set": lambda s: (p.put_bool("ForceAutoTuneOff", s),
                        s and p.put_bool("ForceAutoTune", False),
                        _sync_parent(p, "AdvancedLateralTune", _ADVANCED_LATERAL_KEYS)),
      "enabled": cs.hasAutoTune and cs.isTorqueCar and not cs.isAngleCar,
      "disabled_label": tr("Not Available"),
    })

    toggles.append({
      "key": "ForceTorqueController",
      "title": tr("Force Torque Ctrl"),
      "subtitle": tr("Torque-based steering for smoother lane keeping."),
      "get": lambda: p.get_bool("ForceTorqueController"),
      "set": lambda s: (p.put_bool("ForceTorqueController", s),
                        _sync_parent(p, "LateralTune", _LATERAL_TUNE_KEYS)),
      "enabled": not cs.isTorqueCar and not cs.isAngleCar,
      "disabled_label": tr("Not Available"),
    })

    return toggles

  def _rebuild_toggle_grid(self):
    self._page_grid = self._toggle_grid
    defs = self._build_toggle_defs()
    self._set_toggle_pages([defs[i:i+6] for i in range(0, len(defs), 6)])

  def _measure_content_height(self, width: float) -> float:
    sections = self._build_left_sections()
    left_h = self._stacked_section_height([s["height"] for s in sections if s.get("visible", True)])

    tiles_height = 0.0
    if self._toggle_grid.tiles:
      if self._uses_two_columns(width):
        self._toggle_grid._columns = 2
        column_w = self._column_width(width)
        col_w = (column_w - 24 - 12) / 2
        grid_h = 2 * col_w + 12
        tiles_height = self._section_block_height(grid_h + 24)
      else:
        self._toggle_grid._columns = 3
        tiles_content_h = self._toggle_grid.measure_height(width - 24)
        tiles_height = SECTION_GAP + self._section_block_height(tiles_content_h + 24)

    if self._uses_two_columns(width):
      vh = self._scroll_rect.height if self._scroll_rect and self._scroll_rect.height > 0 else tiles_height
      return max(left_h, vh)
    return left_h + tiles_height

  def _draw_scroll_content(self, rect: rl.Rectangle, width: float):
    self._interactive_rects.clear()
    y = rect.y + self._scroll_offset
    self._draw_panel_content(y, rect.x, width)

  def _draw_panel_content(self, y: float, x: float, width: float):
    sections = self._build_left_sections()

    drawn_first = False

    if self._uses_two_columns(width):
      column_w = self._column_width(width)
      curr_y = y

      for section in sections:
        if not section.get("rows"):
          continue
        if drawn_first:
          curr_y += SECTION_GAP
        drawn_first = True
        draw_section_header(rl.Rectangle(x, curr_y, column_w, SECTION_HEADER_HEIGHT),
                            section["title"], style=PANEL_STYLE)
        curr_y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
        row_count = len(section["rows"])
        container_rect = rl.Rectangle(x, curr_y, column_w, row_count * ROW_HEIGHT)
        draw_list_group_shell(container_rect, style=PANEL_STYLE)
        for index, row in enumerate(section["rows"]):
          row_rect = rl.Rectangle(x, curr_y + index * ROW_HEIGHT, column_w, ROW_HEIGHT)
          self._draw_row(row_rect, row, is_last=index == row_count - 1)
        curr_y += row_count * ROW_HEIGHT

      if self._toggle_grid.tiles:
        rx = x + column_w + self.COLUMN_GAP
        draw_section_header(rl.Rectangle(rx, y, column_w, SECTION_HEADER_HEIGHT),
                            tr("Toggles"), style=PANEL_STYLE)
        right_container_y = y + SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP

        self._toggle_grid._columns = 2
        col_w = (column_w - 24 - 12) / 2
        grid_h = 2 * col_w + 12
        container_h = grid_h + 24

        draw_list_group_shell(rl.Rectangle(rx, right_container_y, column_w, container_h), style=PANEL_STYLE)
        self._render_page_grid(self._toggle_grid, rl.Rectangle(rx + 12, right_container_y + 12, column_w - 24, grid_h))
    else:
      curr_y = y
      for section in sections:
        if not section.get("rows"):
          continue
        if drawn_first:
          curr_y += SECTION_GAP
        drawn_first = True
        draw_section_header(rl.Rectangle(x, curr_y, width, SECTION_HEADER_HEIGHT),
                            section["title"], style=PANEL_STYLE)
        curr_y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
        row_count = len(section["rows"])
        container_rect = rl.Rectangle(x, curr_y, width, row_count * ROW_HEIGHT)
        draw_list_group_shell(container_rect, style=PANEL_STYLE)
        for index, row in enumerate(section["rows"]):
          row_rect = rl.Rectangle(x, curr_y + index * ROW_HEIGHT, width, ROW_HEIGHT)
          self._draw_row(row_rect, row, is_last=index == row_count - 1)
        curr_y += row_count * ROW_HEIGHT

      if self._toggle_grid.tiles:
        curr_y += SECTION_GAP
        draw_section_header(rl.Rectangle(x, curr_y, width, SECTION_HEADER_HEIGHT),
                            tr("Toggles"), style=PANEL_STYLE)
        curr_y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP

        self._toggle_grid._columns = 3
        avail_w = width - 24
        tiles_content_h = self._toggle_grid.measure_height(avail_w)

        draw_list_group_shell(rl.Rectangle(x, curr_y, width, tiles_content_h + 24), style=PANEL_STYLE)
        self._render_page_grid(self._toggle_grid, rl.Rectangle(x + 12, curr_y + 12, avail_w, tiles_content_h))

  def _draw_row(self, rect: rl.Rectangle, row: dict, is_last: bool):
    target_id = row["target_id"]
    is_enabled = row.get("is_enabled", True)
    hovered, pressed = self._interactive_state(target_id, rect) if is_enabled else (False, False)

    draw_selection_list_row(
      rect, title=row["title"], subtitle=row.get("subtitle", ""),
      action_text=row["get_value"](), hovered=hovered and is_enabled,
      pressed=pressed and is_enabled, is_last=is_last,
      action_width=188, action_pill=True,
      action_pill_width=row.get("pill_width", 108), action_pill_height=44,
      title_size=34, subtitle_size=22, action_text_size=18,
      row_separator=PANEL_STYLE.divider_color,
      action_fill=PANEL_STYLE.current_fill if is_enabled else _with_alpha(PANEL_STYLE.current_fill, 120),
      action_border=PANEL_STYLE.current_border if is_enabled else _with_alpha(PANEL_STYLE.current_border, 100),
      action_text_color=AetherListColors.HEADER if is_enabled else AetherListColors.MUTED,
    )

  def _build_left_sections(self) -> list[dict]:
    p = self._controller._params
    cs = starpilot_state.car_state
    sections: list[dict] = []

    alt = p.get_bool("AdvancedLateralTune")
    aol = p.get_bool("AlwaysOnLateral")
    lc = p.get_bool("LaneChanges")
    nlc = p.get_bool("NudgelessLaneChange")
    pos = p.get_bool("PauseLateralOnSignal")

    if alt:
      rows: list[dict] = []
      if cs.steerActuatorDelay != 0:
        rows.append({
          "target_id": "select:SteerDelay",
          "title": tr("Actuator Delay"),
          "subtitle": tr("Time between steering command and vehicle response."),
          "get_value": lambda: f"{p.get_float('SteerDelay'):.2f}s",
          "pill_width": 120,
        })
      if cs.friction != 0:
        rows.append({
          "target_id": "select:SteerFriction",
          "title": tr("Friction"),
          "subtitle": tr("Compensates for steering friction around center."),
          "get_value": lambda: f"{p.get_float('SteerFriction'):.3f}",
          "pill_width": 120,
        })
      if cs.steerKp != 0:
        rows.append({
          "target_id": "select:SteerKP",
          "title": tr("Kp Factor"),
          "subtitle": tr("How strongly openpilot corrects lateral position."),
          "get_value": lambda: f"{p.get_float('SteerKP'):.2f}",
          "pill_width": 120,
        })
      if cs.latAccelFactor != 0:
        rows.append({
          "target_id": "select:SteerLatAccel",
          "title": tr("Lateral Acceleration"),
          "subtitle": tr("Maps steering torque to turning response."),
          "get_value": lambda: f"{p.get_float('SteerLatAccel'):.2f}",
          "pill_width": 120,
        })
      if cs.steerRatio != 0:
        rows.append({
          "target_id": "select:SteerRatio",
          "title": tr("Steer Ratio"),
          "subtitle": tr("Relationship between steering wheel and road-wheel angle."),
          "get_value": lambda: f"{p.get_float('SteerRatio'):.2f}",
          "pill_width": 120,
        })
      sections.append({
        "title": tr("Advanced Tuning"),
        "rows": rows,
        "visible": True,
        "height": self._section_block_height(self._section_height(len(rows), ROW_HEIGHT)),
      })

    if aol:
      aol_rows = [{
        "target_id": "select:PauseAOLOnBrake",
        "title": tr("Pause AOL On Brake"),
        "subtitle": tr("Pause AOL below this speed while brake is pressed."),
        "get_value": lambda: f"{p.get_int('PauseAOLOnBrake')} mph",
        "pill_width": 140,
      }]
      sections.append({
        "title": tr("Always On Lateral"),
        "rows": aol_rows,
        "visible": True,
        "height": self._section_block_height(self._section_height(len(aol_rows), ROW_HEIGHT)),
      })

    if lc:
      lc_rows: list[dict] = [{
        "target_id": "select:MinimumLaneChangeSpeed",
        "title": tr("Min Lane Change Speed"),
        "subtitle": tr("Lowest speed at which openpilot will change lanes."),
        "get_value": lambda: f"{p.get_int('MinimumLaneChangeSpeed')} mph",
        "pill_width": 140,
      }]
      if nlc:
        lc_rows.append({
          "target_id": "select:LaneChangeTime",
          "title": tr("Lane Change Delay"),
          "subtitle": tr("Delay before the start of an automatic lane change. 0 = Instant."),
          "get_value": lambda: tr("Instant") if p.get_float("LaneChangeTime") == 0
                         else f"{p.get_float('LaneChangeTime'):.1f}s",
          "pill_width": 120,
        })
        lc_rows.append({
          "target_id": "select:LaneDetectionWidth",
          "title": tr("Min Lane Width"),
          "subtitle": tr("Prevent lane changes into narrower lanes."),
          "get_value": lambda: f"{p.get_float('LaneDetectionWidth'):.1f} ft",
          "pill_width": 120,
        })
      lc_rows.append({
        "target_id": "select:LaneChangeSmoothing",
        "title": tr("Lane Change Smoothing"),
        "subtitle": tr("Smoothness of lane change commit. 10 = Stock, 1 = Smoothest."),
        "get_value": lambda: tr("Stock") if p.get_int("LaneChangeSmoothing") == 10
                       else f"{p.get_int('LaneChangeSmoothing')}",
        "pill_width": 120,
      })
      sections.append({
        "title": tr("Lane Changes"),
        "rows": lc_rows,
        "visible": True,
        "height": self._section_block_height(self._section_height(len(lc_rows), ROW_HEIGHT)),
      })

    paus_rows: list[dict] = [{
      "target_id": "select:PauseLateralSpeed",
      "title": tr("Pause Lateral Below"),
      "subtitle": tr("Pause steering below the set speed."),
      "get_value": lambda: f"{p.get_int('PauseLateralSpeed')} mph",
      "pill_width": 140,
    }]
    if pos:
      paus_rows.append({
        "target_id": "select:LateralResumeDelay",
        "title": tr("Resume Delay"),
        "subtitle": tr("Delay before lateral resumes after signal off. 0 = Off."),
        "get_value": lambda: tr("Off") if p.get_float("LateralResumeDelay") == 0
                       else f"{p.get_float('LateralResumeDelay'):.1f}s",
        "pill_width": 120,
      })
    sections.append({
      "title": tr("Pause Lateral"),
      "rows": paus_rows,
      "visible": True,
      "height": self._section_block_height(self._section_height(len(paus_rows), ROW_HEIGHT)),
      })

    return sections


# ═══════════════════════════════════════════════════════════════
# StarPilotLateralLayout — top-level hybrid panel
# ═══════════════════════════════════════════════════════════════

class StarPilotLateralLayout(_SettingsPage):
  SLIDER_COLOR = "#5B9BD5"

  def __init__(self):
    super().__init__()
    self._manager_view = SteeringManagerView(self)

  def _on_select(self, key: str):
    if key == "PauseAOLOnBrake":
      self._show_slider("PauseAOLOnBrake", 0, 100, unit=" mph")
    elif key == "PauseLateralSpeed":
      def on_speed_close(res, val):
        if res == DialogResult.CONFIRM:
          self._params.put_int("PauseLateralSpeed", int(val))
          self._params.put_bool("QOLLateral", int(val) > 0)
      current = self._params.get_int("PauseLateralSpeed")
      gui_app.push_widget(AetherSliderDialog(
        tr("Pause Lateral Below"), 0, 100, 1, current, on_speed_close,
        unit=" mph", color=self.SLIDER_COLOR))
    elif key == "LateralResumeDelay":
      self._show_slider("LateralResumeDelay", 0.0, 5.0, step=0.1, unit="s", value_type="float")
    elif key == "MinimumLaneChangeSpeed":
      self._show_slider("MinimumLaneChangeSpeed", 0, 100, unit=" mph")
    elif key == "LaneChangeTime":
      self._show_slider("LaneChangeTime", 0.0, 5.0, step=0.1, unit="s", value_type="float")
    elif key == "LaneDetectionWidth":
      self._show_slider("LaneDetectionWidth", 0.0, 15.0, step=0.1, unit=" ft", value_type="float")
    elif key == "LaneChangeSmoothing":
      self._show_lane_smoothing()
    elif key == "SteerDelay":
      self._show_slider("SteerDelay", 0.01, 1.0, step=0.01, unit="s", value_type="float")
    elif key == "SteerFriction":
      self._show_slider("SteerFriction", 0.0, max(1.0, starpilot_state.car_state.friction * 1.5), step=0.01, value_type="float")
    elif key == "SteerKP":
      self._show_slider("SteerKP", max(0.01, starpilot_state.car_state.steerKp) * 0.5, max(0.01, starpilot_state.car_state.steerKp) * 1.5, step=0.01, value_type="float")
    elif key == "SteerLatAccel":
      self._show_slider("SteerLatAccel", max(0.01, starpilot_state.car_state.latAccelFactor) * 0.5, max(0.01, starpilot_state.car_state.latAccelFactor) * 1.5, step=0.01, value_type="float")
    elif key == "SteerRatio":
      self._show_slider("SteerRatio", max(0.01, starpilot_state.car_state.steerRatio) * 0.5, max(0.01, starpilot_state.car_state.steerRatio) * 1.5, step=0.01, value_type="float")

  def _show_lane_smoothing(self):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int("LaneChangeSmoothing", int(val))
    current = self._params.get_int("LaneChangeSmoothing") if self._params.get_int("LaneChangeSmoothing") > 0 else 10
    gui_app.push_widget(AetherSliderDialog(tr("Lane Change Smoothing"), 1, 10, 1, current, on_close,
                                           color=self.SLIDER_COLOR))
