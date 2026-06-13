from __future__ import annotations

import shutil
import threading
from dataclasses import dataclass, replace
from pathlib import Path

from cereal import log, messaging
import pyray as rl

from openpilot.common.params import Params
from openpilot.selfdrive.ui.ui_state import device, ui_state
from openpilot.system.ui.lib.application import FontWeight, MouseEvent, MousePos, gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop, trn
from openpilot.system.ui.lib.scroll_panel2 import GuiScrollPanel2
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.system.ui.widgets.label import gui_label, gui_text_box
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog

from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AETHER_COMPACT_ROW_HEIGHT,
  AETHER_LIST_METRICS,
  AetherButton,
  AetherListColors,
  AetherScrollbar,
  panel_style_from_color,
  build_list_panel_frame,
  draw_action_pill,
  draw_busy_ring,
  draw_empty_state_card,
  draw_list_panel_shell,
  draw_metric_strip,
  draw_section_header,
  draw_tab_card,
  draw_selection_list_row,
  draw_list_scroll_fades,
  draw_settings_panel_header,
  draw_soft_card,
  init_list_panel,
  _point_hits,
)
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanel
from openpilot.starpilot.common.maps_catalog import (
  MAPS_CATALOG,
  MAP_TOKEN_LABELS,
  MAP_SCHEDULE_LABELS,
  normalize_schedule_value,
  sanitize_selected_locations_csv,
  schedule_label,
)
from openpilot.starpilot.common.maps_selection import COUNTRY_PREFIX, STATE_PREFIX


NetworkType = log.DeviceState.NetworkType

NETWORK_TYPE_LABELS = {
  NetworkType.none: tr_noop("Offline"),
  NetworkType.wifi: tr_noop("Wi-Fi"),
  NetworkType.ethernet: tr_noop("Ethernet"),
  NetworkType.cell2G: tr_noop("2G"),
  NetworkType.cell3G: tr_noop("3G"),
  NetworkType.cell4G: tr_noop("LTE"),
  NetworkType.cell5G: tr_noop("5G"),
}

OFFLINE_MAPS_PATH = Path("/data/media/0/osm/offline")
CANCEL_REQUEST_TIMEOUT = 3.0
HEADER_TOP_OFFSET = 4
HEADER_TITLE_HEIGHT = 40
HEADER_SUBTITLE_HEIGHT = 24
HEADER_BOTTOM_GAP = 12
BROWSER_SECTION_HEADER_HEIGHT = AETHER_LIST_METRICS.section_header_height
BROWSER_SECTION_HEADER_GAP = AETHER_LIST_METRICS.section_header_gap
BROWSER_INSET = AETHER_LIST_METRICS.content_right_gutter
BROWSER_TAB_GAP = AETHER_LIST_METRICS.section_header_gap
BROWSER_CONTEXT_TAB_HEIGHT = 68
BROWSER_REGION_ROW_HEIGHT = AETHER_LIST_METRICS.row_height
BROWSER_EMPTY_STATE_HEIGHT = 128
STATUS_CARD_INSET = BROWSER_INSET
STATUS_BUTTON_HEIGHT = 52
STATUS_BUTTON_GAP = 8
STATUS_REMOVE_HEIGHT = 40
STATUS_METRIC_GAP = 18
STATUS_SELECTION_CHIP_HEIGHT = 30
MAPS_TILE_GREEN = rl.Color(16, 185, 129, 255)
PANEL_STYLE = panel_style_from_color("#10B981")
MAPS_METRICS = replace(AETHER_LIST_METRICS, header_height=240)

COUNTRIES_SECTION = next(section for section in MAPS_CATALOG if section["key"] == "countries")
STATES_SECTION = next(section for section in MAPS_CATALOG if section["key"] == "states")
US_COUNTRY_TOKEN = f"{COUNTRY_PREFIX}US"


def _format_mb(size_bytes: int) -> str:
  mb = size_bytes / (1024 * 1024)
  if mb >= 1024:
    return f"{mb / 1024:.2f} GB"
  return f"{mb:.2f} MB"


def _format_elapsed_ms(elapsed_ms: int) -> str:
  if elapsed_ms <= 0:
    return tr("Calculating...")
  total_seconds = elapsed_ms // 1000
  hours = total_seconds // 3600
  minutes = (total_seconds % 3600) // 60
  seconds = total_seconds % 60
  if hours > 0:
    return f"{hours:d}:{minutes:02d}:{seconds:02d}"
  return f"{minutes:d}:{seconds:02d}"


def _format_eta_ms(elapsed_ms: int, downloaded_files: int, total_files: int) -> str:
  if elapsed_ms <= 0 or downloaded_files <= 0 or total_files <= 0 or downloaded_files >= total_files:
    return tr("Calculating...")
  remaining_files = total_files - downloaded_files
  if remaining_files <= 0:
    return tr("Almost done")
  files_per_ms = downloaded_files / max(elapsed_ms, 1)
  if files_per_ms <= 0:
    return tr("Calculating...")
  remaining_ms = int(remaining_files / files_per_ms)
  return _format_elapsed_ms(remaining_ms)


def _localized_schedule_label(value) -> str:
  return tr(schedule_label(value))


def _selected_token_set(selected_raw: str | bytes | None) -> set[str]:
  normalized = sanitize_selected_locations_csv(selected_raw or "")
  tokens = {token for token in normalized.split(",") if token}
  return tokens


@dataclass(slots=True)
class MapsDownloadState:
  active: bool = False
  cancelled: bool = False
  total_files: int = 0
  downloaded_files: int = 0
  primary_location: str = ""
  location_count: int = 0
  percent: int = 0
  progress_text: str = ""


class MapStatusCard(Widget):
  def __init__(self, controller: "StarPilotMapsLayout"):
    super().__init__()
    self._controller = controller
    self._remove_rect = rl.Rectangle(0, 0, 0, 0)
    self._pressed_remove = False
    self._primary_button = self._child(controller._download_button)
    self._secondary_button = self._child(controller._schedule_button)

  def set_touch_valid_callback(self, touch_callback):
    super().set_touch_valid_callback(touch_callback)
    self._primary_button.set_touch_valid_callback(touch_callback)
    self._secondary_button.set_touch_valid_callback(touch_callback)

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if not self._touch_valid():
      return
    if _point_hits(mouse_pos, self._remove_rect, pad_x=10, pad_y=6) and self._controller._remove_enabled():
      self._pressed_remove = True

  def _handle_mouse_release(self, mouse_pos: MousePos):
    if self._pressed_remove:
      self._pressed_remove = False
      if self._touch_valid() and _point_hits(mouse_pos, self._remove_rect, pad_x=10, pad_y=6) and self._controller._remove_enabled():
        self._controller._on_remove()

  def _render(self, rect: rl.Rectangle):
    draw_soft_card(rect, PANEL_STYLE.surface_fill, PANEL_STYLE.surface_border)

    inset = STATUS_CARD_INSET
    content_x = rect.x + inset
    content_w = rect.width - inset * 2
    actions_w = max(330.0, min(386.0, rect.width * 0.31))
    actions_x = rect.x + rect.width - inset - actions_w
    summary_w = max(250.0, actions_x - 18 - content_x)
    footer_w = min(208.0, max(176.0, summary_w * 0.38))
    metric_gap = 18.0
    metrics_x = content_x + footer_w + metric_gap
    metrics_w = summary_w - footer_w - metric_gap

    title_y = rect.y + 6
    title_text = self._controller._progress_title()
    selection_chip_rect = self._controller._selection_chip_rect(content_x, title_y, summary_w)
    title_w = summary_w
    if selection_chip_rect is not None:
      title_w = selection_chip_rect.x - content_x - 12
      title_width = measure_text_cached(gui_app.font(FontWeight.SEMI_BOLD), title_text, 24, spacing=1).x
      if title_w < 210 or title_width > title_w:
        selection_chip_rect = None
        title_w = summary_w
    gui_label(rl.Rectangle(content_x, title_y, title_w, 24), title_text, 24, AetherListColors.HEADER, FontWeight.SEMI_BOLD)
    if selection_chip_rect is not None:
      draw_action_pill(
        selection_chip_rect,
        self._controller._selected_summary_text(),
        rl.Color(94, 168, 130, 22),
        AetherListColors.SUCCESS_SOFT,
        AetherListColors.HEADER,
        font_size=15,
      )
    gui_text_box(
      rl.Rectangle(content_x, title_y + 28, summary_w, 38),
      self._controller._progress_body(),
      17,
      AetherListColors.SUBTEXT,
      font_weight=FontWeight.NORMAL,
      line_scale=0.94,
    )

    footer_y = rect.y + rect.height - 28
    footer_text = f"{self._controller._network_label()}  •  {tr('Parked') if self._controller._is_parked() else tr('Not parked')}"
    if metrics_w >= 220.0:
      gui_label(rl.Rectangle(content_x, footer_y, footer_w, 16), footer_text, 15, AetherListColors.MUTED, FontWeight.MEDIUM)
      draw_metric_strip(
        rl.Rectangle(metrics_x, rect.y + 72, metrics_w, 30),
        [
          (tr("Storage"), self._controller._storage_text),
          (tr("Last Updated"), self._controller._last_updated_text()),
        ],
        gap=STATUS_METRIC_GAP,
        style=PANEL_STYLE,
        label_top_offset=0,
        value_top_offset=14,
        divider_top_offset=2,
        divider_bottom_offset=16,
      )
    else:
      draw_metric_strip(
        rl.Rectangle(content_x, rect.y + 72, summary_w, 30),
        [
          (tr("Storage"), self._controller._storage_text),
          (tr("Last Updated"), self._controller._last_updated_text()),
        ],
        gap=STATUS_METRIC_GAP,
        style=PANEL_STYLE,
        label_top_offset=0,
        value_top_offset=14,
        divider_top_offset=2,
        divider_bottom_offset=16,
      )

    action_top = rect.y + 12
    col_gap = 10
    action_h = rect.height - 24
    left_col_w = actions_w * 0.42
    right_col_w = actions_w - left_col_w - col_gap
    left_btn_gap = 6
    left_btn_h = (action_h - left_btn_gap) / 2

    self._remove_rect = rl.Rectangle(actions_x, action_top, left_col_w, left_btn_h)
    schedule_rect = rl.Rectangle(actions_x, action_top + left_btn_h + left_btn_gap, left_col_w, left_btn_h)
    primary_rect = rl.Rectangle(actions_x + left_col_w + col_gap, action_top, right_col_w, action_h)

    self._primary_button.render(primary_rect)
    self._secondary_button.render(schedule_rect)

    enabled = self._controller._remove_enabled()
    draw_action_pill(
      self._remove_rect,
      tr("Remove Maps"),
      rl.Color(173, 78, 90, 26 if enabled else 12),
      rl.Color(173, 78, 90, 58 if enabled else 24),
      AetherListColors.HEADER if enabled else AetherListColors.MUTED,
      font_size=16,
    )

    if self._controller._download_state.active:
      center = rl.Vector2(primary_rect.x + primary_rect.width - 22, primary_rect.y + primary_rect.height / 2)
      draw_busy_ring(center, rl.get_time() * 160, PANEL_STYLE.accent, inner_radius=9, outer_radius=13, sweep=210, thickness=20)


class MapBrowserCard(Widget):
  def __init__(self, controller: "StarPilotMapsLayout"):
    super().__init__()
    self._controller = controller
    self._pressed_target: str | None = None
    self._source_rects: dict[str, rl.Rectangle] = {}
    self._context_tab_rects: dict[str, rl.Rectangle] = {}
    self._region_row_rects: dict[str, rl.Rectangle] = {}

  def set_touch_valid_callback(self, touch_callback):
    super().set_touch_valid_callback(touch_callback)

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if not self._touch_valid():
      return
    self._pressed_target = self._target_at(mouse_pos)

  def _handle_mouse_release(self, mouse_pos: MousePos):
    target = self._target_at(mouse_pos) if self._touch_valid() else None
    pressed_target = self._pressed_target
    self._pressed_target = None
    if pressed_target is not None and pressed_target == target:
      self._activate_target(pressed_target)

  def _handle_mouse_event(self, mouse_event: MouseEvent):
    if self._pressed_target is not None and self._target_at(mouse_event.pos) != self._pressed_target:
      self._pressed_target = None

  def _target_at(self, mouse_pos: MousePos) -> str | None:
    parent_rect = getattr(self, "_parent_rect", None)
    if parent_rect is not None and not rl.check_collision_point_rec(mouse_pos, parent_rect):
      return None
    for source_key, rect in self._source_rects.items():
      if _point_hits(mouse_pos, rect, parent_rect, pad_x=6, pad_y=6):
        return f"source:{source_key}"
    for group_key, rect in self._context_tab_rects.items():
      if _point_hits(mouse_pos, rect, parent_rect, pad_x=4, pad_y=4):
        return f"group:{group_key}"
    for token, rect in self._region_row_rects.items():
      if _point_hits(mouse_pos, rect, parent_rect, pad_x=6, pad_y=0):
        return f"region:{token}"
    return None

  def _activate_target(self, target: str):
    if target.startswith("source:"):
      self._controller._select_browse_source(target.split(":", 1)[1])
      return
    if target.startswith("group:"):
      self._controller._set_active_group(target.split(":", 1)[1])
      return
    if target.startswith("region:"):
      self._controller._toggle_region(target.split(":", 1)[1])

  def _render_source_picker(self, rect: rl.Rectangle):
    self._source_rects.clear()

    mouse_pos = gui_app.last_mouse_event.pos
    button_w = (rect.width - BROWSER_TAB_GAP) / 2
    sources = [
      ("us", tr("United States")),
      ("other", tr("Other Countries")),
    ]

    for index, (source_key, title) in enumerate(sources):
      button_rect = rl.Rectangle(rect.x + index * (button_w + BROWSER_TAB_GAP), rect.y, button_w, BROWSER_CONTEXT_TAB_HEIGHT)
      self._source_rects[source_key] = button_rect
      hovered = _point_hits(mouse_pos, button_rect, self._parent_rect, pad_x=6, pad_y=6)
      pressed = self._pressed_target == f"source:{source_key}"
      current = self._controller._active_source_key() == source_key

      draw_tab_card(
        button_rect,
        title,
        current=current,
        hovered=hovered,
        pressed=pressed,
        title_size=28,
        style=PANEL_STYLE,
      )

  def _row_height(self, count: int, row_height: float) -> float:
    return 0.0 if count <= 0 else count * row_height

  def _measure_context_tabs_height(self, width: float) -> float:
    del width
    groups = self._controller._visible_browser_tabs()
    if not groups:
      return 0.0
    return BROWSER_CONTEXT_TAB_HEIGHT

  def _render_context_tabs(self, rect: rl.Rectangle):
    groups = self._controller._visible_browser_tabs()
    self._context_tab_rects.clear()
    if not groups:
      return

    mouse_pos = gui_app.last_mouse_event.pos
    available_w = max(1.0, rect.width)
    tab_gap = BROWSER_TAB_GAP
    tab_w = (available_w - tab_gap * max(0, len(groups) - 1)) / max(1, len(groups))

    for index, group in enumerate(groups):
      tab_rect = rl.Rectangle(rect.x + index * (tab_w + tab_gap), rect.y, tab_w, BROWSER_CONTEXT_TAB_HEIGHT)
      self._context_tab_rects[group["key"]] = tab_rect
      current = self._controller._active_tab_key() == group["key"]
      hovered = _point_hits(mouse_pos, tab_rect, self._parent_rect, pad_x=4, pad_y=4)
      pressed = self._pressed_target == f"group:{group['key']}"

      draw_tab_card(
        tab_rect,
        tr(group["title"]),
        self._controller._group_primary_text(group),
        current=current,
        hovered=hovered,
        pressed=pressed,
        title_size=24,
        subtitle_size=17,
        show_underline=True,
        style=PANEL_STYLE,
      )

  def _render_empty_state(self, rect: rl.Rectangle, title: str, body: str):
    draw_empty_state_card(
      rect,
      title,
      body,
      title_size=32,
      body_size=24,
      body_inset_x=40,
      title_top_padding=24,
      body_height=48,
      border=rl.Color(255, 255, 255, 10),
      style=PANEL_STYLE,
    )

  def _render_region_rows(self, rect: rl.Rectangle, regions: list[dict]):
    if not regions:
      title, body = self._controller._browse_empty_state()
      self._render_empty_state(rect, title, body)
      return

    mouse_pos = gui_app.last_mouse_event.pos
    self._region_row_rects.clear()
    for index, region in enumerate(regions):
      token = region["token"]
      selected = self._controller._get_map_state(token)
      row_rect = rl.Rectangle(rect.x, rect.y + index * BROWSER_REGION_ROW_HEIGHT, rect.width, BROWSER_REGION_ROW_HEIGHT)
      self._region_row_rects[token] = row_rect
      hovered = _point_hits(mouse_pos, row_rect, self._parent_rect, pad_x=6, pad_y=0)
      target_key = f"region:{token}"
      action_text = self._controller._region_action_text(token)
      draw_selection_list_row(
        row_rect,
        title=tr(region["label"]),
        subtitle=self._controller._region_primary_text(token),
        action_text=action_text,
        current=selected,
        hovered=hovered,
        pressed=self._pressed_target == target_key,
        is_last=index == len(regions) - 1,
        action_width=188,
        action_pill=True,
        action_text_size=18,
        action_pill_height=44,
        action_pill_width=132 if selected else 108,
        title_size=34,
        subtitle_size=22,
        row_separator=PANEL_STYLE.divider_color,
        current_bg=PANEL_STYLE.current_fill,
        current_border=PANEL_STYLE.current_border,
        action_fill=rl.Color(94, 168, 130, 18) if selected else rl.Color(255, 255, 255, 8),
        action_border=rl.Color(94, 168, 130, 38) if selected else rl.Color(255, 255, 255, 24),
        action_text_color=AetherListColors.HEADER,
      )

  def _active_browse_regions(self) -> list[dict]:
    return self._controller._browse_regions_for_active_group()

  def _render_section_header(self, rect: rl.Rectangle, title: str, *, count_text: str | None = None):
    draw_section_header(rect, title, trailing_text=count_text or "", title_size=28, trailing_size=22, style=PANEL_STYLE)

  def _measure_height(self, width: float) -> float:
    if self._controller._showing_source_picker():
      del width
      return BROWSER_CONTEXT_TAB_HEIGHT + 20

    total = 10.0
    total += self._measure_context_tabs_height(width) + BROWSER_SECTION_HEADER_GAP
    total += BROWSER_SECTION_HEADER_HEIGHT + BROWSER_SECTION_HEADER_GAP
    region_count = len(self._active_browse_regions())
    total += self._row_height(region_count, BROWSER_REGION_ROW_HEIGHT) if region_count else BROWSER_EMPTY_STATE_HEIGHT
    return total + 10

  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)
    if not self._touch_valid():
      self._pressed_target = None
    draw_soft_card(rect, PANEL_STYLE.surface_fill, PANEL_STYLE.surface_border)
    self._source_rects.clear()
    self._context_tab_rects.clear()
    self._region_row_rects.clear()

    content_x = rect.x + BROWSER_INSET
    content_w = rect.width - BROWSER_INSET * 2
    y = rect.y + 10

    if self._controller._showing_source_picker():
      self._render_source_picker(rl.Rectangle(content_x, y, content_w, BROWSER_CONTEXT_TAB_HEIGHT))
      return

    context_tabs_h = self._measure_context_tabs_height(content_w)
    self._render_context_tabs(rl.Rectangle(content_x, y, content_w, context_tabs_h))
    y += context_tabs_h + BROWSER_SECTION_HEADER_GAP

    self._render_section_header(
      rl.Rectangle(content_x, y, content_w, BROWSER_SECTION_HEADER_HEIGHT),
      tr("Regions"),
      count_text=self._controller._active_group_count_text(),
    )
    y += BROWSER_SECTION_HEADER_HEIGHT + BROWSER_SECTION_HEADER_GAP

    regions = self._active_browse_regions()
    region_h = self._row_height(len(regions), BROWSER_REGION_ROW_HEIGHT) if regions else BROWSER_EMPTY_STATE_HEIGHT
    self._render_region_rows(rl.Rectangle(content_x, y, content_w, region_h), regions)


class StarPilotMapsLayout(StarPilotPanel):
  VIEW_COUNTRIES = 0
  VIEW_STATES = 1

  def __init__(self):
    super().__init__()
    self._params_memory = Params(memory=True)
    self._worker_params = Params()
    self._map_sm = messaging.SubMaster(["mapdExtendedOut", "starpilotCarState"])
    self._scroll_panel = GuiScrollPanel2(horizontal=False)
    self._scrollbar = AetherScrollbar()
    self._scroll_offset = 0.0
    self._content_height = 0.0

    self._storage_text = "0 MB"
    self._has_downloaded_data = False
    self._storage_updated_at = 0.0
    self._storage_refresh_thread: threading.Thread | None = None
    self._storage_refresh_pending = False
    self._storage_refresh_generation = 0
    self._pending_storage_state: tuple[int, str, bool] | None = None
    self._download_started_at: float | None = None
    self._cancel_requested_at: float | None = None
    self._cancel_visual_until = 0.0
    self._download_state = MapsDownloadState()
    self._view_index = self.VIEW_STATES
    self._show_source_picker = True
    self._browse_source_key = "us"
    self._active_state_group_key = "whole_us"
    self._full_us_mode = True
    self._whole_us_context_initialized = False
    self._cached_selected_tokens: set[str] = set()

    self._download_button = self._child(
      AetherButton(
        self._primary_action_label,
        self._on_primary_action,
        enabled=self._primary_action_enabled,
        emphasized=True,
        font_size=24,
        accent_color=MAPS_TILE_GREEN,
      )
    )
    self._schedule_button = self._child(
      AetherButton(
        lambda: tr("Update: {}").format(_localized_schedule_label(self._params.get('PreferredSchedule'))),
        self._on_schedule,
        emphasized=False,
        font_size=20,
      )
    )

    self._status_card = self._child(MapStatusCard(self))
    self._browser_card = self._child(MapBrowserCard(self))

    self._browser_card.set_touch_valid_callback(lambda: self._scroll_panel.is_touch_valid())
    self._status_card.set_touch_valid_callback(lambda: True)

    self._sync_whole_us_view_state()
    self._refresh_storage_cache(force=True)
    self._sync_download_state(force=True)

  def show_event(self):
    super().show_event()
    self._scroll_offset = 0.0
    self._whole_us_context_initialized = False
    self._sync_whole_us_view_state()
    if self._cancel_requested() and self._cancel_requested_at is None:
      self._cancel_requested_at = rl.get_time()
    if self._cancel_requested() and self._cancel_visual_until <= rl.get_time():
      self._cancel_visual_until = rl.get_time() + 2.5
    self._refresh_storage_cache(force=True)
    self._sync_download_state(force=True)

  def hide_event(self):
    super().hide_event()
    self._scroll_offset = 0.0
    self._whole_us_context_initialized = False
    device.set_override_interactive_timeout(None)

  def _update_state(self):
    super()._update_state()
    self._cached_selected_tokens = _selected_token_set(
      self._params.get("MapsSelected", encoding="utf-8") or ""
    )
    self._sync_download_state()
    if self._pending_storage_state is not None:
      generation, storage_text, has_downloaded_data = self._pending_storage_state
      self._pending_storage_state = None
      if generation == self._storage_refresh_generation:
        self._storage_text = storage_text
        self._has_downloaded_data = has_downloaded_data
        self._storage_updated_at = rl.get_time()
      self._storage_refresh_pending = False
    self._refresh_storage_cache()

    if self._download_state.active:
      device.set_override_interactive_timeout(300)
    else:
      device.set_override_interactive_timeout(None)

    if self._cancel_requested_at is not None and not self._download_state.active:
      if (rl.get_time() - self._cancel_requested_at) >= CANCEL_REQUEST_TIMEOUT:
        self._params_memory.remove("CancelDownloadMaps")
        self._cancel_requested_at = None

    if self._cancel_visual_until and rl.get_time() >= self._cancel_visual_until and not self._download_state.active:
      self._cancel_visual_until = 0.0

  def _sync_download_state(self, force: bool = False):
    del force
    self._map_sm.update(0)
    progress = self._map_sm["mapdExtendedOut"].downloadProgress if self._map_sm.valid.get("mapdExtendedOut", False) else None
    active = bool(progress.active) if progress is not None else False

    if active and self._download_started_at is None:
      self._download_started_at = rl.get_time()
    if active:
      self._cancel_requested_at = None
      self._cancel_visual_until = 0.0
    if not self._download_in_flight() and self._download_started_at is not None:
      self._download_started_at = None

    total_files = int(progress.totalFiles) if progress is not None else 0
    downloaded_files = int(progress.downloadedFiles) if progress is not None else 0
    percent = int((downloaded_files * 100) / max(total_files, 1)) if total_files > 0 else 0
    location_count = (len(progress.locationDetails) or len(progress.locations)) if progress is not None else 0
    primary_location = ""
    if progress is not None and len(progress.locationDetails) > 0:
      primary_location = str(progress.locationDetails[0].location)
    elif progress is not None and len(progress.locations) > 0:
      primary_location = str(progress.locations[0])

    progress_text = ""
    if active:
      progress_text = tr("{} / {} ({}%)").format(downloaded_files, total_files, percent)
      if primary_location:
        progress_text = f"{progress_text}  {primary_location}"

    self._download_state = MapsDownloadState(
      active=active,
      cancelled=bool(progress.cancelled) if progress is not None else False,
      total_files=total_files,
      downloaded_files=downloaded_files,
      primary_location=primary_location,
      location_count=location_count,
      percent=percent,
      progress_text=progress_text,
    )

  def _refresh_storage_cache(self, force: bool = False):
    now = rl.get_time()
    if self._storage_refresh_pending:
      return
    if not force and (now - self._storage_updated_at) < 4.0:
      return

    generation = self._storage_refresh_generation + 1
    self._storage_refresh_generation = generation

    def refresh_worker():
      result: tuple[str, bool] | None = None
      try:
        result = self._calculate_storage_state()
      finally:
        if result is None:
          self._storage_refresh_pending = False
        else:
          self._pending_storage_state = (generation, result[0], result[1])

    self._storage_refresh_pending = True
    self._storage_updated_at = now
    self._storage_refresh_thread = threading.Thread(target=refresh_worker, daemon=True)
    self._storage_refresh_thread.start()

  def _calculate_storage_state(self) -> tuple[str, bool]:
    if not OFFLINE_MAPS_PATH.exists():
      return "0 MB", False

    total_size = 0
    has_files = False
    for path in OFFLINE_MAPS_PATH.rglob("*"):
      try:
        if not path.is_file():
          continue
        has_files = True
        total_size += path.stat().st_size
      except OSError:
        continue
    return _format_mb(total_size), has_files

  def _selected_tokens(self) -> set[str]:
    return self._cached_selected_tokens

  def _selected_count(self) -> int:
    return len(self._selected_tokens())

  def _selected_section_count_text(self) -> str:
    count = self._selected_count()
    if count == 0:
      return tr("None selected")
    return tr("{} selected").format(count)

  def _selected_summary_text(self) -> str:
    count = self._selected_count()
    if count == 0:
      return tr("No regions selected")
    return trn("{} region selected", "{} regions selected", count).format(count)

  def _selected_primary_token(self) -> str | None:
    selected = sorted(self._selected_tokens())
    if not selected:
      return None
    return selected[0]

  def _selected_primary_label(self) -> str:
    token = self._selected_primary_token()
    if not token:
      return ""
    return tr(MAP_TOKEN_LABELS.get(token, token))

  def _selection_chip_rect(self, content_x: float, title_y: float, summary_w: float) -> rl.Rectangle | None:
    if self._selected_count() <= 0:
      return None
    text = self._selected_summary_text()
    text_width = measure_text_cached(gui_app.font(FontWeight.SEMI_BOLD), text, 15, spacing=1).x
    chip_w = min(220.0, max(128.0, text_width + 28.0))
    chip_x = content_x + max(0.0, summary_w - chip_w)
    return rl.Rectangle(chip_x, title_y - 2, chip_w, STATUS_SELECTION_CHIP_HEIGHT)

  def _selection_preview_text(self) -> str:
    count = self._selected_count()
    if count <= 0:
      return tr("No regions selected yet")

    primary_label = self._selected_primary_label()
    if count == 1:
      return primary_label
    return tr("{} + {} more").format(primary_label, count - 1)

  def _has_full_us_selected(self) -> bool:
    return US_COUNTRY_TOKEN in self._selected_tokens()

  def _sync_whole_us_view_state(self):
    if self._whole_us_context_initialized:
      return
    if self._has_full_us_selected():
      self._active_state_group_key = "whole_us"
      self._full_us_mode = self._is_states_view()
    self._whole_us_context_initialized = True

  def _is_states_view(self) -> bool:
    return self._view_index == self.VIEW_STATES

  def _showing_source_picker(self) -> bool:
    return self._show_source_picker

  def _active_source_key(self) -> str:
    if self._showing_source_picker():
      return self._browse_source_key
    return "other" if not self._is_states_view() else "us"

  def _select_browse_source(self, source_key: str):
    self._browse_source_key = source_key
    if source_key == "us":
      self._show_source_picker = False
      self._set_active_group("whole_us")
      return
    if source_key == "other":
      self._show_source_picker = False
      self._set_active_group("countries")

  def _is_full_us_mode(self) -> bool:
    return self._is_states_view() and self._full_us_mode

  def _set_full_us_mode(self, enabled: bool):
    self._full_us_mode = bool(enabled) and self._is_states_view()

  def _current_section(self) -> dict:
    return STATES_SECTION if self._is_states_view() else COUNTRIES_SECTION

  def _current_groups(self) -> list[dict]:
    return self._current_section()["groups"]

  def _all_country_regions(self) -> list[dict]:
    return [region for group in COUNTRIES_SECTION["groups"] for region in group["regions"]]

  def _full_us_regions(self) -> list[dict]:
    return [{"token": US_COUNTRY_TOKEN, "label": tr(MAP_TOKEN_LABELS[US_COUNTRY_TOKEN])}]

  def _whole_us_group(self) -> dict:
    return {"key": "whole_us", "title": tr("Whole U.S."), "regions": self._full_us_regions()}

  def _visible_browser_tabs(self) -> list[dict]:
    return [self._whole_us_group(), *STATES_SECTION["groups"], {"key": "countries", "title": tr("Countries"), "regions": []}]

  def _active_tab_key(self) -> str:
    if not self._is_states_view():
      return "countries"
    if self._is_full_us_mode():
      return "whole_us"
    return self._active_state_group_key

  def _set_active_group(self, group_key: str):
    if group_key == "countries":
      self._view_index = self.VIEW_COUNTRIES
      self._full_us_mode = False
      self._browse_source_key = "other"
      return

    self._view_index = self.VIEW_STATES
    self._browse_source_key = "us"
    if group_key == "whole_us":
      self._active_state_group_key = "whole_us"
      self._set_full_us_mode(True)
      return

    group_keys = {group["key"] for group in STATES_SECTION["groups"]}
    if group_key not in group_keys:
      return
    self._full_us_mode = False
    self._active_state_group_key = group_key

  def _active_group(self) -> dict:
    if not self._is_states_view():
      return {"key": "countries", "title": tr("Countries"), "regions": self._all_country_regions()}

    if self._is_full_us_mode():
      return self._whole_us_group()

    group_key = self._active_state_group_key
    for group in STATES_SECTION["groups"]:
      if group["key"] == group_key:
        return group
    fallback = STATES_SECTION["groups"][0]
    self._active_state_group_key = fallback["key"]
    return fallback

  def _active_group_regions(self) -> list[dict]:
    return self._active_group()["regions"]

  def _group_selected_count(self, group: dict) -> int:
    if self._is_states_view() and self._has_full_us_selected() and group["key"] != "whole_us":
      return len(group["regions"])
    return sum(1 for region in group["regions"] if self._get_map_state(region["token"]))

  def _group_primary_text(self, group: dict) -> str:
    if group["key"] == "countries":
      count = sum(1 for region in self._all_country_regions() if self._get_map_state(region["token"]))
      return tr("None selected") if count == 0 else tr("{} selected").format(count)
    if group["key"] == "whole_us":
      return tr("One-tap full set") if not self._get_map_state(US_COUNTRY_TOKEN) else tr("Selected")
    count = self._group_selected_count(group)
    if self._is_states_view():
      return tr("{}/{} states").format(count, len(group["regions"]))
    return tr("None selected") if count == 0 else tr("{} selected").format(count)

  def _active_group_count_text(self) -> str:
    if not self._is_states_view():
      total = len(self._all_country_regions())
      selected_count = sum(1 for region in self._all_country_regions() if self._get_map_state(region["token"]))
      if selected_count <= 0:
        return tr("{} available").format(total)
      return tr("{} selected • {} available").format(selected_count, max(0, total - selected_count))
    if self._is_full_us_mode():
      selected_count = 1 if self._get_map_state(US_COUNTRY_TOKEN) else 0
      return tr("Whole U.S. selected") if selected_count else tr("1 available")
    group = self._active_group()
    total = len(group["regions"])
    selected_count = self._group_selected_count(group)
    if selected_count <= 0:
      return tr("{} available").format(total)
    return tr("{} selected • {} available").format(selected_count, max(0, total - selected_count))

  def _toggle_region(self, token: str):
    self._set_map_state(token, not self._get_map_state(token))

  def _region_primary_text(self, token: str) -> str:
    if self._get_map_state(token):
      return tr("Tap to remove")
    if token == US_COUNTRY_TOKEN and self._is_full_us_mode():
      return tr("Full country package")
    return tr("Tap to add")

  def _region_action_text(self, token: str) -> str:
    if self._get_map_state(token):
      return tr("Selected")
    return tr("Add U.S.") if token == US_COUNTRY_TOKEN and self._is_full_us_mode() else tr("Add")

  def _browse_empty_state(self) -> tuple[str, str]:
    if self._is_states_view() and self._has_full_us_selected():
      return tr("Whole U.S. already selected"), tr("Switch back to the full package above, or remove it if you want to pick individual states.")
    return tr("No regions available"), tr("Switch groups or sources to keep browsing maps.")

  def _browse_regions_for_active_group(self) -> list[dict]:
    if self._is_states_view() and self._has_full_us_selected() and not self._is_full_us_mode():
      return []
    return self._full_us_regions() if self._is_full_us_mode() else self._active_group_regions()

  def _get_map_state(self, token: str) -> bool:
    return token in self._selected_tokens()

  def _set_map_state(self, token: str, state: bool):
    selected = set(self._cached_selected_tokens)
    if state:
      if token == US_COUNTRY_TOKEN:
        selected = {item for item in selected if not item.startswith(STATE_PREFIX)}
        self._active_state_group_key = "whole_us"
        if self._is_states_view():
          self._full_us_mode = True
      elif token.startswith(STATE_PREFIX):
        selected.discard(US_COUNTRY_TOKEN)
        self._full_us_mode = False
      selected.add(token)
    else:
      selected.discard(token)
      if token == US_COUNTRY_TOKEN:
        self._full_us_mode = False
        if self._active_state_group_key == "whole_us":
          self._active_state_group_key = STATES_SECTION["groups"][0]["key"]
    self._params.put("MapsSelected", sanitize_selected_locations_csv(sorted(selected)))
    self._cached_selected_tokens = selected

  def _network_type(self):
    return ui_state.sm["deviceState"].networkType if ui_state.sm.valid.get("deviceState", False) else NetworkType.none

  def _network_label(self) -> str:
    return tr(NETWORK_TYPE_LABELS.get(self._network_type(), tr_noop("Offline")))

  def _is_online(self) -> bool:
    return self._network_type() != NetworkType.none

  def _is_parked(self) -> bool:
    if ui_state.is_offroad():
      return True
    if self._map_sm.valid.get("starpilotCarState", False):
      return bool(self._map_sm["starpilotCarState"].isParked)
    return False

  def _download_requested(self) -> bool:
    return self._params_memory.get_bool("DownloadMaps")

  def _cancel_requested(self) -> bool:
    return self._params_memory.get_bool("CancelDownloadMaps")

  def _is_visually_cancelling(self) -> bool:
    return self._cancel_requested() or (self._cancel_visual_until > rl.get_time())

  def _download_in_flight(self) -> bool:
    return self._download_state.active or self._download_requested()

  def _remove_enabled(self) -> bool:
    return self._has_downloaded_data and self._is_parked() and not self._download_in_flight() and not self._is_visually_cancelling()

  def _download_gate_reason(self) -> str:
    if self._download_in_flight():
      return tr("Download in progress")
    if self._selected_count() == 0:
      return tr("Choose at least one region")
    if not self._is_online():
      return tr("Connect to the internet")
    if not self._is_parked():
      return tr("Park the vehicle to download")
    return ""

  def _primary_action_enabled(self) -> bool:
    if self._is_visually_cancelling():
      return False
    if self._download_in_flight():
      return True
    return self._download_gate_reason() == ""

  def _primary_action_label(self) -> str:
    if self._is_visually_cancelling():
      return tr("Cancelling...")
    if self._download_in_flight():
      return tr("Cancel Download")
    return tr("Download Offline Maps")

  def _on_primary_action(self):
    if self._download_in_flight():
      self._on_cancel()
    else:
      self._on_download()

  def _on_schedule(self):
    localized_options = [(value, tr(label)) for value, label in MAP_SCHEDULE_LABELS.items()]
    options = [label for _, label in localized_options]
    current = _localized_schedule_label(self._params.get("PreferredSchedule"))
    value_by_label = {label: value for value, label in localized_options}

    def on_select(res):
      if res == DialogResult.CONFIRM and dialog.selection:
        selected_value = value_by_label.get(dialog.selection)
        if selected_value is not None:
          self._params.put_int("PreferredSchedule", selected_value)

    dialog = MultiOptionDialog(tr("Auto Update Schedule"), options, current, callback=on_select)
    gui_app.push_widget(dialog)

  def _on_download(self):
    gate_reason = self._download_gate_reason()
    if gate_reason:
      gui_app.push_widget(alert_dialog(gate_reason))
      return

    current_selected = self._params.get("MapsSelected", encoding="utf-8") or ""
    selected_raw = sanitize_selected_locations_csv(current_selected)
    if selected_raw != current_selected:
      self._params.put("MapsSelected", selected_raw)
    if not selected_raw:
      gui_app.push_widget(alert_dialog(tr("Select at least one region before downloading maps.")))
      return

    def on_confirm(res):
      if res == DialogResult.CONFIRM:
        gate_reason = self._download_gate_reason()
        if gate_reason:
          gui_app.push_widget(alert_dialog(gate_reason))
          return
        self._params_memory.put_bool("DownloadMaps", True)
        self._params_memory.remove("CancelDownloadMaps")
        self._download_started_at = rl.get_time()

    gui_app.push_widget(ConfirmDialog(tr("Start downloading offline maps for the selected regions?"), tr("Download"), callback=on_confirm))

  def _on_cancel(self):
    def on_confirm(res):
      if res == DialogResult.CONFIRM:
        if not self._download_in_flight():
          self._cancel_requested_at = None
          self._cancel_visual_until = 0.0
          return
        self._params_memory.put_bool("CancelDownloadMaps", True)
        self._params_memory.remove("DownloadMaps")
        self._cancel_requested_at = rl.get_time()
        self._cancel_visual_until = rl.get_time() + 2.5

    gui_app.push_widget(ConfirmDialog(tr("Cancel the current map download?"), tr("Cancel Download"), callback=on_confirm))

  def _has_downloaded_maps(self) -> bool:
    return self._has_downloaded_data

  def _on_remove(self):
    if not self._remove_enabled():
      if not self._is_parked():
        gui_app.push_widget(alert_dialog(tr("Park to remove downloaded maps.")))
      return

    def on_confirm(res):
      if res == DialogResult.CONFIRM:
        if not self._remove_enabled():
          if not self._is_parked():
            gui_app.push_widget(alert_dialog(tr("Park to remove downloaded maps.")))
          return

        def remove_worker():
          if OFFLINE_MAPS_PATH.exists():
            shutil.rmtree(OFFLINE_MAPS_PATH, ignore_errors=True)
          self._storage_refresh_generation += 1
          self._pending_storage_state = (self._storage_refresh_generation, "0 MB", False)
          self._storage_refresh_pending = False
          self._storage_updated_at = 0.0

        threading.Thread(target=remove_worker, daemon=True).start()
        gui_app.push_widget(alert_dialog(tr("Removing offline maps...")))

    gui_app.push_widget(ConfirmDialog(tr("Delete all downloaded offline map data?"), tr("Remove Maps"), callback=on_confirm))

  def _last_updated_text(self) -> str:
    last_update = self._worker_params.get("LastMapsUpdate", encoding="utf-8")
    return last_update or tr("Never")

  def _progress_title(self) -> str:
    if self._is_visually_cancelling():
      return tr("Cancelling Download")
    if self._download_state.active:
      return tr("Download Readiness")
    if self._download_requested():
      return tr("Download Readiness")
    if self._has_downloaded_maps():
      return tr("Offline Maps")
    return tr("Download Readiness")

  def _progress_body(self) -> str:
    if self._download_state.active:
      elapsed_ms = int((rl.get_time() - (self._download_started_at or rl.get_time())) * 1000)
      elapsed_text = _format_elapsed_ms(elapsed_ms)
      eta_text = _format_eta_ms(elapsed_ms, self._download_state.downloaded_files, self._download_state.total_files)
      if self._download_state.primary_location:
        return tr("{}\nElapsed {} | ETA {}").format(self._download_state.progress_text, elapsed_text, eta_text)
      return tr("{} / {} ({}%)\nElapsed {} | ETA {}").format(
        self._download_state.downloaded_files,
        self._download_state.total_files,
        self._download_state.percent,
        elapsed_text,
        eta_text,
      )

    if self._is_visually_cancelling():
      return tr("Stop request sent. The current transfer will wind down safely.")

    if self._download_requested():
      return tr("Preparing the selected regions for download.")

    gate_reason = self._download_gate_reason()
    if gate_reason:
      if self._selected_count() == 0:
        return tr("Pick regions below, then start the first offline download.")
      return gate_reason
    return tr("Ready to download {}.").format(self._selection_preview_text())

  def _measure_content_height(self, width: float) -> float:
    return self._browser_card._measure_height(width)

  def _draw_scroll_content(self, rect: rl.Rectangle, width: float):
    self._browser_card.set_parent_rect(rect)

    y = rect.y + self._scroll_offset

    browser_height = self._browser_card._measure_height(width)
    self._browser_card.render(rl.Rectangle(rect.x, y, width, browser_height))

  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)
    frame, scroll_rect, content_width = init_list_panel(rect, PANEL_STYLE, MAPS_METRICS)

    hdr = frame.header
    draw_settings_panel_header(hdr, tr("Map Data"), tr("Use offline maps for speed-limit control and keep only the regions you need."),
                                max_title_width=1.0, max_subtitle_width=0.60)

    header_status_y = hdr.y + 48 + HEADER_SUBTITLE_HEIGHT + 12
    header_status_rect = rl.Rectangle(hdr.x, header_status_y, hdr.width, hdr.y + hdr.height - header_status_y - HEADER_BOTTOM_GAP)
    self._status_card.render(header_status_rect)

    scroll_content_rect = rl.Rectangle(scroll_rect.x, scroll_rect.y, scroll_rect.width, scroll_rect.height)
    self._content_height = self._measure_content_height(content_width)
    self._scroll_panel.set_enabled(self.is_visible)
    self._scroll_offset = self._scroll_panel.update(scroll_content_rect, max(self._content_height, scroll_content_rect.height))

    rl.begin_scissor_mode(int(scroll_content_rect.x), int(scroll_content_rect.y), int(scroll_content_rect.width), int(scroll_content_rect.height))
    self._draw_scroll_content(scroll_content_rect, content_width)
    rl.end_scissor_mode()

    if self._content_height > scroll_content_rect.height:
      self._scrollbar.render(scroll_content_rect, self._content_height, self._scroll_offset)

    draw_list_scroll_fades(scroll_content_rect, self._content_height, self._scroll_offset, AetherListColors.PANEL_BG)
