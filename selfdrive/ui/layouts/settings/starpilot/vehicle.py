from __future__ import annotations

import math
import threading
import time

import pyray as rl

from openpilot.system.hardware import HARDWARE
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AETHER_LIST_METRICS,
  AetherSliderDialog,
  COMPACT_PANEL_METRICS,
  DEFAULT_PANEL_STYLE,
  PanelManagerView,
  RowToggleTile,
  SPACING,
  SettingRow,
  TileGrid,
  TOGGLE_MIN_HEIGHT,
  TOGGLE_ROW_HEIGHT,
  GROUP_HEADER_GAP,
  GROUP_HEADER_HEIGHT,
  GROUP_HEADER_LINE_GAP,
  draw_group_header,
  draw_list_group_shell,
  draw_rounded_fill,
  draw_rounded_stroke,
  draw_settings_list_row,
  draw_text_fit_common,
  snap_rect,
  with_alpha,
)
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.selfdrive.ui.lib.fingerprint_catalog import (
  FingerprintModelOption,
  format_fingerprint_value,
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
  {"id": 11, "name": tr_noop("Favorite #1")},
  {"id": 12, "name": tr_noop("Favorite #2")},
  {"id": 13, "name": tr_noop("Favorite #3")},
]
ACTION_NAMES = [o["name"] for o in ACTION_OPTIONS]
ACTION_NAME_BY_ID = {o["id"]: o["name"] for o in ACTION_OPTIONS}


def _lock_doors_timer_labels():
  labels: dict[float, str] = {0.0: tr("Never")}
  for i in range(5, 305, 5):
    labels[float(i)] = f"{i}s"
  return labels


SECTION_GAP = AETHER_LIST_METRICS.section_gap
ROW_HEIGHT = 125.0
PANEL_STYLE = DEFAULT_PANEL_STYLE


class VehicleSettingsManagerView(PanelManagerView):
  METRICS = COMPACT_PANEL_METRICS

  def __init__(self, controller: "StarPilotVehicleSettingsLayout"):
    super().__init__()
    self._controller = controller
    self._shell_rect = rl.Rectangle(0, 0, 0, 0)
    if self.PANEL_STYLE.toggle_row_mode:
      self._toggle_grid = TileGrid(columns=1, padding=SPACING.md, min_tile_height=TOGGLE_MIN_HEIGHT)
    else:
      self._toggle_grid = TileGrid(columns=2, padding=12, min_tile_height=130.0)
    self.register_page_grid(self._toggle_grid)
    self._last_make = ""
    self._last_model = ""

  @property
  def vertical_scrolling_disabled(self) -> bool:
    return True

  def show_event(self):
    super().show_event()
    starpilot_state.update(force=True)
    self._rebuild_toggle_grid()

  def _build_identity_rows(self) -> list[SettingRow]:
    cs = starpilot_state.car_state
    fp = lambda: self._controller._params.get_bool("ForceFingerprint")
    rows = [
      SettingRow("ForceFingerprint", "toggle", tr_noop("Disable Fingerprinting"),
                 subtitle=tr_noop("Manually select vehicle instead of auto-detecting."),
                 get_state=fp,
                 set_state=lambda s: self._controller._on_toggle("ForceFingerprint")),
      SettingRow("CarMake", "value", tr_noop("Car Make"),
                 get_value=self._controller._get_display_make,
                 on_click=lambda: self._controller._on_select("CarMake"),
                 enabled=fp),
      SettingRow("CarModel", "value", tr_noop("Car Model"),
                 get_value=self._controller._get_display_model,
                 on_click=lambda: self._controller._on_select("CarModel"),
                 enabled=fp),
    ]
    if cs.isToyota:
      rows.append(SettingRow("LockDoorsTimer", "value", tr_noop("Lock Doors Timer"),
                 get_value=lambda: _lock_doors_timer_labels().get(
                   float(self._controller._params.get_int("LockDoorsTimer")),
                   f"{self._controller._params.get_int('LockDoorsTimer')}s"),
                 on_click=lambda: self._controller._on_select("LockDoorsTimer")))
      rows.append(SettingRow("ClusterOffset", "value", tr_noop("Dashboard Speed Offset"),
                 get_value=lambda: f"{self._controller._params.get_float('ClusterOffset'):.3f}x",
                 on_click=lambda: self._controller._on_select("ClusterOffset")))
    return rows

  def _combo_value(self, keys: tuple[str, ...]) -> str:
    first_action = self._controller._get_action_name(keys[0])
    mapped_count = sum(1 for k in keys if self._controller._params.get_int(k) != 0)
    if mapped_count > 1:
      return f"{first_action} (+{mapped_count - 1})"
    return first_action

  def _build_steering_rows(self) -> list[SettingRow]:
    cs = starpilot_state.car_state
    rows = []

    dist_keys = ("DistanceButtonControl", "LongDistanceButtonControl", "VeryLongDistanceButtonControl")
    rows.append(SettingRow(
      "combo:distance", "value", tr_noop("Distance Button"),
      get_value=lambda k=dist_keys: self._combo_value(k),
      on_click=lambda: self._controller._on_select("combo:distance"),
    ))

    if cs.isBolt and cs.hasPedal and self._controller._params.get_bool("RemapCancelToDistance"):
      cancel_keys = ("CancelButtonControl", "LongCancelButtonControl", "VeryLongCancelButtonControl")
      rows.append(SettingRow(
        "combo:cancel", "value", tr_noop("Cancel Button"),
        get_value=lambda k=cancel_keys: self._combo_value(k),
        on_click=lambda: self._controller._on_select("combo:cancel"),
      ))

    if not cs.isSubaru:
      rows.append(SettingRow("LKASButtonControl", "value", tr_noop("LKAS Button"),
                   get_value=lambda: self._controller._get_action_name("LKASButtonControl"),
                   on_click=lambda: self._controller._on_select("LKASButtonControl")))

    rows.append(SettingRow("MainCruiseButtonControl", "value", tr_noop("CC Main Button"),
                 get_value=lambda: self._controller._get_action_name("MainCruiseButtonControl"),
                 on_click=lambda: self._controller._on_select("MainCruiseButtonControl")))

    if cs.hasModeStarButtons:
      mode_keys = ("ModeButtonControl", "LongModeButtonControl", "VeryLongModeButtonControl")
      star_keys = ("StarButtonControl", "LongStarButtonControl", "VeryLongStarButtonControl")
      rows.append(SettingRow(
        "combo:mode", "value", tr_noop("Mode Button"),
        get_value=lambda k=mode_keys: self._combo_value(k),
        on_click=lambda: self._controller._on_select("combo:mode"),
      ))
      rows.append(SettingRow(
        "combo:star", "value", tr_noop("Star Button"),
        get_value=lambda k=star_keys: self._combo_value(k),
        on_click=lambda: self._controller._on_select("combo:star"),
      ))

    return rows

  def _draw_row(self, rect: rl.Rectangle, row: SettingRow, is_last: bool):
    target_id = f"{row.type}:{row.id}"
    hovered, pressed = self._interactive_state(target_id, rect)
    enabled = row.enabled() if row.enabled is not None else True
    subtitle = row.disabled_label if not enabled and row.disabled_label else (tr(row.subtitle) if row.subtitle else "")

    row_h = rect.height
    if row_h < 90:
      title_size = 36
      subtitle_size = 26
      value_size = 32
    elif row_h < 105:
      title_size = 42
      subtitle_size = 32
      value_size = 38
    else:
      title_size = 49
      subtitle_size = 38
      value_size = 44

    if row.type == "value" or row.id.startswith("combo:"):
      value_text = row.get_value() if row.get_value else ""
      draw_settings_list_row(rect, title=tr(row.title), subtitle=subtitle,
                             value=value_text, enabled=enabled,
                             hovered=hovered, pressed=pressed,
                             is_last=is_last, show_chevron=row.on_click is not None,
                             title_size=title_size, subtitle_size=subtitle_size, value_size=value_size,
                             style=PANEL_STYLE)
    elif row.type == "toggle":
      toggle_value = row.get_state() if row.get_state else False
      draw_settings_list_row(rect, title=tr(row.title), subtitle=subtitle,
                             toggle_value=toggle_value, enabled=enabled,
                             hovered=hovered, pressed=pressed,
                             is_last=is_last, show_chevron=False,
                             title_size=title_size, subtitle_size=subtitle_size,
                             style=PANEL_STYLE)

  def _draw_section(self, y: float, x: float, width: float, title: str, rows: list[SettingRow], row_height: float = ROW_HEIGHT) -> float:
    hdr_oh = GROUP_HEADER_HEIGHT + GROUP_HEADER_LINE_GAP + GROUP_HEADER_GAP
    group_h = len(rows) * row_height + hdr_oh + 4
    draw_list_group_shell(rl.Rectangle(x, y, width, group_h), style=PANEL_STYLE)
    current_y = y + 4
    current_y = draw_group_header(x + 24, current_y, width - 48, tr(title))
    for i, row in enumerate(rows):
      self._draw_row(rl.Rectangle(x, current_y, width, row_height), row, i == len(rows) - 1)
      current_y += row_height
    return y + group_h

  def _draw_scroll_content(self, rect: rl.Rectangle, width: float):
    y = rect.y + self._scroll_offset
    identity_rows = self._build_identity_rows()
    steering_rows = self._build_steering_rows()

    if self._uses_two_columns(width):
      col_w = self._column_width(width)
      rx = rect.x + col_w + self.COLUMN_GAP

      draw_list_group_shell(rl.Rectangle(rect.x, y, col_w, self._container_h), style=PANEL_STYLE)
      row_y = y + 4
      row_y = draw_group_header(rect.x + 24, row_y, col_w - 48, tr("Vehicle Identity"))
      for i, row in enumerate(identity_rows):
        self._draw_row(rl.Rectangle(rect.x, row_y, col_w, self._left_row_height),
                       row, i == len(identity_rows) - 1 and not steering_rows)
        row_y += self._left_row_height

      if steering_rows:
        row_y = draw_group_header(rect.x + 24, row_y, col_w - 48, tr("Steering Controls"))
        for i, row in enumerate(steering_rows):
          self._draw_row(rl.Rectangle(rect.x, row_y, col_w, self._left_row_height),
                         row, i == len(steering_rows) - 1)
          row_y += self._left_row_height

      if self._toggle_grid.tiles:
        draw_list_group_shell(rl.Rectangle(rx, y, col_w, self._container_h), style=PANEL_STYLE)
        tile_y = y + 4
        tile_y = draw_group_header(rx + 24, tile_y, col_w - 48, tr("Features"))
        avail_h = self._container_h - (tile_y - y)
        self._render_page_grid(self._toggle_grid, rl.Rectangle(rx + 12, tile_y, col_w - 24, max(0.0, avail_h - 12)))
    else:
      y = self._draw_section(y, rect.x, width, tr("Vehicle Identity"), identity_rows, self._left_row_height)
      y += SECTION_GAP
      y = self._draw_section(y, rect.x, width, tr("Steering Controls"), steering_rows, self._left_row_height)
      y += SECTION_GAP

      if self._toggle_grid.tiles:
        if not PANEL_STYLE.toggle_row_mode:
          self._toggle_grid._columns = 3
        avail = width - 24
        th = self.measure_page_grid_height(self._toggle_grid, avail)
        hdr_oh = GROUP_HEADER_HEIGHT + GROUP_HEADER_LINE_GAP + GROUP_HEADER_GAP
        group_h = th + 24 + 4 + hdr_oh
        draw_list_group_shell(rl.Rectangle(rect.x, y, width, group_h), style=PANEL_STYLE)
        features_y = y + 4
        features_y = draw_group_header(rect.x + 24, features_y, width - 48, tr("Features"))
        self._render_page_grid(self._toggle_grid, rl.Rectangle(rect.x + 12, features_y, avail, max(0.0, group_h - (features_y - y) - 12)))

  def _measure_content_height(self, width: float) -> float:
    self._check_rebuild_grid()
    identity_rows = self._build_identity_rows()
    steering_rows = self._build_steering_rows()
    total_rows = len(identity_rows) + len(steering_rows)

    tiles_h = 0.0
    if self._toggle_grid.tiles:
      if self._uses_two_columns(width):
        self._toggle_grid._columns = 1
        col_w = self._column_width(width)
        tiles_h = self.measure_page_grid_height(self._toggle_grid, col_w - 24)
      else:
        self._toggle_grid._columns = 2
        tiles_h = self.measure_page_grid_height(self._toggle_grid, width - 24)

    if self._uses_two_columns(width):
      hdr_oh = GROUP_HEADER_HEIGHT + GROUP_HEADER_LINE_GAP + GROUP_HEADER_GAP
      subsection_overhead = hdr_oh + 4
      if steering_rows:
        subsection_overhead += hdr_oh

      avail_h = self._scroll_rect.height if self._scroll_rect else 760.0
      avail_for_rows = max(100.0, avail_h - subsection_overhead)
      if total_rows > 0:
        self._left_row_height = max(76.0, min(ROW_HEIGHT, avail_for_rows / total_rows))
      else:
        self._left_row_height = ROW_HEIGHT

      left_content_h = total_rows * self._left_row_height + subsection_overhead
      self._container_h = min(avail_h, max(left_content_h, tiles_h))

      total_h = self._compute_two_column_height(self._container_h)
      self._container_h = total_h
      return total_h

    hdr_oh = GROUP_HEADER_HEIGHT + GROUP_HEADER_LINE_GAP + GROUP_HEADER_GAP
    identity_natural_h = hdr_oh + 4 + len(identity_rows) * ROW_HEIGHT
    steering_natural_h = hdr_oh + 4 + len(steering_rows) * ROW_HEIGHT
    left_natural_h = identity_natural_h + SECTION_GAP + steering_natural_h
    tiles_overhead = 4 + hdr_oh + 24 if tiles_h else 0
    return left_natural_h + tiles_h + tiles_overhead

  def _build_driving_toggles(self) -> list[dict]:
    cs = starpilot_state.car_state
    toggles = []

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
    if cs.isGM and cs.hasOpenpilotLongitudinal:
      toggles.append({
        "title": tr("CAN Ignition Only"),
        "subtitle": tr("Use Panda firmware that ignores the physical ignition line and starts only from CAN ignition."),
        "get_state": lambda: self._controller._params.get_bool("IgnoreIgnitionLine"),
        "set_state": lambda s: self._controller._on_panda_firmware_toggle("IgnoreIgnitionLine", tr("CAN Ignition Only requires a Panda firmware update.")),
      })
      toggles.append({
        "title": tr("Remote Start Panda"),
        "get_state": lambda: self._controller._params.get_bool("RemoteStartBootsComma"),
        "set_state": lambda s: self._controller._on_panda_firmware_toggle("RemoteStartBootsComma", tr("Remote Start requires a Panda firmware update.")),
      })
    if cs.isGM and cs.isVolt and not cs.hasSNG:
      toggles.append({
        "title": tr("Volt SNG Hack"),
        "get_state": lambda: self._controller._params.get_bool("VoltSNG"),
        "set_state": lambda s: self._controller._on_toggle("VoltSNG"),
      })
    if cs.isJeep:
      toggles.append({
        "title": tr("Jeep Brake Hold"),
        "subtitle": tr("Hold after ACC times out at a stop and resume when traffic moves."),
        "get_state": lambda: self._controller._params.get_bool("JeepBrakeHold"),
        "set_state": lambda s: self._controller._on_toggle("JeepBrakeHold"),
      })

    if cs.isSubaru:
      toggles.append({
        "title": tr("Stop and Go"),
        "get_state": lambda: self._controller._params.get_bool("SubaruSNG"),
        "set_state": lambda s: self._controller._on_toggle("SubaruSNG"),
      })
      if self._controller._params.get_bool("SubaruSNG"):
        toggles.append({
          "title": tr("Manual Parking Brake SNG"),
          "get_state": lambda: self._controller._params.get_bool("SubaruSNGManualParkingBrake"),
          "set_state": lambda s: self._controller._on_toggle("SubaruSNGManualParkingBrake"),
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
    if cs.isBolt and cs.hasPedal:
      toggles.append({
        "title": tr("Remap Cancel Button"),
        "subtitle": tr("Treat the Cancel button as an extra mappable steering-wheel button."),
        "get_state": lambda: self._controller._params.get_bool("RemapCancelToDistance"),
        "set_state": lambda s: self._controller._on_toggle("RemapCancelToDistance"),
      })

    if cs.isHKGCanFd and cs.hasOpenpilotLongitudinal:
      toggles.append({
        "title": tr("EV Remote Climate"),
        "get_state": lambda: self._controller._params.get_bool("HKGRemoteStartBootsComma"),
        "set_state": lambda s: self._controller._on_panda_firmware_toggle("HKGRemoteStartBootsComma", tr("EV Remote Climate requires a Panda firmware update.")),
      })
      toggles.append({
        "title": tr("Nostalgia Mode"),
        "subtitle": tr("Use the left paddle to pause openpilot acceleration and braking."),
        "get_state": lambda: self._controller._params.get_bool("NostalgiaMode"),
        "set_state": lambda s: self._controller._on_toggle("NostalgiaMode"),
      })

    return toggles

  def _rebuild_toggle_grid(self):
    defs = self._build_driving_toggles()
    page_size = min(4, self._compute_page_size(TOGGLE_ROW_HEIGHT))
    self._set_toggle_pages([defs[i:i+page_size] for i in range(0, len(defs), page_size)])

  def _check_rebuild_grid(self):
    current_make = self._controller._get_display_make()
    current_model = self._controller._get_display_model()
    if current_make != self._last_make or current_model != self._last_model:
      self._last_make = current_make
      self._last_model = current_model
      self._rebuild_toggle_grid()

  def _on_frame_created(self, frame):
    self._shell_rect = frame.shell

  def _activate_target(self, target_id: str | None):
    if not target_id:
      return
    prefix, _, value = target_id.partition(":")
    if prefix == "toggle":
      self._controller._on_toggle(value)
    elif prefix == "value":
      self._controller._on_select(value)


class ButtonActionComboDialog(Widget):
  def __init__(self, controller: "StarPilotVehicleSettingsLayout", title: str,
               keys: tuple[str, ...], labels: tuple[str, ...]):
    super().__init__()
    self._controller = controller
    self._title = title
    self._keys = keys
    self._labels = labels
    self._snapshot = {key: controller._params.get_int(key) for key in keys}
    self._pressed_zone: str | None = None
    self._font_title = gui_app.font(FontWeight.BOLD)
    self._font_btn = gui_app.font(FontWeight.SEMI_BOLD)
    self._ok_offset = 0.0
    self._cancel_offset = 0.0
    self._ok_target = 0.0
    self._cancel_target = 0.0
    self._row_rects: list[rl.Rectangle] = []
    self._cancel_rect = rl.Rectangle(0, 0, 0, 0)
    self._ok_rect = rl.Rectangle(0, 0, 0, 0)

  def _handle_mouse_press(self, mouse_pos):
    for i, rect in enumerate(self._row_rects):
      if rl.check_collision_point_rec(mouse_pos, rect):
        self._pressed_zone = f"row:{i}"
        return
    if rl.check_collision_point_rec(mouse_pos, self._cancel_rect):
      self._pressed_zone = "cancel"
      self._cancel_target = 1.0
      return
    if rl.check_collision_point_rec(mouse_pos, self._ok_rect):
      self._pressed_zone = "ok"
      self._ok_target = 1.0

  def _handle_mouse_release(self, mouse_pos):
    zone = self._pressed_zone
    self._pressed_zone = None
    if not zone:
      return

    if zone.startswith("row:"):
      idx = int(zone.split(":")[1])
      if idx < len(self._row_rects) and rl.check_collision_point_rec(mouse_pos, self._row_rects[idx]):
        self._controller._show_action_picker(self._keys[idx])
      return

    if zone == "cancel":
      self._cancel_target = 0.0
      if rl.check_collision_point_rec(mouse_pos, self._cancel_rect):
        for k, v in self._snapshot.items():
          self._controller._params.put_int(k, v)
        gui_app.pop_widget()
      return

    if zone == "ok":
      self._ok_target = 0.0
      if rl.check_collision_point_rec(mouse_pos, self._ok_rect):
        gui_app.pop_widget()

  def _render(self, rect):
    sw = gui_app.width
    sh = gui_app.height
    rl.draw_rectangle(0, 0, sw, sh, rl.Color(0, 0, 0, 160))

    dialog_w = min(2320, int(rect.width - 40))
    dialog_h = max(min(1015, int(rect.height - 40)), 968)
    dx = rect.x + (rect.width - dialog_w) / 2
    dy = rect.y + (rect.height - dialog_h) / 2
    d_rect = snap_rect(rl.Rectangle(int(dx), int(dy), dialog_w, dialog_h))

    btn_y = int(dy + dialog_h - 160 - 87)
    btn_pair_w = 600 + 40 + 600
    btn_start_x = int(dx + (dialog_w - btn_pair_w) / 2)
    self._cancel_rect = rl.Rectangle(btn_start_x, btn_y, 600, 160)
    self._ok_rect = rl.Rectangle(btn_start_x + 600 + 40, btn_y, 600, 160)

    row_margin = 80
    self._row_rects = []
    for i in range(len(self._keys)):
      self._row_rects.append(rl.Rectangle(
        int(dx + row_margin), int(dy + 130 + i * (170 + 40)),
        dialog_w - 2 * row_margin, 170,
      ))

    mouse_pos = gui_app.last_mouse_event.pos

    draw_rounded_fill(d_rect, rl.Color(10, 12, 16, 255), radius_px=35)
    draw_rounded_stroke(d_rect, rl.Color(255, 255, 255, 16), radius_px=35)
    rl.draw_rectangle_rec(rl.Rectangle(d_rect.x, d_rect.y, d_rect.width, 3), PANEL_STYLE.accent)

    title_size = 64
    ts = measure_text_cached(self._font_title, self._title, title_size)
    rl.draw_text_ex(self._font_title, self._title,
                    rl.Vector2(int(dx + (dialog_w - ts.x) / 2), int(dy + 87)),
                    title_size, 0, rl.WHITE)

    font_label = gui_app.font(FontWeight.MEDIUM)
    font_value = gui_app.font(FontWeight.MEDIUM)
    value_fs = 48
    title_fs = 48

    for i in range(len(self._keys)):
      row_rect = self._row_rects[i]
      hovered = rl.check_collision_point_rec(mouse_pos, row_rect)
      pressed = self._pressed_zone == f"row:{i}"

      bg = rl.Color(255, 255, 255, 4)
      if pressed:
        bg = rl.Color(255, 255, 255, 12)
      elif hovered:
        bg = rl.Color(255, 255, 255, 8)
      draw_rounded_fill(row_rect, bg, radius_px=8)
      draw_rounded_stroke(row_rect, rl.Color(255, 255, 255, 6), radius_px=8)

      if i < len(self._keys) - 1:
        sep_y = int(row_rect.y + row_rect.height - 1)
        rl.draw_line(int(row_rect.x + 24), sep_y, int(row_rect.x + row_rect.width - 24), sep_y, rl.Color(255, 255, 255, 16))

      title_x = int(row_rect.x + 24)
      title_y = int(row_rect.y + (row_rect.height - title_fs) / 2)
      rl.draw_text_ex(self._font_title, self._labels[i], rl.Vector2(title_x, title_y), title_fs, 0, rl.WHITE)

      action_name = self._controller._get_action_name(self._keys[i])
      value_left = int(title_x + 350)
      value_right = int(row_rect.x + row_rect.width - 24)
      available_w = value_right - value_left
      text_w = measure_text_cached(font_label, action_name, value_fs).x
      if text_w <= available_w:
        val_x = value_right - text_w
        val_y = int(row_rect.y + (row_rect.height - value_fs) / 2)
        rl.draw_text_ex(font_value, action_name, rl.Vector2(val_x, val_y), value_fs, 0, rl.WHITE)
      else:
        draw_text_fit_common(
          font_value, action_name,
          rl.Vector2(value_left, int(row_rect.y + (row_rect.height - value_fs) / 2)),
          available_w, value_fs, color=rl.WHITE,
        )

    dt = rl.get_frame_time()
    self._ok_offset += (self._ok_target - self._ok_offset) * (1 - math.exp(-dt / 0.060))
    self._cancel_offset += (self._cancel_target - self._cancel_offset) * (1 - math.exp(-dt / 0.060))

    c_y = self._cancel_rect.y + min(1.0, 10 * self._cancel_offset * 0.1)
    c_face = snap_rect(rl.Rectangle(self._cancel_rect.x, c_y, 600, 160))
    c_hovered = rl.check_collision_point_rec(mouse_pos, self._cancel_rect)
    c_pressed = self._pressed_zone == "cancel"

    if c_pressed:
      c_fill = rl.Color(50, 54, 64, 255)
      c_border = rl.Color(255, 255, 255, 40)
    elif c_hovered:
      c_fill = rl.Color(40, 44, 54, 255)
      c_border = rl.Color(255, 255, 255, 30)
    else:
      c_fill = rl.Color(34, 38, 48, 255)
      c_border = rl.Color(255, 255, 255, 20)

    draw_rounded_fill(c_face, c_fill, radius_px=41)
    draw_rounded_stroke(c_face, c_border, radius_px=41)
    c_text = tr("CANCEL")
    cts = measure_text_cached(self._font_btn, c_text, 49)
    rl.draw_text_ex(self._font_btn, c_text,
                    rl.Vector2(int(c_face.x + (c_face.width - cts.x) / 2),
                               int(c_face.y + (c_face.height - cts.y) / 2)),
                    49, 0, rl.WHITE)

    o_y = self._ok_rect.y + min(1.0, 10 * self._ok_offset * 0.1)
    o_face = snap_rect(rl.Rectangle(self._ok_rect.x, o_y, 600, 160))

    draw_rounded_fill(o_face, PANEL_STYLE.accent, radius_px=41)
    draw_rounded_stroke(o_face, with_alpha(PANEL_STYLE.accent, 150), radius_px=41)
    o_text = tr("OK")
    ots = measure_text_cached(self._font_btn, o_text, 49)
    rl.draw_text_ex(self._font_btn, o_text,
                    rl.Vector2(int(o_face.x + (o_face.width - ots.x) / 2),
                               int(o_face.y + (o_face.height - ots.y) / 2)),
                    49, 0, rl.WHITE)


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
    if param_key == "ForceFingerprint":
      self._manager_view._rebuild_toggle_grid()

  def _on_panda_firmware_toggle(self, param_key: str, prompt: str):
    current = self._params.get_bool(param_key) if self._params.get(param_key) is not None else False
    new_state = not current

    def flash_and_reboot():
      self._params_memory.put_bool("FlashPanda", True)
      while self._params_memory.get_bool("FlashPanda"):
        time.sleep(0.1)
      HARDWARE.reboot()

    def on_confirm(res):
      if res != DialogResult.CONFIRM:
        starpilot_state.update(force=True)
        self._manager_view._rebuild_toggle_grid()
        return
      self._params.put_bool(param_key, new_state)
      threading.Thread(target=flash_and_reboot, daemon=True).start()
      starpilot_state.update(force=True)
      self._manager_view._rebuild_toggle_grid()
      gui_app.push_widget(alert_dialog(tr("Panda flashing started. Device will reboot when finished.")))

    gui_app.push_widget(ConfirmDialog(prompt, tr("Flash"), callback=on_confirm))

  def _on_select(self, key: str):
    if key.startswith("combo:"):
      self._show_button_combo_dialog(key)
      return
    if key in ("CarMake", "CarModel") and not self._params.get_bool("ForceFingerprint"):
      return
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

  def _show_button_combo_dialog(self, key: str):
    combo_configs = {
      "combo:distance": {
        "title": tr_noop("Distance Button"),
        "keys": ("DistanceButtonControl", "LongDistanceButtonControl", "VeryLongDistanceButtonControl"),
        "labels": (tr_noop("Press"), tr_noop("Long Press"), tr_noop("Very Long")),
      },
      "combo:cancel": {
        "title": tr_noop("Cancel Button"),
        "keys": ("CancelButtonControl", "LongCancelButtonControl", "VeryLongCancelButtonControl"),
        "labels": (tr_noop("Press"), tr_noop("Long Press"), tr_noop("Very Long")),
      },
      "combo:mode": {
        "title": tr_noop("Mode Button"),
        "keys": ("ModeButtonControl", "LongModeButtonControl", "VeryLongModeButtonControl"),
        "labels": (tr_noop("Press"), tr_noop("Long Press"), tr_noop("Very Long")),
      },
      "combo:star": {
        "title": tr_noop("Star Button"),
        "keys": ("StarButtonControl", "LongStarButtonControl", "VeryLongStarButtonControl"),
        "labels": (tr_noop("Press"), tr_noop("Long Press"), tr_noop("Very Long")),
      },
    }
    config = combo_configs.get(key)
    if config is None:
      return
    gui_app.push_widget(ButtonActionComboDialog(
      self, tr(config["title"]), config["keys"],
      tuple(tr(l) for l in config["labels"]),
    ))

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
    cs = starpilot_state.car_state
    if key == "MainCruiseButtonControl":
      allowed_ids = {0, 9, 10, 11, 12, 13}
      options = [o for o in ACTION_OPTIONS if o["id"] in allowed_ids]
    else:
      allowed_ids = set(range(9)) | {11, 12, 13}
      if key == "LKASButtonControl":
        allowed_ids.add(9)
      options = [o for o in ACTION_OPTIONS
                 if o["id"] in allowed_ids and (cs.hasOpenpilotLongitudinal or not o.get("requires_longitudinal", False))]

    option_labels = [tr(o["name"]) for o in options]
    option_ids = [o["id"] for o in options]

    current_id = self._params.get_int(key)
    current = next((tr(o["name"]) for o in options if o["id"] == current_id), option_labels[0])

    def on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection in option_labels:
        idx = option_labels.index(dialog.selection)
        self._params.put_int(key, option_ids[idx])

    dialog = MultiOptionDialog(tr(self._action_title(key)), option_labels, current, callback=on_select)
    gui_app.push_widget(dialog)

  def _show_lock_timer_selector(self):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_int("LockDoorsTimer", int(val))

    gui_app.push_widget(AetherSliderDialog(tr("Lock Doors Timer"), 0, 300, 5,
                                            self._params.get_int("LockDoorsTimer"), on_close,
                                            labels=_lock_doors_timer_labels(), color=PANEL_STYLE.accent))

  def _show_offset_selector(self):
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        self._params.put_float("ClusterOffset", float(val))

    gui_app.push_widget(AetherSliderDialog(tr("Dashboard Speed Offset"), 1.000, 1.050, 0.001,
                                            self._params.get_float("ClusterOffset"), on_close,
                                            unit="x", color=PANEL_STYLE.accent))

  def _get_display_make(self) -> str:
    make = self._params.get("CarMake") or ""
    if make:
      return make
    model = self._params.get("CarModel") or ""
    if model:
      return self._make_by_model.get(model, format_fingerprint_value(model.split("_", 1)[0]))
    return tr("Auto") if not self._params.get_bool("ForceFingerprint") else tr("None")

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
    if model:
      return format_fingerprint_value(model)
    return tr("Auto") if not self._params.get_bool("ForceFingerprint") else tr("None")

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
