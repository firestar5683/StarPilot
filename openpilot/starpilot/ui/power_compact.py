"""Compact Device child for parked-power limits."""

from typing import Protocol

from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest, FeatureSettingsState
from openpilot.starpilot.ui.power_owner import ENABLED, confirm_question, power_row_change
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, GreyBigButton


class PowerSession(Protocol):
  def power_snapshot(self) -> FeatureSettingsState: ...
  def power_request(self, request: FeatureSettingsRequest) -> bool: ...


class PowerCompact:
  def __init__(self, session: PowerSession):
    self.session = session

  def entry_button(self) -> BigButton:
    button = BigButton("parked power", "automatic shutdown limits")
    button.set_click_callback(self.open)
    return button

  def open(self) -> None:
    page = NavScroller()
    self._populate(page)
    gui_app.push_widget(page)

  def _populate(self, page: NavScroller) -> None:
    state = self.session.power_snapshot()
    cards = [GreyBigButton("parked power", "saved offroad shutdown limits")]
    for row in state.rows:
      description = row.value + (". " + row.reason if row.reason else "")
      if not row.available:
        cards.append(GreyBigButton(row.label.lower(), description.lower()))
        continue
      button = BigButton(row.label.lower() + (" set " + row.repair_value.lower() if row.repair_value else ""),
                         description.lower())
      def clicked(source=row) -> None:
        if gui_app.get_active_widget() is not page:
          return
        def ask_confirmation(request: FeatureSettingsRequest) -> None:
          def confirmed(result: DialogResult) -> None:
            # Native dialogs pop themselves before invoking this callback.
            if gui_app.get_active_widget() is page and result == DialogResult.CONFIRM and self.session.power_request(
              FeatureSettingsRequest(request.key, request.expected, request.value, confirmation=True)):
              self._populate(page)
          gui_app.push_widget(ConfirmDialog(confirm_question(request), "Save", callback=confirmed))
        if source.key == ENABLED:
          request = power_row_change(source)
          if request is not None:
            ask_confirmation(request)
        else:
          def selected(result: DialogResult) -> None:
            if (gui_app.get_active_widget() is page and result == DialogResult.CONFIRM and
                picker.selection in source.choices and picker.selection != source.value):
              ask_confirmation(FeatureSettingsRequest(source.key, source.source, picker.selection))
          picker = MultiOptionDialog(source.label, list(source.choices), source.value, callback=selected)
          gui_app.push_widget(picker)
      button.set_click_callback(clicked)
      cards.append(button)
    page._scroller.items.clear()
    page._scroller.add_widgets(cards)
