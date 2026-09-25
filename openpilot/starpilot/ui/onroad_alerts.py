"""Source-supplied alerts with native compact lane-guidance rendering."""

import pyray as rl

from openpilot.common.filter_simple import BounceFilter, FirstOrderFilter
from openpilot.starpilot.ui.onroad_state import AlertSize, OnroadAlert
from openpilot.selfdrive.ui.mici.onroad.alert_renderer import Alert as NativeAlert, AlertRenderer as NativeAlertRenderer
from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile


class AlertRenderer:
  def __init__(self, fonts: BitmapFonts):
    self.fonts = fonts
    self._position = BounceFilter(0, 0.1, 1 / 60, initialized=fonts.profile == Profile.COMPACT)
    self._alpha = FirstOrderFilter(0, 0.05, 1 / 60)
    self._lane_renderer: NativeAlertRenderer | None = None
    self._lane_visible = False
    self._previous: OnroadAlert | None = None

  def _center(self, text: str, role: FontRole, size: int, rect: rl.Rectangle, y: float,
              color: rl.Color = rl.WHITE, *, letter_spacing: float = 0) -> None:
    spacing = size * letter_spacing
    measured = self.fonts.measure(text, role, size, spacing=spacing)
    self.fonts.draw(text, role, size, rect.x + (rect.width - measured.width) / 2, y, color, spacing=spacing)

  def render(self, rect: rl.Rectangle, alert: OnroadAlert, *, signal_direction: int = 0) -> None:
    if self.fonts.profile == Profile.COMPACT:
      lane_event = alert.alert_type.split('/', 1)[0] in ('preLaneChangeLeft', 'preLaneChangeRight', 'laneChangeBlocked', 'laneChange',
                                                                    'steerTempUnavailable', 'steerTempUnavailableSilent')
      if lane_event or (self._lane_visible and alert.size == AlertSize.NONE):
        if self._lane_renderer is None:
          self._lane_renderer = NativeAlertRenderer()
        native = NativeAlert(alert.text1, alert.text2, size=list(AlertSize).index(alert.size),
                             status=2 if alert.critical else 1 if alert.user_prompt else 0,
                             visual_alert=alert.visual_alert, alert_type=alert.alert_type) if lane_event else None
        self._lane_visible = self._lane_renderer.render_alert(rect, native, signal_direction=signal_direction)
        self._previous = None
        self._alpha.x = 0
        return
      if self._lane_visible:
        self._lane_renderer._prev_alert = None
        self._lane_renderer._alpha_filter.x = 0
        self._lane_visible = False
    compact_y = self._position.update(rect.y - 50 if alert.size == AlertSize.NONE else rect.y) \
      if self.fonts.profile == Profile.COMPACT else rect.y
    if alert.size == AlertSize.NONE:
      self._alpha.update(0)
      if self._alpha.x <= .01 or self._previous is None:
        self._previous = None
        return
      alert = self._previous
    else:
      self._previous = alert
      self._alpha.update(1)
    if self.fonts.profile == Profile.LARGE:
      height = rect.height if alert.size == AlertSize.FULL else 271 if alert.size == AlertSize.SMALL else 420
      self._large(rect, alert, self._position.update(rect.y + rect.height - height))
    else:
      self._compact(rect, alert, compact_y)

  def _large(self, rect: rl.Rectangle, alert: OnroadAlert, animated_y: float) -> None:
    background_alpha = int(255 * 0.9 * self._alpha.x)
    title_color = rl.Color(255, 255, 255, background_alpha)
    subtitle_color = rl.Color(255, 255, 255, int(255 * 0.65 * self._alpha.x))
    if alert.size == AlertSize.FULL:
      color = (rl.Color(255, 0, 21, background_alpha) if alert.critical else
               rl.Color(255, 115, 0, background_alpha) if alert.user_prompt else rl.Color(0, 0, 0, background_alpha))
      solid = round(rect.height * 0.2)
      rl.draw_rectangle(int(rect.x), int(rect.y), int(rect.width), solid, color)
      rl.draw_rectangle_gradient_v(int(rect.x), int(rect.y + solid), int(rect.width), int(rect.height - solid),
                                   color, rl.Color(color.r, color.g, color.b, 0))
      size = 100 if len(alert.text1) > 16 else 110
      title_h = self.fonts.measure(alert.text1, FontRole.BOLD, size, spacing=size * -0.02).height
      self._center(alert.text1, FontRole.BOLD, size, rl.Rectangle(rect.x + 60, rect.y, rect.width - 120, rect.height),
                   animated_y + (rect.height - title_h) / 2, title_color,
                   letter_spacing=-0.02)
      self._center(alert.text2, FontRole.NORMAL, 56, rl.Rectangle(rect.x + 60, rect.y, rect.width - 120, rect.height),
                   animated_y + (rect.height - title_h) / 2 + title_h,
                   subtitle_color, letter_spacing=0.025)
      return
    alert_height = 271 if alert.size == AlertSize.SMALL else 420
    y = rect.y + rect.height - alert_height
    color = rl.Color(218, 111, 37, background_alpha) if alert.user_prompt else rl.Color(0, 0, 0, background_alpha)
    title_size = 60 if alert.size == AlertSize.SMALL else 88
    title_h = self.fonts.measure(alert.text1, FontRole.BOLD, title_size, spacing=title_size * -0.02).height
    plateau_y = round(animated_y + (alert_height - title_h) / 2) - 2
    plateau_h = round(title_h) + 4
    rl.draw_rectangle_gradient_v(int(rect.x), int(y), int(rect.width), int(plateau_y - y), rl.BLANK, color)
    rl.draw_rectangle(int(rect.x), int(plateau_y), int(rect.width), plateau_h, color)
    rl.draw_rectangle_gradient_v(int(rect.x), int(plateau_y + plateau_h), int(rect.width), int(y + alert_height - plateau_y - plateau_h),
                                 color, rl.BLANK)
    text_rect = rl.Rectangle(rect.x + 60, y, rect.width - 120, alert_height)
    title_y = animated_y + (alert_height - title_h) / 2
    self._center(alert.text1, FontRole.BOLD, title_size, text_rect, title_y, title_color, letter_spacing=-0.02)
    if alert.size == AlertSize.MID:
      self._center(alert.text2, FontRole.NORMAL, 56, text_rect, title_y + title_h,
                   subtitle_color, letter_spacing=0.025)

  def _compact(self, rect: rl.Rectangle, alert: OnroadAlert, animated_y: float) -> None:
    background_alpha = int(255 * 0.9 * self._alpha.x)
    title_color = rl.Color(255, 255, 255, background_alpha)
    subtitle_color = rl.Color(255, 255, 255, int(255 * 0.65 * self._alpha.x))
    color = (rl.Color(255, 0, 21, background_alpha) if alert.critical else
               rl.Color(255, 115, 0, background_alpha) if alert.user_prompt else rl.Color(0, 0, 0, background_alpha))
    event_name = alert.alert_type.split('/', 1)[0]
    height = rect.height
    solid_height = round(height * 0.2)
    rl.draw_rectangle(int(rect.x), int(rect.y), int(rect.width), solid_height, color)
    rl.draw_rectangle_gradient_v(int(rect.x), int(rect.y + solid_height), int(rect.width), int(height - solid_height),
                                 color, rl.Color(color.r, color.g, color.b, 0))
    text = alert.text1.lower()
    subtitle = alert.text2.lower()
    if event_name == 'personalityChanged' and text.startswith('driving personality: '):
      text = text.removeprefix('driving personality: ')
      subtitle = 'driving personality'
    font_size = 82 if len(text) <= 12 else 70 if len(text) <= 16 else 54
    text_x = rect.x + 18
    available_width = rect.width - 36
    while alert.size != AlertSize.FULL and font_size > 30 and self.fonts.measure(
        text, FontRole.DISPLAY, font_size, spacing=-0.02 * font_size).width > available_width:
      font_size -= 2
    spacing = -0.02 * font_size
    if alert.size == AlertSize.FULL:
      # Match word wrapping and line spacing to measured glyph height, not nominal font size.
      available_width = rect.width - 18
      lines: list[str] = []
      current = ""
      for word in text.split():
        candidate = f"{current} {word}" if current else word
        if current and self.fonts.measure(candidate, FontRole.DISPLAY, font_size, spacing=spacing).width > available_width:
          lines.append(current)
          current = word
        else:
          current = candidate
      if current:
        lines.append(current)
      y = animated_y - 4
      for line in lines:
        self.fonts.draw(line, FontRole.DISPLAY, font_size, text_x, y, title_color, spacing=spacing)
        y += self.fonts.measure(line, FontRole.DISPLAY, font_size, spacing=spacing).height * 0.86 * 0.9
      return
    title_y = animated_y + 12
    lines = [text]
    bottom = title_y
    for line in lines:
      measured = self.fonts.measure(line, FontRole.DISPLAY, font_size, spacing=spacing)
      x = text_x
      self.fonts.draw(line, FontRole.DISPLAY, font_size, x, title_y, title_color, spacing=spacing)
      bottom = title_y + measured.height
      title_y += measured.height * .86 * .9
    if subtitle:
      subtitle_y = bottom - 4
      self.fonts.draw(subtitle, FontRole.ROMAN, 36, text_x, subtitle_y,
                      subtitle_color, spacing=36 * 0.025)
