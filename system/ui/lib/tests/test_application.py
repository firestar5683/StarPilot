import os
from importlib.resources import as_file
from types import SimpleNamespace

import pytest

from openpilot.system.ui.lib import application


def test_default_fps_uses_shared_target_or_fps_override():
  assert application._DEFAULT_FPS == int(os.getenv("FPS", "60"))


def test_big_ui_adaptive_fps_uses_60_active_15_idle(monkeypatch):
  monkeypatch.setattr(application, "OFFSCREEN", False)
  monkeypatch.setattr(application, "RECORD", False)
  now = [100.0]
  monkeypatch.setattr(application.time, "monotonic", lambda: now[0])

  app = object.__new__(application.GuiApplication)
  app._full_target_fps = 60
  app._target_fps = 60
  applied_targets = []
  app._set_target_fps = applied_targets.append

  app.configure_adaptive_rendering(True)
  assert app._idle_target_fps == 15
  assert applied_targets[-1] == 60

  now[0] += application.UI_INTERACTION_FPS_DURATION + 0.01
  app._apply_render_mode()
  assert applied_targets[-1] == 15

  app.set_render_mode(True)
  assert applied_targets[-1] == 60


def test_raylib_target_fps_uses_mici_display_refresh(monkeypatch):
  monkeypatch.setattr(application, "OFFSCREEN", False)
  monkeypatch.setattr(application, "DEVICE_TYPE", "mici")
  monkeypatch.setattr(application, "PC", False)

  assert application._raylib_target_fps(60) == 0


def test_raylib_target_fps_limits_mici_desktop_preview(monkeypatch):
  monkeypatch.setattr(application, "OFFSCREEN", False)
  monkeypatch.setattr(application, "DEVICE_TYPE", "mici")
  monkeypatch.setattr(application, "PC", True)

  assert application._raylib_target_fps(60) == 60


def test_raylib_target_fps_limits_other_devices(monkeypatch):
  monkeypatch.setattr(application, "OFFSCREEN", False)
  monkeypatch.setattr(application, "DEVICE_TYPE", "tici")

  assert application._raylib_target_fps(60) == 60


def test_raylib_target_fps_disables_limit_for_offscreen(monkeypatch):
  monkeypatch.setattr(application, "OFFSCREEN", True)
  monkeypatch.setattr(application, "DEVICE_TYPE", "tici")

  assert application._raylib_target_fps(60) == 0


@pytest.mark.parametrize("covered", [False, True])
def test_render_preserves_visible_layers_and_measures_complete_frame(monkeypatch, covered):
  monkeypatch.setattr(application, "PC", False)
  monkeypatch.setattr(application, "RECORD", False)
  monkeypatch.setattr(application.GuiApplication, "_set_log_callback", lambda _: None)
  app = application.GuiApplication(536, 240)
  app._scale = 1.0
  app._nav_stack_widgets_to_render = 2
  app._mouse = SimpleNamespace(get_events=list)
  app._burn_in_shift = lambda: (0, 0)
  app._monitor_fps = lambda: None
  app._show_fps = app._show_touches = False
  app._grid_size = app._profile_render_frames = 0

  clock = SimpleNamespace(wall=10.0, cpu=1.0)
  monkeypatch.setattr(application.time, "monotonic", lambda: clock.wall)
  monkeypatch.setattr(application.time, "thread_time", lambda: clock.cpu)
  monkeypatch.setattr(application.rl, "window_should_close", lambda: False)
  monkeypatch.setattr(application.rl, "begin_drawing", lambda: None)
  monkeypatch.setattr(application.rl, "clear_background", lambda _: None)
  rendered = []

  def draw(name):
    rendered.append(name)
    clock.wall += 0.004
    clock.cpu += 0.003

  def present():
    clock.wall += 0.011
    clock.cpu += 0.001

  def populate_cache():
    clock.wall += 0.003
    clock.cpu += 0.002

  monkeypatch.setattr(application.rl, "end_drawing", present)
  app._populate_render_texture_cache = populate_cache
  app._nav_stack = [
    SimpleNamespace(render=lambda _: draw("road")),
    SimpleNamespace(covers_background=lambda _: covered, render=lambda _: draw("panel")),
  ]
  frames = app.render()
  assert next(frames)
  clock.wall += 0.002
  clock.cpu += 0.001
  app.request_close()
  with pytest.raises(StopIteration):
    next(frames)

  assert rendered == (["panel"] if covered else ["road", "panel"])
  draws = len(rendered)
  assert app.frame_timing == pytest.approx(application.FrameTiming(
    draws * 4 + 16, draws * 3 + 4, draws * 4, 2, 11,
  ))


def test_burn_in_shift_transitions_between_positions(monkeypatch):
  app = object.__new__(application.GuiApplication)
  app._burn_in_start_time = 100.0

  monkeypatch.setattr(application, "BURN_IN_PREVENTION", True)
  monkeypatch.setattr(application, "BURN_IN_SHIFT_INTERVAL", 10.0)
  monkeypatch.setattr(application, "BURN_IN_SHIFT_PIXELS", 2)
  monkeypatch.setattr(application, "BURN_IN_SHIFT_TRANSITION_SECONDS", 2.0)

  assert app._burn_in_shift(108.0) == (0.0, 0.0)
  midpoint = app._burn_in_shift(109.0)
  assert midpoint == (-1.0, 0.0)
  assert app._burn_in_shift(110.0) == (-2.0, 0.0)


def test_brand_font_assets_include_wordmark_glyphs():
  with as_file(application.FONT_DIR.joinpath("como-heavy.fnt")) as font_path:
    lines = font_path.read_text().splitlines()

  glyphs = {}
  for line in lines:
    if not line.startswith("char id="):
      continue
    fields = dict(field.split("=", 1) for field in line.split() if "=" in field)
    glyphs[int(fields["id"])] = (int(fields["width"]), int(fields["height"]))

  for char in set("StarPilot"):
    assert glyphs[ord(char)][0] > 0
    assert glyphs[ord(char)][1] > 0


def test_brand_font_is_not_replaced_by_language_fallback(monkeypatch):
  brand_font = SimpleNamespace(texture=SimpleNamespace(id=1))
  unifont = SimpleNamespace(texture=SimpleNamespace(id=2))
  monkeypatch.setattr(application.multilang, "requires_unifont", lambda: True)
  monkeypatch.setattr(application.gui_app, "font", lambda weight: {
    application.FontWeight.BRAND: brand_font,
    application.FontWeight.UNIFONT: unifont,
  }[weight])

  assert application.font_fallback(brand_font) is brand_font
  assert application.font_fallback(SimpleNamespace(texture=SimpleNamespace(id=3))) is unifont


def test_scissor_mode_shifted_for_direct_framebuffer(monkeypatch):
  orig_scissor_calls = []
  monkeypatch.setattr(application.rl, "begin_scissor_mode", lambda x, y, w, h: orig_scissor_calls.append((x, y, w, h)))
  if hasattr(application.rl, "_orig_begin_scissor_mode"):
    delattr(application.rl, "_orig_begin_scissor_mode")

  app = object.__new__(application.GuiApplication)
  app._scale = 1.0
  app._pixel_scale_x = 1.0
  app._pixel_scale_y = 1.0
  app._render_texture = None
  app._burn_in_shift = lambda: (2.0, -1.0)

  app._patch_scissor_mode()
  application.rl.begin_scissor_mode(100, 200, 300, 400)

  assert orig_scissor_calls[-1] == (102, 199, 300, 400)

  # Inside an offscreen render texture, scissor must remain unshifted
  app._render_texture = SimpleNamespace()
  application.rl.begin_scissor_mode(100, 200, 300, 400)
  assert orig_scissor_calls[-1] == (100, 200, 300, 400)

  # Clean up patched function
  if hasattr(application.rl, "_orig_begin_scissor_mode"):
    application.rl.begin_scissor_mode = application.rl._orig_begin_scissor_mode


def test_needs_render_texture_bypassed_on_tici_by_default(monkeypatch):
  monkeypatch.setattr(application, "PC", False)
  monkeypatch.setattr(application, "DEVICE_TYPE", "tici")
  monkeypatch.setattr(application, "BURN_IN_MODE", False)
  monkeypatch.setattr(application, "RECORD", False)
  monkeypatch.setattr(application, "MICI_FORCE_RENDER_TEXTURE", False)
  monkeypatch.setattr(application, "TICI_FORCE_RENDER_TEXTURE", False)
  monkeypatch.setattr(application, "WHITE_LUMINANCE_CAP", 1.0)

  app = object.__new__(application.GuiApplication)
  app._scale = 1.0

  # On TICI by default, render texture MUST be False (saving 21.8 ms)
  assert app._needs_render_texture() is False

  # Explicit override forces render texture
  monkeypatch.setattr(application, "TICI_FORCE_RENDER_TEXTURE", True)
  assert app._needs_render_texture() is True

  # Recording mode forces render texture
  monkeypatch.setattr(application, "TICI_FORCE_RENDER_TEXTURE", False)
  monkeypatch.setattr(application, "RECORD", True)
  assert app._needs_render_texture() is True


