"""Visible typography invariants for narrow cards, inline offsets and units."""
import unittest
from openpilot.starpilot.ui.speed_card_typography import value_layout, source_header_layout


class SpeedCardTypographyTest(unittest.TestCase):
  def layout(self, value, adjustment=None, height=215, size=86):
    scale=1.242
    return value_layout(value,adjustment,176,height,
                        lambda text,n:len(text)*n*scale*.62,
                        lambda text,n:(n*scale*.18,n*scale*.84),
                        lambda text:len(text)*28*scale*.55,
                        lambda text:(28*scale*.22,28*scale*.86),
                        (24*scale*.2,24*scale*.8),size=size)

  def test_three_digit_limits_and_signed_offsets_remain_inside_card(self):
    for value,adjustment in (('100','+10'),('120','-12'),('72','+7'),('45','-4')):
      with self.subTest(value=value,adjustment=adjustment):
        p=self.layout(value,adjustment)
        self.assertGreaterEqual(p.x,12)
        right=p.offset_x+len(adjustment)*28*1.242*.55
        self.assertLessEqual(right,164)
        self.assertLessEqual(p.unit_y+24*1.242*.8,203)

  def test_adjustment_is_centered_on_visible_digits(self):
    p=self.layout('100','+10')
    digit_center=p.y+p.size*1.242*(.18+.84)/2
    adjustment_center=p.offset_y+28*1.242*(.22+.86)/2
    self.assertAlmostEqual(digit_center,adjustment_center)

  def test_unit_has_twenty_visible_pixels_gap_in_every_card_mode(self):
    for height,size,adjustment in ((196,86,None),(215,86,'+7'),(175,48,'+7')):
      p=self.layout('72',adjustment,height,size)
      visible_unit_top=p.unit_y+24*1.242*.2
      visible_digit_bottom=p.y+p.size*1.242*.84
      self.assertAlmostEqual(visible_unit_top-visible_digit_bottom,20)

  def test_hidden_offset_releases_width_for_main_numeral(self):
    with_offset=self.layout('100','+10')
    without_offset=self.layout('100')
    self.assertGreater(without_offset.size,with_offset.size)
    self.assertIsNone(without_offset.offset_x)
    self.assertIsNone(without_offset.offset_y)


  def test_source_header_preserves_visible_gaps_when_number_shrinks(self):
    label_ink=(8,36)
    source_ink=(4,17)
    source_y, visible_top=source_header_layout(label_ink,source_ink)
    self.assertEqual(source_y+source_ink[0]-(18+label_ink[1]),5)
    p=value_layout('100','+10',176,215,
                   lambda text,n:len(text)*n*.8,lambda text,n:(n*.2,n*.9),
                   lambda text:48,lambda text:(6,25),(5,24),visible_top=visible_top)
    self.assertGreaterEqual(p.y+p.size*.2-(source_y+source_ink[1]),5)
    self.assertAlmostEqual(p.unit_y+5-(p.y+p.size*.9),20)
    self.assertLessEqual(p.unit_y+24,203)

if __name__=='__main__':unittest.main()
