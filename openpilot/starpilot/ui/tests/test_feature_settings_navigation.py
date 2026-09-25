"""Protected Settings root coordinates and guarded large child actions."""

import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS

from openpilot.common.params import Params
from openpilot.starpilot.longitudinal.profile_document import migrate_profile_document
from openpilot.starpilot.ui import feature_settings_compact as compact
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureInput, FeatureRow, FeatureSettingsState, FeatureUiAction, row_change
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.settings_state import Destination, SettingsInput, SettingsState, tile_rects
from opendbc.car.honda.interface import CarInterface as HondaCarInterface
from opendbc.car.honda.values import CAR as HONDA_CAR


class FeatureNavigationTests(unittest.TestCase):
  def test_native_saved_preferences_need_settings_or_favorite_context_not_cp(self):
    from openpilot.starpilot.ui import runtime_app

    cp = HondaCarInterface.get_non_essential_params(HONDA_CAR.HONDA_CIVIC)
    self.assertTrue(cp.openpilotLongitudinalControl and cp.pcmCruise)
    session = runtime_app.StarShellSession.__new__(runtime_app.StarShellSession)
    session._mode = runtime_app.ShellMode.SETTINGS
    with patch.object(session, "confirmed_offroad", return_value=True), patch.object(runtime_app, "ui_state", NS(CP=cp)):
      self.assertFalse(session._feature_authority("long"))
      self.assertTrue(session._feature_authority("preferences"))
      cp.passive = True
      self.assertTrue(session._feature_authority("preferences"))
    with patch.object(session, "confirmed_offroad", return_value=True), patch.object(runtime_app, "ui_state", NS(CP=None)):
      self.assertTrue(session._feature_authority("preferences"))
    with patch.object(session, "confirmed_offroad", return_value=False), patch.object(runtime_app, "ui_state", NS(CP=None)):
      self.assertTrue(session._feature_authority("preferences"))
      self.assertFalse(session._feature_authority("lane"))
    session._mode = runtime_app.ShellMode.ONROAD
    with patch.object(session, "_favorite_authority", return_value=False):
      self.assertFalse(session._feature_authority("preferences"))
    with patch.object(session, "_favorite_authority", return_value=True):
      self.assertTrue(session._feature_authority("preferences"))
      self.assertFalse(session._feature_authority("parked_preferences"))

  def test_large_root_tile_geometry_and_destination(self):
    state = SettingsState()
    self.assertEqual(tile_rects(state)[2], (1611, 92, 529, 471))
    actions = []
    controller = SettingsInput(Profile.LARGE, actions.append)
    controller.press(1800, 300, state)
    controller.release(1800, 300, state)
    self.assertEqual(actions[0].destination.destination, Destination.DRIVING_CONTROLS)

  def test_press_release_cancels_on_drag_or_changed_source(self):
    actions = []
    controller = FeatureInput(actions.append)
    source = FeatureRow("LaneCentering", "Enable Lane Centering", "Off", b"0", ("Off", "On"), available=True)
    state = FeatureSettingsState(page="lane", rows=(source,))
    controller.press(1990, 160, state)
    controller.move(1800, 160, state)
    controller.release(1800, 160, state)
    self.assertFalse(actions)
    controller.press(1990, 160, state)
    changed = FeatureSettingsState(page="lane", rows=(FeatureRow("LaneCentering", "Enable Lane Centering", "On", b"1", ("Off", "On"), available=True),))
    controller.release(1990, 160, changed)
    self.assertFalse(actions)
    controller.press(1990, 160, state)
    controller.release(1990, 160, state)
    self.assertEqual(row_change(actions[0].row).expected, b"0")

  def test_curve_page_uses_shared_large_input_rows(self):
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      owner = FeatureSettingsOwner(params, lambda group: group == "long", vehicle_fingerprint=lambda: "TOYOTA COROLLA TSS2")
      hub = owner.snapshot("hub", parked=True, system_long=True, lateral_context=True, metric=False)
      self.assertIn("curve", [row.page for row in hub.rows])
      page = owner.snapshot("curve", parked=True, system_long=True, lateral_context=True, metric=False)
      master = page.rows[0]
      self.assertEqual(master.key, "CurveSpeedController")
      request = row_change(master)
      self.assertIsNotNone(request)
      if request is None:
        self.fail("the curve master has no action")
      self.assertTrue(owner.apply(request))
      self.assertTrue(params.get_bool("CurveSpeedController"))

  def test_compact_entry_opens_child_scroller(self):
    class Button:
      def __init__(self, text, value):
        self.text, self.value, self.click = text, value, None

      def set_click_callback(self, callback):
        self.click = callback

    class Scroller:
      def __init__(self):
        self.cards = []
        self.items = self.cards
        self._scroller = self

      def add_widgets(self, cards):
        self.cards.extend(cards)

    class Session:
      def feature_snapshot(self, page):
        return FeatureSettingsState(page=page, title="Driving Controls",
                                    rows=(FeatureRow("", "Speed Limit Controller", "Saved settings", page="slc", available=True),))
      def feature_request(self, request):
        return False

    pushed = []
    with patch.object(compact, "BigButton", Button), patch.object(compact, "GreyBigButton", Button), \
         patch.object(compact, "NavScroller", Scroller), patch.object(compact.gui_app, "push_widget", pushed.append):
      entry = compact.FeatureSettingsCompact(Session()).entry_button()
      self.assertEqual(entry.text, "driving controls")
      entry.click()
    self.assertEqual([card.text for card in pushed[0].cards], ["driving controls", "speed limit controller"])

  def test_compact_dependent_cards_and_confirmed_reset(self):
    class Button:
      def __init__(self, text, value):
        self.text, self.value, self.click = text, value, None

      def set_click_callback(self, callback):
        self.click = callback

      def set_enabled(self, enabled):
        self.enabled = enabled

    class ReadButton(Button):
      pass

    class Scroller:
      def __init__(self):
        self.items = []
        self._scroller = self

      def add_widgets(self, cards):
        self.items.extend(cards)

    class Dialog:
      def __init__(self, title, icon, confirm_callback, **kwargs):
        self.confirm = confirm_callback

    class Session:
      def __init__(self, owner):
        self.owner = owner

      def feature_snapshot(self, page):
        return self.owner.snapshot(page, parked=True, system_long=True, lateral_context=True, metric=False)

      def feature_request(self, request):
        return self.owner.apply(request)

    def card(page, text):
      return next(item for item in page.items if item.text == text)

    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      cp = NS(carFingerprint="TOYOTA COROLLA TSS2", openpilotLongitudinalControl=True, pcmCruise=False,
              passive=False, notCar=False, dashcamOnly=False, carVin="TEST", transmissionType=1)
      owner = FeatureSettingsOwner(params, lambda group: True, vehicle_fingerprint=lambda: "TOYOTA COROLLA TSS2",
                                   vehicle_params=lambda: cp)
      adapter = compact.FeatureSettingsCompact(Session(owner))
      pushed = []
      with patch.object(compact, "BigButton", Button), patch.object(compact, "GreyBigButton", ReadButton), \
           patch.object(compact, "NavScroller", Scroller), patch.object(compact, "BigConfirmationDialog", Dialog), \
           patch.object(compact.gui_app, "push_widget", pushed.append), patch.object(compact.gui_app, "texture", lambda *args: None):
        adapter.open("slc")
        slc = pushed[-1]
        self.assertIsInstance(card(slc, "confirm lower limits"), ReadButton)
        card(slc, "require confirmation").click()
        self.assertIsInstance(card(slc, "confirm lower limits"), Button)
        self.assertNotIsInstance(card(slc, "confirm lower limits"), ReadButton)

        adapter.open("aggressive/acceleration")
        curve = pushed[-1]
        for _ in range(5):
          card(curve, "preset").click()
        self.assertEqual(len([item for item in curve.items if item.text.endswith("mph point +")]), 10)

        params.put_bool("CustomPersonalities", True, block=True)
        path = Path(params.get_param_path("LongitudinalPersonalityProfiles"))
        path.write_bytes(b"{invalid")
        adapter.open("profiles")
        profiles = pushed[-1]
        card(profiles, "reset invalid profiles").click()
        pushed[-1].confirm()
        self.assertFalse(params.get_bool("CustomPersonalities"))
        self.assertIsNotNone(migrate_profile_document(path.read_bytes()))
        self.assertFalse(any(item.text == "reset invalid profiles" for item in profiles.items))

  def test_large_hub_back_returns_to_settings_root(self):
    from openpilot.starpilot.ui.runtime_app import StarShellSession
    from openpilot.starpilot.ui.shell import ShellMode
    session = StarShellSession.__new__(StarShellSession)
    session._mode = ShellMode.SETTINGS
    session.selected = Destination.DRIVING_CONTROLS
    session.feature_page = "hub"
    session.feature_scroll = 0
    self.enterContext(patch.object(session, "feature_snapshot", lambda: FeatureSettingsState()))
    self.enterContext(patch.object(session, "input", type("Input", (), {"cancel": lambda self: None})(), create=True))
    session._feature_ui(FeatureUiAction("back"))
    self.assertEqual(session.selected, Destination.STAR)

  def test_curve_adopt_confirmation_on_both_native_pages(self):
    from openpilot.starpilot.ui.runtime_app import StarShellSession
    from openpilot.system.ui.widgets import DialogResult

    class Dialog:
      def __init__(self, _question, *_args, callback=None, **_kwargs):
        self.confirm = callback or _args[-1]

    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      legacy = Path(params.get_param_path("CurvatureData"))
      legacy.write_bytes(b'{}')
      owner = FeatureSettingsOwner(params, lambda _group: True, vehicle_fingerprint=lambda: "TOYOTA COROLLA TSS2")
      row = next(row for row in owner.snapshot("curve", parked=True, system_long=True,
                     lateral_context=True, metric=False).rows if row.key == "curve_adopt")
      self.assertEqual(FeatureInput.target(1900, 160, FeatureSettingsState(page="curve", rows=(row,))).kind, "reset")
      large = StarShellSession.__new__(StarShellSession)
      self.enterContext(patch.object(large, "feature_request", owner.apply))
      pushed = []
      with patch("openpilot.system.ui.widgets.confirm_dialog.ConfirmDialog", Dialog), \
           patch("openpilot.starpilot.ui.runtime_app.gui_app.push_widget", pushed.append):
        large._confirm_feature_reset(row)
        self.assertIsNone(params.get("CurveComfortData"))
        pushed[-1].confirm(DialogResult.CONFIRM)
      self.assertIsNotNone(params.get("CurveComfortData"))

      params.remove("CurveComfortData")
      row = next(row for row in owner.snapshot("curve", parked=True, system_long=True,
                     lateral_context=True, metric=False).rows if row.key == "curve_adopt")
      class Session:
        def feature_snapshot(self, page):
          return owner.snapshot(page, parked=True, system_long=True, lateral_context=True, metric=False)
        def feature_request(self, request):
          return owner.apply(request)
      adapter = compact.FeatureSettingsCompact(Session())
      pushed = []
      with patch.object(compact, "BigConfirmationDialog", Dialog), \
           patch.object(compact.gui_app, "push_widget", pushed.append), \
           patch.object(compact.gui_app, "texture", lambda *_args: None):
        adapter._confirm_reset(row, lambda: None)
        legacy.write_bytes(b'{"0.001":{"average":2.0,"count":2}}')
        pushed[-1].confirm()
        self.assertIsNone(params.get("CurveComfortData"))
        row = next(row for row in owner.snapshot("curve", parked=True, system_long=True,
                       lateral_context=True, metric=False).rows if row.key == "curve_adopt")
        adapter._confirm_reset(row, lambda: None)
        pushed[-1].confirm()
      self.assertIsNotNone(params.get("CurveComfortData"))


if __name__ == "__main__":
  unittest.main()
