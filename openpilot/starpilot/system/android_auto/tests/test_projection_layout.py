"""CPU-only screen persistence and isolated AA placement document."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from openpilot.starpilot.system.android_auto.display_profile import record_screen, read_screen
from openpilot.starpilot.system.android_auto.projection_layout import (
  default_layout, validate_layout, decode_layout, layout_metadata, projection_customization, ProjectionLayoutSource,
  PROJECTION_WIDGETS, NAV_CARD, NAV_MAP, FAVORITE_WIDGETS, BOOKMARK_WIDGET, CAR_EXIT, ACTION_WIDGETS, placement_size,
)
from openpilot.starpilot.ui.onroad_customization import CLOCK_WIDGET, MODE_WIDGET, STOPPED_TIMER_WIDGET, default_document, customization_metadata
from openpilot.starpilot.saved_document import commit_exact

SCREEN = {'version': 1, 'width': 1280, 'height': 720, 'margin_width': 0,
          'margin_height': 240, 'fps': 60, 'config_index': 0}


class TestProjectionLayout(unittest.TestCase):
  def test_stopped_timer_migrates_and_keeps_independent_placement_and_order(self):
    document = default_layout(SCREEN)
    metadata = layout_metadata(SCREEN)
    expected = document['widgets'].pop(STOPPED_TIMER_WIDGET)
    self.assertFalse(expected['enabled'])
    self.assertEqual((metadata['widgets'][STOPPED_TIMER_WIDGET]['width'],
                      metadata['widgets'][STOPPED_TIMER_WIDGET]['height']), (660, 168))
    document['widgetOrder'] = [key for key in metadata['widgetOrder'] if key != STOPPED_TIMER_WIDGET]
    document['widgets']['current_speed']['x'] += 20
    before = copy.deepcopy(document)
    migrated = validate_layout(document, SCREEN)
    self.assertEqual(document, before)
    self.assertEqual(migrated['widgets'][STOPPED_TIMER_WIDGET], expected)
    self.assertEqual(migrated['widgets']['current_speed'], document['widgets']['current_speed'])
    self.assertEqual(migrated['widgetOrder'], [*document['widgetOrder'][:-1], STOPPED_TIMER_WIDGET, CAR_EXIT])
    migrated['widgets'][STOPPED_TIMER_WIDGET].update(enabled=True, x=450, y=600)
    decoded = decode_layout(json.dumps(migrated).encode(), SCREEN)
    base = default_document()
    converted = projection_customization(decoded, base)
    self.assertEqual(converted['layouts']['large'][STOPPED_TIMER_WIDGET], {'enabled': True, 'x': 450, 'y': 600})
    self.assertEqual(converted['layouts']['compact'], base['layouts']['compact'])
    self.assertFalse(base['layouts']['compact'][STOPPED_TIMER_WIDGET]['enabled'])

  def test_bookmark_is_opt_in_and_upgrades_existing_layouts_without_changing_them(self):
    document = default_layout(SCREEN)
    metadata = layout_metadata(SCREEN)
    bookmark = document['widgets'].pop(BOOKMARK_WIDGET)
    self.assertFalse(bookmark['enabled'])
    self.assertEqual((bookmark['opacity'], bookmark['background'], bookmark['display']), (100, True, 'words'))
    document['widgets']['current_speed']['x'] += 20
    document['widgetOrder'] = [key for key in metadata['widgetOrder'] if key != BOOKMARK_WIDGET]
    original = copy.deepcopy(document)
    migrated = validate_layout(document, SCREEN)
    self.assertEqual(document, original)
    self.assertEqual(migrated['widgets'].pop(BOOKMARK_WIDGET), bookmark)
    self.assertEqual(migrated['widgets'], original['widgets'])
    self.assertEqual(migrated['widgetOrder'], [*original['widgetOrder'][:-1], BOOKMARK_WIDGET, CAR_EXIT])
    bookmark.update(enabled=True, display='icons', opacity=35, background=False, x=2740)
    migrated['widgets'][BOOKMARK_WIDGET] = bookmark
    self.assertEqual(placement_size(BOOKMARK_WIDGET, metadata['widgets'][BOOKMARK_WIDGET], bookmark), (110, 110))
    self.assertEqual(validate_layout(migrated, SCREEN), migrated)
    self.assertEqual(decode_layout(json.dumps(migrated).encode(), SCREEN), migrated)

  def test_action_appearance_migrates_and_survives_serialization(self):
    document = default_layout(SCREEN)
    for key in ACTION_WIDGETS:
      document['widgets'][key].pop('opacity')
      document['widgets'][key].pop('background')
    original = copy.deepcopy(document)
    migrated = validate_layout(document, SCREEN)
    self.assertEqual(document, original)
    for key in ACTION_WIDGETS:
      self.assertEqual(migrated['widgets'][key], {**document['widgets'][key], 'opacity': 100, 'background': True})
    for key, opacity in zip(ACTION_WIDGETS, (0, 45, 70, 100), strict=True):
      migrated['widgets'][key].update(opacity=opacity, background=False)
    decoded = decode_layout(json.dumps(migrated).encode(), SCREEN)
    self.assertEqual(decoded, migrated)
    projected = projection_customization(decoded, default_document())
    for key in ACTION_WIDGETS:
      self.assertEqual(projected['layouts']['large'][key], migrated['widgets'][key])

  def test_action_appearance_is_strictly_validated(self):
    for key in ACTION_WIDGETS:
      for field, values in [('opacity', (-1, 101, 50.5, True, None, '50')), ('background', (0, 1, None, 'false', [], {}))]:
        for value in values:
          document = default_layout(SCREEN)
          document['widgets'][key][field] = value
          with self.subTest(key=key, field=field, value=value), self.assertRaises(ValueError):
            validate_layout(document, SCREEN)

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

  def test_border_switches_are_separate_and_strictly_boolean(self):
    document = default_layout(SCREEN)
    self.assertIs(document['blindSpotBorder'], False)
    self.assertIs(document['signalBorder'], False)
    for key in ('blindSpotBorder', 'signalBorder', 'hidePersonalityAlerts', 'wheelPedalFeedback', 'leadIndicator'):
      older = {k: v for k, v in document.items() if k != key}
      self.assertEqual(validate_layout(older, SCREEN)[key], document[key], 'older layouts get the defaults')
      flipped = validate_layout({**document, key: not document[key]}, SCREEN)
      self.assertEqual(flipped[key], not document[key])
      for value in (1, 0, 'true', None, [], {}):
        with self.subTest(key=key, value=value), self.assertRaises(ValueError):
          validate_layout({**document, key: value}, SCREEN)

  def test_lead_info_starts_off_and_takes_only_known_choices(self):
    document = default_layout(SCREEN)
    self.assertEqual((document['leadIndicator'], document['leadInfo']), (False, 'Off'))
    older = {k: v for k, v in document.items() if k not in ('leadIndicator', 'leadInfo')}
    self.assertEqual(validate_layout(older, SCREEN), document, 'older layouts get the lead defaults')
    for choice in ('Off', 'Distance', 'Speed'):
      self.assertEqual(validate_layout({**document, 'leadInfo': choice}, SCREEN)['leadInfo'], choice)
    for value in ('speed', 'Both', 1, True, None, [], {}):
      with self.subTest(value=value), self.assertRaises(ValueError):
        validate_layout({**document, 'leadInfo': value}, SCREEN)

  def test_blind_spot_camera_migrates_and_survives_serialization(self):
    document = default_layout(SCREEN)
    self.assertIs(document.pop('blindSpotCamera'), False)
    self.assertIs(validate_layout(document, SCREEN)['blindSpotCamera'], False)
    document['blindSpotCamera'] = True
    self.assertEqual(decode_layout(json.dumps(document).encode(), SCREEN), document)
    for value in (1, 0, 'true', None, [], {}):
      with self.subTest(value=value), self.assertRaises(ValueError):
        validate_layout({**document, 'blindSpotCamera': value}, SCREEN)

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

  def test_cruise_background_opacity_and_sources_are_android_auto_settings(self):
    from openpilot.starpilot.system.android_auto.projection_layout import (
      default_layout_for_viewport, projection_customization, validate_layout_for_viewport)
    from openpilot.starpilot.ui.onroad_customization import rgba
    layout = default_layout_for_viewport((1920, 1080))
    self.assertEqual(layout['widgets']['cruise_limits']['opacity'], 100)
    self.assertIs(layout['speedSources'], False)
    self.assertEqual(layout['speedAlign'], 'left')
    base = default_document()
    solid = rgba(base, 'cardFill', 'large', 'cruise_limits')
    native = projection_customization(layout, base)
    self.assertEqual(rgba(native, 'cardFill', 'large', 'cruise_limits'), solid)
    self.assertNotIn('opacity', native['layouts']['large']['cruise_limits'])
    layout['widgets']['cruise_limits']['opacity'] = 40
    layout['speedSources'] = True
    native = projection_customization(validate_layout_for_viewport(layout, (1920, 1080)), base)
    self.assertEqual(rgba(native, 'cardFill', 'large', 'cruise_limits'), (*solid[:3], round(solid[3] * .4)))
    self.assertEqual(rgba(native, 'text', 'large', 'cruise_limits'), rgba(base, 'text', 'large', 'cruise_limits'))
    self.assertIs(native['speedSources'], True)
    saved = copy.deepcopy(layout)
    del saved['widgets']['cruise_limits']['opacity']
    del saved['speedSources']
    restored = validate_layout_for_viewport(saved, (1920, 1080))
    self.assertEqual((restored['widgets']['cruise_limits']['opacity'], restored['speedSources']), (100, False))
    self.assertEqual(projection_customization(validate_layout_for_viewport({**layout, 'speedAlign': 'right'}, (1920, 1080)), base)['speedAlign'], 'right')
    with self.assertRaises(ValueError):
      validate_layout_for_viewport({**layout, 'speedAlign': 'justify'}, (1920, 1080))
    for bad in (-1, 101, 50.5, True):
      layout['widgets']['cruise_limits']['opacity'] = bad
      with self.assertRaises(ValueError):
        validate_layout_for_viewport(layout, (1920, 1080))

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
    self.assertEqual((metadata['widgets'][CAR_EXIT]['width'], metadata['widgets'][CAR_EXIT]['height']), (96, 96))
    self.assertTrue(document['widgets'][CAR_EXIT]['enabled'])
    self.assertEqual((document['widgets'][CAR_EXIT]['x'], document['widgets'][CAR_EXIT]['y']), (30, 954))
    document['widgets'][CAR_EXIT].update(x=30, y=30)
    self.assertEqual(validate_layout(document, SCREEN)['widgets'][CAR_EXIT]['x'], 30)
    order = metadata['widgetOrder']
    document['widgetOrder'] = [CAR_EXIT, *(key for key in order if key != CAR_EXIT)]
    self.assertEqual(validate_layout(document, SCREEN)['widgetOrder'][-1], CAR_EXIT)
    document['widgets'][CAR_EXIT]['enabled'] = False
    with self.assertRaisesRegex(ValueError, 'Required'):
      validate_layout(document, SCREEN)

  def test_car_exit_opacity_minimum_and_saved_layout_migration(self):
    document = default_layout(SCREEN)
    self.assertEqual(layout_metadata(SCREEN)['widgets'][CAR_EXIT]['opacity']['min'], 25)
    document['widgets'][CAR_EXIT]['opacity'] = 25
    self.assertEqual(validate_layout(document, SCREEN), document)
    for opacity in (0, 24):
      document['widgets'][CAR_EXIT]['opacity'] = opacity
      with self.subTest(opacity=opacity):
        with self.assertRaisesRegex(ValueError, 'at least 25%'):
          validate_layout(document, SCREEN)
        migrated = decode_layout(json.dumps(document).encode(), SCREEN)
        self.assertEqual(migrated['widgets'][CAR_EXIT]['opacity'], 25)
        migrated['widgets'][CAR_EXIT]['opacity'] = opacity
        self.assertEqual(migrated, document, 'all other layout settings are preserved')

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
