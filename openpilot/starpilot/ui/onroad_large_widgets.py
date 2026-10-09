"""Adapted large StarPilot onroad widgets with supplied observations.

Geometry and drawing order follow the frozen SetSpeedWidget, SpeedLimitWidget,
HudRenderer and ExpButton. See the adjacent UI LICENSE for retained source.
"""

from pathlib import Path
import hashlib
import json
import time

import pyray as rl

from openpilot.starpilot.ui.onroad_customization import offset, rgba, widget_size
from openpilot.starpilot.ui.onroad_state import ObservationKind, OnroadState
from openpilot.starpilot.ui.onroad_widget_style import draw_control_card
from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole
from openpilot.starpilot.ui.wheel_feedback import wheel_feedback_rgb
from openpilot.starpilot.ui.speed_source_drawer import SpeedSourceDrawer
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
    self._source_drawer = SpeedSourceDrawer()
    self._source_session = None

  def collapse_sources(self):
    self._source_drawer.reset()

  def _draw_source_contents(self, panel, state):
    rows = [row for row in state.speed_limit.source_readings if row.enabled]
    if not rows:
      _center(self.fonts, 'No sources enabled', FontRole.NORMAL, 28, panel, panel.y + 30)
      return
    row_height = (panel.height - 32) / len(rows)
    active = state.speed_limit.accepted_source
    labels = {'dashboard': 'Dashboard', 'map': 'Map', 'vision': 'Vision', 'online': 'Online'}
    for index, row in enumerate(rows):
      role = FontRole.MEDIUM if row.source == active else FontRole.NORMAL
      color = rl.WHITE if row.source == active else rl.Color(170, 179, 174, 255)
      value = str(round(row.speed_mps * (3.6 if state.metric else 2.2369362921))) if row.kind == 'valid' and row.speed_mps is not None else '–'
      label = labels[row.source]
      size = 28
      value_width = self.fonts.measure(value, role, 30).width
      while size > 12 and self.fonts.measure(label, role, size).width > panel.width - 64 - value_width:
        size -= 1
      y = panel.y + 16 + index * row_height
      label_height = self.fonts.measure(label, role, size).height
      value_height = self.fonts.measure(value, role, 30).height
      self.fonts.draw(label, role, size, panel.x + 32, y + (row_height - label_height) / 2, color)
      self.fonts.draw(value, role, 30, panel.x + panel.width - 32 - value_width, y + (row_height - value_height) / 2, color)

  def render(self, content: rl.Rectangle, state: OnroadState) -> None:
    from openpilot.starpilot.ui.large_speed_geometry import (WIDTH, MAX_ROW_HEIGHT, PADDING, SOURCE_ROW_HEIGHT,
                                                           card_height, source_toggle_bounds, source_panel_bounds)
    from openpilot.starpilot.ui.onroad_customization import placement
    shown = resolve_unified_speed(state)
    if shown.mode == 'hidden':
      self.collapse_sources()
      return
    saved = placement(state.customization, 'large', 'cruise_limits')
    rect = rl.Rectangle(saved['x'], saved['y'], WIDTH, card_height(shown.mode))
    fill = rl.Color(*rgba(state.customization, 'cardFill', 'large', 'cruise_limits'))
    border = rl.Color(*rgba(state.customization, 'cardBorder', 'large', 'cruise_limits'))
    text = rl.Color(*rgba(state.customization, 'text', 'large', 'cruise_limits'))
    muted, accent = rl.Color(172, 190, 203, 255), rl.Color(197, 163, 255, 255)
    draw_control_card(rect, fill=fill, border=border, border_width=1, roundness=.09)

    def label(value, x, y, size=32, color=muted, role=FontRole.MEDIUM):
      while size > 20 and self.fonts.measure(value, role, size).width > WIDTH - 2 * PADDING:
        size -= 1
      ink_top, _ = self.fonts.vertical_ink(value, role, size)
      self.fonts.draw(value, role, size, x, y - ink_top, color)

    def row(title, value, top, footer, status='', active=False, footer_color=muted, footer_y=174):
      left = rect.x + PADDING
      label(title, left, top + 24, color=accent if active else muted)
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
      self.fonts.draw(value, FontRole.SPEED, size, left, number_y, text)
      if has_value:
        _, unit_bottom = self.fonts.vertical_ink(shown.unit, FontRole.NORMAL, unit_size)
        self.fonts.draw(shown.unit, FontRole.NORMAL, unit_size, left + number_width + 14,
                        top + 72 + number_bottom - number_top - unit_bottom, muted)
      if status:
        label(status, left, top + 174, size=30, role=FontRole.NORMAL, color=accent if active else muted)
      label(footer, left, top + footer_y, size=30, role=FontRole.NORMAL, color=footer_color)

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
    session = state.speed_limit.session_id
    if session != self._source_session:
      self.collapse_sources()
      self._source_session = session
    available = state.speed_limit.kind == ObservationKind.VALID and bool(session) and shown.mode != 'max_only'
    if not available:
      self.collapse_sources()
      return
    now = time.monotonic()
    self._source_drawer.update(state.customization.get('speedSources', False), now)
    left, top, right, bottom = source_toggle_bounds(state)
    if getattr(self, 'source_pressed', lambda: False)():
      rl.draw_rectangle_rounded(rl.Rectangle(left, top, right - left, bottom - top), .15, 8, rl.Color(197, 163, 255, 35))
    label('Hide sources' if state.customization.get('speedSources', False) else 'View sources', left + PADDING, top + 11,
          size=30, role=FontRole.NORMAL)
    if self._source_drawer.progress <= 0:
      return
    rows = sum(row.enabled for row in state.speed_limit.source_readings)
    height = max(1, rows) * SOURCE_ROW_HEIGHT + PADDING
    panel_bounds = source_panel_bounds(state, height, content)
    if panel_bounds is None:
      self.collapse_sources()
      return
    panel = rl.Rectangle(*panel_bounds)
    self._source_drawer.draw_panel(panel, content, fill, border,
                                                       lambda panel: self._draw_source_contents(panel, state))


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
