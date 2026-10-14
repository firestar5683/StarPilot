"""Fake transport exercises native ownership, cancellation and passive input."""

from types import SimpleNamespace as NS
import threading
import time
from unittest.mock import Mock

import pyray as rl
import pytest

from openpilot.starpilot.ui.replay_settings import ReplayCompactPage, ReplayController, ReplayPage, duration
from openpilot.starpilot.ui.presentation import Profile


ROUTE = {'routeId': '00000001--0123456789', 'displayName': 'Recorded route', 'segmentCount': 2,
         'availability': 'ready', 'playable': True, 'reason': None, 'warnings': []}


class Backend:
  def __init__(self):
    self.calls = []
    self.status = {'schemaVersion': 1, 'ownerId': 'a' * 32, 'sessionId': None, 'state': 'idle',
                   'routeId': None, 'profile': 'large', 'revision': 0, 'epoch': 0,
                   'position': 0.0, 'start': 0.0, 'end': 120.0, 'rate': 1.0, 'paused': True,
                   'frameReady': False, 'errorCode': None, 'owned': False, 'offroad': True}
    self.start_gate = None

  def __call__(self, payload):
    self.calls.append(payload)
    operation = payload['op']
    if operation == 'catalog':
      result = {'schemaVersion': 1, 'routes': [dict(ROUTE)]}
    elif operation == 'detail':
      result = dict(ROUTE)
    else:
      if operation == 'start':
        if self.start_gate is not None:
          self.start_gate.wait(2)
        self.status.update(sessionId='b' * 32, state='playing', routeId=ROUTE['routeId'],
                           revision=1, epoch=1, paused=False, owned=True, frameReady=True, framePath='/tmp/private-replay-frame')
      elif operation == 'control':
        assert payload['sessionId'] == self.status['sessionId']
        assert payload['expectedRevision'] == self.status['revision']
        self.status['revision'] += 1
        action = payload['action']
        if action == 'seek':
          self.status.update(position=payload['position'], epoch=self.status['epoch'] + 1)
        elif action == 'pause':
          self.status.update(paused=payload['paused'], state='paused' if payload['paused'] else 'playing')
        else:
          self.status['rate'] = payload['rate']
      elif operation == 'stop':
        self.status.update(sessionId=None, state='idle', frameReady=False)
      result = dict(self.status)
    return {'ok': True, 'result': result}


def pump(owner, predicate):
  deadline = time.monotonic() + 2
  while time.monotonic() < deadline:
    owner.tick()
    if predicate():
      return
    time.sleep(0.001)
  pytest.fail('fake replay operation did not finish')


@pytest.fixture
def playback():
  backend = Backend()
  frames = []
  reader = NS(latest=lambda: frames.pop(0) if frames else None, close=Mock())
  owner = ReplayController(backend, lambda *_: reader)
  pump(owner, lambda: owner.available and owner.pending is None)
  owner.select(ROUTE)
  pump(owner, lambda: owner.pending is None)
  owner.start()
  pump(owner, lambda: owner.active)
  yield owner, backend, frames, reader
  owner.close()
  owner.executor.shutdown(wait=True)


def test_owned_start_and_controls_bind_revision_and_client(playback):
  owner, backend, _, _ = playback
  start = next(call for call in backend.calls if call['op'] == 'start')
  assert start['expectedOwnerId'] == 'a' * 32
  assert start['clientId'] == owner.client_id
  assert owner.seek(1000)
  pump(owner, lambda: owner.status['epoch'] == 2)
  command = next(call for call in backend.calls if call['op'] == 'control')
  assert command['position'] == 120
  assert command['expectedRevision'] == 1
  assert command['sessionId'] == owner.own_session
  assert not owner.seek(float('nan'))


@pytest.fixture(params=[Profile.LARGE, Profile.COMPACT])
def prepared_playback(request):
  backend = Backend()
  backend.status['profile'] = request.param
  def requester(payload):
    response = backend(payload)
    if payload['op'] == 'start':
      backend.status.update(state='paused', paused=True)
      response['result'] = dict(backend.status)
    return response
  frames = []
  reader = NS(latest=lambda: frames.pop(0) if frames else None, close=Mock())
  factory = Mock(return_value=reader)
  clock = NS(now=0.0)
  owner = ReplayController(requester, factory, clock=lambda: clock.now)
  pump(owner, lambda: owner.available and owner.pending is None)
  owner.select(ROUTE)
  pump(owner, lambda: owner.pending is None)
  assert owner.start()
  pump(owner, lambda: owner.active)
  yield owner, backend, frames, clock, factory
  owner.close()
  owner.executor.shutdown(wait=True)


def test_autoplay_waits_one_second_after_first_valid_frame_and_runs_only_once(prepared_playback):
  owner, backend, frames, clock, factory = prepared_playback
  clock.now = 10
  pump(owner, lambda: owner.available and owner.pending is None)
  assert not any(call['op'] == 'control' for call in backend.calls)
  frames.append(NS(session_id=owner.own_session, epoch=0, frame_id=1))
  owner.next_frame = 0
  pump(owner, lambda: not frames and owner.pending is None)
  assert owner.autoplay_at == float('inf')
  frames.append(NS(session_id=owner.own_session, epoch=1, frame_id=2))
  owner.next_frame = 0
  pump(owner, lambda: owner.frame is not None)
  assert factory.call_args.args[2] == backend.status['profile']
  assert owner.autoplay_at == 11
  clock.now = 10.99
  pump(owner, lambda: owner.pending is None)
  assert backend.status['paused']
  clock.now = 11
  pump(owner, lambda: backend.status['paused'] is False)
  controls = [call for call in backend.calls if call['op'] == 'control']
  assert len(controls) == 1
  assert controls[0]['action'] == 'pause' and controls[0]['paused'] is False
  pump(owner, lambda: owner.status['paused'] is False)
  assert owner.control('pause', paused=True)
  pump(owner, lambda: owner.status['paused'] is True)
  clock.now = 12
  pump(owner, lambda: owner.available and owner.pending is None)
  assert backend.status['paused']  # Later pauses must never trigger another autoplay.


@pytest.mark.parametrize('action', ['pause', 'seek', 'stop', 'close', 'offroad'])
def test_autoplay_respects_user_actions_and_offroad_authority(prepared_playback, action):
  owner, backend, frames, clock, _ = prepared_playback
  frames.append(NS(session_id=owner.own_session, epoch=1, frame_id=1))
  owner.next_frame = 0
  pump(owner, lambda: owner.frame is not None)
  if action == 'pause':
    assert owner.control('pause', paused=True)
  elif action == 'seek':
    assert owner.seek(30)
  elif action == 'stop':
    assert owner.stop()
  elif action == 'close':
    owner.close()
  else:
    backend.status['offroad'] = False
    owner.next_status = 0
    pump(owner, lambda: not owner.available)
  if action != 'close':
    pump(owner, lambda: owner.pending is None)
  clock.now = 1.1
  owner.tick()
  if action != 'close':
    pump(owner, lambda: owner.pending is None)
  assert not any(call['op'] == 'control' and call.get('paused') is False for call in backend.calls)


def test_another_client_session_has_no_implicit_native_control():
  backend = Backend()
  backend.status.update(sessionId='c' * 32, state='playing')
  owner = ReplayController(backend)
  try:
    pump(owner, lambda: owner.available)
    assert not owner.active
    assert not owner.control('pause', paused=True)
    assert not owner.stop()
    assert not any(call['op'] in ('start', 'control', 'stop') for call in backend.calls)
  finally:
    owner.close()
    owner.executor.shutdown(wait=True)


def test_close_stops_a_start_that_finishes_after_dismissal():
  backend = Backend()
  owner = ReplayController(backend)
  pump(owner, lambda: owner.available and owner.pending is None)
  owner.select(ROUTE)
  pump(owner, lambda: owner.pending is None)
  backend.start_gate = threading.Event()
  assert owner.start()
  deadline = time.monotonic() + 2
  while not any(call['op'] == 'start' for call in backend.calls) and time.monotonic() < deadline:
    time.sleep(0.001)
  owner.close()
  backend.start_gate.set()
  owner.executor.shutdown(wait=True)
  assert [call['op'] for call in backend.calls][-2:] == ['start', 'stop']
  assert backend.status['sessionId'] is None


def test_old_epoch_frames_are_rejected_and_seek_clears_previous_frame(playback):
  owner, _, frames, _ = playback
  old = NS(data=b'pixels', session_id=owner.own_session, epoch=1, frame_id=1)
  frames.append(old)
  pump(owner, lambda: owner.frame is old)
  assert owner.seek(60)
  pump(owner, lambda: owner.status['epoch'] == 2)
  assert owner.frame is None
  frames.append(old)
  owner.next_frame = 0
  pump(owner, lambda: not frames)
  assert owner.frame is None


def test_control_waits_behind_one_frame_copy_without_blocking_ui(playback):
  owner, backend, _, reader = playback
  entered, release = threading.Event(), threading.Event()
  def blocked_frame():
    entered.set()
    release.wait(2)
    return None
  reader.latest = blocked_frame
  owner.next_frame = 0
  pump(owner, entered.is_set)
  began = time.monotonic()
  assert owner.control('pause', paused=True)
  assert time.monotonic() - began < .1
  assert owner.queued['action'] == 'pause'
  release.set()
  pump(owner, lambda: backend.status['paused'])


def page_for_input():
  controller = NS(status={'epoch': 1, 'start': 0, 'end': 120, 'position': 30, 'rate': 1, 'paused': False},
                  seek=Mock(), control=Mock(), stop=Mock(), active=True)
  fonts = Mock(profile=Profile.LARGE)
  page = ReplayPage(NS(fonts=fonts, profile=Profile.LARGE), Mock(), controller)
  page.set_rect(rl.Rectangle(0, 0, 2160, 1080))
  page.page = 'viewer'
  return page, controller


def test_timeline_commits_only_on_release_and_epoch_change_cancels():
  page, controller = page_for_input()
  page._handle_mouse_press(NS(x=100, y=940))
  page._handle_mouse_event(NS(left_down=True, left_released=False, pos=NS(x=1570, y=940), t=1))
  controller.seek.assert_not_called()
  page._handle_mouse_release(NS(x=1570, y=940))
  controller.seek.assert_called_once_with(90)
  controller.seek.reset_mock()
  page._handle_mouse_press(NS(x=100, y=940))
  controller.status['epoch'] = 2
  page._handle_mouse_release(NS(x=1000, y=940))
  controller.seek.assert_not_called()


def test_recorded_driving_hit_areas_are_passive():
  page, controller = page_for_input()
  page._handle_mouse_press(NS(x=1680, y=150))
  page._handle_mouse_release(NS(x=1680, y=150))
  controller.control.assert_not_called()
  controller.seek.assert_not_called()
  controller.stop.assert_not_called()


def test_unavailable_duration_does_not_become_zero():
  assert duration(None) == 'Unavailable'
  assert duration(float('nan')) == 'Unavailable'
  assert duration(65) == '1:05'


@pytest.mark.parametrize('active,available,paused,awake', [(True, True, False, True), (True, True, True, False),
                                                         (True, False, False, False), (False, True, False, False)])
def test_only_available_native_playback_keeps_display_awake(monkeypatch, active, available, paused, awake):
  from openpilot.starpilot.ui import replay_settings as module
  page, owner = page_for_input()
  owner.tick = Mock()
  owner.active, owner.available = active, available
  owner.status['paused'] = paused
  reset = Mock()
  monkeypatch.setattr(module.device, '_reset_interactive_timeout', reset)
  monkeypatch.setattr(module, 'ui_state', NS(started=False))
  page._tick()
  assert bool(reset.call_count) is awake


def test_status_recovers_owned_session_after_lost_start_response():
  backend = Backend()
  backend.status.update(sessionId='b' * 32, state='preparing', owned=True)
  owner = ReplayController(backend)
  try:
    pump(owner, lambda: owner.available)
    assert owner.own_session == 'b' * 32
    assert owner.active
    assert owner.stop()
    pump(owner, lambda: backend.status['sessionId'] is None)
  finally:
    owner.close()
    owner.executor.shutdown(wait=True)


def test_owned_ended_session_remains_seekable(playback):
  owner, backend, _, _ = playback
  backend.status.update(state='ended', paused=True, position=120)
  owner.next_status = 0
  pump(owner, lambda: owner.status['state'] == 'ended')
  assert owner.active
  assert owner.seek(30)
  pump(owner, lambda: backend.status['position'] == 30)


def test_fresh_ignition_denial_hides_frame_and_prevents_controls(playback):
  owner, backend, _, _ = playback
  backend.status['offroad'] = False
  owner.next_status = 0
  pump(owner, lambda: owner.status.get('offroad') is False)
  assert not owner.available
  assert not owner.seek(30)
  assert not owner.control('pause', paused=True)


@pytest.mark.parametrize('profile', [Profile.LARGE, Profile.COMPACT])
def test_hud_tap_hides_and_shows_transport(profile):
  page, controller = page_for_input()
  page.profile = profile
  page.set_rect(rl.Rectangle(0, 0, *profile.size))
  page.controls = True
  page._handle_mouse_press(NS(x=220, y=20))
  page._handle_mouse_release(NS(x=220, y=20))
  assert page.last_touch == -float('inf')
  page.controls = False
  page._handle_mouse_press(NS(x=220, y=20))
  page._handle_mouse_release(NS(x=220, y=20))
  assert page.last_touch > 0
  controller.control.assert_not_called()
  controller.seek.assert_not_called()


@pytest.mark.parametrize('profile', [Profile.LARGE, Profile.COMPACT])
def test_transport_autohides_only_during_playback_and_tap_does_not_activate_hidden_buttons(monkeypatch, profile):
  from openpilot.starpilot.ui import replay_settings as module
  page, owner = page_for_input()
  page.profile = profile
  page.set_rect(rl.Rectangle(0, 0, *profile.size))
  page.fonts.measure.return_value = NS(width=20, height=20)
  page._button = Mock()
  owner.available, owner.busy, owner.error = True, False, ''
  owner.frame = NS(session_id='b' * 32, epoch=1, frame_id=1, width=profile.size[0], height=profile.size[1], data=b'pixels')
  owner.status.update(state='playing', paused=False)
  monkeypatch.setattr(module, 'ui_state', NS(started=False))
  for name in ('set_texture_filter', 'update_texture', 'draw_texture_pro', 'draw_rectangle', 'draw_circle'):
    monkeypatch.setattr(rl, name, Mock())
  monkeypatch.setattr(rl, 'load_texture_from_image', Mock(return_value=NS(width=profile.size[0], height=profile.size[1])))
  now = 10
  monkeypatch.setattr(module.time, 'monotonic', lambda: now)
  page.last_touch = 0
  page._render_viewer()
  assert page.controls  # Preparation time does not consume the initial visibility timeout.
  panel = rl.draw_rectangle.call_args_list[0].args[-1]
  assert panel.a == 190
  now = 14
  page._button.reset_mock()
  page._render_viewer()
  assert not page.controls
  page._button.assert_called_once_with('Stop', page._collapsed_stop_bounds(), True)
  left, top, width, height = page._collapsed_stop_bounds()
  assert page._target(left + width / 2, top + height / 2) == 'Stop'
  timeline, buttons = page._transport()
  x, y, w, h = buttons[1][1]
  play_pos = NS(x=x + w / 2, y=y + h / 2)
  assert page._target(play_pos.x, play_pos.y) == 'show'
  page._handle_mouse_press(play_pos)
  page._render_viewer()
  page._handle_mouse_release(play_pos)
  owner.control.assert_not_called()
  owner.seek.assert_not_called()
  page._render_viewer()
  assert page.controls
  now = 16
  x, y, _, seek_height = timeline
  seek_pos = NS(x=x, y=y + seek_height / 2)
  page._handle_mouse_press(seek_pos)
  now = 20
  page._render_viewer()
  assert page.controls  # A held seek gesture must not disappear mid-drag.
  page._handle_mouse_release(seek_pos)
  assert page.last_touch == 20
  now = 24
  for state in ('paused', 'preparing', 'buffering', 'ended'):
    owner.status['state'] = state
    page._render_viewer()
    assert page.controls
  owner.status['state'] = 'playing'
  page._render_viewer()
  assert not page.controls
  page._back = Mock()
  pos = NS(x=left + width / 2, y=top + height / 2)
  page._handle_mouse_press(pos)
  page._render_viewer()
  assert not page.controls
  page._handle_mouse_release(pos)
  page._back.assert_called_once()


def test_gap_seek_snaps_to_nearest_available_footage(playback):
  owner, backend, _, _ = playback
  owner.status['seekRanges'] = [[0, 20], [80, 120]]
  assert owner.seek(35)
  pump(owner, lambda: backend.status['position'] == 20)
  assert next(call for call in backend.calls if call['op'] == 'control')['position'] == 20


def test_seek_preparation_clears_frame_before_epoch_advances(playback):
  owner, backend, _, _ = playback
  owner.frame = NS(session_id=owner.own_session, epoch=1, frame_id=1)
  backend.status.update(state='seeking', frameReady=False)
  owner.next_status = 0
  pump(owner, lambda: owner.status['state'] == 'seeking')
  assert owner.status['epoch'] == 1
  assert owner.frame is None


def test_close_stops_owned_status_that_arrives_after_dismissal():
  backend = Backend()
  backend.status.update(sessionId='b' * 32, state='playing', owned=True)
  entered, release = threading.Event(), threading.Event()
  def request(payload):
    if payload['op'] == 'status':
      entered.set()
      release.wait(2)
    return backend(payload)
  owner = ReplayController(request)
  assert owner.submit({'op': 'status', 'clientId': owner.client_id})
  assert entered.wait(2)
  owner.close()
  release.set()
  owner.executor.shutdown(wait=True)
  assert [call['op'] for call in backend.calls] == ['status', 'stop']
  assert backend.status['sessionId'] is None


@pytest.mark.parametrize('profile,size', [(Profile.LARGE, (1600, 800)), (Profile.COMPACT, (536, 240))])
def test_passive_frame_texture_upload_is_cached_and_uses_full_profile(monkeypatch, profile, size):
  from openpilot.starpilot.ui import replay_settings as module
  page, owner = page_for_input()
  page.profile = profile
  page._button = Mock()
  page.fonts.measure.return_value = NS(width=20, height=20)
  owner.available, owner.busy, owner.error = True, False, ''
  owner.frame = NS(session_id='b' * 32, epoch=1, frame_id=1, width=size[0], height=size[1],
                   data=b'\0\xff\x80\x01' * (size[0] * size[1]))
  monkeypatch.setattr(module, 'ui_state', NS(started=False))
  texture = NS(width=size[0], height=size[1])
  monkeypatch.setattr(rl, 'load_texture_from_image', Mock(return_value=texture))
  monkeypatch.setattr(rl, 'set_texture_filter', Mock())
  def check_upload(actual_texture, pixels):
    assert actual_texture is texture
    assert rl.ffi.typeof(pixels) == rl.ffi.typeof('void *')
    assert bytes(rl.ffi.buffer(pixels, len(owner.frame.data))) == owner.frame.data

  upload, draw = Mock(side_effect=check_upload), Mock()
  monkeypatch.setattr(rl, 'update_texture', upload)
  monkeypatch.setattr(rl, 'draw_texture_pro', draw)
  monkeypatch.setattr(rl, 'draw_rectangle', Mock())
  monkeypatch.setattr(rl, 'draw_circle', Mock())
  monkeypatch.setattr(rl, 'draw_ring', Mock())
  page._render_viewer()
  page._render_viewer()
  rl.draw_ring.assert_not_called()
  assert '0:30 / 2:00' in [call.args[0] for call in page.fonts.draw.call_args_list]
  assert upload.call_count == 1
  rect = draw.call_args.args[2]
  assert (rect.x, rect.y, rect.width, rect.height) == (0, 0, *profile.size)
  assert page.frame_key == ('b' * 32, 1, 1)
  owner.frame = NS(**{**vars(owner.frame), 'epoch': 2, 'data': b'\xff\0\x01\x80' * (size[0] * size[1])})
  page._render_viewer()
  assert upload.call_count == 2
  rl.load_texture_from_image.assert_called_once()


def test_paused_new_epoch_frame_can_be_reread_after_status_catches_up():
  backend = Backend()
  frame = NS(session_id='b' * 32, epoch=2, frame_id=1, data=b'paused')
  readers = []
  class FrozenReader:
    def __init__(self):
      self.used = False
    def latest(self):
      if self.used:
        return None
      self.used = True
      return frame
    def close(self):
      pass
  def factory(*_):
    reader = FrozenReader()
    readers.append(reader)
    return reader
  owner = ReplayController(backend, factory)
  try:
    pump(owner, lambda: owner.available and owner.pending is None)
    owner.select(ROUTE)
    pump(owner, lambda: owner.pending is None)
    owner.start()
    pump(owner, lambda: readers and readers[0].used and owner.pending is None)
    assert owner.frame is None  # owner is still at epoch 1
    backend.status.update(epoch=2, paused=True, state='paused')
    owner.next_status = 0
    pump(owner, lambda: owner.frame is frame)
    assert len(readers) == 2
  finally:
    owner.close()
    owner.executor.shutdown(wait=True)


def test_owned_dynamic_source_warning_is_retained_for_route_details(playback):
  owner, backend, _, _ = playback
  warning = 'Stop duration before this seek is unavailable.'
  backend.status['sourceWarnings'] = [warning]
  owner.next_status = 0
  pump(owner, lambda: owner.source_warnings == [warning])
  assert owner.stop()
  pump(owner, lambda: owner.status['state'] == 'idle')
  assert owner.source_warnings == [warning]
  page = ReplayPage(NS(fonts=Mock(profile=Profile.LARGE), profile=Profile.LARGE), Mock(), owner)
  page.page = 'detail'
  assert warning in page._warnings()


@pytest.fixture
def route_detail():
  page, owner = page_for_input()
  page.page = 'detail'
  page.fonts.measure.return_value = NS(width=200, height=50)
  owner.detail = {**ROUTE, 'segmentCount': 3, 'warnings': [f'Warning {number}' for number in range(32)],
                  'segments': [{'number': number, 'files': {'rlog': number != 3, 'qlog': False, 'fcamera': True, 'qcamera': False}}
                               for number in (0, 2, 3)]}
  owner.selected_route = ROUTE['routeId']
  owner.routes, owner.catalog_loaded = [ROUTE], True
  owner.source_warnings = ['Warning 0', 'Recorded clock unavailable']
  owner.available, owner.busy, owner.error = True, False, ''
  owner.status['state'] = 'idle'
  owner.start = Mock()
  return page, owner


@pytest.mark.parametrize('profile', [Profile.LARGE, Profile.COMPACT])
def test_details_are_fixed_with_pinned_play_and_do_not_paginate(route_detail, monkeypatch, profile):
  from openpilot.starpilot.ui import replay_settings as module
  page, owner = route_detail
  page.profile = profile
  page.set_rect(rl.Rectangle(0, 0, *profile.size))
  page._button = Mock()
  monkeypatch.setattr(module, 'draw_settings_header', Mock())
  page._render_detail()
  buttons = page._button.call_args_list
  assert len(buttons) == (3 if profile == Profile.LARGE else 4)  # Warnings cannot grow the summary into more pages.
  label, bounds, enabled = buttons[-1].args
  assert label == 'Play' and enabled
  assert bounds == ((72, 916, 2016, 128) if profile == Profile.LARGE else (12, 184, 512, 48))
  for _, rect, _, _ in page._detail_buttons():
    x, y, w, h = rect
    assert 0 <= x < x + w <= profile.size[0] and 0 <= y < y + h <= profile.size[1]
  assert not any('Warning 0' in call.args[0] for call in page.fonts.draw.call_args_list)
  x, y, w, h = bounds
  pos = NS(x=x + w / 2, y=y + h / 2)
  page._handle_mouse_press(pos)
  page._handle_mouse_release(pos)
  owner.start.assert_called_once_with()
  owner.start.reset_mock()
  owner.available = False
  page._handle_mouse_press(pos)
  page._handle_mouse_release(pos)
  owner.start.assert_not_called()


def test_warning_dialog_keeps_full_list_and_deduplicates_dynamic_notes(route_detail, monkeypatch):
  from openpilot.starpilot.ui import replay_settings as module
  page, _ = route_detail
  dialog = NS(_html_renderer=NS(elements=[]))
  factory = Mock(return_value=dialog)
  monkeypatch.setattr('openpilot.system.ui.widgets.confirm_dialog.ConfirmDialog', factory)
  monkeypatch.setattr(module.gui_app, 'push_widget', Mock())
  page._show_warnings()
  text = factory.call_args.args[0]
  assert text.count('<p>Warning 0</p>') == 1
  assert '<p>Warning 31</p>' in text and 'Recorded clock unavailable' in text
  assert factory.call_args.kwargs['rich']
  module.gui_app.push_widget.assert_called_once_with(dialog)


def test_segment_picker_filters_missing_sources_and_starts_exact_selection(route_detail, monkeypatch):
  from openpilot.starpilot.ui import replay_settings as module
  from openpilot.system.ui.widgets import DialogResult
  page, owner = route_detail
  picker = NS(selection='Segment 2', select_button=Mock())
  factory = Mock(return_value=picker)
  monkeypatch.setattr('openpilot.system.ui.widgets.option_dialog.MultiOptionDialog', factory)
  monkeypatch.setattr(module.gui_app, 'push_widget', Mock())
  monkeypatch.setattr(module.gui_app, 'get_active_widget', lambda: page)
  page._choose_segment()
  assert factory.call_args.args[1] == ['Segment 0', 'Segment 2']
  callback = factory.call_args.kwargs['callback']
  callback(DialogResult.CANCEL)
  owner.start.assert_not_called()
  callback(DialogResult.CONFIRM)
  owner.start.assert_called_once_with(segment=2)
  owner.start.reset_mock()
  owner.selected_route = 'another-route'
  callback(DialogResult.CONFIRM)
  owner.start.assert_not_called()


def test_compact_warnings_use_native_description_screen(route_detail, monkeypatch):
  from openpilot.starpilot.ui import replay_settings as module
  page, _ = route_detail
  page.profile = Profile.COMPACT
  factory = Mock()
  monkeypatch.setattr('openpilot.selfdrive.ui.mici.widgets.dialog.SettingDescriptionDialog', factory)
  monkeypatch.setattr(module.gui_app, 'push_widget', Mock())
  page._show_warnings()
  title, text = factory.call_args.args
  assert title == 'warnings'
  assert text.splitlines() == list(page._warnings())
  module.gui_app.push_widget.assert_called_once_with(factory.return_value)


def test_compact_segment_cards_close_chooser_and_start_exact_segment(route_detail, monkeypatch):
  from openpilot.starpilot.ui import replay_settings as module
  page, owner = route_detail
  page.profile = Profile.COMPACT
  buttons = []
  picker = NS(_scroller=NS(add_widgets=lambda widgets: buttons.extend(widgets)))
  active = [page.stack_widget]
  monkeypatch.setattr('openpilot.system.ui.widgets.scroller.NavScroller', Mock(return_value=picker))
  factory = Mock(side_effect=lambda *_: Mock())
  monkeypatch.setattr(module, 'BigButton', factory)
  monkeypatch.setattr(module.gui_app, 'push_widget', lambda widget: active.__setitem__(0, widget))
  monkeypatch.setattr(module.gui_app, 'pop_widget', lambda: active.__setitem__(0, page.stack_widget))
  monkeypatch.setattr(module.gui_app, 'get_active_widget', lambda: active[0])
  page._choose_segment()
  assert [call.args[0] for call in factory.call_args_list] == ['segment 0', 'segment 2']
  callback = buttons[1].set_click_callback.call_args.args[0]
  callback()
  assert active[0] is page.stack_widget
  owner.start.assert_called_once_with(segment=2)
  owner.start.reset_mock()
  active[0] = picker
  owner.selected_route = 'another-route'
  callback()
  owner.start.assert_not_called()


@pytest.mark.parametrize('page_name,returns_to_routes,dismisses', [('detail', True, False), ('routes', False, True), ('viewer', False, False)])
def test_compact_swipe_down_goes_back_one_level_and_is_blocked_during_playback(monkeypatch, page_name, returns_to_routes, dismisses):
  from openpilot.starpilot.ui import replay_settings as module
  monkeypatch.setattr(module.gui_app, 'texture', Mock(return_value=NS(width=96, height=48)))
  controller = NS(close=Mock())
  page = ReplayCompactPage(NS(fonts=Mock(profile=Profile.COMPACT), profile=Profile.COMPACT), controller)
  page.set_rect(rl.Rectangle(0, 0, 536, 240))
  page.content.page = page_name
  page.content.press = (200, 40, 'held button', 1, True)
  for y, pressed, down, released in [(40, True, True, False), (160, False, True, False), (160, False, False, True)]:
    page._handle_mouse_event(NS(pos=NS(x=200, y=y), left_pressed=pressed, left_down=down, left_released=released))
  assert page._playing_dismiss_animation is dismisses
  assert page.content.page == ('routes' if returns_to_routes else page_name)
  if returns_to_routes:
    assert page.content.press is None
  controller.close.assert_not_called()


def test_compact_route_card_shows_segment_count_and_availability(route_detail, monkeypatch):
  from openpilot.starpilot.ui import replay_settings as module
  page, _ = route_detail
  page.page, page.profile = 'routes', Profile.COMPACT
  page.cards = NS(_scroller=NS(items=[], add_widgets=Mock()))
  factory = Mock()
  monkeypatch.setattr(module, 'BigButton', factory)
  monkeypatch.setattr(module.gui_app, '_mouse_events', [])
  page._compact_cards()
  assert factory.call_args.args[1] == '2 segments - ready'


def test_compact_underlying_buttons_are_disabled_during_overlays_and_back_gestures(monkeypatch):
  from openpilot.starpilot.ui import replay_settings as module
  monkeypatch.setattr(module.gui_app, 'texture', Mock(return_value=NS(width=96, height=48)))
  page = ReplayCompactPage(NS(fonts=Mock(profile=Profile.COMPACT), profile=Profile.COMPACT), NS(close=Mock()))
  assert page.content.enabled and page.content.cards.enabled
  page.set_enabled(False)
  assert not page.content.enabled and not page.content.cards.enabled
  page.set_enabled(True)
  page._dragging_down = True
  assert not page.content.enabled and not page.content.cards.enabled
  page._dragging_down = False
  assert page.content.enabled and page.content.cards.enabled


@pytest.mark.parametrize('profile', [Profile.LARGE, Profile.COMPACT])
@pytest.mark.parametrize('state,error', [('preparing', ''), ('seeking', ''), ('buffering', ''),
                                       ('playing', ''), ('failed', 'Replay failed')])
def test_loading_is_centered_and_warnings_and_unknown_timing_stay_out_of_viewer(monkeypatch, profile, state, error):
  from openpilot.starpilot.ui import replay_settings as module
  page, owner = page_for_input()
  page.profile = profile
  page._button = Mock()
  page.fonts.measure.return_value = NS(width=200, height=32)
  owner.available, owner.busy, owner.error, owner.frame = True, False, error, None
  owner.status.update(state=state, end=None, sourceWarnings=['This route has missing segments'])
  monkeypatch.setattr(module, 'ui_state', NS(started=False))
  monkeypatch.setattr(rl, 'draw_rectangle', Mock())
  monkeypatch.setattr(rl, 'draw_circle', Mock())
  ring = Mock()
  monkeypatch.setattr(rl, 'draw_ring', ring)
  monkeypatch.setattr(module.time, 'monotonic', lambda: 1)
  page._render_viewer()
  texts = [call.args[0] for call in page.fonts.draw.call_args_list]
  assert 'Timing unavailable' not in texts
  assert not any('missing segments' in text for text in texts)
  if error:
    ring.assert_not_called()
    assert error in texts
  else:
    assert ('Replay preparing' if state == 'preparing' else 'Replay loading') in texts
    center, _, radius, angle, *_ = ring.call_args.args
    assert center.x == profile.size[0] / 2
    text = page.fonts.draw.call_args.args
    assert text[3] + 100 == center.x
    assert text[4] > center.y + radius
    monkeypatch.setattr(module.time, 'monotonic', lambda: 1.1)
    page._render_viewer()
    assert ring.call_args.args[3] != angle
