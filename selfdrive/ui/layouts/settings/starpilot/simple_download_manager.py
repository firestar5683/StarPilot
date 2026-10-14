from __future__ import annotations
import re
import time
from pathlib import Path
from collections.abc import Callable

import pyray as rl
from openpilot.system.ui.lib.application import gui_app, FontWeight, MousePos
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.scroll_panel2 import GuiScrollPanel2
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget, DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
    AetherListColors, AetherListMetrics, AetherScrollbar,
    draw_hud_background, draw_action_pill, draw_selection_list_row,
    draw_empty_state_card, draw_busy_ring, draw_list_scroll_fades,
    draw_rounded_fill, draw_rounded_stroke, draw_text_fit_common,
    draw_download_icon,
    with_alpha, hex_to_color, snap_rect, point_hits,
    aether_begin_scissor_mode, aether_end_scissor_mode,
)


# ── Helpers ──

def _theme_display_name(value: str) -> str:
  if not value:
    return "Stock"
  if value.lower() == "stock":
    return "Stock"
  if value.lower() == "none":
    return "None"
  base, creator = (value.split("~", 1) + [""])[:2] if "~" in value else (value, "")
  user_created = False
  for suffix in ("-user_created", "_user_created", "-user-created", "_user-created"):
    if base.endswith(suffix):
      base = base[: -len(suffix)]
      user_created = True
      break
  parts = [part for part in re.split(r"[-_]+", base) if part]
  display = " ".join(part[:1].upper() + part[1:] for part in parts) if parts else value
  if user_created:
    display += " (User Created)"
  if creator:
    display += f" - by: {creator}"
  return display


def _display_to_slug(display: str) -> str:
  slug = display.lower().strip()
  slug = slug.replace("(user created)", "").strip()
  if " - by: " in slug:
    slug = slug.split(" - by: ")[0].strip()
  slug = slug.replace("(", "").replace(")", "").replace("'", "").replace(".", "").replace("\u2728", "").strip()
  slug = slug.replace(" ", "_")
  slug = re.sub(r"_+", "_", slug)
  slug = slug.strip("_")
  return slug


def _delete_asset_file(directory: Path, display_name: str) -> bool:
  base = display_name.lower()
  base = base.replace("(", "-").replace(")", "").replace(" ", "-")
  base = re.sub(r"[^a-z0-9\-]", "", base)
  while base.endswith("-"):
    base = base[:-1]
  base_underscore = base.replace("-", "_")
  candidates = {base, base + "-user-created", base_underscore, base_underscore + "-user_created"}

  for f in sorted(directory.iterdir()):
    if f.is_file():
      normalized = f.stem.lower().replace("_", "-")
      normalized = re.sub(r"[^a-z0-9\-~]", "", normalized)
      if normalized in candidates:
        f.unlink()
        return True
  return False


def _add_to_downloadable_list(params, param_key: str, display_name: str):
  current = params.get(param_key, encoding="utf-8") or ""
  assets = [a.strip() for a in current.split(",") if a.strip()]
  slug = _display_to_slug(display_name)
  if slug and slug not in assets:
    assets.append(slug)
    assets.sort()
    params.put(param_key, ",".join(assets))


def _is_online() -> bool:
  try:
    from openpilot.selfdrive.ui.ui_state import ui_state
    from cereal import log
    nt = ui_state.sm["deviceState"].networkType if ui_state.sm.valid.get("deviceState", False) else log.NetworkType.none
    return nt != log.NetworkType.none
  except Exception:
    return True


def _is_parked() -> bool:
  try:
    from openpilot.selfdrive.ui.ui_state import ui_state
    if ui_state.is_offroad():
      return True
    if ui_state.sm.valid.get("starpilotCarState", False):
      return bool(ui_state.sm["starpilotCarState"].isParked)
  except Exception:
    pass
  return True


class SimpleDownloadManager(Widget):
  """Generic fullscreen dialog for managing downloadable assets."""

  MODE_SELECT = 0
  MODE_DELETE = 1
  MODE_DOWNLOAD = 2

  MODE_LABELS = ["SELECT", "DELETE", "DOWNLOAD"]
  ITEM_HEIGHT = 144
  PILL_HEIGHT = 88
  PILL_GAP = 18
  OUTER_MARGIN = 40

  def __init__(
    self,
    title: str,
    asset_type: str,
    directory: str | Path,
    asset_param: str,
    download_param: str,
    downloadable_list_param: str,
    params,
    params_memory,
    on_close: Callable,
    *,
    get_is_online: Callable[[], bool] | None = None,
    get_is_parked: Callable[[], bool] | None = None,
  ):
    super().__init__()
    self.title = title
    self.asset_type = asset_type
    self.directory = Path(directory)
    self.asset_param = asset_param
    self.download_param = download_param
    self.downloadable_list_param = downloadable_list_param
    self.params = params
    self.params_memory = params_memory
    self._on_close = on_close

    self._get_is_online = get_is_online or (lambda: True)
    self._get_is_parked = get_is_parked or (lambda: True)

    self._active_mode = self.MODE_SELECT
    self._downloading = False
    self.refresh_thread = None
    self._download_progress = ""
    self._finalizing_until = 0.0
    self._pressed_target: str | None = None
    self._pressed_time = 0.0

    self._scroll_panel = GuiScrollPanel2(horizontal=False)
    self._scrollbar = AetherScrollbar()
    self._scroll_offset = 0.0
    self._content_height = 0.0

    self._list_items: list[str] = []
    self._slug_map: dict[str, str] = {}
    self._item_rects: dict[str, rl.Rectangle] = {}
    self._pill_rects: list[rl.Rectangle] = []
    self._close_rect = rl.Rectangle(0, 0, 0, 0)
    self._cancel_rect = rl.Rectangle(0, 0, 0, 0)
    self._info_message = ""
    self._info_message_until = 0.0

    self._refresh_list()
    self.set_touch_valid_callback(lambda: self._scroll_panel.is_touch_valid())

  # ── List data ──

  def _refresh_list(self):
    if self._active_mode in (self.MODE_SELECT, self.MODE_DELETE):
      self._list_items = self._list_downloaded()
    elif self._active_mode == self.MODE_DOWNLOAD:
      downloadable = self._list_downloadable()
      downloaded_stems = set(s.lower() for s in self._list_downloaded_stems())
      self._list_items = [
        item for item in downloadable
        if _display_to_slug(item).lower() not in downloaded_stems
      ]

  def _list_downloaded(self) -> list[str]:
    if not self.directory.is_dir():
      return []
    items: list[str] = []
    for f in sorted(self.directory.iterdir()):
      if f.is_file():
        items.append(_theme_display_name(f.stem))
    return items

  def _list_downloaded_stems(self) -> list[str]:
    if not self.directory.is_dir():
      return []
    return [f.stem for f in self.directory.iterdir() if f.is_file()]

  def _list_downloadable(self) -> list[str]:
    raw = self.params.get(self.downloadable_list_param, encoding="utf-8") or ""
    if not raw.strip():
      return []
    names = [s.strip() for s in raw.split(",") if s.strip()]
    self._slug_map = {}
    result = []
    for n in names:
      display = _theme_display_name(n)
      self._slug_map[display] = n
      result.append(display)
    return result

  def _current_value(self) -> str:
    return self.params.get(self.asset_param, encoding="utf-8") or ""

  # ── Actions ──

  def _select_asset(self, display_name: str):
    slug = _display_to_slug(display_name)
    if slug:
      self.params.put(self.asset_param, slug)
    self._close(DialogResult.CONFIRM, slug)

  def _delete_asset(self, display_name: str):
    _delete_asset_file(self.directory, display_name)
    _add_to_downloadable_list(self.params, self.downloadable_list_param, display_name)
    self._info_message = f"Deleted \"{display_name}\""
    self._info_message_until = time.monotonic() + 2.5
    self._refresh_list()

  def _start_download(self, display_name: str):
    if self._downloading:
      return
    slug = self._slug_map.get(display_name) or _display_to_slug(display_name)
    if not slug:
      return
    self._downloading = True
    self._download_progress = "Downloading..."
    self.params_memory.put("ThemeDownloadProgress", "Downloading...")
    self.params_memory.put(self.download_param, slug)

  def _cancel_download(self):
    self.params_memory.put_bool("CancelThemeDownload", True)
    self._info_message = tr("Cancelling...")
    self._info_message_until = time.monotonic() + 5.0

  def _close(self, result: DialogResult, value=None):
    gui_app.pop_widget()
    if self._on_close:
      self._on_close(result, value)

  # ── Mouse handling ──

  def _hit_target(self, pos: MousePos) -> str | None:
    if rl.check_collision_point_rec(pos, self._close_rect):
      return "close"
    for i, prect in enumerate(self._pill_rects):
      if rl.check_collision_point_rec(pos, prect):
        return f"mode:{i}"
    if self._downloading:
      if rl.check_collision_point_rec(pos, self._cancel_rect):
        return "cancel_download"
      return None
    for key, irect in self._item_rects.items():
      if rl.check_collision_point_rec(pos, irect):
        return key
    return None

  def _handle_mouse_press(self, pos: MousePos):
    target = self._hit_target(pos)
    if target:
      self._pressed_target = target
      self._pressed_time = rl.get_time()

  def _handle_mouse_release(self, pos: MousePos):
    target = self._hit_target(pos)
    if target and target == self._pressed_target:
      self._on_target(target)
    self._pressed_target = None

  def _on_target(self, target: str):
    if target == "close":
      self._close(DialogResult.CANCEL)
    elif target.startswith("mode:"):
      mode = int(target.split(":")[1])
      if mode != self._active_mode:
        self._active_mode = mode
        self._scroll_offset = 0.0
        self._refresh_list()
    elif target.startswith("item:"):
      idx = int(target.split(":")[1])
      if 0 <= idx < len(self._list_items):
        item = self._list_items[idx]
        if self._active_mode == self.MODE_SELECT:
          self._select_asset(item)
        elif self._active_mode == self.MODE_DELETE:
          def on_result(result: DialogResult):
            if result == DialogResult.CONFIRM:
              self._delete_asset(item)

          gui_app.push_widget(ConfirmDialog(
            tr("Delete \"{name}\"?").format(name=item), tr("DELETE"), callback=on_result,
          ))
        elif self._active_mode == self.MODE_DOWNLOAD:
          self._start_download(item)
    elif target == "cancel_download":
      self._cancel_download()

  # ── State update ──

  def _update_state(self):
    now = time.monotonic()
    if self.refresh_thread is not None and not self.refresh_thread.is_alive():
      self.params.invalidate(self.downloadable_list_param)
      self._refresh_list()
      self.refresh_thread = None
    if self._pressed_target is not None and not self.is_pressed:
      self._pressed_target = None
    if self._info_message_until > 0 and now >= self._info_message_until:
      self._info_message = ""
      self._info_message_until = 0.0
    if self._finalizing_until > 0 and now >= self._finalizing_until:
      self._finalizing_until = 0.0
      self._downloading = False
      self._download_progress = ""
      self._refresh_list()
    if self._downloading:
      progress = self.params_memory.get("ThemeDownloadProgress", encoding="utf-8") or ""
      if progress != self._download_progress:
        self._download_progress = progress
        if progress == "Downloaded!" or ("cancelled" in progress.lower() or "failed" in progress.lower() or "offline" in progress.lower() or "unavailable" in progress.lower()):
          self._finalizing_until = now + 2.5

  # ── keepScreenOn support ──

  @property
  def should_keep_screen_on(self) -> bool:
    return self._downloading

  # ── Rendering ──

  def _render(self, rect: rl.Rectangle) -> bool | int | None:
    self.set_rect(rect)

    # Full-screen dark overlay matching AetherSliderDialog
    rl.draw_rectangle(0, 0, gui_app.width, gui_app.height, rl.Color(0, 0, 0, 160))

    # Dialog card (spacious & thematic bounds)
    margin_x = self.OUTER_MARGIN
    margin_y = self.OUTER_MARGIN
    card_w = min(1800, int(rect.width - margin_x * 2))
    card_h = min(960, int(rect.height - margin_y * 2))
    card_x = rect.x + (rect.width - card_w) / 2
    card_y = rect.y + (rect.height - card_h) / 2
    card_rect = snap_rect(rl.Rectangle(card_x, card_y, card_w, card_h))

    # Rounded dialog shell with purple top accent stripe (AetherSliderDialog parity)
    draw_rounded_fill(card_rect, rl.Color(10, 12, 16, 255), radius_px=35)
    draw_rounded_stroke(card_rect, rl.Color(255, 255, 255, 16), radius_px=35)
    rl.draw_rectangle_rec(rl.Rectangle(card_rect.x, card_rect.y, card_rect.width, 3), AetherListColors.PRIMARY)

    cx = int(card_x + 48)
    cw = int(card_w - 96)
    y = int(card_y + 36)

    # ── Title + close ──
    title_font = gui_app.font(FontWeight.BOLD)
    close_size = 56
    close_x = int(card_x + card_w - 48 - close_size)
    self._close_rect = rl.Rectangle(close_x, y, close_size, close_size)

    draw_text_fit_common(title_font, tr(self.title), rl.Vector2(float(cx), float(y + 4)),
                         float(cw - close_size - 32), 48, color=AetherListColors.HEADER)

    close_hovered = self._pressed_target == "close"
    rl.draw_rectangle_rounded(self._close_rect, 0.35, 12,
                              with_alpha(rl.Color(255, 255, 255, 28 if close_hovered else 14), 255))
    rl.draw_rectangle_rounded_lines_ex(self._close_rect, 0.35, 12, 1.5,
                                       with_alpha(rl.Color(255, 255, 255, 40), 255))
    cx_c = self._close_rect.x + self._close_rect.width / 2
    cy_c = self._close_rect.y + self._close_rect.height / 2
    s = close_size * 0.28
    clr = AetherListColors.HEADER if close_hovered else AetherListColors.MUTED
    rl.draw_line_ex(rl.Vector2(cx_c - s, cy_c - s), rl.Vector2(cx_c + s, cy_c + s), 3.0, clr)
    rl.draw_line_ex(rl.Vector2(cx_c + s, cy_c - s), rl.Vector2(cx_c - s, cy_c + s), 3.0, clr)

    y += 72

    # ── Current selection ──
    current_val = self._current_value()
    current_display = _theme_display_name(current_val) if current_val else "Stock"
    info_font = gui_app.font(FontWeight.NORMAL)
    current_text = f"{tr('Current')}: {current_display}"
    rl.draw_text_ex(info_font, current_text,
                    rl.Vector2(float(cx), float(y)), 28, 0, AetherListColors.SUBTEXT)
    y += 44

    # ── Info message ──
    if self._info_message and time.monotonic() < self._info_message_until:
      rl.draw_text_ex(info_font, self._info_message,
                      rl.Vector2(float(cx), float(y)), 26, 0, AetherListColors.SUCCESS)
      y += 36

    # ── Mode pills ──
    pill_w = int((cw - self.PILL_GAP * 2) / 3)
    self._pill_rects = []
    active_fill = AetherListColors.PRIMARY
    active_border = with_alpha(AetherListColors.PRIMARY, 180)
    active_text = AetherListColors.HEADER
    inactive_fill = with_alpha(rl.Color(255, 255, 255, 8), 255)
    inactive_border = with_alpha(rl.Color(255, 255, 255, 36), 255)
    inactive_text = AetherListColors.MUTED

    for i, label in enumerate(self.MODE_LABELS):
      px = cx + i * (pill_w + self.PILL_GAP)
      prect = snap_rect(rl.Rectangle(float(px), float(y), float(pill_w), float(self.PILL_HEIGHT)))
      self._pill_rects.append(prect)
      is_active = i == self._active_mode
      is_pressed = self._pressed_target == f"mode:{i}"
      draw_action_pill(
        prect,
        tr(label),
        active_fill if is_active else inactive_fill,
        active_border if is_active else inactive_border,
        active_text if is_active else inactive_text,
        font_size=28,
        roundness=0.35,
      )
      if is_pressed:
        rl.draw_rectangle_rounded(prect, 0.35, 12, with_alpha(rl.Color(255, 255, 255, 16), 255))

    y += self.PILL_HEIGHT + 24

    # ── Content area ──
    scroll_y = y
    scroll_h = int(card_rect.y + card_rect.height - scroll_y - 28)
    if scroll_h < 40:
      return True
    scroll_rect = rl.Rectangle(float(cx), float(scroll_y), float(cw), float(scroll_h))

    # Measure content
    n_items = len(self._list_items)
    prog_h = 140
    progress_space = prog_h + 40 if self._downloading else 0
    content_height = float(n_items * self.ITEM_HEIGHT + progress_space)

    self._scroll_panel.set_enabled(True)
    self._scroll_offset = self._scroll_panel.update(scroll_rect, max(content_height, scroll_rect.height))

    aether_begin_scissor_mode(int(scroll_rect.x), int(scroll_rect.y),
                              int(scroll_rect.width), int(scroll_rect.height))

    if n_items == 0 and not self._downloading:
      empty_msg = self._empty_state_text()
      draw_empty_state_card(
        scroll_rect,
        tr(empty_msg["title"]),
        tr(empty_msg["body"]),
        title_size=38, body_size=26,
        title_top_padding=50, body_height=80,
        fill=rl.Color(0, 0, 0, 0), border=rl.Color(0, 0, 0, 0),
      )
    else:
      self._item_rects.clear()
      item_y = scroll_rect.y + self._scroll_offset
      normal_font = gui_app.font(FontWeight.NORMAL)

      if self._downloading:
        # Download progress display
        prog_rect = rl.Rectangle(scroll_rect.x + 20, scroll_rect.y + self._scroll_offset + 20,
                                 scroll_rect.width - 40, prog_h)
        draw_rounded_fill(prog_rect, with_alpha(rl.Color(255, 255, 255, 8), 255), radius_px=16)
        draw_rounded_stroke(prog_rect, with_alpha(rl.Color(255, 255, 255, 20), 255), radius_px=16)

        # Busy ring
        ring_center = rl.Vector2(prog_rect.x + 70, prog_rect.y + prog_rect.height / 2)
        draw_busy_ring(ring_center, rl.get_time() * 4, AetherListColors.PRIMARY,
                       track_color=with_alpha(rl.Color(255, 255, 255, 18), 255))

        # Progress text
        progress_text = self._download_progress or "Downloading..."
        draw_text_fit_common(
          normal_font, progress_text,
          rl.Vector2(prog_rect.x + 130, prog_rect.y + 32),
          prog_rect.width - 340, 32,
          color=AetherListColors.HEADER,
        )

        # Cancel button
        cancel_w, cancel_h = 180, 54
        cancel_y = prog_rect.y + (prog_h - cancel_h) / 2
        self._cancel_rect = snap_rect(rl.Rectangle(
          prog_rect.x + prog_rect.width - cancel_w - 24, cancel_y, float(cancel_w), float(cancel_h)))
        cancel_hovered = self._pressed_target == "cancel_download"
        draw_action_pill(
          self._cancel_rect, tr("CANCEL"),
          with_alpha(AetherListColors.DANGER, 50 if cancel_hovered else 30),
          with_alpha(AetherListColors.DANGER, 100),
          AetherListColors.HEADER, font_size=24,
        )

        item_y += progress_space

      # Draw list items
      for idx, item in enumerate(self._list_items):
        irec = rl.Rectangle(scroll_rect.x, item_y, scroll_rect.width, float(self.ITEM_HEIGHT))
        key = f"item:{idx}"
        self._item_rects[key] = irec

        is_last = idx == n_items - 1
        is_current = (
          self._active_mode == self.MODE_SELECT
          and _display_to_slug(item) == self._current_value()
        )
        is_pressed = self._pressed_target == key
        is_hovered = is_pressed

        is_deleting = self._active_mode == self.MODE_DELETE
        is_downloading_mode = self._active_mode == self.MODE_DOWNLOAD

        action_text = ""
        action_fill = AetherListColors.CURRENT_BG
        action_border = AetherListColors.CURRENT_BORDER
        action_text_color = AetherListColors.HEADER
        row_bg = AetherListColors.ROW_BG
        row_border = AetherListColors.ROW_BORDER

        if is_current:
          action_text = tr("Current")
          action_fill = AetherListColors.CURRENT_BG
          action_border = AetherListColors.CURRENT_BORDER
          action_text_color = AetherListColors.HEADER

        if is_deleting:
          action_text = tr("DELETE")
          action_fill = with_alpha(AetherListColors.DANGER, 30)
          action_border = with_alpha(AetherListColors.DANGER, 80)
          action_text_color = AetherListColors.DANGER

        if is_downloading_mode:
          action_text = tr("DOWNLOAD")
          action_fill = with_alpha(AetherListColors.SUCCESS, 30)
          action_border = with_alpha(AetherListColors.SUCCESS, 80)
          action_text_color = AetherListColors.SUCCESS

        draw_selection_list_row(
          irec,
          title=item,
          subtitle="",
          action_text=action_text,
          current=is_current and self._active_mode == self.MODE_SELECT,
          hovered=is_hovered,
          pressed=is_pressed and is_deleting,
          is_last=is_last,
          alpha=255,
          action_pill=True,
          action_pill_height=54,
          title_size=36,
          action_text_size=26,
          title_color=AetherListColors.HEADER,
          subtitle_color=AetherListColors.SUBTEXT,
          action_fill=action_fill,
          action_border=action_border,
          action_text_color=action_text_color,
          row_bg=row_bg,
          row_border=row_border,
          row_separator=AetherListColors.ROW_SEPARATOR,
          row_hover=AetherListColors.ROW_HOVER,
          current_bg=AetherListColors.CURRENT_BG,
          current_border=AetherListColors.CURRENT_BORDER,
        )

        item_y += self.ITEM_HEIGHT

    aether_end_scissor_mode()

    # Scrollbar
    if content_height > scroll_rect.height:
      self._scrollbar.render(scroll_rect, content_height, self._scroll_offset)

    # Fades
    draw_list_scroll_fades(scroll_rect, content_height, self._scroll_offset, rl.Color(14, 13, 18, 255))

    return True

  def _empty_state_text(self) -> dict:
    at = self.asset_type
    if self._active_mode == self.MODE_SELECT:
      return {"title": tr("No {name}s").format(name=at.title()), "body": tr("Download {name}s to see them here.").format(name=at)}
    if self._active_mode == self.MODE_DELETE:
      return {"title": tr("Nothing to Delete"), "body": tr("No {name}s are currently downloaded.").format(name=at)}
    if self._active_mode == self.MODE_DOWNLOAD:
      if self._downloading:
        return {"title": "", "body": ""}
      return {"title": tr("All Available"), "body": tr("You have all available {name}s.").format(name=at)}
    return {"title": "", "body": ""}
