"""CPU-only screen persistence and isolated AA placement document."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from openpilot.starpilot.system.android_auto.display_profile import record_screen, read_screen
from openpilot.starpilot.system.android_auto.projection_layout import (
  default_layout, validate_layout, decode_layout, layout_metadata, projection_customization, ProjectionLayoutSource,
)
from openpilot.starpilot.ui.onroad_customization import default_document, customization_metadata
from openpilot.starpilot.saved_document import commit_exact

SCREEN = {'version': 1, 'width': 1280, 'height': 720, 'margin_width': 0,
          'margin_height': 240, 'fps': 60, 'config_index': 0}


class TestProjectionLayout(unittest.TestCase):
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
    self.assertEqual(converted['layouts']['large'], base['layouts']['large'])
    document['widgets']['current_speed']['x'] += 100
    converted = projection_customization(document, base)
    self.assertEqual(converted['layouts']['large']['current_speed']['x'], 740)
    self.assertEqual(converted['layouts']['compact'], base['layouts']['compact'])
    self.assertEqual(base, before)

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
