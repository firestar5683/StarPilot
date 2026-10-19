import pyray as rl
from abc import abstractmethod
from openpilot.system.ui.widgets import Widget

class LayoutWidget(Widget):
  def __init__(self, name: str, priority: int):
    super().__init__()
    self.name = name
    self.priority = priority

  @property
  @abstractmethod
  def is_visible(self) -> bool:
    """Returns True if the widget should currently be displayed."""

  @abstractmethod
  def get_size(self) -> tuple[float, float]:
    """Returns the width and height of the widget as (width, height)."""

  @property
  def blocks_pointer(self) -> bool:
    """Whether this visual should suppress the on-road background tap."""
    return True

  def contains_pointer(self, mouse_pos) -> bool:
    return rl.check_collision_point_rec(mouse_pos, self.rect)

  def _render(self, rect: rl.Rectangle) -> bool | int | None:
    # Subclasses will implement self._render instead of render
    # to integrate with openpilot.system.ui.widgets.Widget
    pass
