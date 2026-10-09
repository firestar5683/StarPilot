"""The source drawer's reveal, shared frame, and clipped contents."""

import math

import pyray as rl

from openpilot.selfdrive.ui.onroad.starpilot.slc_speed_limit import _draw_source_contents
from openpilot.selfdrive.ui.onroad.starpilot.widget_style import CONTROL_ROUNDNESS, CONTROL_SEGMENTS

SOURCE_DRAWER_WIDTH = 248
OPEN_SECONDS = 0.18
CLOSE_SECONDS = 0.14
_QUARTER = tuple((math.cos(i * math.pi / (2 * CONTROL_SEGMENTS)), math.sin(i * math.pi / (2 * CONTROL_SEGMENTS)))
                 for i in range(CONTROL_SEGMENTS + 1))


def _outline(rect: rl.Rectangle, drawer_top: float, extension: float) -> list[tuple[float, float]]:
  left, top = rect.x, rect.y
  card_right, bottom = left + rect.width, top + rect.height
  right = card_right + extension
  radius = min(rect.width, rect.height) * CONTROL_ROUNDNESS / 2
  points = []

  def corner(cx, cy, r, quadrant):
    for x, y in _QUARTER:
      dx, dy = ((-x, -y), (y, -x), (x, y), (-y, x))[quadrant]
      point = (cx + dx * r, cy + dy * r)
      if not points or math.hypot(point[0] - points[-1][0], point[1] - points[-1][1]) > 1e-5:
        points.append(point)

  corner(left + radius, top + radius, radius, 0)
  if drawer_top <= top:
    corner(right - radius, top + radius, radius, 1)
  else:
    corner(card_right - radius, top + radius, radius, 1)
    points.append((card_right, drawer_top))
    tip_radius = min(radius, extension)
    corner(right - tip_radius, drawer_top + tip_radius, tip_radius, 1)
  corner(right - radius, bottom - radius, radius, 2)
  corner(left + radius, bottom - radius, radius, 3)
  return points


class SpeedSourceDrawer:
  def __init__(self):
    self._mesh_key = None
    self._fill = None
    self._strokes = {}
    self.reset()

  def reset(self) -> None:
    self.progress = 0.0
    self._open = False
    self._start_progress = 0.0
    self._start_time = 0.0

  @property
  def width(self) -> float:
    return SOURCE_DRAWER_WIDTH * self.progress

  def update(self, opened: bool, now: float) -> None:
    # Sample the old transition first so a second tap reverses without jumping.
    target = float(self._open)
    if self.progress != target:
      duration = OPEN_SECONDS if self._open else CLOSE_SECONDS
      phase = min(1.0, max(0.0, (now - self._start_time) / duration))
      self.progress = target + (self._start_progress - target) * (1 - phase) ** 4
    if opened != self._open:
      self._open = opened
      self._start_progress = self.progress
      self._start_time = now

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
    rl.draw_triangle_fan(rl.ffi.cast('Vector2 *', self._fill), len(self._fill), fill)
    self.draw_border(rect, drawer_top, 7, rl.Color(border.r, border.g, border.b, 55))
    self.draw_border(rect, drawer_top, 2, border)

  def draw_contents(self, state: dict, rect: rl.Rectangle, drawer_top: float) -> None:
    bounds = self.bounds(rect, drawer_top)
    panel = rl.Rectangle(bounds.x + bounds.width - SOURCE_DRAWER_WIDTH, bounds.y, SOURCE_DRAWER_WIDTH, bounds.height)
    # Scissor is not stacked in Raylib. This is a top-level HUD widget.
    rl.rl_draw_render_batch_active()
    rl.begin_scissor_mode(math.ceil(bounds.x), math.ceil(bounds.y), math.ceil(bounds.width), math.ceil(bounds.height))
    try:
      _draw_source_contents(state, panel)
      radius = min(rect.width, rect.height) * CONTROL_ROUNDNESS / 2
      top, bottom = drawer_top + radius, rect.y + rect.height - radius
      cap, width = 16, min(12, bounds.width)
      shade, clear = rl.Color(0, 0, 0, 108), rl.BLANK
      rl.draw_rectangle_gradient_ex(rl.Rectangle(bounds.x, top, width, cap), clear, shade, clear, clear)
      rl.draw_rectangle_gradient_h(math.ceil(bounds.x), math.ceil(top + cap), math.ceil(width), int(bottom - top - 2 * cap), shade, clear)
      rl.draw_rectangle_gradient_ex(rl.Rectangle(bounds.x, bottom - cap, width, cap), shade, clear, clear, clear)
    finally:
      rl.rl_draw_render_batch_active()
      rl.end_scissor_mode()
    rim = rl.Color(230, 218, 246, round(46 * self.progress))
    rl.draw_line_ex(rl.Vector2(bounds.x - 0.5, drawer_top + 16),
                    rl.Vector2(bounds.x - 0.5, rect.y + rect.height - 16), 1, rim)
