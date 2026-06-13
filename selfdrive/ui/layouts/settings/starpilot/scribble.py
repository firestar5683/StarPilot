from __future__ import annotations
import math
import pyray as rl


def draw_custom_icon(key: str, x: float, y: float, s: float, color: rl.Color):

  # Helper for drawing quadratic Bezier curves
  def draw_bezier(p0: rl.Vector2, p1: rl.Vector2, p2: rl.Vector2, thick: float):
    segments = 128
    for i in range(segments):
      t1 = i / segments
      t2 = (i + 1) / segments
      x1_val = (1 - t1)**2 * p0.x + 2 * (1 - t1) * t1 * p1.x + t1**2 * p2.x
      y1_val = (1 - t1)**2 * p0.y + 2 * (1 - t1) * t1 * p1.y + t1**2 * p2.y
      x2_val = (1 - t2)**2 * p0.x + 2 * (1 - t2) * t2 * p1.x + t2**2 * p2.x
      y2_val = (1 - t2)**2 * p0.y + 2 * (1 - t2) * t2 * p1.y + t2**2 * p2.y
      rl.draw_line_ex(rl.Vector2(x1_val, y1_val), rl.Vector2(x2_val, y2_val), thick, color)

  # Helper for drawing tilted ellipse arcs
  def draw_ellipse_arc(cx: float, cy: float, a: float, b: float, tilt_deg: float, start_deg: float, end_deg: float, thick: float):
    tilt = math.radians(tilt_deg)
    segments = 128
    step = (end_deg - start_deg) / segments
    for i in range(segments):
      p1 = math.radians(start_deg + i * step)
      p2 = math.radians(start_deg + (i + 1) * step)

      x1_val = a * math.cos(p1)
      y1_val = b * math.sin(p1)
      rx1 = x1_val * math.cos(tilt) - y1_val * math.sin(tilt)
      ry1 = x1_val * math.sin(tilt) + y1_val * math.cos(tilt)

      x2_val = a * math.cos(p2)
      y2_val = b * math.sin(p2)
      rx2 = x2_val * math.cos(tilt) - y2_val * math.sin(tilt)
      ry2 = x2_val * math.sin(tilt) + y2_val * math.cos(tilt)

      rl.draw_line_ex(rl.Vector2(cx + rx1, cy + ry1), rl.Vector2(cx + rx2, cy + ry2), thick, color)

  # Helper for drawing 4-pointed stars
  def draw_star(cx: float, cy: float, R: float, r: float):
    v1a = rl.Vector2(cx - r, cy - r)
    v1b = rl.Vector2(cx + r, cy - r)
    v1c = rl.Vector2(cx, cy - R)

    v2a = rl.Vector2(cx + r, cy - r)
    v2b = rl.Vector2(cx + r, cy + r)
    v2c = rl.Vector2(cx + R, cy)

    v3a = rl.Vector2(cx + r, cy + r)
    v3b = rl.Vector2(cx - r, cy + r)
    v3c = rl.Vector2(cx, cy + R)

    v4a = rl.Vector2(cx - r, cy + r)
    v4b = rl.Vector2(cx - r, cy - r)
    v4c = rl.Vector2(cx - R, cy)

    rl.draw_triangle(v1a, v1b, v1c, color)
    rl.draw_triangle(v2a, v2b, v2c, color)
    rl.draw_triangle(v3a, v3b, v3c, color)
    rl.draw_triangle(v4a, v4b, v4c, color)
    rl.draw_circle_v(rl.Vector2(cx, cy), r, color)

  if key == "sound":
    # Alerts & Sounds: Bell with single side arcs
    x_c = x + 30.0 * s
    y_c = y + 30.0 * s

    # Top loop (handle)
    draw_ellipse_arc(x_c, y_c - 14.0 * s, 3.0 * s, 3.0 * s, 0.0, 180.0, 360.0, 2.0 * s)

    # Bell dome
    rl.draw_circle_sector(rl.Vector2(x_c, y_c - 6.0 * s), 8.0 * s, 180.0, 360.0, 48, color)

    # Main bell body
    rl.draw_rectangle_rec(rl.Rectangle(x_c - 8.0 * s, y_c - 6.0 * s, 16.0 * s, 16.0 * s), color)

    # Flared side triangles
    rl.draw_triangle(
      rl.Vector2(x_c - 8.0 * s, y_c - 6.0 * s),
      rl.Vector2(x_c - 15.0 * s, y_c + 10.0 * s),
      rl.Vector2(x_c - 8.0 * s, y_c + 10.0 * s),
      color
    )
    rl.draw_triangle(
      rl.Vector2(x_c + 8.0 * s, y_c - 6.0 * s),
      rl.Vector2(x_c + 8.0 * s, y_c + 10.0 * s),
      rl.Vector2(x_c + 15.0 * s, y_c + 10.0 * s),
      color
    )

    # Bottom lip
    rl.draw_rectangle_rounded(rl.Rectangle(x_c - 17.0 * s, y_c + 10.0 * s, 34.0 * s, 3.5 * s), 0.5, 4, color)

    # Clapper
    rl.draw_circle_v(rl.Vector2(x_c, y_c + 16.0 * s), 3.5 * s, color)

    # Single elegant wave arc per side (well-spaced) using custom ellipse arc helper to prevent split bugs
    draw_ellipse_arc(x_c, y_c, 26.0 * s, 26.0 * s, 0.0, 150.0, 210.0, 2.5 * s)
    draw_ellipse_arc(x_c, y_c, 26.0 * s, 26.0 * s, 0.0, -30.0, 30.0, 2.5 * s)

  elif key == "steering":
    # Driving Controls: Minimalist 3-spoke steering wheel
    x_c = x + 30.0 * s
    y_c = y + 30.0 * s

    # Outer rim
    rl.draw_ring(rl.Vector2(x_c, y_c), 19.5 * s, 22.5 * s, 0.0, 360.0, 96, color)

    # Center hub
    rl.draw_circle_v(rl.Vector2(x_c, y_c), 4.5 * s, color)

    # Three clean, single-line spokes
    rl.draw_line_ex(rl.Vector2(x_c - 4.5 * s, y_c), rl.Vector2(x_c - 19.5 * s, y_c), 2.5 * s, color)
    rl.draw_line_ex(rl.Vector2(x_c + 4.5 * s, y_c), rl.Vector2(x_c + 19.5 * s, y_c), 2.5 * s, color)
    rl.draw_line_ex(rl.Vector2(x_c, y_c + 4.5 * s), rl.Vector2(x_c, y_c + 19.5 * s), 2.5 * s, color)

  elif key == "navigate":
    # Map Data: Clean location pin with single base shadow ellipse
    x_c = x + 30.0 * s
    y_c = y + 21.0 * s

    # Teardrop head outline (using safe ellipse arc helper to prevent split bugs)
    draw_ellipse_arc(x_c, y_c, 10.0 * s, 10.0 * s, 0.0, 150.0, 390.0, 3.0 * s)

    # Tapered sides to tip
    rl.draw_line_ex(rl.Vector2(x_c - 8.66 * s, y_c + 5.0 * s), rl.Vector2(x_c, y_c + 19.5 * s), 3.0 * s, color)
    rl.draw_line_ex(rl.Vector2(x_c + 8.66 * s, y_c + 5.0 * s), rl.Vector2(x_c, y_c + 19.5 * s), 3.0 * s, color)

    # Inner core dot
    rl.draw_circle_v(rl.Vector2(x_c, y_c), 3.0 * s, color)

    # Perspective base shadow
    draw_ellipse_arc(x_c, y_c + 24.0 * s, 14.0 * s, 4.5 * s, 0.0, 0.0, 360.0, 2.0 * s)

  elif key == "system":
    # System Settings: Interlocking minimalist gears (Large & Small)
    cx1, cy1 = x + 24.0 * s, y + 24.0 * s
    cx2, cy2 = x + 38.5 * s, y + 38.5 * s

    # Gear 1 (Large - 6 cogs)
    rl.draw_ring(rl.Vector2(cx1, cy1), 5.0 * s, 9.0 * s, 0.0, 360.0, 48, color)
    for i in range(6):
      angle_rad = math.radians(i * 60.0)
      cos_a = math.cos(angle_rad)
      sin_a = math.sin(angle_rad)
      rl.draw_line_ex(
        rl.Vector2(cx1 + cos_a * 9.0 * s, cy1 + sin_a * 9.0 * s),
        rl.Vector2(cx1 + cos_a * 13.0 * s, cy1 + sin_a * 13.0 * s),
        4.5 * s,
        color
      )

    # Gear 2 (Small - 5 cogs)
    rl.draw_ring(rl.Vector2(cx2, cy2), 3.0 * s, 6.0 * s, 0.0, 360.0, 48, color)
    for j in range(5):
      angle_rad = math.radians(36.0 + j * 72.0)
      cos_a = math.cos(angle_rad)
      sin_a = math.sin(angle_rad)
      rl.draw_line_ex(
        rl.Vector2(cx2 + cos_a * 6.0 * s, cy2 + sin_a * 6.0 * s),
        rl.Vector2(cx2 + cos_a * 9.5 * s, cy2 + sin_a * 9.5 * s),
        3.5 * s,
        color
      )

  elif key == "display":
    # Appearance: Minimalist widescreen display with core brightness/sun symbol
    # Screen frame outline
    rl.draw_line_ex(rl.Vector2(x + 9.0 * s, y + 12.0 * s), rl.Vector2(x + 51.0 * s, y + 12.0 * s), 2.0 * s, color)
    rl.draw_line_ex(rl.Vector2(x + 51.0 * s, y + 12.0 * s), rl.Vector2(x + 51.0 * s, y + 36.0 * s), 2.0 * s, color)
    rl.draw_line_ex(rl.Vector2(x + 51.0 * s, y + 36.0 * s), rl.Vector2(x + 9.0 * s, y + 36.0 * s), 2.0 * s, color)
    rl.draw_line_ex(rl.Vector2(x + 9.0 * s, y + 36.0 * s), rl.Vector2(x + 9.0 * s, y + 12.0 * s), 2.0 * s, color)

    # Screen stand (pillar & base)
    rl.draw_line_ex(rl.Vector2(x + 30.0 * s, y + 36.0 * s), rl.Vector2(x + 30.0 * s, y + 44.0 * s), 3.0 * s, color)
    rl.draw_line_ex(rl.Vector2(x + 22.0 * s, y + 44.0 * s), rl.Vector2(x + 38.0 * s, y + 44.0 * s), 2.0 * s, color)

    # Minimal sun / brightness symbol in screen center
    sx_c = x + 30.0 * s
    sy_c = y + 24.0 * s
    rl.draw_circle_v(rl.Vector2(sx_c, sy_c), 3.5 * s, color)
    for k in range(8):
      angle_rad = math.radians(k * 45.0)
      cos_a = math.cos(angle_rad)
      sin_a = math.sin(angle_rad)
      rl.draw_line_ex(
        rl.Vector2(sx_c + cos_a * 6.0 * s, sy_c + sin_a * 6.0 * s),
        rl.Vector2(sx_c + cos_a * 8.5 * s, sy_c + sin_a * 8.5 * s),
        1.5 * s,
        color
      )

  elif key == "vehicle":
    # Vehicle Settings: Little Car
    v_front = rl.Vector2(x + 5.0 * s, y + 34.0 * s)
    v_hood_end = rl.Vector2(x + 15.0 * s, y + 27.0 * s)
    v_cabin_end = rl.Vector2(x + 37.0 * s, y + 17.0 * s)
    v_rear = rl.Vector2(x + 55.0 * s, y + 33.0 * s)

    # Car body panels (continuous Bezier curve profile)
    rl.draw_line_ex(rl.Vector2(x + 5.0 * s, y + 38.0 * s), v_front, 2.0 * s, color)
    draw_bezier(v_front, rl.Vector2(x + 9.0 * s, y + 32.0 * s), v_hood_end, 2.0 * s)
    draw_bezier(v_hood_end, rl.Vector2(x + 25.0 * s, y + 17.0 * s), v_cabin_end, 2.0 * s)
    draw_bezier(v_cabin_end, rl.Vector2(x + 48.0 * s, y + 20.0 * s), v_rear, 2.0 * s)
    rl.draw_line_ex(v_rear, rl.Vector2(x + 55.0 * s, y + 38.0 * s), 2.0 * s, color)

    # Underbody frame
    rl.draw_line_ex(rl.Vector2(x + 5.0 * s, y + 38.0 * s), rl.Vector2(x + 11.5 * s, y + 38.0 * s), 2.0 * s, color)
    rl.draw_line_ex(rl.Vector2(x + 21.5 * s, y + 38.0 * s), rl.Vector2(x + 38.5 * s, y + 38.0 * s), 2.0 * s, color)
    rl.draw_line_ex(rl.Vector2(x + 48.5 * s, y + 38.0 * s), rl.Vector2(x + 55.0 * s, y + 38.0 * s), 2.0 * s, color)

    # Wheels (clean hollow rings with high segment counts)
    rl.draw_ring(rl.Vector2(x + 16.5 * s, y + 38.0 * s), 2.5 * s, 5.0 * s, 0.0, 360.0, 48, color)
    rl.draw_ring(rl.Vector2(x + 43.5 * s, y + 38.0 * s), 2.5 * s, 5.0 * s, 0.0, 360.0, 48, color)

    # Window cutout details
    rl.draw_line_ex(rl.Vector2(x + 18.0 * s, y + 25.0 * s), rl.Vector2(x + 36.0 * s, y + 25.0 * s), 1.5 * s, color)
    rl.draw_line_ex(rl.Vector2(x + 36.0 * s, y + 25.0 * s), rl.Vector2(x + 34.0 * s, y + 20.0 * s), 1.5 * s, color)

  elif key == "first_aid":
    # First Aid Kit Symbol
    x_c = x + 30.0 * s
    y_c = y + 30.0 * s

    # Handle on top of the kit
    draw_ellipse_arc(x_c, y_c - 10.0 * s, 6.0 * s, 4.0 * s, 0.0, 180.0, 360.0, 2.5 * s)

    # Box outline with rounded corners
    draw_ellipse_arc(x_c - 15.0 * s, y_c - 7.0 * s, 3.0 * s, 3.0 * s, 0.0, 180.0, 270.0, 2.5 * s)
    draw_ellipse_arc(x_c + 15.0 * s, y_c - 7.0 * s, 3.0 * s, 3.0 * s, 0.0, 270.0, 360.0, 2.5 * s)
    draw_ellipse_arc(x_c + 15.0 * s, y_c + 12.0 * s, 3.0 * s, 3.0 * s, 0.0, 0.0, 90.0, 2.5 * s)
    draw_ellipse_arc(x_c - 15.0 * s, y_c + 12.0 * s, 3.0 * s, 3.0 * s, 0.0, 90.0, 180.0, 2.5 * s)

    # Connecting lines for the box outline
    rl.draw_line_ex(rl.Vector2(x_c - 15.0 * s, y_c - 10.0 * s), rl.Vector2(x_c + 15.0 * s, y_c - 10.0 * s), 2.5 * s, color)
    rl.draw_line_ex(rl.Vector2(x_c - 15.0 * s, y_c + 15.0 * s), rl.Vector2(x_c + 15.0 * s, y_c + 15.0 * s), 2.5 * s, color)
    rl.draw_line_ex(rl.Vector2(x_c - 18.0 * s, y_c - 7.0 * s), rl.Vector2(x_c - 18.0 * s, y_c + 12.0 * s), 2.5 * s, color)
    rl.draw_line_ex(rl.Vector2(x_c + 18.0 * s, y_c - 7.0 * s), rl.Vector2(x_c + 18.0 * s, y_c + 12.0 * s), 2.5 * s, color)

    # Cross in the center (centered at y_c + 2.5)
    rl.draw_line_ex(rl.Vector2(x_c, y_c - 4.0 * s), rl.Vector2(x_c, y_c + 9.0 * s), 3.5 * s, color)
    rl.draw_line_ex(rl.Vector2(x_c - 6.5 * s, y_c + 2.5 * s), rl.Vector2(x_c + 6.5 * s, y_c + 2.5 * s), 3.5 * s, color)

