import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

import pytest


MODULE_NAME = "openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid"
PANEL_MODULE_NAME = "openpilot.selfdrive.ui.layouts.settings.starpilot.panel"
SECTIONED_PANEL_MODULE_NAME = "openpilot.selfdrive.ui.layouts.settings.starpilot.sectioned_panel"


@pytest.fixture(autouse=True)
def restore_ui_modules():
  modules = {name: module for name, module in sys.modules.items() if name == "pyray" or name.startswith("openpilot.")}
  yield
  for name in tuple(sys.modules):
    if (name == "pyray" or name.startswith("openpilot.")) and name not in modules:
      sys.modules.pop(name, None)
  sys.modules.update(modules)


def _clear_modules(*module_names):
  for module_name in module_names:
    sys.modules.pop(module_name, None)


def _register_modules(module_map):
  for name, module in module_map.items():
    sys.modules[name] = module


def _make_texture(width=80, height=80):
  return types.SimpleNamespace(width=width, height=height)


def _install_aethergrid_stubs():
  rl = types.SimpleNamespace(
    Color=lambda r, g, b, a=255: types.SimpleNamespace(r=r, g=g, b=b, a=a),
    Rectangle=lambda x=0, y=0, width=0, height=0: types.SimpleNamespace(x=x, y=y, width=width, height=height),
    Vector2=lambda x=0, y=0: types.SimpleNamespace(x=x, y=y),
    Texture2D=type("Texture2D", (), {}),
    Font=type("Font", (), {}),
    GuiTextAlignment=types.SimpleNamespace(TEXT_ALIGN_CENTER=0),
    BlendMode=types.SimpleNamespace(BLEND_ALPHA_PREMULTIPLY=1),
    WHITE=types.SimpleNamespace(r=255, g=255, b=255, a=255),
    draw_rectangle_rounded=lambda *a, **k: None,
    draw_rectangle_rounded_lines_ex=lambda *a, **k: None,
    draw_rectangle_rec=lambda *a, **k: None,
    draw_rectangle=lambda *a, **k: None,
    draw_rectangle_gradient_v=lambda *a, **k: None,
    draw_ring=lambda *a, **k: None,
    draw_circle=lambda *a, **k: None,
    draw_line=lambda *a, **k: None,
    draw_line_ex=lambda *a, **k: None,
    draw_triangle=lambda *a, **k: None,
    draw_texture_pro=lambda *a, **k: None,
    begin_blend_mode=lambda *a, **k: None,
    end_blend_mode=lambda *a, **k: None,
    draw_text_ex=lambda *a, **k: None,
    check_collision_point_rec=lambda p, r: (r.x <= p.x <= r.x + r.width) and (r.y <= p.y <= r.y + r.height),
    get_frame_time=lambda: 0.016,
    get_mouse_position=lambda: types.SimpleNamespace(x=0, y=0),
  )
  sys.modules["pyray"] = rl

  app_mod = types.ModuleType("openpilot.system.ui.lib.application")
  app_mod.FontWeight = types.SimpleNamespace(BOLD=700, NORMAL=400, MEDIUM=500, SEMI_BOLD=600)
  app_mod.MousePos = type("MousePos", (), {})
  app_mod.MouseEvent = type("MouseEvent", (), {})
  app_mod.FONT_SCALE = 1.0
  app_mod.gui_app = types.SimpleNamespace(
    width=1920,
    height=1080,
    last_mouse_event=types.SimpleNamespace(pos=types.SimpleNamespace(x=0, y=0)),
    font=lambda *_a, **_k: object(),
    texture=lambda *_a, **_k: _make_texture(),
    pop_widget=lambda: None,
  )
  sys.modules["openpilot.system.ui.lib.application"] = app_mod

  scroll_panel_mod = types.ModuleType("openpilot.system.ui.lib.scroll_panel2")
  class GuiScrollPanel2:
    def __init__(self, horizontal=True, handle_out_of_bounds=True):
      self._enabled = True
      self._offset = 0.0

    def set_enabled(self, enabled):
      self._enabled = enabled

    def update(self, bounds, content_size):
      return 0.0

    def is_touch_valid(self):
      return True

  scroll_panel_mod.GuiScrollPanel2 = GuiScrollPanel2
  sys.modules["openpilot.system.ui.lib.scroll_panel2"] = scroll_panel_mod

  multilang_mod = types.ModuleType("openpilot.system.ui.lib.multilang")
  multilang_mod.tr = lambda text: text
  sys.modules["openpilot.system.ui.lib.multilang"] = multilang_mod

  text_measure_mod = types.ModuleType("openpilot.system.ui.lib.text_measure")
  text_measure_mod.measure_text_cached = lambda *_a, **_k: types.SimpleNamespace(x=100, y=20)
  sys.modules["openpilot.system.ui.lib.text_measure"] = text_measure_mod

  widgets_mod = types.ModuleType("openpilot.system.ui.widgets")

  class Widget:
    def __init__(self):
      self._rect = rl.Rectangle()
      self._parent_rect = None
      self._enabled = True
      self.is_pressed = False
      self._children = []

    def _child(self, widget):
      self._children.append(widget)
      return widget

    @property
    def enabled(self):
      return self._enabled() if callable(self._enabled) else self._enabled

    def set_rect(self, rect):
      self._rect = rect

    def set_parent_rect(self, rect):
      self._parent_rect = rect

    def render(self, rect):
      self._rect = rect
      return self._render(rect)

    def set_click_callback(self, callback):
      self.on_click = callback

    def set_touch_valid_callback(self, callback):
      self._touch_valid_callback = callback

    def set_enabled(self, enabled):
      self._enabled = enabled

    def _render(self, rect):
      return None

  widgets_mod.Widget = Widget
  widgets_mod.DialogResult = types.SimpleNamespace(CONFIRM=1, CANCEL=0, NO_ACTION=-1)
  sys.modules["openpilot.system.ui.widgets"] = widgets_mod

  option_dialog_mod = types.ModuleType("openpilot.system.ui.widgets.option_dialog")
  option_dialog_mod.MultiOptionDialog = type("MultiOptionDialog", (), {})
  sys.modules["openpilot.system.ui.widgets.option_dialog"] = option_dialog_mod

  label_mod = types.ModuleType("openpilot.system.ui.widgets.label")
  label_mod.gui_label = lambda *a, **k: None
  sys.modules["openpilot.system.ui.widgets.label"] = label_mod

  asset_loader_mod = types.ModuleType("openpilot.selfdrive.ui.layouts.settings.starpilot.asset_loader")
  asset_loader_mod.starpilot_texture = lambda *_a, **_k: _make_texture()
  sys.modules["openpilot.selfdrive.ui.layouts.settings.starpilot.asset_loader"] = asset_loader_mod


def _install_panel_stubs(aethergrid):
  sectioned_mod = types.ModuleType(SECTIONED_PANEL_MODULE_NAME)
  sectioned_mod.SectionedTileLayout = type("SectionedTileLayout", (), {})
  sectioned_mod.TileSection = type("TileSection", (), {})
  starpilot_variables_mod = types.ModuleType("openpilot.starpilot.common.starpilot_variables")
  starpilot_variables_mod.update_starpilot_toggles = lambda: None

  _register_modules({
    SECTIONED_PANEL_MODULE_NAME: sectioned_mod,
    "openpilot.common.params": types.SimpleNamespace(Params=type("Params", (), {}), UnknownKeyName=Exception),
    "openpilot.starpilot.common.starpilot_variables": starpilot_variables_mod,
    MODULE_NAME: aethergrid,
  })


def _import_module(module_name):
  _install_aethergrid_stubs()
  _clear_modules(module_name)
  return importlib.import_module(module_name)


def _import_aethergrid():
  return _import_module(MODULE_NAME)


def _import_panel(monkeypatch_module=None):
  aethergrid = _import_aethergrid()
  _install_panel_stubs(aethergrid)
  _clear_modules(PANEL_MODULE_NAME)
  return importlib.import_module(PANEL_MODULE_NAME)


def _import_real_sectioned_panel():
  _install_aethergrid_stubs()
  _clear_modules(SECTIONED_PANEL_MODULE_NAME)
  return importlib.import_module(SECTIONED_PANEL_MODULE_NAME)


class RenderSpy:
  def __init__(self):
    self.rects = []
    self.parent_rect = None

  def render(self, rect):
    self.rects.append(rect)

  def show_event(self):
    pass

  def hide_event(self):
    pass

  def set_parent_rect(self, rect):
    self.parent_rect = rect


class TestAethergridContracts(unittest.TestCase):
  def test_aethergrid_module_imports_with_headless_stubs(self):
    mod = _import_aethergrid()

    self.assertTrue(hasattr(mod, "TileGrid"))
    self.assertTrue(hasattr(mod, "HubTile"))
    self.assertTrue(hasattr(mod, "ToggleTile"))
    self.assertTrue(hasattr(mod, "ValueTile"))
    self.assertTrue(hasattr(mod, "RadioTileGroup"))
    self.assertTrue(hasattr(mod, "AetherSliderDialog"))


  def test_tile_grid_column_contract_stays_stable(self):
    mod = _import_aethergrid()
    grid = mod.TileGrid(columns=None, padding=mod.SPACING.tile_gap)

    self.assertEqual(grid.get_column_count(1), 1)
    self.assertEqual(grid.get_column_count(2), 2)
    self.assertEqual(grid.get_column_count(3), 3)
    self.assertEqual(grid.get_column_count(4), 2)
    self.assertEqual(grid.get_column_count(5), 3)
    self.assertEqual(grid.get_column_count(7), 4)


  def test_build_list_panel_frame_contract(self):
    mod = _import_aethergrid()
    frame = mod.build_list_panel_frame(mod.rl.Rectangle(0, 0, 1920, 1080))

    self.assertGreater(frame.shell.width, 0)
    self.assertEqual(frame.header.height, mod.AETHER_LIST_METRICS.header_height)
    self.assertGreater(frame.scroll.height, 0)


  def test_hit_rect_keeps_touch_slop_after_surface_flattening(self):
    mod = _import_aethergrid()
    tile = mod.AetherTile(surface_color="#3B82F6")
    tile.set_rect(mod.rl.Rectangle(100, 200, 300, 150))
    hit = tile._hit_rect

    self.assertGreater(hit.width, tile._rect.width)
    self.assertGreater(hit.height, tile._rect.height)


  def test_hub_tile_preserves_status_progress_api(self):
    mod = _import_aethergrid()
    tile = mod.HubTile("Driving Controls", "Desc", bg_color="#3B82F6", get_status=lambda: "Download 50%")

    self.assertEqual(tile.get_status(), "Download 50%")

  def test_custom_icon_draws_directly_while_cache_fill_is_pending(self):
    mod = _import_aethergrid()
    scribble = sys.modules["openpilot.selfdrive.ui.layouts.settings.starpilot.scribble"]
    geometry = MagicMock()
    cache = MagicMock(return_value=None)

    color = mod.rl.Color(255, 255, 255, 255)
    with patch.object(scribble, "_draw_custom_icon_geometry", geometry), \
         patch.object(scribble.gui_app, "cached_render_texture", cache, create=True):
      scribble.draw_custom_icon("sound", 10, 20, 1.0, color)

    cache.assert_called_once()
    geometry.assert_called_once_with("sound", 10, 20, 1.0, color)

  def test_custom_icon_uses_completed_cache_without_redrawing_geometry(self):
    mod = _import_aethergrid()
    scribble = sys.modules["openpilot.selfdrive.ui.layouts.settings.starpilot.scribble"]
    geometry = MagicMock()
    cache = MagicMock(return_value=object())
    draw_texture = MagicMock()

    with patch.object(scribble, "_draw_custom_icon_geometry", geometry), \
         patch.object(scribble.gui_app, "cached_render_texture", cache, create=True), \
         patch.object(scribble.rl, "draw_texture_pro", draw_texture):
      scribble.draw_custom_icon("sound", 10, 20, 1.0, mod.rl.Color(255, 255, 255, 255))

    geometry.assert_not_called()
    draw_texture.assert_called_once()
    destination = draw_texture.call_args.args[2]
    self.assertLess(destination.x, 10)
    self.assertLess(destination.y, 20)

  def test_translucent_custom_icon_uses_premultiplied_blending(self):
    mod = _import_aethergrid()
    scribble = sys.modules["openpilot.selfdrive.ui.layouts.settings.starpilot.scribble"]
    geometry = MagicMock()
    cache = MagicMock(return_value=object())
    begin_blend = MagicMock()
    end_blend = MagicMock()

    color = mod.rl.Color(160, 170, 185, 80)
    with patch.object(scribble, "_draw_custom_icon_geometry", geometry), \
         patch.object(scribble.gui_app, "cached_render_texture", cache, create=True), \
         patch.object(scribble.rl, "begin_blend_mode", begin_blend), \
         patch.object(scribble.rl, "end_blend_mode", end_blend):
      scribble.draw_custom_icon("first_aid", 10, 20, 0.8, color)

    cache.assert_called_once()
    geometry.assert_not_called()
    begin_blend.assert_called_once_with(mod.rl.BlendMode.BLEND_ALPHA_PREMULTIPLY)
    end_blend.assert_called_once()

  def test_tile_grid_reflows_to_wider_tiles_when_width_is_tight(self):
    mod = _import_aethergrid()
    grid = mod.TileGrid(columns=None, padding=mod.SPACING.tile_gap)

    spies = [RenderSpy() for _ in range(7)]
    for spy in spies:
      grid.add_tile(spy)

    grid.render(mod.rl.Rectangle(0, 0, 700, 500))

    self.assertTrue(spies[0].rects)
    self.assertGreater(spies[0].rects[0].width, 300)


  def test_toggle_and_value_tiles_keep_enabled_contract(self):
    mod = _import_aethergrid()
    toggle = mod.ToggleTile("Feature", lambda: True, lambda _v: None, is_enabled=lambda: False)
    value = mod.ValueTile("Value", lambda: "42", lambda: None, is_enabled=lambda: False)

    self.assertFalse(toggle.enabled)
    self.assertFalse(value.enabled)

  def test_disabled_value_tile_does_not_trigger_click(self):
    mod = _import_aethergrid()
    on_click = MagicMock()
    value = mod.ValueTile("Value", lambda: "42", on_click, is_enabled=lambda: False)
    value.set_rect(mod.rl.Rectangle(0, 0, 300, 150))

    value._handle_mouse_press(types.SimpleNamespace(x=10, y=10))
    value._handle_mouse_release(types.SimpleNamespace(x=10, y=10))

    on_click.assert_not_called()


  def test_slider_dialog_keeps_color_and_callback_contract(self):
    mod = _import_aethergrid()
    captured = []
    dialog = mod.AetherSliderDialog("Test", 0, 10, 1, 5, lambda result, value: captured.append((result, value)), color="#8B5CF6")

    self.assertGreaterEqual(dialog._color.r, 0)
    self.assertEqual(dialog._current_val, 5)


  def test_radio_tile_group_preserves_selection_api(self):
    mod = _import_aethergrid()
    group = mod.RadioTileGroup("", ["A", "B", "C"], 1, lambda idx: None)
    group.set_index(2)

    self.assertEqual(group.current_index, 2)

  def test_zero_span_sliders_do_not_divide_by_zero(self):
    mod = _import_aethergrid()
    slider = mod.AetherSlider(5, 5, 1, 5, lambda _v: None)
    thumb_x = slider._get_thumb_x(mod.rl.Rectangle(0, 0, 320, 80))

    self.assertGreaterEqual(thumb_x, 0)

  def test_panel_module_can_import_against_refactored_aethergrid(self):
    panel_mod = _import_panel()

    self.assertTrue(hasattr(panel_mod, "StarPilotPanel"))
    self.assertTrue(hasattr(panel_mod, "create_tile_panel"))

  def test_sectioned_layout_short_height_uses_scrollable_compact_profile(self):
    mod = _import_aethergrid()
    sectioned_mod = _import_real_sectioned_panel()

    layout = sectioned_mod.SectionedTileLayout()
    grid = mod.TileGrid(columns=2, padding=mod.SPACING.tile_gap, uniform_width=True)

    for _ in range(6):
      grid.add_tile(RenderSpy())

    layout.set_sections([sectioned_mod.TileSection("Test", grid)])
    title_h, title_gap, section_gap, row_h = layout._layout_profile(mod.rl.Rectangle(0, 0, 800, 220), layout._sections)

    self.assertGreaterEqual(row_h, 0)
    self.assertLessEqual(title_h, layout._title_height)

  def test_slider_dialog_on_change_callback(self):
    mod = _import_aethergrid()
    captured_changes = []
    captured_close = []

    dialog = mod.AetherSliderDialog(
      "Test", 0, 10, 1, 5,
      on_close=lambda res, val: captured_close.append((res, val)),
      color="#8B5CF6",
      on_change=lambda val: captured_changes.append(val)
    )

    # Run render to compute button and track rects
    dialog._render(mod.rl.Rectangle(0, 0, 1920, 1080))

    # Mock mouse position hitting the plus rect and press it
    plus_center = mod.rl.Vector2(
      dialog._plus_rect.x + dialog._plus_rect.width / 2,
      dialog._plus_rect.y + dialog._plus_rect.height / 2
    )

    # Mock collision detection to return True when checking the plus button
    old_collision = mod.rl.check_collision_point_rec
    def mock_collision(point, rec):
      if rec == dialog._plus_rect:
        return True
      return False
    mod.rl.check_collision_point_rec = mock_collision

    try:
      dialog._handle_mouse_press(plus_center)
      dialog._handle_mouse_release(plus_center)
    finally:
      mod.rl.check_collision_point_rec = old_collision

    self.assertEqual(dialog._current_val, 6)
    self.assertEqual(captured_changes, [6])

  def test_tile_grid_measure_height_with_explicit_tile_height(self):
    mod = _import_aethergrid()
    grid = mod.TileGrid(columns=2, padding=10, tile_height=140)
    for _ in range(5):
      grid.add_tile(RenderSpy())
    
    h = grid.measure_height(500)
    self.assertEqual(h, 740)

  def test_tile_grid_measure_height_with_min_max_clamping(self):
    mod = _import_aethergrid()
    grid = mod.TileGrid(columns=2, padding=10, tile_height=None, min_tile_height=100.0, max_tile_height=150.0)
    for _ in range(5):
      grid.add_tile(RenderSpy())
    
    h = grid.measure_height(500)
    self.assertEqual(h, 790)

    spy = RenderSpy()
    grid.add_tile(spy)
    grid.render(mod.rl.Rectangle(0, 0, 500, 1000))
    self.assertTrue(spy.rects)
    self.assertEqual(spy.rects[0].height, 150.0)

  def test_tile_grid_measure_height_default_fallback(self):
    mod = _import_aethergrid()
    grid = mod.TileGrid(columns=2, padding=10, tile_height=None)
    for _ in range(5):
      grid.add_tile(RenderSpy())
    
    h = grid.measure_height(500)
    self.assertEqual(h, 940)

  def test_tile_grid_render_top_left_aligned_with_tile_height(self):
    mod = _import_aethergrid()
    grid = mod.TileGrid(columns=2, padding=10, tile_height=140)
    spy = RenderSpy()
    grid.add_tile(spy)
    
    grid.render(mod.rl.Rectangle(0, 50, 500, 300))
    self.assertTrue(spy.rects)
    self.assertEqual(spy.rects[0].y, 130)
    self.assertEqual(spy.rects[0].x, 0)

  def test_disabled_tiles_hud_mode_rendering(self):
    mod = _import_aethergrid()
    
    # ToggleTile disabled
    toggle = mod.ToggleTile(
      title="Test Loud",
      get_state=lambda: True,
      set_state=lambda s: None,
      is_enabled=lambda: False,
    )
    # Spy on _render_hud_background
    orig_hud_bg = toggle._render_hud_background
    spy_called = []
    def spy_hud_bg(*a, **k):
      spy_called.append("toggle")
      return orig_hud_bg(*a, **k)
    toggle._render_hud_background = spy_hud_bg
    toggle.render(mod.rl.Rectangle(0, 0, 150, 130))
    self.assertIn("toggle", spy_called)

    # ValueTile disabled
    value_tile = mod.ValueTile(
      title="Test Value",
      get_value=lambda: "Off",
      on_click=lambda: None,
      is_enabled=lambda: False
    )
    orig_value_hud_bg = value_tile._render_hud_background
    def spy_value_hud_bg(*a, **k):
      spy_called.append("value")
      return orig_value_hud_bg(*a, **k)
    value_tile._render_hud_background = spy_value_hud_bg
    value_tile.render(mod.rl.Rectangle(0, 0, 150, 130))
    self.assertIn("value", spy_called)

    # SliderTile disabled
    slider_tile = mod.SliderTile(
      title="Test Slider",
      get_value=lambda: 50.0,
      set_value=lambda v: None,
      min_val=0.0,
      max_val=100.0,
      step=1.0,
      is_enabled=lambda: False
    )
    orig_slider_hud_bg = slider_tile._render_hud_background
    def spy_slider_hud_bg(*a, **k):
      spy_called.append("slider")
      return orig_slider_hud_bg(*a, **k)
    slider_tile._render_hud_background = spy_slider_hud_bg
    slider_tile.render(mod.rl.Rectangle(0, 0, 150, 130))
    self.assertIn("slider", spy_called)

  def test_tile_grid_force_square(self):
    mod = _import_aethergrid()
    grid = mod.TileGrid(columns=2, padding=10, min_tile_width=100, force_square=True)
    spies = [RenderSpy() for _ in range(5)]
    for spy in spies:
      grid.add_tile(spy)
    
    # col_w = (500 - 10) / 2 = 245
    # rows = 3, gap_h = 2 * 10 = 20
    # expected height = 3 * 245 + 20 = 755
    self.assertEqual(grid.measure_height(500), 755)
    
    grid.render(mod.rl.Rectangle(0, 0, 500, 300))
    self.assertTrue(spies[0].rects)
    self.assertEqual(spies[0].rects[0].width, 245)
    self.assertEqual(spies[0].rects[0].height, 245)

  def test_tile_grid_column_preservation_with_single_tile(self):
    mod = _import_aethergrid()
    grid = mod.TileGrid(columns=2, padding=10, min_tile_width=100, force_square=True)
    spy = RenderSpy()
    grid.add_tile(spy)

    # With only 1 tile in a 2-column layout, it should still calculate the tile size based on 2 columns
    # col_w = (500 - 10) / 2 = 245
    grid.render(mod.rl.Rectangle(0, 0, 500, 300))
    self.assertTrue(spy.rects)
    self.assertEqual(spy.rects[0].width, 245)
    self.assertEqual(spy.rects[0].height, 245)

  def test_hud_background_glow_overflow_protection(self):
    mod = _import_aethergrid()
    tile = mod.ToggleTile("Test", lambda: True, lambda v: None)
    # Test with extreme glow values (negative and large positive) to verify no OverflowError occurs
    try:
      tile._render_hud_background(mod.rl.Rectangle(0, 0, 150, 130), mod.rl.Color(255, 0, 0, 255), glow=5.0)
      tile._render_hud_background(mod.rl.Rectangle(0, 0, 150, 130), mod.rl.Color(255, 0, 0, 255), glow=-2.0)
    except OverflowError:
      self.fail("OverflowError raised with extreme glow values")

  def test_aether_category_tile_view(self):
    mod = _import_aethergrid()
    controller_mock = MagicMock()
    
    toggle_visible = True
    rows = [
      mod.SettingRow("toggle_row", "toggle", "Toggle Title", subtitle="Toggle Subtitle",
                     get_state=lambda: True, set_state=lambda v: None,
                     visible=lambda: toggle_visible),
      mod.SettingRow("value_row", "value", "Value Title", subtitle="Value Subtitle",
                     get_value=lambda: "Value", on_click=lambda: None),
      mod.SettingRow("action_row", "action", "Action Title", action_text="Run", on_click=lambda: None),
    ]

    view = mod.AetherCategoryTileView(controller_mock, "Category Title", rows, color="#FF0000", subtitle="Category Description")
    
    self.assertEqual(len(view._sections), 1)
    self.assertEqual(len(view._sections[0].rows), 3)
    
    visible = view._visible_rows(view._sections[0])
    self.assertEqual(len(visible), 3)
    
    toggle_visible = False
    visible = view._visible_rows(view._sections[0])
    self.assertEqual(len(visible), 2)
    self.assertNotIn(rows[0], visible)

    view._back_btn_rect = mod.rl.Rectangle(196, 56, 68, 68)
    view._slide_progress = 1.0 # fully slide-in
    view.set_rect(mod.rl.Rectangle(0, 0, 1920, 1080))
    
    self.assertEqual(view._target_at(mod.rl.Vector2(200, 60)), mod.BACK_BTN)
    self.assertEqual(view._target_at(mod.rl.Vector2(1000, 60)), "__dismiss__")

    app_mod = sys.modules["openpilot.system.ui.lib.application"]
    app_mod.gui_app.pop_widget = MagicMock()
    
    view._activate_target(mod.BACK_BTN)
    app_mod.gui_app.pop_widget.assert_called_once()


if __name__ == "__main__":
  unittest.main()
