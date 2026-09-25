"""CPU-only checks for the current-UI projection frame boundary."""

import ast
from pathlib import Path
import unittest

from openpilot.starpilot.system.android_auto.current_car_ui import visible_geometry
from openpilot.starpilot.system.android_auto.projection_geometry import projection_geometry
from openpilot.starpilot.system.android_auto.frame_source import FrameRequest
from openpilot.starpilot.system.android_auto.identity import DEFAULT_CONFIG


SOURCE = Path(__file__).parents[1]


class TestCurrentDisplaySource(unittest.TestCase):
  def test_defaults_match_current_renderer_capabilities(self):
    self.assertEqual(DEFAULT_CONFIG['view'], 'car')
    self.assertFalse(DEFAULT_CONFIG['gpu_nv12'])
    self.assertFalse(DEFAULT_CONFIG['async_readback'])
    self.assertFalse(DEFAULT_CONFIG['render_profile'])

  def test_visible_geometry_never_crops_current_ui(self):
    for width, height, margin_w, margin_h in ((1280, 720, 0, 0), (1920, 1080, 160, 80), (1280, 720, 0, 240), (800, 600, 0, 0)):
      request = FrameRequest(width, height, margin_w, margin_h, 33_333)
      visible_w, visible_h, scale, x, y = visible_geometry(request)
      self.assertGreater(scale, 0)
      self.assertGreaterEqual(x, 0)
      self.assertGreaterEqual(y, 0)
      geometry = projection_geometry(width, height, margin_w, margin_h)
      self.assertEqual((x, y), (0, 0))
      self.assertAlmostEqual(geometry.logical_width * scale, visible_w, delta=0.5)
      self.assertAlmostEqual(geometry.logical_height * scale, visible_h, delta=0.5)
      self.assertGreaterEqual(geometry.logical_width, 1860)
      self.assertGreaterEqual(geometry.logical_height, 1080)

  def test_current_renderer_avoids_donor_ui_and_uses_frame_contract(self):
    source = (SOURCE / "current_car_ui.py").read_text()
    tree = ast.parse(source)
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    self.assertIn("openpilot.starpilot.system.android_auto.projection_onroad", imports)
    self.assertNotIn("openpilot.starpilot.ui.runtime_app", imports)
    self.assertIn("openpilot.starpilot.system.android_auto.frame_source", imports)
    self.assertNotIn("openpilot.starpilot.system.android_auto.ui.main", imports)
    self.assertIn("producer.publish(request, readback.finish(), captured_ns)", source)

  def test_view_uses_current_renderer(self):
    source = (SOURCE / "view.py").read_text()
    self.assertIn('"openpilot.starpilot.system.android_auto.current_car_ui"', source)
    self.assertNotIn('"openpilot.starpilot.system.android_auto.car_ui"', source)


if __name__ == "__main__":
  unittest.main()
