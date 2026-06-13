from __future__ import annotations

import json
import math
from pathlib import Path

import pyray as rl

from openpilot.common.params import UnknownKeyName
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import FontWeight, gui_app
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget

ASSETS_PATH = Path(__file__).resolve().parents[4] / "starpilot" / "assets" / "navigation"
FALLBACK_ICON = "direction_turn_straight.png"
NAV_CANCEL_HOLD_SECONDS = 0.65


def _format_distance(distance_m: float, is_metric: bool) -> str:
  if is_metric:
    if distance_m < 1000:
      step = 25 if distance_m < 500 else 50
      return f"{round(distance_m / step) * step} m"
    distance_km = distance_m / 1000.0
    return f"{math.floor(distance_km)} km" if distance_km >= 10.0 else f"{distance_km:.1f} km"

  distance_ft = distance_m * 3.28084
  if distance_ft < 1000:
    step = 10 if distance_ft <= 100 else 50
    return f"{round(distance_ft / step) * step} ft"
  distance_mi = distance_ft / 5280.0
  return f"{math.floor(distance_mi)} mi" if distance_mi >= 10.0 else f"{distance_mi:.1f} mi"


def _modifier_suffix(modifier: str) -> str:
  suffix_map = {
    "left": "left",
    "right": "right",
    "straight": "straight",
    "slightLeft": "slight_left",
    "slightRight": "slight_right",
    "sharpLeft": "sharp_left",
    "sharpRight": "sharp_right",
  }
  return suffix_map.get(modifier, "")


def _normalize_maneuver_type(maneuver_type: str) -> str:
  normalized = maneuver_type or "turn"
  if normalized == "rotary":
    normalized = "roundabout"
  elif normalized in ("new name", "continue"):
    normalized = "turn"
  return normalized.replace(" ", "_")


class NavigationCardRenderer(Widget):
  def __init__(self, layout_variant: str = "default"):
    super().__init__()
    self._font_bold = gui_app.font(FontWeight.BOLD)
    self._font_medium = gui_app.font(FontWeight.MEDIUM)
    self._icons: dict[str, rl.Texture2D] = {}
    self._layout_variant = layout_variant

    self._enabled = False
    self._valid = False
    self._distance = ""
    self._primary_text = ""
    self._secondary_text = ""
    self._maneuver_type = "turn"
    self._modifier = "straight"
    self._has_next = False
    self._next_maneuver_type = "turn"
    self._next_modifier = "straight"
    self._collapsed = False
    self._collapsed_fallback = False
    self._collapsed_param_supported: bool | None = None
    self._interactive_rect = rl.Rectangle(0, 0, 0, 0)
    self._click_delay = 0.15
    self._press_started_at: float | None = None

  @property
  def _hit_rect(self) -> rl.Rectangle:
    if self._interactive_rect.width > 0 and self._interactive_rect.height > 0:
      return self._interactive_rect
    return rl.Rectangle(-1, -1, 0, 0)

  def _toggle_collapsed(self) -> None:
    if not self._valid:
      return
    new_state = not self._collapsed
    try:
      ui_state.params_memory.put_bool("NavInstructionCollapsed", new_state)
      self._collapsed_param_supported = True
    except UnknownKeyName:
      self._collapsed_param_supported = False
      self._collapsed_fallback = new_state
      self._collapsed = new_state

  def _cancel_navigation(self) -> None:
    try:
      ui_state.params.remove("NavDestination")
    except Exception:
      pass

    try:
      ui_state.params_memory.remove("NavInstructionState")
    except Exception:
      pass

    try:
      ui_state.params_memory.remove("NavInstructionCollapsed")
      self._collapsed_param_supported = True
    except UnknownKeyName:
      self._collapsed_param_supported = False

    self._collapsed_fallback = False
    self._collapsed = False
    self._valid = False

  def _handle_mouse_press(self, mouse_pos) -> None:
    self._press_started_at = rl.get_time()

  def _handle_mouse_release(self, mouse_pos) -> None:
    if self._click_delay is not None:
      self._click_release_time = rl.get_time() + self._click_delay

    if not self._valid or self._press_started_at is None:
      self._press_started_at = None
      return

    held_seconds = rl.get_time() - self._press_started_at
    self._press_started_at = None
    if held_seconds >= NAV_CANCEL_HOLD_SECONDS:
      self._cancel_navigation()
    else:
      self._toggle_collapsed()

  def _icon_filename(self, maneuver_type: str, modifier: str) -> str:
    normalized_type = _normalize_maneuver_type(maneuver_type)
    if modifier == "uturn":
      return "direction_uturn.png"

    suffix = _modifier_suffix(modifier)
    candidate = f"direction_{normalized_type}.png" if suffix == "" else f"direction_{normalized_type}_{suffix}.png"
    return candidate if (ASSETS_PATH / candidate).exists() else FALLBACK_ICON

  def _get_icon(self, maneuver_type: str, modifier: str):
    icon_name = self._icon_filename(maneuver_type, modifier)
    if icon_name not in self._icons:
      icon_path = ASSETS_PATH / icon_name
      if not icon_path.exists():
        icon_path = ASSETS_PATH / FALLBACK_ICON
      image = rl.load_image(str(icon_path))
      texture = rl.load_texture_from_image(image)
      rl.set_texture_filter(texture, rl.TextureFilter.TEXTURE_FILTER_BILINEAR)
      rl.set_texture_wrap(texture, rl.TextureWrap.TEXTURE_WRAP_CLAMP)
      rl.unload_image(image)
      self._icons[icon_name] = texture
    return self._icons[icon_name]

  def _update_state(self) -> None:
    self._enabled = ui_state.params.get_bool("NavigationUI")
    self._valid = False
    self._interactive_rect = rl.Rectangle(0, 0, 0, 0)

    if not self._enabled:
      return

    if not (ui_state.params.get("NavDestination") or ""):
      return

    raw_state = ui_state.params_memory.get("NavInstructionState") or {}
    if isinstance(raw_state, str):
      try:
        nav_state = json.loads(raw_state) if raw_state else {}
      except json.JSONDecodeError:
        return
    elif isinstance(raw_state, dict):
      nav_state = raw_state
    else:
      return

    if not nav_state.get("valid", False):
      return

    if str(nav_state.get("maneuverPrimaryText") or "") == "":
      return

    self._distance = _format_distance(float(nav_state.get("maneuverDistance", 0.0) or 0.0), ui_state.is_metric)
    self._primary_text = str(nav_state.get("maneuverPrimaryText") or "")
    self._secondary_text = str(nav_state.get("maneuverSecondaryText") or "")
    self._maneuver_type = str(nav_state.get("maneuverType") or "turn")
    self._modifier = str(nav_state.get("maneuverModifier") or "straight")
    self._next_maneuver_type = str(nav_state.get("nextManeuverType") or "turn")
    self._next_modifier = str(nav_state.get("nextManeuverModifier") or "straight")
    self._has_next = bool(nav_state.get("nextManeuverType") or nav_state.get("nextManeuverModifier"))
    if self._collapsed_param_supported is False:
      self._collapsed = self._collapsed_fallback
    else:
      self._collapsed = ui_state.params_memory.get_bool("NavInstructionCollapsed")

    self._valid = True

  def _wrap_text_lines(self, text: str, max_width: float, font_size: int, max_lines: int = 2) -> tuple[list[str], bool]:
    words = text.split()
    if not words:
      return [], False

    lines: list[str] = []
    current_words: list[str] = []
    word_index = 0

    while word_index < len(words):
      candidate_words = current_words + [words[word_index]]
      candidate_line = " ".join(candidate_words)
      text_width = measure_text_cached(self._font_bold, candidate_line, font_size).x
      if text_width <= max_width or not current_words:
        current_words = candidate_words
        word_index += 1
      else:
        lines.append(" ".join(current_words))
        current_words = []
        if len(lines) >= max_lines:
          break

    if current_words and len(lines) < max_lines:
      lines.append(" ".join(current_words))

    truncated = word_index < len(words)
    if truncated and lines:
      shortened = lines[-1]
      candidate = f"{shortened}…"
      while shortened and measure_text_cached(self._font_bold, candidate, font_size).x > max_width:
        if " " in shortened:
          shortened = shortened.rsplit(" ", 1)[0]
        else:
          shortened = shortened[:-1]
        candidate = f"{shortened}…" if shortened else "…"
      lines[-1] = candidate

    return lines[:max_lines], truncated

  def _fit_title(self, text: str, max_width: float, preferred_size: int, minimum_size: int) -> tuple[list[str], int]:
    font_size = preferred_size
    while font_size > minimum_size:
      lines, truncated = self._wrap_text_lines(text, max_width, font_size)
      widest = max((measure_text_cached(self._font_bold, line, font_size).x for line in lines), default=0)
      if not truncated and widest <= max_width:
        return lines, font_size
      font_size -= 2
    lines, _ = self._wrap_text_lines(text, max_width, minimum_size)
    return lines, minimum_size

  def _truncate_text(self, text: str, max_width: float, font_size: int) -> str:
    if measure_text_cached(self._font_medium, text, font_size).x <= max_width:
      return text

    shortened = text.rstrip()
    candidate = f"{shortened}…"
    while shortened and measure_text_cached(self._font_medium, candidate, font_size).x > max_width:
      shortened = shortened[:-1].rstrip()
      candidate = f"{shortened}…" if shortened else "…"
    return candidate

  def _draw_wrapped_lines(self, lines: list[str], x: float, y: float, font_size: int) -> None:
    if not lines:
      return

    text_y = y if len(lines) == 1 else y - (font_size * 0.35)
    for index, line in enumerate(lines[:2]):
      rl.draw_text_ex(self._font_bold, line, rl.Vector2(x, text_y + index * font_size), font_size, 0, rl.WHITE)

  def _draw_top_aligned_lines(self, lines: list[str], x: float, y: float, font_size: int, line_gap: int = 0) -> None:
    for index, line in enumerate(lines[:2]):
      line_y = y + index * (font_size + line_gap)
      rl.draw_text_ex(self._font_bold, line, rl.Vector2(x, line_y), font_size, 0, rl.WHITE)

  def _render_default(self, rect: rl.Rectangle) -> None:
    container_width = min(int(rect.width - 120), 1080)
    container_width = max(container_width, 760)
    container_height = 225 if rect.width >= 1200 else 195
    container_x = int(rect.x + (rect.width - container_width) / 2)
    container_y = int(rect.y + 62)
    border_radius = 42 if container_height == 225 else 34
    icon_size = 150 if container_height == 225 else 122
    icon_padding = 30 if container_height == 225 else 24
    then_section_width = 180 if container_height == 225 else 144
    then_icon_size = 105 if container_height == 225 else 82
    preferred_font_size = 75 if container_height == 225 else 58
    minimum_font_size = 60 if container_height == 225 else 46
    distance_font_size = 48 if container_height == 225 else 40

    container = rl.Rectangle(container_x, container_y, container_width, container_height)
    self._interactive_rect = container
    rl.draw_rectangle_rounded(container, border_radius / container_height, 10, rl.Color(0, 0, 0, 192))

    icon_x = container_x + icon_padding
    icon_y = container_y + (container_height - icon_size - 38) // 2
    icon = self._get_icon(self._maneuver_type, self._modifier)
    dest_rect = rl.Rectangle(icon_x, icon_y, icon_size, icon_size)
    rl.draw_texture_pro(icon, rl.Rectangle(0, 0, icon.width, icon.height), dest_rect, rl.Vector2(0, 0), 0, rl.WHITE)

    distance_size = measure_text_cached(self._font_bold, self._distance, distance_font_size)
    distance_x = icon_x + (icon_size - distance_size.x) / 2
    distance_y = icon_y + icon_size + 5
    rl.draw_text_ex(self._font_bold, self._distance, rl.Vector2(distance_x, distance_y), distance_font_size, 0, rl.WHITE)

    show_next = self._has_next
    text_x = icon_x + icon_size + 53
    right_gutter = icon_padding + (then_section_width if show_next else 0)
    text_area_width = container_width - (text_x - container_x) - right_gutter
    title_lines, title_font_size = self._fit_title(self._primary_text, text_area_width, preferred_font_size, minimum_font_size)
    title_y = container_y + (container_height - title_font_size) / 2
    self._draw_wrapped_lines(title_lines, text_x, title_y, title_font_size)

    if self._secondary_text:
      secondary_font_size = 38 if container_height == 225 else 30
      secondary_text = self._truncate_text(self._secondary_text, text_area_width, secondary_font_size)
      secondary_y = container_y + container_height - (42 if container_height == 225 else 30)
      rl.draw_text_ex(
        self._font_medium,
        secondary_text,
        rl.Vector2(text_x, secondary_y),
        secondary_font_size,
        0,
        rl.Color(255, 255, 255, 180),
      )

    if not show_next:
      return

    divider_x = container_x + container_width - then_section_width - 8
    rl.draw_line_ex(
      rl.Vector2(divider_x, container_y + 23),
      rl.Vector2(divider_x, container_y + container_height - 23),
      2,
      rl.Color(255, 255, 255, 50),
    )

    then_x = divider_x + 15
    then_label = "Then"
    then_font_size = 53 if container_height == 225 else 40
    then_size = measure_text_cached(self._font_medium, then_label, then_font_size)
    then_label_x = then_x + (then_section_width - 23 - then_size.x) / 2
    rl.draw_text_ex(self._font_medium, then_label, rl.Vector2(then_label_x, container_y + 30), then_font_size, 0, rl.WHITE)

    next_icon = self._get_icon(self._next_maneuver_type, self._next_modifier)
    then_icon_x = then_x + (then_section_width - 23 - then_icon_size) / 2
    then_icon_y = container_y + (84 if container_height == 225 else 72)
    rl.draw_texture_pro(
      next_icon,
      rl.Rectangle(0, 0, next_icon.width, next_icon.height),
      rl.Rectangle(then_icon_x, then_icon_y, then_icon_size, then_icon_size),
      rl.Vector2(0, 0),
      0,
      rl.WHITE,
    )

  def _render_collapsed_default(self, rect: rl.Rectangle) -> None:
    chip_size = 94
    chip_x = int(rect.x + rect.width - chip_size - 32)
    chip_y = int(rect.y + 82)
    chip_rect = rl.Rectangle(chip_x, chip_y, chip_size, chip_size)
    self._interactive_rect = chip_rect

    rl.draw_rectangle_rounded(chip_rect, 0.34, 10, rl.Color(7, 11, 18, 228))
    rl.draw_rectangle_rounded_lines_ex(chip_rect, 0.34, 10, 2, rl.Color(255, 255, 255, 40))

    icon = self._get_icon(self._maneuver_type, self._modifier)
    icon_size = 58
    icon_x = chip_x + (chip_size - icon_size) / 2
    icon_y = chip_y + (chip_size - icon_size) / 2
    rl.draw_texture_pro(
      icon,
      rl.Rectangle(0, 0, icon.width, icon.height),
      rl.Rectangle(icon_x, icon_y, icon_size, icon_size),
      rl.Vector2(0, 0),
      0,
      rl.WHITE,
    )

  def _render_mici(self, rect: rl.Rectangle) -> None:
    left_safe = 96
    right_margin = 12
    available_width = max(260, int(rect.width - left_safe - right_margin))
    container_width = min(available_width, 420)
    container_height = 142
    container_x = int(rect.x + left_safe)
    container_y = int(rect.y + 16)
    container = rl.Rectangle(container_x, container_y, container_width, container_height)
    self._interactive_rect = container
    rl.draw_rectangle_rounded(container, 0.2, 10, rl.Color(7, 11, 18, 228))
    rl.draw_rectangle_rounded_lines_ex(container, 0.2, 10, 2, rl.Color(255, 255, 255, 34))

    chip_size = 68
    chip_padding = 18
    chip_x = container_x + chip_padding
    chip_y = container_y + 16
    chip_rect = rl.Rectangle(chip_x, chip_y, chip_size, chip_size)
    rl.draw_rectangle_rounded(chip_rect, 0.34, 10, rl.Color(70, 80, 94, 228))

    icon = self._get_icon(self._maneuver_type, self._modifier)
    icon_size = 48
    icon_x = chip_x + (chip_size - icon_size) / 2
    icon_y = chip_y + (chip_size - icon_size) / 2
    rl.draw_texture_pro(
      icon,
      rl.Rectangle(0, 0, icon.width, icon.height),
      rl.Rectangle(icon_x, icon_y, icon_size, icon_size),
      rl.Vector2(0, 0),
      0,
      rl.WHITE,
    )

    distance_font_size = 24
    distance_size = measure_text_cached(self._font_bold, self._distance, distance_font_size)
    distance_x = chip_x + (chip_size - distance_size.x) / 2
    distance_y = container_y + container_height - 34
    rl.draw_text_ex(self._font_bold, self._distance, rl.Vector2(distance_x, distance_y), distance_font_size, 0, rl.WHITE)

    show_next = self._has_next and available_width >= 660
    next_section_width = 92 if show_next else 0
    text_x = chip_x + chip_size + 18
    text_width = container_width - (text_x - container_x) - 18 - next_section_width
    title_lines, title_font_size = self._fit_title(self._primary_text, text_width, 32, 24)
    title_top = container_y + (26 if len(title_lines) == 1 else 16)
    self._draw_top_aligned_lines(title_lines, text_x, title_top, title_font_size, line_gap=2)

    show_secondary = bool(self._secondary_text)
    if show_secondary:
      secondary_font_size = 20
      secondary_text = self._truncate_text(self._secondary_text, text_width, secondary_font_size)
      rl.draw_text_ex(
        self._font_medium,
        secondary_text,
        rl.Vector2(text_x, container_y + container_height - 40),
        secondary_font_size,
        0,
        rl.Color(255, 255, 255, 172),
      )

    if not show_next:
      return

    divider_x = container_x + container_width - next_section_width
    rl.draw_line_ex(
      rl.Vector2(divider_x, container_y + 16),
      rl.Vector2(divider_x, container_y + container_height - 16),
      2,
      rl.Color(255, 255, 255, 38),
    )

    then_label = "Then"
    then_font_size = 20
    then_size = measure_text_cached(self._font_medium, then_label, then_font_size)
    then_x = divider_x + (next_section_width - then_size.x) / 2
    rl.draw_text_ex(self._font_medium, then_label, rl.Vector2(then_x, container_y + 16), then_font_size, 0, rl.Color(255, 255, 255, 196))

    next_icon = self._get_icon(self._next_maneuver_type, self._next_modifier)
    next_chip_size = 54
    next_chip_x = divider_x + (next_section_width - next_chip_size) / 2
    next_chip_y = container_y + 46
    next_chip_rect = rl.Rectangle(next_chip_x, next_chip_y, next_chip_size, next_chip_size)
    rl.draw_rectangle_rounded(next_chip_rect, 0.34, 10, rl.Color(70, 80, 94, 210))
    next_icon_size = 38
    next_icon_x = next_chip_x + (next_chip_size - next_icon_size) / 2
    next_icon_y = next_chip_y + (next_chip_size - next_icon_size) / 2
    rl.draw_texture_pro(
      next_icon,
      rl.Rectangle(0, 0, next_icon.width, next_icon.height),
      rl.Rectangle(next_icon_x, next_icon_y, next_icon_size, next_icon_size),
      rl.Vector2(0, 0),
      0,
      rl.WHITE,
    )

  def _render_collapsed_mici(self, rect: rl.Rectangle) -> None:
    chip_size = 72
    right_reserved = 160
    chip_x = int(rect.x + rect.width - chip_size - right_reserved)
    chip_y = int(rect.y + 18)
    chip_rect = rl.Rectangle(chip_x, chip_y, chip_size, chip_size)
    self._interactive_rect = chip_rect

    rl.draw_rectangle_rounded(chip_rect, 0.34, 10, rl.Color(7, 11, 18, 232))
    rl.draw_rectangle_rounded_lines_ex(chip_rect, 0.34, 10, 2, rl.Color(255, 255, 255, 40))

    icon = self._get_icon(self._maneuver_type, self._modifier)
    icon_size = 44
    icon_x = chip_x + (chip_size - icon_size) / 2
    icon_y = chip_y + (chip_size - icon_size) / 2
    rl.draw_texture_pro(
      icon,
      rl.Rectangle(0, 0, icon.width, icon.height),
      rl.Rectangle(icon_x, icon_y, icon_size, icon_size),
      rl.Vector2(0, 0),
      0,
      rl.WHITE,
    )

  def _render(self, rect: rl.Rectangle) -> None:
    self._update_state()
    if not self._valid:
      return
    if self._collapsed:
      if self._layout_variant == "mici":
        self._render_collapsed_mici(rect)
      else:
        self._render_collapsed_default(rect)
      return
    if self._layout_variant == "mici":
      self._render_mici(rect)
    else:
      self._render_default(rect)
