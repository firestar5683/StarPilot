"""Pure reveal and shared-frame geometry; no UI/native resource acquisition."""
import math
from types import SimpleNamespace
import unittest
from openpilot.starpilot.ui.speed_source_drawer_model import DrawerMotion, _outline

class DrawerTest(unittest.TestCase):
  def test_reveal_finishes_and_reverses_without_jumping(self):
    drawer=DrawerMotion();drawer.update(True,1);self.assertEqual(drawer.width,0)
    drawer.update(True,1.09);before=drawer.progress;self.assertTrue(0<before<1)
    drawer.update(False,1.09);self.assertEqual(drawer.progress,before)
    drawer.update(False,1.24);self.assertEqual(drawer.progress,0)
    drawer.update(True,2);drawer.update(True,2.19);self.assertEqual(drawer.width,248)
    drawer.reset();self.assertEqual(drawer.width,0)

  def test_shared_fill_is_finite_and_has_no_overlapping_fan_triangles(self):
    for height,top in ((411,271),(215,75)):
      for extension in (.0001,1,12,40,124,248):
        with self.subTest(height=height,extension=extension):
          rect=SimpleNamespace(x=88,y=75,width=176,height=height)
          points=_outline(rect,top,extension);cx,cy=176,(top+75+height)/2
          self.assertTrue(all(math.isfinite(v) for point in points for v in point))
          for (x,y),(nx,ny) in zip(points,points[1:]+points[:1]):
            self.assertGreaterEqual(((x-cx)*(ny-cy)-(y-cy)*(nx-cx))/2,-1e-8)
          self.assertEqual(max(y for x,y in points),75+height)
          self.assertAlmostEqual(max(x for x,y in points),264+extension)
