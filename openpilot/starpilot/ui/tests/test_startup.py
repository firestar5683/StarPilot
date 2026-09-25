"""The UI choice is final before Raylib creates a window."""

import unittest
from unittest.mock import patch

from openpilot.starpilot.ui import startup
from openpilot.starpilot.ui.presentation import Profile


class TestStartup(unittest.TestCase):
  def test_both_profiles_select_custom_with_exact_assets(self):
    for profile in (Profile.LARGE, Profile.COMPACT):
      with self.subTest(profile=profile), patch.object(startup, "validate_fonts") as fonts, \
           patch.object(startup, "validate_artwork") as artwork:
        choice = startup.select_ui(profile, {"STARPILOT_UI_FONT_DIR": "/reviewed"})
        self.assertTrue(choice.custom)
        fonts.assert_called_once_with(profile, "/reviewed")
        artwork.assert_called_once_with()

  def test_bundled_fonts_select_custom_and_explicit_bad_bundle_fails(self):
    for profile in (Profile.LARGE, Profile.COMPACT):
      with self.subTest(profile=profile), patch.object(startup, "validate_artwork") as artwork:
        choice = startup.select_ui(profile, {})
        self.assertTrue(choice.custom)
        artwork.assert_called_once_with()
      with patch.object(startup, "validate_artwork") as artwork:
        choice = startup.select_ui(profile, {"STARPILOT_UI_FONT_DIR": "/missing-fonts"})
        self.assertFalse(choice.custom)
        artwork.assert_not_called()
      with patch.object(startup, "validate_fonts"), patch.object(startup, "validate_artwork", side_effect=ValueError("bad hash")):
        self.assertIn("bad hash", startup.select_ui(profile, {"STARPILOT_UI_FONT_DIR": "/bad"}).reason)

  def test_force_fails_and_upstream_override_skips_preflight(self):
    with self.assertRaisesRegex(RuntimeError, "Forced StarPilot UI"):
      startup.select_ui(Profile.LARGE, {"STARPILOT_UI_DEV": "1", "STARPILOT_UI_FONT_DIR": "/missing-fonts"})
    with patch.object(startup, "validate_fonts") as fonts, patch.object(startup, "validate_artwork") as artwork:
      choice = startup.select_ui(Profile.COMPACT, {"STARPILOT_UI": "upstream", "STARPILOT_UI_DEV": "1"})
      self.assertFalse(choice.custom)
      fonts.assert_not_called()
      artwork.assert_not_called()

  def test_main_selects_before_window(self):
    from openpilot.selfdrive.ui import ui

    events: list[str] = []
    def selection(profile, environment):
      events.append(f"select:{profile}")
      return startup.UiSelection(False, "fixture")

    def window(_):
      events.append("window")

    with patch.object(ui, "select_ui", side_effect=selection), patch.object(ui.gui_app, "init_window", side_effect=window), \
         patch.object(ui.gui_app, "render", return_value=iter(())), patch.object(ui, "MainLayout", return_value=object()), \
         patch.object(ui, "MiciMainLayout", return_value=object()), patch.object(ui.messaging, "PubMaster"), \
         patch.object(ui, "config_realtime_process"), patch.object(ui, "BIG_UI", True):
      ui.main()
    self.assertEqual(events, ["select:large", "window"])

    with patch.object(ui, "select_ui", side_effect=RuntimeError("bad reviewed font")), \
         patch.object(ui.gui_app, "init_window") as initialize, patch.object(ui, "config_realtime_process"):
      with self.assertRaisesRegex(RuntimeError, "bad reviewed font"):
        ui.main()
      initialize.assert_not_called()

  def test_slc_publisher_gate_is_independent_of_ui_selection(self):
    self.assertTrue(startup.slc_action_transport_enabled({"STARPILOT_UI_DEV": "1"}))
    self.assertTrue(startup.slc_action_transport_enabled({"SLC_REPLAY_RUNTIME": "1"}))
    self.assertTrue(startup.slc_action_transport_enabled({"STARPILOT_UI": "upstream", "SLC_REPLAY_RUNTIME": "1"}))


if __name__ == "__main__":
  unittest.main()
