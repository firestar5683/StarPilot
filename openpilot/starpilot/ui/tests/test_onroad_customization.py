import json
from dataclasses import replace
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import pyray as rl
import pytest

from openpilot.starpilot.ui.onroad_customization import (
  MAX_BYTES, customization_metadata, default_document, offset, read_customization, validate_document, decode_document, widget_palette, rgba,
  widget_size)
from openpilot.starpilot.ui.onroad_compact_widgets import CompactHudRenderer
from openpilot.starpilot.ui.onroad_large_widgets import CurrentSpeedHud, SetSpeedWidget, SteeringWheelWidget
from openpilot.starpilot.ui.onroad_state import (
  AlertSize, ObservationKind, OnroadAlert, OnroadInput, OnroadRequest, OnroadState, SpeedLimitObservation, slc_controls)
from openpilot.starpilot.ui.presentation import Profile


def road(document=None, **changes):
  return replace(OnroadState(True, True, 15.0, 80.0, SpeedLimitObservation()),
                 customization=document or default_document(), **changes)


def test_defaults_and_metadata_are_independent_and_valid():
  document = default_document()
  assert validate_document(document) == document
  for profile, data in customization_metadata()["profiles"].items():
    for key, widget in data["widgets"].items():
      assert document["layouts"][profile][key] == {
        **widget["default"], **({"size": widget["width"]} if key == "steering_wheel" else {})}
      assert offset(document, profile, key) == (0, 0)
  document["layouts"]["large"]["current_speed"]["x"] = 50
  assert default_document()["layouts"]["large"]["current_speed"]["x"] == 640


@pytest.mark.parametrize("widget,x,y", [("max_speed", 174, 19), ("steering_wheel", 174, 131)])
def test_protected_compact_actions_reject_actual_overlap(widget, x, y):
  document = default_document()
  document["layouts"]["compact"][widget].update(x=x, y=y)
  with pytest.raises(ValueError, match="protected"):
    validate_document(document)


@pytest.mark.parametrize("widget,x,y", [("speed_limit", 330, 48), ("max_speed", 174, 18), ("steering_wheel", 124, 180)])
def test_protected_zone_edge_touch_is_valid(widget, x, y):
  document = default_document()
  document["layouts"]["compact"][widget].update(x=x, y=y)
  assert validate_document(document) == document
  zones = customization_metadata()["profiles"]["compact"]["reservedZones"]
  assert zones == []
  assert customization_metadata()["profiles"]["compact"]["protectedWidget"] == "speed_limit_actions"


@pytest.mark.parametrize("change", [
  lambda d: d.update(version=True),
  lambda d: d.update(extra=0),
  lambda d: d["palette"].update(text="#FFFFFF"),
  lambda d: d["palette"].update(text="#GGFFFFFF"),
  lambda d: d["layouts"]["large"].update(unknown={}),
  lambda d: d["layouts"]["compact"]["max_speed"].update(x=float("nan")),
  lambda d: d["layouts"]["compact"]["max_speed"].update(y=float("inf")),
  lambda d: d["layouts"]["large"]["current_speed"].update(x=True),
  lambda d: d["layouts"]["large"]["current_speed"].update(enabled=1),
  lambda d: d["layouts"]["large"]["steering_wheel"].update(x=1800),
  lambda d: d["layouts"]["compact"]["speed_limit"].update(y=200),
])
def test_invalid_contract_rejected(change):
  document = default_document()
  change(document)
  with pytest.raises(ValueError):
    validate_document(document)


@pytest.mark.parametrize("raw", [None, b"{", b"\xff", b"x" * (MAX_BYTES + 1), b'{"version":1,"version":1}', b"[" * 1200 + b"]" * 1200])
def test_saved_invalid_or_absent_uses_defaults(raw):
  with patch("openpilot.starpilot.ui.onroad_customization.read_saved", return_value=(raw, True)):
    assert read_customization(Mock()) == default_document()


def test_saved_valid_layouts_survive_independently():
  document = default_document()
  document["layouts"]["large"]["current_speed"].update(x=100, y=120)
  document["layouts"]["compact"]["max_speed"].update(x=180, y=10)
  with patch("openpilot.starpilot.ui.onroad_customization.read_saved", return_value=(json.dumps(document).encode(), True)):
    assert read_customization(Mock()) == document


def test_v3_layout_migrates_wheel_size_without_changing_saved_placement_or_color():
  document = default_document()
  document["version"] = 3
  document["palette"]["text"] = "#ABCDEF80"
  document["layouts"]["large"]["steering_wheel"].update(x=1300, y=100, enabled=False)
  document["layouts"]["compact"]["steering_wheel"].update(x=90, y=150)
  for profile in ("large", "compact"):
    del document["layouts"][profile]["steering_wheel"]["size"]
  migrated = validate_document(document)
  assert migrated["version"] == 4
  assert migrated["palette"] == document["palette"]
  assert migrated["layouts"]["large"]["steering_wheel"] == {"x": 1300, "y": 100, "enabled": False, "size": 192}
  assert migrated["layouts"]["compact"]["steering_wheel"] == {"x": 90, "y": 150, "enabled": True, "size": 50}


@pytest.mark.parametrize("removed", [("driver_monitor", "torque_bar"), ("torque_bar",), ()])
def test_pre_action_saved_layout_migrates_without_losing_positions_or_palette(removed):
  document = default_document()
  document["version"] = 1
  del document["widgetColors"]
  del document["roadColors"]
  document["palette"]["cardFill"] = "#12345678"
  document["layouts"]["large"]["current_speed"].update(x=700, y=120, enabled=False)
  document["layouts"]["large"]["cruise_limits"].update(x=288, y=175, enabled=False)
  document["layouts"]["compact"]["speed_limit"].update(x=300, y=20)
  for key in ("model_confidence", "conditional_mode", "following_distance"):
    del document["layouts"]["compact"][key]
  for layout in document["layouts"].values():
    del layout["speed_limit_actions"]
    del layout["steering_wheel"]["size"]
    for key in removed:
      del layout[key]
  migrated = validate_document(document)
  assert migrated["palette"] == document["palette"]
  for profile in ("large", "compact"):
    for key, position in document["layouts"][profile].items():
      assert migrated["layouts"][profile][key] == {
        **position, **({"size": customization_metadata()["profiles"][profile]["widgets"][key]["width"]}
                     if key == "steering_wheel" else {})}
  assert migrated["layouts"]["large"]["speed_limit_actions"] == {"x": 288, "y": 600, "enabled": False}
  assert migrated["layouts"]["compact"]["speed_limit_actions"] == default_document()["layouts"]["compact"]["speed_limit_actions"]


def test_malformed_pre_action_cruise_placement_is_rejected():
  document = default_document()
  for key in ("model_confidence", "conditional_mode", "following_distance"):
    del document["layouts"]["compact"][key]
  for layout in document["layouts"].values():
    del layout["speed_limit_actions"]
  document["layouts"]["large"]["cruise_limits"]["x"] = "moved"
  with pytest.raises(ValueError, match="Invalid widget placement"):
    validate_document(document)


def test_duplicate_key_cannot_apply_otherwise_valid_placement():
  document = default_document()
  document["layouts"]["large"]["current_speed"]["x"] = 100
  raw = json.dumps(document).replace('"version": 4', '"version": 4, "version": 4').encode()
  with patch("openpilot.starpilot.ui.onroad_customization.read_saved", return_value=(raw, True)):
    assert read_customization(Mock()) == default_document()


def test_wheel_hit_edges_match_default_draw_bounds():
  emit = Mock()
  inputs = OnroadInput(emit)
  state = road(experimental_available=True)
  for x in (1588, 1775, 1780):
    inputs.press(x, 100, state)
    inputs.release(x, 100, state)
  assert emit.call_count == 3
  emit.reset_mock()
  for x in (1580, 1781):
    inputs.press(x, 100, state)
    inputs.release(x, 100, state)
  emit.assert_not_called()


def test_resized_wheel_draw_and_touch_share_large_bounds():
  document = default_document()
  document["layouts"]["large"]["steering_wheel"].update(x=1300, y=100, size=240)
  state = road(document, experimental_available=True)
  assert validate_document(document) == document
  wheel = SteeringWheelWidget.__new__(SteeringWheelWidget)
  wheel._texture = Mock()
  with patch.object(rl, "draw_circle") as circle, patch.object(rl, "draw_texture_pro") as texture:
    wheel.render(rl.Rectangle(30, 30, 1800, 1020), state)
  assert circle.call_args.args[:3] == (1420, 220, 120)
  rect = texture.call_args.args[2]
  assert (rect.x, rect.y, rect.width, rect.height) == (1330, 130, 180, 180)
  emit = Mock()
  inputs = OnroadInput(emit)
  for x, y in ((1300, 100), (1539, 339)):
    inputs.press(x, y, state)
    inputs.release(x, y, state)
  assert emit.call_count == 2
  inputs.press(1541, 339, state)
  inputs.release(1541, 339, state)
  assert emit.call_count == 2


def test_compact_resize_rejects_protected_overlap_and_other_widget_sizes():
  document = default_document()
  document["layouts"]["compact"]["steering_wheel"].update(size=70, y=160)
  assert validate_document(document) == document
  assert widget_size(document, "compact", "steering_wheel") == (70, 70)
  document["layouts"]["compact"]["steering_wheel"].update(x=150, y=170)
  with pytest.raises(ValueError, match="protected"):
    validate_document(document)
  document = default_document()
  document["layouts"]["compact"]["speed_limit_actions"]["size"] = 70
  with pytest.raises(ValueError, match="placement"):
    validate_document(document)


@pytest.mark.parametrize("changed_token", ["new-settings", "new-drive", "new-mode", ""])
def test_wheel_press_cancels_when_action_token_changes(changed_token):
  emit = Mock()
  inputs = OnroadInput(emit)
  state = road(experimental_available=True, experimental_action_token="displayed-action")
  inputs.press(1600, 100, state)
  assert inputs.claimed
  changed = replace(state, experimental_action_token=changed_token)
  inputs.move(1600, 100, changed)
  assert not inputs.claimed
  inputs.release(1600, 100, state)
  emit.assert_not_called()
  inputs.press(1600, 100, state)
  inputs.release(1600, 100, changed)
  emit.assert_not_called()


@pytest.mark.parametrize("enabled,token", [(False, ""), (True, "stable-action")])
def test_moved_wheel_emits_captured_action_token_and_effective_bool(enabled, token):
  document = default_document()
  document["layouts"]["large"]["steering_wheel"].update(x=1300, y=100)
  state = road(document, experimental_available=True, experimental_enabled=enabled, experimental_action_token=token)
  emit = Mock()
  inputs = OnroadInput(emit)
  inputs.press(1310, 110, state)
  inputs.release(1310, 110, replace(state))
  emit.assert_called_once_with(OnroadRequest("set_experimental", not enabled, token))


def test_large_draw_origins_and_wheel_input_move_together():
  document = default_document()
  document["layouts"]["large"]["cruise_limits"].update(x=188, y=95)
  document["layouts"]["large"]["current_speed"].update(x=680, y=70)
  document["layouts"]["large"]["steering_wheel"].update(x=1300, y=100)
  state = road(document, experimental_available=True)
  fonts = NS(measure=lambda *a, **k: NS(width=10, height=20), draw=Mock())
  content = rl.Rectangle(30, 30, 1800, 1020)
  with patch("openpilot.starpilot.ui.onroad_large_widgets.draw_control_card") as card:
    SetSpeedWidget(fonts).render(content, state)
    rect = card.call_args.args[0]
    assert (rect.x, rect.y, rect.width, rect.height) == (188, 95, 176, 196)
  CurrentSpeedHud(fonts).render(content, state)
  assert fonts.draw.call_args_list[-2].args[3:5] == (965, 112)
  wheel = SteeringWheelWidget.__new__(SteeringWheelWidget)
  wheel._texture = Mock()
  with patch.object(rl, "draw_circle") as circle, patch.object(rl, "draw_texture_pro"):
    wheel.render(content, state)
    assert circle.call_args.args[:3] == (1396, 196, 96)
  emit = Mock()
  inputs = OnroadInput(emit)
  inputs.press(1310, 110, state)
  inputs.release(1310, 110, state)
  emit.assert_called_once()
  emit.reset_mock()
  inputs.press(1600, 80, state)
  inputs.release(1600, 80, state)
  emit.assert_not_called()

  document["layouts"]["large"]["steering_wheel"]["enabled"] = False
  inputs.press(1310, 110, state)
  inputs.release(1310, 110, state)
  emit.assert_not_called()


def test_speed_limit_actions_move_independently_of_cruise_card_and_keep_touch_priority():
  document = default_document()
  document["layouts"]["large"]["cruise_limits"].update(x=288, y=175)
  document["layouts"]["large"]["speed_limit_actions"].update(x=388, y=600)
  observation = SpeedLimitObservation(kind=ObservationKind.VALID, speed_limit_mps=20,
                                     pending_speed_limit_mps=15, session_id="drive", decision_id=1,
                                     presentation_id=2, action_enabled=True)
  state = road(document, speed_limit=observation, longitudinal_active=True, slc_system_long_available=True)
  controls = slc_controls(Profile.LARGE, state)
  assert controls[0].bounds == (388, 600, 472, 658)
  assert slc_controls(Profile.COMPACT, state)[0].bounds == (174, 180, 310, 234)
  emit = Mock()
  inputs = OnroadInput(emit)
  for x, y in ((400, 610), (300, 400)):
    inputs.press(x, y, state)
    inputs.release(x, y, state)
  assert emit.call_count == 2
  assert not slc_controls(Profile.LARGE, replace(state, alert=OnroadAlert(size=AlertSize.FULL)))
  document["layouts"]["large"]["cruise_limits"]["enabled"] = False
  assert slc_controls(Profile.LARGE, state) == controls
  emit.reset_mock()
  inputs.press(300, 400, state)
  inputs.release(300, 400, state)
  emit.assert_not_called()
  document["layouts"]["large"]["speed_limit_actions"]["enabled"] = False
  assert not slc_controls(Profile.LARGE, state)


def test_moved_compact_actions_relocate_hitboxes_without_weakening_state_gate():
  document = default_document()
  document["layouts"]["compact"]["speed_limit_actions"].update(x=174, y=100)
  document["layouts"]["compact"]["speed_limit"]["enabled"] = False
  assert validate_document(document) == document
  document["layouts"]["compact"]["speed_limit_actions"].update(x=100, y=180)
  document = validate_document(document)
  observation = SpeedLimitObservation(kind=ObservationKind.VALID, speed_limit_mps=20,
                                     pending_speed_limit_mps=15, session_id="drive", decision_id=1,
                                     presentation_id=2, action_enabled=True)
  state = road(document, speed_limit=observation, longitudinal_active=True, slc_system_long_available=True)
  assert slc_controls(Profile.COMPACT, state)[0].bounds == (100, 180, 236, 234)
  emit = Mock()
  inputs = OnroadInput(emit, Profile.COMPACT)
  inputs.press(110, 200, state)
  inputs.release(110, 200, state)
  assert emit.call_count == 1
  inputs.press(400, 200, state)
  inputs.release(400, 200, state)
  assert emit.call_count == 1
  assert not slc_controls(Profile.COMPACT, replace(state, alert=OnroadAlert(size=AlertSize.FULL)))


def test_frozen_default_draw_geometry_and_neutral_colors():
  state = road()
  fonts = NS(measure=lambda *a, **k: NS(width=10, height=20), draw=Mock())
  content = rl.Rectangle(30, 30, 1800, 1020)
  with patch("openpilot.starpilot.ui.onroad_large_widgets.draw_control_card") as card:
    SetSpeedWidget(fonts).render(content, state)
    rect = card.call_args.args[0]
    assert (rect.x, rect.y, rect.width, rect.height) == (88, 75, 176, 196)
    fill, border = card.call_args.kwargs["fill"], card.call_args.kwargs["border"]
    assert (fill.r, fill.g, fill.b, fill.a) == (0, 0, 0, 166)
    assert (border.r, border.g, border.b, border.a) == (196, 205, 208, 180)
  CurrentSpeedHud(fonts).render(content, state)
  assert fonts.draw.call_args_list[-2].args[3:5] == (925, 72)
  assert fonts.draw.call_args_list[-1].args[3:5] == (925, 280)
  wheel = SteeringWheelWidget.__new__(SteeringWheelWidget)
  wheel._texture = Mock()
  with patch.object(rl, "draw_circle") as circle, patch.object(rl, "draw_texture_pro"):
    wheel.render(content, state)
    assert circle.call_args.args[:3] == (1684, 171, 96)


@pytest.mark.parametrize("speed,size", [(65, 50), (105, 42)])
def test_compact_us_sign_keeps_camera_visible_at_saved_position(speed, size):
  document = default_document()
  document["layouts"]["compact"]["speed_limit"].update(x=300, y=30)
  state = road(document, metric=True, speed_limit=SpeedLimitObservation(
    kind=ObservationKind.VALID, speed_limit_mps=speed / 3.6))
  state = replace(state, appearance=replace(state.appearance, show_speed_limit_sign=True))
  fonts = NS(measure=lambda *a, **k: NS(width=10, height=20), draw=Mock())
  hud = CompactHudRenderer(fonts, Mock())
  with patch.object(rl, "draw_rectangle_rounded") as fill, \
       patch.object(rl, "draw_rectangle_rounded_lines_ex") as outline:
    hud._speed_limit_sign(state)
  fill.assert_not_called()
  rect = outline.call_args.args[0]
  assert (rect.x, rect.y, rect.width, rect.height) == (310, 38, 100, 116)
  assert outline.call_args.args[3] == 2
  assert [(call.args[0], call.args[2]) for call in fonts.draw.call_args_list] == [("SPEED", 20), ("LIMIT", 20), (str(speed), size)]
  for color in [outline.call_args.args[-1], *(call.args[-1] for call in fonts.draw.call_args_list)]:
    assert tuple(getattr(color, channel) for channel in ("r", "g", "b", "a")) == rl.WHITE


def test_compact_drag_keeps_animation_state_and_separate_origins():
  document = default_document()
  document["layouts"]["compact"]["max_speed"].update(x=100, y=10)
  document["layouts"]["compact"]["steering_wheel"].update(x=90, y=150)
  fonts = NS(draw=Mock())
  hud = CompactHudRenderer(fonts, Mock())
  hud._wheel = Mock()
  state = road(document, lateral_active=True, longitudinal_active=True)
  state = replace(state, appearance=replace(state.appearance, hide_max_speed=True, hide_steering_wheel=True))
  with patch.object(hud, "_speed_limit_sign"), patch.object(rl, "draw_circle_gradient"), patch.object(rl, "draw_texture_pro") as wheel:
    hud.render(state)
    hud.render(state)
    assert fonts.draw.call_args_list[-2].args[3:5] == (117, 6)
    rect = wheel.call_args.args[2]
    assert (rect.x, rect.y) == (115, 175)
    alpha = hud._set_speed_alpha.x
    document["layouts"]["compact"]["max_speed"]["enabled"] = False
    document["layouts"]["compact"]["steering_wheel"]["enabled"] = False
    fonts.draw.reset_mock()
    wheel.reset_mock()
    hud.render(state)
    assert hud._set_speed_alpha.x > alpha
    fonts.draw.assert_not_called()
    wheel.assert_not_called()


def test_saved_six_widget_layout_adds_only_default_rail_positions():
  document = default_document()
  for key in ("model_confidence", "conditional_mode", "following_distance"):
    del document["layouts"]["compact"][key]
  document["layouts"]["compact"]["speed_limit_actions"].update(x=100, enabled=False)
  document["palette"]["text"] = "#ABCD1234"
  migrated = validate_document(document)
  assert migrated["palette"] == document["palette"]
  for profile, layout in document["layouts"].items():
    for key, value in layout.items():
      assert migrated["layouts"][profile][key] == value
  assert migrated["layouts"]["compact"]["conditional_mode"] == {"x": 476, "y": 80, "enabled": True}
  assert "conditional_mode" not in document["layouts"]["compact"]


def test_movable_rail_keeps_limits_and_does_not_cover_active_alerts():
  from openpilot.starpilot.ui.onroad_compact_widgets import MiciSidebarWidgets
  document = default_document()
  document["layouts"]["compact"]["model_confidence"].update(x=200, y=50, enabled=False)
  document["layouts"]["compact"]["conditional_mode"].update(x=260, y=90)
  assert validate_document(document) == document
  widget = MiciSidebarWidgets(Mock())
  widget._confidence_ball, widget._conditional, widget._personality = Mock(), Mock(), Mock()
  with patch.object(rl, "draw_rectangle"):
    widget.render(rl.Rectangle(0, 0, 536, 240), road(document))
    widget._confidence_ball.assert_not_called()
    assert tuple(getattr(widget._conditional.call_args.args[0], name) for name in ("x", "y", "width", "height")) == (260, 90, 60, 80)
    assert tuple(getattr(widget._personality.call_args.args[0], name) for name in ("x", "y", "width", "height")) == (476, 160, 60, 80)
    widget._conditional.reset_mock()
    widget.render(rl.Rectangle(0, 0, 536, 240), road(document, alert=OnroadAlert(size=AlertSize.FULL)))
    widget._conditional.assert_not_called()
  document["layouts"]["compact"]["conditional_mode"].update(x=200, y=101)
  with pytest.raises(ValueError, match="protected"):
    validate_document(document)
  document["layouts"]["compact"]["conditional_mode"].update(x=477, y=0)
  with pytest.raises(ValueError, match="bounds"):
    validate_document(document)


def test_v1_palette_positions_and_visibility_migrate_without_mutating_source():
  import copy

  old = default_document()
  old['version'] = 1
  del old['widgetColors']
  del old['roadColors']
  old['palette'].update(cardFill='#12345678', text='#AABBCCDD')
  old['layouts']['large']['current_speed'].update(x=600.5, y=100.25, enabled=False)
  old['layouts']['compact']['following_distance'].update(x=400, y=80)
  for layout in old['layouts'].values():
    del layout['steering_wheel']['size']
  original = copy.deepcopy(old)
  result = decode_document(json.dumps(old).encode())
  assert old == original
  assert result['version'] == 4
  assert result['palette'] == old['palette']
  for profile, layout in old['layouts'].items():
    for key, position in layout.items():
      assert result['layouts'][profile][key] == {
        **position, **({'size': customization_metadata()['profiles'][profile]['widgets'][key]['width']}
                     if key == 'steering_wheel' else {})}
  assert result['widgetColors'] == {'large': {}, 'compact': {}}
  assert rgba(result, 'text', 'large', 'current_speed') == (170, 187, 204, 221)
  assert rgba(result, 'cardFill', 'compact', 'following_distance') == (0, 0, 0, 0)


@pytest.mark.parametrize('colors', [
  {'large': {}}, {'large': {}, 'compact': [], 'extra': {}},
  {'large': {'unknown': {}}, 'compact': {}},
  {'large': {'current_speed': {'cardFill': '#FFFFFFFF'}}, 'compact': {}},
  {'large': {}, 'compact': {'torque_bar': {'text': '#FFFFFFFF'}}},
  {'large': {'current_speed': {'text': 123}}, 'compact': {}},
  {'large': {'current_speed': {'text': '#FFFFFF'}}, 'compact': {}},
])
def test_unsupported_widget_colors_are_rejected(colors):
  document = default_document()
  document['widgetColors'] = colors
  with pytest.raises(ValueError):
    validate_document(document)


def test_widget_color_isolation_and_native_text_resolution():
  document = default_document()
  document['palette']['text'] = '#10203040'
  document['widgetColors']['large']['current_speed'] = {'text': '#aabbccdd'}
  document['widgetColors']['compact']['following_distance'] = {'cardFill': '#12345678', 'text': '#ABCDEF80'}
  validated = validate_document(document)
  assert rgba(validated, 'text', 'large', 'current_speed') == (170, 187, 204, 221)
  assert rgba(validated, 'text', 'compact', 'max_speed') == (16, 32, 48, 64)
  assert rgba(validated, 'text', 'large', 'cruise_limits') == (16, 32, 48, 64)
  assert widget_palette(validated, 'compact', 'conditional_mode')['cardFill'] == '#00000000'
  fonts = NS(measure=lambda *a, **k: NS(width=10, height=20), draw=Mock())
  CurrentSpeedHud(fonts).render(rl.Rectangle(30, 30, 1800, 1020), road(validated))
  actual = fonts.draw.call_args_list[0].args[-1]
  assert (actual.r, actual.g, actual.b, actual.a) == (170, 187, 204, 221)


def test_unsaved_color_changes_replace_values_and_restore_palette_fallback():
  document = default_document()
  for profile, widget in (("large", "current_speed"), ("compact", "max_speed")):
    assert rgba(document, "text", profile, widget) == (255, 255, 255, 255)
    document["palette"]["text"] = "#10203040"
    assert rgba(document, "text", profile, widget) == (16, 32, 48, 64)
    document["widgetColors"][profile][widget] = {"text": "#aabbccdd"}
    assert rgba(document, "text", profile, widget) == (170, 187, 204, 221)
    document["widgetColors"][profile][widget]["text"] = "#01020304"
    assert rgba(document, "text", profile, widget) == (1, 2, 3, 4)
    del document["widgetColors"][profile][widget]
    assert rgba(document, "text", profile, widget) == (16, 32, 48, 64)
    document["palette"]["text"] = "#FFFFFFFF"


def test_transparent_widget_frames_add_no_default_draw_calls():
  from openpilot.starpilot.ui.onroad_widget_style import draw_widget_frame

  document = default_document()
  with patch.object(rl, 'draw_rectangle_rounded') as fill, patch.object(rl, 'draw_rectangle_rounded_lines_ex') as border:
    for profile, widgets in (('compact', ('driver_monitor', 'model_confidence', 'conditional_mode', 'following_distance')),
                             ('large', ('driver_monitor',))):
      for widget in widgets:
        draw_widget_frame(rl.Rectangle(10, 20, 60, 80), document, profile, widget)
    fill.assert_not_called()
    border.assert_not_called()
    document['widgetColors']['compact']['conditional_mode'] = {'cardFill': '#12345678', 'cardBorder': '#ABCDEF90'}
    draw_widget_frame(rl.Rectangle(200, 80, 60, 80), document, 'compact', 'conditional_mode')
    color = fill.call_args.args[-1]
    assert (color.r, color.g, color.b, color.a) == (18, 52, 86, 120)
    color = border.call_args.args[-1]
    assert (color.r, color.g, color.b, color.a) == (171, 205, 239, 144)


def test_colored_slc_controls_retain_requests_and_touch_bounds():
  from openpilot.starpilot.ui.onroad import OnroadView

  document = default_document()
  state = road(document, slc_system_long_available=True, longitudinal_active=True,
               speed_limit=SpeedLimitObservation(kind=ObservationKind.VALID, speed_limit_mps=20,
                 pending_speed_limit_mps=22, decision_id=1, presentation_id=2,
                 session_id='session', action_enabled=True))
  # Compare the actual owner-produced controls before and after presentation edits.
  before = slc_controls(Profile.COMPACT, state)
  document['widgetColors']['compact']['speed_limit_actions'] = {
    'cardFill': '#12345678', 'cardBorder': '#ABCDEF90', 'text': '#FEDCBAFF'}
  assert slc_controls(Profile.COMPACT, state) == before
  assert before
  fonts = NS(profile=Profile.COMPACT, measure=lambda *a, **k: NS(width=10, height=20), draw=Mock())
  view = OnroadView.__new__(OnroadView)
  view.fonts = fonts
  with patch.object(rl, 'draw_rectangle_rounded') as fill, patch.object(rl, 'draw_rectangle_rounded_lines_ex'):
    view._slc_actions(state)
  color = fill.call_args.args[-1]
  assert (color.r, color.g, color.b, color.a) == (18, 52, 86, 120)
  color = fonts.draw.call_args.args[-1]
  assert (color.r, color.g, color.b, color.a) == (254, 220, 186, 255)


def test_driver_frame_matches_native_preview_and_keeps_face_renderer_separate():
  from openpilot.starpilot.ui.layout_preview_renderer import _DriverMonitorArt
  from openpilot.starpilot.ui.onroad_dm import DriverMonitorLayer

  document = default_document()
  document['layouts']['compact']['driver_monitor'].update(x=90, y=40)
  document['widgetColors']['compact']['driver_monitor'] = {'cardFill': '#AABBCC80'}
  state = road(document)
  live = DriverMonitorLayer.__new__(DriverMonitorLayer)
  live.profile = Profile.COMPACT
  live.renderer = NS(set_should_draw=Mock(), set_position=Mock(), _rect=object(),
                     _fade_filter=NS(update=Mock()), _render=Mock())
  preview = _DriverMonitorArt.__new__(_DriverMonitorArt)
  preview.profile = Profile.COMPACT
  preview.renderer = NS(_render=Mock())
  with patch('openpilot.starpilot.ui.onroad_dm.draw_widget_frame') as live_frame, \
       patch('openpilot.starpilot.ui.layout_preview_renderer.draw_widget_frame') as preview_frame:
    live.render(state, monitor=None, driver=None, fresh=False, onroad=True)
    preview.render(rl.Rectangle(0, 0, 536, 240), state)
  assert live_frame.call_args.args[1:] == preview_frame.call_args.args[1:]
  live_rect, preview_rect = live_frame.call_args.args[0], preview_frame.call_args.args[0]
  assert tuple(getattr(live_rect, key) for key in ('x', 'y', 'width', 'height')) == \
    tuple(getattr(preview_rect, key) for key in ('x', 'y', 'width', 'height')) == (90, 40, 60, 60)
  live.renderer._fade_filter.update.assert_called_once_with(0.35)
  live.renderer._render.assert_called_once()
  preview.renderer._render.assert_called_once()


@pytest.mark.parametrize("enabled", [True, False])
def test_intentional_small_sign_action_overlap_roundtrips_and_large_is_independent(enabled):
  from openpilot.starpilot.ui.onroad_state import compact_sign_obscured_by_actions
  document = default_document()
  large = json.loads(json.dumps(document["layouts"]["large"]))
  document["layouts"]["compact"]["speed_limit"].update(x=330, y=108, enabled=enabled)
  assert decode_document(json.dumps(validate_document(document))) == document
  document["layouts"]["compact"]["speed_limit_actions"].update(x=174, y=100)
  assert validate_document(document) == document
  assert document["layouts"]["large"] == large
  observation = SpeedLimitObservation(kind=ObservationKind.VALID, speed_limit_mps=20,
                                     pending_speed_limit_mps=15, session_id="drive", decision_id=1,
                                     presentation_id=2, action_enabled=True)
  state = road(document, speed_limit=observation, longitudinal_active=True, slc_system_long_available=True)
  assert compact_sign_obscured_by_actions(state)
  for change in ({"longitudinal_active": False}, {"alert": OnroadAlert(size=AlertSize.FULL)},
                 {"speed_limit": replace(observation, pending_speed_limit_mps=None)}):
    assert not compact_sign_obscured_by_actions(replace(state, **change))


def test_saved_small_actions_near_top_preserve_anchor_and_header_stays_visible():
  from openpilot.starpilot.ui.onroad import OnroadView
  document = default_document()
  document["layouts"]["compact"]["speed_limit_actions"].update(x=174, y=0)
  assert decode_document(json.dumps(document)) == document
  observation = SpeedLimitObservation(kind=ObservationKind.VALID, speed_limit_mps=20,
                                     pending_speed_limit_mps=15, session_id="drive", decision_id=1,
                                     presentation_id=2, action_enabled=True)
  state = road(document, speed_limit=observation, longitudinal_active=True, slc_system_long_available=True)
  view = OnroadView.__new__(OnroadView)
  view.fonts = NS(profile=Profile.COMPACT, measure=lambda *a, **k: NS(width=10, height=20), draw=Mock())
  with patch.object(rl, "draw_rectangle_rounded"), patch.object(rl, "draw_rectangle_rounded_lines_ex"):
    view._slc_actions(state)
  assert view.fonts.draw.call_args_list[0].args[4] == 62
  assert slc_controls(Profile.COMPACT, state)[0].bounds == (174, 0, 310, 54)


def test_overlapping_small_sign_restores_after_pending_and_actions_keep_exact_input():
  from openpilot.starpilot.ui.onroad_state import SlcActionKind
  document = default_document()
  document["layouts"]["compact"]["speed_limit"].update(y=108)
  observation = SpeedLimitObservation(kind=ObservationKind.VALID, speed_limit_mps=20,
                                     pending_speed_limit_mps=15, session_id="drive", decision_id=1,
                                     presentation_id=2, action_enabled=True)
  state = road(document, speed_limit=observation, longitudinal_active=True, slc_system_long_available=True)
  fonts = NS(measure=lambda *a, **k: NS(width=10, height=20), draw=Mock())
  hud = CompactHudRenderer(fonts, Mock())
  state = replace(state, appearance=replace(state.appearance, show_speed_limit_sign=True))
  hud._speed_limit_sign(state)
  fonts.draw.assert_not_called()
  with patch.object(rl, "draw_rectangle_rounded"), patch.object(rl, "draw_rectangle_rounded_lines_ex"):
    hud._speed_limit_sign(replace(state, speed_limit=replace(observation, pending_speed_limit_mps=None)))
  assert fonts.draw.called
  emit = Mock()
  inputs = OnroadInput(emit, Profile.COMPACT)
  for x, kind in ((200, SlcActionKind.ACCEPT), (350, SlcActionKind.REJECT)):
    emit.reset_mock()
    inputs.press(x, 200, state)
    inputs.release(x, 200, state)
    inputs.release(x, 200, state)
    emit.assert_called_once()
    assert emit.call_args.args[0].kind == kind
