"""Always-present car-screen escape control for the projected StarPilot UI."""

from __future__ import annotations

from openpilot.starpilot.system.android_auto.projection_layout import CAR_EXIT, CAR_EXIT_SIZE


class ProjectionExit:
  def __init__(self, rl, activate=None):
    self.rl = rl
    self.activate = activate or (lambda: None)
    self._press: tuple[float, float] | None = None

  @staticmethod
  def placement(customization):
    placed = customization.get('layouts', {}).get('large', {}).get(CAR_EXIT)
    return placed if placed is not None and placed.get('enabled') is True else None

  @staticmethod
  def document_placement(document):
    placed = document.get('widgets', {}).get(CAR_EXIT) if document is not None else None
    return placed if placed is not None and placed.get('enabled') is True else None

  def draw(self, placed) -> None:
    if placed is None:
      return
    rl = self.rl
    x, y = placed['x'], placed['y']
    width, height = CAR_EXIT_SIZE
    rect = rl.Rectangle(x, y, width, height)
    border = rl.Color(199, 174, 247, 200)
    icon = rl.Color(199, 174, 247, 230)
    rl.draw_rectangle_rounded(rect, .3, 8, rl.Color(15, 13, 23, 166))
    rl.draw_rectangle_rounded_lines_ex(rect, .3, 8, 3, border)
    # Door frame and outward arrow: the familiar exit-to-app symbol without text.
    for x1, y1, x2, y2 in ((54, 20, 24, 20), (24, 20, 24, 76), (24, 76, 54, 76),
                           (38, 48, 78, 48), (67, 37, 78, 48), (78, 48, 67, 59)):
      rl.draw_line_ex(rl.Vector2(x + x1, y + y1), rl.Vector2(x + x2, y + y2), 5, icon)

  def render(self, state) -> None:
    self.draw(self.placement(state.customization))

  @staticmethod
  def _inside(placed, x, y) -> bool:
    width, height = CAR_EXIT_SIZE
    return placed['x'] <= x < placed['x'] + width and placed['y'] <= y < placed['y'] + height

  def touch(self, kind: str, x: float, y: float, placed) -> bool:
    """Handle one pointer event; True means the escape widget owns the gesture."""
    if kind == 'cancel':
      claimed = self._press is not None
      self._press = None
      return claimed
    if kind == 'down':
      self._press = (x, y) if placed is not None and self._inside(placed, x, y) else None
      return self._press is not None
    if self._press is None:
      return False
    px, py = self._press
    if placed is None or abs(x - px) > 15 or abs(y - py) > 15 or not self._inside(placed, x, y):
      self._press = None
      return True
    if kind == 'up':
      self._press = None
      self.activate()
    return True

  def cancel(self) -> None:
    self._press = None
