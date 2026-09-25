"""Frozen torque arc dimensions and cap-inclusive logical-pixel bounds."""

import math

TORQUE_ANGLE_SPAN = 12.7
RADIUS = 1200
MIN_HEIGHT, MAX_HEIGHT = 14, 56
MIN_OFFSET, MAX_OFFSET = 22, 26
CAP_RADIUS = 7


def maximum_footprint(x, y, width, height, screen_width):
  scale = height / 240 * (width / screen_width)
  half_angle = math.radians(TORQUE_ANGLE_SPAN / 2)
  radius = RADIUS * scale
  center_x = x + width / 2 + 8
  extent_x = (radius + MAX_HEIGHT * scale) * math.sin(half_angle) + CAP_RADIUS * (1 - math.sin(half_angle))
  left, right = math.floor(center_x - extent_x), math.ceil(center_x + extent_x)
  top = math.floor(y + height - (MAX_OFFSET + MAX_HEIGHT) * scale)
  bottom = math.ceil(y + height - MIN_OFFSET * scale + (radius + CAP_RADIUS) * (1 - math.cos(half_angle)))
  return left, top, right - left, bottom - top
