"""Native compact child card for supported audible levels."""

from __future__ import annotations

from typing import Protocol

from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest, FeatureSettingsState, row_change
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, GreyBigButton

class SoundsSession(Protocol):
  def sounds_snapshot(self) -> FeatureSettingsState: ...
  def sounds_request(self, request: FeatureSettingsRequest) -> bool: ...


class SoundsCompact:
  def __init__(self, session: SoundsSession):
    self.session = session

  def entry_button(self) -> BigButton:
    button = BigButton("sounds & alerts", "installed packs & alert levels")
    button.set_click_callback(self.open)
    return button

  def open(self) -> None:
    page = NavScroller()
    self._populate(page)
    gui_app.push_widget(page)

  def _populate(self, page: NavScroller) -> None:
    state = self.session.sounds_snapshot()
    cards = [GreyBigButton("sounds & alerts", "installed packs and alert levels; auto follows ambient sound")]
    for row in state.rows:
      value = row.value + (row.unit if row.value != "Auto" else "")
      if not row.available:
        cards.append(GreyBigButton(row.label.lower(), f"{value}. {row.reason}".lower()))
        continue
      for direction in ((1,) if row.repair_value else (-1, 1)):
        label = row.label.lower() + (f" set {row.repair_value.lower()}" if row.repair_value else " −" if direction < 0 else " +")
        button = BigButton(label, value.lower())
        def clicked(source=row, step=direction) -> None:
          request = row_change(source, step)
          if request is not None and self.session.sounds_request(request):
            self._populate(page)
        button.set_click_callback(clicked)
        cards.append(button)
    page._scroller.items.clear()
    page._scroller.add_widgets(cards)
