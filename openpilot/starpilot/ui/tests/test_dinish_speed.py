"""Pinned numeric atlas and the larger stack's saved/touch geometry."""
from dataclasses import replace
from itertools import product
import io
import re
from types import SimpleNamespace

from PIL import Image
import numpy as np
import pyray as rl

from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile, default_font_directory, font_filename, font_path, validate_bitmap_font
from openpilot.starpilot.ui.large_speed_geometry import WIDTH, PADDING
from openpilot.starpilot.ui.onroad_customization import default_document, validate_document
from openpilot.starpilot.ui.onroad_state import SpeedLimitObservation, slc_controls
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


def test_card_alignment_uses_visible_glyphs_and_centres_the_number():
  from unittest.mock import patch
  from openpilot.starpilot.ui.onroad_large_widgets import UnifiedSpeedWidget
  from openpilot.starpilot.ui.layout_preview_renderer import sample_state
  owns_context = not rl.is_window_ready()
  if owns_context:
    rl.init_window(128, 128, "DINish native font fixture")
  try:
    fonts = BitmapFonts(Profile.LARGE, default_font_directory())
    try:
      # The fixed-width speed digits carry wide side bearings; their ink must still meet the padding.
      left, right = fonts.horizontal_ink('55', FontRole.SPEED, 112)
      assert left > 5 and right < fonts.measure('55', FontRole.SPEED, 112).width - 5
      configurations = product(('left', 'center', 'right'), (False, True), (7, 55, 100, 199, None),
                               ('split', 'max_only', 'limit_only'))
      for align, metric, value, mode in configurations:
        document = default_document()
        document['speedAlign'] = align
        document['showMaxSpeed'] = mode != 'limit_only'
        state = sample_state('engaged', document)
        factor = 3.6 if metric else 2.2369362921
        speed = value / factor if value is not None else None
        observation = (SpeedLimitObservation() if mode == 'max_only' else
                       replace(state.speed_limit, accepted_adjusted_limit_mps=speed, effective_cluster_target_mps=speed))
        state = replace(state, metric=metric, cruise_kph=speed * 3.6 if speed is not None else None, speed_limit=observation)
        card = document['layouts']['large']['cruise_limits']
        calls = []
        with patch.object(fonts, 'draw', lambda text, role, size, x, y, *a, calls=calls, **k: calls.append((text, role, size, x, y))), \
             patch('openpilot.starpilot.ui.onroad_large_widgets.draw_control_card'), patch.object(rl, 'draw_line_ex'):
          UnifiedSpeedWidget(fonts).render(rl.Rectangle(30, 30, 1800, 1020), state)
        units = {'mph', 'km/h'}
        for index, (text, role, size, x, y) in enumerate(calls):
          ink_left, ink_right = fonts.horizontal_ink(text, role, size)
          if align == 'left' and text not in units:
            assert abs(x + ink_left - (card['x'] + PADDING)) < .5, text
          elif align == 'right' and text not in units:
            assert abs(x + ink_right - (card['x'] + WIDTH - PADDING)) < .5, text
          elif align == 'center':
            assert abs(x + (ink_left + ink_right) / 2 - (card['x'] + WIDTH / 2)) < .5, text
          assert card['x'] + PADDING - .5 <= x + ink_left and x + ink_right <= card['x'] + WIDTH - PADDING + .5, (align, text)
          if role == FontRole.SPEED and text != '–':
            unit, unit_role, unit_size, unit_x, unit_y = calls[index + 1]
            assert unit == ('km/h' if metric else 'mph')
            unit_left, unit_right = fonts.horizontal_ink(unit, unit_role, unit_size)
            unit_top, unit_bottom = fonts.vertical_ink(unit, unit_role, unit_size)
            _, number_bottom = fonts.vertical_ink(text, role, size)
            if align == 'center':
              assert unit_y + unit_top >= y + number_bottom + 6
              footer, footer_role, footer_size, _, footer_y = calls[index + 2]
              footer_top, _ = fonts.vertical_ink(footer, footer_role, footer_size)
              assert unit_y + unit_bottom + 6 <= footer_y + footer_top
            elif align == 'right':
              assert abs(x + ink_left - (unit_x + unit_right) - 14) < .5
              assert abs(y + number_bottom - (unit_y + unit_bottom)) < .5
            else:
              assert abs(unit_x + unit_left - (x + ink_right) - 14) < .5
              assert abs(y + number_bottom - (unit_y + unit_bottom)) < .5
    finally:
      fonts.close()
  finally:
    if owns_context and rl.is_window_ready():
      rl.close_window()


def test_galaxy_card_pixels_align_without_reading_font_textures():
  from unittest.mock import patch
  from openpilot.starpilot.ui.layout_preview_renderer import _Canvas, sample_state
  from openpilot.starpilot.ui.onroad_large_widgets import UnifiedSpeedWidget
  from openpilot.starpilot.system.android_auto.projection_layout import (
    default_layout_for_viewport, projection_customization, validate_layout_for_viewport)

  original_readback = rl.load_image_from_texture

  def mobile_readback(texture):
    image = original_readback(texture)
    # Raylib's GLES texture readback unbinds the framebuffer instead of restoring
    # the active preview target. Reproduce that side effect on desktop too.
    rl.rl_disable_framebuffer()
    return image

  owns_context = not rl.is_window_ready()
  if owns_context:
    rl.init_window(128, 128, 'Galaxy card alignment fixture')
  target = rl.load_render_texture(*Profile.LARGE.size)
  try:
    for align, projection in product(('center', 'right'), (False, True)):
      # Start with cold font metrics, as when Galaxy creates its preview canvas.
      with BitmapFonts(Profile.LARGE, default_font_directory()) as fonts:
        document = default_document()
        document['speedAlign'] = align
        viewport = (1920, 1080) if projection else None
        if projection:
          layout = default_layout_for_viewport(viewport)
          layout['speedAlign'] = align
          layout['widgets']['cruise_limits']['opacity'] = 50
          document = projection_customization(validate_layout_for_viewport(layout, viewport), document)
        else:
          document['widgetColors']['large']['cruise_limits'] = {'cardFill': '#10191F80'}
          document = validate_document(document)
        state = sample_state('engaged', document)  # MAX 55 / Your ceiling, SLC 49.
        widget = UnifiedSpeedWidget(fonts)
        canvas = _Canvas.__new__(_Canvas)
        canvas.profile, canvas.viewport, canvas.fonts, canvas.target = Profile.LARGE, viewport, fonts, target
        canvas.view = SimpleNamespace(_ordered_widgets=lambda content, state, widget=widget, **kw: widget.render(content, state))
        canvas._settle = lambda state: None
        with patch.dict('openpilot.starpilot.ui.layout_preview_renderer.RUNTIME_PREVIEW_WIDGETS', large=('cruise_limits',)), \
             patch.object(rl, 'load_image_from_texture', side_effect=mobile_readback) as readback:
          png = canvas.render_widget_art(state, document['layouts']['large'])
          # A saved 50% background must show on the first frame, without a slider
          # edit triggering another render after the font metrics are warm.
          assert png == canvas.render_widget_art(state, document['layouts']['large'])
          # Only the completed preview is read; measuring glyphs must never change its framebuffer.
          assert readback.call_count == 2
          assert readback.call_args.args[0].id == target.texture.id
        with Image.open(io.BytesIO(png)) as image:
          pixels = np.asarray(image.convert('RGBA'))
        assert pixels[100, 10, 3] == 128
        ink = (pixels[..., :3].min(axis=2) > 120) & (pixels[..., 3] > 200)
        rows = np.flatnonzero(ink.any(axis=1))
        lines = np.split(rows, np.flatnonzero(np.diff(rows) > 1) + 1)
        assert len(lines) == (9 if align == 'center' else 7)
        for line in lines:
          columns = np.flatnonzero(ink[line].any(axis=0))
          if align == 'center':
            assert abs((columns[0] + columns[-1] + 1) / 2 - WIDTH / 2) <= 1.5
          else:
            assert abs(columns[-1] + 1 - (WIDTH - PADDING)) <= 1.5
  finally:
    rl.unload_render_texture(target)
    if owns_context:
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

