from dataclasses import replace
from unittest.mock import Mock, patch

import pyray as rl
import pytest

from openpilot.starpilot.ui.onroad_compact_widgets import CompactHudRenderer
from openpilot.starpilot.ui.onroad_large_widgets import UnifiedSpeedWidget
from openpilot.starpilot.ui.onroad_state import ObservationKind, OnroadState, SpeedLimitObservation
from openpilot.starpilot.ui.speed_limit_pulse import SpeedLimitPulse


def state(limit=15.6464, source="vision", **changes):
  observation = SpeedLimitObservation(kind=ObservationKind.VALID, source=source, speed_limit_mps=limit)
  return replace(OnroadState(True, True, 10., 80., observation, drive_frame=1), **changes)


def rgba(color):
  return tuple(color) if isinstance(color, tuple) else (color.r, color.g, color.b, color.a)


@pytest.mark.parametrize("metric", [False, True])
def test_changed_vision_number_pulses_once_with_original_one_second_easing(metric):
  pulse = SpeedLimitPulse()
  current = state(metric=metric)
  pulse.update(current, 10.)
  assert rgba(pulse.color(rl.WHITE, 10.)) == rgba(rl.WHITE)
  assert rgba(pulse.color(rl.WHITE, 10.5)) == (188, 132, 255, 255)
  assert rgba(pulse.color(rl.WHITE, 11.)) == rgba(rl.WHITE)
  for frame in range(100):
    pulse.update(state(15.6464 + (frame % 2) * .01, metric=metric), 11. + frame / 20)
    assert pulse.start_time == 10.
  pulse.update(state(13.4112, metric=metric), 20.)
  assert pulse.start_time == 20.


def test_source_reacquisition_missing_hidden_and_units_do_not_retrigger_same_number():
  pulse = SpeedLimitPulse()
  pulse.update(state(source="map"), 0.)
  pulse.update(state(), 1.)
  assert rgba(pulse.color(rl.WHITE, 1.5)) == rgba(rl.WHITE)
  pulse.update(state(13.4112), 2.)
  pulse.update(state(13.4112, metric=True), 2.1)
  assert pulse.start_time == 2.
  for hidden in (True, False):
    current = state(13.4112)
    pulse.update(current if hidden else replace(current, speed_limit=SpeedLimitObservation()), 2.2, visible=not hidden)
    pulse.update(current, 2.3)
    assert rgba(pulse.color(rl.WHITE, 2.5)) == rgba(rl.WHITE)
  pulse.update(replace(current, drive_frame=2), 3.)
  assert pulse.start_time == 3.


@pytest.mark.parametrize("compact", [False, True])
def test_compact_sign_pulses_while_large_numbers_and_frame_stay_stable(compact):
  fonts = Mock()
  fonts.measure.return_value = Mock(width=20, height=20)
  fonts.vertical_ink.side_effect = lambda text, role, size: (0., size * .7)
  shown = state()
  shown = replace(shown, speed_limit=replace(shown.speed_limit, accepted_adjusted_limit_mps=shown.speed_limit.speed_limit_mps))
  shown = replace(shown, appearance=replace(shown.appearance, show_speed_limit_sign=True))
  renderer = CompactHudRenderer(fonts, Mock()) if compact else UnifiedSpeedWidget(fonts)
  with patch("time.monotonic", return_value=10.) as clock, \
       patch.object(rl, "draw_rectangle_rounded_lines_ex"), patch.object(rl, "draw_rectangle_rounded"), patch.object(rl, "draw_line_ex"), \
       patch("openpilot.starpilot.ui.onroad_large_widgets.draw_control_card") as card:
    def render():
      if isinstance(renderer, CompactHudRenderer):
        renderer._speed_limit_sign(shown)
      else:
        renderer.render(rl.Rectangle(0, 0, 176, 196), shown)
    render()
    clock.return_value = 10.5
    fonts.draw.reset_mock()
    render()
    numeric = next(call for call in fonts.draw.call_args_list if call.args[0] == "35")
    if compact:
      assert rgba(numeric.args[-1]) == (188, 132, 255, 255)
    else:
      assert rgba(card.call_args.kwargs["border"]) == (53, 67, 77, 255)
      assert rgba(numeric.args[-1]) == rgba(rl.WHITE)


def test_transient_missing_sample_keeps_changed_sign_pulse_and_map_changes_pulse():
  pulse = SpeedLimitPulse()
  pulse.update(state(source="map"), 10.)
  pulse.update(replace(state(), speed_limit=SpeedLimitObservation()), 10.1)
  pulse.update(state(source="map"), 10.2)
  assert pulse.start_time == 10.
  assert rgba(pulse.color(rl.WHITE, 10.5)) == (188, 132, 255, 255)
  pulse.update(state(13.4112, source="dashboard"), 11.)
  assert pulse.start_time == 11.
