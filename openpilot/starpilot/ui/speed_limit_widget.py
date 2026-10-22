"""The latest limit, its attention animation and override mark on both screens."""

import time

import pyray as rl

from openpilot.starpilot.ui.large_speed_geometry import LARGE_SIGN_SCALE
from openpilot.starpilot.ui.onroad_state import OnroadState, speed_limit_bounds
from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile
from openpilot.starpilot.ui.speed_limit_pulse import SpeedLimitPulse
from openpilot.starpilot.ui.speed_limit_shapes import SpeedLimitShapes
from openpilot.starpilot.ui.unified_speed_presentation import displayed_adjusted_limit_mps, resolve_unified_speed


INK = rl.Color(241, 246, 243, 255)
MUTED = rl.Color(190, 208, 202, 255)


def draw_text(fonts, text, role, size, x, y, color=INK):
  if isinstance(color, (tuple, list)):
    color = rl.Color(*color)
  radius = 1.15 if fonts.profile == Profile.LARGE else 1.
  contour = rl.Color(6, 14, 10, round(color.a * .90))
  for dx, dy in ((-radius, 0), (radius, 0), (0, -radius), (0, radius)):
    fonts.draw(text, role, size, x + dx, y + dy, contour)
  fonts.draw(text, role, size, x, y + (1.5 if fonts.profile == Profile.LARGE else 1.2),
             rl.Color(7, 16, 12, round(color.a * .32)))
  fonts.draw(text, role, size, x, y, color)


def draw_line(profile, start, end, stroke, color):
  radius = 1.4 if profile == Profile.LARGE else 1.
  rl.draw_line_ex(start, end, stroke + 2 * radius, rl.Color(6, 14, 10, round(color.a * .87)))
  rl.draw_line_ex(start, end, stroke, color)


def draw_ink(fonts, text, role, size, x, top, color=INK):
  ink_top, ink_bottom = fonts.vertical_ink(text, role, size)
  draw_text(fonts, text, role, size, x, top - ink_top, color)
  return fonts.measure(text, role, size).width, ink_bottom - ink_top


def draw_caption(fonts, label, x, top, color=MUTED, *, unit=None):
  large = fonts.profile == Profile.LARGE
  width, height = draw_ink(fonts, label, FontRole.MEDIUM, 32 if large else 24, x, top, color)
  if unit:
    size = 28 if large else 20
    unit_top, _ = fonts.vertical_ink(unit, FontRole.NORMAL, size)
    # Exclude the p descender when aligning mph to the caption baseline.
    _, baseline = fonts.vertical_ink('mh' if unit == 'mph' else unit, FontRole.NORMAL, size)
    gap = 12 if large else 8
    unit_width, _ = draw_ink(fonts, unit, FontRole.NORMAL, size, x + width + gap,
                             top + height - (baseline - unit_top), color)
    width += gap + unit_width
  return width, height


class SpeedLimitWidget:
  def __init__(self, fonts: BitmapFonts, profile: Profile):
    self.fonts = fonts
    self.profile = profile
    self.scale = LARGE_SIGN_SCALE if profile == Profile.LARGE else 1
    self.text_scale = self.scale * Profile.COMPACT.font_scale / profile.font_scale
    self.pulse = SpeedLimitPulse()
    self.shapes = SpeedLimitShapes(self.scale, headless_context=getattr(fonts, '_headless_context', False))

  def close(self):
    self.shapes.close()

  def render(self, state: OnroadState) -> None:
    bounds = speed_limit_bounds(self.profile, state)
    now = state.observed_ns / 1e9 if state.observed_ns else time.monotonic()
    self.pulse.update(state, now, visible=bounds is not None)
    if bounds is None:
      return
    self._sign(state, bounds, now)

  def _sign(self, state: OnroadState, bounds, now: float) -> None:
    shown, obs = resolve_unified_speed(state), state.speed_limit
    x, top = bounds[0] + 12, bounds[1] + 12
    scale = self.scale
    pending = shown.pending and not obs.automatic_adoption_pending
    target = displayed_adjusted_limit_mps(obs) if pending else None
    arrow_direction = 0
    if target is not None and state.speed_mps is not None and target != state.speed_mps:
      arrow_direction = -1 if target > state.speed_mps else 1
    white = self.pulse.color(rl.Color(244, 247, 245, 255), now)
    secondary = self.pulse.color(rl.Color(223, 232, 227, 255), now)

    def ink(text, role, size):
      return (*self.fonts.horizontal_ink(text, role, size * self.text_scale),
              *self.fonts.vertical_ink(text, role, size * self.text_scale))

    def centered(text, role, size, ink_top, color, center_x=x + 59 * scale):
      left, right, a, b = ink(text, role, size)
      origin = center_x - (left + right) / 2
      self.fonts.draw(text, role, size * self.text_scale, origin, ink_top - a, color)
      return origin + left, ink_top, origin + right, ink_top + b - a

    if self.profile == Profile.COMPACT and state.appearance.use_vienna_sign and not shown.offset_text:
      cx, cy = x + 59, top + 67
      rl.draw_circle(int(cx), int(cy), 59, rl.WHITE)
      rl.draw_ring(rl.Vector2(cx, cy), 47, 59, 0, 360, 64, self.pulse.color(rl.Color(201, 34, 49, 255), now))
      color = self.pulse.color(rl.BLACK, now)
      size = 58 if len(shown.posted_text) <= 2 else 48
      measured = self.fonts.measure(shown.posted_text, FontRole.BOLD, size)
      origin, number_top = cx - measured.width / 2, cy - measured.height / 2
      self.fonts.draw(shown.posted_text, FontRole.BOLD, size, origin, number_top, color)
      number = origin, number_top, origin + measured.width, number_top + measured.height
    elif state.appearance.use_vienna_sign:
      cx, cy = x + 59 * scale, top + 67 * scale
      self.shapes.circle(cx, cy, self.pulse.color(rl.Color(201, 34, 49, 255), now))
      # Keep black-on-white numerals stable; the ring carries manual confirmation pulses.
      color = rl.Color(0, 0, 0, 255) if pending else self.pulse.color(rl.Color(0, 0, 0, 255), now)
      size = (54 if pending else 58) if len(shown.posted_text) <= 2 else 48
      number_center = cy - 7 * scale if shown.offset_text else cy + (7 * scale if pending else 0)
      while True:
        left, right, a, b = ink(shown.posted_text, FontRole.BOLD, size)
        if ((right - left) / 2) ** 2 + (abs(number_center - cy) + (b - a) / 2) ** 2 <= (47 * scale) ** 2 or size <= 32:
          break
        size -= 2
      number_top = number_center - (b - a) / 2
      number = centered(shown.posted_text, FontRole.BOLD, size, number_top, color)
      if shown.offset_text:
        offset_top, size = number[3] + 4 * scale, 36
        while True:
          left, right, a, b = ink(shown.offset_text, FontRole.MEDIUM, size)
          if ((right - left) / 2) ** 2 + max((offset_top - cy) ** 2, (offset_top + b - a - cy) ** 2) <= (47 * scale) ** 2 or size <= 24:
            break
          size -= 2
        centered(shown.offset_text, FontRole.MEDIUM, size, offset_top, color)
    else:
      if self.profile == Profile.COMPACT:
        rect = rl.Rectangle(x + 2, top, 116, 132 + (44 if shown.offset_text else 0))
        rl.draw_rectangle_rounded_lines_ex(rl.Rectangle(rect.x + 8, rect.y + 8, rect.width - 16, rect.height - 16),
                                         .14, 16, 2, white)
        for label, size, label_top, role in (('SPEED', 20, 18, FontRole.SEMI_BOLD),
                                              ('LIMIT', 20, 36, FontRole.SEMI_BOLD),
                                              (shown.posted_text, 50 if len(shown.posted_text) <= 2 else 42, 66, FontRole.BOLD)):
          measured = self.fonts.measure(label, role, size)
          origin = rect.x + (rect.width - measured.width) / 2
          self.fonts.draw(label, role, size, origin, rect.y + label_top, white)
          if label == shown.posted_text:
            number = origin, rect.y + label_top, origin + measured.width, rect.y + label_top + measured.height
        if shown.offset_text:
          measured = self.fonts.measure(shown.offset_text, FontRole.MEDIUM, 30)
          self.fonts.draw(shown.offset_text, FontRole.MEDIUM, 30, rect.x + (rect.width - measured.width) / 2,
                          rect.y + 118, secondary)
      else:
        rect = rl.Rectangle(x + 2 * scale, top + 2 * scale, 114 * scale, 128 * scale)
        rl.draw_rectangle_rounded(rect, .1, 16, rl.Color(10, 17, 19, 230))
        rl.draw_rectangle_rounded_lines_ex(rect, .1, 16, 2 * scale, white)
        for label, y in (('SPEED', top + 11 * scale), ('LIMIT', top + 27 * scale)):
          centered(label, FontRole.SEMI_BOLD, 20, y, white, x + (53 if arrow_direction else 59) * scale)
        number = centered(shown.posted_text, FontRole.BOLD, 58, top + (50 if shown.offset_text else 61) * scale, white)
        if shown.offset_text:
          centered(shown.offset_text, FontRole.MEDIUM, 36, top + 98 * scale, secondary)
    if arrow_direction:
      ax, ay = ((x + 59 * scale, top + 29 * scale) if state.appearance.use_vienna_sign else (x + 99 * scale, top + 26 * scale))
      arrow_color = color if state.appearance.use_vienna_sign else white
      self.shapes.arrow('compact' if state.appearance.use_vienna_sign else 'large', ax, ay, arrow_direction, arrow_color)
    if obs.driver_override_active:
      color = rl.Color(197, 163, 255, 240)
      left, top, right, bottom = number
      draw_line(self.profile, rl.Vector2(left - 3 * scale, top - 2 * scale), rl.Vector2(right + 3 * scale, bottom + 2 * scale), 2.5 * scale, color)
      draw_line(self.profile, rl.Vector2(right + 3 * scale, top - 2 * scale), rl.Vector2(left - 3 * scale, bottom + 2 * scale), 2.5 * scale, color)
