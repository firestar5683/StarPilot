import math

import pyray as rl
from openpilot.common.constants import CV
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.selfdrive.ui.onroad.starpilot.widget_style import UNIFIED_ACCENT
from openpilot.selfdrive.ui.onroad.starpilot.source_bubble_layout import (
  enabled_source_titles, fit_source_label, source_abbreviated_value_text,
  source_value_text, visible_source_rows,
)
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state
from openpilot.selfdrive.ui.lib.speed_limit_pulse import SpeedLimitPulse

_WHITE = rl.Color(255, 255, 255, 255)

# ── Constants ─────────────────────────────────────────────────────────

# Source display metadata: source name, main label, value key, bubble label, icon.
SOURCE_DEFS = [
  ("Dashboard", "Dash",  "dashboard_sl", "Dashboard",   "dashboard"),
  ("Map Data",  "MAP",   "map_sl",       "Map Data",    "map"),
  ("Vision",    "VISION", "vision_sl",   "Vision",       "camera"),
  ("Mapbox",    "MBOX",  "mapbox_sl",    "Mapbox",      "map"),
  ("Upcoming",  "NEXT",  "next_sl",      "Next",        "next"),
]
_SOURCE_ICON_KEYS = {source: icon for source, _, _, _, icon in SOURCE_DEFS}


def source_icon_key(source: str) -> str | None:
  """Use the same source glyph as the detailed source diagnostics."""
  return _SOURCE_ICON_KEYS.get(source)

# Vision speed-limit pulse — one-shot purple highlight when the active source
# is "Vision" and the resolved value just changed.
VISION_SPEED_LIMIT_PULSE_SECONDS = 1.0
VISION_SPEED_LIMIT_PULSE_COLOR = rl.Color(188, 132, 255, 255)
_pulse = SpeedLimitPulse()


def _reset_pulse() -> None:
  _pulse.reset()


def _tick_pulse(source: str, resolved_ms: float) -> None:
  speed_conversion = CV.MS_TO_KPH if ui_state.is_metric else CV.MS_TO_MPH
  _pulse.update(source, resolved_ms, speed_conversion, rl.get_time(), ui_state.started_frame)


def _speed_limit_pulse_color(base: rl.Color, alpha: int) -> rl.Color:
  """Blend ``base`` toward VISION_SPEED_LIMIT_PULSE_COLOR with a sin(pi*t) ease.

  Returns ``base`` unchanged (with the supplied alpha) outside the pulse
  window. Inside it, r/g/b are eased toward the pulse color along sin(pi*t)
  where t is elapsed / VISION_SPEED_LIMIT_PULSE_SECONDS.
  """
  base_with_alpha = rl.Color(base.r, base.g, base.b, alpha)
  elapsed = rl.get_time() - _pulse.start_time
  if elapsed < 0.0 or elapsed >= VISION_SPEED_LIMIT_PULSE_SECONDS:
    return base_with_alpha

  progress = elapsed / VISION_SPEED_LIMIT_PULSE_SECONDS
  pulse = math.sin(math.pi * progress)
  return rl.Color(
    round(base.r + (VISION_SPEED_LIMIT_PULSE_COLOR.r - base.r) * pulse),
    round(base.g + (VISION_SPEED_LIMIT_PULSE_COLOR.g - base.g) * pulse),
    round(base.b + (VISION_SPEED_LIMIT_PULSE_COLOR.b - base.b) * pulse),
    alpha,
  )


# ── State ─────────────────────────────────────────────────────────────

def _is_slc_enabled() -> bool:
  toggles = getattr(ui_state, "starpilot_toggles", {})
  if "speed_limit_controller" in toggles:
    return bool(toggles["speed_limit_controller"])
  return ui_state.ui_params.get_bool("SpeedLimitController")


def _get_slc_state():
  """Extract SLC state from SubMaster. Returns dict or None if stale/hidden."""
  slc_enabled = _is_slc_enabled()
  params = ui_state.ui_params
  if not (slc_enabled or params.get_bool("ShowSpeedLimits")):
    _pulse.clear()
    return None

  sm = ui_state.sm
  if sm.recv_frame["starpilotPlan"] < ui_state.started_frame:
    _pulse.clear()
    return None

  plan = sm["starpilotPlan"]
  speed_limit_changed = plan.speedLimitChanged
  presented_source = getattr(plan, 'slcPresentedSpeedLimitSource', '')

  unconfirmed_valid = plan.unconfirmedSlcSpeedLimit > 1

  speed_conversion = CV.MS_TO_KPH if ui_state.is_metric else CV.MS_TO_MPH
  dashboard_sl = sm["starpilotCarState"].dashboardSpeedLimit if sm.valid.get("starpilotCarState", False) else 0.0
  vision_enabled = params.get_bool("VisionSpeedLimitDetection")
  vision_sl = ui_state.params_memory.get_float("VisionSpeedLimit") if vision_enabled else 0.0
  primary_priority = params.get("SLCPriority1", encoding="utf-8") or "Map Data"
  secondary_priority = params.get("SLCPriority2", encoding="utf-8") or "None"
  mapbox_enabled = params.get_bool("SLCMapboxFiller") and bool(
    params.get("MapboxSecretKey", encoding="utf-8")
  )

  # The pulse uses the accepted raw limit, so unit changes cannot retrigger it.
  _tick_pulse(plan.slcSpeedLimitSource, plan.slcSpeedLimit)
  return {
    'accepted_speed_limit_ms': plan.slcSpeedLimit,
    # Match the control target's non-negative base before cluster compensation.
    'effective_target_ms': max(0.0, plan.slcSpeedLimit + plan.slcSpeedLimitOffset),
    'offset_ms': plan.slcSpeedLimitOffset,
    'slc_overridden_speed': plan.slcOverriddenSpeed,
    'speed_limit_source': plan.slcSpeedLimitSource,
    # Older publishers/replays decode the new Text field as "", rather than omitting the attribute.
    'presented_source': presented_source or plan.slcSpeedLimitSource,
    'slc_enabled': slc_enabled,
    # Both UI fields were added together; older plans have no published limiting state.
    'slc_is_limiting_max_set': bool(getattr(plan, 'slcIsLimitingMaxSet', False)) if presented_source else None,
    'unconfirmed_speed_limit': max(0.0, plan.unconfirmedSlcSpeedLimit * speed_conversion),
    'unconfirmed_valid': unconfirmed_valid,
    'speed_limit_changed': speed_limit_changed,
    'speed_conversion': speed_conversion,
    'slc_abbreviated_sources': params.get_bool("SLCAbbreviatedSources"),
    'slc_active_sources_only': params.get_bool("SLCActiveSourcesOnly"),
    'slc_enabled_sources': enabled_source_titles(
      primary_priority,
      secondary_priority,
      vision_enabled=vision_enabled,
      mapbox_enabled=mapbox_enabled,
      dashboard_available=starpilot_state.car_state.hasDashSpeedLimits,
    ),
    # Per-source raw values
    'dashboard_sl': max(0.0, dashboard_sl * speed_conversion),
    'map_sl': max(0.0, plan.slcMapSpeedLimit * speed_conversion),
    'vision_sl': max(0.0, vision_sl * speed_conversion),
    'mapbox_sl': max(0.0, plan.slcMapboxSpeedLimit * speed_conversion),
    'next_sl': max(0.0, plan.slcNextSpeedLimit * speed_conversion),
  }


# ── Fonts ─────────────────────────────────────────────────────────────

_font_bold = None
_font_semi_bold = None

def _get_bold():
  global _font_bold
  if _font_bold is None:
    _font_bold = gui_app.font(FontWeight.BOLD)
  return _font_bold

def _get_semi_bold():
  global _font_semi_bold
  if _font_semi_bold is None:
    _font_semi_bold = gui_app.font(FontWeight.SEMI_BOLD)
  return _font_semi_bold


# ── Source contents ───────────────────────────────────────────────────

_SOURCE_PANEL_PAD_X = 16
_SOURCE_PANEL_PAD_Y = 12
_SOURCE_PANEL_BG = rl.Color(0, 0, 0, 175)
_SOURCE_DIVIDER = rl.Color(UNIFIED_ACCENT.r, UNIFIED_ACCENT.g, UNIFIED_ACCENT.b, 90)
_SOURCE_LABEL_MUTED = rl.Color(170, 179, 174, 255)
_SOURCE_LABEL_SIZE = 26
_SOURCE_VALUE_SIZE = 28
_SOURCE_MIN_LABEL_VALUE_GAP = 12

_SOURCE_COMPACT_LABELS = {
  "Dashboard": "Dash",
  "Map Data": "OSM",
  "Vision": "Vision",
  "Mapbox": "Mapbox",
  "Next": "Next",
}


def _draw_source_icon(icon_key: str, x: float, y: float, size: float, color: rl.Color) -> None:
  """Draw the existing source glyph for both the header and diagnostics."""
  cx = x + size / 2
  cy = y + size / 2
  stroke = max(2.5, size / 12.0)

  if icon_key == "map":
    map_stroke = max(2.5, size * 0.075)
    left = x + size * 0.12
    fold_left = x + size * 0.37
    fold_right = x + size * 0.63
    right = x + size * 0.88
    top = y + size * 0.20
    top_low = y + size * 0.27
    bottom = y + size * 0.80
    bottom_low = y + size * 0.73
    outline = [
      rl.Vector2(left, top),
      rl.Vector2(fold_left, top_low),
      rl.Vector2(fold_right, top),
      rl.Vector2(right, top_low),
      rl.Vector2(right, bottom),
      rl.Vector2(fold_right, bottom_low),
      rl.Vector2(fold_left, bottom),
      rl.Vector2(left, bottom_low),
    ]
    for index, point in enumerate(outline):
      rl.draw_line_ex(point, outline[(index + 1) % len(outline)], map_stroke, color)
    for point in outline:
      rl.draw_circle_v(point, map_stroke / 2, color)
    rl.draw_line_ex(outline[1], outline[6], map_stroke, color)
    rl.draw_line_ex(outline[2], outline[5], map_stroke, color)
  elif icon_key == "camera":
    body = rl.Rectangle(x + size * 0.09, y + size * 0.29, size * 0.82, size * 0.52)
    rl.draw_rectangle_rounded(body, 0.20, 8, color)
    lens = rl.Vector2(cx, y + size * 0.54)
    lens_outer = size * 0.17
    rl.draw_circle_v(lens, lens_outer, _SOURCE_PANEL_BG)
    rl.draw_ring(lens, size * 0.105, lens_outer, 0, 360, max(24, int(size * 0.25)), color)
    rl.draw_rectangle_rounded(
      rl.Rectangle(x + size * 0.30, y + size * 0.18, size * 0.23, size * 0.15),
      0.18, 8, color,
    )
  elif icon_key == "next":
    arrow_stroke = max(2.5, size * 0.08)
    arrow_tip = rl.Vector2(x + size * 0.88, cy)
    rl.draw_line_ex(rl.Vector2(x + size * 0.10, cy), arrow_tip, arrow_stroke, color)
    for endpoint in (
      rl.Vector2(x + size * 0.60, y + size * 0.18),
      rl.Vector2(x + size * 0.60, y + size * 0.82),
    ):
      rl.draw_line_ex(arrow_tip, endpoint, arrow_stroke, color)
    rl.draw_circle_v(arrow_tip, arrow_stroke / 2, color)
  elif icon_key == "navigation":
    pin_center = rl.Vector2(cx, y + size * 0.36)
    pin_radius = size * 0.22
    rl.draw_circle_v(pin_center, pin_radius, color)
    rl.draw_triangle(
      rl.Vector2(cx - pin_radius * 0.82, y + size * 0.40),
      rl.Vector2(cx + pin_radius * 0.82, y + size * 0.40),
      rl.Vector2(cx, y + size * 0.86),
      color,
    )
    rl.draw_circle_v(pin_center, size * 0.09, _SOURCE_PANEL_BG)
  elif icon_key == "dashboard":
    # The Dashboard speed-limit source is a vehicle glyph, distinct from Max Set's gauge.
    body = rl.Rectangle(x + size * 0.10, y + size * 0.43, size * 0.80, size * 0.29)
    rl.draw_rectangle_rounded_lines_ex(body, 0.30, 8, stroke, color)
    rl.draw_line_ex(rl.Vector2(x + size * 0.25, body.y), rl.Vector2(x + size * 0.36, y + size * 0.27), stroke, color)
    rl.draw_line_ex(rl.Vector2(x + size * 0.36, y + size * 0.27), rl.Vector2(x + size * 0.68, y + size * 0.27), stroke, color)
    rl.draw_line_ex(rl.Vector2(x + size * 0.68, y + size * 0.27), rl.Vector2(x + size * 0.79, body.y), stroke, color)
    for wheel_x in (x + size * 0.27, x + size * 0.73):
      rl.draw_circle_v(rl.Vector2(wheel_x, y + size * 0.75), size * 0.07, color)
  elif icon_key == "speedometer":
    gauge_scale = 1.22
    pivot = rl.Vector2(cx, cy + size * 0.17)
    inner_radius = size * 0.27 * gauge_scale
    outer_radius = size * 0.34 * gauge_scale
    ring_segments = max(24, int(size * 0.25))
    rl.draw_ring(pivot, inner_radius, outer_radius, 190, 350, ring_segments, color)
    cap_radius = (outer_radius - inner_radius) / 2
    for angle in (190, 350):
      radians = math.radians(angle)
      rl.draw_circle_v(
        rl.Vector2(
          pivot.x + math.cos(radians) * (inner_radius + cap_radius),
          pivot.y + math.sin(radians) * (inner_radius + cap_radius),
        ),
        cap_radius,
        color,
      )
    needle_angle = math.radians(-48)
    needle_length = inner_radius + stroke * 0.15
    rl.draw_line_ex(
      pivot,
      rl.Vector2(
        pivot.x + math.cos(needle_angle) * needle_length,
        pivot.y + math.sin(needle_angle) * needle_length,
      ),
      stroke,
      color,
    )
    rl.draw_circle_v(pivot, max(2.0, size * 0.06 * gauge_scale), color)


def _draw_sources_bubble_empty_state(panel_rect: rl.Rectangle) -> None:
  """Draw the 3-line centered empty state when no sources are available."""
  font = _get_semi_bold()
  font_size = 30
  line_gap = 6.0
  lines = (tr("NO"), tr("SOURCES"), tr("AVAILABLE"))

  line_sizes = [measure_text_cached(font, line, font_size) for line in lines]
  total_h = sum(sz.y for sz in line_sizes) + line_gap * (len(lines) - 1)
  curr_y = round(panel_rect.y + (panel_rect.height - total_h) / 2)

  for line, sz in zip(lines, line_sizes, strict=True):
    pos_x = round(panel_rect.x + (panel_rect.width - sz.x) / 2)
    rl.draw_text_ex(font, line, rl.Vector2(pos_x, curr_y), font_size, 0, _WHITE)
    curr_y += round(sz.y + line_gap)


def _draw_source_contents(state: dict, panel_rect: rl.Rectangle) -> None:
  """Draw raw source readings; the accepted source is white and bold."""
  font_semi = _get_semi_bold()
  font_bold = _get_bold()
  active_source = state['speed_limit_source']
  enabled_sources = state.get('slc_enabled_sources', ())
  active_only = state.get('slc_active_sources_only', False)
  abbreviated = state.get('slc_abbreviated_sources', False)

  rows = visible_source_rows(SOURCE_DEFS, state, active_source, enabled_sources, active_only)

  if not rows:
    _draw_sources_bubble_empty_state(panel_rect)
    return

  row_h = (panel_rect.height - 2 * _SOURCE_PANEL_PAD_Y) / len(rows)
  content_left = panel_rect.x + _SOURCE_PANEL_PAD_X
  content_right = panel_rect.x + panel_rect.width - _SOURCE_PANEL_PAD_X
  for index, (panel_label, _icon_key, value, is_active) in enumerate(rows):
    font = font_bold if is_active else font_semi
    compact_label = tr(_SOURCE_COMPACT_LABELS[panel_label])
    row_y = panel_rect.y + _SOURCE_PANEL_PAD_Y + index * row_h
    if panel_label == "Next" and index:
      rl.draw_line_ex(
        rl.Vector2(content_left, row_y),
        rl.Vector2(content_right, row_y),
        1,
        _SOURCE_DIVIDER,
      )

    value_text = source_value_text(value)
    text_color = _WHITE if is_active else _SOURCE_LABEL_MUTED

    if abbreviated:
      label_text = fit_source_label(
        f"{compact_label}-{source_abbreviated_value_text(value)}",
        "",
        content_right - content_left,
        lambda text, font=font: measure_text_cached(font, text, _SOURCE_LABEL_SIZE).x,
      )
      label_size = measure_text_cached(font, label_text, _SOURCE_LABEL_SIZE)
      text_y = round(row_y + (row_h - label_size.y) / 2)
      rl.draw_text_ex(
        font,
        label_text,
        rl.Vector2(content_left, text_y),
        _SOURCE_LABEL_SIZE,
        0,
        text_color,
      )
      continue

    full_label = tr(panel_label)
    value_size = measure_text_cached(font, value_text, _SOURCE_VALUE_SIZE)
    max_label_width = max(
      0.0,
      content_right - content_left - _SOURCE_MIN_LABEL_VALUE_GAP - value_size.x,
    )
    label_text = fit_source_label(
      full_label,
      compact_label,
      max_label_width,
      lambda text, font=font: measure_text_cached(font, text, _SOURCE_LABEL_SIZE).x,
    )
    label_size = measure_text_cached(font, label_text, _SOURCE_LABEL_SIZE)
    label_pos = rl.Vector2(content_left, round(row_y + (row_h - label_size.y) / 2))
    value_pos = rl.Vector2(round(content_right - value_size.x), round(row_y + (row_h - value_size.y) / 2))
    rl.draw_text_ex(font, label_text, label_pos, _SOURCE_LABEL_SIZE, 0, text_color)
    rl.draw_text_ex(font, value_text, value_pos, _SOURCE_VALUE_SIZE, 0, text_color)
