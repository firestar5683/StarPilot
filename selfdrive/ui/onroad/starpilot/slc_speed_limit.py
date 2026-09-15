import math
from typing import Optional

import pyray as rl
from openpilot.common.constants import CV
from openpilot.selfdrive.ui.ui_state import ui_state, UIStatus
from openpilot.selfdrive.ui.onroad.hud_renderer import COLORS
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.selfdrive.ui.onroad.starpilot.widget_style import (
  CONTROL_BG, CONTROL_BORDER, CONTROL_BORDER_WIDTH, CONTROL_ROUNDNESS, CONTROL_SEGMENTS, SLC_HEIGHT,
  draw_control_card, roundness_for,
)
from openpilot.selfdrive.ui.onroad.starpilot.source_bubble_layout import (
  enabled_source_titles, fit_source_label, source_abbreviated_value_text,
  source_content_metrics, source_value_text, visible_source_rows,
)
from openpilot.selfdrive.ui.lib.starpilot_state import starpilot_state

_WHITE = rl.Color(255, 255, 255, 255)

# ── Constants ─────────────────────────────────────────────────────────

# EU Vienna sign
EU_SIGN_SIZE = 176
EU_SIGN_WIDTH = 176
RED_RING_WIDTH = 20

# Pending sign blink cadence — 1s period, 50% duty cycle.
PENDING_BLINK_MS = 500

# Source display metadata: source name, main label, value key, bubble label, icon.
SOURCE_DEFS = [
  ("Dashboard", "Dash",  "dashboard_sl", "Dashboard",   "dashboard"),
  ("Map Data",  "MAP",   "map_sl",       "Map Data",    "map"),
  ("Vision",    "VISION", "vision_sl",   "Vision",       "camera"),
  ("Mapbox",    "MBOX",  "mapbox_sl",    "Mapbox",      "map"),
  ("Upcoming",  "NEXT",  "next_sl",      "Next",        "next"),
]

# Fonts
FONT_LABEL = 30
FONT_SOURCE = 40  # Set Speed MAX label size.
FONT_SPEED = 90  # Set Speed value size.
FONT_OFFSET = 29  # Compact offset text.
OFFSET_CHIP_SEGMENTS = 8  # Capsule curve segments.
FONT_EU_LARGE = 70
FONT_EU_SMALL = 60
FONT_EU_OFFSET = 40

# Vision speed-limit pulse — one-shot purple highlight when the active source
# is "Vision" and the resolved value just changed.
VISION_SPEED_LIMIT_PULSE_SECONDS = 1.0
VISION_SPEED_LIMIT_PULSE_COLOR = rl.Color(188, 132, 255, 255)
VISION_SPEED_LIMIT_CHANGE_THRESHOLD = 0.1  # m/s


# ── Vision speed-limit pulse state (one-shot highlight) ────────────────
# Persists across frames so we can detect a just-changed vision limit and
# animate the sign colors toward VISION_SPEED_LIMIT_PULSE_COLOR for
# VISION_SPEED_LIMIT_PULSE_SECONDS. Held at module scope because this file
# is a procedural API consumed once per frame by StarPilotOnroadView.

_pulse = {
  "last": 0.0,            # last resolved vision limit (m/s) seen while active
  "start": -VISION_SPEED_LIMIT_PULSE_SECONDS,  # get_time() stamp of the last change
}


def _reset_pulse() -> None:
  """Clear pulse state when SLC goes hidden or stale."""
  _pulse["last"] = 0.0
  _pulse["start"] = -VISION_SPEED_LIMIT_PULSE_SECONDS


def _tick_pulse(source: str, resolved_ms: float) -> None:
  """Update pulse state once per frame from the resolved speed limit.

  The pulse fires when the active source is "Vision" and its resolved value
  changed by at least VISION_SPEED_LIMIT_CHANGE_THRESHOLD (m/s).
  """
  vision_active = source == "Vision" and resolved_ms > 0.0
  if not vision_active:
    _pulse["start"] = -VISION_SPEED_LIMIT_PULSE_SECONDS
    return

  if abs(resolved_ms - _pulse["last"]) >= VISION_SPEED_LIMIT_CHANGE_THRESHOLD:
    _pulse["start"] = rl.get_time()
  _pulse["last"] = resolved_ms


def _speed_limit_pulse_color(base: rl.Color, alpha: int) -> rl.Color:
  """Blend ``base`` toward VISION_SPEED_LIMIT_PULSE_COLOR with a sin(pi*t) ease.

  Returns ``base`` unchanged (with the supplied alpha) outside the pulse
  window. Inside it, r/g/b are eased toward the pulse color along sin(pi*t)
  where t is elapsed / VISION_SPEED_LIMIT_PULSE_SECONDS.
  """
  base_with_alpha = rl.Color(base.r, base.g, base.b, alpha)
  elapsed = rl.get_time() - _pulse["start"]
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

def _get_slc_state():
  """Extract SLC state from SubMaster. Returns dict or None if stale/hidden."""
  sm = ui_state.sm
  if sm.recv_frame["starpilotPlan"] < ui_state.started_frame:
    _reset_pulse()
    return None

  plan = sm["starpilotPlan"]
  speed_limit_changed = plan.speedLimitChanged

  params = ui_state.ui_params
  show_slc = params.get_bool("ShowSpeedLimits")
  unconfirmed_valid = plan.unconfirmedSlcSpeedLimit > 1

  if not show_slc:
    _reset_pulse()
    return None

  speed_conversion = CV.MS_TO_KPH if ui_state.is_metric else CV.MS_TO_MPH
  show_offset = params.get_bool("ShowSLCOffset")

  dashboard_sl = sm["starpilotCarState"].dashboardSpeedLimit if sm.valid.get("starpilotCarState", False) else 0.0
  vision_enabled = params.get_bool("VisionSpeedLimitDetection")
  vision_sl = ui_state.params_memory.get_float("VisionSpeedLimit") if vision_enabled else 0.0
  primary_priority = params.get("SLCPriority1", encoding="utf-8") or "Map Data"
  secondary_priority = params.get("SLCPriority2", encoding="utf-8") or "None"
  mapbox_enabled = params.get_bool("SLCMapboxFiller") and bool(
    params.get("MapboxSecretKey", encoding="utf-8")
  )

  slc_overridden_speed = plan.slcOverriddenSpeed
  # Keep the source limit visible when overridden.
  speed_limit = plan.slcSpeedLimit

  # Resolved limit in m/s (pre-conversion, pre-offset) — feeds the vision pulse
  # change detector so the comparison is unit-stable across km/h ↔ mph flips.
  resolved_ms = speed_limit

  # Add the per-limit offset to the displayed value only when NOT overridden
  # AND ShowSLCOffset is off (when the offset toggle is on, it's rendered as
  # a separate field below the speed number instead).
  if slc_overridden_speed == 0 and not show_offset:
    speed_limit += plan.slcSpeedLimitOffset
  speed_limit *= speed_conversion

  speed_limit_offset = plan.slcSpeedLimitOffset * speed_conversion
  offset_str = f"{'+' if speed_limit_offset > 0 else '-'}{abs(int(round(speed_limit_offset)))}" if speed_limit_offset != 0 else "\u2013"

  # Update the vision-source pulse once per frame, after resolved_ms is known
  # and before any sign colors are computed downstream.
  _tick_pulse(plan.slcSpeedLimitSource, resolved_ms)

  return {
    'speed_limit': speed_limit,
    'speed_limit_str': "\u2013" if speed_limit <= 1 else str(int(round(speed_limit))),
    'slc_overridden_speed': slc_overridden_speed,
    'speed_limit_source': plan.slcSpeedLimitSource,
    'unconfirmed_speed_limit': max(0.0, plan.unconfirmedSlcSpeedLimit * speed_conversion),
    'unconfirmed_valid': unconfirmed_valid,
    'speed_limit_changed': speed_limit_changed,
    'show_offset': show_offset,
    'use_vienna': params.get_bool("UseVienna"),
    'offset_str': offset_str,
    'speed_conversion': speed_conversion,
    'speed_unit': " km/h" if ui_state.is_metric else " mph",
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


_ACTIVE_SOURCE_LABELS = {title: abbrev.upper() for title, abbrev, *_ in SOURCE_DEFS}


def _active_source_label(state: dict) -> str:
  source = state.get("speed_limit_source")
  if not source or source == "None":
    return tr("LIMIT")
  return _ACTIVE_SOURCE_LABELS.get(source, source.upper())


def _source_label_color(alpha: int, is_overridden: bool = False) -> rl.Color:
  """Match Set Speed's MAX label color."""
  if is_overridden or ui_state.status in (UIStatus.DISENGAGED, UIStatus.OVERRIDE):
    base = COLORS.DISENGAGED
  elif ui_state.status == UIStatus.ENGAGED:
    base = COLORS.ENGAGED
  else:
    base = COLORS.GREY
  return _speed_limit_pulse_color(base, alpha)


# ── US MUTCD Sign ─────────────────────────────────────────────────────

def _draw_offset_chip(rect: rl.Rectangle, offset_str: str, color: rl.Color) -> None:
  """Draw the optional SLC offset as a compact accent chip."""
  font = _get_semi_bold()
  text_size = measure_text_cached(font, offset_str, FONT_OFFSET)
  chip_w = max(64.0, text_size.x + 24.0)
  chip_h = 36.0
  chip_rect = rl.Rectangle(
    rect.x + (rect.width - chip_w) / 2,
    rect.y + rect.height - chip_h - 10,
    chip_w,
    chip_h,
  )
  chip_fill = rl.Color(0, 0, 0, min(120, color.a))
  roundness = roundness_for(chip_rect, 18)
  rl.draw_rectangle_rounded(chip_rect, roundness, OFFSET_CHIP_SEGMENTS, chip_fill)
  rl.draw_rectangle_rounded_lines_ex(chip_rect, roundness, OFFSET_CHIP_SEGMENTS, 2, color)
  rl.draw_text_ex(
    font,
    offset_str,
    rl.Vector2(chip_rect.x + (chip_w - text_size.x) / 2, chip_rect.y + (chip_h - text_size.y) / 2),
    FONT_OFFSET,
    0,
    color,
  )


def _draw_us_sign(x: float, y: float, sign_width: float, sign_height: float,
                  speed_text: str, offset_str: str,
                  source_label: str, alpha: int, show_offset: bool, *,
                  pending: bool = False, is_overridden: bool = False):
  """Draw the NA control card at (x, y).

  The card keeps the SLC's label/value hierarchy while sharing the exact
  visible frame geometry with Set Speed. Border and text colors continue to
  use the existing Vision pulse and pending blink behavior.
  """
  # Pending: blink white/red. Active: shared blue-grey.
  if pending:
    blink_on = int(rl.get_time() * 1000) % 1000 < PENDING_BLINK_MS
    base_border = rl.Color(255, 255, 255, alpha) if blink_on else rl.Color(201, 34, 49, alpha)
  else:
    base_border = rl.Color(CONTROL_BORDER.r, CONTROL_BORDER.g, CONTROL_BORDER.b,
                            min(alpha, CONTROL_BORDER.a))

  # Compose the blink base with the active vision pulse (no-op outside window).
  border_color = _speed_limit_pulse_color(base_border, base_border.a)
  # White value text reads on the translucent road background.
  text_color = _speed_limit_pulse_color(rl.Color(255, 255, 255, 255), alpha)

  card_rect = rl.Rectangle(x, y, sign_width, sign_height)
  card_fill = rl.Color(CONTROL_BG.r, CONTROL_BG.g, CONTROL_BG.b, min(CONTROL_BG.a, alpha))
  draw_control_card(card_rect, fill=card_fill, border=border_color,
                    border_width=CONTROL_BORDER_WIDTH)

  font_bold = _get_bold()
  font_semi = _get_semi_bold()
  cx = x + sign_width / 2

  # Pending layout: "PENDING" + "LIMIT" + speed (no offset shown when pending).
  if pending:
    pending_size = measure_text_cached(font_semi, tr("PENDING"), FONT_LABEL - 2)
    rl.draw_text_ex(font_semi, tr("PENDING"), rl.Vector2(cx - pending_size.x / 2, y + 20), FONT_LABEL - 2, 0, text_color)
    limit_size = measure_text_cached(font_semi, tr("LIMIT"), FONT_LABEL)
    rl.draw_text_ex(font_semi, tr("LIMIT"), rl.Vector2(cx - limit_size.x / 2, y + 48), FONT_LABEL, 0, text_color)
    speed_size = measure_text_cached(font_bold, speed_text, FONT_SPEED - 6)
    rl.draw_text_ex(font_bold, speed_text, rl.Vector2(cx - speed_size.x / 2, y + 85), FONT_SPEED - 6, 0, text_color)
  elif show_offset:
    # Offset ON: source at the top, speed below it, and the offset in a chip.
    source_size = measure_text_cached(font_semi, source_label, FONT_SOURCE)
    source_color = _source_label_color(alpha, is_overridden=is_overridden)
    rl.draw_text_ex(font_semi, source_label, rl.Vector2(cx - source_size.x / 2, y + 8), FONT_SOURCE, 0, source_color)

    speed_size = measure_text_cached(font_bold, speed_text, FONT_SPEED)
    rl.draw_text_ex(font_bold, speed_text, rl.Vector2(cx - speed_size.x / 2, y + 44), FONT_SPEED, 0, text_color)
    _draw_offset_chip(card_rect, offset_str, text_color)
  else:
    # Offset OFF: match Set Speed typography.
    source_size = measure_text_cached(font_semi, source_label, FONT_SOURCE)
    source_color = _source_label_color(alpha, is_overridden=is_overridden)
    rl.draw_text_ex(font_semi, source_label, rl.Vector2(cx - source_size.x / 2, y + 27), FONT_SOURCE, 0, source_color)

    speed_size = measure_text_cached(font_bold, speed_text, FONT_SPEED)
    rl.draw_text_ex(font_bold, speed_text, rl.Vector2(cx - speed_size.x / 2, y + 77), FONT_SPEED, 0, text_color)


# ── EU Vienna Sign ────────────────────────────────────────────────────

def _draw_eu_sign(x: float, y: float, speed_text: str, offset_str: str,
                   source_label: str, text_alpha: int, show_offset: bool, *, pending: bool = False):
  """Draw EU-style (Vienna) speed limit sign at (x, y).

  White disk with a pulsable red ring and pulsable black text. The pre-existing
  pending-text blink (black <-> red) composes with the vision pulse: outside the
  pulse window the blink is unchanged, inside it both colors are eased toward
  VISION_SPEED_LIMIT_PULSE_COLOR.
  """
  center_x = x + EU_SIGN_SIZE / 2
  center_y = y + EU_SIGN_SIZE / 2
  radius = EU_SIGN_SIZE / 2

  # White disk fill.
  rl.draw_circle(int(center_x), int(center_y), radius, rl.Color(255, 255, 255, text_alpha))
  # Red ring; eased toward VISION_SPEED_LIMIT_PULSE_COLOR when a Vision-sourced
  # limit just changed.
  ring_color = _speed_limit_pulse_color(rl.Color(201, 34, 49, 255), text_alpha)
  rl.draw_ring(rl.Vector2(center_x, center_y), radius - RED_RING_WIDTH, radius,
               0, 360, 64, ring_color)

  font_bold = _get_bold()

  eu_font = FONT_EU_LARGE if len(speed_text) <= 2 else FONT_EU_SMALL

  # EU pending: text blinks black/red, composed with the vision pulse.
  if pending:
    blink_on = int(rl.get_time() * 1000) % 1000 < PENDING_BLINK_MS
    base_text = rl.Color(0, 0, 0, 255) if blink_on else rl.Color(201, 34, 49, 255)
  else:
    base_text = rl.Color(0, 0, 0, 255)
  text_color = _speed_limit_pulse_color(base_text, text_alpha)

  # Pending: text centered (no offset display)
  if pending:
    speed_size = measure_text_cached(font_bold, speed_text, eu_font)
    speed_pos = rl.Vector2(center_x - speed_size.x / 2, center_y - speed_size.y / 2)
    rl.draw_text_ex(font_bold, speed_text, speed_pos, eu_font, 0, text_color)
  elif not show_offset:
    font_semi = _get_semi_bold()
    source_size = measure_text_cached(font_semi, source_label, FONT_LABEL - 4)
    source_pos = rl.Vector2(center_x - source_size.x / 2, y + 16)
    rl.draw_text_ex(font_semi, source_label, source_pos, FONT_LABEL - 4, 0, text_color)

    speed_size = measure_text_cached(font_bold, speed_text, eu_font)
    speed_pos = rl.Vector2(center_x - speed_size.x / 2, center_y - speed_size.y / 2)
    rl.draw_text_ex(font_bold, speed_text, speed_pos, eu_font, 0, text_color)
  else:
    # Offset ON: source at the top, speed below it, offset at the bottom.
    font_semi = _get_semi_bold()
    source_size = measure_text_cached(font_semi, source_label, FONT_LABEL - 4)
    source_pos = rl.Vector2(center_x - source_size.x / 2, y + 16)
    rl.draw_text_ex(font_semi, source_label, source_pos, FONT_LABEL - 4, 0, text_color)

    speed_size = measure_text_cached(font_bold, speed_text, eu_font)
    speed_pos = rl.Vector2(center_x - speed_size.x / 2, center_y - speed_size.y / 2 - 5)
    rl.draw_text_ex(font_bold, speed_text, speed_pos, eu_font, 0, text_color)

    offset_size = measure_text_cached(font_semi, offset_str, FONT_EU_OFFSET)
    offset_pos = rl.Vector2(center_x - offset_size.x / 2, y + 122)
    rl.draw_text_ex(font_semi, offset_str, offset_pos, FONT_EU_OFFSET, 0, text_color)


# ── Dispatcher (pending and active sign share the same rect) ─────────

def _draw_sign(state: dict, rect: rl.Rectangle, *, pending: bool = False):
  """Draw either the pending or active sign in the given rect."""
  if pending:
    # Pending shows the unconfirmed value, full opacity
    speed_text = ("\u2013" if state['unconfirmed_speed_limit'] <= 1
                  else str(int(round(state['unconfirmed_speed_limit']))))
  else:
    speed_text = state['speed_limit_str']

  text_alpha = 255
  is_overridden = not pending and state['slc_overridden_speed'] != 0
  source_label = _active_source_label(state)

  if state['use_vienna']:
    _draw_eu_sign(rect.x, rect.y, speed_text, state['offset_str'], source_label, text_alpha,
                   state['show_offset'], pending=pending)
  else:
    _draw_us_sign(rect.x, rect.y, rect.width, rect.height, speed_text, state['offset_str'],
                   source_label, text_alpha, state['show_offset'], pending=pending,
                   is_overridden=is_overridden)


# ── Sources Bubble (expandable overlay) ────────────────────────────────

# Fixed outer footprint; the content scale adapts to the visible row count.
_SOURCE_PANEL_WIDTH = 248
_SOURCE_PANEL_GAP = 20
_SOURCE_PANEL_PAD_X = 9
_SOURCE_PANEL_PAD_Y = 2
_SOURCE_PANEL_BG = rl.Color(0, 0, 0, 175)
_SOURCE_PANEL_BORDER = rl.Color(196, 205, 208, 80)
_SOURCE_DIVIDER = rl.Color(196, 205, 208, 100)
_SOURCE_ACTIVE_BAR = rl.Color(CONTROL_BORDER.r, CONTROL_BORDER.g, CONTROL_BORDER.b, 230)
_SOURCE_ICON_MUTED = rl.Color(160, 170, 175, 200)
_SOURCE_LABEL_MUTED = rl.Color(166, 166, 166, 255)
_SOURCE_ACTIVE_BAR_WIDTH = 6.0
_SOURCE_ACTIVE_BAR_HEIGHT = 36.0
_SOURCE_ACTIVE_BAR_X = 2.0
_SOURCE_ACTIVE_BAR_ROW_INSET = 3.0
_SOURCE_MIN_LABEL_VALUE_GAP = 6.0

_SOURCE_COMPACT_LABELS = {
  "Dashboard": "Dash",
  "Map Data": "OSM",
  "Vision": "Vision",
  "Mapbox": "Mapbox",
  "Next": "Next",
}


def _draw_source_icon(icon_key: str, x: float, y: float, size: float, color: rl.Color) -> None:
  """Draw the small, intentionally simple source glyphs used by the panel."""
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
  else:  # Dashboard / fallback
    dashboard_scale = 1.22
    pivot = rl.Vector2(cx, cy + size * 0.17)
    inner_radius = size * 0.27 * dashboard_scale
    outer_radius = size * 0.34 * dashboard_scale
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
    rl.draw_circle_v(pivot, max(2.0, size * 0.06 * dashboard_scale), color)


def _draw_sources_bubble_empty_state(panel_rect: rl.Rectangle) -> None:
  """Draw the 3-line centered empty state when no sources are available."""
  font = _get_semi_bold()
  font_size = 30
  line_gap = 6.0
  lines = (tr("NO"), tr("SOURCES"), tr("AVAILABLE"))

  line_sizes = [measure_text_cached(font, line, font_size) for line in lines]
  total_h = sum(sz.y for sz in line_sizes) + line_gap * (len(lines) - 1)
  curr_y = round(panel_rect.y + (panel_rect.height - total_h) / 2)

  for line, sz in zip(lines, line_sizes):
    pos_x = round(panel_rect.x + (panel_rect.width - sz.x) / 2)
    rl.draw_text_ex(font, line, rl.Vector2(pos_x, curr_y), font_size, 0, _WHITE)
    curr_y += round(sz.y + line_gap)


def _draw_sources_bubble(state: dict, sign_rect: rl.Rectangle):
  """Draw the expanded source list attached to the SLC card."""
  font_semi = _get_semi_bold()
  font_bold = _get_bold()
  active_source = state['speed_limit_source']
  enabled_sources = state.get('slc_enabled_sources', ())
  active_only = state.get('slc_active_sources_only', False)
  abbreviated = state.get('slc_abbreviated_sources', False)

  panel_rect = rl.Rectangle(
    sign_rect.x + sign_rect.width + _SOURCE_PANEL_GAP,
    sign_rect.y,
    _SOURCE_PANEL_WIDTH,
    sign_rect.height,
  )
  rl.draw_rectangle_rounded(panel_rect, CONTROL_ROUNDNESS, CONTROL_SEGMENTS, _SOURCE_PANEL_BG)
  rl.draw_rectangle_rounded_lines_ex(
    panel_rect, CONTROL_ROUNDNESS, CONTROL_SEGMENTS, 1, _SOURCE_PANEL_BORDER,
  )

  rows = [
    (
      panel_label,
      _SOURCE_COMPACT_LABELS[panel_label],
      icon_key,
      value,
      is_active,
    )
    for panel_label, icon_key, value, is_active in visible_source_rows(
      SOURCE_DEFS, state, active_source, enabled_sources, active_only,
    )
  ]

  if not rows:
    _draw_sources_bubble_empty_state(panel_rect)
    return

  row_h = (panel_rect.height - 2 * _SOURCE_PANEL_PAD_Y) / len(rows)
  content_left = panel_rect.x + _SOURCE_PANEL_PAD_X
  content_right = panel_rect.x + panel_rect.width - _SOURCE_PANEL_PAD_X
  font_size, icon_size, icon_gap = source_content_metrics(len(rows))
  label_left = (
    content_left + _SOURCE_ACTIVE_BAR_WIDTH + _SOURCE_MIN_LABEL_VALUE_GAP
    if abbreviated else content_left + icon_size + icon_gap
  )

  for index, (panel_label, compact_label, icon_key, value, is_active) in enumerate(rows):
    row_y = panel_rect.y + _SOURCE_PANEL_PAD_Y + index * row_h
    if index:
      divider_y = round(row_y)
      rl.draw_line_ex(
        rl.Vector2(content_left, divider_y),
        rl.Vector2(content_right, divider_y),
        1,
        _SOURCE_DIVIDER,
      )

    if is_active:
      active_bar_height = min(
        _SOURCE_ACTIVE_BAR_HEIGHT,
        max(10.0, row_h - 2 * _SOURCE_ACTIVE_BAR_ROW_INSET),
      )
      active_bar_rect = rl.Rectangle(
        panel_rect.x + _SOURCE_ACTIVE_BAR_X,
        round(row_y + (row_h - active_bar_height) / 2),
        _SOURCE_ACTIVE_BAR_WIDTH,
        active_bar_height,
      )
      rl.draw_rectangle_rounded(active_bar_rect, 0.5, 4, _SOURCE_ACTIVE_BAR)

    value_text = source_value_text(value)
    text_color = _WHITE if is_active else _SOURCE_LABEL_MUTED

    if abbreviated:
      text_font = font_bold if is_active else font_semi
      label_text = fit_source_label(
        f"{tr(compact_label)}-{source_abbreviated_value_text(value)}",
        "",
        content_right - label_left,
        lambda text: measure_text_cached(text_font, text, font_size).x,
      )
      label_size = measure_text_cached(text_font, label_text, font_size)
      text_y = round(row_y + (row_h - label_size.y) / 2)
      rl.draw_text_ex(
        text_font,
        label_text,
        rl.Vector2(label_left, text_y),
        font_size,
        0,
        text_color,
      )
      continue

    compact_label = tr(compact_label)
    full_label = tr(panel_label)
    value_size = measure_text_cached(font_bold, value_text, font_size)
    max_label_width = max(
      0.0,
      content_right - label_left - _SOURCE_MIN_LABEL_VALUE_GAP - value_size.x,
    )
    label_text = fit_source_label(
      full_label,
      compact_label,
      max_label_width,
      lambda text: measure_text_cached(font_semi, text, font_size).x,
    )
    label_size = measure_text_cached(font_semi, label_text, font_size)
    text_height = max(label_size.y, value_size.y)
    text_y = round(row_y + (row_h - text_height) / 2)
    icon_y = round(row_y + (row_h - icon_size) / 2)

    icon_color = _WHITE if is_active else _SOURCE_ICON_MUTED
    _draw_source_icon(icon_key, content_left, icon_y, icon_size, icon_color)

    label_pos = rl.Vector2(label_left, text_y)
    value_pos = rl.Vector2(round(content_right - value_size.x), text_y)
    rl.draw_text_ex(font_semi, label_text, label_pos, font_size, 0, text_color)
    rl.draw_text_ex(font_bold, value_text, value_pos, font_size, 0, text_color)


# ── Public API ────────────────────────────────────────────────────────

def render_speed_limit_at(state: dict, rect: rl.Rectangle, expanded: bool = False) -> Optional[rl.Rectangle]:
  """Render the SLC sign and optional source bubble at a layout rect."""
  flashing_pending = state['speed_limit_changed'] and state['unconfirmed_valid']

  if flashing_pending:
    _draw_sign(state, rect, pending=True)
    return None

  _draw_sign(state, rect, pending=False)

  use_vienna = state['use_vienna']
  visual_rect = rl.Rectangle(rect.x, rect.y, EU_SIGN_SIZE, EU_SIGN_SIZE) if use_vienna else rect

  if expanded:
    _draw_sources_bubble(state, visual_rect)

  return visual_rect
