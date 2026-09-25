"""Adapted large StarPilot onroad widgets with supplied observations.

Geometry and drawing order follow the frozen SetSpeedWidget, SpeedLimitWidget,
HudRenderer and ExpButton. See the adjacent UI LICENSE for retained source.
"""

from dataclasses import replace
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
from openpilot.starpilot.ui.speed_limit_pulse import SpeedLimitPulse
from openpilot.starpilot.ui import clip
from openpilot.starpilot.ui.speed_source_drawer import SpeedSourceDrawer
from openpilot.starpilot.ui.speed_card_typography import value_layout, source_header_layout
from openpilot.starpilot.ui.unified_speed_presentation import displayed_limit_mps, resolve_unified_speed


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
    self._pulse = SpeedLimitPulse()
    self._source_drawer = SpeedSourceDrawer()
    self._source_bounds = None
    self._source_session = None

  def collapse_sources(self):
    self._source_drawer.reset()
    self._source_bounds = None

  def source_bounds(self):
    return self._source_bounds

  def _draw_source_contents(self, panel, state):
    rows = [row for row in state.speed_limit.source_readings if row.enabled]
    if not rows:
      _center(self.fonts, 'No sources enabled', FontRole.SEMI_BOLD, 18, panel, panel.y + 30)
      return
    row_height = (panel.height - 24) / len(rows)
    active = state.speed_limit.accepted_source
    labels = {'dashboard': 'Dashboard', 'map': 'Map', 'vision': 'Vision', 'online': 'Online'}
    for index, row in enumerate(rows):
      role = FontRole.BOLD if row.source == active else FontRole.SEMI_BOLD
      color = rl.WHITE if row.source == active else rl.Color(170, 179, 174, 255)
      value = str(round(row.speed_mps * (3.6 if state.metric else 2.2369362921))) if row.kind == 'valid' and row.speed_mps is not None else '--'
      label = labels[row.source]
      size = 22
      value_width = self.fonts.measure(value, role, 24).width
      while size > 12 and self.fonts.measure(label, role, size).width > panel.width - 44 - value_width:
        size -= 1
      y = panel.y + 12 + index * row_height
      label_height = self.fonts.measure(label, role, size).height
      value_height = self.fonts.measure(value, role, 24).height
      self.fonts.draw(label, role, size, panel.x + 16, y + (row_height - label_height) / 2, color)
      self.fonts.draw(value, role, 24, panel.x + panel.width - 16 - value_width, y + (row_height - value_height) / 2, color)

  def render(self, content: rl.Rectangle, state: OnroadState) -> None:
    shown = resolve_unified_speed(state)
    if shown.mode == "hidden":
      self.collapse_sources()
      return
    dx, dy = offset(state.customization, "large", "cruise_limits")
    rect = rl.Rectangle(content.x + 58 + dx, content.y + 45 + dy, 176,
                        411 if shown.mode in ("split", "merged") else 215 if shown.mode == "limit_only" else 196)
    now = time.monotonic()
    observation = state.speed_limit
    posted = displayed_limit_mps(observation)
    pulse_state = (replace(state, speed_limit=replace(observation, speed_limit_mps=posted))
                   if posted is not None else state)
    self._pulse.update(pulse_state, now, visible=shown.mode != "max_only")
    fill = rl.Color(*rgba(state.customization, "cardFill", "large", "cruise_limits"))
    border = self._pulse.color(rl.Color(*rgba(state.customization, "cardBorder", "large", "cruise_limits")), now)
    text = rl.Color(*rgba(state.customization, "text", "large", "cruise_limits"))
    drawer = self._source_drawer
    session = state.speed_limit.session_id
    if session != self._source_session:
      self.collapse_sources()
      self._source_session = session
    drawer_top = rect.y + (196 if shown.mode in ('split', 'merged') else 0)
    if (state.speed_limit.kind != ObservationKind.VALID or not session or shown.pending or shown.mode == 'max_only'):
      self.collapse_sources()
    else:
      drawer.update(state.customization.get('speedSources', False), now)
    self._source_bounds = clip._intersection(drawer.bounds(rect, drawer_top), content) if drawer.width > 0 else None
    if drawer.width > 0:
      drawer.draw_frame(rect, drawer_top, fill, border)
    else:
      draw_control_card(rect, fill=fill, border=border)
    accent = rl.Color(188, 132, 255, 255)
    def fitted(text_value, role, size, y, color):
      width = self.fonts.measure(text_value, role, size).width
      if width > rect.width - 24:
        size = max(12, int(size * (rect.width - 24) / width))
      _center(self.fonts, text_value, role, size, rect, y, color)
      return size
    def value(value, adjustment, top, height, *, size=86, unit=True, unit_color=DISENGAGED, visible_top=None):
      layout = value_layout(value, adjustment, rect.width, height,
                            lambda text_value, font_size: self.fonts.measure(text_value, FontRole.BOLD, font_size).width,
                            lambda text_value, font_size: self.fonts.vertical_ink(text_value, FontRole.BOLD, font_size),
                            lambda text_value: self.fonts.measure(text_value, FontRole.SEMI_BOLD, 28).width,
                            lambda text_value: self.fonts.vertical_ink(text_value, FontRole.SEMI_BOLD, 28),
                            self.fonts.vertical_ink(shown.unit, FontRole.MEDIUM, 24), size=size, visible_top=visible_top)
      self.fonts.draw(value, FontRole.BOLD, layout.size, rect.x + layout.x, top + layout.y, text)
      if adjustment:
        self.fonts.draw(adjustment, FontRole.SEMI_BOLD, 28, rect.x + layout.offset_x, top + layout.offset_y, text)
      if unit:
        _center(self.fonts, shown.unit, FontRole.MEDIUM, 24, rect, top + layout.unit_y, unit_color)
    def row(label, number, top, height, active=False, source="", adjustment=None):
      color = accent if active else DISENGAGED
      label_size = fitted(label, FontRole.SEMI_BOLD, 17 if label == "MAX SET / LIMIT" else 29, top + 18, color)
      visible_top = None
      if source:
        source_size = 14
        source_width = self.fonts.measure(source.upper(), FontRole.SEMI_BOLD, source_size).width
        if source_width > rect.width - 24:
          source_size = max(12, int(source_size * (rect.width - 24) / source_width))
        source_y, visible_top = source_header_layout(
          self.fonts.vertical_ink(label, FontRole.SEMI_BOLD, label_size),
          self.fonts.vertical_ink(source.upper(), FontRole.SEMI_BOLD, source_size))
        _center(self.fonts, source.upper(), FontRole.SEMI_BOLD, source_size, rect, top + source_y, text)
      value(number, adjustment, top, height, unit_color=color, visible_top=visible_top)
    if shown.mode == "merged":
      row("MAX SET / LIMIT", shown.max_text, rect.y, 196, shown.active_side == "shared")
      fitted(shown.source.upper(), FontRole.SEMI_BOLD, 25, rect.y + 238, text)
      value(shown.posted_text, shown.offset_text, rect.y + 236, 175, size=48, unit=False)
    else:
      if shown.mode != "limit_only":
        row("MAX SET", shown.max_text, rect.y, 196, shown.active_side == "max")
      if shown.mode != "max_only":
        top = rect.y + (196 if shown.mode == "split" else 0)
        row("NEW LIMIT" if shown.pending else "LIMIT", shown.posted_text, top, 215,
            shown.active_side == "slc" or shown.pending, shown.source, shown.offset_text)
    if drawer.width > 0:
      drawer.draw_contents(lambda panel: self._draw_source_contents(panel, state), rect, drawer_top, content)


class CurrentSpeedHud:
  def __init__(self, fonts: BitmapFonts):
    self.fonts = fonts

  def render(self, content: rl.Rectangle, state: OnroadState) -> None:
    if state.speed_mps is None:
      return
    speed = str(round(state.speed_mps * (3.6 if state.metric else 2.2369362921)))
    dx, dy = offset(state.customization, "large", "current_speed")
    rect = rl.Rectangle(content.x + 610 + dx, content.y + dy, 580, 300)
    _center(self.fonts, speed, FontRole.BOLD, 176, rect, content.y + 42 + dy, rl.Color(*rgba(state.customization, "text", "large", "current_speed")))
    unit = "km/h" if state.metric else "mph"
    unit_height = self.fonts.measure(unit, FontRole.MEDIUM, 66).height
    red, green, blue, alpha = rgba(state.customization, "text", "large", "current_speed")
    _center(self.fonts, unit, FontRole.MEDIUM, 66, rect, 290 - unit_height / 2 + dy,
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
