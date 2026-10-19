import math

import pyray as rl
import pytest

from openpilot.selfdrive.ui.onroad.starpilot import speed_source_drawer as drawer_module
from openpilot.selfdrive.ui.onroad.starpilot.speed_source_drawer import SpeedSourceDrawer, _outline


@pytest.fixture(autouse=True)
def no_gpu_batch(monkeypatch):
  monkeypatch.setattr(rl, "rl_draw_render_batch_active", lambda: None)


def test_motion_is_bounded_finishes_on_time_and_reverses_without_jumping():
  drawer = SpeedSourceDrawer()
  drawer.update(True, 1)
  assert drawer.progress == 0
  drawer.update(True, 1.09)
  assert 0 < drawer.progress < 1
  before_reverse = drawer.progress
  drawer.update(False, 1.09)
  assert drawer.progress == before_reverse
  drawer.update(False, 1.13)
  assert 0 < drawer.progress < before_reverse
  drawer.update(False, 1.24)
  assert drawer.progress == 0
  drawer.update(True, 2)
  drawer.update(True, 2.18)
  assert drawer.progress == 1
  drawer.update(False, 3)
  drawer.update(False, 3.14)
  assert drawer.progress == 0


@pytest.mark.parametrize("height,top", [(448, 283), (250, 75)])
@pytest.mark.parametrize("extension", [0.0001, 1, 12, 40.6, 124, 248])
def test_shared_surface_has_no_overlapping_fill_and_preserves_bottom_edge(height, top, extension):
  rect = rl.Rectangle(30, 75, 232, height)
  points = _outline(rect, top, extension)
  center = (146, (top + 75 + height) / 2)
  triangles = [((x - center[0]) * (ny - center[1]) - (y - center[1]) * (nx - center[0])) / 2
               for (x, y), (nx, ny) in zip(points, points[1:] + points[:1], strict=True)]
  # Every fan triangle has the same winding: the translucent surface is painted once.
  assert all(area >= -1e-8 for area in triangles)
  assert all(math.isfinite(value) for point in points for value in point)
  assert min(y for _x, y in points) == 75
  assert max(y for _x, y in points) == 75 + height
  assert max(x for x, _y in points) == pytest.approx(262 + extension)
  bottom = [x for x, y in points if y == 75 + height]
  assert min(bottom) == pytest.approx(70.6)
  assert max(bottom) == pytest.approx(262 + extension - 40.6)


def test_settled_frame_reuses_mesh_and_border_buffers(monkeypatch):
  for name in ("draw_triangle_fan", "draw_triangle_strip"):
    monkeypatch.setattr(rl, name, lambda *args: None)
  drawer = SpeedSourceDrawer()
  drawer.update(True, 0)
  drawer.update(True, 1)
  rect = rl.Rectangle(30, 75, 232, 448)
  border = rl.Color(255, 255, 255, 255)
  drawer.draw_frame(rect, 283, rl.BLACK, border)
  fill, strokes = drawer._fill, dict(drawer._strokes)
  for _ in range(10):
    drawer.draw_frame(rect, 283, rl.BLACK, border)
  assert drawer._fill is fill
  assert all(drawer._strokes[width] is buffer for width, buffer in strokes.items())
  drawer.draw_border(rect, 283, 3, border)
  assert drawer._fill is fill
  assert len(drawer._strokes) == 3


def test_fixed_width_contents_translate_behind_card_and_clip_is_restored_on_failure(monkeypatch):
  drawer = SpeedSourceDrawer()
  drawer.progress = 0.5
  clips, ended = [], []
  monkeypatch.setattr(rl, "begin_scissor_mode", lambda *args: clips.append(args))
  monkeypatch.setattr(rl, "end_scissor_mode", lambda: ended.append(True))

  def fail_contents(_state, panel):
    assert (panel.x, panel.y, panel.width, panel.height) == (138, 283, 248, 240)
    raise ValueError("source rendering failed")

  monkeypatch.setattr(drawer_module, "_draw_source_contents", fail_contents)
  with pytest.raises(ValueError, match="source rendering failed"):
    drawer.draw_contents({}, rl.Rectangle(30, 75, 232, 448), 283)
  assert clips == [(262, 283, 124, 240)]
  assert ended == [True]
