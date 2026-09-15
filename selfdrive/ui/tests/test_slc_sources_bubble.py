from openpilot.selfdrive.ui.onroad.starpilot.source_bubble_layout import (
  enabled_source_titles,
  fit_source_label,
  source_abbreviated_value_text,
  source_content_metrics,
  source_value_text,
  visible_source_rows,
)


def test_source_content_metrics_scale_with_visible_row_count():
  assert source_content_metrics(3) == (30, 34, 7)
  assert source_content_metrics(4) == (30, 32, 7)
  assert source_content_metrics(5) == (28, 30, 6)


def test_fit_source_label_preserves_a_safe_value_column_gap():
  def width(text: str) -> int:
    return len(text) * 10

  assert fit_source_label("Dashboard", "Dash", 80, width) == "Dash"
  assert fit_source_label("Vision", "Vision", 70, width) == "Vision"
  assert fit_source_label("Dashboard", "Dash", 20, width) == "D…"


def test_source_value_text_keeps_missing_values_as_a_dash():
  assert source_value_text(0) == "–"
  assert source_value_text(0.1) == "–"
  assert source_value_text(55) == "55"
  assert source_value_text(float("nan")) == "–"
  assert source_value_text(float("inf")) == "–"
  assert source_abbreviated_value_text(0) == "X"
  assert source_abbreviated_value_text(55) == "55"


def test_enabled_source_titles_follow_priority_and_fallback_settings():
  assert enabled_source_titles(
    "Map Data", "Vision", vision_enabled=True, mapbox_enabled=False,
  ) == ("Map Data", "Vision", "Upcoming")
  assert enabled_source_titles(
    "Dashboard", "None", vision_enabled=False, mapbox_enabled=True,
  ) == ("Dashboard", "Mapbox")
  assert enabled_source_titles(
    "Highest", "None", vision_enabled=True, mapbox_enabled=True,
  ) == ("Dashboard", "Map Data", "Mapbox", "Upcoming")
  assert enabled_source_titles(
    "Dashboard", "Map Data", vision_enabled=False, mapbox_enabled=False,
    dashboard_available=False,
  ) == ("Map Data", "Upcoming")


def test_visible_source_rows_honor_active_only_and_source_order():
  source_defs = [
    ("Dashboard", "Dash", "dashboard", "Dashboard", "dashboard"),
    ("Map Data", "MapD", "map", "Map Data", "map"),
    ("Vision", "Vision", "vision", "Vision", "camera"),
    ("Mapbox", "MapB", "mapbox", "Mapbox", "map"),
    ("Upcoming", "Next", "next", "Next", "next"),
  ]
  values = {"dashboard": 45.0, "map": 0.0, "vision": 50.0, "mapbox": 30.0, "next": 20.0}

  # Map Data has value 0.0, so it is omitted; Dashboard (45.0) is active
  assert visible_source_rows(
    source_defs, values, "Dashboard", ("Dashboard", "Map Data"),
  ) == [
    ("Dashboard", "dashboard", 45.0, True),
  ]
  # When Map Data is the active target but has 0.0 reading, Dashboard is inactive (available standby)
  assert visible_source_rows(
    source_defs, values, "Map Data", ("Dashboard", "Map Data"),
  ) == [
    ("Dashboard", "dashboard", 45.0, False),
  ]
  # Multiple available sources with readings appear in canonical order
  assert visible_source_rows(
    source_defs, values, "Vision", ("Dashboard", "Map Data", "Vision"),
  ) == [
    ("Dashboard", "dashboard", 45.0, False),
    ("Vision", "camera", 50.0, True),
  ]
  # When no sources have a valid speed reading (> 0), returns empty list (triggers empty state)
  assert visible_source_rows(
    source_defs, {key: 0.0 for key in values}, "Map Data", ("Map Data",),
  ) == []


def test_source_label_color_override_and_engagement_states():
  from openpilot.selfdrive.ui.onroad.starpilot.slc_speed_limit import _source_label_color
  from openpilot.selfdrive.ui.onroad.hud_renderer import COLORS
  from openpilot.selfdrive.ui.ui_state import ui_state, UIStatus

  # Engaged and not overridden -> Active green
  ui_state.status = UIStatus.ENGAGED
  color = _source_label_color(255, is_overridden=False)
  assert (color.r, color.g, color.b, color.a) == (COLORS.ENGAGED.r, COLORS.ENGAGED.g, COLORS.ENGAGED.b, 255)

  # Engaged but overridden -> Disengaged/override gray
  color_overridden = _source_label_color(255, is_overridden=True)
  assert (color_overridden.r, color_overridden.g, color_overridden.b, color_overridden.a) == (
    COLORS.DISENGAGED.r, COLORS.DISENGAGED.g, COLORS.DISENGAGED.b, 255
  )

  # Disengaged -> Disengaged/override gray
  ui_state.status = UIStatus.DISENGAGED
  color_disengaged = _source_label_color(255, is_overridden=False)
  assert (color_disengaged.r, color_disengaged.g, color_disengaged.b, color_disengaged.a) == (
    COLORS.DISENGAGED.r, COLORS.DISENGAGED.g, COLORS.DISENGAGED.b, 255
  )

  # Override UI status -> Disengaged/override gray
  ui_state.status = UIStatus.OVERRIDE
  color_ui_override = _source_label_color(255, is_overridden=False)
  assert (color_ui_override.r, color_ui_override.g, color_ui_override.b, color_ui_override.a) == (
    COLORS.OVERRIDE.r, COLORS.OVERRIDE.g, COLORS.OVERRIDE.b, 255
  )


def test_vision_pulse_ignores_same_limit_source_flapping(monkeypatch):
  from openpilot.selfdrive.ui.onroad.starpilot import slc_speed_limit as slc

  def rgba(color):
    return color.r, color.g, color.b, color.a

  now = [0.0]
  monkeypatch.setattr(slc.rl, "get_time", lambda: now[0])
  base = slc.rl.Color(255, 255, 255, 255)

  slc._reset_pulse()
  slc._tick_pulse("Vision", 15.6464)
  now[0] = 0.5
  assert rgba(slc._speed_limit_pulse_color(base, 255)) == (188, 132, 255, 255)

  slc._tick_pulse("Map Data", 15.6464)
  assert rgba(slc._speed_limit_pulse_color(base, 255)) == (255, 255, 255, 255)

  now[0] = 0.6
  slc._tick_pulse("Vision", 15.6464)
  assert rgba(slc._speed_limit_pulse_color(base, 255)) == (255, 255, 255, 255)

  now[0] = 0.7
  slc._tick_pulse("Vision", 13.4112)
  now[0] = 1.2
  assert rgba(slc._speed_limit_pulse_color(base, 255)) == (188, 132, 255, 255)
