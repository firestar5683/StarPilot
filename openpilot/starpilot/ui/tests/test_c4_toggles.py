"""Original C4 Safe Mode interaction remains effective in the current native panel."""

from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import Mock, patch

from openpilot.common.params import Params
from openpilot.selfdrive.ui.mici.layouts.settings import toggles


class TestC4SafeMode(unittest.TestCase):
  def test_safe_mode_clears_experimental_choice_and_relaxes_personality(self):
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      params.put_bool("SafeMode", True, block=True)
      params.put_bool("ExperimentalMode", True, block=True)
      params.put("LongitudinalPersonality", 0, block=True)
      panel = toggles.TogglesLayoutMici.__new__(toggles.TogglesLayoutMici)
      panel._safe_mode_btn = Mock()
      panel._experimental_btn = Mock()
      panel._personality_toggle = Mock()
      panel._metric_toggle = Mock()
      self.enterContext(patch.object(panel, "_slc_offsets", NS(_raw=lambda _key: b"0"), create=True))
      toggles_to_refresh = (("SafeMode", panel._safe_mode_btn), ("ExperimentalMode", panel._experimental_btn))
      self.enterContext(patch.object(panel, "_refresh_toggles", toggles_to_refresh, create=True))
      fake_ui = NS(params=params, CP=None, update_params=Mock())
      with patch.object(toggles, "ui_state", fake_ui):
        panel._update_toggles()
      self.assertFalse(params.get_bool("ExperimentalMode"))
      self.assertEqual(params.get("LongitudinalPersonality"), 2)
      panel._experimental_btn.set_enabled.assert_called_once_with(False)
      panel._personality_toggle.set_enabled.assert_called_once_with(False)
      panel._personality_toggle.set_value.assert_called_once_with("relaxed")
