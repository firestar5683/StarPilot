"""Compact Device child for the shared saved display preferences."""

from typing import Protocol

from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest, FeatureSettingsState, row_change
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, GreyBigButton


class DisplaySession(Protocol):
  def display_snapshot(self) -> FeatureSettingsState: ...
  def display_request(self, request: FeatureSettingsRequest) -> bool: ...


class DisplayCompact:
  def __init__(self, session: DisplaySession):
    self.session = session

  def entry_button(self) -> BigButton:
    button = BigButton("display", "brightness and screen timing")
    button.set_click_callback(self.open)
    return button

  def open(self) -> None:
    page = NavScroller()
    self._populate(page)
    gui_app.push_widget(page)

  def _populate(self, page: NavScroller) -> None:
    state = self.session.display_snapshot()
    cards = [GreyBigButton("display", "saved brightness and screen timing")]
    for row in state.rows:
      description = row.value + (" " + row.unit if row.unit and row.value != "Auto" else "") + (". " + row.reason if row.reason else "")
      if not row.available:
        cards.append(GreyBigButton(row.label.lower(), description.lower()))
        continue
      label = row.label.lower() + (" set " + row.repair_value.lower() if row.repair_value else "")
      button = BigButton(label, description.lower())
      def clicked(source=row) -> None:
        request = row_change(source)
        if request is not None and self.session.display_request(request):
          self._populate(page)
      button.set_click_callback(clicked)
      cards.append(button)
    page._scroller.items.clear()
    page._scroller.add_widgets(cards)
