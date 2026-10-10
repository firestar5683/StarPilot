"""Home and Work cards shared by the AA renderer and its layout preview."""
from itertools import pairwise

import pyray as rl

from openpilot.starpilot.ui.presentation import FontRole
from openpilot.starpilot.ui.navigation_favorites_state import favorite_visible


class NavigationFavorites:
  def __init__(self, fonts):
    self.fonts = fonts
    self.document: dict | None = None
    self.error = ''

  def render(self, key, state):
    placed = state.customization['layouts']['large'].get(key)
    if placed is None or not placed['enabled'] or state.alert.size != 'none':
      return
    if not favorite_visible(key, self.document, state.customization['layouts']['large']):
      return
    label = key.removeprefix('nav_').title()
    doc = self.document
    place = next((row for row in doc['favorites'] if row.get('label') == label.lower()), None) if doc else None
    active = bool(place and doc and doc['destination'] and doc['destination']['id'] == place['id'])
    available = bool(active or place and doc and doc['enabled'] and doc['token'])
    title = 'End route' if active else label
    detail = self.error or (label if active else 'Navigate' if available else 'Set in Galaxy' if place is None else 'Enable navigation')
    icons = placed.get('display') == 'icons'
    rect = rl.Rectangle(placed['x'], placed['y'], 110 if icons else 320, 110)
    tint = rl.Color(240, 150, 150, 255) if active else rl.Color(199, 174, 247, 255)
    rl.draw_rectangle_rounded(rect, .3, 8, rl.Color(15, 13, 23, 245))
    rl.draw_rectangle_rounded_lines_ex(rect, .3, 8, 3, tint if available else rl.Color(140, 140, 150, 170))
    ink = tint if available else rl.Color(160, 157, 167, 255)
    if icons:
      if active:
        for start, end in (((35, 35), (75, 75)), ((35, 75), (75, 35))):
          rl.draw_line_ex(rl.Vector2(rect.x + start[0], rect.y + start[1]),
                          rl.Vector2(rect.x + end[0], rect.y + end[1]), 6, ink)
      else:
        self.draw_icon(key, rect, ink)
      badge = '!' if self.error else '+' if place is None else '!' if not available else ''
      if badge:
        rl.draw_circle(int(rect.x + 91), int(rect.y + 19), 14, rl.Color(15, 13, 23, 255))
        measured = self.fonts.measure(badge, FontRole.SEMI_BOLD, 23)
        self.fonts.draw(badge, FontRole.SEMI_BOLD, 23, rect.x + 91 - measured.width / 2, rect.y + 4, ink)
      return
    for text, role, size, offset in ((title, FontRole.SEMI_BOLD, 34, 18), (detail, FontRole.NORMAL, 25, 64)):
      measured = self.fonts.measure(text, role, size)
      self.fonts.draw(text, role, size, rect.x + (rect.width - measured.width) / 2, rect.y + offset,
                      ink)

  @staticmethod
  def draw_icon(key, rect, color):
    paths = (((3, 11), (12, 3), (21, 11)), ((5, 9), (5, 21), (10, 21), (10, 14), (14, 14), (14, 21), (19, 21), (19, 9))) if key == 'nav_home' else (
      ((8, 7), (8, 4), (16, 4), (16, 7)), ((3, 7), (21, 7), (21, 21), (3, 21), (3, 7)),
      ((3, 12), (10, 15), (14, 15), (21, 12)), ((10, 13), (10, 17), (14, 17), (14, 13)))
    scale = 64 / 24
    for path in paths:
      for (x1, y1), (x2, y2) in pairwise(path):
        rl.draw_line_ex(rl.Vector2(rect.x + 23 + x1 * scale, rect.y + 23 + y1 * scale),
                        rl.Vector2(rect.x + 23 + x2 * scale, rect.y + 23 + y2 * scale), 4.5, color)
