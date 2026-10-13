"""Bookmark taps reach the existing native UI action, without duplicate IPC publishers."""
import ast
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest

from openpilot.starpilot.system.android_auto.projection_bookmark import BookmarkReceiver, BookmarkSender, MAX_AGE_NS


@pytest.fixture
def transport():
  # macOS Unix sockets have a short path limit; pytest's per-test paths exceed it.
  with tempfile.TemporaryDirectory(prefix='aa-bm-', dir='/tmp') as directory:
    path = Path(directory) / 'bookmark.sock'
    receiver, sender = BookmarkReceiver(path), BookmarkSender(path)
    try:
      yield receiver, sender
    finally:
      sender.close()
      receiver.close()
    assert not path.exists()


def native_poll():
  # Exercise the production native dispatch without loading device-only UI/IPC libraries.
  source = Path(__file__).parents[3] / 'ui/runtime_app.py'
  tree = ast.parse(source.read_text())
  method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == '_poll_projection_bookmark')
  namespace: dict[str, Any] = {'ui_state': NS(started=True, started_frame=1, sm=NS(logMonoTime={'carState': 50})),
                             'display_message': Mock(return_value=object()), 'cast': cast}
  exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
  return namespace


def test_request_publishes_a_bookmark_whatever_the_comma_screen_shows(transport):
  # The comma screen's alerts and page gate taps on that screen, not taps on the car's.
  receiver, sender = transport
  namespace = native_poll()
  publish = Mock()
  session = NS(_projection_bookmarks=receiver, _publish_bookmark=publish,
               _favorite_authority=Mock(side_effect=AssertionError('the comma screen does not gate car taps')))
  with patch('time.monotonic_ns', return_value=100):
    assert sender.send(50)
  namespace['_poll_projection_bookmark'](session, 101)
  publish.assert_called_once_with()
  namespace['_poll_projection_bookmark'](session, 102)
  publish.assert_called_once_with()


@pytest.mark.parametrize('block', ['offroad', 'stale_car', 'replay', 'no_publisher'])
def test_native_ui_consumes_requests_it_cannot_bookmark(transport, block):
  receiver, sender = transport
  namespace = native_poll()
  publish = Mock()
  session = NS(_projection_bookmarks=receiver, _publish_bookmark=None if block == 'no_publisher' else publish)
  namespace['ui_state'].started = block != 'offroad'
  if block == 'replay':
    namespace['ui_state'].replay_clock = object()
  if block == 'stale_car':
    namespace['display_message'].return_value = None
  with patch('time.monotonic_ns', return_value=100):
    assert sender.send(50)
  namespace['_poll_projection_bookmark'](session, 101)
  publish.assert_not_called()
  assert receiver.drain(102, 50, authorized=True) == 0


def test_stale_future_duplicate_and_malformed_requests_are_dropped(transport):
  receiver, sender = transport
  now = 2 * MAX_AGE_NS
  for raw in (b'bad', b'1:2:3', f'{now - MAX_AGE_NS - 1}:50'.encode(), f'{now + 1}:50'.encode(),
              f'{now}:{50 + MAX_AGE_NS + 1}'.encode(), f'{now}:{50 - MAX_AGE_NS - 1}'.encode()):
    sender.sock.sendto(raw, sender.path)
  assert receiver.drain(now, 50, authorized=True) == 0
  with patch('time.monotonic_ns', return_value=now):
    assert sender.send(50)
    assert sender.send(50)
  assert receiver.drain(now, 50, authorized=True) == 1
  assert receiver.drain(now, 50, authorized=True) == 0


def test_small_car_state_skew_between_renderers_does_not_lose_tap(transport):
  receiver, sender = transport
  with patch('time.monotonic_ns', return_value=100):
    assert sender.send(60)
  assert receiver.drain(101, 50, authorized=True) == 1


def test_sender_is_best_effort_when_native_ui_unavailable(tmp_path):
  sender = BookmarkSender(tmp_path / 'missing.sock')
  try:
    assert not sender.send(0)
    assert not sender.send(True)
    assert not sender.send(50)
  finally:
    sender.close()


def test_tap_after_a_frame_draw_still_sends(transport):
  # The car screen reads car state, draws for ~25 ms, then handles taps: past carState's 20 ms control limit.
  import time
  from openpilot.starpilot.system.android_auto.projection_bookmark import request_bookmark
  from openpilot.starpilot.ui.runtime_snapshot import current_message, display_message
  receiver, sender = transport
  now = time.monotonic_ns()

  class SubMaster(NS):
    def __getitem__(self, service):
      return f'{service} message'

  def ui(age_ns, *, started=True, valid=True):
    sm = SubMaster(logMonoTime={'carState': now - age_ns}, valid={'carState': valid}, alive={'carState': True},
                   recv_frame={'carState': 5})
    return NS(started=started, started_frame=1, sm=sm)
  assert current_message(ui(30_000_000).sm, 'carState', now, after_frame=1) is None, 'the old check dropped every tap'
  assert request_bookmark(sender, ui(30_000_000), display_message, now)
  assert receiver.drain(time.monotonic_ns(), now - 30_000_000, authorized=True) == 1
  for state in (ui(300_000_000), ui(30_000_000, started=False), ui(30_000_000, valid=False)):
    assert not request_bookmark(sender, state, display_message, now)
  assert receiver.drain(time.monotonic_ns(), now, authorized=True) == 0
