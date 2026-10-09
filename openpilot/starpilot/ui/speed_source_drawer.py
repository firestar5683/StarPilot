"""A vertically revealed, display-only source panel."""

import pyray as rl

from openpilot.starpilot.ui import clip
from openpilot.starpilot.ui.speed_source_drawer_model import DrawerMotion


class SpeedSourceDrawer(DrawerMotion):
  def draw_panel(self, panel, parent, fill, border, draw_contents):
    if self.progress <= 0:
      return None
    visible = rl.Rectangle(panel.x, panel.y, panel.width, panel.height * self.progress)
    with clip.clipped(visible, parent):
      rl.draw_rectangle_rounded(panel, .14, 12, fill)
      rl.draw_rectangle_rounded_lines_ex(panel, .14, 12, 1, border)
      draw_contents(panel)
