from types import SimpleNamespace
from dataclasses import replace

import pyray as rl
import pytest

from cereal import custom
from openpilot.common.constants import CV
from openpilot.selfdrive.ui.onroad.starpilot import slc_speed_limit
from openpilot.selfdrive.ui.onroad.starpilot.unified_speed_presentation import UnifiedSpeedPresentation, resolve_unified_speed
from openpilot.selfdrive.ui.onroad.starpilot.widgets import unified_speed


@pytest.fixture(autouse=True)
def no_gpu_batch(monkeypatch):
  monkeypatch.setattr(rl, "rl_draw_render_batch_active", lambda: None)


def make_widget(mode="split", pending=False):
  widget = object.__new__(unified_speed.UnifiedSpeedWidget)
  height = unified_speed.UNIFIED_HEIGHT if mode in ("split", "merged") else unified_speed.SINGLE_HEIGHT
  widget._rect = rl.Rectangle(30, 75, unified_speed.UNIFIED_WIDTH, height)
  widget._presentation = UnifiedSpeedPresentation(mode, "70", "65", "70", "+5", "mph", "Map Data", pending, "slc")
  widget._show_max = True
  widget._slc_state = None
  widget._pedal_override = False
  widget._font_semi_bold = widget._font_bold = None
  widget._semi_bold_digit_center = widget._bold_digit_center = 0.5
  widget._bold_digit_bottom = 0.8
  widget._unit_tops = {"mph": 0.0, "km/h": 0.0}
  widget._source_drawer = unified_speed.SpeedSourceDrawer()
  widget.hud_renderer = SimpleNamespace(is_cruise_set=True)
  return widget


@pytest.fixture
def header_icon_cache(monkeypatch):
  app = object.__new__(type(unified_speed.gui_app))
  app._scale = app._pixel_scale_x = app._pixel_scale_y = 1.0
  app._cached_render_textures = {}
  app._pending_render_textures = {}
  geometry, draws, allocations, scales = [], [], [], []
  monkeypatch.setattr(unified_speed, "gui_app", app)
  monkeypatch.setattr(unified_speed, "_draw_source_icon", lambda *args: geometry.append(args))
  monkeypatch.setattr(unified_speed, "measure_text_cached", lambda *args: rl.Vector2(100, 28))
  monkeypatch.setattr(rl, "draw_text_ex", lambda *args: None)
  monkeypatch.setattr(rl, "draw_texture_pro", lambda *args: draws.append(args))
  monkeypatch.setattr(rl, "rl_scalef", lambda *args: scales.append(args))
  for name in ("rl_push_matrix", "rl_pop_matrix", "begin_texture_mode", "end_texture_mode", "clear_background",
               "rl_set_blend_factors_separate", "begin_blend_mode", "end_blend_mode", "set_texture_filter", "set_texture_wrap"):
    monkeypatch.setattr(rl, name, lambda *args: None)

  def allocate(width, height):
    allocations.append((width, height))
    return SimpleNamespace(texture=SimpleNamespace(width=width, height=height))

  monkeypatch.setattr(rl, "load_render_texture", allocate)
  return app, geometry, draws, allocations, scales


def test_header_glyph_cache_is_shared_and_skips_geometry_after_first_frame(header_icon_cache):
  app, geometry, draws, allocations, _scales = header_icon_cache
  widgets = [make_widget(), make_widget()]
  for widget in widgets:
    widget._font_semi_bold = None
  widget = widgets[0]
  for label, icon in (("MAX SET", "speedometer"), ("SPEED LIMIT", "map")):
    widget._draw_header(widget.rect, label, icon, rl.WHITE)
  assert len(geometry) == 2
  assert allocations == []
  app._populate_render_texture_cache()
  assert len(geometry) == 4

  for frame in range(60):
    widget = widgets[frame % 2]
    bounds = rl.Rectangle(frame, frame, 260, 250)
    widget._draw_header(bounds, "MAX SET", "speedometer", rl.WHITE)
    widget._draw_header(bounds, f"LIMIT {frame}", "map", rl.GRAY)
  assert len(geometry) == 4
  assert len(draws) == 120
  assert len(allocations) == len(app._cached_render_textures) == 2
  assert app._pending_render_textures == {}


@pytest.mark.parametrize("scale,dpi,texture_size", [(0.5, 1.0, 68), (1.0, 2.0, 136), (1.25, 1.5, 128)])
def test_header_cache_resolution_preserves_logical_geometry(header_icon_cache, scale, dpi, texture_size):
  app, geometry, draws, allocations, scales = header_icon_cache
  app._scale, app._pixel_scale_x = scale, dpi
  for icon in ("speedometer", "map", "camera", "dashboard", "next"):
    unified_speed._draw_header_icon(icon, 10, 20)
  app._populate_render_texture_cache()
  assert len(app._cached_render_textures) == 5
  assert allocations == [(texture_size, texture_size)] * 5
  assert all(args[1:4] == (0, 0, 34) for args in geometry[5:])
  assert scales == [(texture_size / 34, texture_size / 34, 1.0)] * 5

  unified_speed._draw_header_icon("map", 200, 300)
  assert len(geometry) == 10
  source, destination = draws[-1][1:3]
  assert (source.width, source.height) == (texture_size, -texture_size)
  assert (destination.x, destination.y, destination.width, destination.height) == (200, 300, 34, 34)


def test_speed_limit_hit_target_is_lower_row_in_both_layouts():
  for mode in ("split", "merged"):
    limit = make_widget(mode)._speed_limit_bounds(rl.Rectangle(30, 75, 232, 448))
    assert (limit.x, limit.y, limit.width, limit.height) == (30, 283, 232, 240)


def test_confirmation_touch_only_accepts_on_speed_limit_side(monkeypatch):
  widget = make_widget(pending=True)
  writes = []
  monkeypatch.setattr(unified_speed, "Params", lambda memory: SimpleNamespace(put_bool=lambda key, value: writes.append((key, value))))
  widget._handle_mouse_press(rl.Vector2(100, 150))
  assert writes == []
  widget._handle_mouse_press(rl.Vector2(100, 282))
  assert writes == []
  widget._handle_mouse_press(rl.Vector2(100, 283))
  assert writes == [("SpeedLimitAccepted", True)]


def test_merged_speed_limit_side_toggles_sources(monkeypatch):
  widget = make_widget("merged")
  writes = []
  params = SimpleNamespace(get_bool=lambda _key: False, put_bool=lambda key, value: writes.append((key, value)))
  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(ui_params=params))
  widget._handle_mouse_press(rl.Vector2(100, 150))
  assert writes == []
  widget._handle_mouse_press(rl.Vector2(100, 282))
  assert writes == []
  widget._handle_mouse_press(rl.Vector2(100, 400))
  assert writes == [("SpeedLimitSources", True)]


def test_diagnostic_sources_can_be_dismissed_from_max_only_card(monkeypatch):
  widget = make_widget("max_only")
  widget._slc_state = {}
  params = SimpleNamespace(get_bool=lambda _key: True, put_bool=lambda key, value: writes.append((key, value)))
  writes = []
  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(ui_params=params))
  widget._handle_mouse_press(rl.Vector2(100, 150))
  assert writes == [("SpeedLimitSources", False)]


def test_lower_border_overlay_is_clipped_to_speed_limit_row(monkeypatch):
  events = []
  monkeypatch.setattr(unified_speed.rl, "begin_scissor_mode", lambda *args: events.append(("begin", args)))
  monkeypatch.setattr(unified_speed.rl, "draw_rectangle_rounded_lines_ex", lambda *args: events.append(("outline", args)))
  monkeypatch.setattr(unified_speed.rl, "draw_line_ex", lambda *args: events.append(("divider", args)))
  monkeypatch.setattr(unified_speed.rl, "end_scissor_mode", lambda: events.append(("end",)))
  for mode, expected in (("split", ["begin", "outline", "end", "divider"]),
                         ("merged", ["begin", "outline", "end"])):
    events.clear()
    widget = make_widget(mode)
    rect = widget.rect
    limit = widget._speed_limit_bounds(rect)
    widget._draw_speed_limit_border(rect, limit, rl.Color(188, 132, 255, 200))
    assert events[0] == ("begin", (30, 283, 233, 241))
    assert [event[0] for event in events] == expected
    if mode == "split":
      start, end = events[-1][1][:2]
      assert (start.x, start.y, end.x, end.y) == (38, 283, 254, 283)


def test_split_and_merged_draw_one_card_with_both_headers(monkeypatch):
  cards = []
  lines = []
  monkeypatch.setattr(unified_speed, "draw_control_card", lambda *args, **kwargs: cards.append(args[0]))
  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(status=unified_speed.UIStatus.DISENGAGED,
                                                                 ui_params=SimpleNamespace(get_bool=lambda _key: False)))
  monkeypatch.setattr(unified_speed.rl, "draw_line_ex", lambda *args: lines.append(args))
  monkeypatch.setattr(unified_speed.rl, "draw_rectangle_rounded_lines_ex", lambda *args: None)
  for mode in ("split", "merged"):
    lines.clear()
    widget = make_widget(mode)
    headers = []
    values = []
    separators = []
    offsets = []
    monkeypatch.setattr(widget, "_draw_header", lambda bounds, text, icon, _color, rows=headers: rows.append((bounds, text, icon)))
    monkeypatch.setattr(widget, "_draw_centered_text", lambda text, *args, rows=values, **kwargs: rows.append(text))
    def posted_limit(bounds, y, _value_color, _offset_color, *, compact=False,
                     widget=widget, values=values, offsets=offsets):
      if not compact:
        values.append(widget._presentation.posted_speed_text)
      offsets.append((bounds, widget._presentation.offset_text, y))
      return unified_speed.OFFSET_FONT_SIZE if compact else unified_speed.VALUE_FONT_SIZE

    monkeypatch.setattr(widget, "_draw_posted_limit", posted_limit)
    monkeypatch.setattr(widget, "_draw_merged_separator", lambda _rect, rows=separators: rows.append(True))
    monkeypatch.setattr(widget, "_draw_active_emphasis", lambda *args: None)
    widget._render(widget.rect)
    assert [(text, icon) for _bounds, text, icon in headers] == [("MAX SET", "speedometer"), ("SPEED LIMIT", "map")]
    assert headers[0][0].y == 75
    assert headers[1][0].y == (413 if mode == "merged" else 283)
    assert all(bounds.x == 30 and bounds.width == 232 for bounds, _text, _icon in headers)
    assert separators == ([True] if mode == "merged" else [])
    assert sum(line[0].y == line[1].y == 283 for line in lines) == (1 if mode == "split" else 0)
    assert values == (["70", "mph"] if mode == "merged" else ["70", "mph", "65", "mph"])
    assert offsets[0][0].x == 30
    assert offsets[0][2] == pytest.approx(523 - 22 * unified_speed.FONT_SCALE - 16 if mode == "merged" else 349)
  assert len(cards) == 2


def test_merged_draws_effective_speed_once_and_skips_active_line(monkeypatch):
  widget = make_widget("merged")
  widget._presentation = replace(widget._presentation, max_speed_text="71", effective_speed_text="70", active_side="shared")
  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(status=unified_speed.UIStatus.ENGAGED,
                                                                 ui_params=SimpleNamespace(get_bool=lambda _key: False)))
  monkeypatch.setattr(unified_speed, "draw_control_card", lambda *args, **kwargs: None)
  monkeypatch.setattr(unified_speed.rl, "draw_rectangle_rounded_lines_ex", lambda *args: None)
  lines = []
  monkeypatch.setattr(unified_speed.rl, "draw_line_ex", lambda *args: lines.append(args))
  monkeypatch.setattr(widget, "_draw_merged_separator", lambda _rect: None)
  monkeypatch.setattr(widget, "_draw_header", lambda *args: None)
  monkeypatch.setattr(widget, "_draw_posted_limit", lambda *args, **kwargs: None)
  values = []
  monkeypatch.setattr(widget, "_draw_centered_text", lambda text, bounds, y, size, *args, **kwargs: values.append((text, bounds, y, size)))
  widget._render(widget.rect)
  assert [value[0] for value in values] == ["70", "mph"]
  speed, unit = values
  assert speed[1].x > widget.rect.x + 30  # The inward curve has its own gutter.
  assert speed[1].x + speed[1].width == widget.rect.x + widget.rect.width
  assert (speed[2] + unit[2] + unit[3] * unified_speed.FONT_SCALE) / 2 == pytest.approx(widget.rect.y + widget.rect.height / 2)
  assert unit[2] > speed[2] + speed[3] * unified_speed.FONT_SCALE
  assert lines == []


def test_merged_separator_is_vertical_with_a_shallow_inward_curve(monkeypatch):
  widget = make_widget("merged")
  segments = []
  monkeypatch.setattr(unified_speed.rl, "draw_line_ex", lambda *args: segments.append(("line", args)))
  monkeypatch.setattr(unified_speed.rl, "draw_spline_segment_bezier_cubic", lambda *args: segments.append(("curve", args)))
  widget._draw_merged_separator(widget.rect)
  assert [segment[0] for segment in segments] == ["line", "curve", "line", "curve", "line"]
  start, end = segments[0][1][:2]
  assert start.x == end.x == widget.rect.x + 18
  assert start.y == widget.rect.y + 76
  center_start, center_end = segments[2][1][:2]
  assert center_start.x == center_end.x == widget.rect.x + 30
  assert (center_start.y + center_end.y) / 2 == widget.rect.y + widget.rect.height / 2
  assert segments[-1][1][1].y < widget.rect.y + widget.rect.height - 90  # Clear the lower header's icon.


def test_enabled_slc_keeps_both_rows_when_plan_is_stale(monkeypatch):
  widget = make_widget("split")
  widget._snapshot_frame = None
  widget.hud_renderer = SimpleNamespace(is_cruise_available=True, is_cruise_set=True, set_speed=70)
  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(
    sm=SimpleNamespace(frame=1), starpilot_toggles={}, is_metric=False, engaged=False,
  ))
  monkeypatch.setattr(unified_speed, "_is_slc_enabled", lambda: True)
  monkeypatch.setattr(unified_speed, "_get_slc_state", lambda: None)
  assert widget.get_size() == (232.0, 448.0)
  assert widget.is_visible
  assert widget._presentation.posted_speed_text == "–"


@pytest.fixture
def pedal_snapshot(monkeypatch):
  class SubMaster(dict):
    pass

  sm = SubMaster(carState=SimpleNamespace(gasPressed=True))
  sm.frame = 20
  sm.valid = {"carState": True}
  sm.alive = {"carState": True}
  sm.recv_frame = {"carState": 20}
  ui = SimpleNamespace(sm=sm, started_frame=10, engaged=True, starpilot_toggles={}, is_metric=False)
  widget = make_widget()
  widget._snapshot_frame = None
  widget.hud_renderer = SimpleNamespace(is_cruise_available=True, is_cruise_set=True, set_speed=70)
  monkeypatch.setattr(unified_speed, "ui_state", ui)
  monkeypatch.setattr(unified_speed, "_is_slc_enabled", lambda: True)
  monkeypatch.setattr(unified_speed, "_get_slc_state", lambda: None)
  return widget, ui


@pytest.mark.parametrize("gas,engaged,cruise_set,valid,alive,received,expected", [
  (True, True, True, True, True, 20, True),
  (False, True, True, True, True, 20, False),
  (True, False, True, True, True, 20, False),
  (True, True, False, True, True, 20, False),
  (True, True, True, False, True, 20, False),
  (True, True, True, True, False, 20, False),
  (True, True, True, True, True, 9, False),
])
def test_pedal_override_requires_fresh_gas_and_engaged_cruise(pedal_snapshot, gas, engaged, cruise_set, valid, alive, received, expected):
  widget, ui = pedal_snapshot
  ui.sm["carState"].gasPressed = gas
  ui.engaged = engaged
  widget.hud_renderer.is_cruise_set = cruise_set
  ui.sm.valid["carState"] = valid
  ui.sm.alive["carState"] = alive
  ui.sm.recv_frame["carState"] = received
  widget._refresh_snapshot()
  assert widget._pedal_override == expected


def test_pedal_cue_clears_on_release_with_a_persistent_slc_override(pedal_snapshot, monkeypatch):
  widget, ui = pedal_snapshot
  sm = ui.sm
  state = {
    "speed_conversion": CV.MS_TO_MPH, "accepted_speed_limit_ms": 65 * CV.MPH_TO_MS,
    "effective_target_ms": 70 * CV.MPH_TO_MS, "offset_ms": 5 * CV.MPH_TO_MS,
    "speed_limit_changed": False, "unconfirmed_valid": False, "presented_source": "Map Data",
    "slc_is_limiting_max_set": False, "slc_overridden_speed": 80 * CV.MPH_TO_MS,
  }
  monkeypatch.setattr(unified_speed, "_get_slc_state", lambda: state)
  widget._refresh_snapshot()
  assert widget._pedal_override
  presentation = widget._presentation

  sm["carState"].gasPressed = False
  widget._refresh_snapshot()
  assert widget._pedal_override
  sm.frame += 1
  sm.recv_frame["carState"] = sm.frame
  widget._refresh_snapshot()
  assert not widget._pedal_override
  assert widget._presentation == presentation
  assert widget._slc_state["slc_overridden_speed"] > 0


@pytest.mark.parametrize("mode", ["split", "merged", "max_only", "limit_only"])
@pytest.mark.parametrize("unit", ["mph", "km/h"])
def test_pedal_cue_mutes_targets_and_preserves_units_offsets_and_layout(monkeypatch, mode, unit):
  widget = make_widget(mode)
  widget._pedal_override = True
  widget._font_semi_bold = None
  widget._show_max = mode != "limit_only"
  widget._presentation = replace(widget._presentation, unit_text=unit)
  values, headers, pauses, lines = [], [], [], []
  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(status=unified_speed.UIStatus.ENGAGED))
  monkeypatch.setattr(unified_speed, "draw_control_card", lambda *args, **kwargs: None)
  monkeypatch.setattr(unified_speed, "measure_text_cached", lambda *args: rl.Vector2(60, 28))
  monkeypatch.setattr(rl, "draw_rectangle_rounded_lines_ex", lambda *args: None)
  monkeypatch.setattr(rl, "draw_rectangle_rec", lambda *args: pauses.append(args))
  monkeypatch.setattr(rl, "draw_line_ex", lambda *args: lines.append(args))
  monkeypatch.setattr(widget, "_draw_merged_separator", lambda *args: None)
  monkeypatch.setattr(widget, "_draw_header", lambda bounds, text, icon, color: headers.append(color))
  monkeypatch.setattr(widget, "_draw_centered_text", lambda text, bounds, y, size, color, **kwargs: values.append((text, bounds, size, color)))

  widget._render(widget.rect)
  speed_values = [value for value in values if value[2] == unified_speed.VALUE_FONT_SIZE]
  unit_values = [value for value in values if value[0] == unit and value[2] == unified_speed.UNIT_FONT_SIZE]
  expected_speeds = {"split": ["70", "65"], "merged": ["70"], "max_only": ["70"], "limit_only": ["65"]}
  assert [value[0] for value in speed_values] == expected_speeds[mode]
  assert all(value[3] == unified_speed.COLORS.DISENGAGED for value in speed_values + unit_values)
  assert all(color == unified_speed.COLORS.DISENGAGED for color in headers)
  assert [value[0] for value in unit_values] == [unit] * (2 if mode == "split" else 1)
  assert len(pauses) == 2 * len(unit_values)
  assert all(color == unified_speed.PAUSE_COLOR for _bounds, color in pauses)
  offsets = [value for value in values if value[0] == "+5"]
  assert [value[0] for value in offsets] == ([] if mode == "max_only" else ["+5"])
  assert all(value[3] == unified_speed.COLORS.DISENGAGED for value in offsets)
  assert not any(line[2] == 3 for line in lines)
  for index, value in enumerate(unit_values):
    pause = pauses[index * 2][0]
    assert pause.x == pytest.approx(value[1].x + (value[1].width - 60) / 2 - 20)

  values.clear()
  pauses.clear()
  widget._pedal_override = False
  widget._render(widget.rect)
  assert not pauses
  assert all(value[3] == unified_speed.COLORS.WHITE for value in values if value[2] == unified_speed.VALUE_FONT_SIZE)
  assert all(value[3] == unified_speed.COLORS.WHITE_TRANSLUCENT for value in values if value[2] == unified_speed.UNIT_FONT_SIZE)
  assert all(value[3] == unified_speed.COLORS.WHITE_TRANSLUCENT for value in values if value[0] == "+5")


def test_split_merged_transitions_keep_the_same_footprint(monkeypatch):
  widget = make_widget("split")
  monkeypatch.setattr(widget, "_refresh_snapshot", lambda: None)
  sizes = []
  for mode in ("split", "merged", "split", "merged"):
    widget._presentation = replace(widget._presentation, mode=mode)
    sizes.append(widget.get_size())
  assert sizes == [(232.0, 448.0)] * 4


@pytest.mark.parametrize("mode", ["max_only", "limit_only"])
def test_single_target_keeps_a_compact_card(monkeypatch, mode):
  widget = make_widget(mode)
  monkeypatch.setattr(widget, "_refresh_snapshot", lambda: None)
  assert widget.get_size() == (232.0, 250.0)
  limit = widget._speed_limit_bounds(widget.rect)
  if mode == "limit_only":
    assert limit is widget.rect
  else:
    assert limit is None


@pytest.mark.parametrize("mode", ["split", "merged", "limit_only", "max_only"])
def test_sources_panel_is_attached_to_slc_row(monkeypatch, mode):
  widget = make_widget(mode)
  widget._show_max = mode != "limit_only"
  widget._slc_state = {"slc_overridden_speed": 0}
  widget._source_drawer.update(True, 0)
  widget._source_drawer.update(True, 1)
  monkeypatch.setattr(rl, "get_time", lambda: 1)
  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(
    status=unified_speed.UIStatus.DISENGAGED, ui_params=SimpleNamespace(get_bool=lambda _key: True),
  ))
  monkeypatch.setattr(unified_speed, "draw_control_card", lambda *args, **kwargs: None)
  monkeypatch.setattr(unified_speed, "_speed_limit_pulse_color", lambda color, _alpha: color)
  for name in ("draw_rectangle_rounded_lines_ex", "draw_line_ex", "draw_spline_segment_bezier_cubic"):
    monkeypatch.setattr(rl, name, lambda *args: None)
  for name in ("_draw_header", "_draw_centered_text", "_draw_posted_limit", "_draw_unit", "_unit_y"):
    monkeypatch.setattr(widget, name, lambda *args, **kwargs: None)
  panels = []
  monkeypatch.setattr(widget._source_drawer, "draw_frame", lambda *args: None)
  monkeypatch.setattr(widget._source_drawer, "draw_contents", lambda _state, rect, top: panels.append(widget._source_drawer.bounds(rect, top)))
  widget._render(widget.rect)
  assert len(panels) == 1
  panel = panels[0]
  assert (panel.x, panel.width) == (widget.rect.x + widget.rect.width, 248)
  assert (panel.y, panel.height) == ((283, 240) if mode in ("split", "merged") else (75, 250))


def test_drawer_taps_toggle_sources_and_empty_upper_area_does_not(monkeypatch):
  widget = make_widget("merged")
  widget._source_drawer.update(True, 0)
  widget._source_drawer.update(True, 1)
  writes = []
  params = SimpleNamespace(get_bool=lambda _key: True, put_bool=lambda key, value: writes.append((key, value)))
  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(ui_params=params))
  assert widget.contains_pointer(rl.Vector2(400, 350))
  assert not widget.contains_pointer(rl.Vector2(400, 200))
  assert not widget.contains_pointer(rl.Vector2(511, 350))
  widget._handle_mouse_press(rl.Vector2(400, 200))
  assert writes == []
  widget._handle_mouse_press(rl.Vector2(400, 350))
  assert writes == [("SpeedLimitSources", False)]
  widget.collapse_sources()
  assert not widget.contains_pointer(rl.Vector2(400, 350))


@pytest.mark.parametrize("pending,stale", [(True, False), (False, True)])
def test_pending_confirmation_and_stale_state_hide_drawer_without_changing_preference(monkeypatch, pending, stale):
  widget = make_widget(pending=pending)
  widget._slc_state = None if stale else {"slc_overridden_speed": 0}
  widget._source_drawer.update(True, 0)
  widget._source_drawer.update(True, 1)
  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(status=unified_speed.UIStatus.DISENGAGED,
                                                                 ui_params=SimpleNamespace(get_bool=lambda _key: True)))
  monkeypatch.setattr(unified_speed, "draw_control_card", lambda *args, **kwargs: None)
  for name in ("draw_rectangle_rounded_lines_ex", "draw_line_ex", "draw_spline_segment_bezier_cubic", "begin_scissor_mode", "end_scissor_mode"):
    monkeypatch.setattr(rl, name, lambda *args: None)
  for name in ("_draw_header", "_draw_centered_text", "_draw_posted_limit", "_draw_unit", "_unit_y"):
    monkeypatch.setattr(widget, name, lambda *args, **kwargs: None)
  widget._render(widget.rect)
  assert widget._source_drawer.width == 0
  assert not widget.contains_pointer(rl.Vector2(400, 350))


@pytest.fixture
def slc_ui(monkeypatch):
  class Params(dict):
    def get_bool(self, key):
      return bool(self.get(key))

    def get(self, key, encoding=None):
      return super().get(key)

  class SubMaster(dict):
    recv_frame = {"starpilotPlan": 10}
    valid = {"starpilotCarState": True}

  plan = custom.StarPilotPlan.new_message(
    slcSpeedLimit=30 * CV.MPH_TO_MS, slcSpeedLimitOffset=0.0, slcSpeedLimitSource="Map Data",
    slcOverriddenSpeed=0.0, slcMapSpeedLimit=30 * CV.MPH_TO_MS, slcMapboxSpeedLimit=0.0,
    slcNextSpeedLimit=0.0, unconfirmedSlcSpeedLimit=0.0, speedLimitChanged=False,
  )
  sm = SubMaster(starpilotPlan=plan, starpilotCarState=SimpleNamespace(dashboardSpeedLimit=0.0))
  sm.recv_frame = sm.recv_frame.copy()
  params = Params(SpeedLimitController=True, ShowSpeedLimits=False)
  ui = SimpleNamespace(
    sm=sm, started_frame=10, is_metric=False, ui_params=params, starpilot_toggles={},
    params_memory=SimpleNamespace(get_float=lambda _key: 0.0),
  )
  monkeypatch.setattr(slc_speed_limit, "ui_state", ui)
  monkeypatch.setattr(slc_speed_limit, "starpilot_state", SimpleNamespace(car_state=SimpleNamespace(hasDashSpeedLimits=True)))
  monkeypatch.setattr(slc_speed_limit, "_tick_pulse", lambda *args: None)
  return ui


def test_slc_state_extraction_respects_feature_and_display_toggles(slc_ui):
  assert slc_speed_limit._is_slc_enabled()
  assert slc_speed_limit._get_slc_state()["slc_enabled"]
  slc_ui.starpilot_toggles["speed_limit_controller"] = False
  assert not slc_speed_limit._is_slc_enabled()
  assert slc_speed_limit._get_slc_state() is None
  slc_ui.ui_params["ShowSpeedLimits"] = True
  assert not slc_speed_limit._get_slc_state()["slc_enabled"]
  slc_ui.starpilot_toggles["speed_limit_controller"] = True
  slc_ui.sm.recv_frame["starpilotPlan"] = 9
  assert slc_speed_limit._get_slc_state() is None


@pytest.mark.parametrize("presented_source,expected_source,expected_speed", [
  ("", "Map Data", "30"),
  ("Map Data", "Map Data", "30"),
  ("None", "None", "–"),
  ("Previous Limit", "Previous Limit", "30"),
  ("Vision", "Vision", "30"),
])
def test_serialized_plan_source_defaults_and_explicit_values(slc_ui, presented_source, expected_source, expected_speed):
  message = slc_ui.sm["starpilotPlan"]
  if presented_source:
    message.slcPresentedSpeedLimitSource = presented_source
  # Replay decodes older plans with a present but empty Text attribute.
  with custom.StarPilotPlan.from_bytes(message.to_bytes()) as plan:
    slc_ui.sm["starpilotPlan"] = plan
    state = slc_speed_limit._get_slc_state()
    result = resolve_unified_speed(True, True, 35, state, True, False)
    assert result.source == expected_source
    assert result.posted_speed_text == expected_speed
    assert result.mode == "split"


def test_legacy_replay_limit_and_offset_merge_with_max_set(slc_ui):
  message = slc_ui.sm["starpilotPlan"]
  message.slcSpeedLimitOffset = 5 * CV.MPH_TO_MS
  with custom.StarPilotPlan.from_bytes(message.to_bytes()) as plan:
    slc_ui.sm["starpilotPlan"] = plan
    result = resolve_unified_speed(True, True, 35, slc_speed_limit._get_slc_state(), True, False)
    assert (result.source, result.posted_speed_text, result.effective_speed_text) == ("Map Data", "30", "35")
    assert (result.mode, result.offset_text) == ("merged", "+5")


@pytest.mark.parametrize("presented_source,limiting,max_speed,enabled,overridden,expected_side,line_y", [
  ("", False, 40, True, False, "slc", 348),
  ("", False, 34, True, False, "max", 140),
  ("", False, 35, True, False, "shared", None),
  ("", False, 40, False, False, "max", 140),
  ("", False, 40, True, True, "none", None),
  ("Map Data", False, 40, True, False, "max", 140),
  ("Map Data", True, 40, True, False, "slc", 348),
])
def test_active_underline_with_legacy_and_current_plans(slc_ui, monkeypatch, presented_source, limiting,
                                                       max_speed, enabled, overridden, expected_side, line_y):
  message = slc_ui.sm["starpilotPlan"]
  message.slcSpeedLimitOffset = 5 * CV.MPH_TO_MS
  message.slcPresentedSpeedLimitSource = presented_source
  message.slcIsLimitingMaxSet = limiting
  message.slcOverriddenSpeed = 40 * CV.MPH_TO_MS if overridden else 0.0
  slc_ui.starpilot_toggles["speed_limit_controller"] = enabled
  slc_ui.ui_params["ShowSpeedLimits"] = True
  with custom.StarPilotPlan.from_bytes(message.to_bytes()) as plan:
    slc_ui.sm["starpilotPlan"] = plan
    presentation = resolve_unified_speed(True, True, max_speed, slc_speed_limit._get_slc_state(), enabled, False)
  assert presentation.active_side == expected_side

  widget = make_widget(presentation.mode)
  widget._presentation = presentation
  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(status=unified_speed.UIStatus.ENGAGED))
  lines = []
  monkeypatch.setattr(unified_speed.rl, "draw_line_ex", lambda *args: lines.append(args))
  widget._draw_active_emphasis(widget.rect)
  if line_y is None:
    assert lines == []
  else:
    assert len(lines) == 1
    assert (lines[0][0].x, lines[0][0].y, lines[0][1].x, lines[0][1].y) == (48, line_y, 244, line_y)
    assert lines[0][3] == unified_speed.UNIFIED_ACCENT


def test_legacy_plan_without_active_source_does_not_use_diagnostic_map_limit(slc_ui):
  message = slc_ui.sm["starpilotPlan"]
  message.slcSpeedLimitSource = "None"
  with custom.StarPilotPlan.from_bytes(message.to_bytes()) as plan:
    slc_ui.sm["starpilotPlan"] = plan
    state = slc_speed_limit._get_slc_state()
    assert round(state["map_sl"]) == 30
    result = resolve_unified_speed(True, True, 35, state, True, False)
    assert (result.source, result.posted_speed_text, result.mode) == ("None", "–", "split")


def test_legacy_pending_candidate_remains_visible_without_active_source(slc_ui):
  message = slc_ui.sm["starpilotPlan"]
  message.slcSpeedLimitSource = "None"
  message.unconfirmedSlcSpeedLimit = 45 * CV.MPH_TO_MS
  message.speedLimitChanged = True
  with custom.StarPilotPlan.from_bytes(message.to_bytes()) as plan:
    slc_ui.sm["starpilotPlan"] = plan
    result = resolve_unified_speed(True, True, 35, slc_speed_limit._get_slc_state(), True, False)
    assert (result.posted_speed_text, result.mode, result.confirmation_pending) == ("45", "split", True)


def test_header_colors_preserve_engaged_disengaged_and_override_semantics(monkeypatch):
  widget = make_widget()
  colors = unified_speed.COLORS
  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(status=unified_speed.UIStatus.ENGAGED))
  assert widget._max_header_color("max", True) == colors.ENGAGED
  assert widget._max_header_color("slc", True) == colors.GREY
  assert widget._limit_header_color("slc", False) == colors.ENGAGED

  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(status=unified_speed.UIStatus.DISENGAGED))
  assert widget._max_header_color("max", True) == colors.DISENGAGED
  assert widget._limit_header_color("slc", False) == colors.DISENGAGED

  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(status=unified_speed.UIStatus.OVERRIDE))
  assert widget._max_header_color("max", True) == colors.DISENGAGED
  assert widget._limit_header_color("slc", False) == colors.DISENGAGED

  monkeypatch.setattr(unified_speed, "ui_state", SimpleNamespace(status=unified_speed.UIStatus.ENGAGED))
  assert widget._limit_header_color("none", True) == colors.DISENGAGED
