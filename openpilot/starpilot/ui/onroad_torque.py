"""Adapted StarPilot torque-bar polygon with supplied utilization.

The arc polygon generator is retained from the frozen renderer under LICENSE.
"""

import math
import time
from collections import OrderedDict
from functools import lru_cache, wraps

import numpy as np
import pyray as rl

from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.system.ui.lib.shader_polygon import draw_polygon
from openpilot.starpilot.ui.onroad_state import OnroadState
from openpilot.starpilot.ui.onroad_customization import offset as widget_offset, placement
from openpilot.starpilot.ui.onroad_torque_geometry import (
  CAP_RADIUS, LARGE_CAP_RADIUS, MAX_HEIGHT, MAX_OFFSET, MIN_HEIGHT, MIN_OFFSET, RADIUS, TORQUE_ANGLE_SPAN,
)

DEBUG = False

def quantized_lru_cache(maxsize=128):
  def decorator(func):
    cache = OrderedDict()
    @wraps(func)
    def wrapper(r_mid, thickness, a0_deg, a1_deg, **kwargs):
      # Quantize inputs: balanced for smoothness vs cache effectiveness
      key = (round(r_mid),
             round(thickness),           # 1px precision for smoother height transitions
             round(a0_deg * 10) / 10,    # 0.1° precision for smoother angle transitions
             round(a1_deg * 10) / 10,
             tuple(sorted(kwargs.items())))

      if key in cache:
        cache.move_to_end(key)
      else:
        if len(cache) >= maxsize:
          cache.popitem(last=False)

        result = func(r_mid, thickness, a0_deg, a1_deg, **kwargs)
        cache[key] = result
      return cache[key]
    return wrapper
  return decorator


@lru_cache(maxsize=16)
def _cap_vectors(left: bool, segments: int):
  # These quarter-circle samples depend only on tessellation, not live torque,
  # radius or widget placement. Reuse them when the arc geometry cache misses.
  start, end = (180, 90) if left else (90, 0)
  alpha = np.deg2rad(np.linspace(start, end, segments + 2))[1:-1]
  start, end = (-90, -180) if left else (0, -90)
  alpha2 = np.deg2rad(np.linspace(start, end, segments + 1))[:-1]
  vectors = (np.cos(alpha), np.sin(alpha), np.cos(alpha2), np.sin(alpha2))
  for vector in vectors:
    vector.flags.writeable = False
  return vectors


@quantized_lru_cache(maxsize=256)
def arc_bar_pts(r_mid: float, thickness: float,
                a0_deg: float, a1_deg: float,
                *, max_points: int = 100, cap_segs: int = 10,
                cap_radius: float = CAP_RADIUS, px_per_seg: float = 2.0) -> np.ndarray:
  """Return Nx2 np.float32 points for a single closed polygon (rounded thick arc), centered at origin."""

  def get_cap(left: bool, a_deg: float):
    # end cap at a1: center (a1), sweep a1→a1+180 (skip endpoints to avoid dupes)
    # quarter arc (outer corner) at a1 with fixed pixel radius cap_radius

    nx, ny = math.cos(math.radians(a_deg)), math.sin(math.radians(a_deg))  # outward normal
    tx, ty = -ny, nx  # tangent (CCW)

    mx, my = nx * r_mid, ny * r_mid  # mid-point at a1
    if DEBUG:
      rl.draw_circle(int(mx), int(my), 4, rl.PURPLE)

    ex = mx + nx * (half - cap_radius)
    ey = my + ny * (half - cap_radius)

    if DEBUG:
      rl.draw_circle(int(ex), int(ey), 2, rl.WHITE)

    # sweep 90° in the local (t,n) frame: from outer edge toward inside
    cos_a, sin_a, cos_b, sin_b = _cap_vectors(left, cap_segs)
    cap_end = np.column_stack((ex + cos_a * cap_radius * tx + sin_a * cap_radius * nx,
                              ey + cos_a * cap_radius * ty + sin_a * cap_radius * ny))

    # bottom quarter (inner corner) at a1
    ex2 = mx + nx * (-half + cap_radius)
    ey2 = my + ny * (-half + cap_radius)
    if DEBUG:
      rl.draw_circle(int(ex2), int(ey2), 2, rl.WHITE)

    cap_end_bot = np.column_stack((ex2 + cos_b * cap_radius * tx + sin_b * cap_radius * nx,
                                  ey2 + cos_b * cap_radius * ty + sin_b * cap_radius * ny))

    # append to the top quarter
    if not left:
      cap_end = np.vstack((cap_end, cap_end_bot))
    else:
      cap_end = np.vstack((cap_end_bot, cap_end))

    return cap_end

  if a1_deg < a0_deg:
    a0_deg, a1_deg = a1_deg, a0_deg
  half = thickness * 0.5

  cap_radius = min(cap_radius, half)

  span = max(1e-3, a1_deg - a0_deg)

  # pick arc segment count from arc length, clamp to shader points[] budget
  arc_len = r_mid * math.radians(span)
  arc_segs = max(6, int(arc_len / px_per_seg))
  max_arc = (max_points - (4 * cap_segs + 3)) // 2
  arc_segs = max(6, min(arc_segs, max_arc))

  # outer arc a0→a1
  ang_o = np.deg2rad(np.linspace(a0_deg, a1_deg, arc_segs + 1))
  outer = np.column_stack((np.cos(ang_o) * (r_mid + half),
                          np.sin(ang_o) * (r_mid + half)))

  # end cap at a1
  cap_end = get_cap(False, a1_deg)

  # inner arc a1→a0
  ang_i = np.deg2rad(np.linspace(a1_deg, a0_deg, arc_segs + 1))
  inner = np.column_stack((np.cos(ang_i) * (r_mid - half),
                          np.sin(ang_i) * (r_mid - half)))

  # start cap at a0
  cap_start = get_cap(True, a0_deg)

  pts = np.vstack((outer, cap_end, inner, cap_start, outer[:1])).astype(np.float32)

  # Rotate to start from middle of cap for proper triangulation
  pts = np.roll(pts, cap_segs, axis=0)

  if DEBUG:
    n = len(pts)
    idx = int(time.monotonic() * 12) % max(1, n)  # speed: 12 pts/sec
    for i, (x, y) in enumerate(pts):
      j = (i - idx) % n  # rotate the gradient
      t = j / n
      color = rl.Color(255, int(255 * (1 - t)), int(255 * t), 255)
      rl.draw_circle(int(x), int(y), 2, color)

  return pts

class TorqueBarWidget:
  def __init__(self):
    self._torque_filter = FirstOrderFilter(0.0, 0.1, 1 / 60)
    self._alpha_filter = FirstOrderFilter(0.0, 0.1, 1 / 60)
    self._drive_frame = None

  def render(self, rect: rl.Rectangle, state: OnroadState, screen_width: float) -> None:
    drive_frame = getattr(state, 'torque_drive_frame', None)
    if drive_frame != self._drive_frame:
      self._torque_filter.x = self._alpha_filter.x = 0.0
      self._drive_frame = drive_frame
    profile = 'large' if screen_width == 2160 else 'compact'
    enabled = placement(state.customization, profile, 'torque_bar')['enabled']
    if not state.lateral_active or not getattr(state, 'torque_source_available', True):
      self._torque_filter.x = 0.0
      self._alpha_filter.x = 0.0
      return
    utilization = max(-1.0, min(1.0, state.torque_utilization))
    torque = self._torque_filter.update(utilization)
    alpha = self._alpha_filter.update(1.0)
    scale = rect.height / 240.0 * (rect.width / screen_width)
    torque_offset = float(np.interp(abs(torque), [0.5, 1.0], [MIN_OFFSET * scale, MAX_OFFSET * scale]))
    torque_height = float(np.interp(abs(torque), [0.5, 1.0], [MIN_HEIGHT * scale, MAX_HEIGHT * scale]))
    radius = RADIUS * scale
    span = alpha * TORQUE_ANGLE_SPAN
    middle_radius = radius + torque_height / 2
    center_x = rect.x + rect.width / 2 + 8
    center_y = rect.y + rect.height + radius - torque_offset
    offset = np.array([center_x, center_y], dtype=np.float32)
    dx, dy = widget_offset(state.customization, profile, 'torque_bar')
    translation = np.array([dx, dy], dtype=np.float32)
    draw_rect = rl.Rectangle(rect.x + dx, rect.y + dy, rect.width, rect.height)
    cap_radius = LARGE_CAP_RADIUS if profile == 'large' else CAP_RADIUS
    points = arc_bar_pts(middle_radius, torque_height, -90 - span / 2, -90 + span / 2, cap_radius=cap_radius) + offset
    if not enabled:
      return
    bg_alpha = float(np.interp(abs(torque), [0.5, 1.0], [0.25, 0.5]))
    draw_polygon(draw_rect, points + translation, color=rl.Color(255, 255, 255, int(255 * bg_alpha * alpha)))
    indicator_end = -90 + span / 2 * torque
    indicator = arc_bar_pts(middle_radius, torque_height, -90, indicator_end, cap_radius=cap_radius) + offset
    indicator_color = rl.Color(255, 255, 255, int(255 * 0.9 * alpha))
    draw_polygon(draw_rect, indicator + translation, color=indicator_color)
    if abs(torque) < 0.5:
      dot_y = rect.y + rect.height - torque_offset - torque_height / 2
      rl.draw_circle(int(center_x + dx), int(dot_y + dy), 5 * scale, rl.Color(182, 182, 182, int(255 * 0.9 * alpha)))
