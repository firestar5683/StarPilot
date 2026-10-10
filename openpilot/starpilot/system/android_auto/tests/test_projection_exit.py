import uuid
from unittest.mock import patch

import pytest

from openpilot.starpilot.system.android_auto.projection_control import NATIVE_FOCUS, ProjectionControlReceiver, ProjectionControlSender
from openpilot.starpilot.system.android_auto.projection_exit import ProjectionExit
from openpilot.starpilot.system.android_auto.projection_layout import CAR_EXIT, default_layout_for_viewport


class Graphics:
  lines = []

  @staticmethod
  def Rectangle(*values): return values

  @staticmethod
  def Vector2(*values): return values

  @staticmethod
  def Color(*values): return values

  @staticmethod
  def draw_rectangle_rounded(*_): pass

  @staticmethod
  def draw_rectangle_rounded_lines_ex(*_): pass

  @classmethod
  def draw_line_ex(cls, *values): cls.lines.append(values)

@pytest.mark.parametrize('background', [True, False])
@pytest.mark.parametrize('opacity', [0, 40, 100])
def test_exit_appearance_preserves_tap_action(background, opacity):
  calls = []
  control = ProjectionExit(Graphics, lambda: calls.append(NATIVE_FOCUS))
  placed = {**default_layout_for_viewport((2880, 1080))['widgets'][CAR_EXIT],
            'opacity': opacity, 'background': background}
  with patch.object(Graphics, 'draw_rectangle_rounded') as fill, \
       patch.object(Graphics, 'draw_rectangle_rounded_lines_ex') as border, patch.object(Graphics, 'draw_line_ex') as lines:
    control.draw(placed)
  assert fill.call_count == border.call_count == int(background)
  if background:
    assert fill.call_args.args[-1][-1] == round(166 * opacity / 100)
    assert border.call_args.args[-1][-1] == round(200 * opacity / 100)
  assert lines.call_count == 6
  assert all(call.args[-1][-1] == round(230 * opacity / 100) for call in lines.call_args_list)
  x, y = placed['x'] + 48, placed['y'] + 48
  assert control.touch('down', x, y, placed)
  assert control.touch('up', x, y, placed)
  assert calls == [NATIVE_FOCUS]


def test_car_widget_tap_requests_native_focus_and_drag_does_not():
  calls = []
  Graphics.lines = []
  control = ProjectionExit(Graphics, lambda: calls.append(NATIVE_FOCUS))
  placed = default_layout_for_viewport((2880, 1080))['widgets'][CAR_EXIT]
  x, y = placed['x'] + 48, placed['y'] + 48
  control.draw(placed)
  assert len(Graphics.lines) == 6
  assert control.touch('down', x, y, placed)
  assert control.touch('up', x, y, placed)
  assert calls == [NATIVE_FOCUS]
  assert control.touch('down', x, y, placed)
  assert control.touch('move', x - 30, y, placed)
  assert not control.touch('up', x, y, placed)
  assert calls == [NATIVE_FOCUS]


def test_projection_control_datagram_is_bounded_and_validated():
  path = f"/tmp/aa-control-{uuid.uuid4().hex}.sock"
  receiver, sender = ProjectionControlReceiver(path), ProjectionControlSender(path)
  try:
    sender.send(NATIVE_FOCUS)
    assert receiver.drain() == [NATIVE_FOCUS]
    assert receiver.drain() == []
    try:
      sender.send('disconnect')
    except ValueError:
      pass
    else:
      raise AssertionError('unknown renderer actions must be rejected')
  finally:
    sender.close()
    receiver.close()
