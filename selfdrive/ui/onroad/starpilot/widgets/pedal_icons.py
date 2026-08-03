import pyray as rl
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.selfdrive.ui.onroad.starpilot.widgets.base import LayoutWidget
from openpilot.selfdrive.ui.onroad.starpilot.pedal_icons import render_pedal_icons


class PedalIconsWidget(LayoutWidget):
  def __init__(self):
    super().__init__("pedal_icons", priority=2)
    self._font_bold = gui_app.font(FontWeight.BOLD)

  @property
  def is_visible(self) -> bool:
    params = ui_state.ui_params
    if not params.get_bool("PedalsOnUI"):
      return False
    # Only render when car state is valid
    return "carState" in ui_state.sm.valid and ui_state.sm.valid["carState"]

  def get_size(self) -> tuple[float, float]:
    # Width is 180 (two circles of radius 36 centered at 48 and 144)
    # Height is 96 (center 48 + radius 36 + padding)
    return 180.0, 96.0

  def _render(self, rect: rl.Rectangle) -> None:
    render_pedal_icons(rect.x, rect.y, self._font_bold)
