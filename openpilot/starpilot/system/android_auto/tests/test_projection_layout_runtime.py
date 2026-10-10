"""Connection-scoped saved layout and real frozen-state replacement regressions."""
import copy
import fcntl
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from openpilot.starpilot.system.android_auto.display_profile import record_screen, read_screen
from openpilot.starpilot.system.android_auto.projection_layout import ProjectionLayoutSource, default_layout_for_viewport
from openpilot.starpilot.system.android_auto.projection_layout_runtime import load_projection_layout
from openpilot.starpilot.system.android_auto.tests import test_projection_onroad_boundary as boundary
projection = boundary.projection
from openpilot.starpilot.ui.onroad_customization import default_document

SCREEN = {'version': 1, 'width': 1280, 'height': 720, 'margin_width': 0,
          'margin_height': 240, 'fps': 60, 'config_index': 0}


class TestProjectionLayoutRuntime(unittest.TestCase):
  def test_saved_gamma_trial_reaches_only_projection_camera(self):
    for enabled in (False, True):
      with self.subTest(enabled=enabled):
        helper = boundary.TestProjectionOnroad()
        native, _ = helper.dependencies()
        document = default_layout_for_viewport((2880, 1080))
        document['largeUiGammaTrial'] = enabled
        view = projection.ProjectionOnroad(dependencies=native, customization=document)
        try:
          self.assertIs(view.camera.large_ui_gamma_trial, enabled)
          # Pacing follows the stream selected during rendering, not before it.
          view.camera.stream_type = 0
          def render(*args, camera=view.camera, **kwargs):
            camera.stream_type = 2
          view.camera.render_camera_model_layer = render
          view._camera_layer(None, SimpleNamespace(customization=default_document()))
          self.assertEqual(view.camera_stream, 2)
        finally:
          view.close()

  def test_absent_corrupt_wrong_canvas_default_without_rewriting(self):
    with tempfile.TemporaryDirectory() as directory:
      source = ProjectionLayoutSource(Path(directory) / 'layouts/document.json')
      source.prepare()
      viewport = (2880, 1080)
      defaults = default_layout_for_viewport(viewport)
      self.assertEqual(load_projection_layout(viewport, source), defaults)
      for raw in (b'bad', b'x' * 16385, json.dumps(default_layout_for_viewport((1860, 1240))).encode()):
        source.path.write_bytes(raw)
        self.assertEqual(load_projection_layout(viewport, source), defaults)
        self.assertEqual(source.path.read_bytes(), raw)

  def test_saved_layout_loaded_once_and_next_connection_observes_save(self):
    with tempfile.TemporaryDirectory() as directory:
      source = ProjectionLayoutSource(Path(directory) / 'layouts/document.json')
      source.prepare()
      original = default_layout_for_viewport((2880, 1080))
      source.path.write_text(json.dumps(original))
      connection = load_projection_layout((2880, 1080), source)
      changed = copy.deepcopy(original)
      changed['widgets']['current_speed']['x'] += 60
      source.path.write_text(json.dumps(changed))
      self.assertEqual(connection, original)
      self.assertEqual(load_projection_layout((2880, 1080), source), changed)

  def test_screen_writer_lock_contention_preserves_previous_receipt(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'screen.json'
      record_screen(SCREEN, path)
      before = path.read_bytes()
      descriptor = os.open(Path(directory) / '.lock', os.O_RDONLY)
      try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with self.assertRaises(BlockingIOError):
          record_screen(SCREEN | {'config_index': 1}, path)
        self.assertEqual(path.read_bytes(), before)
      finally:
        os.close(descriptor)
      record_screen(SCREEN | {'config_index': 1}, path)
      self.assertEqual(read_screen(path)['config_index'], 1)

  def test_real_onroad_dataclass_replacement_cache_and_shared_color_refresh(self):
    from openpilot.starpilot.ui.onroad_state import OnroadState, SpeedLimitObservation
    helper = boundary.TestProjectionOnroad()
    native, _ = helper.dependencies()
    native.ui_state.started = True
    base = default_document()
    before = copy.deepcopy(base)
    state = OnroadState(False, False, None, None, SpeedLimitObservation(), customization=base)
    rendered = []
    native.adapter = lambda *_: SimpleNamespace(build=lambda *_a, **_k: SimpleNamespace(onroad=state))
    layout = default_layout_for_viewport((2880, 1080))
    layout['widgets']['current_speed']['x'] += 60
    view = projection.ProjectionOnroad(dependencies=native, viewport=(2880, 1080), customization=layout)
    self.addCleanup(view.close)
    view.onroad.render = rendered.append
    # The frame loop must not open saved files; conversion is cached by base identity.
    with patch('openpilot.starpilot.saved_source.read_saved', side_effect=AssertionError('frame file read')):
      view.render()
      view.render()
      self.assertIs(rendered[0].customization, rendered[1].customization)
      self.assertIsNot(rendered[0], state)
      self.assertEqual(state.customization, before)
      self.assertEqual(rendered[0].customization['layouts']['compact'], before['layouts']['compact'])
      old_projected = rendered[-1].customization
      base = copy.deepcopy(base)
      base['palette']['text'] = '#123456FF'
      state = OnroadState(False, False, None, None, SpeedLimitObservation(), customization=base)
      view.render()
      self.assertIsNot(rendered[-1].customization, old_projected)
      self.assertEqual(rendered[-1].customization['palette']['text'], '#123456FF')
      self.assertEqual(rendered[-1].customization['layouts']['large']['current_speed']['x'], 700)

  def test_real_onroad_state_unchanged_without_projection_document(self):
    from openpilot.starpilot.ui.onroad_state import OnroadState, SpeedLimitObservation
    helper = boundary.TestProjectionOnroad()
    native, _ = helper.dependencies()
    native.ui_state.started = True
    state = OnroadState(False, False, None, None, SpeedLimitObservation())
    rendered = []
    native.adapter = lambda *_: SimpleNamespace(build=lambda *_a, **_k: SimpleNamespace(onroad=state))
    view = projection.ProjectionOnroad(dependencies=native, viewport=(2880, 1080))
    self.addCleanup(view.close)
    view.onroad.render = rendered.append
    view.render()
    self.assertIs(rendered[0], state)


if __name__ == '__main__':
  unittest.main()
