"""CPU-only checks for the current-UI projection frame boundary."""

import ast
from pathlib import Path
import unittest

from openpilot.starpilot.system.android_auto.current_car_ui import create_readback, scale_scissors, visible_geometry
from openpilot.starpilot.system.android_auto.projection_geometry import projection_geometry
from openpilot.starpilot.system.android_auto.frame_source import FrameRequest
from openpilot.starpilot.system.android_auto.identity import DEFAULT_CONFIG


SOURCE = Path(__file__).parents[1]


class TestCurrentDisplaySource(unittest.TestCase):
  def test_defaults_match_current_renderer_capabilities(self):
    self.assertEqual(DEFAULT_CONFIG['view'], 'car')
    self.assertTrue(DEFAULT_CONFIG['gpu_nv12'])        # current_car_ui converts with gpu_nv12.Nv12Converter
    self.assertTrue(DEFAULT_CONFIG['async_readback'])  # and publishes the asynchronous readback one step later
    self.assertTrue(DEFAULT_CONFIG['render_profile'])  # render_profile.RenderSampler, started by current_car_ui

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
    self.assertIn("pixels = readback.finish()", source)
    self.assertIn("producer.publish(request, pixels, in_flight_ns, pixel_format, advance=False)", source)

  def test_waiting_publishes_only_finished_frames(self):
    # Blocking on the LOW-priority GPU before the camera wait stacked ~30 ms on every frame.
    source = (SOURCE / "current_car_ui.py").read_text()
    self.assertEqual(source.count("if readback.pending and readback.ready():"), 2)
    self.assertIn("camera_pacer.wait(layout.camera_stream, now, step)", source)

  def test_nv12_path_fuses_scale_margins_and_conversion_without_an_output_texture(self):
    source = (SOURCE / "current_car_ui.py").read_text()
    self.assertIn("content = rl.load_render_texture(geometry.width, geometry.height)", source)
    self.assertIn("margin_w=request.margin_w, margin_h=request.margin_h, compose=True", source)
    self.assertIn("output = rl.load_render_texture(request.width, request.height) if converter is None else None", source)
    self.assertIn("regions = converter.convert(content.texture) if converter is not None else rgba_regions", source)

  def test_scissors_follow_the_ui_scale(self):
    # The UI clips in logical coordinates; the visible-size target needs them scaled like the drawing.
    calls = []
    rl = type("Rl", (), {})()
    rl.begin_scissor_mode = lambda *args: calls.append(args)
    scale_scissors(rl, 1.0)
    rl.begin_scissor_mode(30, 30, 1800, 1020)
    scale_scissors(rl, 800 / 1860)
    rl.begin_scissor_mode(30, 30, 1800, 1020)
    self.assertEqual(calls, [(30, 30, 1800, 1020), (12, 12, 775, 439)])

  def test_scissors_include_letterbox_offset(self):
    calls = []
    rl = type("Rl", (), {})()
    rl.begin_scissor_mode = lambda *args: calls.append(args)
    scale_scissors(rl, .5, 20, 40)
    rl.begin_scissor_mode(10, 30, 100, 50)
    self.assertEqual(calls, [(25, 55, 50, 25)])

  def test_view_uses_current_renderer(self):
    source = (SOURCE / "view.py").read_text()
    self.assertIn('"openpilot.starpilot.system.android_auto.current_car_ui"', source)
    self.assertNotIn('"openpilot.starpilot.system.android_auto.car_ui"', source)


if __name__ == "__main__":
  unittest.main()


class TestReadbackFallback(unittest.TestCase):
  def test_async_initialization_falls_back_without_changing_explicit_sync(self):
    from unittest.mock import Mock, call
    synchronous = Mock(asynchronous=False)
    factory = Mock(side_effect=[RuntimeError("PBO allocation failed"), synchronous])
    self.assertIs(create_readback(factory, 12, True), synchronous)
    self.assertEqual(factory.call_args_list, [call(12, asynchronous=True), call(12, asynchronous=False)])
    factory = Mock(side_effect=RuntimeError("readback unavailable"))
    with self.assertRaises(RuntimeError):
      create_readback(factory, 12, False)
    factory.assert_called_once_with(12, asynchronous=False)
