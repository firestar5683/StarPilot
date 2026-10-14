"""Pinned numeric atlas and the larger stack's saved/touch geometry."""
from dataclasses import replace
import re
from types import SimpleNamespace

from PIL import Image
import pyray as rl

from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile, default_font_directory, font_filename, font_path, validate_bitmap_font
from openpilot.starpilot.ui.large_speed_geometry import WIDTH, PADDING
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
    bounds = atlas.crop((x, y, x + w, y + h)).getchannel('A').getbbox()
    assert bounds is not None and bounds[0] > 0


def test_three_digit_values_units_and_long_status_fit_actual_fonts():
  owns_context = not rl.is_window_ready()
  if owns_context:
    rl.init_window(128, 128, "DINish native font fixture")
  try:
    assert rl.is_window_ready(), "Native font fixture requires a real graphics context"
    fonts = BitmapFonts(Profile.LARGE, default_font_directory())
    try:
      room = WIDTH - 2 * PADDING
      def fitted(text, role, size, extra=0.):
        # The card shrinks a line one point at a time until it fits, as UnifiedSpeedWidget.render does.
        while fonts.measure(text, role, size).width + extra > room:
          size -= 1
        return size
      for value in ('88', '99', '100', '110', '120', '199', '–'):
        # Three-digit mph stays full size; three-digit km/h may shrink slightly.
        assert fitted(value, FontRole.SPEED, 112, 14 + fonts.measure('mph', FontRole.NORMAL, 28).width) == 112
        assert fitted(value, FontRole.SPEED, 112, 14 + fonts.measure('km/h', FontRole.NORMAL, 28).width) >= 106
      for status in ('Using accelerator', 'Overridden', 'Above set speed', 'Matches set speed', 'Override saved',
                     'Using set speed', 'Using speed limit', 'Matches speed limit', 'Unavailable', 'Cruise off',
                     'Set-speed override'):
        assert fitted(status, FontRole.NORMAL, 30) >= 28
      top, bottom = fonts.vertical_ink('120', FontRole.SPEED, 112)
      assert 85 <= bottom - top <= 90
    finally:
      fonts.close()
  finally:
    if owns_context and rl.is_window_ready():
      rl.close_window()


def test_v5_geometry_migrates_and_keeps_custom_actions_independent():
  doc = default_document()
  doc['version'] = 5
  doc['speedSources'] = True
  doc['layouts']['large']['cruise_limits'].update(x=1550, y=638)
  doc['layouts']['large']['speed_limit_actions'].update(x=1550, y=954)
  migrated = validate_document(doc)
  assert migrated['version'] == 7
  assert migrated['layouts']['large']['cruise_limits'] == {'x': 1510, 'y': 580, 'enabled': True}
  assert migrated['layouts']['large']['speed_limit_actions'] == {'x': 1510, 'y': 942, 'enabled': True}
  assert migrated['speedSources'] is True
  assert doc['layouts']['large']['cruise_limits']['x'] == 1550
  assert validate_document(migrated) == migrated
  doc['layouts']['large']['cruise_limits'].update(x=88, y=75)
  doc['layouts']['large']['speed_limit_actions'].update(x=88, y=447)
  assert validate_document(doc)['layouts']['large']['speed_limit_actions']['y'] == 567


def test_pending_buttons_name_both_speeds():
  state = road()
  state = replace(state, speed_limit=replace(state.speed_limit, pending_speed_limit_mps=25, pending_adjusted_limit_mps=24,
                                             accepted_adjusted_limit_mps=22))
  apply, keep = slc_controls(Profile.LARGE, state)
  assert apply.bounds == (88, 611, 242, 675)
  assert keep.bounds == (254, 611, 408, 675)
  # Each choice says the speed it leaves you at: the new target or the limit already in use.
  assert (apply.label, keep.label) == ('Apply 54', 'Keep 49')
  no_current = replace(state, speed_limit=replace(state.speed_limit, accepted_adjusted_limit_mps=None))
  assert slc_controls(Profile.LARGE, no_current)[1].label == 'Keep'


def test_projection_v1_layout_migrates_without_losing_other_widgets():
  viewport = (2880, 1080)
  doc = default_layout_for_viewport(viewport)
  doc['version'] = 1
  doc['widgets']['speed_limit_actions'].update(x=88, y=447)
  doc['widgets']['current_speed'].update(x=1400, y=100)
  migrated = validate_layout_for_viewport(doc, viewport)
  assert migrated['version'] == 3
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
  assert migrated['widgets']['cruise_limits']['x'] == 1510
  assert migrated['widgets']['speed_limit_actions'] == {'x': 1510, 'y': 567, 'enabled': True}


