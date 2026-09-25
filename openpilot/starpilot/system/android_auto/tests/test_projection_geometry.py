"""Projection expands a uniformly scaled HUD scene inside negotiated safe space."""
import unittest

from openpilot.starpilot.system.android_auto.projection_geometry import FALLBACK_VIEWPORT, projection_geometry


class TestProjectionGeometry(unittest.TestCase):
  def test_fallback_is_landscape_three_to_two(self):
    self.assertEqual(FALLBACK_VIEWPORT, (1860, 1240))
    self.assertEqual(FALLBACK_VIEWPORT[0] / FALLBACK_VIEWPORT[1], 3 / 2)

  def test_actual_motorola_mode(self):
    geometry = projection_geometry(1280, 720, 0, 240)
    self.assertEqual((geometry.width, geometry.height), (1280, 480))
    self.assertEqual((geometry.logical_width, geometry.logical_height), (2880, 1080))
    self.assertEqual(geometry.scale, 4 / 9)

  def test_supported_aspects_fill_without_cropping_base_hud(self):
    for width, height, mw, mh in [(800, 480, 0, 15), (1280, 720, 0, 240),
                                 (1920, 1080, 0, 360), (1280, 720, 0, 0),
                                 (800, 480, 100, 0), (800, 480, 0, 200)]:
      with self.subTest(mode=(width, height, mw, mh)):
        g = projection_geometry(width, height, mw, mh)
        self.assertGreaterEqual(g.logical_width, 1860)
        self.assertGreaterEqual(g.logical_height, 1080)
        self.assertAlmostEqual(g.logical_width * g.scale, width - mw, delta=0.5)
        self.assertAlmostEqual(g.logical_height * g.scale, height - mh, delta=0.5)

  def test_extreme_valid_margins_use_bounded_fallback(self):
    for margins in [(1279, 0), (0, 719)]:
      g = projection_geometry(1280, 720, *margins)
      self.assertEqual((g.logical_width, g.logical_height), FALLBACK_VIEWPORT)
      self.assertLessEqual(g.logical_width * g.scale, g.width)
      self.assertLessEqual(g.logical_height * g.scale, g.height)

  def test_rejects_invalid_receiver_geometry(self):
    for mode in [(0, 720, 0, 0), (1280, 720, -1, 0), (1280, 720, 1280, 0), (1280, 720, 0, 720)]:
      with self.subTest(mode=mode), self.assertRaises(ValueError):
        projection_geometry(*mode)
