"""Pinned numeric atlas and the larger stack's saved/touch geometry."""
from dataclasses import replace
import re
from types import SimpleNamespace

from PIL import Image

from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile, default_font_directory, font_filename, font_path, validate_bitmap_font
from openpilot.starpilot.ui.large_speed_geometry import WIDTH, PADDING, source_panel_bounds, source_toggle_bounds
from openpilot.starpilot.ui.onroad_customization import default_document, validate_document
from openpilot.starpilot.ui.onroad_state import slc_controls
from openpilot.starpilot.ui.tests.test_speed_stack import road
from openpilot.starpilot.system.android_auto.projection_layout import default_layout_for_viewport, validate_layout_for_viewport


def test_numeric_subset_is_pinned_and_has_real_tabular_glyphs():
  filename = font_filename(Profile.LARGE, FontRole.SPEED)
  path = font_path(default_font_directory(), filename)
  assert filename == 'DINish-Speed.fnt'
  assert font_filename(Profile.COMPACT, FontRole.SPEED) == 'Inter-Bold.fnt'
  assert font_path(default_font_directory() / 'missing', filename) == path
  validate_bitmap_font(path)
  glyphs = {int(row['id']): row for line in path.read_text().splitlines() if line.startswith('char id=')
            for row in [dict(re.findall(r'(\w+)=(-?\d+)', line))]}
  assert set(map(ord, '0123456789–-?')) <= glyphs.keys()
  assert len({glyphs[ord(char)]['xadvance'] for char in '0123456789'}) == 1
  one = glyphs[ord('1')]
  x, y, w, h = (int(one[key]) for key in ('x', 'y', 'width', 'height'))
  with Image.open(path.with_suffix('.png')) as atlas:
    assert atlas.crop((x, y, x + w, y + h)).getchannel('A').getbbox()[0] > 0


def test_three_digit_values_units_and_long_status_fit_actual_fonts():
  fonts = BitmapFonts(Profile.LARGE, default_font_directory())
  try:
    for value in ('88', '99', '100', '110', '120', '199', '–'):
      for unit in ('mph', 'km/h'):
        assert fonts.measure(value, FontRole.SPEED, 112).width + 14 + fonts.measure(unit, FontRole.NORMAL, 28).width <= WIDTH - 2 * PADDING
    for status in ('Using accelerator', 'Overridden', 'Above set speed', 'Matches set speed', 'Override saved', 'Using set speed', 'Using speed limit', 'Matches speed limit', 'Unavailable', 'Cruise off'):
      assert fonts.measure(status, FontRole.NORMAL, 30).width <= WIDTH - 2 * PADDING
    top, bottom = fonts.vertical_ink('120', FontRole.SPEED, 112)
    assert 85 <= bottom - top <= 90
  finally:
    fonts.close()


def test_v5_geometry_migrates_and_keeps_custom_actions_independent():
  doc = default_document()
  doc['version'] = 5
  doc['speedSources'] = True
  doc['layouts']['large']['cruise_limits'].update(x=1550, y=638)
  doc['layouts']['large']['speed_limit_actions'].update(x=1550, y=954)
  migrated = validate_document(doc)
  assert migrated['version'] == 6
  assert migrated['layouts']['large']['cruise_limits'] == {'x': 1486, 'y': 528, 'enabled': True}
  assert migrated['layouts']['large']['speed_limit_actions'] == {'x': 1486, 'y': 942, 'enabled': True}
  assert migrated['speedSources'] is True
  assert doc['layouts']['large']['cruise_limits']['x'] == 1550
  assert validate_document(migrated) == migrated
  doc['layouts']['large']['cruise_limits'].update(x=88, y=75)
  doc['layouts']['large']['speed_limit_actions'].update(x=88, y=447)
  assert validate_document(doc)['layouts']['large']['speed_limit_actions']['y'] == 567


def test_pending_buttons_and_source_popup_do_not_cover_monitor():
  state = road()
  state = replace(state, speed_limit=replace(state.speed_limit, pending_speed_limit_mps=25))
  apply, keep = slc_controls(Profile.LARGE, state)
  assert apply.bounds == (88, 611, 254, 675)
  assert keep.bounds == (266, 611, 432, 675)
  assert source_toggle_bounds(state) == (88, 697, 432, 741)
  panel = source_panel_bounds(state, 200, SimpleNamespace(x=30, y=30, width=1800, height=1020))
  assert panel is not None
  x, y, width, height = panel
  assert x >= 280 or x + width <= 88 or y + height <= 808 or y >= 1000
  assert x >= 1437 or x + width <= 439 or y + height <= 759 or y >= 999


def test_projection_v1_layout_migrates_without_losing_other_widgets():
  viewport = (2880, 1080)
  doc = default_layout_for_viewport(viewport)
  doc['version'] = 1
  doc['widgets']['speed_limit_actions'].update(x=88, y=447)
  doc['widgets']['current_speed'].update(x=1400, y=100)
  migrated = validate_layout_for_viewport(doc, viewport)
  assert migrated['version'] == 2
  assert migrated['widgets']['speed_limit_actions']['y'] == 567
  assert migrated['widgets']['current_speed'] == doc['widgets']['current_speed']
  assert validate_layout_for_viewport(migrated, viewport) == migrated


def test_committed_projection_v1_right_edge_is_preserved_and_clamped():
  viewport = (1860, 1080)
  doc = default_layout_for_viewport(viewport)
  doc['version'] = 1
  doc['widgets']['cruise_limits'].update(x=1654, y=75)
  doc['widgets']['speed_limit_actions'].update(x=1654, y=500)
  migrated = validate_layout_for_viewport(doc, viewport)
  assert migrated['widgets']['cruise_limits']['x'] == 1486
  assert migrated['widgets']['speed_limit_actions'] == {'x': 1486, 'y': 567, 'enabled': True}


def test_projected_source_popup_avoids_moved_navigation_card():
  from openpilot.starpilot.system.android_auto.projection_layout import projection_customization
  viewport = (2880, 1080)
  doc = default_layout_for_viewport(viewport)
  rect = SimpleNamespace(x=30, y=30, width=2820, height=1020)
  state = road(projection_customization(doc, default_document()))
  first = source_panel_bounds(state, 200, rect)
  assert first is not None
  doc['widgets']['nav_card'].update(x=first[0], y=first[1], enabled=True)
  state = road(projection_customization(doc, default_document()))
  moved = source_panel_bounds(state, 200, rect)
  if moved is not None:
    x, y, width, height = moved
    nx, ny = doc['widgets']['nav_card']['x'], doc['widgets']['nav_card']['y']
    assert x + width <= nx or x >= nx + 560 or y + height <= ny or y >= ny + 195
