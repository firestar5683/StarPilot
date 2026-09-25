import pytest
import pyray as rl

from openpilot.starpilot.ui.onroad_corner import _commands


def test_corner_geometry_tracks_layout_origin_without_changing_colors():
  original = _commands(0., 0., 2160., 1080.)
  moved = _commands(29., 21., 2160., 1080.)
  assert len(original) == len(moved)
  for (draw, arguments), (moved_draw, moved_arguments) in zip(original, moved, strict=True):
    assert draw == moved_draw
    for old, new in zip(arguments, moved_arguments, strict=True):
      if hasattr(old, "x"):
        assert new.x == pytest.approx(old.x + 29., abs=1e-4)
        assert new.y == pytest.approx(old.y + 21., abs=1e-4)
      elif isinstance(old, rl.ffi.CData) and rl.ffi.typeof(old).kind == 'array':
        assert len(old) == len(new) == 4
        for a, b in zip(old, new, strict=True):
          assert b.x == pytest.approx(a.x + 29., abs=1e-4)
          assert b.y == pytest.approx(a.y + 21., abs=1e-4)
      elif hasattr(old, "r"):
        assert (new.r, new.g, new.b, new.a) == (old.r, old.g, old.b, old.a)
      else:
        assert old == new


def test_repeated_layout_sizes_have_bounded_geometry_storage():
  _commands.cache_clear()
  for width in range(1600, 2161):
    _commands(0., 0., float(width), 1080.)
  assert _commands.cache_info().currsize == 4
  assert _commands(0., 0., 2160., 1080.) is _commands(0., 0., 2160., 1080.)
  _commands.cache_clear()
