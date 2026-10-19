"""Shared visual tokens for the StarPilot on-road control widgets."""

import pyray as rl


# The two left-hand control cards share a visible frame.  Keeping these values
# here prevents the Set Speed and SLC implementations from drifting apart.
CONTROL_WIDTH = 176
SET_SPEED_HEIGHT = 196
SLC_HEIGHT = SET_SPEED_HEIGHT
# Stable Raylib shape settings for scaled rendering.
CONTROL_RADIUS = 31
CONTROL_ROUNDNESS = 0.35
CONTROL_SEGMENTS = 10
CONTROL_BORDER_WIDTH = 6
CONTROL_BG = rl.Color(0, 0, 0, 166)
CONTROL_BORDER = rl.Color(196, 205, 208, 180)
UNIFIED_ACCENT = rl.Color(160, 96, 230, 230)
# The layout manager has historically anchored the left controls at x + 146.
# Keep that placement stable while making the width explicit and shared.
WIDGET_ANCHOR_OFFSET = 146


def roundness_for(rect: rl.Rectangle, radius: float = CONTROL_RADIUS) -> float:
  """Convert a pixel corner radius to Raylib's normalized roundness value."""
  return min(1.0, radius / max(1.0, min(rect.width, rect.height) / 2.0))


def draw_control_card(rect: rl.Rectangle, *, fill: rl.Color = CONTROL_BG,
                      border: rl.Color = CONTROL_BORDER,
                      border_width: float = CONTROL_BORDER_WIDTH) -> None:
  """Draw the common translucent rounded card used by left-hand controls."""
  roundness = CONTROL_ROUNDNESS
  rl.draw_rectangle_rounded(rect, roundness, CONTROL_SEGMENTS, fill)
  rl.draw_rectangle_rounded_lines_ex(rect, roundness, CONTROL_SEGMENTS, border_width, border)
