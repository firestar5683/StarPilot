import fcntl
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import time
import unittest
from unittest.mock import patch

import pyray as rl

from openpilot.common.params import Params
from openpilot.selfdrive.ui.layouts.settings import device
from openpilot.selfdrive.ui.mici.layouts.settings.device import device_layout
from openpilot.starpilot.ui.calibration_reset import CalibrationReset
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import DialogResult


class TestCalibrationReset(unittest.TestCase):
  def setUp(self):
    directory = tempfile.TemporaryDirectory()
    self.addCleanup(directory.cleanup)
    self.root = Path(directory.name)
    self.params = Params(directory.name)
    self.reset = CalibrationReset()
    self.ui = NS(params=self.params, engaged=False, ignition=False, is_offroad=lambda: True,
                 prime_state=NS(is_paired=lambda: False))
    self.enterContext(patch.object(device_layout, "ui_state", self.ui))
    self.enterContext(patch.object(device_layout, "Params", return_value=self.params))
    self.enterContext(patch.object(device_layout, "calibration_reset", self.reset))
    self.enterContext(patch.object(device, "ui_state", self.ui))
    self.enterContext(patch.object(device, "calibration_reset", self.reset))
    self.enterContext(patch.object(gui_app, "font", return_value=rl.Font()))
    self.enterContext(patch.object(gui_app, "texture", return_value=NS(width=64, height=64)))
    self.pushed = self.enterContext(patch.object(gui_app, "push_widget"))
    self.panel = device_layout.DeviceLayoutMici()
    self.button = next(item for item in self.panel._scroller._items
                       if hasattr(item, "get_text") and item.get_text() == "reset calibration")

  def wait_for_reset(self):
    deadline = time.monotonic() + 3
    while self.reset.pending and time.monotonic() < deadline:
      time.sleep(.01)
    self.assertFalse(self.reset.pending, "Calibration reset did not finish")

  def confirm(self):
    self.button._click_callback()
    self.pushed.call_args.args[0]._confirm_callback()

  def test_native_confirmation_returns_during_params_contention_and_coalesces(self):
    keys = ("CalibrationParams", "LiveTorqueParameters", "LiveParametersV2", "LiveDelay")
    for key in keys:
      self.params.put(key, b"existing learned cache", block=True)
    self.params.put_bool("ShowSpeedLimits", False, block=True)
    with (self.root / ".lock").open("a") as lock:
      fcntl.flock(lock, fcntl.LOCK_EX)
      try:
        start = time.monotonic()
        self.confirm()
        self.assertLess(time.monotonic() - start, .5)
        self.assertTrue(self.reset.pending)
        self.assertFalse(self.button.enabled)
        self.assertFalse(self.reset.request(self.params))
        self.assertFalse(self.params.get_bool("OnroadCycleRequested"))
        self.assertIsNotNone(self.params.get("CalibrationParams"))
      finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
    self.wait_for_reset()
    for key in keys:
      self.assertFalse(Path(self.params.get_param_path(key)).exists())
    self.assertTrue(self.params.get_bool("OnroadCycleRequested"))
    self.assertFalse(self.params.get_bool("DoReboot"))
    self.assertFalse(self.params.get_bool("ShowSpeedLimits"))
    self.assertFalse(self.reset.request(self.params))

  def test_confirmation_rechecks_engagement(self):
    self.params.put("CalibrationParams", b"saved", block=True)
    self.button._click_callback()
    confirm = self.pushed.call_args.args[0]._confirm_callback
    self.ui.engaged = True
    confirm()
    self.assertFalse(self.button.enabled)
    self.assertEqual(self.params.get("CalibrationParams"), b"saved")
    self.assertFalse(self.params.get_bool("OnroadCycleRequested"))

  def test_c3_cancel_and_action_guard_prevent_reset(self):
    panel = device.DeviceLayout.__new__(device.DeviceLayout)
    panel._params = self.params
    panel._calibration_reset_pending = False
    guard = [True]
    with patch.object(device, "ConfirmDialog") as dialog:
      panel._reset_calibration_prompt(lambda: guard[0])
    confirm = dialog.call_args.kwargs["callback"]
    confirm(DialogResult.CANCEL)
    guard[0] = False
    confirm(DialogResult.CONFIRM)
    self.assertFalse(self.reset.pending)
    self.assertFalse(self.params.get_bool("OnroadCycleRequested"))
    guard[0] = True
    confirm(DialogResult.CONFIRM)
    self.wait_for_reset()
    self.assertTrue(self.params.get_bool("OnroadCycleRequested"))

  def test_absent_caches_reset_normally(self):
    self.confirm()
    self.wait_for_reset()
    self.assertIsNone(self.reset.take_error())
    self.assertTrue(self.params.get_bool("OnroadCycleRequested"))

  def test_failed_delete_is_reported_once_without_requesting_cycle(self):
    self.params.put("CalibrationParams", b"saved", block=True)
    with patch.object(self.params, "remove", return_value=None):
      self.confirm()
      self.wait_for_reset()
    self.assertFalse(self.params.get_bool("OnroadCycleRequested"))
    self.assertEqual(self.params.get("CalibrationParams"), b"saved")
    self.pushed.reset_mock()
    self.panel._update_state()
    self.pushed.assert_called_once()
    self.panel._update_state()
    self.pushed.assert_called_once()
    self.assertFalse(self.reset.pending)
