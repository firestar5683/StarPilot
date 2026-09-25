import unittest
from unittest.mock import Mock, patch

from openpilot.starpilot.ui.layout_preview_runtime import LayoutPreviewRuntime


class LayoutPreviewRuntimeTests(unittest.TestCase):
  def test_start_failure_leaves_ui_available(self):
    with patch("openpilot.starpilot.ui.layout_preview_runtime.LayoutPreviewRenderer") as renderer_type, \
         patch("openpilot.starpilot.ui.layout_preview_runtime.PreviewService") as service_type:
      service_type.return_value.start.side_effect = OSError("occupied")
      authority = Mock()
      runtime = LayoutPreviewRuntime(None, "large", authority=authority)
      runtime.poll()
      service_type.return_value.poll.assert_not_called()
      service_type.return_value.close.assert_called_once()
      runtime.close()
      renderer_type.return_value.close.assert_called_once()
      authority.close.assert_called_once()

  def test_parked_loss_releases_canvas_before_transport_poll(self):
    events = []
    authority = Mock()
    authority.parked.return_value = False
    with patch("openpilot.starpilot.ui.layout_preview_runtime.LayoutPreviewRenderer") as renderer_type, \
         patch("openpilot.starpilot.ui.layout_preview_runtime.PreviewService") as service_type:
      renderer = renderer_type.return_value
      renderer.has_resources = True
      renderer.close.side_effect = lambda: events.append("release")
      service_type.return_value.poll.side_effect = lambda: events.append("poll")
      runtime = LayoutPreviewRuntime(None, "compact", authority=authority)
      runtime.poll()
      self.assertEqual(events, ["release", "poll"])
      runtime.close()

  def test_warmup_primes_fresh_source_then_stops_idle_reads(self):
    authority = Mock()
    authority.parked.side_effect = [False, True]
    with patch("openpilot.starpilot.ui.layout_preview_runtime.LayoutPreviewRenderer") as renderer_type, \
         patch("openpilot.starpilot.ui.layout_preview_runtime.PreviewService") as service_type, \
         patch("openpilot.starpilot.ui.layout_preview_runtime.time.monotonic", side_effect=[10.0, 10.05, 10.11, 20.0]):
      renderer_type.return_value.has_resources = False
      runtime = LayoutPreviewRuntime(None, "large", authority=authority)
      runtime.poll()
      runtime.poll()
      runtime.poll()
      runtime.poll()
      self.assertEqual(authority.parked.call_count, 2)
      self.assertEqual(service_type.return_value.poll.call_count, 4)
      service_type.assert_called_once_with(renderer_type.return_value, authority.parked, active_profile="large")
      runtime.close()

  def test_onroad_hint_defers_warmup_until_parked_then_restarts(self):
    authority = Mock()
    authority.parked.return_value = True
    hint = Mock(side_effect=[False, True, False, True])
    with patch("openpilot.starpilot.ui.layout_preview_runtime.LayoutPreviewRenderer") as renderer_type, \
         patch("openpilot.starpilot.ui.layout_preview_runtime.PreviewService"), \
         patch("openpilot.starpilot.ui.layout_preview_runtime.time.monotonic", side_effect=[1.0, 2.0, 3.0, 4.0]):
      renderer_type.return_value.has_resources = False
      runtime = LayoutPreviewRuntime(None, "compact", offroad_hint=hint, authority=authority)
      for _ in range(4):
        runtime.poll()
      self.assertEqual(authority.parked.call_count, 2)
      runtime.close()


if __name__ == "__main__":
  unittest.main()
