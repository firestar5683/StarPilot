"""Verify safety-icon spacing without opening native UI or device libraries."""
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'selfdrive/ui/mici/onroad'))
from hud_layout import steering_warning_rect


class SafetyIconLayoutTests(unittest.TestCase):
  def test_warning_follows_wheel_edge_instead_of_overlapping_it(self):
    self.assertEqual(steering_warning_rect(46, 201, 50, 50, 0, 44, 44), (81, 179, 44, 44))

  def test_warning_clears_rotated_wheel_at_every_steering_angle(self):
    for angle in range(-180, 181, 5):
      x, y, w, h = steering_warning_rect(46, 201, 50, 50, angle, 44, 44)
      corners = [46 + dx * math.cos(math.radians(angle)) - dy * math.sin(math.radians(angle))
                 for dx in (-25, 25) for dy in (-25, 25)]
      self.assertGreaterEqual(x - max(corners), 9.999)
      self.assertEqual((y, w, h), (179, 44, 44))
