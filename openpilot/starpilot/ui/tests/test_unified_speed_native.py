"""One set speed and a shared, latest-limit sign in the large and compact UIs."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pyray as rl
import pytest

from openpilot.starpilot.ui.onroad_compact_widgets import CompactHudRenderer
from openpilot.starpilot.ui.onroad_large_widgets import UnifiedSpeedWidget
from openpilot.starpilot.ui.onroad import OnroadView
from openpilot.starpilot.ui.onroad_state import ObservationKind, OnroadState, SpeedLimitObservation, slc_controls
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.speed_limit_widget import INK, MUTED, SpeedLimitWidget, draw_text
from openpilot.starpilot.ui.speed_limit_shapes import SpeedLimitShapes
from openpilot.starpilot.ui.unified_speed_presentation import displayed_limit_mps, resolve_unified_speed


@pytest.fixture(autouse=True)
def drawing(monkeypatch):
  calls = {}
  for name in ('draw_rectangle_rounded_lines_ex', 'draw_rectangle_rounded', 'draw_line_ex', 'draw_circle', 'draw_ring', 'draw_circle_gradient'):
    calls[name] = Mock()
    monkeypatch.setattr(rl, name, calls[name])
  for name in ('circle', 'arrow'):
    calls[name] = Mock()
    monkeypatch.setattr(SpeedLimitShapes, name, calls[name])
  monkeypatch.setattr('openpilot.starpilot.ui.onroad_large_widgets.draw_control_card', Mock())
  return calls


def state(**changes):
  observation = SpeedLimitObservation(ObservationKind.VALID, 'map', 50 / 3.6,
    accepted_speed_limit_mps=40 / 3.6, accepted_adjusted_limit_mps=45 / 3.6,
    pending_speed_limit_mps=50 / 3.6, pending_adjusted_limit_mps=55 / 3.6,
    presentation_adjusted_limit_mps=55 / 3.6, accepted_source='dashboard', action_enabled=True,
    session_id='drive', presentation_id=2, decision_id=1, pending_since_ns=10_000_000_000)
  return replace(OnroadState(True, False, 45 / 3.6, 100., observation, metric=True, longitudinal_active=True,
                              observed_ns=10_000_000_000), **changes)


def fonts(profile=Profile.LARGE):
  return SimpleNamespace(profile=profile, draw=Mock(), vertical_ink=lambda text, role, size: (0, size * .75),
                         horizontal_ink=lambda text, role, size: (0, len(text) * size * .5),
                         measure=lambda text, role, size: SimpleNamespace(width=len(text) * size * .5, height=size))


@pytest.mark.parametrize('headless', [False, True])
def test_speed_limit_widget_forwards_fonts_context(monkeypatch, headless):
  font = fonts()
  if headless:
    font._headless_context = True
  shapes = Mock()
  monkeypatch.setattr('openpilot.starpilot.ui.speed_limit_widget.SpeedLimitShapes', shapes)
  widget = SpeedLimitWidget(font, Profile.LARGE)
  shapes.assert_called_once_with(widget.scale, headless_context=headless)
  widget.close()
  shapes.return_value.close.assert_called_once_with()


def foreground_calls(draw):
  return [call for call in draw.call_args_list if (call.args[-1].r, call.args[-1].g, call.args[-1].b) not in ((6, 14, 10), (7, 16, 12))]


def rgba_tuple(color):
  return (color.r, color.g, color.b, color.a)


def test_latest_limit_and_offset_replace_accepted_sign_while_waiting():
  shown = resolve_unified_speed(state())
  assert (shown.max_text, shown.posted_text, shown.offset_text, shown.source) == ('100', '50', '+5', 'map')
  assert displayed_limit_mps(state().speed_limit) == 50 / 3.6


@pytest.mark.parametrize('profile', list(Profile))
def test_both_renderers_show_small_latest_sign_and_offset(profile):
  font = fonts(profile)
  current = state()
  if profile == Profile.LARGE:
    UnifiedSpeedWidget(font).render(rl.Rectangle(30, 30, 1800, 1020), current)
    texts = [call.args[0] for call in foreground_calls(font.draw)]
    assert texts.count('100') == 1
    assert 'SET' in texts
    assert 'SLC LIMIT' not in texts
  else:
    CompactHudRenderer(font, Mock())._speed_limit_sign(current)
  texts = [call.args[0] for call in foreground_calls(font.draw)]
  assert '50' in texts and '+5' in texts and '40' not in texts


@pytest.mark.parametrize('metric', [False, True])
@pytest.mark.parametrize('vienna', [False, True])
@pytest.mark.parametrize('offset', [None, 0., .01, -.01])
def test_compact_sign_omits_missing_zero_and_rounded_zero_offsets(metric, vienna, offset):
  current = state(metric=metric)
  factor = 3.6 if metric else 2.2369362921
  current = replace(current, appearance=replace(current.appearance, use_vienna_sign=vienna),
    speed_limit=SpeedLimitObservation(ObservationKind.VALID, 'map', 65 / factor, offset_mps=offset,
                                    action_enabled=True))
  assert resolve_unified_speed(current).offset_text is None
  font = fonts(Profile.COMPACT)
  CompactHudRenderer(font, Mock())._speed_limit_sign(current)
  assert [call.args[0] for call in font.draw.call_args_list] == (['65'] if vienna else ['SPEED', 'LIMIT', '65'])


@pytest.mark.parametrize('profile', list(Profile))
@pytest.mark.parametrize('vienna', [False, True])
def test_pending_sign_pulses_in_place_and_arrow_follows_vehicle_speed(profile, vienna, drawing):
  font = fonts(profile)
  sign = SpeedLimitWidget(font, profile)
  current = state()
  current = replace(current, appearance=replace(current.appearance, use_vienna_sign=vienna))
  sign.render(current)
  before = {call.args[0]: call.args for call in foreground_calls(font.draw)}
  assert drawing['arrow'].call_args.args[3] == -1
  sign.render(replace(current, observed_ns=10_350_000_000, speed_mps=60 / 3.6))
  after = {call.args[0]: call.args for call in foreground_calls(font.draw)}
  assert all(after[text][3:5] == args[3:5] for text, args in before.items())
  if vienna:
    assert rgba_tuple(after['50'][-1]) == (0, 0, 0, 255)
    assert drawing['circle'].call_args.args[:2] == ((389, 87) if profile == Profile.COMPACT else (328.05, 138.65))
    assert rgba_tuple(drawing['circle'].call_args.args[-1]) == (170, 115, 235, 255)
  else:
    assert rgba_tuple(after['50'][-1]) == (170, 115, 235, 255)
    assert rgba_tuple(before['LIMIT'][-1]) == (244, 247, 245, 255)
    assert rgba_tuple(after['LIMIT'][-1]) == (170, 115, 235, 255)
  assert drawing['arrow'].call_args.args[3] == 1


@pytest.mark.parametrize('reason', ['steady', 'automatic', 'equal_speed', 'unknown_speed'])
def test_compact_us_heading_stays_centered_without_an_arrow(reason, drawing):
  current = state()
  if reason == 'steady':
    current = replace(current, speed_limit=replace(current.speed_limit, pending_speed_limit_mps=None))
  elif reason == 'automatic':
    current = replace(current, speed_limit=replace(current.speed_limit, automatic_adoption_pending=True))
  else:
    current = replace(current, speed_mps=55 / 3.6 if reason == 'equal_speed' else None)
  font = fonts(Profile.COMPACT)
  SpeedLimitWidget(font, Profile.COMPACT).render(current)
  drawing['arrow'].assert_not_called()
  for call in font.draw.call_args_list:
    text, role, size, x, _, _ = call.args
    left, right = font.horizontal_ink(text, role, size)
    assert x + (left + right) / 2 == 390


@pytest.mark.parametrize('profile', list(Profile))
def test_only_set_speed_override_draws_cross(profile, drawing):
  sign = SpeedLimitWidget(fonts(profile), profile)
  current = state()
  current = replace(current, speed_limit=replace(current.speed_limit, pending_speed_limit_mps=None))
  sign.render(replace(current, longitudinal_overridden=True))
  assert drawing['draw_line_ex'].call_count == 0
  sign.render(replace(current, speed_limit=replace(current.speed_limit, driver_override_active=True)))
  assert len(foreground_calls(drawing['draw_line_ex'])) == 2


def test_compact_set_speed_fades_after_adjustment_and_reappears_on_change():
  renderer = CompactHudRenderer(fonts(), Mock())
  current = state(drive_frame=1)
  for now in range(10_000_000_000, 20_000_000_000, 100_000_000):
    alpha = renderer._set_speed_opacity(current, now)
  assert alpha < .01
  changed = replace(current, cruise_kph=current.cruise_kph + 10)
  assert renderer._set_speed_opacity(changed, 20_000_000_000) < .01
  assert renderer._set_speed_opacity(changed, 20_020_000_000) > .01
  assert renderer._set_speed_opacity(replace(current, longitudinal_active=False), 20_000_000_000) == 0


def test_compact_max_restores_dinish_number_label_and_shadow(drawing):
  from openpilot.starpilot.ui.presentation import FontRole, font_filename
  font = fonts(Profile.COMPACT)
  hud = CompactHudRenderer(font, Mock())
  current = state(drive_frame=1, cruise_kph=80)
  hud.render_max_speed(current)
  hud.render_max_speed(replace(current, observed_ns=current.observed_ns + 20_000_000))
  assert [(call.args[0], call.args[1]) for call in font.draw.call_args_list] == [
    ('80', FontRole.SET_SPEED), ('MAX', FontRole.SEMI_BOLD)]
  assert font_filename(Profile.COMPACT, FontRole.SET_SPEED) == 'DINish-Speed.fnt'
  assert font.draw.call_args_list[0].args[3:5] == (17, -4)
  assert font.draw.call_args_list[1].args[2:5] == (36, 25, 109)
  drawing['draw_circle_gradient'].assert_called_once()


def test_large_limit_keeps_a_unit_when_set_speed_is_hidden():
  profile = Profile.LARGE
  current = state()
  current.customization['showMaxSpeed'] = False
  current.customization['layouts']['compact']['max_speed']['enabled'] = False
  font = fonts(profile)
  UnifiedSpeedWidget(font).render(rl.Rectangle(30, 30, 1800, 1020), current)
  assert [call.args[0] for call in foreground_calls(font.draw)].count('km/h') == 1


@pytest.mark.parametrize('profile', list(Profile))
def test_actions_have_only_fixed_size_words_divider_and_pressed_underline(profile, drawing):
  from openpilot.starpilot.ui.large_speed_geometry import ACTION_TEXT
  view = OnroadView.__new__(OnroadView)
  view.fonts = fonts(profile)
  current = state(slc_prompt_open=True)
  view._slc_actions(current)
  assert [(call.args[0], call.args[2]) for call in foreground_calls(view.fonts.draw)] == [
    ('Accept', ACTION_TEXT[profile][0]), ('Decline', ACTION_TEXT[profile][0])]
  assert len(foreground_calls(drawing['draw_line_ex'])) == 1
  view.pressed_action = lambda: slc_controls(profile, current)[0].request
  drawing['draw_line_ex'].reset_mock()
  view._slc_actions(current)
  assert len(foreground_calls(drawing['draw_line_ex'])) == 2
  drawing['draw_rectangle_rounded'].assert_not_called()
  drawing['draw_rectangle_rounded_lines_ex'].assert_not_called()


@pytest.mark.parametrize('profile', list(Profile))
@pytest.mark.parametrize('alpha', [96, 255])
def test_text_contour_is_bounded_and_preserves_foreground_opacity(profile, alpha):
  from openpilot.starpilot.ui.presentation import FontRole
  font = fonts(profile)
  color = rl.Color(188, 132, 255, alpha)
  draw_text(font, '65 +5', FontRole.MEDIUM, 36, 100, 50, color)
  calls = [call.args for call in font.draw.call_args_list]
  assert len(calls) == 6
  assert all(call[:3] == ('65 +5', FontRole.MEDIUM, 36) for call in calls)
  assert calls[-1][3:5] == (100, 50) and calls[-1][-1] is color
  radius = 1.15 if profile == Profile.LARGE else 1.
  assert {(round(call[3]-100, 2), round(call[4]-50, 2)) for call in calls[:4]} == {
    (-radius, 0), (radius, 0), (0, -radius), (0, radius)}
  assert all(call[-1].a == round(alpha*.90) for call in calls[:4])
  assert calls[-2][3:5] == (100, 50+(1.5 if profile == Profile.LARGE else 1.2))
  assert calls[-2][-1].a == round(alpha*.32)


def test_full_coverage_contour_protects_base_muted_and_peak_purple_on_white():
  from openpilot.starpilot.ui.presentation import FontRole
  def luminance(channels):
    linear = [((x/255+.055)/1.055)**2.4 if x/255 > .04045 else x/255/12.92 for x in channels]
    return sum(x*weight for x, weight in zip(linear, (.2126, .7152, .0722), strict=True))
  for color in (INK, MUTED, rl.Color(188, 132, 255, 255), rl.Color(170, 115, 235, 255)):
    font = fonts()
    draw_text(font, '65', FontRole.BOLD, 70, 100, 50, color)
    contour = font.draw.call_args_list[0].args[-1]
    background = [value*contour.a/255+255-contour.a for value in (contour.r, contour.g, contour.b)]
    assert (luminance((color.r, color.g, color.b))+.05)/(luminance(background)+.05) >= 4.5


def test_contour_accepts_raylib_standard_color_tuples():
  from openpilot.starpilot.ui.presentation import FontRole
  font = fonts()
  draw_text(font, 'Dash', FontRole.NORMAL, 22, 100, 50, rl.WHITE)
  color = font.draw.call_args.args[-1]
  assert (color.r, color.g, color.b, color.a) == (255, 255, 255, 255)


def test_retained_compact_fade_still_validates_before_decoding(tmp_path, monkeypatch):
  from openpilot.starpilot.ui.onroad import _load_fade
  directory = Path(__file__).parents[3] / 'selfdrive/assets'
  path = directory / 'icons_mici/onroad/onroad_fade.png'
  decoder = Mock(return_value=SimpleNamespace(id=1))
  monkeypatch.setattr(rl, 'load_texture', decoder)
  assert _load_fade(path) is decoder.return_value
  decoder.reset_mock()
  invalid = tmp_path / path.name
  invalid.write_bytes(b'invalid PNG')
  with pytest.raises(ValueError, match='Unreviewed'):
    _load_fade(invalid)
  decoder.assert_not_called()
