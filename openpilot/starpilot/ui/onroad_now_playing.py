"""The Android Auto now-playing card; both live rendering and previews use this drawing."""
import time

import pyray as rl

from openpilot.starpilot.soloist.now_playing import elapsed_ms
from openpilot.starpilot.system.android_auto.projection_layout import NOW_PLAYING_SIZE, NOW_PLAYING_WIDGET
from openpilot.starpilot.ui.presentation import FontRole

ACCENT = rl.Color(199, 174, 247, 255)
TEXT = rl.Color(245, 242, 252, 255)
MUTED = rl.Color(184, 178, 200, 255)
PAD = 22


class NowPlayingWidget:
  def __init__(self, fonts, clock=time.time):
    self.fonts = fonts
    self.clock = clock
    self.track = None

  def _fit(self, text, role, size, width):
    measured = self.fonts.measure(text, role, size)
    return size * width / measured.width if measured.width > width else size

  def render(self, state):
    placed = state.customization['layouts']['large'].get(NOW_PLAYING_WIDGET)
    track = self.track
    if not placed or not placed['enabled'] or not track or state.alert.size != 'none':
      return
    rect = rl.Rectangle(placed['x'], placed['y'], *NOW_PLAYING_SIZE)
    alpha = round(235 * placed.get('opacity', 85) / 100)
    rl.draw_rectangle_rounded(rect, .28, 10, rl.Color(15, 13, 23, alpha))
    # Left accent bar, then the pause/play mark at the right; text stays solid whatever the opacity.
    rl.draw_rectangle_rounded(rl.Rectangle(rect.x + 10, rect.y + 18, 5, rect.height - 36), 1.0, 4, ACCENT)
    playing = track['status'] == 'playing'
    mark_x, mark_y = rect.x + rect.width - PAD - 30, rect.y + 28
    if playing:
      for dx in (0, 18):
        rl.draw_rectangle_rounded(rl.Rectangle(mark_x + dx, mark_y, 10, 34), .4, 4, ACCENT)
    else:
      rl.draw_triangle(rl.Vector2(mark_x, mark_y), rl.Vector2(mark_x, mark_y + 34), rl.Vector2(mark_x + 30, mark_y + 17), ACCENT)
    left, width = rect.x + PAD + 10, rect.width - 2 * PAD - 10 - 56
    rows = ((track['title'], FontRole.SEMI_BOLD, 34, 18, TEXT), (track['artist'] or track['album'], FontRole.NORMAL, 26, 62, MUTED))
    for text, role, size, y, color in rows:
      if text:
        self.fonts.draw(text, role, self._fit(text, role, size, width), left, rect.y + y, color)
    duration = track.get('durationMs')
    if duration and track.get('position'):
      bar = rl.Rectangle(left, rect.y + rect.height - 26, rect.width - PAD - 10 - left + rect.x, 6)
      rl.draw_rectangle_rounded(bar, 1.0, 4, rl.Color(255, 255, 255, 50))
      done = min(1.0, elapsed_ms(track, self.clock() * 1000) / duration)
      if done > 0:
        rl.draw_rectangle_rounded(rl.Rectangle(bar.x, bar.y, max(bar.height, bar.width * done), bar.height), 1.0, 4, ACCENT)
