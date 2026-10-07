"""Saved display choices in real disposable Params and native UI adapters."""
from unittest.mock import Mock, patch
from dataclasses import replace


import os
from types import SimpleNamespace as NS
from pathlib import Path
import tempfile
import unittest

from openpilot.common.params import Params
from openpilot.starpilot.ui import display_compact
from openpilot.starpilot.ui.display_owner import DisplayOwner
from openpilot.starpilot.ui.display_preferences import MASTER, read_choice, read_preferences
from openpilot.starpilot.ui.feature_settings_state import (
  FEATURE_CONTROL_LEFT, FEATURE_CONTROL_RIGHT, FEATURE_ROW_HEIGHT, FEATURE_VISIBLE_ROWS,
  FeatureInput, FeatureSettingsRequest, feature_row_top, row_change,
  FeatureSettingsState, value_buttons, value_done_rect,
)
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.settings_state import Destination, SettingsInput, SettingsState, tile_rects
from openpilot.starpilot.ui.shell import ShellInput, ShellMode, ShellSnapshot
from openpilot.starpilot.ui.power_owner import PowerOwner, HOURS, VOLTS
from openpilot.system.ui.widgets import DialogResult
from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW, ui_fake


class DisplaySettingsTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.parked = True
    self.owner = DisplayOwner(self.params, lambda: self.parked)

  def row(self, key, profile=Profile.LARGE):
    return next(row for row in self.owner.snapshot(profile).rows if row.key == key)

  def request(self, key, profile=Profile.LARGE):
    request = row_change(self.row(key, profile))
    assert request is not None
    return request

  def large_session(self, expanded=True):
    from openpilot.starpilot.ui.runtime_app import StarShellSession
    session = StarShellSession.__new__(StarShellSession)
    session.profile = Profile.LARGE
    session._mode, session.selected = ShellMode.SETTINGS, Destination.SYSTEM
    session.display_owner = self.owner
    session.power_owner = PowerOwner(self.params, lambda: self.parked)
    session.map_snapshot = Mock(return_value=FeatureSettingsState())
    session.drive_state = NS(snapshot=lambda: {"mode": "auto", "revision": None, "available": False, "effective": None})
    session.display_scroll, session.display_edit_key = 0, None
    session.sidebar_expanded = expanded
    session._snapshot_cache = None
    session._on_destination_change = None
    session.confirmed_offroad = Mock(return_value=True)
    session.favorites, session.view = Mock(), Mock()
    session.view.display.reset.return_value = False
    session._unavailable = Mock()
    session.input = ShellInput(Profile.LARGE, session._emit)
    return session

  def touch(self, session, state, bounds):
    from openpilot.starpilot.ui import runtime_app
    state = replace(state, sidebar_expanded=session.sidebar_expanded)
    snapshot = ShellSnapshot(ShellMode.SETTINGS, Mock(), SettingsState(sidebar_expanded=session.sidebar_expanded), Mock(),
                             selected=Destination.SYSTEM, display=state)
    session.snapshot = Mock(return_value=snapshot)
    x, y, width, height = bounds
    with patch.object(runtime_app, "ui_state", NS(started=False, started_frame=0)):
      session.press(ShellMode.SETTINGS, x + width / 2, y + height / 2)
      session.move(ShellMode.SETTINGS, x + width / 2, y + height / 2)
      return session.release(ShellMode.SETTINGS, x + width / 2, y + height / 2)

  def test_system_presets_touch_save_confirm_and_done_from_overview_pages(self):
    from openpilot.starpilot.ui.runtime_app import SYSTEM_PRESETS
    self.params.put_bool(MASTER, True, block=True)
    steps = {"ScreenBrightness": ("25", "26"), "ScreenBrightnessOnroad": ("25", "26"),
             "ScreenTimeout": ("15", "20"), "ScreenTimeoutOnroad": ("15", "20"),
             HOURS: ("6 h", "7 h"), VOLTS: ("12.0 V", "12.1 V")}
    self.assertEqual(set(SYSTEM_PRESETS), set(steps))
    def fake_dialog(_question, _button, callback):
      return NS(callback=callback)
    with patch("openpilot.starpilot.ui.runtime_app.gui_app.push_widget") as pushed, \
         patch("openpilot.system.ui.widgets.confirm_dialog.ConfirmDialog", side_effect=fake_dialog), \
         patch("openpilot.starpilot.ui.runtime_app.native_device.invalidate_display_preferences"):
      for expanded in (True, False):
        for key, presets in SYSTEM_PRESETS.items():
          session = self.large_session(expanded)
          overview = session.system_snapshot()
          index = next(i for i, row in enumerate(overview.rows) if row.key == key)
          session.display_scroll = index // FEATURE_VISIBLE_ROWS * FEATURE_VISIBLE_ROWS
          overview = replace(overview, scroll=session.display_scroll)
          self.assertFalse(any(row.key.startswith("display:auto:") for row in overview.rows))
          y = feature_row_top(overview) + (index - overview.scroll) * FEATURE_ROW_HEIGHT
          self.assertTrue(self.touch(session, overview, (700, y, 200, FEATURE_ROW_HEIGHT)))
          self.assertEqual(session.display_edit_key, key)
          for value, _label in presets:
            editor = replace(session.system_snapshot(), sidebar_expanded=expanded)
            row = editor.rows[0]
            button = next(button for button in value_buttons(editor, row, feature_row_top(editor)) if button[0] == value)
            if not button[2]:
              continue
            pushed.reset_mock()
            self.assertTrue(self.touch(session, editor, button[1]))
            if key in (HOURS, VOLTS):
              self.assertEqual(session.system_snapshot().rows[0].source, row.source)
              dialog = pushed.call_args.args[0]
              dialog.callback(DialogResult.CANCEL)
              self.assertEqual(session.system_snapshot().rows[0].source, row.source)
              pushed.reset_mock()
              self.assertTrue(self.touch(session, editor, button[1]))
              pushed.call_args.args[0].callback(DialogResult.CONFIRM)
            else:
              pushed.assert_not_called()
            fresh = session.system_snapshot()
            self.assertEqual(fresh.rows[0].value, value)
            self.assertFalse(next(button for button in value_buttons(fresh, fresh.rows[0]) if button[0] == value)[2])
            if value == steps[key][0]:
              fresh = replace(fresh, sidebar_expanded=expanded)
              plus = value_buttons(fresh, fresh.rows[0], feature_row_top(fresh))[-1]
              self.assertTrue(self.touch(session, fresh, plus[1]))
              if key in (HOURS, VOLTS):
                pushed.call_args.args[0].callback(DialogResult.CONFIRM)
              self.assertEqual(session.system_snapshot().rows[0].value, steps[key][1])
          editor = replace(session.system_snapshot(), sidebar_expanded=expanded)
          before = editor.rows[0].source
          self.assertTrue(self.touch(session, editor, value_done_rect(editor)))
          self.assertIsNone(session.display_edit_key)
          self.assertEqual(session.selected, Destination.SYSTEM)
          self.assertEqual(session.display_scroll, overview.scroll)
          self.assertEqual(next(row for row in session.system_snapshot().rows if row.key == key).source, before)
          session._unavailable.assert_not_called()

  def test_system_editor_stale_dependencies_repairs_and_compact_snapshot(self):
    from openpilot.starpilot.ui.feature_settings_state import FeatureUiAction
    self.params.put_bool(MASTER, True, block=True)
    session = self.large_session()
    session.display_edit_key = "ScreenTimeout"
    editor = session.system_snapshot()
    button_index = next(i for i, button in enumerate(value_buttons(editor, editor.rows[0])) if button[0] == "60")
    self.params.put_bool(MASTER, False, block=True)
    session._display_ui(FeatureUiAction("action", editor.rows[0], button_index))
    self.assertIsNone(read_choice(self.params, "ScreenTimeout", large=True).raw)
    disabled = session.system_snapshot()
    self.assertTrue(all(not enabled for _, _, enabled in value_buttons(disabled, disabled.rows[0])))
    self.assertTrue(self.touch(session, disabled, value_done_rect(disabled)))
    Path(self.params.get_param_path("ScreenTimeout")).write_bytes(b"bad")
    session.display_edit_key = "ScreenTimeout"
    editor = session.system_snapshot()
    self.assertEqual(value_buttons(editor, editor.rows[0]), ())
    repair = (FEATURE_CONTROL_LEFT, feature_row_top(editor) + 36, FEATURE_CONTROL_RIGHT - FEATURE_CONTROL_LEFT, 82)
    with patch("openpilot.starpilot.ui.runtime_app.native_device.invalidate_display_preferences"):
      self.assertTrue(self.touch(session, editor, repair))
    self.assertEqual(read_choice(self.params, "ScreenTimeout", large=True).value, 30)
    session.profile = Profile.COMPACT
    self.assertEqual(session.display_snapshot(), self.owner.snapshot(Profile.COMPACT))
    self.assertTrue(all(not row.presets for row in session.system_snapshot().rows))

  def test_system_editor_bounds_and_changed_editor_cancel_touch(self):
    from openpilot.starpilot.ui import runtime_app
    self.params.put_bool(MASTER, True, block=True)
    self.params.put("ScreenBrightness", 100, block=True)
    session = self.large_session()
    session.display_edit_key = "ScreenBrightness"
    editor = session.system_snapshot()
    self.assertFalse(value_buttons(editor, editor.rows[0])[-1][2])
    self.params.put("ScreenBrightness", 5, block=True)
    editor = session.system_snapshot()
    self.assertFalse(value_buttons(editor, editor.rows[0])[0][2])
    session.display_edit_key = HOURS
    editor = session.system_snapshot()
    self.assertFalse(value_buttons(editor, editor.rows[0])[-1][2])
    session.display_edit_key = VOLTS
    editor = session.system_snapshot()
    self.assertFalse(value_buttons(editor, editor.rows[0])[0][2])
    session.display_edit_key = "ScreenBrightness"
    editor = session.system_snapshot()
    snapshot = ShellSnapshot(ShellMode.SETTINGS, Mock(), SettingsState(), Mock(), selected=Destination.SYSTEM, display=editor)
    session.snapshot = Mock(return_value=snapshot)
    with patch.object(runtime_app, "ui_state", NS(started=False, started_frame=0)):
      session.press(ShellMode.SETTINGS, 1200, 950)
      session.display_edit_key = "ScreenTimeout"
      self.assertFalse(session.release(ShellMode.SETTINGS, 1200, 950))
    self.assertEqual(session.display_edit_key, "ScreenTimeout")

  def test_absent_defaults_and_registered_keys_do_not_write(self):
    self.assertEqual(self.row(MASTER).value, "Off")
    self.assertEqual(self.row("ScreenBrightness").value, "Auto")
    self.assertEqual((self.row("ScreenBrightness").step, self.row("ScreenBrightness").maximum,
                      self.row("ScreenBrightness").unit), (1.0, 100.0, "%"))
    self.assertEqual((self.row("ScreenTimeout").value, self.row("ScreenTimeout").unit), ("30", "s"))
    self.assertEqual(self.row("ScreenTimeoutOnroad").value, "10")
    self.assertEqual(self.row("ScreenTimeoutOnroad", Profile.COMPACT).value, "5")
    self.assertEqual(list(Path(self.params.get_param_path(MASTER)).parent.iterdir()), [])
    for key in (MASTER, "ScreenBrightness", "ScreenBrightnessOnroad", "ScreenTimeout", "ScreenTimeoutOnroad"):
      self.assertIsNone(read_choice(self.params, key, large=True).raw)

  def test_master_enable_requires_valid_values_but_off_remains_available(self):
    path = Path(self.params.get_param_path("ScreenBrightnessOnroad"))
    path.write_bytes(b"0")
    self.assertEqual(self.row("ScreenBrightnessOnroad").value, "Saved Off (unsupported)")
    self.assertEqual(self.row("ScreenBrightnessOnroad").repair_value, "Auto")
    self.assertFalse(self.owner.apply(self.request(MASTER)))
    self.assertEqual(path.read_bytes(), b"0")
    self.assertTrue(self.owner.apply(self.request("ScreenBrightnessOnroad")))
    self.assertTrue(self.owner.apply(self.request(MASTER)))
    self.assertTrue(read_preferences(self.params, large=True).enabled)
    path.write_bytes(b"broken")
    self.assertTrue(self.owner.apply(self.request(MASTER)))
    self.assertFalse(read_preferences(self.params, large=True).enabled)
    self.assertEqual(path.read_bytes(), b"broken")

  def test_source_dependency_and_parked_guards(self):
    self.assertFalse(self.row("ScreenTimeout").available)
    self.params.put_bool(MASTER, True, block=True)
    request = row_change(self.row("ScreenTimeout"))
    assert request is not None
    self.params.put_bool(MASTER, False, block=True)
    self.assertFalse(self.owner.apply(request))
    self.params.put_bool(MASTER, True, block=True)
    request = row_change(self.row("ScreenTimeout"))
    assert request is not None
    self.parked = False
    self.assertFalse(self.owner.apply(request))
    self.parked = True
    checks = 0
    def parked_once():
      nonlocal checks
      checks += 1
      return checks == 1
    self.assertFalse(DisplayOwner(self.params, parked_once).apply(request))
    self.assertIsNone(read_choice(self.params, "ScreenTimeout", large=True).raw)
    self.params.put_bool(MASTER, False, block=True)
    self.assertFalse(self.owner.apply(request))

  def test_numeric_metadata_and_master_off_cannot_be_bypassed(self):
    row = self.row("ScreenTimeout")
    self.assertEqual((row.value, row.step, row.minimum, row.maximum, row.unit, row.choices), ("30", 5.0, 5.0, 60.0, "s", ()))
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(row.key, row.source, "35", dependencies=row.dependencies)))
    self.params.put_bool(MASTER, True, block=True)
    self.params.put("ScreenBrightness", 50, block=True)
    row = self.row("ScreenBrightness")
    self.assertEqual((row.value, row.step, row.minimum, row.maximum, row.unit, row.choices), ("50", 1.0, 5.0, 100.0, "%", ("Auto",)))
    self.assertTrue(self.owner.apply(self.request("ScreenBrightness")))
    self.assertEqual(read_choice(self.params, "ScreenBrightness", large=True).value, 51)
    self.assertTrue(self.owner.apply(self.request("display:auto:ScreenBrightness")))
    self.assertEqual(self.row("ScreenBrightness").value, "Auto")

  def test_final_source_and_master_freshness_prevent_write(self):
    self.params.put_bool(MASTER, True, block=True)
    request = self.request("ScreenTimeout")
    original_path = self.params.get_param_path
    key_reads = 0
    def unreadable_on_final(key):
      nonlocal key_reads
      if key == "ScreenTimeout":
        key_reads += 1
        if key_reads == 2:
          raise OSError("file became unreadable")
      return original_path(key)
    with patch.object(self.params, "get_param_path", side_effect=unreadable_on_final):
      self.assertFalse(self.owner.apply(request))
    self.assertIsNone(read_choice(self.params, "ScreenTimeout", large=True).raw)
    master_reads = 0
    def changed_master_on_final(key):
      nonlocal master_reads
      if key == MASTER:
        master_reads += 1
        if master_reads == 2:
          Path(original_path(MASTER)).write_bytes(b"0")
      return original_path(key)
    with patch.object(self.params, "get_param_path", side_effect=changed_master_on_final):
      self.assertFalse(self.owner.apply(request))
    self.assertIsNone(read_choice(self.params, "ScreenTimeout", large=True).raw)

  def test_corrupt_oversized_and_nonregular_are_preserved(self):
    path = Path(self.params.get_param_path("ScreenBrightness"))
    path.write_bytes(b"\xff")
    self.assertEqual(self.row("ScreenBrightness").value, "Invalid saved choice")
    self.assertTrue(self.owner.apply(self.request("ScreenBrightness")))
    self.assertEqual(path.read_bytes(), b"101")
    oversized = b"1" * 100_000
    path.write_bytes(oversized)
    row = self.row("ScreenBrightness")
    self.assertFalse(row.available)
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(row.key, row.source, "Auto", dependencies=row.dependencies)))
    self.assertEqual(path.read_bytes(), oversized)
    path.unlink()
    target = path.parent / "target"
    target.write_bytes(b"101")
    path.symlink_to(target)
    self.assertFalse(self.row("ScreenBrightness").available)
    path.unlink()
    os.mkfifo(path)
    self.assertFalse(self.row("ScreenBrightness").available)

  def test_native_press_and_compact_refresh(self):
    changed = []
    input_owner = FeatureInput(changed.append)
    state = self.owner.snapshot(Profile.LARGE)
    visible_row = next(index for index, row in enumerate(state.rows) if row.key == MASTER) - state.scroll
    self.assertTrue(0 <= visible_row < FEATURE_VISIBLE_ROWS)
    x = (FEATURE_CONTROL_LEFT + FEATURE_CONTROL_RIGHT) / 2
    y = feature_row_top(state) + (visible_row + .5) * FEATURE_ROW_HEIGHT
    input_owner.press(x, y, state)
    input_owner.release(x, y, state)
    self.assertEqual(changed[0].row.key, MASTER)
    input_owner.press(x, y, state)
    input_owner.cancel()
    input_owner.release(x, y, state)
    self.assertEqual(len(changed), 1)
    class Button:
      def __init__(self, label, value):
        self.label, self.value, self.click = label, value, None
      def set_click_callback(self, callback):
        self.click = callback
    class Scroller:
      def __init__(self):
        self._scroller = self
        self.items = []
      def add_widgets(self, cards):
        self.items.extend(cards)
    class Session:
      def display_snapshot(inner):
        return self.owner.snapshot(Profile.COMPACT)
      def display_request(inner, request):
        return self.owner.apply(request)
    shown = []
    with patch.object(display_compact, "BigButton", Button), patch.object(display_compact, "GreyBigButton", Button), \
         patch.object(display_compact, "NavScroller", Scroller), patch.object(display_compact.gui_app, "push_widget", shown.append):
      display_compact.DisplayCompact(Session()).entry_button().click()
      page = shown[0]
      self.assertEqual(page.items[0].label, "display")
      page.items[1].click()
      self.assertEqual(page.items[1].value, "on")
      self.assertTrue(read_preferences(self.params, large=False).enabled)

  def test_large_system_tile_routes_to_display_and_back(self):
    from openpilot.starpilot.ui.runtime_app import StarShellSession
    from openpilot.starpilot.ui.runtime_snapshot import RuntimeSnapshotAdapter
    from openpilot.starpilot.ui.feature_settings_state import FeatureUiAction
    ui = ui_fake()
    ui.params = self.params
    ui.started = False
    ui.sm.messages["deviceState"].started = False
    ui.sm.messages["pandaStates"][0].ignitionLine = False
    adapter = RuntimeSnapshotAdapter(ui)
    snapshot = adapter.build(ShellMode.SETTINGS, now_ns=NOW)
    self.assertTrue(snapshot.settings.destination(Destination.SYSTEM).available)
    emitted = []
    settings_input = SettingsInput(Profile.LARGE, emitted.append)
    x, y, width, height = tile_rects(snapshot.settings)[3]
    settings_input.press(x + width / 2, y + height / 2, snapshot.settings)
    settings_input.release(x + width / 2, y + height / 2, snapshot.settings)
    self.assertEqual(emitted[0].destination.destination, Destination.SYSTEM)
    session = StarShellSession.__new__(StarShellSession)
    self.enterContext(patch.object(session, 'drive_state', NS(snapshot=lambda: {"mode": "auto", "revision": None, "available": False,
                                                    "effective": None, "overrideAllowed": False}), create=True))
    session._mode = ShellMode.SETTINGS
    session.selected = Destination.SYSTEM
    session.display_owner = self.owner
    from openpilot.starpilot.ui.power_owner import PowerOwner
    session.power_owner = PowerOwner(self.params, lambda: self.parked)
    session.display_scroll = 0
    session._snapshot_cache = None
    session.input = ShellInput(Profile.LARGE, lambda _: None)
    session.profile = Profile.LARGE
    session._display_ui(FeatureUiAction("back"))
    self.assertEqual(session.selected, Destination.STAR)
