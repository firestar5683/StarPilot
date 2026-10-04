from unittest.mock import Mock
from openpilot.starpilot.ui.presentation import BitmapFonts

from unittest.mock import patch
import unittest
from dataclasses import replace
from types import SimpleNamespace as NS

from openpilot.starpilot.ui.onroad_customization import default_document, validate_document
from openpilot.starpilot.ui.onroad_dm import DriverMonitorLayer, StableDriverStateRenderer, monitor_bounds, monitor_visible, valid_observation
from openpilot.starpilot.ui.onroad_state import AlertSize, OnroadAlert, OnroadState, SpeedLimitObservation
from openpilot.starpilot.ui.appearance_preferences import CameraViewChoice
from openpilot.starpilot.ui.presentation import Profile


def road():
  return OnroadState(True, True, 20, 80, SpeedLimitObservation())


def observation():
  return NS(isRHD=False, activePolicy='vision', visionPolicyState=NS(faceDetected=True, awarenessPercent=100, pose=NS(pitch=0.0, yaw=0.0))), NS(
    leftDriverData=NS(), rightDriverData=NS()
  )


class TestDriverMonitor(unittest.TestCase):
  def test_monitor_uses_same_frame_observation_as_other_widgets(self):
    from openpilot.starpilot.ui import runtime_app
    from openpilot.starpilot.ui.tests.test_runtime_snapshot import ui_fake, NOW

    ui = ui_fake()
    ui.is_onroad = lambda: True
    monitor, driver = observation()
    ui.sm.put('driverMonitoringState', monitor, age_ns=60_000_000)
    ui.sm.put('driverStateV2', driver, age_ns=60_000_000)
    session = object.__new__(runtime_app.StarShellSession)
    session.profile = Profile.LARGE
    session._driver_monitor_layer = Mock()
    with patch.object(runtime_app, 'ui_state', ui), patch.object(runtime_app.time, 'monotonic_ns', return_value=NOW + 180_000_000):
      session._render_driver_monitor(None, replace(road(), observed_ns=NOW))
    self.assertTrue(session._driver_monitor_layer.render.call_args.kwargs['fresh'])
    # A new frame must reject the genuinely old samples; this is not an
    # indefinite active-face hold or an action-freshness extension.
    with patch.object(runtime_app, 'ui_state', ui):
      session._render_driver_monitor(None, replace(road(), observed_ns=NOW + 201_000_000))
    self.assertFalse(session._driver_monitor_layer.render.call_args.kwargs['fresh'])

  def test_known_old_layout_migrates_without_losing_palette_positions_or_visibility(self):
    old = default_document()
    for layout in old['layouts'].values():
      for key in ('driver_monitor', 'torque_bar', 'speed_limit_actions', 'model_confidence', 'conditional_mode', 'following_distance'):
        layout.pop(key, None)
    old['palette']['text'] = '#12345678'
    old['layouts']['large']['steering_wheel'].update(x=500.5, y=600.25, enabled=False)
    migrated = validate_document(old)
    self.assertEqual(migrated['palette'], old['palette'])
    for profile, layout in old['layouts'].items():
      for key, position in layout.items():
        self.assertEqual(migrated['layouts'][profile][key], position)
      self.assertEqual(migrated['layouts'][profile]['driver_monitor'], default_document()['layouts'][profile]['driver_monitor'])
    self.assertNotIn('driver_monitor', old['layouts']['large'])

  def test_only_complete_known_old_shape_migrates(self):
    for shape in ('partial', 'unknown', 'mixed'):
      with self.subTest(shape=shape):
        document = default_document()
        del document['layouts']['large']['driver_monitor']
        del document['layouts']['large']['torque_bar']
        if shape != 'mixed':
          del document['layouts']['compact']['driver_monitor']
          del document['layouts']['compact']['torque_bar']
        if shape == 'partial':
          del document['layouts']['large']['current_speed']
        elif shape == 'unknown':
          document['layouts']['large']['unknown'] = {'x': 0, 'y': 0, 'enabled': True}
        with self.assertRaises(ValueError):
          validate_document(document)

  def test_default_large_driver_side_and_custom_position(self):
    document = default_document()
    left = monitor_bounds(document, Profile.LARGE, False)
    right = monitor_bounds(document, Profile.LARGE, True)
    self.assertEqual((left.x, left.y, left.width, left.height), (88, 808, 192, 192))
    self.assertEqual((right.x, right.y), (1580, 808))
    document['layouts']['large']['driver_monitor'].update(x=700.5, y=600.25)
    custom = monitor_bounds(validate_document(document), Profile.LARGE, True)
    self.assertEqual((custom.x, custom.y), (700.5, 600.25))
    compact = monitor_bounds(default_document(), Profile.COMPACT, True)
    self.assertEqual((compact.x, compact.y, compact.width, compact.height), (16, 10, 60, 60))

  def test_visibility_reserves_critical_alerts_and_respects_saved_choice(self):
    state = road()
    for profile in Profile:
      self.assertTrue(monitor_visible(profile, state, fresh=True, onroad=True, top_icons=False))
      for changes, source in (
        ({}, {'onroad': False}),
        ({'appearance': replace(state.appearance, hide_dm_icon=True)}, {}),
        ({'alert': OnroadAlert(size=AlertSize.FULL)}, {}),
      ):
        with self.subTest(profile=profile, changes=changes, source=source):
          self.assertFalse(monitor_visible(profile, replace(state, **changes), **{'fresh': True, 'onroad': True, 'top_icons': False, **source}))
      document = default_document()
      document['layouts'][str(profile)]['driver_monitor']['enabled'] = False
      self.assertFalse(monitor_visible(profile, replace(state, customization=document), fresh=True, onroad=True, top_icons=False))

  def test_transient_sources_hud_and_small_alerts_do_not_remove_monitor(self):
    for profile in Profile:
      for camera in CameraViewChoice:
        state = replace(
          road(),
          reversing=True,
          camera_available=False,
          appearance=replace(road().appearance, camera_view=camera),
          alert=OnroadAlert(size=AlertSize.SMALL, text1='Bookmark Saved'),
        )
        self.assertTrue(monitor_visible(profile, state, fresh=False, onroad=True, top_icons=False))

  def test_set_speed_occludes_only_overlapping_compact_monitor(self):
    state = road()
    self.assertFalse(monitor_visible(Profile.COMPACT, state, fresh=True, onroad=True, top_icons=True))
    self.assertTrue(monitor_visible(Profile.LARGE, state, fresh=True, onroad=True, top_icons=True))
    document = default_document()
    document['layouts']['compact']['driver_monitor'].update(x=300, y=170)
    moved = replace(state, customization=document)
    self.assertTrue(monitor_visible(Profile.COMPACT, moved, fresh=True, onroad=True, top_icons=True))
    self.assertTrue(monitor_visible(Profile.COMPACT, state, fresh=True, onroad=True, top_icons=False))

  def test_bad_monitor_data_draws_neutral_person_without_stale_active_cone(self):
    monitor, driver = observation()
    self.assertTrue(valid_observation(monitor, driver))
    monitor.visionPolicyState.pose.pitch = float('nan')
    layer = DriverMonitorLayer.__new__(DriverMonitorLayer)
    layer.profile = Profile.LARGE
    self.enterContext(
      patch.object(
        layer,
        'renderer',
        NS(set_should_draw=Mock(), set_position=Mock(), _rect=object(), _is_active=True, _fade_filter=NS(update=Mock()), _update_state=Mock(), _render=Mock()),
        create=True,
      )
    )
    layer.render(road(), monitor=monitor, driver=driver, fresh=True, onroad=True)
    layer.renderer._update_state.assert_not_called()
    layer.renderer._render.assert_called_once()
    self.assertFalse(layer.renderer._is_active)
    layer.renderer._fade_filter.update.assert_called_once_with(0.35)

  def test_visible_face_keeps_person_solid_even_when_vision_policy_is_inactive(self):
    from openpilot.selfdrive.ui.mici.onroad.driver_state import DriverStateRenderer

    renderer = StableDriverStateRenderer.__new__(StableDriverStateRenderer)
    renderer._should_draw = True
    self.enterContext(patch.object(renderer, '_fade_filter', NS(x=0.35), create=True))
    renderer._face_detected = True
    renderer._is_active = False
    with patch.object(DriverStateRenderer, '_update_state'):
      renderer._update_state()
    self.assertEqual(renderer._fade_filter.x, 1.0)
    self.assertFalse(renderer._is_active)

    renderer._face_detected = False
    with patch.object(DriverStateRenderer, '_update_state'):
      renderer._update_state()
    self.assertEqual(renderer._fade_filter.x, 0.35)

  def test_native_renderer_receives_moved_origin_and_updates_policy_without_forcing(self):
    monitor, driver = observation()
    document = default_document()
    document['layouts']['large']['driver_monitor'].update(x=700.5, y=600.25)
    layer = DriverMonitorLayer.__new__(DriverMonitorLayer)
    layer.profile = Profile.LARGE
    self.enterContext(
      patch.object(layer, 'renderer', NS(set_should_draw=Mock(), set_position=Mock(), _update_state=Mock(), _render=Mock(), _rect=object()), create=True)
    )
    layer.render(replace(road(), customization=document), monitor=monitor, driver=driver, fresh=True, onroad=True)
    layer.renderer.set_position.assert_called_once_with(732.5, 632.25)
    layer.renderer._update_state.assert_called_once()
    layer.renderer._render.assert_called_once_with(layer.renderer._rect)

  def test_composition_wires_actual_monitor_layer_before_alert(self):
    from contextlib import ExitStack
    from pathlib import Path
    from openpilot.starpilot.ui import onroad

    view = onroad.OnroadView(Mock(spec=BitmapFonts, **vars(NS(profile=Profile.LARGE))), Path('/unused'))
    order = []
    view.driver_monitor_layer = lambda rect, state: order.append('dm')
    self.enterContext(patch.object(view.alert, 'render', lambda rect, alert: order.append('alert'), create=True))
    scene = replace(road(), camera_available=False, alert=OnroadAlert(size=AlertSize.FULL), appearance=replace(road().appearance, hide_speed=True))
    with ExitStack() as stack:
      for name in ('draw_rectangle_rec', 'draw_rectangle_gradient_v', 'draw_rectangle_lines_ex', 'draw_rectangle_rounded_lines_ex'):
        stack.enter_context(patch.object(onroad.rl, name))
      stack.enter_context(patch.object(onroad, 'render_glow'))
      stack.enter_context(patch.object(onroad.clip, 'begin_scissor_mode'))
      stack.enter_context(patch.object(onroad.clip, 'end_scissor_mode'))
      view.render(scene)
    self.assertEqual(order, ['dm', 'alert'])

  def test_runtime_binding_requires_fresh_post_drive_dm_receipts(self):
    from openpilot.starpilot.ui import runtime_app

    monitor, driver = observation()

    class Sources(dict):
      pass

    now = 5_000_000_000
    sources = Sources(driverMonitoringState=monitor, driverStateV2=driver, selfdriveState=NS())
    sources.valid = dict.fromkeys(sources, True)
    sources.alive = dict.fromkeys(sources, True)
    sources.logMonoTime = dict.fromkeys(sources, now)
    sources.recv_frame = dict.fromkeys(sources, 11)
    session = runtime_app.StarShellSession.__new__(runtime_app.StarShellSession)
    session.profile = Profile.LARGE
    self.enterContext(patch.object(session, '_driver_monitor_layer', NS(render=Mock()), create=True))
    native = NS(sm=sources, started_frame=10, is_onroad=lambda: True)
    with patch.object(runtime_app, 'ui_state', native), patch.object(runtime_app.time, 'monotonic_ns', return_value=now):
      session._render_driver_monitor(None, road())
      self.assertTrue(session._driver_monitor_layer.render.call_args.kwargs['fresh'])
      for service in ('driverMonitoringState', 'driverStateV2'):
        with self.subTest(service=service):
          sources.recv_frame[service] = 10
          session._render_driver_monitor(None, road())
          self.assertFalse(session._driver_monitor_layer.render.call_args.kwargs['fresh'])
          sources.recv_frame[service] = 11
          sources.logMonoTime[service] = now - 1_000_000_000
          session._render_driver_monitor(None, road())
          self.assertFalse(session._driver_monitor_layer.render.call_args.kwargs['fresh'])
          sources.logMonoTime[service] = now
          sources.valid[service] = False
          session._render_driver_monitor(None, road())
          self.assertFalse(session._driver_monitor_layer.render.call_args.kwargs['fresh'])
          sources.valid[service] = True
      sources.logMonoTime['selfdriveState'] = now - 1_000_000_000
      session._render_driver_monitor(None, road())
      self.assertTrue(session._driver_monitor_layer.render.call_args.kwargs['fresh'])

  def test_saved_layout_migration_keeps_exact_original_bytes_as_commit_source(self):
    import json
    import tempfile
    from pathlib import Path
    from openpilot.common.params import Params
    from openpilot.starpilot.galaxy.onroad_layout import LayoutChanged, OnroadLayoutOwner
    from openpilot.starpilot.ui.onroad_customization import PARAM_KEY

    old = default_document()
    for layout in old['layouts'].values():
      for key in ('driver_monitor', 'torque_bar', 'speed_limit_actions', 'model_confidence', 'conditional_mode', 'following_distance'):
        layout.pop(key, None)
    old['palette']['text'] = '#12345678'
    old['layouts']['large']['current_speed'].update(x=700.5, y=200.25)
    raw = json.dumps(old).encode()
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      path = Path(params.get_param_path(PARAM_KEY))
      path.write_bytes(raw)
      owner = OnroadLayoutOwner(params, lambda: True)
      snapshot = owner.snapshot()
      self.assertTrue(snapshot['valid'])
      self.assertIn('driver_monitor', snapshot['document']['layouts']['large'])
      self.assertEqual(path.read_bytes(), raw)
      path.write_bytes(raw + b' ')
      with self.assertRaises(LayoutChanged):
        owner.save({'revision': snapshot['revision'], 'document': snapshot['document']}, session_valid=lambda: True)
      self.assertEqual(path.read_bytes(), raw + b' ')
      current = owner.snapshot()
      saved = owner.save({'revision': current['revision'], 'document': current['document']}, session_valid=lambda: True)
      self.assertEqual(saved['document']['palette'], old['palette'])
      self.assertEqual(saved['document']['layouts']['large']['current_speed'], old['layouts']['large']['current_speed'])
      self.assertIn('driver_monitor', json.loads(path.read_bytes())['layouts']['compact'])
