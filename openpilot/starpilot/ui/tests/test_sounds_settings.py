"""Stock alert preferences through actual temporary Params and native requests."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from openpilot.common.params import Params
from openpilot.selfdrive.ui.soundd import ALERT_VOLUME_KEYS, CRITICAL_MAX, AudibleAlert, Soundd, sound_list
from openpilot.starpilot.audio.alert_volume import AUTO, VOLUMES, effective_volume, read_volume
from openpilot.starpilot.ui import sounds_compact
from openpilot.starpilot.ui.feature_settings_state import feature_row_top, FeatureInput, FeatureSettingsRequest, FeatureUiAction, row_change
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.settings_state import Destination, SettingsInput, SettingsState, tile_rects
from openpilot.starpilot.ui.sounds_owner import SoundsOwner
from openpilot.starpilot.ui.shell import ShellInput, ShellMode


class SoundsSettingsTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.parked = True
    self.owner = SoundsOwner(self.params, lambda: self.parked)

  def row(self, key):
    return next(row for row in self.owner.snapshot().rows if row.key == key)

  def test_absence_auto_no_writes_and_native_registry(self):
    state = self.owner.snapshot()
    self.assertEqual(len(state.rows), 8)
    for key, _, _ in VOLUMES:
      self.assertEqual(self.row(key).value, "Auto")
      self.assertEqual((self.row(key).step, self.row(key).maximum, self.row(key).unit), (5.0, 100.0, "%"))
      self.assertIsNone(read_volume(self.params, key).raw)
      self.assertEqual(self.params.get_type(key).name, "INT")

  def test_saved_choices_corruption_and_exact_source(self):
    engage = self.row("EngageVolume")
    engage_request = row_change(engage, 1)
    assert engage_request is not None
    self.assertTrue(self.owner.apply(engage_request))
    self.assertEqual(self.params.get("EngageVolume"), 0)
    self.assertFalse(self.owner.apply(engage_request))
    path = Path(self.params.get_param_path("WarningSoftVolume"))
    path.write_bytes(b"\xff")
    corrupt = self.row("WarningSoftVolume")
    self.assertEqual(corrupt.value, "Invalid saved level")
    self.assertEqual(path.read_bytes(), b"\xff")
    repair = row_change(corrupt)
    assert repair is not None
    self.assertTrue(self.owner.apply(repair))
    self.assertEqual(read_volume(self.params, "WarningSoftVolume").value, AUTO)
    self.assertFalse(self.owner.apply(repair))

  def test_historical_zero_levels_for_refuse_and_disengage(self):
    for key in ("RefuseVolume", "DisengageVolume"):
      request = row_change(self.row(key), 1)
      assert request is not None
      self.assertTrue(self.owner.apply(request))
      self.assertEqual(read_volume(self.params, key).value, 0)

  def test_fixed_volume_slider_preserves_warning_floor_and_auto(self):
    self.params.put("WarningImmediateVolume", 40, block=True)
    row = self.row("WarningImmediateVolume")
    self.assertEqual((row.value, row.minimum, row.maximum, row.step, row.unit, row.choices), ("40", 25.0, 100.0, 5.0, "%", ("Auto",)))
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(row.key, row.source, "20")))
    request = row_change(row)
    assert request is not None
    self.assertTrue(self.owner.apply(request))
    self.assertEqual(read_volume(self.params, row.key).value, 45)
    auto = row_change(self.row("sounds:auto:WarningImmediateVolume"))
    assert auto is not None
    self.assertTrue(self.owner.apply(auto))
    self.assertEqual(read_volume(self.params, row.key).value, AUTO)

  def test_parked_and_final_read_guards(self):
    request = row_change(self.row("RefuseVolume"), 1)
    assert request is not None
    self.parked = False
    self.assertFalse(self.owner.apply(request))
    self.assertIsNone(read_volume(self.params, "RefuseVolume").raw)
    self.parked = True
    original = self.params.get_param_path
    calls = 0
    def path(key):
      nonlocal calls
      calls += 1
      if calls == 2:
        raise OSError("lost source")
      return original(key)
    with patch.object(self.params, "get_param_path", side_effect=path):
      self.assertFalse(self.owner.apply(request))
    self.assertIsNone(read_volume(self.params, "RefuseVolume").raw)

  def test_oversized_and_unreadable_source_does_not_write(self):
    path = Path(self.params.get_param_path("WarningImmediateVolume"))
    original = b"9" * 100_000
    path.write_bytes(original)
    self.assertEqual(read_volume(self.params, "WarningImmediateVolume").value, None)
    oversized = self.row("WarningImmediateVolume")
    self.assertFalse(oversized.available)
    self.assertIsNone(row_change(oversized))
    self.assertEqual(path.read_bytes(), original)
    # Equal bounded prefixes do not authorize edits when the tail changed.
    path.write_bytes(original[:-1] + b"8")
    self.assertFalse(self.owner.apply(FeatureSettingsRequest("WarningImmediateVolume", oversized.source, "Auto")))
    self.assertFalse(self.row("WarningImmediateVolume").available)
    self.assertEqual(path.read_bytes(), original[:-1] + b"8")
    path.unlink()
    path.mkdir()
    unreadable = self.row("WarningImmediateVolume")
    self.assertFalse(unreadable.available)
    self.assertTrue(path.is_dir())

  def test_soundd_poll_reads_saved_values_without_touching_samples(self):
    sound = Soundd.__new__(Soundd)
    sound.pack_loader = Mock(is_builtin=Mock(return_value=False))
    sound.volume_params = self.params
    sound.saved_volumes = {key: AUTO for key, _, _ in VOLUMES}
    sound.volume_read_at = 0.0
    self.params.put("DisengageVolume", 45, block=True)
    sound.refresh_saved_volumes(1.0)
    self.assertEqual(sound.saved_volumes["DisengageVolume"], 45)
    self.params.put("DisengageVolume", 65, block=True)
    sound.refresh_saved_volumes(1.1)
    self.assertEqual(sound.saved_volumes["DisengageVolume"], 45)
    sound.refresh_saved_volumes(1.3)
    self.assertEqual(sound.saved_volumes["DisengageVolume"], 65)
    Path(self.params.get_param_path("WarningImmediateVolume")).write_bytes(b"0")
    sound.refresh_saved_volumes(1.6)
    self.assertIsNone(sound.saved_volumes["WarningImmediateVolume"])
    self.assertEqual(effective_volume("WarningImmediateVolume", sound.saved_volumes["WarningImmediateVolume"], 0.14,
                                      immediate_ramp=0.14), 0.14)

  def test_large_tile_press_cancel_and_sound_row_request(self):
    actions = []
    settings_input = SettingsInput(Profile.LARGE, actions.append)
    x, y, width, height = tile_rects(SettingsState())[0]
    settings_input.press(x + width / 2, y + height / 2, SettingsState())
    settings_input.release(x + width / 2, y + height / 2, SettingsState())
    self.assertEqual(actions[0].destination.destination, Destination.SOUNDS)
    received = []
    native = FeatureInput(received.append)
    state = self.owner.snapshot()
    native.press(1980, feature_row_top(state) + 112, state)
    native.move(1800, feature_row_top(state) + 112, state)
    native.release(1800, feature_row_top(state) + 112, state)
    self.assertFalse(received)
    native.press(1980, feature_row_top(state) + 112, state)
    native.release(1980, feature_row_top(state) + 112, state)
    self.assertEqual(row_change(received[0].row).key, "WarningImmediateVolume")

  def test_large_session_routes_saved_edit_and_back(self):
    from openpilot.starpilot.ui.runtime_app import StarShellSession
    session = StarShellSession.__new__(StarShellSession)
    session._mode = ShellMode.SETTINGS
    session.selected = Destination.SOUNDS
    session.sounds_owner = self.owner
    session.sounds_scroll = 0
    session._snapshot_cache = None
    session.input = ShellInput(Profile.LARGE, lambda _: None)
    row = self.row("EngageVolume")
    session._sounds_ui(FeatureUiAction("change", row, 1))
    self.assertEqual(read_volume(self.params, "EngageVolume").value, 0)
    self.parked = False
    session._sounds_ui(FeatureUiAction("change", self.row("EngageVolume"), 1))
    self.assertEqual(read_volume(self.params, "EngageVolume").value, 0)
    session._sounds_ui(FeatureUiAction("back"))
    self.assertEqual(session.selected, Destination.STAR)

  def test_compact_child_refreshes_after_saved_edit(self):
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
      def sounds_snapshot(inner):
        return self.owner.snapshot()
      def sounds_request(inner, request):
        return self.owner.apply(request)
    shown = []
    with patch.object(sounds_compact, "BigButton", Button), patch.object(sounds_compact, "GreyBigButton", Button), \
         patch.object(sounds_compact, "NavScroller", Scroller), patch.object(sounds_compact.gui_app, "push_widget", shown.append):
      sounds_compact.SoundsCompact(Session()).entry_button().click()
      page = shown[0]
      self.assertEqual(page.items[0].label, "sounds & alerts")
      plus = next(item for item in page.items if item.label == "engagement chime +")
      plus.click()
      self.assertEqual(read_volume(self.params, "EngageVolume").value, 0)
      self.assertIn("0%", next(item for item in page.items if item.label == "engagement chime +").value)

  def test_soundd_auto_samples_and_protected_warning_ramp(self):
    sound = Soundd.__new__(Soundd)
    sound.pack_loader = Mock(is_builtin=Mock(return_value=False))
    sound.current_alert = AudibleAlert.engage
    sound.current_sound = AudibleAlert.engage
    sound.current_sound_frame = 0
    sound.pending_stop = False
    sound.current_volume = 0.17
    sound.loaded_sounds = {AudibleAlert.engage: np.array([0.5, -0.5], dtype=np.float32),
                           AudibleAlert.warningImmediate: np.array([0.5, -0.5], dtype=np.float32)}
    sound.saved_volumes = {"EngageVolume": AUTO, "WarningImmediateVolume": AUTO}
    np.testing.assert_array_equal(sound.get_sound_data(2), np.array([0.085, -0.085], dtype=np.float32))
    sound.current_sound_frame = 0
    sound.saved_volumes["EngageVolume"] = 0
    np.testing.assert_array_equal(sound.get_sound_data(2), np.zeros(2, dtype=np.float32))
    sound.current_alert = AudibleAlert.warningImmediate
    sound.current_sound = AudibleAlert.warningImmediate
    sound.current_sound_frame = 0
    sound.saved_volumes["WarningImmediateVolume"] = 25
    np.testing.assert_array_equal(sound.get_sound_data(2), np.array([0.125, -0.125], dtype=np.float32))
    sound.current_sound_frame = 0
    sound.current_volume = 1.0
    np.testing.assert_array_equal(sound.get_sound_data(2), np.array([0.5, -0.5], dtype=np.float32))
    self.assertEqual(effective_volume("WarningImmediateVolume", None, 0.17, immediate_ramp=0.17), 0.17)

  def test_auto_matches_prior_gain_for_every_stock_family_and_timeout(self):
    sound = Soundd.__new__(Soundd)
    sound.pack_loader = Mock(is_builtin=Mock(return_value=False))
    waveform = np.array([0.5, -0.5], dtype=np.float32)
    sound.loaded_sounds = dict.fromkeys(sound_list, waveform)
    sound.saved_volumes = {key: AUTO for key, _, _ in VOLUMES}
    sound.current_volume = 0.17
    sound.pending_stop = False
    for alert in sound_list:
      if alert == CRITICAL_MAX:
        self.assertNotIn(alert, ALERT_VOLUME_KEYS)
      else:
        self.assertIn(alert, ALERT_VOLUME_KEYS)
      sound.current_alert = alert
      sound.current_sound = alert
      sound.current_sound_frame = 0
      np.testing.assert_array_equal(sound.get_sound_data(2), waveform * 0.17)
    # The existing timeout path produces the same immediate-warning alert.
    sound.current_alert = AudibleAlert.none
    sound.current_sound = AudibleAlert.none
    sound.current_sound_frame = 0
    sound.selfdrive_timeout_alert = False
    sm = type("State", (), {"updated": {"selfdriveState": False}})()
    with patch("openpilot.selfdrive.ui.soundd.check_selfdrive_timeout_alert", return_value=True):
      sound.get_audible_alert(sm)
    self.assertEqual(sound.current_alert, AudibleAlert.warningImmediate)
    self.assertTrue(sound.selfdrive_timeout_alert)
    np.testing.assert_array_equal(sound.get_sound_data(2), waveform * 0.17)
    sound.current_sound_frame = 0
    sound.current_volume = 0.83
    np.testing.assert_array_equal(sound.get_sound_data(2), waveform * 0.83)

  def test_looping_alert_final_chunk_keeps_producing_alert_gain(self):
    sound = Soundd.__new__(Soundd)
    sound.pack_loader = Mock(is_builtin=Mock(return_value=False))
    sound.current_alert = AudibleAlert.promptRepeat
    sound.current_sound = AudibleAlert.promptRepeat
    sound.current_sound_frame = 2
    sound.pending_stop = True
    sound.current_volume = 0.17
    sound.loaded_sounds = {AudibleAlert.promptRepeat: np.array([0.5, -0.5], dtype=np.float32)}
    sound.saved_volumes = {"PromptVolume": 0}
    np.testing.assert_array_equal(sound.get_sound_data(2), np.zeros(2, dtype=np.float32))
    self.assertEqual(sound.current_alert, AudibleAlert.none)
    sound.current_alert = AudibleAlert.promptRepeat
    sound.current_sound = AudibleAlert.promptRepeat
    sound.current_sound_frame = 2
    sound.pending_stop = True
    sound.saved_volumes["PromptVolume"] = AUTO
    np.testing.assert_array_equal(sound.get_sound_data(2), np.array([0.085, -0.085], dtype=np.float32))
