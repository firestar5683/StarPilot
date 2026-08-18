from __future__ import annotations

import json
import math
from collections.abc import Callable
from typing import Any

from cereal import log
import pyray as rl

from openpilot.selfdrive.ui.widgets.drive_stats import (
  CARD_BORDER,
  CARD_COLOR,
  MUTED_COLOR,
  TEXT_COLOR,
  TRACK_COLOR,
  TEAL,
)
from openpilot.starpilot.navigation.destination_store import (
  FAVORITE_DESTINATIONS_KEY,
  NavigationDestinationStore,
  load_favorite_destinations,
  ordered_favorite_destinations,
  routing_configured,
  same_destination,
)
from openpilot.system.ui.lib.application import FontWeight, MousePos, gui_app
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget


HEADER_HEIGHT = 82.0
ROW_COUNT = 3
PAGE_SWITCH_SIZE = 72.0
TEXT_LEFT_INSET = 30.0
TEXT_RIGHT_INSET = 34.0


def _has_valid_gps_payload(raw: Any) -> bool:
  if not raw:
    return False
  try:
    data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    if isinstance(data, dict):
      if str(data.get("hasFix")).strip().lower() in ("0", "false", "no", "off", "", "none"):
        return False
      lat, lon = float(data.get("latitude", 0.0)), float(data.get("longitude", 0.0))
      return math.isfinite(lat) and math.isfinite(lon) and (abs(lat) > 1e-6 or abs(lon) > 1e-6)
  except Exception:
    pass
  return False


class HomeInfoCard(Widget):
  """Paired offroad Home card for Quick Start and Personal Records."""

  def __init__(
    self,
    params: Any,
    drive_stats: Any,
    *,
    online_provider: Callable[[], bool] | None = None,
    gps_provider: Callable[[], bool] | None = None,
  ):
    super().__init__()
    self._params = params
    self._store = NavigationDestinationStore(params)
    self._drive_stats = drive_stats
    self._online_provider = online_provider
    self._gps_provider = gps_provider

    self._show_records = False
    self._quick_start_available = False
    self._favorites: list[dict[str, Any]] = []
    self._active_destination: dict[str, Any] | None = None
    self._flip_rect = rl.Rectangle(0, 0, 0, 0)
    self._destination_rects: list[rl.Rectangle] = []

    self._font_semi_bold: rl.Font | None = None
    self._font_medium: rl.Font | None = None

  @property
  def quick_start_available(self) -> bool:
    return self._quick_start_available

  @property
  def show_records(self) -> bool:
    return self._show_records

  @property
  def favorites(self) -> list[dict[str, Any]]:
    return list(self._favorites)

  @property
  def active_destination(self) -> dict[str, Any] | None:
    return self._active_destination

  def show_event(self):
    self._show_records = False
    self.refresh()
    super().show_event()

  def _is_online(self) -> bool:
    if self._online_provider is not None:
      return bool(self._online_provider())
    try:
      from openpilot.selfdrive.ui.ui_state import ui_state
      if hasattr(ui_state, "sm") and ui_state.sm.valid.get("deviceState", False):
        return ui_state.sm["deviceState"].networkType != log.DeviceState.NetworkType.none
    except Exception:
      pass
    return False

  def _has_gps(self) -> bool:
    if self._gps_provider is not None:
      return bool(self._gps_provider())

    if _has_valid_gps_payload(self._params.get("LastGPSPosition", encoding="utf-8")):
      return True

    try:
      from openpilot.selfdrive.ui.ui_state import ui_state
      if hasattr(ui_state, "sm") and ui_state.sm.valid.get("gpsLocationExternal", False):
        gps = ui_state.sm["gpsLocationExternal"]
        if getattr(gps, "hasFix", False):
          lat, lon = float(getattr(gps, "latitude", 0.0)), float(getattr(gps, "longitude", 0.0))
          if math.isfinite(lat) and math.isfinite(lon) and (abs(lat) > 1e-6 or abs(lon) > 1e-6):
            return True

      if hasattr(ui_state, "params_memory"):
        return _has_valid_gps_payload(ui_state.params_memory.get("LastGPSPosition", encoding="utf-8"))
    except Exception:
      pass
    return False

  def refresh(self) -> None:
    was_available = self._quick_start_available
    self._active_destination = self._store.active_destination()

    raw_favorites = self._params.get(FAVORITE_DESTINATIONS_KEY, encoding="utf-8", default="[]")
    favorites = load_favorite_destinations(raw_favorites)
    self._favorites = ordered_favorite_destinations(favorites, limit=ROW_COUNT)
    self._quick_start_available = (
      routing_configured(self._params)
      and bool(self._favorites)
      and self._is_online()
      and self._has_gps()
    )

    if not self._quick_start_available:
      self._show_records = True
    elif not was_available:
      self._show_records = False

  def _update_layout_rects(self) -> None:
    self._flip_rect = rl.Rectangle(
      self._rect.x + max(0.0, self._rect.width - PAGE_SWITCH_SIZE - 12.0),
      self._rect.y + 5.0,
      PAGE_SWITCH_SIZE,
      PAGE_SWITCH_SIZE,
    )

    row_height = max(0.0, (self._rect.height - HEADER_HEIGHT - 12.0) / ROW_COUNT)
    self._destination_rects = [
      rl.Rectangle(
        self._rect.x,
        self._rect.y + HEADER_HEIGHT + index * row_height,
        self._rect.width,
        row_height,
      )
      for index in range(ROW_COUNT)
    ]

  def _handle_mouse_release(self, mouse_pos: MousePos) -> None:
    super()._handle_mouse_release(mouse_pos)

    if not self._quick_start_available:
      return

    if rl.check_collision_point_rec(mouse_pos, self._flip_rect):
      self._show_records = not self._show_records
      return

    if self._show_records:
      return

    for index, row_rect in enumerate(self._destination_rects):
      if rl.check_collision_point_rec(mouse_pos, row_rect):
        self._select_destination(index)
        return

  def _select_destination(self, index: int) -> None:
    if index < 0 or index >= len(self._favorites):
      return

    favorite = self._favorites[index]
    destination = self._store.set_destination(favorite, skip_if_same=True)
    if destination is not None:
      self._active_destination = destination

  def _font(self, weight: FontWeight) -> rl.Font:
    if weight == FontWeight.SEMI_BOLD:
      if self._font_semi_bold is None:
        self._font_semi_bold = gui_app.font(weight)
      return self._font_semi_bold
    if self._font_medium is None:
      self._font_medium = gui_app.font(weight)
    return self._font_medium

  @staticmethod
  def _fit_text(font: Any, text: str, font_size: int, max_width: float) -> str:
    if max_width <= 0:
      return ""
    if measure_text_cached(font, text, font_size).x <= max_width:
      return text

    ellipsis = "…"
    fitted = text
    while fitted and measure_text_cached(font, f"{fitted}{ellipsis}", font_size).x > max_width:
      fitted = fitted[:-1]
    return f"{fitted}{ellipsis}" if fitted else ellipsis

  @staticmethod
  def _draw_card(rect: rl.Rectangle) -> None:
    rl.draw_rectangle_rounded(rect, 0.04, 12, CARD_COLOR)
    rl.draw_rectangle_rounded_lines_ex(rect, 0.04, 12, 2, CARD_BORDER)

  @staticmethod
  def _draw_checkmark(center_x: float, center_y: float, scale: float = 1.0) -> None:
    color = TEAL
    rl.draw_line_ex(
      rl.Vector2(center_x - 14 * scale, center_y),
      rl.Vector2(center_x - 3 * scale, center_y + 11 * scale),
      4 * scale,
      color,
    )
    rl.draw_line_ex(
      rl.Vector2(center_x - 3 * scale, center_y + 11 * scale),
      rl.Vector2(center_x + 16 * scale, center_y - 12 * scale),
      4 * scale,
      color,
    )

  @staticmethod
  def _draw_page_icon(rect: rl.Rectangle) -> None:
    center_x = rect.x + rect.width / 2
    center_y = rect.y + rect.height / 2
    color = MUTED_COLOR
    thickness = 3.0

    rl.draw_line_ex(
      rl.Vector2(center_x - 16, center_y - 7),
      rl.Vector2(center_x + 14, center_y - 7),
      thickness,
      color,
    )
    rl.draw_line_ex(
      rl.Vector2(center_x + 14, center_y - 7),
      rl.Vector2(center_x + 6, center_y - 14),
      thickness,
      color,
    )
    rl.draw_line_ex(
      rl.Vector2(center_x + 14, center_y - 7),
      rl.Vector2(center_x + 6, center_y),
      thickness,
      color,
    )
    rl.draw_line_ex(
      rl.Vector2(center_x + 16, center_y + 8),
      rl.Vector2(center_x - 14, center_y + 8),
      thickness,
      color,
    )
    rl.draw_line_ex(
      rl.Vector2(center_x - 14, center_y + 8),
      rl.Vector2(center_x - 6, center_y + 1),
      thickness,
      color,
    )
    rl.draw_line_ex(
      rl.Vector2(center_x - 14, center_y + 8),
      rl.Vector2(center_x - 6, center_y + 15),
      thickness,
      color,
    )

  def _draw_header(self, rect: rl.Rectangle, title: str) -> None:
    rl.draw_text_ex(
      self._font(FontWeight.SEMI_BOLD),
      title,
      rl.Vector2(rect.x + TEXT_LEFT_INSET, rect.y + 26),
      32,
      0,
      TEXT_COLOR,
    )
    self._draw_page_icon(self._flip_rect)

  def _draw_quick_start(self, rect: rl.Rectangle) -> None:
    self._draw_card(rect)
    self._draw_header(rect, tr("START NAVIGATION"))

    row_height = (rect.height - HEADER_HEIGHT - 12.0) / ROW_COUNT
    title_font = self._font(FontWeight.MEDIUM)
    for index in range(ROW_COUNT):
      row_y = rect.y + HEADER_HEIGHT + index * row_height
      if index > 0:
        rl.draw_line(
          int(rect.x + 24),
          int(row_y),
          int(rect.x + rect.width - 24),
          int(row_y),
          TRACK_COLOR,
        )

      favorite = self._favorites[index] if index < len(self._favorites) else None
      if favorite is None:
        if index == len(self._favorites):
          empty_text = tr("Add favorites in Navigation")
          empty_size = measure_text_cached(title_font, empty_text, 28)
          rl.draw_text_ex(
            title_font,
            empty_text,
            rl.Vector2(rect.x + (rect.width - empty_size.x) / 2, row_y + (row_height - empty_size.y) / 2),
            28,
            0,
            MUTED_COLOR,
          )
        continue

      selected = same_destination(self._active_destination, favorite)
      name = str(favorite.get("name") or tr("Favorite destination"))
      name_width = rect.width - TEXT_LEFT_INSET - TEXT_RIGHT_INSET - (74 if selected else 0)
      name = self._fit_text(title_font, name, 38, name_width)
      name_size = measure_text_cached(title_font, name, 38)
      text_x = rect.x + TEXT_LEFT_INSET
      center_y = row_y + row_height / 2
      rl.draw_text_ex(
        title_font,
        name,
        rl.Vector2(text_x, center_y - name_size.y - 5),
        38,
        0,
        TEXT_COLOR,
      )

      if selected:
        subtitle = tr("Selected for next drive")
      elif favorite.get("is_home"):
        subtitle = tr("Home")
      elif favorite.get("is_work"):
        subtitle = tr("Work")
      else:
        subtitle = tr("Favorite destination")
      subtitle = self._fit_text(title_font, subtitle, 25, name_width)
      rl.draw_text_ex(
        title_font,
        subtitle,
        rl.Vector2(text_x, center_y + 17),
        25,
        0,
        MUTED_COLOR if not selected else TEAL,
      )

      if selected:
        self._draw_checkmark(rect.x + rect.width - 60, center_y, 0.9)

  def _render(self, rect: rl.Rectangle):
    if not self._quick_start_available:
      self._drive_stats.render_records(rect)
      return

    if self._show_records:
      self._drive_stats.render_records(rect)
      self._draw_page_icon(self._flip_rect)
    else:
      self._draw_quick_start(rect)
