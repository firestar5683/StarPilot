from __future__ import annotations

import shutil
import threading
from dataclasses import dataclass, replace

from cereal import log, messaging
import pyray as rl

from openpilot.common.params import Params
from openpilot.selfdrive.ui.ui_state import device, ui_state
from openpilot.system.ui.lib.application import FontWeight, gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop, trn
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.system.ui.widgets.label import gui_label, gui_text_box
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog

from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AETHER_LIST_METRICS,
  AetherButton,
  AetherListColors,
  AetherSegmentedControl,
  DEFAULT_PANEL_STYLE,
  PanelManagerView,
  aether_begin_scissor_mode,
  aether_end_scissor_mode,
  draw_action_pill,
  draw_busy_ring,
  draw_empty_state_card,
  draw_list_group_shell,
  draw_metric_strip,
  draw_section_header,
  draw_selection_list_row,
  with_alpha,
)
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage
from openpilot.starpilot.common.maps_catalog import (
  MAPS_CATALOG,
  MAP_TOKEN_LABELS,
  MAP_SCHEDULE_LABELS,
  sanitize_selected_locations_csv,
  schedule_label,
)
from openpilot.starpilot.common.maps_download_progress import MAPS_STORAGE_CACHE_PARAM, load_maps_storage_cache
from openpilot.starpilot.common.maps_selection import COUNTRY_PREFIX
from openpilot.starpilot.common.starpilot_variables import MAPS_PATH as OFFLINE_MAPS_PATH


NetworkType = log.DeviceState.NetworkType

CANCEL_REQUEST_TIMEOUT = 3.0
PANEL_STYLE = DEFAULT_PANEL_STYLE
MAPS_METRICS = replace(AETHER_LIST_METRICS, header_height=0)

COUNTRIES_SECTION = next(section for section in MAPS_CATALOG if section["key"] == "countries")
STATES_SECTION = next(section for section in MAPS_CATALOG if section["key"] == "states")
US_COUNTRY_TOKEN = f"{COUNTRY_PREFIX}US"

ALL_US_STATE_TOKENS = frozenset({
  region["token"] for group in STATES_SECTION["groups"] for region in group["regions"]
})

REGIONAL_PACKAGES = {
  "pkg:midwest": {
    "title": tr_noop("U.S. Midwest Region (12 States)"),
    "subtitle": tr_noop("IL, IN, IA, KS, MI, MN, MO, NE, ND, OH, SD, WI"),
    "tokens": frozenset({r["token"] for g in STATES_SECTION["groups"] if g["key"] == "midwest" for r in g["regions"]}),
  },
  "pkg:northeast": {
    "title": tr_noop("U.S. Northeast Region (9 States)"),
    "subtitle": tr_noop("CT, ME, MA, NH, NJ, NY, PA, RI, VT"),
    "tokens": frozenset({r["token"] for g in STATES_SECTION["groups"] if g["key"] == "northeast" for r in g["regions"]}),
  },
  "pkg:south": {
    "title": tr_noop("U.S. South Region (17 States)"),
    "subtitle": tr_noop("AL, AR, DE, DC, FL, GA, KY, LA, MD, MS, NC, OK, SC, TN, TX, VA, WV"),
    "tokens": frozenset({r["token"] for g in STATES_SECTION["groups"] if g["key"] == "south" for r in g["regions"]}),
  },
  "pkg:west": {
    "title": tr_noop("U.S. West Region (13 States)"),
    "subtitle": tr_noop("AK, AZ, CA, CO, HI, ID, MT, NV, NM, OR, UT, WA, WY"),
    "tokens": frozenset({r["token"] for g in STATES_SECTION["groups"] if g["key"] == "west" for r in g["regions"]}),
  },
  "pkg:territories": {
    "title": tr_noop("U.S. Territories (5 Territories)"),
    "subtitle": tr_noop("AS, GU, MP, PR, VI"),
    "tokens": frozenset({r["token"] for g in STATES_SECTION["groups"] if g["key"] == "territories" for r in g["regions"]}),
  },
}

STATUS_CARD_HEIGHT = 232.0
SEGMENTED_CONTROL_HEIGHT = 68.0
BROWSER_SECTION_HEADER_HEIGHT = 56.0
BROWSER_REGION_ROW_HEIGHT = 104.0
BROWSER_EMPTY_STATE_HEIGHT = 128.0
BROWSER_INSET = 18.0

HEADER_GAP = 16.0
SUBHEADER_GAP = 12.0
LIST_TOP_GAP = 12.0

FIXED_HEADER_HEIGHT = STATUS_CARD_HEIGHT + HEADER_GAP + SEGMENTED_CONTROL_HEIGHT + SUBHEADER_GAP + BROWSER_SECTION_HEADER_HEIGHT + LIST_TOP_GAP


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
  return {token for token in normalized.split(",") if token}


@dataclass(slots=True)
class MapsDownloadState:
  active: bool = False
  cancelled: bool = False
  total_files: int = 0
  downloaded_files: int = 0
  primary_location: str = ""
  percent: int = 0
  progress_text: str = ""


class MapsManagerView(PanelManagerView):
  METRICS = replace(MAPS_METRICS, header_height=FIXED_HEADER_HEIGHT)
  PANEL_STYLE = PANEL_STYLE

  def __init__(self, controller: StarPilotMapsLayout):
    super().__init__()
    self._controller = controller
    self._remove_rect = rl.Rectangle(0, 0, 0, 0)

    self._source_segmented_control = self._child(
      AetherSegmentedControl(
        [tr("U.S. States & Regions"), tr("Other Countries")],
        self._controller._get_source_segment_index,
        self._controller._on_source_segment_change,
        style=PANEL_STYLE,
        suppress_background=True,
      )
    )

  def _measure_content_height(self, content_width: float) -> float:
    downloaded, downloadable = self._controller._browse_regions_for_active_view()
    total_rows = len(downloaded) + len(downloadable)
    if total_rows <= 0:
      return BROWSER_EMPTY_STATE_HEIGHT
    h = total_rows * BROWSER_REGION_ROW_HEIGHT
    if downloaded and downloadable:
      h += BROWSER_SECTION_HEADER_HEIGHT + 16.0
    return h

  def _target_at(self, mouse_pos):
    if rl.check_collision_point_rec(mouse_pos, self._remove_rect):
      return "action:remove_maps"
    return super()._target_at(mouse_pos)

  def _draw_header(self, scroll_rect: rl.Rectangle):
    content_width = scroll_rect.width
    # 1. Pinned Status Card
    status_rect = rl.Rectangle(scroll_rect.x, scroll_rect.y, content_width, STATUS_CARD_HEIGHT)
    self._draw_status_card(status_rect)

    # 2. Pinned Source Segmented Control ([ U.S. States & Regions | Other Countries ])
    seg_y = scroll_rect.y + STATUS_CARD_HEIGHT + HEADER_GAP
    seg_rect = rl.Rectangle(scroll_rect.x + BROWSER_INSET, seg_y, content_width - BROWSER_INSET * 2, SEGMENTED_CONTROL_HEIGHT)
    self._source_segmented_control.render(seg_rect)

    # 3. Pinned Master Section Header
    header_y = seg_y + SEGMENTED_CONTROL_HEIGHT + SUBHEADER_GAP
    draw_section_header(
      rl.Rectangle(scroll_rect.x + BROWSER_INSET, header_y, content_width - BROWSER_INSET * 2, BROWSER_SECTION_HEADER_HEIGHT),
      tr("Map Packages & Regions"),
      trailing_text=self._controller._active_view_count_text(),
      title_size=36,
      trailing_size=24,
      style=PANEL_STYLE,
    )

  def _draw_scroll_content(self, scroll_rect: rl.Rectangle, content_width: float):
    rows_top_y = scroll_rect.y
    rows_visible_h = scroll_rect.height
    rows_scissor_rect = rl.Rectangle(scroll_rect.x, rows_top_y, content_width, rows_visible_h)

    aether_begin_scissor_mode(
      int(rows_scissor_rect.x),
      int(rows_scissor_rect.y),
      int(rows_scissor_rect.width),
      int(rows_scissor_rect.height),
    )

    downloaded, downloadable = self._controller._browse_regions_for_active_view()
    if not downloaded and not downloadable:
      title, body = self._controller._browse_empty_state()
      draw_empty_state_card(
        rl.Rectangle(scroll_rect.x + BROWSER_INSET, rows_top_y + self._scroll_offset, content_width - BROWSER_INSET * 2, BROWSER_EMPTY_STATE_HEIGHT),
        title,
        body,
        title_size=32,
        body_size=24,
        border=with_alpha(PANEL_STYLE.surface_border, 10),
        style=PANEL_STYLE,
      )
      aether_end_scissor_mode()
      return

    y = rows_top_y + self._scroll_offset

    # ── TOP SECTION: Downloaded / Installed Maps ──
    if downloaded:
      for index, region in enumerate(downloaded):
        token = region["token"]
        row_rect = rl.Rectangle(scroll_rect.x + BROWSER_INSET, y, content_width - BROWSER_INSET * 2, BROWSER_REGION_ROW_HEIGHT)
        target_id = f"region:{token}"
        hovered, pressed = self._interactive_state(target_id, row_rect, pad_y=0)

        draw_selection_list_row(
          row_rect,
          title=tr(region["label"]),
          subtitle=tr("Downloaded on device"),
          action_text=tr("Downloaded"),
          current=True,
          hovered=hovered,
          pressed=pressed,
          is_last=index == len(downloaded) - 1 and not downloadable,
          action_width=164,
          action_pill=True,
          action_text_size=26,
          action_pill_height=56,
          action_pill_width=154,
          title_size=32,
          subtitle_size=22,
          row_separator=PANEL_STYLE.divider_color,
          current_bg=PANEL_STYLE.current_fill,
          current_border=PANEL_STYLE.current_border,
          action_fill=with_alpha(AetherListColors.SUCCESS_SOFT, 36),
          action_border=with_alpha(AetherListColors.SUCCESS, 60),
          action_text_color=AetherListColors.HEADER,
        )
        y += BROWSER_REGION_ROW_HEIGHT

      # ── THIN DIVIDER LINE + SECTION HEADER: Separating Downloaded from Downloadable ──
      if downloadable:
        y += 8.0
        draw_section_header(
          rl.Rectangle(scroll_rect.x + BROWSER_INSET, y, content_width - BROWSER_INSET * 2, BROWSER_SECTION_HEADER_HEIGHT),
          tr("Available for Download"),
          trailing_text=tr("{} available").format(len(downloadable)),
          title_size=30,
          trailing_size=22,
          style=PANEL_STYLE,
        )
        y += BROWSER_SECTION_HEADER_HEIGHT + 8.0

    # ── BOTTOM SECTION: Available / Downloadable Maps ──
    for index, region in enumerate(downloadable):
      token = region["token"]
      selected = self._controller._get_map_state(token)
      row_rect = rl.Rectangle(scroll_rect.x + BROWSER_INSET, y, content_width - BROWSER_INSET * 2, BROWSER_REGION_ROW_HEIGHT)
      target_id = f"region:{token}"
      hovered, pressed = self._interactive_state(target_id, row_rect, pad_y=0)

      action_text = self._controller._region_action_text(token)
      draw_selection_list_row(
        row_rect,
        title=tr(region["label"]),
        subtitle=self._controller._region_primary_text(token),
        action_text=action_text,
        current=selected,
        hovered=hovered,
        pressed=pressed,
        is_last=index == len(downloadable) - 1,
        action_width=164,
        action_pill=True,
        action_text_size=26,
        action_pill_height=56,
        action_pill_width=154 if selected else 128,
        title_size=32,
        subtitle_size=22,
        row_separator=PANEL_STYLE.divider_color,
        current_bg=PANEL_STYLE.current_fill,
        current_border=PANEL_STYLE.current_border,
        action_fill=with_alpha(AetherListColors.SUCCESS_SOFT, 24) if selected else rl.Color(255, 255, 255, 8),
        action_border=with_alpha(AetherListColors.SUCCESS, 48) if selected else rl.Color(255, 255, 255, 20),
        action_text_color=AetherListColors.HEADER,
      )
      y += BROWSER_REGION_ROW_HEIGHT

    aether_end_scissor_mode()

  def _draw_status_card(self, rect: rl.Rectangle):
    draw_list_group_shell(rect, style=PANEL_STYLE)

    inset = 24.0
    actions_w = min(400.0, max(320.0, rect.width * 0.36))
    actions_x = rect.x + rect.width - inset - actions_w
    content_x = rect.x + inset
    summary_w = max(240.0, actions_x - 20.0 - content_x)

    # Title (32pt Bold)
    title_text = self._controller._progress_title()
    gui_label(rl.Rectangle(content_x, rect.y + 18, summary_w, 34), title_text, 32, AetherListColors.HEADER, FontWeight.SEMI_BOLD)

    # Selection Summary Badge next to title if selected (24pt, height 38)
    if self._controller._selected_count() > 0:
      chip_text = self._controller._selected_summary_text()
      title_measured_w = measure_text_cached(gui_app.font(FontWeight.SEMI_BOLD), title_text, 32, spacing=1).x
      chip_width = measure_text_cached(gui_app.font(FontWeight.SEMI_BOLD), chip_text, 22, spacing=1).x + 30.0
      chip_x = content_x + title_measured_w + 16.0
      if chip_x + chip_width <= content_x + summary_w:
        draw_action_pill(
          rl.Rectangle(chip_x, rect.y + 16, chip_width, 38),
          chip_text,
          with_alpha(AetherListColors.SUCCESS_SOFT, 30),
          AetherListColors.SUCCESS_SOFT,
          AetherListColors.HEADER,
          font_size=24,
        )

    # Subtitle / Body Progress Description (26pt)
    gui_text_box(
      rl.Rectangle(content_x, rect.y + 58, summary_w, 54),
      self._controller._progress_body(),
      26,
      AetherListColors.SUBTEXT,
      font_weight=FontWeight.NORMAL,
      line_scale=0.95,
    )

    # Telemetry Strip (Storage & Last Updated — Label 24pt, Value 32pt, value_top_offset=30 for zero overlap)
    metrics = [
      (tr("Storage"), self._controller._storage_text),
      (tr("Last Updated"), self._controller._last_updated_text()),
    ]
    draw_metric_strip(
      rl.Rectangle(content_x, rect.y + 128, summary_w, 72),
      metrics,
      gap=36.0,
      min_col_width=140.0,
      label_size=24,
      value_size=32,
      style=PANEL_STYLE,
      label_top_offset=0,
      value_top_offset=30,
      divider_top_offset=4,
      divider_bottom_offset=54,
    )

    # Action Column
    primary_h = 84.0
    primary_rect = rl.Rectangle(actions_x, rect.y + 20, actions_w, primary_h)
    self._controller._download_button.render(primary_rect)

    if self._controller._download_state.active:
      center = rl.Vector2(primary_rect.x + primary_rect.width - 28, primary_rect.y + primary_rect.height / 2)
      draw_busy_ring(center, rl.get_time() * 160, PANEL_STYLE.accent, inner_radius=10, outer_radius=14, sweep=210, thickness=20)

    # Bottom Row Actions: Schedule Button & Remove Maps Pill (64px height)
    bottom_y = rect.y + 116.0
    bottom_h = 64.0
    col_gap = 10.0
    sched_w = (actions_w - col_gap) * 0.58
    remove_w = (actions_w - col_gap) * 0.42

    sched_rect = rl.Rectangle(actions_x, bottom_y, sched_w, bottom_h)
    self._controller._schedule_button.render(sched_rect)

    self._remove_rect = rl.Rectangle(actions_x + sched_w + col_gap, bottom_y, remove_w, bottom_h)
    enabled = self._controller._remove_enabled()
    hovered = rl.check_collision_point_rec(gui_app.last_mouse_event.pos, self._remove_rect)
    pressed = self._pressed_target == "action:remove_maps"

    remove_bg = with_alpha(AetherListColors.DANGER_SOFT, 36 if (pressed or hovered) else (24 if enabled else 12))
    remove_border = with_alpha(AetherListColors.DANGER, 90 if (pressed or hovered) else (56 if enabled else 24))
    draw_action_pill(
      self._remove_rect,
      tr("Remove"),
      remove_bg,
      remove_border,
      AetherListColors.HEADER if enabled else AetherListColors.MUTED,
      font_size=26,
    )

  def _activate_target(self, target_id: str | None):
    if not target_id:
      return
    if target_id == "action:remove_maps":
      self._controller._on_remove()
      return
    if target_id.startswith("region:"):
      self._controller._toggle_region(target_id.split(":", 1)[1])


class StarPilotMapsLayout(_SettingsPage):
  VIEW_STATES = 0
  VIEW_COUNTRIES = 1

  def __init__(self):
    super().__init__()
    self._params_memory = Params(memory=True)
    self._worker_params = Params()
    self._map_sm = messaging.SubMaster(["mapdExtendedOut", "starpilotCarState"])

    self._storage_text = tr("Calculating...")
    self._storage_known = False
    self._has_downloaded_data = False
    self._storage_updated_at = 0.0
    self._download_started_at: float | None = None
    self._cancel_requested_at: float | None = None
    self._cancel_visual_until = 0.0
    self._download_state = MapsDownloadState()
    self._view_index = self.VIEW_STATES
    self._cached_selected_tokens: set[str] = set()

    self._download_button = self._child(
      AetherButton(
        self._primary_action_label,
        self._on_primary_action,
        enabled=self._primary_action_enabled,
        emphasized=True,
      )
    )
    self._schedule_button = self._child(
      AetherButton(
        lambda: tr("Update: {}").format(_localized_schedule_label(self._params.get('PreferredSchedule'))),
        self._on_schedule,
        emphasized=False,
      )
    )

    self._manager_view = MapsManagerView(self)

    self._refresh_storage_state(force=True)
    self._sync_download_state(force=True)

  def show_event(self):
    super().show_event()
    self._refresh_storage_state(force=True)
    raw_selected = self._params.get("MapsSelected", encoding="utf-8") or ""
    self._cached_selected_tokens = _selected_token_set(raw_selected)

    if self._cancel_requested() and self._cancel_requested_at is None:
      self._cancel_requested_at = rl.get_time()
    if self._cancel_requested() and self._cancel_visual_until <= rl.get_time():
      self._cancel_visual_until = rl.get_time() + 2.5
    self._sync_download_state(force=True)

  def hide_event(self):
    super().hide_event()
    device.set_override_interactive_timeout(None)

  def _update_state(self):
    super()._update_state()
    self._cached_selected_tokens = _selected_token_set(
      self._params.get("MapsSelected", encoding="utf-8") or ""
    )
    self._sync_download_state()
    self._refresh_storage_state()

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
      percent=percent,
      progress_text=progress_text,
    )

  def _refresh_storage_state(self, force: bool = False):
    now = rl.get_time()
    if not force and (now - self._storage_updated_at) < 4.0:
      return

    cache = load_maps_storage_cache(self._worker_params.get(MAPS_STORAGE_CACHE_PARAM, encoding="utf-8") or "")
    total_size = cache.storage_bytes
    self._storage_known = cache.storage_known
    self._has_downloaded_data = bool(cache.maps_present)
    self._storage_text = _format_mb(total_size) if total_size is not None else tr("Calculating...")
    self._storage_updated_at = now

  def _selected_tokens(self) -> set[str]:
    return self._cached_selected_tokens

  def _selected_count(self) -> int:
    tokens = self._selected_tokens()
    if US_COUNTRY_TOKEN in tokens:
      return len(ALL_US_STATE_TOKENS)
    return len(tokens)

  def _selected_summary_text(self) -> str:
    count = self._selected_count()
    if count == 0:
      return tr("No regions selected")
    if US_COUNTRY_TOKEN in self._selected_tokens():
      return tr("Whole U.S. (56 states)")
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
    if token == US_COUNTRY_TOKEN:
      return tr("Whole U.S.")
    return tr(MAP_TOKEN_LABELS.get(token, token))

  def _selection_preview_text(self) -> str:
    count = self._selected_count()
    if count <= 0:
      return tr("No regions selected yet")
    if US_COUNTRY_TOKEN in self._selected_tokens():
      return tr("Whole U.S. package")
    primary_label = self._selected_primary_label()
    if count == 1:
      return primary_label
    return tr("{} + {} more").format(primary_label, count - 1)

  def _has_full_us_selected(self) -> bool:
    tokens = self._selected_tokens()
    return (US_COUNTRY_TOKEN in tokens) or ALL_US_STATE_TOKENS.issubset(tokens)

  def _is_states_view(self) -> bool:
    return self._view_index == self.VIEW_STATES

  def _get_source_segment_index(self) -> int:
    return 0 if self._is_states_view() else 1

  def _on_source_segment_change(self, idx: int):
    self._view_index = self.VIEW_STATES if idx == 0 else self.VIEW_COUNTRIES

  def _all_country_regions(self) -> list[dict]:
    regions = [region for group in COUNTRIES_SECTION["groups"] for region in group["regions"]]
    return sorted(regions, key=lambda r: tr(r["label"]))

  def _all_us_states_regions(self) -> list[dict]:
    regions = [region for group in STATES_SECTION["groups"] for region in group["regions"]]
    return sorted(regions, key=lambda r: tr(r["label"]))

  def _bulk_package_regions(self) -> list[dict]:
    return [
      {"token": US_COUNTRY_TOKEN, "label": tr("Whole U.S. (All 50 States & Territories)")},
      *[
        {"token": key, "label": tr(spec["title"])}
        for key, spec in REGIONAL_PACKAGES.items()
      ]
    ]

  def _active_view_count_text(self) -> str:
    if not self._is_states_view():
      total = len(self._all_country_regions())
      selected_count = sum(1 for region in self._all_country_regions() if self._get_map_state(region["token"]))
    else:
      total = len(self._all_us_states_regions())
      selected_count = self._selected_count()
      if self._has_full_us_selected():
        return tr("Whole U.S. Selected")

    if selected_count <= 0:
      return tr("{} available - Tap to select").format(total)
    return tr("{} selected | {} available").format(selected_count, max(0, total - selected_count))

  def _toggle_region(self, token: str):
    self._set_map_state(token, not self._get_map_state(token))

  def _is_region_downloaded(self, token: str) -> bool:
    """Returns True ONLY if map data is actually downloaded on disk AND token is part of installed set."""
    if not self._has_downloaded_data:
      return False
    return self._get_map_state(token)

  def _region_primary_text(self, token: str) -> str:
    if token == US_COUNTRY_TOKEN:
      return tr("Master Package - Full country map data")
    if token in REGIONAL_PACKAGES:
      return tr(REGIONAL_PACKAGES[token]["subtitle"])
    if self._get_map_state(token):
      return tr("Selected for download")
    return tr("Tap to select state")

  def _region_action_text(self, token: str) -> str:
    if self._get_map_state(token):
      return tr("Selected")
    return tr("Add")

  def _browse_empty_state(self) -> tuple[str, str]:
    return tr("No regions available"), tr("Switch sources to keep browsing maps.")

  def _browse_regions_for_active_view(self) -> tuple[list[dict], list[dict]]:
    """Partition active view regions into (downloaded_on_device, available_for_download)."""
    if not self._is_states_view():
      all_regions = self._all_country_regions()
    else:
      all_regions = [*self._bulk_package_regions(), *self._all_us_states_regions()]

    # If NO map data exists on disk, ZERO regions are downloaded on device!
    if not self._has_downloaded_data:
      return [], all_regions

    downloaded = []
    downloadable = []
    for region in all_regions:
      token = region["token"]
      if self._is_region_downloaded(token):
        downloaded.append(region)
      else:
        downloadable.append(region)

    return downloaded, downloadable

  def _get_map_state(self, token: str) -> bool:
    tokens = self._selected_tokens()
    if not tokens:
      return False
    if US_COUNTRY_TOKEN in tokens:
      return True
    if token == US_COUNTRY_TOKEN:
      return ALL_US_STATE_TOKENS.issubset(tokens)
    if token in REGIONAL_PACKAGES:
      return REGIONAL_PACKAGES[token]["tokens"].issubset(tokens)
    return token in tokens

  def _set_map_state(self, token: str, state: bool):
    selected = set(self._cached_selected_tokens)

    # Expand Whole U.S. to individual states first if modifying a subset
    if US_COUNTRY_TOKEN in selected:
      selected.remove(US_COUNTRY_TOKEN)
      selected.update(ALL_US_STATE_TOKENS)

    if state:
      if token == US_COUNTRY_TOKEN:
        selected = {US_COUNTRY_TOKEN}
      elif token in REGIONAL_PACKAGES:
        selected.update(REGIONAL_PACKAGES[token]["tokens"])
      else:
        selected.add(token)
    else:
      if token == US_COUNTRY_TOKEN:
        selected.difference_update(ALL_US_STATE_TOKENS)
        selected.discard(US_COUNTRY_TOKEN)
      elif token in REGIONAL_PACKAGES:
        selected.difference_update(REGIONAL_PACKAGES[token]["tokens"])
      else:
        selected.discard(token)

    # Auto-consolidate to c:US if all 56 states are selected
    if ALL_US_STATE_TOKENS.issubset(selected):
      selected = {US_COUNTRY_TOKEN}

    self._params.put("MapsSelected", sanitize_selected_locations_csv(sorted(selected)))
    self._cached_selected_tokens = selected

  def _is_online(self) -> bool:
    network_type = ui_state.sm["deviceState"].networkType if ui_state.sm.valid.get("deviceState", False) else NetworkType.none
    return network_type != NetworkType.none

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
    reasons = []
    if self._download_in_flight():
      reasons.append(tr("Download in progress"))
    if not self._is_online():
      reasons.append(tr("Connect to the internet"))
    if not self._is_parked():
      reasons.append(tr("Park the vehicle to download"))
    return "\n".join(reasons) if reasons else ""

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
    if self._selected_count() == 0:
      return tr("Select Regions Below")
    return tr("Download Offline Maps")

  def _on_primary_action(self):
    if self._download_in_flight():
      self._on_cancel()
    elif self._selected_count() == 0:
      gui_app.push_widget(alert_dialog(tr("Please select 'Whole U.S.' or pick individual states from the list below.")))
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
      gui_app.push_widget(alert_dialog(tr("Please select 'Whole U.S.' or pick individual states from the list below.")))
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
            OFFLINE_MAPS_PATH.mkdir(parents=True, exist_ok=True)
          cache = load_maps_storage_cache(self._worker_params.get(MAPS_STORAGE_CACHE_PARAM, encoding="utf-8") or "")
          cache.clear()
          self._worker_params.put(MAPS_STORAGE_CACHE_PARAM, cache.to_json())
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
      return tr("Downloading Maps")
    if self._download_requested():
      return tr("Starting Download")
    if self._has_downloaded_data:
      return tr("Offline Maps")
    if not self._storage_known:
      return tr("Checking Offline Maps")
    if self._selected_count() == 0:
      return tr("Select Map Data")
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

    if self._selected_count() == 0:
      return tr("No regions selected yet. Tap 'Whole U.S.' or pick specific states below to get started.")

    gate_reason = self._download_gate_reason()
    if gate_reason:
      return gate_reason

    return tr("Ready to download {}.").format(self._selection_preview_text())
