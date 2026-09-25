"""Reviewed Settings geometry, independent of application state and services."""

from __future__ import annotations

import math
import random
import pyray as rl
from openpilot.starpilot.ui.home_geometry import outside_rounded_border

TILE_RADIUS_PX = 18.0

_HUD_BG_ON = rl.Color(12, 10, 18, 230)

_HUD_BORDER_OFF = rl.Color(28, 27, 34, 255)

_CONST_PRIMARY = rl.Color(235, 240, 255, 255)

_CONST_SECONDARY = rl.Color(180, 195, 220, 255)

_CONST_TERTIARY = rl.Color(145, 155, 175, 255)

_CONST_REGIONS_TILE = [
  (0.18, 0.30, 0.18, 0.30),  # top-left corner
  (0.70, 0.82, 0.18, 0.30),  # top-right corner
  (0.18, 0.30, 0.70, 0.82),  # bottom-left corner
  (0.70, 0.82, 0.70, 0.82),  # bottom-right corner
  (0.38, 0.62, 0.18, 0.28),  # top-center edge
  (0.38, 0.62, 0.72, 0.82),  # bottom-center edge
  (0.18, 0.28, 0.38, 0.62),  # left-center edge
  (0.72, 0.82, 0.38, 0.62),  # right-center edge
]

def _snap(value: float) -> float:
  return float(round(value))

def snap_rect(rect: rl.Rectangle) -> rl.Rectangle:
  return rl.Rectangle(
    _snap(rect.x), _snap(rect.y),
    _snap(rect.width), _snap(rect.height),
  )

def _roundness_for(rect: rl.Rectangle, radius_px: float = TILE_RADIUS_PX) -> float:
  min_dim = max(1.0, min(rect.width, rect.height))
  return max(0.0, min(0.5, radius_px / min_dim))

def _segments_for(rect: rl.Rectangle, radius_px: float = TILE_RADIUS_PX) -> int:
  effective_radius = max(2.0, min(radius_px, min(rect.width, rect.height) / 2))
  return max(12, min(28, int(round(effective_radius * 1.25))))

def draw_rounded_fill(rect: rl.Rectangle, color: rl.Color, radius_px: float = TILE_RADIUS_PX, segments: int | None = None):
  snapped = snap_rect(rect)
  rl.draw_rectangle_rounded(snapped, _roundness_for(snapped, radius_px), segments or _segments_for(snapped, radius_px), color)

def draw_rounded_stroke(rect: rl.Rectangle, color: rl.Color, thickness: int = 1, radius_px: float = TILE_RADIUS_PX, segments: int | None = None):
  snapped = snap_rect(rect)
  outside_rounded_border(snapped, _roundness_for(snapped, radius_px), segments or _segments_for(snapped, radius_px), thickness, color)

def draw_hud_background(rect: rl.Rectangle, accent: rl.Color, glow: float = 1.0, *,
                        radius_px: float = 100, bg_color: rl.Color | None = None) -> tuple[rl.Rectangle, rl.Color]:
  snapped = snap_rect(rect)
  rx, ry, rw, rh = int(snapped.x), int(snapped.y), int(snapped.width), int(snapped.height)
  face = rl.Rectangle(rx, ry, rw, rh)

  off_border = _HUD_BORDER_OFF

  for i in range(4, 0, -1):
    if glow < 0.1 and i == 4:
      off = 6.0
      a = 6
    else:
      off = i * 2.5 * glow
      a = int(25 * (1.0 - i / 5) * glow)
    gr = rl.Rectangle(rx - off, ry - off, rw + off * 2, rh + off * 2)
    draw_rounded_fill(gr, rl.Color(accent.r, accent.g, accent.b, max(0, min(255, a))), radius_px=radius_px)

  draw_rounded_fill(face, bg_color if bg_color is not None else _HUD_BG_ON, radius_px=radius_px)

  gl = max(glow, 0.18)
  bc = rl.Color(
    max(0, min(255, int(off_border.r + (accent.r - off_border.r) * gl))),
    max(0, min(255, int(off_border.g + (accent.g - off_border.g) * gl))),
    max(0, min(255, int(off_border.b + (accent.b - off_border.b) * gl))),
    255)
  draw_rounded_stroke(face, bc, radius_px=radius_px)

  return face, accent

def _build_constellation_nodes(
  rng: random.Random,
  num: int,
  regions: list[tuple[float, float, float, float]],
  *,
  r_min: float,
  r_max: float,
  min_sep: float,
  x_margin: float,
  y_margin: float,
) -> tuple[list[dict], list[tuple[int, int]]]:
  """Shared constellation node generator used by both tiles and toggle pills."""
  ax_min, ax_max, ay_min, ay_max = regions[rng.randint(0, len(regions) - 1)]
  ax = ax_min + rng.random() * (ax_max - ax_min)
  ay = ay_min + rng.random() * (ay_max - ay_min)
  nodes: list[dict] = []
  for _ in range(num):
    for _ in range(20):
      a = rng.random() * 2.0 * math.pi
      r = r_min + rng.random() * r_max
      x = max(x_margin, min(1.0 - x_margin, ax + r * math.cos(a)))
      y = max(y_margin, min(1.0 - y_margin, ay + r * math.sin(a)))
      if all(math.sqrt((x - n['x'])**2 + (y - n['y'])**2) >= min_sep for n in nodes):
        nodes.append({'x': x, 'y': y})
        break
    else:
      nodes.append({'x': x, 'y': y})
  nodes.sort(key=lambda n: -(abs(n['x'] - 0.5) + abs(n['y'] - 0.5)))
  for i, n in enumerate(nodes):
    n['w'] = 0 if i == 0 else 1 if i == 1 else 2
  vecs: list[tuple[int, int]] = [(0, j) for j in range(1, len(nodes))]
  return nodes, vecs

def draw_constellation_nodes(
  nodes: list[dict],
  vecs: list[tuple[int, int]],
  rect: rl.Rectangle,
  accent: rl.Color,
  glow: float,
  *,
  scale: float = 1.0,
) -> None:
  """Shared constellation renderer used by both tiles and toggle pills.

  `scale` shrinks core/glow radii for smaller surfaces (e.g. 0.45 for pills).
  """
  rx, ry, rw, rh = int(rect.x), int(rect.y), int(rect.width), int(rect.height)
  va = int(10 + glow * 25)
  if va > 2:
    vc = rl.Color(accent.r, accent.g, accent.b, min(255, va))
    for i, j in vecs:
      rl.draw_line_ex(
        rl.Vector2(int(rx + nodes[i]['x'] * rw), int(ry + nodes[i]['y'] * rh)),
        rl.Vector2(int(rx + nodes[j]['x'] * rw), int(ry + nodes[j]['y'] * rh)),
        1.0, vc,
      )
  for nd in nodes:
    nx = int(rx + nd['x'] * rw)
    ny = int(ry + nd['y'] * rh)
    w = nd.get('w', 2)
    if w == 0:
      core_r, diff_r, col = 3.0 * scale, 12.0 * scale, _CONST_PRIMARY
    elif w == 1:
      core_r, diff_r, col = 2.0 * scale, 8.0 * scale, _CONST_SECONDARY
    else:
      core_r, diff_r, col = 1.2 * scale, 0.0, _CONST_TERTIARY
    da = int(5 + glow * 20)
    if diff_r > 0 and da > 2:
      rl.draw_circle(nx, ny, max(1.0, diff_r), rl.Color(col.r, col.g, col.b, min(255, da)))
    ca = int(130 + glow * 125)
    rl.draw_circle(nx, ny, max(1.0, core_r), rl.Color(col.r, col.g, col.b, min(255, ca)))

def constellation(title, rect):
  rng = random.Random(f"{title}:{int(rect.x)}:{int(rect.y)}")
  return _build_constellation_nodes(rng, 3 + rng.randint(0, 2), _CONST_REGIONS_TILE,
                                    r_min=0.05, r_max=0.11, min_sep=0.07, x_margin=0.04, y_margin=0.04)
