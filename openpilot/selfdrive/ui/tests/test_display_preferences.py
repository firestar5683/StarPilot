"""Native Device policy with saved display choices and no hardware calls."""

from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import Mock, patch

from openpilot.common.params import Params
from openpilot.selfdrive.ui import ui_state as module
from openpilot.starpilot.ui.display_preferences import read_preferences


class DisplayDeviceTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.state = NS(params=self.params, started=False, ignition=False, light_sensor=-1,
                    projection_read_only=False, sm=NS(valid={}, alive={}))
    self.patches = [patch.object(module, "ui_state", self.state),
                    patch.object(module.gui_app, "big_ui", return_value=True),
                    patch.object(module.HARDWARE, "set_display_power"),
                    patch.object(module.HARDWARE, "set_screen_brightness")]
    for guard in self.patches:
      guard.start()
      self.addCleanup(guard.stop)
    filter_guard = patch.object(module.FirstOrderFilter, "update", autospec=True,
                                side_effect=lambda _filter, value: value)
    self.filter_update = filter_guard.start()
    self.addCleanup(filter_guard.stop)
    self.device = module.Device()

  def test_absent_master_matches_existing_auto_and_timeout_policy(self):
    self.device._refresh_display_preferences()
    self.assertFalse(self.device._display_preferences.enabled)
    self.assertEqual(self.device.interactive_timeout, 30)
    self.device._update_brightness()
    self.assertEqual(self.device._brightness_target, module.BACKLIGHT_OFFROAD)
    self.state.started = self.state.ignition = True
    self.state.light_sensor = 100
    self.assertEqual(self.device.interactive_timeout, 10)
    self.device._update_brightness()
    self.assertEqual(self.device._brightness_target, 100)
    self.device._awake = False
    self.device._update_brightness()
    self.assertEqual(self.device._brightness_target, 0)

  def test_manual_target_uses_existing_filter_and_wake_zero(self):
    self.params.put_bool("StarPilotDisplayPreferencesEnabled", True, block=True)
    self.params.put("ScreenBrightness", 40, block=True)
    self.params.put("ScreenBrightnessOnroad", 75, block=True)
    self.params.put("ScreenTimeout", 45, block=True)
    self.params.put("ScreenTimeoutOnroad", 20, block=True)
    self.device._refresh_display_preferences()
    self.assertEqual(self.device.interactive_timeout, 45)
    self.device._update_brightness()
    self.filter_update.assert_called_with(self.device._brightness_filter, 40)
    self.state.started = self.state.ignition = True
    self.assertEqual(self.device.interactive_timeout, 20)
    self.device._update_brightness()
    self.filter_update.assert_called_with(self.device._brightness_filter, 75)
    self.device._awake = False
    self.device._update_brightness()
    self.assertEqual(self.device._brightness_target, 0)
    self.device.set_override_interactive_timeout(7)
    self.assertEqual(self.device.interactive_timeout, 7)

  def test_bounded_reads_invalidation_and_ignition_transition(self):
    with patch.object(module, "read_preferences", wraps=read_preferences) as reads, \
         patch.object(module.time, "monotonic", side_effect=[10.0, 10.2, 11.1, 11.2]):
      self.device._refresh_display_preferences()
      self.device._refresh_display_preferences()
      self.assertEqual(reads.call_count, 1)
      self.device._refresh_display_preferences()
      self.assertEqual(reads.call_count, 2)
      self.device.invalidate_display_preferences()
      self.device._refresh_display_preferences()
      self.assertEqual(reads.call_count, 3)
    self.params.put_bool("StarPilotDisplayPreferencesEnabled", True, block=True)
    self.device.invalidate_display_preferences()
    self.device._refresh_display_preferences()
    self.device._interaction_time = 1
    with patch.object(self.device, "_reset_interactive_timeout") as reset:
      self.state.ignition = True
      self.device._update_wakefulness()
      reset.assert_called_once()
    self.assertTrue(self.device.awake)

  def test_invalid_saved_values_fail_to_existing_auto_policy(self):
    self.params.put_bool("StarPilotDisplayPreferencesEnabled", True, block=True)
    self.params.put("ScreenBrightnessOnroad", 0, block=True)
    saved = read_preferences(self.params, large=True)
    self.assertTrue(saved.enabled)
    self.assertEqual(saved.driving_brightness, 101)
    self.params.put("ScreenTimeoutOnroad", 999, block=True)
    self.assertEqual(read_preferences(self.params, large=True).driving_timeout, 10)

  def test_started_transition_refreshes_saved_profile_without_worker_restart(self):
    self.params.put_bool("StarPilotDisplayPreferencesEnabled", True, block=True)
    self.params.put("ScreenBrightnessOnroad", 80, block=True)
    with patch.object(self.device, "_start_brightness_thread") as start, \
         patch.object(module, "read_preferences", wraps=read_preferences) as reads:
      self.device.update()
      self.device.update()
      self.assertEqual(reads.call_count, 1)
      self.state.started = self.state.ignition = True
      self.device.update()
      self.assertEqual(reads.call_count, 2)
      self.assertEqual(self.filter_update.call_args.args[-1], 80)
      self.assertEqual(start.call_count, 3)

  def test_parked_timeout_callback_and_ignition_wake(self):
    self.params.put_bool("StarPilotDisplayPreferencesEnabled", True, block=True)
    self.params.put("ScreenTimeout", 5, block=True)
    self.device._refresh_display_preferences()
    callback = Mock()
    self.device.add_interactive_timeout_callback(callback)
    self.device._interaction_time = 1
    with patch.object(module, "PC", False), patch.object(module.gui_app, "set_should_render") as render:
      self.device._update_wakefulness()
      callback.assert_called_once()
      self.assertFalse(self.device.awake)
      render.assert_called_with(False)
      self.state.ignition = True
      self.device._update_wakefulness()
      self.assertTrue(self.device.awake)
      render.assert_called_with(True)
