from __future__ import annotations

import colorsys

import numpy as np
import pyray as rl

from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.selfdrive.ui.lib.starpilot_theme import get_param_color, get_theme_color, is_stock_color_scheme, with_alpha
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.shader_polygon import draw_polygon, Gradient
from openpilot.system.ui.lib.text_measure import measure_text_cached

_METRICS_FONT_SIZE = 45
_STOCK_LINE_GREEN = rl.Color(0, 255, 0, 241)


def _hsla_to_color(h: float, s: float, l: float, a: float) -> rl.Color:
  rgb = colorsys.hls_to_rgb(h, l, s)
  return rl.Color(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), int(a * 255))


def _make_gradient(hue: float) -> Gradient:
  return Gradient(
    start=(0.0, 1.0),
    end=(0.0, 0.0),
    colors=[
      _hsla_to_color(hue, 0.75, 0.5, 0.4),
      _hsla_to_color(hue, 0.75, 0.5, 0.35),
      _hsla_to_color(hue, 0.75, 0.5, 0.0),
    ],
    stops=[0.0, 0.5, 1.0],
  )


def _draw_text_with_outline(text: str, x: float, y: float, font, font_size: int):
  pos = rl.Vector2(x, y)
  rl.draw_text_ex(font, text, rl.Vector2(pos.x - 1, pos.y - 1), font_size, 0, rl.BLACK)
  rl.draw_text_ex(font, text, rl.Vector2(pos.x + 1, pos.y - 1), font_size, 0, rl.BLACK)
  rl.draw_text_ex(font, text, rl.Vector2(pos.x - 1, pos.y + 1), font_size, 0, rl.BLACK)
  rl.draw_text_ex(font, text, rl.Vector2(pos.x + 1, pos.y + 1), font_size, 0, rl.BLACK)
  rl.draw_text_ex(font, text, pos, font_size, 0, rl.WHITE)


def render_adjacent_lanes(renderer) -> None:
  """Draw left and right adjacent lane paths.

  Consolidates adjacent width path rendering and blind spot warning overlays.
  If a blind spot is active on a side and BlindSpotPath is enabled, that side draws red.
  Otherwise, if AdjacentPath is enabled, it draws with width-based gradient coloring.
  """
  sm = ui_state.sm
  adjacent_enabled = renderer._params.get_bool("AdjacentPath")
  blind_spot_enabled = renderer._params.get_bool("BlindSpotPath")

  if not (adjacent_enabled or blind_spot_enabled):
    return

  vertices = renderer._adjacent_path_vertices
  if not vertices or len(vertices) < 2:
    return

  # Fetch blindspot status if blind spot path is enabled
  blindspot_left = False
  blindspot_right = False
  if blind_spot_enabled and sm.recv_frame["carState"] >= ui_state.started_frame:
    car_state = sm["carState"]
    blindspot_left = bool(car_state.leftBlindspot)
    blindspot_right = bool(car_state.rightBlindspot)
    vasm_left = ui_state.params_memory.get("VASMLeftActive") == "1"
    vasm_right = ui_state.params_memory.get("VASMRightActive") == "1"
    blindspot_left = blindspot_left or vasm_left
    blindspot_right = blindspot_right or vasm_right

  # Fetch adjacent lane widths if adjacent path is enabled
  lane_width_left = 0.0
  lane_width_right = 0.0
  lane_detection_width = 3.5
  if adjacent_enabled and sm.recv_frame["starpilotPlan"] >= ui_state.started_frame:
    plan = sm["starpilotPlan"]
    lane_width_left = float(plan.laneWidthLeft)
    lane_width_right = float(plan.laneWidthRight)
    lane_detection_width = renderer._params.get_float("LaneDetectionWidth") if renderer._params.get("LaneDetectionWidth") else 3.5

  rect = renderer._rect
  show_metrics = renderer._params.get_bool("AdjacentPathMetrics")
  distance_conversion = 3.28084 if not ui_state.is_metric else 1.0
  unit = "ft" if not ui_state.is_metric else "m"
  font = gui_app.font(FontWeight.SEMI_BOLD)

  sides = [
    (0, blindspot_left, lane_width_left),
    (1, blindspot_right, lane_width_right)
  ]

  for side_idx, has_blindspot, lane_width in sides:
    verts = vertices[side_idx]
    if verts.size < 4:
      continue

    hue = None
    if has_blindspot:
      hue = 0.0  # Red for blind spot warning
    elif adjacent_enabled and lane_width > 0.0:
      ratio = np.clip(lane_width / lane_detection_width, 0.0, 1.0)
      hue = (ratio * ratio) * (120.0 / 360.0)

    if hue is not None:
      gradient = _make_gradient(hue)
      draw_polygon(rect, verts, gradient=gradient)

      # Draw width text if adjacent path is enabled on this side
      if adjacent_enabled and lane_width > 0.0 and show_metrics:
        mid_index = len(verts) // 2
        left = verts[mid_index // 2]
        right = verts[mid_index + (len(verts) - mid_index) // 2]

        text = f"{lane_width * distance_conversion:.2f}{unit}"
        text_sz = measure_text_cached(font, text, _METRICS_FONT_SIZE)
        text_width = text_sz.x
        text_height = text_sz.y

        text_x = (left[0] + right[0]) / 2.0 - text_width / 2.0
        text_y = (left[1] + right[1]) / 2.0 - text_height / 2.0 + text_height * 0.75
        _draw_text_with_outline(text, text_x, text_y, font, _METRICS_FONT_SIZE)


def render_path_edges(renderer) -> None:
  """Draw colored edge strips along the driving path.

  Qt reference: paintPathEdges in starpilot_annotated_camera.cc:732-769

  Path edges are the area between track_edge_vertices (outer) and track_vertices (inner).
  Color selection on Python UIs:
  - If path_edges_color is set: use that color
  - Else if color_scheme != "stock": use the active theme color
  - Else: use a fixed stock-style green so border color carries engagement status

  The path_edges_color param is a hex string like "#178644".
  """
  outer = renderer._track_edge_vertices
  inner = renderer._path.projected_points

  if outer.size < 4 or inner.size < 4:
    return

  edge_strip = np.vstack([outer, inner[::-1]])

  override = get_param_color(renderer._params, "PathEdgesColor", 241)
  if override is not None:
    base_color = rl.Color(override.r, override.g, override.b, 241)
  elif is_stock_color_scheme(renderer._params):
    base_color = _STOCK_LINE_GREEN
  else:
    theme_color = get_theme_color("PathEdge", _STOCK_LINE_GREEN)
    base_color = rl.Color(theme_color.r, theme_color.g, theme_color.b, 241)

  gradient = Gradient(
    start=(0.0, 1.0),
    end=(0.0, 0.0),
    colors=[
      with_alpha(base_color, int(255 * 0.4)),
      with_alpha(base_color, int(255 * 0.35)),
      with_alpha(base_color, 0),
    ],
    stops=[0.0, 0.5, 1.0],
  )

  draw_polygon(renderer._rect, edge_strip, gradient=gradient)
