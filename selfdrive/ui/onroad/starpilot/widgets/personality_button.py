import pyray as rl
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.onroad.starpilot.widgets.base import LayoutWidget
from openpilot.selfdrive.ui.onroad.starpilot.personality_button import PersonalityButton

class PersonalityButtonWidget(LayoutWidget):
  def __init__(self):
    super().__init__("personality_button", priority=1)
    self._button = PersonalityButton()
    self._button.set_visible(True)
    self._child(self._button)

  @property
  def is_visible(self) -> bool:
    params = ui_state.ui_params
    toggle_on = params.get_bool("OnroadDistanceButton")
    return bool(toggle_on and ui_state.started and ui_state.has_longitudinal_control)

  def get_size(self) -> tuple[float, float]:
    return 192.0, 192.0

  def _render(self, rect: rl.Rectangle) -> None:
    # Render the child button within the layout rect
    self._button.render(rect)
