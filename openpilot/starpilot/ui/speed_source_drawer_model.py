"""Pure geometry and reversible reveal for the display-only source drawer."""
import math
CONTROL_ROUNDNESS = 0.35
CONTROL_SEGMENTS = 10

SOURCE_DRAWER_WIDTH = 248
OPEN_SECONDS = 0.18
CLOSE_SECONDS = 0.14
_QUARTER = tuple((math.cos(i * math.pi / (2 * CONTROL_SEGMENTS)), math.sin(i * math.pi / (2 * CONTROL_SEGMENTS)))
                 for i in range(CONTROL_SEGMENTS + 1))


def _outline(rect, drawer_top: float, extension: float) -> list[tuple[float, float]]:
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


class DrawerMotion:
  def __init__(self):
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

