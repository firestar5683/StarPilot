from contextlib import nullcontext
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from openpilot.starpilot.replay import render
from openpilot.starpilot.replay.render import Compositor, Engine, camera_options, frame_matches, parse_wall_offset


def test_camera_selection_uses_selected_sources_and_current_preferences():
  sources = {'fcamera.hevc', 'ecamera.hevc', 'dcamera.hevc'}
  assert camera_options('compact', {}, sources) == (False, False)
  assert camera_options('large', {}, sources) == (True, False)
  assert camera_options('compact', {'CameraView': b'0'}, sources) == (True, False)
  assert camera_options('compact', {'CameraView': b'1'}, sources) == (False, True)
  assert camera_options('compact', {'CameraView': b'3', 'DriverCamera': b'1'}, sources) == (True, True)
  assert camera_options('compact', {'CameraView': b'4', 'DriverCamera': b'1'}, sources) == (False, False)
  assert camera_options('large', {'PIPPreviewEnabled': b'1'}, sources) == (True, True)
  assert camera_options('compact', {'CameraView': b'1', 'PIPPreviewEnabled': b'1'}, {'qcamera.ts'}) == (False, False)


def test_engine_passes_selected_segment_to_machine_replay(tmp_path, monkeypatch):
  process = Mock()
  monkeypatch.setattr(render.subprocess, 'Popen', Mock(return_value=process))
  monkeypatch.setattr(render.threading, 'Thread', Mock())
  Engine('recorded-route', tmp_path, wide=False, cabin=False, start_segment=2)
  command = render.subprocess.Popen.call_args.args[0]
  assert command[command.index('--start-segment') + 1] == '2'


def test_camera_matches_recorded_identity_across_distinct_clock_domains():
  state = SimpleNamespace(frameId=5, timestampSof=9_000_000_000, timestampEof=9_010_000_000)
  client = SimpleNamespace(frame_id=5, timestamp_sof=9_000_000_000, timestamp_eof=9_010_000_000)
  frame = SimpleNamespace(frame_id=5)
  stamp, boot_now = 9_020_000_000, 9_050_000_000
  assert frame_matches(client, frame, state, stamp, boot_now)
  assert not frame_matches(client, frame, state, stamp, 1_050_000_000)  # MONOTONIC is the wrong domain.
  assert not frame_matches(client, frame, state, stamp, stamp - 1)
  assert not frame_matches(client, frame, state, stamp, stamp + 500_000_001)
  assert not frame_matches(client, None, state, stamp, boot_now)
  assert not frame_matches(client, frame, SimpleNamespace(frameId=5), stamp, boot_now)
  assert not frame_matches(client, frame, state, stamp, None)
  client.frame_id = 4
  assert not frame_matches(client, frame, state, stamp, boot_now)
  client.frame_id, client.timestamp_sof = 5, 9_000_000_001
  assert not frame_matches(client, frame, state, stamp, boot_now)


def test_paused_same_route_clock_never_advances_filters_or_gpu():
  core = object.__new__(Compositor)
  core.ui = SimpleNamespace(replay_sample=SimpleNamespace(now_ns=100))
  core.last_route_frame = (2, 100)
  core.context = Mock()
  assert core.draw(2, 0, 9_000_000_000) is False
  core.context.begin_frame.assert_not_called()


@pytest.mark.parametrize('frame_ready', (False, True))
def test_recorded_camera_preview_does_not_require_initial_device_state(frame_ready):
  @dataclass
  class Onroad:
    camera_available: bool = False
    viewport_width: int = 0

  core = object.__new__(Compositor)
  core.ui = SimpleNamespace(replay_sample=SimpleNamespace(now_ns=100),
                            sm=SimpleNamespace(seen={'extrinsicsCalibration': False}))
  core.last_route_frame = None
  core.context = core.placement = Mock()
  core.adapter = Mock()
  core.adapter.build.return_value = SimpleNamespace(onroad=Onroad())
  core._primary_matches = Mock(return_value=frame_ready)
  core._optional_placeholder_ready = Mock(return_value=False)
  core.rl = Mock()
  core.gui = SimpleNamespace(_render_prepare=[], _frame=0)
  core.content = Mock()
  core.scale = 1
  core.profile = SimpleNamespace(size=(1600, 800))
  core.view = Mock()
  core.view.render.side_effect = lambda state: setattr(core, 'primary_ready', state.camera_available)
  core.output = None
  core.converter = Mock()
  core.readback = Mock()
  assert core.draw(2, 0, 9_000_000_000) is frame_ready
  drawn = core.view.render.call_args.args[0]
  assert drawn.camera_available is frame_ready
  assert core.adapter.build.return_value.onroad.camera_available is False
  assert core.readback.start.call_count == int(frame_ready)


@pytest.mark.parametrize('profile', ('onroad', 'mici.onroad'))
@pytest.mark.parametrize('replay', (False, True))
def test_camera_layers_allow_recorded_preview_and_preserve_live_start_gate(monkeypatch, profile, replay):
  import importlib
  from openpilot.cereal.visionipc import VisionStreamType
  module = importlib.import_module(f'openpilot.selfdrive.ui.{profile}.augmented_road_view')
  monkeypatch.setattr(module.ui_state, 'started', False)
  monkeypatch.setattr(module.ui_state, 'replay_clock', object() if replay else None)
  measure = Mock()
  monkeypatch.setattr(module.gui_app, 'measure_frame_phase', measure)
  camera = object.__new__(module.AugmentedRoadView)
  camera.close = Mock()
  camera._switch_stream_if_needed = Mock(return_value=VisionStreamType.VISION_STREAM_NARROW_ROAD)
  camera._update_calibration = Mock()
  camera._stream_type = VisionStreamType.VISION_STREAM_NARROW_ROAD
  camera._target_stream_type = None
  camera._switching = False
  camera.available_streams = set()
  camera.frame = None
  camera.model_renderer = Mock(road_style={})
  camera._model_renderer = Mock()
  camera.render_camera_model_layer(Mock())
  assert bool(measure.call_count) is replay
  assert camera._update_calibration.call_count == int(replay)


def test_worker_preserves_final_engine_error_after_exit(tmp_path, monkeypatch):
  session = tmp_path / ('a' * 32)
  session.mkdir(mode=0o700)
  for key in ('STARPILOT_PROJECTION_READ_ONLY', 'BIG', 'SCALE'):
    monkeypatch.setenv(key, '')
  monkeypatch.setattr(render.signal, 'signal', Mock())
  monkeypatch.setattr(render.threading, 'Thread', Mock())
  monkeypatch.setattr(render, 'validate_context', lambda path: path)
  monkeypatch.setattr(render, 'seed_display', lambda path: {})
  catalog = Mock()
  catalog.detail.return_value = {'playable': True, 'segments': []}
  monkeypatch.setattr('openpilot.starpilot.replay.catalog.ReplayCatalog', lambda path: catalog)
  monkeypatch.setattr(render, 'Compositor', lambda *args, **kwargs: Mock())
  engine = Mock(status={'state': 'preparing'}, error=None)
  engine.process.poll.return_value = 2
  def final_status(**kwargs):
    engine.status = {'state': 'failed', 'error': 'Recorded clock correlation is unavailable'}
  engine.reader.join.side_effect = final_status
  monkeypatch.setattr(render, 'Engine', lambda *args, **kwargs: engine)
  with pytest.raises(RuntimeError, match='Recorded clock correlation is unavailable'):
    render.run(session, 'recorded-route', tmp_path, 'native', 'large', Mock())
  engine.reader.join.assert_called_once_with(timeout=1)


def test_engine_starts_before_idle_renderer_placement_and_closes_if_renderer_fails(tmp_path, monkeypatch):
  for key in ('STARPILOT_PROJECTION_READ_ONLY', 'BIG', 'SCALE'):
    monkeypatch.setenv(key, '')
  monkeypatch.setattr(render.signal, 'signal', Mock())
  monkeypatch.setattr(render, 'validate_context', lambda path: path)
  monkeypatch.setattr(render, 'seed_display', lambda path: {})
  catalog = Mock()
  catalog.detail.return_value = {'playable': True, 'segments': []}
  monkeypatch.setattr('openpilot.starpilot.replay.catalog.ReplayCatalog', lambda path: catalog)
  calls = []
  engine = Mock()
  def start_engine(*args, **kwargs):
    calls.append('engine')
    return engine
  def start_renderer(*args, **kwargs):
    calls.append('renderer')
    raise RuntimeError('renderer unavailable')
  monkeypatch.setattr(render, 'Engine', start_engine)
  monkeypatch.setattr(render, 'Compositor', start_renderer)
  with pytest.raises(RuntimeError, match='renderer unavailable'):
    render.run(tmp_path, 'recorded-route', tmp_path, 'native', 'large', Mock())
  assert calls == ['engine', 'renderer']
  engine.close.assert_called_once()


def test_published_readiness_survives_delivery_jitter_but_expires_and_rejects_old_epochs(tmp_path, monkeypatch):
  session = tmp_path / ('a' * 32)
  session.mkdir(mode=0o700)
  for key in ('STARPILOT_PROJECTION_READ_ONLY', 'BIG', 'SCALE'):
    monkeypatch.setenv(key, '')
  monkeypatch.setattr(render.signal, 'signal', Mock())
  monkeypatch.setattr(render.threading, 'Thread', Mock())
  monkeypatch.setattr(render, 'validate_context', lambda path: path)
  monkeypatch.setattr(render, 'seed_display', lambda path: {})
  catalog = Mock()
  catalog.detail.return_value = {'playable': True, 'segments': []}
  monkeypatch.setattr('openpilot.starpilot.replay.catalog.ReplayCatalog', lambda path: catalog)
  publisher = Mock()
  monkeypatch.setattr(render, 'ReplayFramePublisher', lambda *args: publisher)
  times, step = (1, 1.01, 1.11, 1.61, 10, 10.2, 10.4), [0]
  monkeypatch.setattr(render.time, 'monotonic', lambda: times[step[0]])
  monkeypatch.setattr(render.time, 'monotonic_ns', lambda: round(times[step[0]] * 1e9))
  engine = Mock(error=None, status={'state': 'playing', 'paused': False, 'epoch': 1, 'position': 0,
                                   'routeStartNs': 100, 'start': 0, 'end': 20})
  engine.process.poll.return_value = None
  monkeypatch.setattr(render, 'Engine', lambda *args, **kwargs: engine)
  core = Mock(cabin=False)
  core.camera = Mock(client=None, frame=object(), _target_client=None, _switching=False)
  core.pip_stream._client = None
  core.readback.pending = False
  core.ui.replay_needs_reprime = False
  available = dict.fromkeys(('modelV2', 'extrinsicsCalibration', 'longitudinalPlan'), True)
  core.ui.sm = SimpleNamespace(seen=available, valid=available, alive=available)
  core.update.side_effect = lambda: SimpleNamespace(valid=step[0] != 6, epoch=engine.status['epoch'], now_ns=100, boot_ns=100)
  core.finish.side_effect = lambda: nullcontext((b'pixels', (1, 0, 1_010_000_000)) if step[0] == 2 else None)
  core._primary_matches.return_value = core._optional_placeholder_ready.return_value = False
  attempts = []
  def draw(*args):
    attempts.append(times[step[0]])
    return step[0] == 1
  core.draw.side_effect = draw
  monkeypatch.setattr(render, 'Compositor', lambda *args, **kwargs: core)
  def next_loop(delay):
    if step[0] == len(times) - 1:
      engine.error = 'test complete'
      return
    step[0] += 1
    if step[0] == 4:
      engine.status.update(paused=True, state='paused')
    if step[0] == 5:
      engine.status['epoch'] = 2
  monkeypatch.setattr(render.time, 'sleep', next_loop)
  states = []
  with pytest.raises(RuntimeError, match='test complete'):
    render.run(session, 'recorded-route', tmp_path, 'native', 'large', lambda value: states.append(value))
  assert attempts[:2] == [1, 1.01]  # A failed draw retries before the 50 ms frame interval.
  assert [(value['state'], value['frameReady']) for value in states] == [
    ('preparing', False), ('playing', True), ('buffering', False), ('paused', True), ('seeking', False), ('seeking', False)]
  publisher.publish.assert_called_once_with(b'pixels', epoch=1, position=0, captured_ns=1_010_000_000)


@pytest.mark.parametrize('matching_frame', (False, True))
def test_epoch_reset_preserves_native_camera_stream_and_eligible_paused_frame(monkeypatch, matching_frame):
  monkeypatch.setattr('openpilot.starpilot.ui.runtime_snapshot.RuntimeSnapshotAdapter', Mock())
  monkeypatch.setattr('openpilot.starpilot.ui.pip_render.PiPRenderer', Mock())
  core = object.__new__(Compositor)
  streams = {0, 2}
  client = Mock(frame_id=5 if matching_frame else 4, timestamp_sof=9_000_000_000, timestamp_eof=9_010_000_000)
  client.is_connected.return_value = True
  frame = SimpleNamespace(frame_id=5)
  core.camera = Mock(client=client, frame=frame, stream_type=0, available_streams=streams)
  core.camera_class = Mock(return_value=Mock())
  core._close_camera = Mock()
  core._new_view = Mock()
  core.readback = Mock(pending=False)
  core.pip_stream = Mock()
  core.pip = core.view = core.context = Mock()
  idx = SimpleNamespace(frameId=5, timestampSof=9_000_000_000, timestampEof=9_010_000_000)
  sm = Mock()
  sm.__getitem__ = Mock(return_value=idx)
  sm.seen = sm.valid = {'narrowRoadEncodeIdx': True}
  sm.logMonoTime = {'narrowRoadEncodeIdx': 9_020_000_000}
  core.ui = SimpleNamespace(replay_sample=SimpleNamespace(valid=True, boot_ns=9_050_000_000), sm=sm)
  core.render_receipts = {'modelV2': 1}
  core.reset_epoch(3)
  assert core.render_receipts == {}
  assert core.camera.client is client
  assert core.camera.available_streams == streams
  assert core.camera.available_streams is not streams
  core.camera._initialize_textures.assert_called_once()
  assert core.camera.frame is (frame if matching_frame else None)
  assert core.epoch == 3 and core.last_route_frame is None


def test_initial_hud_primer_required_even_when_camera_received_a_frame(tmp_path, monkeypatch):
  session = tmp_path / ('a' * 32)
  session.mkdir(mode=0o700)
  for key in ('STARPILOT_PROJECTION_READ_ONLY', 'BIG', 'SCALE'):
    monkeypatch.setenv(key, '')
  monkeypatch.setattr(render.signal, 'signal', Mock())
  monkeypatch.setattr(render.threading, 'Thread', Mock())
  monkeypatch.setattr(render, 'validate_context', lambda path: path)
  monkeypatch.setattr(render, 'seed_display', lambda path: {})
  catalog = Mock()
  catalog.detail.return_value = {'playable': True, 'segments': []}
  monkeypatch.setattr('openpilot.starpilot.replay.catalog.ReplayCatalog', lambda path: catalog)
  core = Mock(cabin=False)
  core.camera = Mock(client=Mock(), frame=object(), _target_client=None, _switching=False)
  core.pip_stream._client = None
  core.readback.pending = False
  core.ui.replay_needs_reprime = False
  available = dict.fromkeys(('modelV2', 'extrinsicsCalibration', 'longitudinalPlan'), True)
  core.ui.sm = SimpleNamespace(seen=available, valid=available, alive=available)
  core.update.return_value = SimpleNamespace(valid=True, epoch=2, now_ns=100, boot_ns=100)
  core.finish.return_value = nullcontext(None)
  monkeypatch.setattr(render, 'Compositor', lambda *args, **kwargs: core)
  engine = Mock(status={'state': 'paused', 'paused': True, 'epoch': 2, 'position': 0, 'routeStartNs': 100, 'start': 0, 'end': 1}, error=None)
  engine.process.poll.return_value = None
  monkeypatch.setattr(render, 'Engine', lambda *args, **kwargs: engine)
  def next_loop(delay):
    engine.error = 'test complete'
  monkeypatch.setattr(render.time, 'sleep', next_loop)
  with pytest.raises(RuntimeError, match='test complete'):
    render.run(session, 'recorded-route', tmp_path, 'native', 'large', Mock())
  engine.command.assert_called_once_with({'op': 'seek', 'position': 0, 'requestId': '0' * 32}, reprime=True)
  core.draw.assert_not_called()


def test_early_camera_subscriber_is_polled_before_paused_reprime():
  from openpilot.cereal.visionipc import VisionStreamType
  sample = SimpleNamespace(valid=True, epoch=1, boot_ns=9_050_000_000)
  idx = SimpleNamespace(frameId=5, timestampSof=9_000_000_000, timestampEof=9_010_000_000)
  sm = Mock()
  sm.__getitem__ = Mock(return_value=idx)
  sm.seen = sm.valid = {'narrowRoadEncodeIdx': True}
  sm.logMonoTime = {'narrowRoadEncodeIdx': 9_020_000_000}
  frame = SimpleNamespace(frame_id=5)
  client = Mock(frame_id=5, timestamp_sof=idx.timestampSof, timestamp_eof=idx.timestampEof)
  # The first receive synchronizes with a publisher created after this client.
  client.recv.side_effect = [None, frame]
  core = object.__new__(Compositor)
  core.ui = Mock(replay_sample=sample, sm=sm)
  core.epoch, core.cabin = 1, False
  core.camera = Mock(client=client, frame=None, stream_type=VisionStreamType.VISION_STREAM_NARROW_ROAD)
  core.camera._ensure_connection.return_value = True
  core.update()
  assert not core._primary_matches()
  core.update()
  assert core.camera.frame is frame and core._primary_matches()


def test_recorded_wall_clock_uses_only_verified_route_pair():
  from openpilot.starpilot.replay.render import recorded_wall_clock
  sample = SimpleNamespace(valid=True, now_ns=10_000_000_000)
  assert recorded_wall_clock(sample, None) is None
  assert recorded_wall_clock(SimpleNamespace(valid=False), 1_000_000_000) is None
  instant = recorded_wall_clock(sample, 1_000_000_000_000_000_000)
  assert instant.timestamp() == 1_000_000_010


def test_private_wall_offset_protocol_preserves_full_nanoseconds():
  import json
  offset = 1_791_870_000_000_000_123
  value = json.loads('{"wallMinusMonoNs":"1791870000000000123"}')
  assert parse_wall_offset(value['wallMinusMonoNs']) == offset
  for invalid in (None, False, offset, float(offset), '0', '-1', '9' * 20, str(2**63), '1.79187e18'):
    assert parse_wall_offset(invalid) is None


def test_camera_reprime_cannot_overwrite_an_unacknowledged_user_action():
  import io
  import json
  import threading
  engine = object.__new__(Engine)
  engine.write_lock = threading.Lock()
  engine.process = SimpleNamespace(stdin=io.StringIO())
  engine.last_request_id = engine.seek_request = None
  request = {'op': 'seek', 'position': 65, 'requestId': 'a' * 32}
  assert engine.command(request)
  assert not engine.command({'op': 'seek', 'position': 0, 'requestId': '0' * 32}, reprime=True)
  assert engine.seek_request == request['requestId']
  assert [json.loads(line) for line in engine.process.stdin.getvalue().splitlines()] == [request]
  assert engine.command(request, reprime=True)
  pause = {'op': 'pause', 'paused': True, 'requestId': 'b' * 32}
  assert engine.command(pause)
  assert not engine.command(request, reprime=True)
  assert engine.command({'op': 'seek', 'position': 65, 'requestId': pause['requestId']}, reprime=True)


@pytest.mark.parametrize('profile', ('onroad', 'mici.onroad'))
def test_replay_draw_retains_updates_until_stock_consumers_read_them(monkeypatch, profile):
  import importlib
  import numpy as np
  import pyray as rl
  from openpilot.cereal import messaging
  from openpilot.cereal.visionipc import VisionStreamType
  from openpilot.selfdrive.ui.ui_state import UIStatus
  model_module = importlib.import_module(f'openpilot.selfdrive.ui.{profile}.model_renderer')
  camera_module = importlib.import_module(f'openpilot.selfdrive.ui.{profile}.augmented_road_view')
  sm = messaging.SubMaster(['modelV2', 'extrinsicsCalibration', 'radarState', 'carParams', 'carState',
                           'selfdriveState', 'carOutput', 'longitudinalPlan'])
  clock = [1_000_000_000]
  ui = SimpleNamespace(sm=sm, started=False, started_frame=0, replay_clock=object(), status=UIStatus.ENGAGED,
                       display_time_ns=lambda: clock[0], replay_sample=SimpleNamespace(valid=True, now_ns=clock[0]))
  monkeypatch.setattr(model_module, 'ui_state', ui)
  monkeypatch.setattr(camera_module, 'ui_state', ui)
  monkeypatch.setattr(model_module, 'Params', lambda: SimpleNamespace(get=lambda _: None))
  monkeypatch.setattr(camera_module.gui_app, 'measure_frame_phase',
                      lambda phase, fn, *args, **kwargs: None if phase == 'camera' else fn(*args, **kwargs))
  monkeypatch.setattr(model_module, 'draw_polygon', Mock())
  renderer = model_module.ModelRenderer()
  renderer._update_raw_points = Mock(wraps=renderer._update_raw_points)
  renderer._update_model = Mock()
  renderer._draw_lane_lines = renderer._draw_path = Mock()
  renderer.render = lambda rect: renderer._render(rect)
  camera = object.__new__(camera_module.AugmentedRoadView)
  camera.close = Mock()
  camera.device_camera = object()
  camera.view_from_calib = camera.view_from_wide_calib = np.eye(3)
  camera._switch_stream_if_needed = Mock(return_value=VisionStreamType.VISION_STREAM_NARROW_ROAD)
  camera._stream_type = VisionStreamType.VISION_STREAM_NARROW_ROAD
  camera._target_stream_type, camera._switching = None, False
  camera.available_streams, camera.frame = {camera.stream_type}, object()
  camera.model_renderer = camera._model_renderer = renderer
  core = object.__new__(Compositor)
  core.ui, core.camera = ui, camera
  core.profile = 'compact' if profile == 'mici.onroad' else 'large'
  core.cabin = core.wide = False
  core.render_receipts = {}
  core._primary_matches = Mock(return_value=True)
  core._optional_placeholder_ready = Mock(return_value=False)
  core._receive_primary, core.rl = Mock(), Mock()
  state = SimpleNamespace(appearance=SimpleNamespace(camera_view=2, show_lead_indicator=False, lead_info_mode=0,
                                                    lead_info_metric=False), reverse_driver_camera=False,
                          lead_indicator_source_fresh=False, lateral_active=True,
                          customization={'roadColors': {'compact': {}, 'large': {}}})
  rect = rl.Rectangle(0, 0, 536, 240)
  model = messaging.new_message('modelV2', valid=True)
  model.modelV2.position.x = [5., 10., 15.]
  model.modelV2.position.y = model.modelV2.position.z = [0., 0., 0.]
  sm.update_msgs(1., [model])
  sm.update_msgs(1.01, [])
  core._camera_layer(rect, state)
  renderer._update_raw_points.assert_not_called()
  calib = messaging.new_message('extrinsicsCalibration', valid=True, logMonoTime=clock[0] + 50_000_000)
  calib.extrinsicsCalibration.rpyCalib = [0.1, 0., 0.]
  calib.extrinsicsCalibration.calStatus = camera_module.CALIBRATED
  sm.update_msgs(1.02, [calib])
  sm.update_msgs(1.03, [])
  sm.alive['extrinsicsCalibration'] = False
  core._camera_layer(rect, state)
  renderer._update_raw_points.assert_not_called()
  assert 'extrinsicsCalibration' not in core.render_receipts
  clock[0] += 50_000_000
  ui.replay_sample.now_ns = clock[0]
  sm.alive['extrinsicsCalibration'] = True
  original = sm.updated
  rotation = Mock(wraps=camera_module.rot_from_euler)
  monkeypatch.setattr(camera_module, 'rot_from_euler', rotation)
  core._camera_layer(rect, state)
  core._camera_layer(rect, state)
  assert sm.updated is original
  assert renderer._update_raw_points.call_count == 1
  np.testing.assert_array_equal(renderer._path.raw_points[:, 0], [5., 10., 15.])
  assert rotation.call_count == 1

  params = messaging.new_message('carParams', valid=True)
  params.carParams.openpilotLongitudinalControl = True
  sm.update_msgs(1.035, [params, messaging.new_message('radarState', valid=False)])
  sm.update_msgs(1.036, [])
  geometry_calls = renderer._update_model.call_count
  core._camera_layer(rect, state)
  assert renderer._longitudinal_control
  assert renderer._update_raw_points.call_count == 1
  assert renderer._update_model.call_count == geometry_calls + 1
  assert renderer._update_model.call_args.kwargs['update_lane_geometry'] is False

  renderer._path.projected_points = np.ones((3, 2), dtype=np.float32)
  renderer._rect = rect
  renderer._draw_path = model_module.ModelRenderer._draw_path.__get__(renderer)
  state.customization['roadColors'][core.profile] = {'pathMode': 'color'}
  car = messaging.new_message('carState', valid=True)
  car.carState.vEgo = 22.
  sm.update_msgs(1.037, [car])
  sm.update_msgs(1.038, [])
  core._camera_layer(rect, state)
  assert 'carState' not in core.render_receipts
  state.customization['roadColors'][core.profile] = {'pathMode': 'rainbow'}
  core._camera_layer(rect, state)
  assert renderer._rainbow_path.speed_mps == 22.
  sample_ns = renderer._rainbow_path.sample_ns
  clock[0] += 50_000_000
  core._camera_layer(rect, state)
  assert renderer._rainbow_path.sample_ns == sample_ns

  sm.update_msgs(1.04, [model])
  sm.update_msgs(1.05, [])
  if core.profile == 'compact':
    state.appearance.camera_view = 4
    core._camera_layer(rect, state)
    assert renderer._update_raw_points.call_count == 1
    state.appearance.camera_view = 2
  core._camera_layer(rect, state)
  assert renderer._update_raw_points.call_count == 2
  before, original = dict(core.render_receipts), sm.updated
  def failed_draw(*args, **kwargs):
    sm.updated['modelV2']
    raise RuntimeError('draw failed')
  camera.render_camera_model_layer = failed_draw
  with pytest.raises(RuntimeError, match='draw failed'):
    core._camera_layer(rect, state)
  assert sm.updated is original and core.render_receipts == before


@pytest.mark.parametrize('valid,epoch', [(True, 1), (False, 1), (True, 2)])
def test_finished_frame_is_borrowed_until_delivery_finishes(valid, epoch):
  core = object.__new__(Compositor)
  pixels = memoryview(bytearray(b'pixels'))
  core.readback = Mock(pending=True)
  core.readback.finish.return_value = pixels
  core.ui = SimpleNamespace(replay_clock=Mock())
  core.ui.replay_clock.sample.return_value = SimpleNamespace(valid=valid, epoch=epoch)
  core.meta = 1, 0., 100
  with pytest.raises(RuntimeError, match='delivery failed'):
    with core.finish() as finished:
      core.readback.release.assert_not_called()
      assert finished == ((pixels, core.meta) if valid and epoch == 1 else None)
      if finished:
        assert finished[0] is pixels
      raise RuntimeError('delivery failed')
  core.readback.release.assert_called_once()


def test_web_delivery_times_packets_and_flushes_pause_end_and_stall(tmp_path, monkeypatch):
  session = tmp_path / ('a' * 32)
  session.mkdir(mode=0o700)
  for key in ('STARPILOT_PROJECTION_READ_ONLY', 'BIG', 'SCALE'):
    monkeypatch.setenv(key, '')
  monkeypatch.setattr(render.signal, 'signal', Mock())
  monkeypatch.setattr(render.threading, 'Thread', Mock())
  monkeypatch.setattr(render, 'validate_context', lambda path: path)
  monkeypatch.setattr(render, 'seed_display', lambda path: {})
  catalog = Mock()
  catalog.detail.return_value = {'playable': True, 'segments': []}
  monkeypatch.setattr('openpilot.starpilot.replay.catalog.ReplayCatalog', lambda path: catalog)
  times = (1., 1.06, 1.125, 1.15, 10., 10.06, 10.12, 10.125, 10.23, 10.25, 11.3, 11.36, 11.42, 11.54)
  step = [0]
  monkeypatch.setattr(render.time, 'monotonic', lambda: times[step[0]])
  monkeypatch.setattr(render.time, 'monotonic_ns', lambda: round(times[step[0]] * 1e9))
  engine = Mock(error=None, status={'state': 'playing', 'paused': False, 'epoch': 1, 'position': 0,
                                   'routeStartNs': 100, 'start': 0, 'end': 20})
  engine.process.poll.return_value = None
  monkeypatch.setattr(render, 'Engine', lambda *args, **kwargs: engine)
  core = Mock(cabin=False)
  core.camera = Mock(client=None, frame=object(), _target_client=None, _switching=False)
  core.pip_stream._client = None
  core.readback.pending = core.ui.replay_needs_reprime = False
  available = dict.fromkeys(('modelV2', 'extrinsicsCalibration', 'longitudinalPlan'), True)
  core.ui.sm = SimpleNamespace(seen=available, valid=available, alive=available)
  core.update.side_effect = lambda: SimpleNamespace(valid=True, epoch=engine.status['epoch'], now_ns=100, boot_ns=100)
  delivered = {0, 1, 2, 5, 6, 7, 9, 11, 12}
  core.finish.side_effect = lambda: nullcontext((b'pixels', (engine.status['epoch'], 0, round(times[step[0]] * 1e9)))
                                               if step[0] in delivered else None)
  core.draw.return_value = False
  monkeypatch.setattr(render, 'Compositor', lambda *args, **kwargs: core)
  encoder = Mock(supports_nv12=True)
  encoder.encode_nv12.side_effect = lambda pixels, keyframe: (b'packet', keyframe)
  monkeypatch.setattr('openpilot.starpilot.system.android_auto.hw_encoder.HardwareH264Encoder', lambda *args, **kwargs: encoder)
  muxes = []
  def new_mux(*args):
    mux = Mock(codec='avc1.42c01f', init=b'init')
    mux.frame.return_value = b'fragment'
    muxes.append(mux)
    return mux
  monkeypatch.setattr(render, 'MediaMux', new_mux)
  def next_loop(delay):
    if step[0] == len(times) - 1:
      engine.error = 'test complete'
      return
    step[0] += 1
    if step[0] in (3, 7):
      engine.status.update(paused=True, state='paused')
    if step[0] == 7:
      engine.status['epoch'] = 2
    if step[0] in (5, 9):
      engine.status.update(paused=False, state='playing', rate=2)
    if step[0] == 13:
      engine.status.update(paused=True, state='ended')
  monkeypatch.setattr(render.time, 'sleep', next_loop)
  states = []
  with pytest.raises(RuntimeError, match='test complete'):
    render.run(session, 'recorded-route', tmp_path, 'web', 'large', states.append)
  assert len(muxes) == 2
  assert [(call.kwargs['pts_us'], call.kwargs['duration_us']) for call in muxes[0].frame.call_args_list] == [
    (0, 60000), (60000, 65000), (125000, 50000), (175000, 60000)]
  assert [(call.kwargs['pts_us'], call.kwargs['duration_us']) for call in muxes[1].frame.call_args_list] == [
    (0, 50000), (50000, 50000), (100000, 60000), (160000, 50000)]
  assert states[0]['mediaReady'] is False
  assert any(state['epoch'] == 2 and state['state'] == 'paused' and state['mediaReady'] for state in states)
  assert states[-1]['state'] == 'ended' and states[-1]['mediaReady']
  for mux in muxes:
    mux.close.assert_called_once()
