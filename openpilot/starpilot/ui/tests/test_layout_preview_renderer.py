
from unittest.mock import patch
import io
import struct
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
import zlib

from openpilot.starpilot.ui.layout_preview_renderer import LayoutPreviewRenderer, _Canvas, _DriverMonitorArt, _png_rgba, sample_state
from openpilot.starpilot.ui.layout_preview_sidebar import SAMPLE_METRICS, metric_rects, render_sidebar
from openpilot.starpilot.ui.onroad_customization import default_document
from openpilot.starpilot.ui.presentation import Profile
import pyray as rl


class LayoutPreviewRendererTests(unittest.TestCase):
  def test_fixed_scenes_have_no_camera_or_live_input(self):
    document = default_document()
    expected = {
      "engaged": (True, True), "aol": (True, False), "long_only": (False, True),
      "experimental": (True, True), "braking": (True, True), "slc_pending": (True, True),
      "cem_stop_light": (True, True), "cem_lead": (True, True), "cem_curve": (True, True),
    }
    for name, axes in expected.items():
      with self.subTest(name=name):
        state = sample_state(name, document)
        self.assertFalse(state.camera_available)
        self.assertEqual((state.lateral_active, state.longitudinal_active), axes)
        self.assertEqual(state.alert.size, "none")
        self.assertEqual(state.wheel_feedback.brake_pressed, name == "braking")
        self.assertTrue(state.appearance.show_speed_limit_sign)
        if state.lateral_active:
          self.assertGreater(state.torque_utilization, 0.5)
        else:
          self.assertEqual(state.torque_utilization, 0)
    from openpilot.starpilot.ui.onroad_state import slc_controls
    pending = sample_state("slc_pending", document)
    for profile in (Profile.LARGE, Profile.COMPACT):
      self.assertEqual([item.label for item in slc_controls(profile, pending)], ["ACCEPT", "REJECT"])
      self.assertFalse(slc_controls(profile, sample_state("engaged", document)))
    manual = sample_state("experimental", document)
    self.assertTrue(manual.experimental_enabled)
    self.assertIsNone(manual.visual_preview)
    self.assertIsNone(manual.conditional_effective)
    for scene, reason in (("cem_stop_light", "STOP LIGHT"), ("cem_lead", "LEAD"), ("cem_curve", "CURVE")):
      with self.subTest(scene=scene):
        sample = sample_state(scene, document)
        self.assertTrue(sample.experimental_enabled)
        self.assertEqual(sample.visual_preview.cem_reason, reason)
        self.assertIsNone(sample.conditional_effective)
        self.assertEqual(sample.visual_preview.label, "SYNTHETIC REPLAY PREVIEW")
    self.assertEqual(sample_state("cem_lead", document).speed_mps, 0.0)
    with self.assertRaises(ValueError):
      sample_state("live", document)

  def test_invalid_draft_rejected_before_gl_resources(self):
    renderer = LayoutPreviewRenderer()
    document = default_document()
    document["layouts"]["large"]["current_speed"]["x"] = -1
    with patch("openpilot.starpilot.ui.layout_preview_renderer._Canvas") as canvas:
      with self.assertRaises(ValueError):
        renderer({"document": document, "profile": "large", "scene": "engaged"})
      canvas.assert_not_called()

  def test_profile_swap_and_inactivity_release_owned_canvas(self):
    renderer = LayoutPreviewRenderer()
    document = default_document()
    with patch("openpilot.starpilot.ui.layout_preview_renderer.rl.is_window_ready", return_value=True), \
         patch("openpilot.starpilot.ui.layout_preview_renderer._Canvas") as canvas_type, \
         patch("openpilot.starpilot.ui.layout_preview_renderer.time.monotonic", side_effect=[10.0, 11.0, 50.0]):
      first, second = Mock(profile=Profile.LARGE), Mock(profile=Profile.COMPACT)
      first.render.return_value = second.render.return_value = b"png"
      canvas_type.side_effect = [first, second]
      self.assertEqual(renderer({"document": document, "profile": "large", "scene": "aol"}), b"png")
      self.assertEqual(renderer({"document": document, "profile": "compact", "scene": "aol"}), b"png")
      first.close.assert_called_once()
      renderer.expire()
      second.close.assert_called_once()

  def test_png_encoder_preserves_rgba_pixels(self):
    pixels = bytes((255, 0, 0, 255, 0, 255, 0, 128))
    png = _png_rgba(2, 1, pixels)
    self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
    stream = io.BytesIO(png[8:])
    chunks = {}
    while length_bytes := stream.read(4):
      length = struct.unpack(">I", length_bytes)[0]
      kind = stream.read(4)
      data = stream.read(length)
      crc = struct.unpack(">I", stream.read(4))[0]
      self.assertEqual(crc, zlib.crc32(kind + data) & 0xffffffff)
      chunks[kind] = data
    self.assertEqual(struct.unpack(">II", chunks[b"IHDR"][:8]), (2, 1))
    self.assertEqual(zlib.decompress(chunks[b"IDAT"]), b"\0" + pixels)

  def test_compact_sample_seeds_settled_native_widget_filters(self):
    canvas = _Canvas.__new__(_Canvas)
    canvas.profile = Profile.COMPACT
    canvas.viewport = None
    self.enterContext(patch.object(canvas, 'view', NS(compact_hud=NS(_was_cruise_active=False, _set_speed_alpha=NS(x=0.0),
                                   _wheel_alpha=NS(x=0.0), _wheel_y=NS(x=25.0)),
                     torque_bar=NS(_torque_filter=NS(x=0.0), _alpha_filter=NS(x=0.0))), create=True))
    braking = sample_state("braking", default_document())
    canvas._settle(braking)
    self.assertTrue(canvas.view.compact_hud._was_cruise_active)
    self.assertEqual(canvas.view.compact_hud._set_speed_alpha.x, 1.0)
    self.assertGreater(canvas.view.compact_hud._wheel_alpha.x, 200)
    self.assertEqual(canvas.view.compact_hud._wheel_y.x, 0.0)
    self.assertEqual(canvas.view.torque_bar._torque_filter.x, braking.torque_utilization)
    self.assertEqual(canvas.view.torque_bar._alpha_filter.x, 1.0)

  def test_preview_uses_runtime_monitor_occlusion_for_default_and_moved_widgets(self):
    canvas = _Canvas.__new__(_Canvas)
    canvas.profile = Profile.COMPACT
    canvas.viewport = None
    self.enterContext(patch.object(canvas, 'view', NS(compact_hud=NS(_set_speed_alpha=NS(x=1.0))), create=True))
    canvas.monitor = _DriverMonitorArt.__new__(_DriverMonitorArt)
    canvas.monitor.profile = Profile.COMPACT
    canvas.monitor.renderer = Mock()
    state = sample_state("engaged", default_document())
    with patch("openpilot.starpilot.ui.layout_preview_renderer.draw_widget_frame"):
      canvas._render_driver_monitor(rl.Rectangle(), state)
      canvas.monitor.renderer._render.assert_not_called()
      state.customization["layouts"]["compact"]["driver_monitor"].update(x=200, y=100)
      canvas._render_driver_monitor(rl.Rectangle(), state)
      canvas.monitor.renderer._render.assert_called_once()
      canvas.monitor.renderer._render.reset_mock()
      state.customization["layouts"]["compact"]["driver_monitor"].update(x=16, y=10)
      canvas.view.compact_hud._set_speed_alpha.x = 0.0
      canvas._render_driver_monitor(rl.Rectangle(), state)
      canvas.monitor.renderer._render.assert_called_once()

  def test_big_sidebar_matches_original_right_rail_and_is_sample_only(self):
    frame = rl.Rectangle(1860, 0, 300, 1080)
    rects = metric_rects(frame, len(SAMPLE_METRICS))
    self.assertEqual(len(rects), 7)
    self.assertEqual([(r.x, r.y, r.width, r.height) for r in rects],
                     [(1873, y, 275, 126) for y in (24, 174, 324, 474, 624, 774, 924)])
    self.assertEqual([metric.label for metric in SAMPLE_METRICS],
                     ["ACCEL", "STEER DELAY", "FRICTION", "LAT ACCEL", "LATERAL %", "TORQUE %", "CHESTNUT"])
    with self.assertRaises(ValueError):
      metric_rects(frame, 8)

  def test_sidebar_render_uses_caller_supplied_values_without_live_state(self):
    fonts = Mock()
    fonts.measure.return_value = NS(width=80, height=25)
    metric = (SAMPLE_METRICS[0],)
    with patch("openpilot.starpilot.ui.layout_preview_sidebar.rl.draw_rectangle_rec"), \
         patch("openpilot.starpilot.ui.layout_preview_sidebar.rl.draw_rectangle_rounded"), \
         patch("openpilot.starpilot.ui.layout_preview_sidebar.rl.draw_rectangle_rounded_lines_ex"):
      render_sidebar(fonts, rl.Rectangle(1860, 0, 300, 1080), metric)
    labels = [call.args[0] for call in fonts.draw.call_args_list]
    self.assertEqual(labels, ["ACCEL", "1.08 ft/s²", "SAMPLE DATA"])


if __name__ == "__main__":
  unittest.main()


def test_native_preview_draws_independent_camera_circles_without_camera_input():
  canvas = _Canvas.__new__(_Canvas)
  canvas.profile = Profile.COMPACT
  document = default_document()
  state = sample_state('engaged', document)
  with patch('openpilot.starpilot.ui.layout_preview_renderer.rl.draw_circle_v') as circle, \
       patch('openpilot.starpilot.ui.layout_preview_renderer.rl.draw_ring') as ring:
    canvas._render_side_cameras(state)
    assert circle.call_count == ring.call_count == 2
    right_center = circle.call_args.args[0]
    document['layouts']['compact']['pip_left']['enabled'] = False
    document['layouts']['compact']['pip_left']['x'] = 150
    circle.reset_mock()
    ring.reset_mock()
    canvas._render_side_cameras(sample_state('engaged', document))
    assert circle.call_count == ring.call_count == 1
    assert circle.call_args.args[0].x == right_center.x
    assert circle.call_args.args[0].y == right_center.y
