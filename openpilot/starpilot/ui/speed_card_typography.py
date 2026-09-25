"""Fit a speed and inline adjustment using actual visible glyph extents."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ValueLayout:
  size: int
  x: float
  y: float
  offset_x: float | None
  offset_y: float | None
  unit_y: float


def value_layout(value, adjustment, width, height, measure_value, value_ink,
                 measure_adjustment, adjustment_ink, unit_ink, *, size=86, y=55, visible_top=None):
  """Keep numerals inside the card and a 20px visible gap above the unit."""
  adjustment_width = measure_adjustment(adjustment) if adjustment else 0
  gap = 8 if adjustment else 0
  available_width = width - 24 - gap - adjustment_width
  unit_top, unit_bottom = unit_ink
  available_bottom = height - 12 - (unit_bottom - unit_top) - 20
  def baseline(font_size):
    return max(y, visible_top - value_ink(value, font_size)[0]) if visible_top is not None else y
  while size > 22 and (measure_value(value, size) > available_width or baseline(size) + value_ink(value, size)[1] > available_bottom):
    size -= 1
  y = baseline(size)
  value_width = measure_value(value, size)
  x = (width - value_width - gap - adjustment_width) / 2
  top, bottom = value_ink(value, size)
  offset_x = offset_y = None
  if adjustment:
    adjustment_top, adjustment_bottom = adjustment_ink(adjustment)
    offset_x = x + value_width + gap
    offset_y = y + (top + bottom - adjustment_top - adjustment_bottom) / 2
  return ValueLayout(size, x, y, offset_x, offset_y, y + bottom + 20 - unit_top)


def source_header_layout(label_ink, source_ink, *, label_y=18, gap=5):
  """Separate visible label, source and numeral ink without line-box guesses."""
  source_y = label_y + label_ink[1] + gap - source_ink[0]
  return source_y, source_y + source_ink[1] + gap
