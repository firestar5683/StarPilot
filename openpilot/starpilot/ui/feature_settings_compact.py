"""Compact native card/page adapter for the shared saved-feature owner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Protocol

from openpilot.starpilot.ui.vehicle_bool import VEHICLE_BOOL_KEYS, confirmation_question as vehicle_question
from openpilot.starpilot.ui.feature_settings_state import (
  FeaturePage, FeatureRow, FeatureSettingsRequest, FeatureSettingsState,
  FEATURE_CONFIRM_ACTIONS, CONDITIONAL_CONFIRM_ACTIONS, is_long_confirm_action, row_change,
)
from openpilot.starpilot.ui.lane_change_feature import KEYS as LANE_CHANGE_KEYS, RESET as LANE_CHANGE_RESET
from openpilot.starpilot.ui.long_profile_feature import long_confirm_question
from openpilot.starpilot.ui.conditional_feature import confirmation_question as conditional_question
from openpilot.starpilot.ui.controller_feature import SETUP_ACTION, SETUP_QUESTION
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, GreyBigButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigConfirmationDialog
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog

class FeatureSession(Protocol):
  def feature_snapshot(self, page: str) -> FeatureSettingsState: ...
  def feature_request(self, request: FeatureSettingsRequest) -> bool: ...


class FeatureSettingsCompact:
  def __init__(self, session: FeatureSession):
    self.session = session

  def entry_button(self) -> BigButton:
    button = BigButton("driving controls", "saved feature settings")
    button.set_click_callback(lambda: self.open(FeaturePage.HUB))
    return button

  def open(self, page_name: str) -> None:
    page = NavScroller()
    self._populate(page, page_name)
    gui_app.push_widget(page)

  def _populate(self, page: NavScroller, page_name: str) -> None:
    state = self.session.feature_snapshot(page_name)
    def refresh() -> None:
      self._populate(page, page_name)
    cards = [GreyBigButton(state.title.lower(), state.subtitle.lower())]
    for row in state.rows:
      if row.page and row.available:
        button = BigButton(row.label.lower(), row.value.lower())
        button.set_click_callback(lambda name=row.page: self.open(name))
        cards.append(button)
      elif (row.key in FEATURE_CONFIRM_ACTIONS or
            is_long_confirm_action(row.key)):
        button = BigButton("reset invalid profiles" if row.key == "reset_profiles" else row.label.lower(),
                           "")
        button.set_enabled(row.available)
        button.set_click_callback(lambda selected=row: self._confirm_reset(selected, refresh, page))
        cards.append(button)
      elif row.available:
        cards.extend(self._editable(row, refresh, page))
      else:
        detail = (row.value + " " + row.unit).strip()
        if row.reason:
          detail += " · " + row.reason
        cards.append(GreyBigButton(row.label.lower(), detail.lower()))
    page._scroller.items.clear()
    page._scroller.add_widgets(cards)

  def _editable(self, row: FeatureRow, refresh: Callable[[], None], page: NavScroller) -> list[BigButton]:
    result: list[BigButton] = []
    directions = (1,) if row.repair_value else (-1, 1) if row.step else (1,)
    for direction in directions:
      label = row.label.lower() + (" set " + row.repair_value.lower() if row.repair_value else
                                   " −" if direction < 0 else " +" if row.step else "")
      detail = (row.value + " " + row.unit).strip()
      if row.reason:
        detail += " · " + row.reason
      button = BigButton(label, detail)

      def clicked(source=row, direction=direction) -> None:
        request = row_change(source, direction)
        if request is None:
          return
        if request.key in VEHICLE_BOOL_KEYS:
          self._confirm_vehicle_bool(request, refresh, page)
        elif request.key in LANE_CHANGE_KEYS:
          self._confirm_lane_change(request, refresh, page)
        elif self.session.feature_request(request):
          refresh()

      button.set_click_callback(clicked)
      result.append(button)
    return result

  def _confirm_reset(self, row: FeatureRow, refresh: Callable[[], None], page: NavScroller | None = None) -> None:
    request = FeatureSettingsRequest(row.key, row.source, "confirm", confirmation=True,
                                     related_source=row.related_source,
                                     vehicle_fingerprint=row.vehicle_fingerprint,
                                     capability=row.capability, dependencies=row.dependencies)
    if row.key == LANE_CHANGE_RESET:
      if page is not None:
        self._confirm_lane_change(request, refresh, page)
      return
    if row.key in CONDITIONAL_CONFIRM_ACTIONS:
      if page is not None:
        self._confirm_conditional(request, refresh, page)
      return
    def confirmed() -> None:
      if self.session.feature_request(request):
        refresh()
    question = {"torque_adopt": "use new torque editor for this vehicle model? old values remain saved but inactive",
                SETUP_ACTION: SETUP_QUESTION,
                "torque_reset": "reset invalid torque profiles? old values remain saved but inactive",
                "torque_reset_profile": "reset this vehicle model's custom torque profile?",
                "torque_gain_rebase": "Apply the saved steering response to the selected controller and current vehicle tune? " +
                                     "Friction and other models stay unchanged.",
                "torque_rebase": f"reapply saved torque values ({row.value}) with the current vehicle tune?",
                "slc_adopt": "keep these offsets and speed ranges when units change? old saved values remain, but no longer control the offsets",
                "slc_reset": f"reset speed-limit offsets to zero? {row.value}. " +
                             "saved control may resume if its switch is on; its switch will not change",
                "curve_reset": "Erase learned curve data? Curve Speed Controller keeps its current On or Off choice.",
                "reset_profiles": "reset invalid profiles"}.get(row.key, long_confirm_question(row))
    gui_app.push_widget(BigConfirmationDialog(question,
                                               gui_app.texture("icons_mici/settings/device/uninstall.png", 64, 64),
                                               confirmed, red=True))

  def _confirm_lane_change(self, request: FeatureSettingsRequest, refresh: Callable[[], None], page: NavScroller) -> None:
    if gui_app.get_active_widget() is not page:
      return
    if request.key == LANE_CHANGE_RESET:
      question = "Restore stock driver-nudged lane-change settings for the next drive?"
    elif request.key == "lane_change:speed":
      question = f"Save a {request.value} {request.display_unit} minimum for the next drive? Blindspot checks remain required."
    elif request.key == "lane_change:auto":
      question = f"Save Automatic Lane Changes {request.value} for the next drive? Vehicle support, lane and blindspot checks remain required."
    elif request.key in ("lane_change:delay", "lane_change:width"):
      unit = "seconds" if request.key == "lane_change:delay" else "feet"
      question = f"Save {request.value} {unit} for automatic lane changes on the next drive? Lane and blindspot checks remain required."
    else:
      question = f"Save {request.value} for the next drive? Blindspot checks remain required."
    def confirmed(result: DialogResult) -> None:
      if (result == DialogResult.CONFIRM and gui_app.get_active_widget() is page and
          self.session.feature_request(replace(request, confirmation=True))):
        refresh()
    gui_app.push_widget(ConfirmDialog(question, "Save", callback=confirmed))

  def _confirm_vehicle_bool(self, request: FeatureSettingsRequest, refresh: Callable[[], None], page: NavScroller) -> None:
    if gui_app.get_active_widget() is not page:
      return
    question = vehicle_question(request)
    def confirmed(result: DialogResult) -> None:
      if result == DialogResult.CONFIRM and gui_app.get_active_widget() is page and \
         self.session.feature_request(replace(request, confirmation=True)):
        refresh()
    gui_app.push_widget(ConfirmDialog(question, "Save", callback=confirmed))

  def _confirm_conditional(self, request: FeatureSettingsRequest, refresh: Callable[[], None], page: NavScroller) -> None:
    if gui_app.get_active_widget() is not page:
      return
    question = conditional_question(request)
    def confirmed(result: DialogResult) -> None:
      if result == DialogResult.CONFIRM and gui_app.get_active_widget() is page and \
         self.session.feature_request(replace(request, confirmation=True)):
        refresh()
    gui_app.push_widget(ConfirmDialog(question, "Save", callback=confirmed))
