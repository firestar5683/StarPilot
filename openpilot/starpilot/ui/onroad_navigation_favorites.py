"""Home and Work cards shared by the AA renderer and its layout preview."""
import pyray as rl

from openpilot.starpilot.ui.presentation import FontRole


class NavigationFavorites:
  def __init__(self, fonts):
    self.fonts = fonts
    self.document = None
    self.error = ''

  def render(self, key, state):
    placed = state.customization['layouts']['large'].get(key)
    if placed is None or not placed['enabled'] or state.alert.size != 'none':
      return
    label = key.removeprefix('nav_').title()
    doc = self.document
    place = next((row for row in doc['favorites'] if row.get('label') == label.lower()), None) if doc else None
    active = bool(place and doc['destination'] and doc['destination']['id'] == place['id'])
    available = bool(active or place and doc['enabled'] and doc['token'])
    title = 'End navigation' if active else label
    detail = self.error or (label if active else 'Navigate' if available else 'Set in Galaxy' if place is None else 'Enable navigation')
    rect = rl.Rectangle(placed['x'], placed['y'], 320, 110)
    tint = rl.Color(240, 150, 150, 255) if active else rl.Color(199, 174, 247, 255)
    rl.draw_rectangle_rounded(rect, .3, 8, rl.Color(15, 13, 23, 245))
    rl.draw_rectangle_rounded_lines_ex(rect, .3, 8, 3, tint if available else rl.Color(140, 140, 150, 170))
    for text, role, size, offset in ((title, FontRole.SEMI_BOLD, 34, 18), (detail, FontRole.NORMAL, 25, 64)):
      measured = self.fonts.measure(text, role, size)
      self.fonts.draw(text, role, size, rect.x + (rect.width - measured.width) / 2, rect.y + offset,
                      tint if available else rl.Color(160, 157, 167, 255))
