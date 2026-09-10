import sys
from types import SimpleNamespace

import pyray as rl

from openpilot.common.params import ParamKeyType
from openpilot.selfdrive.ui.onroad.starpilot.favorite_radial_menu import FavoriteRadialMenu
from openpilot.starpilot.common.favorite_slots import (
  FAVORITE_ACTION_DECEL_COUNTER,
  FAVORITE_ACTION_DISTANCE_DECREASE,
  FAVORITE_SLOTS_PARAM,
)


class FakeParams:
  def __init__(self):
    self.store = {}
    self.types = {
      FAVORITE_SLOTS_PARAM: ParamKeyType.JSON,
      "FeatureToggle": ParamKeyType.BOOL,
      "OtherToggle": ParamKeyType.BOOL,
    }

  def get(self, key):
    return self.store.get(key)

  def get_bool(self, key):
    return bool(self.store.get(key, False))

  def put(self, key, value):
    self.store[key] = value

  def put_bool(self, key, value):
    self.store[key] = bool(value)

  def put_bool_nonblocking(self, key, value):
    self.put_bool(key, value)

  def get_int(self, key, default=0):
    return int(self.store.get(key, default))

  def put_int(self, key, value):
    self.store[key] = int(value)

  def put_int_nonblocking(self, key, value):
    self.put_int(key, value)

  def put_nonblocking(self, key, value):
    self.put(key, value)

  def get_type(self, key):
    return self.types.get(key, ParamKeyType.STRING)


def _event(x, y, *, pressed=False, released=False, down=False):
  return SimpleNamespace(
    pos=SimpleNamespace(x=x, y=y),
    slot=0,
    left_pressed=pressed,
    left_released=released,
    left_down=down,
  )


def _tap(menu, rect, center):
  menu.process_mouse_events([_event(center.x, center.y, pressed=True)], rect)
  menu.process_mouse_events([_event(center.x, center.y, released=True)], rect)


def _rect_center(rect):
  return SimpleNamespace(x=rect.x + rect.width / 2, y=rect.y + rect.height / 2)


def _open_picker(menu, rect, slot_index=0):
  _tap(menu, rect, menu.corner_center(rect))
  _tap(menu, rect, menu.slot_centers(rect)[slot_index])
  assert menu.state == FavoriteRadialMenu.STATE_PICKER


def _menu(clock, options=None):
  params = FakeParams()
  memory = FakeParams()
  options = options or [
    {"key": "FeatureToggle", "label": "Feature Toggle", "description": "The primary test setting.", "section": "Testing"},
    {"key": "OtherToggle", "label": "Other Toggle", "description": "Another test setting.", "section": "Testing"},
  ]
  return FavoriteRadialMenu(params, memory, lambda: options, clock=lambda: clock[0]), params, memory


def test_radial_menu_opens_from_corner_tap_and_arranges_three_slots_on_an_arc():
  clock = [0.0]
  menu, _params, _memory = _menu(clock)
  rect = rl.Rectangle(0, 0, 2160, 1080)

  _tap(menu, rect, menu.corner_center(rect))

  assert menu.state == FavoriteRadialMenu.STATE_RADIAL
  centers = menu.slot_centers(rect)
  assert len(centers) == 3
  assert centers[0].x < centers[1].x < centers[2].x
  assert centers[0].y < centers[1].y < centers[2].y


def test_corner_hint_keeps_visible_ring_near_content_corner():
  clock = [0.0]
  menu, _params, _memory = _menu(clock)
  rect = rl.Rectangle(0, 0, 2160, 1080)

  scale = menu._scale_for(rect)
  center = menu.corner_center(rect)
  ring_radius = menu.CORNER_HINT_RING_RADIUS * scale
  edge_margin = menu.CORNER_HINT_EDGE_MARGIN * scale

  assert center.x - ring_radius == rect.x + edge_margin
  assert rect.y + rect.height - center.y - ring_radius == edge_margin
  assert menu._contains(menu._corner_touch_zone_for(rect), center)


def test_radial_menu_opens_from_diagonal_inward_swipe_and_auto_collapses_after_six_seconds():
  clock = [0.0]
  menu, _params, _memory = _menu(clock)
  rect = rl.Rectangle(0, 0, 2160, 1080)
  start = menu.corner_center(rect)
  end = SimpleNamespace(x=start.x + 170, y=start.y - 170)

  menu.process_mouse_events([_event(start.x, start.y, pressed=True)], rect)
  menu.process_mouse_events([_event(end.x, end.y, released=True)], rect)

  assert menu.state == FavoriteRadialMenu.STATE_RADIAL

  clock[0] = 6.01
  menu.process_mouse_events([], rect)

  assert menu.state == FavoriteRadialMenu.STATE_COLLAPSED


def test_add_slot_opens_option_grid_and_saves_shared_favorite_slot_params():
  clock = [0.0]
  menu, params, memory = _menu(clock)
  rect = rl.Rectangle(0, 0, 2160, 1080)

  _tap(menu, rect, menu.corner_center(rect))
  _tap(menu, rect, menu.slot_centers(rect)[0])

  assert menu.state == FavoriteRadialMenu.STATE_PICKER
  assert menu.selected_slot == 0

  _tap(menu, rect, menu.option_centers(rect)[0])

  assert menu.state == FavoriteRadialMenu.STATE_RADIAL
  assert params.get(FAVORITE_SLOTS_PARAM)[0] == {
    "enabled": True,
    "show_onroad": True,
    "key": "FeatureToggle",
    "label": "Feature Toggle",
  }
  assert memory.get_bool("StarPilotTogglesUpdated") is True


def test_radial_menu_filters_stored_slot_that_is_not_in_current_catalog():
  clock = [0.0]
  menu, params, _memory = _menu(clock, options=[
    {"key": "FeatureToggle", "label": "Feature Toggle", "description": "Available", "section": "Testing"},
  ])
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "OtherToggle", "label": "Other Toggle"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)

  _tap(menu, rect, menu.corner_center(rect))

  assert menu.state == FavoriteRadialMenu.STATE_RADIAL
  assert menu._slots[0]["key"] is None


def test_picker_stays_open_for_thirty_seconds():
  clock = [0.0]
  menu, _params, _memory = _menu(clock)
  rect = rl.Rectangle(0, 0, 2160, 1080)

  _tap(menu, rect, menu.corner_center(rect))
  _tap(menu, rect, menu.slot_centers(rect)[0])
  assert menu.state == FavoriteRadialMenu.STATE_PICKER

  clock[0] = 6.01
  menu.process_mouse_events([], rect)
  assert menu.state == FavoriteRadialMenu.STATE_PICKER

  clock[0] = 30.01
  menu.process_mouse_events([], rect)
  assert menu.state == FavoriteRadialMenu.STATE_COLLAPSED


def test_configured_radial_slot_uses_the_shared_toggle_behavior():
  clock = [0.0]
  menu, params, memory = _menu(clock)
  params.put("FeatureToggle", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "FeatureToggle", "label": "Feature Toggle"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)

  _tap(menu, rect, menu.corner_center(rect))
  _tap(menu, rect, menu.slot_centers(rect)[0])

  assert params.get_bool("FeatureToggle") is True
  assert memory.get_bool("StarPilotTogglesUpdated") is True


def test_picker_pages_keep_all_available_options_selectable():
  clock = [0.0]
  params = FakeParams()
  memory = FakeParams()
  options = [
    {"key": f"Option{index:02}", "label": f"Option {index:02}", "description": "Test option", "section": "Testing"}
    for index in range(9)
  ]
  params.types.update({option["key"]: ParamKeyType.BOOL for option in options})
  menu = FavoriteRadialMenu(params, memory, lambda: options, clock=lambda: clock[0])
  rect = rl.Rectangle(0, 0, 2160, 1080)

  _tap(menu, rect, menu.corner_center(rect))
  _tap(menu, rect, menu.slot_centers(rect)[0])

  # The first-page Previous button is disabled, but it must not close the drawer.
  _tap(menu, rect, _rect_center(menu._drawer_prev_rect))
  assert menu.state == FavoriteRadialMenu.STATE_PICKER

  _tap(menu, rect, _rect_center(menu._drawer_next_rect))
  second_page_centers = menu.option_centers(rect)
  assert len(second_page_centers) == 1

  _tap(menu, rect, second_page_centers[0])
  assert params.get(FAVORITE_SLOTS_PARAM)[0]["key"] == "Option08"


def test_picker_geometry_fits_the_production_content_rect_without_card_overlap():
  clock = [0.0]
  options = [
    {"key": f"Option{index}", "label": f"Option {index}", "description": "Test option", "section": "Testing"}
    for index in range(8)
  ]
  menu, _params, _memory = _menu(clock, options=options)
  rect = rl.Rectangle(30, 30, 2100, 1020)

  _open_picker(menu, rect)

  drawer = menu._drawer_rect
  assert drawer.x >= rect.x
  assert drawer.y >= rect.y
  assert drawer.x + drawer.width <= rect.x + rect.width
  assert drawer.y + drawer.height <= rect.y + rect.height
  assert len(menu._option_rects) == 8

  cards = [option_rect for _index, option_rect in menu._option_rects]
  for card in cards:
    assert card.x >= drawer.x
    assert card.y >= drawer.y
    assert card.x + card.width <= drawer.x + drawer.width
    assert card.y + card.height <= drawer.y + drawer.height
    assert card.width >= 440
    assert card.height >= 250

  for index, first in enumerate(cards):
    for second in cards[index + 1:]:
      horizontal_gap = max(first.x, second.x) - min(first.x + first.width, second.x + second.width)
      vertical_gap = max(first.y, second.y) - min(first.y + first.height, second.y + second.height)
      assert horizontal_gap > 0 or vertical_gap > 0

  footer_top = drawer.y + drawer.height - menu.PICKER_FOOTER_HEIGHT * menu._scale_for(rect)
  assert menu._drawer_prev_rect.y >= footer_top
  assert menu._drawer_next_rect.y >= footer_top


def test_picker_control_hit_targets_are_tall_enough_for_production_scale():
  clock = [0.0]
  options = [
    {"key": f"Option{index}", "label": f"Option {index}", "description": "Test option", "section": "Testing"}
    for index in range(9)
  ]
  menu, _params, _memory = _menu(clock, options=options)
  rect = rl.Rectangle(30, 30, 2100, 1020)

  _open_picker(menu, rect)
  minimum_hit_height = 144.0 * menu._scale_for(rect)

  assert menu._drawer_prev_hit_rect.height >= minimum_hit_height
  assert menu._drawer_next_hit_rect.height >= minimum_hit_height
  assert menu._drawer_close_hit_rect.height >= minimum_hit_height


def test_picker_description_uses_measured_wrap_and_truncates_to_two_lines(monkeypatch):
  clock = [0.0]
  long_description = "This description is deliberately long enough to require measured wrapping."
  option = {
    "key": "MeasuredDescription",
    "label": "Measured Description",
    "description": long_description,
    "section": "Testing",
  }
  menu, _params, _memory = _menu(clock, options=[option])
  rect = rl.Rectangle(30, 30, 2100, 1020)
  _open_picker(menu, rect)
  card_rect = menu._option_rects[0][1]

  wrap_calls = []
  drawn_texts = []

  def fake_wrap(font, text, font_size, max_width, spacing=0):
    wrap_calls.append((text, font_size, max_width))
    return ["Measured first line", "Measured second line", "Measured overflow"]

  monkeypatch.setitem(sys.modules, "openpilot.system.ui.lib.wrap_text", SimpleNamespace(wrap_text=fake_wrap))
  monkeypatch.setattr(menu, "_font", lambda *, bold: object())
  monkeypatch.setattr(FavoriteRadialMenu, "_measure_text",
                      staticmethod(lambda _font, text, _font_size: rl.Vector2(max(10, len(text) * 4), 20)))
  monkeypatch.setattr(FavoriteRadialMenu, "_draw_text",
                      staticmethod(lambda _font, text, _pos, _font_size, _color: drawn_texts.append(text)))
  monkeypatch.setattr(rl, "draw_rectangle_rounded", lambda *args: None)
  monkeypatch.setattr(rl, "draw_rectangle_rounded_lines_ex", lambda *args: None)

  menu._draw_option_card(card_rect, option, menu._scale_for(rect))

  assert len(wrap_calls) == 1
  assert wrap_calls[0][0] == long_description
  assert wrap_calls[0][1] >= 24
  assert wrap_calls[0][2] > 0
  assert drawn_texts[-2:] == ["Measured first line", "Measured second line..."]


def test_picker_uses_compact_section_labels_without_mutating_catalog_copy():
  clock = [0.0]
  menu, _params, _memory = _menu(clock)

  assert menu._picker_section_label({"section": "Longitudinal (Speed & Following)"}) == "Speed & Following"
  assert menu._picker_section_label({"section": "Lateral (Steering)"}) == "Steering"
  assert menu._picker_section_label({"section": "Visual (Display & UI)"}) == "Display & UI"
  assert menu._picker_section_label({"section": "Testing"}) == "Testing"


def test_picker_fit_text_truncates_at_word_boundary(monkeypatch):
  monkeypatch.setattr(FavoriteRadialMenu, "_measure_text",
                      staticmethod(lambda _font, text, _font_size: rl.Vector2(len(text) * 10, 20)))

  fitted = FavoriteRadialMenu._fit_picker_text(object(), "Longitudinal Speed Following", 24, 160)

  assert fitted == "Longitudinal..."


def test_picker_wraps_long_titles_by_measured_words(monkeypatch):
  clock = [0.0]
  option = {
    "key": "LongTitle",
    "label": "Fallback Label",
    "picker_label": "Adaptive Acceleration Limit",
    "description": "",
    "section": "Testing",
  }
  menu, _params, _memory = _menu(clock, options=[option])
  rect = rl.Rectangle(30, 30, 2100, 1020)
  _open_picker(menu, rect)
  card_rect = menu._option_rects[0][1]
  drawn_texts = []

  def fake_measure(_font, text, _font_size):
    width = 1000 if text == "Adaptive Acceleration Limit" else max(10, len(text) * 4)
    return rl.Vector2(width, 20)

  def fake_wrap(_font, text, _font_size, _max_width, spacing=0):
    assert text == "Adaptive Acceleration Limit"
    return ["Adaptive Acceleration", "Limit"]

  monkeypatch.setitem(sys.modules, "openpilot.system.ui.lib.wrap_text", SimpleNamespace(wrap_text=fake_wrap))
  monkeypatch.setattr(menu, "_font", lambda *, bold: object())
  monkeypatch.setattr(FavoriteRadialMenu, "_measure_text", staticmethod(fake_measure))
  monkeypatch.setattr(FavoriteRadialMenu, "_draw_text",
                      staticmethod(lambda _font, text, _pos, _font_size, _color: drawn_texts.append(text)))
  monkeypatch.setattr(rl, "draw_rectangle_rounded", lambda *args: None)
  monkeypatch.setattr(rl, "draw_rectangle_rounded_lines_ex", lambda *args: None)

  menu._draw_option_card(card_rect, option, menu._scale_for(rect))

  assert "Adaptive Acceleration" in drawn_texts
  assert "Limit" in drawn_texts
  assert "Fallback Label" not in drawn_texts


def test_picker_prefers_picker_specific_description(monkeypatch):
  clock = [0.0]
  option = {
    "key": "CompactDescription",
    "label": "Compact Description",
    "description": "The complete settings description should remain available outside the picker.",
    "picker_description": "Short picker description.",
    "section": "Testing",
  }
  menu, _params, _memory = _menu(clock, options=[option])
  rect = rl.Rectangle(30, 30, 2100, 1020)
  _open_picker(menu, rect)
  card_rect = menu._option_rects[0][1]
  wrap_inputs = []
  drawn_texts = []

  def fake_wrap(font, text, font_size, max_width, spacing=0):
    wrap_inputs.append(text)
    return [text]

  monkeypatch.setitem(sys.modules, "openpilot.system.ui.lib.wrap_text", SimpleNamespace(wrap_text=fake_wrap))
  monkeypatch.setattr(menu, "_font", lambda *, bold: object())
  monkeypatch.setattr(FavoriteRadialMenu, "_measure_text",
                      staticmethod(lambda _font, text, _font_size: rl.Vector2(max(10, len(text) * 4), 20)))
  monkeypatch.setattr(FavoriteRadialMenu, "_draw_text",
                      staticmethod(lambda _font, text, _pos, _font_size, _color: drawn_texts.append(text)))
  monkeypatch.setattr(rl, "draw_rectangle_rounded", lambda *args: None)
  monkeypatch.setattr(rl, "draw_rectangle_rounded_lines_ex", lambda *args: None)

  menu._draw_option_card(card_rect, option, menu._scale_for(rect))

  assert wrap_inputs == ["Short picker description."]
  assert "Short picker description." in drawn_texts
  assert "The complete settings description should remain available outside the picker." not in drawn_texts


def test_picker_pressed_card_has_a_distinct_visual_state(monkeypatch):
  clock = [0.0]
  option = {"key": "PressedOption", "label": "Pressed Option", "description": "", "section": "Testing"}
  menu, _params, _memory = _menu(clock, options=[option])
  rect = rl.Rectangle(30, 30, 2100, 1020)
  _open_picker(menu, rect)
  card_rect = menu._option_rects[0][1]
  card_colors = []

  def capture_card_fill(draw_rect, *_args):
    if all(abs(getattr(draw_rect, attr) - getattr(card_rect, attr)) < 0.01 for attr in ("x", "y", "width", "height")):
      color = _args[-1]
      card_colors.append((color.r, color.g, color.b, color.a))

  monkeypatch.setattr(menu, "_font", lambda *, bold: object())
  monkeypatch.setattr(FavoriteRadialMenu, "_measure_text",
                      staticmethod(lambda _font, text, _font_size: rl.Vector2(max(10, len(text) * 4), 20)))
  monkeypatch.setattr(FavoriteRadialMenu, "_draw_text", staticmethod(lambda *args: None))
  monkeypatch.setattr(rl, "draw_rectangle_rounded", capture_card_fill)
  monkeypatch.setattr(rl, "draw_rectangle_rounded_lines_ex", lambda *args: None)

  menu._draw_option_card(card_rect, option, menu._scale_for(rect), pressed=False)
  menu._draw_option_card(card_rect, option, menu._scale_for(rect), pressed=True)

  assert len(card_colors) == 2
  assert card_colors[0] != card_colors[1]


def test_picker_release_on_a_different_option_cancels_without_assignment():
  clock = [0.0]
  options = [
    {"key": "OptionA", "label": "Option A", "description": "A", "section": "Testing"},
    {"key": "OptionB", "label": "Option B", "description": "B", "section": "Testing"},
  ]
  menu, params, _memory = _menu(clock, options=options)
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _open_picker(menu, rect)
  option_a, option_b = menu.option_centers(rect)

  menu.process_mouse_events([_event(option_a.x, option_a.y, pressed=True)], rect)
  menu.process_mouse_events([_event(option_b.x, option_b.y, released=True)], rect)

  assert menu.state == FavoriteRadialMenu.STATE_PICKER
  assert params.get(FAVORITE_SLOTS_PARAM) is None


def test_picker_release_target_must_match_pressed_target(monkeypatch):
  clock = [0.0]
  menu, _params, _memory = _menu(clock, options=[
    {"key": "OptionA", "label": "Option A", "description": "A", "section": "Testing"},
    {"key": "OptionB", "label": "Option B", "description": "B", "section": "Testing"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _open_picker(menu, rect)
  press_pos = SimpleNamespace(x=100, y=100)
  activated = []
  menu._pressed_target = ("option", 0)
  menu._press_start_time = clock[0]
  menu._press_start_pos = press_pos
  monkeypatch.setattr(menu, "_target_at", lambda _mouse_pos: ("option", 1))
  monkeypatch.setattr(menu, "_activate_target", lambda target: activated.append(target))

  menu._handle_release(press_pos)

  assert activated == []
  assert menu.state == FavoriteRadialMenu.STATE_PICKER


def test_picker_release_outside_after_pressing_an_option_cancels_without_assignment():
  clock = [0.0]
  option = {"key": "OptionA", "label": "Option A", "description": "A", "section": "Testing"}
  menu, params, _memory = _menu(clock, options=[option])
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _open_picker(menu, rect)
  option_a = menu.option_centers(rect)[0]
  outside = SimpleNamespace(x=rect.x + 5, y=rect.y + 5)

  menu.process_mouse_events([_event(option_a.x, option_a.y, pressed=True)], rect)
  menu.process_mouse_events([_event(outside.x, outside.y, released=True)], rect)

  assert menu.state == FavoriteRadialMenu.STATE_PICKER
  assert params.get(FAVORITE_SLOTS_PARAM) is None


def test_picker_release_on_the_same_option_assigns_it():
  clock = [0.0]
  option = {"key": "OptionA", "label": "Option A", "description": "A", "section": "Testing"}
  menu, params, _memory = _menu(clock, options=[option])
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _open_picker(menu, rect)

  _tap(menu, rect, menu.option_centers(rect)[0])

  assert menu.state == FavoriteRadialMenu.STATE_RADIAL
  assert params.get(FAVORITE_SLOTS_PARAM)[0]["key"] == "OptionA"


def test_picker_disabled_previous_stays_open_but_an_untargeted_outside_tap_dismisses():
  clock = [0.0]
  options = [
    {"key": f"Option{index:02}", "label": f"Option {index:02}", "description": "Test option", "section": "Testing"}
    for index in range(9)
  ]
  menu, _params, _memory = _menu(clock, options=options)
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _open_picker(menu, rect)

  _tap(menu, rect, _rect_center(menu._drawer_prev_rect))
  assert menu.state == FavoriteRadialMenu.STATE_PICKER

  outside = SimpleNamespace(x=rect.x + 5, y=rect.y + 5)
  _tap(menu, rect, outside)
  assert menu.state == FavoriteRadialMenu.STATE_COLLAPSED


def test_short_tap_toggles_action_and_does_not_enter_edit_mode():
  clock = [0.0]
  menu, params, memory = _menu(clock)
  params.put("FeatureToggle", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "FeatureToggle", "label": "Feature Toggle"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _tap(menu, rect, menu.corner_center(rect))

  # Short tap: 0.20s duration (< 0.60s)
  slot_pos = menu.slot_centers(rect)[0]
  clock[0] = 1.0
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, pressed=True)], rect)
  clock[0] = 1.20
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, released=True)], rect)

  assert params.get_bool("FeatureToggle") is True
  assert memory.get_bool("StarPilotTogglesUpdated") is True
  assert menu.editing_slot is None
  assert menu.state == FavoriteRadialMenu.STATE_RADIAL


def test_long_press_enters_edit_mode_without_toggling_action():
  clock = [0.0]
  menu, params, memory = _menu(clock)
  params.put("FeatureToggle", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "FeatureToggle", "label": "Feature Toggle"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _tap(menu, rect, menu.corner_center(rect))

  # Long press: 0.65s duration (>= 0.60s)
  slot_pos = menu.slot_centers(rect)[0]
  clock[0] = 1.0
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, pressed=True)], rect)
  clock[0] = 1.65
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, released=True)], rect)

  # Must NOT toggle parameter on hold or release
  assert params.get_bool("FeatureToggle") is False
  assert menu.editing_slot == 0
  assert len(menu.unassign_centers(rect)) == 1


def test_unassign_target_resets_slot_and_refreshes_memory():
  clock = [0.0]
  menu, params, memory = _menu(clock)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "FeatureToggle", "label": "Feature Toggle"},
    {"enabled": True, "show_onroad": True, "key": "OtherToggle", "label": "Other Toggle"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _tap(menu, rect, menu.corner_center(rect))

  # Enter edit mode on slot 0
  slot_pos = menu.slot_centers(rect)[0]
  clock[0] = 1.0
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, pressed=True)], rect)
  clock[0] = 1.70
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, released=True)], rect)
  assert menu.editing_slot == 0

  # Tap unassign target
  unassign_pos = menu.unassign_centers(rect)[0]
  _tap(menu, rect, unassign_pos)

  slots = params.get(FAVORITE_SLOTS_PARAM)
  assert slots[0] == {"enabled": False, "show_onroad": False, "key": None, "label": ""}
  assert slots[1]["key"] == "OtherToggle"
  assert memory.get_bool("StarPilotTogglesUpdated") is True
  assert menu.editing_slot is None


def test_tapping_away_cancels_edit_mode_without_unassigning():
  clock = [0.0]
  menu, params, _memory = _menu(clock)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "FeatureToggle", "label": "Feature Toggle"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _tap(menu, rect, menu.corner_center(rect))

  # Long press to enter edit mode
  slot_pos = menu.slot_centers(rect)[0]
  clock[0] = 1.0
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, pressed=True)], rect)
  clock[0] = 1.70
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, released=True)], rect)
  assert menu.editing_slot == 0

  # Tapping slot card outside unassign button cancels edit mode
  _tap(menu, rect, slot_pos)
  assert menu.editing_slot is None
  assert params.get(FAVORITE_SLOTS_PARAM)[0]["key"] == "FeatureToggle"


def test_long_press_cancelled_by_drag_travel():
  clock = [0.0]
  menu, params, _memory = _menu(clock)
  params.put("FeatureToggle", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "FeatureToggle", "label": "Feature Toggle"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _tap(menu, rect, menu.corner_center(rect))

  slot_pos = menu.slot_centers(rect)[0]
  clock[0] = 1.0
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, pressed=True)], rect)
  clock[0] = 1.70
  # Drag 60px away (> MAX_TAP_TRAVEL * scale)
  menu.process_mouse_events([_event(slot_pos.x + 60, slot_pos.y, released=True)], rect)

  assert params.get_bool("FeatureToggle") is False
  assert menu.editing_slot is None


def test_unassign_action_slot_does_not_trigger_action_counter():
  clock = [0.0]
  menu, params, memory = _menu(clock, options=[
    {"key": FAVORITE_ACTION_DISTANCE_DECREASE, "label": "Distance -", "section": "Actions"},
  ])
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": FAVORITE_ACTION_DISTANCE_DECREASE, "label": "Distance -"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _tap(menu, rect, menu.corner_center(rect))

  slot_pos = menu.slot_centers(rect)[0]
  clock[0] = 1.0
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, pressed=True)], rect)
  clock[0] = 1.70
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, released=True)], rect)
  _tap(menu, rect, menu.unassign_centers(rect)[0])

  assert memory.get(FAVORITE_ACTION_DECEL_COUNTER) in (None, 0)
  assert params.get(FAVORITE_SLOTS_PARAM)[0]["key"] is None


def test_auto_collapse_cleans_up_edit_mode():
  clock = [0.0]
  menu, params, _memory = _menu(clock)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "FeatureToggle", "label": "Feature Toggle"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _tap(menu, rect, menu.corner_center(rect))

  # Enter edit mode
  slot_pos = menu.slot_centers(rect)[0]
  clock[0] = 1.0
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, pressed=True)], rect)
  clock[0] = 1.70
  menu.process_mouse_events([_event(slot_pos.x, slot_pos.y, released=True)], rect)
  assert menu.editing_slot == 0

  # Idle timeout expires
  clock[0] = 8.0
  menu.process_mouse_events([], rect)
  assert menu.state == FavoriteRadialMenu.STATE_COLLAPSED
  assert menu.editing_slot is None


def test_tapping_blade_label_triggers_slot_toggle():
  clock = [0.0]
  menu, params, memory = _menu(clock)
  params.put("FeatureToggle", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "FeatureToggle", "label": "Feature Toggle"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _tap(menu, rect, menu.corner_center(rect))

  # Tap at +120px to the right of node center (on the blade label body)
  slot_pos = menu.slot_centers(rect)[0]
  blade_label_pos = SimpleNamespace(x=slot_pos.x + 120, y=slot_pos.y)
  _tap(menu, rect, blade_label_pos)

  assert params.get_bool("FeatureToggle") is True
  assert memory.get_bool("StarPilotTogglesUpdated") is True


def test_semantic_split_label_handles_various_lengths():
  # Short label: stays on 1 line
  line1, line2 = FavoriteRadialMenu._semantic_split_label("Always On Lateral", max_chars=18)
  assert line1 == "Always On Lateral"
  assert line2 is None

  # Long label: splits into 2 lines
  line1, line2 = FavoriteRadialMenu._semantic_split_label("Automatic Lane Changes", max_chars=18)
  assert line1 == "Automatic Lane"
  assert line2 == "Changes"

  # Long setting with parenthetical
  line1, line2 = FavoriteRadialMenu._semantic_split_label("Neural Network Feedforward (NNFF)", max_chars=18)
  assert line1 == "Neural Network"
  assert line2 == "Feedforward (NNFF)"


def test_tapping_dropdown_blade_cycles_parameter():
  clock = [0.0]
  options = [
    {"key": "AccelerationProfile", "label": "Acceleration Profile", "ui_type": "dropdown", "data_type": "int",
     "options": [{"value": 0, "label": "Standard"}, {"value": 1, "label": "Eco"}, {"value": 2, "label": "Sport"}, {"value": 3, "label": "Sport+"}]},
  ]
  menu, params, memory = _menu(clock, options=options)
  params.types["AccelerationProfile"] = ParamKeyType.INT
  params.put_int("AccelerationProfile", 0)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "AccelerationProfile", "label": "Acceleration Profile"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)

  # Open menu
  _tap(menu, rect, menu.corner_center(rect))

  # Tap slot 0 blade -> cycles to 1 (Eco)
  _tap(menu, rect, menu.slot_centers(rect)[0])
  assert params.get_int("AccelerationProfile") == 1
  assert memory.get_bool("StarPilotTogglesUpdated") is True

  # Advance clock past cooldown (300ms) and tap again -> cycles to 2 (Sport)
  clock[0] = 0.35
  _tap(menu, rect, menu.slot_centers(rect)[0])
  assert params.get_int("AccelerationProfile") == 2


def test_render_during_wave_flash_animation(monkeypatch):
  clock = [0.0]
  options = [
    {"key": "Compass", "label": "Compass", "ui_type": "toggle", "data_type": "bool"},
  ]
  menu, params, memory = _menu(clock, options=options)
  params.types["Compass"] = ParamKeyType.BOOL
  params.put("Compass", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "Compass", "label": "Compass"},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)

  # Mock drawing functions and fonts for headless testing
  from openpilot.system.ui.lib.application import gui_app
  drawn_rings = []
  monkeypatch.setattr(gui_app, "font", lambda *a, **kw: rl.Font())
  monkeypatch.setattr(menu, "_measure_text", lambda *a, **kw: rl.Vector2(100.0, 20.0))
  monkeypatch.setattr(rl, "draw_ring", lambda *args: drawn_rings.append(args))
  monkeypatch.setattr(rl, "draw_circle_v", lambda *args: None)
  monkeypatch.setattr(rl, "draw_rectangle_rounded", lambda *args: None)
  monkeypatch.setattr(rl, "draw_rectangle_rounded_lines_ex", lambda *args: None)
  monkeypatch.setattr(rl, "draw_line_ex", lambda *args: None)
  monkeypatch.setattr(rl, "draw_triangle", lambda *args: None)
  monkeypatch.setattr(rl, "draw_text_ex", lambda *args: None)

  # Open menu
  _tap(menu, rect, menu.corner_center(rect))

  # Tap Compass slot -> triggers wave flash
  _tap(menu, rect, menu.slot_centers(rect)[0])
  assert params.get_bool("Compass") is True
  assert menu._flash_slot == 0

  # Render frames across the entire flash duration (0ms to 250ms) to ensure zero math/color exceptions
  for t in [0.0, 0.01, 0.05, 0.09, 0.1799, 0.180, 0.20, 0.25]:
    clock[0] = t
    menu.render(rect)

  assert len(drawn_rings) > 0
  assert menu._flash_slot is None


def test_radial_render_rect_snaps_each_boundary():
  rect = rl.Rectangle(10.36, 20.64, 450.75, 103.21)

  snapped = FavoriteRadialMenu._snap_render_rect(rect)

  assert (snapped.x, snapped.y, snapped.width, snapped.height) == (10.0, 21.0, 451.0, 103.0)


def test_radial_blade_render_uses_pixel_aligned_chassis_and_border(monkeypatch):
  clock = [0.0]
  options = [
    {"key": "Compass", "label": "Compass", "ui_type": "toggle", "data_type": "bool"},
  ]
  menu, params, _memory = _menu(clock, options=options)
  params.types["Compass"] = ParamKeyType.BOOL
  params.put("Compass", False)
  rect = rl.Rectangle(0, 0, 2160, 1080)

  fills = []
  strokes = []
  monkeypatch.setattr(menu, "_font", lambda *, bold: object())
  monkeypatch.setattr(FavoriteRadialMenu, "_measure_text",
                      staticmethod(lambda _font, _text, _font_size: rl.Vector2(100.0, 20.0)))
  monkeypatch.setattr(FavoriteRadialMenu, "_draw_text", staticmethod(lambda *args: None))
  monkeypatch.setattr(rl, "draw_ring", lambda *args: None)
  monkeypatch.setattr(rl, "draw_circle_v", lambda *args: None)
  monkeypatch.setattr(rl, "draw_line_ex", lambda *args: None)
  monkeypatch.setattr(rl, "draw_rectangle_rounded",
                      lambda *args: fills.append(args))
  monkeypatch.setattr(rl, "draw_rectangle_rounded_lines_ex",
                      lambda *args: strokes.append(args))

  cases = (
    ([], None, 1, 255),
    ([{"enabled": True, "show_onroad": True, "key": "Compass", "label": "Compass"}], ("slot", 0), 2, 255),
  )
  for slot_payload, pressed_target, expected_border_width, expected_fill_alpha in cases:
    params.put(FAVORITE_SLOTS_PARAM, slot_payload)
    menu._pressed_target = pressed_target
    menu._layout(rect)
    fills.clear()
    strokes.clear()

    blade_rect = menu._slot_rects[0][5]
    chassis_rect = blade_rect
    if pressed_target is not None:
      pad = 2.0 * menu._scale_for(rect)
      chassis_rect = rl.Rectangle(
        blade_rect.x + pad,
        blade_rect.y + pad,
        blade_rect.width - pad * 2.0,
        blade_rect.height - pad * 2.0,
      )
    expected_rect = menu._snap_render_rect(chassis_rect)

    menu._draw_radial_menu()

    assert fills
    assert strokes
    expected_tuple = (expected_rect.x, expected_rect.y, expected_rect.width, expected_rect.height)
    assert (fills[0][0].x, fills[0][0].y, fills[0][0].width, fills[0][0].height) == expected_tuple
    assert (strokes[0][0].x, strokes[0][0].y, strokes[0][0].width, strokes[0][0].height) == expected_tuple
    assert strokes[0][3] == expected_border_width
    assert fills[0][3].a == expected_fill_alpha
    assert all(float(value).is_integer() for value in (
      strokes[0][0].x,
      strokes[0][0].y,
      strokes[0][0].width,
      strokes[0][0].height,
      strokes[0][3],
    ))


def test_render_boolean_toggle_switch_and_picker_badges(monkeypatch):
  clock = [0.0]
  options = [
    {"key": "RedneckCruise", "label": "Redneck Cruise", "ui_type": "toggle", "data_type": "bool", "section": "Speed"},
    {"key": "AccelerationProfile", "label": "Accel Profile", "ui_type": "dropdown", "data_type": "int", "options": [{"value": 0, "label": "Eco"}, {"value": 1, "label": "Sport"}], "section": "Longitudinal"},
    {"key": "__starpilot_favorite_action__:distance_decrease", "label": "Distance -", "section": "Actions"},
  ]
  menu, params, memory = _menu(clock, options=options)
  params.types["RedneckCruise"] = ParamKeyType.BOOL
  params.put("RedneckCruise", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "RedneckCruise", "label": "Redneck Cruise"},
    {"enabled": False, "show_onroad": False, "key": None, "label": ""},
    {"enabled": False, "show_onroad": False, "key": None, "label": ""},
  ])
  rect = rl.Rectangle(0, 0, 2160, 1080)

  from openpilot.system.ui.lib.application import gui_app
  drawn_texts = []
  monkeypatch.setattr(gui_app, "font", lambda *a, **kw: rl.Font())
  monkeypatch.setattr(FavoriteRadialMenu, "_measure_text", staticmethod(lambda font, text, fs, *a, **kw: rl.Vector2(100.0, 20.0)))
  monkeypatch.setattr(FavoriteRadialMenu, "_draw_text", staticmethod(lambda font, text, pos, fs, col: drawn_texts.append(text)))
  monkeypatch.setattr(rl, "draw_ring", lambda *args: None)
  monkeypatch.setattr(rl, "draw_circle_v", lambda *args: None)
  monkeypatch.setattr(rl, "draw_rectangle_rounded", lambda *args: None)
  monkeypatch.setattr(rl, "draw_rectangle_rounded_lines_ex", lambda *args: None)
  monkeypatch.setattr(rl, "draw_line_ex", lambda *args: None)
  monkeypatch.setattr(rl, "draw_triangle", lambda *args: None)
  monkeypatch.setattr(rl, "draw_rectangle_rec", lambda *args: None)
  monkeypatch.setattr(rl, "draw_text_ex", lambda *args: None)

  # Open menu in radial mode with RedneckCruise OFF
  _tap(menu, rect, menu.corner_center(rect))
  drawn_texts.clear()
  menu.render(rect)
  assert "OFF" in drawn_texts

  # Toggle RedneckCruise ON
  _tap(menu, rect, menu.slot_centers(rect)[0])
  assert params.get_bool("RedneckCruise") is True
  drawn_texts.clear()
  menu.render(rect)
  assert "ON" in drawn_texts

  # Tap empty slot 2 to open picker drawer
  _tap(menu, rect, menu.slot_centers(rect)[1])
  assert menu.is_picker_open
  drawn_texts.clear()
  menu.render(rect)
  assert "TOGGLE" in drawn_texts
  assert "2 STATES" in drawn_texts
  assert "ACTION" in drawn_texts



def test_speed_assignment_requires_new_galaxy_without_disabling_existing_slot():
  from openpilot.starpilot.common.controller_actions import CONTROLLER_ACTION_SET_SPEED

  speed_option = {"key": CONTROLLER_ACTION_SET_SPEED, "label": "Set Speed To", "value_type": "speed", "default_value": 30}
  menu, params, _memory = _menu([0.0], options=[speed_option, {"key": "FeatureToggle", "label": "Feature Toggle"}])
  params.put(FAVORITE_SLOTS_PARAM, [{"enabled": True, "show_onroad": True, "key": "FeatureToggle", "label": "Feature Toggle"}])
  menu._open_picker(0)

  assert CONTROLLER_ACTION_SET_SPEED in menu._available_option_keys
  assert [option["key"] for option in menu._picker_options] == ["FeatureToggle"]
  menu._assign_option(speed_option)
  assert params.get(FAVORITE_SLOTS_PARAM)[0]["key"] == "FeatureToggle"
  assert menu.state == FavoriteRadialMenu.STATE_PICKER


def test_saved_speed_favorite_retains_value_and_displays_current_unit():
  from openpilot.starpilot.common.controller_actions import CONTROLLER_ACTION_SET_SPEED

  menu, params, _memory = _menu([0.0], options=[{"key": CONTROLLER_ACTION_SET_SPEED, "label": "Set Speed To", "value_type": "speed"}])
  params.put(FAVORITE_SLOTS_PARAM, [{"enabled": True, "show_onroad": True, "key": CONTROLLER_ACTION_SET_SPEED, "label": "Set Speed To", "value": 42}])
  menu._open_radial()
  for metric, unit in [(False, "mph"), (True, "km/h")]:
    params.put_bool("IsMetric", metric)
    menu._layout(rl.Rectangle(0, 0, 2160, 1080))
    slot = menu._slots[0]
    assert menu._slot_is_configured(slot)
    assert slot["value"] == 42
    assert slot["label"] == f"Set Speed To 42 {unit}"
  assert params.get(FAVORITE_SLOTS_PARAM)[0]["label"] == "Set Speed To"



def test_native_saved_speed_favorite_tap_dispatches_configured_value(monkeypatch):
  from openpilot.starpilot.common.controller_actions import CONTROLLER_ACTION_SET_SPEED
  from openpilot.starpilot.system.wheel_controls import wheel_controlsd

  menu, params, memory = _menu([0.0], options=[{"key": CONTROLLER_ACTION_SET_SPEED, "label": "Set Speed To", "value_type": "speed"}])
  slot = {"enabled": True, "show_onroad": True, "key": CONTROLLER_ACTION_SET_SPEED, "label": "Set Speed To", "value": 42}
  params.put(FAVORITE_SLOTS_PARAM, [slot])
  dispatched = []
  monkeypatch.setattr(wheel_controlsd, "execute_controller_key", lambda key, params, memory, **kwargs: dispatched.append((key, kwargs["value"])) or True)
  rect = rl.Rectangle(0, 0, 2160, 1080)
  _tap(menu, rect, menu.corner_center(rect))
  _tap(menu, rect, menu.slot_centers(rect)[0])

  assert dispatched == [(CONTROLLER_ACTION_SET_SPEED, 42)]
  assert params.get(FAVORITE_SLOTS_PARAM) == [slot]
