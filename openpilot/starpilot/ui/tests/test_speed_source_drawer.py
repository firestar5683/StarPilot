"""Pure reveal and shared-frame geometry; no UI/native resource acquisition."""

import unittest
from openpilot.starpilot.ui.speed_source_drawer_model import DrawerMotion


class DrawerTest(unittest.TestCase):
  def test_reveal_finishes_and_reverses_without_jumping(self):
    drawer = DrawerMotion()
    drawer.update(True, 1)
    self.assertEqual(drawer.progress, 0)
    drawer.update(True, 1.09)
    before = drawer.progress
    self.assertTrue(0 < before < 1)
    drawer.update(False, 1.09)
    self.assertEqual(drawer.progress, before)
    drawer.update(False, 1.24)
    self.assertEqual(drawer.progress, 0)
    drawer.update(True, 2)
    drawer.update(True, 2.19)
    self.assertEqual(drawer.progress, 1)
    drawer.reset()
    self.assertEqual(drawer.progress, 0)
