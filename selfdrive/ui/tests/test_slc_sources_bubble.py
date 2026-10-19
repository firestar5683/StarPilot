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
    source_defs, dict.fromkeys(values, 0.0), "Map Data", ("Map Data",),
  ) == []


def test_header_reuses_diagnostic_source_icons_without_unknown_fallback():
  from openpilot.selfdrive.ui.onroad.starpilot.slc_speed_limit import source_icon_key

  assert source_icon_key("Vision") == "camera"
  assert source_icon_key("Dashboard") == "dashboard"
  assert source_icon_key("Map Data") == "map"
  assert source_icon_key("Mapbox") == "map"
  assert source_icon_key("None") is None
  assert source_icon_key("Unexpected") is None


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
