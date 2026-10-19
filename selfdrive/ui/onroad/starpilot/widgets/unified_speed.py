"""One vertical Big UI card for Max Set and the accepted speed limit."""

from __future__ import annotations

import math

import pyray as rl
from openpilot.common.params import Params
from openpilot.selfdrive.ui.ui_state import ui_state, UIStatus
from openpilot.selfdrive.ui.onroad.hud_renderer import COLORS
from openpilot.selfdrive.ui.onroad.starpilot.slc_speed_limit import (
  _draw_source_icon, _get_slc_state, _is_slc_enabled, _speed_limit_pulse_color, source_icon_key,
)
from openpilot.selfdrive.ui.onroad.starpilot.speed_source_drawer import SpeedSourceDrawer
from openpilot.selfdrive.ui.onroad.starpilot.unified_speed_presentation import (
  UnifiedSpeedPresentation, resolve_unified_speed,
)
from openpilot.selfdrive.ui.onroad.starpilot.widget_style import (
  CONTROL_BG, CONTROL_ROUNDNESS, CONTROL_SEGMENTS, UNIFIED_ACCENT, draw_control_card,
)
from openpilot.selfdrive.ui.onroad.starpilot.widgets.base import LayoutWidget
from openpilot.system.ui.lib.application import gui_app, FontWeight, FONT_SCALE
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.text_measure import measure_text_cached


# Fits the existing left-column anchor without shifting the card toward the road.
UNIFIED_WIDTH = 232
MAX_ROW_HEIGHT = 208
LIMIT_ROW_HEIGHT = 240
UNIFIED_HEIGHT = MAX_ROW_HEIGHT + LIMIT_ROW_HEIGHT
SINGLE_HEIGHT = 250
MERGED_FOOTER_HEIGHT = 110
HEADER_ICON_SIZE = 34
HEADER_FONT_SIZE = 28
VALUE_FONT_SIZE = 96
UNIT_FONT_SIZE = 28
UNIT_GAP = 20
PAUSE_ICON_WIDTH = 12
PAUSE_ICON_HEIGHT = 14
PAUSE_ICON_GAP = 8
OFFSET_FONT_SIZE = 22
INLINE_OFFSET_FONT_SIZE = 28
CONFIRMATION_COLOR = rl.Color(188, 132, 255, 255)
PAUSE_COLOR = rl.Color(UNIFIED_ACCENT.r, UNIFIED_ACCENT.g, UNIFIED_ACCENT.b, 255)


def _digit_metrics(font: rl.Font) -> tuple[float, float]:
  index = rl.get_glyph_index(font, ord("0"))
  top = font.glyphs[index].offsetY
  height = font.recs[index].height
  return (top + height / 2) / font.baseSize, (top + height) / font.baseSize


def _draw_header_icon(icon_key: str, x: float, y: float) -> None:
  scale = max(1.0, gui_app._scale * max(gui_app._pixel_scale_x, gui_app._pixel_scale_y))
  # Supersample for smooth edges.
  texture_size = math.ceil(2 * HEADER_ICON_SIZE * scale)

  def render() -> None:
    rl.rl_push_matrix()
    try:
      texture_scale = texture_size / HEADER_ICON_SIZE
      rl.rl_scalef(texture_scale, texture_scale, 1.0)
      _draw_source_icon(icon_key, 0, 0, HEADER_ICON_SIZE, rl.WHITE)
    finally:
      rl.rl_pop_matrix()

  texture = gui_app.cached_render_texture(
    f"unified-speed-header:{icon_key}:{texture_size}", texture_size, texture_size, render,
  )
  if texture is None:
    _draw_source_icon(icon_key, x, y, HEADER_ICON_SIZE, rl.WHITE)
    return

  rl.begin_blend_mode(rl.BlendMode.BLEND_ALPHA_PREMULTIPLY)
  try:
    rl.draw_texture_pro(
      texture, rl.Rectangle(0, 0, texture_size, -texture_size),
      rl.Rectangle(x, y, HEADER_ICON_SIZE, HEADER_ICON_SIZE), rl.Vector2(0, 0), 0.0, rl.WHITE,
    )
  finally:
    rl.end_blend_mode()


class UnifiedSpeedWidget(LayoutWidget):
  TOUCH_SLOP = 20

  def __init__(self, hud_renderer):
    super().__init__("unified_speed", priority=1)
    self.hud_renderer = hud_renderer
    self._font_semi_bold = gui_app.font(FontWeight.SEMI_BOLD)
    self._font_bold = gui_app.font(FontWeight.BOLD)
    self._semi_bold_digit_center, _ = _digit_metrics(self._font_semi_bold)
    self._bold_digit_center, self._bold_digit_bottom = _digit_metrics(self._font_bold)
    self._unit_tops: dict[str, float] = {}
    self._slc_state: dict | None = None
    self._slc_enabled = False
    self._presentation: UnifiedSpeedPresentation | None = None
    self._show_max = False
    self._pedal_override = False
    self._snapshot_frame: int | None = None
    self._source_drawer = SpeedSourceDrawer()
    self.set_touch_event_valid_callback(lambda event: self.contains_pointer(event.pos))

  def collapse_sources(self) -> None:
    """Hide the visual drawer without changing the user's persistent preference."""
    self._source_drawer.reset()

  def hide_event(self) -> None:
    self.collapse_sources()
    super().hide_event()

  def _refresh_snapshot(self) -> None:
    frame = getattr(ui_state.sm, "frame", None)
    if frame is not None and frame == self._snapshot_frame:
      return
    self._snapshot_frame = frame
    self._slc_enabled = _is_slc_enabled()
    self._slc_state = _get_slc_state()
    self._show_max = (
      self.hud_renderer.is_cruise_available and
      not ui_state.starpilot_toggles.get("hide_max_speed", False)
    )
    self._pedal_override = (
      self.hud_renderer.is_cruise_set and ui_state.engaged and
      ui_state.sm.valid.get("carState", False) and ui_state.sm.alive.get("carState", False) and
      ui_state.sm.recv_frame["carState"] >= ui_state.started_frame and ui_state.sm["carState"].gasPressed
    )
    self._presentation = resolve_unified_speed(
      self._show_max, self.hud_renderer.is_cruise_set, self.hud_renderer.set_speed,
      self._slc_state, self._slc_enabled, ui_state.is_metric,
    )

  @property
  def is_visible(self) -> bool:
    self._refresh_snapshot()
    visible = self._show_max or self._presentation.mode != "max_only"
    if not visible:
      self.collapse_sources()
    return visible

  def get_size(self) -> tuple[float, float]:
    self._refresh_snapshot()
    height = UNIFIED_HEIGHT if self._presentation.mode in ("split", "merged") else SINGLE_HEIGHT
    return float(UNIFIED_WIDTH), float(height)

  @property
  def _card_hit_rect(self) -> rl.Rectangle:
    rect = self.rect
    return rl.Rectangle(
      rect.x, rect.y - self.TOUCH_SLOP,
      rect.width + self.TOUCH_SLOP, rect.height + 2 * self.TOUCH_SLOP,
    )

  @property
  def _hit_rect(self) -> rl.Rectangle:
    rect = self._card_hit_rect
    return rl.Rectangle(rect.x, rect.y, rect.width + self._source_drawer.width, rect.height)

  def contains_pointer(self, mouse_pos) -> bool:
    return (rl.check_collision_point_rec(mouse_pos, self._card_hit_rect) or
            (self._source_drawer.width > 0 and rl.check_collision_point_rec(mouse_pos, self._source_bounds())))

  def _source_bounds(self) -> rl.Rectangle:
    limit = self._speed_limit_bounds(self.rect) or self.rect
    return self._source_drawer.bounds(self.rect, limit.y)

  def _speed_limit_bounds(self, rect: rl.Rectangle) -> rl.Rectangle | None:
    mode = self._presentation.mode
    if mode in ("split", "merged"):
      return rl.Rectangle(rect.x, rect.y + MAX_ROW_HEIGHT, rect.width, rect.height - MAX_ROW_HEIGHT)
    if mode == "limit_only":
      return rect
    return None

  def _draw_centered_text(self, text: str, bounds: rl.Rectangle, y: float,
                          font_size: int, color: rl.Color, *, bold: bool = False) -> None:
    font = self._font_bold if bold else self._font_semi_bold
    text_size = measure_text_cached(font, text, font_size)
    text_x = bounds.x + (bounds.width - text_size.x) / 2
    rl.draw_text_ex(font, text, rl.Vector2(text_x, y), font_size, 0, color)

  def _draw_header(self, bounds: rl.Rectangle, text: str, icon_key: str | None, label_color: rl.Color) -> None:
    text = tr(text)
    font_size = HEADER_FONT_SIZE
    icon_width = HEADER_ICON_SIZE + 9 if icon_key else 0
    while font_size > 16 and measure_text_cached(self._font_semi_bold, text, font_size).x + icon_width > bounds.width - 24:
      font_size -= 1
    text_size = measure_text_cached(self._font_semi_bold, text, font_size)
    group_width = icon_width + text_size.x
    group_x = bounds.x + (bounds.width - group_width) / 2
    icon_y = bounds.y + 20
    if icon_key:
      _draw_header_icon(icon_key, group_x, icon_y)
    rl.draw_text_ex(
      self._font_semi_bold, text,
      rl.Vector2(group_x + icon_width, icon_y + (HEADER_ICON_SIZE - text_size.y) / 2),
      font_size, 0, label_color,
    )

  def _draw_posted_limit(self, bounds: rl.Rectangle, y: float, value_color: rl.Color,
                         offset_color: rl.Color, *, compact: bool = False) -> int:
    presentation = self._presentation
    size = OFFSET_FONT_SIZE if compact else VALUE_FONT_SIZE
    offset_font_size = OFFSET_FONT_SIZE if compact else INLINE_OFFSET_FONT_SIZE
    font = self._font_semi_bold if compact else self._font_bold
    offset = None if presentation.confirmation_pending else presentation.offset_text
    if offset is None:
      self._draw_centered_text(presentation.posted_speed_text, bounds, y, size, value_color, bold=not compact)
      return size

    value_size = measure_text_cached(font, presentation.posted_speed_text, size)
    offset_size = measure_text_cached(self._font_semi_bold, offset, offset_font_size)
    gap = 8
    available = bounds.width - 24 - gap - offset_size.x
    if value_size.x > available:
      size = max(OFFSET_FONT_SIZE, int(size * available / value_size.x))
      value_size = measure_text_cached(font, presentation.posted_speed_text, size)
    x = bounds.x + (bounds.width - value_size.x - gap - offset_size.x) / 2
    if not compact:
      # Favor the dominant numeral's center, with room for the complete adjustment.
      x = min(bounds.x + (bounds.width - value_size.x) / 2,
              bounds.x + bounds.width - 12 - value_size.x - gap - offset_size.x)
    self._draw_centered_text(
      presentation.posted_speed_text, rl.Rectangle(x, y, value_size.x, value_size.y), y, size, value_color, bold=not compact,
    )
    # Center the adjustment against the visible digits rather than the line box.
    digit_center = self._semi_bold_digit_center if compact else self._bold_digit_center
    offset_y = y + (size * digit_center - offset_font_size * self._semi_bold_digit_center) * FONT_SCALE
    self._draw_centered_text(
      offset, rl.Rectangle(x + value_size.x + gap, offset_y, offset_size.x, offset_size.y),
      offset_y, offset_font_size, offset_color,
    )
    return size

  def _unit_y(self, value_y: float, value_size: int) -> float:
    text = tr(self._presentation.unit_text)
    if text not in self._unit_tops:
      font = self._font_semi_bold
      self._unit_tops[text] = min(font.glyphs[rl.get_glyph_index(font, ord(char))].offsetY for char in text if not char.isspace()) / font.baseSize
    return value_y + value_size * FONT_SCALE * self._bold_digit_bottom + UNIT_GAP - UNIT_FONT_SIZE * FONT_SCALE * self._unit_tops[text]

  def _draw_unit(self, bounds: rl.Rectangle, y: float) -> None:
    text = tr(self._presentation.unit_text)
    color = COLORS.WHITE_TRANSLUCENT
    if self._pedal_override:
      text_size = measure_text_cached(self._font_semi_bold, text, UNIT_FONT_SIZE)
      text_shift = (PAUSE_ICON_WIDTH + PAUSE_ICON_GAP) / 2
      icon_x = bounds.x + (bounds.width - text_size.x) / 2 - text_shift
      icon_y = y + (text_size.y - PAUSE_ICON_HEIGHT) / 2
      bar_width = PAUSE_ICON_WIDTH / 3
      for x in (icon_x, icon_x + 2 * bar_width):
        rl.draw_rectangle_rec(rl.Rectangle(x, icon_y, bar_width, PAUSE_ICON_HEIGHT), PAUSE_COLOR)
      bounds = rl.Rectangle(bounds.x + text_shift, bounds.y, bounds.width, bounds.height)
      color = COLORS.DISENGAGED
    self._draw_centered_text(text, bounds, y, UNIT_FONT_SIZE, color)

  def _max_header_color(self, active_side: str, cruise_set: bool) -> rl.Color:
    if self._pedal_override:
      return COLORS.DISENGAGED
    if cruise_set and ui_state.status == UIStatus.ENGAGED and active_side in ("max", "shared"):
      return COLORS.ENGAGED
    if cruise_set and ui_state.status in (UIStatus.DISENGAGED, UIStatus.OVERRIDE):
      return COLORS.DISENGAGED
    return COLORS.GREY

  def _limit_header_color(self, active_side: str, overridden: bool) -> rl.Color:
    if self._pedal_override or overridden or ui_state.status in (UIStatus.DISENGAGED, UIStatus.OVERRIDE):
      return COLORS.DISENGAGED
    if ui_state.status == UIStatus.ENGAGED and active_side in ("slc", "shared"):
      return COLORS.ENGAGED
    return COLORS.GREY

  def _draw_active_emphasis(self, rect: rl.Rectangle) -> None:
    presentation = self._presentation
    if self._pedal_override or presentation.mode == "merged" or ui_state.status != UIStatus.ENGAGED or presentation.active_side == "none":
      return
    if presentation.mode in ("max_only", "limit_only"):
      bounds = rect
    elif presentation.active_side == "slc":
      bounds = self._speed_limit_bounds(rect)
    elif presentation.active_side == "max":
      bounds = rl.Rectangle(rect.x, rect.y, rect.width, MAX_ROW_HEIGHT)
    else:
      bounds = rect
    rl.draw_line_ex(
      rl.Vector2(bounds.x + 18, bounds.y + 65),
      rl.Vector2(bounds.x + bounds.width - 18, bounds.y + 65),
      3, UNIFIED_ACCENT,
    )

  def _draw_merged_separator(self, rect: rl.Rectangle) -> None:
    center = rect.y + rect.height / 2
    shelf_x = rect.x + 18
    valley_x = shelf_x + 12
    color = rl.Color(UNIFIED_ACCENT.r, UNIFIED_ACCENT.g, UNIFIED_ACCENT.b, 170)
    rl.draw_line_ex(rl.Vector2(shelf_x, rect.y + 76), rl.Vector2(shelf_x, center - 34), 2, color)
    rl.draw_spline_segment_bezier_cubic(
      rl.Vector2(shelf_x, center - 34), rl.Vector2(shelf_x, center - 19),
      rl.Vector2(valley_x, center - 23), rl.Vector2(valley_x, center - 7), 2, color,
    )
    rl.draw_line_ex(rl.Vector2(valley_x, center - 7), rl.Vector2(valley_x, center + 7), 2, color)
    rl.draw_spline_segment_bezier_cubic(
      rl.Vector2(valley_x, center + 7), rl.Vector2(valley_x, center + 23),
      rl.Vector2(shelf_x, center + 19), rl.Vector2(shelf_x, center + 34), 2, color,
    )
    rl.draw_line_ex(rl.Vector2(shelf_x, center + 34), rl.Vector2(shelf_x, rect.y + rect.height - MERGED_FOOTER_HEIGHT), 2, color)

  def _draw_speed_limit_border(self, rect: rl.Rectangle, limit: rl.Rectangle, color: rl.Color) -> None:
    # Clip the shared rounded outline so only the lower Speed Limit row changes.
    drawer = self._source_drawer
    if drawer.width > 0:
      rl.rl_draw_render_batch_active()
      rl.begin_scissor_mode(int(limit.x - 3), int(limit.y), math.ceil(limit.width + drawer.width + 6), int(limit.height + 4))
    else:
      rl.begin_scissor_mode(int(limit.x), int(limit.y), int(limit.width + 1), int(limit.height + 1))
    try:
      if drawer.width > 0:
        drawer.draw_border(rect, limit.y, 3, color)
      else:
        rl.draw_rectangle_rounded_lines_ex(rect, CONTROL_ROUNDNESS, CONTROL_SEGMENTS, 3, color)
    finally:
      rl.rl_draw_render_batch_active()
      rl.end_scissor_mode()
    if self._presentation.mode == "split":
      rl.draw_line_ex(rl.Vector2(rect.x + 8, limit.y), rl.Vector2(rect.x + rect.width - 8, limit.y), 3, color)

  def _render(self, rect: rl.Rectangle) -> None:
    presentation = self._presentation
    state = self._slc_state
    speed_color = COLORS.DISENGAGED if self._pedal_override else COLORS.WHITE
    limit_bounds = self._speed_limit_bounds(rect)
    drawer = self._source_drawer
    if state is None or presentation.confirmation_pending:
      drawer.reset()
    else:
      drawer.update(ui_state.ui_params.get_bool("SpeedLimitSources"), rl.get_time())
    if drawer.width > 0:
      drawer.draw_frame(rect, (limit_bounds or rect).y, CONTROL_BG, UNIFIED_ACCENT)
    else:
      rl.draw_rectangle_rounded_lines_ex(
        rect, CONTROL_ROUNDNESS, CONTROL_SEGMENTS, 7,
        rl.Color(UNIFIED_ACCENT.r, UNIFIED_ACCENT.g, UNIFIED_ACCENT.b, 55),
      )
      draw_control_card(rect, fill=CONTROL_BG, border=UNIFIED_ACCENT, border_width=2)
    if presentation.mode == "split":
      rl.draw_line_ex(
        rl.Vector2(rect.x + 8, limit_bounds.y), rl.Vector2(rect.x + rect.width - 8, limit_bounds.y),
        2, rl.Color(UNIFIED_ACCENT.r, UNIFIED_ACCENT.g, UNIFIED_ACCENT.b, 110),
      )
    elif presentation.mode == "merged":
      self._draw_merged_separator(rect)

    self._draw_active_emphasis(rect)
    max_bounds = rl.Rectangle(rect.x, rect.y, rect.width, MAX_ROW_HEIGHT) if presentation.mode in ("split", "merged") else rect
    if self._show_max or presentation.confirmation_pending:
      max_color = COLORS.DARK_GREY if not self.hud_renderer.is_cruise_set else speed_color
      max_label_color = self._max_header_color(presentation.active_side, self.hud_renderer.is_cruise_set)
      self._draw_header(max_bounds, "MAX SET", "speedometer", max_label_color)
      if presentation.mode != "merged":
        value_y = max_bounds.y + (60 if presentation.mode == "split" else 75)
        self._draw_centered_text(presentation.max_speed_text, max_bounds, value_y, VALUE_FONT_SIZE, max_color, bold=True)
        unit_y = max_bounds.y + max_bounds.height - 42 if presentation.mode == "split" else self._unit_y(value_y, VALUE_FONT_SIZE)
        self._draw_unit(max_bounds, unit_y)

    if limit_bounds is not None:
      icon_key = source_icon_key(presentation.source)
      overridden = bool(state and state['slc_overridden_speed'])
      label_color = self._limit_header_color(presentation.active_side, overridden)
      detail_color = COLORS.DISENGAGED if label_color == COLORS.DISENGAGED else COLORS.WHITE_TRANSLUCENT
      header_bounds = limit_bounds
      if presentation.mode == "merged":
        header_bounds = rl.Rectangle(limit_bounds.x, rect.y + rect.height - MERGED_FOOTER_HEIGHT, limit_bounds.width, MERGED_FOOTER_HEIGHT)
      self._draw_header(header_bounds, "SPEED LIMIT", icon_key, label_color)
      if presentation.mode != "merged":
        value_y = limit_bounds.y + 66
        value_size = self._draw_posted_limit(limit_bounds, value_y, speed_color, detail_color)
        if presentation.confirmation_pending:
          self._draw_centered_text(tr("PENDING"), limit_bounds, limit_bounds.y + 168, 25, CONFIRMATION_COLOR)
        unit_y = limit_bounds.y + limit_bounds.height - 42 if presentation.confirmation_pending else self._unit_y(value_y, value_size)
        self._draw_unit(limit_bounds, unit_y)

    if presentation.mode == "merged":
      # Leave a gutter for the vertical connector, then center the shared value and unit as a group.
      shared_bounds = rl.Rectangle(rect.x + 32, rect.y, rect.width - 32, rect.height)
      value_height = VALUE_FONT_SIZE * FONT_SCALE
      unit_height = UNIT_FONT_SIZE * FONT_SCALE
      value_y = rect.y + (rect.height - value_height - unit_height - 8) / 2
      self._draw_centered_text(presentation.effective_speed_text, shared_bounds, value_y, VALUE_FONT_SIZE, speed_color, bold=True)
      self._draw_unit(shared_bounds, value_y + value_height + 8)
      if presentation.offset_text is not None:
        self._draw_posted_limit(
          limit_bounds, rect.y + rect.height - OFFSET_FONT_SIZE * FONT_SCALE - 16, detail_color, detail_color, compact=True,
        )

    if presentation.confirmation_pending and limit_bounds is not None:
      intensity = (1.0 + math.sin(2.0 * math.pi * rl.get_time())) / 2.0
      alpha = round(100 + 155 * intensity)
      pulse = rl.Color(CONFIRMATION_COLOR.r, CONFIRMATION_COLOR.g, CONFIRMATION_COLOR.b, alpha)
      self._draw_speed_limit_border(rect, limit_bounds, pulse)
    else:
      if limit_bounds is not None and state is not None:
        vision_color = _speed_limit_pulse_color(UNIFIED_ACCENT, UNIFIED_ACCENT.a)
        if (vision_color.r, vision_color.g, vision_color.b) != (UNIFIED_ACCENT.r, UNIFIED_ACCENT.g, UNIFIED_ACCENT.b):
          self._draw_speed_limit_border(rect, limit_bounds, vision_color)
      if drawer.width > 0:
        drawer.draw_contents(state, rect, (limit_bounds or rect).y)

  def _handle_mouse_press(self, mouse_pos) -> None:
    limit = self._speed_limit_bounds(self.rect)
    if limit is None and self._slc_state is not None:
      # The detailed source panel remains dismissible when no limit is valid.
      limit = self.rect
    if limit is None:
      return
    # Extra touch padding must not turn a tap on Max into an SLC confirmation.
    top_slop = 0 if self._presentation.mode in ("split", "merged") else self.TOUCH_SLOP
    target = rl.Rectangle(limit.x, limit.y - top_slop,
                          limit.width + self.TOUCH_SLOP, limit.height + top_slop + self.TOUCH_SLOP)
    in_drawer = (not self._presentation.confirmation_pending and self._source_drawer.width > 0 and
                 rl.check_collision_point_rec(mouse_pos, self._source_bounds()))
    if not rl.check_collision_point_rec(mouse_pos, target) and not in_drawer:
      return
    if self._presentation.confirmation_pending:
      Params(memory=True).put_bool("SpeedLimitAccepted", True)
      return
    params = ui_state.ui_params
    params.put_bool("SpeedLimitSources", not params.get_bool("SpeedLimitSources"))
