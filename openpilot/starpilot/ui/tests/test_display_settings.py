"""Saved display choices in real disposable Params and native UI adapters."""

import os
from types import SimpleNamespace as NS
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.starpilot.ui import display_compact
from openpilot.starpilot.ui.display_owner import DisplayOwner
from openpilot.starpilot.ui.display_preferences import MASTER, read_choice, read_preferences
from openpilot.starpilot.ui.feature_settings_state import FeatureInput, FeatureSettingsRequest, row_change
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.settings_state import Destination, SettingsInput, tile_rects
from openpilot.starpilot.ui.shell import ShellInput, ShellMode
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
    input_owner.press(1980, 320, state)
    input_owner.release(1980, 320, state)
    self.assertEqual(changed[0].row.key, MASTER)
    input_owner.press(1980, 320, state)
    input_owner.cancel()
    input_owner.release(1980, 320, state)
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
    session.drive_state = NS(snapshot=lambda: {"mode": "auto", "revision": None, "available": False,
                                                    "effective": None, "overrideAllowed": False})
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
