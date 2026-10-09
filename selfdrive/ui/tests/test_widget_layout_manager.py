import unittest
import pyray as rl

from openpilot.selfdrive.ui.onroad.starpilot.widgets.base import LayoutWidget
from openpilot.selfdrive.ui.onroad.starpilot.widget_layout_manager import WidgetLayoutManager


class DummyLayoutWidget(LayoutWidget):
  def __init__(self, name: str, priority: int, width: float, height: float, visible: bool = True):
    super().__init__(name, priority)
    self._width = width
    self._height = height
    self._visible = visible

  @property
  def is_visible(self) -> bool:
    return self._visible

  def get_size(self) -> tuple[float, float]:
    return self._width, self._height


class TestWidgetLayoutManager(unittest.TestCase):
  def setUp(self):
    # Set up content rect matching screen resolution 2160x1080 inside borders
    self.content_rect = rl.Rectangle(30, 30, 2100, 1020)
    self.layout_manager = WidgetLayoutManager(self.content_rect)

  def test_priority_sorting(self):
    w1 = DummyLayoutWidget("widget1", priority=3, width=100, height=100)
    w2 = DummyLayoutWidget("widget2", priority=1, width=100, height=100)
    w3 = DummyLayoutWidget("widget3", priority=2, width=100, height=100)

    self.layout_manager.register_widget("left", w1)
    self.layout_manager.register_widget("left", w2)
    self.layout_manager.register_widget("left", w3)

    # Should be sorted: w2 (1), w3 (2), w1 (3)
    self.assertEqual(self.layout_manager.zones["left"][0], w2)
    self.assertEqual(self.layout_manager.zones["left"][1], w3)
    self.assertEqual(self.layout_manager.zones["left"][2], w1)

  def test_left_zone_vertical_stacking(self):
    # Left zone widgets stack vertically
    # Center X anchor should be rect.x + 60 + 172 // 2 = 30 + 60 + 86 = 176
    w1 = DummyLayoutWidget("set_speed", priority=1, width=200, height=204)
    w2 = DummyLayoutWidget("speed_limit", priority=2, width=176, height=176)

    self.layout_manager.register_widget("left", w1)
    self.layout_manager.register_widget("left", w2)

    self.layout_manager.update_layout(self.content_rect, is_rhd=False)

    # w1 should be at y = rect.y + 45 = 30 + 45 = 75
    # center is 176, so x = 176 - 200/2 = 76
    self.assertEqual(w1.rect.x, 76)
    self.assertEqual(w1.rect.y, 75)
    self.assertEqual(w1.rect.width, 200)
    self.assertEqual(w1.rect.height, 204)

    # w2 should stack below w1: y = 75 + 204 + 15 (spacing) = 294
    # center is 176, so x = 176 - 176/2 = 88
    self.assertEqual(w2.rect.x, 88)
    self.assertEqual(w2.rect.y, 294)

  def test_vertical_speed_card_aligns_with_gauge_and_clears_bottom_controls(self):
    from openpilot.selfdrive.ui.onroad.starpilot.widgets.unified_speed import UNIFIED_WIDTH, UNIFIED_HEIGHT

    speed = DummyLayoutWidget("unified_speed", priority=1, width=UNIFIED_WIDTH, height=UNIFIED_HEIGHT)
    gauge = DummyLayoutWidget("aethergauge", priority=3, width=176, height=260)
    personality = DummyLayoutWidget("personality", priority=1, width=192, height=192)
    self.layout_manager.register_widget("left", speed)
    self.layout_manager.register_widget("left", gauge)
    self.layout_manager.register_widget("bottom", personality)

    for content_rect in (self.content_rect, rl.Rectangle(330, 30, 1800, 1020)):
      for is_rhd in (False, True):
        self.layout_manager.update_layout(content_rect, is_rhd=is_rhd)
        speed_center = speed.rect.x + speed.rect.width / 2
        self.assertEqual(speed_center, gauge.rect.x + gauge.rect.width / 2)
        self.assertGreaterEqual(speed.rect.x, content_rect.x + 30)
        self.assertEqual(gauge.rect.y, speed.rect.y + speed.rect.height + self.layout_manager.spacing)
        self.assertLess(gauge.rect.y + gauge.rect.height, personality.rect.y)

  def test_bottom_zone_lhd_stacking(self):
    # Bottom zone: LHD horizontal stacking from left to right starting at x = 146
    # Y center should be content_rect.y + content_rect.height - 146 = 30 + 1020 - 146 = 904
    w1 = DummyLayoutWidget("personality", priority=1, width=192, height=192)
    w2 = DummyLayoutWidget("driver_monitor", priority=2, width=192, height=192)
    w3 = DummyLayoutWidget("third", priority=3, width=192, height=192)

    self.layout_manager.register_widget("bottom", w1)
    self.layout_manager.register_widget("bottom", w2)
    self.layout_manager.register_widget("bottom", w3)

    self.layout_manager.update_layout(self.content_rect, is_rhd=False)

    # w1 (first): center_x = content_rect.x + 146 = 30 + 146 = 176
    # so x = 176 - 192/2 = 80
    # y = 904 - 192/2 = 808
    self.assertEqual(w1.rect.x, 80)
    self.assertEqual(w1.rect.y, 808)

    # w2 (second): center_x = 176 + 192 + 15 = 383
    # so x = 383 - 192/2 = 287
    self.assertEqual(w2.rect.x, 287)
    self.assertEqual(w2.rect.y, 808)

    # w3 (third): center_x = 383 + 192 + 15 = 590
    # so x = 590 - 192/2 = 494
    self.assertEqual(w3.rect.x, 494)
    self.assertEqual(w3.rect.y, 808)


  def test_bottom_zone_rhd_stacking(self):
    # Bottom zone: RHD horizontal stacking such that last widget center is at width - 146
    w1 = DummyLayoutWidget("personality", priority=1, width=192, height=192)
    w2 = DummyLayoutWidget("driver_monitor", priority=2, width=192, height=192)
    w3 = DummyLayoutWidget("third", priority=3, width=192, height=192)

    self.layout_manager.register_widget("bottom", w1)
    self.layout_manager.register_widget("bottom", w2)
    self.layout_manager.register_widget("bottom", w3)

    self.layout_manager.update_layout(self.content_rect, is_rhd=True)

    # Total width of widgets = 192 + 15 + 192 + 15 + 192 = 606
    # Last widget center should be width - 146 = 2130 - 146 = 1984
    # Middle widget (w2) center should be 1984 - 192 - 15 = 1777
    # First widget (w1) center should be 1777 - 192 - 15 = 1570
    
    # w1: center_x = 1570, so x = 1570 - 192/2 = 1474
    self.assertEqual(w1.rect.x, 1474)

    # w2: center_x = 1777, so x = 1777 - 192/2 = 1681
    self.assertEqual(w2.rect.x, 1681)

    # w3: center_x = 1984, so x = 1984 - 192/2 = 1888
    self.assertEqual(w3.rect.x, 1888)

  def test_dynamic_visibility_shifting(self):
    # Left zone: w1, w2, w3. w2 becomes invisible. w3 should shift up to occupy w2's space.
    w1 = DummyLayoutWidget("w1", priority=1, width=100, height=100)
    w2 = DummyLayoutWidget("w2", priority=2, width=100, height=100, visible=False)
    w3 = DummyLayoutWidget("w3", priority=3, width=100, height=100)

    self.layout_manager.register_widget("left", w1)
    self.layout_manager.register_widget("left", w2)
    self.layout_manager.register_widget("left", w3)

    self.layout_manager.update_layout(self.content_rect, is_rhd=False)

    # w1: y = 75
    self.assertEqual(w1.rect.y, 75)
    # w2: is invisible, should not be set (or rather, is skipped in stacking)
    # w3: should stack directly below w1: y = 75 + 100 + 15 = 190
    self.assertEqual(w3.rect.y, 190)

  def test_wide_unified_card_stays_inside_the_left_edge(self):
    card = DummyLayoutWidget("unified_speed", priority=1, width=520, height=250)
    gauge = DummyLayoutWidget("aethergauge", priority=3, width=176, height=260)
    self.layout_manager.register_widget("left", card)
    self.layout_manager.register_widget("left", gauge)

    self.layout_manager.update_layout(self.content_rect)

    self.assertEqual(card.rect.x, self.content_rect.x + 30)
    self.assertEqual(card.rect.y, self.content_rect.y + 45)
    self.assertEqual(gauge.rect.x + gauge.rect.width / 2, self.content_rect.x + 146)
    self.assertEqual(gauge.rect.y, card.rect.y + card.rect.height + self.layout_manager.spacing)

  def test_dynamic_repositioning_on_rect_change(self):
    # Register a widget
    w1 = DummyLayoutWidget("w1", priority=1, width=100, height=100)
    self.layout_manager.register_widget("right", w1)

    # Initial layout
    self.layout_manager.update_layout(self.content_rect, is_rhd=False)
    # center_x = 30 + 2100 - 146 = 1984. x = 1984 - 50 = 1934
    initial_x = w1.rect.x

    # New layout with different rect
    new_rect = rl.Rectangle(0, 0, 1920, 1080)
    self.layout_manager.update_layout(new_rect, is_rhd=False)
    # center_x = 0 + 1920 - 146 = 1774. x = 1774 - 50 = 1724
    new_x = w1.rect.x

    self.assertNotEqual(initial_x, new_x)
    self.assertEqual(initial_x, 1934)
    self.assertEqual(new_x, 1724)

  def test_right_zone_vertical_stacking(self):
    # Right zone widgets stack vertically
    # X anchor is self.content_rect.x + self.content_rect.width - 146
    w1 = DummyLayoutWidget("pedal_icons", priority=1, width=100, height=200)
    w2 = DummyLayoutWidget("other", priority=2, width=100, height=100)

    self.layout_manager.register_widget("right", w1)
    self.layout_manager.register_widget("right", w2)

    self.layout_manager.update_layout(self.content_rect, is_rhd=False)

    # center_x = 30 + 2100 - 146 = 1984
    # w1 x = 1984 - 50 = 1934
    # w1 y = 30 + 45 = 75
    self.assertEqual(w1.rect.x, 1934)
    self.assertEqual(w1.rect.y, 75)
    
    # w2 x = 1934
    # w2 y = 75 + 200 + 15 = 290
    self.assertEqual(w2.rect.x, 1934)
    self.assertEqual(w2.rect.y, 290)

  def test_right_center_zone_is_centered_on_the_right_widget_column(self):
    w1 = DummyLayoutWidget("model_source", priority=1, width=300, height=208)
    self.layout_manager.register_widget("right_center", w1)

    self.layout_manager.update_layout(self.content_rect, is_rhd=False)

    # The 300px widget needs a 150px inset to remain inside the content rect.
    # center_x = 30 + 2100 - 150 = 1980; center_y = 30 + 1020 / 2 = 540
    self.assertEqual(w1.rect.x, 1830)
    self.assertEqual(w1.rect.y, 436)
    self.assertEqual(w1.rect.width, 300)
    self.assertEqual(w1.rect.height, 208)



if __name__ == "__main__":
  unittest.main()
