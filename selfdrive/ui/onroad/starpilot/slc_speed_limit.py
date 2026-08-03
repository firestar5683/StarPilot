import math
from typing import Optional

import pyray as rl
from openpilot.common.constants import CV
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.text_measure import measure_text_cached

# ── Constants ─────────────────────────────────────────────────────────

# Set speed rect layout (from hud_renderer.py UI_CONFIG)
SET_SPEED_WIDTH_IMP = 172
SET_SPEED_WIDTH_MET = 200

# US MUTCD sign
US_SIGN_HEIGHT = 186
US_INNER_RADIUS = 16
US_BORDER_WIDTH = 6
US_INSET = 9

# EU Vienna sign
EU_SIGN_SIZE = 176
EU_SIGN_WIDTH = 176
RED_RING_WIDTH = 20

# Pending sign blink cadence — 1s period, 50% duty cycle.
PENDING_BLINK_MS = 500

# Source display metadata: title, abbreviation, raw-value key (display order).
SOURCE_DEFS = [
  ("Dashboard", "Dash",   "dashboard_sl"),
  ("Map Data",  "Maps",    "map_sl"),
  ("Vision",    "Vision", "vision_sl"),
  ("Mapbox",    "Mapbox", "mapbox_sl"),
  ("Upcoming",  "Next",   "next_sl"),
]

# Fonts
FONT_LABEL = 28
FONT_SPEED = 70
FONT_OFFSET = 50
FONT_EU_LARGE = 70
FONT_EU_SMALL = 60
FONT_EU_OFFSET = 40

# Layout
SIGN_MARGIN = 12

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
  "active": False,        # is the active source currently "Vision"?
  "last": 0.0,            # last resolved vision limit (m/s) seen while active
  "start": -VISION_SPEED_LIMIT_PULSE_SECONDS,  # get_time() stamp of the last change
}


def _reset_pulse() -> None:
  """Clear pulse state when SLC goes hidden or stale."""
  _pulse["active"] = False
  _pulse["last"] = 0.0
  _pulse["start"] = -VISION_SPEED_LIMIT_PULSE_SECONDS


def _tick_pulse(source: str, resolved_ms: float) -> None:
  """Update pulse state once per frame from the resolved speed limit.

  The pulse fires when the active source is "Vision" and either the source
  just became active or the resolved value changed by at least
  VISION_SPEED_LIMIT_CHANGE_THRESHOLD (m/s).
  """
  vision_active = source == "Vision" and resolved_ms > 0.0
  if vision_active and (not _pulse["active"] or abs(resolved_ms - _pulse["last"]) >= VISION_SPEED_LIMIT_CHANGE_THRESHOLD):
    _pulse["start"] = rl.get_time()
  _pulse["active"] = vision_active
  _pulse["last"] = resolved_ms if vision_active else 0.0


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
  show_slc = params.get_bool("ShowSpeedLimits") or params.get_bool("SpeedLimitController")
  hide_sl = params.get_bool("HideSpeedLimit")
  unconfirmed_valid = plan.unconfirmedSlcSpeedLimit > 1
  # A pending (unconfirmed) limit overrides HideSpeedLimit so the prompt always shows.
  hide = not (speed_limit_changed and unconfirmed_valid) and hide_sl

  if not show_slc and not speed_limit_changed:
    _reset_pulse()
    return None

  speed_conversion = CV.MS_TO_KPH if ui_state.is_metric else CV.MS_TO_MPH
  show_offset = params.get_bool("ShowSLCOffset")

  dashboard_sl = sm["starpilotCarState"].dashboardSpeedLimit if sm.valid.get("starpilotCarState", False) else 0.0
  vision_sl = ui_state.params_memory.get_float("VisionSpeedLimit") if params.get_bool("VisionSpeedLimitDetection") else 0.0

  slc_overridden_speed = plan.slcOverriddenSpeed
  # Driver override takes precedence over the planner's limit when active.
  speed_limit = slc_overridden_speed if slc_overridden_speed != 0 else plan.slcSpeedLimit

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
    'hide': hide,
    'show_offset': show_offset,
    'use_vienna': params.get_bool("UseVienna"),
    'offset_str': offset_str,
    'speed_conversion': speed_conversion,
    'speed_unit': " km/h" if ui_state.is_metric else " mph",
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


# ── US MUTCD Sign ─────────────────────────────────────────────────────

def _draw_us_sign(x: float, y: float, sign_width: float, speed_text: str, offset_str: str,
                  alpha: int, show_offset: bool, *, pending: bool = False):
  """Draw US-style speed limit sign at (x, y) with the given width.

  Transparent panel (the road shows through) drawn with only an inset
  white-on-transparent outline border and white text. Border and text colors
  are routed through _speed_limit_pulse_color so a freshly-changed Vision
  limit pulses toward VISION_SPEED_LIMIT_PULSE_COLOR for
  VISION_SPEED_LIMIT_PULSE_SECONDS. The pending-state blink (white <-> red
  border) composes with that pulse. ``alpha`` is the sign-wide opacity
  (e.g. 72 when the driver has manually overridden the limit, 255 otherwise).
  """
  # Pending: border blinks white <-> red. Active: border is white.
  if pending:
    blink_on = int(rl.get_time() * 1000) % 1000 < PENDING_BLINK_MS
    base_border = rl.Color(255, 255, 255, alpha) if blink_on else rl.Color(201, 34, 49, alpha)
  else:
    base_border = rl.Color(255, 255, 255, alpha)

  # Compose the blink base with the active vision pulse (no-op outside window).
  border_color = _speed_limit_pulse_color(base_border, alpha)
  # White text reads on the transparent background, matching the border color.
  text_color = _speed_limit_pulse_color(rl.Color(255, 255, 255, 255), alpha)

  # No solid fill — the sign is an outline-only overlay on the road.
  # Inset outline border; thinner than the outer radius for visual separation.
  border_rect = rl.Rectangle(x + US_INSET, y + US_INSET,
                              sign_width - 2 * US_INSET,
                              US_SIGN_HEIGHT - 2 * US_INSET)
  rl.draw_rectangle_rounded_lines_ex(border_rect, US_INNER_RADIUS / (US_SIGN_HEIGHT - 18), 16,
                                     max(US_BORDER_WIDTH - 2, 1), border_color)

  font_bold = _get_bold()
  font_semi = _get_semi_bold()
  cx = x + sign_width / 2

  # Pending layout: "PENDING" + "LIMIT" + speed (no offset shown when pending).
  if pending:
    pending_size = measure_text_cached(font_semi, tr("PENDING"), FONT_LABEL)
    rl.draw_text_ex(font_semi, tr("PENDING"), rl.Vector2(cx - pending_size.x / 2, y + 22), FONT_LABEL, 0, text_color)
    limit_size = measure_text_cached(font_semi, tr("LIMIT"), FONT_LABEL)
    rl.draw_text_ex(font_semi, tr("LIMIT"), rl.Vector2(cx - limit_size.x / 2, y + 51), FONT_LABEL, 0, text_color)
    speed_size = measure_text_cached(font_bold, speed_text, FONT_SPEED)
    rl.draw_text_ex(font_bold, speed_text, rl.Vector2(cx - speed_size.x / 2, y + 85), FONT_SPEED, 0, text_color)
  elif show_offset:
    # Offset ON: "LIMIT" at y=22, speed at y=51, offset at y=120
    limit_size = measure_text_cached(font_semi, tr("LIMIT"), FONT_LABEL)
    rl.draw_text_ex(font_semi, tr("LIMIT"), rl.Vector2(cx - limit_size.x / 2, y + 22), FONT_LABEL, 0, text_color)

    speed_size = measure_text_cached(font_bold, speed_text, FONT_SPEED)
    rl.draw_text_ex(font_bold, speed_text, rl.Vector2(cx - speed_size.x / 2, y + 51), FONT_SPEED, 0, text_color)

    offset_size = measure_text_cached(font_semi, offset_str, FONT_OFFSET)
    rl.draw_text_ex(font_semi, offset_str, rl.Vector2(cx - offset_size.x / 2, y + 120), FONT_OFFSET, 0, text_color)
  else:
    # Offset OFF: "SPEED" at y=22, "LIMIT" at y=51, speed at y=85
    speed_label_size = measure_text_cached(font_semi, tr("SPEED"), FONT_LABEL)
    rl.draw_text_ex(font_semi, tr("SPEED"), rl.Vector2(cx - speed_label_size.x / 2, y + 22), FONT_LABEL, 0, text_color)

    limit_size = measure_text_cached(font_semi, tr("LIMIT"), FONT_LABEL)
    rl.draw_text_ex(font_semi, tr("LIMIT"), rl.Vector2(cx - limit_size.x / 2, y + 51), FONT_LABEL, 0, text_color)

    speed_size = measure_text_cached(font_bold, speed_text, FONT_SPEED)
    rl.draw_text_ex(font_bold, speed_text, rl.Vector2(cx - speed_size.x / 2, y + 85), FONT_SPEED, 0, text_color)


# ── EU Vienna Sign ────────────────────────────────────────────────────

def _draw_eu_sign(x: float, y: float, speed_text: str, offset_str: str,
                   text_alpha: int, show_offset: bool, *, pending: bool = False):
  """Draw EU-style (Vienna) speed limit sign at (x, y).

  White disk with a pulsable red ring and pulsable black text. The disk
  fill, ring, and text all carry the sign-wide ``text_alpha`` (e.g. 72 when
  driver-overridden, 255 otherwise), so the road shows through when dimmed
  without losing legibility. The pre-existing pending-text blink
  (black <-> red) composes with the vision pulse: outside the pulse window
  the blink is unchanged, inside it both colors are eased toward
  VISION_SPEED_LIMIT_PULSE_COLOR.
  """
  center_x = x + EU_SIGN_SIZE / 2
  center_y = y + EU_SIGN_SIZE / 2
  radius = EU_SIGN_SIZE / 2

  # White disk fill; alpha-dims with the sign so an overridden limit fades
  # against the road.
  rl.draw_circle(int(center_x), int(center_y), radius, rl.Color(255, 255, 255, text_alpha))
  # Red ring; eased toward VISION_SPEED_LIMIT_PULSE_COLOR when a Vision-sourced
  # limit just changed, and alpha-dims with the sign.
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
  if pending or not show_offset:
    speed_size = measure_text_cached(font_bold, speed_text, eu_font)
    speed_pos = rl.Vector2(center_x - speed_size.x / 2, center_y - speed_size.y / 2)
    rl.draw_text_ex(font_bold, speed_text, speed_pos, eu_font, 0, text_color)
  else:
    # Offset ON: speed shifted up, offset below
    speed_size = measure_text_cached(font_bold, speed_text, eu_font)
    speed_pos = rl.Vector2(center_x - speed_size.x / 2, center_y - speed_size.y / 2 - 25)
    rl.draw_text_ex(font_bold, speed_text, speed_pos, eu_font, 0, text_color)

    font_semi = _get_semi_bold()
    offset_size = measure_text_cached(font_semi, offset_str, FONT_EU_OFFSET)
    offset_pos = rl.Vector2(center_x - offset_size.x / 2, y + 100)
    rl.draw_text_ex(font_semi, offset_str, offset_pos, FONT_EU_OFFSET, 0, text_color)


# ── Dispatcher (pending and active sign share the same rect) ─────────

def _draw_sign(state: dict, rect: rl.Rectangle, *, pending: bool = False):
  """Draw either the pending or active sign in the given rect."""
  if pending:
    # Pending shows the unconfirmed value, full opacity
    speed_text = ("\u2013" if state['unconfirmed_speed_limit'] <= 1
                  else str(int(round(state['unconfirmed_speed_limit']))))
    text_alpha = 255
  else:
    speed_text = state['speed_limit_str']
    # Override dim: when the driver has manually overridden the speed limit,
    # fade the sign to alpha=72 to indicate it's no longer the auto-detected
    # value.
    text_alpha = 72 if state['slc_overridden_speed'] != 0 else 255

  if state['use_vienna']:
    _draw_eu_sign(rect.x, rect.y, speed_text, state['offset_str'], text_alpha,
                   state['show_offset'], pending=pending)
  else:
    _draw_us_sign(rect.x, rect.y, rect.width, speed_text, state['offset_str'],
                   text_alpha, state['show_offset'], pending=pending)


# ── Active Source Label (single-line mode when sources panel is off) ──

_SOURCE_ABBREV = {"Dashboard": "Dash", "Map Data": "Maps", "Vision": "Vision",
                  "Mapbox": "Mapbox", "Upcoming": "Next"}

def _draw_active_source_label(state: dict, cx: float, bottom_y: float, sign_width: float, expanded: bool = False) -> Optional[rl.Rectangle]:
  """Draw the single active-source pill below the sign. Returns pill rect for hit-testing."""
  source = state.get('speed_limit_source')
  if not source or source == "None" or source == "":
    return None
  label = _SOURCE_ABBREV.get(source, source.upper())
  font = _get_semi_bold()
  font_size = 24
  sz = measure_text_cached(font, label, font_size)
  
  pill_w = sign_width
  pill_h = 32
  rect = rl.Rectangle(cx - pill_w / 2, bottom_y + 8, pill_w, pill_h)
  
  rl.draw_rectangle_rounded(rect, 0.4, 8, rl.Color(0, 0, 0, 180))
  rl.draw_rectangle_rounded_lines_ex(rect, 0.4, 8, 1, rl.Color(255, 255, 255, 100))
  
  text_y = rect.y + (pill_h - sz.y) / 2
  rl.draw_text_ex(font, label, rl.Vector2(cx - sz.x / 2, text_y), font_size, 0, rl.WHITE)
  return rect


# ── Sources Bubble (expandable overlay) ────────────────────────────────

def _draw_text_outlined(font, text: str, pos: rl.Vector2, font_size: int, fill: rl.Color, outline: rl.Color):
  """Draw text with a black outline stroke for legibility on colored fills."""
  for dx in (-2, -1, 1, 2):
    for dy in (-2, -1, 1, 2):
      rl.draw_text_ex(font, text, rl.Vector2(pos.x + dx, pos.y + dy), font_size, 0, outline)
  rl.draw_text_ex(font, text, pos, font_size, 0, fill)


_BUBBLE_PAD_X = 24
_BUBBLE_ROW_H = 48
_BUBBLE_GAP = 2
_BUBBLE_FONT = 34
_BUBBLE_BG = rl.Color(0, 0, 0, 200)
_BUBBLE_BORDER = rl.Color(255, 255, 255, 80)
_BUBBLE_ACCENT = rl.Color(201, 34, 49, 255)

def _draw_sources_bubble(state: dict, anchor_rect: rl.Rectangle, sign_rect: rl.Rectangle):
  """Draw the expanded sources bubble to the right of the anchor pill."""
  font_bold = _get_bold()
  font_semi = _get_semi_bold()
  active_source = state['speed_limit_source']

  rows = []
  for title, abbrev, value_key in SOURCE_DEFS:
    value = state[value_key]
    if value == 0:
      continue
    rows.append((title, abbrev, value, active_source == title and value != 0))

  if not rows:
    return

  bubble_w = sign_rect.width + 24
  bubble_h = sign_rect.height + 40

  bubble_x = sign_rect.x + sign_rect.width + 12
  bubble_y = sign_rect.y

  bg_rect = rl.Rectangle(bubble_x, bubble_y, bubble_w, bubble_h)
  rl.draw_rectangle_rounded(bg_rect, 0.25, 8, _BUBBLE_BG)
  rl.draw_rectangle_rounded_lines_ex(bg_rect, 0.25, 8, 1, _BUBBLE_BORDER)

  arrow_y = int(anchor_rect.y + anchor_rect.height / 2)
  rl.draw_triangle(
    rl.Vector2(bubble_x, arrow_y - 6),
    rl.Vector2(bubble_x, arrow_y + 6),
    rl.Vector2(bubble_x - 6, arrow_y),
    _BUBBLE_BG,
  )

  row_h = min(44.0, (bubble_h - 8 - (len(rows) - 1) * _BUBBLE_GAP) / len(rows))
  total_content_h = len(rows) * row_h + (len(rows) - 1) * _BUBBLE_GAP
  y = bubble_y + (bubble_h - total_content_h) / 2

  for title, abbrev, value, is_active in rows:
    if is_active:
      rl.draw_rectangle(int(bubble_x), int(y), 4, int(row_h), _BUBBLE_ACCENT)

    text_font = font_bold if is_active else font_semi
    abbrev_text = abbrev
    value_text = str(int(round(value)))

    abbrev_size = measure_text_cached(text_font, abbrev_text, _BUBBLE_FONT)
    value_size = measure_text_cached(text_font, value_text, _BUBBLE_FONT)

    font_size = _BUBBLE_FONT
    available_w = bubble_w - 16
    needed_w = abbrev_size.x + value_size.x + 8
    if needed_w > available_w:
      font_size = max(26, int(_BUBBLE_FONT * (available_w / needed_w)))
      abbrev_size = measure_text_cached(text_font, abbrev_text, font_size)
      value_size = measure_text_cached(text_font, value_text, font_size)

    abbrev_pos = rl.Vector2(bubble_x + 8, y + (row_h - font_size) / 2)
    value_pos = rl.Vector2(bubble_x + bubble_w - 8 - value_size.x, y + (row_h - font_size) / 2)

    text_color = rl.WHITE if is_active else rl.Color(255, 255, 255, 180)

    if is_active:
      _draw_text_outlined(text_font, abbrev_text, abbrev_pos, font_size, text_color, rl.Color(0, 0, 0, 255))
      _draw_text_outlined(text_font, value_text, value_pos, font_size, text_color, rl.Color(0, 0, 0, 255))
    else:
      rl.draw_text_ex(text_font, abbrev_text, abbrev_pos, font_size, 0, text_color)
      rl.draw_text_ex(text_font, value_text, value_pos, font_size, 0, text_color)

    y += row_h + _BUBBLE_GAP


# ── Public API ────────────────────────────────────────────────────────

def render_speed_limit_at(state: dict, rect: rl.Rectangle, expanded: bool = False) -> Optional[rl.Rectangle]:
  """Render SLC speed limit signs at a specific rect calculated by the layout manager.
  Returns the pill rect for hit-testing, or None if no pill was drawn."""
  flashing_pending = state['speed_limit_changed'] and state['unconfirmed_valid']

  if flashing_pending:
    _draw_sign(state, rect, pending=True)
    return None

  if state['hide']:
    return None

  _draw_sign(state, rect, pending=False)

  use_vienna = state['use_vienna']
  cx_center = rect.x + rect.width / 2
  sign_h = EU_SIGN_SIZE if use_vienna else US_SIGN_HEIGHT
  bottom_y = rect.y + sign_h
  
  visual_w = EU_SIGN_SIZE if use_vienna else rect.width - 2 * US_INSET
  visual_x = rect.x if use_vienna else rect.x + US_INSET
  visual_rect = rl.Rectangle(visual_x, rect.y, visual_w, sign_h)

  pill_rect = _draw_active_source_label(state, cx_center, bottom_y, visual_w, expanded)

  if expanded and pill_rect:
    _draw_sources_bubble(state, pill_rect, visual_rect)

  return pill_rect
