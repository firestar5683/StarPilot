"""Read-only offline-map status in the compact Software section."""

from collections.abc import Callable
import time
from typing import Protocol

from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsState
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, GreyBigButton


class MapSession(Protocol):
  def map_snapshot(self) -> FeatureSettingsState: ...


class _MapsPage(NavScroller):
  def __init__(self, owner: "MapsCompact"):
    super().__init__()
    self.owner = owner
    self.current: FeatureSettingsState | None = None
    self.next_refresh = 0.0

  def render(self, rect=None):
    self.owner.refresh_visible(self)
    return super().render(rect)


class MapsCompact:
  REFRESH_SECONDS = 0.5

  def __init__(self, session: MapSession, clock: Callable[[], float] = time.monotonic):
    self.session = session
    self.clock = clock

  def entry_button(self) -> BigButton:
    button = BigButton("offline maps", "status and selected region")
    button.set_click_callback(self.open)
    return button

  def open(self) -> None:
    page = _MapsPage(self)
    self._populate(page, self.session.map_snapshot())
    page.next_refresh = self.clock() + self.REFRESH_SECONDS
    gui_app.push_widget(page)

  def refresh_visible(self, page: _MapsPage) -> None:
    if gui_app.get_active_widget() is not page:
      return
    now = self.clock()
    if now < page.next_refresh:
      return
    page.next_refresh = now + self.REFRESH_SECONDS
    state = self.session.map_snapshot()
    if state != page.current:
      self._populate(page, state)

  @staticmethod
  def _populate(page: _MapsPage, state: FeatureSettingsState) -> None:
    page.current = state
    cards = [GreyBigButton(state.title.lower(), state.subtitle.lower())]
    cards.extend(GreyBigButton(row.label.lower(), f"{row.value}. {row.reason}".lower()) for row in state.rows)
    page._scroller.items.clear()
    page._scroller.add_widgets(cards)
