"""Adapted large StarPilot onroad widgets with supplied observations.

Geometry and drawing order follow the frozen SetSpeedWidget, SpeedLimitWidget,
HudRenderer and ExpButton. See the adjacent UI LICENSE for retained source.
"""

from pathlib import Path
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
    from openpilot.starpilot.ui.large_speed_geometry import GAP, WIDTH, MAX_ROW_HEIGHT, PADDING, SOURCE_ROW_HEIGHT, card_height
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

    def start(width):
      # Text sits left (the default), centred, or right within the card's padding.
      return (rect.x + (WIDTH - width) / 2 if align == 'center' else
              rect.x + WIDTH - PADDING - width if align == 'right' else rect.x + PADDING)

    def label(value, y, size=32, color=muted, role=FontRole.MEDIUM):
      while size > 20 and self.fonts.measure(value, role, size).width > WIDTH - 2 * PADDING:
        size -= 1
      ink_top, _ = self.fonts.vertical_ink(value, role, size)
      self.fonts.draw(value, role, size, start(self.fonts.measure(value, role, size).width), y - ink_top, color)

    def row(title, value, top, footer, status='', active=False, footer_color=muted, footer_y=174):
      label(title, top + 24, color=accent if active else muted)
      size, unit_size = 112, 28
      has_value = value != '–'
      unit_width = self.fonts.measure(shown.unit, FontRole.NORMAL, unit_size).width if has_value else 0
      while size > 72 and self.fonts.measure(value, FontRole.SPEED, size).width + unit_width + 14 > WIDTH - PADDING * 2:
        size -= 1
      number_width = self.fonts.measure(value, FontRole.SPEED, size).width
      number_top, number_bottom = self.fonts.vertical_ink(value, FontRole.SPEED, size)
      number_y = top + 72 - number_top
      if not has_value:
        digit_top, digit_bottom = self.fonts.vertical_ink('0', FontRole.SPEED, size)
        number_y += ((digit_bottom - digit_top) - (number_bottom - number_top)) / 2
      left = start(number_width + (14 + unit_width if has_value else 0))
      self.fonts.draw(value, FontRole.SPEED, size, left, number_y, text)
      if has_value:
        _, unit_bottom = self.fonts.vertical_ink(shown.unit, FontRole.NORMAL, unit_size)
        self.fonts.draw(shown.unit, FontRole.NORMAL, unit_size, left + number_width + 14,
                        top + 72 + number_bottom - number_top - unit_bottom, muted)
      if status:
        label(status, top + 174, size=30, role=FontRole.NORMAL, color=accent if active else muted)
      label(footer, top + footer_y, size=30, role=FontRole.NORMAL, color=footer_color)

    if shown.mode != 'limit_only':
      max_active = shown.active_side in ('max', 'shared') and shown.max_text != '–'
      row('MAX SET', shown.max_text, rect.y, shown.max_status,
          active=max_active, footer_color=accent if max_active else muted)
    if shown.mode != 'max_only':
      top = rect.y + (MAX_ROW_HEIGHT if shown.mode == 'split' else 0)
      if shown.mode == 'split':
        rl.draw_line_ex(rl.Vector2(rect.x + 1, top), rl.Vector2(rect.x + WIDTH - 1, top), 1, border)
      road_limit = f'Road limit {shown.posted_text}'
      if shown.offset_text:
        road_limit += f' {shown.offset_text}'
      row('SLC LIMIT', shown.limit_text, top, road_limit, shown.limit_status,
          active=shown.active_side in ('slc', 'shared'), footer_y=224)
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
