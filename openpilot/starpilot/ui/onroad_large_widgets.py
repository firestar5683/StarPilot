"""Adapted large StarPilot onroad widgets with supplied observations.

Geometry and drawing order follow the frozen SetSpeedWidget, SpeedLimitWidget,
HudRenderer and ExpButton. See the adjacent UI LICENSE for retained source.
"""

from pathlib import Path
from typing import cast
import hashlib
import json

import pyray as rl

from openpilot.starpilot.ui.onroad_customization import offset, rgba, widget_size
from openpilot.starpilot.ui.onroad_state import ObservationKind, OnroadState
from openpilot.starpilot.ui.onroad_widget_style import draw_control_card
from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole
from openpilot.starpilot.ui.wheel_feedback import wheel_feedback_rgb
from openpilot.starpilot.ui.unified_speed_presentation import resolve_unified_speed


ENGAGED = rl.Color(128, 216, 166, 255)
DISENGAGED = rl.Color(145, 155, 149, 255)


def _center(fonts: BitmapFonts, text: str, role: FontRole, size: int, rect: rl.Rectangle, y: float,
            color: rl.Color = rl.WHITE) -> None:
  measured = fonts.measure(text, role, size)
  fonts.draw(text, role, size, rect.x + (rect.width - measured.width) / 2, y, color)


class UnifiedSpeedWidget:
  """One vertical MAX SET/sign card; actions remain decision-bound by the host."""

  def __init__(self, fonts: BitmapFonts):
    self.fonts = fonts

  def _draw_sources(self, rect, state):
    """Each enabled source as a small label over its reading; the accepted source is highlighted."""
    from openpilot.starpilot.ui.large_speed_geometry import PADDING
    rows = [row for row in state.speed_limit.source_readings if row.enabled]
    if not rows:
      _center(self.fonts, 'No sources enabled', FontRole.NORMAL, 26, rect, rect.y + 22)
      return
    active = state.speed_limit.accepted_source
    labels = {'dashboard': 'Dash', 'map': 'Map', 'vision': 'Vision', 'online': 'Online'}
    cell = (rect.width - 2 * PADDING) / len(rows)
    for index, row in enumerate(rows):
      color = rl.WHITE if row.source == active else rl.Color(170, 179, 174, 255)
      value = str(round(row.speed_mps * (3.6 if state.metric else 2.2369362921))) if row.kind == 'valid' and row.speed_mps is not None else '–'
      box = rl.Rectangle(rect.x + PADDING + index * cell, rect.y, cell, rect.height)
      size = 22
      while size > 12 and self.fonts.measure(labels[row.source], FontRole.NORMAL, size).width > cell - 4:
        size -= 1
      _center(self.fonts, labels[row.source], FontRole.NORMAL, size, box, rect.y + 10, color)
      _center(self.fonts, value, FontRole.MEDIUM if row.source == active else FontRole.NORMAL, 30, box, rect.y + 36, color)

  def render(self, content: rl.Rectangle, state: OnroadState) -> None:
    from openpilot.starpilot.ui.large_speed_geometry import GAP, WIDTH, MAX_ROW_HEIGHT, LIMIT_ROW_HEIGHT, PADDING, SOURCE_ROW_HEIGHT, card_height
    from openpilot.starpilot.ui.onroad_customization import placement
    shown = resolve_unified_speed(state)
    if shown.mode == 'hidden':
      return
    saved = placement(state.customization, 'large', 'cruise_limits')
    height = card_height(shown.mode)
    rect = rl.Rectangle(saved['x'], saved['y'], WIDTH, height)
    # Sources follow the Galaxy layout setting: a row in this card, or a small card of its own right below.
    sources = (state.customization.get('speedSources') is True and shown.mode != 'max_only' and
               state.speed_limit.kind == ObservationKind.VALID and bool(state.speed_limit.session_id))
    separate = state.customization.get('speedSourcesCard') is True
    if sources and not separate:
      rect.height += SOURCE_ROW_HEIGHT
    fill = rl.Color(*rgba(state.customization, 'cardFill', 'large', 'cruise_limits'))
    border = rl.Color(*rgba(state.customization, 'cardBorder', 'large', 'cruise_limits'))
    text = rl.Color(*rgba(state.customization, 'text', 'large', 'cruise_limits'))
    muted, accent = rl.Color(172, 190, 203, 255), rl.Color(197, 163, 255, 255)
    draw_control_card(rect, fill=fill, border=border, border_width=1, roundness=.09)

    align = state.customization.get('speedAlign', 'left')

    def start(ink_left, ink_right):
      # Align visible glyphs so the digits' side bearings do not offset them from the labels.
      if align == 'right':
        return rect.x + WIDTH - PADDING - ink_right
      if align != 'center':
        return rect.x + PADDING - ink_left
      return rect.x + WIDTH / 2 - (ink_left + ink_right) / 2

    def label(value, y, size=32, color=muted, role=FontRole.MEDIUM):
      while size > 20 and self.fonts.measure(value, role, size).width > WIDTH - 2 * PADDING:
        size -= 1
      ink_top, _ = self.fonts.vertical_ink(value, role, size)
      self.fonts.draw(value, role, size, start(*self.fonts.horizontal_ink(value, role, size)), y - ink_top, color)

    def row(title, value, top, footer, status='', active=False, footer_color=muted, footer_y=174, height=MAX_ROW_HEIGHT):
      has_value = value != '–'
      size, unit_size = 112, 28

      def fit_size(val, role, max_size, min_size=20):
        sz = max_size
        while sz > min_size and self.fonts.measure(val, role, sz).width > WIDTH - 2 * PADDING:
          sz -= 1
        return sz

      title_size = fit_size(title, FontRole.MEDIUM, 32)
      title_ink = self.fonts.horizontal_ink(title, FontRole.MEDIUM, title_size)
      title_v = self.fonts.vertical_ink(title, FontRole.MEDIUM, title_size)
      title_h = title_v[1] - title_v[0]

      number_ink = self.fonts.horizontal_ink(value, FontRole.SPEED, size)
      unit_ink = self.fonts.horizontal_ink(shown.unit, FontRole.NORMAL, unit_size) if has_value else (0, 0)
      extra = unit_ink[1] - unit_ink[0] + 14 if has_value and align != 'center' else 0
      while size > 72 and number_ink[1] - number_ink[0] + extra > WIDTH - PADDING * 2:
        size -= 1
        number_ink = self.fonts.horizontal_ink(value, FontRole.SPEED, size)
      number_v = self.fonts.vertical_ink(value, FontRole.SPEED, size)
      number_h = number_v[1] - number_v[0]

      if not has_value:
        digit_v = self.fonts.vertical_ink('0', FontRole.SPEED, size)
        dash_offset = ((digit_v[1] - digit_v[0]) - number_h) / 2
        effective_number_h = digit_v[1] - digit_v[0]
      else:
        dash_offset = 0
        effective_number_h = number_h

      if has_value:
        unit_v = self.fonts.vertical_ink(shown.unit, FontRole.NORMAL, unit_size)
        unit_h = unit_v[1] - unit_v[0]
      else:
        unit_v, unit_h = None, 0

      status_size = fit_size(status, FontRole.NORMAL, 30) if status else 30
      status_ink = self.fonts.horizontal_ink(status, FontRole.NORMAL, status_size) if status else None
      status_v = self.fonts.vertical_ink(status, FontRole.NORMAL, status_size) if status else None
      status_h = (cast(tuple[float, float], status_v)[1] - cast(tuple[float, float], status_v)[0]) if status else 0

      footer_size = fit_size(footer, FontRole.NORMAL, 30) if footer else 30
      footer_ink = self.fonts.horizontal_ink(footer, FontRole.NORMAL, footer_size) if footer else None
      footer_v = self.fonts.vertical_ink(footer, FontRole.NORMAL, footer_size) if footer else None
      footer_h = (cast(tuple[float, float], footer_v)[1] - cast(tuple[float, float], footer_v)[0]) if footer else 0

      if align == 'center':
        # Every line shares the card's horizontal center, and the entire stack is visually vertically centered.
        segments = []
        segments.append((
          title_v[0], title_h,
          lambda y: self.fonts.draw(title, FontRole.MEDIUM, title_size, start(*title_ink), y - title_v[0], accent if active else muted)
        ))
        segments.append((
          number_v[0], effective_number_h,
          lambda y: self.fonts.draw(value, FontRole.SPEED, size, start(*number_ink), y - number_v[0] + dash_offset, text)
        ))
        if has_value:
          unit_v = cast(tuple[float, float], unit_v)
          segments.append((
            unit_v[0], unit_h,
            lambda y: self.fonts.draw(shown.unit, FontRole.NORMAL, unit_size, start(*unit_ink), y - unit_v[0], muted)
          ))
        if status:
          status_ink = cast(tuple[float, float], status_ink)
          status_v = cast(tuple[float, float], status_v)
          segments.append((
            status_v[0], status_h,
            lambda y: self.fonts.draw(status, FontRole.NORMAL, status_size, start(*status_ink), y - status_v[0], accent if active else muted)
          ))
        if footer:
          footer_ink = cast(tuple[float, float], footer_ink)
          footer_v = cast(tuple[float, float], footer_v)
          segments.append((
            footer_v[0], footer_h,
            lambda y: self.fonts.draw(footer, FontRole.NORMAL, footer_size, start(*footer_ink), y - footer_v[0], footer_color)
          ))

        num_items = len(segments)
        gap = 8 if num_items >= 5 else 10 if num_items == 4 and height > 210 else 8 if num_items == 4 else 14
        total_ink_height = sum(seg[1] for seg in segments)
        total_content_height = total_ink_height + (num_items - 1) * gap
        margin = max(PADDING / 2, (height - total_content_height) / 2)

        curr_y = top + margin
        for _, seg_h, draw_fn in segments:
          draw_fn(curr_y)
          curr_y += seg_h + gap
      else:
        # Left and right alignments anchor against card padding; number and unit are inline on the baseline.
        label(title, top + 24, color=accent if active else muted)
        number_y = top + 72 - number_v[0] + dash_offset
        left = start(*number_ink)
        self.fonts.draw(value, FontRole.SPEED, size, left, number_y, text)
        if has_value:
          unit_v = cast(tuple[float, float], unit_v)
          unit_x = left + number_ink[0] - 14 - unit_ink[1] if align == 'right' else left + number_ink[1] + 14 - unit_ink[0]
          unit_y = number_y + number_v[1] - unit_v[1]
          self.fonts.draw(shown.unit, FontRole.NORMAL, unit_size, unit_x, unit_y, muted)
        if status:
          label(status, top + 174, size=30, role=FontRole.NORMAL, color=accent if active else muted)
        label(footer, top + footer_y, size=30, role=FontRole.NORMAL, color=footer_color)

    if shown.mode != 'limit_only':
      max_active = shown.active_side in ('max', 'shared') and shown.max_text != '–'
      row('MAX SET', shown.max_text, rect.y, shown.max_status,
          active=max_active, footer_color=accent if max_active else muted, height=MAX_ROW_HEIGHT)
    if shown.mode != 'max_only':
      top = rect.y + (MAX_ROW_HEIGHT if shown.mode == 'split' else 0)
      if shown.mode == 'split':
        rl.draw_line_ex(rl.Vector2(rect.x + 1, top), rl.Vector2(rect.x + WIDTH - 1, top), 1, border)
      road_limit = f'Road limit {shown.posted_text}'
      if shown.offset_text:
        road_limit += f' {shown.offset_text}'
      row('SLC LIMIT', shown.limit_text, top, road_limit, shown.limit_status,
          active=shown.active_side in ('slc', 'shared'), footer_y=224, height=LIMIT_ROW_HEIGHT)
    if sources:
      row = rl.Rectangle(rect.x, rect.y + height + (GAP if separate else 0), WIDTH, SOURCE_ROW_HEIGHT)
      if separate:
        draw_control_card(row, fill=fill, border=border, border_width=1, roundness=.2)
      else:
        rl.draw_line_ex(rl.Vector2(rect.x + 1, row.y), rl.Vector2(rect.x + WIDTH - 1, row.y), 1, border)
      self._draw_sources(row, state)


class CurrentSpeedHud:
  def __init__(self, fonts: BitmapFonts):
    self.fonts = fonts

  def render(self, content: rl.Rectangle, state: OnroadState) -> None:
    if state.speed_mps is None:
      return
    speed = str(round(state.speed_mps * (3.6 if state.metric else 2.2369362921)))
    dx, dy = offset(state.customization, "large", "current_speed")
    rect = rl.Rectangle(content.x + 610 + dx, content.y + dy, 580, 300)
    number_top, _ = self.fonts.vertical_ink(speed, FontRole.SPEED, 176)
    old_top, old_bottom = self.fonts.vertical_ink(speed, FontRole.BOLD, 176)
    _center(self.fonts, speed, FontRole.SPEED, 176, rect, content.y + 42 + dy + old_top - number_top,
            rl.Color(*rgba(state.customization, 'text', 'large', 'current_speed')))
    unit = 'km/h' if state.metric else 'mph'
    unit_top, _ = self.fonts.vertical_ink(unit, FontRole.NORMAL, 44)
    red, green, blue, alpha = rgba(state.customization, 'text', 'large', 'current_speed')
    _center(self.fonts, unit, FontRole.NORMAL, 44, rect, content.y + 42 + dy + old_bottom + 20 - unit_top,
            rl.Color(red, green, blue, int(alpha * 200 / 255)))



class SteeringWheelWidget:
  """Frozen ExpButton shape; clicks are handled by the separate request input."""

  def __init__(self, asset_directory: Path):
    self.asset_directory = asset_directory
    self._texture: rl.Texture | None = None

  def prepare(self) -> None:
    if self._texture is not None:
      return
    path = self.asset_directory / "icons/chffr_wheel.png"
    entry = json.loads(Path(__file__).with_name("onroad-assets.json").read_text())["files"][0]
    data = path.read_bytes()
    if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
      raise ValueError("Unreviewed steering wheel art")
    image = rl.load_image(str(path))
    try:
      if image.data == rl.ffi.NULL:
        raise RuntimeError("Unable to load steering wheel art")
      rl.image_resize(image, 144, 144)
      texture = rl.load_texture_from_image(image)
      if not texture.id:
        raise RuntimeError("Unable to create steering wheel texture")
      self._texture = texture
    finally:
      if image.data != rl.ffi.NULL:
        rl.unload_image(image)

  def render(self, content: rl.Rectangle, state: OnroadState) -> None:
    if self._texture is None:
      self.prepare()
    dx, dy = offset(state.customization, "large", "steering_wheel")
    x = content.x + content.width - 146 - 96 + dx
    y = content.y + 45 + dy
    size, _ = widget_size(state.customization, "large", "steering_wheel")
    radius = size / 2
    rl.draw_circle(int(x + radius), int(y + radius), radius, rl.Color(*rgba(state.customization, "cardFill", "large", "steering_wheel")))
    border = rl.Color(*rgba(state.customization, "cardBorder", "large", "steering_wheel"))
    if border.a:
      rl.draw_ring(rl.Vector2(x + radius, y + radius), radius - 3, radius, 0, 360, 64, border)
    feedback = wheel_feedback_rgb(state.wheel_feedback, state.appearance.wheel_pedal_feedback)
    color = rl.Color(*feedback, 255) if feedback is not None else rl.WHITE
    rl.draw_texture_pro(self._texture, rl.Rectangle(0, 0, 144, 144),
                        rl.Rectangle(x + size / 8, y + size / 8, size * .75, size * .75),
                        rl.Vector2(0, 0), 0, color)

  def close(self) -> None:
    if self._texture is not None and rl.is_window_ready():
      rl.unload_texture(self._texture)
    self._texture = None
