"""C4 reset clears only the supported saved detector state for the next start."""

from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import Mock, patch

from openpilot.common.params import Params
from openpilot.selfdrive.ui.mici.layouts.settings.device import device_layout
from openpilot.selfdrive.monitoring.policy import DriverMonitoring


class TestC4DriverMonitoringReset(unittest.TestCase):
  def test_active_preview_or_unparked_state_blocks_reset(self):
    panel = device_layout.DeviceLayoutMici.__new__(device_layout.DeviceLayoutMici)
    params = NS(get_bool=Mock(return_value=True), remove=Mock(), put_bool=Mock())
    with patch.object(device_layout, "ui_state", NS(params=params)), \
         patch.object(device_layout, "native_parked", return_value=True):
      self.assertFalse(panel._can_reset_driver_monitoring())
      panel._reset_driver_monitoring()
    params.remove.assert_not_called()
    params.put_bool.assert_not_called()

    params.get_bool.return_value = False
    with patch.object(device_layout, "ui_state", NS(params=params)), \
         patch.object(device_layout, "native_parked", return_value=False):
      panel._reset_driver_monitoring()
    params.remove.assert_not_called()

  def test_parked_reset_clears_detected_cache_and_requests_next_cycle(self):
    panel = device_layout.DeviceLayoutMici.__new__(device_layout.DeviceLayoutMici)
    params = NS(get_bool=Mock(return_value=False), remove=Mock(), put_bool=Mock())
    with patch.object(device_layout, "ui_state", NS(params=params)), \
         patch.object(device_layout, "native_parked", return_value=True):
      self.assertTrue(panel._can_reset_driver_monitoring())
      panel._reset_driver_monitoring()
    params.get_bool.assert_called_with("IsDriverViewEnabled")
    params.remove.assert_called_once_with("IsRhdDetected")
    params.put_bool.assert_called_once_with("OnroadCycleRequested", True, block=True)

  def test_real_saved_cache_changes_next_monitoring_instance_only(self):
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      params.put_bool("IsRhdDetected", True, block=True)
      current = DriverMonitoring(rhd_saved=params.get_bool("IsRhdDetected"), always_on=False)
      panel = device_layout.DeviceLayoutMici.__new__(device_layout.DeviceLayoutMici)
      with patch.object(device_layout, "ui_state", NS(params=params)), \
           patch.object(device_layout, "native_parked", return_value=True):
        panel._reset_driver_monitoring()
      next_start = DriverMonitoring(rhd_saved=params.get_bool("IsRhdDetected"), always_on=False)
      self.assertTrue(current.wheel_on_right_default)
      self.assertFalse(next_start.wheel_on_right_default)
      self.assertTrue(params.get_bool("OnroadCycleRequested"))
