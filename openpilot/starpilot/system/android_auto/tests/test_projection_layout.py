"""CPU-only screen persistence and isolated AA placement document."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from openpilot.starpilot.system.android_auto.display_profile import record_screen, read_screen
from openpilot.starpilot.system.android_auto.projection_layout import (
  default_layout, validate_layout, decode_layout, layout_metadata, projection_customization, ProjectionLayoutSource,
  PROJECTION_WIDGETS, NAV_CARD, NAV_MAP, FAVORITE_WIDGETS, CAR_EXIT, placement_size,
)
from openpilot.starpilot.ui.onroad_customization import CLOCK_WIDGET, MODE_WIDGET, default_document, customization_metadata
from openpilot.starpilot.saved_document import commit_exact

SCREEN = {'version': 1, 'width': 1280, 'height': 720, 'margin_width': 0,
          'margin_height': 240, 'fps': 60, 'config_index': 0}


class TestProjectionLayout(unittest.TestCase):
  def test_gamma_trial_is_opt_in_and_strictly_boolean(self):
    document = default_layout(SCREEN)
    self.assertFalse(document['largeUiGammaTrial'])
    document['largeUiGammaTrial'] = True
    self.assertTrue(validate_layout(document, SCREEN)['largeUiGammaTrial'])
    document.pop('largeUiGammaTrial')
    self.assertFalse(validate_layout(document, SCREEN)['largeUiGammaTrial'])
    for value in (1, 0, 'true', None, [], {}):
      with self.subTest(value=value), self.assertRaises(ValueError):
        validate_layout({**document, 'largeUiGammaTrial': value}, SCREEN)

  def test_screen_roundtrip_omits_identity(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'screen.json'
      self.assertIsNone(read_screen(path))
      record_screen({**SCREEN, 'channel': 2, 'address': 'private'}, path)
      self.assertEqual(read_screen(path), SCREEN)
      self.assertNotIn('private', path.read_text())
      self.assertEqual(path.stat().st_mode & 0o777, 0o600)
      path.write_bytes(b'x' * 2049)
      self.assertIsNone(read_screen(path))

  def test_invalid_geometry_never_overwrites_last_good(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'screen.json'
      record_screen(SCREEN, path)
      for change in [{'margin_height': 720}, {'width': 999}, {'fps': True}]:
        with self.assertRaises(ValueError):
          record_screen({**SCREEN, **change}, path)
      self.assertEqual(read_screen(path), SCREEN)

  def test_dynamic_defaults_and_native_metadata_unchanged(self):
    original = customization_metadata()
    document = default_layout(SCREEN)
    self.assertEqual(document['canvas'], {'width': 2880, 'height': 1080})
    self.assertEqual(validate_layout(document, SCREEN), document)
    self.assertEqual(layout_metadata(SCREEN)['reservedZones'], [])
    self.assertEqual(customization_metadata(), original)

  def test_overlap_allowed_and_edges_finite_enforced(self):
    document = default_layout(SCREEN)
    document['widgets']['driver_monitor'].update(x=88, y=75)
    validate_layout(document, SCREEN)
    for number in [float('nan'), float('inf'), -1, True, 99999]:
      broken = copy.deepcopy(document)
      broken['widgets']['current_speed']['x'] = number
      with self.assertRaises(ValueError):
        validate_layout(broken, SCREEN)
    with self.assertRaises(ValueError):
      decode_layout(b'{"version":1,"version":1}', SCREEN)

  def test_projection_offsets_are_applied_once_and_separate(self):
    base = default_document()
    before = copy.deepcopy(base)
    document = default_layout(SCREEN)
    converted = projection_customization(document, base)
    native = {key: value for key, value in converted['layouts']['large'].items() if key not in PROJECTION_WIDGETS}
    self.assertEqual(native, base['layouts']['large'])
    self.assertEqual(converted['layouts']['large'][NAV_MAP], document['widgets'][NAV_MAP])
    document['widgets']['current_speed']['x'] += 100
    converted = projection_customization(document, base)
    self.assertEqual(converted['layouts']['large']['current_speed']['x'], 740)
    self.assertEqual(converted['layouts']['compact'], base['layouts']['compact'])
    self.assertEqual(base, before)

  def test_projection_clock_format_is_independent_and_migrates(self):
    document = default_layout(SCREEN)
    self.assertFalse(document['clock24Hour'])
    document['clock24Hour'] = True
    self.assertTrue(projection_customization(document, default_document())['clock24Hour'])
    document.pop('clock24Hour')
    self.assertFalse(validate_layout(document, SCREEN)['clock24Hour'])
    document['clock24Hour'] = 1
    with self.assertRaisesRegex(ValueError, 'clock format'):
      validate_layout(document, SCREEN)

  def test_new_optional_widgets_preserve_saved_projection_layout(self):
    for key in (MODE_WIDGET, CLOCK_WIDGET):
      with self.subTest(key=key):
        document = default_layout(SCREEN)
        self.assertFalse(document['widgets'].pop(key)['enabled'])
        document['widgets']['current_speed'].update(x=300, y=400, enabled=False)
        migrated = validate_layout(document, SCREEN)
        self.assertFalse(migrated['widgets'][key]['enabled'])
        self.assertEqual({name: value for name, value in migrated['widgets'].items() if name != key}, document['widgets'])
        migrated['widgets'][key].update(enabled=True, x=500, y=200)
        self.assertEqual(validate_layout(migrated, SCREEN), migrated)
        converted = projection_customization(migrated, default_document())
        self.assertEqual(converted['layouts']['large'][key]['x'] + (migrated['canvas']['width'] - 1860) / 2, 500)

  def test_favorite_display_migrates_and_uses_its_actual_footprint(self):
    document = default_layout(SCREEN)
    metadata = layout_metadata(SCREEN)
    for key in FAVORITE_WIDGETS:
      document['widgets'][key].pop('display')
    original = copy.deepcopy(document)
    migrated = validate_layout(document, SCREEN)
    self.assertEqual(document, original)
    self.assertTrue(all(migrated['widgets'][key]['display'] == 'words' for key in FAVORITE_WIDGETS))
    home = migrated['widgets']['nav_home']
    home.update(display='icons', enabled=True, x=2740)
    self.assertEqual(placement_size('nav_home', metadata['widgets']['nav_home'], home), (110, 110))
    validated = validate_layout(migrated, SCREEN)
    self.assertEqual(projection_customization(validated, default_document())['layouts']['large']['nav_home'], home)
    self.assertEqual(validated['widgets']['nav_work']['display'], 'words')
    for display in ('words', 'emoji', None, True, [], {}):
      broken = copy.deepcopy(migrated)
      broken['widgets']['nav_home']['display'] = display
      with self.assertRaises(ValueError):
        validate_layout(broken, SCREEN)

  def test_existing_exact_commit_adapter_checks_revision_and_authority(self):
    with tempfile.TemporaryDirectory() as directory:
      source = ProjectionLayoutSource(Path(directory) / 'layouts/document.json')
      source.prepare()
      raw = json.dumps(default_layout(SCREEN)).encode()
      args = {'key': 'projection', 'max_bytes': 16384, 'raw': raw, 'expected': None, 'temp_prefix': '.aa-test-'}
      self.assertFalse(commit_exact(source, authorized=lambda: False, **args).committed)
      result = commit_exact(source, authorized=lambda: True, **args)
      self.assertTrue(result.committed and result.verified)
      self.assertFalse(commit_exact(source, authorized=lambda: True, **args).committed)

  def test_android_auto_widgets_are_added_to_older_layouts(self):
    document = default_layout(SCREEN)
    older = copy.deepcopy(document)
    for key in PROJECTION_WIDGETS:
      del older['widgets'][key]
    older['widgets']['current_speed']['x'] += 20
    upgraded = validate_layout(older, SCREEN)
    self.assertEqual(upgraded['widgets'][NAV_MAP], document['widgets'][NAV_MAP])
    self.assertEqual(upgraded['widgets'][NAV_CARD], document['widgets'][NAV_CARD])
    self.assertEqual(upgraded['widgets']['current_speed']['x'], document['widgets']['current_speed']['x'] + 20)
    self.assertFalse(upgraded['widgets'][NAV_MAP]['enabled'], 'the map is something you add')
    self.assertTrue(upgraded['widgets'][NAV_CARD]['enabled'], 'the turn card keeps showing where it always did')
    self.assertTrue(upgraded['widgets'][CAR_EXIT]['enabled'], 'the escape control is added and always available')
    missing_native = copy.deepcopy(document)
    del missing_native['widgets']['current_speed']
    with self.assertRaises(ValueError):
      validate_layout(missing_native, SCREEN)

  def test_car_exit_is_required_movable_and_frontmost(self):
    document = default_layout(SCREEN)
    metadata = layout_metadata(SCREEN)
    self.assertEqual(metadata['widgets'][CAR_EXIT]['label'], 'Exit to car')
    self.assertTrue(metadata['widgets'][CAR_EXIT]['required'])
    self.assertTrue(metadata['widgets'][CAR_EXIT]['frontmost'])
    self.assertEqual((metadata['widgets'][CAR_EXIT]['width'], metadata['widgets'][CAR_EXIT]['height']), (110, 110))
    self.assertTrue(document['widgets'][CAR_EXIT]['enabled'])
    self.assertEqual((document['widgets'][CAR_EXIT]['x'], document['widgets'][CAR_EXIT]['y']), (30, 940))
    document['widgets'][CAR_EXIT].update(x=30, y=30)
    self.assertEqual(validate_layout(document, SCREEN)['widgets'][CAR_EXIT]['x'], 30)
    order = metadata['widgetOrder']
    document['widgetOrder'] = [CAR_EXIT, *(key for key in order if key != CAR_EXIT)]
    self.assertEqual(validate_layout(document, SCREEN)['widgetOrder'][-1], CAR_EXIT)
    document['widgets'][CAR_EXIT]['enabled'] = False
    with self.assertRaisesRegex(ValueError, 'Required'):
      validate_layout(document, SCREEN)

  def test_map_overlay_size_opacity_and_edges(self):
    document = default_layout(SCREEN)
    metadata = layout_metadata(SCREEN)
    box = metadata['widgets'][NAV_MAP]['box']
    placement = document['widgets'][NAV_MAP]
    self.assertEqual(set(placement), {'x', 'y', 'enabled', 'width', 'height', 'opacity'})
    placement.update(x=30, y=30, width=box['maxWidth'], height=box['maxHeight'], opacity=15, enabled=True)
    validate_layout(document, SCREEN)
    for change in ({'width': box['maxWidth'] + 1}, {'height': box['minHeight'] - 1}, {'opacity': 14},
                   {'opacity': 101}, {'opacity': 70.0}, {'width': 600.5}, {'x': 31},
                   {'extra': 1}):
      broken = copy.deepcopy(document)
      broken['widgets'][NAV_MAP].update(change)
      with self.assertRaises(ValueError, msg=str(change)):
        validate_layout(broken, SCREEN)

  def test_map_defaults_scale_with_the_screen(self):
    from openpilot.starpilot.system.android_auto.projection_layout import default_layout_for_viewport
    small, wide = default_layout_for_viewport((1860, 1080)), default_layout_for_viewport((2880, 1080))
    for document in (small, wide):
      card, overlay = document['widgets'][NAV_CARD], document['widgets'][NAV_MAP]
      self.assertEqual(card['x'] + 560, overlay['x'] + overlay['width'], 'right edges line up')
      self.assertGreaterEqual(overlay['y'], card['y'] + 195)
      self.assertLessEqual(overlay['y'] + overlay['height'], document['canvas']['height'] - 30)
    self.assertLess(small['widgets'][NAV_MAP]['width'], wide['widgets'][NAV_MAP]['width'])
