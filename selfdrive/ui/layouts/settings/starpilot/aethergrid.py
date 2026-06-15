from __future__ import annotations
from dataclasses import dataclass, replace
import math
import time
import pyray as rl
from collections.abc import Callable
from openpilot.system.ui.lib.application import gui_app, FontWeight, MousePos, MouseEvent
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.scroll_panel2 import GuiScrollPanel2
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget, DialogResult
from openpilot.system.ui.widgets.label import gui_label

from openpilot.selfdrive.ui.layouts.settings.starpilot.scribble import draw_custom_icon


GEOMETRY_OFFSET = 10
PLATE_TAU = 0.060
TILE_RADIUS = 0.08
TILE_SEGMENTS = 12
SLIDER_BUTTON_SIZE = 60
TILE_INSET = 1.0
TILE_RADIUS_PX = 18.0
TILE_SIGNAL_WIDTH = 1
MIN_TILE_WIDTH = 300

_HUD_BG_ON = rl.Color(12, 10, 18, 230)
_HUD_BORDER_OFF = rl.Color(28, 27, 34, 255)
_HUD_TEXT_DIM = rl.Color(160, 160, 175, 255)
_HUD_LED_BASE = rl.Color(36, 35, 44, 255)


class SPACING:
  xs: int = 4
  sm: int = 8
  md: int = 12
  lg: int = 16
  xl: int = 24
  xxl: int = 32
  xxxl: int = 48

  tile_gap: int = 16
  tile_content: int = 16
  line_gap: int = 8
  section_gap: int = 24
  tab_height: int = 96
  tab_panel_gap: int = 16


def hex_to_color(hex_str: str) -> rl.Color:
  hex_str = hex_str.lstrip('#')
  return rl.Color(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16), 255)


def _resolve_value(value, default=""):
  if callable(value):
    return value()
  return value if value is not None else default


def _with_alpha(color: rl.Color, alpha: int) -> rl.Color:
  return rl.Color(color.r, color.g, color.b, max(0, min(color.a, int(alpha))))


def _mix_colors(base: rl.Color, accent: rl.Color, weight: float, alpha: int | None = None) -> rl.Color:
  w = max(0.0, min(1.0, weight))
  return rl.Color(
    int(round(base.r + (accent.r - base.r) * w)),
    int(round(base.g + (accent.g - base.g) * w)),
    int(round(base.b + (accent.b - base.b) * w)),
    base.a if alpha is None else alpha,
  )


def _tone_step(color: rl.Color, delta: int, alpha: int | None = None) -> rl.Color:
  return rl.Color(
    max(0, min(255, color.r + delta)),
    max(0, min(255, color.g + delta)),
    max(0, min(255, color.b + delta)),
    color.a if alpha is None else alpha,
  )


def _default_substrate_for(color: rl.Color) -> rl.Color:
  return _mix_colors(rl.Color(14, 17, 23, 255), color, 0.14)


def _snap(value: float) -> float:
  return float(round(value))


def _snap_rect(rect: rl.Rectangle) -> rl.Rectangle:
  return rl.Rectangle(
    _snap(rect.x), _snap(rect.y),
    _snap(rect.width), _snap(rect.height),
  )


def _inset_rect(rect: rl.Rectangle, inset: float) -> rl.Rectangle:
  return _snap_rect(rl.Rectangle(rect.x + inset, rect.y + inset, rect.width - inset * 2, rect.height - inset * 2))


def _intersect_rect(a: rl.Rectangle, b: rl.Rectangle) -> rl.Rectangle:
  left = max(a.x, b.x)
  top = max(a.y, b.y)
  right = min(a.x + a.width, b.x + b.width)
  bottom = min(a.y + a.height, b.y + b.height)
  if right <= left or bottom <= top:
    return rl.Rectangle(left, top, 0, 0)
  return rl.Rectangle(left, top, right - left, bottom - top)


def _roundness_for(rect: rl.Rectangle, radius_px: float = TILE_RADIUS_PX) -> float:
  min_dim = max(1.0, min(rect.width, rect.height))
  return max(0.0, min(0.5, radius_px / min_dim))


def _segments_for(rect: rl.Rectangle, radius_px: float = TILE_RADIUS_PX) -> int:
  effective_radius = max(2.0, min(radius_px, min(rect.width, rect.height) / 2))
  return max(12, min(28, int(round(effective_radius * 1.25))))


def _draw_text_fit_common(
  font: rl.Font,
  text: str,
  pos: rl.Vector2,
  max_width: float,
  font_size: float,
  *,
  align_center: bool = False,
  align_right: bool = False,
  letter_spacing: float = 0,
  uppercase: bool = False,
  color: rl.Color = rl.WHITE,
  shadow_alpha: int = 0,
):
  if uppercase:
    text = text.upper()
  requested_spacing = letter_spacing if letter_spacing > 0 else font_size * 0.06
  spacing = round(requested_spacing)
  base_font_size = max(1, int(round(font_size)))
  size = measure_text_cached(font, text, base_font_size, spacing=spacing)
  actual_font_size = base_font_size
  if size.x > max_width:
    MIN_FONT = 8
    hi = max(MIN_FONT, int(round(font_size * (max_width / size.x))))
    lo = MIN_FONT
    actual_font_size = hi
    while lo < hi:
      mid = (lo + hi + 1) // 2
      fitted_spacing = round(requested_spacing * (mid / base_font_size))
      if measure_text_cached(font, text, mid, spacing=fitted_spacing).x <= max_width:
        lo = mid
        actual_font_size = mid
      else:
        hi = mid - 1
    fitted_spacing = round(requested_spacing * (actual_font_size / base_font_size))
    spacing = fitted_spacing
    render_width = measure_text_cached(font, text, actual_font_size, spacing=spacing).x
  else:
    render_width = size.x
  nudge_y = (font_size - actual_font_size) / 2
  draw_x = pos.x
  if align_center:
    draw_x = pos.x + (max_width - render_width) / 2
  elif align_right:
    draw_x = pos.x + max_width - render_width
  if shadow_alpha > 0:
    shadow_pos = rl.Vector2(round(draw_x + 1), round(pos.y + nudge_y + 1))
    rl.draw_text_ex(font, text, shadow_pos, actual_font_size, spacing, rl.Color(0, 0, 0, shadow_alpha))
  rl.draw_text_ex(font, text, rl.Vector2(round(draw_x), round(pos.y + nudge_y)), actual_font_size, spacing, color)


def _draw_rounded_fill(rect: rl.Rectangle, color: rl.Color, radius_px: float = TILE_RADIUS_PX, segments: int | None = None):
  snapped = _snap_rect(rect)
  rl.draw_rectangle_rounded(snapped, _roundness_for(snapped, radius_px), segments or _segments_for(snapped, radius_px), color)


def _draw_rounded_stroke(rect: rl.Rectangle, color: rl.Color, thickness: int = 1, radius_px: float = TILE_RADIUS_PX, segments: int | None = None):
  snapped = _snap_rect(rect)
  rl.draw_rectangle_rounded_lines_ex(snapped, _roundness_for(snapped, radius_px), segments or _segments_for(snapped, radius_px), thickness, color)


class AetherListColors:
  PANEL_BG = rl.Color(8, 8, 10, 255)
  PANEL_BORDER = rl.Color(255, 255, 255, 22)
  PANEL_GLOW = rl.Color(92, 116, 151, 34)
  HEADER = rl.Color(236, 242, 250, 255)
  SUBTEXT = rl.Color(164, 177, 196, 255)
  MUTED = rl.Color(126, 139, 158, 255)
  ROW_BG = rl.Color(255, 255, 255, 0)
  ROW_BORDER = rl.Color(255, 255, 255, 0)
  ROW_SEPARATOR = rl.Color(255, 255, 255, 16)
  ROW_HOVER = rl.Color(255, 255, 255, 8)
  CURRENT_BG = rl.Color(89, 116, 151, 18)
  CURRENT_BORDER = rl.Color(116, 136, 168, 44)
  ACTION_BG = rl.Color(255, 255, 255, 0)
  ACTION_SEPARATOR = rl.Color(255, 255, 255, 18)
  PRIMARY = hex_to_color("#8B5CF6")
  PRIMARY_SOFT = rl.Color(89, 116, 151, 48)
  DANGER = rl.Color(173, 78, 90, 255)
  DANGER_SOFT = rl.Color(173, 78, 90, 44)
  SUCCESS = rl.Color(94, 168, 130, 255)
  SUCCESS_SOFT = rl.Color(94, 168, 130, 44)
  WARNING = rl.Color(204, 158, 83, 255)
  SCROLL_TRACK = rl.Color(255, 255, 255, 10)
  SCROLL_THUMB = rl.Color(255, 255, 255, 90)


@dataclass(frozen=True)
class AetherListMetrics:
  max_content_width: int = 1560
  outer_margin_x: int = 18
  outer_margin_y: int = 24
  panel_padding_x: int = 16
  panel_padding_top: int = 28
  panel_padding_bottom: int = 22
  header_height: int = 210
  section_gap: int = 28
  section_header_height: int = 34
  section_header_gap: int = 12
  row_height: int = 122
  utility_row_height: int = 88
  row_radius: float = 0.12
  action_width: int = 188
  header_button_height: int = 58
  header_button_gap: int = 10  # noqa: used implicitly by driving_model
  fade_height: int = 24
  content_right_gutter: int = 18
  toggle_width: int = 78
  toggle_height: int = 42
  toggle_right_inset: int = 34
  adjustor_row_height: int = 94
  adjustor_row_active_height: int = 154
  adjustor_preset_height: int = 44
  adjustor_preset_gap: int = 10
  adjustor_scrubber_height: int = 52
  adjustor_value_pill_height: int = 36
  adjustor_value_pill_width: int = 144
  utility_value_right: int = 270
  utility_value_width: int = 220
  utility_chevron_right: int = 62
  menu_button_font_size: int = 18
  menu_button_roundness: float = 0.35
  menu_button_segments: int = 12


@dataclass(frozen=True)
class AetherListFrame:
  shell: rl.Rectangle
  header: rl.Rectangle
  scroll: rl.Rectangle


AETHER_LIST_METRICS = AetherListMetrics()
AETHER_COMPACT_ROW_HEIGHT = AETHER_LIST_METRICS.utility_row_height
COMPACT_PANEL_METRICS = replace(AETHER_LIST_METRICS, header_height=96)


@dataclass(frozen=True, slots=True)
class PanelStyle:
  shell_bg: rl.Color
  shell_border: rl.Color
  shell_glow: rl.Color
  surface_fill: rl.Color
  surface_border: rl.Color
  current_fill: rl.Color
  current_border: rl.Color
  title_color: rl.Color
  subtitle_color: rl.Color
  muted_color: rl.Color
  divider_color: rl.Color
  underline_color: rl.Color
  accent: rl.Color
  danger_fill: rl.Color
  danger_border: rl.Color
  danger_text: rl.Color


DEFAULT_PANEL_STYLE = PanelStyle(
  shell_bg=AetherListColors.PANEL_BG,
  shell_border=AetherListColors.PANEL_BORDER,
  shell_glow=AetherListColors.PANEL_GLOW,
  surface_fill=rl.Color(255, 255, 255, 4),
  surface_border=rl.Color(255, 255, 255, 14),
  current_fill=rl.Color(255, 255, 255, 12),
  current_border=rl.Color(255, 255, 255, 20),
  title_color=AetherListColors.HEADER,
  subtitle_color=AetherListColors.SUBTEXT,
  muted_color=AetherListColors.MUTED,
  divider_color=rl.Color(255, 255, 255, 14),
  underline_color=rl.Color(116, 136, 168, 150),
  accent=AetherListColors.PRIMARY,
  danger_fill=AetherListColors.DANGER_SOFT,
  danger_border=rl.Color(173, 78, 90, 50),
  danger_text=AetherListColors.DANGER,
)


def panel_style_from_color(hex_color: str, base: PanelStyle | None = None) -> PanelStyle:
    color = hex_to_color(hex_color)
    if base is None:
        base = DEFAULT_PANEL_STYLE
    return replace(
        base,
        accent=color,
        current_fill=rl.Color(color.r, color.g, color.b, 16),
        current_border=rl.Color(color.r, color.g, color.b, 42),
        underline_color=rl.Color(color.r, color.g, color.b, 150),
    )


def _inflate_rect(rect: rl.Rectangle, pad_x: float = 10, pad_y: float = 6) -> rl.Rectangle:
  return rl.Rectangle(rect.x - pad_x, rect.y - pad_y, rect.width + pad_x * 2, rect.height + pad_y * 2)


def _hit_rect(rect: rl.Rectangle, parent_rect: rl.Rectangle | None = None, pad_x: float = 10, pad_y: float = 6) -> rl.Rectangle:
  hit = _inflate_rect(rect, pad_x, pad_y)
  if parent_rect is not None:
    return rl.get_collision_rec(hit, parent_rect)
  return hit


def _point_hits(mouse_pos: MousePos, rect: rl.Rectangle, parent_rect: rl.Rectangle | None = None, pad_x: float = 10, pad_y: float = 6) -> bool:
  hit = _hit_rect(rect, parent_rect, pad_x, pad_y)
  return hit.width > 0 and hit.height > 0 and rl.check_collision_point_rec(mouse_pos, hit)


def build_list_panel_frame(rect: rl.Rectangle, metrics: AetherListMetrics = AETHER_LIST_METRICS) -> AetherListFrame:
  shell_w = min(rect.width - metrics.outer_margin_x * 2, metrics.max_content_width)
  shell_x = rect.x + (rect.width - shell_w) / 2
  shell_y = rect.y + metrics.outer_margin_y
  shell_h = rect.height - metrics.outer_margin_y * 2
  shell_rect = rl.Rectangle(shell_x, shell_y, shell_w, shell_h)

  header_rect = rl.Rectangle(
    shell_x + metrics.panel_padding_x,
    shell_y + metrics.panel_padding_top,
    shell_w - metrics.panel_padding_x * 2,
    metrics.header_height,
  )

  scroll_rect = rl.Rectangle(
    shell_x + metrics.panel_padding_x,
    header_rect.y + header_rect.height,
    shell_w - metrics.panel_padding_x * 2,
    shell_h - metrics.header_height - metrics.panel_padding_top - metrics.panel_padding_bottom,
  )

  return AetherListFrame(shell_rect, header_rect, scroll_rect)


def draw_list_panel_shell(frame: AetherListFrame, style: PanelStyle | None = None, *, bg: rl.Color = AetherListColors.PANEL_BG, border: rl.Color = AetherListColors.PANEL_BORDER, glow: rl.Color = AetherListColors.PANEL_GLOW):
  if style is not None:
    bg = style.shell_bg
    border = style.shell_border
    glow = style.shell_glow
  shell = _snap_rect(frame.shell)
  _draw_rounded_fill(shell, bg, radius_px=22)
  _draw_rounded_stroke(shell, border, radius_px=22)
  if glow.a > 0:
    glow_rect = _inset_rect(shell, 2)
    _draw_rounded_stroke(glow_rect, _with_alpha(glow, 14), radius_px=20)


def init_list_panel(rect: rl.Rectangle, style: PanelStyle | None = None, metrics: AetherListMetrics = AETHER_LIST_METRICS) -> tuple[AetherListFrame, rl.Rectangle, float]:
  frame = build_list_panel_frame(rect, metrics)
  draw_list_panel_shell(frame, style)
  scroll_rect = frame.scroll
  content_width = scroll_rect.width - AETHER_LIST_METRICS.content_right_gutter
  return frame, scroll_rect, content_width


def draw_interactive_rect(target_id: str, rect: rl.Rectangle, interactive_rects: dict[str, rl.Rectangle],
                           pressed_target: str | None, scroll_rect: rl.Rectangle | None = None,
                           pad_x: float = 6, pad_y: float = 0) -> tuple[bool, bool]:
  interactive_rects[target_id] = rect
  mouse_pos = gui_app.last_mouse_event.pos
  hovered = _point_hits(mouse_pos, rect, scroll_rect, pad_x=pad_x, pad_y=pad_y)
  pressed = pressed_target == target_id and hovered
  return hovered, pressed


def resolve_interactive_target(mouse_pos: MousePos, interactive_rects: dict[str, rl.Rectangle],
                                scroll_rect: rl.Rectangle | None = None,
                                pad_x: float = 6, pad_y: float = 0) -> str | None:
  for target_id, rect in interactive_rects.items():
    if _point_hits(mouse_pos, rect, scroll_rect, pad_x=pad_x, pad_y=pad_y):
      return target_id
  return None


class AetherInteractiveMixin:
  """Standard interactive target system for list-panel ManagerViews.

  Provides centralized _interactive_rects management, _pressed_target tracking,
  touch validation via _scroll_panel.is_touch_valid(), and standard mouse
  handling dispatch.

  Subclasses MUST define:
    - self._scroll_rect (rl.Rectangle) — for parent clipping in hit tests
    - self._scroll_panel (GuiScrollPanel2) — for touch validation

  Subclasses SHOULD override:
    - _activate_target(target_id) — custom action dispatch
    - _target_at(mouse_pos) — custom hit target resolution
  """

  def __init__(self, *args, **kwargs):
    self._interactive_rects: dict[str, rl.Rectangle] = {}
    self._pressed_target: str | None = None
    self._can_click = True
    super().__init__(*args, **kwargs)

  def _interactive_state(self, target_id: str, rect: rl.Rectangle, *, pad_y: float = 0) -> tuple[bool, bool]:
    self._interactive_rects[target_id] = rect
    hovered = _point_hits(gui_app.last_mouse_event.pos, rect, self._scroll_rect, pad_x=6, pad_y=pad_y)
    return hovered, self._pressed_target == target_id

  def _target_at(self, mouse_pos: MousePos) -> str | None:
    for target_id, rect in self._interactive_rects.items():
      if _point_hits(mouse_pos, rect, self._scroll_rect, pad_x=6, pad_y=0):
        return target_id
    return None

  def _activate_target(self, target_id: str | None):
    pass

  def _handle_mouse_press(self, mouse_pos: MousePos):
    self._pressed_target = self._target_at(mouse_pos)
    self._can_click = True

  def _handle_mouse_event(self, mouse_event: MouseEvent):
    if not self._scroll_panel.is_touch_valid():
      self._can_click = False
      return
    if self._pressed_target is not None and self._target_at(mouse_event.pos) != self._pressed_target:
      self._pressed_target = None

  def _handle_mouse_release(self, mouse_pos: MousePos):
    target = self._target_at(mouse_pos) if self._scroll_panel.is_touch_valid() else None
    if self._pressed_target is not None and self._pressed_target == target and self._can_click:
      self._activate_target(target)
    self._pressed_target = None
    self._can_click = True

  def show_event(self):
    super().show_event()
    self._pressed_target = None
    self._can_click = True

  def hide_event(self):
    super().hide_event()
    self._pressed_target = None
    self._can_click = True


class PanelManagerView(AetherInteractiveMixin, Widget):
  """Shared base for list-panel ManagerViews used by some panels.

  Encapsulates scroll infrastructure, the standard ``_render`` pipeline,
  shared two-column layout helpers, and a convenience toggle-tile factory.
  Subclasses declare panel-specific metrics via ``METRICS`` and override
  ``_draw_header``, ``_measure_content_height``, and
  ``_draw_scroll_content`` (at minimum).
  """

  METRICS: AetherListMetrics = AETHER_LIST_METRICS
  PANEL_STYLE: PanelStyle = DEFAULT_PANEL_STYLE
  TWO_COLUMN_BREAKPOINT: int = 1180
  COLUMN_GAP: float = 22.0

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._scroll_panel = GuiScrollPanel2(horizontal=False)
    self._scrollbar = AetherScrollbar()
    self._content_height = 0.0
    self._scroll_offset = 0.0
    self._scroll_rect = rl.Rectangle(0, 0, 0, 0)
    self._toggle_pages: list[list] = []
    self._page_count = 1
    self._current_page = 0
    self._page_grid: TileGrid | None = None
    self._page_animating = False
    self._page_anim_start = 0.0
    self._page_anim_from = 0.0
    self._page_anim_committed = False
    self._page_anim_prev_tiles: list = []
    self._page_drag_active = False
    self._page_drag_offset = 0.0
    self._page_drag_start_x = 0.0
    self._page_drag_start_y = 0.0
    self._page_clip_rect: rl.Rectangle | None = None

  # ── hooks ─────────────────────────────────────────────────

  def _on_frame_created(self, frame: AetherListFrame) -> None:
    """Called after ``init_list_panel`` builds the panel frame.
    Override to store ``frame.shell`` or perform per-frame setup."""

  def _draw_header(self, header_rect: rl.Rectangle) -> None:
    """Override to render the panel header."""

  def _measure_content_height(self, content_width: float) -> float:
    """Override to compute total scrollable content height."""

  def _draw_scroll_content(self, scroll_rect: rl.Rectangle, content_width: float) -> None:
    """Override to render visible content rows inside the scissor region."""

  # ── render pipeline ───────────────────────────────────────

  def _render(self, rect: rl.Rectangle) -> None:
    self._interactive_rects.clear()
    self.set_rect(rect)

    frame, scroll_rect, content_width = init_list_panel(rect, self.PANEL_STYLE, self.METRICS)
    self._scroll_rect = scroll_rect
    self._on_frame_created(frame)

    self._draw_header(frame.header)

    self._content_height = self._measure_content_height(content_width)
    self._scroll_panel.set_enabled(self.is_visible)
    self._scroll_offset = self._scroll_panel.update(
      scroll_rect, max(self._content_height, scroll_rect.height))

    rl.begin_scissor_mode(
      int(scroll_rect.x), int(scroll_rect.y),
      int(scroll_rect.width), int(scroll_rect.height))
    self._draw_scroll_content(scroll_rect, content_width)
    rl.end_scissor_mode()

    if self._content_height > scroll_rect.height:
      self._scrollbar.render(scroll_rect, self._content_height, self._scroll_offset)

    draw_list_scroll_fades(scroll_rect, self._content_height, self._scroll_offset,
                           AetherListColors.PANEL_BG)
    self._draw_page_dots(frame.scroll)

  # ── shared layout helpers ─────────────────────────────────

  def _uses_two_columns(self, width: float) -> bool:
    return width >= self.TWO_COLUMN_BREAKPOINT

  def _column_width(self, width: float) -> float:
    return (width - self.COLUMN_GAP) / 2 if self._uses_two_columns(width) else width

  def _section_height(self, count: int, row_height: float) -> float:
    return 0.0 if count <= 0 else count * row_height

  def _section_block_height(self, content_height: float) -> float:
    if content_height <= 0:
      return 0.0
    return self.METRICS.section_header_height + self.METRICS.section_header_gap + content_height

  def _stacked_section_height(self, sections: list[float]) -> float:
    if not sections:
      return 0.0
    return sum(sections) + self.METRICS.section_gap * (len(sections) - 1)

  # ── convenience builders ──────────────────────────────────

  def _make_toggle_tile(self, d: dict) -> ToggleTile:
    return ToggleTile(
      title=d["title"],
      get_state=d.get("get_state", d.get("get")),
      set_state=d.get("set_state", d.get("set")),
      bg_color=self.PANEL_STYLE.accent,
      desc=d.get("subtitle", d.get("desc", "")),
      is_enabled=d.get("is_enabled", d.get("enabled")),
      disabled_label=d.get("disabled_label", ""),
    )

  # ── pagination ─────────────────────────────────────────────

  PAGE_COMMIT_RATIO = 0.20
  PAGE_ANIM_DURATION = 0.28
  PAGE_SNAP_DURATION = 0.20

  PAGE_DOT_RADIUS = 6.0
  PAGE_DOT_GAP = 20.0

  @property
  def _has_pagination(self) -> bool:
    return self._page_count > 1

  def _set_toggle_pages(self, pages: list[list]) -> None:
    self._toggle_pages = pages
    self._page_count = max(1, len(pages))
    self._current_page = 0
    self._on_page_changed()

  def _get_page_defs(self) -> list:
    if self._has_pagination and self._current_page < len(self._toggle_pages):
      return self._toggle_pages[self._current_page]
    return []

  def _on_page_changed(self) -> None:
    if not getattr(self, '_toggle_pages', None) or self._page_grid is None:
      return
    self._page_grid.clear()
    page_idx = self._current_page if self._current_page < len(self._toggle_pages) else 0
    for d in self._toggle_pages[page_idx]:
      self._page_grid.add_tile(self._make_toggle_tile(d))

  # ── scissor helpers ────────────────────────────────────────

  def _page_scissor_push(self, rect: rl.Rectangle | None) -> None:
    if rect is None:
      return
    rl.end_scissor_mode()
    rl.begin_scissor_mode(int(rect.x), int(rect.y), int(rect.width), int(rect.height))

  def _page_scissor_pop(self) -> None:
    rl.end_scissor_mode()
    rl.begin_scissor_mode(int(self._scroll_rect.x), int(self._scroll_rect.y),
                          int(self._scroll_rect.width), int(self._scroll_rect.height))

  # ── drag + animation ───────────────────────────────────────

  GRID_PADDING = 12

  def _start_drag_commit(self, from_offset: float) -> None:
    if self._page_grid is not None:
      self._page_anim_prev_tiles = list(self._page_grid.tiles)
    self._page_animating = True
    self._page_anim_committed = True
    self._page_anim_start = time.monotonic()
    self._page_anim_from = from_offset

  def _start_drag_snap(self, from_offset: float) -> None:
    self._page_animating = True
    self._page_anim_committed = False
    self._page_anim_start = time.monotonic()
    self._page_anim_from = from_offset

  def _render_page_grid(self, grid: TileGrid, rect: rl.Rectangle, clip_rect: rl.Rectangle | None = None) -> None:
    if clip_rect is None:
      clip_rect = rl.Rectangle(rect.x - self.GRID_PADDING, rect.y - self.GRID_PADDING,
                               rect.width + self.GRID_PADDING * 2, rect.height + self.GRID_PADDING * 2)
    self._page_clip_rect = clip_rect

    # active drag
    if self._page_drag_active:
      drag_off = self._page_drag_offset
      self._page_scissor_push(clip_rect)
      grid.render(rl.Rectangle(rect.x + drag_off, rect.y, rect.width, rect.height))
      self._page_scissor_pop()
      return

    # no animation
    if not self._page_animating:
      grid.set_parent_rect(self._scroll_rect)
      grid.render(rect)
      return

    # animation
    elapsed = time.monotonic() - self._page_anim_start
    duration = self.PAGE_ANIM_DURATION if self._page_anim_committed else self.PAGE_SNAP_DURATION
    if elapsed >= duration:
      self._page_animating = False
      self._page_anim_prev_tiles.clear()
      grid.set_parent_rect(self._scroll_rect)
      grid.render(rect)
      return

    t = elapsed / duration
    t = 1.0 - (1.0 - t) ** 3

    if self._page_anim_committed:
      direction = 1 if self._page_anim_from < 0 else -1
      old_target = -direction * rect.width
      prev_offset = self._page_anim_from + (old_target - self._page_anim_from) * t
      cur_offset = direction * rect.width + (0.0 - direction * rect.width) * t

      self._page_scissor_push(clip_rect)
      if self._page_anim_prev_tiles:
        old_grid = TileGrid(columns=grid.get_column_count(), padding=grid.gap, tile_height=grid._tile_height)
        old_grid.tiles.extend(self._page_anim_prev_tiles)
        old_grid.set_parent_rect(self._scroll_rect)
        old_grid.render(rl.Rectangle(rect.x + prev_offset, rect.y, rect.width, rect.height))
      grid.set_parent_rect(self._scroll_rect)
      grid.render(rl.Rectangle(rect.x + cur_offset, rect.y, rect.width, rect.height))
      self._page_scissor_pop()
    else:
      cur_offset = self._page_anim_from * (1.0 - t)
      self._page_scissor_push(clip_rect)
      grid.set_parent_rect(self._scroll_rect)
      grid.render(rl.Rectangle(rect.x + cur_offset, rect.y, rect.width, rect.height))
      self._page_scissor_pop()

  # ── mouse handling ─────────────────────────────────────────

  def _handle_mouse_press(self, mouse_pos: MousePos) -> None:
    super()._handle_mouse_press(mouse_pos)
    if self._has_pagination:
      if self._page_animating:
        self._page_animating = False
        self._page_anim_prev_tiles.clear()
      self._page_drag_start_x = mouse_pos.x
      self._page_drag_start_y = mouse_pos.y
      self._page_drag_active = True
      self._page_drag_offset = 0.0

  def _handle_mouse_event(self, mouse_event: MouseEvent) -> None:
    super()._handle_mouse_event(mouse_event)
    if self._page_drag_active and self._has_pagination:
      dx = mouse_event.pos.x - self._page_drag_start_x
      dy = abs(mouse_event.pos.y - self._page_drag_start_y)
      if dy > abs(dx) * 1.2 and dy > 32:
        self._page_drag_active = False
        self._page_drag_offset = 0.0
        return
      if (self._current_page == 0 and dx > 0) or \
         (self._current_page >= self._page_count - 1 and dx < 0):
        dx = 0
      self._page_drag_offset = dx
      if abs(dx) > 6:
        self._pressed_target = None
        self._can_click = False

  def _handle_mouse_release(self, mouse_pos: MousePos) -> None:
    if self._page_drag_active and self._has_pagination:
      self._page_drag_active = False
      offset = self._page_drag_offset
      self._page_drag_offset = 0.0
      threshold = self._scroll_rect.width * self.PAGE_COMMIT_RATIO
      if abs(offset) > threshold:
        direction = 1 if offset < 0 else -1
        new_page = self._current_page + (1 if direction == 1 else -1)
        if 0 <= new_page < self._page_count:
          self._start_drag_commit(offset)
          self._current_page = new_page
          self._on_page_changed()
          return
        elif abs(offset) > 8:
          self._start_drag_snap(offset)
          return
      elif abs(offset) > 8:
        self._start_drag_snap(offset)
        return
    super()._handle_mouse_release(mouse_pos)

  # ── page indicator ─────────────────────────────────────────

  def _draw_page_dots(self, rect: rl.Rectangle) -> None:
    if not self._has_pagination:
      return
    clip = self._page_clip_rect
    n = min(self._page_count, 8)
    total_w = n * self.PAGE_DOT_RADIUS * 2 + max(0, n - 1) * self.PAGE_DOT_GAP
    start_x = (clip.x + (clip.width - total_w) / 2) if clip else rect.x + (rect.width - total_w) / 2
    dot_y = rect.y + rect.height + 8
    for i in range(n):
      cx = start_x + i * (self.PAGE_DOT_RADIUS * 2 + self.PAGE_DOT_GAP) + self.PAGE_DOT_RADIUS
      fill = self.PANEL_STYLE.accent if i == self._current_page else _with_alpha(AetherListColors.MUTED, 100)
      rl.draw_circle(int(cx), int(dot_y), self.PAGE_DOT_RADIUS, fill)
    if self._page_count > 8:
      more_x = start_x + n * (self.PAGE_DOT_RADIUS * 2 + self.PAGE_DOT_GAP)
      rl.draw_text_ex(
        gui_app.font(FontWeight.MEDIUM), "···",
        rl.Vector2(more_x, dot_y - 8), 16, 0, AetherListColors.MUTED)

  # ── lifecycle ──────────────────────────────────────────────

  def show_event(self) -> None:
    super().show_event()
    self._page_drag_active = False
    self._page_drag_offset = 0.0
    self._page_animating = False
    self._page_anim_prev_tiles.clear()
    if self._has_pagination and self._current_page != 0:
      self._current_page = 0
      self._on_page_changed()


PANEL_HEADER_TITLE_Y: int = 4
PANEL_HEADER_SUBTITLE_Y: int = 48
PANEL_HEADER_TITLE_FONT_SIZE: int = 40
PANEL_HEADER_SUBTITLE_FONT_SIZE: int = 22
PANEL_HEADER_TITLE_FONT: FontWeight = FontWeight.SEMI_BOLD
PANEL_HEADER_SUBTITLE_FONT: FontWeight = FontWeight.NORMAL


def draw_settings_panel_header(header_rect: rl.Rectangle, title: str, subtitle: str | None = None,
                                *,
                                title_size: int = PANEL_HEADER_TITLE_FONT_SIZE,
                                subtitle_size: int = PANEL_HEADER_SUBTITLE_FONT_SIZE,
                                max_title_width: float = 0.55,
                                max_subtitle_width: float = 0.58,
                                title_color: rl.Color = AetherListColors.HEADER,
                                subtitle_color: rl.Color = AetherListColors.SUBTEXT,
                                title_weight: FontWeight = PANEL_HEADER_TITLE_FONT,
                                subtitle_weight: FontWeight = PANEL_HEADER_SUBTITLE_FONT):
  title_rect = rl.Rectangle(header_rect.x, header_rect.y + PANEL_HEADER_TITLE_Y, header_rect.width * max_title_width, title_size + 2)
  gui_label(title_rect, title, title_size, title_color, title_weight)
  if subtitle:
    subtitle_rect = rl.Rectangle(header_rect.x, header_rect.y + PANEL_HEADER_SUBTITLE_Y, header_rect.width * max_subtitle_width, subtitle_size + 4)
    gui_label(subtitle_rect, subtitle, subtitle_size, subtitle_color, subtitle_weight)


def draw_soft_card(rect: rl.Rectangle, fill: rl.Color, border: rl.Color, radius: float = 0.08, segments: int = 18):
  radius_px = radius * min(rect.width, rect.height)
  _draw_rounded_fill(rect, fill, radius_px=radius_px, segments=segments)
  _draw_rounded_stroke(rect, border, radius_px=radius_px, segments=segments)


def draw_status_badges(
  start_x: float,
  y: float,
  items: list[str],
  style: PanelStyle,
  *,
  height: float = 28.0,
  font_size: int = 15,
  gap: float = 8.0,
  padding_x: float = 18.0,
  text_color: rl.Color = AetherListColors.HEADER,
):
  badge_x = start_x
  font = gui_app.font(FontWeight.BOLD)
  for item in items:
    text_size = measure_text_cached(font, item, font_size)
    badge_w = text_size.x + padding_x
    badge_rect = rl.Rectangle(badge_x, y, badge_w, height)

    fill_color = _with_alpha(style.accent, 24)
    border_color = _with_alpha(style.accent, 80)
    _draw_rounded_fill(badge_rect, fill_color, radius_px=8)
    _draw_rounded_stroke(badge_rect, border_color, radius_px=8)

    text_x = badge_rect.x + (badge_rect.width - text_size.x) / 2
    text_y = badge_rect.y + (badge_rect.height - text_size.y) / 2
    rl.draw_text_ex(font, item, rl.Vector2(round(text_x), round(text_y)), font_size, 0, text_color)

    badge_x += badge_w + gap


def draw_list_row_shell(
  rect: rl.Rectangle,
  *,
  current: bool = False,
  hovered: bool = False,
  pressed: bool = False,
  is_last: bool = False,
  alpha: int = 255,
  row_bg: rl.Color = AetherListColors.ROW_BG,
  row_border: rl.Color = AetherListColors.ROW_BORDER,
  row_separator: rl.Color = AetherListColors.ROW_SEPARATOR,
  row_hover: rl.Color = AetherListColors.ROW_HOVER,
  current_bg: rl.Color = AetherListColors.CURRENT_BG,
  current_border: rl.Color = AetherListColors.CURRENT_BORDER,
  row_radius: float = AetherListMetrics.row_radius,
  segments: int = 18,
  separator_inset: int = 22,
):
  bg = current_bg if current else row_bg
  border = current_border if current else row_border
  if hovered:
    bg = rl.Color(bg.r, bg.g, bg.b, min(bg.a + row_hover.a, 255))
  if pressed:
    bg = rl.Color(bg.r, bg.g, bg.b, min(bg.a + 8, 255))

  if bg.a > 0:
    rl.draw_rectangle_rounded(rect, row_radius, segments, _with_alpha(bg, alpha))
  if current and border.a > 0:
    rl.draw_rectangle_rounded_lines_ex(rect, row_radius, segments, 1, _with_alpha(border, alpha))
  if not is_last:
    line_y = int(rect.y + rect.height - 1)
    rl.draw_line(int(rect.x + separator_inset), line_y, int(rect.x + rect.width - separator_inset), line_y, _with_alpha(row_separator, alpha))


def draw_action_rail(
  rect: rl.Rectangle,
  action_width: int,
  *,
  current: bool = False,
  alpha: int = 255,
  fill: rl.Color = AetherListColors.ACTION_BG,
  current_fill: rl.Color = rl.Color(255, 255, 255, 6),
  separator: rl.Color = AetherListColors.ACTION_SEPARATOR,
  inset_y: int = 18,
):
  action_x = rect.x + rect.width - action_width
  action_rect = rl.Rectangle(action_x, rect.y, action_width, rect.height)
  action_fill = current_fill if current else fill
  if action_fill.a > 0:
    rl.draw_rectangle_rec(action_rect, _with_alpha(action_fill, alpha))
  rl.draw_line(int(action_x), int(rect.y + inset_y), int(action_x), int(rect.y + rect.height - inset_y), _with_alpha(separator, alpha))
  return action_rect


def draw_list_scroll_fades(
  scroll_rect: rl.Rectangle,
  content_height: float,
  scroll_offset: float,
  bg_color: rl.Color,
  *,
  fade_height: int = AETHER_LIST_METRICS.fade_height,
  right_trim: int = 12,
  threshold: int = 4,
):
  if content_height <= scroll_rect.height + threshold:
    return

  fade_h = min(fade_height, int(scroll_rect.height / 4))
  if scroll_offset < -threshold:
    rl.draw_rectangle_gradient_v(
      int(scroll_rect.x), int(scroll_rect.y), int(scroll_rect.width - right_trim), fade_h, _with_alpha(bg_color, 255), _with_alpha(bg_color, 0)
    )

  if (-scroll_offset + scroll_rect.height) < (content_height - threshold):
    bottom_y = int(scroll_rect.y + scroll_rect.height - fade_h)
    rl.draw_rectangle_gradient_v(
      int(scroll_rect.x), bottom_y, int(scroll_rect.width - right_trim), fade_h, _with_alpha(bg_color, 0), _with_alpha(bg_color, 255)
    )


def draw_busy_ring(
  center: rl.Vector2,
  phase: float,
  accent_color: rl.Color,
  *,
  track_color: rl.Color = rl.Color(255, 255, 255, 26),
  inner_radius: float = 20,
  outer_radius: float = 26,
  sweep: float = 260,
  thickness: int = 48,
):
  rl.draw_ring(center, inner_radius, outer_radius, 0, 360, thickness, track_color)
  rl.draw_ring(center, inner_radius, outer_radius, phase, phase + sweep, thickness, accent_color)


def draw_standard_toggle_row(
  rect: rl.Rectangle,
  title: str,
  subtitle: str,
  toggle_value: bool,
  *,
  enabled: bool = True,
  hovered: bool = False,
  pressed: bool = False,
  is_last: bool = False,
  style: PanelStyle = DEFAULT_PANEL_STYLE,
):
  """Draw a standard toggle settings row with consistent sizing."""
  draw_settings_list_row(
    rect,
    title=title,
    subtitle=subtitle,
    toggle_value=toggle_value,
    enabled=enabled,
    hovered=hovered,
    pressed=pressed,
    is_last=is_last,
    show_chevron=False,
    title_size=34, subtitle_size=22,
    style=style,
  )


def draw_toggle_switch(
  rect: rl.Rectangle,
  enabled: bool,
  *,
  is_enabled: bool = True,
  track_color: rl.Color = AetherListColors.PRIMARY,
  off_track_color: rl.Color = rl.Color(255, 255, 255, 24),
  knob_color: rl.Color = rl.WHITE,
  width: int = AETHER_LIST_METRICS.toggle_width,
  height: int = AETHER_LIST_METRICS.toggle_height,
  right_inset: int = AETHER_LIST_METRICS.toggle_right_inset,
  knob_offset: int = 20,
):
  toggle_rect = rl.Rectangle(rect.x + rect.width - width - right_inset, rect.y + (rect.height - height) / 2, width, height)
  track = track_color if enabled else off_track_color
  if not is_enabled:
    track = _with_alpha(_mix_colors(off_track_color, track, 0.35), 42)
    knob_color = _with_alpha(knob_color, 132)
  knob_x = toggle_rect.x + toggle_rect.width - knob_offset if enabled else toggle_rect.x + knob_offset
  rl.draw_rectangle_rounded(toggle_rect, 1.0, 16, track)
  rl.draw_circle(int(knob_x), int(toggle_rect.y + toggle_rect.height / 2), 16, knob_color)


def draw_action_pill(
  rect: rl.Rectangle,
  text: str,
  fill: rl.Color,
  border: rl.Color,
  text_color: rl.Color,
  *,
  font_size: int = AETHER_LIST_METRICS.menu_button_font_size,
  roundness: float = AETHER_LIST_METRICS.menu_button_roundness,
  segments: int = AETHER_LIST_METRICS.menu_button_segments,
):
  rl.draw_rectangle_rounded(rect, roundness, segments, fill)
  rl.draw_rectangle_rounded_lines_ex(rect, roundness, segments, 1, border)
  rl.draw_rectangle_rec(rl.Rectangle(rect.x, rect.y, rect.width, 1), _with_alpha(text_color, 18))
  _draw_text_fit_common(
    gui_app.font(FontWeight.SEMI_BOLD),
    text,
    rl.Vector2(rect.x + 12, rect.y + (rect.height - font_size) / 2),
    max(1.0, rect.width - 24),
    font_size,
    align_center=True,
    color=text_color,
  )


def draw_chevron_icon(rect: rl.Rectangle, color: rl.Color, *, thickness: float = 3.0):
  snapped = _snap_rect(rect)
  center_x = snapped.x + snapped.width / 2
  center_y = snapped.y + snapped.height / 2
  size = max(6.0, min(snapped.width, snapped.height) * 0.28)
  left_x = center_x - size * 0.6
  right_x = center_x + size * 0.35
  top_y = center_y - size
  bottom_y = center_y + size
  rl.draw_line_ex(rl.Vector2(left_x, top_y), rl.Vector2(right_x, center_y), thickness, color)
  rl.draw_line_ex(rl.Vector2(left_x, bottom_y), rl.Vector2(right_x, center_y), thickness, color)


TAB_HEIGHT = 68
TAB_GAP = 10
TAB_BOTTOM_GAP = 18


def draw_tab_bar(
  rect: rl.Rectangle,
  tab_defs: list[dict],
  active_tab_key: str,
  interactive_fn: Callable,
  *,
  subtitle_fn: Callable[[str], str] | None = None,
  style: PanelStyle = DEFAULT_PANEL_STYLE,
  tab_height: int = TAB_HEIGHT,
  tab_gap: int = TAB_GAP,
  tab_bottom_gap: int = TAB_BOTTOM_GAP,
) -> float:
  """Draw tab cards and register interactive targets.

  Returns the y position after the tab bar + bottom gap."""
  if not tab_defs:
    return rect.y
  n = len(tab_defs)
  tab_w = (rect.width - tab_gap * max(0, n - 1)) / max(1, n)
  for i, tab in enumerate(tab_defs):
    tab_rect = rl.Rectangle(rect.x + i * (tab_w + tab_gap), rect.y, tab_w, tab_height)
    hovered, pressed = interactive_fn(f"tab:{tab['id']}", tab_rect, pad_y=4)
    subtitle = subtitle_fn(tab["id"]) if subtitle_fn else tab.get("subtitle", "")
    draw_tab_card(
      tab_rect, tab["title"], subtitle,
      current=active_tab_key == tab["id"],
      hovered=hovered, pressed=pressed,
      title_size=26, subtitle_size=17, show_underline=True, style=style,
    )
  return rect.y + tab_height + tab_bottom_gap


def draw_tab_card(
  rect: rl.Rectangle,
  title: str,
  subtitle: str = "",
  *,
  current: bool = False,
  hovered: bool = False,
  pressed: bool = False,
  title_size: int = 19,
  subtitle_size: int = 14,
  show_underline: bool = False,
  underline_inset: int = 18,
  title_color: rl.Color | None = None,
  subtitle_color: rl.Color | None = None,
  style: PanelStyle = DEFAULT_PANEL_STYLE,
):
  fill = style.current_fill if current else style.surface_fill
  border = style.current_border if current else style.surface_border
  if not current and hovered:
    fill = rl.Color(fill.r, fill.g, fill.b, min(fill.a + 3, 255))
  if pressed:
    fill = rl.Color(fill.r, fill.g, fill.b, min(fill.a + 6, 22))

  draw_soft_card(rect, fill, border)

  if subtitle:
    resolved_title_color = title_color or (style.title_color if current else style.subtitle_color)
    resolved_subtitle_color = subtitle_color or (style.title_color if current else style.muted_color)
    gap = 4
    total_text_h = title_size + gap + subtitle_size
    text_start_y = rect.y + (rect.height - total_text_h) / 2
    _draw_text_fit_common(
      gui_app.font(FontWeight.MEDIUM),
      title,
      rl.Vector2(rect.x + 12, text_start_y),
      max(1.0, rect.width - 24),
      title_size,
      align_center=True,
      color=resolved_title_color,
    )
    _draw_text_fit_common(
      gui_app.font(FontWeight.NORMAL),
      subtitle,
      rl.Vector2(rect.x + 12, text_start_y + title_size + gap),
      max(1.0, rect.width - 24),
      subtitle_size,
      align_center=True,
      color=resolved_subtitle_color,
    )
  else:
    resolved_title_color = title_color or (style.title_color if current else style.subtitle_color)
    _draw_text_fit_common(
      gui_app.font(FontWeight.MEDIUM),
      title,
      rl.Vector2(rect.x + 12, rect.y + (rect.height - title_size) / 2),
      max(1.0, rect.width - 24),
      title_size,
      align_center=True,
      color=resolved_title_color,
    )

  if show_underline and current:
    rl.draw_rectangle_rec(
      rl.Rectangle(rect.x + underline_inset, rect.y + rect.height - 4, rect.width - underline_inset * 2, 2),
      style.underline_color,
    )


def draw_metric_strip(
  rect: rl.Rectangle,
  metrics: list[tuple[str, str]],
  *,
  gap: int = 18,
  min_col_width: float = 72.0,
  label_size: int = 14,
  value_size: int = 18,
  style: PanelStyle = DEFAULT_PANEL_STYLE,
  label_top_offset: int = 0,
  value_top_offset: int = 14,
  divider_top_offset: int = 2,
  divider_bottom_offset: int = 16,
):
  if not metrics:
    return

  available_w = max(1.0, rect.width)
  col_w = max(min_col_width, (available_w - gap * max(0, len(metrics) - 1)) / max(1, len(metrics)))
  label_font = gui_app.font(FontWeight.MEDIUM)
  value_font = gui_app.font(FontWeight.SEMI_BOLD)

  for index, (label, value) in enumerate(metrics):
    metric_x = rect.x + index * (col_w + gap)
    _draw_text_fit_common(
      label_font,
      label,
      rl.Vector2(metric_x, rect.y + label_top_offset),
      col_w,
      label_size,
      color=style.muted_color,
    )
    _draw_text_fit_common(
      value_font,
      value,
      rl.Vector2(metric_x, rect.y + value_top_offset),
      col_w,
      value_size,
      color=style.title_color,
    )
    if index < len(metrics) - 1:
      divider_x = metric_x + col_w + gap / 2
      rl.draw_line(
        int(divider_x),
        int(rect.y + divider_top_offset),
        int(divider_x),
        int(rect.y + value_top_offset + divider_bottom_offset),
        style.divider_color,
      )


def draw_section_header(
  rect: rl.Rectangle,
  title: str = "",
  *,
  trailing_text: str = "",
  title_size: int = 26,
  trailing_size: int = 20,
  title_color: rl.Color | None = None,
  trailing_color: rl.Color | None = None,
  style: PanelStyle = DEFAULT_PANEL_STYLE,
):
  if title:
    trailing_reserved = min(320.0, rect.width * 0.38) if trailing_text else 0.0
    title_rect = rl.Rectangle(rect.x, rect.y + (rect.height - title_size) / 2, max(1.0, rect.width - trailing_reserved), title_size + 4)
    gui_label(title_rect, title, title_size, title_color or style.subtitle_color, FontWeight.MEDIUM)

  if trailing_text:
    trailing_rect = rl.Rectangle(rect.x, rect.y + (rect.height - trailing_size) / 2, rect.width, trailing_size + 4)
    gui_label(
      trailing_rect,
      trailing_text,
      trailing_size,
      trailing_color or style.subtitle_color,
      FontWeight.NORMAL,
      alignment=rl.GuiTextAlignment.TEXT_ALIGN_RIGHT,
    )


def draw_empty_state_card(
  rect: rl.Rectangle,
  title: str,
  body: str,
  *,
  title_size: int = 30,
  body_size: int = 22,
  body_inset_x: int = 48,
  title_gap: int = 14,
  title_top_padding: float | None = None,
  body_height: float | None = None,
  fill: rl.Color | None = None,
  border: rl.Color | None = None,
  radius: float = 0.08,
  segments: int = 18,
  style: PanelStyle = DEFAULT_PANEL_STYLE,
):
  card_rect = _snap_rect(rect)
  resolved_fill = fill if fill is not None else style.surface_fill
  resolved_border = border if border is not None else style.surface_border
  draw_soft_card(card_rect, resolved_fill, resolved_border, radius=radius, segments=segments)

  title_h = max(34.0, title_size + 8)
  title_y = card_rect.y + (title_top_padding if title_top_padding is not None else max(24.0, min(42.0, card_rect.height * 0.22)))
  inset_x = min(float(body_inset_x), max(18.0, card_rect.width * 0.22))
  body_y = title_y + title_h + title_gap
  resolved_body_h = body_height if body_height is not None else max(40.0, card_rect.height - (body_y - card_rect.y) - 24.0)

  gui_label(
    rl.Rectangle(card_rect.x, title_y, card_rect.width, title_h),
    title,
    title_size,
    style.title_color,
    FontWeight.MEDIUM,
    alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER,
  )
  gui_label(
    rl.Rectangle(card_rect.x + inset_x, body_y, max(1.0, card_rect.width - inset_x * 2), resolved_body_h),
    body,
    body_size,
    style.subtitle_color,
    FontWeight.NORMAL,
    alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER,
  )


def draw_list_group_shell(
  rect: rl.Rectangle,
  *,
  fill: rl.Color | None = None,
  border: rl.Color | None = None,
  radius: float = 0.055,
  segments: int = 18,
  style: PanelStyle = DEFAULT_PANEL_STYLE,
):
  draw_soft_card(rect, fill if fill is not None else style.surface_fill, border if border is not None else style.surface_border, radius=radius, segments=segments)


def draw_settings_list_row(
  rect: rl.Rectangle,
  *,
  title: str,
  subtitle: str = "",
  value: str = "",
  toggle_value: bool | None = None,
  enabled: bool = True,
  hovered: bool = False,
  pressed: bool = False,
  is_last: bool = False,
  show_chevron: bool = True,
  title_size: int = 28,
  subtitle_size: int = 20,
  value_size: int = 24,
  separator_inset: int = 22,
  title_color: rl.Color | None = None,
  subtitle_color: rl.Color | None = None,
  value_color: rl.Color | None = None,
  style: PanelStyle = DEFAULT_PANEL_STYLE,
):
  draw_rect = _snap_rect(rect)
  resolved_title_color = title_color or (style.title_color if enabled else style.muted_color)
  resolved_subtitle_color = subtitle_color or (style.subtitle_color if enabled else style.muted_color)
  resolved_value_color = value_color or (style.title_color if enabled else style.muted_color)
  chevron_rect = rl.Rectangle(draw_rect.x + draw_rect.width - AETHER_LIST_METRICS.utility_chevron_right, draw_rect.y + 18, 26, 26)
  draw_list_row_shell(
    draw_rect,
    hovered=hovered and enabled,
    pressed=pressed and enabled,
    is_last=is_last,
    row_bg=rl.Color(255, 255, 255, 0),
    row_border=rl.Color(255, 255, 255, 0),
    row_separator=style.divider_color,
    current_bg=rl.Color(255, 255, 255, 0),
    current_border=rl.Color(255, 255, 255, 0),
    separator_inset=separator_inset,
  )

  # Compute text width based on right-side elements — no truncation, font-size reduces gracefully
  text_left = draw_rect.x + 24
  if toggle_value is not None:
    text_right = draw_rect.x + draw_rect.width - AETHER_LIST_METRICS.toggle_width - AETHER_LIST_METRICS.toggle_right_inset - 12
  elif value:
    text_right = draw_rect.x + draw_rect.width - AETHER_LIST_METRICS.utility_value_right - 12
  elif show_chevron:
    text_right = draw_rect.x + draw_rect.width - AETHER_LIST_METRICS.utility_chevron_right - 26 - 12
  else:
    text_right = draw_rect.x + draw_rect.width - 24
  text_width = max(100.0, text_right - text_left)
  _draw_text_fit_common(
    gui_app.font(FontWeight.MEDIUM), title,
    rl.Vector2(text_left, draw_rect.y + 16),
    text_width, title_size,
    color=resolved_title_color,
  )
  if subtitle:
    _draw_text_fit_common(
      gui_app.font(FontWeight.NORMAL), subtitle,
      rl.Vector2(text_left, draw_rect.y + 54),
      text_width, subtitle_size,
      color=resolved_subtitle_color,
    )

  if toggle_value is not None:
    draw_toggle_switch(draw_rect, bool(toggle_value), is_enabled=enabled, track_color=style.accent)
    return

  if value:
    value_left = draw_rect.x + draw_rect.width - AETHER_LIST_METRICS.utility_value_right
    value_right = chevron_rect.x - 16 if show_chevron else draw_rect.x + draw_rect.width - 24
    value_rect = rl.Rectangle(value_left, draw_rect.y + 20, max(48.0, value_right - value_left), 28)
    gui_label(
      value_rect,
      value,
      value_size,
      resolved_value_color,
      FontWeight.MEDIUM,
      alignment=rl.GuiTextAlignment.TEXT_ALIGN_RIGHT,
    )
  if show_chevron:
    draw_chevron_icon(
      chevron_rect,
      style.muted_color,
    )


def format_adjustor_value(value: float, *, step: float = 1.0, unit: str = "", labels: dict[float, str] | None = None) -> str:
  label_map = labels or {}
  tolerance = max(abs(step) * 0.5, 1e-4) if step != 0 else 1e-4
  for label_value, label in label_map.items():
    if abs(float(label_value) - float(value)) <= tolerance:
      return label

  if step > 0 and step < 1:
    decimals = max(1, min(3, len(f"{step:.6f}".rstrip("0").split(".")[-1])))
    return f"{value:.{decimals}f}{unit}"
  if abs(value - round(value)) <= tolerance:
    return f"{int(round(value))}{unit}"
  return f"{value:.2f}".rstrip("0").rstrip(".") + unit



class AetherInlineRangeControl(Widget):
  def __init__(
    self,
    min_val: float,
    max_val: float,
    step: float,
    current_val: float,
    on_change: Callable[[float], None],
    *,
    on_commit: Callable[[float], None] | None = None,
    unit: str = "",
    labels: dict[float, str] | None = None,
    color: rl.Color = AetherListColors.PRIMARY,
    major_tick_count: int = 5,
  ):
    super().__init__()
    self.min_val = min_val
    self.max_val = max_val
    self.step = step
    self.current_val = current_val
    self._on_change = on_change
    self._on_commit = on_commit
    self._unit = unit
    self._labels = labels or {}
    self._color = color
    self._major_tick_count = max(0, major_tick_count)
    self._font = gui_app.font(FontWeight.SEMI_BOLD)

    self._smooth_value = current_val
    self._thumb_focus = 0.0
    self._pending_drag = False
    self._is_dragging = False
    self._started_on_thumb = False
    self._press_start = rl.Vector2(0, 0)
    self._value_at_press = current_val

    self._pressed_button: int = 0
    self._button_press_started = 0.0
    self._next_repeat_at = 0.0
    self._repeat_count = 0
    self._button_press_changed = False

    self._minus_rect = rl.Rectangle(0, 0, 0, 0)
    self._plus_rect = rl.Rectangle(0, 0, 0, 0)
    self._track_rect = rl.Rectangle(0, 0, 0, 0)
    self._thumb_rect = rl.Rectangle(0, 0, 0, 0)

  @property
  def is_interacting(self) -> bool:
    return self._pending_drag or self._is_dragging or self._pressed_button != 0

  def set_value(self, value: float) -> None:
    self.current_val = self._clamp_and_snap(value)

  def reset_interaction(self) -> None:
    self._pending_drag = False
    self._is_dragging = False
    self._started_on_thumb = False
    self._pressed_button = 0
    self._repeat_count = 0
    self._button_press_changed = False

  def set_touch_valid_callback(self, touch_callback: Callable[[], bool]) -> None:
    super().set_touch_valid_callback(touch_callback)

  def _cancel_interaction(self, *, revert: bool = False) -> None:
    if revert and self.current_val != self._value_at_press:
      self.current_val = self._value_at_press
      self._on_change(self.current_val)
    self.reset_interaction()

  def _clamp_and_snap(self, value: float) -> float:
    if self.step <= 0:
      return max(self.min_val, min(self.max_val, value))
    snapped = round((value - self.min_val) / self.step) * self.step + self.min_val
    return max(self.min_val, min(self.max_val, snapped))

  def _step_value(self, direction: int) -> bool:
    new_val = self._clamp_and_snap(self.current_val + direction * self.step)
    if new_val == self.current_val:
      return False
    self.current_val = new_val
    self._on_change(self.current_val)
    self._button_press_changed = True
    return True

  def _value_fraction(self, value: float) -> float:
    value_range = self.max_val - self.min_val
    if value_range == 0:
      return 0.0
    return max(0.0, min(1.0, (value - self.min_val) / value_range))

  def _update_val_from_mouse(self, mouse_pos: MousePos) -> None:
    if self._track_rect.width <= 0:
      return
    rel_x = max(0.0, min(1.0, (mouse_pos.x - self._track_rect.x) / self._track_rect.width))
    value = self.min_val + rel_x * (self.max_val - self.min_val)
    snapped = self._clamp_and_snap(value)
    if snapped != self.current_val:
      self.current_val = snapped
      self._on_change(self.current_val)

  def _commit_if_needed(self) -> None:
    if self.current_val != self._value_at_press and self._on_commit is not None:
      self._on_commit(self.current_val)

  def _update_state(self):
    super()._update_state()
    if self._pressed_button == 0:
      return
    now = time.monotonic()
    if now < self._next_repeat_at:
      return

    if self._step_value(self._pressed_button):
      self._repeat_count += 1
    repeat_interval = 0.12 if self._repeat_count < 3 else 0.075
    self._next_repeat_at = now + repeat_interval

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if not self._touch_valid() or not rl.check_collision_point_rec(mouse_pos, self._rect):
      return

    self._value_at_press = self.current_val
    self._button_press_changed = False
    now = time.monotonic()
    if rl.check_collision_point_rec(mouse_pos, self._minus_rect):
      self._pressed_button = -1
      self._button_press_started = now
      self._next_repeat_at = now + 0.34
      self._repeat_count = 0
      return
    if rl.check_collision_point_rec(mouse_pos, self._plus_rect):
      self._pressed_button = 1
      self._button_press_started = now
      self._next_repeat_at = now + 0.34
      self._repeat_count = 0
      return

    self._pending_drag = True
    self._started_on_thumb = rl.check_collision_point_rec(mouse_pos, _inflate_rect(self._thumb_rect, 12, 12))
    self._press_start = rl.Vector2(mouse_pos.x, mouse_pos.y)

  def _handle_mouse_release(self, mouse_pos: MousePos):
    if self._pressed_button != 0:
      direction = self._pressed_button
      button_rect = self._minus_rect if direction < 0 else self._plus_rect
      if rl.check_collision_point_rec(mouse_pos, button_rect) and self._repeat_count == 0:
        self._step_value(direction)
      self._pressed_button = 0
      self._repeat_count = 0
      self._commit_if_needed()
      return

    if self._is_dragging:
      self._is_dragging = False
      self._commit_if_needed()
      return

    if self._pending_drag:
      if not self._started_on_thumb and rl.check_collision_point_rec(mouse_pos, self._rect):
        self._update_val_from_mouse(mouse_pos)
        self._commit_if_needed()
      self._pending_drag = False
      self._started_on_thumb = False

  def _handle_mouse_event(self, mouse_event: MouseEvent):
    mouse_in_rect = rl.check_collision_point_rec(mouse_event.pos, self._rect)
    if mouse_event.left_released and self.is_interacting and not mouse_in_rect:
      if self._pressed_button != 0:
        self._pressed_button = 0
        self._repeat_count = 0
        self._commit_if_needed()
      elif self._is_dragging or self._pending_drag:
        self._cancel_interaction(revert=True)
      return

    if not self._touch_valid():
      self._cancel_interaction(revert=True)
      return

    if self._pressed_button != 0:
      button_rect = self._minus_rect if self._pressed_button < 0 else self._plus_rect
      if not rl.check_collision_point_rec(mouse_event.pos, _inflate_rect(button_rect, 4, 4)):
        self._pressed_button = 0
        self._repeat_count = 0
        if self._button_press_changed:
          self._commit_if_needed()
      return

    if self._pending_drag and not self._is_dragging:
      dx = mouse_event.pos.x - self._press_start.x
      dy = mouse_event.pos.y - self._press_start.y
      if abs(dy) > 12 and abs(dy) > abs(dx):
        self._pending_drag = False
        self._started_on_thumb = False
        return
      if abs(dx) > 12 and abs(dx) >= abs(dy):
        self._pending_drag = False
        self._is_dragging = True

    if self._is_dragging:
      dx = mouse_event.pos.x - self._press_start.x
      dy = mouse_event.pos.y - self._press_start.y
      if abs(dy) > 18 and abs(dy) > abs(dx) * 1.15:
        self._cancel_interaction(revert=True)
        return
      self._update_val_from_mouse(mouse_event.pos)

  def _draw_button(self, rect: rl.Rectangle, label: str, *, pressed: bool = False):
    fill = rl.Color(255, 255, 255, 8 if not pressed else 14)
    border = rl.Color(255, 255, 255, 18 if not pressed else 28)
    _draw_rounded_fill(rect, fill, radius_px=14)
    _draw_rounded_stroke(rect, border, radius_px=14)
    _draw_text_fit_common(
      self._font,
      label,
      rl.Vector2(rect.x + 10, rect.y + (rect.height - 22) / 2),
      max(1.0, rect.width - 20),
      22,
      align_center=True,
      color=AetherListColors.HEADER,
    )

  def _render(self, rect: rl.Rectangle):
    rect = _snap_rect(rect)
    self.set_rect(rect)
    dt = rl.get_frame_time()
    self._smooth_value += (self.current_val - self._smooth_value) * (1 - math.exp(-dt / 0.075))
    thumb_target = 1.0 if self._is_dragging or self._pending_drag else 0.0
    self._thumb_focus += (thumb_target - self._thumb_focus) * (1 - math.exp(-dt / 0.070))

    button_size = min(rect.height, 44)
    button_y = rect.y + (rect.height - button_size) / 2
    self._minus_rect = _snap_rect(rl.Rectangle(rect.x, button_y, button_size, button_size))
    self._plus_rect = _snap_rect(rl.Rectangle(rect.x + rect.width - button_size, button_y, button_size, button_size))
    self._draw_button(self._minus_rect, "-", pressed=self._pressed_button < 0)
    self._draw_button(self._plus_rect, "+", pressed=self._pressed_button > 0)

    track_x = self._minus_rect.x + self._minus_rect.width + 14
    track_w = max(1.0, self._plus_rect.x - 14 - track_x)
    lane_h = rect.height
    track_h = 4.0
    track_y = rect.y + (lane_h - track_h) / 2
    self._track_rect = _snap_rect(rl.Rectangle(track_x, track_y, track_w, track_h))

    rl.draw_rectangle_rounded(self._track_rect, 1.0, 12, rl.Color(255, 255, 255, 18))
    if self._major_tick_count > 1:
      for index in range(self._major_tick_count):
        frac = index / max(1, self._major_tick_count - 1)
        tick_x = self._track_rect.x + frac * self._track_rect.width
        rl.draw_rectangle_rec(rl.Rectangle(tick_x - 1, rect.y + rect.height / 2 - 8, 2, 16), rl.Color(255, 255, 255, 24))

    fill_frac = self._value_fraction(self._smooth_value)
    fill_w = fill_frac * self._track_rect.width
    if fill_w > 1:
      fill_rect = _snap_rect(rl.Rectangle(self._track_rect.x, self._track_rect.y, fill_w, self._track_rect.height))
      rl.draw_rectangle_rounded(fill_rect, 1.0, 12, _with_alpha(self._color, 220))

    thumb_w = 22 + self._thumb_focus * 4
    thumb_h = 28 + self._thumb_focus * 4
    thumb_center_x = self._track_rect.x + fill_frac * self._track_rect.width
    thumb_center_y = rect.y + rect.height / 2
    self._thumb_rect = _snap_rect(rl.Rectangle(thumb_center_x - thumb_w / 2, thumb_center_y - thumb_h / 2, thumb_w, thumb_h))
    thumb_fill = _mix_colors(rl.Color(224, 230, 238, 255), self._color, 0.12)
    _draw_rounded_fill(self._thumb_rect, thumb_fill, radius_px=12)
    _draw_rounded_stroke(self._thumb_rect, rl.Color(14, 17, 23, 52), radius_px=12)
    if self._thumb_focus > 0.02:
      _draw_rounded_stroke(_inflate_rect(self._thumb_rect, 1, 1), _with_alpha(self._color, int(70 * self._thumb_focus)), radius_px=13)

    if self._is_dragging or self._pressed_button != 0:
      bubble_text = format_adjustor_value(self.current_val, step=self.step, unit=self._unit, labels=self._labels)
      bubble_w = max(80.0, min(132.0, 44.0 + len(bubble_text) * 10.0))
      bubble_rect = _snap_rect(rl.Rectangle(thumb_center_x - bubble_w / 2, rect.y - 40, bubble_w, 32))
      bubble_fill = _mix_colors(rl.Color(18, 22, 28, 255), self._color, 0.18)
      bubble_border = _with_alpha(self._color, 70)
      _draw_rounded_fill(bubble_rect, bubble_fill, radius_px=14)
      _draw_rounded_stroke(bubble_rect, bubble_border, radius_px=14)
      _draw_text_fit_common(
        gui_app.font(FontWeight.MEDIUM),
        bubble_text,
        rl.Vector2(bubble_rect.x + 10, bubble_rect.y + 7),
        max(1.0, bubble_rect.width - 20),
        16,
        align_center=True,
        color=AetherListColors.HEADER,
      )


class AetherAdjustorRow(Widget):
  def __init__(
    self,
    title: str,
    subtitle: str,
    min_val: float,
    max_val: float,
    step: float,
    get_value: Callable[[], float],
    on_change: Callable[[float], None],
    *,
    on_commit: Callable[[float], None] | None = None,
    unit: str = "",
    labels: dict[float, str] | None = None,
    presets: list[float] | None = None,
    is_active: bool | Callable[[], bool] = False,
    set_active: Callable[[bool], None] | None = None,
    style: PanelStyle = DEFAULT_PANEL_STYLE,
    color: rl.Color | None = None,
  ):
    super().__init__()
    self._title = title
    self._subtitle = subtitle
    self._get_value = get_value
    self._is_active = is_active
    self._set_active = set_active
    self._style = style
    self._color = color or style.accent
    self._presets = presets or []
    self._preset_applied = False
    self._font_title = gui_app.font(FontWeight.MEDIUM)
    self._font_subtitle = gui_app.font(FontWeight.NORMAL)
    self._font_value = gui_app.font(FontWeight.SEMI_BOLD)
    self._focus_progress = 0.0
    self._pressed_zone: str | None = None
    self._is_last = False
    self._header_rect = rl.Rectangle(0, 0, 0, 0)
    self._value_rect = rl.Rectangle(0, 0, 0, 0)
    self._hint_rect = rl.Rectangle(0, 0, 0, 0)
    self._preset_rects: list[tuple[float, rl.Rectangle]] = []
    self._scrubber_rect = rl.Rectangle(0, 0, 0, 0)
    self._scrubber = self._child(
      AetherInlineRangeControl(
        min_val,
        max_val,
        step,
        get_value(),
        on_change,
        on_commit=on_commit,
        unit=unit,
        labels=labels,
        color=self._color,
      )
    )
    self._unit = unit
    self._labels = labels or {}
    self._step = step

  @property
  def is_interacting(self) -> bool:
    return self._scrubber.is_interacting

  def _active(self) -> bool:
    return bool(self._is_active() if callable(self._is_active) else self._is_active)

  def reset_interaction(self) -> None:
    self._pressed_zone = None
    self._scrubber.reset_interaction()

  def set_touch_valid_callback(self, touch_callback: Callable[[], bool]) -> None:
    super().set_touch_valid_callback(touch_callback)
    self._scrubber.set_touch_valid_callback(touch_callback)

  def set_is_last(self, is_last: bool) -> None:
    self._is_last = is_last

  def _current_value(self) -> float:
    return self._scrubber.current_val if (self._active() or self._scrubber.is_interacting) else self._get_value()

  def formatted_value(self) -> str:
    return format_adjustor_value(self._current_value(), step=self._step, unit=self._unit, labels=self._labels)

  def measure_height(self, width: float) -> float:
    del width
    if not self._active():
      return float(AETHER_LIST_METRICS.adjustor_row_height)
    preset_height = AETHER_LIST_METRICS.adjustor_preset_height + AETHER_LIST_METRICS.adjustor_preset_gap if self._presets else 0
    return float(AETHER_LIST_METRICS.adjustor_row_active_height + preset_height)

  def _set_active_state(self, active: bool) -> None:
    if self._set_active is not None:
      self._set_active(active)

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if not self._touch_valid() or not rl.check_collision_point_rec(mouse_pos, self._rect):
      return
    self._pressed_zone = None

    if self._active():
      for preset_value, preset_rect in self._preset_rects:
        if rl.check_collision_point_rec(mouse_pos, _inflate_rect(preset_rect, 4, 4)):
          self._pressed_zone = f"preset:{preset_value}"
          return
      if rl.check_collision_point_rec(mouse_pos, self._scrubber_rect):
        self._pressed_zone = "scrubber"
        return

    if rl.check_collision_point_rec(mouse_pos, self._header_rect) or rl.check_collision_point_rec(mouse_pos, self._value_rect) or rl.check_collision_point_rec(mouse_pos, self._hint_rect):
      self._pressed_zone = "header"

  def _handle_mouse_release(self, mouse_pos: MousePos):
    pressed_zone = self._pressed_zone
    self._pressed_zone = None

    if pressed_zone == "scrubber":
      return

    if pressed_zone and pressed_zone.startswith("preset:"):
      self._scrubber._value_at_press = self._scrubber.current_val
      try:
        preset_value = float(pressed_zone.split(":", 1)[1])
      except ValueError:
        return
      for value, preset_rect in self._preset_rects:
        if value == preset_value and rl.check_collision_point_rec(mouse_pos, _inflate_rect(preset_rect, 4, 4)):
          self._scrubber.set_value(preset_value)
          self._scrubber._on_change(self._scrubber.current_val)
          self._scrubber._commit_if_needed()
          self._preset_applied = True
          return
      return

    if pressed_zone == "header":
      active = self._active()
      if rl.check_collision_point_rec(mouse_pos, _inflate_rect(self._header_rect, 6, 4)) or rl.check_collision_point_rec(mouse_pos, _inflate_rect(self._value_rect, 6, 4)) or rl.check_collision_point_rec(mouse_pos, _inflate_rect(self._hint_rect, 6, 4)):
        self._set_active_state(not active)

  def _handle_mouse_event(self, mouse_event: MouseEvent):
    del mouse_event

  def _render_preset_chip(self, rect: rl.Rectangle, text: str, *, current: bool, pressed: bool):
    fill = rl.Color(255, 255, 255, 5)
    border = rl.Color(255, 255, 255, 14)
    text_color = self._style.subtitle_color
    if current:
      fill = _mix_colors(rl.Color(18, 22, 28, 255), self._color, 0.22, alpha=255)
      border = _with_alpha(self._color, 72)
      text_color = self._style.title_color
    elif pressed:
      fill = rl.Color(255, 255, 255, 10)
      border = rl.Color(255, 255, 255, 22)

    _draw_rounded_fill(rect, fill, radius_px=13)
    _draw_rounded_stroke(rect, border, radius_px=13)
    _draw_text_fit_common(
      gui_app.font(FontWeight.MEDIUM),
      text,
      rl.Vector2(rect.x + 10, rect.y + 7),
      max(1.0, rect.width - 20),
      15,
      align_center=True,
      color=text_color,
    )

  def _render(self, rect: rl.Rectangle):
    rect = _snap_rect(rect)
    self.set_rect(rect)
    active = self._active()
    if not self._scrubber.is_interacting:
      self._scrubber.set_value(self._get_value())

    dt = rl.get_frame_time()
    focus_target = 1.0 if active else 0.0
    self._focus_progress += (focus_target - self._focus_progress) * (1 - math.exp(-dt / 0.09))

    hovered = _point_hits(gui_app.last_mouse_event.pos, rect, self._parent_rect, pad_x=6, pad_y=0)
    current_bg = _with_alpha(_mix_colors(rl.Color(18, 22, 28, 255), self._color, 0.16), int(18 + self._focus_progress * 14))
    current_border = _with_alpha(self._color, int(34 + self._focus_progress * 34))
    draw_list_row_shell(
      rect,
      current=active or self._focus_progress > 0.02,
      hovered=hovered and not self.is_interacting,
      pressed=self._pressed_zone == "header",
      is_last=self._is_last,
      row_bg=rl.Color(255, 255, 255, 0),
      row_border=rl.Color(255, 255, 255, 0),
      row_separator=self._style.divider_color,
      current_bg=current_bg,
      current_border=current_border,
    )

    value_pill_w = min(float(AETHER_LIST_METRICS.adjustor_value_pill_width), max(118.0, rect.width * 0.22))
    self._header_rect = rl.Rectangle(rect.x, rect.y, rect.width, min(rect.height, 78))
    self._value_rect = _snap_rect(rl.Rectangle(rect.x + rect.width - value_pill_w - 18, rect.y + 14, value_pill_w, AETHER_LIST_METRICS.adjustor_value_pill_height))
    content_right = self._value_rect.x - 18
    content_left = rect.x + 24
    content_width = max(120.0, content_right - content_left)

    gui_label(rl.Rectangle(content_left, rect.y + 14, content_width, 28), self._title, 24, self._style.title_color, FontWeight.MEDIUM)
    gui_label(rl.Rectangle(content_left, rect.y + 44, content_width, 22), self._subtitle, 18, self._style.subtitle_color, FontWeight.NORMAL)

    pill_fill = rl.Color(255, 255, 255, 5)
    pill_border = rl.Color(255, 255, 255, 14)
    if active:
      pill_fill = _mix_colors(rl.Color(18, 22, 28, 255), self._color, 0.20, alpha=255)
      pill_border = _with_alpha(self._color, 64)
    _draw_rounded_fill(self._value_rect, pill_fill, radius_px=16)
    _draw_rounded_stroke(self._value_rect, pill_border, radius_px=16)
    _draw_text_fit_common(
      self._font_value,
      self.formatted_value(),
      rl.Vector2(self._value_rect.x + 14, self._value_rect.y + 8),
      max(1.0, self._value_rect.width - 28),
      18,
      align_center=True,
      color=self._style.title_color,
    )

    hint_y = rect.y + 76
    self._hint_rect = _snap_rect(rl.Rectangle(content_left, hint_y, rect.width - 48, 8))
    hint_track = _snap_rect(rl.Rectangle(self._hint_rect.x, self._hint_rect.y + 2, self._hint_rect.width, 4))
    rl.draw_rectangle_rounded(hint_track, 1.0, 10, rl.Color(255, 255, 255, 10))
    fill_w = hint_track.width * self._scrubber._value_fraction(self._current_value())
    if fill_w > 0:
      rl.draw_rectangle_rounded(_snap_rect(rl.Rectangle(hint_track.x, hint_track.y, fill_w, hint_track.height)), 1.0, 10, _with_alpha(self._color, 180 if active else 120))

    if not active:
      return

    tray_alpha = max(0, min(255, int(255 * self._focus_progress)))
    tray_top = rect.y + 92 - (1.0 - self._focus_progress) * 6
    current_y = tray_top
    self._preset_rects.clear()

    if self._presets:
      chip_gap = 12.0
      chip_h = float(AETHER_LIST_METRICS.adjustor_preset_height)
      chip_w = max(68.0, (rect.width - 48 - chip_gap * (len(self._presets) - 1)) / max(1, len(self._presets)))
      chip_x = content_left
      for preset_value in self._presets:
        chip_rect = _snap_rect(rl.Rectangle(chip_x, current_y, chip_w, chip_h))
        self._preset_rects.append((preset_value, chip_rect))
        self._render_preset_chip(
          chip_rect,
          format_adjustor_value(preset_value, step=self._step, unit=self._unit, labels=self._labels),
          current=abs(self._current_value() - preset_value) <= max(abs(self._step) * 0.5, 1e-4),
          pressed=self._pressed_zone == f"preset:{preset_value}",
        )
        chip_x += chip_w + chip_gap
      current_y += chip_h + AETHER_LIST_METRICS.adjustor_preset_gap

    self._scrubber_rect = _snap_rect(rl.Rectangle(content_left, current_y, rect.width - 48, AETHER_LIST_METRICS.adjustor_scrubber_height))
    self._scrubber.set_parent_rect(self._parent_rect)
    self._scrubber.render(self._scrubber_rect)


def draw_selection_list_row(
  rect: rl.Rectangle,
  *,
  title: str,
  subtitle: str = "",
  action_text: str = "",
  current: bool = False,
  hovered: bool = False,
  pressed: bool = False,
  is_last: bool = False,
  alpha: int = 255,
  action_width: int = AETHER_LIST_METRICS.action_width,
  action_chip: bool = False,
  action_pill: bool = False,
  title_size: int = 30,
  subtitle_size: int = 20,
  action_text_size: int = 18,
  action_pill_height: int = 44,
  action_pill_width: float | None = None,
  title_color: rl.Color = AetherListColors.HEADER,
  subtitle_color: rl.Color = AetherListColors.SUBTEXT,
  action_fill: rl.Color = AetherListColors.CURRENT_BG,
  action_border: rl.Color = AetherListColors.CURRENT_BORDER,
  action_text_color: rl.Color = AetherListColors.HEADER,
  row_bg: rl.Color = AetherListColors.ROW_BG,
  row_border: rl.Color = AetherListColors.ROW_BORDER,
  row_separator: rl.Color = AetherListColors.ROW_SEPARATOR,
  row_hover: rl.Color = AetherListColors.ROW_HOVER,
  current_bg: rl.Color = AetherListColors.CURRENT_BG,
  current_border: rl.Color = AetherListColors.CURRENT_BORDER,
):
  draw_rect = _snap_rect(rect)
  draw_list_row_shell(
    draw_rect,
    current=current,
    hovered=hovered,
    pressed=pressed,
    is_last=is_last,
    alpha=alpha,
    row_bg=row_bg,
    row_border=row_border,
    row_separator=row_separator,
    row_hover=row_hover,
    current_bg=current_bg,
    current_border=current_border,
  )
  action_rect = rl.Rectangle(draw_rect.x + draw_rect.width - action_width, draw_rect.y, action_width, draw_rect.height)
  if not action_pill:
    action_rect = draw_action_rail(draw_rect, action_width, current=current, alpha=alpha)

  info_gap = 36 if action_pill else 42
  info_rect = rl.Rectangle(draw_rect.x + 24, draw_rect.y + 16, max(0.0, draw_rect.width - action_width - info_gap), draw_rect.height - 32)
  title_font = gui_app.font(FontWeight.MEDIUM)
  subtitle_font = gui_app.font(FontWeight.NORMAL)

  if subtitle:
    text_height = title_size + subtitle_size + 8
    title_y = info_rect.y + (info_rect.height - text_height) / 2
    subtitle_y = title_y + title_size + 8
  else:
    title_y = info_rect.y + (info_rect.height - title_size) / 2
    subtitle_y = title_y

  _draw_text_fit_common(
    title_font,
    title,
    rl.Vector2(info_rect.x, title_y),
    info_rect.width,
    title_size,
    color=_with_alpha(title_color, alpha),
  )

  if subtitle:
    _draw_text_fit_common(
      subtitle_font,
      subtitle,
      rl.Vector2(info_rect.x, subtitle_y),
      info_rect.width,
      subtitle_size,
      color=_with_alpha(subtitle_color, alpha),
    )

  if action_text:
    if action_pill:
      available_w = max(96.0, action_rect.width - 28)
      chip_w = min(available_w, action_pill_width) if action_pill_width is not None else min(available_w, max(96.0, 42 + len(action_text) * 9))
      chip_h = min(float(action_pill_height), max(36.0, action_rect.height - 28))
      chip_rect = rl.Rectangle(action_rect.x + action_rect.width - chip_w - 18, action_rect.y + (action_rect.height - chip_h) / 2, chip_w, chip_h)
      draw_action_pill(
        chip_rect,
        action_text,
        _with_alpha(action_fill, alpha),
        _with_alpha(action_border, alpha),
        _with_alpha(action_text_color, alpha),
        font_size=action_text_size,
      )
      return chip_rect
    if action_chip:
      available_w = max(74.0, action_rect.width - 24)
      chip_w = min(available_w, max(74.0, 44 + len(action_text) * 9))
      chip_rect = rl.Rectangle(action_rect.x + (action_rect.width - chip_w) / 2, action_rect.y + (action_rect.height - 40) / 2, chip_w, 40)
      AetherChip(
        action_text,
        _with_alpha(action_fill, alpha),
        _with_alpha(action_border, alpha),
        _with_alpha(action_text_color, alpha),
        pill=True,
      ).render(chip_rect)
    else:
      _draw_text_fit_common(
        title_font,
        action_text,
        rl.Vector2(action_rect.x + 16, action_rect.y + (action_rect.height - 18) / 2),
        max(1.0, action_rect.width - 32),
        action_text_size,
        align_center=True,
        color=_with_alpha(action_text_color, alpha),
      )

  return action_rect


def draw_status_led(center: rl.Vector2, enabled: bool):
  if enabled:
    led_color = rl.Color(110, 175, 245, 255)
    rl.draw_circle(int(center.x), int(center.y), 11, rl.Color(110, 175, 245, 24))
    rl.draw_circle(int(center.x), int(center.y), 6, led_color)
  else:
    rl.draw_circle(int(center.x), int(center.y), 7, rl.Color(14, 16, 22, 255))
    rl.draw_ring(center, 5, 6, 0, 360, 24, rl.Color(70, 78, 95, 140))


def draw_overflow_dots(center: rl.Vector2, color: rl.Color):
  dot_r = 4
  gap = 12
  for i in range(3):
    rl.draw_circle(int(center.x + (i - 1) * gap), int(center.y), dot_r, color)



def draw_heart_icon(center: rl.Vector2, color: rl.Color):
  rl.draw_circle(int(center.x - 5), int(center.y - 3), 7, color)
  rl.draw_circle(int(center.x + 5), int(center.y - 3), 7, color)
  rl.draw_triangle(
    rl.Vector2(center.x + 13, center.y + 1),
    rl.Vector2(center.x - 13, center.y + 1),
    rl.Vector2(center.x, center.y + 13),
    color,
  )


def draw_download_icon(center: rl.Vector2, color: rl.Color):
  shaft_top = rl.Vector2(center.x, center.y - 18)
  shaft_bottom = rl.Vector2(center.x, center.y + 8)
  left_head = rl.Vector2(center.x - 11, center.y - 2)
  right_head = rl.Vector2(center.x + 11, center.y - 2)
  tray_left = rl.Vector2(center.x - 14, center.y + 18)
  tray_right = rl.Vector2(center.x + 14, center.y + 18)
  rl.draw_line_ex(shaft_top, shaft_bottom, 4, color)
  rl.draw_line_ex(left_head, shaft_bottom, 4, color)
  rl.draw_line_ex(right_head, shaft_bottom, 4, color)
  rl.draw_line_ex(tray_left, tray_right, 4, color)


class AetherButton(Widget):
  def __init__(
    self,
    text: str | Callable[[], str],
    click_callback: Callable[[], None] | None = None,
    enabled: bool | Callable[[], bool] = True,
    emphasized: bool = False,
    font_size: int = 24,
    accent_color: rl.Color | None = None,
  ):
    super().__init__()
    self._text = text
    self._emphasized = emphasized
    self._font_size = font_size
    self._accent_color = accent_color
    self.set_click_callback(click_callback)
    self.set_enabled(enabled)

  @property
  def text(self) -> str:
    return str(_resolve_value(self._text, ""))

  def set_text(self, text: str | Callable[[], str]):
    self._text = text

  def set_emphasized(self, emphasized: bool):
    self._emphasized = emphasized

  def _render(self, rect: rl.Rectangle):
    enabled = self.enabled
    hovered = enabled and rl.check_collision_point_rec(gui_app.last_mouse_event.pos, rect)
    pressed = enabled and self.is_pressed

    if self._emphasized:
      accent = self._accent_color or AetherListColors.PRIMARY
      bg = accent if enabled else rl.Color(accent.r, accent.g, accent.b, 80)
      border = _with_alpha(accent, 190 if enabled else 70)
    else:
      bg = rl.Color(255, 255, 255, 10 if enabled else 5)
      border = rl.Color(255, 255, 255, 22 if enabled else 10)

    if hovered:
      bg = rl.Color(min(bg.r + 10, 255), min(bg.g + 10, 255), min(bg.b + 10, 255), bg.a)
    if pressed:
      bg = rl.Color(max(bg.r - 8, 0), max(bg.g - 8, 0), max(bg.b - 8, 0), bg.a)

    rl.draw_rectangle_rounded(rect, 0.18, 12, bg)
    rl.draw_rectangle_rounded_lines_ex(rect, 0.18, 12, 1, border)
    rl.draw_rectangle_rec(rl.Rectangle(rect.x, rect.y, rect.width, 1), _with_alpha(AetherListColors.HEADER, 18 if enabled else 8))
    if self._emphasized and enabled:
      rl.draw_rectangle_rec(rl.Rectangle(rect.x + 1, rect.y + 1, rect.width - 2, 1), _with_alpha(AetherListColors.HEADER, 14))
    _draw_text_fit_common(
      gui_app.font(FontWeight.MEDIUM),
      self.text,
      rl.Vector2(rect.x + 18, rect.y + (rect.height - self._font_size) / 2),
      max(1.0, rect.width - 36),
      self._font_size,
      align_center=True,
      color=AetherListColors.HEADER if enabled else AetherListColors.MUTED,
    )


class AetherChip:
  def __init__(self, text: str | Callable[[], str], fill: rl.Color, border: rl.Color, text_color: rl.Color, pill: bool = False, font_size: int = 18):
    self._text = text
    self._fill = fill
    self._border = border
    self._text_color = text_color
    self._pill = pill
    self._font_size = font_size

  @property
  def text(self) -> str:
    return str(_resolve_value(self._text, ""))

  def render(self, rect: rl.Rectangle):
    roundness = 1.0 if self._pill else 0.4
    rl.draw_rectangle_rounded(rect, roundness, 18, self._fill)
    rl.draw_rectangle_rounded_lines_ex(rect, roundness, 18, 1, _with_alpha(self._border, 110))
    _draw_text_fit_common(
      gui_app.font(FontWeight.MEDIUM),
      self.text,
      rl.Vector2(rect.x + 12, rect.y + (rect.height - self._font_size) / 2),
      max(1.0, rect.width - 24),
      self._font_size,
      align_center=True,
      color=self._text_color,
    )


class AetherScrollbar:
  def __init__(
    self,
    track_color: rl.Color = AetherListColors.SCROLL_TRACK,
    thumb_color: rl.Color = AetherListColors.SCROLL_THUMB,
    track_width: int = 4,
    track_inset_x: int = 7,
    track_inset_y: int = 8,
    min_thumb_height: float = 46.0,
  ):
    self._track_color = track_color
    self._thumb_color = thumb_color
    self._track_width = track_width
    self._track_inset_x = track_inset_x
    self._track_inset_y = track_inset_y
    self._min_thumb_height = min_thumb_height

  def render(self, rect: rl.Rectangle, content_height: float, scroll_offset: float):
    if content_height <= 0 or content_height <= rect.height:
      return

    track_rect = rl.Rectangle(rect.x + rect.width - self._track_inset_x, rect.y + self._track_inset_y, self._track_width, rect.height - self._track_inset_y * 2)
    rl.draw_rectangle_rounded(track_rect, 1.0, 12, self._track_color)

    max_scroll = max(content_height - rect.height, 1.0)
    thumb_height = max(self._min_thumb_height, track_rect.height * (rect.height / content_height))
    thumb_range = max(track_rect.height - thumb_height, 0.0)
    thumb_y = track_rect.y + (-scroll_offset / max_scroll) * thumb_range
    thumb_rect = rl.Rectangle(track_rect.x, thumb_y, track_rect.width, thumb_height)
    rl.draw_rectangle_rounded(thumb_rect, 1.0, 12, self._thumb_color)


# ── SettingRow / SettingSection dataclasses ──

SECTION_GAP = AETHER_LIST_METRICS.section_gap
SECTION_HEADER_HEIGHT = AETHER_LIST_METRICS.section_header_height
SECTION_HEADER_GAP = AETHER_LIST_METRICS.section_header_gap
ROW_HEIGHT = AETHER_LIST_METRICS.row_height


@dataclass
class SettingRow:
  id: str
  type: str
  title: str
  subtitle: str = ""
  visible: Callable[[], bool] | None = None
  enabled: Callable[[], bool] | None = None
  disabled_label: str = ""
  get_state: Callable[[], bool] | None = None
  set_state: Callable[[bool], None] | None = None
  get_value: Callable[[], str] | None = None
  on_click: Callable[[], object] | None = None
  action_text: str = ""
  action_danger: bool = False
  navigate_to: str = ""


@dataclass
class SettingSection:
  title: str
  rows: list[SettingRow]
  visible: Callable[[], bool] | None = None
  tab_key: str = ""
  column_pair: str = ""
  row_height: int = ROW_HEIGHT


# ── AetherSettingsView — reusable list-panel ManagerView ──

class AetherSettingsView(AetherInteractiveMixin, Widget):
  """Reusable list-panel manager for toggle/value/action settings pages."""

  TAB_HEIGHT = 68
  TAB_GAP = 10
  TAB_BOTTOM_GAP = 18
  COLUMN_GAP = 22
  TWO_COLUMN_BREAKPOINT = 1180

  def __init__(self, controller, sections: list[SettingSection],
               *, header_title: str = "", header_subtitle: str = "",
               tab_defs: list[dict] | None = None,
               panel_style=None, fade_height: float = AETHER_LIST_METRICS.fade_height,
               metrics = COMPACT_PANEL_METRICS):
    super().__init__()
    self._panel_style = panel_style or DEFAULT_PANEL_STYLE
    self._fade_height = fade_height
    self._metrics = metrics
    self._controller = controller
    self._sections = sections
    self._header_title = header_title
    self._header_subtitle = header_subtitle
    self._has_header = bool(header_title)
    self._tab_defs = tab_defs
    self._active_tab_key = tab_defs[0]["id"] if tab_defs else ""
    self._scroll_panel = GuiScrollPanel2(horizontal=False)
    self._scrollbar = AetherScrollbar()
    self._content_height = 0.0
    self._scroll_offset = 0.0
    self._scroll_rect = rl.Rectangle(0, 0, 0, 0)

  def _find_row(self, target_id: str) -> SettingRow | None:
    for section in self._active_sections():
      for row in section.rows:
        if f"{row.type}:{row.id}" == target_id:
          return row
    return None

  def _activate_target(self, target_id: str | None):
    if not target_id:
      return
    if target_id.startswith("tab:") and self._tab_defs:
      self._active_tab_key = target_id[4:]
      return
    row = self._find_row(target_id)
    if row is None:
      return
    if row.navigate_to:
      self._controller._navigate_to(row.navigate_to)
    elif row.on_click:
      row.on_click()
    elif row.type == "toggle" and row.set_state and row.get_state:
      row.set_state(not row.get_state())

  def _render(self, rect: rl.Rectangle):
    self.set_rect(rect)
    self._interactive_rects.clear()

    frame, scroll_rect, content_width = init_list_panel(rect, self._panel_style, metrics=self._metrics)
    self._scroll_rect = scroll_rect

    if self._has_header:
      self._draw_header(frame.header)

    self._content_height = self._measure_content_height(content_width)
    self._scroll_panel.set_enabled(self.is_visible)
    self._scroll_offset = self._scroll_panel.update(
      self._scroll_rect, max(self._content_height, self._scroll_rect.height))

    rl.begin_scissor_mode(int(self._scroll_rect.x), int(self._scroll_rect.y),
                           int(self._scroll_rect.width), int(self._scroll_rect.height))
    self._draw_scroll_content(self._scroll_rect, content_width)
    rl.end_scissor_mode()

    if self._content_height > self._scroll_rect.height:
      self._scrollbar.render(self._scroll_rect, self._content_height, self._scroll_offset)

    draw_list_scroll_fades(self._scroll_rect, self._content_height, self._scroll_offset,
                            AetherListColors.PANEL_BG, fade_height=self._fade_height)

  def _draw_header(self, rect: rl.Rectangle):
    title = tr(self._header_title) if self._header_title else ""
    subtitle = tr(self._header_subtitle) if self._header_subtitle else ""
    draw_settings_panel_header(rect, title, subtitle)

  def _active_sections(self) -> list[SettingSection]:
    if self._tab_defs and self._active_tab_key:
      return [s for s in self._sections if s.tab_key == self._active_tab_key]
    return self._sections

  def _visible_rows(self, section: SettingSection) -> list[SettingRow]:
    if section.visible is not None and not section.visible():
      return []
    return [row for row in section.rows if row.visible is None or row.visible()]

  def _measure_content_height(self, width: float) -> float:
    total = 0.0
    if self._tab_defs:
      total += self.TAB_HEIGHT + self.TAB_BOTTOM_GAP
    active = self._active_sections()
    i = 0
    while i < len(active):
      section = active[i]
      visible_rows = self._visible_rows(section)
      if not visible_rows:
        i += 1
        continue
      row_h = len(visible_rows) * section.row_height
      if section.column_pair and i + 1 < len(active) and active[i + 1].column_pair == section.column_pair and self._uses_two_columns(width):
        right_rows = self._visible_rows(active[i + 1])
        row_h = max(row_h, len(right_rows) * active[i + 1].row_height)
        i += 2
        total += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP
        total += row_h
        total += SECTION_GAP
      else:
        i += 1
        total += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP if section.title else 0.0
        total += row_h
        total += SECTION_GAP
    return max(0.0, total - SECTION_GAP) if total > 0 else 0.0

  def _draw_tabs(self, y: float, x: float, width: float) -> float:
    return draw_tab_bar(
      rl.Rectangle(x, y, width, self.TAB_HEIGHT),
      self._tab_defs, self._active_tab_key, self._interactive_state,
      style=self._panel_style,
    )

  def _uses_two_columns(self, width: float) -> bool:
    return width >= self.TWO_COLUMN_BREAKPOINT

  def _has_subsequent_visible(self, start_idx: int, sections: list[SettingSection]) -> bool:
    for j in range(start_idx, len(sections)):
      if self._visible_rows(sections[j]):
        return True
    return False

  def _draw_scroll_content(self, rect: rl.Rectangle, width: float):
    y = rect.y + self._scroll_offset
    if self._tab_defs:
      y = self._draw_tabs(y, rect.x, width)
    active = self._active_sections()
    has_visible = any(self._visible_rows(s) for s in active)
    if not has_visible:
      draw_empty_state_card(
        rl.Rectangle(rect.x, y, width, rect.height - (y - rect.y)),
        tr("No settings to display"),
        tr("All options in this panel are hidden or unavailable."),
        style=self._panel_style,
      )
      return
    i = 0
    while i < len(active):
      section = active[i]
      visible_rows = self._visible_rows(section)
      if not visible_rows:
        i += 1
        continue
      if section.column_pair and i + 1 < len(active) and active[i + 1].column_pair == section.column_pair and self._uses_two_columns(width):
        right_section = active[i + 1]
        right_rows = self._visible_rows(right_section)
        col_w = (width - self.COLUMN_GAP) / 2
        section_h = len(visible_rows) * section.row_height
        right_h = len(right_rows) * right_section.row_height
        group_h = max(section_h, right_h)

        draw_section_header(
          rl.Rectangle(rect.x, y, col_w, SECTION_HEADER_HEIGHT),
          tr(section.title), style=self._panel_style,
        )
        draw_section_header(
          rl.Rectangle(rect.x + col_w + self.COLUMN_GAP, y, col_w, SECTION_HEADER_HEIGHT),
          tr(right_section.title), style=self._panel_style,
        )
        y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP

        left_group = rl.Rectangle(rect.x, y, col_w, section_h)
        right_group = rl.Rectangle(rect.x + col_w + self.COLUMN_GAP, y, col_w, right_h)
        draw_list_group_shell(left_group, style=self._panel_style)
        draw_list_group_shell(right_group, style=self._panel_style)

        for j, row in enumerate(visible_rows):
          self._draw_row(rl.Rectangle(rect.x, y + j * section.row_height, col_w, section.row_height), row, is_last=(j == len(visible_rows) - 1))
        for j, row in enumerate(right_rows):
          self._draw_row(rl.Rectangle(rect.x + col_w + self.COLUMN_GAP, y + j * right_section.row_height, col_w, right_section.row_height), row, is_last=(j == len(right_rows) - 1))

        y += group_h
        if self._has_subsequent_visible(i + 2, active):
          y += SECTION_GAP
        i += 2
      else:
        y = self._draw_section(y, rect.x, width, section, visible_rows)
        if self._has_subsequent_visible(i + 1, active):
          y += SECTION_GAP
        i += 1

  def _draw_section(self, y: float, x: float, width: float,
                    section: SettingSection, rows: list[SettingRow]) -> float:
    if section.title:
      draw_section_header(
        rl.Rectangle(x, y, width, SECTION_HEADER_HEIGHT),
        tr(section.title),
        style=self._panel_style,
      )
      y += SECTION_HEADER_HEIGHT + SECTION_HEADER_GAP

    group_rect = rl.Rectangle(x, y, width, len(rows) * section.row_height)
    draw_list_group_shell(group_rect, style=self._panel_style)

    for i, row in enumerate(rows):
      row_rect = rl.Rectangle(x, y + i * section.row_height, width, section.row_height)
      self._draw_row(row_rect, row, is_last=(i == len(rows) - 1))

    return y + group_rect.height

  def _draw_row(self, rect: rl.Rectangle, row: SettingRow, is_last: bool):
    target_id = f"{row.type}:{row.id}"
    hovered, pressed = self._interactive_state(target_id, rect)

    enabled = row.enabled() if row.enabled is not None else True
    subtitle = row.disabled_label if not enabled and row.disabled_label else row.subtitle

    if row.type == "toggle":
      toggle_value = row.get_state() if row.get_state else False
      draw_standard_toggle_row(
        rect, tr(row.title), tr(subtitle), toggle_value,
        enabled=enabled, hovered=hovered, pressed=pressed,
        is_last=is_last, style=self._panel_style,
      )
    elif row.type == "value":
      value_text = row.get_value() if row.get_value else ""
      draw_settings_list_row(
        rect,
        title=tr(row.title),
        subtitle=tr(subtitle),
        value=value_text,
        enabled=enabled,
        hovered=hovered,
        pressed=pressed,
        is_last=is_last,
        show_chevron=row.on_click is not None,
        title_size=34, subtitle_size=22, value_size=28,
        style=self._panel_style,
      )
    elif row.type == "action":
      action_fill = self._panel_style.danger_fill if row.action_danger else self._panel_style.current_fill
      action_border = self._panel_style.danger_border if row.action_danger else self._panel_style.current_border
      action_text_color = self._panel_style.danger_text if row.action_danger else AetherListColors.HEADER
      draw_selection_list_row(
        rect,
        title=tr(row.title),
        subtitle=tr(subtitle),
        action_text=tr(row.action_text),
        hovered=hovered,
        pressed=pressed,
        is_last=is_last,
        action_pill=True,
        title_size=34, subtitle_size=22,
        action_pill_height=44, action_text_size=18,
        action_text_color=action_text_color,
        action_fill=action_fill,
        action_border=action_border,
        row_separator=self._panel_style.divider_color,
      )


class AetherTile(Widget):
  def __init__(self, surface_color: rl.Color | str | None = None, substrate_color: rl.Color | str | None = None, on_click: Callable | None = None):
    super().__init__()
    if isinstance(surface_color, str):
      self.surface_color = hex_to_color(surface_color)
    elif surface_color:
      self.surface_color = surface_color
    else:
      self.surface_color = AetherListColors.PRIMARY
    if isinstance(substrate_color, str):
      self.substrate_color = hex_to_color(substrate_color)
    else:
      self.substrate_color = substrate_color or _default_substrate_for(self.surface_color)
    self.on_click = on_click
    self._plate_offset: float = 0.0
    self._plate_target: float = 0.0
    self._is_pressed: bool = False

  def _surface_rect(self, rect: rl.Rectangle) -> rl.Rectangle:
    return _inset_rect(_snap_rect(rect), TILE_INSET)

  @property
  def _hit_rect(self) -> rl.Rectangle:
    hit_rect = rl.Rectangle(
      self._rect.x - GEOMETRY_OFFSET,
      self._rect.y - GEOMETRY_OFFSET,
      self._rect.width + 2 * GEOMETRY_OFFSET,
      self._rect.height + 2 * GEOMETRY_OFFSET,
    )
    parent_rect = getattr(self, "_parent_rect", None)
    if parent_rect is not None:
      return _intersect_rect(hit_rect, parent_rect)
    return hit_rect

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if not self.enabled:
      return
    if rl.check_collision_point_rec(mouse_pos, self._hit_rect):
      self._is_pressed = True
      self._plate_target = 1.0

  def _handle_mouse_release(self, mouse_pos: MousePos):
    if not self.enabled:
      self._is_pressed = False
      self._plate_target = 0.0
      return
    if self._is_pressed:
      if rl.check_collision_point_rec(mouse_pos, self._hit_rect):
        self._plate_target = 0.0
        if self.on_click:
          self.on_click()
      else:
        self._plate_target = 0.0
      self._is_pressed = False

  def _handle_mouse_event(self, mouse_event):
    if not rl.check_collision_point_rec(mouse_event.pos, self._hit_rect):
      self._plate_target = 0.0

  def _animate_plate(self, dt: float):
    if self._plate_offset == self._plate_target:
      return
    self._plate_offset += (self._plate_target - self._plate_offset) * (1 - math.exp(-dt / PLATE_TAU))

  def _render_layers(self, rect: rl.Rectangle, radius: float = TILE_RADIUS, segments: int = TILE_SEGMENTS):
    self._animate_plate(rl.get_frame_time())
    snapped_rect = _snap_rect(rect)
    self.set_rect(snapped_rect)

    surface_rect = self._surface_rect(snapped_rect)
    base_color = _mix_colors(self.substrate_color, self.surface_color, 0.10)
    surface_color = _mix_colors(AetherListColors.PANEL_BG, self.surface_color, 0.16 if self.enabled else 0.08)
    if self._is_pressed:
      surface_color = _tone_step(surface_color, -8)
    border_color = _mix_colors(AetherListColors.PANEL_BORDER, self.surface_color, 0.38, alpha=84 if self.enabled else 42)

    _draw_rounded_fill(snapped_rect, base_color)
    _draw_rounded_fill(surface_rect, surface_color)
    _draw_rounded_stroke(surface_rect, border_color)
    rl.draw_rectangle_rec(rl.Rectangle(surface_rect.x, surface_rect.y + surface_rect.height - 1, surface_rect.width, 1), _with_alpha(border_color, 48))

    return surface_rect

  def _draw_text_fit(
    self,
    font: rl.Font,
    text: str,
    pos: rl.Vector2,
    max_width: float,
    font_size: float,
    align_center: bool = False,
    align_right: bool = False,
    letter_spacing: float = 0,
    uppercase: bool = False,
    color: rl.Color = rl.WHITE,
    shadow_alpha: int = 0,
  ):
    _draw_text_fit_common(
      font,
      text,
      pos,
      max_width,
      font_size,
      align_center=align_center,
      align_right=align_right,
      letter_spacing=letter_spacing,
      uppercase=uppercase,
      color=color,
      shadow_alpha=shadow_alpha,
    )

  def _centered_content(
    self, face: rl.Rectangle, icon: rl.Texture2D | None, icon_scale: float, title_font_size: float, text_lines: int, line_heights: list[float]
  ):
    line_spacing = SPACING.line_gap
    total_h = sum(line_heights) + line_spacing * (text_lines - 1)
    icon_w = icon.width * icon_scale if icon else 0
    icon_h = icon.height * icon_scale if icon else 0
    if icon:
      total_h += icon_h + line_spacing
    group_top = face.y + (face.height - total_h) / 2
    if icon:
      ix = face.x + (face.width - icon_w) / 2
      rl.draw_texture_pro(icon, rl.Rectangle(0, 0, icon.width, icon.height), rl.Rectangle(ix, group_top, icon_w, icon_h), rl.Vector2(0, 0), 0, rl.WHITE)
      ty = group_top + icon_h + line_spacing
    else:
      ty = group_top
    return face, ty

  def _wrap_text(self, font: rl.Font, text: str, max_width: float, font_size: float, max_lines: int = 2) -> list[str]:
    spacing = font_size * 0.15
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
      candidate = f"{current} {word}".strip() if current else word
      if measure_text_cached(font, candidate, int(font_size), spacing=spacing).x <= max_width:
        current = candidate
      else:
        if current:
          lines.append(current)
        current = word
        if len(lines) >= max_lines:
          break
    if current and len(lines) < max_lines:
      lines.append(current)
    return lines if lines else [text]

  def _draw_signal_edge(self, face: rl.Rectangle, color: rl.Color, width: int = 2, alpha: int = 58):
    snapped_face = _snap_rect(face)
    signal_width = max(1, int(width))
    glow_color = _with_alpha(color, max(4, alpha // 3))
    core_color = _with_alpha(color, alpha)
    rl.draw_rectangle_rec(rl.Rectangle(snapped_face.x, snapped_face.y, signal_width, snapped_face.height), glow_color)
    inner_x = snapped_face.x + max(1, signal_width - 2)
    inner_w = max(1, signal_width - 1)
    rl.draw_rectangle_rec(rl.Rectangle(inner_x, snapped_face.y, inner_w, snapped_face.height), core_color)

  def _measure_tile_stack(
    self,
    face: rl.Rectangle,
    *,
    icon_height: float,
    title_lines: int,
    title_size: int,
    primary_size: int,
    desc_lines: int,
    desc_size: int,
  ) -> dict[str, float]:
    title_block = title_lines * title_size + max(0, title_lines - 1) * SPACING.line_gap
    icon_gap = SPACING.line_gap if icon_height > 0 else 0
    primary_gap = SPACING.line_gap if title_block > 0 else 0
    desc_gap = SPACING.sm if desc_lines > 0 else 0
    desc_block = desc_lines * desc_size + max(0, desc_lines - 1) * SPACING.xs
    total_height = icon_height + icon_gap + title_block + primary_gap + primary_size + desc_gap + desc_block
    available_height = face.height
    if total_height > available_height:
      overflow = total_height - available_height
      reduce_icon = min(icon_height * 0.35, overflow)
      icon_height -= reduce_icon
      total_height -= reduce_icon
      if total_height > available_height and desc_block > 0:
        reduce_desc = min(desc_block * 0.5, total_height - available_height)
        desc_block -= reduce_desc
        total_height -= reduce_desc
      if total_height > available_height:
        title_block = max(title_size, title_block - (total_height - available_height))
        total_height = icon_height + icon_gap + title_block + primary_gap + primary_size + desc_gap + desc_block
    top = max(face.y, face.y + (available_height - total_height) / 2)
    title_y = top + icon_height + icon_gap
    primary_y = title_y + title_block + primary_gap
    desc_y = primary_y + primary_size + desc_gap
    return {
      "top": top,
      "title_y": title_y,
      "primary_y": primary_y,
      "desc_y": desc_y,
      "desc_bottom": desc_y + desc_block,
    }

  def _draw_custom_icon(self, key: str, x: float, y: float, s: float, color: rl.Color):
    draw_custom_icon(key, x, y, s, color)

  def _render_tile_stack(
    self,
    face: rl.Rectangle,
    *,
    icon: rl.Texture2D | None = None,
    title: str,
    primary: str,
    desc: str,
    title_font: rl.Font,
    primary_font: rl.Font,
    desc_font: rl.Font,
    title_size: int,
    primary_size: int,
    desc_size: int = 18,
    custom_icon_key: str | None = None,
  ):
    # Parameters for custom vector icons: base 100x100 layout footprint,
    # 25% scale increase, and 60x60 canvas size defined in scribble.py coordinates.
    custom_icon_base_size = 100.0
    custom_icon_scale_mult = 1.25
    custom_icon_canvas_size = 60.0

    content_pad = SPACING.tile_content
    max_w = face.width - (content_pad * 2)
    scale = max(0.82, min(1.12, min(face.width / 360.0, face.height / 205.0)))
    title_size = max(22, int(round(title_size * scale)))
    primary_size = max(18, int(round(primary_size * scale)))
    desc_size = max(14, int(round(desc_size * scale)))
    title_lines = self._wrap_text(title_font, title, max_w, title_size, max_lines=2)
    has_icon = (icon is not None) or (custom_icon_key is not None)
    icon_scale = min(0.80, max(0.56, scale * 0.72)) if has_icon else 0.0
    if custom_icon_key:
      icon_height = custom_icon_base_size * custom_icon_scale_mult * icon_scale
    elif icon:
      icon_height = icon.height * icon_scale
    else:
      icon_height = 0.0
    desc_lines = self._wrap_text(desc_font, desc, max_w, desc_size, max_lines=3) if desc else []
    layout = self._measure_tile_stack(
      face,
      icon_height=icon_height,
      title_lines=len(title_lines),
      title_size=title_size,
      primary_size=primary_size,
      desc_lines=len(desc_lines),
      desc_size=desc_size,
    )

    if custom_icon_key:
      icon_width = custom_icon_base_size * custom_icon_scale_mult * icon_scale
      icon_x = face.x + (face.width - icon_width) / 2
      s = icon_scale * (custom_icon_base_size / custom_icon_canvas_size) * custom_icon_scale_mult
      self._draw_custom_icon(custom_icon_key, icon_x, layout["top"], s, _mix_colors(rl.Color(255, 255, 255, 255), self.surface_color, 0.08))
    elif icon:
      icon_width = icon.width * icon_scale
      icon_x = face.x + (face.width - icon_width) / 2
      rl.draw_texture_pro(
        icon,
        rl.Rectangle(0, 0, icon.width, icon.height),
        rl.Rectangle(icon_x, layout["top"], icon_width, icon_height),
        rl.Vector2(0, 0),
        0,
        rl.WHITE,
      )

    for i, line in enumerate(title_lines):
      self._draw_text_fit(
        title_font,
        line,
        rl.Vector2(face.x + content_pad, layout["title_y"] + i * (title_size + SPACING.line_gap)),
        max_w,
        title_size,
        align_center=True,
        color=AetherListColors.HEADER,
      )

    self._draw_text_fit(
      primary_font,
      primary,
      rl.Vector2(face.x + content_pad, layout["primary_y"]),
      max_w,
      primary_size,
      align_center=True,
      color=AetherListColors.SUBTEXT if desc else AetherListColors.HEADER,
    )

    if desc_lines:
      for i, line in enumerate(desc_lines):
        self._draw_text_fit(
          desc_font,
          line,
          rl.Vector2(face.x + content_pad, layout["desc_y"] + i * (desc_size + SPACING.xs)),
          max_w,
          desc_size,
          align_center=True,
          color=AetherListColors.MUTED,
        )

    return layout

  def _render_hud_background(self, rect: rl.Rectangle, accent: rl.Color, glow: float = 1.0) -> tuple[rl.Rectangle, rl.Color]:
    sq = getattr(self, '_squish', 1.0)
    snapped = _snap_rect(rect)
    sw = snapped.width * sq
    sh = snapped.height * sq
    ox = snapped.x + (snapped.width - sw) / 2
    oy = snapped.y + (snapped.height - sh) / 2
    rx, ry, rw, rh = int(ox), int(oy), int(sw), int(sh)
    face = rl.Rectangle(rx, ry, rw, rh)

    off_border = _HUD_BORDER_OFF

    for i in range(4, 0, -1):
      off = i * 2.5 * glow
      gr = rl.Rectangle(rx - off, ry - off, rw + off * 2, rh + off * 2)
      a = int(25 * (1.0 - i / 5) * glow)
      _draw_rounded_fill(gr, rl.Color(accent.r, accent.g, accent.b, max(0, min(255, a))), radius_px=100)

    _draw_rounded_fill(face, _HUD_BG_ON, radius_px=100)

    bc = rl.Color(
      max(0, min(255, int(off_border.r + (accent.r - off_border.r) * glow))),
      max(0, min(255, int(off_border.g + (accent.g - off_border.g) * glow))),
      max(0, min(255, int(off_border.b + (accent.b - off_border.b) * glow))),
      255)
    _draw_rounded_stroke(face, bc, radius_px=100)

    led_w, led_h = 32, 2
    led_x = rx + (rw - led_w) // 2
    led_y = ry + 12
    led_base = _HUD_LED_BASE
    led_col = rl.Color(
      max(0, min(255, int(led_base.r + (accent.r - led_base.r) * glow))),
      max(0, min(255, int(led_base.g + (accent.g - led_base.g) * glow))),
      max(0, min(255, int(led_base.b + (accent.b - led_base.b) * glow))),
      255)
    rl.draw_rectangle(led_x, led_y, led_w, led_h, led_col)

    return face, accent

  def _render(self, rect: rl.Rectangle):
    pass


class HubTile(AetherTile):
  def __init__(
    self,
    title: str | Callable[[], str],
    desc: str | Callable[[], str],
    icon_key: str | None = None,
    on_click: Callable | None = None,
    bg_color: rl.Color | str | None = None,
    get_status: Callable[[], str] | None = None,
  ):
    if bg_color:
      super().__init__(surface_color=bg_color, on_click=on_click)
    else:
      super().__init__(on_click=on_click)
    self.get_status = get_status
    self.title = title
    self.desc = desc
    self.custom_icon_key = icon_key if icon_key in ("sound", "steering", "navigate", "system", "display", "vehicle") else None
    self._icon = None
    self._font_title = gui_app.font(FontWeight.BOLD)
    self._font_desc = gui_app.font(FontWeight.NORMAL)
    self._squish: float = 1.0

  def _update_state(self):
    dt = rl.get_frame_time()
    if self._squish < 1.0:
      self._squish += (1.0 - self._squish) * 15.0 * dt

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if not self.enabled:
      return
    if rl.check_collision_point_rec(mouse_pos, self._hit_rect):
      self._is_pressed = True
      self._plate_target = 1.0
      self._squish = 0.95

  def _render(self, rect: rl.Rectangle):
    self._animate_plate(rl.get_frame_time())

    status_text = self.get_status() if self.get_status else ""
    title_text = str(_resolve_value(self.title, ""))
    fallback_desc = str(_resolve_value(self.desc, ""))

    face, accent = self._render_hud_background(rect, self.surface_color)
    rx, ry, rw, rh = face.x, face.y, face.width, face.height
    content_pad = SPACING.tile_content
    max_w = rw - content_pad * 2
    text_scale = min(rw / 360.0, rh / 205.0)
    gap = SPACING.line_gap

    title_size = max(18, int(round(22 * text_scale)))
    desc_to_render = status_text if status_text else fallback_desc
    desc_size = max(12, int(round(14 * text_scale))) if desc_to_render else 0

    icon_h = 0.0
    if self.custom_icon_key:
      icon_base_size = 100.0
      icon_scale_mult = 1.25
      icon_canvas_size = 60.0
      icon_scale = min(0.80, max(0.56, text_scale * 0.72))
      icon_h = icon_base_size * icon_scale_mult * icon_scale

    total_h = icon_h + (gap if icon_h > 0 else 0) + title_size + (gap if desc_to_render else 0) + desc_size
    content_top = ry + max(0, (rh - total_h) / 2)

    if self.custom_icon_key:
      icon_base_size = 100.0
      icon_scale_mult = 1.25
      icon_canvas_size = 60.0
      icon_scale = min(0.80, max(0.56, text_scale * 0.72))
      icon_width = icon_base_size * icon_scale_mult * icon_scale
      icon_x = rx + (rw - icon_width) / 2
      s = icon_scale * (icon_base_size / icon_canvas_size) * icon_scale_mult
      self._draw_custom_icon(self.custom_icon_key, icon_x, content_top, s, _mix_colors(rl.Color(255, 255, 255, 255), accent, 0.08))
      content_top += icon_h + gap

    self._draw_text_fit(self._font_title, title_text,
                        rl.Vector2(rx + content_pad, content_top),
                        max_w, title_size, align_center=True, color=rl.WHITE)
    content_top += title_size

    if desc_to_render:
      content_top += gap
      self._draw_text_fit(self._font_desc, desc_to_render,
                          rl.Vector2(rx + content_pad, content_top),
                          max_w, desc_size, align_center=True, color=_HUD_TEXT_DIM)

    if status_text:
      import re
      m = re.search(r'(\d+)%$', status_text)
      if m:
        ratio = min(1.0, max(0.0, float(m.group(1)) / 100.0))
        if ratio > 0.05:
          meter_h = 6
          meter_rect = rl.Rectangle(rx + content_pad, ry + rh - content_pad - meter_h, rw - content_pad * 2, meter_h)
          fill_rect = rl.Rectangle(meter_rect.x, meter_rect.y, meter_rect.width * ratio, meter_h)
          rl.draw_rectangle_rec(_snap_rect(meter_rect), rl.Color(255, 255, 255, 14))
          rl.draw_rectangle_rec(_snap_rect(fill_rect), _with_alpha(accent, 170))


class AetherSelectionTile(AetherTile):
  def __init__(
    self,
    title: str | Callable[[], str],
    status: str | Callable[[], str] = "",
    on_click: Callable | None = None,
    bg_color: rl.Color | str | None = None,
  ):
    super().__init__(surface_color=bg_color, on_click=on_click)
    self.title = title
    self.status = status
    self._font_title = gui_app.font(FontWeight.BOLD)
    self._font_status = gui_app.font(FontWeight.NORMAL)

  def _render(self, rect: rl.Rectangle):
    face = self._render_layers(rect)
    title_text = str(_resolve_value(self.title, ""))
    status_text = str(_resolve_value(self.status, ""))
    content_pad = max(16, min(22, int(face.width * 0.06)))
    max_w = max(1.0, face.width - content_pad * 2)
    title_size = max(22, min(28, int(face.height * 0.28)))
    status_size = max(15, min(18, int(face.height * 0.20)))
    title_lines = self._wrap_text(self._font_title, title_text, max_w, title_size, max_lines=2)
    title_y = face.y + max(14.0, min(20.0, face.height * 0.18))

    for i, line in enumerate(title_lines):
      self._draw_text_fit(
        self._font_title,
        line,
        rl.Vector2(face.x + content_pad, title_y + i * (title_size + SPACING.xs)),
        max_w,
        title_size,
        color=AetherListColors.HEADER,
      )

    if status_text:
      status_y = face.y + face.height - status_size - max(12.0, min(16.0, face.height * 0.16))
      self._draw_text_fit(
        self._font_status,
        status_text,
        rl.Vector2(face.x + content_pad, status_y),
        max_w,
        status_size,
        color=AetherListColors.SUBTEXT,
      )


class ToggleTile(AetherTile):
  def __init__(
    self,
    title: str,
    get_state: Callable[[], bool],
    set_state: Callable[[bool], None],
    bg_color: rl.Color | str | None = None,
    desc: str = "",
    is_enabled: Callable[[], bool] | None = None,
    disabled_label: str = "",
    show_led: bool = True,
  ):
    if bg_color:
      super().__init__(surface_color=bg_color)
    else:
      super().__init__(surface_color=AetherListColors.SUCCESS)
    self.title = title
    self.desc = desc
    self.get_state = get_state
    self.set_state = set_state
    self.set_enabled(is_enabled or True)
    self._font = gui_app.font(FontWeight.BOLD)
    self._font_desc = gui_app.font(FontWeight.NORMAL)
    self._active_color = self.surface_color
    self._inactive_color = rl.Color(120, 120, 120, 255)
    self._disabled_color = rl.Color(75, 75, 75, 255)
    self._disabled_label = disabled_label
    self._show_led = show_led
    self._glow: float = 1.0 if (self.get_state() and (is_enabled or True)) else 0.0
    self._squish: float = 1.0

  def _update_state(self):
    dt = rl.get_frame_time()
    target = 1.0 if self.get_state() and self.enabled else 0.0
    self._glow += (target - self._glow) * 10.0 * dt
    if self._squish < 1.0:
      self._squish += (1.0 - self._squish) * 15.0 * dt

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if not self.enabled:
      return
    if rl.check_collision_point_rec(mouse_pos, self._hit_rect):
      self._is_pressed = True
      self._plate_target = 1.0
      self._squish = 0.95

  def _handle_mouse_release(self, mouse_pos: MousePos):
    if self._is_pressed:
      if rl.check_collision_point_rec(mouse_pos, self._hit_rect) and self.enabled:
        self.set_state(not self.get_state())
      self._plate_target = 0.0
      self._is_pressed = False

  def _render(self, rect: rl.Rectangle):
    enabled = self.enabled
    active = self.get_state()
    self._animate_plate(rl.get_frame_time())

    if not enabled:
      self._plate_offset = 0.0
      self._plate_target = 0.0

    if not self._show_led:
      self.surface_color = self._disabled_color if not enabled else (self._active_color if active else self._inactive_color)
      state_text = tr(self._disabled_label) if not enabled and self._disabled_label else (tr("LOCKED") if not enabled else (tr("ON") if active else tr("OFF")))
      signal_color = self._active_color if (enabled and active) else self.surface_color
      alpha = 62 if (enabled and active) else 28

      face = self._render_layers(rect)
      self._draw_signal_edge(face, signal_color, width=TILE_SIGNAL_WIDTH, alpha=alpha)
      self._render_tile_stack(face, title=self.title, primary=state_text, desc=self.desc,
                              title_font=self._font, primary_font=self._font, desc_font=self._font_desc,
                              title_size=28, primary_size=30)
      return

    # --- HUD toggle path (show_led) ---
    color = self._active_color if enabled else self._disabled_color
    glow = self._glow if enabled else 0.0
    face, accent = self._render_hud_background(rect, color, glow)
    rx, ry, rw, rh = face.x, face.y, face.width, face.height

    content_pad = SPACING.tile_content
    max_w = rw - content_pad * 2
    text_scale = min(rw / 360.0, rh / 205.0)
    title_size = max(18, int(round(22 * text_scale)))

    if not enabled:
      self._draw_text_fit(self._font, self.title,
                          rl.Vector2(rx + content_pad, ry + int(rh * 0.40)),
                          max_w, title_size, align_center=True, color=_HUD_TEXT_DIM)
      disabled_text = tr(self._disabled_label) if self._disabled_label else tr("LOCKED")
      desc_size = max(14, int(round(16 * text_scale)))
      self._draw_text_fit(self._font_desc, disabled_text,
                          rl.Vector2(rx + content_pad, ry + int(rh * 0.68)),
                          max_w, desc_size, align_center=True, color=_HUD_TEXT_DIM)
    else:
      title_color = rl.WHITE if active else _HUD_TEXT_DIM
      self._draw_text_fit(self._font, self.title,
                          rl.Vector2(rx + content_pad, ry + int(rh * 0.50)),
                          max_w, title_size, align_center=True, color=title_color)
      led_cx = rx + rw // 2
      led_cy = ry + int(rh * 0.75)
      if active:
        rl.draw_circle(int(led_cx), int(led_cy), 11, rl.Color(accent.r, accent.g, accent.b, 24))
        rl.draw_circle(int(led_cx), int(led_cy), 6, accent)
      else:
        rl.draw_circle(int(led_cx), int(led_cy), 7, rl.Color(14, 16, 22, 255))
        rl.draw_ring(rl.Vector2(led_cx, led_cy), 5, 6, 0, 360, 24, rl.Color(70, 78, 95, 140))


class ValueTile(AetherTile):
  def __init__(
    self,
    title: str,
    get_value: Callable[[], str],
    on_click: Callable,
    bg_color: rl.Color | str | None = None,
    is_enabled: Callable[[], bool] | None = None,
    desc: str = "",
  ):
    super().__init__(surface_color=bg_color, on_click=on_click)
    self.title = title
    self.desc = desc
    self.get_value = get_value
    self.set_enabled(is_enabled or (lambda: True))
    self._font = gui_app.font(FontWeight.BOLD)
    self._font_desc = gui_app.font(FontWeight.NORMAL)
    self._active_color = self.surface_color
    self._disabled_color = rl.Color(120, 120, 120, 255)
    self._squish: float = 1.0

  def _update_state(self):
    dt = rl.get_frame_time()
    if self._squish < 1.0:
      self._squish += (1.0 - self._squish) * 15.0 * dt

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if not self.enabled:
      return
    if rl.check_collision_point_rec(mouse_pos, self._hit_rect):
      self._is_pressed = True
      self._plate_target = 1.0
      self._squish = 0.95

  def _render(self, rect: rl.Rectangle):
    enabled = self.enabled
    self._animate_plate(rl.get_frame_time())

    if not enabled:
      self._plate_offset = 0.0
      self._plate_target = 0.0

    color = self._active_color if enabled else self._disabled_color
    glow = 1.0 if enabled else 0.0
    face, accent = self._render_hud_background(rect, color, glow)
    rx, ry, rw, rh = face.x, face.y, face.width, face.height

    content_pad = SPACING.tile_content
    max_w = rw - content_pad * 2
    text_scale = min(rw / 360.0, rh / 205.0)

    # Title
    title_size = max(18, int(round(22 * text_scale)))
    self._draw_text_fit(self._font, self.title,
                        rl.Vector2(rx + content_pad, ry + int(rh * 0.35)),
                        max_w, title_size, align_center=True, color=_HUD_TEXT_DIM)

    # Value
    val_text = self.get_value()
    val_size = max(18, int(round(24 * text_scale)))
    val_color = accent if enabled else _HUD_TEXT_DIM
    self._draw_text_fit(self._font, val_text,
                        rl.Vector2(rx + content_pad, ry + int(rh * 0.58)),
                        max_w, val_size, align_center=True, color=val_color)


class SliderTile(AetherTile):
    LONG_PRESS_THRESHOLD = 0.5
    DRAG_THRESHOLD = 10

    def __init__(
        self,
        title: str,
        get_value: Callable[[], float],
        set_value: Callable[[float], None],
        min_val: float,
        max_val: float,
        step: float,
        bg_color: rl.Color | str | None = None,
        is_enabled: Callable[[], bool] | None = None,
        desc: str = "",
        unit: str = "",
        labels: dict[float, str] | None = None,
        on_test: Callable[[], None] | None = None,
    ):
        super().__init__(surface_color=bg_color)
        self.title = title
        self.desc = desc
        self.get_value = get_value
        self.set_value = set_value
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.unit = unit
        self.labels = labels or {}
        self.on_test = on_test
        self.set_enabled(is_enabled or (lambda: True))
        self._font = gui_app.font(FontWeight.BOLD)
        self._font_desc = gui_app.font(FontWeight.NORMAL)
        self._active_color = self.surface_color
        self._disabled_color = rl.Color(120, 120, 120, 255)

        self._is_dragging = False
        self._last_mouse_x = 0.0
        self._velocity = 0.0
        self._smooth_value = get_value()
        self._press_start_x = 0.0
        self._press_start_time: float | None = None
        self._long_press_triggered = False
        self._squish: float = 1.0

    def _update_state(self):
        dt = rl.get_frame_time()
        if self._squish < 1.0:
            self._squish += (1.0 - self._squish) * 15.0 * dt

    def _handle_mouse_press(self, mouse_pos: MousePos):
        if rl.check_collision_point_rec(mouse_pos, self._hit_rect) and self.enabled:
            self._is_pressed = True
            self._squish = 0.95
            self._last_mouse_x = mouse_pos.x
            self._velocity = 0.0
            self._press_start_x = mouse_pos.x
            self._press_start_time = time.monotonic()
            self._long_press_triggered = False

    def _handle_mouse_release(self, mouse_pos: MousePos):
        self._is_dragging = False
        self._is_pressed = False
        self._press_start_time = None

    def _handle_mouse_event(self, mouse_event):
        if not rl.check_collision_point_rec(mouse_event.pos, self._hit_rect):
            if not self._is_dragging and not self._press_start_time:
                self._plate_target = 0.0

        if self._press_start_time and not self._is_dragging and not self._long_press_triggered:
            dx = abs(mouse_event.pos.x - self._press_start_x)
            if dx > self.DRAG_THRESHOLD:
                self._is_dragging = True
                self._press_start_time = None
            else:
                elapsed = time.monotonic() - self._press_start_time
                if elapsed >= self.LONG_PRESS_THRESHOLD:
                    self._long_press_triggered = True
                    self._press_start_time = None
                    if self.on_test:
                        self.on_test()

        if self._is_dragging:
            dt = rl.get_frame_time()
            current_val = self.get_value()
            mouse_pos = mouse_event.pos
            dx = mouse_pos.x - self._last_mouse_x
            self._velocity = dx / max(dt, 0.001)
            self._last_mouse_x = mouse_pos.x

            rect_w = self._rect.width
            if rect_w > 0:
                val_range = self.max_val - self.min_val
                val_dx = (dx / rect_w) * val_range
                new_val = current_val + val_dx

                abs_vel = abs(self._velocity)
                snap_threshold = 800
                coarse_step = 10 if val_range >= 100 else self.step * 5
                dynamic_step = coarse_step if abs_vel > snap_threshold else self.step

                snapped = round(new_val / dynamic_step) * dynamic_step
                snapped = max(self.min_val, min(self.max_val, snapped))

                if abs(snapped - current_val) >= self.step:
                    self.set_value(float(snapped))

    def _render(self, rect: rl.Rectangle):
        enabled = self.enabled
        current_val = self.get_value()
        dt = rl.get_frame_time()

        self._smooth_value += (current_val - self._smooth_value) * (1 - math.exp(-dt / 0.1))
        self._animate_plate(dt)

        if not enabled:
            self._plate_offset = 0.0
            self._plate_target = 0.0

        color = self._active_color if enabled else self._disabled_color
        glow = 1.0 if enabled else 0.0
        face, accent = self._render_hud_background(rect, color, glow)
        rx, ry, rw, rh = face.x, face.y, face.width, face.height

        content_pad = SPACING.tile_content
        max_w = rw - content_pad * 2
        text_scale = min(rw / 360.0, rh / 205.0)

        # Title
        title_size = max(18, int(round(22 * text_scale)))
        self._draw_text_fit(self._font, self.title,
                            rl.Vector2(rx + content_pad, ry + int(rh * 0.30)),
                            max_w, title_size, align_center=True, color=_HUD_TEXT_DIM)

        # Value text
        val_str = self.labels.get(current_val, f"{int(current_val)}{self.unit}")
        val_size = max(18, int(round(24 * text_scale)))
        val_color = accent if enabled else _HUD_TEXT_DIM
        self._draw_text_fit(self._font, val_str,
                            rl.Vector2(rx + content_pad, ry + int(rh * 0.52)),
                            max_w, val_size, align_center=True, color=val_color)

        # Slider meter
        value_range = self.max_val - self.min_val
        frac = 0.0 if value_range == 0 else max(0.0, min(1.0, (self._smooth_value - self.min_val) / value_range))
        meter_h = 6
        meter_rect = rl.Rectangle(rx + content_pad, ry + rh - content_pad - meter_h, rw - content_pad * 2, meter_h)
        fill_w = meter_rect.width * frac
        rl.draw_rectangle_rec(_snap_rect(meter_rect), rl.Color(255, 255, 255, 14))
        if fill_w > 1:
            fill_rect = rl.Rectangle(meter_rect.x, meter_rect.y, fill_w, meter_rect.height)
            fill_color = _with_alpha(accent, 176) if enabled else rl.Color(120, 120, 120, 100)
            rl.draw_rectangle_rec(_snap_rect(fill_rect), fill_color)


class AetherSlider(Widget):
  def __init__(
    self,
    min_val: float,
    max_val: float,
    step: float,
    current_val: float,
    on_change: Callable[[float], None],
    unit: str = "",
    labels: dict[float, str] | None = None,
    color: rl.Color = rl.Color(54, 77, 239, 255),
    on_commit: Callable[[float], None] | None = None,
    show_value_label: bool = True,
  ):
    super().__init__()
    self.min_val, self.max_val, self.step, self.current_val = min_val, max_val, step, current_val
    self.on_change, self.on_commit = on_change, on_commit
    self.unit, self.labels, self.color = unit, labels or {}, color
    self.show_value_label = show_value_label
    self._is_dragging = False
    self._font = gui_app.font(FontWeight.BOLD)
    self._thumb_offset: float = 0.0
    self._minus_offset: float = 0.0
    self._plus_offset: float = 0.0
    self._minus_pressed = False
    self._plus_pressed = False
    self._pending_drag = False
    self._press_start = rl.Vector2(0, 0)
    self._started_on_thumb = False
    self._value_at_press = current_val

  @property
  def is_interacting(self) -> bool:
    return self._is_dragging or self._pending_drag or self._minus_pressed or self._plus_pressed

  def set_value(self, value: float) -> None:
    self.current_val = self._clamp_and_snap(value)

  def reset_interaction(self) -> None:
    self._is_dragging = False
    self._pending_drag = False
    self._started_on_thumb = False
    self._thumb_offset = 0.0
    self._minus_pressed = False
    self._plus_pressed = False

  def _cancel_interaction(self, *, revert: bool = False) -> None:
    if revert and self.current_val != self._value_at_press:
      self.current_val = self._value_at_press
      self.on_change(self.current_val)
    self.reset_interaction()

  def _finalize_interaction(self, mouse_pos: MousePos, *, inside_release: bool) -> None:
    button_w = self._button_width(self._rect)
    changed = False

    if self._minus_pressed:
      self._minus_pressed = False
      if inside_release and rl.check_collision_point_rec(mouse_pos, rl.Rectangle(self._rect.x, self._rect.y, button_w, self._rect.height)):
        new_val = self._clamp_and_snap(self.current_val - self.step)
        if new_val != self.current_val:
          self.current_val = new_val
          self.on_change(self.current_val)
          changed = True

    if self._plus_pressed:
      self._plus_pressed = False
      if inside_release and rl.check_collision_point_rec(mouse_pos, rl.Rectangle(self._rect.x + self._rect.width - button_w, self._rect.y, button_w, self._rect.height)):
        new_val = self._clamp_and_snap(self.current_val + self.step)
        if new_val != self.current_val:
          self.current_val = new_val
          self.on_change(self.current_val)
          changed = True

    if self._is_dragging:
      changed = changed or self.current_val != self._value_at_press
      self._is_dragging = False
      self._thumb_offset = 0.0
    elif self._pending_drag:
      if inside_release and not self._started_on_thumb and rl.check_collision_point_rec(mouse_pos, self._rect):
        before_tap = self.current_val
        self._update_val_from_mouse(mouse_pos)
        changed = changed or before_tap != self.current_val
      self._pending_drag = False
      self._thumb_offset = 0.0
      changed = changed or self.current_val != self._value_at_press

    self._started_on_thumb = False
    if changed and self.on_commit is not None:
      self.on_commit(self.current_val)

  def _clamp_and_snap(self, val: float) -> float:
    if self.step <= 0:
      return max(self.min_val, min(self.max_val, val))
    snapped = round((val - self.min_val) / self.step) * self.step + self.min_val
    return max(self.min_val, min(self.max_val, snapped))

  def _button_width(self, rect: rl.Rectangle) -> int:
    return min(SLIDER_BUTTON_SIZE, max(44, int(rect.width * 0.14)))

  def _thumb_size(self, rect: rl.Rectangle, track_h: int | None = None) -> tuple[int, int]:
    effective_track_h = track_h if track_h is not None else max(12, int(rect.height * 0.22))
    return max(18, int(effective_track_h * 0.95)), max(34, int(rect.height * 0.50))

  def _get_thumb_x(self, rect: rl.Rectangle) -> float:
    button_w = self._button_width(rect)
    track_x = rect.x + button_w
    track_w = rect.width - 2 * button_w
    value_range = self.max_val - self.min_val
    frac = 0.0 if value_range == 0 else (self.current_val - self.min_val) / value_range
    return track_x + frac * track_w

  def _exponential_ease(self, current: float, target: float, dt: float) -> float:
    if current == target:
      return target
    return current + (target - current) * (1 - math.exp(-dt / PLATE_TAU))

  def _draw_slider_button(self, rect: rl.Rectangle, label: str):
    offset = self._minus_offset if label == "-" else self._plus_offset
    face_x = _snap(rect.x)
    face_y = _snap(rect.y + min(1.0, offset))
    face_rect = _snap_rect(rl.Rectangle(face_x, face_y, rect.width, rect.height))
    btn_color = rl.Color(34, 38, 48, 255)
    border_color = rl.Color(255, 255, 255, 28)
    _draw_rounded_fill(face_rect, btn_color, radius_px=16)
    _draw_rounded_stroke(face_rect, border_color, radius_px=16)
    rl.draw_rectangle_rec(rl.Rectangle(face_rect.x, face_rect.y, face_rect.width, 1), rl.Color(255, 255, 255, 16))
    font_size = max(22, int(round(min(rect.width, rect.height) * 0.52)))
    ts = measure_text_cached(self._font, label, font_size)
    label_pos = rl.Vector2(face_x + (rect.width - ts.x) / 2, face_y + (rect.height - ts.y) / 2)
    rl.draw_text_ex(self._font, label, rl.Vector2(round(label_pos.x), round(label_pos.y)), font_size, 0, rl.WHITE)

  def _render(self, rect: rl.Rectangle):
    rect = _snap_rect(rect)
    self.set_rect(rect)
    dt = rl.get_frame_time()
    if self._is_dragging:
      self._update_val_from_mouse(rl.get_mouse_position())
    self._minus_offset = self._exponential_ease(self._minus_offset, 1.0 if self._minus_pressed else 0.0, dt)
    self._plus_offset = self._exponential_ease(self._plus_offset, 1.0 if self._plus_pressed else 0.0, dt)
    button_w = self._button_width(rect)
    minus_rect = _snap_rect(rl.Rectangle(rect.x, rect.y, button_w, rect.height))
    plus_rect = _snap_rect(rl.Rectangle(rect.x + rect.width - button_w, rect.y, button_w, rect.height))
    self._draw_slider_button(minus_rect, "-")
    self._draw_slider_button(plus_rect, "+")
    track_x = rect.x + button_w
    track_w = rect.width - 2 * button_w
    track_h = max(12, int(rect.height * 0.22))
    track_rect = _snap_rect(rl.Rectangle(track_x, rect.y + (rect.height - track_h) / 2, track_w, track_h))
    _draw_rounded_fill(track_rect, rl.Color(34, 38, 48, 255), radius_px=track_h / 2)
    _draw_rounded_stroke(track_rect, rl.Color(255, 255, 255, 20), radius_px=track_h / 2)
    value_range = self.max_val - self.min_val
    frac = 0.0 if value_range == 0 else (self.current_val - self.min_val) / value_range
    fill_w = frac * track_w
    if fill_w > 0:
      fill_rect = _snap_rect(rl.Rectangle(track_x, track_rect.y, fill_w, track_h))
      rl.draw_rectangle_rec(fill_rect, _with_alpha(self.color, 190))
    if self.step > 0:
      n_steps = int(round(value_range / self.step))
      if n_steps > 0:
        tick_count = min(n_steps, 24)
        for i in range(tick_count + 1):
          tick_x = track_x + (i / max(1, tick_count)) * track_w
          tick_h = int(track_h * 0.6)
          tick_y = track_rect.y + (track_h - tick_h) / 2
          rl.draw_rectangle_rec(rl.Rectangle(tick_x - 1, tick_y, 2, tick_h), rl.Color(255, 255, 255, 60))
    thumb_w, thumb_h = self._thumb_size(rect, track_h)
    thumb_x = self._get_thumb_x(rect) - thumb_w / 2
    thumb_y = rect.y + (rect.height - thumb_h) / 2
    thumb_offset = GEOMETRY_OFFSET * self._thumb_offset
    t_face_rect = _snap_rect(rl.Rectangle(thumb_x, thumb_y + min(1.0, thumb_offset), thumb_w, thumb_h))
    _draw_rounded_fill(t_face_rect, rl.Color(230, 235, 242, 255), radius_px=12)
    _draw_rounded_stroke(t_face_rect, rl.Color(20, 22, 28, 46), radius_px=12)
    rl.draw_rectangle_rec(rl.Rectangle(t_face_rect.x, t_face_rect.y, t_face_rect.width, 1), rl.Color(255, 255, 255, 40))
    if self.show_value_label:
      val_str = self.labels.get(self.current_val, f"{self.current_val:.2f}".rstrip('0').rstrip('.') + self.unit)
      label_size = max(18, int(round(rect.height * 0.38)))
      ts = measure_text_cached(self._font, val_str, label_size)
      val_x = max(rect.x, min(thumb_x + (thumb_w - ts.x) / 2, rect.x + rect.width - ts.x))
      val_pos = rl.Vector2(val_x, thumb_y - label_size - 10)
      rl.draw_text_ex(self._font, val_str, rl.Vector2(round(val_pos.x), round(val_pos.y)), label_size, 0, rl.WHITE)

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if not self._touch_valid() or not rl.check_collision_point_rec(mouse_pos, self._rect):
      return
    self._value_at_press = self.current_val
    button_w = self._button_width(self._rect)
    minus_rect = rl.Rectangle(self._rect.x, self._rect.y, button_w, self._rect.height)
    plus_rect = rl.Rectangle(self._rect.x + self._rect.width - button_w, self._rect.y, button_w, self._rect.height)
    if rl.check_collision_point_rec(mouse_pos, minus_rect):
      self._minus_pressed = True
      return
    if rl.check_collision_point_rec(mouse_pos, plus_rect):
      self._plus_pressed = True
      return
    thumb_w, thumb_h = self._thumb_size(self._rect)
    thumb_x = self._get_thumb_x(self._rect) - thumb_w / 2
    thumb_y = self._rect.y + (self._rect.height - thumb_h) / 2
    thumb_rect = rl.Rectangle(thumb_x - 8, thumb_y - 8, thumb_w + 16, thumb_h + 16)
    if rl.check_collision_point_rec(mouse_pos, thumb_rect):
      self._pending_drag = True
      self._started_on_thumb = True
      self._press_start = rl.Vector2(mouse_pos.x, mouse_pos.y)
      self._thumb_offset = 1.0
    else:
      self._pending_drag = True
      self._started_on_thumb = False
      self._press_start = rl.Vector2(mouse_pos.x, mouse_pos.y)

  def _handle_mouse_release(self, mouse_pos: MousePos):
    self._finalize_interaction(mouse_pos, inside_release=True)

  def _handle_mouse_event(self, mouse_event: MouseEvent):
    mouse_in_rect = rl.check_collision_point_rec(mouse_event.pos, self._rect)
    if mouse_event.left_released and self.is_interacting and not mouse_in_rect:
      self._finalize_interaction(mouse_event.pos, inside_release=False)
      return

    if not self._touch_valid():
      self._cancel_interaction(revert=True)
      return

    if self._pending_drag and not self._is_dragging:
      dx = mouse_event.pos.x - self._press_start.x
      dy = mouse_event.pos.y - self._press_start.y
      if abs(dy) > 12 and abs(dy) > abs(dx):
        self._pending_drag = False
        self._started_on_thumb = False
        self._thumb_offset = 0.0
        return
      if abs(dx) > 12 and abs(dx) >= abs(dy):
        self._pending_drag = False
        self._is_dragging = True
        self._thumb_offset = 1.0

    if self._is_dragging:
      dx = mouse_event.pos.x - self._press_start.x
      dy = mouse_event.pos.y - self._press_start.y
      if abs(dy) > 18 and abs(dy) > abs(dx) * 1.15:
        self._cancel_interaction(revert=True)
        return
      self._update_val_from_mouse(mouse_event.pos)

  def _update_val_from_mouse(self, mouse_pos: MousePos):
    button_w = self._button_width(self._rect)
    track_x = self._rect.x + button_w
    track_w = self._rect.width - 2 * button_w
    if track_w <= 0:
      return
    rel_x = max(0.0, min(1.0, (mouse_pos.x - track_x) / track_w))
    val = self.min_val + rel_x * (self.max_val - self.min_val)
    snapped = self._clamp_and_snap(val)
    if snapped != self.current_val:
      self.current_val = snapped
      self.on_change(self.current_val)


class AetherSliderDialog(Widget):
  def __init__(
    self,
    title: str,
    min_val: float,
    max_val: float,
    step: float,
    current_val: float,
    on_close: Callable,
    presets: list[float] | None = None,
    unit: str = "",
    labels: dict[float, str] | None = None,
    color: rl.Color | str = "#8B5CF6",
    on_change: Callable[[float], None] | None = None,
  ):
    super().__init__()
    self.title, self._user_callback = title, on_close
    self._on_change = on_change
    self._color = hex_to_color(color) if isinstance(color, str) else color
    self._font_title, self._font_btn = gui_app.font(FontWeight.BOLD), gui_app.font(FontWeight.BOLD)
    self._font_value = gui_app.font(FontWeight.BOLD)
    self._current_val = current_val
    self.min_val = min_val
    self.max_val = max_val
    self.step = step
    self._presets = presets or []
    self._unit = unit
    self._labels = labels or {}
    self._preset_rects: list[tuple[float, rl.Rectangle]] = []
    self._pressed_zone: str | None = None
    self._is_pressed_ok = False
    self._is_pressed_cancel = False
    self._ok_offset = 0.0
    self._cancel_offset = 0.0
    self._ok_target = 0.0
    self._cancel_target = 0.0
    self._is_dragging = False
    self._val_on_press = current_val

    self._ok_rect = rl.Rectangle(0, 0, 0, 0)
    self._cancel_rect = rl.Rectangle(0, 0, 0, 0)
    self._minus_rect = rl.Rectangle(0, 0, 0, 0)
    self._plus_rect = rl.Rectangle(0, 0, 0, 0)
    self._track_rect = rl.Rectangle(0, 0, 0, 0)
    self._thumb_rect = rl.Rectangle(0, 0, 0, 0)

  def _value_fraction(self, value: float) -> float:
    val_range = self.max_val - self.min_val
    if val_range == 0:
      return 0.0
    return max(0.0, min(1.0, (value - self.min_val) / val_range))

  def _clamp_and_snap(self, val: float) -> float:
    if self.step <= 0:
      return max(self.min_val, min(self.max_val, val))
    snapped = round((val - self.min_val) / self.step) * self.step + self.min_val
    return max(self.min_val, min(self.max_val, snapped))

  def _update_val_from_mouse(self, mouse_pos: MousePos) -> None:
    if self._track_rect.width <= 0:
      return
    rel_x = max(0.0, min(1.0, (mouse_pos.x - self._track_rect.x) / self._track_rect.width))
    val = self.min_val + rel_x * (self.max_val - self.min_val)
    self._current_val = self._clamp_and_snap(val)

  def formatted_value(self) -> str:
    return format_adjustor_value(self._current_val, step=self.step, unit=self._unit, labels=self._labels)

  def _handle_mouse_press(self, mouse_pos: MousePos):
    self._val_on_press = self._current_val
    if rl.check_collision_point_rec(mouse_pos, self._ok_rect):
      self._is_pressed_ok = True
      self._ok_target = 1.0
      return
    if rl.check_collision_point_rec(mouse_pos, self._cancel_rect):
      self._is_pressed_cancel = True
      self._cancel_target = 1.0
      return

    for value, preset_rect in self._preset_rects:
      if rl.check_collision_point_rec(mouse_pos, preset_rect):
        self._pressed_zone = f"preset:{value}"
        return

    if rl.check_collision_point_rec(mouse_pos, self._minus_rect):
      self._pressed_zone = "minus"
      return
    if rl.check_collision_point_rec(mouse_pos, self._plus_rect):
      self._pressed_zone = "plus"
      return

    hit_track = _inflate_rect(self._track_rect, 0, 36)
    if rl.check_collision_point_rec(mouse_pos, hit_track):
      self._is_dragging = True
      self._update_val_from_mouse(mouse_pos)
      return

  def _handle_mouse_release(self, mouse_pos: MousePos):
    is_ok = self._is_pressed_ok
    is_cancel = self._is_pressed_cancel

    if self._is_pressed_ok:
      self._ok_target = 0.0
      if rl.check_collision_point_rec(mouse_pos, self._ok_rect):
        gui_app.pop_widget()
        self._user_callback(DialogResult.CONFIRM, self._current_val)
      self._is_pressed_ok = False
    elif self._is_pressed_cancel:
      self._cancel_target = 0.0
      if rl.check_collision_point_rec(mouse_pos, self._cancel_rect):
        gui_app.pop_widget()
        self._user_callback(DialogResult.CANCEL, self._current_val)
      self._is_pressed_cancel = False
    elif self._pressed_zone:
      if self._pressed_zone.startswith("preset:"):
        try:
          preset_value = float(self._pressed_zone.split(":", 1)[1])
        except ValueError:
          preset_value = None
        if preset_value is not None:
          for value, preset_rect in self._preset_rects:
            if value == preset_value and rl.check_collision_point_rec(mouse_pos, preset_rect):
              self._current_val = preset_value
              break
      elif self._pressed_zone == "minus":
        if rl.check_collision_point_rec(mouse_pos, self._minus_rect):
          self._current_val = self._clamp_and_snap(self._current_val - self.step)
      elif self._pressed_zone == "plus":
        if rl.check_collision_point_rec(mouse_pos, self._plus_rect):
          self._current_val = self._clamp_and_snap(self._current_val + self.step)
      self._pressed_zone = None

    if self._is_dragging:
      self._is_dragging = False

    if not is_ok and not is_cancel:
      if self._current_val != self._val_on_press and self._on_change:
        self._on_change(self._current_val)

  def _handle_mouse_event(self, mouse_event):
    if self._is_dragging:
      self._update_val_from_mouse(mouse_event.pos)

  def _render_preset_chip(self, rect: rl.Rectangle, text: str, *, current: bool, pressed: bool):
    fill = rl.Color(255, 255, 255, 5)
    border = rl.Color(255, 255, 255, 14)
    text_color = AetherListColors.SUBTEXT
    if current:
      fill = _mix_colors(rl.Color(18, 22, 28, 255), self._color, 0.22, alpha=255)
      border = _with_alpha(self._color, 72)
      text_color = AetherListColors.HEADER
    elif pressed:
      fill = rl.Color(255, 255, 255, 10)
      border = rl.Color(255, 255, 255, 22)

    _draw_rounded_fill(rect, fill, radius_px=16)
    _draw_rounded_stroke(rect, border, radius_px=16)
    _draw_text_fit_common(
      gui_app.font(FontWeight.MEDIUM),
      text,
      rl.Vector2(rect.x + 10, rect.y + (rect.height - 28) / 2),
      max(1.0, rect.width - 20),
      28,
      align_center=True,
      color=text_color,
    )

  def _render(self, rect: rl.Rectangle):
    dt = rl.get_frame_time()
    self._ok_offset += (self._ok_target - self._ok_offset) * (1 - math.exp(-dt / PLATE_TAU))
    self._cancel_offset += (self._cancel_target - self._cancel_offset) * (1 - math.exp(-dt / PLATE_TAU))
    rl.draw_rectangle(0, 0, gui_app.width, gui_app.height, rl.Color(0, 0, 0, 160))

    has_presets = len(self._presets) > 0
    dialog_w = 1600
    dialog_h = 840 if has_presets else 700
    button_height = 110
    button_width = 600

    dx, dy = rect.x + (rect.width - dialog_w) / 2, rect.y + (rect.height - dialog_h) / 2
    self._ok_rect = rl.Rectangle(dx + dialog_w - button_width - 80, dy + dialog_h - button_height - 60, button_width, button_height)
    self._cancel_rect = rl.Rectangle(dx + 80, dy + dialog_h - button_height - 60, button_width, button_height)

    d_rect = _snap_rect(rl.Rectangle(dx, dy, dialog_w, dialog_h))
    _draw_rounded_fill(d_rect, rl.Color(10, 12, 16, 255), radius_px=24)
    _draw_rounded_stroke(d_rect, rl.Color(255, 255, 255, 16), radius_px=24)
    rl.draw_rectangle_rec(rl.Rectangle(d_rect.x, d_rect.y, d_rect.width, 3), self._color)

    title_size = 44
    ts = measure_text_cached(self._font_title, self.title, title_size)
    rl.draw_text_ex(self._font_title, self.title, rl.Vector2(round(dx + (dialog_w - ts.x) / 2), round(dy + 60)), title_size, 0, rl.WHITE)

    # Large value display below title
    val_str = self.formatted_value()
    val_size = 96
    vts = measure_text_cached(self._font_value, val_str, val_size)
    rl.draw_text_ex(self._font_value, val_str, rl.Vector2(round(dx + (dialog_w - vts.x) / 2), round(dy + 140)), val_size, 0, self._color)

    # Render presets below the value display (if any)
    presets_y = dy + 270
    self._preset_rects.clear()
    if has_presets:
      chip_h = 84.0
      chip_gap = 24.0
      chip_w = max(90.0, (dialog_w - 80 * 2 - chip_gap * (len(self._presets) - 1)) / max(1, len(self._presets)))
      for index, val in enumerate(self._presets):
        chip_x = dx + 80 + index * (chip_w + chip_gap)
        chip_rect = _snap_rect(rl.Rectangle(chip_x, presets_y, chip_w, chip_h))
        self._preset_rects.append((val, chip_rect))
        formatted_label = format_adjustor_value(val, step=self.step, unit=self._unit, labels=self._labels)
        self._render_preset_chip(
          chip_rect,
          formatted_label,
          current=abs(self._current_val - val) <= 0.5 * self.step,
          pressed=self._pressed_zone == f"preset:{val}",
        )
      slider_y = dy + 470
    else:
      slider_y = dy + 330

    # Slider
    btn_size = 110
    self._minus_rect = _snap_rect(rl.Rectangle(dx + 80, slider_y - btn_size / 2, btn_size, btn_size))
    self._plus_rect = _snap_rect(rl.Rectangle(dx + dialog_w - 80 - btn_size, slider_y - btn_size / 2, btn_size, btn_size))

    # Draw minus button
    minus_pressed = self._pressed_zone == "minus"
    _draw_rounded_fill(self._minus_rect, rl.Color(255, 255, 255, 14 if minus_pressed else 8), radius_px=55)
    _draw_rounded_stroke(self._minus_rect, rl.Color(255, 255, 255, 28 if minus_pressed else 18), radius_px=55)
    mts = measure_text_cached(self._font_btn, "-", 44)
    rl.draw_text_ex(self._font_btn, "-", rl.Vector2(round(self._minus_rect.x + (btn_size - mts.x) / 2), round(self._minus_rect.y + (btn_size - mts.y) / 2)), 44, 0, rl.WHITE)

    # Draw plus button
    plus_pressed = self._pressed_zone == "plus"
    _draw_rounded_fill(self._plus_rect, rl.Color(255, 255, 255, 14 if plus_pressed else 8), radius_px=55)
    _draw_rounded_stroke(self._plus_rect, rl.Color(255, 255, 255, 28 if plus_pressed else 18), radius_px=55)
    pts = measure_text_cached(self._font_btn, "+", 44)
    rl.draw_text_ex(self._font_btn, "+", rl.Vector2(round(self._plus_rect.x + (btn_size - pts.x) / 2), round(self._plus_rect.y + (btn_size - pts.y) / 2)), 44, 0, rl.WHITE)

    # Draw track
    track_x = self._minus_rect.x + btn_size + 36
    track_w = self._plus_rect.x - 36 - track_x
    track_h = 16
    track_y = slider_y - track_h / 2
    self._track_rect = _snap_rect(rl.Rectangle(track_x, track_y, track_w, track_h))

    _draw_rounded_fill(self._track_rect, rl.Color(255, 255, 255, 14), radius_px=8)
    _draw_rounded_stroke(self._track_rect, rl.Color(255, 255, 255, 8), radius_px=8)

    # Draw ticks at preset values (or custom ticks if no presets)
    ticks_to_draw = self._presets
    if not has_presets:
      ticks_to_draw = [self.min_val, (self.min_val + self.max_val) / 2, self.max_val]

    for val in ticks_to_draw:
      frac = self._value_fraction(val)
      tick_x = track_x + frac * track_w
      rl.draw_rectangle_rec(rl.Rectangle(tick_x - 1, track_y - 7, 3, 30), rl.Color(255, 255, 255, 28))

    # Draw active fill
    fill_frac = self._value_fraction(self._current_val)
    fill_w = fill_frac * track_w
    if fill_w > 0:
      fill_rect = _snap_rect(rl.Rectangle(track_x, track_y, fill_w, track_h))
      _draw_rounded_fill(fill_rect, self._color, radius_px=8)

    # Draw thumb
    thumb_w = 32
    thumb_h = 64
    thumb_x = track_x + fill_frac * track_w
    self._thumb_rect = _snap_rect(rl.Rectangle(thumb_x - thumb_w / 2, slider_y - thumb_h / 2, thumb_w, thumb_h))
    _draw_rounded_fill(self._thumb_rect, rl.WHITE, radius_px=16)
    _draw_rounded_stroke(self._thumb_rect, rl.Color(20, 22, 28, 46), radius_px=16)

    # Cancel Button
    c_face_x = self._cancel_rect.x
    c_face_y = self._cancel_rect.y + min(1.0, GEOMETRY_OFFSET * self._cancel_offset * 0.1)
    c_face = _snap_rect(rl.Rectangle(c_face_x, c_face_y, button_width, button_height))
    _draw_rounded_fill(c_face, rl.Color(34, 38, 48, 255), radius_px=28)
    _draw_rounded_stroke(c_face, rl.Color(255, 255, 255, 20), radius_px=28)
    cts = measure_text_cached(self._font_btn, tr("CANCEL"), 34)
    rl.draw_text_ex(self._font_btn, tr("CANCEL"), rl.Vector2(round(c_face_x + (button_width - cts.x) / 2), round(c_face_y + (button_height - cts.y) / 2)), 34, 0, rl.WHITE)

    # OK Button
    o_face_x = self._ok_rect.x
    o_face_y = self._ok_rect.y + min(1.0, GEOMETRY_OFFSET * self._ok_offset * 0.1)
    o_face = _snap_rect(rl.Rectangle(o_face_x, o_face_y, button_width, button_height))
    _draw_rounded_fill(o_face, self._color, radius_px=28)
    _draw_rounded_stroke(o_face, _with_alpha(self._color, 150), radius_px=28)
    ots = measure_text_cached(self._font_btn, tr("OK"), 34)
    rl.draw_text_ex(self._font_btn, tr("OK"), rl.Vector2(round(o_face_x + (button_width - ots.x) / 2), round(o_face_y + (button_height - ots.y) / 2)), 34, 0, rl.WHITE)
    return DialogResult.NO_ACTION


class RadioTileGroup(Widget):
  def __init__(self, title: str, options: list[str], current_index: int, on_change: Callable):
    super().__init__()
    self.title, self.options, self.current_index, self.on_change = title, options, current_index, on_change
    self._font, self._font_title = gui_app.font(FontWeight.BOLD), gui_app.font(FontWeight.NORMAL)
    self._active_color, self._inactive_color = AetherListColors.PRIMARY, rl.Color(80, 80, 80, 255)
    self._pressed_index = -1
    self._option_rects: list[rl.Rectangle] = []
    self._option_offsets: list[float] = []
    self._option_targets: list[float] = []

  def set_index(self, index: int):
    self.current_index = index

  def _handle_mouse_press(self, mouse_pos: MousePos):
    for i, r in enumerate(self._option_rects):
      hit = rl.Rectangle(r.x - GEOMETRY_OFFSET, r.y - GEOMETRY_OFFSET, r.width + 2 * GEOMETRY_OFFSET, r.height + 2 * GEOMETRY_OFFSET)
      if rl.check_collision_point_rec(mouse_pos, hit):
        self._pressed_index = i
        if i < len(self._option_offsets):
          self._option_targets[i] = 1.0
        return

  def _handle_mouse_release(self, mouse_pos: MousePos):
    if self._pressed_index != -1:
      r = self._option_rects[self._pressed_index]
      hit = rl.Rectangle(r.x - GEOMETRY_OFFSET, r.y - GEOMETRY_OFFSET, r.width + 2 * GEOMETRY_OFFSET, r.height + 2 * GEOMETRY_OFFSET)
      if rl.check_collision_point_rec(mouse_pos, hit):
        if self.current_index != self._pressed_index:
          self.current_index = self._pressed_index
          self.on_change(self.current_index)
      if self._pressed_index < len(self._option_targets):
        self._option_targets[self._pressed_index] = 0.0
      self._pressed_index = -1

  def _render(self, rect: rl.Rectangle):
    rect = _snap_rect(rect)
    self.set_rect(rect)
    self._option_rects.clear()
    dt = rl.get_frame_time()
    while len(self._option_offsets) < len(self.options):
      self._option_offsets.append(0.0)
      self._option_targets.append(0.0)
    for i in range(len(self._option_offsets)):
      self._option_offsets[i] += (self._option_targets[i] - self._option_offsets[i]) * (1 - math.exp(-dt / PLATE_TAU))
    gap = SPACING.lg
    option_w = (rect.width - max(0, len(self.options) - 1) * gap) / max(1, len(self.options))
    total_width = len(self.options) * option_w + max(0, len(self.options) - 1) * gap
    if self.title:
      title_size = measure_text_cached(self._font_title, self.title, 40)
      rl.draw_text_ex(self._font_title, self.title, rl.Vector2(round(rect.x), round(rect.y + (rect.height - title_size.y) / 2)), 40, 0, rl.WHITE)
      start_x = rect.x + rect.width - total_width
    else:
      start_x = rect.x + (rect.width - total_width) / 2
    for i, opt in enumerate(self.options):
      r = _snap_rect(rl.Rectangle(start_x + i * (option_w + gap), rect.y, option_w, rect.height))
      self._option_rects.append(r)
      is_active = i == self.current_index
      fill = _mix_colors(rl.Color(28, 32, 40, 255), self._active_color, 0.18 if is_active else 0.05)
      border = _with_alpha(self._active_color if is_active else rl.Color(255, 255, 255, 36), 96 if is_active else 28)
      offset = self._option_offsets[i] if i < len(self._option_offsets) else 0.0
      face_x = r.x
      face_y = r.y + min(1.0, offset)
      face_rect = _snap_rect(rl.Rectangle(face_x, face_y, r.width, r.height))
      _draw_rounded_fill(face_rect, fill, radius_px=16)
      _draw_rounded_stroke(face_rect, border, radius_px=16)
      rl.draw_rectangle_rec(rl.Rectangle(face_rect.x, face_rect.y, face_rect.width, 1), rl.Color(255, 255, 255, 16))
      font_size = max(18, min(30, int(r.height * 0.34)))
      spacing = round(font_size * 0.05)
      max_width = r.width - (SPACING.lg + SPACING.xs)
      ts = measure_text_cached(self._font, opt, font_size, spacing=spacing)
      while font_size > 16 and ts.x > max_width:
        font_size -= 1
        spacing = round(font_size * 0.05)
        ts = measure_text_cached(self._font, opt, font_size, spacing=spacing)
      text_pos = rl.Vector2(face_x + (r.width - ts.x) / 2, face_y + (r.height - ts.y) / 2)
      rl.draw_text_ex(self._font, opt, rl.Vector2(round(text_pos.x), round(text_pos.y)), font_size, spacing, AetherListColors.HEADER if is_active else AetherListColors.SUBTEXT)


class AetherSegmentedControl(Widget):
  def __init__(
    self,
    options: list[str | Callable[[], str]],
    current_index: int | Callable[[], int],
    on_change: Callable[[int], None],
    statuses: list[str | Callable[[], str] | None] | None = None,
    compact: bool = False,
    style: PanelStyle | None = None,
  ):
    super().__init__()
    self._options = options
    self._current_index = current_index
    self._on_change = on_change
    self._statuses = statuses or [""] * len(options)
    if len(self._statuses) < len(self._options):
      self._statuses += [""] * (len(self._options) - len(self._statuses))
    self._compact = compact
    self._style = style
    self._font = gui_app.font(FontWeight.BOLD)
    self._font_status = gui_app.font(FontWeight.NORMAL)
    self._pressed_index = -1
    self._option_rects: list[rl.Rectangle] = []
    self._option_offsets: list[float] = []
    self._option_targets: list[float] = []

  def _current(self) -> int:
    if callable(self._current_index):
      return max(0, min(len(self._options) - 1, int(self._current_index())))
    return max(0, min(len(self._options) - 1, int(self._current_index)))

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if not self._touch_valid():
      return
    for i, r in enumerate(self._option_rects):
      hit = rl.Rectangle(r.x - GEOMETRY_OFFSET, r.y - GEOMETRY_OFFSET, r.width + 2 * GEOMETRY_OFFSET, r.height + 2 * GEOMETRY_OFFSET)
      if rl.check_collision_point_rec(mouse_pos, hit):
        self._pressed_index = i
        while len(self._option_targets) < len(self._options):
          self._option_offsets.append(0.0)
          self._option_targets.append(0.0)
        self._option_targets[i] = 1.0
        return

  def _handle_mouse_release(self, mouse_pos: MousePos):
    if self._pressed_index == -1:
      return
    pressed_index = self._pressed_index
    self._pressed_index = -1
    if pressed_index < len(self._option_targets):
      self._option_targets[pressed_index] = 0.0
    if not self._touch_valid():
      return
    r = self._option_rects[pressed_index]
    hit = rl.Rectangle(r.x - GEOMETRY_OFFSET, r.y - GEOMETRY_OFFSET, r.width + 2 * GEOMETRY_OFFSET, r.height + 2 * GEOMETRY_OFFSET)
    if rl.check_collision_point_rec(mouse_pos, hit) and self._current() != pressed_index:
      self._on_change(pressed_index)

  def _handle_mouse_event(self, mouse_event: MouseEvent):
    if self._pressed_index == -1:
      return
    if not self._touch_valid():
      if self._pressed_index < len(self._option_targets):
        self._option_targets[self._pressed_index] = 0.0
      self._pressed_index = -1
      return
    if self._pressed_index < len(self._option_rects):
      r = self._option_rects[self._pressed_index]
      hit = rl.Rectangle(r.x - GEOMETRY_OFFSET, r.y - GEOMETRY_OFFSET, r.width + 2 * GEOMETRY_OFFSET, r.height + 2 * GEOMETRY_OFFSET)
      if not rl.check_collision_point_rec(mouse_event.pos, hit):
        if self._pressed_index < len(self._option_targets):
          self._option_targets[self._pressed_index] = 0.0
        self._pressed_index = -1

  def _render(self, rect: rl.Rectangle):
    rect = _snap_rect(rect)
    self.set_rect(rect)
    self._option_rects.clear()

    if not self._touch_valid() and self._pressed_index != -1:
      if self._pressed_index < len(self._option_targets):
        self._option_targets[self._pressed_index] = 0.0
      self._pressed_index = -1

    dt = rl.get_frame_time()
    while len(self._option_offsets) < len(self._options):
      self._option_offsets.append(0.0)
      self._option_targets.append(0.0)
    for i in range(len(self._option_offsets)):
      self._option_offsets[i] += (self._option_targets[i] - self._option_offsets[i]) * (1 - math.exp(-dt / PLATE_TAU))

    draw_soft_card(rect, rl.Color(255, 255, 255, 4), rl.Color(255, 255, 255, 14))

    inner_pad = 4 if self._compact else 5
    gap = 4 if self._compact else 6
    inner_rect = rl.Rectangle(rect.x + inner_pad, rect.y + inner_pad, rect.width - inner_pad * 2, rect.height - inner_pad * 2)
    option_w = (inner_rect.width - max(0, len(self._options) - 1) * gap) / max(1, len(self._options))
    has_status = any(str(_resolve_value(status, "")) for status in self._statuses)
    current_index = self._current()

    for i, option in enumerate(self._options):
      base_rect = _snap_rect(rl.Rectangle(inner_rect.x + i * (option_w + gap), inner_rect.y, option_w, inner_rect.height))
      self._option_rects.append(base_rect)
      offset = self._option_offsets[i] if i < len(self._option_offsets) else 0.0
      face_rect = _snap_rect(rl.Rectangle(base_rect.x, base_rect.y + min(1.0, offset), base_rect.width, base_rect.height))
      is_active = i == current_index

      if self._style is not None:
        accent = self._style.accent
        fill = _mix_colors(rl.Color(18, 22, 28, 255), accent, 0.16, alpha=255) if is_active else rl.Color(255, 255, 255, 3)
        border = _with_alpha(accent, 72) if is_active else rl.Color(255, 255, 255, 8)
        title_color = accent if is_active else AetherListColors.SUBTEXT
        status_color = _mix_colors(accent, AetherListColors.HEADER, 0.4) if is_active else AetherListColors.MUTED
      else:
        fill = rl.Color(255, 255, 255, 12) if is_active else rl.Color(255, 255, 255, 3)
        border = rl.Color(255, 255, 255, 30) if is_active else rl.Color(255, 255, 255, 8)
        title_color = AetherListColors.HEADER if is_active else AetherListColors.SUBTEXT
        status_color = AetherListColors.MUTED

      _draw_rounded_fill(face_rect, fill, radius_px=16)
      _draw_rounded_stroke(face_rect, border, radius_px=16)
      rl.draw_rectangle_rec(rl.Rectangle(face_rect.x, face_rect.y, face_rect.width, 1), rl.Color(255, 255, 255, 18 if is_active else 10))

      label = str(_resolve_value(option, ""))
      status = str(_resolve_value(self._statuses[i], ""))
      title_size = max(18, min(24, int(face_rect.height * (0.28 if has_status else 0.36))))
      status_size = max(14, min(17, int(face_rect.height * 0.22)))

      if has_status:
        title_y = face_rect.y + max(9.0, min(14.0, face_rect.height * 0.18))
        status_y = face_rect.y + face_rect.height - status_size - max(9.0, min(14.0, face_rect.height * 0.18))
        _draw_text_fit_common(
          self._font,
          label,
          rl.Vector2(face_rect.x + 16, title_y),
          face_rect.width - 32,
          title_size,
          align_center=True,
          color=title_color,
        )
        _draw_text_fit_common(
          self._font_status,
          status,
          rl.Vector2(face_rect.x + 16, status_y),
          face_rect.width - 32,
          status_size,
          align_center=True,
          color=status_color,
        )
      else:
        _draw_text_fit_common(
          self._font,
          label,
          rl.Vector2(face_rect.x + 16, face_rect.y + (face_rect.height - title_size) / 2),
          face_rect.width - 32,
          title_size,
          align_center=True,
          color=title_color,
        )


class TileGrid(Widget):
  def __init__(self, columns: int | None = None, padding: int | None = None, uniform_width: bool = False, min_tile_width: int | None = None, tile_height: float | None = None, force_square: bool = False):
    super().__init__()
    self._columns = columns
    self._gap = padding if padding is not None else SPACING.tile_gap
    self.tiles = []
    self._uniform_width = uniform_width
    self._min_tile_width = min_tile_width if min_tile_width is not None else MIN_TILE_WIDTH
    self._tile_height = tile_height
    self.force_square = force_square


  @property
  def gap(self) -> int:
    return self._gap

  def add_tile(self, tile: Widget):
    self.tiles.append(tile)
    touch_valid_callback = getattr(self, "_touch_valid_callback", None)
    if touch_valid_callback is not None and hasattr(tile, "set_touch_valid_callback"):
      tile.set_touch_valid_callback(touch_valid_callback)

  def set_touch_valid_callback(self, touch_callback: Callable[[], bool]) -> None:
    super().set_touch_valid_callback(touch_callback)
    for tile in self.tiles:
      if hasattr(tile, "set_touch_valid_callback"):
        tile.set_touch_valid_callback(touch_callback)

  def clear(self):
    self.tiles.clear()

  def get_column_count(self, tile_count: int | None = None) -> int:
    count = len(self.tiles) if tile_count is None else tile_count
    if count <= 0:
      return self._columns or 1
    if self._columns is not None:
      return self._columns
    if count == 1:
      return 1
    if count == 2:
      return 2
    if count == 3:
      return 3
    if count == 4:
      return 2
    if count <= 6:
      return 3
    return 4

  def get_effective_column_count(self, available_width: float | None = None, tile_count: int | None = None) -> int:
    count = len(self.tiles) if tile_count is None else tile_count
    preferred = self.get_column_count(count)
    if available_width is None or available_width <= 0:
      return preferred
    min_tile_width = max(1, self._min_tile_width)
    max_cols_by_width = max(1, int((available_width + self._gap) / (min_tile_width + self._gap)))
    limit_by_count = count if self._columns is None else preferred
    return max(1, min(preferred, limit_by_count, max_cols_by_width))

  def get_row_count(self, tile_count: int | None = None, available_width: float | None = None) -> int:
    count = len(self.tiles) if tile_count is None else tile_count
    if count <= 0:
      return 0
    cols = self.get_effective_column_count(available_width, count)
    return (count + cols - 1) // cols

  def get_internal_gap_height(self, tile_count: int | None = None, available_width: float | None = None) -> float:
    rows = self.get_row_count(tile_count, available_width=available_width)
    return self._gap * max(0, rows - 1)

  def measure_height(self, width: float) -> float:
    if not self.tiles:
      return 0.0
    count = len(self.tiles)
    rows = self.get_row_count(count, available_width=width)
    if self.force_square:
      cols = self.get_effective_column_count(width, count)
      col_w = (width - (self._gap * (cols - 1))) / cols
      h = col_w
    else:
      h = self._tile_height if self._tile_height is not None else 130.0
    return rows * h + self.get_internal_gap_height(count, available_width=width)

  def _render(self, rect: rl.Rectangle):
    rect = _snap_rect(rect)
    self.set_rect(rect)
    if not self.tiles:
      return
    tiles_to_render = list(self.tiles)
    count = len(tiles_to_render)
    cols = self.get_effective_column_count(rect.width, count)
    rows = self.get_row_count(count, available_width=rect.width)
    if self.force_square:
      uniform_tile_w = (rect.width - (self._gap * (cols - 1))) / cols
      tile_h = uniform_tile_w
    else:
      if self._tile_height is not None:
        tile_h = self._tile_height
      else:
        tile_h = (rect.height - (self._gap * (rows - 1))) / rows
      uniform_tile_w = (rect.width - (self._gap * (cols - 1))) / cols if self._uniform_width else 0
    tile_idx = 0
    for r in range(rows):
      remaining = count - tile_idx
      if remaining <= 0:
        break
      items_in_row = min(cols, remaining)
      if self.force_square or self._uniform_width:
        row_tile_w = uniform_tile_w
        row_x = rect.x
      else:
        row_tile_w = (rect.width - (self._gap * (items_in_row - 1))) / items_in_row
        row_x = rect.x
      for c in range(items_in_row):
        tile = tiles_to_render[tile_idx]
        parent_rect = getattr(self, "_parent_rect", None)
        if parent_rect is not None and hasattr(tile, "set_parent_rect"):
          tile.set_parent_rect(parent_rect)
        tile.render(_snap_rect(rl.Rectangle(row_x + c * (row_tile_w + self._gap), rect.y + r * (tile_h + self._gap), row_tile_w, tile_h)))
        tile_idx += 1


def draw_toggle_pill(rect: rl.Rectangle, is_on: bool, is_enabled: bool, title: str, status_str: str, hovered: bool, pressed: bool, style: PanelStyle = DEFAULT_PANEL_STYLE, *, subtitle: str = ""):
  rect = _snap_rect(rect)
  bg_color = rl.Color(28, 32, 40, 200 if not is_enabled else 255)
  accent = style.accent if is_on and is_enabled else rl.Color(255, 255, 255, 52 if is_enabled else 20)
  _draw_rounded_fill(rect, bg_color, radius_px=18)
  _draw_rounded_stroke(rect, _with_alpha(accent, 92 if is_on and is_enabled else accent.a), radius_px=18)

  if (hovered or pressed) and is_enabled:
    overlay = rl.Color(255, 255, 255, 14 if pressed else 8)
    _draw_rounded_fill(rect, overlay, radius_px=18)

  if is_on and is_enabled:
    rl.draw_rectangle_rec(rl.Rectangle(rect.x, rect.y, 1, rect.height), _with_alpha(style.accent, 160))

  font = gui_app.font(FontWeight.BOLD)
  title_size = max(16, min(22, int(rect.height * 0.26)))
  status_size = max(18, min(24, int(rect.height * 0.32)))

  if subtitle:
    title_y = rect.y + (rect.height - title_size - 18) / 2
    rl.draw_text_ex(font, title, rl.Vector2(round(rect.x + 24), round(title_y)), title_size, 0, AetherListColors.SUBTEXT if is_enabled else AetherListColors.MUTED)
    sub_font = gui_app.font(FontWeight.NORMAL)
    sub_size = max(12, min(16, int(rect.height * 0.18)))
    rl.draw_text_ex(sub_font, subtitle, rl.Vector2(round(rect.x + 24), round(title_y + title_size + 2)), sub_size, 0, AetherListColors.MUTED)
  else:
    title_y = rect.y + (rect.height - title_size) / 2
    rl.draw_text_ex(font, title, rl.Vector2(round(rect.x + 24), round(title_y)), title_size, 0, AetherListColors.SUBTEXT if is_enabled else AetherListColors.MUTED)

  ts = measure_text_cached(font, status_str, status_size)
  status_x = rect.x + rect.width - ts.x - 24
  rl.draw_text_ex(font, status_str, rl.Vector2(round(status_x), round(rect.y + (rect.height - ts.y) / 2)), status_size, 0, AetherListColors.HEADER if is_enabled else AetherListColors.MUTED)



