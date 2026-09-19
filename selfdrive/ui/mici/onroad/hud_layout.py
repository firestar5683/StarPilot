"""Pure geometry for native HUD icon groups."""
import math


def steering_warning_rect(center_x, center_y, wheel_width, wheel_height, rotation, warning_width, warning_height, gap=10):
  """Keep the unrotated warning clear of the steering wheel at any angle."""
  angle = math.radians(rotation)
  rotated_half_width = (wheel_width * abs(math.cos(angle)) + wheel_height * abs(math.sin(angle))) / 2
  return (center_x + rotated_half_width + gap, center_y - warning_height / 2, warning_width, warning_height)
