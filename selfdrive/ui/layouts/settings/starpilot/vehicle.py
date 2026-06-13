from __future__ import annotations

import pyray as rl

from openpilot.system.hardware import HARDWARE
from openpilot.system.ui.lib.application import FontWeight, gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.lib.scroll_panel2 import GuiScrollPanel2
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.widgets.label import gui_label
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AetherListMetrics,
  AetherInteractiveMixin,
  AetherListColors,
  AetherScrollbar,
  AetherSliderDialog,
  panel_style_from_color,
  draw_list_group_shell,
  draw_list_scroll_fades,
  draw_section_header,
  draw_selection_list_row,
  draw_settings_list_row,
  draw_settings_panel_header,
  draw_soft_card,
  init_list_panel,
  TileGrid,
  ToggleTile,
  _with_alpha,
  _draw_rounded_fill,
  _draw_rounded_stroke,
  draw_status_badges,
)
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.selfdrive.ui.lib.fingerprint_catalog import (
  FingerprintModelOption,
  get_fingerprint_catalog,
  shorten_model_label,
)
from openpilot.starpilot.common.starpilot_variables import migrate_cancel_button_controls


ACTION_OPTIONS = [
  {"id": 0, "name": tr_noop("No Action")},
  {"id": 1, "name": tr_noop("Change Personality"), "requires_longitudinal": True},
  {"id": 2, "name": tr_noop("Force Coast"), "requires_longitudinal": True},
  {"id": 3, "name": tr_noop("Pause Steering")},
  {"id": 4, "name": tr_noop("Pause Accel/Brake"), "requires_longitudinal": True},
  {"id": 5, "name": tr_noop("Toggle Experimental"), "requires_longitudinal": True},
  {"id": 6, "name": tr_noop("Toggle Traffic"), "requires_longitudinal": True},
  {"id": 7, "name": tr_noop("Toggle Switchback")},
  {"id": 8, "name": tr_noop("Create Bookmark")},
  {"id": 9, "name": tr_noop("Toggle Always On Lateral")},
  {"id": 10, "name": tr_noop("Adopt Current Speed Limit")},
]
ACTION_NAMES = [o["name"] for o in ACTION_OPTIONS]
ACTION_IDS = {o["name"]: o["id"] for o in ACTION_OPTIONS}
ACTION_NAME_BY_ID = {o["id"]: o["name"] for o in ACTION_OPTIONS}


def _lock_doors_timer_labels():
  labels: dict[float, str] = {0.0: tr("Never")}
  for i in range(5, 305, 5):
    labels[float(i)] = f"{i}s"
  return labels


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
FADE_HEIGHT = CUSTOM_METRICS.fade_height
PANEL_STYLE = panel_style_from_color("#64748B")


class VehicleSettingsManagerView(AetherInteractiveMixin, Widget):
  HEADER_SUBTITLE_HEIGHT = 22
  HEADER_SUMMARY_GAP = 10
  HEADER_CARD_HEIGHT = 100
  TWO_COLUMN_BREAKPOINT = 1180
  COLUMN_GAP = 22

  def __init__(self, controller: "StarPilotVehicleSettingsLayout"):
    super().__init__()
    self._controller = controller
    self._scroll_panel = GuiScrollPanel2(horizontal=False)
    self._scrollbar = AetherScrollbar()
    self._content_height = 0.0
    self._scroll_offset = 0.0
    self._shell_rect = rl.Rectangle(0, 0, 0, 0)
    self._scroll_rect = rl.Rectangle(0, 0, 0, 0)

    self._toggle_grid = TileGrid(columns=2, padding=12, min_tile_width=100)
    self._toggle_grid.set_touch_valid_callback(lambda: self._scroll_panel.is_touch_valid())
    self._child(self._toggle_grid)

    self._last_make = ""
    self._last_model = ""

  def _build_driving_toggles(self) -> list[dict]:
    cs = starpilot_state.car_state
    toggles = []

    toggles.append({
      "title": tr("Disable Fingerprinting"),
      "subtitle": tr("Manually select vehicle instead of auto-detecting."),
      "get_state": lambda: self._controller._params.get_bool("ForceFingerprint"),
      "set_state": lambda s: self._controller._on_toggle("ForceFingerprint"),
    })

    toggles.append({
      "title": tr("Disable openpilot Long"),
      "subtitle": tr("Revert to stock longitudinal control."),
      "get_state": lambda: self._controller._params.get_bool("DisableOpenpilotLongitudinal"),
      "set_state": lambda s: self._controller._on_toggle("DisableOpenpilotLongitudinal"),
    })

    if cs.isGM and (cs.hasPedal or cs.canUsePedal):
      toggles.append({
        "title": tr("Pedal for Long"),
        "get_state": lambda: self._controller._params.get_bool("GMPedalLongitudinal"),
        "set_state": lambda s: self._controller._on_toggle("GMPedalLongitudinal"),
      })
      toggles.append({
        "title": tr("Offsets on Dash Spoof"),
        "get_state": lambda: self._controller._params.get_bool("GMDashSpoofOffsets"),
        "set_state": lambda s: self._controller._on_toggle("GMDashSpoofOffsets"),
      })
    if cs.isGM:
      toggles.append({
        "title": tr("Remote Start Panda"),
        "get_state": lambda: self._controller._params.get_bool("RemoteStartBootsComma"),
        "set_state": lambda s: self._controller._on_toggle("RemoteStartBootsComma"),
      })
    if cs.isGM and cs.isVolt and not cs.hasSNG:
      toggles.append({
        "title": tr("Volt SNG Hack"),
        "get_state": lambda: self._controller._params.get_bool("VoltSNG"),
        "set_state": lambda s: self._controller._on_toggle("VoltSNG"),
      })

    if cs.isSubaru:
      toggles.append({
        "title": tr("Stop and Go"),
        "get_state": lambda: self._controller._params.get_bool("SubaruSNG"),
        "set_state": lambda s: self._controller._on_toggle("SubaruSNG"),
      })

    if cs.isToyota:
      toggles.append({
        "title": tr("Auto Lock Doors"),
        "get_state": lambda: self._controller._params.get_bool("LockDoors"),
        "set_state": lambda s: self._controller._on_toggle("LockDoors"),
      })
      toggles.append({
        "title": tr("Auto Unlock Doors"),
        "get_state": lambda: self._controller._params.get_bool("UnlockDoors"),
        "set_state": lambda s: self._controller._on_toggle("UnlockDoors"),
      })
    if cs.isToyota and not cs.hasSNG:
      toggles.append({
        "title": tr("Stop-and-Go Hack"),
        "get_state": lambda: self._controller._params.get_bool("SNGHack"),
        "set_state": lambda s: self._controller._on_toggle("SNGHack"),
      })
    if cs.isToyota and cs.hasOpenpilotLongitudinal:
      toggles.append({
        "title": tr("FrogsGoMoo Tweak"),
        "get_state": lambda: self._controller._params.get_bool("FrogsGoMoosTweak"),
        "set_state": lambda s: self._controller._on_toggle("FrogsGoMoosTweak"),
      })

    if cs.isBolt and cs.hasPedal:
      toggles.append({
        "title": tr("Remap Cancel Button"),
        "subtitle": tr("Treat the Cancel button as an extra mappable steering-wheel button."),
        "get_state": lambda: self._controller._params.get_bool("RemapCancelToDistance"),
        "set_state": lambda s: self._controller._on_toggle("RemapCancelToDistance"),
      })

    if cs.isHKGCanFd and cs.hasOpenpilotLongitudinal:
      toggles.append({
        "title": tr("Nostalgia Mode"),
        "subtitle": tr("Use the left paddle to pause openpilot acceleration and braking."),
        "get_state": lambda: self._controller._params.get_bool("NostalgiaMode"),
        "set_state": lambda s: self._controller._on_toggle("NostalgiaMode"),
      })

    return toggles

  def _rebuild_toggle_grid(self):
    self._toggle_grid.clear()
    toggles = self._build_driving_toggles()
    self._toggle_grid._columns = len(toggles)
    for toggle_def in toggles:
      tile = ToggleTile(
        title=toggle_def["title"],
        get_state=toggle_def["get_state"],
        set_state=toggle_def["set_state"],
        bg_color=PANEL_STYLE.accent,
        desc=toggle_def.get("subtitle", ""),
        is_enabled=toggle_def.get("is_enabled"),
        disabled_label=toggle_def.get("disabled_label", ""),
      )
      self._toggle_grid.add_tile(tile)

  def _check_rebuild_grid(self):
    current_make = self._controller._get_display_make()
    current_model = self._controller._get_display_model()
    if current_make != self._last_make or current_model != self._last_model:
      self._last_make = current_make
      self._last_model = current_model
      self._rebuild_toggle_grid()

  def _uses_two_columns(self, width: float) -> bool:
    return width >= self.TWO_COLUMN_BREAKPOINT

  def _column_width(self, width: float) -> float:
    return (width - self.COLUMN_GAP) / 2 if self._uses_two_columns(width) else width

  def _section_height(self, count: int, row_height: float) -> float:
    return 0.0 if count <= 0 else count * row_height

  def _section_block_height(self, content_height: float) -> float:
    if content_height <= 0:
      return 0.0
    return SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP + content_height

  def _stacked_section_height(self, sections: list[float]) -> float:
    if not sections:
      return 0.0
    return sum(sections) + SECTION_GAP * (len(sections) - 1)

  def _activate_target(self, target_id: str | None):
    if not target_id:
      return
    prefix, _, value = target_id.partition(":")
    if prefix == "toggle":
      self._controller._on_toggle(value)
    elif prefix == "select":
      self._controller._on_select(value)

  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)

    frame, scroll_rect, content_width = init_list_panel(rect, PANEL_STYLE, CUSTOM_METRICS)
    self._shell_rect = frame.shell
    self._scroll_rect = scroll_rect

    self._draw_header(frame.header)

    self._content_height = self._measure_content_height(content_width)
    self._scroll_panel.set_enabled(self.is_visible)
    self._scroll_offset = self._scroll_panel.update(scroll_rect, max(self._content_height, scroll_rect.height))

    rl.begin_scissor_mode(int(scroll_rect.x), int(scroll_rect.y), int(scroll_rect.width), int(scroll_rect.height))
    self._draw_scroll_content(scroll_rect, content_width)
    rl.end_scissor_mode()

    if self._content_height > scroll_rect.height:
      self._scrollbar.render(scroll_rect, self._content_height, self._scroll_offset)

    draw_list_scroll_fades(scroll_rect, self._content_height, self._scroll_offset, AetherListColors.PANEL_BG, fade_height=FADE_HEIGHT)

  def _draw_header(self, rect: rl.Rectangle):
    draw_settings_panel_header(rect, tr("Vehicle Settings"),
                                tr("Configure vehicle fingerprint, driving features, and steering controls."),
                                subtitle_size=22)

    summary_y = rect.y + 44 + self.HEADER_SUBTITLE_HEIGHT + self.HEADER_SUMMARY_GAP
    summary_rect = rl.Rectangle(rect.x, summary_y, rect.width, min(self.HEADER_CARD_HEIGHT, rect.y + rect.height - summary_y))
    self._draw_summary_card(summary_rect)

  def _draw_summary_card(self, rect: rl.Rectangle):
    draw_soft_card(rect, PANEL_STYLE.surface_fill, PANEL_STYLE.surface_border)

    inset = 24
    avail_w = rect.width - inset * 2
    col1_w = avail_w * 0.32
    col2_w = avail_w * 0.20
    col3_w = avail_w * 0.24
    col4_w = avail_w * 0.24

    col1_x = rect.x + inset
    col2_x = col1_x + col1_w
    col3_x = col2_x + col2_w
    col4_x = col3_x + col3_w

    # 1. Current Vehicle
    make = self._controller._get_display_make()
    model = self._controller._get_display_model()
    vehicle_name = f"{make} {model}" if make != tr("None") else tr("No vehicle selected")

    gui_label(rl.Rectangle(col1_x, rect.y + 16, col1_w - 16, 18), tr("CURRENT VEHICLE"), 14, AetherListColors.MUTED, FontWeight.MEDIUM)
    gui_label(rl.Rectangle(col1_x, rect.y + 38, col1_w - 16, 28), vehicle_name, 22, AetherListColors.HEADER, FontWeight.BOLD)

    # 2. Fingerprint
    fingerprint_state = tr("Forced") if self._controller._params.get_bool("ForceFingerprint") else tr("Auto")
    gui_label(rl.Rectangle(col2_x, rect.y + 16, col2_w - 16, 18), tr("FINGERPRINT"), 14, AetherListColors.MUTED, FontWeight.MEDIUM)
    gui_label(rl.Rectangle(col2_x, rect.y + 38, col2_w - 16, 26), fingerprint_state, 20, AetherListColors.HEADER, FontWeight.SEMI_BOLD)

    # 3. Hardware
    cs = starpilot_state.car_state
    hardware_items = []
    if cs.canUsePedal:
      hardware_items.append(tr("Pedal"))
    if cs.hasSASCM:
      hardware_items.append(tr("SASCM"))
    if cs.canUseSDSU:
      hardware_items.append(tr("SDSU"))
    if cs.hasZSS:
      hardware_items.append(tr("ZSS"))

    gui_label(rl.Rectangle(col3_x, rect.y + 16, col3_w - 16, 18), tr("HARDWARE"), 14, AetherListColors.MUTED, FontWeight.MEDIUM)
    if not hardware_items:
      gui_label(rl.Rectangle(col3_x, rect.y + 38, col3_w - 16, 26), tr("Standard"), 18, AetherListColors.MUTED, FontWeight.MEDIUM)
    else:
      draw_status_badges(col3_x, rect.y + 37, hardware_items, PANEL_STYLE)

    # 4. Capabilities
    gui_label(rl.Rectangle(col4_x, rect.y + 16, col4_w - 16, 18), tr("CAPABILITIES"), 14, AetherListColors.MUTED, FontWeight.MEDIUM)

    metrics = []
    if cs.hasRadar:
      metrics.append(tr("Radar"))
    if cs.hasOpenpilotLongitudinal:
      metrics.append(tr("Long"))
    if cs.hasBSM:
      metrics.append(tr("BSM"))
    if cs.hasSNG:
      metrics.append(tr("SNG"))

    if not metrics:
      gui_label(rl.Rectangle(col4_x, rect.y + 38, col4_w - 16, 26), tr("Standard"), 18, AetherListColors.MUTED, FontWeight.MEDIUM)
    else:
      draw_status_badges(col4_x, rect.y + 37, metrics, PANEL_STYLE)

  def _measure_content_height(self, width: float) -> float:
    self._check_rebuild_grid()
    cs = starpilot_state.car_state

    # Left Column heights
    identity_rows = 2
    if cs.isToyota:
      identity_rows += 2
    identity_h = self._section_block_height(self._section_height(identity_rows, ROW_HEIGHT))

    steering_rows = self._build_steering_rows()
    steering_h = self._section_block_height(self._section_height(len(steering_rows), ROW_HEIGHT))

    left_h = identity_h + SECTION_GAP + steering_h

    # Right Column/Features height
    tiles_height = 0.0
    if self._toggle_grid.tiles:
      N = len(self._toggle_grid.tiles)
      gap = self._toggle_grid.gap
      if self._uses_two_columns(width):
        cols = 2
        tile_rows = (N + cols - 1) // cols
        tile_gaps = gap * (tile_rows - 1) if tile_rows > 0 else 0
        tiles_content_h = tile_rows * 130 + tile_gaps
        tiles_height = self._section_block_height(tiles_content_h + 24)
      else:
        avail_w = width - 24
        cols = 3
        tile_rows = (N + cols - 1) // cols
        tile_gaps = gap * (tile_rows - 1) if tile_rows > 0 else 0
        tiles_content_h = tile_rows * 130 + tile_gaps
        tiles_height = SECTION_GAP + self._section_block_height(tiles_content_h + 24)

    if self._uses_two_columns(width):
      return max(left_h, tiles_height)
    return left_h + tiles_height

  def _draw_scroll_content(self, rect: rl.Rectangle, width: float):
    self._interactive_rects.clear()
    y = rect.y + self._scroll_offset
    self._draw_panel_content(y, rect.x, width)

  def _draw_panel_content(self, y: float, x: float, width: float):
    self._check_rebuild_grid()
    cs = starpilot_state.car_state

    identity_rows = [
      {"target_id": "select:CarMake", "type": "select", "title": tr("Car Make"),
       "get_value": self._controller._get_display_make, "pill_width": 160},
      {"target_id": "select:CarModel", "type": "select", "title": tr("Car Model"),
       "get_value": self._controller._get_display_model, "pill_width": 160},
    ]
    if cs.isToyota:
      identity_rows.append({"target_id": "select:LockDoorsTimer", "type": "select",
                    "title": tr("Lock Doors Timer"),
                    "get_value": lambda: _lock_doors_timer_labels().get(float(self._controller._params.get_int("LockDoorsTimer")), f"{self._controller._params.get_int('LockDoorsTimer')}s"),
                    "pill_width": 100})
      identity_rows.append({"target_id": "select:ClusterOffset", "type": "select",
                    "title": tr("Dashboard Speed Offset"),
                    "get_value": lambda: f"{self._controller._params.get_float('ClusterOffset'):.3f}x",
                    "pill_width": 120})

    steering_rows = self._build_steering_rows()

    if self._uses_two_columns(width):
      column_w = self._column_width(width)

      # Left Column: Vehicle Identity & Steering Controls
      curr_y = y
      draw_section_header(rl.Rectangle(x, curr_y, column_w, SECTION_HEADER_HEIGHT), tr("Vehicle Identity"), style=PANEL_STYLE)
      curr_y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
      container_rect = rl.Rectangle(x, curr_y, column_w, len(identity_rows) * ROW_HEIGHT)
      draw_list_group_shell(container_rect, style=PANEL_STYLE)
      for index, row in enumerate(identity_rows):
        row_rect = rl.Rectangle(x, curr_y + index * ROW_HEIGHT, column_w, ROW_HEIGHT)
        self._draw_row(row_rect, row, is_last=index == len(identity_rows) - 1)
      curr_y += len(identity_rows) * ROW_HEIGHT

      curr_y += SECTION_GAP
      draw_section_header(rl.Rectangle(x, curr_y, column_w, SECTION_HEADER_HEIGHT), tr("Steering Controls"), style=PANEL_STYLE)
      curr_y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
      container_rect = rl.Rectangle(x, curr_y, column_w, len(steering_rows) * ROW_HEIGHT)
      draw_list_group_shell(container_rect, style=PANEL_STYLE)
      for index, row in enumerate(steering_rows):
        row_rect = rl.Rectangle(x, curr_y + index * ROW_HEIGHT, column_w, ROW_HEIGHT)
        self._draw_row(row_rect, row, is_last=index == len(steering_rows) - 1)
      left_end_y = curr_y + len(steering_rows) * ROW_HEIGHT

      # Right Column: Features
      if self._toggle_grid.tiles:
        rx = x + column_w + self.COLUMN_GAP
        draw_section_header(rl.Rectangle(rx, y, column_w, SECTION_HEADER_HEIGHT), tr("Features"), style=PANEL_STYLE)
        right_container_y = y + SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP

        N = len(self._toggle_grid.tiles)
        cols = 2
        self._toggle_grid._columns = cols
        gap = self._toggle_grid.gap
        tile_rows = (N + cols - 1) // cols
        tile_gaps = gap * (tile_rows - 1) if tile_rows > 0 else 0
        tiles_content_h = tile_rows * 130 + tile_gaps

        needed_height = tiles_content_h + 24
        left_content_height = left_end_y - right_container_y
        container_h = max(needed_height, left_content_height)

        draw_list_group_shell(rl.Rectangle(rx, right_container_y, column_w, container_h), style=PANEL_STYLE)
        self._toggle_grid.set_parent_rect(self._scroll_rect)
        self._toggle_grid.render(rl.Rectangle(rx + 12, right_container_y + 12, column_w - 24, container_h - 24))
    else:
      # Single Column Stacked Layout
      draw_section_header(rl.Rectangle(x, y, width, SECTION_HEADER_HEIGHT), tr("Vehicle Identity"), style=PANEL_STYLE)
      y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
      container_rect = rl.Rectangle(x, y, width, len(identity_rows) * ROW_HEIGHT)
      draw_list_group_shell(container_rect, style=PANEL_STYLE)
      for index, row in enumerate(identity_rows):
        row_rect = rl.Rectangle(x, y + index * ROW_HEIGHT, width, ROW_HEIGHT)
        self._draw_row(row_rect, row, is_last=index == len(identity_rows) - 1)
      y += len(identity_rows) * ROW_HEIGHT

      y += SECTION_GAP
      draw_section_header(rl.Rectangle(x, y, width, SECTION_HEADER_HEIGHT), tr("Steering Controls"), style=PANEL_STYLE)
      y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
      container_rect = rl.Rectangle(x, y, width, len(steering_rows) * ROW_HEIGHT)
      draw_list_group_shell(container_rect, style=PANEL_STYLE)
      for index, row in enumerate(steering_rows):
        row_rect = rl.Rectangle(x, y + index * ROW_HEIGHT, width, ROW_HEIGHT)
        self._draw_row(row_rect, row, is_last=index == len(steering_rows) - 1)
      y += len(steering_rows) * ROW_HEIGHT

      if self._toggle_grid.tiles:
        y += SECTION_GAP
        draw_section_header(rl.Rectangle(x, y, width, SECTION_HEADER_HEIGHT), tr("Features"), style=PANEL_STYLE)
        y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP

        N = len(self._toggle_grid.tiles)
        cols = 3
        self._toggle_grid._columns = cols
        gap = self._toggle_grid.gap
        avail_w = width - 24
        tile_rows = (N + cols - 1) // cols
        tile_gaps = gap * (tile_rows - 1) if tile_rows > 0 else 0
        tiles_content_h = tile_rows * 130 + tile_gaps

        draw_list_group_shell(rl.Rectangle(x, y, width, tiles_content_h + 24), style=PANEL_STYLE)
        self._toggle_grid.set_parent_rect(self._scroll_rect)
        self._toggle_grid.render(rl.Rectangle(x + 12, y + 12, avail_w, tiles_content_h))

  def _draw_row(self, rect: rl.Rectangle, row: dict, is_last: bool):
    target_id = row["target_id"]
    hovered, pressed = self._interactive_state(target_id, rect)
    row_type = row.get("type", "toggle")

    if row_type == "toggle":
      draw_settings_list_row(
        rect, title=row["title"], subtitle=row.get("subtitle", ""),
        toggle_value=row["get_state"](), hovered=hovered, pressed=pressed,
        is_last=is_last, show_chevron=False, title_size=34, subtitle_size=22,
        style=PANEL_STYLE,
      )
    elif row_type == "select":
      draw_selection_list_row(
        rect, title=row["title"], subtitle=row.get("subtitle", ""),
        action_text=row["get_value"](), hovered=hovered, pressed=pressed,
        is_last=is_last, action_width=188, action_pill=True,
        action_pill_width=row.get("pill_width", 108), action_pill_height=44,
        title_size=34, subtitle_size=22, action_text_size=18,
        row_separator=PANEL_STYLE.divider_color,
        action_fill=PANEL_STYLE.current_fill,
        action_border=PANEL_STYLE.current_border,
        action_text_color=AetherListColors.HEADER,
      )
    elif row_type == "info":
      draw_settings_list_row(
        rect, title=row["title"], value=row["get_value"](),
        hovered=False, pressed=False, is_last=is_last,
        show_chevron=False, title_size=34, subtitle_size=22,
        style=PANEL_STYLE,
      )

  def _build_steering_rows(self) -> list[dict]:
    cs = starpilot_state.car_state
    rows = []
    for key in ("DistanceButtonControl", "LongDistanceButtonControl", "VeryLongDistanceButtonControl"):
      rows.append({"target_id": f"select:{key}", "type": "select", "title": tr(self._controller._action_title(key)),
                    "get_value": lambda k=key: self._controller._get_action_name(k), "pill_width": 140})
    if cs.isBolt and cs.hasPedal and self._controller._params.get_bool("RemapCancelToDistance"):
      for key in ("CancelButtonControl", "LongCancelButtonControl", "VeryLongCancelButtonControl"):
        rows.append({"target_id": f"select:{key}", "type": "select", "title": tr(self._controller._action_title(key)),
                      "get_value": lambda k=key: self._controller._get_action_name(k), "pill_width": 140})
    if not cs.isSubaru:
      rows.append({"target_id": "select:LKASButtonControl", "type": "select", "title": tr("LKAS Button"),
                    "get_value": lambda: self._controller._get_action_name("LKASButtonControl"), "pill_width": 140})
    rows.append({"target_id": "select:MainCruiseButtonControl", "type": "select", "title": tr("CC Main Button"),
                  "get_value": lambda: self._controller._get_action_name("MainCruiseButtonControl"), "pill_width": 140})
    if cs.hasModeStarButtons:
      for key in ("ModeButtonControl", "LongModeButtonControl", "VeryLongModeButtonControl",
                   "StarButtonControl", "LongStarButtonControl", "VeryLongStarButtonControl"):
        rows.append({"target_id": f"select:{key}", "type": "select", "title": tr(self._controller._action_title(key)),
                      "get_value": lambda k=key: self._controller._get_action_name(k), "pill_width": 140})
    return rows


class StarPilotVehicleSettingsLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._make_options, self._models_by_make, self._models_by_value, self._make_by_model = get_fingerprint_catalog()
    self._manager_view = VehicleSettingsManagerView(self)


  def _action_title(self, key: str) -> str:
    titles = {
      "CancelButtonControl": "Cancel Button",
      "DistanceButtonControl": "Distance Button",
      "LongCancelButtonControl": "Cancel (Long Press)",
      "LongDistanceButtonControl": "Distance (Long Press)",
      "VeryLongCancelButtonControl": "Cancel (Very Long)",
      "VeryLongDistanceButtonControl": "Distance (Very Long)",
      "LKASButtonControl": "LKAS Button",
      "MainCruiseButtonControl": "CC Main Button",
      "ModeButtonControl": "Mode Button",
      "LongModeButtonControl": "Mode (Long Press)",
      "VeryLongModeButtonControl": "Mode (Very Long)",
      "StarButtonControl": "Star Button",
      "LongStarButtonControl": "Star (Long Press)",
      "VeryLongStarButtonControl": "Star (Very Long)",
    }
    return titles.get(key, key)

  def _get_action_name(self, key: str) -> str:
    idx = self._params.get_int(key)
    return tr(ACTION_NAME_BY_ID.get(idx, ACTION_NAMES[0]))

  def _get_available_actions(self, key: str | None = None) -> list[str]:
    cs = starpilot_state.car_state
    if key == "MainCruiseButtonControl":
      allowed_ids = {0, 9, 10}
      return [tr(o["name"]) for o in ACTION_OPTIONS if o["id"] in allowed_ids]
    allowed_ids = set(range(9))
    if key == "LKASButtonControl":
      allowed_ids.add(9)
    return [tr(o["name"]) for o in ACTION_OPTIONS
            if o["id"] in allowed_ids and (cs.hasOpenpilotLongitudinal or not o.get("requires_longitudinal", False))]

  def _on_toggle(self, param_key: str):
    if param_key == "DisableOpenpilotLongitudinal":
      current = self._params.get_bool("DisableOpenpilotLongitudinal")
      if not current:
        def on_confirm(res):
          if res == DialogResult.CONFIRM:
            self._params.put_bool("DisableOpenpilotLongitudinal", True)
            starpilot_state.update(force=True)
            if starpilot_state.started:
              HARDWARE.reboot()
        gui_app.push_widget(ConfirmDialog(tr("Disable openpilot longitudinal control?"), tr("Disable"), callback=on_confirm))
      else:
        self._params.put_bool("DisableOpenpilotLongitudinal", False)
        starpilot_state.update(force=True)
      return
    if param_key == "RemapCancelToDistance":
      new_state = not self._params.get_bool("RemapCancelToDistance")
      self._params.put_bool("RemapCancelToDistance", new_state)
      if new_state:
        migrate_cancel_button_controls(self._params)
      starpilot_state.update(force=True)
      return
    current = self._params.get_bool(param_key) if self._params.get(param_key) is not None else False
    self._params.put_bool(param_key, not current)
    starpilot_state.update(force=True)

  def _on_select(self, key: str):
    if key == "CarMake":
      self._on_select_make()
    elif key == "CarModel":
      self._on_select_model()
    elif key == "LockDoorsTimer":
      self._show_lock_timer_selector()
    elif key == "ClusterOffset":
      self._show_offset_selector()
    else:
      self._show_action_picker(key)

  def _on_select_make(self):
    makes = list(self._make_options)
    if not makes:
      gui_app.push_widget(ConfirmDialog(tr("No fingerprint list available."), tr("OK")))
      return
    current_make = self._params.get("CarMake") or ""
    default_make = current_make if current_make in makes else makes[0]

    def on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        self._params.put("CarMake", dialog.selection)
        current_model = self._params.get("CarModel") or ""
        available = {o.value for o in self._models_by_make.get(dialog.selection, ())}
        if current_model not in available:
          self._params.remove("CarModel")
          self._params.remove("CarModelName")
        starpilot_state.update(force=True)

    dialog = MultiOptionDialog(tr("Select Make"), makes, default_make, callback=on_select)
    gui_app.push_widget(dialog)

  def _on_select_model(self):
    make = self._params.get("CarMake") or ""
    if not make:
      gui_app.push_widget(ConfirmDialog(tr("Please select a Car Make first!"), tr("OK")))
      return
    model_options = self._models_by_make.get(make, ())
    if not model_options:
      gui_app.push_widget(ConfirmDialog(tr("No models available for this make."), tr("OK")))
      return
    option_labels = [o.option_label for o in model_options]
    selected_by_label = {o.option_label: o for o in model_options}
    current_model = self._params.get("CarModel") or ""
    current_model_name = self._params.get("CarModelName") or ""
    default_option = next((o.option_label for o in model_options if o.value == current_model and o.label == current_model_name), None)
    if default_option is None:
      default_option = next((o.option_label for o in model_options if o.value == current_model), option_labels[0])

    def on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        opt = selected_by_label[dialog.selection]
        self._params.put("CarModel", opt.value)
        self._params.put("CarModelName", opt.label)
        self._params.put("CarMake", make)
        starpilot_state.update(force=True)

    dialog = MultiOptionDialog(tr("Select Model"), option_labels, default_option, callback=on_select)
    gui_app.push_widget(dialog)

  def _show_action_picker(self, key: str):
    actions = self._get_available_actions(key)
    current = self._get_action_name(key)
    if current not in actions:
      current = actions[0]

    def on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        self._params.put_int(key, ACTION_IDS.get(dialog.selection, 0))

    dialog = MultiOptionDialog(tr(key), actions, current, callback=on_select)
    gui_app.push_widget(dialog)

  def _show_lock_timer_selector(self):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int("LockDoorsTimer", int(val))

    gui_app.push_widget(AetherSliderDialog(tr("Lock Doors Timer"), 0, 300, 5,
                                            self._params.get_int("LockDoorsTimer"), on_close, labels=_lock_doors_timer_labels(), color=PANEL_STYLE.accent))

  def _show_offset_selector(self):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_float("ClusterOffset", float(val))

    gui_app.push_widget(AetherSliderDialog(tr("Dashboard Speed Offset"), 1.000, 1.050, 0.001,
                                            self._params.get_float("ClusterOffset"), on_close, unit="x", color=PANEL_STYLE.accent))

  def _get_display_make(self) -> str:
    make = self._params.get("CarMake") or ""
    if make:
      return make
    model = self._params.get("CarModel") or ""
    if model:
      return self._make_by_model.get(model, tr("None"))
    return tr("None")

  def _get_display_model(self) -> str:
    selected = self._get_selected_model_option()
    if selected is not None:
      return selected.button_label
    model = self._params.get("CarModel") or ""
    model_name = self._params.get("CarModelName") or ""
    make = self._params.get("CarMake") or self._make_by_model.get(model, "")
    if model_name:
      return shorten_model_label(make, model_name) if make else model_name
    if model and model in self._models_by_value:
      return self._models_by_value[model].button_label
    return tr("None")

  def _get_selected_model_option(self) -> FingerprintModelOption | None:
    model = self._params.get("CarModel") or ""
    if not model:
      return None
    model_name = self._params.get("CarModelName") or ""
    make = self._params.get("CarMake") or self._make_by_model.get(model, "")
    if make and model_name:
      for option in self._models_by_make.get(make, ()):
        if option.value == model and option.label == model_name:
          return option
    return self._models_by_value.get(model)
