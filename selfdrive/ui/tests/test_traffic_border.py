from types import SimpleNamespace

from openpilot.selfdrive.ui.lib.starpilot_status import TRAFFIC_COLOR, CEM_OVERRIDE_COLOR
from openpilot.selfdrive.ui.onroad.starpilot import starpilot_border
from openpilot.selfdrive.ui.ui_state import ui_state

TRANSPARENT = (0, 0, 0, 0)


def _rgba(color):
  return color.r, color.g, color.b, color.a


def _car_state(left_blindspot=False, right_blindspot=False, left_blinker=False, right_blinker=False):
  return SimpleNamespace(
    leftBlindspot=left_blindspot,
    rightBlindspot=right_blindspot,
    leftBlinker=left_blinker,
    rightBlinker=right_blinker,
  )


def _setup(monkeypatch, *, car_state, signal=True, blindspot=True, v_asm_enabled=False, v_asm=(False, False), time=0.0):
  class FakeSM(dict):
    valid = {"carState": True}

  monkeypatch.setattr(ui_state, "sm", FakeSM(carState=car_state))
  monkeypatch.setattr(
    ui_state,
    "ui_params",
    SimpleNamespace(get_bool=lambda key: {"SignalMetrics": signal, "BlindSpotMetrics": blindspot}[key]),
  )
  monkeypatch.setattr(ui_state, "starpilot_toggles", {"v_asm_enabled": v_asm_enabled})
  monkeypatch.setattr(ui_state, "params_memory", object())
  monkeypatch.setattr(starpilot_border, "get_fresh_vasm_state", lambda _memory: v_asm)
  monkeypatch.setattr(starpilot_border.rl, "get_time", lambda: time)


def test_traffic_border_inactive_when_metrics_disabled(monkeypatch):
  _setup(monkeypatch, car_state=_car_state(left_blinker=True), signal=False, blindspot=False)

  assert starpilot_border.get_traffic_border_colors() is None


def test_traffic_border_inactive_when_nothing_active(monkeypatch):
  _setup(monkeypatch, car_state=_car_state())

  assert starpilot_border.get_traffic_border_colors() is None


def test_traffic_border_left_blindspot_is_red(monkeypatch):
  _setup(monkeypatch, car_state=_car_state(left_blindspot=True))

  left, right = starpilot_border.get_traffic_border_colors()

  assert _rgba(left) == _rgba(TRAFFIC_COLOR)
  assert _rgba(right) == TRANSPARENT


def test_traffic_border_right_blindspot_is_red(monkeypatch):
  _setup(monkeypatch, car_state=_car_state(right_blindspot=True))

  left, right = starpilot_border.get_traffic_border_colors()

  assert _rgba(left) == TRANSPARENT
  assert _rgba(right) == _rgba(TRAFFIC_COLOR)


def test_traffic_border_blinker_alone_flickers_amber(monkeypatch):
  _setup(monkeypatch, car_state=_car_state(left_blinker=True), blindspot=False, time=0.1)

  left, right = starpilot_border.get_traffic_border_colors()
  assert _rgba(left) == _rgba(CEM_OVERRIDE_COLOR)
  assert _rgba(right) == TRANSPARENT

  _setup(monkeypatch, car_state=_car_state(left_blinker=True), blindspot=False, time=0.6)
  left, right = starpilot_border.get_traffic_border_colors()
  assert _rgba(left) == TRANSPARENT
  assert _rgba(right) == TRANSPARENT


def test_traffic_border_blinker_with_blindspot_flickers_red_and_amber(monkeypatch):
  _setup(monkeypatch, car_state=_car_state(left_blinker=True, left_blindspot=True), time=0.1)

  left, _ = starpilot_border.get_traffic_border_colors()
  assert _rgba(left) == _rgba(TRAFFIC_COLOR)

  _setup(monkeypatch, car_state=_car_state(left_blinker=True, left_blindspot=True), time=0.3)
  left, _ = starpilot_border.get_traffic_border_colors()
  assert _rgba(left) == _rgba(CEM_OVERRIDE_COLOR)


def test_traffic_border_v_asm_blindspot_is_red(monkeypatch):
  _setup(monkeypatch, car_state=_car_state(), v_asm_enabled=True, v_asm=(True, False))

  left, right = starpilot_border.get_traffic_border_colors()
  assert _rgba(left) == _rgba(TRAFFIC_COLOR)
  assert _rgba(right) == TRANSPARENT


def test_c4_draw_border_paints_traffic_color_on_active_half(monkeypatch):
  import pyray as rl
  from openpilot.selfdrive.ui.mici.onroad import augmented_road_view as mici_view

  view = object.__new__(mici_view.AugmentedRoadView)
  view._content_rect = rl.Rectangle(10, 20, 200, 100)
  view._get_border_width = lambda: 8
  view._closed = True

  base_color = rl.Color(0, 0, 0, 255)
  calls = []
  monkeypatch.setattr(mici_view, "get_border_color", lambda _state: base_color)
  monkeypatch.setattr(mici_view, "get_traffic_border_colors", lambda: (TRAFFIC_COLOR, rl.Color(0, 0, 0, 0)))
  monkeypatch.setattr(mici_view.rl, "begin_scissor_mode", lambda *args: calls.append(("begin_scissor", args)))
  monkeypatch.setattr(mici_view.rl, "end_scissor_mode", lambda: calls.append(("end_scissor",)))
  monkeypatch.setattr(mici_view.rl, "draw_rectangle_rounded_lines_ex", lambda *args: calls.append(("line", args)))

  view._draw_border()

  lines = [c for c in calls if c[0] == "line"]
  assert len(lines) == 2
  assert _rgba(lines[0][1][4]) == _rgba(base_color)
  assert _rgba(lines[1][1][4]) == _rgba(TRAFFIC_COLOR)

  scissor = [c for c in calls if c[0] == "begin_scissor"]
  assert scissor[0][1] == (10, 20, 200, 100)
  assert scissor[1][1] == (14, 24, 96, 92)


def test_c4_draw_border_skips_traffic_colors_when_inactive(monkeypatch):
  import pyray as rl
  from openpilot.selfdrive.ui.mici.onroad import augmented_road_view as mici_view

  view = object.__new__(mici_view.AugmentedRoadView)
  view._content_rect = rl.Rectangle(10, 20, 200, 100)
  view._get_border_width = lambda: 8
  view._closed = True

  calls = []
  monkeypatch.setattr(mici_view, "get_border_color", lambda _state: rl.Color(0, 0, 0, 255))
  monkeypatch.setattr(mici_view, "get_traffic_border_colors", lambda: None)
  monkeypatch.setattr(mici_view.rl, "begin_scissor_mode", lambda *args: calls.append(("begin_scissor", args)))
  monkeypatch.setattr(mici_view.rl, "end_scissor_mode", lambda: calls.append(("end_scissor",)))
  monkeypatch.setattr(mici_view.rl, "draw_rectangle_rounded_lines_ex", lambda *args: calls.append(("line", args)))

  view._draw_border()

  assert len([c for c in calls if c[0] == "line"]) == 1
  assert len([c for c in calls if c[0] == "begin_scissor"]) == 1
