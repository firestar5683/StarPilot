"""The source drawer's reveal, shared frame, and clipped contents."""

import math

import pyray as rl

from openpilot.starpilot.ui.onroad_widget_style import CONTROL_ROUNDNESS
from openpilot.starpilot.ui import clip

from openpilot.starpilot.ui.speed_source_drawer_model import DrawerMotion, SOURCE_DRAWER_WIDTH, _outline


class SpeedSourceDrawer(DrawerMotion):
  def __init__(self):
    self._mesh_key = None
    self._fill = None
    self._strokes = {}
    self.reset()

  def bounds(self, rect: rl.Rectangle, drawer_top: float) -> rl.Rectangle:
    return rl.Rectangle(rect.x + rect.width, drawer_top, self.width, rect.y + rect.height - drawer_top)

  def _prepare_mesh(self, rect: rl.Rectangle, drawer_top: float) -> None:
    key = (rect.x, rect.y, rect.width, rect.height, drawer_top, self.width)
    if key == self._mesh_key:
      return
    points = _outline(rect, drawer_top, self.width)
    # The lower-left interior sees the entire L-shaped outline without overlap.
    center = (rect.x + rect.width / 2, (drawer_top + rect.y + rect.height) / 2)
    self._fill = rl.ffi.new('Vector2[]', [center, *reversed(points), points[-1]])
    self._points = points
    self._miters = []
    for i, (x, y) in enumerate(points):
      px, py = points[i - 1]
      nx, ny = points[(i + 1) % len(points)]
      before, after = math.hypot(x - px, y - py), math.hypot(nx - x, ny - y)
      ax, ay = (y - py) / before, -(x - px) / before
      bx, by = (ny - y) / after, -(nx - x) / after
      denominator = 1 + ax * bx + ay * by
      self._miters.append(((ax + bx) / denominator, (ay + by) / denominator))
    self._strokes.clear()
    self._mesh_key = key

  def draw_border(self, rect: rl.Rectangle, drawer_top: float, width: float, color: rl.Color) -> None:
    self._prepare_mesh(rect, drawer_top)
    if width not in self._strokes:
      vertices = []
      for (x, y), (mx, my) in zip(self._points + [self._points[0]], self._miters + [self._miters[0]], strict=True):
        vertices.extend(((x + mx * width, y + my * width), (x, y)))
      self._strokes[width] = rl.ffi.new('Vector2[]', vertices)
    vertices = self._strokes[width]
    rl.draw_triangle_strip(rl.ffi.cast('Vector2 *', vertices), len(vertices), color)

  def draw_frame(self, rect: rl.Rectangle, drawer_top: float, fill: rl.Color, border: rl.Color) -> None:
    self._prepare_mesh(rect, drawer_top)
    assert self._fill is not None
    rl.draw_triangle_fan(rl.ffi.cast('Vector2 *', self._fill), len(self._fill), fill)
    self.draw_border(rect, drawer_top, 7, rl.Color(border.r, border.g, border.b, 55))
    self.draw_border(rect, drawer_top, 2, border)

  def draw_contents(self, draw_contents, rect: rl.Rectangle, drawer_top: float, parent: rl.Rectangle) -> None:
    bounds = self.bounds(rect, drawer_top)
    panel = rl.Rectangle(bounds.x + bounds.width - SOURCE_DRAWER_WIDTH, bounds.y, SOURCE_DRAWER_WIDTH, bounds.height)
    # The shell owns clipping; restore the containing card viewport afterward.
    rl.rl_draw_render_batch_active()
    with clip.clipped(bounds, parent):
      draw_contents(panel)
      radius = min(rect.width, rect.height) * CONTROL_ROUNDNESS / 2
      top, bottom = drawer_top + radius, rect.y + rect.height - radius
      cap, width = 16, min(12, bounds.width)
      shade, clear = rl.Color(0, 0, 0, 108), rl.BLANK
      rl.draw_rectangle_gradient_ex(rl.Rectangle(bounds.x, top, width, cap), clear, shade, clear, clear)
      rl.draw_rectangle_gradient_h(math.ceil(bounds.x), math.ceil(top + cap), math.ceil(width), int(bottom - top - 2 * cap), shade, clear)
      rl.draw_rectangle_gradient_ex(rl.Rectangle(bounds.x, bottom - cap, width, cap), shade, clear, clear, clear)
    rim = rl.Color(230, 218, 246, round(46 * self.progress))
    rl.draw_line_ex(rl.Vector2(bounds.x - 0.5, drawer_top + 16),
                    rl.Vector2(bounds.x - 0.5, rect.y + rect.height - 16), 1, rim)
